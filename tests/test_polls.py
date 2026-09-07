#!/usr/bin/env python3
"""
Unit Tests for eToro Polls Architecture
=======================================
Tests Monday Macro, Wednesday Thematic, Friday Performers,
and strict eToro constraints (<= 28 chars options, zero '#' hashtags).
"""

import os
import sys
import unittest
from unittest import mock

# Ensure src in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import poll_generator
import economic_calendar
import etoro_client


class TestPollArchitecture(unittest.TestCase):

    def test_clean_no_hashtags(self):
        """Verify that all '#' hashtags are removed without touching '$' cashtags."""
        sample = "Rally su $PLTR e $NVDA! #eToro #CopyTrading #Investimenti. Che ne dite?"
        cleaned = poll_generator._clean_no_hashtags(sample)
        self.assertNotIn("#", cleaned)
        self.assertIn("$PLTR", cleaned)
        self.assertIn("$NVDA", cleaned)
        self.assertIn("Che ne dite?", cleaned)

    def test_smart_truncate(self):
        """Verify that smart_truncate never cuts mid-word and preserves complete sentences."""
        long_text = (
            "Prima frase completa con dettagli importanti. "
            "Seconda frase che contiene spiegazioni molto ampie sui tassi e sui mercati. "
            "Terza frase finale che conclude il discorso."
        )
        # Should cut at end of second sentence without cutting words
        truncated = economic_calendar.smart_truncate(long_text, max_chars=130)
        self.assertLessEqual(len(truncated), 130)
        self.assertTrue(truncated.endswith("."))
        self.assertNotIn("..", truncated)  # not cut mid-sentence with ellipsis if sentence terminator found
        self.assertIn("Seconda frase", truncated)
        self.assertNotIn("Terza frase", truncated)

        # Text shorter than max_chars should remain intact
        short_text = "Frase breve intatta."
        self.assertEqual(economic_calendar.smart_truncate(short_text, 100), short_text)

    def test_monday_macro_poll_structure(self):
        """Verify Monday Macro poll structure, calendar formatting, and limits."""
        poll = economic_calendar.get_weekly_macro_poll()
        self.assertIn("title", poll)
        self.assertIn("options", poll)
        self.assertIn("message", poll)
        self.assertIn("tickers", poll)

        # Title <= 200 chars
        self.assertLessEqual(len(poll["title"]), 200)

        # Options between 2 and 4, each <= 28 chars
        self.assertGreaterEqual(len(poll["options"]), 2)
        self.assertLessEqual(len(poll["options"]), 4)
        for opt in poll["options"]:
            self.assertLessEqual(len(opt), 28, f"Option '{opt}' exceeds 28 chars!")
            self.assertNotIn("#", opt)

        # Message <= 1000 chars, no '#' hashtags
        self.assertLessEqual(len(poll["message"]), 1000)
        self.assertNotIn("#", poll["message"])

        # Check Day-by-Day Calendar format
        msg = poll["message"]
        self.assertIn("CALENDARIO MACRO", msg)
        self.assertIn("Lunedì", msg)
        self.assertIn("Venerdì", msg)
        self.assertIn("▪️", msg)

    def test_wednesday_thematic_poll_structure(self):
        """Verify Wednesday Thematic poll templates."""
        for t in poll_generator.POLL_TEMPLATES:
            poll = poll_generator.generate_wednesday_thematic_poll(specific_id=t["id"])
            self.assertLessEqual(len(poll["title"]), 200)
            self.assertGreaterEqual(len(poll["options"]), 2)
            self.assertLessEqual(len(poll["options"]), 4)
            for opt in poll["options"]:
                self.assertLessEqual(len(opt), 28, f"Template {t['id']} option '{opt}' exceeds 28 chars!")
                self.assertNotIn("#", opt)
            self.assertNotIn("#", poll["message"])

    @unittest.mock.patch("finance_fetcher.fetch_stock_data")
    def test_friday_performers_poll_structure(self, mock_fetch):
        """Verify Friday Top Performers poll generation."""
        mock_fetch.return_value = {
            "PLTR": {"company_name": "Palantir", "weekly_change": 8.45},
            "NVDA": {"company_name": "NVIDIA", "weekly_change": 6.12},
            "CCJ": {"company_name": "Cameco", "weekly_change": 5.30},
            "ENI.MI": {"company_name": "Eni", "weekly_change": 1.20},
            "XEON.DE": {"company_name": "Xtrackers", "weekly_change": 0.05},
        }
        poll = poll_generator.generate_friday_performers_poll()
        self.assertIn("title", poll)
        self.assertIn("options", poll)
        self.assertIn("message", poll)
        self.assertIn("tickers", poll)

        self.assertLessEqual(len(poll["title"]), 200)
        self.assertGreaterEqual(len(poll["options"]), 2)
        self.assertLessEqual(len(poll["options"]), 4)

        # Options should be top 3 + 1
        self.assertTrue(poll["options"][0].startswith("$PLTR"))
        self.assertTrue(poll["options"][1].startswith("$NVDA"))
        self.assertTrue(poll["options"][2].startswith("$CCJ"))

        for opt in poll["options"]:
            self.assertLessEqual(len(opt), 28, f"Option '{opt}' exceeds 28 chars!")
            self.assertNotIn("#", opt)

        self.assertNotIn("#", poll["message"])
        # Should include broad market tags
        self.assertIn("SPX500", poll["tickers"])
        self.assertIn("NSDQ100", poll["tickers"])

    @unittest.mock.patch("finance_fetcher.fetch_stock_data")
    def test_dry_run_modes(self, mock_fetch):
        """Test dry-run executions for Monday, Wednesday, Friday, and Auto."""
        mock_fetch.return_value = {
            "PLTR": {"company_name": "Palantir", "weekly_change": 8.45},
            "NVDA": {"company_name": "NVIDIA", "weekly_change": 6.12},
            "CCJ": {"company_name": "Cameco", "weekly_change": 5.30},
        }
        for mode in ("monday", "wednesday", "friday", "auto"):
            res = poll_generator.publish_etoro_poll(poll_id=mode, dry_run=True)
            self.assertTrue(res.get("success"))
            self.assertTrue(res.get("dry_run"))
            self.assertNotIn("#", res.get("title", ""))
            for opt in res.get("options", []):
                self.assertLessEqual(len(opt), 28)
                self.assertNotIn("#", opt)

    def test_market_ids_mapping(self):
        """Verify that major market indices have valid eToro market IDs."""
        ids = etoro_client.get_market_ids_for_tickers(["SPX500", "NSDQ100", "PLTR", "NVDA"])
        self.assertIn(27, ids)    # SPX500
        self.assertIn(28, ids)    # NSDQ100
        self.assertIn(7991, ids)  # PLTR
        self.assertIn(1137, ids)  # NVDA


if __name__ == "__main__":
    unittest.main()

