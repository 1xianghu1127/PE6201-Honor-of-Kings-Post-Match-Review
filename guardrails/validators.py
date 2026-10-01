"""Validate match inputs and the required structure of generated reviews."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_ROLES = {"Marksman", "Mage", "Assassin", "Fighter", "Tank", "Support"}
ALLOWED_RESULTS = {"win", "loss"}
INTEGER_FIELDS = ("duration_min", "kills", "deaths", "assists", "gold", "damage_dealt", "damage_taken")
PERCENT_FIELDS = (
    "gold_share_pct",
    "damage_dealt_share_pct",
    "damage_taken_share_pct",
    "kill_participation_pct",
)
FULL_STOP_STATUSES = {
    "conflict",
    "invalid_values",
    "insufficient_data",
}


@dataclass
class ValidationResult:
    level: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)

    @property
    def can_analyse(self) -> bool:
        return self.level != "full"


def validate_match_data(data: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    missing: list[str] = []
    status = str(data.get("validation_status") or "valid")

    if status in FULL_STOP_STATUSES:
        errors.append(f"Input validation status is {status}.")

    role = data.get("role")
    if role is not None and role not in ALLOWED_ROLES:
        errors.append(f"Unsupported role: {role}.")
    result = data.get("match_result")
    if result is not None and result not in ALLOWED_RESULTS:
        errors.append(f"Unsupported match result: {result}.")

    for field_name in INTEGER_FIELDS:
        value = data.get(field_name)
        if value is None:
            missing.append(field_name)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{field_name} must be numeric.")
        elif value < 0:
            errors.append(f"{field_name} cannot be negative.")

    for field_name in PERCENT_FIELDS:
        value = data.get(field_name)
        if value is None:
            missing.append(field_name)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{field_name} must be numeric.")
        elif value < 0 or value > 100:
            errors.append(f"{field_name} must be between 0 and 100.")

    if not data.get("hero"):
        missing.append("hero")
    if not role:
        missing.append("role")
    if result is None:
        missing.append("match_result")

    core_stats = ("kills", "deaths", "assists", "gold_share_pct", "damage_dealt_share_pct")
    if all(data.get(name) is None for name in core_stats):
        errors.append("No usable performance statistics were provided.")

    if errors:
        return ValidationResult("full", errors, warnings, sorted(set(missing)))
    if missing:
        warnings.append("Some aspects cannot be judged because fields are missing.")
        return ValidationResult("partial", errors, warnings, sorted(set(missing)))
    return ValidationResult("none", errors, warnings, [])


def validate_review_structure(review: dict[str, Any], expected_level: str) -> list[str]:
    errors: list[str] = []
    required = ("what_went_well", "what_to_improve", "next_match_focus")
    for name in required:
        value = review.get(name)
        if not isinstance(value, list) or not value:
            errors.append(f"{name} must be a non-empty list.")
    actual_level = review.get("abstention_level")
    if actual_level != expected_level:
        errors.append(f"Expected abstention level {expected_level}, got {actual_level}.")
    if expected_level == "full":
        combined = " ".join(str(item) for name in required for item in review.get(name, []))
        if "信息不足" not in combined and "无法" not in combined and "确认" not in combined:
            errors.append("A full abstention must explain why analysis cannot proceed.")
    return errors
