from app.code_memory.pr_check import check_pr


def test_pr_check_known_risky_file():
    # OrderClient.py is tied to past incident INC-0007
    result = check_pr(files=["services/checkout/OrderClient.py"])
    assert result["risk_level"] in ("high", "medium", "low")
    matches = result["matched_incidents"]
    assert len(matches) > 0
    assert any("INC-0007" in m["incident_id"] for m in matches)
    assert any(m["role"] in ("root_cause", "involved") for m in matches)
    assert len(result["recommendations"]) > 0


def test_pr_check_safe_new_file():
    result = check_pr(files=["docs/new_documentation_file.md"])
    assert result["risk_level"] == "low"
    assert len(result["matched_incidents"]) == 0
    assert len(result["recommendations"]) == 0
