from contextlib import asynccontextmanager
import hmac
import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import __version__, models, schemas
from .config import Settings
from .db import Base, make_database
from .evaluate import run_baseline
from .providers import ProviderFailure
from .seed import seed_demo
from .service import analyze_ticket, audit, decide_action, ingest_tickets, scoped_one


request_logger = logging.getLogger("relayops.requests")
request_logger.setLevel(logging.INFO)
if not request_logger.handlers:
    request_logger.addHandler(logging.StreamHandler())


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    engine, sessions = make_database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(engine)
        if settings.demo_mode:
            with sessions() as session:
                seed_demo(session)
        yield
        engine.dispose()

    app = FastAPI(
        title="RelayOps API",
        version=__version__,
        description="Tenant-scoped support operations portfolio demo. Connector actions are local simulations.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessions = sessions
    # Dependency-injected fake clients are only assigned in tests. None uses the real SDK in opt-in mode.
    app.state.openai_client = None

    @app.middleware("http")
    async def request_trace(request: Request, call_next):
        started = perf_counter()
        request_id = str(uuid4())
        content_length = request.headers.get("content-length", "")
        if content_length.isdigit() and int(content_length) > 5_000_000:
            return JSONResponse({"detail": "Request body exceeds 5 MB"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={(perf_counter() - started) * 1000:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        request_logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "route": getattr(request.scope.get("route"), "path", "<static-or-unmatched>"),
                    "status": response.status_code,
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                }
            )
        )
        return response

    def get_session():
        with sessions() as session:
            yield session

    def tenant(x_api_key: Annotated[str | None, Header()] = None):
        if x_api_key:
            for key, value in settings.keys.items():
                if hmac.compare_digest(x_api_key.encode(), key.encode()):
                    return value
        raise HTTPException(status_code=401, detail="A valid workspace X-API-Key is required")

    DB = Annotated[Session, Depends(get_session)]
    Tenant = Annotated[dict, Depends(tenant)]
    prefix = "/api/v1"

    @app.get("/health")
    def health(db: DB):
        db.execute(text("SELECT 1"))
        return {"status": "ok", "version": __version__}

    @app.get(prefix + "/workspace")
    def workspace(current: Tenant):
        return {"tenant": current, "mode": settings.ai_provider}

    @app.get(prefix + "/tickets", response_model=list[schemas.TicketOut])
    def tickets(db: DB, current: Tenant):
        return db.scalars(
            select(models.Ticket)
            .where(models.Ticket.tenant_id == current["id"])
            .order_by(models.Ticket.created_at, models.Ticket.external_id)
        ).all()

    @app.get(prefix + "/tickets/{ticket_id}", response_model=schemas.TicketOut)
    def ticket(ticket_id: str, db: DB, current: Tenant):
        return scoped_one(db, models.Ticket, current["id"], ticket_id)

    @app.post(prefix + "/tickets/{ticket_id}/analyze", response_model=schemas.AnalysisOut)
    def analyze(ticket_id: str, db: DB, current: Tenant):
        try:
            return analyze_ticket(
                db, settings, current["id"], ticket_id, client=app.state.openai_client
            )
        except ProviderFailure as exc:
            db.rollback()
            audit(
                db,
                current["id"],
                "analysis.failed",
                ticket_id,
                {"reason": "provider_validation_failure", "provider": settings.ai_provider},
            )
            db.commit()
            raise HTTPException(502, str(exc)) from exc

    @app.get(prefix + "/tickets/{ticket_id}/analysis", response_model=schemas.AnalysisOut | None)
    def latest_analysis(ticket_id: str, db: DB, current: Tenant):
        scoped_one(db, models.Ticket, current["id"], ticket_id)
        row = db.scalar(
            select(models.Analysis)
            .where(
                models.Analysis.tenant_id == current["id"], models.Analysis.ticket_id == ticket_id
            )
            .order_by(models.Analysis.created_at.desc(), models.Analysis.id.desc())
            .limit(1)
        )
        return row.data if row else None

    @app.get(prefix + "/actions", response_model=list[schemas.ActionOut])
    def actions(db: DB, current: Tenant):
        return db.scalars(
            select(models.Action)
            .where(models.Action.tenant_id == current["id"])
            .order_by(models.Action.created_at.desc())
        ).all()

    @app.post(prefix + "/actions/{action_id}/approve", response_model=schemas.ActionOut)
    def approve(action_id: str, body: schemas.DecisionInput, db: DB, current: Tenant):
        return decide_action(db, current["id"], action_id, body)

    @app.get(prefix + "/audit", response_model=list[schemas.AuditOut])
    def audit_events(db: DB, current: Tenant):
        return db.scalars(
            select(models.Audit)
            .where(models.Audit.tenant_id == current["id"])
            .order_by(models.Audit.created_at.desc())
            .limit(200)
        ).all()

    @app.get(prefix + "/documents", response_model=list[schemas.DocumentOut])
    def documents(db: DB, current: Tenant):
        return db.scalars(
            select(models.Document)
            .where(models.Document.tenant_id == current["id"])
            .order_by(models.Document.created_at)
        ).all()

    @app.post(prefix + "/documents", response_model=schemas.DocumentOut, status_code=201)
    def add_document(body: schemas.DocumentInput, db: DB, current: Tenant):
        document = models.Document(tenant_id=current["id"], **body.model_dump())
        db.add(document)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                409, "A document with this source already exists in this workspace"
            ) from exc
        audit(
            db,
            current["id"],
            "document.created",
            document.id,
            {"title": document.title, "source": document.source},
        )
        db.commit()
        return document

    @app.post(prefix + "/ingest")
    def ingest(body: schemas.IngestInput, db: DB, current: Tenant):
        return ingest_tickets(db, current["id"], body.tickets)

    @app.get(prefix + "/metrics")
    def metrics(db: DB, current: Tenant):
        tid = current["id"]

        def count(model, *conditions):
            return (
                db.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(model.tenant_id == tid, *conditions)
                )
                or 0
            )

        data = db.scalars(
            select(models.Analysis.data).where(models.Analysis.tenant_id == tid)
        ).all()
        return {
            "total_tickets": count(models.Ticket),
            "open_tickets": count(models.Ticket, models.Ticket.status == "open"),
            "analyzed_tickets": db.scalar(
                select(func.count(func.distinct(models.Analysis.ticket_id))).where(
                    models.Analysis.tenant_id == tid
                )
            )
            or 0,
            "pending_approvals": count(models.Action, models.Action.status == "pending"),
            "approved_actions": count(models.Action, models.Action.status == "approved"),
            "avg_latency_ms": round(sum(a["latency_ms"] for a in data) / len(data), 3)
            if data
            else 0,
            "grounded_rate": sum(bool(a["citations"]) for a in data) / len(data) if data else 0,
        }

    @app.post(prefix + "/evaluations/run", response_model=schemas.EvaluationOut)
    def evaluate(db: DB, current: Tenant):
        data = run_baseline()
        db.add(models.Evaluation(id=data["id"], tenant_id=current["id"], data=data))
        audit(
            db,
            current["id"],
            "evaluation.completed",
            data["id"],
            {"baseline": "offline-lexical-v1", "passed": data["passed"], "total": data["total"]},
        )
        db.commit()
        return data

    @app.get(prefix + "/evaluations/latest", response_model=schemas.EvaluationOut | None)
    def latest_evaluation(db: DB, current: Tenant):
        row = db.scalar(
            select(models.Evaluation)
            .where(models.Evaluation.tenant_id == current["id"])
            .order_by(models.Evaluation.created_at.desc())
            .limit(1)
        )
        return row.data if row else None

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    return app


app = create_app()
