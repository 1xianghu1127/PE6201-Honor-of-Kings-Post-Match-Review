"""Run the deterministic baseline over the reviewed 40-case dataset."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baseline.rules import generate_baseline_review
from evaluation.metrics import scoring_columns
from guardrails.validators import validate_review_structure


DATASET = ROOT / "confirmed_evaluation_dataset.json"
RESULT_DIR = ROOT / "evaluation" / "results"


def main() -> None:
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    results = []
    score_rows = []
    for case in dataset["cases"]:
        output = generate_baseline_review(case["input"])
        expected = case["ground_truth"]["abstention_level"]
        structure_errors = validate_review_structure(output, expected)
        results.append(
            {
                "case_id": case["case_id"],
                "input": case["input"],
                "expected": case["ground_truth"],
                "output": output,
                "automatic_checks": {
                    "structure_valid": not structure_errors,
                    "structure_errors": structure_errors,
                    "abstention_correct": output["abstention_level"] == expected,
                },
            }
        )
        score_rows.append(
            {
                "case_id": case["case_id"],
                "system": "rule_baseline",
                "expected_abstention": expected,
                "actual_abstention": output["abstention_level"],
                "data_consistency": "",
                "grounding_correctness": "n/a",
                "actionability": "",
                "abstention_correct": "yes" if output["abstention_level"] == expected else "no",
                "reviewer_notes": "",
            }
        )

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "baseline_outputs.json"
    output_path.write_text(
        json.dumps(
            {
                "system": "rule_baseline",
                "run_at": datetime.now(timezone.utc).isoformat(),
                "dataset_version": dataset["version"],
                "case_count": len(results),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    score_path = RESULT_DIR / "baseline_human_scoring.csv"
    with score_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=scoring_columns())
        writer.writeheader()
        writer.writerows(score_rows)
    print(f"Saved {len(results)} baseline outputs to {output_path}")
    print(f"Saved human scoring template to {score_path}")


if __name__ == "__main__":
    main()
