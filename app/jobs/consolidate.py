import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from app.config import get_settings
from app.core.embeddings import get_embedder
from app.db import get_db
from app.logging import get_logger

logger = get_logger(__name__)


def compute_decay_weight(
    age_days: float, half_life_days: float = 90.0, min_weight: float = 0.3
) -> float:
    """Calculates exponential half-life decay weight for historical memories."""
    if half_life_days <= 0 or age_days <= 0:
        return 1.0
    decay = 0.5 ** (age_days / half_life_days)
    return max(min_weight, float(decay))


CATEGORY_RULES = {
    "connection_pool": {
        "rule": "When observing recurring connection_pool symptoms, the root cause is typically unreleased connections or slow downstream transactions saturating the pool. Inspect active checkout count and connection leak logs.",
        "exception": "Rule does not hold if the database instance itself is unreachable or returning TCP connection refused.",
        "signals": ["HikariPool connection timeout", "503 Service Unavailable latency spike"],
        "checks": [
            "Inspect HikariCP active/idle pool metrics",
            "Check for long-running uncommitted DB transactions",
            "Verify pool max-size configuration",
        ],
        "runbooks": ["RB-db-pool-exhaustion"],
    },
    "certificate_expiry": {
        "rule": "When TLS handshake failures or x509 certificate errors occur, verify certificate expiration dates on ingress routes and automated renewal cron jobs.",
        "exception": "Rule does not hold if the client TLS version is incompatible with server cipher suites.",
        "signals": ["x509: certificate has expired or is not yet valid", "SSL handshake failed"],
        "checks": [
            "Check cert-manager pod status",
            "Inspect ingress TLS secret expiration with openssl",
            "Verify automated ACME renewal job",
        ],
        "runbooks": ["RB-cert-expiry"],
    },
    "network_dns": {
        "rule": "When dial tcp or DNS lookup timeouts occur across multiple microservices, inspect CoreDNS pod health, node kube-dns endpoints, and upstream resolver latency.",
        "exception": "Rule does not hold if single-service egress security group rules were modified.",
        "signals": ["dial tcp: lookup failed: i/o timeout", "Temporary failure in name resolution"],
        "checks": [
            "Inspect CoreDNS logs and pod restarts",
            "Verify kube-dns ClusterIP reachability from nodes",
            "Check upstream cloud DNS quotas",
        ],
        "runbooks": ["RB-dns-resolution-failure"],
    },
    "cache_issue": {
        "rule": "When observing cache stampede or Redis saturation, inspect hot key eviction rates and ensure cache warming or single-flight request coalescing is active.",
        "exception": "Rule does not hold if Redis memory is exhausted due to missing TTL keys.",
        "signals": [
            "Redis latency spike",
            "Cache miss storm on restart",
            "Downstream DB load spike",
        ],
        "checks": [
            "Inspect Redis CPU and command latency",
            "Check hot-key access patterns",
            "Verify cache single-flight mutex",
        ],
        "runbooks": ["RB-cache-stampede"],
    },
    "memory_leak": {
        "rule": "When container OOMKilled restarts or GC pause spikes occur, inspect recent commit diffs for unclosed streams or unbounded in-memory caches.",
        "exception": "Rule does not hold if traffic volume grew by more than 300% without autoscaling.",
        "signals": [
            "Container terminated with exit code 137 (OOMKilled)",
            "Heap usage monotonically increasing",
        ],
        "checks": [
            "Inspect container memory cgroup metrics",
            "Review recent heap dumps and gc pause times",
            "Check unclosed HTTP/DB response bodies",
        ],
        "runbooks": ["RB-memory-leak-restart"],
    },
    "disk_full": {
        "rule": "When disk write errors or log rotation stalls occur, inspect log directories and container ephemeral storage volumes.",
        "exception": "Rule does not hold if inode exhaustion occurred with available disk space.",
        "signals": ["No space left on device", "DiskWriteQuotaExceeded"],
        "checks": [
            "Check df -h and df -i on affected nodes",
            "Verify systemd journald retention limits",
            "Purge unrotated /var/log debug archives",
        ],
        "runbooks": ["RB-disk-full"],
    },
    "capacity_traffic": {
        "rule": "When global request latency degrades with 429/503 errors during traffic spikes, enable rate limiting and scale out stateless replicas.",
        "exception": "Rule does not hold if downstream third-party APIs are rate-limiting inbound calls.",
        "signals": [
            "HTTP 503 Service Unavailable",
            "P99 latency > 5s across ingress",
            "CPU throttle percentage spike",
        ],
        "checks": [
            "Inspect HPA replica limits",
            "Check ingress rate limit drop counters",
            "Verify edge CDN cache offload ratio",
        ],
        "runbooks": ["RB-bad-deploy-rollback"],
    },
    "bad_deploy": {
        "rule": "When error rates immediately surge within 5 minutes of a deployment, initiate automated rollback to previous known-good image tag.",
        "exception": "Rule does not hold if schema migrations were applied that are backwards-incompatible.",
        "signals": [
            "Deployment canary error rate > 5%",
            "Pod CrashLoopBackOff following image rollout",
        ],
        "checks": [
            "Inspect git diff of latest deployment commit",
            "Verify environment variable configurations",
            "Initiate instant rollback via Helm/ArgoCD",
        ],
        "runbooks": ["RB-bad-deploy-rollback"],
    },
    "queue_backlog": {
        "rule": "When message consumer lag surges and message processing age exceeds SLA, scale consumer worker pools and inspect dead-letter queues.",
        "exception": "Rule does not hold if consumer crashes on poison pill payloads.",
        "signals": [
            "Kafka/RabbitMQ consumer lag > 10,000",
            "End-to-end task completion latency degraded",
        ],
        "checks": [
            "Inspect DLQ error logs for poison payloads",
            "Check consumer thread pool utilization",
            "Scale horizontal consumer pods",
        ],
        "runbooks": ["RB-queue-backlog"],
    },
    "dependency_failure": {
        "rule": "When an external upstream dependency fails or degrades, enable circuit breakers and fallback cached responses.",
        "exception": "Rule does not hold if the upstream failure is localized to a single tenant.",
        "signals": ["Upstream 502/504 Bad Gateway", "Circuit breaker OPEN state"],
        "checks": [
            "Check third-party status dashboard",
            "Verify client-side timeout settings",
            "Confirm circuit breaker fallback behavior",
        ],
        "runbooks": ["RB-bad-deploy-rollback"],
    },
}


def run_consolidation(dry_run: bool = False) -> dict[str, Any]:
    """Runs nightly sleep-replay consolidation: clusters incidents into patterns and decays old memory."""
    settings = get_settings()
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    report_lines = [
        f"# Sleep-Replay Consolidation Report - {today_str}",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Executive Summary",
        "During sleep-replay consolidation, episodic incident records from working and episodic memory",
        "are clustered using Agglomerative Cosine Clustering to extract generalized neocortical patterns.",
        "Additionally, half-life temporal decay is applied to prioritize active architectures over obsolete ones.",
        "",
    ]

    new_patterns_count = 0
    decayed_count = 0
    incidents_data: list[dict[str, Any]] = []
    is_online = False

    # 1. Attempt loading from database
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, services, root_cause, root_cause_category,
                           emb_full, started_at, architecture_epoch
                    FROM incidents
                    WHERE status = 'confirmed';
                    """
                )
                rows = cur.fetchall()
                if rows:
                    incidents_data = [dict(r) for r in rows]
                    is_online = True
    except Exception as e:
        logger.debug("consolidation_db_offline_fallback", error=str(e))

    # 2. Fallback to offline seed incidents if DB unavailable or empty
    if not incidents_data:
        from app.memory.retrieval import _get_offline_incidents

        offline = _get_offline_incidents()
        for inc in offline:
            incidents_data.append(
                {
                    "id": inc["id"],
                    "title": inc["title"],
                    "services": inc["services"],
                    "root_cause": inc["root_cause"],
                    "root_cause_category": inc.get("category", "unknown"),
                    "emb_full": inc["emb"],
                    "started_at": datetime.now(timezone.utc),
                    "architecture_epoch": "v1",
                }
            )

    if len(incidents_data) < 2:
        report_lines.append(
            f"Insufficient incidents ({len(incidents_data)}) to cluster into patterns."
        )
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_file = reports_dir / f"consolidation_{today_str}.md"
        report_file.write_text("\n".join(report_lines), encoding="utf-8")
        return {
            "status": "success",
            "patterns_created": 0,
            "incidents_decayed": 0,
            "report_path": str(report_file),
        }

    # 3. Category-informed Agglomerative Clustering
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for inc in incidents_data:
        cat = inc.get("root_cause_category") or "general"
        by_cat.setdefault(cat, []).append(inc)

    discovered_patterns: list[dict[str, Any]] = []
    embedder = get_embedder()

    report_lines.append("## 🧠 Discovered Knowledge Patterns (Neocortical Consolidation)")
    report_lines.append("")

    for cat, members in by_cat.items():
        if len(members) < 2:
            continue

        embs = np.array([m["emb_full"] for m in members])
        clustering = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=settings.PATTERN_DISTANCE_THRESHOLD,
        )
        labels = clustering.fit_predict(embs)

        sub_clusters: dict[int, list[dict[str, Any]]] = {}
        for idx, lab in enumerate(labels):
            sub_clusters.setdefault(lab, []).append(members[idx])

        cat_meta = CATEGORY_RULES.get(
            cat,
            {
                "rule": f"Recurring failure pattern in {cat.replace('_', ' ')} across services.",
                "exception": "Rule does not hold if caused by independent external outage.",
                "signals": [f"{cat} alerts", "Service latency spikes"],
                "checks": ["Inspect telemetry metrics", "Review deployment history"],
                "runbooks": ["RB-bad-deploy-rollback"],
            },
        )

        for c_label, submembers in sub_clusters.items():
            if len(submembers) < 2:
                continue

            member_ids = [m["id"] for m in submembers]
            all_services = sorted(list({s for m in submembers for s in m.get("services", [])}))
            pattern_title = f"Generalized Pattern: {cat.replace('_', ' ').title()} Failures ({', '.join(all_services[:2])})"
            rule_text = cat_meta["rule"]
            exceptions_text = cat_meta["exception"]
            signals = cat_meta["signals"]
            checks = cat_meta["checks"]
            runbooks = cat_meta.get("runbooks", [])

            pattern_emb = embedder.embed_documents([f"{pattern_title}\n{rule_text}"])[0]

            pattern_record = {
                "id": len(discovered_patterns) + 1,
                "title": pattern_title,
                "rule_text": rule_text,
                "exceptions_text": exceptions_text,
                "trigger_signals": signals,
                "recommended_checks": checks,
                "recommended_runbooks": runbooks,
                "member_incident_ids": member_ids,
                "confidence": 0.88,
                "services": all_services,
                "emb": pattern_emb,
            }
            discovered_patterns.append(pattern_record)
            new_patterns_count += 1

            report_lines.append(f"### 📌 {pattern_title}")
            report_lines.append(
                f"- **Cluster Size:** {len(submembers)} incidents ({', '.join(member_ids)})"
            )
            report_lines.append(f"- **Synthesized Rule:** {rule_text}")
            report_lines.append(f"- **Mismatch Boundary (Exceptions):** {exceptions_text}")
            report_lines.append(f"- **Trigger Signals:** {', '.join(signals)}")
            report_lines.append(f"- **Recommended Checks:** {', '.join(checks)}")
            report_lines.append(f"- **Reinforced Runbooks:** {', '.join(runbooks)}")
            report_lines.append("")

            # If connected to DB, write pattern
            if is_online and not dry_run:
                try:
                    with get_db() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO patterns (title, rule_text, exceptions_text, trigger_signals,
                                                      recommended_checks, member_incident_ids, confidence, emb)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING;
                                """,
                                (
                                    pattern_title,
                                    rule_text,
                                    exceptions_text,
                                    signals,
                                    checks,
                                    member_ids,
                                    0.88,
                                    pattern_emb,
                                ),
                            )
                            conn.commit()
                except Exception as e:
                    logger.debug("consolidation_db_pattern_insert_failed", error=str(e))

    # 4. Memory Decay Calculation
    report_lines.append("## ⏳ Temporal Memory Decay")
    report_lines.append(
        f"Half-life parameter: **{settings.DECAY_HALF_LIFE_DAYS} days** ($w = \\max(0.3, 0.5^{{t / T_{{1/2}}}})$)"
    )
    report_lines.append("")

    now = datetime.now(timezone.utc)
    for inc in incidents_data:
        started = inc.get("started_at") or now
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        age_days = (now - started).days
        weight = max(0.3, 0.5 ** (age_days / settings.DECAY_HALF_LIFE_DAYS))
        decayed_count += 1

        if is_online and not dry_run:
            try:
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE incidents SET weight = %s WHERE id = %s;",
                            (weight, inc["id"]),
                        )
                        conn.commit()
            except Exception as e:
                logger.debug("consolidation_db_decay_update_failed", error=str(e))

    report_lines.append(
        f"- Total episodes evaluated and recalibrated for decay: **{decayed_count}**"
    )
    report_lines.append(f"- Total generalized patterns discovered: **{new_patterns_count}**")

    # 5. Persist discovered patterns to local JSON store for offline retrieval
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    patterns_store_file = data_dir / "consolidated_patterns.json"
    clean_patterns_to_save = [
        {k: v for k, v in p.items() if k != "emb"} for p in discovered_patterns
    ]
    patterns_store_file.write_text(json.dumps(clean_patterns_to_save, indent=2), encoding="utf-8")

    # 6. Save Markdown consolidation report
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"consolidation_{today_str}.md"
    report_file.write_text("\n".join(report_lines), encoding="utf-8")
    logger.info("consolidation_completed", report=str(report_file), patterns=new_patterns_count)

    return {
        "status": "success",
        "patterns_created": new_patterns_count,
        "incidents_decayed": decayed_count,
        "report_path": str(report_file),
    }


if __name__ == "__main__":
    run_consolidation()
