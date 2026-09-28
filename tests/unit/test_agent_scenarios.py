from app.agent.investigate import investigate


def test_scenario_a_pool_exhaustion():
    analysis = investigate(scenario_name="A_pool_exhaustion")
    assert analysis.precedent_strength in ("strong", "partial")
    assert len(analysis.hypotheses) >= 1
    top_hyp = analysis.hypotheses[0]
    assert "pool" in top_hyp.cause.lower() or "connection" in top_hyp.cause.lower()
    # Check that destructive actions are placed in needs_human_decision
    assert len(analysis.needs_human_decision) > 0


def test_scenario_b_cert_expiry():
    analysis = investigate(scenario_name="B_cert_expiry")
    top_hyp = analysis.hypotheses[0]
    assert "cert" in top_hyp.cause.lower() or "tls" in top_hyp.cause.lower()
    assert top_hyp.runbook_id == "RB-cert-expiry"


def test_scenario_c_novel():
    analysis = investigate(scenario_name="C_novel")
    # For a completely novel failure, precedent strength must be 'none'
    assert analysis.precedent_strength == "none"
    assert len(analysis.hypotheses[0].similar_incidents) == 0


def test_scenario_d_lookalike_dns():
    analysis = investigate(scenario_name="D_lookalike_dns")
    top_hyp = analysis.hypotheses[0]
    assert "dns" in top_hyp.cause.lower()
    assert top_hyp.runbook_id == "RB-dns-resolution-failure"
    # Differences must mention that pool exhaustion is ruled out
    if top_hyp.similar_incidents:
        diffs = top_hyp.similar_incidents[0].differences.lower()
        assert "dns" in diffs or "host" in diffs or "pool" in diffs
