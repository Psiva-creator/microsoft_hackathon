import time
from contextlib import contextmanager
from typing import Generator

import psycopg
import redis
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings
from app.logging import get_logger

logger = get_logger(__name__)

_pool: ConnectionPool | None = None
_redis_client: redis.Redis | None = None
_last_db_failure_time: float = 0.0


def configure_connection(conn: psycopg.Connection) -> None:
    """Configures each new database connection by registering pgvector types."""
    register_vector(conn)


def get_db_pool() -> ConnectionPool:
    global _pool
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
def get_db() -> Generator[psycopg.Connection, None, None]:
    global _last_db_failure_time
    if time.time() - _last_db_failure_time < 300.0:
        raise ConnectionError("Database offline cooldown active")

    try:
        pool = get_db_pool()
        with pool.connection(timeout=0.5) as conn:
            _last_db_failure_time = 0.0
            yield conn
    except Exception as e:
        _last_db_failure_time = time.time()
        raise e


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
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
    try:
        client = get_redis()
        return client.ping()
    except Exception as e:
        logger.debug("redis_health_check_failed", error=str(e))
        return False


check_db = check_db_health
check_redis = check_redis_health
