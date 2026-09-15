#!/usr/bin/env python3
"""
Test Suite: Weekend Strategy & Cooldown Guard
=============================================
Verifies:
1. check_cooldown_and_similarity blocks rapid consecutive posts (< 75 minutes) to prevent spam.
2. check_cooldown_and_similarity blocks duplicate sessions within 6 hours.
3. FORCE_RUN environment variable bypasses cooldown check.
4. WEEKLY_SUN greeting pool and prompts are forward-looking for the week ahead.
5. Dashboard HTML generation includes cache-control meta tags, live sync pill, and excludes XEON.DE from holdings.
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import social_publisher
import ai_news_generator
import analytics_tracker


class TestCooldownAndWeekendStrategy(unittest.TestCase):

    def test_cooldown_blocks_rapid_consecutive_post(self):
        """Ensure post is blocked if published within the cooldown threshold (e.g. 10 minutes ago)."""
        recent_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        mock_post = {
            "created_at": recent_time,
            "session_name": "Daily crypto recap",
        }

        with patch.dict(os.environ, {"FORCE_RUN": "false"}):
            with patch("gist_storage.get_last_etoro_post", return_value=mock_post):
                can_post, reason = social_publisher.check_cooldown_and_similarity("European market open", min_cooldown_minutes=75)
                self.assertFalse(can_post)
                self.assertIn("COOLDOWN ACTIVE", reason)

    def test_cooldown_allows_after_interval(self):
        """Ensure post is allowed if last post was 90 minutes ago (> 75 min threshold)."""
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat()
        mock_post = {
            "created_at": past_time,
            "session_name": "Community Poll",
        }

        with patch.dict(os.environ, {"FORCE_RUN": "false"}):
            with patch("gist_storage.get_last_etoro_post", return_value=mock_post):
                # Also mock post_analytics.json check to return empty
                with patch("os.path.exists", return_value=False):
                    can_post, reason = social_publisher.check_cooldown_and_similarity("Stock focus", min_cooldown_minutes=75)
                    self.assertTrue(can_post)

    def test_duplicate_session_guard(self):
        """Ensure identical session is blocked if it ran 2 hours ago (< 360 min)."""
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=120)).isoformat()
        mock_post = {
            "created_at": past_time,
            "session_name": "Weekly recap (Sun)",
        }

        with patch.dict(os.environ, {"FORCE_RUN": "false"}):
            with patch("gist_storage.get_last_etoro_post", return_value=mock_post):
                with patch("os.path.exists", return_value=False):
                    can_post, reason = social_publisher.check_cooldown_and_similarity("Weekly recap (Sun)", min_cooldown_minutes=75)
                    self.assertFalse(can_post)
                    self.assertIn("DUPLICATE SESSION GUARD", reason)

    def test_force_run_bypasses_cooldown(self):
        """Ensure FORCE_RUN=true bypasses the cooldown guard."""
        recent_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        mock_post = {
            "created_at": recent_time,
            "session_name": "Daily crypto recap",
        }

        with patch.dict(os.environ, {"FORCE_RUN": "true"}):
            with patch("gist_storage.get_last_etoro_post", return_value=mock_post):
                can_post, reason = social_publisher.check_cooldown_and_similarity("Stock focus", min_cooldown_minutes=75)
                self.assertTrue(can_post)
                self.assertIn("FORCE_RUN", reason)

    def test_weekly_sun_greetings_are_forward_looking(self):
        """Verify that WEEKLY_SUN greeting pool contains forward-looking preview phrases."""
        greetings = ai_news_generator._GREETING_POOLS.get("WEEKLY_SUN", {}).get("default", [])
        self.assertTrue(len(greetings) > 0)
        found_forward_looking = False
        for g in greetings:
            g_lower = g.lower()
            if any(k in g_lower for k in ["prossima settimana", "nuova settimana", "riaprire", "anteprima", "prossimi giorni"]):
                found_forward_looking = True
                break
        self.assertTrue(found_forward_looking, "WEEKLY_SUN greetings should contain forward-looking preview phrasing.")

    def test_dashboard_contains_cache_busting_and_live_badge(self):
        """Verify generated dashboard HTML contains Cache-Control and Live status pill, and excludes XEON.DE from holdings."""
        html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "index.html")
        self.assertTrue(os.path.exists(html_path))
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("no-cache", content)
        self.assertIn("live-status-pill", content)
        self.assertIn("pulse-indicator", content)

        idx_holdings = content.find("const holdingsData =")
        self.assertNotEqual(idx_holdings, -1)
        end_holdings = content.find(";", idx_holdings)
        holdings_sub = content[idx_holdings:end_holdings]
        self.assertNotIn("XEON", holdings_sub, "XEON.DE must not be present in active holdingsData.")

    def test_dynamic_portfolio_weights_and_allocations(self):
        """Verify that weights normalize to 100% and dynamic allocation distributions sum to 100%."""
        weights = analytics_tracker.load_portfolio_weights()
        self.assertTrue(len(weights) >= 40)
        total_w = sum(weights.values())
        self.assertAlmostEqual(total_w, 100.0, delta=0.1, msg="Portfolio weights must sum to 100%")

        holdings_with_weights = [dict(h, weight=weights.get(h["ticker"], 1.0)) for h in analytics_tracker.HOLDINGS_DATA]
        alloc = analytics_tracker.compute_allocation_distributions(holdings_with_weights)

        for category in ["geo", "sector", "asset_class", "currency"]:
            cat_sum = sum(alloc[category].values())
            self.assertAlmostEqual(cat_sum, 100.0, delta=0.1, msg=f"Allocation '{category}' must sum to 100%")

    def test_nomadz_referral_integration(self):
        """Verify Nomadz referral link, code y453MHFA, Solana mention, and modal popup are present in docs/index.html."""
        html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "index.html")
        self.assertTrue(os.path.exists(html_path))
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("https://nomadz.xyz/sign-up?referralCode=y453MHFA", content)
        self.assertIn("y453MHFA", content)
        self.assertIn("nomadzModal", content)
        self.assertIn("openNomadzModal", content)
        self.assertIn("sol-pill", content)
        self.assertIn("Solana", content)

    def test_github_workflows_syntax_and_bash_validity(self):
        """Ensure all GitHub Actions workflow YAML files are valid and all embedded bash run steps pass syntax check."""
        import glob
        import re
        import subprocess
        import tempfile
        import yaml

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        workflows_dir = os.path.join(repo_root, ".github", "workflows")
        workflow_files = glob.glob(os.path.join(workflows_dir, "*.yml"))
        self.assertTrue(len(workflow_files) > 0, "At least one workflow file must exist.")

        for yml in workflow_files:
            # 1. Validate YAML parsing
            with open(yml, "r", encoding="utf-8") as f:
                content = f.read()
            data = yaml.safe_load(content)
            self.assertIsInstance(data, dict, f"{yml} must parse as a valid YAML mapping")

            # 2. Validate run scripts with bash -n
            jobs = data.get("jobs", {})
            for job_name, job in jobs.items():
                steps = job.get("steps", [])
                for i, step in enumerate(steps):
                    run_script = step.get("run")
                    if run_script:
                        # Replace GitHub template syntax ${{ ... }} with dummy text
                        clean_script = re.sub(r"\$\{\{.*?\}\}", "MOCK_EXPR", run_script)
                        with tempfile.NamedTemporaryFile("w", suffix=".sh") as tf:
                            tf.write(clean_script)
                            tf.flush()
                            res = subprocess.run(["bash", "-n", tf.name], capture_output=True, text=True)
                            self.assertEqual(
                                res.returncode,
                                0,
                                f"Syntax error in {os.path.basename(yml)} (job: {job_name}, step: {step.get('name', i)}):\n{res.stderr}",
                            )

            # 3. Check for accidental duplicate git commit statements
            lines = content.splitlines()
            for idx in range(len(lines) - 1):
                if "git commit" in lines[idx] and "git commit" in lines[idx + 1]:
                    self.fail(f"Consecutive duplicate 'git commit' found in {os.path.basename(yml)} lines {idx+1}-{idx+2}")


if __name__ == "__main__":
    unittest.main()

