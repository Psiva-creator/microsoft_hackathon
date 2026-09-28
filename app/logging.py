import logging
import sys
from typing import Any

import structlog


def setup_logging(
    log_level: str | None = None,
    log_format: str | None = None,
) -> None:
    """Configures structured logging supporting both JSON and human-readable console formats.

    Args:
        log_level: Logging level (e.g. "DEBUG", "INFO", "WARNING"). If omitted,
                   resolved from Settings.LOG_LEVEL.
        log_format: Output format ("json" or "console"). If omitted,
                    resolved from Settings.LOG_FORMAT.
    """
    if log_level is None or log_format is None:
        try:
            from app.config import get_settings

            settings = get_settings()
            if log_level is None:
                log_level = getattr(settings, "LOG_LEVEL", "INFO")
            if log_format is None:
                log_format = getattr(settings, "LOG_FORMAT", "console")
        except Exception:
            if log_level is None:
                log_level = "INFO"
            if log_format is None:
                log_format = "console"

    level_num = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level_num,
        force=True,
    )

    format_choice = (log_format or "console").lower()
    renderer: Any
    if format_choice == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())

    structlog.reset_defaults()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level_num),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)

