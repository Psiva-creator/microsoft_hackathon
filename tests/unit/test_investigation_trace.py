from app.agent.investigate import get_investigation_trace, investigate


def test_investigation_trace_generation():
    analysis = investigate(scenario_name="A_pool_exhaustion")
    trace = get_investigation_trace(analysis)

    assert "summary" in trace
    assert trace["hypotheses_count"] >= 1
    assert "pool" in trace["primary_cause"].lower() or "connection" in trace["primary_cause"].lower()
    assert trace["requires_human_approval"] is True
    assert len(trace["human_decision_items"]) > 0
    assert isinstance(trace["dropped_citations"], list)
