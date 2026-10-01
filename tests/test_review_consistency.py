"""Tests for deterministic semantic-consistency checks."""

import unittest

from guardrails.review_consistency import validate_review_consistency


class ReviewConsistencyTests(unittest.TestCase):
    def test_case_01_style_contradictions_are_rejected(self):
        data = {"role": "Marksman", "deaths": 2, "gold_share_pct": 25.4, "damage_dealt_share_pct": 34.2}
        review = {
            "what_went_well": ["输出占比较高。"],
            "what_to_improve": ["减少死亡并提高经济转化。"],
            "next_match_focus": ["确保输出与经济匹配。"],
            "evidence_used": [],
        }
        errors = validate_review_consistency(review, data)
        self.assertGreaterEqual(len(errors), 2)

    def test_case_02_style_gold_claim_is_rejected(self):
        data = {"role": "Marksman", "deaths": 8, "gold_share_pct": 17.8, "damage_dealt_share_pct": 14.1, "kill_participation_pct": 25}
        review = {
            "what_went_well": ["有一定参与。"],
            "what_to_improve": ["经济分享比例较高，但输出不足。"],
            "next_match_focus": ["减少高风险交战。"],
            "evidence_used": [],
        }
        errors = validate_review_consistency(review, data)
        self.assertTrue(any("gold share" in error for error in errors))

    def test_low_damage_share_cannot_be_hidden_by_raw_damage_praise(self):
        data = {
            "role": "Marksman", "deaths": 8, "gold_share_pct": 17.8,
            "damage_dealt_share_pct": 14.1, "kill_participation_pct": 25,
        }
        review = {
            "abstention_level": "none",
            "what_went_well": ["输出伤害总量为31000，显示出一定的输出能力。"],
            "what_to_improve": ["死亡次数过高，参团率和输出占比较低。"],
            "next_match_focus": ["减少高风险交战并提高团队参与。"],
            "evidence_used": ["输出占比14.1%"],
        }
        errors = validate_review_consistency(review, data)
        self.assertTrue(any("praises raw damage" in error for error in errors))

    def test_consistent_claims_pass(self):
        data = {"role": "Marksman", "deaths": 2, "gold_share_pct": 25.4, "damage_dealt_share_pct": 34.2, "kill_participation_pct": 57}
        review = {
            "what_went_well": ["死亡较少，输出占比较高，经济转化良好。"],
            "what_to_improve": ["现有数据没有达到阈值的明显问题。"],
            "next_match_focus": ["继续保持安全输出。"],
            "evidence_used": ["死亡2次", "输出占比34.2%"],
        }
        self.assertEqual(validate_review_consistency(review, data), [])

    def test_low_damage_taken_cannot_be_treated_as_a_weakness(self):
        data = {"role": "Marksman", "deaths": 4, "damage_taken_share_pct": 11, "gold_share_pct": 25, "damage_dealt_share_pct": 35}
        review = {
            "abstention_level": "none",
            "what_went_well": ["输出占比较高。"],
            "what_to_improve": ["承受伤害占比11%，较低，需注意生存。"],
            "next_match_focus": ["减少承受伤害。"],
            "evidence_used": ["承伤占比11%"],
        }
        errors = validate_review_consistency(review, data)
        self.assertTrue(any("damage-taken share" in error for error in errors))

    def test_case_01_observed_wording_is_rejected(self):
        data = {
            "role": "Marksman", "deaths": 2, "gold_share_pct": 25.4,
            "damage_dealt_share_pct": 34.2, "damage_taken_share_pct": 11.4,
            "kill_participation_pct": 57,
        }
        review = {
            "abstention_level": "none",
            "what_went_well": ["击杀参与率为57%，显示出良好的团队参与度。"],
            "what_to_improve": ["伤害承受占比为11.4%，低于阈值，需关注自身生存能力。"],
            "next_match_focus": ["请提供关于如何提高生存能力的具体策略。"],
            "evidence_used": ["伤害承受占比为11.4%"],
        }
        errors = validate_review_consistency(review, data)
        self.assertTrue(any("damage-taken share" in error for error in errors))
        self.assertTrue(any("middle range" in error for error in errors))
        self.assertTrue(any("coaching strategy" in error for error in errors))

    def test_support_low_gold_and_damage_are_not_required_improvements(self):
        data = {"role": "Support", "deaths": 3, "gold_share_pct": 15, "damage_dealt_share_pct": 4, "damage_taken_share_pct": 13}
        review = {
            "abstention_level": "none",
            "what_went_well": ["死亡较少。"],
            "what_to_improve": ["经济占比较低，输出占比仅为4%。"],
            "next_match_focus": ["提高经济占比并增加输出。"],
            "evidence_used": [],
        }
        errors = validate_review_consistency(review, data)
        self.assertTrue(any("gold share" in error for error in errors))
        self.assertTrue(any("required improvement for Support" in error for error in errors))

    def test_partial_abstention_requires_explicit_missing_field_request(self):
        data = {
            "hero": "李白", "role": "Assassin", "kills": 8, "deaths": 2, "assists": 5,
            "gold_share_pct": None, "damage_dealt_share_pct": 22,
            "damage_taken_share_pct": 13, "kill_participation_pct": 62,
            "match_result": "win",
        }
        review = {
            "abstention_level": "partial",
            "what_went_well": ["输出占比符合角色标准。"],
            "what_to_improve": ["现有数据没有明显问题。"],
            "next_match_focus": ["保持安全输出。"],
            "evidence_used": ["输出占比22%"],
        }
        errors = validate_review_consistency(review, data)
        self.assertTrue(any("missing gold share" in error for error in errors))

    def test_partial_abstention_with_explicit_boundary_passes(self):
        data = {
            "hero": "李白", "role": "Assassin", "kills": 8, "deaths": 2, "assists": 5,
            "gold_share_pct": None, "damage_dealt_share_pct": 22,
            "damage_taken_share_pct": 13, "kill_participation_pct": 62,
            "match_result": "win",
        }
        review = {
            "abstention_level": "partial",
            "what_went_well": ["死亡较少，输出占比符合角色标准。"],
            "what_to_improve": ["缺少经济占比，无法评价发育和经济转化。"],
            "next_match_focus": ["保持安全输出；补充经济占比后再评价发育效率。"],
            "evidence_used": ["死亡2次", "输出占比22%"],
        }
        self.assertEqual(validate_review_consistency(review, data), [])

    def test_weak_conversion_can_receive_conversion_action(self):
        data = {
            "hero": "后羿", "role": "Marksman", "kills": 0, "deaths": 0, "assists": 0,
            "gold_share_pct": 30, "damage_dealt_share_pct": 4,
            "damage_taken_share_pct": 3, "kill_participation_pct": 0,
            "match_result": "loss",
        }
        review = {
            "abstention_level": "none",
            "what_went_well": ["死亡为0，经济占比较高。"],
            "what_to_improve": ["输出占比和参团率很低，经济没有转化为可见输出。"],
            "next_match_focus": ["及时参与有队友配合的团战，确保经济转化为有效贡献。"],
            "evidence_used": ["经济占比30%", "输出占比4%", "参团率0%"],
        }
        self.assertEqual(validate_review_consistency(review, data), [])


if __name__ == "__main__":
    unittest.main()
