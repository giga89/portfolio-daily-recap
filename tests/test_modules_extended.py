#!/usr/bin/env python3
"""
Extended Unit Test Suite for Core & Auxiliary Modules
=====================================================
Tests market_calendar, formatter, educational_series_publisher,
post_verifier, etoro_sender, ai_model_cascade, ai_comment_responder,
dividend_tracker, poll_generator, and ai_news_generator helpers.
"""

import datetime
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import ai_comment_responder
import ai_model_cascade
import ai_news_generator
import dividend_tracker
import educational_series_publisher
import etoro_sender
import formatter
import market_calendar
import poll_generator
import post_verifier


class TestMarketCalendarModule(unittest.TestCase):
    """Test deterministic US & European market holiday computation."""

    def test_easter_computation_known_years(self):
        self.assertEqual(market_calendar.get_easter_date(2025), datetime.date(2025, 4, 20))
        self.assertEqual(market_calendar.get_easter_date(2026), datetime.date(2026, 4, 5))
        self.assertEqual(market_calendar.get_easter_date(2027), datetime.date(2027, 3, 28))

    def test_us_market_holidays_2026(self):
        holidays_2026 = market_calendar.get_us_market_holidays(2026)
        # July 4, 2026 is a Saturday -> observed Friday July 3, 2026
        self.assertIn(datetime.date(2026, 7, 3), holidays_2026)
        self.assertEqual(holidays_2026[datetime.date(2026, 7, 3)], "Independence Day")
        # Good Friday 2026 is April 3, 2026
        self.assertIn(datetime.date(2026, 4, 3), holidays_2026)
        # Christmas 2026 is Dec 25, 2026
        self.assertIn(datetime.date(2026, 12, 25), holidays_2026)

    def test_is_us_market_holiday_true_and_false(self):
        is_hol, name = market_calendar.is_us_market_holiday(datetime.date(2026, 12, 25))
        self.assertTrue(is_hol)
        self.assertIn("Christmas", name)

        is_hol2, name2 = market_calendar.is_us_market_holiday(datetime.date(2026, 10, 27))
        self.assertFalse(is_hol2)
        self.assertIsNone(name2)

    def test_eu_universal_holidays(self):
        eu_hols = market_calendar.get_eu_universal_holidays(2026)
        self.assertIn(datetime.date(2026, 1, 1), eu_hols)
        self.assertIn(datetime.date(2026, 4, 3), eu_hols)   # Good Friday
        self.assertIn(datetime.date(2026, 4, 6), eu_hols)   # Easter Monday
        self.assertIn(datetime.date(2026, 12, 25), eu_hols)
        self.assertIn(datetime.date(2026, 12, 26), eu_hols)


class TestFormatterModule(unittest.TestCase):
    """Test recap formatting, NaN filtering, and sanctions exclusion."""

    @patch("formatter.ai_news_generator.generate_market_news_recap", return_value="Analisi di mercato test.")
    def test_generate_recap_filters_nan_and_excluded_tickers(self, _mock_ai):
        stock_data = {
            "NVDA": {
                "company_name": "NVIDIA",
                "daily_change": 3.5,
                "weekly_change": 5.0,
                "monthly_change": 10.0,
                "yearly_change": 80.0,
                "has_traded_today": True,
            },
            "MNODL.L": {
                "company_name": "Norilsk",
                "daily_change": 50.0,
                "weekly_change": 50.0,
                "monthly_change": 50.0,
                "yearly_change": 50.0,
                "has_traded_today": True,
            },
            "BAD_NAN": {
                "company_name": "NaN Corp",
                "daily_change": float("nan"),
                "weekly_change": 1.0,
                "monthly_change": 2.0,
                "yearly_change": 3.0,
                "has_traded_today": True,
            },
        }
        sheets_data = {"five_year_return": 200.0, "yearly_avg": 20.0}
        with patch.dict(os.environ, {"MARKET_SESSION": "U.S. market close"}):
            recap = formatter.generate_recap(
                stock_data=stock_data,
                portfolio_daily=1.8,
                sheets_data=sheets_data,
                benchmark_data={"S&P 500": 15.0, "NASDAQ 100": 20.0},
            )
        self.assertIn("NVDA", recap)
        self.assertNotIn("MNODL.L", recap)
        self.assertNotIn("BAD_NAN", recap)


class TestEducationalSeriesPublisherModule(unittest.TestCase):
    """Test episode rotation and series JSON integrity."""

    def test_load_series_episodes_and_rotation(self):
        episodes = educational_series_publisher.load_series_episodes()
        self.assertGreaterEqual(len(episodes), 20)
        for ep in episodes:
            self.assertIn("episode", ep)
            self.assertIn("title", ep)
            self.assertIn("post_content", ep)
            self.assertNotIn("#", ep["post_content"])

        # Rotation wrap-around
        state_zero = {"last_published_episode": 0}
        self.assertEqual(
            educational_series_publisher.get_next_episode_number(state_zero, len(episodes)),
            1,
        )
        state_last = {"last_published_episode": len(episodes)}
        self.assertEqual(
            educational_series_publisher.get_next_episode_number(state_last, len(episodes)),
            1,
        )


class TestEtoroSenderFormatting(unittest.TestCase):
    """Test eToro HTML stripping, markdown cleanup, and cashtag preservation."""

    def test_strip_html_and_build_etoro_post_text(self):
        raw = "<b>Titolo</b> con **grassetto** e #hashtag inutile su $NVDA e $PLTR."
        formatted = etoro_sender.build_etoro_post_text(raw)
        self.assertNotIn("<b>", formatted)
        self.assertNotIn("**", formatted)
        self.assertNotIn("#hashtag", formatted)
        self.assertIn("$NVDA", formatted)
        self.assertIn("$PLTR", formatted)


class TestAiModelCascadeModule(unittest.TestCase):
    """Test model cascade constants and helper functions."""

    def test_default_gemini_models_non_empty_and_unique(self):
        models = ai_model_cascade.DEFAULT_GEMINI_MODELS
        self.assertTrue(len(models) >= 2)
        self.assertEqual(len(models), len(set(models)))


class TestPostVerifierDeterministicRules(unittest.TestCase):
    """Test deterministic fast-gate rules in post_verifier.py."""

    def test_blocks_accumulating_etfs_with_dividend_claims(self):
        for acc_ticker in ["$WDEF.L", "$IB01.L", "$INDO.PA", "$PPFB.DE"]:
            text = f"Ottimo rendimento cedolare e dividendo trimestrale per {acc_ticker} in portafoglio."
            ok, issues, _ = post_verifier.verify_post_deterministic(text)
            self.assertFalse(ok, f"Accumulating ETF {acc_ticker} with dividend claim must be blocked")
            self.assertTrue(len(issues) > 0)

    def test_blocks_purged_tickers_deterministically(self):
        for purged in ["$XEON.DE", "$SPCX.RTH", "$MAU.PA"]:
            text = f"Manteniamo una quota strategica su {purged} nel lungo periodo."
            ok, issues, _ = post_verifier.verify_post_deterministic(text)
            self.assertFalse(ok, f"Purged ticker {purged} must be blocked")
            self.assertTrue(len(issues) > 0)

    def test_blocks_100_percent_copiers_in_profit_claim(self):
        text = "Con la nostra strategia abbiamo il 100% dei copiatori in profitto su eToro."
        ok, issues, _ = post_verifier.verify_post_deterministic(text)
        self.assertFalse(ok)
        self.assertTrue(any("100%" in i for i in issues))

    def test_sanitize_etoro_cashtags_unwraps_parentheses(self):
        raw = "Seguiamo NVIDIA ($NVDA) e Palantir ($PLTR) con ottimi risultati."
        cleaned = ai_news_generator.sanitize_etoro_cashtags(raw)
        self.assertNotIn("($NVDA)", cleaned)
        self.assertNotIn("($PLTR)", cleaned)
        self.assertIn("$NVDA", cleaned)
        self.assertIn("$PLTR", cleaned)


class TestAiNewsGeneratorHelpers(unittest.TestCase):
    """Test robotic phrase cleaning, thematic emojis, and copy trading fallback."""

    def test_clean_robotic_phrases_strips_markdown_and_self_intro(self):
        raw = "Come Andrea Ravalli, ecco un'analisi su **$NVDA** e **$MSFT** per il portafoglio."
        cleaned = ai_news_generator._clean_robotic_phrases(raw)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("Come Andrea Ravalli", cleaned)
        self.assertIn("$NVDA", cleaned)

    def test_copy_trading_fallback_for_all_themes(self):
        for theme in ai_news_generator.COPY_TRADING_ETORO_THEMES:
            post = ai_news_generator._copy_trading_fallback(
                history_stats_text="Win rate: 82.5%",
                portfolio_perf=210.4,
                rankings_data={"copiers": 35, "riskScore": 3, "winRatio": 82.5},
                theme=theme,
            )
            self.assertIn("210.4%", post)
            self.assertIn("Risk Score 3/10", post)
            for t in theme["tickers"]:
                self.assertIn(f"${t}", post)

    def test_dividend_tracker_has_time_imported_and_fallback_works(self):
        self.assertTrue(hasattr(dividend_tracker, "time"))
        fb = ai_news_generator._dividend_post_fallback(
            ticker="ENEL.MI",
            company_name="Enel S.p.A.",
            pay_date="21/10/2026",
            dps_amount="€0.22",
            div_yield="6.1%",
            weight_pct=3.5,
        )
        self.assertIn("$ENEL.MI", fb)
        self.assertNotIn("($ENEL.MI)", fb)
        self.assertNotIn("#", fb)


class TestPollGeneratorScheduleRouting(unittest.TestCase):
    """Test poll_generator schedule selection and hashtag sanitization."""

    def test_clean_no_hashtags_preserves_cashtags(self):
        raw = "Sondaggio #Macro e #Trading su $SPX500 e $NVDA!"
        cleaned = poll_generator._clean_no_hashtags(raw)
        self.assertNotIn("#Macro", cleaned)
        self.assertNotIn("#Trading", cleaned)
        self.assertIn("$SPX500", cleaned)
        self.assertIn("$NVDA", cleaned)

    @patch("poll_generator.generate_monday_macro_poll", return_value={"title": "Monday", "options": ["1", "2", "3", "4"], "tickers": ["SPX500"], "message": "M"})
    @patch("poll_generator.generate_friday_performers_poll", return_value={"title": "Friday", "options": ["1", "2", "3", "4"], "tickers": ["NVDA"], "message": "F"})
    def test_get_poll_for_schedule_explicit_modes(self, _mock_fri, _mock_mon):
        self.assertEqual(poll_generator.get_poll_for_schedule("monday")["title"], "Monday")
        self.assertEqual(poll_generator.get_poll_for_schedule("friday")["title"], "Friday")
        pltr_poll = poll_generator.get_poll_for_schedule("pltr_conviction")
        self.assertIn("Palantir", pltr_poll["title"])
        self.assertEqual(len(pltr_poll["options"]), 4)


class TestAiCommentResponderFilters(unittest.TestCase):
    """Test third-party mention detection and syntax validation in ai_comment_responder."""

    def test_is_third_party_mention(self):
        self.assertTrue(ai_comment_responder.is_third_party_mention("@MarcoRossi concordo con te!"))
        self.assertFalse(ai_comment_responder.is_third_party_mention("@AndreaRavalli ottimo lavoro!"))
        self.assertFalse(ai_comment_responder.is_third_party_mention("Ottima analisi su $NVDA!"))

    def test_validate_response_syntax(self):
        ok, cleaned, err = ai_comment_responder.validate_response_syntax(
            "@Utente123 Grazie mille per il tuo commento! Puntiamo su $NVDA con un orizzonte di lungo periodo (3-5+ anni), zero leva e Risk Score 3/10. 🚀",
            "Utente123",
        )
        self.assertTrue(ok, f"Valid reply should pass: {err}")
        self.assertIn("@Utente123", cleaned)

        # Truncated sentence ending in preposition must fail
        ok_bad, _, _ = ai_comment_responder.validate_response_syntax(
            "@Utente123 Grazie per il commento, investiamo in questo titolo con orizzonte di lungo periodo e disciplina per",
            "Utente123",
        )
        self.assertFalse(ok_bad)


if __name__ == "__main__":
    unittest.main()
