import re
from typing import Literal

from pydantic import BaseModel, Field

from app.config import get_settings
from app.llm.client import get_llm_client
from app.llm.prompts import EXTRACTION_SYSTEM_PROMPT
from app.logging import get_logger

logger = get_logger(__name__)


class FileMention(BaseModel):
    path: str
    function: str = ""


class ExtractedIncident(BaseModel):
    title: str
    severity: Literal["sev1", "sev2", "sev3", "sev4", "unknown"] = "unknown"
    started_at: str | None = None
    resolved_at: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    error_messages: list[str] = Field(default_factory=list)
    stack_traces: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    trigger_type: str | None = "unknown"
    trigger_ref: str | None = None
    root_cause: str | None = None
    root_cause_category: str = "unknown"
    resolution_steps: list[str] = Field(default_factory=list)
    runbooks_mentioned: list[str] = Field(default_factory=list)
    fix_worked: bool | None = True
    lessons: str | None = None
    files_mentioned: list[FileMention] = Field(default_factory=list)
    extraction_confidence: Literal["low", "medium", "high"] = "medium"
    missing_fields: list[str] = Field(default_factory=list)


RECORD_INCIDENT_TOOL = {
    "name": "record_incident",
    "description": "Records structured incident data extracted from engineering text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "severity": {"type": "string", "enum": ["sev1", "sev2", "sev3", "sev4", "unknown"]},
            "started_at": {"type": "string"},
            "resolved_at": {"type": "string"},
            "symptoms": {"type": "array", "items": {"type": "string"}},
            "error_messages": {"type": "array", "items": {"type": "string"}},
            "stack_traces": {"type": "array", "items": {"type": "string"}},
            "services": {"type": "array", "items": {"type": "string"}},
            "trigger_type": {"type": "string"},
            "trigger_ref": {"type": "string"},
            "root_cause": {"type": "string"},
            "root_cause_category": {
                "type": "string",
                "enum": [
                    "resource_exhaustion",
                    "connection_pool",
                    "memory_leak",
                    "bad_deploy",
                    "config_change",
                    "dependency_failure",
                    "network_dns",
                    "certificate_expiry",
                    "disk_full",
                    "capacity_traffic",
                    "data_corruption",
                    "cache_issue",
                    "queue_backlog",
                    "security",
                    "human_error",
                    "unknown",
                ],
            },
            "resolution_steps": {"type": "array", "items": {"type": "string"}},
            "runbooks_mentioned": {"type": "array", "items": {"type": "string"}},
            "fix_worked": {"type": "boolean"},
            "lessons": {"type": "string"},
            "files_mentioned": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "function": {"type": "string"},
                    },
                    "required": ["path"],
                },
            },
            "extraction_confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "missing_fields": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "root_cause_category", "extraction_confidence"],
    },
}


def _heuristic_extract(text: str, source_id: str) -> ExtractedIncident:
    """Fast deterministic extractor used when LLM is unavailable or for synthetic seed ingestion."""
    lines = text.strip().splitlines()
    first_line = lines[0] if lines else "Incident"
    title = re.sub(r"^[#\s\-*]+", "", first_line).strip()

    services: set[str] = set()
    for svc in [
        "web-frontend",
        "checkout-api",
        "payments-gateway",
        "orders-service",
        "inventory-service",
        "postgres-primary",
        "redis-cache",
        "kafka-orders",
        "auth-service",
        "notification-worker",
    ]:
        if svc in text.lower():
            services.add(svc)

    category = "unknown"
    for cat in [
        "connection_pool",
        "bad_deploy",
        "certificate_expiry",
        "disk_full",
        "network_dns",
        "memory_leak",
        "cache_issue",
        "queue_backlog",
        "capacity_traffic",
        "dependency_failure",
    ]:
        if cat in text.lower() or cat in source_id.lower():
            category = cat
            break

    runbooks: list[str] = re.findall(r"\b(RB-[a-zA-Z0-9_\-]+)\b", text)
    files: list[FileMention] = []
    file_matches = re.findall(r"([a-zA-Z0-9_\-/\\]+\.(?:py|java|go|js|ts|yaml|yml))", text)
    for fm in set(file_matches):
        if not fm.startswith("http"):
            files.append(FileMention(path=fm))

    error_messages: list[str] = []
    symptoms: list[str] = []
    resolution_steps: list[str] = []
    root_cause = "Underlying cause identified in log/system analysis."

    for line in lines:
        l_str = line.strip()
        if (
            "HikariPool" in l_str
            or "x509:" in l_str
            or "lookup" in l_str
            or "error" in l_str.lower()
        ):
            error_messages.append(l_str[:200])
        if l_str.startswith("- ") or l_str.startswith("* "):
            symptoms.append(l_str[2:])
        if re.match(r"^\d+\.\s+", l_str):
            resolution_steps.append(re.sub(r"^\d+\.\s+", "", l_str))
        if "root cause" in l_str.lower():
            root_cause = l_str

    return ExtractedIncident(
        title=title or f"Incident from {source_id}",
        services=list(services),
        root_cause=root_cause,
        root_cause_category=category,
        symptoms=symptoms[:5],
        error_messages=error_messages[:3],
        resolution_steps=resolution_steps[:5],
        runbooks_mentioned=list(set(runbooks)),
        files_mentioned=files[:5],
        extraction_confidence="high" if category != "unknown" else "medium",
    )


def extract_incident(text: str, source_id: str = "") -> ExtractedIncident:
    """Extracts structured incident data from raw engineering text."""
    settings = get_settings()

    if not settings.ANTHROPIC_API_KEY:
        # Fallback to heuristic parser if API key is not configured
        return _heuristic_extract(text, source_id)

    try:
        client = get_llm_client()
        raw = client.extract_structured(
            system=EXTRACTION_SYSTEM_PROMPT,
            user=f"Extract this document (ID: {source_id}):\n\n{text}",
            tool_schema=RECORD_INCIDENT_TOOL,
            model=settings.LLM_MODEL_FAST,
        )
        return ExtractedIncident(**raw)
    except Exception as e:
        logger.warning("llm_extraction_failed_using_heuristic", error=str(e), source_id=source_id)
        return _heuristic_extract(text, source_id)
