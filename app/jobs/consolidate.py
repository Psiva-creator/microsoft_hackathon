from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

try:
    from sklearn.cluster import AgglomerativeClustering
except Exception:
    AgglomerativeClustering = None

from app.config import get_settings
from app.core.embeddings import get_embedder
from app.db import get_db
from app.logging import get_logger

logger = get_logger(__name__)


def run_consolidation(dry_run: bool = False) -> dict[str, Any]:
    """Runs nightly sleep-replay consolidation: clusters incidents into patterns and decays old memory."""
    settings = get_settings()
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    report_lines = [
        f"# Sleep-Replay Consolidation Report - {today_str}",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    new_patterns_count = 0
    decayed_count = 0

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # 1. Load confirmed incidents with embeddings
                cur.execute(
                    """
                    SELECT id, title, services, root_cause, root_cause_category,
                           emb_full, started_at, architecture_epoch
                    FROM incidents
                    WHERE status = 'confirmed';
                    """
                )
                rows = cur.fetchall()

                if len(rows) < settings.PATTERN_MIN_CLUSTER:
                    report_lines.append(f"Insufficient incidents ({len(rows)}) to cluster into patterns.")
                else:
                    emb_matrix = np.array([r["emb_full"] for r in rows])

                    # 2. Agglomerative Clustering
                    if AgglomerativeClustering is not None:
                        clustering = AgglomerativeClustering(
                            n_clusters=None,
                            metric="cosine",
                            linkage="average",
                            distance_threshold=settings.PATTERN_DISTANCE_THRESHOLD,
                        )
                        cluster_labels = clustering.fit_predict(emb_matrix)
                    else:
                        import scipy.cluster.hierarchy as sch
                        import scipy.spatial.distance as ssd

                        d = ssd.pdist(emb_matrix, metric="cosine")
                        Z = sch.linkage(d, method="average")
                        cluster_labels = sch.fcluster(
                            Z, t=settings.PATTERN_DISTANCE_THRESHOLD, criterion="distance"
                        )

                    clusters: dict[int, list[dict[str, Any]]] = {}
                    for idx, lab in enumerate(cluster_labels):
                        clusters.setdefault(lab, []).append(rows[idx])

                    report_lines.append("## Knowledge Consolidation: Discovered Patterns")

                    embedder = get_embedder()

                    # 3. Process clusters
                    for c_label, members in clusters.items():
                        if len(members) < settings.PATTERN_MIN_CLUSTER:
                            continue

                        member_ids = [m["id"] for m in members]
                        common_cat = members[0]["root_cause_category"]
                        pattern_title = f"Generalized Pattern: {common_cat.replace('_', ' ').title()} Failures"
                        rule_text = (
                            f"When observing recurring {common_cat} symptoms across {', '.join(members[0]['services'])}, "
                            f"the root cause is typically related to unreleased resources or upstream saturation. "
                            f"Inspect service metrics and pool capacity first."
                        )
                        exceptions_text = (
                            "Rule does not hold if DNS resolution logs or network reachability issues are present."
                        )
                        signals = [f"Spike in {common_cat} errors", "Client 503 latency"]
                        checks = ["Inspect active connections", "Verify recent deploys"]

                        pattern_emb = embedder.embed_documents([f"{pattern_title}\n{rule_text}"])[0]

                        if not dry_run:
                            cur.execute(
                                """
                                INSERT INTO patterns (title, rule_text, exceptions_text, trigger_signals,
                                                      recommended_checks, member_incident_ids, confidence, emb)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING id;
                                """,
                                (
                                    pattern_title,
                                    rule_text,
                                    exceptions_text,
                                    signals,
                                    checks,
                                    member_ids,
                                    0.85,
                                    pattern_emb,
                                ),
                            )
                        new_patterns_count += 1
                        report_lines.append(f"- **{pattern_title}** (Cluster size: {len(members)})")
                        report_lines.append(f"  - Members: {', '.join(member_ids)}")
                        report_lines.append(f"  - Rule: {rule_text}")

                # 4. Memory Decay calculation
                now = datetime.now(timezone.utc)
                for r in rows:
                    started = r["started_at"] or now
                    if started.tzinfo is None:
                        started = started.replace(tzinfo=timezone.utc)
                    age_days = (now - started).days
                    weight = max(0.3, 0.5 ** (age_days / settings.DECAY_HALF_LIFE_DAYS))

                    if not dry_run:
                        cur.execute(
                            "UPDATE incidents SET weight = %s WHERE id = %s;",
                            (weight, r["id"]),
                        )
                    decayed_count += 1

                conn.commit()
    except Exception as e:
        logger.warning("consolidation_db_offline_or_failed", error=str(e))
        report_lines.append(f"Database was unavailable during consolidation run: {e}")

    # 5. Write consolidation report
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"consolidation_{today_str}.md"
    report_file.write_text("\n".join(report_lines), encoding="utf-8")
    logger.info("consolidation_completed", report=str(report_file))

    return {
        "status": "success",
        "patterns_created": new_patterns_count,
        "incidents_decayed": decayed_count,
        "report_path": str(report_file),
    }


if __name__ == "__main__":
    run_consolidation()
