from app.memory.retrieval import compute_relevance_breakdown
from app.models import ScoredIncident


def test_compute_relevance_breakdown():
    incident = ScoredIncident(
        id="INC-0007",
        title="Database pool exhaustion",
        summary="Pool exhaustion on checkout-api",
        root_cause="Leaked db connections",
        resolution_steps=["Restart pool"],
        runbook_ids=["RB-db-pool-exhaustion"],
        fix_worked=True,
        final=0.50,
        scores={"vec": 0.8, "fts": 0.5, "fp": 0.0, "svc": 0.4, "code": 0.0},
        matched_on=["vec", "fts"],
        flags=[],
    )
    breakdown = compute_relevance_breakdown(incident)
    assert "vec" in breakdown
    assert "fts" in breakdown
    assert breakdown["vec"] > breakdown["fts"]
    assert breakdown["fp"] == 0.0


def test_compute_relevance_breakdown_zero_score():
    incident = ScoredIncident(
        id="INC-0000",
        title="Zero score",
        summary="Zero score summary",
        root_cause="None",
        resolution_steps=[],
        runbook_ids=[],
        fix_worked=False,
        final=0.0,
        scores={"vec": 0.0, "fts": 0.0, "fp": 0.0, "svc": 0.0, "code": 0.0},
        matched_on=[],
        flags=[],
    )
    breakdown = compute_relevance_breakdown(incident)
    assert breakdown["vec"] == 0.0
    assert breakdown["fts"] == 0.0
