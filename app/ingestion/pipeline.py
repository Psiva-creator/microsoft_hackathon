import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.core.embeddings import get_embedder
from app.core.fingerprint import fingerprints, parse_stack_trace
from app.core.normalize import normalize_text
from app.core.redact import redact
from app.ingestion.extract import extract_incident
from app.ingestion.loaders import RawDoc, load_folder
from app.logging import get_logger
from app.memory.store import (
    find_incident_by_doc_hash,
    find_near_duplicate_incident,
    get_next_incident_id,
    insert_incident,
    insert_incident_file,
    upsert_runbook,
    upsert_service,
)

logger = get_logger(__name__)


def ingest_runbooks(runbooks_dir: str | Path = "data/runbooks") -> int:
    """Loads and embeds markdown runbooks with YAML frontmatter."""
    p = Path(runbooks_dir)
    if not p.exists():
        return 0

    embedder = get_embedder()
    count = 0

    for file_path in p.glob("*.md"):
        content = file_path.read_text(encoding="utf-8")
        # Extract YAML frontmatter
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not m:
            continue

        frontmatter_raw, body_md = m.groups()
        meta: dict[str, Any] = {}
        for line in frontmatter_raw.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()
                if v.startswith("[") and v.endswith("]"):
                    # list of items
                    items = [x.strip() for x in v[1:-1].split(",") if x.strip()]
                    meta[k] = items
                else:
                    meta[k] = v

        rb_id = meta.get("id", file_path.stem)
        title = meta.get("title", rb_id)
        services = meta.get("services", [])

        # Embed title + body
        emb = embedder.embed_documents([f"{title}\n\n{body_md}"])[0]

        upsert_runbook(
            id=rb_id,
            title=title,
            body_md=body_md,
            services=services,
            emb=emb,
        )
        count += 1
        logger.info("runbook_ingested", id=rb_id, services=services)

    return count


def process_raw_doc(doc: RawDoc, accept_low: bool = False) -> str | None:
    """Ingests a single raw document into the episodic memory store."""
    raw_text = doc.text.strip()
    if not raw_text:
        return None

    # 1. Idempotency check via SHA256
    text_sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    existing_id = find_incident_by_doc_hash(text_sha)
    if existing_id:
        logger.debug("doc_already_ingested", source_id=doc.source_id, existing_id=existing_id)
        return existing_id

    # 2. Redact then extract
    sanitized_text = redact(raw_text)
    extracted = extract_incident(sanitized_text, source_id=doc.source_id)

    # 3. Handle low confidence
    if extracted.extraction_confidence == "low" and not accept_low:
        review_path = Path("data/review_queue") / f"{doc.source_id}.json"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(extracted.model_dump_json(indent=2))
        logger.info("low_confidence_queued", source_id=doc.source_id, path=str(review_path))
        return None

    # 4. Normalize errors and compute fingerprints
    norm_errors = [normalize_text(e) for e in extracted.error_messages]
    all_trace_text = "\n".join(extracted.stack_traces) + "\n" + "\n".join(extracted.error_messages)
    fps = fingerprints(all_trace_text)

    # 5. Build symptom_text and full_text
    symptoms_str = " ".join(extracted.symptoms)
    errors_str = " ".join(norm_errors)
    services_str = " ".join(extracted.services)
    trigger_str = extracted.trigger_type or "unknown"

    symptom_text = f"{extracted.title}. Symptoms: {symptoms_str}. Errors: {errors_str}. Services: {services_str}. Trigger: {trigger_str}"
    full_text = f"{symptom_text}. Root Cause: {extracted.root_cause}. Resolution: {' '.join(extracted.resolution_steps)}. Lessons: {extracted.lessons or ''}"

    # 6. Embed both texts
    embedder = get_embedder()
    embeddings = embedder.embed_documents([symptom_text, full_text])
    emb_symptom = embeddings[0]
    emb_full = embeddings[1]

    # 7. Dedupe: near-duplicate check (similarity >= 0.97 on same services)
    if extracted.services:
        dupe = find_near_duplicate_incident(emb_full, extracted.services)
        if dupe:
            logger.info(
                "near_duplicate_merged",
                incoming=doc.source_id,
                merged_into=dupe["id"],
                similarity=dupe["sim"],
            )
            return dupe["id"]

    # 8. Generate next ID and insert incident
    new_id = get_next_incident_id()

    # Link runbooks mentioned or by similarity
    runbook_ids = list(set(extracted.runbooks_mentioned))

    source_doc_meta = [
        {
            "type": doc.source_type,
            "id": doc.source_id,
            "sha256": text_sha,
        }
    ]

    record = {
        "id": new_id,
        "title": extracted.title,
        "status": "confirmed",
        "severity": extracted.severity,
        "started_at": extracted.started_at,
        "resolved_at": extracted.resolved_at,
        "time_to_resolve_min": None,
        "symptoms": extracted.symptoms,
        "error_messages": norm_errors,
        "error_fingerprints": fps,
        "services": extracted.services,
        "trigger_type": extracted.trigger_type,
        "trigger_ref": extracted.trigger_ref,
        "root_cause": extracted.root_cause,
        "root_cause_category": extracted.root_cause_category,
        "resolution_steps": extracted.resolution_steps,
        "runbook_ids": runbook_ids,
        "fix_worked": extracted.fix_worked,
        "lessons": extracted.lessons,
        "source_docs": json.dumps(source_doc_meta),
        "symptom_text": symptom_text,
        "full_text": full_text,
        "emb_symptom": emb_symptom,
        "emb_full": emb_full,
        "weight": 1.0,
        "architecture_epoch": 1,
    }

    inserted_id = insert_incident(record)

    # 9. Insert incident_files
    for fm in extracted.files_mentioned:
        insert_incident_file(inserted_id, fm.path, fm.function, role="root_cause")

    frames = parse_stack_trace(all_trace_text)
    for frame in frames:
        if frame.is_app:
            insert_incident_file(inserted_id, frame.file, frame.function, role="involved")

    # 10. Upsert services
    for svc in extracted.services:
        upsert_service(svc)

    logger.info("incident_ingested", id=inserted_id, title=extracted.title)
    return inserted_id


def ingest_folder(folder_path: str | Path, accept_low: bool = False) -> int:
    """Ingests all documents in a folder."""
    count = 0
    for doc in load_folder(folder_path):
        res = process_raw_doc(doc, accept_low=accept_low)
        if res:
            count += 1
    return count
