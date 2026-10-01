"""Summarise human-scoring CSV files without merging separate quality checks."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


YES = {"yes", "y", "1", "true", "pass"}
NO = {"no", "n", "0", "false", "fail"}


def _normalise(value: str | None) -> str | None:
    if value is None:
        return None
    item = value.strip().lower()
    if item in YES:
        return "yes"
    if item in NO:
        return "no"
    if item in {"n/a", "na", "not applicable"}:
        return "n/a"
    return None


def summarise_scoring_csv(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    metrics = {
        "match_data_consistency": "data_consistency",
        "grounding_correctness": "grounding_correctness",
        "actionability": "actionability",
        "correct_abstention": "abstention_correct",
    }
    summary: dict[str, Any] = {"total_cases": len(rows)}
    for label, column in metrics.items():
        values = [_normalise(row.get(column)) for row in rows]
        applicable = [value for value in values if value in {"yes", "no"}]
        summary[label] = {
            "passed": sum(value == "yes" for value in applicable),
            "applicable": len(applicable),
            "unscored": sum(value is None for value in values),
            "not_applicable": sum(value == "n/a" for value in values),
        }
    return summary


def scoring_columns() -> list[str]:
    return [
        "case_id",
        "system",
        "expected_abstention",
        "actual_abstention",
        "data_consistency",
        "grounding_correctness",
        "actionability",
        "abstention_correct",
        "reviewer_notes",
    ]
