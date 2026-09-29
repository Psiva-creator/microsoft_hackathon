from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.agent.investigate import investigate
from app.agent.postmortem import confirm_and_save_to_memory, resolve_incident
from app.config import get_settings
from app.db import check_db, check_redis, close_db_pool, get_db_pool
from app.logging import get_logger, setup_logging
from app.memory.retrieval import recall
from app.memory.stats import record_feedback
from app.memory.working import (
    append_event,
    get_context,
    get_events,
    get_hypotheses,
    list_active_incidents,
    set_hypotheses,
)
from app.memory.working import create as create_working_memory
from app.models import Cue, Hypothesis, LiveEvent

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info("application_starting")
    try:
        get_db_pool()
    except Exception as e:
        logger.warning("db_pool_init_deferred", error=str(e))
    yield
    logger.info("application_stopping")
    close_db_pool()


app = FastAPI(
    title="Incident Response Agent",
    description="Brain-Inspired Memory Incident Response Assistant",
    version="0.1.0",
    lifespan=lifespan,
)


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    settings = get_settings()
    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
    return x_api_key


# Request / Response Schemas
class CreateIncidentRequest(BaseModel):
    title: str
    description: str = ""
    services: list[str] = Field(default_factory=list)
    error_text: str | None = None


class AppendEventRequest(BaseModel):
    kind: str = "message"
    source: str = "api"
    text: str
    data: dict[str, Any] | None = None


class ResolveRequest(BaseModel):
    root_cause: str
    steps: list[str] = Field(default_factory=list)
    runbook_ids: list[str] = Field(default_factory=list)
    worked: bool = True


class ConfirmPostMortemRequest(BaseModel):
    approved_markdown: str


class FeedbackRequest(BaseModel):
    suggestion_id: int | None = None
    runbook_id: str | None = None
    helpful: bool
    comment: str | None = None


class PRCheckRequest(BaseModel):
    repo: str | None = None
    files: list[str] = Field(default_factory=list)
    diff: str | None = None


@app.get("/")
def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url="/docs")
    return {
        "status": "healthy",
        "service": "Incident Response Agent",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/healthz",
    }


@app.get("/healthz")
def healthz() -> JSONResponse:
    postgres_healthy = check_db()
    redis_healthy = check_redis()
    is_healthy = postgres_healthy and redis_healthy
    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if is_healthy else "unhealthy",
            "postgres": "healthy" if postgres_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
        },
    )


@app.post("/webhooks/alertmanager", status_code=status.HTTP_202_ACCEPTED)
def alertmanager_webhook(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
):
    group_key = payload.get("groupKey", "alert")
    now_dt = datetime.now(timezone.utc)
    live_id = f"LIVE-{now_dt.strftime('%Y%m%d')}-{abs(hash(group_key)) % 1000:03d}"

    alerts = payload.get("alerts", [])
    first_alert = alerts[0] if alerts else {}
    annotations = first_alert.get("annotations", {})
    labels = first_alert.get("labels", {})

    service = labels.get("service") or labels.get("app") or "unknown"
    title = annotations.get("summary") or labels.get("alertname") or f"Alert on {service}"
    description = annotations.get("description", "")

    create_working_memory(live_id, {"title": title, "services": [service]})
    append_event(
        live_id,
        LiveEvent(
            ts=now_dt.isoformat().replace("+00:00", "Z"),
            kind="alert",
            source="alertmanager",
            text=f"{title}: {description}",
            data=first_alert,
        ),
    )

    def run_bg(lid: str, s: str, desc: str):
        cue = Cue(text=desc, services=[s], error_messages=[desc])
        investigate(live_id=lid, cue=cue)

    background_tasks.add_task(run_bg, live_id, service, description)
    return {"status": "accepted", "live_incident_id": live_id}


@app.post("/webhooks/pagerduty", status_code=status.HTTP_202_ACCEPTED)
def pagerduty_webhook(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
):
    event = payload.get("event", {})
    incident_data = event.get("data", {})
    p_id = incident_data.get("id", "pd")
    live_id = f"LIVE-{datetime.utcnow().strftime('%Y%m%d')}-{abs(hash(p_id)) % 1000:03d}"
    title = incident_data.get("title", "PagerDuty Incident")

    create_working_memory(live_id, {"title": title})
    return {"status": "accepted", "live_incident_id": live_id}


@app.post("/incidents", status_code=status.HTTP_201_CREATED)
def create_incident(
    req: CreateIncidentRequest,
    api_key: str = Depends(verify_api_key),
):
    now_dt = datetime.now(timezone.utc)
    now_str = now_dt.strftime("%Y%m%d")
    live_id = f"LIVE-{now_str}-{int(now_dt.timestamp()) % 1000:03d}"

    create_working_memory(
        live_id,
        {
            "title": req.title,
            "services": req.services,
            "status": "open",
        },
    )

    if req.description or req.error_text:
        append_event(
            live_id,
            LiveEvent(
                ts=now_dt.isoformat().replace("+00:00", "Z"),
                kind="alert",
                source="user",
                text=f"{req.description}\n{req.error_text or ''}".strip(),
            ),
        )

    return {"live_incident_id": live_id, "title": req.title, "services": req.services}


@app.get("/incidents")
def list_active_incidents_view(
    api_key: str = Depends(verify_api_key),
):
    """Lists all active incidents currently held in Prefrontal Cortex working memory."""
    return list_active_incidents()


@app.get("/incidents/{id}")
def get_live_incident_view(
    id: str,
    api_key: str = Depends(verify_api_key),
):
    ctx = get_context(id)
    return ctx.model_dump()


@app.post("/incidents/{id}/events")
def append_incident_event(
    id: str,
    req: AppendEventRequest,
    api_key: str = Depends(verify_api_key),
):
    event = LiveEvent(
        ts=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        kind=req.kind,  # type: ignore
        source=req.source,
        text=req.text,
        data=req.data,
    )
    append_event(id, event)
    return {"status": "appended", "event": event.model_dump()}


@app.get("/incidents/{id}/events")
def get_incident_events_view(
    id: str,
    limit: int = Query(30, ge=1, le=200),
    kind: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key),
):
    """Retrieves chronological timeline events for an active incident."""
    events = get_events(id, limit=limit)
    if kind:
        events = [e for e in events if e.kind == kind]
    return [e.model_dump() for e in events]


@app.get("/incidents/{id}/hypotheses")
def get_incident_hypotheses_view(
    id: str,
    api_key: str = Depends(verify_api_key),
):
    """Retrieves active hypotheses held in Prefrontal Cortex working memory during triage."""
    hypotheses = get_hypotheses(id)
    return [h.model_dump() for h in (hypotheses or [])]


@app.put("/incidents/{id}/hypotheses")
def update_incident_hypotheses_view(
    id: str,
    hypotheses: list[Hypothesis],
    api_key: str = Depends(verify_api_key),
):
    """Updates active hypotheses during triage and appends a triage note to the timeline."""
    set_hypotheses(id, hypotheses)
    append_event(
        id,
        LiveEvent(
            ts=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            kind="note",
            source="human_triage",
            text=f"Updated triage hypotheses ({len(hypotheses)} active)",
            data={"hypotheses": [h.model_dump() for h in hypotheses]},
        ),
    )
    return {"status": "updated", "hypotheses": [h.model_dump() for h in hypotheses]}


@app.post("/incidents/{id}/investigate")
def investigate_live_incident(
    id: str,
    note: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key),
):
    ctx = get_context(id)
    combined_texts = [e.text for e in ctx.events]
    cue = Cue(
        text=f"{ctx.title} {' '.join(combined_texts)}",
        services=ctx.services,
        error_messages=[e.text for e in ctx.events if e.kind in ("alert", "log")],
    )

    analysis = investigate(live_id=id, cue=cue, note=note)
    return analysis.model_dump()


@app.post("/incidents/{id}/resolve")
def resolve_live_incident(
    id: str,
    req: ResolveRequest,
    api_key: str = Depends(verify_api_key),
):
    draft = resolve_incident(
        live_id=id,
        root_cause=req.root_cause,
        steps=req.steps,
        runbook_ids=req.runbook_ids,
        worked=req.worked,
    )
    return draft.model_dump()


@app.post("/incidents/{id}/postmortem/confirm")
def confirm_postmortem(
    id: str,
    req: ConfirmPostMortemRequest,
    api_key: str = Depends(verify_api_key),
):
    inc_id = confirm_and_save_to_memory(live_id=id, approved_markdown=req.approved_markdown)
    return {"status": "saved_to_memory", "incident_id": inc_id}


@app.post("/feedback")
def submit_feedback(
    req: FeedbackRequest,
    api_key: str = Depends(verify_api_key),
):
    record_feedback(
        suggestion_id=req.suggestion_id,
        runbook_id=req.runbook_id,
        helpful=req.helpful,
        comment=req.comment,
    )
    return {"status": "feedback_recorded"}


@app.get("/memory/incidents")
def search_memory(
    q: str = Query(...),
    service: Optional[List[str]] = Query(None),
    limit: int = Query(5),
    api_key: str = Depends(verify_api_key),
):
    cue = Cue(text=q, services=service or [])
    result = recall(cue, top_k=limit)
    return result.model_dump()


@app.post("/pr-check")
def pr_check(
    req: PRCheckRequest,
    api_key: str = Depends(verify_api_key),
):
    from app.code_memory.pr_check import check_pr
    result = check_pr(files=req.files, diff=req.diff)
    return result
