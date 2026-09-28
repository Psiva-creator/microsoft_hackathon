import json
from pathlib import Path

SCENARIOS_DIR = Path("data/mock_env/scenarios")

# Scenario A: Pool Exhaustion
a_dir = SCENARIOS_DIR / "A_pool_exhaustion"
a_dir.mkdir(parents=True, exist_ok=True)
(a_dir / "alert.json").write_text(
    json.dumps(
        {
            "alertname": "HighLatencyAnd503s",
            "service": "checkout-api",
            "severity": "critical",
            "description": "checkout-api p99 latency spiked to 8200ms and 503 error rate reached 34%",
            "started_at": "2026-09-28T14:15:00Z",
        },
        indent=2,
    )
)
(a_dir / "deploys.json").write_text(
    json.dumps(
        [
            {
                "service": "checkout-api",
                "version": "v212",
                "deployed_at": "2026-09-28T14:05:00Z",
                "commit_sha": "a1b2c3d4",
                "author": "dev@company.com",
                "status": "success",
            }
        ],
        indent=2,
    )
)
(a_dir / "logs.jsonl").write_text(
    """{"timestamp": "2026-09-28T14:10:01Z", "level": "ERROR", "message": "HikariPool-1 - Connection is not available, request timed out after 30000ms"}
{"timestamp": "2026-09-28T14:12:15Z", "level": "ERROR", "message": "HTTP 503 Service Unavailable on POST /v1/checkout/submit"}
{"timestamp": "2026-09-28T14:14:22Z", "level": "WARN", "message": "Connection pool saturation 50/50 active connections in checkout-api"}
"""
)
(a_dir / "metrics.json").write_text(
    json.dumps(
        {
            "service": "checkout-api",
            "metric": "db_connections_active",
            "points": [
                {"timestamp": f"2026-09-28T14:{i:02d}:00Z", "value": 10 + i * 4} for i in range(15)
            ],
        },
        indent=2,
    )
)
(a_dir / "commits.json").write_text(
    json.dumps(
        [
            {
                "sha": "a1b2c3d4",
                "author": "dev@company.com",
                "date": "2026-09-28T13:45:00Z",
                "message": "Add retry wrapper around OrderClient.submit()",
                "files": ["services/checkout/OrderClient.py"],
            }
        ],
        indent=2,
    )
)

# Scenario B: Cert Expiry
b_dir = SCENARIOS_DIR / "B_cert_expiry"
b_dir.mkdir(parents=True, exist_ok=True)
(b_dir / "alert.json").write_text(
    json.dumps(
        {
            "alertname": "TLSHandshakeFailures",
            "service": "payments-gateway",
            "severity": "critical",
            "description": "Inbound payment webhook requests failing with SSL certificate expiration",
            "started_at": "2026-09-28T10:00:00Z",
        },
        indent=2,
    )
)
(b_dir / "deploys.json").write_text(json.dumps([], indent=2))
(b_dir / "logs.jsonl").write_text(
    """{"timestamp": "2026-09-28T10:01:05Z", "level": "ERROR", "message": "x509: certificate has expired for api.payments.internal"}
{"timestamp": "2026-09-28T10:02:10Z", "level": "ERROR", "message": "SSL_ERROR_EXPIRED_CERT_HASH handshake failed"}
"""
)
(b_dir / "metrics.json").write_text(
    json.dumps(
        {
            "service": "payments-gateway",
            "metric": "tls_handshake_errors",
            "points": [
                {"timestamp": f"2026-09-28T10:{i:02d}:00Z", "value": i * 15} for i in range(15)
            ],
        },
        indent=2,
    )
)
(b_dir / "commits.json").write_text(json.dumps([], indent=2))

# Scenario C: Novel
c_dir = SCENARIOS_DIR / "C_novel"
c_dir.mkdir(parents=True, exist_ok=True)
(c_dir / "alert.json").write_text(
    json.dumps(
        {
            "alertname": "NovelUnseenWorkerCrash",
            "service": "notification-worker",
            "severity": "critical",
            "description": "notification-worker crashed with strange quantum parity hardware error",
            "started_at": "2026-09-28T15:30:00Z",
        },
        indent=2,
    )
)
(c_dir / "deploys.json").write_text(json.dumps([], indent=2))
(c_dir / "logs.jsonl").write_text(
    """{"timestamp": "2026-09-28T15:31:00Z", "level": "FATAL", "message": "QuantumHardwareParityBitFault: cosmic ray induced bitflip in register 0x7FFF"}
{"timestamp": "2026-09-28T15:32:00Z", "level": "FATAL", "message": "Kernel panic: unknown machine check exception in user space worker"}
"""
)
(c_dir / "metrics.json").write_text(
    json.dumps(
        {
            "service": "notification-worker",
            "metric": "pod_crash_count",
            "points": [{"timestamp": "2026-09-28T15:31:00Z", "value": 1.0}],
        },
        indent=2,
    )
)
(c_dir / "commits.json").write_text(json.dumps([], indent=2))

# Scenario D: Lookalike DNS
d_dir = SCENARIOS_DIR / "D_lookalike_dns"
d_dir.mkdir(parents=True, exist_ok=True)
(d_dir / "alert.json").write_text(
    json.dumps(
        {
            "alertname": "CheckoutLatencyAnd503s",
            "service": "checkout-api",
            "severity": "critical",
            "description": "checkout-api elevated 503 errors and client timeouts",
            "started_at": "2026-09-28T16:00:00Z",
        },
        indent=2,
    )
)
(d_dir / "deploys.json").write_text(json.dumps([], indent=2))
(d_dir / "logs.jsonl").write_text(
    """{"timestamp": "2026-09-28T16:01:22Z", "level": "ERROR", "message": "dial tcp: lookup postgres-primary on 10.96.0.10:53: no such host"}
{"timestamp": "2026-09-28T16:02:45Z", "level": "ERROR", "message": "HTTP 503 upstream connection timeout to postgres-primary"}
"""
)
(d_dir / "metrics.json").write_text(
    json.dumps(
        {
            "service": "checkout-api",
            "metric": "dns_lookup_errors",
            "points": [
                {"timestamp": f"2026-09-28T16:{i:02d}:00Z", "value": 50 + i * 10} for i in range(10)
            ],
        },
        indent=2,
    )
)
(d_dir / "commits.json").write_text(json.dumps([], indent=2))

print("Created all mock scenario files in data/mock_env/scenarios/")
