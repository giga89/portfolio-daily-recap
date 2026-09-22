"""
Unit tests for Event Monitor, Dividend Pay Day, and Corporate Earnings.
Verifies post generation, fallback determinism, Gist deduplication, and lookback logic.
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import ai_news_generator
import gist_storage
import event_monitor


class TestEventMonitor(unittest.TestCase):

    def test_dividend_post_fallback(self):
        """Verify dividend pay day fallback generates compliant, non-empty Italian text."""
        text = ai_news_generator._dividend_post_fallback(
            ticker="GLEN.L",
            company_name="Glencore PLC",
            pay_date="Sep 18, 2026",
            dps_amount="$0.09 / azione",
            div_yield="3.15%",
            weight_pct=1.12,
        )
        self.assertIn("$GLEN.L", text)
        self.assertIn("Glencore PLC", text)
        self.assertIn("ACCREDITO DIVIDENDO", text)
        self.assertIn("Sep 18, 2026", text)
        self.assertNotIn("#", text, "eToro posts must not contain '#' hashtags")
        self.assertLess(len(text), 1400, "Must be under eToro 1400 character limit")

    def test_earnings_post_fallback(self):
        """Verify corporate earnings fallback generates compliant, non-empty Italian text."""
        text = ai_news_generator._earnings_post_fallback(
            ticker="AVGO",
            company_name="Broadcom Inc.",
            quarter="Q3 2026",
            eps_actual="$3.32",
            eps_est="$3.16",
            eps_beat=True,
            rev_actual="$29.6B",
            rev_growth_yoy="+86% YoY",
            guidance_text="Guida solida per cluster AI.",
            thesis_impact="Infrastruttura critica per chip custom.",
            weight_pct=2.45,
        )
        self.assertIn("$AVGO", text)
        self.assertIn("Broadcom Inc.", text)
        self.assertIn("EARNINGS FLASH", text)
        self.assertIn("Q3 2026", text)
        self.assertNotIn("#", text, "eToro posts must not contain '#' hashtags")
        self.assertLess(len(text), 1400, "Must be under eToro 1400 character limit")

    def test_generate_dividend_post_callable(self):
        """Verify generate_dividend_post returns valid text without throwing exceptions."""
        text = ai_news_generator.generate_dividend_post(
            ticker="ENI.MI",
            company_name="Eni S.p.A.",
            pay_date="Sep 23, 2026",
            dps_amount="€0.25 / azione",
            div_yield="6.8%",
            weight_pct=2.30,
        )
        self.assertIsInstance(text, str)
        self.assertIn("$ENI.MI", text)
        self.assertGreater(len(text), 100)

    def test_generate_earnings_post_callable(self):
        """Verify generate_earnings_post returns valid text without throwing exceptions."""
        text = ai_news_generator.generate_earnings_post(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            quarter="Q2 2026",
            eps_actual="$0.68",
            eps_est="$0.64",
            eps_beat=True,
            rev_actual="$30.0B",
            rev_growth_yoy="+122% YoY",
        )
        self.assertIsInstance(text, str)
        self.assertIn("$NVDA", text)
        self.assertGreater(len(text), 100)

    def test_gist_dedup_functions(self):
        """Verify that Gist deduplication functions for pay days and earnings work properly."""
        from unittest.mock import patch
        mock_data = {}

        def mock_load():
            return mock_data

        def mock_save(new_data):
            nonlocal mock_data
            mock_data = new_data
            return True

        with patch("gist_storage.load_data", side_effect=mock_load), \
             patch("gist_storage.save_data", side_effect=mock_save), \
             patch("gist_storage._invalidate_cache"):

            # Test dividend pay day dedup
            self.assertFalse(gist_storage.is_dividend_posted("TEST_TICKER", "Sep 18, 2026"))
            gist_storage.mark_dividend_posted("TEST_TICKER", "Sep 18, 2026", post_id="test_post_123")
            self.assertTrue(gist_storage.is_dividend_posted("TEST_TICKER", "Sep 18, 2026"))

            # Test earnings dedup
            self.assertFalse(gist_storage.is_earnings_posted("TEST_TICKER", "Q3 2026", 2026))
            gist_storage.mark_earnings_posted("TEST_TICKER", "Q3 2026", 2026, post_id="test_post_456")
            self.assertTrue(gist_storage.is_earnings_posted("TEST_TICKER", "Q3 2026", 2026))


    def test_check_and_publish_dividends_dry_run(self):
        """Verify check_and_publish_dividends runs cleanly in dry-run with lookback."""
        results = event_monitor.check_and_publish_dividends(dry_run=True, lookback_days=10)
        self.assertIsInstance(results, list)
        for res in results:
            self.assertTrue(res.get("success"))
            self.assertTrue(res.get("dry_run"))


if __name__ == "__main__":
    unittest.main()
