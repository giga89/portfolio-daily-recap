#!/usr/bin/env python3
"""
Test Suite: Meme Generator & Selection Logic
=============================================
Verifies:
1. determine_sentiment correctly classifies bull, bear, sideways, and weekend.
2. generate_meme_card produces a valid image file.
3. Meme templates catalog integrity.
"""

import os
import sys
import unittest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import meme_generator


class TestMemeCard(unittest.TestCase):

    def test_determine_sentiment(self):
        self.assertEqual(meme_generator.determine_sentiment(2.5), "BULL_EXTREME")
        self.assertEqual(meme_generator.determine_sentiment(0.8), "BULL_STEADY")
        self.assertEqual(meme_generator.determine_sentiment(0.0), "SIDEWAYS")
        self.assertEqual(meme_generator.determine_sentiment(-0.8), "BEAR_DIP")
        self.assertEqual(meme_generator.determine_sentiment(-2.0), "BEAR_CRASH")
        self.assertEqual(meme_generator.determine_sentiment(1.0, is_weekend=True), "WEEKEND")

    def test_meme_catalog_templates_exist(self):
        """Ensure all template files specified in the catalog exist in assets/memes."""
        for sentiment, memes in meme_generator.MEME_CATALOG.items():
            for m in memes:
                template_path = os.path.join(meme_generator.MEMES_DIR, m["template"])
                self.assertTrue(
                    os.path.exists(template_path),
                    f"Template {m['template']} not found for sentiment {sentiment}"
                )

    def test_clean_text_for_rendering(self):
        """Verify that clean_text_for_rendering strips emojis and handles whitespace."""
        self.assertEqual(meme_generator.clean_text_for_rendering("😼 CALM AS A CAT"), "CALM AS A CAT")
        self.assertEqual(meme_generator.clean_text_for_rendering("-0.66% 😼"), "-0.66%")
        self.assertEqual(meme_generator.clean_text_for_rendering("A NUOVI MASSIMI 🚀"), "A NUOVI MASSIMI")
        self.assertEqual(meme_generator.clean_text_for_rendering("US ENJOYING ANOTHER MASSIVE GREEN DAY 🍀🔥"), "US ENJOYING ANOTHER MASSIVE GREEN DAY")
        self.assertEqual(meme_generator.clean_text_for_rendering("🏊‍♂️ MARKET LIQUIDITY"), "MARKET LIQUIDITY")
        self.assertEqual(meme_generator.clean_text_for_rendering(""), "")
        self.assertEqual(meme_generator.clean_text_for_rendering(None), "")

    def test_meme_catalog_rendered_fields_clean(self):
        """Ensure no raw emojis exist in title, top_text, bottom_text, en_top, en_bottom."""
        for sentiment, memes in meme_generator.MEME_CATALOG.items():
            for m in memes:
                for field in ["title", "top_text", "bottom_text", "en_top", "en_bottom"]:
                    val = m.get(field, "")
                    cleaned = meme_generator.clean_text_for_rendering(val)
                    self.assertEqual(
                        val, cleaned,
                        f"Field '{field}' in sentiment '{sentiment}' template '{m.get('template')}' contains unrendered emoji: {val}"
                    )

    def test_generate_meme_card(self):
        """Test generating a card and verifying output image properties."""
        test_path = meme_generator.generate_meme_card(
            portfolio_daily=1.25,
            top_performers=[("NVDA", 2.5), ("MSFT", 1.8)],
            lang="it",
            aspect_ratio="16:9"
        )
        self.assertTrue(os.path.exists(test_path), f"Meme card was not generated at {test_path}")
        with Image.open(test_path) as img:
            self.assertEqual(img.size, (1280, 720))

        # Cleanup test image
        try:
            os.remove(test_path)
        except OSError:
            pass


    def test_should_use_meme_probabilities(self):
        """
        Verify that:
        - Movimenti più marcati (|daily| >= 0.5%) have 66% probability.
        - Movimento contenuto (-0.5% < daily < 0.5%) in evening sessions has 33% probability.
        """
        class MockRng:
            def __init__(self, val):
                self.val = val
            def random(self):
                return self.val

        # 1. Movimenti più marcati (|daily| >= 0.5%) -> 66% chance (< 0.66)
        # Bull move >= +0.5%
        self.assertTrue(meme_generator.should_use_meme(0.50, market_session="U.S. market close", rng=MockRng(0.65)))
        self.assertFalse(meme_generator.should_use_meme(0.50, market_session="U.S. market close", rng=MockRng(0.66)))
        self.assertFalse(meme_generator.should_use_meme(1.20, market_session="U.S. market close", rng=MockRng(0.70)))
        # Bear move <= -0.5%
        self.assertTrue(meme_generator.should_use_meme(-0.50, market_session="U.S. market close", rng=MockRng(0.65)))
        self.assertFalse(meme_generator.should_use_meme(-0.50, market_session="U.S. market close", rng=MockRng(0.66)))
        self.assertTrue(meme_generator.should_use_meme(-1.50, market_session="Daily recap", rng=MockRng(0.50)))

        # 2. Movimento contenuto (-0.5% < daily < 0.5%) la sera -> 33% chance (< 0.33)
        # US Market Close
        self.assertTrue(meme_generator.should_use_meme(0.20, market_session="U.S. market close", rng=MockRng(0.32)))
        self.assertFalse(meme_generator.should_use_meme(0.20, market_session="U.S. market close", rng=MockRng(0.33)))
        self.assertFalse(meme_generator.should_use_meme(0.20, market_session="U.S. market close", rng=MockRng(0.50)))
        # Daily recap
        self.assertTrue(meme_generator.should_use_meme(-0.15, market_session="Daily recap", rng=MockRng(0.30)))
        self.assertFalse(meme_generator.should_use_meme(-0.15, market_session="Daily recap", rng=MockRng(0.34)))
        # Contained sideways
        self.assertTrue(meme_generator.should_use_meme(0.00, market_session="Evening close recap", rng=MockRng(0.32)))
        self.assertFalse(meme_generator.should_use_meme(0.00, market_session="Evening close recap", rng=MockRng(0.33)))

        # 3. Movimento contenuto in sessioni diurne / altre -> 33% chance
        self.assertTrue(meme_generator.should_use_meme(0.05, market_session="European market open", rng=MockRng(0.32)))
        self.assertFalse(meme_generator.should_use_meme(0.05, market_session="European market open", rng=MockRng(0.34)))


if __name__ == '__main__':
    unittest.main()

