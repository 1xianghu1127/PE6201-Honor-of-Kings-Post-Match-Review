"""Detect and repair role or threshold contradictions in generated reviews."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


THRESHOLD_PATH = Path(__file__).resolve().parents[1] / "baseline" / "role_thresholds.json"


def _number(data: dict[str, Any], field: str) -> float | None:
    value = data.get(field)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _review_text(review: dict[str, Any]) -> str:
    fields = ("what_went_well", "what_to_improve", "next_match_focus", "evidence_used")
    return " ".join(str(item) for field in fields for item in review.get(field, [])).lower()


def _section_text(review: dict[str, Any], *fields: str) -> str:
    return " ".join(str(item) for field in fields for item in review.get(field, [])).lower()


def _mentions_missing_dimension(text: str, dimension_pattern: str) -> bool:
    missing_pattern = r"缺少|未提供|未填写|未录入|未知|无法|不能|不可"
    return bool(
        re.search(rf"(?:{missing_pattern}).{{0,18}}(?:{dimension_pattern})", text)
        or re.search(rf"(?:{dimension_pattern}).{{0,18}}(?:{missing_pattern})", text)
    )


def _requests_missing_dimension(text: str, dimension_pattern: str) -> bool:
    request_pattern = r"补充|填写|提供|录入|确认"
    return bool(
        re.search(rf"(?:{request_pattern}).{{0,18}}(?:{dimension_pattern})", text)
        or re.search(rf"(?:{dimension_pattern}).{{0,18}}(?:{request_pattern})", text)
    )


def _missing_dimensions(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    dimensions: list[tuple[str, str, str]] = []
    if any(data.get(name) is None for name in ("kills", "deaths", "assists")):
        dimensions.append(("K/D/A", "K/D/A", r"k/?d/?a|击杀|死亡|助攻"))
    for field_name, english_label, chinese_label, pattern in (
        ("gold_share_pct", "gold share", "经济占比", r"经济|金币|金钱|黄金"),
        ("damage_dealt_share_pct", "damage output", "输出占比", r"输出|伤害"),
        ("damage_taken_share_pct", "damage taken", "承伤占比", r"承伤|伤害承受|承受伤害"),
        ("kill_participation_pct", "kill participation", "参团率", r"参团|击杀参与"),
        ("match_result", "match result", "比赛结果", r"比赛结果|胜负"),
        ("hero", "hero name", "英雄名称", r"英雄|英雄名称"),
        ("role", "role", "角色", r"角色"),
    ):
        if data.get(field_name) is None or data.get(field_name) == "":
            dimensions.append((english_label, chinese_label, pattern))
    return dimensions


def _filter_items(items: Any, pattern: str) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(item) for item in items if not re.search(pattern, str(item).lower())]


def _safe_focus(data: dict[str, Any], config: dict[str, Any]) -> list[str]:
    role = data.get("role")
    role_rules = config.get(role, {})
    global_rules = config["global"]
    deaths = _number(data, "deaths")
    participation = _number(data, "kill_participation_pct")
    damage = _number(data, "damage_dealt_share_pct")
    gold = _number(data, "gold_share_pct")
    focus: list[str] = []

    if deaths is not None:
        high_deaths = role_rules.get("high_deaths", global_rules["high_deaths"])
        if deaths >= high_deaths:
            focus.append("下一局减少缺少队友支援时的高风险交战，优先控制死亡次数。")
        elif deaths <= 3:
            focus.append("下一局继续保持低死亡表现。")

    if participation is not None and participation < global_rules["low_kill_participation_pct"]:
        focus.append("下一局与队友同步参与关键团战，提高参团率。")

    if role in {"Marksman", "Mage", "Assassin"} and damage is not None:
        good_damage = role_rules.get("good_damage_share_pct", 25)
        low_damage = role_rules.get("low_damage_share_pct", 15)
        if damage >= good_damage:
            focus.append("下一局继续保持当前输出占比。")
        elif damage < low_damage:
            focus.append("下一局在有队友配合时寻找更多有效输出机会。")

    high_gold = role_rules.get("high_gold_share_pct", 25)
    if gold is not None and damage is not None and role in {"Marksman", "Mage", "Assassin", "Fighter"}:
        if gold >= high_gold and damage < gold - 7:
            focus.append("下一局将已有经济转化为更有效的团队战斗贡献。")

    if role == "Tank":
        focus.append("下一局继续根据阵容需要承担前排和团队协作职责。")
    elif role == "Support":
        focus.append("下一局继续跟随并保护团队主要输出队友。")
    elif not focus:
        focus.append("下一局继续保持现有数据支持的良好表现。")
    return focus[:3]


def repair_review_consistency(review: dict[str, Any], data: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    """Remove claims already rejected by deterministic checks and add safe replacements."""
    repaired = deepcopy(review)
    repaired.setdefault("what_went_well", [])
    repaired.setdefault("what_to_improve", [])
    repaired.setdefault("next_match_focus", [])
    repaired.setdefault("evidence_used", [])

    for error in errors:
        if "deaths as a weakness" in error:
            pattern = r"死亡(次数)?(较多|偏高|过高)|高死亡|减少死亡|降低死亡|控制死亡"
            repaired["what_to_improve"] = _filter_items(repaired["what_to_improve"], pattern)
            repaired["next_match_focus"] = _filter_items(repaired["next_match_focus"], pattern)
        elif "calls" in error and "gold share high" in error:
            repaired["what_went_well"] = _filter_items(repaired["what_went_well"], r"经济|金币|金钱|黄金")
        elif "damage share good/high" in error:
            repaired["what_went_well"] = _filter_items(repaired["what_went_well"], r"输出|伤害")
        elif "praises raw damage" in error:
            repaired["what_went_well"] = _filter_items(repaired["what_went_well"], r"输出|伤害")
        elif "damage share low" in error:
            repaired["what_to_improve"] = _filter_items(repaired["what_to_improve"], r"输出|伤害")
            repaired["next_match_focus"] = _filter_items(repaired["next_match_focus"], r"输出|伤害")
        elif "gold share as a weakness" in error or ("recommends raising" in error and "gold share" in error):
            pattern = r"经济|金币|金钱|黄金"
            repaired["what_to_improve"] = _filter_items(repaired["what_to_improve"], pattern)
            repaired["next_match_focus"] = _filter_items(repaired["next_match_focus"], pattern)
        elif "damage-taken share as a weakness" in error:
            pattern = r"承伤|伤害承受|承受伤害|被击中|受到的伤害|生存|站位|位置"
            repaired["what_to_improve"] = _filter_items(repaired["what_to_improve"], pattern)
            repaired["next_match_focus"] = _filter_items(repaired["next_match_focus"], pattern)
        elif "required improvement for" in error:
            repaired["what_to_improve"] = _filter_items(repaired["what_to_improve"], r"输出|伤害")
            repaired["next_match_focus"] = _filter_items(repaired["next_match_focus"], r"输出|伤害")
        elif "participation good/high" in error:
            repaired["what_went_well"] = _filter_items(repaired["what_went_well"], r"参团|团队参与|击杀参与")
        elif "participation low" in error:
            repaired["what_to_improve"] = _filter_items(repaired["what_to_improve"], r"参团|团队参与|击杀参与")
            repaired["next_match_focus"] = _filter_items(repaired["next_match_focus"], r"参团|团队参与|击杀参与")
        elif "gold conversion" in error or "classifies gold conversion" in error:
            pattern = r"转化|转换|经济.{0,12}利用|资源.{0,12}利用|输出.{0,8}与经济匹配"
            repaired["what_went_well"] = _filter_items(repaired["what_went_well"], pattern)
            repaired["what_to_improve"] = _filter_items(repaired["what_to_improve"], pattern)
            repaired["next_match_focus"] = _filter_items(repaired["next_match_focus"], pattern)
        elif "provide coaching strategy" in error:
            repaired["next_match_focus"] = _filter_items(
                repaired["next_match_focus"],
                r"请.{0,8}(提供|补充).{0,16}(策略|建议|方法)",
            )

    if repaired.get("abstention_level") == "partial":
        all_text = _review_text(repaired)
        focus_text = _section_text(repaired, "next_match_focus")
        for _, chinese_label, pattern in _missing_dimensions(data):
            if not _mentions_missing_dimension(all_text, pattern):
                repaired["what_to_improve"].append(f"缺少{chinese_label}，无法评价相关表现。")
            if not _requests_missing_dimension(focus_text, pattern):
                repaired["next_match_focus"].append(f"请补充{chinese_label}后再评价该维度。")
            all_text = _review_text(repaired)
            focus_text = _section_text(repaired, "next_match_focus")

    if not repaired["what_went_well"]:
        repaired["what_went_well"] = ["现有数据不足以确认明显优势。"]
    if not repaired["what_to_improve"]:
        repaired["what_to_improve"] = ["现有数据中没有达到项目阈值的明显弱点。"]
    if not repaired["next_match_focus"]:
        config = json.loads(THRESHOLD_PATH.read_text(encoding="utf-8"))
        repaired["next_match_focus"] = _safe_focus(data, config)
    return repaired


def validate_review_consistency(review: dict[str, Any], data: dict[str, Any]) -> list[str]:
    """Detect a small set of high-confidence numerical contradictions."""
    config = json.loads(THRESHOLD_PATH.read_text(encoding="utf-8"))
    role = data.get("role")
    role_rules = config.get(role, {})
    global_rules = config["global"]
    text = _review_text(review)
    positive_text = _section_text(review, "what_went_well")
    negative_text = _section_text(review, "what_to_improve", "next_match_focus")
    focus_text = _section_text(review, "next_match_focus")
    errors: list[str] = []

    deaths = _number(data, "deaths")
    if deaths is not None and deaths <= 3 and re.search(r"死亡(次数)?(较多|偏高|过高)|高死亡|减少死亡|降低死亡|控制死亡", text):
        errors.append(f"The review treats {deaths:g} deaths as a weakness even though the project rule classifies <= 3 as low.")

    gold = _number(data, "gold_share_pct")
    high_gold = role_rules.get("high_gold_share_pct", 25)
    if gold is not None and gold < high_gold and re.search(r"(经济|金币)(占比|分享比例)?(较高|偏高|很高)", text):
        errors.append(f"The review calls {gold:g}% gold share high, below the declared {high_gold}% high threshold.")

    damage = _number(data, "damage_dealt_share_pct")
    if role in {"Marksman", "Mage", "Assassin"} and damage is not None:
        good_damage = role_rules.get("good_damage_share_pct", 25)
        low_damage = role_rules.get("low_damage_share_pct", 15)
        if damage < low_damage and re.search(r"(输出|伤害)(占比)?(较高|偏高|很高|突出|良好)", text):
            errors.append(f"The review calls {damage:g}% damage share good/high, below the declared {low_damage}% low threshold.")
        if damage < low_damage and re.search(
            r"(输出伤害总量|造成.{0,12}(输出|伤害)).{0,24}(一定|良好|不错|能力|贡献)",
            positive_text,
        ):
            errors.append(
                f"The review praises raw damage despite a low {damage:g}% damage share; team share is the primary project measure."
            )
        if damage >= good_damage and re.search(r"(输出|伤害)(占比)?(较低|偏低|不足|很低)", text):
            errors.append(f"The review calls {damage:g}% damage share low, at or above the declared {good_damage}% good threshold.")

    gold_low_claim = re.search(
        r"(经济|金币|金钱|黄金)(占比|分享比例)?.{0,10}(较低|偏低|不高|不足|仅为|低[:：]|未达到)",
        negative_text,
    )
    gold_increase_action = re.search(
        r"(提高|提升|增加|争取|改善|优化).{0,12}(经济|金币|金钱|黄金)(占比|分享|获取|资源)",
        negative_text,
    )
    damage_is_low = False
    if role in {"Marksman", "Mage", "Assassin"} and damage is not None:
        damage_is_low = damage < role_rules.get("low_damage_share_pct", 15)
    if gold is not None and gold < high_gold and gold_low_claim:
        errors.append(
            f"The review treats {gold:g}% gold share as a weakness although the project only classifies it as not high; this is not a low-gold rule."
        )
    elif gold is not None and gold < high_gold and gold_increase_action and (role in {"Tank", "Support"} or not damage_is_low):
        errors.append(
            f"The review recommends raising {gold:g}% gold share without a role-aware low-gold rule or low damage-share evidence."
        )

    taken = _number(data, "damage_taken_share_pct")
    high_taken = role_rules.get("high_damage_taken_share_pct")
    if taken is not None and high_taken is not None and taken < high_taken:
        unsupported_taken_criticism = re.search(
            r"(承伤|伤害承受|承受伤害).{0,40}(较高|偏高|过高|未达到高标准|生存|站位|位置|减少被击中|减少受到|需要减少|需减少|降低)"
            r"|(减少|降低).{0,12}(承伤|伤害承受|承受伤害|被击中|受到的伤害)",
            negative_text,
        )
        if unsupported_taken_criticism:
            errors.append(
                f"The review treats {taken:g}% damage-taken share as a weakness even though it is below the declared {high_taken}% high threshold."
            )

    if role in {"Tank", "Support"}:
        role_inappropriate_output = re.search(
            r"(输出|伤害)(占比|比例)?.{0,12}(较低|偏低|不足|仅为|提高|提升|增加)"
            r"|(提高|提升|增加|增强).{0,12}(输出|伤害)",
            negative_text,
        )
        if role_inappropriate_output:
            errors.append(f"The review treats damage output as a required improvement for {role}, which is not supported by the role rules.")

    participation = _number(data, "kill_participation_pct")
    if participation is not None:
        low_kp = global_rules["low_kill_participation_pct"]
        good_kp = role_rules.get("good_kill_participation_pct", global_rules["high_kill_participation_pct"])
        if participation < low_kp and re.search(r"(参团率|团队参与)(较高|很高|良好|突出)", text):
            errors.append(f"The review calls {participation:g}% participation good/high, below the declared {low_kp}% low threshold.")
        if participation >= good_kp and re.search(r"(参团率|团队参与)(较低|偏低|不足|很低)", text):
            errors.append(f"The review calls {participation:g}% participation low, at or above the declared {good_kp}% good threshold.")
        if low_kp <= participation < good_kp:
            if re.search(r"(参团率|团队参与|击杀参与率).{0,12}(较高|很高|良好|突出)", text):
                errors.append(f"The review calls {participation:g}% participation good/high although project rules classify it as middle range.")
            if re.search(r"(参团率|团队参与|击杀参与率).{0,12}(较低|偏低|不足|很低)", text):
                errors.append(f"The review calls {participation:g}% participation low although project rules classify it as middle range.")

    if re.search(r"请.{0,8}(提供|补充).{0,16}(策略|建议|方法)", focus_text):
        errors.append("next_match_focus asks the user to provide coaching strategy instead of giving an executable next-match action.")

    if gold is not None and damage is not None and role in {"Marksman", "Mage", "Assassin", "Fighter"}:
        gap = damage - gold
        negative_conversion = re.search(
            r"(经济|金币|金钱|黄金|资源).{0,14}(转化|转换|利用).{0,12}(不足|较低|偏低|差|提高|提升|改善|优化|确保)"
            r"|(提高|提升|改善|优化|确保).{0,14}(经济|金币|金钱|黄金|资源).{0,10}(转化|转换|利用)"
            r"|输出.{0,8}与经济匹配",
            negative_text,
        )
        positive_conversion = re.search(
            r"(经济|金币|金钱|黄金|资源).{0,14}(转化|转换|利用).{0,12}(良好|较好|优秀|有效|高效)",
            positive_text,
        )
        weak_conversion = gold >= high_gold and gap < -7
        good_conversion = gap >= 7
        if good_conversion and negative_conversion:
            errors.append(
                f"The review criticises gold conversion although damage share exceeds gold share by {gap:.1f} points."
            )
        elif weak_conversion and positive_conversion:
            errors.append(f"The review praises gold conversion although damage share trails a high gold share by {-gap:.1f} points.")
        elif not good_conversion and not weak_conversion and (negative_conversion or positive_conversion):
            errors.append(
                f"The review classifies gold conversion although the {gap:.1f}-point damage-minus-gold gap is unclassified by project rules."
            )

    if review.get("abstention_level") == "partial":
        for label, _, pattern in _missing_dimensions(data):
            if not _mentions_missing_dimension(text, pattern):
                errors.append(f"Partial abstention does not explicitly decline the missing {label} dimension.")
            if not _requests_missing_dimension(focus_text, pattern):
                errors.append(f"Partial abstention does not ask the user to provide the missing {label} field in next_match_focus.")

    return errors
