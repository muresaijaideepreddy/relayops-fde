import asyncio
from pathlib import Path
import sys

import httpx
from mcp import Client, StdioServerParameters
import pytest

from server import build_server

TOOL_NAMES = {"list_tickets", "inspect_ticket", "search_evidence", "workspace_metrics"}


def test_mcp_exposes_read_only_tools_and_preserves_tenant_key():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.method == "GET"
        assert request.headers["X-API-Key"] == "test-tenant-key"
        if request.url.path.endswith("/analysis"):
            return httpx.Response(200, content="null", headers={"Content-Type": "application/json"})
        if request.url.path.endswith("/tickets/T-1"):
            return httpx.Response(200, json={"id": "T-1", "title": "Late shipment"})
        return httpx.Response(
            200,
            json=[
                {
                    "id": "T-1",
                    "external_id": "EXT-1",
                    "title": "Late shipment",
                    "priority": "high",
                    "status": "open",
                }
            ],
        )

    async def run():
        server = build_server(
            "http://127.0.0.1:8000", "test-tenant-key", transport=httpx.MockTransport(handler)
        )
        async with Client(server, raise_exceptions=True) as client:
            tools = (await client.list_tools()).tools
            assert {tool.name for tool in tools} == TOOL_NAMES
            assert all(tool.annotations.read_only_hint for tool in tools)
            result = await client.call_tool("list_tickets", {"status": "open"})
            assert not result.is_error
            assert result.structured_content["tickets"][0]["id"] == "T-1"
            inspected = await client.call_tool("inspect_ticket", {"ticket_id": "T-1"})
            assert not inspected.is_error
            assert inspected.structured_content["analysis"] is None
            before = len(requests)
            invalid = await client.call_tool("inspect_ticket", {"ticket_id": "../actions/approve"})
            assert invalid.is_error and len(requests) == before
            too_many = await client.call_tool("list_tickets", {"limit": 999})
            assert too_many.is_error and len(requests) == before

    asyncio.run(run())


def test_upstream_auth_errors_are_sanitized():
    async def run():
        server = build_server(
            "http://localhost:8000",
            "secret-test-key",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(401, json={"detail": "internal secret-test-key"})
            ),
        )
        async with Client(server) as client:
            result = await client.call_tool("list_tickets", {})
            assert result.is_error
            assert "secret-test-key" not in str(result)
            assert "authentication failed" in str(result)

    asyncio.run(run())


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://user:password@example.com",
        "file:///tmp/data",
        "https://example.com/api",
        "https://example.com?key=x",
    ],
)
def test_rejects_unsafe_or_ambiguous_origin(url):
    with pytest.raises(ValueError):
        build_server(url, "test-key")


def test_requires_explicit_tenant_key():
    with pytest.raises(ValueError):
        build_server("http://localhost:8000", "")


def test_evidence_search_returns_matching_bounded_excerpts_and_metrics():
    requests = []
    content = "Earlier policy text. " * 150 + "Shipment delays require a tracking review. " * 100

    def handler(request):
        requests.append(request)
        assert request.method == "GET"
        assert request.headers["X-API-Key"] == "tenant-key"
        if request.url.path == "/api/v1/documents":
            return httpx.Response(
                200,
                json=[
                    {"id": "D-1", "title": "Shipping policy", "source": "demo", "content": content},
                    {"id": "D-2", "title": "Other", "source": "demo", "content": "Account access"},
                ],
            )
        if request.url.path == "/api/v1/workspace":
            return httpx.Response(
                200, json={"tenant": {"id": "test", "name": "Test"}, "mode": "demo"}
            )
        if request.url.path == "/api/v1/metrics":
            return httpx.Response(200, json={"total_tickets": 4, "approved_actions": 0})
        raise AssertionError(f"Unexpected path: {request.url.path}")

    async def run():
        server = build_server(
            "http://127.0.0.1:8000", "tenant-key", transport=httpx.MockTransport(handler)
        )
        async with Client(server, raise_exceptions=True) as client:
            result = await client.call_tool("search_evidence", {"query": "sHiPmEnT"})
            assert not result.is_error
            document = result.structured_content["documents"][0]
            assert result.structured_content["total"] == 1
            assert "Shipment" in document["excerpt"]
            assert document["excerpt"] in content
            assert len(document["excerpt"]) <= 2000 and document["truncated"]
            literal = await client.call_tool("search_evidence", {"query": ".*"})
            assert literal.structured_content["documents"] == []
            before = len(requests)
            invalid = await client.call_tool("search_evidence", {"query": "   "})
            assert invalid.is_error and len(requests) == before
            metrics = await client.call_tool("workspace_metrics", {})
            assert metrics.structured_content["workspace"]["tenant"]["id"] == "test"
            assert metrics.structured_content["metrics"]["total_tickets"] == 4

    asyncio.run(run())


def test_does_not_forward_tenant_key_to_a_redirect_target():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "https://other.example/collect"})

    async def run():
        server = build_server(
            "https://relayops.example", "tenant-key", transport=httpx.MockTransport(handler)
        )
        async with Client(server) as client:
            result = await client.call_tool("list_tickets", {})
            assert result.is_error
            assert len(requests) == 1
            assert requests[0].url.host == "relayops.example"

    asyncio.run(run())


def test_invalid_upstream_json_is_a_safe_actionable_error():
    async def run():
        server = build_server(
            "http://localhost:8000",
            "tenant-key",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, text="internal tenant-key diagnostics")
            ),
        )
        async with Client(server) as client:
            result = await client.call_tool("list_tickets", {})
            assert result.is_error
            assert "invalid response" in str(result)
            assert "tenant-key" not in str(result)

    asyncio.run(run())


def test_stdio_subprocess_handshake_and_tool_discovery():
    """Exercise the actual entry point over stdio; discovery makes no HTTP requests."""
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).with_name("server.py").resolve())],
        env={"RELAYOPS_URL": "http://127.0.0.1:8000", "RELAYOPS_API_KEY": "stdio-test-tenant-key"},
    )

    async def run():
        async with Client(parameters) as client:
            result = await client.list_tools()
            assert {tool.name for tool in result.tools} == TOOL_NAMES
            assert all(tool.annotations.read_only_hint for tool in result.tools)
            assert all(tool.input_schema["type"] == "object" for tool in result.tools)
            assert all(tool.output_schema["type"] == "object" for tool in result.tools)

    asyncio.run(asyncio.wait_for(run(), timeout=30))
