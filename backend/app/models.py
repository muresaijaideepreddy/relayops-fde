from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, CheckConstraint, ForeignKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def new_id() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Scoped:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class Ticket(Scoped, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id"),
        UniqueConstraint("tenant_id", "id"),
        CheckConstraint("status IN ('open','in_review','reviewed')"),
        CheckConstraint("priority IN ('low','medium','high','urgent')"),
    )
    external_id: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    customer: Mapped[str] = mapped_column(String(200))
    priority: Mapped[str] = mapped_column(String(12), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="open")


class Document(Scoped, Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("tenant_id", "source"),)
    title: Mapped[str] = mapped_column(String(240))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(500))


class Analysis(Scoped, Base):
    __tablename__ = "analyses"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(["tenant_id", "ticket_id"], ["tickets.tenant_id", "tickets.id"]),
    )
    ticket_id: Mapped[str] = mapped_column(String(36), index=True)
    data: Mapped[dict] = mapped_column(JSON)


class Action(Scoped, Base):
    __tablename__ = "actions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(["tenant_id", "ticket_id"], ["tickets.tenant_id", "tickets.id"]),
        ForeignKeyConstraint(["tenant_id", "analysis_id"], ["analyses.tenant_id", "analyses.id"]),
        CheckConstraint("status IN ('pending','approved','rejected')"),
    )
    ticket_id: Mapped[str] = mapped_column(String(36), index=True)
    analysis_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(50), default="simulated_crm_note")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decided_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class CRMNote(Scoped, Base):
    __tablename__ = "crm_notes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "action_id"),
        ForeignKeyConstraint(["tenant_id", "action_id"], ["actions.tenant_id", "actions.id"]),
    )
    action_id: Mapped[str] = mapped_column(String(36))
    ticket_id: Mapped[str] = mapped_column(String(36))
    content: Mapped[str] = mapped_column(Text)


class Audit(Scoped, Base):
    __tablename__ = "audit_events"
    event: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(120))
    detail: Mapped[dict] = mapped_column(JSON)


class Evaluation(Scoped, Base):
    __tablename__ = "evaluations"
    data: Mapped[dict] = mapped_column(JSON)
