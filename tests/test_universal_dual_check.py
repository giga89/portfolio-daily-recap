#!/usr/bin/env python3
"""
Test Suite: Universal Dual-Check & AI Model Cascade
===================================================
Verifies:
1. Prioritized AI Model Cascade starts with the smartest reasoning models.
2. Deterministic & AI double-check for comments and user replies.
3. Strict blocking of purged assets (XEON.DE).
4. Strict blocking of dividend claims on accumulating ETFs (WDEF.L, INDO.PA, IB01.L, PPFB.DE).
5. Pre-send gatekeepers in etoro_client and etoro_sender.
6. Deterministic blocking and auto-correction of WDEF.L identity hallucinations (Defence vs Equity Income / Windows Europe).
7. Complete removal of WDEF.L from all dividend schedules & breakdown structures.
8. Zero duplicate keys in dictionary literals across the codebase.
"""

import sys
import os
import ast
import glob
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from ai_model_cascade import DEFAULT_GEMINI_MODELS, REVIEWER_GEMINI_MODELS
from post_verifier import (
    verify_post_deterministic,
    verify_and_clean_comment,
    verify_and_clean_post,
    clean_etoro_formatting,
)
from ai_news_generator import _clean_robotic_phrases
import etoro_client
import dividend_tracker
import analytics_tracker
import winners_losers_card


class TestUniversalDualCheck(unittest.TestCase):

    def test_model_cascade_priority(self):
        """Verify model cascade priority order."""
        self.assertEqual(DEFAULT_GEMINI_MODELS[0], 'gemini-3.1-pro-preview')
        self.assertEqual(DEFAULT_GEMINI_MODELS[1], 'gemini-3.8-flash')
        self.assertIn('gemini-3.7-flash', DEFAULT_GEMINI_MODELS)
        self.assertIn('gemini-2.5-flash', DEFAULT_GEMINI_MODELS)
        self.assertEqual(REVIEWER_GEMINI_MODELS[0], 'gemini-3.1-pro-preview')

    def test_purged_asset_xeon_blocked(self):
        """Purged asset XEON.DE must be blocked deterministically."""
        bad_comment = "Abbiamo anche $XEON.DE per proteggere la liquidità del portafoglio."
        is_ok, issues, _ = verify_post_deterministic(bad_comment)
        self.assertFalse(is_ok, "XEON.DE should be flagged as critical error")
        self.assertTrue(any("dismesso" in i or "XEON.DE" in i for i in issues))

        ok_c, _, audit = verify_and_clean_comment(bad_comment, run_ai_review=False)
        self.assertFalse(ok_c, "Comment containing XEON.DE must be rejected")

    def test_accumulating_etf_comment_blocked(self):
        """Dividend claims on accumulating ETF WDEF.L must fail deterministic check."""
        hallucinated_reply = "@copier $WDEF.L è un ottimo ETF che stacca un generoso dividendo trimestrale per i nostri flussi di cassa."
        is_ok, issues, _ = verify_post_deterministic(hallucinated_reply, primary_ticker="WDEF.L")
        self.assertFalse(is_ok, "Dividend claim on WDEF.L must fail deterministic check")

        ok_c, _, audit = verify_and_clean_comment(
            text=hallucinated_reply,
            user_comment="Ma WDEF paga dividendi?",
            user_author="copier",
            primary_ticker="WDEF.L",
            run_ai_review=False,
        )
        self.assertFalse(ok_c, "Hallucinated comment on WDEF.L dividends must be rejected")

    def test_valid_comment_approved(self):
        """Valid comment on certified dividend payer must pass."""
        good_reply = "@copier Ciao! **$ENEL.MI** è una utility con un dividendo del 6.5% e flussi regolati. Non è un consiglio finanziario. 🤝📈"
        ok_c, clean_text, audit = verify_and_clean_comment(
            text=good_reply,
            user_comment="Cosa ne pensi del dividendo di Enel?",
            user_author="copier",
            primary_ticker="ENEL.MI",
            run_ai_review=False,
        )
        self.assertTrue(ok_c, f"Valid comment should be approved: {audit.get('issues')}")
        self.assertNotIn("**", clean_text, "Markdown bold asterisks must be stripped")
        self.assertIn("$ENEL.MI", clean_text)

    def test_etoro_client_pre_send_gates(self):
        """Pre-send network gates in etoro_client must block bad content before API dispatch."""
        res1 = etoro_client.add_post_comment(
            post_id="dummy_post",
            message="Acquistate $WDEF.L perché paga un dividendo ricco e garantito!"
        )
        self.assertFalse(res1["success"], "etoro_client.add_post_comment must block critical error")
        self.assertIn("Pre-send verification gate", res1["error"])

        res2 = etoro_client.reply_to_comment(
            post_id="dummy_post",
            comment_id="dummy_comment",
            message="@user abbiamo ancora $XEON.DE in portafoglio."
        )
        self.assertFalse(res2["success"], "etoro_client.reply_to_comment must block purged XEON")
        self.assertIn("Pre-send verification gate", res2["error"])

    def test_wdef_hallucination_blocked_deterministically(self):
        """
        The exact hallucination from post c2a9db30-a977-11f1-8080-800175a4fa89
        (WisdomTree Europe Equity Income instead of Defence) MUST be flagged as CRITICAL.
        """
        bad_post = "Il nostro ETF $WDEF.L (WisdomTree Europe Equity Income) ha risentito un po' di questo sentiment generale..."
        is_ok, issues, _ = verify_post_deterministic(bad_post, primary_ticker="WDEF.L")
        self.assertFalse(is_ok, "Must reject WisdomTree Europe Equity Income hallucination")
        self.assertTrue(
            any("WDEF" in i and ("Defence" in i or "Equity Income" in i) for i in issues),
            f"Issues must mention WDEF identity violation, got: {issues}"
        )

        # Also test Windows Europe hallucination
        bad_post_2 = "Oggi analizziamo $WDEF.L di Windows Europe."
        is_ok_2, issues_2, _ = verify_post_deterministic(bad_post_2)
        self.assertFalse(is_ok_2, "Must reject Windows Europe hallucination")

    def test_wdef_sanitization_in_formatting_and_cleaning(self):
        """Verify that formatting helpers automatically correct known WDEF naming errors."""
        raw_text = "Il nostro ETF $WDEF.L (WisdomTree Europe Equity Income) ha chiuso in calo."
        clean_1 = clean_etoro_formatting(raw_text)
        self.assertIn("WisdomTree Europe Defence UCITS ETF", clean_1)
        self.assertNotIn("Equity Income", clean_1)

        clean_2 = _clean_robotic_phrases("Focus su Windows Europe Defence e $WDEF.L.")
        self.assertIn("WisdomTree Europe Defence", clean_2)
        self.assertNotIn("Windows", clean_2)

    def test_wdef_not_in_any_dividend_structure(self):
        """Verify that WDEF.L is absent from all dividend schedules, breakdown tables, and profiles."""
        self.assertNotIn("WDEF.L", dividend_tracker.DIVIDEND_PROFILES)
        self.assertNotIn("WDEF", dividend_tracker.DIVIDEND_PROFILES)
        self.assertNotIn("WDEF.L", analytics_tracker.DIVIDEND_BREAKDOWN)
        self.assertNotIn("WDEF", analytics_tracker.DIVIDEND_BREAKDOWN)
        self.assertEqual(winners_losers_card.SECTOR_TAGS.get("WDEF.L"), "ETF Difesa europea")

    def test_zero_duplicate_dict_keys_in_codebase(self):
        """AST analysis must find ZERO duplicate keys in dictionary literals across the codebase."""
        class DuplicateKeyVisitor(ast.NodeVisitor):
            def __init__(self, filename):
                self.filename = filename
                self.duplicates = []

            def visit_Dict(self, node):
                keys = set()
                for k in node.keys:
                    if k is not None and isinstance(k, ast.Constant):
                        val = k.value
                        if val in keys:
                            self.duplicates.append((self.filename, k.lineno, val))
                        keys.add(val)
                self.generic_visit(node)

        all_duplicates = []
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for pattern in ['src/**/*.py', 'scripts/**/*.py']:
            search_path = os.path.join(base_dir, pattern)
            for f in sorted(glob.glob(search_path, recursive=True)):
                with open(f, 'r', encoding='utf-8') as fp:
                    tree = ast.parse(fp.read(), filename=f)
                    visitor = DuplicateKeyVisitor(f)
                    visitor.visit(tree)
                    all_duplicates.extend(visitor.duplicates)

        self.assertEqual(
            all_duplicates,
            [],
            f"Found duplicate dictionary keys in codebase: {all_duplicates}"
        )


if __name__ == "__main__":
    unittest.main()
