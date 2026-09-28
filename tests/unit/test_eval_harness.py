import json
import tempfile
from pathlib import Path

from app.eval.harness import evaluate_mode, load_cases, run_evaluation


def test_load_cases():
    cases = load_cases("eval/cases.jsonl")
    assert len(cases) >= 10
    first = cases[0]
    assert "case_id" in first
    assert "source_incident_id" in first
    assert "cue" in first
    assert "expected_related_ids" in first
    assert "expected_root_cause_category" in first


def test_evaluate_mode_keyword():
    cases = load_cases("eval/cases.jsonl")[:5]
    res = evaluate_mode(cases, mode="keyword")
    assert res["mode"] == "keyword"
    assert res["sample_count"] == 5
    assert 0.0 <= res["recall_at_1"] <= 1.0
    assert 0.0 <= res["recall_at_3"] <= 1.0
    assert res["p50_latency_ms"] >= 0.0


def test_evaluate_mode_hybrid():
    cases = load_cases("eval/cases.jsonl")[:5]
    res = evaluate_mode(cases, mode="hybrid")
    assert res["mode"] == "hybrid"
    assert res["sample_count"] == 5
    assert 0.0 <= res["recall_at_3"] <= 1.0
    assert "p95_latency_ms" in res


def test_run_evaluation_creates_reports():
    with tempfile.TemporaryDirectory() as tmp_dir:
        cases_file = Path(tmp_dir) / "test_cases.jsonl"
        sample_cases = [
            {
                "case_id": "test_01",
                "source_incident_id": "INC-0007",
                "cue": {
                    "text": "checkout-api 503s after deploy",
                    "services": ["checkout-api"],
                    "error_messages": ["HikariPool connection timeout"],
                    "trigger_type": "deploy"
                },
                "expected_related_ids": ["INC-0011", "INC-0061"],
                "expected_root_cause_category": "connection_pool",
                "notes": "Test case"
            }
        ]
        with open(cases_file, "w", encoding="utf-8") as f:
            for c in sample_cases:
                f.write(json.dumps(c) + "\n")

        results = run_evaluation(cases_path=cases_file, output_dir=tmp_dir)
        assert "hybrid" in results
        assert "keyword" in results
        assert "vector" in results
        assert (Path(tmp_dir) / "report.md").exists()
        assert (Path(tmp_dir) / "report.json").exists()

        content = (Path(tmp_dir) / "report.md").read_text()
        assert "Comparative Retrieval Performance" in content
        assert "Hybrid (Full Brain Architecture)" in content
