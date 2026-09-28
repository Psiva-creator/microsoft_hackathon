from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Cue(BaseModel):
    text: str
    error_messages: list[str] = Field(default_factory=list)
    stack_traces: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    commit_refs: list[str] = Field(default_factory=list)
    trigger_type: str | None = None
    exclude_ids: list[str] = Field(default_factory=list)


class SimilarIncident(BaseModel):
    id: str
    why_similar: str
    differences: str


class Hypothesis(BaseModel):
    rank: int
    cause: str
    confidence: Literal["low", "medium", "high"]
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    similar_incidents: list[SimilarIncident] = Field(default_factory=list)
    recommended_steps: list[str] = Field(default_factory=list)
    runbook_id: str | None = None
    risk_notes: str | None = None


class Analysis(BaseModel):
    summary: str
    precedent_strength: Literal["strong", "partial", "none"]
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    what_to_check_next: list[str] = Field(default_factory=list)
    needs_human_decision: list[str] = Field(default_factory=list)
    dropped_citations: list[str] = Field(default_factory=list)


class ScoredIncident(BaseModel):
    id: str
    title: str
    final: float
    scores: dict[str, float] = Field(default_factory=dict)
    matched_on: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    summary: str
    runbook_ids: list[str] = Field(default_factory=list)
    fix_worked: bool | None = None
    root_cause: str | None = None
    resolution_steps: list[str] = Field(default_factory=list)


class Pattern(BaseModel):
    id: int | None = None
    title: str
    rule_text: str
    exceptions_text: str | None = None
    trigger_signals: list[str] = Field(default_factory=list)
    recommended_checks: list[str] = Field(default_factory=list)
    recommended_runbooks: list[str] = Field(default_factory=list)
    member_incident_ids: list[str] = Field(default_factory=list)
    confidence: float | None = None


class Runbook(BaseModel):
    id: str
    title: str
    body_md: str
    services: list[str] = Field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    updated_at: datetime | None = None


class RetrievalResult(BaseModel):
    incidents: list[ScoredIncident] = Field(default_factory=list)
    patterns: list[Pattern] = Field(default_factory=list)
    runbooks: list[Runbook] = Field(default_factory=list)


class LiveEvent(BaseModel):
    ts: str
    kind: Literal[
        "alert", "log", "deploy", "message", "tool_result", "suggestion", "note", "resolve"
    ]
    source: str
    text: str
    data: dict[str, Any] | None = None


class LiveContext(BaseModel):
    id: str
    title: str
    services: list[str] = Field(default_factory=list)
    events: list[LiveEvent] = Field(default_factory=list)
    hypotheses: list[Hypothesis] | None = None
