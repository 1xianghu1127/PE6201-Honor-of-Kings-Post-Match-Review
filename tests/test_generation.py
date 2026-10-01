"""Tests for generation, retry, repair, and full-abstention paths."""

import json
import unittest

from core.openrouter_client import DEFAULT_TEXT_MODEL, OpenRouterResult
from guardrails.review_consistency import validate_review_consistency
from rag.generation import generate_rag_review


class FakeClient:
    def __init__(self):
        self.called = False
        self.kwargs = None

    def chat(self, **kwargs):
        self.called = True
        self.kwargs = kwargs
        content = json.dumps({
            "abstention_level": "none",
            "what_went_well": ["输出占比较高。"],
            "what_to_improve": ["现有数据不能证明具体走位问题。"],
            "next_match_focus": ["继续保持安全输出。"],
            "evidence_used": ["damage_dealt_share_pct", "retrieved role guidance"],
        }, ensure_ascii=False)
        return OpenRouterResult(content, "fake-model", 0.01, 10, 10, 20, 0.001, {})


class CorrectingFakeClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def chat(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        bad = self.calls == 1
        content = json.dumps({
            "abstention_level": "none",
            "what_went_well": ["输出占比较高。"],
            "what_to_improve": ["需要减少死亡。" if bad else "现有数据中没有明显严重问题。"],
            "next_match_focus": ["保持安全输出。"],
            "evidence_used": ["damage_dealt_share_pct=34.2", "deaths=2"],
        }, ensure_ascii=False)
        return OpenRouterResult(content, "fake-model", 0.01, 10, 10, 20, 0.001, {})


class AlwaysLowTakenViolationClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def chat(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        content = json.dumps({
            "abstention_level": "none",
            "what_went_well": ["输出占比较高，死亡较少。", "击杀参与率为57%，显示出良好的团队参与度。"],
            "what_to_improve": ["伤害承受占比为11.4%，低于阈值，需关注自身生存能力。"],
            "next_match_focus": ["请提供关于如何提高生存能力的具体策略。"],
            "evidence_used": ["输出占比34.2%", "承伤占比11.4%"],
        }, ensure_ascii=False)
        return OpenRouterResult(content, "fake-model", 0.01, 10, 10, 20, 0.001, {})


class EmptyImprovementClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def chat(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        content = json.dumps({
            "abstention_level": "none",
            "what_went_well": ["输出占比较高，死亡较少。"],
            "what_to_improve": [],
            "next_match_focus": ["继续保持当前输出表现。"],
            "evidence_used": ["输出占比34.2%", "死亡2次"],
        }, ensure_ascii=False)
        return OpenRouterResult(content, "fake-model", 0.01, 10, 10, 20, 0.001, {})


class MissingCostClient(FakeClient):
    def chat(self, **kwargs):
        result = super().chat(**kwargs)
        result.cost_usd = None
        return result


class GenerationTests(unittest.TestCase):
    def test_complete_case_uses_retrieval_and_model(self):
        data = {
            "hero": "后羿", "role": "Marksman", "duration_min": 20,
            "kills": 9, "deaths": 2, "assists": 7,
            "gold": 13200, "gold_share_pct": 25.4,
            "damage_dealt": 82000, "damage_dealt_share_pct": 34.2,
            "damage_taken": 24000, "damage_taken_share_pct": 11.4,
            "kill_participation_pct": 57, "match_result": "win",
            "validation_status": "valid",
        }
        client = FakeClient()
        review = generate_rag_review(data, client=client)
        self.assertTrue(client.called)
        self.assertEqual(client.kwargs["model"], DEFAULT_TEXT_MODEL)
        self.assertEqual(review["abstention_level"], "none")
        self.assertEqual(review["pipeline_version"], "2.2-role-aware-deterministic-repair")
        self.assertTrue(review["retrieved_chunks"])
        self.assertEqual(review["cost_usd"], 0.001)
        self.assertEqual(review["semantic_guardrail_retries"], 0)
        self.assertFalse(review["semantic_guardrail_repair_applied"])
        prompt = client.kwargs["messages"][1]["content"]
        self.assertIn("ANALYTICAL FACTS", prompt)
        self.assertIn("Deaths are low", prompt)
        system_prompt = client.kwargs["messages"][0]["content"]
        self.assertIn('"Not high" is neutral', system_prompt)
        self.assertIn("For Tank and Support", system_prompt)

    def test_missing_provider_cost_is_recorded_as_zero(self):
        data = {
            "hero": "后羿", "role": "Marksman", "duration_min": 20,
            "kills": 9, "deaths": 2, "assists": 7,
            "gold": 13200, "gold_share_pct": 25.4,
            "damage_dealt": 82000, "damage_dealt_share_pct": 34.2,
            "damage_taken": 24000, "damage_taken_share_pct": 11.4,
            "kill_participation_pct": 57, "match_result": "win",
            "validation_status": "valid",
        }
        review = generate_rag_review(data, client=MissingCostClient())
        self.assertEqual(review["cost_usd"], 0.0)

    def test_numerical_contradiction_triggers_one_correction(self):
        data = {
            "hero": "后羿", "role": "Marksman", "duration_min": 20,
            "kills": 9, "deaths": 2, "assists": 7,
            "gold": 13200, "gold_share_pct": 25.4,
            "damage_dealt": 82000, "damage_dealt_share_pct": 34.2,
            "damage_taken": 24000, "damage_taken_share_pct": 11.4,
            "kill_participation_pct": 57, "match_result": "win",
            "validation_status": "valid",
        }
        client = CorrectingFakeClient()
        review = generate_rag_review(data, client=client)
        self.assertEqual(client.calls, 2)
        self.assertEqual(review["semantic_guardrail_retries"], 1)
        self.assertEqual(review["total_tokens"], 40)
        self.assertEqual(review["cost_usd"], 0.002)
        self.assertFalse(review["semantic_guardrail_repair_applied"])

    def test_repeated_low_taken_violation_is_repaired_deterministically(self):
        data = {
            "hero": "后羿", "role": "Marksman", "duration_min": 20,
            "kills": 9, "deaths": 2, "assists": 7,
            "gold": 13200, "gold_share_pct": 25.4,
            "damage_dealt": 82000, "damage_dealt_share_pct": 34.2,
            "damage_taken": 24000, "damage_taken_share_pct": 11.4,
            "kill_participation_pct": 57, "match_result": "win",
            "validation_status": "valid",
        }
        client = AlwaysLowTakenViolationClient()
        review = generate_rag_review(data, client=client)
        self.assertEqual(client.calls, 2)
        self.assertTrue(review["semantic_guardrail_repair_applied"])
        self.assertEqual(validate_review_consistency(review, data), [])
        self.assertNotIn("关注自身生存", " ".join(review["what_to_improve"]))
        self.assertNotIn("良好的团队参与度", " ".join(review["what_went_well"]))
        self.assertNotIn("请提供", " ".join(review["next_match_focus"]))
        self.assertTrue(review["next_match_focus"])

    def test_empty_improvement_section_is_repaired_deterministically(self):
        data = {
            "hero": "后羿", "role": "Marksman", "duration_min": 20,
            "kills": 9, "deaths": 2, "assists": 7,
            "gold": 13200, "gold_share_pct": 25.4,
            "damage_dealt": 82000, "damage_dealt_share_pct": 34.2,
            "damage_taken": 24000, "damage_taken_share_pct": 11.4,
            "kill_participation_pct": 57, "match_result": "win",
            "validation_status": "valid",
        }
        client = EmptyImprovementClient()
        review = generate_rag_review(data, client=client)
        self.assertEqual(client.calls, 2)
        self.assertTrue(review["semantic_guardrail_repair_applied"])
        self.assertTrue(review["what_to_improve"])
        self.assertIn("没有达到项目阈值的明显弱点", review["what_to_improve"][0])
        self.assertEqual(validate_review_consistency(review, data), [])

    def test_full_abstention_does_not_call_model(self):
        data = {"hero": "后羿", "role": "Marksman", "validation_status": "insufficient_data"}
        client = FakeClient()
        review = generate_rag_review(data, client=client)
        self.assertFalse(client.called)
        self.assertEqual(review["abstention_level"], "full")
        self.assertEqual(review["cost_usd"], 0.0)
        self.assertIn("K/D/A", review["next_match_focus"][0])


if __name__ == "__main__":
    unittest.main()
