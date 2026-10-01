"""Tests for baseline reviews and abstention behaviour."""

import unittest

from baseline.rules import generate_baseline_review


class BaselineTests(unittest.TestCase):
    def test_complete_marksman_review(self):
        data = {
            "hero": "后羿", "role": "Marksman", "duration_min": 20,
            "kills": 9, "deaths": 2, "assists": 7,
            "gold": 13200, "gold_share_pct": 25.4,
            "damage_dealt": 82000, "damage_dealt_share_pct": 34.2,
            "damage_taken": 24000, "damage_taken_share_pct": 11.4,
            "kill_participation_pct": 57, "match_result": "win",
            "validation_status": "valid",
        }
        review = generate_baseline_review(data)
        self.assertEqual(review["abstention_level"], "none")
        self.assertTrue(review["what_went_well"])
        self.assertEqual(review["cost_usd"], 0.0)

    def test_partial_review_keeps_supported_output(self):
        data = {
            "hero": "马可波罗", "role": "Marksman", "duration_min": 22,
            "kills": 7, "deaths": 3, "assists": 8,
            "gold": 13400, "gold_share_pct": 24.0,
            "damage_dealt": None, "damage_dealt_share_pct": None,
            "damage_taken": 30000, "damage_taken_share_pct": 12.0,
            "kill_participation_pct": 54, "match_result": "win",
            "validation_status": "incomplete",
        }
        review = generate_baseline_review(data)
        self.assertEqual(review["abstention_level"], "partial")
        self.assertTrue(review["next_match_focus"])

    def test_invalid_values_full_abstention(self):
        data = {
            "hero": "蔡文姬", "role": "Support", "kills": -1,
            "deaths": 3, "assists": 18, "gold": 8500,
            "gold_share_pct": 15.0, "damage_dealt": 12000,
            "damage_dealt_share_pct": 105.0, "damage_taken": 35000,
            "damage_taken_share_pct": 14.0, "kill_participation_pct": 70,
            "duration_min": 20, "match_result": "win",
            "validation_status": "invalid_values",
        }
        review = generate_baseline_review(data)
        self.assertEqual(review["abstention_level"], "full")


if __name__ == "__main__":
    unittest.main()
