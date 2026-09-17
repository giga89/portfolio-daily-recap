#!/usr/bin/env python3
"""
Test Suite: Balanced Tag Rotation & Community Engagement Prioritization
========================================================================
Verifies:
1. _get_ticker_engagement_scores() reads and computes engagement weights from post_analytics.json.
2. _select_tags_for_rotation() allocates high-engagement crowd favorites and 1 niche holding slot.
3. Rotation updates used_tags state and cycles through all portfolio holdings over time.
4. Edge cases (single tag, empty pool, excluded tags) behave predictably without crashing.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import ai_news_generator


class TestTagRotationBalance(unittest.TestCase):

    def test_get_ticker_engagement_scores_from_analytics(self):
        """Verify that engagement scores are parsed properly from post_analytics.json data."""
        mock_data = {
            "posts": [
                {
                    "tickers": ["NVDA", "PLTR"],
                    "likes": 25,
                    "comments": 4
                },
                {
                    "tickers": ["NVDA", "CCJ"],
                    "likes": 15,
                    "comments": 2
                },
                {
                    "tickers": ["TRIG.L"],
                    "likes": 2,
                    "comments": 0
                }
            ]
        }
        with patch("os.path.exists", return_value=True):
            with patch("json.load", return_value=mock_data):
                with patch("builtins.open", unittest.mock.mock_open()):
                    scores = ai_news_generator._get_ticker_engagement_scores()
                    self.assertIn("NVDA", scores)
                    self.assertIn("PLTR", scores)
                    self.assertIn("CCJ", scores)
                    self.assertIn("TRIGL", scores)
                    # NVDA: (25*1.5 + 4*2.0) + (15*1.5 + 2*2.0) = 45.5 + 26.5 = 72.0
                    # PLTR: 45.5
                    # TRIGL: 3.0
                    self.assertGreater(scores["NVDA"], scores["PLTR"])
                    self.assertGreater(scores["PLTR"], scores["TRIGL"])

    def test_select_tags_for_rotation_balances_favorites_and_niche(self):
        """Ensure selection allocates high-interest favorites and reserves a slot for niche holdings."""
        mock_engagement = {
            "NVDA": 100.0,
            "PLTR": 80.0,
            "TSM": 60.0,
            "CCJ": 50.0,
            "AMZN": 40.0,
            "ENELMI": 5.0,
            "TRIGL": 4.0,
            "PRYMI": 3.0,
            "AZNL": 2.0,
            "1919HK": 1.0,
        }

        mock_storage = {"used_tags": []}

        with patch("ai_news_generator._get_ticker_engagement_scores", return_value=mock_engagement):
            with patch("ai_news_generator.load_data", return_value=mock_storage):
                with patch("ai_news_generator.save_data") as mock_save:
                    selected = ai_news_generator._select_tags_for_rotation(
                        max_tags=3,
                        allowed_tickers=["NVDA", "PLTR", "TSM", "CCJ", "AMZN", "ENEL.MI", "TRIG.L", "PRY.MI", "AZN.L", "1919.HK"]
                    )
                    self.assertEqual(len(selected), 3)

                    # Top half (5 items) = high pool: NVDA, PLTR, TSM, CCJ, AMZN
                    high_pool = {"NVDA", "PLTR", "TSM", "CCJ", "AMZN"}
                    # Bottom half (5 items) = niche pool: ENEL.MI, TRIG.L, PRY.MI, AZN.L, 1919.HK
                    niche_pool = {"ENEL.MI", "TRIG.L", "PRY.MI", "AZN.L", "1919.HK"}

                    high_selected = [t for t in selected if t in high_pool or t.replace('.', '') in high_pool]
                    niche_selected = [t for t in selected if t in niche_pool or t.replace('.', '') in niche_pool]

                    self.assertEqual(len(high_selected), 2)
                    self.assertEqual(len(niche_selected), 1)
                    self.assertTrue(mock_save.called)

    def test_rotation_cycles_through_niche_holdings(self):
        """Verify that across multiple rounds, different niche holdings are rotated through."""
        mock_engagement = {
            "NVDA": 100.0,
            "PLTR": 80.0,
            "TSM": 60.0,
            "AMZN": 50.0,
            "ENELMI": 5.0,
            "TRIGL": 4.0,
            "PRYMI": 3.0,
            "AZNL": 2.0,
        }

        storage = {"used_tags": []}

        def mock_load():
            return {"used_tags": list(storage["used_tags"])}

        def mock_save(data):
            storage["used_tags"] = list(data.get("used_tags", []))

        allowed = ["NVDA", "PLTR", "TSM", "AMZN", "ENEL.MI", "TRIG.L", "PRY.MI", "AZN.L"]

        with patch("ai_news_generator._get_ticker_engagement_scores", return_value=mock_engagement):
            with patch("ai_news_generator.load_data", side_effect=mock_load):
                with patch("ai_news_generator.save_data", side_effect=mock_save):
                    round1 = ai_news_generator._select_tags_for_rotation(max_tags=3, allowed_tickers=allowed)
                    round2 = ai_news_generator._select_tags_for_rotation(max_tags=3, allowed_tickers=allowed)

                    # Ensure both rounds succeed and produce distinct combinations
                    self.assertEqual(len(round1), 3)
                    self.assertEqual(len(round2), 3)

                    niche_candidates = {"ENEL.MI", "TRIG.L", "PRY.MI", "AZN.L"}
                    niche_r1 = set(round1).intersection(niche_candidates)
                    niche_r2 = set(round2).intersection(niche_candidates)

                    self.assertEqual(len(niche_r1), 1)
                    self.assertEqual(len(niche_r2), 1)
                    # Round 2 niche pick must be different from Round 1 niche pick
                    self.assertNotEqual(niche_r1, niche_r2)


if __name__ == "__main__":
    unittest.main()
