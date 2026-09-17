"""
Tests for Scheduled Dividends Calendar and Dynamic Date Filtering.
Ensures that past dividend dates are never rendered in the Next Scheduled Dividends widget.
"""

import unittest
from datetime import datetime, timezone
import json
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
import analytics_tracker


class TestDividendsSchedule(unittest.TestCase):
    def test_next_dividends_structure_and_dates(self):
        """Verify that all items in NEXT_DIVIDENDS are well-formed and parseable."""
        self.assertGreater(len(analytics_tracker.NEXT_DIVIDENDS), 0)
        
        for item in analytics_tracker.NEXT_DIVIDENDS:
            self.assertIn("ticker", item)
            self.assertIn("type", item)
            self.assertIn("date", item)
            self.assertIn("pay", item)
            
            # Must parse cleanly with %b %d, %Y
            parsed_date = datetime.strptime(item["date"], "%b %d, %Y").date()
            self.assertIsNotNone(parsed_date)

    def test_no_past_dividends_rendered_in_dashboard(self):
        """Verify that docs/index.html does not contain past dividend distributions."""
        index_path = os.path.join(os.path.dirname(__file__), "..", "docs", "index.html")
        self.assertTrue(os.path.exists(index_path))
        
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Extract nextDivsData JSON from HTML
        match = re.search(r"const nextDivsData = (\[.*?\]);", content)
        self.assertIsNotNone(match, "nextDivsData must be present in docs/index.html")
        
        data = json.loads(match.group(1))
        today = datetime.now(timezone.utc).date()
        
        for div in data:
            d = datetime.strptime(div["date"], "%b %d, %Y").date()
            self.assertGreaterEqual(
                d,
                today,
                f"Dividend {div['ticker']} on {div['date']} is in the past (< {today}) and must not be rendered!"
            )

    def test_client_side_filter_present(self):
        """Verify that client-side JavaScript implements dynamic date filtering."""
        index_path = os.path.join(os.path.dirname(__file__), "..", "docs", "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        self.assertIn("activeDivs = nextDivsData.filter", content)


if __name__ == "__main__":
    unittest.main()
