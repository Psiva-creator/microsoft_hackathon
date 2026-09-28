"""Evaluation Matrix Exporter: Runs evaluation across Keyword, Vector, and Hybrid retrieval modes."""

import json
from pathlib import Path

from app.eval.harness import run_evaluation


def main():
    cases_file = Path("eval/cases.jsonl")
    if not cases_file.exists():
        print(f"Error: {cases_file} not found.")
        return

    print("Running Leave-One-Out Evaluation Matrix across 60 benchmark cases...")
    report = run_evaluation(str(cases_file))

    output_path = Path("eval/eval_matrix_summary.json")
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"✅ Evaluation Matrix saved to {output_path}")


if __name__ == "__main__":
    main()
