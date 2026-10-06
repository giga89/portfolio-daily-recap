#!/usr/bin/env python3
"""
Unit tests for the eToro Educational Series ('Investing Mastery')
"""

import os
import sys
import json
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "educational_series")

sys.path.insert(0, SRC_DIR)

import educational_card_generator
import educational_series_publisher
import etoro_client


class TestEducationalSeries(unittest.TestCase):

    def setUp(self):
        self.json_path = os.path.join(DATA_DIR, "etoro_educational_series.json")
        with open(self.json_path, "r", encoding="utf-8") as f:
            self.episodes = json.load(f)

    def test_twenty_episodes_present(self):
        """Verify exactly 20 episodes are configured."""
        self.assertEqual(len(self.episodes), 20)

    def test_episode_structure(self):
        """Verify each episode has all mandatory keys and formatting constraints."""
        for ep in self.episodes:
            num = ep.get("episode")
            self.assertIsInstance(num, int, f"Episode number missing or not int in ep {ep}")
            self.assertTrue(1 <= num <= 20, f"Episode number out of range: {num}")
            self.assertTrue(bool(ep.get("title")), f"Missing title in ep {num}")
            self.assertTrue(bool(ep.get("subtitle")), f"Missing subtitle in ep {num}")
            self.assertIn(ep.get("palette"), educational_card_generator.THEME_PALETTES, f"Invalid palette in ep {num}")

            tickers = ep.get("tickers", [])
            self.assertIsInstance(tickers, list, f"Tickers must be list in ep {num}")
            self.assertTrue(len(tickers) >= 1, f"Episode {num} must have at least 1 ticker")
            self.assertTrue(len(tickers) <= 4, f"Episode {num} exceeds eToro limit of 4 cashtags: {len(tickers)}")

            pillars = ep.get("pillars", [])
            self.assertEqual(len(pillars), 3, f"Episode {num} must have exactly 3 pillars")
            for p in pillars:
                self.assertTrue(bool(p.get("label")), f"Missing label in pillar of ep {num}")
                self.assertTrue(bool(p.get("highlight")), f"Missing highlight in pillar of ep {num}")
                self.assertTrue(bool(p.get("text")), f"Missing text in pillar of ep {num}")

            content = ep.get("post_content", "")
            self.assertTrue(len(content) > 100, f"Post content too short in ep {num}")
            self.assertTrue(len(content) <= 3900, f"Post content exceeds eToro 4000 char limit in ep {num}")
            self.assertIn("etoro.com/people/andrearavalli", content, f"Missing profile CTA in ep {num}")

    def test_all_images_exist(self):
        """Verify all 20 image card assets exist on disk."""
        for i in range(1, 21):
            img_file = os.path.join(ASSETS_DIR, f"story_{i:02d}.png")
            self.assertTrue(os.path.exists(img_file), f"Image missing: {img_file}")
            # Ensure not empty
            self.assertGreater(os.path.getsize(img_file), 10000, f"Image file too small: {img_file}")

    def test_rotation_logic(self):
        """Test sequential next episode computation and looping."""
        state_0 = {"last_published_episode": 0}
        self.assertEqual(educational_series_publisher.get_next_episode_number(state_0, 20), 1)

        state_5 = {"last_published_episode": 5}
        self.assertEqual(educational_series_publisher.get_next_episode_number(state_5, 20), 6)

        state_20 = {"last_published_episode": 20}
        self.assertEqual(educational_series_publisher.get_next_episode_number(state_20, 20), 1)


if __name__ == "__main__":
    unittest.main()
