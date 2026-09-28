import io
import json
import sys

from app.config import get_settings
from app.logging import get_logger, setup_logging


def test_logging_configuration_defaults() -> None:
    settings = get_settings()
    assert hasattr(settings, "LOG_LEVEL")
    assert hasattr(settings, "LOG_FORMAT")
    assert settings.LOG_LEVEL == "INFO"
    assert settings.LOG_FORMAT in ("console", "json")


def test_json_logging_output() -> None:
    buffer = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buffer
        setup_logging(log_level="INFO", log_format="json")
        logger = get_logger("test_json")
        logger.info("service_started", service="checkout-api", attempt=1)
    finally:
        sys.stdout = old_stdout

    output = buffer.getvalue().strip()
    assert output, "Expected log output in JSON mode"

    # Verify JSON structure
    data = json.loads(output)
    assert data["event"] == "service_started"
    assert data["service"] == "checkout-api"
    assert data["attempt"] == 1
    assert data["level"] == "info"
    assert "timestamp" in data


def test_console_logging_output() -> None:
    buffer = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buffer
        setup_logging(log_level="INFO", log_format="console")
        logger = get_logger("test_console")
        logger.info("cache_hit", key="inc:123", latency_ms=4.2)
    finally:
        sys.stdout = old_stdout

    output = buffer.getvalue().strip()
    assert output, "Expected log output in console mode"
    assert "cache_hit" in output
    assert "key=" in output
    assert "latency_ms=" in output


def test_log_level_filtering() -> None:
    buffer = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buffer
        setup_logging(log_level="WARNING", log_format="json")
        logger = get_logger("test_filter")
        logger.info("should_be_filtered")
        logger.warning("important_alert", metric="cpu_high")
    finally:
        sys.stdout = old_stdout

    output = buffer.getvalue().strip()
    assert "should_be_filtered" not in output
    assert "important_alert" in output
    data = json.loads(output)
    assert data["level"] == "warning"
    assert data["metric"] == "cpu_high"


def test_exception_logging() -> None:
    buffer = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buffer
        setup_logging(log_level="ERROR", log_format="json")
        logger = get_logger("test_exc")
        try:
            raise ValueError("simulated_failure")
        except ValueError:
            logger.exception("unhandled_error", incident_id="INC-0001")
    finally:
        sys.stdout = old_stdout

    output = buffer.getvalue().strip()
    data = json.loads(output)
    assert data["event"] == "unhandled_error"
    assert data["incident_id"] == "INC-0001"
    assert data["level"] == "error"
    assert "exception" in data or "exc_info" in data
