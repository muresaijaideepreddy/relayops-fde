from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select

from app import models, service
from app.schemas import DecisionInput
from conftest import NORTH


def test_approval_records_one_simulated_note_and_rejects_conflict(
    client, action, ticket, application
):
    url = f"/api/v1/actions/{action}/approve"
    first = client.post(
        url, headers=NORTH, json={"decision": "approve", "note": "Verified against policy"}
    )
    repeated = client.post(
        url, headers=NORTH, json={"decision": "approve", "note": "A later retry"}
    )
    assert first.status_code == repeated.status_code == 200
    assert first.json() == repeated.json()
    assert first.json()["result"]["simulated"] is True
    assert first.json()["result"]["reviewer_note"] == "Verified against policy"
    assert client.post(url, headers=NORTH, json={"decision": "reject"}).status_code == 409
    assert (
        client.get(f"/api/v1/tickets/{ticket['id']}", headers=NORTH).json()["status"] == "reviewed"
    )
    with application.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(models.CRMNote)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(models.Audit)
                .where(models.Audit.event == "action.approved")
            )
            == 1
        )


def test_rejection_does_not_execute_and_retries_are_stable(client, action, ticket, application):
    url = f"/api/v1/actions/{action}/approve"
    first = client.post(url, headers=NORTH, json={"decision": "reject", "note": "Needs revision"})
    repeated = client.post(url, headers=NORTH, json={"decision": "reject"})
    assert first.json() == repeated.json()
    assert first.json()["status"] == "rejected"
    assert first.json()["result"]["crm_note_id"] is None
    assert client.get(f"/api/v1/tickets/{ticket['id']}", headers=NORTH).json()["status"] == "open"
    with application.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(models.CRMNote)) == 0


@pytest.mark.parametrize(
    "decisions", [("approve", "approve"), ("reject", "reject"), ("approve", "reject")]
)
def test_concurrent_decisions_use_atomic_compare_and_set(
    client, application, action, monkeypatch, decisions
):
    barrier = Barrier(2)
    seen = local()
    original = service.scoped_one

    def synchronized_read(db, model, tenant_id, entity_id):
        row = original(db, model, tenant_id, entity_id)
        if model is models.Action and not getattr(seen, "initial_read", False):
            seen.initial_read = True
            assert row.status == "pending"
            barrier.wait(timeout=10)
        return row

    monkeypatch.setattr(service, "scoped_one", synchronized_read)

    def worker(decision):
        with application.state.sessions() as db:
            try:
                result = service.decide_action(
                    db,
                    "northstar",
                    action,
                    DecisionInput(decision=decision, note="Concurrent reviewer"),
                )
                return 200, result.status, result.result
            except HTTPException as exc:
                return exc.status_code, None, None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, decisions))
    if decisions[0] == decisions[1]:
        assert outcomes[0] == outcomes[1]
        assert outcomes[0][0] == 200
    else:
        assert sorted(o[0] for o in outcomes) == [200, 409]
    with application.state.sessions() as db:
        saved = db.scalar(select(models.Action).where(models.Action.id == action))
        expected_notes = int(saved.status == "approved")
        assert db.scalar(select(func.count()).select_from(models.CRMNote)) == expected_notes
        assert (
            db.scalar(
                select(func.count())
                .select_from(models.Audit)
                .where(models.Audit.event.in_(["action.approved", "action.rejected"]))
            )
            == 1
        )


def test_connector_failure_rolls_back_decision_and_ticket(client, application, action, ticket):
    def fail_insert(*_):
        raise RuntimeError("simulated persistence failure")

    event.listen(models.CRMNote, "before_insert", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="persistence failure"):
            with application.state.sessions() as db:
                service.decide_action(db, "northstar", action, DecisionInput(decision="approve"))
    finally:
        event.remove(models.CRMNote, "before_insert", fail_insert)
    with application.state.sessions() as db:
        saved = db.scalar(select(models.Action).where(models.Action.id == action))
        assert saved.status == "pending"
        assert saved.result is None
        assert db.scalar(select(func.count()).select_from(models.CRMNote)) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(models.Audit)
                .where(models.Audit.event == "action.approved")
            )
            == 0
        )
    assert (
        client.get(f"/api/v1/tickets/{ticket['id']}", headers=NORTH).json()["status"] == "in_review"
    )


@pytest.mark.parametrize(
    "first_decision,last_decision,expected",
    [
        ("approve", "reject", "reviewed"),
        ("reject", "reject", "open"),
        ("reject", "approve", "reviewed"),
    ],
)
def test_ticket_stays_in_review_until_all_pending_actions_decided(
    client, ticket, action, first_decision, last_decision, expected
):
    second = client.post(f"/api/v1/tickets/{ticket['id']}/analyze", headers=NORTH).json()[
        "action_id"
    ]
    assert second != action
    client.post(
        f"/api/v1/actions/{action}/approve", headers=NORTH, json={"decision": first_decision}
    )
    assert (
        client.get(f"/api/v1/tickets/{ticket['id']}", headers=NORTH).json()["status"] == "in_review"
    )
    client.post(
        f"/api/v1/actions/{second}/approve", headers=NORTH, json={"decision": last_decision}
    )
    assert client.get(f"/api/v1/tickets/{ticket['id']}", headers=NORTH).json()["status"] == expected
