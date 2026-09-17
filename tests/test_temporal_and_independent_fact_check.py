#!/usr/bin/env python3
"""
Test Suite: Temporal Consistency & Independent Multi-AI Fact-Checker
====================================================================
Verifies:
1. Deterministic temporal gate in post_verifier.py strictly blocks:
   - Future-tense claims about today's events in evening/close recaps (US_CLOSE).
   - Anachronistic claims citing former officials (e.g. Powell as current decider).
   - Claims awaiting decisions of today when the session has ended.
2. Valid past-tense market recaps pass deterministic verification.
3. Independent fact-checker module (Groq / Mistral):
   - Builds accurate temporal context (day, month, CET, ET, session state).
   - Successfully runs independent audit via Groq when key is available.
   - Gracefully handles Mistral 429 rate limit without throwing unhandled exceptions.
4. Full verify_and_clean_post integration:
   - Auto-corrects temporal hallucinations into verified post text.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from post_verifier import verify_post_deterministic, verify_and_clean_post
from independent_fact_checker import (
    get_current_temporal_context,
    audit_with_groq,
    audit_with_mistral,
    run_independent_fact_check,
)


class TestTemporalAndIndependentFactCheck(unittest.TestCase):

    def test_temporal_context_builder(self):
        """Temporal context builder must provide rich Italian date, times, and market state."""
        ctx = get_current_temporal_context(session_name="US_CLOSE")
        self.assertIn("formatted_date", ctx)
        self.assertIn("rome_time", ctx)
        self.assertIn("ny_time", ctx)
        self.assertIn("market_state", ctx)
        self.assertIn("CONCLUSA", ctx["market_state"])

        ctx_eu = get_current_temporal_context(session_name="EUROPEAN MARKET OPEN")
        self.assertIn("PRE-APERTURA", ctx_eu["market_state"])

    def test_deterministic_temporal_gate_blocks_future_on_us_close(self):
        """Evening US_CLOSE recap using future tense for today's decisions must be blocked deterministically."""
        bad_post = (
            "Buonasera a tutti! Chiusura USA completata: vediamo cosa ha combinato il mercato oggi. "
            "Stasera la Fed prenderà una decisione sui tassi e i mercati sono in forte attesa. "
            "$NVDA e $MSFT attendono la decisione."
        )
        is_clean, issues, _ = verify_post_deterministic(bad_post, session_name="US_CLOSE")
        self.assertFalse(is_clean, "Future tense for today's Fed decision in US_CLOSE must fail deterministic gate")
        self.assertTrue(any("Paradosso temporale" in i for i in issues))

    def test_deterministic_temporal_gate_blocks_powell_hallucination(self):
        """Mentions of Jerome Powell taking current decisions must be blocked deterministically."""
        bad_post = (
            "Buonasera a tutti! Chiusura USA completata. "
            "Oggi Powell deciderà sui tassi di interesse e orienterà i listini. $SPX500 $NSDQ100"
        )
        is_clean, issues, _ = verify_post_deterministic(bad_post, session_name="US_CLOSE")
        self.assertFalse(is_clean, "Powell taking decision today must be blocked as anachronism")
        self.assertTrue(any("Powell" in i or "Paradosso temporale" in i for i in issues))

    def test_deterministic_temporal_gate_allows_valid_past_recap(self):
        """Past-tense factual recap in US_CLOSE must pass deterministic gate."""
        good_post = (
            "Buonasera a tutti! Chiusura USA completata: vediamo cosa ha combinato il mercato oggi. "
            "Wall Street ha archiviato la seduta in territorio positivo dopo la decisione sui tassi "
            "comunicata oggi dalla banca centrale. $NVDA e $MSFT hanno trainato i rialzi tecnologici."
        )
        is_clean, issues, cleaned = verify_post_deterministic(good_post, session_name="US_CLOSE")
        self.assertTrue(is_clean, f"Valid past-tense recap should pass: {issues}")
        self.assertIn("$NVDA", cleaned)
        self.assertIn("$MSFT", cleaned)

    def test_independent_fact_checker_groq_live_or_mock(self):
        """Verify Groq auditor handles temporal paradox appropriately."""
        bad_text = (
            "Buonasera a tutti! Chiusura USA completata. "
            "Stasera Powell prenderà una decisione sui tassi d'interesse per $NVDA."
        )
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            audit = audit_with_groq(bad_text, session_name="US_CLOSE")
            self.assertIsNotNone(audit, "Groq audit should return a structured dict when key is active")
            self.assertIn(audit.get("decision"), ["AUTO_CORRECT", "REJECT"])
            self.assertIn("groq:", audit.get("auditor", ""))
        else:
            # Mock verification
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": '{"decision": "AUTO_CORRECT", "score": 80, "verified_text": "Chiusura USA.", "explanation": "Corretto"}'
                    }
                }]
            }
            with patch("requests.post", return_value=mock_response):
                audit = audit_with_groq(bad_text, session_name="US_CLOSE", api_key="dummy_key")
                self.assertEqual(audit["decision"], "AUTO_CORRECT")

    def test_independent_fact_checker_mistral_429_graceful(self):
        """Mistral 429 quota exhaustion must be handled gracefully without crashing."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = '{"message": "Rate limit exceeded"}'
        with patch("requests.post", return_value=mock_response):
            audit = audit_with_mistral("Test text", session_name="US_CLOSE", api_key="test_key")
            self.assertIsNone(audit, "Mistral 429 should return None for graceful fallback")

    def test_independent_fact_checker_mistral_live_or_mock(self):
        """Mistral ministral-8b-latest live or mock audit."""
        mistral_key = os.environ.get("MISTRAL_API_KEY")
        if mistral_key:
            audit = audit_with_mistral("Chiusura USA positiva per $NVDA.", session_name="US_CLOSE")
            if audit:
                self.assertIn("mistral:", audit.get("auditor", ""))
                self.assertIn(audit.get("decision"), ["APPROVE", "AUTO_CORRECT", "REJECT"])
        else:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": '{"decision": "APPROVE", "score": 95, "verified_text": "Chiusura OK", "explanation": "OK"}'
                    }
                }]
            }
            with patch("requests.post", return_value=mock_response):
                audit = audit_with_mistral("Chiusura USA", session_name="US_CLOSE", api_key="dummy_key")
                self.assertEqual(audit["decision"], "APPROVE")

    def test_full_pipeline_autocorrects_temporal_error(self):
        """verify_and_clean_post with Groq enabled auto-corrects the user's reported error."""
        hallucinated_post = (
            "Buonasera a tutti! Chiusura USA completata: vediamo cosa ha combinato il mercato oggi. "
            "Stasera Powell prenderà una decisione sui tassi di interesse e i mercati attendono la riunione. "
            "$NVDA e $MSFT chiudono la giornata."
        )
        approved, final_text, audit = verify_and_clean_post(
            hallucinated_post,
            session_name="US_CLOSE",
            run_ai_review=True,
        )
        self.assertTrue(approved, f"Pipeline should auto-correct and approve: {audit}")
        self.assertNotIn("prenderà una decisione", final_text.lower())
        self.assertNotIn("powell", final_text.lower())
        self.assertIn("$NVDA", final_text)


if __name__ == "__main__":
    unittest.main()
