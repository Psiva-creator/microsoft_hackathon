import time

from app.memory.retrieval import recall
from app.models import Cue


def test_dns_lookalike_ranks_above_pool_exhaustion() -> None:
    """SPEC.md Section 14.2:
    test_retrieval_lookalike.py: the DNS cue returns the DNS incident above the pool-exhaustion one.
    """
    dns_cue = Cue(
        text="checkout-api 503s and connection timed out CoreDNS evicted",
        services=["checkout-api"],
        error_messages=["dial tcp: lookup postgres-primary on 10.96.0.10:53: no such host"],
    )
    result = recall(dns_cue, top_k=5)
    incident_ids = [inc.id for inc in result.incidents]

    assert "INC-0019" in incident_ids, f"Expected INC-0019 in results, got {incident_ids}"
    if "INC-0007" in incident_ids:
        idx_dns = incident_ids.index("INC-0019")
        idx_pool = incident_ids.index("INC-0007")
        assert idx_dns < idx_pool, f"INC-0019 (rank {idx_dns}) should rank above INC-0007 (rank {idx_pool})"

    # Direct runbook retrieval should include RB-dns-resolution-failure
    runbook_ids = [rb.id for rb in result.runbooks]
    assert "RB-dns-resolution-failure" in runbook_ids


def test_pool_exhaustion_ranks_above_dns() -> None:
    """Scenario A cue must return the pool exhaustion incident at top rank."""
    pool_cue = Cue(
        text="checkout-api p99 latency 8s and 503s after deploy v212",
        services=["checkout-api"],
        error_messages=["HikariPool-1 - Connection is not available, request timed out after 30000ms"],
        trigger_type="deploy",
    )
    result = recall(pool_cue, top_k=5)
    assert len(result.incidents) > 0
    top_inc = result.incidents[0]
    assert top_inc.id in ("INC-0007", "INC-0061"), f"Expected INC-0007 or INC-0061 at rank 1, got {top_inc.id}"

    # Runbooks should include RB-db-pool-exhaustion
    runbook_ids = [rb.id for rb in result.runbooks]
    assert "RB-db-pool-exhaustion" in runbook_ids


def test_pattern_separation_flags() -> None:
    """Verify deterministic pattern separation flags without LLM."""
    cue = Cue(
        text="connection pool timeout error",
        services=["auth-service"],  # doesn't match checkout-api
        error_messages=["Connection is not available"],
        trigger_type="cron",  # differs from deploy
    )
    result = recall(cue, top_k=5)
    for inc in result.incidents:
        if inc.id == "INC-0007":
            # INC-0007 has service checkout-api and trigger deploy
            assert "service_mismatch" in inc.flags
            assert "trigger_mismatch" in inc.flags


def test_retrieval_latency_sub_500ms() -> None:
    """SPEC.md Section 10.6 & 16 Phase 3:
    Retrieval p95 under 500 ms on a laptop.
    """
    cue = Cue(
        text="checkout-api 503s and connection timed out",
        services=["checkout-api"],
        error_messages=["dial tcp: lookup postgres-primary: no such host"],
    )
    # Warmup
    recall(cue, top_k=5)

    latencies_ms: list[float] = []
    for _ in range(10):
        t0 = time.perf_counter()
        recall(cue, top_k=5)
        dt = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt)

    latencies_ms.sort()
    # 95th percentile index for 10 elements
    p95 = latencies_ms[int(0.95 * len(latencies_ms))]
    assert p95 < 500.0, f"Retrieval p95 latency {p95:.2f}ms exceeded 500ms limit"


def test_relevance_breakdown_explainability() -> None:
    """Verify that compute_relevance_breakdown produces explainable percentage weights."""
    from app.memory.retrieval import compute_relevance_breakdown

    cue = Cue(
        text="checkout-api 503s HikariPool timeout",
        services=["checkout-api"],
        error_messages=["HikariPool-1 - Connection is not available"],
    )
    result = recall(cue, top_k=1)
    assert len(result.incidents) > 0
    breakdown = compute_relevance_breakdown(result.incidents[0])
    for key in ("vec", "fts", "fp", "svc", "code"):
        assert key in breakdown
        assert isinstance(breakdown[key], float)
