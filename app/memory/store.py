import json
import re
from pathlib import Path
from typing import Any

import numpy as np

from app.db import get_db
from app.logging import get_logger
from app.models import Runbook

logger = get_logger(__name__)

# In-memory storage for offline / disconnected environments and unit testing
_IN_MEMORY_INCIDENTS: dict[str, dict[str, Any]] = {}
_IN_MEMORY_DOC_HASHES: dict[str, str] = {}  # sha256 -> incident_id
_IN_MEMORY_SERVICES: dict[str, dict[str, Any]] = {}
_IN_MEMORY_DEPENDENCIES: dict[str, set[str]] = {}  # service -> set of dependency names
_IN_MEMORY_RUNBOOKS: dict[str, dict[str, Any]] = {}
_IN_MEMORY_INCIDENT_FILES: list[dict[str, Any]] = []


def clear_in_memory_store() -> None:
    """Clears in-memory incident and document hash stores (useful for test fixtures)."""
    _IN_MEMORY_INCIDENTS.clear()
    _IN_MEMORY_DOC_HASHES.clear()
    _IN_MEMORY_INCIDENT_FILES.clear()


def upsert_service(
    name: str,
    owner_team: str | None = None,
    description: str | None = None,
    epoch: int = 1,
) -> int:
    try:
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
    except Exception:
        pass

    _IN_MEMORY_SERVICES[name] = {
        "id": len(_IN_MEMORY_SERVICES) + 1,
        "name": name,
        "owner_team": owner_team or "unknown",
        "description": description or "",
        "epoch": epoch,
    }
    return _IN_MEMORY_SERVICES[name]["id"]


def add_service_dependency(service_name: str, depends_on_name: str) -> None:
    svc_id = upsert_service(service_name)
    dep_id = upsert_service(depends_on_name)
    try:
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
                return
    except Exception:
        pass

    if service_name not in _IN_MEMORY_DEPENDENCIES:
        _IN_MEMORY_DEPENDENCIES[service_name] = set()
    _IN_MEMORY_DEPENDENCIES[service_name].add(depends_on_name)


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
        logger.debug("get_service_dependencies_db_unavailable", error=str(e))

    # In-memory dependency lookup
    downstream = list(_IN_MEMORY_DEPENDENCIES.get(service_name, []))
    upstream = [svc for svc, deps in _IN_MEMORY_DEPENDENCIES.items() if service_name in deps]
    return {"upstream": upstream, "downstream": downstream}


def upsert_runbook(
    id: str,
    title: str,
    body_md: str,
    services: list[str],
    emb: list[float] | None = None,
) -> None:
    try:
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
                return
    except Exception:
        pass

    _IN_MEMORY_RUNBOOKS[id] = {
        "id": id,
        "title": title,
        "body_md": body_md,
        "services": services,
        "emb": emb,
        "success_count": 0,
        "failure_count": 0,
    }


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

    if id in _IN_MEMORY_RUNBOOKS:
        data = _IN_MEMORY_RUNBOOKS[id]
        return Runbook(
            id=data["id"],
            title=data["title"],
            body_md=data["body_md"],
            services=data.get("services", []),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
        )

    # Offline file fallback
    rb_file = Path("data/runbooks") / f"{id}.md"
    if rb_file.exists():
        content = rb_file.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        body = m.group(2).strip() if m else content
        from app.memory.stats import get_offline_runbook_counts

        counts = get_offline_runbook_counts(id)
        return Runbook(
            id=id,
            title=id.replace("RB-", "").replace("-", " ").title(),
            body_md=body,
            services=[],
            success_count=counts.get("success", 0),
            failure_count=counts.get("failure", 0),
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
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM incidents ORDER BY id DESC LIMIT 1;")
                row = cur.fetchone()
                if row:
                    last_id = row["id"]
                    num = int(last_id.replace("INC-", ""))
                    return f"INC-{num + 1:04d}"
                return "INC-0001"
    except Exception:
        pass

    # In-memory fallback
    if _IN_MEMORY_INCIDENTS:
        nums = [
            int(k.replace("INC-", ""))
            for k in _IN_MEMORY_INCIDENTS.keys()
            if k.startswith("INC-") and k.replace("INC-", "").isdigit()
        ]
        if nums:
            return f"INC-{max(nums) + 1:04d}"
    return "INC-0001"


def find_incident_by_doc_hash(sha256_hash: str) -> str | None:
    """Finds an existing incident that already contains a document with the given SHA-256 hash."""
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
                if row:
                    return row["id"]
    except Exception:
        pass

    # Check in-memory hash registry
    if sha256_hash in _IN_MEMORY_DOC_HASHES:
        return _IN_MEMORY_DOC_HASHES[sha256_hash]

    # Check all in-memory incident records
    for inc_id, inc in _IN_MEMORY_INCIDENTS.items():
        docs = inc.get("source_docs")
        if isinstance(docs, str):
            try:
                docs = json.loads(docs)
            except Exception:
                docs = []
        if isinstance(docs, list):
            for d in docs:
                if isinstance(d, dict) and d.get("sha256") == sha256_hash:
                    _IN_MEMORY_DOC_HASHES[sha256_hash] = inc_id
                    return inc_id

    return None


def find_near_duplicate_incident(
    emb_full: list[float],
    services: list[str],
) -> dict[str, Any] | None:
    """Identifies near-duplicate incidents using cosine similarity (>= 0.97) across matching services."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, root_cause, 1 - (emb_full <=> %s::vector) AS sim,
                           services, started_at
                    FROM incidents
                    WHERE services && %s
                    ORDER BY emb_full <=> %s::vector
                    LIMIT 1;
                    """,
                    (emb_full, services, emb_full),
                )
                row = cur.fetchone()
                if row and float(row["sim"]) >= 0.97:
                    return dict(row)
                return None
    except Exception:
        pass

    # In-memory fallback: compute cosine similarity in Python
    svc_set = set(services)
    best_inc = None
    best_sim = -1.0

    a = np.array(emb_full, dtype=float)
    norm_a = np.linalg.norm(a)
    if norm_a == 0:
        return None

    for inc_id, inc in _IN_MEMORY_INCIDENTS.items():
        inc_svcs = set(inc.get("services", []))
        if not (svc_set & inc_svcs):
            continue
        inc_emb = inc.get("emb_full")
        if not inc_emb:
            continue

        b = np.array(inc_emb, dtype=float)
        norm_b = np.linalg.norm(b)
        if norm_b > 0:
            sim = float(np.dot(a, b) / (norm_a * norm_b))
            if sim > best_sim:
                best_sim = sim
                best_inc = inc

    if best_inc and best_sim >= 0.97:
        res = dict(best_inc)
        res["sim"] = best_sim
        return res

    return None


def merge_incident(
    existing_id: str,
    incoming: dict[str, Any],
    source_doc: dict[str, Any] | None = None,
) -> str:
    """Merges an incoming near-duplicate incident into an existing incident record."""
    existing = get_incident(existing_id)
    if not existing:
        return existing_id

    # 1. Union array fields
    def _union_lists(l1: Any, l2: Any) -> list[Any]:
        items1 = l1 if isinstance(l1, list) else []
        items2 = l2 if isinstance(l2, list) else []
        combined: list[Any] = []
        for x in items1 + items2:
            if x not in combined:
                combined.append(x)
        return combined

    services = _union_lists(existing.get("services"), incoming.get("services"))
    symptoms = _union_lists(existing.get("symptoms"), incoming.get("symptoms"))
    error_messages = _union_lists(existing.get("error_messages"), incoming.get("error_messages"))
    error_fingerprints = _union_lists(
        existing.get("error_fingerprints"), incoming.get("error_fingerprints")
    )
    runbook_ids = _union_lists(existing.get("runbook_ids"), incoming.get("runbook_ids"))
    resolution_steps = _union_lists(
        existing.get("resolution_steps"), incoming.get("resolution_steps")
    )

    # 2. Retain the longer root-cause text
    existing_cause = existing.get("root_cause") or ""
    incoming_cause = incoming.get("root_cause") or ""
    root_cause = incoming_cause if len(incoming_cause) > len(existing_cause) else existing_cause

    # 3. Append source doc metadata
    docs = existing.get("source_docs")
    if isinstance(docs, str):
        try:
            docs = json.loads(docs)
        except Exception:
            docs = []
    elif not isinstance(docs, list):
        docs = []

    if source_doc and source_doc not in docs:
        docs.append(source_doc)
        if source_doc.get("sha256"):
            _IN_MEMORY_DOC_HASHES[source_doc["sha256"]] = existing_id

    source_docs_json = json.dumps(docs)

    # 4. Update database if available
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE incidents SET
                        services = %s,
                        symptoms = %s,
                        error_messages = %s,
                        error_fingerprints = %s,
                        runbook_ids = %s,
                        resolution_steps = %s,
                        root_cause = %s,
                        source_docs = %s::jsonb
                    WHERE id = %s;
                    """,
                    (
                        services,
                        symptoms,
                        error_messages,
                        error_fingerprints,
                        runbook_ids,
                        resolution_steps,
                        root_cause,
                        source_docs_json,
                        existing_id,
                    ),
                )
                conn.commit()
    except Exception as e:
        logger.debug("merge_incident_db_failed_using_memory", id=existing_id, error=str(e))

    # 5. Always update in-memory record
    if existing_id in _IN_MEMORY_INCIDENTS:
        rec = _IN_MEMORY_INCIDENTS[existing_id]
        rec["services"] = services
        rec["symptoms"] = symptoms
        rec["error_messages"] = error_messages
        rec["error_fingerprints"] = error_fingerprints
        rec["runbook_ids"] = runbook_ids
        rec["resolution_steps"] = resolution_steps
        rec["root_cause"] = root_cause
        rec["source_docs"] = source_docs_json

    logger.info("incident_near_duplicate_merged", id=existing_id)
    return existing_id


def insert_incident(data: dict[str, Any]) -> str:
    inc_id = data["id"]
    try:
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
                inc_id = new_id
    except Exception as e:
        logger.debug("insert_incident_db_failed_using_memory", id=inc_id, error=str(e))

    # Always index in-memory
    _IN_MEMORY_INCIDENTS[inc_id] = dict(data)
    docs = data.get("source_docs")
    if isinstance(docs, str):
        try:
            docs = json.loads(docs)
        except Exception:
            docs = []
    if isinstance(docs, list):
        for d in docs:
            if isinstance(d, dict) and d.get("sha256"):
                _IN_MEMORY_DOC_HASHES[d["sha256"]] = inc_id

    return inc_id


def get_incident(id: str) -> dict[str, Any] | None:
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM incidents WHERE id = %s;", (id,))
                row = cur.fetchone()
                if row:
                    return dict(row)
    except Exception as e:
        logger.debug("get_incident_db_unavailable", id=id, error=str(e))

    return _IN_MEMORY_INCIDENTS.get(id)


def insert_incident_file(
    incident_id: str,
    file_path: str,
    function_name: str = "",
    role: str = "involved",
) -> None:
    try:
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
    except Exception:
        pass

    _IN_MEMORY_INCIDENT_FILES.append(
        {
            "incident_id": incident_id,
            "file_path": file_path,
            "function_name": function_name,
            "role": role,
        }
    )


def get_incident_count() -> int:
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) AS total FROM incidents;")
    except Exception:
        pass
    if _IN_MEMORY_INCIDENTS:
        return len(_IN_MEMORY_INCIDENTS)
    try:
        from app.memory.retrieval import _get_offline_incidents

        return len(_get_offline_incidents())
    except Exception:
        return 0
