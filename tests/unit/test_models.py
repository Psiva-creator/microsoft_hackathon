import pytest
from pydantic import ValidationError

from app.models import (
    Analysis,
    Cue,
    Hypothesis,
    LiveContext,
    LiveEvent,
    SimilarIncident,
)


def test_valid_cue() -> None:
    # Minimal required fields
    cue = Cue(text="checkout-api 503 latency spike")
    assert cue.text == "checkout-api 503 latency spike"
    assert cue.error_messages == []
    assert cue.stack_traces == []
    assert cue.services == []
    assert cue.files == []
    assert cue.commit_refs == []
    assert cue.trigger_type is None
    assert cue.exclude_ids == []

    # Full fields
    full_cue = Cue(
        text="database failure",
        error_messages=["Connection refused"],
        stack_traces=["Traceback: ..."],
        services=["checkout-api", "postgres-primary"],
        files=["OrderClient.py"],
        commit_refs=["abc1234"],
        trigger_type="bad_deploy",
        exclude_ids=["INC-0001"],
    )
    assert len(full_cue.services) == 2
    assert full_cue.trigger_type == "bad_deploy"


def test_valid_hypothesis() -> None:
    sim = SimilarIncident(
        id="INC-0007",
        why_similar="HikariPool exhaustion after deploy",
        differences="Different service version and error message details",
    )
    hyp = Hypothesis(
        rank=1,
        cause="HikariPool connection leak in OrderClient",
        confidence="high",
        evidence_for=["HikariPool timeout in logs", "Deploy v212 occurred 10m ago"],
        evidence_against=["No CPU saturation on DB"],
        similar_incidents=[sim],
        recommended_steps=["Rollback deploy v212", "Restart checkout-api"],
        runbook_id="RB-db-pool-exhaustion",
        risk_notes="Requires approval before rollback",
    )
    assert hyp.rank == 1
    assert hyp.confidence == "high"
    assert len(hyp.similar_incidents) == 1
    assert hyp.similar_incidents[0].id == "INC-0007"
    assert hyp.runbook_id == "RB-db-pool-exhaustion"


def test_valid_analysis() -> None:
    hyp = Hypothesis(
        rank=1,
        cause="TLS certificate expired",
        confidence="medium",
        recommended_steps=["Renew certificate"],
    )
    analysis = Analysis(
        summary="TLS handshake errors observed on payments gateway",
        precedent_strength="strong",
        hypotheses=[hyp],
        what_to_check_next=["Check cert renewal cron status"],
        needs_human_decision=["Rotate production TLS cert"],
        dropped_citations=[],
    )
    assert analysis.precedent_strength == "strong"
    assert len(analysis.hypotheses) == 1
    assert len(analysis.needs_human_decision) == 1


def test_valid_live_context() -> None:
    event = LiveEvent(
        ts="2026-09-28T22:00:00Z",
        kind="alert",
        source="alertmanager",
        text="Firing: HighErrorRate on checkout-api",
        data={"metric": 503, "rate": 0.12},
    )
    ctx = LiveContext(
        id="LIVE-20260928-001",
        title="Elevated 503 errors on checkout-api",
        services=["checkout-api"],
        events=[event],
    )
    assert ctx.id == "LIVE-20260928-001"
    assert ctx.title == "Elevated 503 errors on checkout-api"
    assert len(ctx.events) == 1
    assert ctx.events[0].kind == "alert"
    assert ctx.hypotheses is None


def test_required_field_validation() -> None:
    # Cue requires text
    with pytest.raises(ValidationError) as exc:
        Cue.model_validate({})
    assert "text" in str(exc.value)

    # Hypothesis requires rank, cause, confidence
    with pytest.raises(ValidationError) as exc:
        Hypothesis.model_validate({"rank": 1})
    assert "cause" in str(exc.value)

    # Analysis requires summary, precedent_strength
    with pytest.raises(ValidationError) as exc:
        Analysis.model_validate({"summary": "test"})
    assert "precedent_strength" in str(exc.value)

    # LiveContext requires id, title
    with pytest.raises(ValidationError) as exc:
        LiveContext.model_validate({"id": "LIVE-001"})
    assert "title" in str(exc.value)

    # SimilarIncident requires id, why_similar, differences
    with pytest.raises(ValidationError) as exc:
        SimilarIncident.model_validate({"id": "INC-001"})
    assert "why_similar" in str(exc.value)

    # LiveEvent requires ts, kind, source, text
    with pytest.raises(ValidationError) as exc:
        LiveEvent.model_validate({"ts": "2026-01-01T00:00:00Z"})
    assert "kind" in str(exc.value)


def test_invalid_type_and_enum_validation() -> None:
    # Hypothesis confidence must be low, medium, or high
    with pytest.raises(ValidationError):
        Hypothesis(rank=1, cause="cause", confidence="invalid_confidence")  # type: ignore[arg-type]

    # Analysis precedent_strength must be strong, partial, or none
    with pytest.raises(ValidationError):
        Analysis(summary="summary", precedent_strength="super_strong")  # type: ignore[arg-type]

    # LiveEvent kind must be one of the permitted literals
    with pytest.raises(ValidationError):
        LiveEvent(
            ts="2026-01-01",
            kind="not_a_valid_kind",  # type: ignore[arg-type]
            source="test",
            text="hello",
        )


def test_model_serialization_and_roundtrip() -> None:
    hyp = Hypothesis(
        rank=1,
        cause="Cache stampede",
        confidence="low",
        evidence_for=["High redis CPU"],
        recommended_steps=["Flush or warm keys"],
        runbook_id="RB-cache-stampede",
    )
    analysis = Analysis(
        summary="Cache latency degradation",
        precedent_strength="partial",
        hypotheses=[hyp],
        what_to_check_next=["Check TTL distribution"],
        needs_human_decision=["Restart redis"],
    )

    # Test model_dump dict serialization
    dumped = analysis.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["summary"] == "Cache latency degradation"
    assert dumped["precedent_strength"] == "partial"
    assert dumped["hypotheses"][0]["cause"] == "Cache stampede"

    # Test model_dump_json & model_validate_json roundtrip
    json_str = analysis.model_dump_json()
    assert isinstance(json_str, str)
    restored = Analysis.model_validate_json(json_str)
    assert restored.summary == analysis.summary
    assert restored.hypotheses[0].cause == hyp.cause
    assert restored == analysis
