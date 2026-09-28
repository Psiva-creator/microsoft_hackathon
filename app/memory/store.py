import json
import re
from pathlib import Path
from typing import Any

from app.db import get_db
from app.logging import get_logger
from app.models import Runbook

logger = get_logger(__name__)


def upsert_service(
    name: str,
    owner_team: str | None = None,
    description: str | None = None,
    epoch: int = 1,
) -> int:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO services (name, owner_team, description, architecture_epoch)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    owner_team = COALESCE(EXCLUDED.owner_team, services.owner_team),
                    description = COALESCE(EXCLUDED.description, services.description),
                    architecture_epoch = EXCLUDED.architecture_epoch
                RETURNING id;
                """,
                (name, owner_team, description, epoch),
            )
            res = cur.fetchone()
            conn.commit()
            return res["id"]


def add_service_dependency(service_name: str, depends_on_name: str) -> None:
    svc_id = upsert_service(service_name)
    dep_id = upsert_service(depends_on_name)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO service_dependencies (service_id, depends_on_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (svc_id, dep_id),
            )
            conn.commit()


def get_service_dependencies(service_name: str) -> dict[str, list[str]]:
    """Returns upstream and downstream dependencies for a service."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM services WHERE name = %s", (service_name,))
                row = cur.fetchone()
                if not row:
                    return {"upstream": [], "downstream": []}
                svc_id = row["id"]

                cur.execute(
                    """
                    SELECT s.name FROM services s
                    JOIN service_dependencies sd ON s.id = sd.depends_on_id
                    WHERE sd.service_id = %s;
                    """,
                    (svc_id,),
                )
                downstream = [r["name"] for r in cur.fetchall()]

                cur.execute(
                    """
                    SELECT s.name FROM services s
                    JOIN service_dependencies sd ON s.id = sd.service_id
                    WHERE sd.depends_on_id = %s;
                    """,
                    (svc_id,),
                )
                upstream = [r["name"] for r in cur.fetchall()]

                return {"upstream": upstream, "downstream": downstream}
    except Exception as e:
        logger.warning("get_service_dependencies_db_unavailable", error=str(e))
        return {"upstream": [], "downstream": []}


def upsert_runbook(
    id: str,
    title: str,
    body_md: str,
    services: list[str],
    emb: list[float] | None = None,
) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runbooks (id, title, body_md, services, emb, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    body_md = EXCLUDED.body_md,
                    services = EXCLUDED.services,
                    emb = COALESCE(EXCLUDED.emb, runbooks.emb),
                    updated_at = now();
                """,
                (id, title, body_md, services, emb),
            )
            conn.commit()


def get_runbook(id: str) -> Runbook | None:
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, body_md, services, success_count, failure_count, updated_at
                    FROM runbooks WHERE id = %s;
                    """,
                    (id,),
                )
                row = cur.fetchone()
                if row:
                    return Runbook(**row)
    except Exception as e:
        logger.debug("get_runbook_db_unavailable", id=id, error=str(e))

    # Offline file fallback
    rb_file = Path("data/runbooks") / f"{id}.md"
    if rb_file.exists():
        content = rb_file.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        body = m.group(2).strip() if m else content
        return Runbook(
            id=id,
            title=id.replace("RB-", "").replace("-", " ").title(),
            body_md=body,
            services=[],
        )
    return None


def get_all_runbooks() -> list[Runbook]:
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, body_md, services, success_count, failure_count, updated_at
                    FROM runbooks ORDER BY id;
                    """
                )
                return [Runbook(**r) for r in cur.fetchall()]
    except Exception:
        pass

    # Offline file fallback
    runbooks_dir = Path("data/runbooks")
    results = []
    if runbooks_dir.exists():
        for f in sorted(runbooks_dir.glob("*.md")):
            rb = get_runbook(f.stem)
            if rb:
                results.append(rb)
    return results


def get_next_incident_id() -> str:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM incidents ORDER BY id DESC LIMIT 1;")
            row = cur.fetchone()
            if not row:
                return "INC-0001"
            last_id = row["id"]
            num = int(last_id.replace("INC-", ""))
            return f"INC-{num + 1:04d}"


def find_incident_by_doc_hash(sha256_hash: str) -> str | None:
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id FROM incidents
                    WHERE source_docs @> %s::jsonb
                    LIMIT 1;
                    """,
                    (json.dumps([{"sha256": sha256_hash}]),),
                )
                row = cur.fetchone()
                return row["id"] if row else None
    except Exception:
        return None


def find_near_duplicate_incident(
    emb_full: list[float],
    services: list[str],
) -> dict[str, Any] | None:
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, root_cause, 1 - (emb_full <=> %s::vector) AS sim
                    FROM incidents
                    WHERE services && %s
                    ORDER BY emb_full <=> %s::vector
                    LIMIT 1;
                    """,
                    (emb_full, services, emb_full),
                )
                row = cur.fetchone()
                if row and row["sim"] >= 0.97:
                    return row
                return None
    except Exception:
        return None


def insert_incident(data: dict[str, Any]) -> str:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO incidents (
                    id, title, status, severity, started_at, resolved_at,
                    time_to_resolve_min, symptoms, error_messages, error_fingerprints,
                    services, trigger_type, trigger_ref, root_cause, root_cause_category,
                    resolution_steps, runbook_ids, fix_worked, lessons, source_docs,
                    symptom_text, full_text, emb_symptom, emb_full, weight, architecture_epoch
                ) VALUES (
                    %(id)s, %(title)s, %(status)s, %(severity)s, %(started_at)s, %(resolved_at)s,
                    %(time_to_resolve_min)s, %(symptoms)s, %(error_messages)s, %(error_fingerprints)s,
                    %(services)s, %(trigger_type)s, %(trigger_ref)s, %(root_cause)s, %(root_cause_category)s,
                    %(resolution_steps)s, %(runbook_ids)s, %(fix_worked)s, %(lessons)s, %(source_docs)s::jsonb,
                    %(symptom_text)s, %(full_text)s, %(emb_symptom)s, %(emb_full)s, %(weight)s, %(architecture_epoch)s
                ) RETURNING id;
                """,
                data,
            )
            new_id = cur.fetchone()["id"]
            conn.commit()
            return new_id


def get_incident(id: str) -> dict[str, Any] | None:
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM incidents WHERE id = %s;", (id,))
                return cur.fetchone()
    except Exception as e:
        logger.debug("get_incident_db_unavailable", id=id, error=str(e))
        return None


def insert_incident_file(
    incident_id: str,
    file_path: str,
    function_name: str = "",
    role: str = "involved",
) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO incident_files (incident_id, file_path, function_name, role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (incident_id, file_path, function_name, role),
            )
            conn.commit()


def get_incident_count() -> int:
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) AS total FROM incidents;")
                return cur.fetchone()["total"]
    except Exception:
        return 0
