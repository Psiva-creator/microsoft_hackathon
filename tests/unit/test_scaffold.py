from pathlib import Path

from app.config import get_settings


def test_settings_loaded() -> None:
    settings = get_settings()
    assert settings.EMBED_DIM == 384
    assert settings.ALLOW_ACTIONS is False
    assert settings.DATABASE_URL.startswith("postgresql://")
    assert settings.REDIS_URL.startswith("redis://")
    assert settings.LOG_LEVEL == "INFO"
    assert settings.LOG_FORMAT in ("console", "json")


def test_scaffolding_files_exist() -> None:
    required_files = [
        "pyproject.toml",
        "Dockerfile",
        "docker-compose.yml",
        "Makefile",
        ".env.example",
        ".github/workflows/ci.yml",
    ]
    for filename in required_files:
        path = Path(filename)
        assert path.exists(), f"Required scaffolding file missing: {filename}"
        assert path.stat().st_size > 0, f"Scaffolding file is empty: {filename}"


def test_pyproject_configuration() -> None:
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "incident-agent"' in pyproject_text
    assert 'requires-python = ">=3.12"' in pyproject_text
    assert 'cli = "app.cli:app"' in pyproject_text
    assert "fastapi" in pyproject_text
    assert "pydantic" in pyproject_text
    assert "structlog" in pyproject_text
    assert "pytest" in pyproject_text
    assert "ruff" in pyproject_text


def test_dockerfile_configuration() -> None:
    dockerfile_text = Path("Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in dockerfile_text
    assert "uv" in dockerfile_text
    assert "EXPOSE 8000" in dockerfile_text
    assert "uvicorn" in dockerfile_text


def test_docker_compose_services() -> None:
    compose_text = Path("docker-compose.yml").read_text(encoding="utf-8")
    required_services = ["db:", "redis:", "api:", "slackbot:", "worker:"]
    for svc in required_services:
        assert svc in compose_text, f"Missing service in docker-compose.yml: {svc}"
    assert "pgvector/pgvector:pg16" in compose_text
    assert "redis:7" in compose_text


def test_makefile_targets() -> None:
    makefile_text = Path("Makefile").read_text(encoding="utf-8")
    targets = ["install:", "up:", "down:", "test:", "lint:", "seed:", "eval:", "consolidate:"]
    for target in targets:
        assert target in makefile_text, f"Missing Makefile target: {target}"


def test_ci_workflow_steps() -> None:
    ci_text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "actions/checkout@v4" in ci_text
    assert 'python-version: "3.12"' in ci_text
    assert "ruff check" in ci_text
    assert "pytest" in ci_text
    assert "cli eval" in ci_text
