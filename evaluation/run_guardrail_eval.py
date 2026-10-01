"""Execute the separate validation and semantic guardrail checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from guardrails.validators import validate_match_data
from guardrails.review_consistency import validate_review_consistency


def main() -> None:
    suite = json.loads((ROOT / "guardrail_cases.json").read_text(encoding="utf-8"))
    results = []
    for case in suite["cases"]:
        if case["type"] == "structured":
            actual = validate_match_data(case["input"]).level
            results.append({"id": case["id"], "expected": case["expected"], "actual": actual, "passed": actual == case["expected"]})
            continue
        if case["type"] == "semantic":
            errors = validate_review_consistency(case["review"], case["input"])
            actual = "reject_output" if errors else "accept_output"
            results.append({
                "id": case["id"],
                "expected": case["expected"],
                "actual": actual,
                "passed": actual == case["expected"],
                "detected_issues": errors,
            })
            continue
        else:
            results.append({"id": case["id"], "status": "manual_or_integration_test", "passed": None})
            continue
    automatic = [item for item in results if item["passed"] is not None]
    summary = {
        "automatic_passed": sum(item["passed"] for item in automatic),
        "automatic_total": len(automatic),
        "manual_or_integration_total": sum(item["passed"] is None for item in results),
        "results": results,
    }
    output = ROOT / "evaluation" / "results" / "guardrail_results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
