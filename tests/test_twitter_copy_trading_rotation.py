#!/usr/bin/env python3
"""
Test Suite: Twitter/X & Bluesky Dynamic Performance & Copy Trading Footer Rotation
===================================================================================
Verifies:
1. twitter_sender.build_twitter_copy_trading_thread dynamically computes verified
   performance since 2020 and risk score.
2. The footer varies across runs (9 diversified themes) targeting distinct audience
   demographics (Tech/AI, Nuclear, Semis, Healthcare, European Champions, Defense,
   Wealth Compounders, Fintech, eToro Popular Investor).
3. All rotated themes strictly comply with Twitter's 280-character limit.
4. All rotated themes strictly comply with Twitter API v2 Free limit (max 1 cashtag in Tweet 1).
5. Gist storage round-robin index rotation advances reliably.
6. bluesky_sender.build_bluesky_copy_trading_thread stays <= 300 chars and rotates themes.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import twitter_sender
import bluesky_sender
import gist_storage
from post_verifier import extract_cashtags


class TestTwitterCopyTradingRotation(unittest.TestCase):

    def test_default_copy_trading_thread_structure(self):
        """Default call with no arguments should produce a compliant 2-tweet thread."""
        tweets = twitter_sender.build_twitter_copy_trading_thread()
        self.assertEqual(len(tweets), 2)

        tweet1, tweet2 = tweets[0], tweets[1]
        self.assertLessEqual(len(tweet1), 280, f"Tweet 1 exceeds 280 chars ({len(tweet1)})")
        self.assertLessEqual(len(tweet2), 280, f"Tweet 2 exceeds 280 chars ({len(tweet2)})")

        cashtags = extract_cashtags(tweet1)
        self.assertLessEqual(len(cashtags), 1, f"Tweet 1 exceeds 1 cashtag: {cashtags}")

        self.assertIn("Andrea Ravalli", tweet1)
        self.assertIn("since 2020", tweet1)
        self.assertIn("Risk Score", tweet1)
        self.assertIn("Zero leverage", tweet1)

        self.assertIn("Live Hub", tweet2)
        self.assertIn("Copy on eToro", tweet2)
        self.assertIn("Join eToro" if "Join" in tweet2 else "Free Signup", tweet2)

    def test_all_themes_char_limit_and_cashtags(self):
        """Every single theme in COPY_TRADING_THEMES must stay <= 280 chars and <= 1 cashtag."""
        themes = twitter_sender.COPY_TRADING_THEMES
        self.assertGreaterEqual(len(themes), 8, "Expected at least 8 rotating audience themes")

        test_metrics = [
            ("+195%", "~17% CAGR", 3),
            ("+215%", "~19% CAGR", 4),
            ("+250%", "~21% CAGR", 3),
        ]

        seen_footers = set()
        seen_audiences = set()

        for idx, theme in enumerate(themes):
            seen_footers.add(theme["footer"] if "footer" in theme else f"{theme['tickers_line']} {theme['hashtags']}")
            seen_audiences.add(theme.get("audience", theme["id"]))

            for gain, cagr, risk in test_metrics:
                tweets = twitter_sender.build_twitter_copy_trading_thread(
                    gain_pct=gain,
                    cagr_pct=cagr,
                    risk_score=risk,
                    theme_index=idx,
                )
                tweet1 = tweets[0]
                cashtags = extract_cashtags(tweet1)

                self.assertLessEqual(
                    len(tweet1), 280,
                    f"Theme '{theme['id']}' exceeded 280 chars ({len(tweet1)}): {tweet1}"
                )
                self.assertLessEqual(
                    len(cashtags), 1,
                    f"Theme '{theme['id']}' has more than 1 cashtag: {cashtags}"
                )
                self.assertIn(gain, tweet1)
                self.assertIn(cagr, tweet1)
                self.assertIn(f"Risk Score {risk}/10", tweet1)

        self.assertEqual(len(seen_footers), len(themes), "Footers must all be unique across themes")

    def test_dynamic_metrics_computation_from_gain_history(self):
        """Simulated monthly gain history must compound correctly since 2020."""
        history = [
            {"date": "2020-01-01", "gain": 50.0},   # 1.50
            {"date": "2021-01-01", "gain": 20.0},   # 1.50 * 1.20 = 1.80
            {"date": "2022-01-01", "gain": -10.0},  # 1.80 * 0.90 = 1.62 (+62%)
        ]
        rankings = {"riskScore": 4}

        gain_str, cagr_str, risk = twitter_sender.compute_copy_strategy_metrics(
            rankings_data=rankings,
            gain_history=history,
        )

        self.assertEqual(gain_str, "+62%")
        self.assertEqual(risk, 4)
        self.assertTrue("CAGR" in cagr_str)

        tweets = twitter_sender.build_twitter_copy_trading_thread(
            gain_history=history,
            rankings_data=rankings,
            theme_index=0,
        )
        self.assertIn("+62% since 2020", tweets[0])
        self.assertIn("Risk Score 4/10", tweets[0])

    def test_gist_theme_rotation_advancement(self):
        """Verify that get_next_twitter_copy_theme_index advances round-robin."""
        num_themes = len(twitter_sender.COPY_TRADING_THEMES)
        current = gist_storage.get_current_twitter_copy_theme_index(num_themes)
        next_val = gist_storage.get_next_twitter_copy_theme_index(num_themes)
        self.assertEqual(next_val, current)
        after = gist_storage.get_current_twitter_copy_theme_index(num_themes)
        self.assertEqual(after, (current + 1) % num_themes)

    def test_bluesky_copy_trading_thread_rotation_and_limits(self):
        """Bluesky thread builder must stay <= 300 chars and rotate themes."""
        for idx in range(len(twitter_sender.COPY_TRADING_THEMES)):
            posts = bluesky_sender.build_bluesky_copy_trading_thread(
                gain_pct="+195%",
                cagr_pct="~17% CAGR",
                risk_score=3,
                theme_index=idx,
            )
            self.assertEqual(len(posts), 2)
            self.assertLessEqual(len(posts[0]), 300, f"Bluesky post 1 too long: {len(posts[0])}")
            self.assertLessEqual(len(posts[1]), 300, f"Bluesky post 2 too long: {len(posts[1])}")
            self.assertIn("+195%", posts[0])
            self.assertIn("3/10 Risk Score", posts[0])
    def test_us_close_hashtag_rotation_and_ticker_formatting(self):
        """US close recap must rotate hashtags and format European tickers cleanly."""
        top_movers = [("MRVL", 4.81), ("TSM", 2.94), ("VOW3.DE", 2.74)]
        seen_hashtags = set()

        for idx in range(len(twitter_sender.US_CLOSE_HASHTAG_SETS)):
            tweets = twitter_sender.build_twitter_thread(
                portfolio_daily=1.0,
                top_performers=top_movers,
                hashtag_index=idx,
            )
            tweet1 = tweets[0]
            self.assertLessEqual(len(tweet1), 280, f"US close tweet exceeds 280 chars: {tweet1}")

            cashtags = extract_cashtags(tweet1)
            self.assertLessEqual(len(cashtags), 1, f"US close tweet exceeds 1 cashtag: {cashtags}")

            # Check that VOW3.DE was formatted cleanly to prevent Twitter domain linkification
            self.assertIn("VOW3 (DE)", tweet1)
            self.assertNotIn("VOW3.DE", tweet1)

            htag_set = twitter_sender.US_CLOSE_HASHTAG_SETS[idx]
            seen_hashtags.add(htag_set)
            self.assertIn(htag_set, tweet1)

        self.assertEqual(len(seen_hashtags), len(twitter_sender.US_CLOSE_HASHTAG_SETS))

    def test_gist_close_hashtag_rotation_advancement(self):
        """Verify that get_next_twitter_close_hashtag_index advances round-robin."""
        num_sets = len(twitter_sender.US_CLOSE_HASHTAG_SETS)
        current = gist_storage.get_current_twitter_close_hashtag_index(num_sets)
        next_val = gist_storage.get_next_twitter_close_hashtag_index(num_sets)
        self.assertEqual(next_val, current)
        after = gist_storage.get_current_twitter_close_hashtag_index(num_sets)
        self.assertEqual(after, (current + 1) % num_sets)


if __name__ == "__main__":
    unittest.main()
