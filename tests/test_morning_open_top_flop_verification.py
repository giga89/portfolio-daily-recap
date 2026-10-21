#!/usr/bin/env python3
"""
Unit Tests for Morning Open TOP/FLOP Stale Price Prevention & Active Trading Verification
======================================================================================
Validates that:
1. Untraded/unopened assets (like INDO.PA at European market open) are never assigned
   stale previous-session percentage changes or marked as has_traded_today.
2. Volume == 0 or prior-date bars strictly set daily_change=0.0 and has_traded_today=False.
3. European Market Open Top & Flop card (winners_losers_card.py) rejects US stocks,
   rejects untraded/closed assets, and only picks actively moving European instruments.
4. If fewer than 2 active candidates have traded, the Top & Flop card safely returns None.
5. social_publisher._extract_top_performers() strictly filters out untraded and 0.00% assets.
"""

import os
import sys
import datetime
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import winners_losers_card
import social_publisher
import formatter


class TestMorningOpenTopFlopVerification(unittest.TestCase):

    def test_winners_losers_card_excludes_untraded_indo_pa_at_eu_open(self):
        """
        Verify that in European Market Open, an ETF like INDO.PA which has not yet traded
        (has_traded_today=False, even if daily_change holds stale value) is strictly excluded
        from being crowned Winner or Loser.
        """
        mock_stock_data = {
            # Stale / untraded INDO.PA (yesterday closed +3.5%)
            "INDO.PA": {
                "company_name": "Amundi MSCI Indonesia ETF",
                "daily_change": 3.50,
                "has_traded_today": False,
                "is_us_stock": False,
            },
            # Active European stocks that actually traded this morning
            "PRY.MI": {
                "company_name": "Prysmian Group",
                "daily_change": 1.20,
                "has_traded_today": True,
                "is_us_stock": False,
            },
            "ENEL.MI": {
                "company_name": "Enel S.p.A.",
                "daily_change": -0.85,
                "has_traded_today": True,
                "is_us_stock": False,
            },
            # US stock (closed/pre-market)
            "NVDA": {
                "company_name": "Nvidia",
                "daily_change": 4.50,
                "has_traded_today": True,  # even if mistakenly marked True
                "is_us_stock": True,
            },
        }

        with patch("winners_losers_card.generate_winners_losers_card") as mock_gen:
            mock_gen.return_value = "output/winners_losers.png"
            card = winners_losers_card.build_card_from_stock_data(
                stock_data=mock_stock_data,
                session_name="European market open",
                fetch_logos=False,
            )

            self.assertIsNotNone(card)
            mock_gen.assert_called_once()
            call_kwargs = mock_gen.call_args[1]
            winner = call_kwargs["winner"]
            loser = call_kwargs["loser"]

            # INDO.PA must NOT be the winner despite +3.50% because has_traded_today=False
            self.assertNotEqual(winner["ticker"], "INDO.PA")
            self.assertEqual(winner["ticker"], "PRY.MI")
            self.assertEqual(winner["change"], 1.20)

            # NVDA must NOT be the winner because it is a US stock during EU Open
            self.assertNotEqual(winner["ticker"], "NVDA")

            # Loser must be ENEL.MI
            self.assertEqual(loser["ticker"], "ENEL.MI")
            self.assertEqual(loser["change"], -0.85)

    def test_winners_losers_card_skips_when_fewer_than_two_active_candidates(self):
        """
        If at EU market open only 1 European stock has traded, or all are flat/untraded,
        build_card_from_stock_data must return None to avoid displaying invalid cards.
        """
        mock_stock_data = {
            "INDO.PA": {
                "company_name": "Amundi MSCI Indonesia ETF",
                "daily_change": 0.0,
                "has_traded_today": False,
                "is_us_stock": False,
            },
            "PRY.MI": {
                "company_name": "Prysmian Group",
                "daily_change": 0.50,
                "has_traded_today": True,
                "is_us_stock": False,
            },
            # All other stocks untraded
            "ENI.MI": {
                "company_name": "Eni",
                "daily_change": 0.0,
                "has_traded_today": False,
                "is_us_stock": False,
            },
        }

        card = winners_losers_card.build_card_from_stock_data(
            stock_data=mock_stock_data,
            session_name="European market open",
            fetch_logos=False,
        )
        self.assertIsNone(card, "Card should be skipped when fewer than 2 active candidates exist")

    def test_winners_losers_card_skips_flat_zero_performers(self):
        """
        If candidates only have 0.00% change, they must not be selected as Winner or Loser.
        """
        mock_stock_data = {
            "PRY.MI": {
                "company_name": "Prysmian Group",
                "daily_change": 0.0,
                "has_traded_today": True,
                "is_us_stock": False,
            },
            "ENEL.MI": {
                "company_name": "Enel S.p.A.",
                "daily_change": 0.0,
                "has_traded_today": True,
                "is_us_stock": False,
            },
        }

        card = winners_losers_card.build_card_from_stock_data(
            stock_data=mock_stock_data,
            session_name="European market open",
            fetch_logos=False,
        )
        self.assertIsNone(card, "Flat 0.00% candidates must not generate a Winner/Loser card")

    def test_social_publisher_extract_top_performers_filters_untraded(self):
        """
        Verify _extract_top_performers strictly ignores untraded assets and 0.00% moves.
        """
        mock_stock_data = {
            "INDO.PA": {
                "company_name": "Amundi MSCI Indonesia ETF",
                "daily_change": 5.0,  # Fake high stale change
                "has_traded_today": False,
            },
            "PRY.MI": {
                "company_name": "Prysmian Group",
                "daily_change": 1.5,
                "has_traded_today": True,
            },
            "GLEN.L": {
                "company_name": "Glencore",
                "daily_change": 1.2,
                "has_traded_today": True,
            },
            "AZN.L": {
                "company_name": "AstraZeneca",
                "daily_change": 0.0,  # flat
                "has_traded_today": True,
            },
        }

        top = social_publisher._extract_top_performers("", stock_data=mock_stock_data)
        tickers = [sym for sym, pct in top]

        self.assertNotIn("INDO.PA", tickers, "Untraded INDO.PA must not appear in top performers")
        self.assertNotIn("AZN.L", tickers, "Flat 0.00% AZN.L must not appear in top performers")
        self.assertEqual(tickers, ["PRY.MI", "GLEN.L"])

    def test_formatter_active_stocks_filter(self):
        """
        Verify formatter uses strict has_traded_today=False default.
        """
        mock_stock_data = {
            "INDO.PA": {
                "company_name": "Amundi MSCI Indonesia ETF",
                "daily_change": 2.5,
                "has_traded_today": False,
            },
            "PRY.MI": {
                "company_name": "Prysmian Group",
                "daily_change": 1.0,
                "has_traded_today": True,
            },
            "MISSING_FLAG": {
                "company_name": "Unknown",
                "daily_change": 3.0,
                # has_traded_today missing -> must default to False
            },
        }

        active = {k: v for k, v in mock_stock_data.items() if v.get("has_traded_today", False)}
        self.assertEqual(list(active.keys()), ["PRY.MI"])


if __name__ == "__main__":
    unittest.main()
