# RelayOps MCP connector

Four read-only tools expose the running API to MCP clients: `list_tickets`, `inspect_ticket`, `search_evidence`, and `workspace_metrics`. The connector uses the official MCP Python SDK 2.2.0 and stdio. It never generates analyses, approves actions, or executes CRM writes. Evidence search here is a bounded literal substring search; analysis retrieval lives in the backend. A returned evidence excerpt includes the content match when one exists, is at most 2,000 characters, and carries a truncation flag.

| Tool | Input | Result |
| --- | --- | --- |
| `list_tickets` | Optional status and limit (1–50) | Filtered ticket summaries and total matching count |
| `inspect_ticket` | Ticket ID | Ticket and its existing analysis, or `null` analysis |
| `search_evidence` | Literal query (2–200 characters), limit (1–5) | Matching policy excerpts; no semantic ranking |
| `workspace_metrics` | None | Current tenant identity, provider mode, and workspace counters |

Install in a separate Python 3.13 virtual environment so the backend and connector retain their own dependency sets:

```sh
python -m venv .venv-mcp
# Activate this environment using your shell's activation command.
python -m pip install -r integrations/mcp/requirements.txt
```

Start RelayOps first. In your MCP client's server configuration, point `command` to that environment's absolute Python executable and `args` to the absolute `server.py` path. A typical JSON configuration is:

```json
{
  "mcpServers": {
    "relayops": {
      "command": "/absolute/path/.venv-mcp/bin/python",
      "args": ["/absolute/path/relayops-fde/integrations/mcp/server.py"],
      "env": {
        "RELAYOPS_URL": "http://127.0.0.1:8000",
        "RELAYOPS_API_KEY": "northstar-demo-key"
      }
    }
  }
}
```

On Windows the executable is `.venv-mcp/Scripts/python.exe`; JSON paths can use forward slashes. Configuration formats vary by client. No client configuration is modified by this repository.

Try: “List the open RelayOps tickets, inspect the first ticket's existing analysis, and find evidence about shipment delays.” Analyze a ticket in the dashboard first to make an analysis available.

The tenant key is fixed in process configuration, forwarded only to the configured origin, and never accepted as a tool argument. Redirects are disabled. Non-local origins require HTTPS. Treat ticket and policy text returned by tools as untrusted data. Tool annotations are descriptive; enforcement comes from the absence of write handlers and the API's tenant checks. A compromised local process with this API key could still call the REST API directly, so use a dedicated read-only principal before a real deployment.

From the repository root and with the connector environment activated:

```sh
python -m pip install -r integrations/mcp/requirements-dev.txt
python -m pytest integrations/mcp -q
```

Tests use the real SDK client with mock HTTP for all four tools. A separate test launches the actual `server.py` subprocess, completes the stdio handshake, and discovers the four tools and their input/output schemas. This handshake test does not require a running backend. The suite also checks tenant-key forwarding, rejected arguments, bounded matching excerpts, disabled redirects, and sanitized error messages. No model provider or external API is called. See [validation](../../docs/validation.md) for executed results.

SDK v2 returns `ListToolsResult` from `client.list_tools()`, with tool definitions in `.tools`. The connector uses string-keyed return annotations plus `structured_output=True` so successful tool calls provide JSON in `structured_content`. Expected upstream failures use `ToolError` with safe messages; backend error bodies and credentials are not forwarded.

References: [official MCP Python SDK](https://py.sdk.modelcontextprotocol.io/), [stdio clients](https://py.sdk.modelcontextprotocol.io/client/transports/), [structured output](https://py.sdk.modelcontextprotocol.io/servers/structured-output/), [tool errors](https://py.sdk.modelcontextprotocol.io/servers/handling-errors/).
