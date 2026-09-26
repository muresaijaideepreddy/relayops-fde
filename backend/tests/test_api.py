from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app import models
from app.config import Settings
from app.main import create_app
from app.schemas import TicketInput
from app.seed import seed_demo
from app.service import ingest_tickets
from conftest import MERIDIAN, NORTH


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/workspace"),
        ("GET", "/tickets"),
        ("GET", "/tickets/missing"),
        ("GET", "/tickets/missing/analysis"),
        ("POST", "/tickets/missing/analyze"),
        ("GET", "/actions"),
        ("POST", "/actions/missing/approve"),
        ("GET", "/audit"),
        ("GET", "/documents"),
        ("POST", "/documents"),
        ("POST", "/ingest"),
        ("GET", "/metrics"),
        ("POST", "/evaluations/run"),
        ("GET", "/evaluations/latest"),
    ],
)
def test_business_routes_require_auth(client, method, path):
    assert client.request(method, "/api/v1" + path).status_code == 401
    assert (
        client.request(method, "/api/v1" + path, headers={"X-API-Key": "wrong-key"}).status_code
        == 401
    )


def test_health_and_trace_headers(client):
    response = client.get("/health")
    assert response.json() == {"status": "ok", "version": "1.0.0"}
    assert len(response.headers["X-Request-ID"]) == 36
    assert "dur=" in response.headers["Server-Timing"]
    assert client.get("/api/v1/workspace", headers=NORTH).headers["Cache-Control"] == "no-store"


def test_cross_tenant_ids_and_lists_are_isolated(client, ticket, action):
    paths = [f"/tickets/{ticket['id']}", f"/tickets/{ticket['id']}/analysis"]
    for path in paths:
        assert client.get("/api/v1" + path, headers=MERIDIAN).status_code == 404
    assert (
        client.post(f"/api/v1/tickets/{ticket['id']}/analyze", headers=MERIDIAN).status_code == 404
    )
    assert (
        client.post(
            f"/api/v1/actions/{action}/approve",
            headers=MERIDIAN,
            json={"decision": "approve", "note": ""},
        ).status_code
        == 404
    )
    assert client.get("/api/v1/actions", headers=MERIDIAN).json() == []
    assert client.get("/api/v1/audit", headers=MERIDIAN).json() == []
    meridian_tickets = client.get("/api/v1/tickets", headers=MERIDIAN).json()
    assert all(t["external_id"].startswith("MR-") for t in meridian_tickets)
    assert all("tenant_id" not in t for t in meridian_tickets)
    meridian_docs = client.get("/api/v1/documents", headers=MERIDIAN).json()
    assert all(d["source"].startswith("demo://meridian/") for d in meridian_docs)


def test_analysis_citations_are_exact_and_action_requires_approval(client, ticket, application):
    assert client.get(f"/api/v1/tickets/{ticket['id']}/analysis", headers=NORTH).json() is None
    response = client.post(f"/api/v1/tickets/{ticket['id']}/analyze", headers=NORTH)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "demo"
    assert data["citations"]
    docs = {d["id"]: d for d in client.get("/api/v1/documents", headers=NORTH).json()}
    for citation in data["citations"]:
        assert citation["excerpt"] in docs[citation["document_id"]]["content"]
    assert 0 < data["confidence"] < 1
    assert all(step["duration_ms"] >= 0 for step in data["steps"])
    pending = client.get("/api/v1/actions", headers=NORTH).json()
    assert pending[0]["status"] == "pending" and pending[0]["result"] is None
    assert (
        client.get(f"/api/v1/tickets/{ticket['id']}", headers=NORTH).json()["status"] == "in_review"
    )
    assert client.get(f"/api/v1/tickets/{ticket['id']}/analysis", headers=NORTH).json() == data
    with application.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(models.CRMNote)) == 0


@pytest.mark.parametrize("external_id", ["NS-1046", "NS-1047"])
def test_no_evidence_and_known_injection_abstain(client, external_id):
    ticket = next(
        t
        for t in client.get("/api/v1/tickets", headers=NORTH).json()
        if t["external_id"] == external_id
    )
    data = client.post(f"/api/v1/tickets/{ticket['id']}/analyze", headers=NORTH).json()
    assert data["citations"] == []
    assert data["needs_escalation"] is True
    assert data["confidence"] <= 0.25
    assert data["risk"] == "high"


def test_ingest_is_idempotent_and_tenant_scoped(client):
    payload = {
        "tickets": [
            {
                "external_id": "SHARED-1",
                "title": "Shipment delay",
                "body": "No shipment tracking scan",
                "customer": "Synthetic",
                "priority": "high",
            }
        ]
    }
    assert client.post("/api/v1/ingest", headers=NORTH, json=payload).json() == {
        "imported": 1,
        "skipped": 0,
    }
    assert client.post("/api/v1/ingest", headers=NORTH, json=payload).json() == {
        "imported": 0,
        "skipped": 1,
    }
    assert client.post("/api/v1/ingest", headers=MERIDIAN, json=payload).json() == {
        "imported": 1,
        "skipped": 0,
    }
    payload["tickets"] *= 2
    assert client.post("/api/v1/ingest", headers=NORTH, json=payload).json() == {
        "imported": 0,
        "skipped": 2,
    }


def test_concurrent_ingestion_uniqueness(client, application):
    barrier = Barrier(6)
    item = TicketInput(
        external_id="RACE-1",
        title="Shipment delayed",
        body="Tracking scan missing",
        customer="Synthetic",
    )

    def worker():
        with application.state.sessions() as db:
            barrier.wait(timeout=10)
            return ingest_tickets(db, "northstar", [item])

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: worker(), range(6)))
    assert sum(r["imported"] for r in results) == 1
    assert sum(r["skipped"] for r in results) == 5


def test_documents_source_conflict_and_tenant_isolation(client):
    payload = {
        "title": "Customer onboarding",
        "content": "Verify workspace ownership before onboarding a user.",
        "source": "manual://onboarding",
    }
    response = client.post("/api/v1/documents", headers=NORTH, json=payload)
    assert response.status_code == 201
    assert response.json()["content"] == payload["content"]
    assert client.post("/api/v1/documents", headers=NORTH, json=payload).status_code == 409
    assert client.post("/api/v1/documents", headers=MERIDIAN, json=payload).status_code == 201


@pytest.mark.parametrize(
    "patch",
    [
        {"title": " "},
        {"body": "x" * 10001},
        {"priority": "critical"},
        {"external_id": "x" * 121},
        {"tenant_id": "meridian"},
        {"customer": ""},
    ],
)
def test_invalid_tickets_are_rejected_atomically(client, patch):
    before = len(client.get("/api/v1/tickets", headers=NORTH).json())
    valid = {
        "external_id": "NEW-1",
        "title": "Valid",
        "body": "Valid body",
        "customer": "Test",
        "priority": "low",
    }
    response = client.post(
        "/api/v1/ingest", headers=NORTH, json={"tickets": [valid, {**valid, **patch}]}
    )
    assert response.status_code == 422
    assert len(client.get("/api/v1/tickets", headers=NORTH).json()) == before


def test_batch_and_document_limits(client):
    item = {"external_id": "NEW-1", "title": "Valid", "body": "Valid body", "customer": "Test"}
    assert (
        client.post("/api/v1/ingest", headers=NORTH, json={"tickets": [item] * 101}).status_code
        == 422
    )
    assert client.post("/api/v1/ingest", headers=NORTH, json={"tickets": []}).status_code == 422
    assert (
        client.post(
            "/api/v1/documents",
            headers=NORTH,
            json={"title": "Valid", "content": "x" * 20001, "source": "test"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/documents",
            headers=NORTH,
            json={"title": "Valid", "content": "   ", "source": "test"},
        ).status_code
        == 422
    )


def test_invalid_approval_input(client, action):
    assert (
        client.post(
            f"/api/v1/actions/{action}/approve", headers=NORTH, json={"decision": "execute"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/actions/{action}/approve",
            headers=NORTH,
            json={"decision": "approve", "note": "x" * 2001},
        ).status_code
        == 422
    )


def test_seed_is_idempotent(client, application):
    with application.state.sessions() as db:
        before = db.scalar(select(func.count()).select_from(models.Ticket))
        seed_demo(db)
        seed_demo(db)
        assert db.scalar(select(func.count()).select_from(models.Ticket)) == before == 9
        assert db.scalar(select(func.count()).select_from(models.Document)) == 7


def test_metrics_measure_tenant_state(client, action):
    north = client.get("/api/v1/metrics", headers=NORTH).json()
    other = client.get("/api/v1/metrics", headers=MERIDIAN).json()
    assert north["analyzed_tickets"] == north["pending_approvals"] == 1
    assert north["grounded_rate"] == 1
    assert other["analyzed_tickets"] == other["pending_approvals"] == other["grounded_rate"] == 0
    client.post(f"/api/v1/actions/{action}/approve", headers=NORTH, json={"decision": "approve"})
    updated = client.get("/api/v1/metrics", headers=NORTH).json()
    assert updated["approved_actions"] == 1 and updated["pending_approvals"] == 0


def test_evaluations_are_isolated_from_mutations_and_other_tenants(client, application):
    with application.state.sessions() as db:
        db.execute(delete(models.Document))
        db.commit()
    response = client.post("/api/v1/evaluations/run", headers=NORTH)
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] == data["total"] == 8
    assert data["pass_rate"] == 1
    assert client.get("/api/v1/evaluations/latest", headers=NORTH).json() == data
    assert client.get("/api/v1/evaluations/latest", headers=MERIDIAN).json() is None
    assert client.get("/api/v1/actions", headers=NORTH).json() == []


def test_non_demo_custom_key_starts_empty_and_rejects_builtin_keys(tmp_path):
    key = "a-custom-secret-that-is-long-enough"
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'custom.db'}",
            demo_mode=False,
            tenant_api_keys={key: {"id": "new-org", "name": "Custom Organization"}},
        )
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/tickets", headers=NORTH).status_code == 401
        assert client.get("/api/v1/tickets", headers={"X-API-Key": key}).json() == []
        assert (
            client.get("/api/v1/workspace", headers={"X-API-Key": key}).json()["tenant"]["id"]
            == "new-org"
        )
