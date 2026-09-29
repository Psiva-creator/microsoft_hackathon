"""Prefrontal Cortex (Working Memory) backed by Redis.

In the cognitive incident response architecture:
- Working Memory (Prefrontal Cortex) holds active incident states, live context,
  chronological investigation timeline events, working hypotheses, and episodic retrieval cues.
- Operating characteristics:
  * Low-latency Redis data structures:
    - inc:{id}:meta        -> Hash of active incident metadata
    - inc:{id}:events      -> List of chronological events (RPUSH)
    - inc:{id}:services    -> Set of services touched/discovered (SADD)
    - inc:{id}:hypotheses  -> String of current ranked hypotheses JSON
    - inc:{id}:cue         -> String of current search cue JSON
    - inc:active_ids       -> Set of currently active incident IDs
  * Lifespan & biological pruning:
    - Persistent and untimed while the incident is open/investigating.
    - Upon resolution (close), a 72-hour (259,200s) TTL is applied to all incident keys.
  * Resilience & degraded operation:
    - Seamless fallback to thread-safe in-memory working cache if Redis is offline.
    - Durable recovery from PostgreSQL live_incidents table if Redis keys are evicted.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis

from app.db import get_db, get_redis
from app.logging import get_logger
from app.models import Cue, Hypothesis, LiveContext, LiveEvent

logger = get_logger(__name__)

# Key prefixes and constants
KEY_PREFIX = "inc"
ACTIVE_INCIDENTS_SET = "inc:active_ids"
DEFAULT_TTL_SECONDS = 72 * 3600  # 72 hours (259,200 seconds)
MAX_CONTEXT_EVENTS = 30
MAX_EVENT_TEXT_LEN = 1500

ACTIVE_STATUSES = {"open", "investigating", "postmortem_draft"}
TERMINAL_STATUSES = {"resolved", "confirmed", "archived"}


def _current_timestamp() -> str:
    """Returns current UTC ISO-8601 formatted timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class PrefrontalCortex:
    """Prefrontal Cortex Working Memory Manager backed by Redis with resilient fallback."""

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        fallback_to_memory: bool = True,
    ) -> None:

        self._custom_redis = redis_client
        self._fallback_to_memory = fallback_to_memory
        # In-memory working cache for offline tests / fallback
        self._in_memory_store: dict[str, dict[str, Any]] = {}
        self._in_memory_active_ids: set[str] = set()
        self._last_redis_check_time: float = 0.0
        self._redis_connected: bool = False

    def _get_client(self) -> redis.Redis | None:
        """Returns the active Redis client, or None if unavailable."""
        if self._custom_redis is not None:
            return self._custom_redis

        import time

        now = time.time()
        # Cooldown check: if recent connection check failed within 5.0s, do not stall on socket connect
        if not self._redis_connected and (now - self._last_redis_check_time < 5.0):
            return None

        self._last_redis_check_time = now
        try:
            client = get_redis()
            if client.ping():
                self._redis_connected = True
                return client
            self._redis_connected = False
        except Exception as e:
            self._redis_connected = False
            logger.debug("redis_connection_unavailable", error=str(e))
        return None

    def is_available(self) -> bool:
        """Checks if the underlying Redis store is responsive."""
        return self._get_client() is not None

    def _key(self, live_id: str, suffix: str) -> str:
        return f"{KEY_PREFIX}:{live_id}:{suffix}"

    def create(self, live_id: str, meta: dict[str, Any]) -> None:
        """Initializes working memory for an active incident."""
        now_iso = _current_timestamp()
        status = meta.get("status", "open")
        services_list = meta.get("services", [])
        if isinstance(services_list, str):
            services_list = [services_list]

        meta_data = {
            "id": live_id,
            "title": str(meta.get("title", f"Live Incident {live_id}")),
            "status": str(status),
            "services": json.dumps(list(services_list)),
            "severity": str(meta.get("severity", "unknown")),
            "slack_channel": str(meta.get("slack_channel", "")),
            "slack_thread_ts": str(meta.get("slack_thread_ts", "")),
            "started_at": str(meta.get("started_at", now_iso)),
            "updated_at": now_iso,
            "resolved_at": str(meta.get("resolved_at", "")),
            "resolution": json.dumps(meta.get("resolution", {})),
        }

        r = self._get_client()
        if r is not None:
            try:
                pipe = r.pipeline(transaction=True)
                pipe.hset(self._key(live_id, "meta"), mapping=meta_data)
                if services_list:
                    pipe.sadd(self._key(live_id, "services"), *services_list)
                if status in ACTIVE_STATUSES:
                    pipe.sadd(ACTIVE_INCIDENTS_SET, live_id)
                else:
                    pipe.srem(ACTIVE_INCIDENTS_SET, live_id)
                # Ensure no lingering TTL while active
                for k in ("meta", "events", "services", "hypotheses", "cue"):
                    pipe.persist(self._key(live_id, k))
                pipe.execute()
                return
            except Exception as e:
                logger.warning("redis_working_memory_create_failed", error=str(e), live_id=live_id)

        # In-memory working cache fallback
        if self._fallback_to_memory:
            self._in_memory_store[live_id] = {
                "meta": meta_data,
                "events": [],
                "services": set(services_list),
                "hypotheses": None,
                "cue": None,
                "ttl_expires_at": None,
            }
            if status in ACTIVE_STATUSES:
                self._in_memory_active_ids.add(live_id)
            else:
                self._in_memory_active_ids.discard(live_id)

    def init_live_incident(
        self,
        title: str,
        services: list[str] | None = None,
        description: str = "",
        severity: str = "unknown",
        slack_channel: str = "",
        slack_thread_ts: str = "",
        initial_event: LiveEvent | None = None,
    ) -> str:
        """Generates a unique live incident ID and activates working memory."""
        now_dt = datetime.now(timezone.utc)
        live_id = f"LIVE-{now_dt.strftime('%Y%m%d%H%M%S')}"
        svc_list = services or []

        self.create(
            live_id=live_id,
            meta={
                "title": title,
                "services": svc_list,
                "description": description,
                "status": "investigating",
                "severity": severity,
                "slack_channel": slack_channel,
                "slack_thread_ts": slack_thread_ts,
            },
        )

        if initial_event:
            self.append_event(live_id, initial_event)
        elif description:
            self.append_event(
                live_id,
                LiveEvent(
                    ts=_current_timestamp(),
                    kind="alert",
                    source="init",
                    text=description,
                    data={"title": title, "services": svc_list},
                ),
            )

        return live_id

    def append_event(self, live_id: str, event: LiveEvent) -> None:
        """Appends an event to the chronological incident timeline."""
        event_dict = event.model_dump()
        event_json = json.dumps(event_dict)
        now_iso = _current_timestamp()

        # Service discovery from event metadata
        discovered_services: list[str] = []
        if event.data:
            if "service" in event.data and isinstance(event.data["service"], str):
                discovered_services.append(event.data["service"])
            if "services" in event.data and isinstance(event.data["services"], list):
                discovered_services.extend(
                    [s for s in event.data["services"] if isinstance(s, str)]
                )

        r = self._get_client()
        if r is not None:
            try:
                pipe = r.pipeline(transaction=True)
                pipe.rpush(self._key(live_id, "events"), event_json)
                pipe.hset(self._key(live_id, "meta"), "updated_at", now_iso)
                if discovered_services:
                    pipe.sadd(self._key(live_id, "services"), *discovered_services)
                pipe.execute()
                return
            except Exception as e:
                logger.warning("redis_append_event_failed", error=str(e), live_id=live_id)

        # In-memory fallback
        if self._fallback_to_memory:
            if live_id not in self._in_memory_store:
                self.create(live_id, {"title": f"Live Incident {live_id}"})
            store = self._in_memory_store[live_id]
            store["events"].append(event_dict)
            store["meta"]["updated_at"] = now_iso
            if discovered_services:
                store["services"].update(discovered_services)

    def get_events(self, live_id: str, limit: int = MAX_CONTEXT_EVENTS) -> list[LiveEvent]:
        """Retrieves up to `limit` latest events for an incident in chronological order."""
        r = self._get_client()
        if r is not None:
            try:
                # -limit to -1 gets the most recent `limit` events in chronological order
                raw_events = r.lrange(self._key(live_id, "events"), -limit, -1)
                events = []
                for item in raw_events:
                    data = json.loads(item)
                    events.append(LiveEvent(**data))
                if events:
                    return events
            except Exception as e:
                logger.warning("redis_get_events_failed", error=str(e), live_id=live_id)

        # In-memory store fallback
        mem_events = self._in_memory_store.get(live_id, {}).get("events", [])
        if mem_events:
            return [LiveEvent(**e) for e in mem_events[-limit:]]

        return []

    def get_all_events(self, live_id: str) -> list[LiveEvent]:
        """Retrieves the complete timeline of events for an incident."""
        r = self._get_client()
        if r is not None:
            try:
                raw_events = r.lrange(self._key(live_id, "events"), 0, -1)
                return [LiveEvent(**json.loads(item)) for item in raw_events]
            except Exception as e:
                logger.warning("redis_get_all_events_failed", error=str(e), live_id=live_id)

        mem_events = self._in_memory_store.get(live_id, {}).get("events", [])
        return [LiveEvent(**e) for e in mem_events]

    def set_hypotheses(self, live_id: str, hypotheses: list[Hypothesis]) -> None:
        """Stores the agent's current active ranked hypotheses in working memory."""
        hyp_json = json.dumps([h.model_dump() for h in hypotheses])
        now_iso = _current_timestamp()

        r = self._get_client()
        if r is not None:
            try:
                pipe = r.pipeline(transaction=True)
                pipe.set(self._key(live_id, "hypotheses"), hyp_json)
                pipe.hset(self._key(live_id, "meta"), "updated_at", now_iso)
                pipe.execute()
                return
            except Exception as e:
                logger.warning("redis_set_hypotheses_failed", error=str(e), live_id=live_id)

        if self._fallback_to_memory and live_id in self._in_memory_store:
            self._in_memory_store[live_id]["hypotheses"] = [h.model_dump() for h in hypotheses]
            self._in_memory_store[live_id]["meta"]["updated_at"] = now_iso

    def get_hypotheses(self, live_id: str) -> list[Hypothesis] | None:
        """Retrieves currently active hypotheses."""
        r = self._get_client()
        if r is not None:
            try:
                raw_hyp = r.get(self._key(live_id, "hypotheses"))
                if raw_hyp:
                    hyp_data = json.loads(raw_hyp)
                    return [Hypothesis(**h) for h in hyp_data]
            except Exception as e:
                logger.warning("redis_get_hypotheses_failed", error=str(e), live_id=live_id)

        raw = self._in_memory_store.get(live_id, {}).get("hypotheses")
        if raw is not None:
            return [Hypothesis(**h) for h in raw]
        return None

    def set_cue(self, live_id: str, cue: Cue) -> None:
        """Stores the active episodic retrieval Cue in working memory."""
        cue_json = cue.model_dump_json()
        now_iso = _current_timestamp()

        r = self._get_client()
        if r is not None:
            try:
                pipe = r.pipeline(transaction=True)
                pipe.set(self._key(live_id, "cue"), cue_json)
                pipe.hset(self._key(live_id, "meta"), "updated_at", now_iso)
                if cue.services:
                    pipe.sadd(self._key(live_id, "services"), *cue.services)
                pipe.execute()
                return
            except Exception as e:
                logger.warning("redis_set_cue_failed", error=str(e), live_id=live_id)

        if self._fallback_to_memory and live_id in self._in_memory_store:
            self._in_memory_store[live_id]["cue"] = cue.model_dump()
            self._in_memory_store[live_id]["meta"]["updated_at"] = now_iso
            if cue.services:
                self._in_memory_store[live_id]["services"].update(cue.services)

    def get_cue(self, live_id: str) -> Cue | None:
        """Retrieves the latest search cue from working memory."""
        r = self._get_client()
        if r is not None:
            try:
                raw_cue = r.get(self._key(live_id, "cue"))
                if raw_cue:
                    return Cue(**json.loads(raw_cue))
            except Exception as e:
                logger.warning("redis_get_cue_failed", error=str(e), live_id=live_id)

        raw = self._in_memory_store.get(live_id, {}).get("cue")
        if raw:
            return Cue(**raw)
        return None

    def add_services(self, live_id: str, services: list[str]) -> None:
        """Adds services to the active incident working set."""
        if not services:
            return
        clean_svcs = [s.strip() for s in services if s.strip()]
        if not clean_svcs:
            return

        r = self._get_client()
        if r is not None:
            try:
                pipe = r.pipeline(transaction=True)
                pipe.sadd(self._key(live_id, "services"), *clean_svcs)
                # Keep meta hash in sync with union
                all_svcs = list(set(self.get_services(live_id)) | set(clean_svcs))
                pipe.hset(self._key(live_id, "meta"), "services", json.dumps(all_svcs))
                pipe.hset(self._key(live_id, "meta"), "updated_at", _current_timestamp())
                pipe.execute()
                return
            except Exception as e:
                logger.warning("redis_add_services_failed", error=str(e), live_id=live_id)

        if self._fallback_to_memory and live_id in self._in_memory_store:
            store = self._in_memory_store[live_id]
            store["services"].update(clean_svcs)
            store["meta"]["services"] = json.dumps(list(store["services"]))
            store["meta"]["updated_at"] = _current_timestamp()

    def get_services(self, live_id: str) -> list[str]:
        """Returns all services associated with the active incident."""
        services: set[str] = set()

        r = self._get_client()
        if r is not None:
            try:
                svc_set = r.smembers(self._key(live_id, "services"))
                if svc_set:
                    services.update(svc_set)
                meta_services_raw = r.hget(self._key(live_id, "meta"), "services")
                if meta_services_raw:
                    services.update(json.loads(meta_services_raw))
                return sorted(services)
            except Exception as e:
                logger.warning("redis_get_services_failed", error=str(e), live_id=live_id)

        mem = self._in_memory_store.get(live_id)
        if mem:
            services.update(mem.get("services", set()))
            meta_svcs = mem.get("meta", {}).get("services")
            if meta_svcs:
                if isinstance(meta_svcs, str):
                    services.update(json.loads(meta_svcs))
                elif isinstance(meta_svcs, list):
                    services.update(meta_svcs)

        return sorted(services)

    def update_status(self, live_id: str, status: str) -> None:
        """Updates the active incident lifecycle status."""
        now_iso = _current_timestamp()
        r = self._get_client()
        if r is not None:
            try:
                pipe = r.pipeline(transaction=True)
                pipe.hset(
                    self._key(live_id, "meta"),
                    mapping={"status": status, "updated_at": now_iso},
                )
                if status in ACTIVE_STATUSES:
                    pipe.sadd(ACTIVE_INCIDENTS_SET, live_id)
                elif status in TERMINAL_STATUSES:
                    pipe.srem(ACTIVE_INCIDENTS_SET, live_id)
                pipe.execute()
                return
            except Exception as e:
                logger.warning("redis_update_status_failed", error=str(e), live_id=live_id)

        if self._fallback_to_memory and live_id in self._in_memory_store:
            store = self._in_memory_store[live_id]
            store["meta"]["status"] = status
            store["meta"]["updated_at"] = now_iso
            if status in ACTIVE_STATUSES:
                self._in_memory_active_ids.add(live_id)
            elif status in TERMINAL_STATUSES:
                self._in_memory_active_ids.discard(live_id)

    def update_meta(self, live_id: str, updates: dict[str, Any]) -> None:
        """Updates arbitrary fields in the incident meta hash."""
        now_iso = _current_timestamp()
        string_updates: dict[str, str] = {"updated_at": now_iso}

        for k, v in updates.items():
            if isinstance(v, (dict, list)):
                string_updates[k] = json.dumps(v)
            else:
                string_updates[k] = str(v)

        r = self._get_client()
        if r is not None:
            try:
                pipe = r.pipeline(transaction=True)
                pipe.hset(self._key(live_id, "meta"), mapping=string_updates)
                if "status" in updates:
                    st = updates["status"]
                    if st in ACTIVE_STATUSES:
                        pipe.sadd(ACTIVE_INCIDENTS_SET, live_id)
                    elif st in TERMINAL_STATUSES:
                        pipe.srem(ACTIVE_INCIDENTS_SET, live_id)
                if "services" in updates:
                    svcs = updates["services"]
                    if isinstance(svcs, list) and svcs:
                        pipe.sadd(self._key(live_id, "services"), *svcs)
                pipe.execute()
                return
            except Exception as e:
                logger.warning("redis_update_meta_failed", error=str(e), live_id=live_id)

        if self._fallback_to_memory and live_id in self._in_memory_store:
            self._in_memory_store[live_id]["meta"].update(string_updates)
            if "status" in updates:
                st = updates["status"]
                if st in ACTIVE_STATUSES:
                    self._in_memory_active_ids.add(live_id)
                elif st in TERMINAL_STATUSES:
                    self._in_memory_active_ids.discard(live_id)

    def get_meta(self, live_id: str) -> dict[str, Any]:
        """Retrieves raw metadata for an incident."""
        r = self._get_client()
        if r is not None:
            try:
                meta = r.hgetall(self._key(live_id, "meta"))
                if meta:
                    # Parse JSON fields
                    parsed: dict[str, Any] = dict(meta)
                    if "services" in parsed:
                        try:
                            parsed["services"] = json.loads(parsed["services"])
                        except Exception:
                            pass
                    if "resolution" in parsed:
                        try:
                            parsed["resolution"] = json.loads(parsed["resolution"])
                        except Exception:
                            pass
                    return parsed
            except Exception as e:
                logger.warning("redis_get_meta_failed", error=str(e), live_id=live_id)

        mem = self._in_memory_store.get(live_id, {}).get("meta")
        if mem:
            parsed = dict(mem)
            if isinstance(parsed.get("services"), str):
                try:
                    parsed["services"] = json.loads(parsed["services"])
                except Exception:
                    pass
            if isinstance(parsed.get("resolution"), str):
                try:
                    parsed["resolution"] = json.loads(parsed["resolution"])
                except Exception:
                    pass
            return parsed

        return {}

    def get_context(self, live_id: str) -> LiveContext:
        """Returns a compact context structure for LLM reasoning and inspection.

        Rules (SPEC.md Section 9):
        - Latest up to 30 events, each truncated to 1,500 characters.
        - Union of services mentioned.
        - Hypotheses and active search cue.
        - Fallback to PostgreSQL live_incidents durable record if Redis context lost.
        """
        events = self.get_events(live_id, limit=MAX_CONTEXT_EVENTS)

        # Truncate each event text to 1,500 characters to prevent prompt overflow
        truncated_events: list[LiveEvent] = []
        for ev in events:
            t = ev.text
            if len(t) > MAX_EVENT_TEXT_LEN:
                t = t[:MAX_EVENT_TEXT_LEN] + "... [truncated]"
            truncated_events.append(
                LiveEvent(ts=ev.ts, kind=ev.kind, source=ev.source, text=t, data=ev.data)
            )

        title = f"Live Incident {live_id}"
        status = "open"
        severity = "unknown"
        started_at = None
        resolved_at = None
        slack_channel = None
        slack_thread_ts = None
        resolution: dict[str, Any] = {}
        meta_dict: dict[str, Any] = {}
        services = self.get_services(live_id)
        hypotheses = self.get_hypotheses(live_id)
        cue = self.get_cue(live_id)

        meta = self.get_meta(live_id)
        if meta:
            meta_dict = meta
            title = meta.get("title", title)
            status = meta.get("status", status)
            severity = meta.get("severity", severity)
            started_at = meta.get("started_at")
            resolved_at = meta.get("resolved_at") or None
            slack_channel = meta.get("slack_channel") or None
            slack_thread_ts = meta.get("slack_thread_ts") or None
            if isinstance(meta.get("resolution"), dict):
                resolution = meta["resolution"]
            elif isinstance(meta.get("resolution"), str):
                try:
                    resolution = json.loads(meta["resolution"])
                except Exception:
                    pass
        elif not truncated_events:
            # Redis lost data or incident not found in working memory:
            # Check PostgreSQL live_incidents durable record
            db_recovered = self._recover_from_database(live_id)
            if db_recovered:
                title = db_recovered.get("title", title)
                status = db_recovered.get("status", status)
                slack_channel = db_recovered.get("slack_channel")
                slack_thread_ts = db_recovered.get("slack_thread_ts")
                started_at = db_recovered.get("created_at")
                resolved_at = db_recovered.get("resolved_at")
                resolution = db_recovered.get("resolution") or {}
                # Add notice event as required by SPEC.md line 464
                notice_event = LiveEvent(
                    ts=_current_timestamp(),
                    kind="note",
                    source="prefrontal_cortex",
                    text=(
                        "[Prefrontal Cortex Notice: Working memory context was evicted or missing. "
                        "Incident metadata partially restored from durable database record.]"
                    ),
                    data={"live_id": live_id, "status": status},
                )
                truncated_events.append(notice_event)

        return LiveContext(
            id=live_id,
            title=title,
            status=status,
            severity=severity,
            services=services,
            events=truncated_events,
            hypotheses=hypotheses,
            cue=cue,
            started_at=started_at,
            resolved_at=resolved_at,
            slack_channel=slack_channel,
            slack_thread_ts=slack_thread_ts,
            resolution=resolution,
            meta=meta_dict,
        )

    def _recover_from_database(self, live_id: str) -> dict[str, Any] | None:
        """Recovers baseline incident data from PostgreSQL live_incidents table if Redis lost data."""
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, title, status, slack_channel, slack_thread_ts,
                               created_at, resolved_at, resolution, postmortem_draft
                        FROM live_incidents
                        WHERE id = %s
                        LIMIT 1;
                        """,
                        (live_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        return {
                            "id": row["id"],
                            "title": row["title"],
                            "status": row["status"],
                            "slack_channel": row.get("slack_channel"),
                            "slack_thread_ts": row.get("slack_thread_ts"),
                            "created_at": (
                                row["created_at"].isoformat() if row.get("created_at") else None
                            ),
                            "resolved_at": (
                                row["resolved_at"].isoformat() if row.get("resolved_at") else None
                            ),
                            "resolution": row.get("resolution") or {},
                        }
        except Exception as e:
            logger.debug("prefrontal_db_recovery_failed", live_id=live_id, error=str(e))
        return None

    def close(
        self,
        live_id: str,
        resolution: dict[str, Any] | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        """Sets incident status to resolved and applies 72-hour TTL to all incident keys.

        Rules (SPEC.md Section 9):
        - No TTL while the incident is open.
        - On resolve, set TTL to 72 hours (259,200s) on all working memory keys.
        - Remove incident from active index.
        """
        now_iso = _current_timestamp()
        res_data = resolution or {}

        # 1. Append resolve event to timeline
        resolve_event = LiveEvent(
            ts=now_iso,
            kind="resolve",
            source="human",
            text=f"Incident resolved: {res_data.get('root_cause', 'Mitigation verified.')}",
            data=res_data,
        )

        r = self._get_client()
        if r is not None:
            try:
                pipe = r.pipeline(transaction=True)
                # Append resolve event
                pipe.rpush(self._key(live_id, "events"), json.dumps(resolve_event.model_dump()))
                # Update meta
                pipe.hset(
                    self._key(live_id, "meta"),
                    mapping={
                        "status": "resolved",
                        "resolved_at": now_iso,
                        "updated_at": now_iso,
                        "resolution": json.dumps(res_data),
                    },
                )
                # Remove from active incidents index
                pipe.srem(ACTIVE_INCIDENTS_SET, live_id)
                # Apply 72-hour TTL expiration across all 5 incident keys
                keys = [
                    self._key(live_id, "meta"),
                    self._key(live_id, "events"),
                    self._key(live_id, "services"),
                    self._key(live_id, "hypotheses"),
                    self._key(live_id, "cue"),
                ]
                for k in keys:
                    pipe.expire(k, ttl_seconds)
                pipe.execute()
                return
            except Exception as e:
                logger.warning("redis_close_failed", error=str(e), live_id=live_id)

        # In-memory store fallback
        if self._fallback_to_memory and live_id in self._in_memory_store:
            store = self._in_memory_store[live_id]
            store["events"].append(resolve_event.model_dump())
            store["meta"]["status"] = "resolved"
            store["meta"]["resolved_at"] = now_iso
            store["meta"]["updated_at"] = now_iso
            store["meta"]["resolution"] = json.dumps(res_data)
            store["ttl_expires_at"] = datetime.now(timezone.utc).timestamp() + ttl_seconds
            self._in_memory_active_ids.discard(live_id)

    resolve = close

    def list_active_incidents(self) -> list[dict[str, Any]]:
        """Returns summaries of all currently active incidents managed in working memory."""
        results: list[dict[str, Any]] = []

        r = self._get_client()
        if r is not None:
            try:
                active_ids = r.smembers(ACTIVE_INCIDENTS_SET)
                for aid in active_ids:
                    meta = self.get_meta(aid)
                    event_count = r.llen(self._key(aid, "events"))
                    services = self.get_services(aid)
                    results.append(
                        {
                            "id": aid,
                            "title": meta.get("title", f"Incident {aid}"),
                            "status": meta.get("status", "open"),
                            "severity": meta.get("severity", "unknown"),
                            "services": services,
                            "started_at": meta.get("started_at"),
                            "updated_at": meta.get("updated_at"),
                            "event_count": event_count,
                            "slack_channel": meta.get("slack_channel") or None,
                        }
                    )
                return sorted(results, key=lambda x: str(x.get("started_at") or ""), reverse=True)
            except Exception as e:
                logger.warning("redis_list_active_incidents_failed", error=str(e))

        # In-memory store fallback
        for aid in sorted(self._in_memory_active_ids, reverse=True):
            mem = self._in_memory_store.get(aid, {})
            meta = mem.get("meta", {})
            results.append(
                {
                    "id": aid,
                    "title": meta.get("title", f"Incident {aid}"),
                    "status": meta.get("status", "open"),
                    "severity": meta.get("severity", "unknown"),
                    "services": list(mem.get("services", [])),
                    "started_at": meta.get("started_at"),
                    "updated_at": meta.get("updated_at"),
                    "event_count": len(mem.get("events", [])),
                    "slack_channel": meta.get("slack_channel") or None,
                }
            )

        return results

    def get_active_incident_count(self) -> int:
        """Returns the number of active incidents currently held in working memory."""
        r = self._get_client()
        if r is not None:
            try:
                return int(r.scard(ACTIVE_INCIDENTS_SET))
            except Exception:
                pass
        return len(self._in_memory_active_ids)

    def get_ttl(self, live_id: str) -> dict[str, int]:
        """Returns the TTL in seconds for each working memory key for an incident."""
        ttls: dict[str, int] = {}
        r = self._get_client()
        if r is not None:
            try:
                for suffix in ("meta", "events", "services", "hypotheses", "cue"):
                    k = self._key(live_id, suffix)
                    ttls[suffix] = r.ttl(k)
                return ttls
            except Exception as e:
                logger.warning("redis_get_ttl_failed", error=str(e), live_id=live_id)

        # In-memory approximation
        exp = self._in_memory_store.get(live_id, {}).get("ttl_expires_at")
        if exp is not None:
            remaining = int(max(0, exp - datetime.now(timezone.utc).timestamp()))
            return {k: remaining for k in ("meta", "events", "services", "hypotheses", "cue")}

        return {k: -1 for k in ("meta", "events", "services", "hypotheses", "cue")}

    def clear(self, live_id: str) -> None:
        """Deletes all working memory keys for an incident (used in tests or cleanup)."""
        r = self._get_client()
        if r is not None:
            try:
                keys = [
                    self._key(live_id, "meta"),
                    self._key(live_id, "events"),
                    self._key(live_id, "services"),
                    self._key(live_id, "hypotheses"),
                    self._key(live_id, "cue"),
                ]
                r.delete(*keys)
                r.srem(ACTIVE_INCIDENTS_SET, live_id)
            except Exception as e:
                logger.warning("redis_clear_failed", error=str(e), live_id=live_id)

        self._in_memory_store.pop(live_id, None)
        self._in_memory_active_ids.discard(live_id)


# Semantic alias
WorkingMemory = PrefrontalCortex

# Default singleton instance
default_prefrontal_cortex = PrefrontalCortex()

# Backwards-compatible module-level functions delegating to default instance
create = default_prefrontal_cortex.create
init_live_incident = default_prefrontal_cortex.init_live_incident
append_event = default_prefrontal_cortex.append_event
get_events = default_prefrontal_cortex.get_events
get_all_events = default_prefrontal_cortex.get_all_events
set_hypotheses = default_prefrontal_cortex.set_hypotheses
get_hypotheses = default_prefrontal_cortex.get_hypotheses
set_cue = default_prefrontal_cortex.set_cue
get_cue = default_prefrontal_cortex.get_cue
add_services = default_prefrontal_cortex.add_services
get_services = default_prefrontal_cortex.get_services
update_status = default_prefrontal_cortex.update_status
update_meta = default_prefrontal_cortex.update_meta
get_meta = default_prefrontal_cortex.get_meta
get_context = default_prefrontal_cortex.get_context
get_live_context = default_prefrontal_cortex.get_context
close = default_prefrontal_cortex.close
resolve = default_prefrontal_cortex.close
list_active_incidents = default_prefrontal_cortex.list_active_incidents
get_active_incident_count = default_prefrontal_cortex.get_active_incident_count
get_ttl = default_prefrontal_cortex.get_ttl
clear = default_prefrontal_cortex.clear
