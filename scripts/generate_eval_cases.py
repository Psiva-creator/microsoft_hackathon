import json
import re
from pathlib import Path

SEED_DIR = Path("data/seed")
LABELS_FILE = SEED_DIR / "_labels.json"
CASES_FILE = Path("eval/cases.jsonl")
CASES_FILE.parent.mkdir(parents=True, exist_ok=True)

with open(LABELS_FILE, encoding="utf-8") as f:
    labels = json.load(f)

def fn_to_id(fn: str) -> str:
    m = re.search(r"inc_(\d+)", fn)
    if m:
        return f"INC-{int(m.group(1)):04d}"
    return fn

# Category specific typical errors and symptom templates
CATEGORY_SYMPTOMS = {
    "connection_pool": {
        "symptoms": ["elevated 503 error rates", "connection pool saturation", "database query timeouts"],
        "error": "HikariPool-1 - Connection is not available, request timed out after 30000ms",
    },
    "network_dns": {
        "symptoms": ["cluster wide DNS resolution errors", "service discovery timeouts", "internal connection drops"],
        "error": "dial tcp: lookup postgres-primary on 10.96.0.10:53: no such host",
    },
    "certificate_expiry": {
        "symptoms": ["TLS handshake failures", "HTTPS webhook delivery errors", "SSL validation alert"],
        "error": "x509: certificate has expired or is not yet valid",
    },
    "cache_issue": {
        "symptoms": ["cache stampede", "Redis memory exhaustion", "database read spike from cache miss"],
        "error": "OOM command not allowed when used memory > 'maxmemory'",
    },
    "disk_full": {
        "symptoms": ["database write rejections", "disk capacity 100% full", "WAL archiving failure"],
        "error": "PANIC: could not write to log file: No space left on device",
    },
    "memory_leak": {
        "symptoms": ["JVM GC pause times > 10s", "container OOMKilled", "gradual heap growth"],
        "error": "java.lang.OutOfMemoryError: Java heap space",
    },
    "queue_backlog": {
        "symptoms": ["Kafka consumer group lag spike", "message processing backlog", "rebalancing storm"],
        "error": "CommitFailedException: Commit cannot be completed since the group has already rebalanced",
    },
    "capacity_traffic": {
        "symptoms": ["ingress 502 Bad Gateway", "upstream connection reset under flash sale", "traffic surge"],
        "error": "upstream connect error or disconnect/reset before headers. reset reason: connection termination",
    },
    "dependency_failure": {
        "symptoms": ["third-party partner API outages", "upstream 500 responses", "circuit breaker tripped"],
        "error": "StripeConnectionError: Error communicating with Stripe api.stripe.com",
    },
    "bad_deploy": {
        "symptoms": ["pod CrashLoopBackOff", "syntax error in configuration", "failed healthcheck after deploy"],
        "error": "FATAL: invalid configuration parameter 'max_connections_limit' in config.yaml",
    },
}

# Group IDs by category
category_to_ids: dict[str, list[str]] = {}
for fn, meta in labels.items():
    cat = meta["category"]
    inc_id = fn_to_id(fn)
    category_to_ids.setdefault(cat, []).append(inc_id)

cases: list[dict] = []

# 1. Ten Hand-written Reference Cases
handwritten_cases = [
    {
        "case_id": "c001",
        "source_incident_id": "INC-0007",
        "cue": {
            "text": "checkout-api 503s and p99 8s after deploy",
            "services": ["checkout-api", "postgres-primary"],
            "error_messages": [
                "HikariPool-1 - Connection is not available, request timed out after 30000ms"
            ],
            "trigger_type": "deploy"
        },
        "expected_related_ids": [i for i in category_to_ids["connection_pool"] if i != "INC-0007"],
        "expected_root_cause_category": "connection_pool",
        "notes": "Classic connection pool leak. Look-alike partner is INC-0019 (DNS failure)."
    },
    {
        "case_id": "c002",
        "source_incident_id": "INC-0019",
        "cue": {
            "text": "checkout-api connection failures across all replicas simultaneously",
            "services": ["checkout-api", "postgres-primary"],
            "error_messages": [
                "dial tcp: lookup postgres-primary on 10.96.0.10:53: no such host"
            ],
            "trigger_type": "unknown"
        },
        "expected_related_ids": [i for i in category_to_ids["network_dns"] if i != "INC-0019"],
        "expected_root_cause_category": "network_dns",
        "notes": "CoreDNS pod eviction look-alike vs pool leak."
    },
    {
        "case_id": "c003",
        "source_incident_id": "INC-0012",
        "cue": {
            "text": "payments-gateway TLS handshake errors on webhook delivery",
            "services": ["payments-gateway"],
            "error_messages": [
                "x509: certificate has expired or is not yet valid"
            ],
            "trigger_type": "cron"
        },
        "expected_related_ids": [i for i in category_to_ids["certificate_expiry"] if i != "INC-0012"],
        "expected_root_cause_category": "certificate_expiry",
        "notes": "Expired Let's Encrypt TLS certificate."
    },
    {
        "case_id": "c004",
        "source_incident_id": "INC-0024",
        "cue": {
            "text": "redis-cache high memory usage and cache miss avalanche",
            "services": ["redis-cache", "inventory-service"],
            "error_messages": [
                "OOM command not allowed when used memory > 'maxmemory'"
            ],
            "trigger_type": "traffic"
        },
        "expected_related_ids": [i for i in category_to_ids["cache_issue"] if i != "INC-0024"],
        "expected_root_cause_category": "cache_issue",
        "notes": "Cache stampede due to simultaneous key expiration."
    },
    {
        "case_id": "c005",
        "source_incident_id": "INC-0005",
        "cue": {
            "text": "postgres-primary refusing writes with disk exhaustion alert",
            "services": ["postgres-primary", "orders-service"],
            "error_messages": [
                "PANIC: could not write to log file: No space left on device"
            ],
            "trigger_type": "unknown"
        },
        "expected_related_ids": [i for i in category_to_ids["disk_full"] if i != "INC-0005"],
        "expected_root_cause_category": "disk_full",
        "notes": "Disk full look-alike vs sudden traffic spike."
    },
    {
        "case_id": "c006",
        "source_incident_id": "INC-0015",
        "cue": {
            "text": "orders-service JVM garbage collection pauses exceeding 15 seconds",
            "services": ["orders-service"],
            "error_messages": [
                "java.lang.OutOfMemoryError: Java heap space"
            ],
            "trigger_type": "deploy"
        },
        "expected_related_ids": [i for i in category_to_ids["memory_leak"] if i != "INC-0015"],
        "expected_root_cause_category": "memory_leak",
        "notes": "Memory leak from unclosed static cache list."
    },
    {
        "case_id": "c007",
        "source_incident_id": "INC-0027",
        "cue": {
            "text": "kafka-orders consumer group rebalancing loop and lag spike",
            "services": ["kafka-orders", "notification-worker"],
            "error_messages": [
                "CommitFailedException: Commit cannot be completed since the group has already rebalanced"
            ],
            "trigger_type": "traffic"
        },
        "expected_related_ids": [i for i in category_to_ids["queue_backlog"] if i != "INC-0027"],
        "expected_root_cause_category": "queue_backlog",
        "notes": "Kafka consumer lag and group rebalancing timeout."
    },
    {
        "case_id": "c008",
        "source_incident_id": "INC-0006",
        "cue": {
            "text": "web-frontend ingress 502 Bad Gateway under flash sale load",
            "services": ["web-frontend", "orders-service"],
            "error_messages": [
                "upstream connect error or disconnect/reset before headers. reset reason: connection termination"
            ],
            "trigger_type": "traffic"
        },
        "expected_related_ids": [i for i in category_to_ids["capacity_traffic"] if i != "INC-0006"],
        "expected_root_cause_category": "capacity_traffic",
        "notes": "Sudden traffic surge exceeding HPA pod scale up rate."
    },
    {
        "case_id": "c009",
        "source_incident_id": "INC-0029",
        "cue": {
            "text": "payments-gateway external provider timeouts on checkout completion",
            "services": ["payments-gateway"],
            "error_messages": [
                "StripeConnectionError: Error communicating with Stripe api.stripe.com"
            ],
            "trigger_type": "unknown"
        },
        "expected_related_ids": [i for i in category_to_ids["dependency_failure"] if i != "INC-0029"],
        "expected_root_cause_category": "dependency_failure",
        "notes": "Upstream third-party payment partner outage."
    },
    {
        "case_id": "c010",
        "source_incident_id": "INC-0021",
        "cue": {
            "text": "auth-service crashlooping immediately upon startup after config push",
            "services": ["auth-service"],
            "error_messages": [
                "FATAL: invalid configuration parameter 'max_connections_limit' in config.yaml"
            ],
            "trigger_type": "config"
        },
        "expected_related_ids": [i for i in category_to_ids["bad_deploy"] if i != "INC-0021"],
        "expected_root_cause_category": "bad_deploy",
        "notes": "Invalid configuration key syntax introduced in deployment."
    }
]

cases.extend(handwritten_cases)

# 2. Automated Generation for remaining incidents with high-fidelity cues
case_counter = 11
for fn, meta in sorted(labels.items()):
    source_id = fn_to_id(fn)
    if any(c["source_incident_id"] == source_id for c in handwritten_cases):
        continue

    category = meta["category"]
    services = meta.get("services", ["core-service"])
    template = CATEGORY_SYMPTOMS.get(category, {
        "symptoms": ["general service outage"],
        "error": f"Error detected in {category}"
    })

    main_svc = services[0] if services else "service"
    cue_text = f"{main_svc} degraded: {template['symptoms'][0]} and {template['symptoms'][1]}"
    error_msg = template["error"]

    related = [i for i in category_to_ids.get(category, []) if i != source_id]
    if not related:
        continue

    case_obj = {
        "case_id": f"c{case_counter:03d}",
        "source_incident_id": source_id,
        "cue": {
            "text": cue_text,
            "services": services[:2],
            "error_messages": [error_msg],
            "trigger_type": "deploy" if category in ("bad_deploy", "connection_pool") else "unknown"
        },
        "expected_related_ids": related,
        "expected_root_cause_category": category,
        "notes": f"High-fidelity leave-one-out case for {category}."
    }
    cases.append(case_obj)
    case_counter += 1

with open(CASES_FILE, "w", encoding="utf-8") as f:
    for c in cases:
        f.write(json.dumps(c) + "\n")

print(f"Generated {len(cases)} leave-one-out evaluation cases in {CASES_FILE}")
