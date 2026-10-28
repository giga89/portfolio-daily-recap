#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Code Audit & Quality Improvements
==============================================================
Tests all bug fixes, security redactions, verification gates, caching,
template integrity, and edge cases identified during the full repository audit.
"""

import io
import json
import os
import re
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import ai_news_generator
import cross_link_scheduler
import dividend_tracker
import economic_calendar
import event_monitor
import finance_fetcher
import independent_fact_checker
import poll_generator
import portfolio_manager
import post_verifier
import social_publisher
import stock_news_commenter
import telegram_sender


class TestTopGainersSelection(unittest.TestCase):
    """Test _get_top_gainers_with_news edge cases and default has_traded_today handling."""

    @patch("tavily_search.search_tavily")
    def test_defaults_has_traded_today_to_true_when_omitted(self, mock_tavily):
        mock_tavily.return_value = [{"title": "Catalyst news", "content": "Strong demand"}]
        stock_data = {
            "NVDA": {"daily_change": 4.5, "current_price": 135.0},
            "PLTR": {"daily_change": 6.2, "current_price": 42.0},
            "LLY": {"daily_change": 2.1, "current_price": 900.0},
        }
        top = ai_news_generator._get_top_gainers_with_news(stock_data, count=3)
        self.assertEqual([t["ticker"] for t in top], ["PLTR", "NVDA", "LLY"])

    @patch("tavily_search.search_tavily")
    def test_skips_explicitly_untraded_and_excluded_money_market_tickers(self, mock_tavily):
        mock_tavily.return_value = [{"title": "Catalyst news", "content": "Strong demand"}]
        stock_data = {
            "IB01.L": {"daily_change": 9.9, "has_traded_today": True},
            "XEON.DE": {"daily_change": 8.8, "has_traded_today": True},
            "TSM": {"daily_change": 5.0, "has_traded_today": False},
            "AVGO": {"daily_change": 3.4, "has_traded_today": True},
            "MSFT": {"daily_change": 1.2, "has_traded_today": True},
        }
        top = ai_news_generator._get_top_gainers_with_news(stock_data, count=2)
        tickers = [t["ticker"] for t in top]
        self.assertEqual(tickers, ["AVGO", "MSFT"])
        self.assertNotIn("IB01.L", tickers)
        self.assertNotIn("XEON.DE", tickers)
        self.assertNotIn("TSM", tickers)

    @patch("tavily_search.search_tavily")
    def test_prioritizes_positive_gainers_over_negative_movers(self, mock_tavily):
        mock_tavily.return_value = [{"title": "Catalyst news", "content": "Strong demand"}]
        stock_data = {
            "NVDA": {"daily_change": 2.5, "has_traded_today": True},
            "PLTR": {"daily_change": -1.0, "has_traded_today": True},
            "AMZN": {"daily_change": -3.5, "has_traded_today": True},
        }
        top = ai_news_generator._get_top_gainers_with_news(stock_data, count=3)
        self.assertEqual(top[0]["ticker"], "NVDA")
        self.assertEqual(len(top), 3)


class TestVerificationGatesReachability(unittest.TestCase):
    """Ensure all generator functions actually execute _run_post_verification before returning."""

    @patch("finance_fetcher.fetch_portfolio_weights", return_value={"NVDA": 8.5})
    @patch("portfolio_manager.load_config", return_value={"tickers": {"NVDA": ["NVDA", "NVIDIA Corporation"]}})
    @patch("ai_news_generator.genai.Client")
    @patch("ai_news_generator._run_post_verification")
    @patch("gist_storage.save_used_stock_focus_ticker")
    def test_generate_stock_focus_post_runs_verification_and_saves_ticker_once(
        self, mock_save_ticker, mock_verify, mock_client_cls, _mock_cfg, _mock_weights
    ):
        mock_resp = MagicMock()
        mock_resp.text = "🔍 FOCUS ASSET: Perché ho in portafoglio NVIDIA $NVDA\n\nAnalisi approfondita sul titolo."
        mock_client_cls.return_value.models.generate_content.return_value = mock_resp
        mock_verify.return_value = (True, "🔍 FOCUS ASSET: $NVDA — TESTO VERIFICATO E CERTIFICATO.")

        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-gemini-key"}):
            ticker, post = ai_news_generator.generate_stock_focus_post(ticker="NVDA")
        self.assertEqual(ticker, "NVDA")
        self.assertEqual(post, "🔍 FOCUS ASSET: $NVDA — TESTO VERIFICATO E CERTIFICATO.")
        mock_verify.assert_called_once()
        mock_save_ticker.assert_called_once_with("NVDA")

    @patch("portfolio_manager.load_config", return_value={"tickers": {"PLTR": ["PLTR", "Palantir Technologies"]}})
    @patch("ai_news_generator.genai.Client")
    @patch("ai_news_generator._run_post_verification")
    def test_generate_weekly_portfolio_outlook_runs_verification(
        self, mock_verify, mock_client_cls, _mock_cfg
    ):
        mock_resp = MagicMock()
        mock_resp.text = "📅 ANTEPRIMA SETTIMANALE: Analisi settimanale completa dei pilastri strategici."
        mock_client_cls.return_value.models.generate_content.return_value = mock_resp
        mock_verify.return_value = (True, "📅 ANTEPRIMA SETTIMANALE VERIFICATA.")

        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-gemini-key"}):
            result = ai_news_generator.generate_weekly_portfolio_outlook()
        self.assertEqual(result, "📅 ANTEPRIMA SETTIMANALE VERIFICATA.")
        mock_verify.assert_called_once()

    @patch("ai_news_generator.genai.Client")
    @patch("ai_news_generator._run_post_verification")
    def test_generate_crypto_daily_post_runs_verification(
        self, mock_verify, mock_client_cls
    ):
        mock_resp = MagicMock()
        mock_resp.text = "⚡ FLASH CRYPTO DEL GIORNO & SENTIMENT 🪙\n\n$TRX mostra resilienza con volumi solidi."
        mock_client_cls.return_value.models.generate_content.return_value = mock_resp
        mock_verify.return_value = (True, "⚡ FLASH CRYPTO VERIFICATO.")

        crypto_data = {
            "sentiment": {"score": 55, "classification_it": "Neutrale", "emoji": "⚖️"},
            "cryptos": {
                "TRX": {
                    "symbol": "TRX",
                    "name": "TRON",
                    "emoji": "🪙",
                    "cashtag": "$TRX",
                    "price_formatted": "$0.24",
                    "change_24h": 2.1,
                    "volume_formatted": "$500M",
                    "low_formatted": "$0.23",
                    "high_formatted": "$0.25",
                }
            },
        }
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-gemini-key"}):
            label, post = ai_news_generator.generate_crypto_daily_post(crypto_data=crypto_data)
        self.assertEqual(label, "Daily crypto recap")
        self.assertEqual(post, "⚡ FLASH CRYPTO VERIFICATO.")
        mock_verify.assert_called_once()

    @patch("stock_news_commenter.genai.Client")
    @patch("stock_news_commenter.verify_and_clean_comment")
    def test_generate_catalyst_comment_text_runs_comment_verifier(
        self, mock_verify_comment, mock_client_cls
    ):
        mock_resp = MagicMock()
        mock_resp.text = "🔔 AGGIORNAMENTO $NVDA: Nuovo catalizzatore positivo per i data center AI."
        mock_client_cls.return_value.models.generate_content.return_value = mock_resp
        mock_verify_comment.return_value = (True, "🔔 AGGIORNAMENTO $NVDA VERIFICATO.", {})

        res = stock_news_commenter.generate_catalyst_comment_text(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            news_item={"title": "NVIDIA announces next-gen AI rack shipments", "description": "Major growth"},
            api_key="fake-gemini-key",
        )
        self.assertEqual(res, "🔔 AGGIORNAMENTO $NVDA VERIFICATO.")
        mock_verify_comment.assert_called_once()


class TestPollTemplatesIntegrity(unittest.TestCase):
    """Validate all curated POLL_TEMPLATES against eToro API constraints."""

    def test_all_poll_templates_have_4_unique_valid_options_under_28_chars(self):
        seen_ids = set()
        for tpl in poll_generator.POLL_TEMPLATES:
            tpl_id = tpl.get("id")
            self.assertTrue(tpl_id, "Poll template missing id")
            self.assertNotIn(tpl_id, seen_ids, f"Duplicate poll template id: {tpl_id}")
            seen_ids.add(tpl_id)

            title = tpl.get("title", "")
            self.assertTrue(10 <= len(title) <= 200, f"Invalid title length in {tpl_id}")
            self.assertNotIn("#", title, f"Hashtag found in title of {tpl_id}")

            options = tpl.get("options", [])
            self.assertEqual(len(options), 4, f"{tpl_id} must have exactly 4 options")
            self.assertEqual(
                len(set(options)), 4, f"{tpl_id} has duplicate options: {options}"
            )
            for opt in options:
                self.assertTrue(1 <= len(opt) <= 28, f"Option '{opt}' in {tpl_id} exceeds 28 chars ({len(opt)})")
                self.assertNotIn("()", opt, f"Option '{opt}' in {tpl_id} contains empty parentheses '()'")
                self.assertNotIn("#", opt, f"Option '{opt}' in {tpl_id} contains hashtag '#'")

            msg = tpl.get("message", "")
            self.assertTrue(100 <= len(msg) <= 850, f"Invalid message length in {tpl_id}")
            self.assertNotIn("#", msg, f"Hashtag found in message of {tpl_id}")

    def test_economic_calendar_sanitize_macro_poll(self):
        raw = {
            "title": "Macro #Test della settimana",
            "options": ["Opzione 1"],
            "message": "Calendario #Macro della settimana con dati CPI e BCE.",
        }
        cleaned = economic_calendar._sanitize_macro_poll(raw)
        self.assertNotIn("#", cleaned["title"])
        self.assertNotIn("#", cleaned["message"])
        self.assertEqual(len(cleaned["options"]), 4)
        self.assertEqual(cleaned["tickers"], ["SPX500", "NSDQ100", "EURUSD"])


class TestPortfolioMetadataAndCrossLinkIntegrity(unittest.TestCase):
    """Ensure PORTFOLIO_ASSETS_METADATA and cross_link_scheduler have zero purged or non-portfolio tickers."""

    def test_no_purged_assets_in_portfolio_metadata(self):
        purged = {"XEON.DE", "SPCX.RTH", "MAU.PA", "VWCE.L", "MELI"}
        for ticker, meta in portfolio_manager.PORTFOLIO_ASSETS_METADATA.items():
            self.assertNotIn(ticker, purged, f"Purged asset {ticker} still in PORTFOLIO_ASSETS_METADATA")
            for rel in meta.get("related_tickers", []):
                clean_rel = rel.replace("$", "").upper()
                self.assertNotIn(
                    clean_rel,
                    purged,
                    f"Forbidden related_ticker {rel} found in metadata for {ticker}",
                )
            for tag in meta.get("primary_tags", []):
                clean_tag = tag.replace("$", "").upper()
                self.assertNotIn(
                    clean_tag,
                    purged,
                    f"Forbidden primary_tag {tag} found in metadata for {ticker}",
                )

    def test_cross_link_scheduler_profiles_match_active_portfolio(self):
        active_tickers = set(portfolio_manager.PORTFOLIO_ASSETS_METADATA.keys())
        all_profiles = {}
        all_profiles.update(cross_link_scheduler.AI_TECH_PROFILES)
        all_profiles.update(cross_link_scheduler.DEFENSIVE_VALUE_PROFILES)
        all_profiles.update(cross_link_scheduler.ETF_MACRO_PROFILES)

        self.assertNotIn("BMW.DE", all_profiles)
        self.assertIn("ULVR.L", cross_link_scheduler.DEFENSIVE_VALUE_PROFILES)

        for ticker, prof in all_profiles.items():
            self.assertIn(
                ticker,
                active_tickers,
                f"Cross-link ticker {ticker} is not in PORTFOLIO_ASSETS_METADATA",
            )
            self.assertNotIn(
                "espormi",
                prof.get("question", ""),
                f"Typo 'espormi' found in question for {ticker}",
            )

        comments = cross_link_scheduler.build_dynamic_cross_link_comments(session_name="U.S. market open")
        self.assertEqual(len(comments), 3)
        for c in comments:
            self.assertIn(c["ticker"], active_tickers)
            self.assertNotIn("#", c["text"])
            self.assertNotIn("**", c["text"])


class TestBenchmarksCacheAndFactCheckerPropagation(unittest.TestCase):
    """Test TTL caching on fetch_benchmarks_daily_performance and context propagation in fact checker."""

    def setUp(self):
        finance_fetcher._BENCHMARKS_DAILY_CACHE["timestamp"] = 0.0
        finance_fetcher._BENCHMARKS_DAILY_CACHE["data"] = None

    def tearDown(self):
        finance_fetcher._BENCHMARKS_DAILY_CACHE["timestamp"] = 0.0
        finance_fetcher._BENCHMARKS_DAILY_CACHE["data"] = None

    @patch("finance_fetcher.yf.Ticker")
    def test_fetch_benchmarks_daily_performance_uses_ttl_cache(self, mock_yf_ticker):
        import pandas as pd

        mock_hist = pd.DataFrame({"Close": [100.0, 101.5]})
        mock_yf_ticker.return_value.history.return_value = mock_hist

        first = finance_fetcher.fetch_benchmarks_daily_performance()
        call_count_after_first = mock_yf_ticker.call_count
        self.assertGreater(call_count_after_first, 0)

        second = finance_fetcher.fetch_benchmarks_daily_performance()
        self.assertEqual(mock_yf_ticker.call_count, call_count_after_first)
        self.assertEqual(first, second)
        # Ensure returned dict is a copy so caller mutation doesn't corrupt cache
        first["SPX500"] = 999.9
        third = finance_fetcher.fetch_benchmarks_daily_performance()
        self.assertNotEqual(third["SPX500"], 999.9)

    @patch("independent_fact_checker.audit_with_groq")
    @patch("independent_fact_checker.audit_with_mistral")
    @patch("independent_fact_checker.get_current_temporal_context")
    def test_run_independent_fact_check_reuses_provided_temporal_ctx(
        self, mock_get_temporal, mock_mistral, mock_groq
    ):
        mock_groq.return_value = {
            "decision": "APPROVE",
            "score": 95,
            "verified_text": "Post di test verificato.",
            "auditor": "groq:test",
        }
        mock_mistral.return_value = {
            "decision": "APPROVE",
            "score": 95,
            "verified_text": "Post di test verificato.",
            "auditor": "mistral:test",
        }

        audit_res = independent_fact_checker.run_independent_fact_check(
            text="Post di test verificato.",
            session_name="U.S. market close",
            live_news_context="",
            temporal_ctx={"formatted_date": "Martedì 27 Ottobre 2026"},
            benchmark_daily_data={"SPX500": 0.5, "NSDQ100": 0.8},
        )
        self.assertIsNotNone(audit_res)
        self.assertEqual(audit_res.get("decision"), "APPROVE")
        self.assertEqual(audit_res.get("verified_text"), "Post di test verificato.")
        mock_get_temporal.assert_not_called()


class TestTelegramSecretRedaction(unittest.TestCase):
    """Ensure TELEGRAM_BOT_TOKEN is never leaked to stdout in logs or exception messages."""

    @patch("telegram_sender.requests.post")
    def test_send_telegram_message_redacts_token_on_exception(self, mock_post):
        secret_token = "1234567890:AAH_SUPER_SECRET_BOT_TOKEN_XYZ"
        url_with_secret = f"https://api.telegram.org/bot{secret_token}/sendMessage"
        mock_post.side_effect = telegram_sender.requests.exceptions.ConnectionError(
            f"HTTPSConnectionPool(host='api.telegram.org', port=443): Max retries exceeded with url: {url_with_secret}"
        )

        buf = io.StringIO()
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": secret_token, "TELEGRAM_CHAT_ID": "99999"}):
            with redirect_stdout(buf):
                res = telegram_sender.send_telegram_message("Hello world")

        output = buf.getvalue()
        self.assertFalse(res)
        self.assertNotIn(secret_token, output)
        self.assertNotIn(secret_token[:10], output)
        self.assertIn("***REDACTED***", output)


class TestSocialPublisherCopyTradingSingleSend(unittest.TestCase):
    """Ensure _publish_copy_trading_post sends Telegram message once, not twice."""

    @patch("social_publisher.analytics_tracker.update_and_build_dashboard")
    @patch("social_publisher.etoro_history.get_history_from_gist", return_value=[])
    @patch("social_publisher.etoro_history.get_stats_summary_text", return_value="Win rate: 80%")
    @patch("social_publisher.ai_news_generator.generate_copy_trading_post", return_value="📊 Copy trading post di test.")
    @patch("copy_trading_card.generate_copy_card_auto", return_value="/tmp/fake_chart.png")
    @patch("social_publisher.etoro_sender.etoro_client.is_configured", return_value=False)
    @patch("social_publisher.telegram_sender.send_telegram_photo", return_value=True)
    @patch("social_publisher.telegram_sender.send_telegram_message", return_value=True)
    @patch("social_publisher.os.path.exists", return_value=True)
    def test_publish_copy_trading_post_sends_single_telegram_message(
        self,
        _mock_exists,
        mock_tg_msg,
        mock_tg_photo,
        _mock_etoro_conf,
        _mock_card,
        _mock_gen,
        _mock_stats,
        _mock_hist,
        _mock_dash,
    ):
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "tok",
                "TELEGRAM_CHAT_ID": "chat",
                "BLUESKY_HANDLE": "",
                "TWITTER_API_KEY": "",
            },
            clear=False,
        ):
            res = social_publisher._publish_copy_trading_post(portfolio_perf=210.0)
        self.assertTrue(res.get("telegram_copy_trading"))
        mock_tg_msg.assert_called_once()
        mock_tg_photo.assert_called_once()


class TestEventMonitorQuarterYearExtraction(unittest.TestCase):
    """Ensure publish_earnings_for_ticker extracts the year from quarter string when saving to Gist."""

    @patch("event_monitor.YFINANCE_AVAILABLE", False)
    @patch("event_monitor._get_current_weight", return_value=5.2)
    @patch("event_monitor.etoro_sender.etoro_client.is_configured", return_value=True)
    @patch("event_monitor.etoro_sender.send_etoro_post", return_value=True)
    @patch("event_monitor.earnings_card.generate_earnings_card", return_value="/tmp/earn.png")
    @patch("event_monitor.ai_news_generator.generate_earnings_post", return_value="📊 TRIMESTRALE $NVDA Q4 2025")
    @patch("event_monitor.telegram_sender.send_telegram_photo", return_value=True)
    @patch("event_monitor.telegram_sender.send_telegram_message", return_value=True)
    @patch("event_monitor.gist_storage.mark_earnings_posted")
    def test_publish_earnings_for_ticker_extracts_year_from_quarter(
        self,
        mock_mark_earnings,
        _mock_tg_msg,
        _mock_tg_photo,
        _mock_gen_text,
        _mock_gen_card,
        _mock_send_etoro,
        _mock_conf,
        _mock_weight,
    ):
        event_monitor.etoro_sender.LAST_PUBLISHED_POST_ID = "earn-post-123"
        res = event_monitor.publish_earnings_for_ticker(
            ticker="NVDA",
            quarter="Q4 2025",
            eps_actual="$0.89",
            eps_est="$0.84",
            eps_beat=True,
            rev_actual="$39.3B",
            rev_growth="+78% YoY",
            dry_run=False,
        )
        self.assertTrue(res.get("success"))
        mock_mark_earnings.assert_called_once_with(
            "NVDA", "Q4 2025", 2025, post_id="earn-post-123"
        )


if __name__ == "__main__":
    unittest.main()
