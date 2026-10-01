"""Deterministic role-aware baseline used by the evaluation and web demo."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from guardrails.validators import validate_match_data


THRESHOLD_PATH = Path(__file__).with_name("role_thresholds.json")


def _thresholds() -> dict[str, Any]:
    return json.loads(THRESHOLD_PATH.read_text(encoding="utf-8"))


def _value(data: dict[str, Any], name: str) -> float | None:
    value = data.get(name)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def generate_baseline_review(data: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    validation = validate_match_data(data)
    if validation.level == "full":
        reason = "；".join(validation.errors) or "关键数据不足或冲突。"
        return {
            "system": "rule_baseline",
            "abstention_level": "full",
            "what_went_well": ["信息不足，无法可靠判断本局表现。"],
            "what_to_improve": [f"当前不能评价比赛表现：{reason}"],
            "next_match_focus": ["请修正冲突或补充完整数据后重新分析。"],
            "evidence": [],
            "latency_seconds": time.perf_counter() - started,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_usd": 0.0,
        }

    config = _thresholds()
    global_rules = config["global"]
    role = data.get("role")
    role_rules = config.get(role, {})
    strengths: list[str] = []
    weaknesses: list[str] = []
    actions: list[str] = []
    evidence: list[str] = []

    kills = _value(data, "kills")
    deaths = _value(data, "deaths")
    assists = _value(data, "assists")
    kp = _value(data, "kill_participation_pct")
    gold_share = _value(data, "gold_share_pct")
    damage_share = _value(data, "damage_dealt_share_pct")
    taken_share = _value(data, "damage_taken_share_pct")

    if deaths is not None and deaths <= 3:
        strengths.append(f"死亡次数较少（{int(deaths)}次），生存表现较好。")
        evidence.append("deaths")
    if deaths is not None and deaths >= global_rules["high_deaths"]:
        weaknesses.append(f"死亡次数较多（{int(deaths)}次），可能减少持续贡献时间。")
        actions.append("下一局优先减少无队友支援时的高风险交战。")
        evidence.append("deaths")
    if kp is not None and kp >= role_rules.get("good_kill_participation_pct", global_rules["high_kill_participation_pct"]):
        strengths.append(f"参团率为{kp:.0f}%，团队参与较好。")
        evidence.append("kill_participation_pct")
    elif kp is not None and kp < global_rules["low_kill_participation_pct"]:
        weaknesses.append(f"参团率只有{kp:.0f}%，团队参与偏低。")
        actions.append("下一局在保证发育的同时，更及时地参与有队友配合的团战。")
        evidence.append("kill_participation_pct")

    if role in {"Marksman", "Mage", "Assassin"}:
        good_damage = role_rules.get("good_damage_share_pct", 25)
        low_damage = role_rules.get("low_damage_share_pct", 15)
        if damage_share is not None and damage_share >= good_damage:
            strengths.append(f"输出占比为{damage_share:.1f}%，完成了较好的伤害贡献。")
            evidence.append("damage_dealt_share_pct")
        elif damage_share is not None and damage_share < low_damage:
            weaknesses.append(f"输出占比只有{damage_share:.1f}%，与角色的伤害职责不匹配。")
            actions.append("下一局在安全位置寻找更多有效输出机会。")
            evidence.append("damage_dealt_share_pct")
        if taken_share is not None and taken_share >= role_rules.get("high_damage_taken_share_pct", 22):
            weaknesses.append(f"承伤占比为{taken_share:.1f}%，对该输出角色偏高。")
            actions.append("团战中尽量利用前排保护，减少暴露在主要攻击范围内的时间。")
            evidence.append("damage_taken_share_pct")

    if role in {"Tank", "Fighter"} and taken_share is not None:
        target = role_rules.get("good_damage_taken_share_pct", 24)
        if taken_share >= target and (deaths is None or deaths < global_rules["high_deaths"]):
            strengths.append(f"承伤占比为{taken_share:.1f}%，且死亡次数未明显失控。")
            evidence.extend(["damage_taken_share_pct", "deaths"])
        elif taken_share >= role_rules.get("high_damage_taken_share_pct", 36) and deaths is not None:
            weaknesses.append("承伤占比较高且死亡较多，部分承伤可能没有形成有效收益。")
            actions.append("承担伤害前先确认队友是否能够跟进。")

    if role == "Support" and assists is not None and assists >= 15:
        strengths.append(f"获得{int(assists)}次助攻，支援参与较好。")
        evidence.append("assists")

    if gold_share is not None and damage_share is not None:
        if gold_share >= role_rules.get("high_gold_share_pct", 25) and damage_share + 7 < gold_share and role in {"Marksman", "Mage", "Assassin", "Fighter"}:
            weaknesses.append("经济占比较高，但输出占比没有同步提升。")
            actions.append("下一局重点提高经济到有效战斗贡献的转化。")
            evidence.extend(["gold_share_pct", "damage_dealt_share_pct"])
        elif damage_share >= gold_share + 7:
            strengths.append("输出占比明显高于经济占比，输出效率较好。")
            evidence.extend(["gold_share_pct", "damage_dealt_share_pct"])

    if not strengths:
        strengths.append("现有数据中没有达到规则阈值的明显优势。")
    if not weaknesses:
        weaknesses.append("现有数据中没有达到规则阈值的明显问题。")
    if not actions:
        actions.append("下一局继续保持当前表现，并优先保证稳定参与和生存。")

    if validation.level == "partial":
        missing_text = "、".join(validation.missing_fields)
        weaknesses.append(f"以下字段缺失，相关方面无法判断：{missing_text}。")
        actions.append("补充缺失字段后可获得更完整的复盘。")

    return {
        "system": "rule_baseline",
        "abstention_level": validation.level,
        "what_went_well": strengths,
        "what_to_improve": weaknesses,
        "next_match_focus": list(dict.fromkeys(actions)),
        "evidence": list(dict.fromkeys(evidence)),
        "latency_seconds": time.perf_counter() - started,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cost_usd": 0.0,
    }
