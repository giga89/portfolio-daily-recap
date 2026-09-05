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


if __name__ == '__main__':
    unittest.main()
