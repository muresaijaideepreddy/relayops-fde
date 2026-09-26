from time import perf_counter

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from . import models
from .config import Settings
from .providers import demo_draft, openai_draft
from .retrieval import EvidenceDocument, retrieve
from .schemas import AnalysisOut, DecisionInput, TicketInput


def audit(session, tenant_id: str, event: str, entity_id: str, detail: dict) -> None:
    session.add(models.Audit(tenant_id=tenant_id, event=event, entity_id=entity_id, detail=detail))


def scoped_one(session, model, tenant_id: str, entity_id: str):
    row = session.scalar(select(model).where(model.tenant_id == tenant_id, model.id == entity_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Resource not found in this workspace")
    return row


def ingest_tickets(session, tenant_id: str, tickets: list[TicketInput]) -> dict:
    imported = 0
    for ticket in tickets:
        try:
            with session.begin_nested():
                row = models.Ticket(tenant_id=tenant_id, **ticket.model_dump())
                session.add(row)
                session.flush()
        except IntegrityError:
            # A database constraint, not a preflight check, arbitrates concurrent imports.
            existing = session.scalar(
                select(models.Ticket.id).where(
                    models.Ticket.tenant_id == tenant_id,
                    models.Ticket.external_id == ticket.external_id,
                )
            )
            if existing is None:
                raise
        else:
            imported += 1
    result = {"imported": imported, "skipped": len(tickets) - imported}
    audit(session, tenant_id, "tickets.ingested", tenant_id, result)
    session.commit()
    return result


def analyze_ticket(
    session, settings: Settings, tenant_id: str, ticket_id: str, client=None
) -> dict:
    started = perf_counter()
    ticket = scoped_one(session, models.Ticket, tenant_id, ticket_id)
    documents = session.scalars(
        select(models.Document).where(models.Document.tenant_id == tenant_id)
    ).all()
    evidence = [EvidenceDocument(d.id, d.tenant_id, d.title, d.content) for d in documents]
    retrieve_start = perf_counter()
    citations = retrieve(ticket.title + " " + ticket.body, evidence, tenant_id)
    retrieve_ms = (perf_counter() - retrieve_start) * 1000
    draft_start = perf_counter()
    if settings.ai_provider == "openai":
        result = openai_draft(
            settings, ticket.title, ticket.body, ticket.priority, citations, client=client
        )
    else:
        result = demo_draft(ticket.title, ticket.body, ticket.priority, citations)
    draft_ms = (perf_counter() - draft_start) * 1000
    analysis_id, action_id = models.new_id(), models.new_id()
    draft_data = result.draft.model_dump(exclude={"citation_ids"})
    data = AnalysisOut(
        id=analysis_id,
        ticket_id=ticket_id,
        action_id=action_id,
        **draft_data,
        citations=result.citations,
        provider=result.provider,
        latency_ms=round((perf_counter() - started) * 1000, 3),
        created_at=models.now(),
        steps=[
            {
                "name": "Tenant evidence retrieval",
                "status": "completed" if citations else "abstained",
                "detail": f"Searched {len(evidence)} workspace documents; found {len(citations)} lexical matches. At least two distinct matching terms are required.",
                "duration_ms": round(retrieve_ms, 3),
            },
            {
                "name": "Grounded draft",
                "status": "escalation" if result.draft.needs_escalation else "completed",
                "detail": f"Provider: {result.provider}. Citation IDs were constrained to retrieved workspace evidence. Confidence is a heuristic, not calibrated probability.",
                "duration_ms": round(draft_ms, 3),
            },
            {
                "name": "Human approval gate",
                "status": "pending",
                "detail": "A reviewer must approve the local simulated CRM note. No external action is available.",
                "duration_ms": 0,
            },
        ],
    ).model_dump()
    session.add(
        models.Analysis(id=analysis_id, tenant_id=tenant_id, ticket_id=ticket_id, data=data)
    )
    session.flush()
    session.add(
        models.Action(
            id=action_id,
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            analysis_id=analysis_id,
            payload={
                "connector": "local-simulated-crm",
                "note": result.draft.draft_reply,
                "recommended_action": result.draft.recommended_action,
                "requires_specialist": result.draft.needs_escalation,
            },
        )
    )
    ticket.status = "in_review"
    audit(
        session,
        tenant_id,
        "analysis.created",
        analysis_id,
        {
            "ticket_id": ticket_id,
            "action_id": action_id,
            "provider": result.provider,
            "citation_count": len(result.citations),
            "needs_escalation": result.draft.needs_escalation,
        },
    )
    session.commit()
    return data


def decide_action(session, tenant_id: str, action_id: str, decision: DecisionInput):
    action = scoped_one(session, models.Action, tenant_id, action_id)
    desired = "approved" if decision.decision == "approve" else "rejected"
    if action.status != "pending":
        if action.status != desired:
            raise HTTPException(409, "This action already has a different decision")
        return action
    decided_at = models.now()
    note_id = models.new_id() if desired == "approved" else None
    result = {
        "connector": "local-simulated-crm",
        "simulated": True,
        "crm_note_id": note_id,
        "message": "Recorded a local CRM note; no external system was contacted."
        if note_id
        else "Rejected without executing the connector.",
        "reviewer_note": decision.note,
    }
    # Serialize decisions for distinct actions on the same ticket on PostgreSQL.
    # SQLite serializes writers when the compare-and-set below acquires its write lock.
    session.execute(
        select(models.Ticket.id)
        .where(models.Ticket.id == action.ticket_id, models.Ticket.tenant_id == tenant_id)
        .with_for_update()
    )
    # Compare-and-set and connector write share one transaction. PostgreSQL and SQLite
    # serialize this update; only its winner is allowed to create a CRM note or audit event.
    changed = session.execute(
        update(models.Action)
        .where(
            models.Action.id == action_id,
            models.Action.tenant_id == tenant_id,
            models.Action.status == "pending",
        )
        .values(status=desired, decided_at=decided_at, result=result),
        execution_options={"synchronize_session": False},
    ).rowcount
    if not changed:
        session.rollback()
        action = scoped_one(session, models.Action, tenant_id, action_id)
        if action.status != desired:
            raise HTTPException(409, "This action already has a different decision")
        return action
    if note_id:
        session.add(
            models.CRMNote(
                id=note_id,
                tenant_id=tenant_id,
                action_id=action_id,
                ticket_id=action.ticket_id,
                content=action.payload["note"],
            )
        )
    other_pending = session.scalar(
        select(models.Action.id)
        .where(
            models.Action.tenant_id == tenant_id,
            models.Action.ticket_id == action.ticket_id,
            models.Action.status == "pending",
        )
        .limit(1)
    )
    has_approved = session.scalar(
        select(models.Action.id)
        .where(
            models.Action.tenant_id == tenant_id,
            models.Action.ticket_id == action.ticket_id,
            models.Action.status == "approved",
        )
        .limit(1)
    )
    ticket_status = "in_review" if other_pending else "reviewed" if has_approved else "open"
    session.execute(
        update(models.Ticket)
        .where(models.Ticket.id == action.ticket_id, models.Ticket.tenant_id == tenant_id)
        .values(status=ticket_status)
    )
    audit(
        session,
        tenant_id,
        f"action.{desired}",
        action_id,
        {
            "ticket_id": action.ticket_id,
            "simulated": True,
            "crm_note_id": note_id,
            "reviewer_note": decision.note,
        },
    )
    session.commit()
    session.expire_all()
    return scoped_one(session, models.Action, tenant_id, action_id)
