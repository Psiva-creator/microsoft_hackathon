from app.models import Analysis, Hypothesis, SimilarIncident
from app.slack.bot import build_analysis_blocks, build_resolve_modal, create_slack_app


def test_build_analysis_blocks():
    analysis = Analysis(
        summary="Database pool exhaustion in checkout-api",
        precedent_strength="strong",
        hypotheses=[
            Hypothesis(
                rank=1,
                cause="HikariPool leak in OrderClient.py",
                confidence="high",
                evidence_for=["HikariPool timeout logs", "Recent deploy v212"],
                evidence_against=[],
                recommended_steps=["Rollback deploy v212", "Restart checkout-api pods"],
                runbook_id="RB-db-pool-exhaustion",
                similar_incidents=[
                    SimilarIncident(
                        id="INC-0007",
                        why_similar="Same service and HikariPool error",
                        differences="Version was v210 previously",
                    )
                ],
            )
        ],
        needs_human_decision=["Rollback deploy requires engineering approval"],
        what_to_check_next=["Active Postgres connections via pg_stat_activity"],
    )

    blocks = build_analysis_blocks(analysis, live_id="LIVE-20260928-001")
    assert len(blocks) >= 5

    # Check header
    header_block = blocks[0]
    assert header_block["type"] == "header"
    assert "LIVE-20260928-001" in header_block["text"]["text"]

    # Check confidence badge
    summary_block = blocks[1]
    assert "🟢 *HIGH CONFIDENCE*" in summary_block["text"]["text"]

    # Check actions block
    actions_block = blocks[-1]
    assert actions_block["type"] == "actions"
    action_ids = [btn["action_id"] for btn in actions_block["elements"]]
    assert "feedback_helpful" in action_ids
    assert "feedback_unhelpful" in action_ids
    assert "reinvestigate" in action_ids
    assert "mark_resolved" in action_ids


def test_build_resolve_modal():
    modal = build_resolve_modal(live_id="LIVE-TEST-001")
    assert modal["type"] == "modal"
    assert modal["callback_id"] == "resolve_incident_modal"
    assert modal["private_metadata"] == "LIVE-TEST-001"

    block_ids = [b["block_id"] for b in modal["blocks"]]
    assert "root_cause_block" in block_ids
    assert "steps_block" in block_ids
    assert "worked_block" in block_ids


def test_create_slack_app():
    app = create_slack_app()
    assert app is not None
