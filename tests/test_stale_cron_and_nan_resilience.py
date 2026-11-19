#!/usr/bin/env python3
"""
Unit tests verifying fixes for:
1. Schedule window guard preventing stale/delayed GitHub Actions fallback crons
   from running hours later across UTC midnight.
2. Trading-day timezone + cooldown deduplication in gist_storage.
3. Yahoo Finance trailing Close=NaN repair & drop resilience in finance_fetcher
   and formatter.
4. Pre-publication market data quality circuit breaker in data_collector.
"""

import math
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

import data_collector
import finance_fetcher
import formatter
import gist_storage
import schedule_guard


class TestScheduleGuard(unittest.TestCase):
    def test_rejects_delayed_stale_fallback_crons(self):
        # Nov 18 02:35 UTC (21:35 EST Nov 17) - run 44224420051
        ok, reason = schedule_guard.is_schedule_within_window(
            "U.S. market close",
            "schedule",
            now_utc=datetime(2026, 11, 18, 2, 35, tzinfo=timezone.utc),
        )
        self.assertFalse(ok, reason)

        # Nov 19 01:59 UTC (20:59 EST Nov 18) - run 44440996769 (broken recap)
        ok, reason = schedule_guard.is_schedule_within_window(
            "U.S. market close",
            "schedule",
            now_utc=datetime(2026, 11, 19, 1, 59, tzinfo=timezone.utc),
        )
        self.assertFalse(ok, reason)

        # Nov 17 00:21 UTC (01:21 CET Nov 17) - delayed Daily crypto recap
        ok, reason = schedule_guard.is_schedule_within_window(
            "Daily crypto recap",
            "schedule",
            now_utc=datetime(2026, 11, 17, 0, 21, tzinfo=timezone.utc),
        )
        self.assertFalse(ok, reason)

        # Nov 16 01:29 UTC (02:29 CET Monday) - delayed Weekly recap (Sun)
        ok, reason = schedule_guard.is_schedule_within_window(
            "Weekly recap (Sun)",
            "schedule",
            now_utc=datetime(2026, 11, 16, 1, 29, tzinfo=timezone.utc),
        )
        self.assertFalse(ok, reason)

        # Nov 18 21:58 UTC (16:58 EST) - delayed U.S. market open
        ok, reason = schedule_guard.is_schedule_within_window(
            "U.S. market open",
            "schedule",
            now_utc=datetime(2026, 11, 18, 21, 58, tzinfo=timezone.utc),
        )
        self.assertFalse(ok, reason)

    def test_accepts_ontime_est_and_edt_fallback_crons(self):
        valid_cases = [
            # U.S. market close: EST & EDT
            ("U.S. market close", datetime(2026, 11, 18, 21, 5, tzinfo=timezone.utc)),
            ("U.S. market close", datetime(2026, 7, 15, 20, 5, tzinfo=timezone.utc)),
            # U.S. market open: EST & EDT
            ("U.S. market open", datetime(2026, 11, 18, 14, 35, tzinfo=timezone.utc)),
            ("U.S. market open", datetime(2026, 7, 15, 13, 35, tzinfo=timezone.utc)),
            # European market open: CET & CEST
            ("European market open", datetime(2026, 11, 18, 8, 20, tzinfo=timezone.utc)),
            ("European market open", datetime(2026, 7, 15, 7, 20, tzinfo=timezone.utc)),
            # Daily crypto recap: CET & CEST
            ("Daily crypto recap", datetime(2026, 11, 18, 16, 20, tzinfo=timezone.utc)),
            ("Daily crypto recap", datetime(2026, 7, 15, 16, 20, tzinfo=timezone.utc)),
            # Stock focus (including parameterized form)
            ("Stock focus", datetime(2026, 11, 18, 12, 30, tzinfo=timezone.utc)),
            ("Stock focus:NVDA", datetime(2026, 7, 15, 12, 30, tzinfo=timezone.utc)),
            # Copy trading post: weekday & Saturday
            ("Copy trading post", datetime(2026, 11, 18, 11, 30, tzinfo=timezone.utc)),
            ("Copy trading post", datetime(2026, 11, 21, 10, 15, tzinfo=timezone.utc)),
            # Community Poll: Mon/Wed/Fri
            ("Community Poll", datetime(2026, 11, 18, 10, 30, tzinfo=timezone.utc)),
            # Weekly recap (Sat & Sun)
            ("Weekly recap (Sat)", datetime(2026, 11, 21, 9, 30, tzinfo=timezone.utc)),
            ("Weekly recap (Sun)", datetime(2026, 11, 22, 16, 0, tzinfo=timezone.utc)),
            ("Weekly recap (Sun)", datetime(2026, 11, 22, 21, 30, tzinfo=timezone.utc)),
        ]
        for session, dt in valid_cases:
            ok, reason = schedule_guard.is_schedule_within_window(session, "schedule", now_utc=dt)
            self.assertTrue(ok, f"{session} at {dt}: {reason}")

        # Negative day-of-week checks
        ok_sun_copy, _ = schedule_guard.is_schedule_within_window(
            "Copy trading post", "schedule", now_utc=datetime(2026, 11, 22, 11, 30, tzinfo=timezone.utc)
        )
        self.assertFalse(ok_sun_copy)
        ok_tue_poll, _ = schedule_guard.is_schedule_within_window(
            "Community Poll", "schedule", now_utc=datetime(2026, 11, 17, 10, 30, tzinfo=timezone.utc)
        )
        self.assertFalse(ok_tue_poll)

    def test_monthly_recap_window_and_bypass_triggers(self):
        # Last day of month (Nov 30) 21:05 UTC = 16:05 EST -> valid
        ok, reason = schedule_guard.is_schedule_within_window(
            "Monthly recap",
            "schedule",
            now_utc=datetime(2026, 11, 30, 21, 5, tzinfo=timezone.utc),
        )
        self.assertTrue(ok, reason)

        # Next day 02:00 UTC (21:00 EST Nov 30) -> outside 15:00-19:00 NY -> rejected
        ok_late, _ = schedule_guard.is_schedule_within_window(
            "Monthly recap",
            "schedule",
            now_utc=datetime(2026, 12, 1, 2, 0, tzinfo=timezone.utc),
        )
        self.assertFalse(ok_late)

        # Nov 29 21:05 UTC -> not last day -> rejected
        ok_early_day, _ = schedule_guard.is_schedule_within_window(
            "Monthly recap",
            "schedule",
            now_utc=datetime(2026, 11, 29, 21, 5, tzinfo=timezone.utc),
        )
        self.assertFalse(ok_early_day)

        # repository_dispatch, workflow_dispatch, and force_run=True always bypass
        stale_dt = datetime(2026, 11, 19, 1, 59, tzinfo=timezone.utc)
        for trigger in ("repository_dispatch", "workflow_dispatch"):
            ok_trig, _ = schedule_guard.is_schedule_within_window(
                "U.S. market close", trigger, now_utc=stale_dt
            )
            self.assertTrue(ok_trig)

        ok_force, _ = schedule_guard.is_schedule_within_window(
            "U.S. market close", "schedule", now_utc=stale_dt, force_run=True
        )
        self.assertTrue(ok_force)


class TestGistDeduplicationAndCooldown(unittest.TestCase):
    def setUp(self):
        self.store = {"session_runs": {}}

    def _fake_load(self):
        return self.store

    def _fake_save(self, data):
        self.store = data
        return True

    def test_cross_midnight_and_next_day_us_close(self):
        with patch.object(gist_storage, "load_data", side_effect=self._fake_load), \
             patch.object(gist_storage, "save_data", side_effect=self._fake_save):
            gist_storage.mark_session_run(
                "U.S. market close",
                now_utc=datetime(2026, 11, 17, 21, 12, tzinfo=timezone.utc),
            )
            self.assertIn("2026-11-17:U.S. market close", self.store["session_runs"])

            # Cross-midnight UTC (Nov 18 02:35 UTC is still Nov 17 in NY & within 14h cooldown)
            self.assertTrue(
                gist_storage.has_session_run_today(
                    "U.S. market close",
                    now_utc=datetime(2026, 11, 18, 2, 35, tzinfo=timezone.utc),
                )
            )
            # Actual next trading day (Nov 18 21:02 UTC = Nov 18 in NY, ~23.8h later) -> allowed
            self.assertFalse(
                gist_storage.has_session_run_today(
                    "U.S. market close",
                    now_utc=datetime(2026, 11, 18, 21, 2, tzinfo=timezone.utc),
                )
            )

    def test_crypto_recap_cross_midnight_and_sat_to_sun(self):
        with patch.object(gist_storage, "load_data", side_effect=self._fake_load), \
             patch.object(gist_storage, "save_data", side_effect=self._fake_save):
            gist_storage.mark_session_run(
                "Daily crypto recap",
                now_utc=datetime(2026, 11, 16, 17, 10, tzinfo=timezone.utc),
            )
            # Delayed cron arriving at 00:21 UTC (within 14h cooldown) -> duplicate
            self.assertTrue(
                gist_storage.has_session_run_today(
                    "Daily crypto recap",
                    now_utc=datetime(2026, 11, 17, 0, 21, tzinfo=timezone.utc),
                )
            )

            # Reset for Sat 18:00 CET (17:00 UTC) -> Sun 14:00 CET (13:00 UTC) = 20h later
            self.store["session_runs"] = {}
            gist_storage.mark_session_run(
                "Daily crypto recap",
                now_utc=datetime(2026, 11, 21, 17, 0, tzinfo=timezone.utc),
            )
            self.assertFalse(
                gist_storage.has_session_run_today(
                    "Daily crypto recap",
                    now_utc=datetime(2026, 11, 22, 13, 0, tzinfo=timezone.utc),
                )
            )

    def test_weekly_sun_cooldown_and_month_boundary_pruning_and_clear(self):
        with patch.object(gist_storage, "load_data", side_effect=self._fake_load), \
             patch.object(gist_storage, "save_data", side_effect=self._fake_save):
            gist_storage.mark_session_run(
                "Weekly recap (Sun)",
                now_utc=datetime(2026, 11, 15, 21, 10, tzinfo=timezone.utc),
            )
            # Delayed run on Monday 01:29 UTC -> blocked by 48h weekly cooldown
            self.assertTrue(
                gist_storage.has_session_run_today(
                    "Weekly recap (Sun)",
                    now_utc=datetime(2026, 11, 16, 1, 29, tzinfo=timezone.utc),
                )
            )

            # Month boundary: Nov 30 entry survives Dec 1 pruning, Oct 1 entry is pruned
            self.store["session_runs"]["2026-10-01:U.S. market close"] = "2026-10-01T20:10:00+00:00"
            gist_storage.mark_session_run(
                "U.S. market close",
                now_utc=datetime(2026, 11, 30, 21, 10, tzinfo=timezone.utc),
            )
            gist_storage.mark_session_run(
                "European market open",
                now_utc=datetime(2026, 12, 1, 8, 25, tzinfo=timezone.utc),
            )
            self.assertIn("2026-11-30:U.S. market close", self.store["session_runs"])
            self.assertNotIn("2026-10-01:U.S. market close", self.store["session_runs"])

            # Clear helper
            self.assertTrue(gist_storage.clear_session_run("U.S. market close", date_str="2026-11-30"))
            self.assertNotIn("2026-11-30:U.S. market close", self.store["session_runs"])
            self.assertFalse(gist_storage.clear_session_run("U.S. market close", date_str="2026-11-30"))


class TestNanHistorySanitization(unittest.TestCase):
    def setUp(self):
        finance_fetcher._BENCHMARKS_DAILY_CACHE["timestamp"] = 0.0
        finance_fetcher._BENCHMARKS_DAILY_CACHE["data"] = None

    def tearDown(self):
        finance_fetcher._BENCHMARKS_DAILY_CACHE["timestamp"] = 0.0
        finance_fetcher._BENCHMARKS_DAILY_CACHE["data"] = None

    def test_repairs_trailing_nan_with_matching_date_and_scale(self):
        idx = pd.to_datetime(["2026-11-17", "2026-11-18"]).tz_localize("Europe/London")
        df = pd.DataFrame({"Close": [13802.0, float("nan")], "Volume": [1629678, 1591835]}, index=idx)
        rmt = int(datetime(2026, 11, 18, 17, 31, tzinfo=timezone.utc).timestamp())
        info = {"regularMarketPrice": 13646.0, "regularMarketTime": rmt}

        repaired = finance_fetcher._sanitize_history_close(df, info=info, symbol="AZN.L")
        self.assertEqual(len(repaired), 2)
        self.assertAlmostEqual(float(repaired["Close"].iloc[-1]), 13646.0)

    def test_drops_trailing_nan_on_date_or_scale_mismatch(self):
        idx = pd.to_datetime(["2026-11-17", "2026-11-18"]).tz_localize("Europe/London")
        df = pd.DataFrame({"Close": [13802.0, float("nan")]}, index=idx)

        # Date mismatch (info from Nov 17 instead of Nov 18)
        rmt_wrong_date = int(datetime(2026, 11, 17, 17, 30, tzinfo=timezone.utc).timestamp())
        dropped_date = finance_fetcher._sanitize_history_close(
            df,
            info={"regularMarketPrice": 13646.0, "regularMarketTime": rmt_wrong_date},
            symbol="AZN.L",
        )
        self.assertEqual(len(dropped_date), 1)
        self.assertAlmostEqual(float(dropped_date["Close"].iloc[-1]), 13802.0)

        # Scale mismatch (100x GBP vs GBX)
        rmt_match = int(datetime(2026, 11, 18, 17, 30, tzinfo=timezone.utc).timestamp())
        dropped_scale = finance_fetcher._sanitize_history_close(
            df,
            info={"regularMarketPrice": 136.46, "regularMarketTime": rmt_match},
            symbol="AZN.L",
        )
        self.assertEqual(len(dropped_scale), 1)
        self.assertAlmostEqual(float(dropped_scale["Close"].iloc[-1]), 13802.0)

    def test_range_index_safe_and_benchmark_nan_recovery(self):
        range_df = pd.DataFrame({"Close": [100.0, 101.5]})
        out = finance_fetcher._sanitize_history_close(range_df, info=None, symbol="TEST")
        self.assertEqual(len(out), 2)
        self.assertAlmostEqual(float(out["Close"].iloc[-1]), 101.5)

        idx = pd.to_datetime(["2026-11-17", "2026-11-18"]).tz_localize("America/New_York")
        fxi_df = pd.DataFrame({"Close": [32.88, float("nan")]}, index=idx)
        fxi_rmt = int(datetime(2026, 11, 18, 21, 0, tzinfo=timezone.utc).timestamp())

        class _FakeTicker:
            def __init__(self, sym):
                self.sym = sym

            @property
            def info(self):
                if self.sym == "FXI":
                    return {"regularMarketPrice": 32.39, "regularMarketTime": fxi_rmt}
                return {}

            def history(self, period="5d", interval="1d"):
                if self.sym == "FXI":
                    return fxi_df.copy()
                return pd.DataFrame({"Close": [100.0, 101.0]})

        with patch("finance_fetcher.yf.Ticker", side_effect=lambda s: _FakeTicker(s)):
            perf = finance_fetcher.fetch_benchmarks_daily_performance()

        self.assertIn("CHINA50", perf)
        self.assertTrue(math.isfinite(perf["CHINA50"]))
        self.assertAlmostEqual(perf["CHINA50"], -1.49, places=2)

    def test_formatter_filters_data_degraded_tickers(self):
        stock_data = {
            "NVDA": {
                "company_name": "NVIDIA",
                "daily_change": 2.5,
                "weekly_change": 4.0,
                "monthly_change": 5.0,
                "yearly_change": 30.0,
                "has_traded_today": True,
                "data_degraded": False,
            },
            "ABBV": {
                "company_name": "AbbVie",
                "daily_change": 0.0,
                "weekly_change": 0.0,
                "monthly_change": 0.0,
                "yearly_change": 0.0,
                "has_traded_today": True,
                "data_degraded": True,
            },
        }
        with patch.dict(os.environ, {"MARKET_SESSION": "U.S. market close"}), \
             patch("formatter.ai_news_generator.get_recent_tags", return_value=[]), \
             patch("formatter.ai_news_generator.generate_market_news_recap", return_value="Mock AI news"), \
             patch("formatter.ai_news_generator.get_why_copy_message", return_value=""), \
             patch.object(formatter, "API_TRACKER_AVAILABLE", False):
            recap = formatter.generate_recap(
                stock_data,
                portfolio_daily=1.2,
                sheets_data={"five_year_return": 176.0, "yearly_performance": 2.1},
                benchmark_data={"SPX500": 124.0},
                ath_distance=-24.0,
            )
        self.assertIn("NVDA", recap)
        self.assertNotIn("ABBV +0.00%", recap)


class TestDataCollectorCircuitBreaker(unittest.TestCase):
    def _build_portfolio_sample(self, us_active=True, degraded_count=0):
        data = {}
        # 17 US stocks, 16 EU stocks, 3 HK stocks, 1 crypto = 37 symbols
        for i in range(17):
            is_deg = i < degraded_count
            data[f"US{i}"] = {
                "yahoo_ticker": f"US{i}",
                "daily_change": 0.0 if (is_deg or not us_active) else (1.1 + i * 0.1),
                "weekly_change": 0.0 if is_deg else 2.5,
                "monthly_change": 0.0 if is_deg else 3.0,
                "yearly_change": 0.0 if is_deg else 15.0,
                "has_traded_today": False if is_deg else us_active,
                "is_us_stock": True,
                "data_degraded": is_deg,
            }
        for i in range(16):
            idx = 17 + i
            is_deg = idx < degraded_count
            data[f"EU{i}.MI"] = {
                "yahoo_ticker": f"EU{i}.MI",
                "daily_change": 0.0 if is_deg else -0.8,
                "weekly_change": 0.0 if is_deg else 1.2,
                "monthly_change": 0.0 if is_deg else 2.0,
                "yearly_change": 0.0 if is_deg else 8.0,
                "has_traded_today": False,
                "is_us_stock": False,
                "data_degraded": is_deg,
            }
        for i in range(3):
            data[f"0{i+1}00.HK"] = {
                "yahoo_ticker": f"0{i+1}00.HK",
                "daily_change": -0.5,
                "weekly_change": -1.0,
                "monthly_change": -2.0,
                "yearly_change": 10.0,
                "has_traded_today": True,
                "is_us_stock": False,
                "data_degraded": False,
            }
        data["TRX"] = {
            "yahoo_ticker": "TRX-USD",
            "daily_change": 0.72,
            "weekly_change": 1.5,
            "monthly_change": -0.8,
            "yearly_change": 8.3,
            "has_traded_today": True,
            "is_us_stock": True,
            "data_degraded": False,
        }
        return data

    def test_blocks_nov19_degraded_us_close_and_catastrophic_degradation(self):
        nov19_broken = self._build_portfolio_sample(us_active=False, degraded_count=33)
        ok, reason = data_collector.validate_session_market_data(nov19_broken, "U.S. market close")
        self.assertFalse(ok, reason)

        # Catastrophic >50% degradation also blocks Weekly recap (Sat)
        ok_sat_deg, reason_sat = data_collector.validate_session_market_data(
            nov19_broken, "Weekly recap (Sat)"
        )
        self.assertFalse(ok_sat_deg, reason_sat)

        # Empty stock_data blocked
        ok_empty, _ = data_collector.validate_session_market_data({}, "Daily crypto recap")
        self.assertFalse(ok_empty)

    def test_allows_healthy_us_close_and_weekend_sessions(self):
        healthy_us = self._build_portfolio_sample(us_active=True, degraded_count=0)
        ok, reason = data_collector.validate_session_market_data(healthy_us, "U.S. market close")
        self.assertTrue(ok, reason)

        # Weekend: US & EU stocks have has_traded_today=False and daily_change=0,
        # but non-zero weekly/monthly/yearly metrics -> valid for Weekly recap & Crypto recap
        weekend_data = self._build_portfolio_sample(us_active=False, degraded_count=0)
        ok_sat, reason_sat = data_collector.validate_session_market_data(
            weekend_data, "Weekly recap (Sat)"
        )
        self.assertTrue(ok_sat, reason_sat)

        ok_crypto, reason_crypto = data_collector.validate_session_market_data(
            weekend_data, "Daily crypto recap"
        )
        self.assertTrue(ok_crypto, reason_crypto)


if __name__ == "__main__":
    unittest.main()
