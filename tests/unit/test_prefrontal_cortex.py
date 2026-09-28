import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config import get_settings
from app.memory.working import (
    DEFAULT_TTL_SECONDS,
    MAX_CONTEXT_EVENTS,
    MAX_EVENT_TEXT_LEN,
    PrefrontalCortex,
    WorkingMemory,
)
from app.models import Cue, Hypothesis, LiveEvent, SimilarIncident


@pytest.fixture
def fake_redis_client():
    """Provides an isolated fakeredis client for testing Redis working memory."""
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server, decode_responses=True)
    return client


@pytest.fixture
def pfc_redis(fake_redis_client):
    """PrefrontalCortex instance bound to fakeredis."""
    return PrefrontalCortex(redis_client=fake_redis_client)


@pytest.fixture
def pfc_memory():
    """PrefrontalCortex instance operating strictly with in-memory fallback."""
    pfc = PrefrontalCortex(redis_client=None, fallback_to_memory=True)
    # Ensure it doesn't attempt to connect to external redis
    pfc._get_client = lambda: None
    return pfc


def test_prefrontal_cortex_redis_initialization(pfc_redis, fake_redis_client):
    """Verifies creation of incident meta hash, services set, and active incident index in Redis."""
    live_id = "LIVE-20260928-TEST01"
    meta = {
        "title": "High 503s on checkout-api",
        "services": ["checkout-api", "redis-cache"],
        "severity": "sev1",
        "slack_channel": "C01234567",
        "slack_thread_ts": "1727540000.123400",
        "status": "investigating",
    }

    pfc_redis.create(live_id, meta)

    # 1. Verify meta hash in Redis
    meta_key = f"inc:{live_id}:meta"
    assert fake_redis_client.exists(meta_key)
    redis_meta = fake_redis_client.hgetall(meta_key)
    assert redis_meta["title"] == "High 503s on checkout-api"
    assert redis_meta["status"] == "investigating"
    assert redis_meta["severity"] == "sev1"
    assert redis_meta["slack_channel"] == "C01234567"
    assert redis_meta["slack_thread_ts"] == "1727540000.123400"
    assert "started_at" in redis_meta

    # 2. Verify services set in Redis
    svc_key = f"inc:{live_id}:services"
    services = fake_redis_client.smembers(svc_key)
    assert "checkout-api" in services
    assert "redis-cache" in services

    # 3. Verify active incidents registry
    active_ids = fake_redis_client.smembers("inc:active_ids")
    assert live_id in active_ids
    assert pfc_redis.get_active_incident_count() == 1


def test_prefrontal_cortex_init_live_incident_helper(pfc_redis, fake_redis_client):
    """Verifies init_live_incident creates live ID and initial alert event."""
    live_id = pfc_redis.init_live_incident(
        title="Payment Gateway Timeout",
        services=["payments-gateway"],
        description="Upstream HTTP 504 Gateway Timeout during auth charge",
        severity="sev2",
    )

    assert live_id.startswith("LIVE-")
    events = pfc_redis.get_events(live_id)
    assert len(events) == 1
    assert events[0].kind == "alert"
    assert "Upstream HTTP 504" in events[0].text
    assert "payments-gateway" in pfc_redis.get_services(live_id)


def test_event_timeline_and_service_autodiscovery(pfc_redis, fake_redis_client):
    """Verifies timeline appending, chronological order, and service auto-discovery from event data."""
    live_id = "LIVE-20260928-TEST02"
    pfc_redis.create(live_id, {"title": "Database connection drop", "services": ["orders-service"]})

    ev1 = LiveEvent(
        ts="2026-09-28T20:00:00Z",
        kind="alert",
        source="alertmanager",
        text="Order service DB timeouts",
        data={"service": "postgres-primary"},
    )
    ev2 = LiveEvent(
        ts="2026-09-28T20:01:00Z",
        kind="log",
        source="loki",
        text="HikariPool connection timeout after 30000ms",
        data={"services": ["checkout-api", "inventory-service"]},
    )
    ev3 = LiveEvent(
        ts="2026-09-28T20:02:00Z",
        kind="message",
        source="slack",
        text="Deploying hotfix v213 to checkout-api",
    )

    pfc_redis.append_event(live_id, ev1)
    pfc_redis.append_event(live_id, ev2)
    pfc_redis.append_event(live_id, ev3)

    # Check chronological ordering
    events = pfc_redis.get_events(live_id)
    assert len(events) == 3
    assert events[0].kind == "alert"
    assert events[1].kind == "log"
    assert events[2].kind == "message"
    assert events[0].text == "Order service DB timeouts"
    assert events[2].text == "Deploying hotfix v213 to checkout-api"

    # Check auto-discovered services
    all_svcs = pfc_redis.get_services(live_id)
    assert "orders-service" in all_svcs
    assert "postgres-primary" in all_svcs
    assert "checkout-api" in all_svcs
    assert "inventory-service" in all_svcs


def test_hypotheses_and_cue_storage(pfc_redis, fake_redis_client):
    """Verifies storing and retrieving ranked hypotheses and retrieval cues in working memory."""
    live_id = "LIVE-20260928-TEST03"
    pfc_redis.create(live_id, {"title": "Cache Stampede", "services": ["redis-cache"]})

    # Test Cue storage
    cue = Cue(
        text="redis-cache hit ratio dropped to 41% after bulk key expiry",
        error_messages=["Cache miss surge"],
        services=["redis-cache", "inventory-service"],
        trigger_type="traffic_spike",
    )
    pfc_redis.set_cue(live_id, cue)
    retrieved_cue = pfc_redis.get_cue(live_id)
    assert retrieved_cue is not None
    assert retrieved_cue.text == cue.text
    assert "inventory-service" in retrieved_cue.services

    # Test Hypotheses storage
    hypotheses = [
        Hypothesis(
            rank=1,
            cause="Nightly batch job expired keys with identical TTLs",
            confidence="high",
            evidence_for=["Hit ratio dropped at 02:00 UTC", "DB CPU surged to 95%"],
            evidence_against=[],
            similar_incidents=[
                SimilarIncident(
                    id="INC-0024",
                    why_similar="Same hit ratio drop and DB spike pattern",
                    differences="Inventory service instead of catalog service",
                )
            ],
            recommended_steps=["Implement jittered TTLs", "Enable request coalescing"],
            runbook_id="RB-cache-stampede",
        )
    ]
    pfc_redis.set_hypotheses(live_id, hypotheses)
    retrieved_hyp = pfc_redis.get_hypotheses(live_id)
    assert retrieved_hyp is not None
    assert len(retrieved_hyp) == 1
    assert retrieved_hyp[0].rank == 1
    assert retrieved_hyp[0].confidence == "high"
    assert retrieved_hyp[0].runbook_id == "RB-cache-stampede"


def test_context_compaction_and_event_truncation(pfc_redis):
    """Verifies that get_context limits to latest 30 events and truncates events over 1500 chars."""
    live_id = "LIVE-20260928-TEST04"
    pfc_redis.create(live_id, {"title": "Alert Storm Stress Test"})

    # Add 40 events with large payloads
    huge_text = "A" * 2500
    for i in range(40):
        ev = LiveEvent(
            ts=f"2026-09-28T20:{i:02d}:00Z",
            kind="log",
            source="system",
            text=f"Event {i}: {huge_text}",
        )
        pfc_redis.append_event(live_id, ev)

    ctx = pfc_redis.get_context(live_id)
    # Must only retain latest 30 events (SPEC.md Section 9)
    assert len(ctx.events) == MAX_CONTEXT_EVENTS
    # First returned event should be Event 10 (since 0..9 were dropped by limit)
    assert ctx.events[0].text.startswith("Event 10:")
    assert ctx.events[-1].text.startswith("Event 39:")

    # Each event text must be truncated to 1500 chars + suffix
    for ev in ctx.events:
        assert len(ev.text) <= MAX_EVENT_TEXT_LEN + len("... [truncated]")
        assert ev.text.endswith("... [truncated]")


def test_active_incidents_management_and_state_transitions(pfc_redis, fake_redis_client):
    """Verifies active incident listing and lifecycle transitions."""
    id1 = "LIVE-20260928-A01"
    id2 = "LIVE-20260928-A02"

    pfc_redis.create(id1, {"title": "Issue 1", "services": ["auth-service"], "severity": "sev2"})
    pfc_redis.create(id2, {"title": "Issue 2", "services": ["checkout-api"], "severity": "sev1"})

    active = pfc_redis.list_active_incidents()
    assert len(active) == 2
    active_ids = [a["id"] for a in active]
    assert id1 in active_ids
    assert id2 in active_ids

    # Update status of id1 to investigating
    pfc_redis.update_status(id1, "investigating")
    meta1 = pfc_redis.get_meta(id1)
    assert meta1["status"] == "investigating"
    assert id1 in fake_redis_client.smembers("inc:active_ids")


def test_close_incident_resolution_and_72h_ttl(pfc_redis, fake_redis_client):
    """Verifies that closing/resolving an incident applies 72h TTL to all keys and removes from active index."""
    live_id = "LIVE-20260928-TEST05"
    pfc_redis.create(live_id, {"title": "Memory Leak in auth-service", "services": ["auth-service"]})
    pfc_redis.append_event(
        live_id,
        LiveEvent(
            ts="2026-09-28T21:00:00Z",
            kind="alert",
            source="prometheus",
            text="Container OOMKilled",
        ),
    )
    pfc_redis.set_cue(live_id, Cue(text="Container OOMKilled auth-service"))
    pfc_redis.set_hypotheses(
        live_id,
        [
            Hypothesis(
                rank=1,
                cause="JWT session token leak in memory",
                confidence="medium",
            )
        ],
    )

    # Confirm keys currently have no TTL while open (-1 means no expiration)
    assert fake_redis_client.ttl(f"inc:{live_id}:meta") == -1
    assert fake_redis_client.ttl(f"inc:{live_id}:events") == -1
    assert fake_redis_client.ttl(f"inc:{live_id}:services") == -1
    assert fake_redis_client.ttl(f"inc:{live_id}:hypotheses") == -1
    assert fake_redis_client.ttl(f"inc:{live_id}:cue") == -1
    assert live_id in fake_redis_client.smembers("inc:active_ids")

    # Close and resolve incident
    resolution_data = {
        "root_cause": "Unbounded cache in TokenValidator.py",
        "steps": ["Restarted deployment", "Applied fix PR #104"],
        "worked": True,
        "runbook_ids": ["RB-memory-leak"],
    }
    pfc_redis.close(live_id, resolution=resolution_data)

    # 1. Verify status is resolved and resolved_at timestamp set
    meta = pfc_redis.get_meta(live_id)
    assert meta["status"] == "resolved"
    assert meta["resolved_at"] != ""
    assert meta["resolution"]["root_cause"] == "Unbounded cache in TokenValidator.py"

    # 2. Verify resolve event was appended
    events = pfc_redis.get_events(live_id)
    assert events[-1].kind == "resolve"
    assert "Unbounded cache" in events[-1].text

    # 3. Verify removed from active incident index
    assert live_id not in fake_redis_client.smembers("inc:active_ids")
    assert pfc_redis.get_active_incident_count() == 0

    # 4. Verify 72-hour (259,200 seconds) TTL is set on all 5 keys (SPEC.md Section 9)
    ttls = pfc_redis.get_ttl(live_id)
    for suffix in ("meta", "events", "services", "hypotheses", "cue"):
        assert 0 < ttls[suffix] <= DEFAULT_TTL_SECONDS
        assert ttls[suffix] >= DEFAULT_TTL_SECONDS - 5  # within 5 seconds


def test_in_memory_fallback_equivalence(pfc_memory):
    """Verifies that all Prefrontal Cortex operations work identically under in-memory fallback."""
    live_id = "LIVE-INMEM-001"
    pfc_memory.create(
        live_id,
        {
            "title": "Fallback Test Incident",
            "services": ["web-frontend"],
            "severity": "sev3",
        },
    )

    # Event appending
    pfc_memory.append_event(
        live_id,
        LiveEvent(
            ts="2026-09-28T21:10:00Z",
            kind="alert",
            source="test",
            text="Frontend latency spike",
            data={"service": "checkout-api"},
        ),
    )

    # Hypotheses
    pfc_memory.set_hypotheses(
        live_id,
        [Hypothesis(rank=1, cause="Network partition", confidence="low")],
    )

    # Cue
    pfc_memory.set_cue(live_id, Cue(text="Frontend latency spike"))

    # Active count
    assert pfc_memory.get_active_incident_count() == 1
    active = pfc_memory.list_active_incidents()
    assert len(active) == 1
    assert active[0]["id"] == live_id

    # Services union
    svcs = pfc_memory.get_services(live_id)
    assert "web-frontend" in svcs
    assert "checkout-api" in svcs

    # Context
    ctx = pfc_memory.get_context(live_id)
    assert ctx.title == "Fallback Test Incident"
    assert len(ctx.events) == 1
    assert ctx.hypotheses[0].cause == "Network partition"

    # Close
    pfc_memory.close(live_id, resolution={"root_cause": "Transient DNS issue"})
    assert pfc_memory.get_active_incident_count() == 0
    closed_ctx = pfc_memory.get_context(live_id)
    assert closed_ctx.status == "resolved"


def test_working_memory_api_routes(fake_redis_client, monkeypatch):
    """Verifies REST API integration with Prefrontal Cortex working memory."""
    from app.memory import working

    monkeypatch.setattr(working.default_prefrontal_cortex, "_custom_redis", fake_redis_client)
    settings = get_settings()
    client = TestClient(app)
    headers = {"X-API-Key": settings.API_KEY}

    # 1. Create incident via REST
    create_resp = client.post(
        "/incidents",
        headers=headers,
        json={
            "title": "REST API Test Incident",
            "description": "Slow API response times observed",
            "services": ["orders-service"],
        },
    )
    assert create_resp.status_code == 201
    live_id = create_resp.json()["live_incident_id"]

    # 2. Append event via REST
    append_resp = client.post(
        f"/incidents/{live_id}/events",
        headers=headers,
        json={
            "kind": "log",
            "source": "ci-test",
            "text": "orders-service response latency p99 > 4000ms",
        },
    )
    assert append_resp.status_code == 200

    # 3. Get live context via REST
    get_resp = client.get(f"/incidents/{live_id}", headers=headers)
    assert get_resp.status_code == 200
    ctx_data = get_resp.json()
    assert ctx_data["id"] == live_id
    assert ctx_data["title"] == "REST API Test Incident"
    assert len(ctx_data["events"]) >= 1

    # 4. List active incidents via GET /incidents
    list_resp = client.get("/incidents", headers=headers)
    assert list_resp.status_code == 200
    active_incidents = list_resp.json()
    assert isinstance(active_incidents, list)
    matching = [inc for inc in active_incidents if inc["id"] == live_id]
    assert len(matching) == 1
    assert matching[0]["title"] == "REST API Test Incident"

    # 5. Query events timeline via GET /incidents/{id}/events
    events_resp = client.get(f"/incidents/{live_id}/events", headers=headers)
    assert events_resp.status_code == 200
    all_events = events_resp.json()
    assert len(all_events) >= 2  # alert + log

    # Query filtered by kind
    log_events_resp = client.get(f"/incidents/{live_id}/events?kind=log", headers=headers)
    assert log_events_resp.status_code == 200
    log_events = log_events_resp.json()
    assert len(log_events) >= 1
    assert all(e["kind"] == "log" for e in log_events)

    # 6. Triage hypotheses via PUT and GET /incidents/{id}/hypotheses
    triage_hypotheses = [
        {
            "rank": 1,
            "cause": "Database connection saturation in orders-service",
            "confidence": "high",
            "evidence_for": ["p99 latency > 4000ms", "Connection pool timeout logs"],
            "evidence_against": [],
            "similar_incidents": [],
            "recommended_steps": ["Increase pool max_size", "Inspect pg_stat_activity"],
            "runbook_id": "RB-db-pool-exhaustion",
        }
    ]
    put_hyp_resp = client.put(
        f"/incidents/{live_id}/hypotheses",
        headers=headers,
        json=triage_hypotheses,
    )
    assert put_hyp_resp.status_code == 200

    get_hyp_resp = client.get(f"/incidents/{live_id}/hypotheses", headers=headers)
    assert get_hyp_resp.status_code == 200
    retrieved_hyp = get_hyp_resp.json()
    assert len(retrieved_hyp) == 1
    assert retrieved_hyp[0]["cause"] == "Database connection saturation in orders-service"

    # 7. Resolve incident and verify automatic 72-hour TTL expiration
    resolve_resp = client.post(
        f"/incidents/{live_id}/resolve",
        headers=headers,
        json={
            "root_cause": "PostgreSQL max_connections reached by rogue batch worker",
            "steps": ["Killed idle rogue connections", "Scaled up pool size"],
            "runbook_ids": ["RB-db-pool-exhaustion"],
            "worked": True,
        },
    )
    assert resolve_resp.status_code == 200

    # Verify incident is no longer in active incidents
    active_after_resolve = client.get("/incidents", headers=headers).json()
    assert not any(inc["id"] == live_id for inc in active_after_resolve)

    # Verify resolved status in context
    resolved_ctx = client.get(f"/incidents/{live_id}", headers=headers).json()
    assert resolved_ctx["status"] == "resolved"
    assert len(resolved_ctx["events"]) >= 3
    assert any(e["kind"] == "resolve" for e in resolved_ctx["events"])
