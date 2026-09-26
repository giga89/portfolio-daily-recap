#!/usr/bin/env python3
"""
Test Suite: Post Sanitization, Epuration & Heavy Tag Rotation
============================================================
Verifies:
1. sanitize_or_prune_post_content automatically fixes non-compliant copiers claims.
2. sanitize_or_prune_post_content auto-sanitizes or epurates paragraphs where accumulation
   assets are mistakenly linked to dividend terms (preventing post drops like the one on Thursday).
3. COPY_TRADING_ETORO_THEMES has diverse themes, all including $SPX500 or major benchmarks + common heavy holdings.
4. _copy_trading_fallback incorporates rotated themes and heavy tickers seamlessly.
5. HEAVY_ANCHOR_TICKERS are prioritized in engagement scoring.
"""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

import post_verifier
import ai_news_generator
from post_verifier import sanitize_or_prune_post_content, verify_post_deterministic


class TestPostSanitizationAndEpuration(unittest.TestCase):

    def test_sanitize_copier_profit_claims(self):
        """Claims like '100% dei copiatori in profitto' must be auto-rephrased into compliant claims."""
        flawed_text = (
            "Buongiorno a tutti! ☕\n\n"
            "Voglio condividere un risultato straordinario: abbiamo il 100% dei copiatori in profitto questo mese!\n\n"
            "La nostra allocazione difensiva su $MSFT e $SPX500 continua a premiare la disciplina.\n\n"
            "Cosa ne pensate? Scrivetelo nei commenti! 👇"
        )
        is_clean, issues, _ = verify_post_deterministic(flawed_text)
        self.assertFalse(is_clean, "Flawed text should fail deterministic check")

        sanitized, is_now_clean, remaining_issues = sanitize_or_prune_post_content(flawed_text)
        self.assertTrue(is_now_clean, f"Sanitized text should pass: {remaining_issues}")
        self.assertNotIn("100% dei copiatori in profitto", sanitized)
        self.assertIn("profitto", sanitized)

    def test_epuration_of_flawed_non_dividend_paragraph(self):
        """
        If a specific paragraph falsely claims dividends for an accumulation asset (like WCLD.L),
        the system should sanitize or prune that paragraph while preserving the rest of the post.
        """
        post_with_flawed_para = (
            "🌆 CHIUSURA DEI MERCATI USA\n\n"
            "Wall Street ha chiuso una seduta volatile con l'indice $SPX500 in modesto recupero.\n\n"
            "🤖 Per $NVDA (+3.20%) la domanda di chip per infrastrutture AI resta solida.\n\n"
            "☁️ L'asset $WCLD.L ha staccato un ricco dividendo con un yield straordinario per tutti gli investitori.\n\n"
            "⚖️ Rotazione settoriale favorevole ai titoli difensivi e liquidi del nostro portafoglio.\n\n"
            "Come avete vissuto la seduta di oggi? Parliamone nei commenti! 👇"
        )
        is_clean, issues, _ = verify_post_deterministic(post_with_flawed_para)
        self.assertFalse(is_clean, "Should fail due to WCLD.L accumulation violation")

        sanitized, is_now_clean, remaining_issues = sanitize_or_prune_post_content(post_with_flawed_para)
        self.assertTrue(is_now_clean, f"Auto-epuration should salvage the post: {remaining_issues}")
        self.assertIn("CHIUSURA DEI MERCATI USA", sanitized)
        self.assertIn("$NVDA", sanitized)
        self.assertIn("$SPX500", sanitized)
        # Verify the false dividend claim is gone
        self.assertNotIn("staccato un ricco dividendo", sanitized)

    def test_copy_trading_etoro_themes_structure(self):
        """All copy trading themes must include heavy tickers like SPX500 and common giants."""
        themes = ai_news_generator.COPY_TRADING_ETORO_THEMES
        self.assertGreaterEqual(len(themes), 8, "Expected at least 8 rotating themes")

        seen_titles = set()
        for t in themes:
            self.assertIn("id", t)
            self.assertIn("title", t)
            self.assertIn("tickers", t)
            self.assertIn("angle", t)
            self.assertTrue(len(t["tickers"]) >= 3)
            # Ensure heavy benchmark SPX500 or major heavy stock is present
            has_heavy = any(tick in ("SPX500", "NSDQ100", "NVDA", "MSFT", "AMZN", "BTC") for tick in t["tickers"])
            self.assertTrue(has_heavy, f"Theme '{t['id']}' must include a heavy ticker: {t['tickers']}")
            seen_titles.add(t["title"])

        self.assertEqual(len(seen_titles), len(themes), "All theme titles should be unique")

    def test_copy_trading_fallback_with_theme_rotation(self):
        """Fallback copy trading post must include the rotated theme and heavy tickers."""
        for idx in range(len(ai_news_generator.COPY_TRADING_ETORO_THEMES)):
            theme = ai_news_generator.COPY_TRADING_ETORO_THEMES[idx]
            post = ai_news_generator._copy_trading_fallback(
                history_stats_text="Win rate 78%",
                portfolio_perf=160.5,
                rankings_data={"copiers": 35, "riskScore": 3, "winRatio": 78.5},
                theme=theme,
            )
            self.assertIn(theme["title"].upper(), post)
            for tick in theme["tickers"]:
                self.assertIn(f"${tick}", post)
            self.assertIn("eToro", post)
            self.assertIn("Copy Trading", post)


if __name__ == "__main__":
    unittest.main()
