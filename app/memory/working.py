import json
from datetime import datetime
from typing import Any

from app.db import get_redis
from app.logging import get_logger
from app.models import Hypothesis, LiveContext, LiveEvent

logger = get_logger(__name__)

# In-memory fallback if Redis is offline (e.g. in local unit tests)
_in_memory_store: dict[str, dict[str, Any]] = {}


def _is_redis_available() -> bool:
    try:
        client = get_redis()
        return bool(client.ping())
    except Exception:
        return False


def create(live_id: str, meta: dict[str, Any]) -> None:
    """Initializes working memory for a live incident."""
    now_iso = datetime.utcnow().isoformat() + "Z"
    meta_data = {
        "title": meta.get("title", f"Live Incident {live_id}"),
        "status": meta.get("status", "open"),
        "services": json.dumps(meta.get("services", [])),
        "severity": meta.get("severity", "unknown"),
        "slack_channel": meta.get("slack_channel", ""),
        "slack_thread_ts": meta.get("slack_thread_ts", ""),
        "started_at": meta.get("started_at", now_iso),
    }

    if _is_redis_available():
        try:
            r = get_redis()
            meta_key = f"inc:{live_id}:meta"
            r.hset(meta_key, mapping=meta_data)
            if meta.get("services"):
                svc_key = f"inc:{live_id}:services"
                r.sadd(svc_key, *meta["services"])
            return
        except Exception as e:
            logger.warning("redis_working_memory_write_failed", error=str(e))

    # In-memory fallback
    _in_memory_store[live_id] = {
        "meta": meta_data,
        "events": [],
        "services": set(meta.get("services", [])),
        "hypotheses": None,
        "cue": None,
    }


def append_event(live_id: str, event: LiveEvent) -> None:
    """Appends an event to the working memory timeline."""
    event_dict = event.model_dump()
    event_json = json.dumps(event_dict)

    if _is_redis_available():
        try:
            r = get_redis()
            r.rpush(f"inc:{live_id}:events", event_json)
            return
        except Exception as e:
            logger.warning("redis_append_event_failed", error=str(e))

    if live_id not in _in_memory_store:
        create(live_id, {"title": f"Live Incident {live_id}"})
    _in_memory_store[live_id]["events"].append(event_dict)


def get_events(live_id: str, limit: int = 30) -> list[LiveEvent]:
    """Retrieves the latest events for an incident."""
    if _is_redis_available():
        try:
            r = get_redis()
            raw_events = r.lrange(f"inc:{live_id}:events", -limit, -1)
            events = []
            for item in raw_events:
                data = json.loads(item)
                events.append(LiveEvent(**data))
            return events
        except Exception as e:
            logger.warning("redis_get_events_failed", error=str(e))

    mem = _in_memory_store.get(live_id, {}).get("events", [])
    return [LiveEvent(**e) for e in mem[-limit:]]


def set_hypotheses(live_id: str, hypotheses: list[Hypothesis]) -> None:
    """Updates current active hypotheses in working memory."""
    hyp_json = json.dumps([h.model_dump() for h in hypotheses])

    if _is_redis_available():
        try:
            r = get_redis()
            r.set(f"inc:{live_id}:hypotheses", hyp_json)
            return
        except Exception as e:
            logger.warning("redis_set_hypotheses_failed", error=str(e))

    if live_id in _in_memory_store:
        _in_memory_store[live_id]["hypotheses"] = [h.model_dump() for h in hypotheses]


def get_context(live_id: str) -> LiveContext:
    """Returns a compact context structure for LLM investigation."""
    events = get_events(live_id, limit=30)
    # Truncate each event text to 1,500 characters
    truncated_events = []
    for ev in events:
        t = ev.text
        if len(t) > 1500:
            t = t[:1500] + "... [truncated]"
        truncated_events.append(LiveEvent(ts=ev.ts, kind=ev.kind, source=ev.source, text=t, data=ev.data))

    title = f"Live Incident {live_id}"
    services: list[str] = []
    hypotheses: list[Hypothesis] | None = None

    if _is_redis_available():
        try:
            r = get_redis()
            meta = r.hgetall(f"inc:{live_id}:meta")
            if meta:
                title = meta.get("title", title)
                if "services" in meta:
                    services = json.loads(meta["services"])
            svc_set = r.smembers(f"inc:{live_id}:services")
            if svc_set:
                services = list(set(services) | svc_set)

            raw_hyp = r.get(f"inc:{live_id}:hypotheses")
            if raw_hyp:
                hyp_data = json.loads(raw_hyp)
                hypotheses = [Hypothesis(**h) for h in hyp_data]
            return LiveContext(id=live_id, title=title, services=services, events=truncated_events, hypotheses=hypotheses)
        except Exception as e:
            logger.warning("redis_get_context_failed", error=str(e))

    mem = _in_memory_store.get(live_id)
    if mem:
        title = mem.get("meta", {}).get("title", title)
        services = list(mem.get("services", []))
        if mem.get("hypotheses"):
            hypotheses = [Hypothesis(**h) for h in mem["hypotheses"]]

    return LiveContext(id=live_id, title=title, services=services, events=truncated_events, hypotheses=hypotheses)


def close(live_id: str) -> None:
    """Sets a 72-hour (259200s) TTL on all working memory keys upon incident resolution."""
    ttl_seconds = 72 * 3600  # 72 hours
    if _is_redis_available():
        try:
            r = get_redis()
            keys = [
                f"inc:{live_id}:meta",
                f"inc:{live_id}:events",
                f"inc:{live_id}:services",
                f"inc:{live_id}:hypotheses",
                f"inc:{live_id}:cue",
            ]
            for k in keys:
                r.expire(k, ttl_seconds)
            return
        except Exception as e:
            logger.warning("redis_close_expire_failed", error=str(e))

    if live_id in _in_memory_store:
        _in_memory_store[live_id]["meta"]["status"] = "resolved"


get_live_context = get_context


def init_live_incident(
    title: str,
    services: list[str] | None = None,
    description: str = "",
) -> str:
    """Generates a unique live incident ID and initializes working memory."""
    live_id = f"LIVE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    create(
        live_id=live_id,
        meta={
            "title": title,
            "services": services or [],
            "description": description,
            "status": "investigating",
        },
    )
    return live_id
