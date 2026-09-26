from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Title = Annotated[NonBlank, Field(max_length=240)]
Priority = Literal["low", "medium", "high", "urgent"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class TicketInput(StrictModel):
    external_id: Annotated[NonBlank, Field(max_length=120)]
    title: Title
    body: Annotated[NonBlank, Field(max_length=10_000)]
    customer: Annotated[NonBlank, Field(max_length=200)]
    priority: Priority = "medium"


class TicketOut(TicketInput):
    id: str
    status: Literal["open", "in_review", "reviewed"]
    created_at: str


class IngestInput(StrictModel):
    tickets: Annotated[list[TicketInput], Field(min_length=1, max_length=100)]


class DocumentInput(StrictModel):
    title: Title
    content: Annotated[NonBlank, Field(max_length=20_000)]
    source: Annotated[NonBlank, Field(max_length=500)]


class DocumentOut(DocumentInput):
    id: str
    created_at: str


class DecisionInput(StrictModel):
    decision: Literal["approve", "reject"]
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ""


class Citation(StrictModel):
    document_id: str
    title: str
    excerpt: str
    score: float = Field(ge=0, le=1)


class Step(StrictModel):
    name: str
    status: str
    detail: str
    duration_ms: float = Field(ge=0)


class AnalysisOut(StrictModel):
    id: str
    ticket_id: str
    summary: str
    recommended_action: str
    risk: Literal["low", "medium", "high"]
    confidence: float = Field(ge=0, le=1)
    citations: list[Citation]
    steps: list[Step]
    draft_reply: str
    needs_escalation: bool
    provider: str
    latency_ms: float = Field(ge=0)
    created_at: str
    action_id: str


class ActionOut(StrictModel):
    id: str
    ticket_id: str
    analysis_id: str
    kind: str
    status: Literal["pending", "approved", "rejected"]
    payload: dict
    result: dict | None
    created_at: str
    decided_at: str | None


class AuditOut(StrictModel):
    id: str
    event: str
    entity_id: str
    detail: dict
    created_at: str


class EvaluationCase(StrictModel):
    id: str
    name: str
    passed: bool
    expected: str
    actual: str
    latency_ms: float


class EvaluationOut(StrictModel):
    id: str
    total: int
    passed: int
    pass_rate: float = Field(ge=0, le=1)
    cases: list[EvaluationCase]
    created_at: str
