import json
import re
from pathlib import Path
from typing import Any

import numpy as np

from app.config import get_settings
from app.core.embeddings import get_embedder
from app.core.fingerprint import fingerprints
from app.core.normalize import normalize_text
from app.db import get_db
from app.logging import get_logger
from app.memory.stats import get_runbook_success_probability
from app.memory.store import get_runbook, get_service_dependencies
from app.models import Cue, Pattern, RetrievalResult, Runbook, ScoredIncident

logger = get_logger(__name__)

STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "up",
    "about",
    "into",
    "over",
    "after",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
}


def _extract_distinctive_tokens(text: str, max_tokens: int = 12) -> list[str]:
    tokens = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    filtered = [t for t in tokens if t not in STOP_WORDS and not t.startswith("<")]
    seen = set()
    result = []
    for t in filtered:
        if t not in seen:
            seen.add(t)
            result.append(t)
            if len(result) >= max_tokens:
                break
    return result


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    a = np.array(v1, dtype=float)
    b = np.array(v2, dtype=float)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


_OFFLINE_RUNBOOKS_CACHE: list[dict[str, Any]] | None = None


def _get_offline_runbooks() -> list[dict[str, Any]]:
    global _OFFLINE_RUNBOOKS_CACHE
    if _OFFLINE_RUNBOOKS_CACHE is not None:
        return _OFFLINE_RUNBOOKS_CACHE

    rb_dir = Path("data/runbooks")
    if not rb_dir.exists():
        return []

    embedder = get_embedder()
    res = []
    texts_to_embed = []
    for f in sorted(rb_dir.glob("RB-*.md")):
        content = f.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        body = m.group(2).strip() if m else content
        rb_id = f.stem
        title = rb_id.replace("RB-", "").replace("-", " ").title()
        services: list[str] = []
        if m:
            fm = m.group(1)
            for line in fm.splitlines():
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("services:"):
                    svcs_raw = line.split(":", 1)[1].strip()
                    services = [s.strip("[] '\"") for s in svcs_raw.split(",") if s.strip("[] '\"")]
        embed_text = f"{title}\n{body}"
        res.append(
            {
                "id": rb_id,
                "title": title,
                "body_md": body,
                "services": services,
                "embed_text": embed_text,
            }
        )
        texts_to_embed.append(embed_text)

    if texts_to_embed:
        embs = embedder.embed_documents(texts_to_embed)
        for r, emb in zip(res, embs):
            r["emb"] = emb

    _OFFLINE_RUNBOOKS_CACHE = res
    return _OFFLINE_RUNBOOKS_CACHE


def _find_top_runbooks_by_emb(q_vec: list[float], top_n: int = 2) -> list[Runbook]:
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, body_md, services, success_count, failure_count, updated_at,
                           1 - (emb <=> %s::vector) AS sim
                    FROM runbooks
                    WHERE emb IS NOT NULL
                    ORDER BY sim DESC
                    LIMIT %s;
                    """,
                    (q_vec, top_n),
                )
                rows = cur.fetchall()
                if rows:
                    return [Runbook(**r) for r in rows]
    except Exception:
        pass

    rbs = _get_offline_runbooks()
    if not rbs:
        return []
    scored = []
    for r in rbs:
        sim = _cosine_similarity(q_vec, r.get("emb", []))
        scored.append((sim, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        Runbook(
            id=r["id"],
            title=r["title"],
            body_md=r["body_md"],
            services=r.get("services", []),
        )
        for _, r in scored[:top_n]
    ]


_OFFLINE_INCIDENTS_CACHE: list[dict[str, Any]] | None = None


def _get_offline_incidents() -> list[dict[str, Any]]:
    global _OFFLINE_INCIDENTS_CACHE
    if _OFFLINE_INCIDENTS_CACHE is not None:
        return _OFFLINE_INCIDENTS_CACHE

    seed_dir = Path("data/seed")
    labels_file = seed_dir / "_labels.json"
    if not labels_file.exists():
        return []

    with open(labels_file, encoding="utf-8") as f:
        labels = json.load(f)

    embedder = get_embedder()
    incidents: list[dict[str, Any]] = []

    for fn, meta in labels.items():
        if meta.get("is_duplicate_of"):
            continue

        m = re.search(r"inc_(\d+)", fn)
        inc_id = f"INC-{int(m.group(1)):04d}" if m else fn
        file_path = seed_dir / fn
        if not file_path.exists():
            continue

        content = file_path.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        title = lines[0].strip("#* -") if lines else inc_id

        # Error fingerprints & errors
        fps = fingerprints(content)
        error_lines = [
            line
            for line in lines
            if any(
                k in line.lower()
                for k in [
                    "error",
                    "exception",
                    "failed",
                    "panic",
                    "timeout",
                    "hikaripool",
                    "x509",
                    "dial tcp",
                ]
            )
        ]

        # Symptoms & Root Cause
        root_cause = "Identified root cause in system logs."
        res_steps = []
        for line in lines:
            if "root cause" in line.lower():
                root_cause = line
            if re.match(r"^\d+\.\s+", line):
                res_steps.append(re.sub(r"^\d+\.\s+", "", line))

        symptoms = [line[2:] for line in lines if line.startswith("- ") or line.startswith("* ")][
            :4
        ]
        runbooks = re.findall(r"\b(RB-[a-zA-Z0-9_\-]+)\b", content)

        symptom_text = (
            f"{title}. Symptoms: {' '.join(symptoms)}. "
            f"Errors: {' '.join(error_lines[:2])}. "
            f"Services: {' '.join(meta.get('services', []))}."
        )

        trigger = "unknown"
        if "deploy" in content.lower() or "version" in content.lower():
            trigger = "deploy"
        elif (
            "cron" in content.lower()
            or "scheduled" in content.lower()
            or "nightly" in content.lower()
        ):
            trigger = "cron"
        elif (
            "traffic" in content.lower() or "load" in content.lower() or "surge" in content.lower()
        ):
            trigger = "traffic"
        elif "config" in content.lower():
            trigger = "config"

        incidents.append(
            {
                "id": inc_id,
                "title": title,
                "category": meta.get("category", "unknown"),
                "services": meta.get("services", []),
                "lookalike_partner": meta.get("lookalike_partner"),
                "symptoms": symptoms,
                "error_fingerprints": fps,
                "error_text": " ".join(error_lines).lower(),
                "content": content.lower(),
                "root_cause": root_cause,
                "resolution_steps": res_steps or ["Restart service and apply runbook"],
                "runbook_ids": list(set(runbooks)),
                "fix_worked": meta.get("fix_worked", True),
                "weight": float(meta.get("weight", 1.0)),
                "architecture_epoch": int(meta.get("architecture_epoch", 1)),
                "trigger_type": trigger,
                "symptom_text": symptom_text,
            }
        )

    if incidents:
        texts = [normalize_text(inc["symptom_text"]) for inc in incidents]
        embs = embedder.embed_documents(texts)
        for inc, emb in zip(incidents, embs):
            inc["emb"] = emb

    _OFFLINE_INCIDENTS_CACHE = incidents
    return incidents


def _offline_recall(
    cue: Cue,
    top_k: int,
    w_vec: float,
    w_fts: float,
    w_fp: float,
    w_svc: float,
    w_code: float,
    q_vec: list[float] | None = None,
) -> RetrievalResult:
    """Offline standalone retrieval fallback when PostgreSQL is not running."""
    incidents = _get_offline_incidents()
    if not incidents:
        return RetrievalResult(incidents=[], patterns=[], runbooks=[])

    exclude_ids = set(cue.exclude_ids or [])
    full_cue_text = cue.text
    if cue.error_messages:
        full_cue_text = f"{cue.text} {' '.join(cue.error_messages)}"
    norm_cue_text = normalize_text(full_cue_text)
    combined_errors = "\n".join(cue.error_messages + cue.stack_traces)
    cue_fps = set(fingerprints(combined_errors)) if combined_errors else set()

    if q_vec is None:
        embedder = get_embedder()
        q_vec = embedder.embed_query(norm_cue_text)
    cue_tokens = set(_extract_distinctive_tokens(norm_cue_text))
    cue_services = set(cue.services)

    scored: list[ScoredIncident] = []

    for inc in incidents:
        inc_id = inc["id"]
        if inc_id in exclude_ids:
            continue

        # 1. Vector similarity
        v = _cosine_similarity(q_vec, inc["emb"]) if w_vec > 0 else 0.0

        # 2. FTS / Keyword token overlap
        f = 0.0
        if w_fts > 0 and cue_tokens:
            content = inc["content"]
            hits = sum(1 for tok in cue_tokens if tok in content)
            f = hits / len(cue_tokens)

        # 3. Fingerprint match
        fp = 0.0
        if w_fp > 0:
            if cue_fps and (cue_fps & set(inc["error_fingerprints"])):
                fp = 1.0
            elif any(err.lower() in inc["error_text"] for err in cue.error_messages if err):
                fp = 0.8

        # 4. Service match (gentle prior)
        s = 0.0
        if w_svc > 0 and cue_services:
            inc_svcs = set(inc["services"])
            if cue_services & inc_svcs:
                s = 0.3

        # 5. Code match
        c = 0.0
        if w_code > 0 and cue.files:
            c = 1.0 if any(f.lower() in inc["content"] for f in cue.files) else 0.0

        base = w_vec * v + w_fts * f + w_fp * fp + w_svc * s + w_code * c

        rb_probs = [get_runbook_success_probability(rb_id) for rb_id in inc["runbook_ids"]]
        best_rb_p = max(rb_probs) if rb_probs else 0.5
        final = base * float(inc["weight"]) * (0.85 + 0.30 * best_rb_p)

        flags: list[str] = []
        if inc.get("fix_worked") is False:
            final *= 0.7
            flags.append("fix_did_not_work")

        if cue.services and not (cue_services & set(inc["services"])):
            flags.append("service_mismatch")

        if (
            cue.trigger_type
            and inc.get("trigger_type")
            and cue.trigger_type != "unknown"
            and inc.get("trigger_type") != "unknown"
            and cue.trigger_type != inc.get("trigger_type")
        ):
            flags.append("trigger_mismatch")

        if inc.get("architecture_epoch", 1) < 1:
            flags.append("stale_architecture")

        if float(inc.get("weight", 1.0)) < 0.6:
            flags.append("old")

        matched_on: list[str] = []
        if v >= 0.4:
            matched_on.append("vec")
        if f >= 0.4:
            matched_on.append("fts")
        if fp >= 0.5:
            matched_on.append("fp")
        if s >= 0.5:
            matched_on.append("svc")
        if c >= 0.5:
            matched_on.append("code")

        summary_text = f"{inc['title']}. Root cause: {inc['root_cause']}."

        scored.append(
            ScoredIncident(
                id=inc_id,
                title=inc["title"],
                final=round(final, 4),
                scores={
                    "vec": round(v, 3),
                    "fts": round(f, 3),
                    "fp": round(fp, 3),
                    "svc": round(s, 3),
                    "code": round(c, 3),
                },
                matched_on=matched_on,
                flags=flags,
                summary=summary_text,
                runbook_ids=inc["runbook_ids"],
                fix_worked=inc["fix_worked"],
                root_cause=inc["root_cause"],
                resolution_steps=inc["resolution_steps"],
            )
        )

    scored.sort(key=lambda x: x.final, reverse=True)
    top_incidents = scored[:top_k]

    result_runbooks: list[Runbook] = []
    target_rb_ids = set()
    for inc in top_incidents:
        target_rb_ids.update(inc.runbook_ids)
    for rb_id in target_rb_ids:
        rb = get_runbook(rb_id)
        if rb:
            result_runbooks.append(rb)

    # Top 2 runbooks by direct embedding similarity
    existing_ids = {rb.id for rb in result_runbooks}
    direct_rbs = _find_top_runbooks_by_emb(q_vec, top_n=2)
    for drb in direct_rbs:
        if drb.id not in existing_ids:
            result_runbooks.append(drb)
            existing_ids.add(drb.id)

    matched_patterns: list[Pattern] = []
    patterns_file = Path("data/consolidated_patterns.json")
    if patterns_file.exists():
        try:
            with open(patterns_file, encoding="utf-8") as pf:
                all_patterns = json.load(pf)
            cue_text = f"{cue.text} {' '.join(cue.services)} {' '.join(cue.error_messages)}".lower()
            for p_dict in all_patterns:
                title_lower = p_dict.get("title", "").lower()
                p_services = [s.lower() for s in p_dict.get("services", [])]
                if any(
                    s.lower() in p_services or s.lower() in title_lower for s in cue.services
                ) or any(tok in cue_text for tok in title_lower.split() if len(tok) > 4):
                    matched_patterns.append(Pattern(**p_dict))
                    if len(matched_patterns) >= 2:
                        break
        except Exception:
            pass

    return RetrievalResult(
        incidents=top_incidents,
        patterns=matched_patterns,
        runbooks=result_runbooks,
    )


def recall(
    cue: Cue,
    top_k: int | None = None,
    mode: str = "hybrid",
    weights_override: dict[str, float] | None = None,
) -> RetrievalResult:
    """The Hippocampal Retrieval Engine. Performs multi-modal hybrid retrieval and pattern separation."""
    settings = get_settings()
    k = top_k or settings.RETRIEVAL_TOP_K
    cand_limit = settings.RETRIEVAL_CANDIDATES
    exclude_ids = cue.exclude_ids or [""]

    # Configure component weights based on mode and overrides
    w_vec = settings.W_VEC
    w_fts = settings.W_FTS
    w_fp = settings.W_FP
    w_svc = settings.W_SVC
    w_code = settings.W_CODE

    if mode == "keyword":
        w_vec = 0.0
        w_fts = 1.0
        w_fp = 0.0
        w_svc = 0.0
        w_code = 0.0
    elif mode == "vector":
        w_vec = 1.0
        w_fts = 0.0
        w_fp = 0.0
        w_svc = 0.0
        w_code = 0.0
    elif weights_override:
        w_vec = weights_override.get("W_VEC", w_vec)
        w_fts = weights_override.get("W_FTS", w_fts)
        w_fp = weights_override.get("W_FP", w_fp)
        w_svc = weights_override.get("W_SVC", w_svc)
        w_code = weights_override.get("W_CODE", w_code)

    # 1. Normalize cue text & generate fingerprints
    full_cue_text = cue.text
    if cue.error_messages:
        full_cue_text = f"{cue.text} {' '.join(cue.error_messages)}"
    norm_cue_text = normalize_text(full_cue_text)
    combined_errors = "\n".join(cue.error_messages + cue.stack_traces)
    cue_fps = fingerprints(combined_errors) if combined_errors else []

    # 2. Embed cue
    embedder = get_embedder()
    q_vec = embedder.embed_query(norm_cue_text)

    vec_scores: dict[str, float] = {}
    fts_scores: dict[str, float] = {}
    fp_scores: dict[str, float] = {}
    svc_scores: dict[str, float] = {}
    code_scores: dict[str, float] = {}

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Set HNSW search depth
                cur.execute("SET LOCAL hnsw.ef_search = 100;")

                # 2a. Vector Candidates
                if w_vec > 0 or mode in ("vector", "hybrid"):
                    cur.execute(
                        """
                        SELECT id, 1 - (emb_symptom <=> %s::vector) AS sim
                        FROM incidents
                        WHERE id <> ALL(%s)
                        ORDER BY emb_symptom <=> %s::vector
                        LIMIT %s;
                        """,
                        (q_vec, exclude_ids, q_vec, cand_limit),
                    )
                    for r in cur.fetchall():
                        sim = max(0.0, min(1.0, float(r["sim"])))
                        vec_scores[r["id"]] = sim

                # 2b. Full-Text Search Candidates
                if w_fts > 0 or mode in ("keyword", "hybrid"):
                    distinct_tokens = _extract_distinctive_tokens(norm_cue_text)
                    if distinct_tokens:
                        fts_query_str = " | ".join(distinct_tokens)
                        cur.execute(
                            """
                            SELECT id, ts_rank_cd(tsv, to_tsquery('english', %s)) AS rank
                            FROM incidents
                            WHERE id <> ALL(%s) AND tsv @@ to_tsquery('english', %s)
                            ORDER BY rank DESC
                            LIMIT %s;
                            """,
                            (fts_query_str, exclude_ids, fts_query_str, cand_limit),
                        )
                        raw_fts = cur.fetchall()
                        max_rank = max([r["rank"] for r in raw_fts], default=0.0)
                        for r in raw_fts:
                            fts_scores[r["id"]] = (
                                float(r["rank"]) / max_rank if max_rank > 0 else 0.0
                            )

                # 2c. Fingerprint Candidates
                if w_fp > 0 and cue_fps:
                    cur.execute(
                        """
                        SELECT id FROM incidents
                        WHERE error_fingerprints && %s AND id <> ALL(%s)
                        LIMIT %s;
                        """,
                        (cue_fps, exclude_ids, cand_limit),
                    )
                    for r in cur.fetchall():
                        fp_scores[r["id"]] = 1.0

                # 2d. Service Graph Candidates
                cue_services = set(cue.services)
                one_hop_services: set[str] = set()
                if w_svc > 0 and cue_services:
                    for svc in cue_services:
                        deps = get_service_dependencies(svc)
                        one_hop_services.update(deps["upstream"])
                        one_hop_services.update(deps["downstream"])

                    all_graph_svcs = list(cue_services | one_hop_services)
                    cur.execute(
                        """
                        SELECT id, services FROM incidents
                        WHERE services && %s AND id <> ALL(%s)
                        LIMIT %s;
                        """,
                        (all_graph_svcs, exclude_ids, cand_limit),
                    )
                    for r in cur.fetchall():
                        inc_svcs = set(r["services"])
                        if inc_svcs & cue_services:
                            svc_scores[r["id"]] = 1.0
                        elif inc_svcs & one_hop_services:
                            svc_scores[r["id"]] = 0.5

                # 2e. Code Candidates
                if w_code > 0 and cue.files:
                    cur.execute(
                        """
                        SELECT DISTINCT incident_id FROM incident_files
                        WHERE file_path = ANY(%s) AND incident_id <> ALL(%s)
                        LIMIT %s;
                        """,
                        (cue.files, exclude_ids, cand_limit),
                    )
                    for r in cur.fetchall():
                        code_scores[r["incident_id"]] = 1.0

                all_candidate_ids = list(
                    set(vec_scores.keys())
                    | set(fts_scores.keys())
                    | set(fp_scores.keys())
                    | set(svc_scores.keys())
                    | set(code_scores.keys())
                )

                if not all_candidate_ids:
                    return RetrievalResult(incidents=[], patterns=[], runbooks=[])

                # Fetch full candidate records
                cur.execute(
                    """
                    SELECT id, title, services, trigger_type, root_cause, resolution_steps,
                           runbook_ids, fix_worked, weight, architecture_epoch, symptoms,
                           1 - (emb_symptom <=> %s::vector) AS direct_vec_sim
                    FROM incidents
                    WHERE id = ANY(%s);
                    """,
                    (q_vec, all_candidate_ids),
                )
                records = {r["id"]: r for r in cur.fetchall()}
    except Exception as e:
        logger.debug("retrieval_database_offline_falling_back", error=str(e))
        return _offline_recall(
            cue=cue,
            top_k=k,
            w_vec=w_vec,
            w_fts=w_fts,
            w_fp=w_fp,
            w_svc=w_svc,
            w_code=w_code,
            q_vec=q_vec,
        )

    # 3. Score candidates and compute mismatch flags
    scored = []
    for inc_id, rec in records.items():
        v = vec_scores.get(inc_id, max(0.0, float(rec["direct_vec_sim"])))
        f = fts_scores.get(inc_id, 0.0)
        fp = fp_scores.get(inc_id, 0.0)
        s = svc_scores.get(inc_id, 0.0)
        c = code_scores.get(inc_id, 0.0)

        base = w_vec * v + w_fts * f + w_fp * fp + w_svc * s + w_code * c

        rb_probs = [get_runbook_success_probability(rb_id) for rb_id in rec["runbook_ids"]]
        best_rb_p = max(rb_probs) if rb_probs else 0.5

        final = base * float(rec["weight"]) * (0.85 + 0.30 * best_rb_p)

        flags = []
        if rec["fix_worked"] is False:
            final *= 0.7
            flags.append("fix_did_not_work")

        inc_services = set(rec["services"])
        if cue.services and not (cue_services & inc_services):
            flags.append("service_mismatch")

        if (
            cue.trigger_type
            and rec["trigger_type"]
            and cue.trigger_type != "unknown"
            and rec["trigger_type"] != "unknown"
            and cue.trigger_type != rec["trigger_type"]
        ):
            flags.append("trigger_mismatch")

        if float(rec["weight"]) < 0.6:
            flags.append("old")

        matched_on = []
        if v >= 0.3:
            matched_on.append("vec")
        if f >= 0.3:
            matched_on.append("fts")
        if fp >= 0.5:
            matched_on.append("fp")
        if s >= 0.5:
            matched_on.append("svc")
        if c >= 0.5:
            matched_on.append("code")

        summary_text = (
            f"{rec['title']}. Root cause: {rec['root_cause']}. "
            f"Fix: {', '.join(rec['resolution_steps'])}."
        )

        scored.append(
            ScoredIncident(
                id=inc_id,
                title=rec["title"],
                final=round(final, 4),
                scores={
                    "vec": round(v, 3),
                    "fts": round(f, 3),
                    "fp": round(fp, 3),
                    "svc": round(s, 3),
                    "code": round(c, 3),
                },
                matched_on=matched_on,
                flags=flags,
                summary=summary_text,
                runbook_ids=rec["runbook_ids"],
                fix_worked=rec["fix_worked"],
                root_cause=rec["root_cause"],
                resolution_steps=rec["resolution_steps"],
            )
        )

    scored.sort(key=lambda x: x.final, reverse=True)
    top_incidents = scored[:k]

    # 4. Patterns retrieval
    matched_patterns: list[Pattern] = []
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, rule_text, exceptions_text, trigger_signals,
                           recommended_checks, recommended_runbooks, member_incident_ids,
                           confidence, 1 - (emb <=> %s::vector) AS sim
                    FROM patterns
                    WHERE emb IS NOT NULL AND 1 - (emb <=> %s::vector) >= 0.60
                    ORDER BY sim DESC
                    LIMIT 3;
                    """,
                    (q_vec, q_vec),
                )
                for r in cur.fetchall():
                    matched_patterns.append(Pattern(**r))
    except Exception:
        pass

    # 5. Runbooks union
    target_rb_ids = set()
    for inc in top_incidents:
        target_rb_ids.update(inc.runbook_ids)
    for pat in matched_patterns:
        target_rb_ids.update(pat.recommended_runbooks)

    result_runbooks = []
    existing_ids = set()
    for rb_id in target_rb_ids:
        rb = get_runbook(rb_id)
        if rb:
            result_runbooks.append(rb)
            existing_ids.add(rb.id)

    # Top 2 runbooks by direct embedding similarity
    direct_rbs = _find_top_runbooks_by_emb(q_vec, top_n=2)
    for drb in direct_rbs:
        if drb.id not in existing_ids:
            result_runbooks.append(drb)
            existing_ids.add(drb.id)

    return RetrievalResult(
        incidents=top_incidents,
        patterns=matched_patterns,
        runbooks=result_runbooks,
    )


def compute_relevance_breakdown(incident: ScoredIncident) -> dict[str, float]:
    """Computes percentage contribution of each signal component to the final hybrid score."""
    total = incident.final
    if total <= 0:
        return {"vec": 0.0, "fts": 0.0, "fp": 0.0, "svc": 0.0, "code": 0.0}
    vec = incident.scores.get("vec", 0.0)
    fts = incident.scores.get("fts", 0.0)
    fp = incident.scores.get("fp", 0.0)
    svc = incident.scores.get("svc", 0.0)
    code = incident.scores.get("code", 0.0)
    return {
        "vec": round((vec * 0.45 / total) * 100, 1),
        "fts": round((fts * 0.20 / total) * 100, 1),
        "fp": round((fp * 0.20 / total) * 100, 1),
        "svc": round((svc * 0.10 / total) * 100, 1),
        "code": round((code * 0.05 / total) * 100, 1),
    }
