import json
import random
from pathlib import Path

# Fixed seed for reproducibility
random.seed(42)

SEED_DIR = Path("data/seed")
SEED_DIR.mkdir(parents=True, exist_ok=True)
for f in SEED_DIR.glob("*"):
    f.unlink()

CATEGORIES = [
    "connection_pool",
    "bad_deploy",
    "certificate_expiry",
    "disk_full",
    "network_dns",
    "memory_leak",
    "cache_issue",
    "queue_backlog",
    "capacity_traffic",
    "dependency_failure",
]

SERVICES = [
    "web-frontend",
    "checkout-api",
    "payments-gateway",
    "orders-service",
    "inventory-service",
    "postgres-primary",
    "redis-cache",
    "kafka-orders",
    "auth-service",
    "notification-worker",
]

CATEGORY_DETAILS = {
    "connection_pool": {
        "symptoms": ["HTTP 503 errors on checkout", "HikariPool saturation", "database query timeout"],
        "errors": [
            "HikariPool-1 - Connection is not available, request timed out after 30000ms",
            "org.postgresql.util.PSQLException: FATAL: remaining connection slots are reserved for non-replication superuser connections",
            "ActiveConnectionsExhausted: Pool max size 50 reached in OrderRepository.getConnection()",
        ],
        "runbooks": ["RB-db-pool-exhaustion"],
    },
    "bad_deploy": {
        "symptoms": ["CrashLoopBackOff on service pods", "syntax error on startup", "readiness probe failure"],
        "errors": [
            "FATAL: invalid configuration parameter 'max_connections_limit' in config.yaml",
            "ModuleNotFoundError: No module named 'payments.v2.client'",
            "panic: runtime error: invalid memory address or nil pointer dereference at main.go:42",
        ],
        "runbooks": ["RB-bad-deploy-rollback"],
    },
    "certificate_expiry": {
        "symptoms": ["TLS handshake failures", "external webhook delivery failure", "SSL validation errors"],
        "errors": [
            "x509: certificate has expired for domain api.payments.internal",
            "javax.net.ssl.SSLHandshakeException: PKIX path validation failed: certificate expired",
            "OpenSSL.SSL.Error: ('SSL routines', 'ssl3_read_bytes', 'certificate verify failed')",
        ],
        "runbooks": ["RB-cert-expiry"],
    },
    "disk_full": {
        "symptoms": ["database write rejections", "disk capacity at 100%", "WAL archiving failure"],
        "errors": [
            "PANIC: could not write to log file: No space left on device",
            "java.io.IOException: Disk space is full for path /var/lib/postgresql/data",
            "OSError: [Errno 28] No space left on device while writing transaction log",
        ],
        "runbooks": ["RB-disk-full"],
    },
    "network_dns": {
        "symptoms": ["CoreDNS lookup failures", "service discovery timeouts", "internal connection drops"],
        "errors": [
            "dial tcp: lookup postgres-primary on 10.96.0.10:53: no such host",
            "java.net.UnknownHostException: payments-gateway.internal: Name or service not known",
            "getaddrinfo ENOTFOUND kafka-orders.cluster.local:53",
        ],
        "runbooks": ["RB-dns-resolution-failure"],
    },
    "memory_leak": {
        "symptoms": ["container OOMKilled", "JVM GC pause times > 10s", "memory usage gradual linear increase"],
        "errors": [
            "java.lang.OutOfMemoryError: Java heap space at com.acme.worker.TaskProcessor.run(TaskProcessor.java:184)",
            "MemoryError: unable to allocate 128MB array in worker.py:64",
            "Kubelet: container exceeded memory limit of 2Gi and was killed (OOMKilled)",
        ],
        "runbooks": ["RB-memory-leak-restart"],
    },
    "cache_issue": {
        "symptoms": ["cache hit ratio dropped from 95% to 40%", "database CPU surge", "cache stampede"],
        "errors": [
            "OOM command not allowed when used memory > 'maxmemory' in redis-cache",
            "redis.exceptions.ConnectionError: Error 111 connecting to 10.0.1.20:6379. Connection refused",
            "CacheMissStorm: Simultaneous cache key invalidation caused DB CPU to reach 99%",
        ],
        "runbooks": ["RB-cache-stampede"],
    },
    "queue_backlog": {
        "symptoms": ["Kafka consumer lag exceeding 500k messages", "event ingestion delay", "consumer rebalance loop"],
        "errors": [
            "CommitFailedException: Commit cannot be completed since the group has already rebalanced",
            "kafka.errors.BufferError: Queue is full and cannot accept more messages",
            "ConsumerLagAlert: Partition 3 consumer lag exceeded 200000 messages",
        ],
        "runbooks": ["RB-queue-backlog"],
    },
    "capacity_traffic": {
        "symptoms": ["HTTP 502 Bad Gateway under surge", "rate limit exceeded", "ingress connection termination"],
        "errors": [
            "upstream connect error or disconnect/reset before headers. reset reason: connection termination",
            "RateLimitExceeded: Maximum concurrency limit 5000 requests/sec reached",
            "HTTP 429 Too Many Requests: Ingress gateway connection queue full",
        ],
        "runbooks": ["RB-bad-deploy-rollback"],
    },
    "dependency_failure": {
        "symptoms": ["third-party vendor API timeouts", "upstream 500 responses", "circuit breaker open"],
        "errors": [
            "StripeConnectionError: Error communicating with Stripe api.stripe.com after 10000ms",
            "CircuitBreakerOpenException: Downstream service orders-service circuit breaker tripped",
            "HTTP 504 Gateway Timeout: Upstream banking partner failed to respond in 30s",
        ],
        "runbooks": ["RB-bad-deploy-rollback"],
    },
}

labels: dict[str, dict] = {}

# 1. Four Hand-written Reference Incidents (INC-0007, INC-0012, INC-0019, INC-0024)
reference_incidents = [
    {
        "filename": "inc_0007_connection_pool.md",
        "category": "connection_pool",
        "lookalike_partner": "inc_0019_lookalike_dns.md",
        "services": ["checkout-api", "postgres-primary"],
        "content": """# Post-Mortem: INC-0007 - Database Connection Pool Exhaustion on checkout-api

## Executive Summary
On 2026-07-14 at 14:22 UTC, checkout-api experienced severe latency spikes (p99 reaching 8s) and elevated HTTP 503 error rates affecting 45% of customer transactions following deployment of version v212. Total duration was 23 minutes.

## Symptoms
- HTTP 503 Service Unavailable and 504 Gateway Timeout on checkout endpoints.
- HikariPool connection pool saturation.
- Client error logs: HikariPool-1 - Connection is not available, request timed out after 30000ms.

## Root Cause
A retry wrapper implemented in services/checkout/OrderClient.py within the submit() method failed to release acquired database connections in its exception catch block. Repeated retries rapidly exhausted the pool of 50 connections.

## Resolution Steps
1. Rolled back checkout-api deployment from tag v212 to previous stable release v211.
2. Executed rolling restart of checkout-api pods to immediately release orphaned connections.
3. Consulted and executed runbook RB-db-pool-exhaustion.

## Lessons Learned
- Ensure all connection borrows are enclosed in try-with-resources or try-finally blocks.
- Add connection leak detection threshold alerts in staging.
""",
    },
    {
        "filename": "inc_0012_cert_expiry.md",
        "category": "certificate_expiry",
        "lookalike_partner": None,
        "services": ["payments-gateway"],
        "content": """# Post-Mortem: INC-0012 - TLS Handshake Failures on payments-gateway

## Executive Summary
On 2026-05-18 at 09:10 UTC, inbound payments gateway requests failed due to expired SSL certificates. The outage lasted 41 minutes before certificate re-issuance and deployment.

## Symptoms
- 100% of external webhook callbacks failed with TLS handshake errors.
- Logs: x509: certificate has expired for domain api.payments.internal.
- Monitoring alert: CertificateExpiryCritical.

## Root Cause
An automated certificate renewal cron job failed silently following a service-account token rotation 3 weeks prior. The renewal process lacked failure alerting.

## Resolution Steps
1. Followed runbook RB-cert-expiry.
2. Manually provisioned wildcard TLS certificate using emergency offline CA.
3. Updated Kubernetes secret tls-payments-gateway and restarted ingress pods.
4. Corrected IAM service-account binding for cert-manager cron job.
""",
    },
    {
        "filename": "inc_0019_lookalike_dns.md",
        "category": "network_dns",
        "lookalike_partner": "inc_0007_connection_pool.md",
        "services": ["checkout-api", "postgres-primary"],
        "content": """# Post-Mortem: INC-0019 - CoreDNS Pod Eviction Causing Database Disconnection

## Executive Summary
On 2026-08-02 at 18:30 UTC, checkout-api returned widespread 503 errors and connection timeouts for 35 minutes. While symptoms closely resembled pool exhaustion (INC-0007), the root cause was cluster DNS resolution failure.

## Symptoms
- checkout-api 503 errors and client-facing timeouts.
- Error log: dial tcp: lookup postgres-primary on 10.96.0.10:53: no such host.
- Latency spike across multiple internal services simultaneously.

## Root Cause
CoreDNS pods were evicted from worker nodes under sudden memory pressure. checkout-api was unable to resolve the hostname postgres-primary, causing subsequent connection attempts to fail.

## Resolution Steps
1. Consulted runbook RB-dns-resolution-failure.
2. Restarted CoreDNS deployment and scaled replicas from 2 to 6.
3. Added PodDisruptionBudget and dedicated resource guarantees to CoreDNS.
""",
    },
    {
        "filename": "inc_0024_cache_stampede.md",
        "category": "cache_issue",
        "lookalike_partner": None,
        "services": ["redis-cache", "inventory-service"],
        "content": """# Post-Mortem: INC-0024 - Synchronized Cache Expiry Causing Database Overload

## Executive Summary
On 2026-04-11 at 00:05 UTC, inventory-service database CPU surged to 95% following a sharp drop in redis-cache hit ratio from 96% to 41%. Service degradation lasted 52 minutes.

## Symptoms
- redis-cache hit ratio dropped abruptly.
- Postgres primary CPU pinned at 98%.
- Inventory queries timing out with 504 Gateway Timeout.

## Root Cause
A nightly bulk data refresh in services/inventory/cache.py set identical 24-hour TTLs across 800,000 product inventory keys, causing synchronized mass expiry at midnight.

## Resolution Steps
1. Executed runbook RB-cache-stampede.
2. Ran temporary cache pre-warming script to re-populate hot product keys.
3. Deployed patch introducing randomized TTL jitter (+/- 15 minutes) to avoid synchronized expiration.
""",
    },
]

# Write reference incidents
for inc in reference_incidents:
    path = SEED_DIR / inc["filename"]
    path.write_text(inc["content"], encoding="utf-8")
    labels[inc["filename"]] = {
        "category": inc["category"],
        "lookalike_partner": inc["lookalike_partner"],
        "services": inc["services"],
    }

# 2. Allocate non-colliding IDs for remaining 56 incidents
used_ids = {7, 12, 19, 24}
avail_ids = [i for i in range(1, 61) if i not in used_ids]

# 5 Look-alike pairs (10 incidents)
lookalike_templates = [
    (
        "disk_full",
        "postgres-primary write failure due to disk exhaustion",
        "capacity_traffic",
        "postgres-primary write failure due to connection limits under traffic spike",
        ["postgres-primary", "orders-service"],
    ),
    (
        "bad_deploy",
        "payments-gateway crash on startup after missing config env var",
        "dependency_failure",
        "payments-gateway crash on startup after third-party bank sandbox API down",
        ["payments-gateway"],
    ),
    (
        "memory_leak",
        "notification-worker OOMKilled after processing large attachment",
        "queue_backlog",
        "notification-worker high latency due to 1M backlog in kafka-orders",
        ["notification-worker", "kafka-orders"],
    ),
    (
        "connection_pool",
        "orders-service connection starvation from unclosed session",
        "network_dns",
        "orders-service connection starvation from internal DNS timeout",
        ["orders-service", "postgres-primary"],
    ),
    (
        "cache_issue",
        "web-frontend slow render caused by Redis memory eviction",
        "capacity_traffic",
        "web-frontend slow render caused by flash sale 10x traffic spike",
        ["web-frontend", "redis-cache"],
    ),
]

for cat1, desc1, cat2, desc2, svcs in lookalike_templates:
    id1 = avail_ids.pop(0)
    id2 = avail_ids.pop(0)

    f1 = f"inc_{id1:04d}_lookalike_{cat1}.md"
    f2 = f"inc_{id2:04d}_lookalike_{cat2}.md"

    det1 = CATEGORY_DETAILS[cat1]
    det2 = CATEGORY_DETAILS[cat2]

    err1 = det1["errors"][id1 % len(det1["errors"])]
    err2 = det2["errors"][id2 % len(det2["errors"])]
    rb1 = det1["runbooks"][0]
    rb2 = det2["runbooks"][0]

    c1 = f"""# Post-Mortem: INC-{id1:04d} - {desc1}
## Summary
Incident INC-{id1:04d} affecting {", ".join(svcs)}.
## Symptoms
- {det1['symptoms'][0]}
- {det1['symptoms'][1]}
- Logs: {err1}
## Root Cause
Root cause identified as {cat1}: {desc1}.
## Resolution Steps
1. Consulted runbook {rb1}.
2. Restarted impacted pods in {svcs[0]}.
"""
    c2 = f"""# Post-Mortem: INC-{id2:04d} - {desc2}
## Summary
Incident INC-{id2:04d} affecting {", ".join(svcs)}.
## Symptoms
- {det2['symptoms'][0]}
- {det2['symptoms'][1]}
- Logs: {err2}
## Root Cause
Root cause identified as {cat2}: {desc2}.
## Resolution Steps
1. Consulted runbook {rb2}.
2. Restarted impacted pods in {svcs[0]}.
"""
    (SEED_DIR / f1).write_text(c1, encoding="utf-8")
    (SEED_DIR / f2).write_text(c2, encoding="utf-8")
    labels[f1] = {"category": cat1, "lookalike_partner": f2, "services": svcs}
    labels[f2] = {"category": cat2, "lookalike_partner": f1, "services": svcs}

# Remaining 46 synthetic incidents
formats = ["postmortem", "jira", "slack"]
while avail_ids:
    inc_id_num = avail_ids.pop(0)
    cat = CATEGORIES[inc_id_num % len(CATEGORIES)]
    svcs = random.sample(SERVICES, k=random.randint(1, 3))
    fmt = formats[inc_id_num % len(formats)]
    det = CATEGORY_DETAILS[cat]
    err = det["errors"][inc_id_num % len(det["errors"])]
    rb = det["runbooks"][0]

    if fmt == "postmortem":
        fname = f"inc_{inc_id_num:04d}_{cat}.md"
        content = f"""# Post-Mortem: Incident INC-{inc_id_num:04d}
## Summary
Service outage affecting {", ".join(svcs)} for {random.randint(15, 60)} minutes.
## Symptoms
- {det['symptoms'][0]}
- {det['symptoms'][1]}
- Error logs: {err}
## Root Cause
Identified issue in {cat} affecting subsystem stability: {det['symptoms'][0]}.
## Resolution Steps
1. Followed runbook {rb}.
2. Investigated logs from {svcs[0]} and applied fix.
3. Validated health check.
"""
    elif fmt == "jira":
        fname = f"inc_{inc_id_num:04d}_{cat}.json"
        data = {
            "key": f"OPS-{inc_id_num + 1000}",
            "summary": f"Critical outage in {svcs[0]} caused by {cat} (INC-{inc_id_num:04d})",
            "description": f"Service {svcs[0]} incident INC-{inc_id_num:04d}. Symptoms: {det['symptoms'][0]}. Error: {err}. Root cause was {cat}. Followed runbook {rb}.",
            "status": "Resolved",
            "resolution": "Fixed",
            "comments": [
                {"author": "devops1", "body": f"Restarted service pods for {svcs[0]} and applied {rb}."},
                {"author": "sre_lead", "body": f"Confirmed {cat} resolved."},
            ],
        }
        content = json.dumps(data, indent=2)
    else:  # slack
        fname = f"inc_{inc_id_num:04d}_{cat}_slack.txt"
        content = f"""[14:02:11] @channel Alert: {svcs[0]} {det['symptoms'][0]} INC-{inc_id_num:04d}
[14:03:00] @alice: Seeing errors: {err}
[14:05:30] @bob: Root cause is {cat}. Following runbook {rb}.
[14:12:00] @bob: Applying mitigation steps for {cat}.
[14:18:22] @alice: Error rate back down to 0.1%. Outage resolved.
"""
    (SEED_DIR / fname).write_text(content, encoding="utf-8")
    labels[fname] = {"category": cat, "lookalike_partner": None, "services": svcs}

# 3. Four near-duplicates (INC-0061 to INC-0064)
near_dupes = [
    ("inc_0007_connection_pool.md", "inc_0061_dupe_0007.md"),
    ("inc_0012_cert_expiry.md", "inc_0062_dupe_0012.md"),
    ("inc_0019_lookalike_dns.md", "inc_0063_dupe_0019.md"),
    ("inc_0024_cache_stampede.md", "inc_0064_dupe_0024.md"),
]
for src, dupe_name in near_dupes:
    src_content = (SEED_DIR / src).read_text(encoding="utf-8")
    dupe_content = f"# Copy of incident report\n\n{src_content}\nNote: Internal audit copy."
    (SEED_DIR / dupe_name).write_text(dupe_content, encoding="utf-8")
    labels[dupe_name] = {
        "category": labels[src]["category"],
        "lookalike_partner": labels[src]["lookalike_partner"],
        "services": labels[src]["services"],
        "is_duplicate_of": src,
    }

# Save _labels.json
with open(SEED_DIR / "_labels.json", "w", encoding="utf-8") as f:
    json.dump(labels, f, indent=2)

print(f"Generated {len(labels)} seed files in data/seed/ and saved data/seed/_labels.json")
