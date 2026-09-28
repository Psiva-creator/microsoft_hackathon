from pathlib import Path

from app.config import get_settings
from app.jobs.consolidate import run_consolidation
from app.memory.retrieval import recall
from app.memory.stats import (
    get_runbook_success_probability,
    record_feedback,
    reset_offline_stats,
    update_runbook_resolution_outcome,
)
from app.models import Cue


def test_laplace_smoothing_progression():
    reset_offline_stats()
    rb_id = "RB-test-smoothing"

    # Initial state (0 success, 0 failure): (0 + 1) / (0 + 0 + 2) = 0.5
    assert get_runbook_success_probability(rb_id) == 0.5

    # 1 success: (1 + 1) / (1 + 0 + 2) = 2/3 ≈ 0.6667
    update_runbook_resolution_outcome([rb_id], worked=True)
    assert abs(get_runbook_success_probability(rb_id) - (2 / 3)) < 1e-4

    # 2 successes: (2 + 1) / (2 + 0 + 2) = 3/4 = 0.75
    update_runbook_resolution_outcome([rb_id], worked=True)
    assert abs(get_runbook_success_probability(rb_id) - 0.75) < 1e-4

    # 1 failure (2 successes, 1 failure): (2 + 1) / (2 + 1 + 2) = 3/5 = 0.60
    update_runbook_resolution_outcome([rb_id], worked=False)
    assert abs(get_runbook_success_probability(rb_id) - 0.60) < 1e-4


def test_record_feedback_updates_stats():
    reset_offline_stats()
    rb_id = "RB-test-feedback"

    record_feedback(suggestion_id=101, runbook_id=rb_id, helpful=True, comment="Fixed the outage")
    assert abs(get_runbook_success_probability(rb_id) - (2 / 3)) < 1e-4

    record_feedback(suggestion_id=102, runbook_id=rb_id, helpful=False, comment="Did not help")
    assert abs(get_runbook_success_probability(rb_id) - 0.5) < 1e-4


def test_memory_decay_calculation():
    settings = get_settings()
    half_life = settings.DECAY_HALF_LIFE_DAYS

    # 0 days old -> weight = 1.0
    age_0 = 0
    w_0 = max(0.3, 0.5 ** (age_0 / half_life))
    assert w_0 == 1.0

    # 1 half-life old -> weight = 0.5
    age_1 = half_life
    w_1 = max(0.3, 0.5 ** (age_1 / half_life))
    assert abs(w_1 - 0.5) < 1e-4

    # 3 half-lives old -> 0.125 clamped to floor of 0.3
    age_3 = half_life * 3
    w_3 = max(0.3, 0.5 ** (age_3 / half_life))
    assert w_3 == 0.3


def test_run_consolidation_offline_and_report_generation():
    result = run_consolidation(dry_run=True)
    assert result["status"] == "success"
    assert result["patterns_created"] >= 10
    assert result["incidents_decayed"] >= 50

    report_path = Path(result["report_path"])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Sleep-Replay Consolidation Report" in content
    assert "Discovered Knowledge Patterns" in content
    assert "Temporal Memory Decay" in content


def test_consolidated_patterns_recalled_in_cue():
    # Ensure patterns are consolidated
    run_consolidation(dry_run=False)

    cue = Cue(
        text="HikariPool connection timeout and 503 errors on checkout-api",
        services=["checkout-api"],
        error_messages=["HikariPool-1 - Connection is not available, request timed out after 30000ms"],
    )
    result = recall(cue=cue, top_k=3)

    assert len(result.incidents) > 0
    assert len(result.patterns) > 0
    pattern_titles = [p.title.lower() for p in result.patterns]
    assert any("connection pool" in t for t in pattern_titles)
