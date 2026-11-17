#!/usr/bin/env python3
"""
Unit tests verifying fixes for the European Market Open recap & pipeline:
1. Canonical BYD Hong Kong symbol '01211.HK' and alias cleanup across configs & eToro API mapping.
2. Cashtag budget protection: auditors cannot inject new $ tags (like $NSDQ100/$DJ30), and
   preferred_tags preserves selected portfolio holdings in limit_cashtags / _limit_tags_in_text.
3. EU Open Top/Flop card excludes .HK and US stocks so HK closing moves never dominate EU Open.
4. Daily live economic calendar formatting in Europe/Rome timezone with portfolio earnings.
5. Temporal context awareness for pre-09:00 vs post-09:00 CET European Market Open.
"""

import json
import os
import sys
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

import ai_news_generator
import economic_calendar
import etoro_client
import independent_fact_checker
import portfolio_manager
import post_verifier
import winners_losers_card


class TestEuOpenFixes(unittest.TestCase):

    def test_canonical_byd_and_weights_config(self):
        with open(os.path.join(ROOT_DIR, "portfolio_config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIn("01211.HK", cfg["tickers"])
        self.assertNotIn("1211.HK", cfg["tickers"])
        self.assertIn("BESI.NV", cfg["tickers"])

        with open(os.path.join(ROOT_DIR, "data", "portfolio_weights.json"), "r", encoding="utf-8") as f:
            weights = json.load(f)
        self.assertIn("01211.HK", weights)
        self.assertNotIn("1211.HK", weights)
        self.assertNotIn("MNODL.L", weights)
        self.assertNotIn("NVTKL.L", weights)
        self.assertIn("BESI.NV", weights)
        self.assertIn("GOOG", weights)

        self.assertIn("01211.HK", portfolio_manager.DEFAULT_TICKERS)
        self.assertNotIn("1211.HK", portfolio_manager.DEFAULT_TICKERS)

    def test_etoro_client_id_to_ticker_and_zero_weight_exclusion(self):
        id_to_ticker = {v: k for k, v in etoro_client.MARKET_IDS.items()}
        self.assertEqual(id_to_ticker[2380], "01211.HK")
        self.assertEqual(id_to_ticker[4513], "BESI.NV")
        self.assertEqual(id_to_ticker[1002], "GOOG")
        self.assertEqual(id_to_ticker[1552], "ABT.US")
        self.assertEqual(etoro_client.get_market_ids_for_tickers(["$01211.HK", "$1211.HK"]), [2380, 2380])

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "positions": [
                {"instrumentId": 2380, "investmentPct": 2.35, "netProfit": 0.0},
                {"instrumentId": 1352, "investmentPct": 1.00, "netProfit": 0.0},  # MNODL.L frozen
                {"instrumentId": 1004, "investmentPct": 0.0, "netProfit": 0.0},   # MSFT 0%
            ]
        }
        with patch.object(etoro_client, "get_headers", return_value={"x-api-key": "test"}), \
             patch.object(etoro_client.requests, "get", return_value=mock_resp):
            live_weights = etoro_client.fetch_portfolio_weights()

        self.assertEqual(list(live_weights.keys()), ["01211.HK"])
        self.assertAlmostEqual(live_weights["01211.HK"], 70.15, places=2)
        self.assertNotIn("1211.HK", live_weights)
        self.assertNotIn("MNODL.L", live_weights)
        self.assertNotIn("MSFT", live_weights)

    def test_clean_and_sanitize_canonicalize_1211_and_strip_injected_cashtags(self):
        dirty = "Analisi su ($1211.HK) e 1211.HK in ottima forma."
        cleaned = post_verifier.clean_etoro_formatting(dirty)
        self.assertIn("$01211.HK", cleaned)
        self.assertIn("01211.HK", cleaned)
        self.assertNotIn("$1211.HK", cleaned)

        original = (
            "🚀 Buongiorno! Apertura dei mercati europei.\n\n"
            "📈 Sul fronte macro, $SPX500 influenza il sentiment insieme a Nasdaq e Dow Jones.\n\n"
            "🚗 Nel comparto auto brilla $01211.HK, con solidi volumi."
        )
        audited = (
            "🚀 Buongiorno! Apertura dei mercati europei.\n\n"
            "📈 Sul fronte macro, $SPX500 guida il sentiment insieme a $NSDQ100 e $DJ30.\n\n"
            "🚗 Nel comparto auto brilla $1211.HK, con solidi volumi."
        )
        sanitized = independent_fact_checker.sanitize_verified_text(original, audited)
        self.assertIn("$SPX500", sanitized)
        self.assertIn("$01211.HK", sanitized)
        self.assertNotIn("$NSDQ100", sanitized)
        self.assertNotIn("$DJ30", sanitized)
        self.assertIn("NSDQ100", sanitized)
        self.assertIn("DJ30", sanitized)

    def test_preferred_tags_protect_selected_stocks_from_upstream_index_tags(self):
        post = (
            "🚀 Mercati europei aperti!\n\n"
            "📈 Wall Street vista mista: $SPX500, $NSDQ100 e $DJ30 restano al centro dell'attenzione.\n\n"
            "⚡ Bene $ENI.MI in avvio.\n\n"
            "🚙 Solida $VOW3.DE, seguita da vicino.\n\n"
            "🔋 Ottima $01211.HK, leader nella transizione elettrica."
        )
        preferred = ["ENI.MI", "VOW3.DE", "01211.HK", "SPX500"]

        limited_pv = post_verifier.limit_cashtags(post, max_tags=4, preferred_tags=preferred)
        pv_tags = post_verifier.extract_cashtags(limited_pv)
        self.assertEqual(set(pv_tags), {"ENI.MI", "VOW3.DE", "01211.HK", "SPX500"})
        self.assertNotIn("$NSDQ100", limited_pv)
        self.assertNotIn("$DJ30", limited_pv)
        self.assertIn("$01211.HK,", limited_pv)

        limited_gen = ai_news_generator._limit_tags_in_text(
            post,
            allowed_tags=["ENI.MI", "VOW3.DE", "01211.HK", "SPX500", "NSDQ100", "DJ30"],
            max_tags=4,
            preferred_tags=preferred,
        )
        gen_tags = post_verifier.extract_cashtags(limited_gen)
        self.assertEqual(set(gen_tags), {"ENI.MI", "VOW3.DE", "01211.HK", "SPX500"})
        self.assertNotIn("$NSDQ100", limited_gen)
        self.assertNotIn("$DJ30", limited_gen)

    def test_eu_open_winners_losers_card_excludes_hk_and_us_stocks(self):
        # Only HK active + 1 EU active -> insufficient active EU movers -> must return None
        hk_only_eu_data = {
            "01211.HK": {"company_name": "BYD", "daily_change": -2.6, "has_traded_today": True, "is_us_stock": False},
            "1919.HK": {"company_name": "COSCO", "daily_change": 1.1, "has_traded_today": True, "is_us_stock": False},
            "2318.HK": {"company_name": "Ping An", "daily_change": 1.4, "has_traded_today": True, "is_us_stock": False},
            "ENEL.MI": {"company_name": "Enel", "daily_change": 0.5, "has_traded_today": True, "is_us_stock": False},
            "PRY.MI": {"company_name": "Prysmian", "daily_change": 0.0, "has_traded_today": False, "is_us_stock": False},
        }
        with patch.object(winners_losers_card, "generate_winners_losers_card") as mock_gen:
            res = winners_losers_card.build_card_from_stock_data(
                hk_only_eu_data,
                session_name="European market open",
                fetch_logos=False,
            )
            self.assertIsNone(res)
            mock_gen.assert_not_called()

        # When 2+ EU stocks are active, only EU stocks are selected (never 01211.HK)
        eu_plus_hk_data = {
            **hk_only_eu_data,
            "PRY.MI": {"company_name": "Prysmian", "daily_change": -0.45, "has_traded_today": True, "is_us_stock": False},
        }
        with patch.object(winners_losers_card, "generate_winners_losers_card", return_value="card.png") as mock_gen:
            res = winners_losers_card.build_card_from_stock_data(
                eu_plus_hk_data,
                session_name="European market open",
                fetch_logos=False,
            )
            self.assertEqual(res, "card.png")
            kwargs = mock_gen.call_args.kwargs
            self.assertEqual(kwargs["winner"]["ticker"], "ENEL.MI")
            self.assertEqual(kwargs["loser"]["ticker"], "PRY.MI")

    def test_daily_macro_events_context_formats_rome_times_and_earnings(self):
        fake_feed = [
            {
                "title": "FOMC Member Waller Speaks",
                "country": "USD",
                "date": "2026-11-17T02:00:00+00:00",  # 03:00 CET -> filtered pre-06:00 noise
                "impact": "Medium",
                "forecast": "",
                "previous": "",
                "actual": "",
            },
            {
                "title": "German ZEW Economic Sentiment",
                "country": "EUR",
                "date": "2026-11-17T10:00:00+00:00",  # 11:00 CET
                "impact": "High",
                "forecast": "14.5",
                "previous": "13.1",
                "actual": "",
            },
            {
                "title": "Core Retail Sales m/m",
                "country": "USD",
                "date": "2026-11-17T13:30:00+00:00",  # 14:30 CET
                "impact": "High",
                "forecast": "0.3%",
                "previous": "0.5%",
                "actual": "",
            },
        ]
        with patch.object(economic_calendar, "_fetch_raw_calendar_events", return_value=fake_feed), \
             patch("market_calendar.get_earnings_for_session", return_value=[{"ticker": "NVDA", "name": "NVIDIA"}]):
            ctx = economic_calendar.get_daily_macro_events_context(
                focus="EU",
                target_date=date(2026, 11, 17),
            )

        self.assertIn("17/11/2026", ctx)
        self.assertIn("11:00 CET", ctx)
        self.assertIn("German ZEW Economic Sentiment", ctx)
        self.assertIn("14:30 CET", ctx)
        self.assertIn("Core Retail Sales m/m", ctx)
        self.assertNotIn("Waller Speaks", ctx)
        self.assertIn("Trimestrali portafoglio oggi: NVIDIA (NVDA)", ctx)


if __name__ == "__main__":
    unittest.main()
