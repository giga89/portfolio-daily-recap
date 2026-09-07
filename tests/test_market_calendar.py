#!/usr/bin/env python3
"""
Unit Tests for Market Calendar & Holiday Session Routing
=========================================================
Tests US and EU market holiday algorithms, session routing (SKIP, HOLIDAY_MEME, NORMAL),
and holiday meme card generation.
"""

import os
import sys
import datetime
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import market_calendar
import meme_generator


class TestMarketCalendar(unittest.TestCase):

    def test_us_holidays_2026(self):
        """Verify that all 2026 US market holidays are correctly identified."""
        holidays_2026 = market_calendar.get_us_market_holidays(2026)
        
        # Labor Day (1st Monday of September)
        labor_day = datetime.date(2026, 9, 7)
        self.assertIn(labor_day, holidays_2026)
        self.assertEqual(holidays_2026[labor_day], "Labor Day")
        is_h, name = market_calendar.is_us_market_holiday(labor_day)
        self.assertTrue(is_h)
        self.assertEqual(name, "Labor Day")

        # Thanksgiving (4th Thursday of November)
        t_day = datetime.date(2026, 11, 26)
        self.assertIn(t_day, holidays_2026)
        self.assertEqual(holidays_2026[t_day], "Thanksgiving Day")

        # Good Friday
        gf_day = datetime.date(2026, 4, 3)
        self.assertIn(gf_day, holidays_2026)
        self.assertEqual(holidays_2026[gf_day], "Good Friday")

        # Regular trading day (Tuesday Sep 8, 2026)
        regular_day = datetime.date(2026, 9, 8)
        is_reg, reg_name = market_calendar.is_us_market_holiday(regular_day)
        self.assertFalse(is_reg)
        self.assertIsNone(reg_name)

    def test_eu_holidays_2026(self):
        """Verify universal European market holidays."""
        holidays_2026 = market_calendar.get_eu_universal_holidays(2026)

        # Capodanno
        self.assertIn(datetime.date(2026, 1, 1), holidays_2026)
        # Good Friday
        self.assertIn(datetime.date(2026, 4, 3), holidays_2026)
        # Easter Monday
        self.assertIn(datetime.date(2026, 4, 6), holidays_2026)
        # Christmas
        self.assertIn(datetime.date(2026, 12, 25), holidays_2026)

        # Today (Sep 7, 2026) is NOT an all-closed EU holiday
        is_eu_h, _ = market_calendar.is_all_eu_markets_closed(datetime.date(2026, 9, 7))
        self.assertFalse(is_eu_h)

    def test_session_routing_today_labor_day(self):
        """Verify that on Labor Day: us_close is SKIPPED, us_open is HOLIDAY_MEME, eu_open is NORMAL."""
        labor_day = datetime.date(2026, 9, 7)

        # US Close -> MUST SKIP
        close_action = market_calendar.should_skip_or_meme_session("U.S. market close", labor_day)
        self.assertEqual(close_action["action"], "SKIP")
        self.assertEqual(close_action["holiday_name"], "Labor Day")
        self.assertIn("Wall Street is closed", close_action["reason"])

        # US Open -> MUST PUBLISH HOLIDAY MEME
        open_action = market_calendar.should_skip_or_meme_session("U.S. market open", labor_day)
        self.assertEqual(open_action["action"], "HOLIDAY_MEME")
        self.assertEqual(open_action["holiday_name"], "Labor Day")
        self.assertEqual(open_action["market"], "US")

        # EU Open -> NORMAL (European markets were open today)
        eu_action = market_calendar.should_skip_or_meme_session("European market open", labor_day)
        self.assertEqual(eu_action["action"], "NORMAL")

    def test_session_routing_eu_holiday(self):
        """Verify that on a day when all EU markets are closed (e.g. Capodanno), eu_open is HOLIDAY_MEME."""
        capodanno = datetime.date(2026, 1, 1)

        eu_action = market_calendar.should_skip_or_meme_session("European market open", capodanno)
        self.assertEqual(eu_action["action"], "HOLIDAY_MEME")
        self.assertEqual(eu_action["market"], "EU")

    def test_holiday_post_text(self):
        """Verify holiday post text formatting, tickers, and absence of '#' hashtags."""
        text_us = market_calendar.generate_holiday_post_text("Labor Day", market="US")
        self.assertNotIn("#", text_us)
        self.assertIn("Labor Day", text_us)
        self.assertIn("$SPX500", text_us)
        self.assertIn("$PLTR", text_us)

        text_eu = market_calendar.generate_holiday_post_text("Capodanno", market="EU")
        self.assertNotIn("#", text_eu)
        self.assertIn("Capodanno", text_eu)
        self.assertIn("$SX7PEX.DE", text_eu)

    def test_holiday_meme_card_generation(self):
        """Verify that generate_meme_card creates a valid 16:9 card for holiday sentiment."""
        card_path = meme_generator.generate_meme_card(
            portfolio_daily=0.0,
            is_holiday=True,
            holiday_name="Labor Day",
        )
        self.assertIsNotNone(card_path)
        self.assertTrue(os.path.exists(card_path))
        self.assertIn("meme_holiday", os.path.basename(card_path))


if __name__ == "__main__":
    unittest.main()
