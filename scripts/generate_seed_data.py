import json
import random
from pathlib import Path

# Fixed seed for reproducibility
random.seed(42)

SEED_DIR = Path("data/seed")
SEED_DIR.mkdir(parents=True, exist_ok=True)

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

labels = {}

# 1. Hand-written Reference Incidents
incidents_data = [
    {
        "filename": "inc_0007_connection_pool.md",
        "format": "markdown",
        "category": "connection_pool",
        "lookalike_partner": "inc_0019_lookalike_dns.md",
        "services": ["checkout-api", "postgres-primary"],
        "files": [("services/checkout/OrderClient.py", "submit")],
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
        "format": "markdown",
        "category": "certificate_expiry",
        "lookalike_partner": None,
        "services": ["payments-gateway"],
        "files": [("infra/certmanager/cron.yaml", "renew_certs")],
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
        "format": "markdown",
        "category": "network_dns",
        "lookalike_partner": "inc_0007_connection_pool.md",
        "services": ["checkout-api", "postgres-primary"],
        "files": [("k8s/coredns/deployment.yaml", "coredns")],
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
        "format": "markdown",
        "category": "cache_issue",
        "lookalike_partner": None,
        "services": ["redis-cache", "inventory-service"],
        "files": [("services/inventory/cache.py", "batch_refresh")],
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

# Write hand-written reference incidents
for inc in incidents_data:
    path = SEED_DIR / inc["filename"]
    path.write_text(inc["content"])
    labels[inc["filename"]] = {
        "category": inc["category"],
        "lookalike_partner": inc["lookalike_partner"],
        "services": inc["services"],
    }

# Generate synthetic incidents across categories and formats
file_index = len(incidents_data) + 1

# Templates for Look-alike pairs
lookalikes = [
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

for idx, (cat1, desc1, cat2, desc2, svcs) in enumerate(lookalikes, 1):
    f1 = f"inc_{file_index:04d}_lookalike_{cat1}.md"
    file_index += 1
    f2 = f"inc_{file_index:04d}_lookalike_{cat2}.md"
    file_index += 1

    content1 = f"""# Post-Mortem: {desc1}
## Summary
Incident affecting {", ".join(svcs)}. Users observed severe latency and 500 errors.
## Symptoms
- Error rate above 20%.
- Elevated response times.
- Logs: Error in database client: {desc1}.
## Root Cause
Underlying root cause identified as {cat1}: {desc1}.
## Resolution Steps
1. Identified root cause in system metrics.
2. Applied recovery steps according to standard runbook.
3. System returned to normal operating capacity.
"""

    content2 = f"""# Post-Mortem: {desc2}
## Summary
Incident affecting {", ".join(svcs)}. Visible symptoms mirror {cat1} but root cause differs.
## Symptoms
- Error rate above 20%.
- Elevated response times.
- Logs: Error in database client: {desc2}.
## Root Cause
Underlying root cause identified as {cat2}: {desc2}.
## Resolution Steps
1. Confirmed symptoms are not due to {cat1} by inspecting logs.
2. Applied remediation for {cat2}.
3. Restored service availability.
"""
    (SEED_DIR / f1).write_text(content1)
    (SEED_DIR / f2).write_text(content2)
    labels[f1] = {"category": cat1, "lookalike_partner": f2, "services": svcs}
    labels[f2] = {"category": cat2, "lookalike_partner": f1, "services": svcs}

# Generate remaining incidents to reach 60 incidents
while file_index <= 60:
    cat = CATEGORIES[file_index % len(CATEGORIES)]
    svcs = random.sample(SERVICES, k=random.randint(1, 3))
    fmt = random.choice(["postmortem", "jira", "slack"])
    ip = f"10.0.{random.randint(1, 20)}.{random.randint(1, 250)}"
    port = random.choice([5432, 6379, 8000, 9092])

    if fmt == "postmortem":
        fname = f"inc_{file_index:04d}_{cat}.md"
        content = f"""# Post-Mortem: Incident INC-{file_index:04d}
## Summary
Service outage affecting {", ".join(svcs)} for {random.randint(15, 60)} minutes.
## Symptoms
- HTTP 500 and 503 errors on endpoints.
- Error logs: Connection failed to {ip}:{port} with status 503.
## Root Cause
Identified issue in {cat} affecting subsystem stability.
## Resolution Steps
1. Investigated logs from {svcs[0]}.
2. Restarted failed components.
3. Validated health check.
"""
    elif fmt == "jira":
        fname = f"inc_{file_index:04d}_{cat}.json"
        data = {
            "key": f"OPS-{file_index + 1000}",
            "summary": f"Critical outage in {svcs[0]} caused by {cat}",
            "description": f"Service {svcs[0]} stopped responding after connection error to {ip}:{port}. Root cause was {cat}.",
            "status": "Resolved",
            "resolution": "Fixed",
            "comments": [
                {"author": "devops1", "body": f"Restarted service pods for {svcs[0]}."},
                {"author": "sre_lead", "body": f"Confirmed {cat} resolved."},
            ],
        }
        content = json.dumps(data, indent=2)
    else:  # slack transcript
        fname = f"inc_{file_index:04d}_{cat}_slack.txt"
        content = f"""[14:02:11] @channel Alert: {svcs[0]} high error rate (> 15%)
[14:03:00] @alice: Seeing timeouts connecting to {ip}:{port} on {svcs[0]}
[14:05:30] @bob: Root cause appears to be {cat}. Investigating now.
[14:12:00] @bob: Applying mitigation steps for {cat}.
[14:18:22] @alice: Error rate back down to 0.1%. Outage resolved.
"""
    (SEED_DIR / fname).write_text(content)
    labels[fname] = {"category": cat, "lookalike_partner": None, "services": svcs}
    file_index += 1

# Generate 4 near-duplicates to test deduplication
near_dupes = [
    ("inc_0007_connection_pool.md", "inc_0061_dupe_0007.md"),
    ("inc_0012_cert_expiry.md", "inc_0062_dupe_0012.md"),
    ("inc_0019_lookalike_dns.md", "inc_0063_dupe_0019.md"),
    ("inc_0024_cache_stampede.md", "inc_0064_dupe_0024.md"),
]
for src, dupe_name in near_dupes:
    src_content = (SEED_DIR / src).read_text()
    dupe_content = f"# Copy of incident report\n\n{src_content}\nNote: Internal audit copy."
    (SEED_DIR / dupe_name).write_text(dupe_content)
    labels[dupe_name] = {
        "category": labels[src]["category"],
        "lookalike_partner": labels[src]["lookalike_partner"],
        "services": labels[src]["services"],
        "is_duplicate_of": src,
    }

# Save _labels.json
with open(SEED_DIR / "_labels.json", "w") as f:
    json.dump(labels, f, indent=2)

print(f"Generated {len(labels)} seed files in data/seed/ and saved data/seed/_labels.json")
