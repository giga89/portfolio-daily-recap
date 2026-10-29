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

    def test_non_portfolio_ticker_rejected(self):
        """Verify that any asset not in PORTFOLIO_ASSETS_METADATA (e.g. 0005.HK) is rejected."""
        from stock_focus_card import TICKER_THEMES
        from portfolio_manager import PORTFOLIO_ASSETS_METADATA

        self.assertNotIn("0005.HK", PORTFOLIO_ASSETS_METADATA)
        self.assertNotIn("0005.HK", TICKER_THEMES)

        res_earnings = event_monitor.publish_earnings_for_ticker("0005.HK", dry_run=True)
        self.assertFalse(res_earnings["success"])
        self.assertIn("not in portfolio", res_earnings["error"])

        res_div = event_monitor.publish_dividend_for_ticker("0005.HK", dry_run=True)
        self.assertFalse(res_div["success"])
        self.assertIn("not in portfolio", res_div["error"])

    def test_reporting_quarter_calculation(self):
        """Verify corporate reporting quarter logic calculates preceding completed quarter."""
        import datetime
        import earnings_timing

        oct_28 = datetime.date(2026, 10, 28)
        nov_17 = datetime.date(2026, 11, 17)
        nov_02 = datetime.date(2026, 11, 2)

        # MSFT FY ends in June -> Oct is Q1 FY(year+1)
        self.assertEqual(earnings_timing.get_reporting_quarter("MSFT", oct_28), "Q1 FY2027")
        # GOOG calendar year -> Oct is Q3
        self.assertEqual(earnings_timing.get_reporting_quarter("GOOG", oct_28), "Q3 2026")
        # NVDA FY ends in Jan -> Nov is Q3 FY(year+1)
        self.assertEqual(earnings_timing.get_reporting_quarter("NVDA", nov_17), "Q3 FY2027")
        # AAPL FY ends in Sept -> Nov is Q4 FY(year)
        self.assertEqual(earnings_timing.get_reporting_quarter("AAPL", nov_02), "Q4 FY2026")
        # Standard European calendar
        self.assertEqual(earnings_timing.get_reporting_quarter("BESI.NV", oct_28), "Q3 2026")

    def test_premature_earnings_release_blocked_before_release_time(self):
        """Verify that scheduled earnings cannot be published prior to market close / release hour."""
        import datetime
        import pandas as pd
        from unittest.mock import MagicMock, patch
        import earnings_timing

        mock_ticker = MagicMock()
        # Scheduled at 20:00 UTC (AMC)
        sched_dt = datetime.datetime(2026, 10, 28, 20, 0, tzinfo=datetime.timezone.utc)
        df = pd.DataFrame(
            [{"EPS Estimate": 4.72, "Reported EPS": float("nan"), "Surprise(%)": float("nan")}],
            index=[sched_dt],
        )
        mock_ticker.earnings_dates = df

        with patch("earnings_timing.yf.Ticker", return_value=mock_ticker):
            # Simulated check at 15:00 UTC (hours before release)
            check_time = datetime.datetime(2026, 10, 28, 15, 0, tzinfo=datetime.timezone.utc)
            is_rel, data, reason = earnings_timing.verify_earnings_release_status(
                "MSFT", "MSFT", lookback_days=1, check_time=check_time
            )
            self.assertFalse(is_rel)
            self.assertIn("Market release time not reached yet", reason)

    def test_nan_reported_eps_blocks_earnings_publication(self):
        """Verify that even after scheduled hour, if Reported EPS is still NaN, publication is blocked."""
        import datetime
        import pandas as pd
        from unittest.mock import MagicMock, patch
        import earnings_timing

        mock_ticker = MagicMock()
        sched_dt = datetime.datetime(2026, 10, 28, 20, 0, tzinfo=datetime.timezone.utc)
        df = pd.DataFrame(
            [{"EPS Estimate": 4.72, "Reported EPS": float("nan"), "Surprise(%)": float("nan")}],
            index=[sched_dt],
        )
        mock_ticker.earnings_dates = df

        with patch("earnings_timing.yf.Ticker", return_value=mock_ticker):
            # Simulated check in European morning (after release hour and within publication window, but Reported EPS is still NaN)
            check_time = datetime.datetime(2026, 10, 29, 8, 0, tzinfo=datetime.timezone.utc)
            is_rel, data, reason = earnings_timing.verify_earnings_release_status(
                "MSFT", "MSFT", lookback_days=1, check_time=check_time
            )
            self.assertFalse(is_rel)
            self.assertIn("Reported EPS is still NaN/pending", reason)

    def test_verified_reported_eps_allows_earnings_publication(self):
        """Verify that when release hour has passed and Reported EPS is present, verification succeeds."""
        import datetime
        import pandas as pd
        from unittest.mock import MagicMock, patch
        import earnings_timing

        mock_ticker = MagicMock()
        sched_dt = datetime.datetime(2026, 10, 28, 20, 0, tzinfo=datetime.timezone.utc)
        df = pd.DataFrame(
            [{"EPS Estimate": 4.72, "Reported EPS": 4.88, "Surprise(%)": 3.39}],
            index=[sched_dt],
        )
        mock_ticker.earnings_dates = df
        mock_ticker.info = {"currency": "USD"}
        mock_ticker.quarterly_income_stmt = pd.DataFrame()

        with patch("earnings_timing.yf.Ticker", return_value=mock_ticker):
            # Simulated check in the European morning (08:00 UTC next day) per new timing policy
            check_time = datetime.datetime(2026, 10, 29, 8, 0, tzinfo=datetime.timezone.utc)
            is_rel, data, reason = earnings_timing.verify_earnings_release_status(
                "MSFT", "MSFT", lookback_days=1, check_time=check_time
            )
            self.assertTrue(is_rel)
            self.assertEqual(data["eps_actual"], "$4.88")
            self.assertEqual(data["eps_est"], "$4.72")
            self.assertTrue(data["eps_beat"])
            self.assertEqual(data["quarter"], "Q1 FY2027")

    def test_amc_earnings_held_until_european_morning(self):
        """Verify that AMC earnings on release evening are held until European morning window."""
        import datetime
        import pandas as pd
        from unittest.mock import MagicMock, patch
        import earnings_timing

        mock_ticker = MagicMock()
        sched_dt = datetime.datetime(2026, 10, 28, 20, 0, tzinfo=datetime.timezone.utc)
        df = pd.DataFrame(
            [{"EPS Estimate": 4.72, "Reported EPS": 4.88, "Surprise(%)": 3.39}],
            index=[sched_dt],
        )
        mock_ticker.earnings_dates = df

        with patch("earnings_timing.yf.Ticker", return_value=mock_ticker):
            # Checked on the evening of release (21:30 UTC): must be held
            check_evening = datetime.datetime(2026, 10, 28, 21, 30, tzinfo=datetime.timezone.utc)
            is_rel, _, reason = earnings_timing.verify_earnings_release_status(
                "MSFT", "MSFT", lookback_days=1, check_time=check_evening
            )
            self.assertFalse(is_rel)
            self.assertIn("European morning window", reason)

            # Checked the next morning at 08:00 UTC: must be allowed
            check_morning = datetime.datetime(2026, 10, 29, 8, 0, tzinfo=datetime.timezone.utc)
            is_rel_m, _, _ = earnings_timing.verify_earnings_release_status(
                "MSFT", "MSFT", lookback_days=1, check_time=check_morning
            )
            self.assertTrue(is_rel_m)

    def test_bmo_earnings_held_until_after_us_open(self):
        """Verify that BMO earnings are held until shortly after US market open (>= 10:00 ET)."""
        import datetime
        import pandas as pd
        from unittest.mock import MagicMock, patch
        import earnings_timing

        mock_ticker = MagicMock()
        # 08:00 EDT = 12:00 UTC
        sched_dt = datetime.datetime(2026, 10, 29, 12, 0, tzinfo=datetime.timezone.utc)
        df = pd.DataFrame(
            [{"EPS Estimate": 5.10, "Reported EPS": 5.40, "Surprise(%)": 5.88}],
            index=[sched_dt],
        )
        mock_ticker.earnings_dates = df

        with patch("earnings_timing.yf.Ticker", return_value=mock_ticker):
            # Checked at 12:30 UTC (08:30 EDT - pre-market): must be held
            check_pre = datetime.datetime(2026, 10, 29, 12, 30, tzinfo=datetime.timezone.utc)
            is_rel, _, reason = earnings_timing.verify_earnings_release_status(
                "LLY", "LLY", lookback_days=1, check_time=check_pre
            )
            self.assertFalse(is_rel)
            self.assertIn("shortly after US market open", reason)

            # Checked at 14:15 UTC (10:15 EDT - after US open): must be allowed
            check_open = datetime.datetime(2026, 10, 29, 14, 15, tzinfo=datetime.timezone.utc)
            is_rel_open, _, _ = earnings_timing.verify_earnings_release_status(
                "LLY", "LLY", lookback_days=1, check_time=check_open
            )
            self.assertTrue(is_rel_open)

    def test_box3_fallback_c_b_a_and_rigid_verification(self):
        """Verify Box 3 fallback chain C -> B -> A and rigid rejection of generic boilerplate."""
        import earnings_timing
        from unittest.mock import MagicMock

        # Test rigid verification rejects boilerplate
        fluff = ["• Commenti del management e outlook strategico", "• Crescita continua"]
        ok, _, reason = earnings_timing.verify_option_c_highlights("MSFT", fluff)
        self.assertFalse(ok)
        self.assertIn("Contains forbidden generic boilerplate", reason)

        # Test valid Option C bullets pass
        valid = ["• Azure Cloud cresce del +29% YoY trainato da AI", "• Margini operativi in espansione al 45%"]
        ok, lines, _ = earnings_timing.verify_option_c_highlights("MSFT", valid)
        self.assertTrue(ok)
        self.assertEqual(len(lines), 2)

        # Test Option B when Option C is absent
        mock_t = MagicMock()
        import pandas as pd
        q_df = pd.DataFrame(
            {"2026-09-30": [40e9, 90e9]},
            index=["Operating Income", "Total Revenue"]
        )
        mock_t.quarterly_income_stmt = q_df
        res_b = earnings_timing.resolve_box3_content("MSFT", "Q1 FY2027", yf_ticker_obj=mock_t)
        self.assertEqual(res_b["mode"], "metric")
        self.assertIn("44.4%", res_b["metric"])

        # Test Option A fallback when Option B has no income statement
        mock_t_empty = MagicMock()
        mock_t_empty.quarterly_income_stmt = pd.DataFrame()
        res_a = earnings_timing.resolve_box3_content("MSFT", "Q1 FY2027", yf_ticker_obj=mock_t_empty)
        self.assertEqual(res_a["mode"], "text")
        self.assertIn("DRIVER STRATEGICO", res_a["title"])
        self.assertTrue(len(res_a["text"]) > 10)

    def test_fiscal_year_deduplication_sync(self):
        """Verify that fiscal year quarter (Q1 FY2027) prevents duplicate publishing regardless of year key."""
        import gist_storage
        from unittest.mock import patch

        fake_store = {}
        with patch.object(gist_storage, "load_data", side_effect=lambda: {"posted_earnings": fake_store}), \
             patch.object(gist_storage, "save_data", return_value=True):
            # Save using fiscal year (2027)
            gist_storage.mark_earnings_posted("MSFT", "Q1 FY2027", 2027, post_id="test-post-123")

            # Check using calendar year (2026) -> MUST RETURN TRUE!
            self.assertTrue(gist_storage.is_earnings_posted("MSFT", "Q1 FY2027", 2026))
            # Check using fiscal year (2027) -> MUST RETURN TRUE!
            self.assertTrue(gist_storage.is_earnings_posted("MSFT", "Q1 FY2027", 2027))
            # Check without explicit year -> MUST RETURN TRUE!
            self.assertTrue(gist_storage.is_earnings_posted("MSFT", "Q1 FY2027"))

    def test_publish_earnings_for_ticker_rejects_missing_eps_actual(self):
        """Calling publish_earnings_for_ticker without eps_actual on an unreleased ticker must reject."""
        from unittest.mock import patch

        with patch("earnings_timing.verify_earnings_release_status", return_value=(False, None, "Market release time not reached")):
            res = event_monitor.publish_earnings_for_ticker("MSFT", dry_run=True)
            self.assertFalse(res["success"])
            self.assertIn("Reported EPS not released/verified", res["error"])

    def test_post_verifier_blocks_mock_earnings_figures(self):
        """Ensure post_verifier strictly blocks hallucinated mock figures ($1.85 vs $1.75, $986.0B)."""
        import post_verifier

        mock_post = (
            "Trimestrale Q4 2026 per $MSFT.\n"
            "- EPS: $1.85 vs $1.75 stimati (beat netto)\n"
            "- Ricavi: $331,8B con crescita del +24% YoY"
        )
        is_clean, issues, _ = post_verifier.verify_post_deterministic(mock_post)
        self.assertFalse(is_clean)
        self.assertTrue(any("Allucinazione dati finanziari mock" in i for i in issues))
        self.assertTrue(any("Allucinazione ricavi trimestrali" in i for i in issues))


if __name__ == "__main__":
    unittest.main()
