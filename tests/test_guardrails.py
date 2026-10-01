"""Tests for input and output-structure validation."""

import unittest

from guardrails.validators import validate_match_data, validate_review_structure


class GuardrailTests(unittest.TestCase):
    def test_percentage_over_100_is_rejected(self):
        result = validate_match_data({
            "hero": "后羿", "role": "Marksman", "duration_min": 20,
            "kills": 1, "deaths": 2, "assists": 3,
            "gold": 10000, "gold_share_pct": 20,
            "damage_dealt": 50000, "damage_dealt_share_pct": 101,
            "damage_taken": 20000, "damage_taken_share_pct": 10,
            "kill_participation_pct": 40, "match_result": "win",
        })
        self.assertEqual(result.level, "full")

    def test_unsupported_match_result_is_rejected(self):
        result = validate_match_data({
            "hero": "安琪拉", "role": "Mage", "duration_min": 22,
            "kills": 6, "deaths": 3, "assists": 9,
            "gold": 12100, "gold_share_pct": 22,
            "damage_dealt": 82000, "damage_dealt_share_pct": 30,
            "damage_taken": 29000, "damage_taken_share_pct": 11,
            "kill_participation_pct": 58, "match_result": "draw",
        })
        self.assertEqual(result.level, "full")

    def test_full_review_requires_explanation(self):
        errors = validate_review_structure({
            "abstention_level": "full",
            "what_went_well": [""],
            "what_to_improve": [""],
            "next_match_focus": [""],
        }, "full")
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
