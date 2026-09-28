from app.db import get_db
from app.logging import get_logger

logger = get_logger(__name__)


def get_runbook_success_probability(runbook_id: str) -> float:
    """Computes Laplace-smoothed success probability: (success + 1) / (success + failure + 2)."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT success_count, failure_count FROM runbooks WHERE id = %s;
                    """,
                    (runbook_id,),
                )
                row = cur.fetchone()
                if not row:
                    return 0.5
                s = row["success_count"]
                f = row["failure_count"]
                return (s + 1) / (s + f + 2)
    except Exception:
        return 0.5


def record_feedback(
    suggestion_id: int | None,
    runbook_id: str | None,
    helpful: bool,
    comment: str | None = None,
    user_ref: str | None = None,
) -> None:
    """Stores user feedback and updates runbook success/failure statistics."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO feedback (suggestion_id, runbook_id, helpful, comment, user_ref)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (suggestion_id, runbook_id, helpful, comment, user_ref),
                )
                if runbook_id:
                    if helpful:
                        cur.execute(
                            """
                            UPDATE runbooks
                            SET success_count = success_count + 1, updated_at = NOW()
                            WHERE id = %s;
                            """,
                            (runbook_id,),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE runbooks
                            SET failure_count = failure_count + 1, updated_at = NOW()
                            WHERE id = %s;
                            """,
                            (runbook_id,),
                        )
    except Exception as e:
        logger.debug("record_feedback_offline", error=str(e))


def update_runbook_resolution_stats(runbook_ids: list[str], worked: bool) -> None:
    """Updates success/failure counts on incident resolution."""
    if not runbook_ids:
        return
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                for rb_id in runbook_ids:
                    if worked:
                        cur.execute(
                            """
                            UPDATE runbooks
                            SET success_count = success_count + 1, updated_at = NOW()
                            WHERE id = %s;
                            """,
                            (rb_id,),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE runbooks
                            SET failure_count = failure_count + 1, updated_at = NOW()
                            WHERE id = %s;
                            """,
                            (rb_id,),
                        )
    except Exception as e:
        logger.debug("update_runbook_resolution_stats_offline", error=str(e))


update_runbook_resolution_outcome = update_runbook_resolution_stats
