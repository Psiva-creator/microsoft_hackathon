import socket
import time
from contextlib import contextmanager
from typing import Any, Generator
from urllib.parse import urlparse

try:
    import psycopg
    from pgvector.psycopg import register_vector
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
except Exception as _e:
    psycopg = None  # type: ignore
    register_vector = None  # type: ignore
    dict_row = None  # type: ignore
    ConnectionPool = None  # type: ignore

import redis

from app.config import get_settings
from app.logging import get_logger

logger = get_logger(__name__)

_pool: Any | None = None
_redis_client: redis.Redis | None = None
_last_db_failure_time: float = 0.0


def is_service_port_open(url: str, timeout: float = 0.05) -> bool:
    """Performs a quick non-blocking TCP socket check to see if database/redis port is listening."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (5432 if "postgres" in parsed.scheme else 6379)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def configure_connection(conn: Any) -> None:
    """Configures each new database connection by registering pgvector types."""
    if register_vector is not None:
        register_vector(conn)


def get_db_pool() -> Any:
    global _pool
    if ConnectionPool is None:
        raise ConnectionError("psycopg / ConnectionPool is not available in current environment")
    if _pool is None:
        settings = get_settings()
        _pool = ConnectionPool(
            conninfo=settings.DATABASE_URL,
            min_size=1,
            max_size=20,
            timeout=1.0,
            open=True,
            configure=configure_connection,
            kwargs={"row_factory": dict_row, "connect_timeout": 1},
        )
    return _pool


def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_db() -> Generator[Any, None, None]:
    global _last_db_failure_time
    if time.time() - _last_db_failure_time < 300.0:
        raise ConnectionError("Database offline cooldown active")

    settings = get_settings()
    if not is_service_port_open(settings.DATABASE_URL):
        _last_db_failure_time = time.time()
        raise ConnectionError("Database port is unreachable (offline mode active)")

    try:
        pool = get_db_pool()
        with pool.connection(timeout=0.5) as conn:
            _last_db_failure_time = 0.0
            yield conn
    except Exception as e:
        _last_db_failure_time = time.time()
        raise e


_last_redis_failure_time: float = 0.0


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.3,
            socket_timeout=0.5,
        )
    return _redis_client


def check_db_health() -> bool:
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return cur.fetchone() is not None
    except Exception as e:
        logger.debug("db_health_check_failed", error=str(e))
        return False


def check_redis_health() -> bool:
    global _last_redis_failure_time
    if time.time() - _last_redis_failure_time < 10.0:
        return False
    try:
        client = get_redis()
        res = bool(client.ping())
        if res:
            _last_redis_failure_time = 0.0
        return res
    except Exception as e:
        _last_redis_failure_time = time.time()
        logger.debug("redis_health_check_failed", error=str(e))
        return False


check_db = check_db_health
check_redis = check_redis_health

