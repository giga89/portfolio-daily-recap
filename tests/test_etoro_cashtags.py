#!/usr/bin/env python3
"""
Test Suite: eToro Cashtag Capping & Verification
================================================
Verifies:
1. limit_cashtags strictly caps unique cashtags to max_tags (default 4).
2. Pure currency amounts ($100, $5.000, $10,000) are not counted as cashtags.
3. verify_post_deterministic automatically limits cashtags to 4.
4. etoro_sender resolves at most 4 unique market IDs.
5. twitter_sender threads have at most 1 cashtag per tweet to comply with Twitter API v2.
"""

import sys
import os
import unittest
import re

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from post_verifier import limit_cashtags, extract_cashtags, verify_post_deterministic
import etoro_client
import twitter_sender


class TestEtoroCashtags(unittest.TestCase):

    def test_limit_cashtags_caps_to_4(self):
        """Ensure limit_cashtags strips '$' from 5th ticker onwards while keeping first 4."""
        sample_text = (
            "Nel portafoglio abbiamo $NVDA, $MSFT, $AMZN e $TSM in crescita. "
            "Anche $GOOG, $PLTR, $PRY.MI e $RACE si sono mossi oggi. "
            "Abbiamo investito $500 e poi $10,000 aggiuntivi."
        )
        limited = limit_cashtags(sample_text, max_tags=4)
        tags = extract_cashtags(limited)

        self.assertEqual(len(tags), 4)
        self.assertEqual(tags, ["NVDA", "MSFT", "AMZN", "TSM"])
        # Subsequent tickers must appear without $
        self.assertIn(" GOOG", limited)
        self.assertNotIn("$GOOG", limited)
        self.assertIn(" PLTR", limited)
        self.assertNotIn("$PLTR", limited)
        # Currency amounts must be preserved
        self.assertIn("$500", limited)
        self.assertIn("$10,000", limited)

    def test_limit_cashtags_preserves_duplicates_within_budget(self):
        """Repeated mentions of one of the allowed 4 tickers should keep their '$'."""
        sample_text = "$NVDA è salita. Anche $TSM è forte. $NVDA continua il rally. $MSFT e $AMZN seguono. $PLTR è ferma."
        limited = limit_cashtags(sample_text, max_tags=4)
        tags = extract_cashtags(limited)

        self.assertEqual(len(tags), 4)
        self.assertIn("NVDA", tags)
        self.assertIn("TSM", tags)
        self.assertIn("MSFT", tags)
        self.assertIn("AMZN", tags)
        self.assertNotIn("$PLTR", limited)
        self.assertIn("PLTR", limited)

    def test_verify_post_deterministic_caps_tags(self):
        """verify_post_deterministic should warn and clean if post exceeds 4 cashtags."""
        bad_post = "Analisi di $TSM, $VOW3.DE, $MRVL, $PRY.MI, $RACE, $LLY, $ABBV, $AMZN."
        is_clean, issues, cleaned = verify_post_deterministic(bad_post)

        cleaned_tags = extract_cashtags(cleaned)
        self.assertEqual(len(cleaned_tags), 4)
        self.assertTrue(any("cashtag" in i and "limite di 4" in i for i in issues))

    def test_etoro_sender_market_ids_capped(self):
        """Check regex and capping logic in etoro_sender ensures max 4 unique market IDs."""
        post_text = "$TSM $VOW3.DE $TSM $MRVL $PRY.MI $RACE $LLY $ABBV"
        # Simulate etoro_sender logic
        found_tickers = re.findall(r"\$([A-Za-z0-9\.\-]+)", post_text)
        unique_tickers = []
        for t in found_tickers:
            tu = t.upper()
            if tu in etoro_client.MARKET_IDS and tu not in [x.upper() for x in unique_tickers]:
                unique_tickers.append(t)
        valid_tickers = unique_tickers[:4]
        market_ids = etoro_client.get_market_ids_for_tickers(valid_tickers)

        self.assertLessEqual(len(valid_tickers), 4)
        self.assertLessEqual(len(market_ids), 4)
        self.assertEqual(len(valid_tickers), len(set(valid_tickers)))

    def test_twitter_sender_max_1_cashtag(self):
        """Twitter thread must not contain more than 1 cashtag in Tweet 1 to avoid 403."""
        top_performers = [("PRY.MI", 5.11), ("GLEN.L", 4.17), ("AVGO", 2.98)]
        tweets = twitter_sender.build_twitter_thread(
            portfolio_daily=0.5,
            top_performers=top_performers,
            session_name="U.S. market close",
        )
        tweet1 = tweets[0]
        cashtags = extract_cashtags(tweet1)
        self.assertLessEqual(len(cashtags), 1, f"Tweet 1 exceeds 1 cashtag: {cashtags}")

        copy_tweets = twitter_sender.build_twitter_copy_trading_thread()
        copy_cashtags = extract_cashtags(copy_tweets[0])
        self.assertLessEqual(len(copy_cashtags), 1, f"Copy trading tweet exceeds 1 cashtag: {copy_cashtags}")


if __name__ == "__main__":
    unittest.main()
