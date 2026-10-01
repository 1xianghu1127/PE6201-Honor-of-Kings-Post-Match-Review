"""Run the paid RAG evaluation and create its human-scoring template."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.metrics import scoring_columns
from core.openrouter_client import DEFAULT_TEXT_MODEL, prompt_for_openrouter_api_key
from rag.generation import generate_rag_review
from rag.retrieval import KnowledgeRetriever


DATASET = ROOT / "confirmed_evaluation_dataset.json"
RESULT_DIR = ROOT / "evaluation" / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the reviewed 40-case RAG evaluation.")
    parser.add_argument("--confirm-api-spend", action="store_true", help="Required before paid API calls are made.")
    parser.add_argument("--limit", type=int, default=None, help="Optional smoke-test limit before the full run.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.confirm_api_spend:
        raise SystemExit("Refusing to call OpenRouter without --confirm-api-spend.")
    try:
        prompt_for_openrouter_api_key()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = dataset["cases"][: args.limit] if args.limit else dataset["cases"]
    retriever = KnowledgeRetriever()
    results = []
    score_rows = []
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "rag_outputs.json"

    for index, case in enumerate(cases, start=1):
        output = generate_rag_review(case["input"], retriever=retriever, model=DEFAULT_TEXT_MODEL)
        expected = case["ground_truth"]["abstention_level"]
        results.append(
            {
                "case_id": case["case_id"],
                "input": case["input"],
                "expected": case["ground_truth"],
                "output": output,
            }
        )
        score_rows.append(
            {
                "case_id": case["case_id"],
                "system": "rag_llm",
                "expected_abstention": expected,
                "actual_abstention": output["abstention_level"],
                "data_consistency": "",
                "grounding_correctness": "",
                "actionability": "",
                "abstention_correct": "yes" if output["abstention_level"] == expected else "no",
                "reviewer_notes": "",
            }
        )
        output_path.write_text(
            json.dumps(
                {
                    "system": "rag_llm",
                    "run_at": datetime.now(timezone.utc).isoformat(),
                    "dataset_version": dataset["version"],
                    "completed_cases": index,
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Completed {index}/{len(cases)}: {case['case_id']}")

    score_path = RESULT_DIR / "rag_human_scoring.csv"
    with score_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=scoring_columns())
        writer.writeheader()
        writer.writerows(score_rows)
    print(f"Saved RAG outputs to {output_path}")
    print(f"Saved human scoring template to {score_path}")


if __name__ == "__main__":
    main()
