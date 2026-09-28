import json
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.redact import redact
from app.db import get_db
from app.ingestion.loaders import RawDoc
from app.ingestion.pipeline import process_raw_doc
from app.logging import get_logger
from app.memory.stats import update_runbook_resolution_outcome
from app.memory.working import close as close_working_memory
from app.memory.working import get_context

logger = get_logger(__name__)


class TimelineEntry(BaseModel):
    timestamp: str
    description: str


class PostMortemDraft(BaseModel):
    summary: str
    impact: str
    timeline: list[TimelineEntry] = Field(default_factory=list)
    root_cause: str
    contributing_factors: list[str] = Field(default_factory=list)
    what_worked: list[str] = Field(default_factory=list)
    what_did_not_work: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    markdown: str


def draft_postmortem(
    live_id: str,
    root_cause: str,
    steps: list[str],
    runbook_ids: list[str],
    worked: bool,
) -> PostMortemDraft:
    """Generates a blameless post-mortem draft where human-provided fields are strictly authoritative."""
    context = get_context(live_id)

    timeline_entries: list[TimelineEntry] = []
    for ev in context.events:
        timeline_entries.append(TimelineEntry(timestamp=ev.ts, description=redact(ev.text[:200])))

    # Fallback or synthetic draft
    summary_text = f"Incident {live_id} affecting {', '.join(context.services)} resolved."
    impact_text = f"Degradation across services: {', '.join(context.services)}."

    md_lines = [
        f"# Post-Mortem: Incident {live_id}",
        "",
        "## Summary",
        summary_text,
        "",
        "## Root Cause",
        root_cause,
        "",
        "## Resolution Steps",
    ]
    for idx, s in enumerate(steps, 1):
        md_lines.append(f"{idx}. {s}")

    md_lines.extend([
        "",
        "## Runbooks Used",
        ", ".join(runbook_ids) or "None",
        "",
        "## Outcome",
        f"Resolution worked: {'Yes' if worked else 'No'}",
        "",
        "## Timeline",
    ])
    for t in timeline_entries:
        md_lines.append(f"- **{t.timestamp}**: {t.description}")

    md_rendering = "\n".join(md_lines)

    return PostMortemDraft(
        summary=summary_text,
        impact=impact_text,
        timeline=timeline_entries,
        root_cause=root_cause,
        contributing_factors=["Service dependency pressure"],
        what_worked=steps,
        what_did_not_work=[],
        follow_ups=["Add alerts for early symptom detection"],
        markdown=md_rendering,
    )


def resolve_incident(
    live_id: str,
    root_cause: str,
    steps: list[str],
    runbook_ids: list[str],
    worked: bool,
) -> PostMortemDraft:
    """Marks live incident resolved, drafts post-mortem, and sets Redis 72h TTL."""
    now_iso = datetime.utcnow().isoformat() + "Z"
    resolution_data = {
        "root_cause": root_cause,
        "steps": steps,
        "runbook_ids": runbook_ids,
        "worked": worked,
        "resolved_at": now_iso,
    }

    draft = draft_postmortem(live_id, root_cause, steps, runbook_ids, worked)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO live_incidents (id, title, status, resolved_at, resolution, postmortem_draft)
                    VALUES (%s, %s, 'postmortem_draft', %s, %s::jsonb, %s::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                        status = 'postmortem_draft',
                        resolved_at = EXCLUDED.resolved_at,
                        resolution = EXCLUDED.resolution,
                        postmortem_draft = EXCLUDED.postmortem_draft;
                    """,
                    (
                        live_id,
                        f"Live Incident {live_id}",
                        now_iso,
                        json.dumps(resolution_data),
                        draft.model_dump_json(),
                    ),
                )
                conn.commit()
    except Exception as e:
        logger.warning("live_incident_db_write_failed", error=str(e))

    close_working_memory(live_id)
    return draft


def confirm_and_save_to_memory(live_id: str, approved_markdown: str) -> str:
    """Takes approved post-mortem, ingests into long-term Postgres memory, updates stats, sets confirmed."""
    raw_doc = RawDoc(
        source_type="postmortem",
        source_id=f"postmortem_{live_id}",
        text=approved_markdown,
        metadata={"live_id": live_id},
    )

    incident_id = process_raw_doc(raw_doc) or live_id

    # Retrieve resolution data to update runbook success stats
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT resolution FROM live_incidents WHERE id = %s", (live_id,))
                row = cur.fetchone()
                if row and row["resolution"]:
                    res = row["resolution"]
                    runbook_ids = res.get("runbook_ids", [])
                    worked = res.get("worked", True)
                    update_runbook_resolution_outcome(runbook_ids, worked)

                cur.execute("UPDATE live_incidents SET status = 'confirmed' WHERE id = %s", (live_id,))
                conn.commit()
    except Exception as e:
        logger.warning("confirm_memory_stats_failed", error=str(e))

    logger.info("incident_confirmed_into_memory", live_id=live_id, incident_id=incident_id)
    return incident_id
