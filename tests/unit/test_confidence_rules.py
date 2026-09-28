from app.agent.investigate import _enforce_code_confidence_rules
from app.models import Analysis, Hypothesis


def test_confidence_capping_without_live_evidence():
    analysis = Analysis(
        summary="Test analysis",
        precedent_strength="strong",
        hypotheses=[
            Hypothesis(
                rank=1,
                cause="Possible pool leak",
                confidence="high",
                recommended_steps=["Check logs"],
            )
        ],
        what_to_check_next=[],
        needs_human_decision=[],
    )

    # When live_evidence_found is False, confidence must be capped at medium
    updated = _enforce_code_confidence_rules(
        analysis, best_precedent_score=0.85, live_evidence_found=False
    )
    assert updated.hypotheses[0].confidence == "medium"


def test_weak_precedent_sets_strength_none():
    analysis = Analysis(
        summary="Novel failure",
        precedent_strength="strong",
        hypotheses=[
            Hypothesis(
                rank=1,
                cause="Unknown hardware glitch",
                confidence="medium",
                recommended_steps=["Reboot"],
            )
        ],
        what_to_check_next=[],
        needs_human_decision=[],
    )

    # When best_precedent_score < 0.35, precedent_strength must become 'none'
    updated = _enforce_code_confidence_rules(
        analysis, best_precedent_score=0.20, live_evidence_found=True
    )
    assert updated.precedent_strength == "none"
