"""Convert match statistics into deterministic facts supplied to the model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


THRESHOLD_PATH = Path(__file__).resolve().parents[1] / "baseline" / "role_thresholds.json"
DAMAGE_ROLES = {"Marksman", "Mage", "Assassin"}


def _number(data: dict[str, Any], field: str) -> float | None:
    value = data.get(field)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def build_analytical_facts(data: dict[str, Any]) -> dict[str, Any]:
    """Turn raw values into auditable, role-aware facts for the LLM.

    These facts use the same pre-declared project thresholds as the baseline, but
    they do not write the review. The LLM remains responsible for the final advice.
    """
    config = json.loads(THRESHOLD_PATH.read_text(encoding="utf-8"))
    global_rules = config["global"]
    role = data.get("role")
    role_rules = config.get(role, {})
    judgements: list[str] = []

    deaths = _number(data, "deaths")
    gold_share = _number(data, "gold_share_pct")
    damage_share = _number(data, "damage_dealt_share_pct")
    taken_share = _number(data, "damage_taken_share_pct")
    participation = _number(data, "kill_participation_pct")

    if deaths is not None:
        if deaths <= 3:
            judgements.append(f"Deaths are low: {deaths:g} deaths (project low-death rule: <= 3); do not present deaths as a weakness.")
        elif deaths >= role_rules.get("high_deaths", global_rules["high_deaths"]):
            judgements.append(f"Deaths are high: {deaths:g} deaths (project high-death rule: >= {role_rules.get('high_deaths', global_rules['high_deaths'])}).")
        else:
            judgements.append(f"Deaths are neither low nor high under project thresholds: {deaths:g}.")

    if participation is not None:
        good_kp = role_rules.get("good_kill_participation_pct", global_rules["high_kill_participation_pct"])
        if participation < global_rules["low_kill_participation_pct"]:
            judgements.append(f"Kill participation is low: {participation:g}% (project low threshold: < {global_rules['low_kill_participation_pct']}%).")
        elif participation >= good_kp:
            judgements.append(f"Kill participation is good: {participation:g}% (role-aware good threshold: >= {good_kp}%).")
        else:
            judgements.append(f"Kill participation is in the middle range: {participation:g}%.")

    if role in DAMAGE_ROLES and damage_share is not None:
        good_damage = role_rules.get("good_damage_share_pct", 25)
        low_damage = role_rules.get("low_damage_share_pct", 15)
        if damage_share >= good_damage:
            judgements.append(f"Damage share is good for {role}: {damage_share:g}% (project threshold: >= {good_damage}%).")
        elif damage_share < low_damage:
            judgements.append(f"Damage share is low for {role}: {damage_share:g}% (project threshold: < {low_damage}%).")
        else:
            judgements.append(f"Damage share is in the middle range for {role}: {damage_share:g}%.")

    if taken_share is not None and role_rules.get("high_damage_taken_share_pct") is not None:
        high_taken = role_rules["high_damage_taken_share_pct"]
        if taken_share >= high_taken:
            judgements.append(f"Damage-taken share is high for {role}: {taken_share:g}% (project threshold: >= {high_taken}%).")
        else:
            judgements.append(f"Damage-taken share is not high for {role}: {taken_share:g}% (high threshold: >= {high_taken}%).")

    if gold_share is not None:
        high_gold = role_rules.get("high_gold_share_pct", 25)
        if gold_share >= high_gold:
            judgements.append(f"Gold share is high under the project rule: {gold_share:g}% (threshold: >= {high_gold}%).")
        else:
            judgements.append(f"Gold share is not high under the project rule: {gold_share:g}% (high threshold: >= {high_gold}%).")

    if gold_share is not None and damage_share is not None and role in DAMAGE_ROLES | {"Fighter"}:
        gap = damage_share - gold_share
        if gap >= 7:
            judgements.append(f"Damage share exceeds gold share by {gap:.1f} percentage points; this supports good gold-to-damage conversion, not poor conversion.")
        elif gold_share >= role_rules.get("high_gold_share_pct", 25) and gap < -7:
            judgements.append(f"Damage share is {-gap:.1f} percentage points below a high gold share; this supports weak visible gold-to-damage conversion.")
        else:
            judgements.append(f"Damage share minus gold share is {gap:.1f} percentage points; the project rules do not classify conversion as clearly good or poor.")

    observed = {
        key: data.get(key)
        for key in (
            "hero", "role", "duration_min", "kills", "deaths", "assists",
            "gold_share_pct", "damage_dealt_share_pct", "damage_taken_share_pct",
            "kill_participation_pct", "match_result",
        )
    }
    return {
        "status": "authoritative deterministic interpretation of supplied numbers",
        "observed_values": observed,
        "role_aware_judgements": judgements,
        "instruction": "The review must not contradict these judgements. Missing fields remain unknown.",
    }
