#!/usr/bin/env python3
"""
Unit tests for Tavily Live Search integration with fact checking and news generation.
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from tavily_search import search_tavily, get_live_market_news_context
from independent_fact_checker import (
    _build_audit_prompt,
    get_current_temporal_context,
    run_micro_topic_consensus_fact_check,
)


class TestTavilyIntegration(unittest.TestCase):
    def test_search_tavily_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            res = search_tavily("Wall Street news")
            self.assertEqual(res, [])

    @patch("requests.post")
    def test_search_tavily_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Fed Holds Rates Steady",
                    "content": "Federal Reserve decided to maintain interest rates at current levels.",
                    "url": "https://reuters.com/fed-decision"
                },
                {
                    "title": "Nvidia Announces New Chip",
                    "content": "Nvidia unveiled its next-generation architecture for cloud AI computing.",
                    "url": "https://bloomberg.com/nvda-announcement"
                }
            ]
        }
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"TAVILY_API_KEY": "dummy_key"}):
            results = search_tavily("market update", max_results=2)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["title"], "Fed Holds Rates Steady")
            self.assertIn("Nvidia", results[1]["content"])

    @patch("requests.post")
    def test_search_tavily_handles_exception(self, mock_post):
        import requests
        mock_post.side_effect = requests.RequestException("Connection error")

        with patch.dict(os.environ, {"TAVILY_API_KEY": "dummy_key"}):
            results = search_tavily("market update")
            self.assertEqual(results, [])

    @patch("tavily_search.search_tavily")
    def test_get_live_market_news_context_formatting(self, mock_search):
        mock_search.return_value = [
            {
                "title": "Tech Stocks Lead Rally",
                "content": "Nasdaq surged 1.5% driven by semiconductor strength.",
                "url": "https://cnbc.com/tech-rally"
            }
        ]

        with patch.dict(os.environ, {"TAVILY_API_KEY": "dummy_key"}):
            context = get_live_market_news_context(
                session_name="US_CLOSE",
                tickers=["NVDA", "PLTR"]
            )
            self.assertIn("Tech Stocks Lead Rally", context)
            self.assertIn("cnbc.com", context)
            self.assertIn("Sintesi:", context)

    def test_build_audit_prompt_includes_tavily_context(self):
        temporal_ctx = get_current_temporal_context(session_name="US_CLOSE")
        live_context = "### FONTI WEB (TAVILY):\n- S&P 500 closed up 0.4% after solid earnings."
        prompt = _build_audit_prompt(
            text="S&P 500 in salita oggi.",
            session_name="US_CLOSE",
            temporal_ctx=temporal_ctx,
            live_news_context=live_context
        )
        self.assertIn("FONTI NOTIZIE FINANZIARIE REALI RECENTI (LIVE WEB - TAVILY)", prompt)
        self.assertIn("S&P 500 closed up 0.4%", prompt)

    @patch("independent_fact_checker.is_tavily_available", return_value=True)
    @patch("independent_fact_checker.get_live_market_news_context")
    @patch("independent_fact_checker.run_independent_fact_check")
    def test_micro_topic_consensus_uses_tavily_context(self, mock_audit, mock_get_context, mock_is_avail):
        mock_get_context.return_value = "### TAVILY CONTEXT: Market solid"
        mock_audit.return_value = {
            "decision": "APPROVE",
            "score": 95,
            "verified_text": "Sample text",
            "temporal_issues": [],
            "hallucinations_detected": [],
            "auditor": "consensus:dual",
            "explanation": "OK"
        }

        sample_post = (
            "Buongiorno! Apertura europea in corso:\n\n"
            "• $NVDA stabile dopo le ultime news sui chip.\n\n"
            "Cosa ne pensate? Dite la vostra! 👇\n\n"
            "📌 $NVDA"
        )

        res = run_micro_topic_consensus_fact_check(
            sample_post,
            session_name="EU_OPEN"
        )

        # Confirm Tavily context was fetched once
        self.assertTrue(mock_get_context.called)
        # Confirm audit was called with the Tavily context
        for call_args in mock_audit.call_args_list:
            self.assertEqual(call_args.kwargs.get("live_news_context"), "### TAVILY CONTEXT: Market solid")
        self.assertEqual(res["decision"], "APPROVE")


if __name__ == "__main__":
    unittest.main()
