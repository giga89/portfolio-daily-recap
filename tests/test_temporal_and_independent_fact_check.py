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
            if audit:
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
            with patch("requests.post", return_value=mock_response), \
                 patch("independent_fact_checker._MISTRAL_AVAILABLE", True):
                audit = audit_with_mistral("Chiusura USA", session_name="US_CLOSE", api_key="dummy_key")
                self.assertIsNotNone(audit)
                self.assertEqual(audit["decision"], "APPROVE")

    def test_full_pipeline_autocorrects_temporal_error(self):
        """verify_and_clean_post with Groq enabled auto-corrects or vetoes the user's reported error."""
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
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            if approved:
                self.assertNotIn("prenderà una decisione", final_text.lower())
                self.assertNotIn("powell", final_text.lower())
                self.assertIn("$NVDA", final_text)
            else:
                self.assertEqual(audit.get("decision"), "REJECT")
                self.assertTrue(bool(audit.get("temporal_issues") or audit.get("hallucinations_detected") or audit.get("issues")))
        else:
            self.assertFalse(approved, "Without GROQ_API_KEY, deterministic gate correctly rejects temporal paradox")




    def test_deterministic_gate_catches_banal_platitudes(self):
        """Ensure post_verifier deterministically detects empty banal platitudes."""
        banal_post = (
            "Nel nostro portafoglio continuiamo a seguire con estrema fiducia $TSM , sostenuta dalla domanda sempre fortissima. "
            "La tesi sull uranio rimane solida e rappresenta una copertura strategica importante per bilanciare il nostro portafoglio. "
            "Infine per $ABT.US continua ad offrire ottima stabilità e siamo pronti a gestire la volatilità."
        )
        is_clean, issues, cleaned = verify_post_deterministic(banal_post, session_name="US_OPEN")
        self.assertFalse(is_clean)
        self.assertTrue(len(issues) >= 3, f"Expected multiple platitude issues, got: {issues}")
        self.assertTrue(any("BANALITÀ VIETATA" in issue for issue in issues))

    def test_sentiment_mismatch_blocks_positive_tone_when_index_negative(self):
        """Deterministic gate must block positive tone claims when benchmarks are negative."""
        user_reported_post = (
            "Buonasera! I mercati USA hanno chiuso: ecco il nostro recap di fine giornata... 🌆 "
            "La seduta a Wall Street si è chiusa con un tono complessivamente positivo per l'indice $SPX500 , "
            "che ha metabolizzato i risultati dell'inflazione CPI rilasciati oggi."
        )
        benchmarks_negative = {"SPX500": -1.11, "NSDQ100": -2.02}
        is_clean, issues, _ = verify_post_deterministic(
            user_reported_post,
            session_name="US_CLOSE",
            benchmark_daily=benchmarks_negative,
        )
        self.assertFalse(is_clean, "Positive tone on -1.11% drop must fail deterministic verification")
        self.assertTrue(any("Incongruenza di tono/sentiment" in i for i in issues))

    def test_sanitize_or_prune_post_content_fixes_sentiment_mismatch(self):
        """Sanitizer must replace positive sentiment with flessione/prese di beneficio when index dropped."""
        from post_verifier import sanitize_or_prune_post_content
        user_reported_post = (
            "Buonasera! I mercati USA hanno chiuso: ecco il nostro recap di fine giornata... 🌆 "
            "La seduta a Wall Street si è chiusa con un tono complessivamente positivo per l'indice $SPX500 , "
            "che ha metabolizzato i dati macro."
        )
        benchmarks_negative = {"SPX500": -1.11, "NSDQ100": -2.02}
        sanitized_text, is_modified, _ = sanitize_or_prune_post_content(
            user_reported_post,
            benchmark_daily=benchmarks_negative,
        )
        self.assertTrue(is_modified)
        self.assertNotIn("tono complessivamente positivo", sanitized_text)
        self.assertIn("chiuso con listini in flessione", sanitized_text)

    def test_sanitize_never_alters_positive_individual_stocks(self):
        """Sanitizer must NOT turn positive stock gains into flessione or calo even when indices are negative."""
        from post_verifier import sanitize_or_prune_post_content, verify_post_deterministic
        text = (
            "🌆 La seduta a Wall Street si è chiusa con listini in flessione: l'indice $SPX500 ha perso il -0.52%.\n\n"
            "📊 Ottima performance per $MRVL , che ha chiuso in rialzo del +2.26%.\n\n"
            "☁️ Seduta positiva per il software con l'ETF $WCLD.L , salito dell'1,2%.\n\n"
            "⚖️ Rotazione settoriale selettiva."
        )
        benchmarks_negative = {"SPX500": -0.52, "NSDQ100": -0.00}
        sanitized_text, is_clean, issues = sanitize_or_prune_post_content(
            text,
            session_name="US_CLOSE",
            benchmark_daily=benchmarks_negative,
        )
        self.assertIn("chiuso in rialzo del +2.26%", sanitized_text)
        self.assertNotIn("chiuso in flessione del +2.26%", sanitized_text)
        self.assertIn("Seduta positiva per il software", sanitized_text)
        self.assertNotIn("Seduta in flessione per il software", sanitized_text)

    def test_fix_sign_sentiment_oxymorons(self):
        """Oxymorons like 'chiuso in flessione del +2.26%' must be auto-corrected to positive wording."""
        from post_verifier import fix_sign_sentiment_oxymorons
        flawed = (
            "Ottima performance per $MRVL , che ha chiuso in flessione del +2.26%.\n"
            "Seduta in flessione per il software con l'ETF $WCLD.L , salito dell'1,2%.\n"
            "Titolo debole $TSLA , che ha chiuso in rialzo del -3.10%."
        )
        fixed = fix_sign_sentiment_oxymorons(flawed)
        self.assertIn("chiuso in rialzo del +2.26%", fixed)
        self.assertNotIn("chiuso in flessione del +2.26%", fixed)
        self.assertIn("Seduta positiva per il software con l'ETF $WCLD.L , salito dell'1,2%", fixed)
        self.assertIn("chiuso in calo del -3.10%", fixed)
        self.assertNotIn("chiuso in rialzo del -3.10%", fixed)

    def test_sentiment_mismatch_blocks_negative_tone_when_index_positive(self):
        """Deterministic gate must block negative tone and inverted signs when benchmarks are positive."""
        from post_verifier import verify_post_deterministic
        todays_hallucinated_post = (
            "🌆 La prima sessione d'oltreoceano della settimana si è chiusa in flessione, con l'indice $SPX500 che ha perso 0.66%, "
            "mentre il Nasdaq 100 ha mostrato una performance negativa, chiudendo a -1.21%. "
            "A guidare questa seduta negativa è stato un sentiment di preoccupazione generale..."
        )
        benchmarks_positive = {"SPX500": 0.67, "NSDQ100": 1.21}
        is_clean, issues, _ = verify_post_deterministic(
            todays_hallucinated_post,
            session_name="US_CLOSE",
            benchmark_daily=benchmarks_positive,
        )
        self.assertFalse(is_clean, "Negative tone on +0.67% / +1.21% gains must fail deterministic verification")
        self.assertTrue(any("Incongruenza di tono/sentiment" in i for i in issues))

    def test_enforce_benchmark_ground_truth_recovers_todays_exact_hallucination(self):
        """enforce_benchmark_ground_truth must turn inverted negative wording and signs into positive ones."""
        from post_verifier import enforce_benchmark_ground_truth
        todays_hallucinated_post = (
            "🌆 La prima sessione d'oltreoceano della settimana si è chiusa in flessione, con l'indice $SPX500 che ha perso 0.66%, "
            "mentre il Nasdaq 100 ha mostrato una performance negativa, chiudendo a -1.21%. "
            "A guidare questa seduta negativa è stato un sentiment di preoccupazione generale..."
        )
        benchmarks_positive = {"SPX500": 0.67, "NSDQ100": 1.21}
        corrected, was_modified = enforce_benchmark_ground_truth(
            todays_hallucinated_post,
            benchmark_daily=benchmarks_positive,
            session_name="US_CLOSE",
        )
        self.assertTrue(was_modified)
        self.assertNotIn("chiusa in flessione", corrected)
        self.assertNotIn("ha perso", corrected)
        self.assertNotIn("-1.21%", corrected)
        self.assertNotIn("seduta negativa", corrected)
        self.assertIn("chiusa in rialzo", corrected)
        self.assertIn("+0.67%", corrected)
        self.assertIn("+1.21%", corrected)

    def test_sanitize_or_prune_post_content_fixes_positive_market_sentiment_and_inverted_signs(self):
        """sanitize_or_prune_post_content must sanitize today's inverted signs and tone."""
        from post_verifier import sanitize_or_prune_post_content
        todays_hallucinated_post = (
            "🌆 La prima sessione d'oltreoceano della settimana si è chiusa in flessione, con l'indice $SPX500 che ha perso 0.66%, "
            "mentre il Nasdaq 100 ha mostrato una performance negativa, chiudendo a -1.21%. "
            "A guidare questa seduta negativa è stato un sentiment di preoccupazione generale..."
        )
        benchmarks_positive = {"SPX500": 0.67, "NSDQ100": 1.21}
        sanitized_text, is_clean, issues = sanitize_or_prune_post_content(
            todays_hallucinated_post,
            session_name="US_CLOSE",
            benchmark_daily=benchmarks_positive,
        )
        self.assertNotIn("ha perso 0.66%", sanitized_text)
        self.assertNotIn("-1.21%", sanitized_text)
        self.assertIn("+0.67%", sanitized_text)
        self.assertIn("+1.21%", sanitized_text)
        self.assertIn("seduta positiva", sanitized_text)

    def test_symmetric_rule_8_prompt_instructions(self):
        """Ensure _build_audit_prompt contains symmetric instructions for both positive and negative closes."""
        from independent_fact_checker import _build_audit_prompt, get_current_temporal_context
        ctx = get_current_temporal_context(session_name="US_CLOSE")
        prompt = _build_audit_prompt("Sample post", session_name="US_CLOSE", temporal_ctx=ctx)
        self.assertIn("CASO A: SE GLI INDICI HANNO CHIUSO IN RIALZO", prompt)
        self.assertIn("CASO B: SE GLI INDICI HANNO CHIUSO IN CALO", prompt)
        self.assertIn("TASSATIVAMENTE VIETATO invertire il segno matematico", prompt)


    def test_fetch_benchmarks_daily_performance(self):
        """Verify fetch_benchmarks_daily_performance returns expected structure with SPX500 and NSDQ100."""
        from finance_fetcher import fetch_benchmarks_daily_performance
        perf = fetch_benchmarks_daily_performance()
        self.assertIsInstance(perf, dict)
        self.assertIn("SPX500", perf)
        self.assertIn("NSDQ100", perf)
        if perf.get("SPX500") is not None:
            self.assertIsInstance(perf["SPX500"], float)

    def test_next_trading_session_info_deterministic(self):
        """Verify get_next_trading_session_info handles weekdays, weekends, and holidays."""
        import datetime
        import market_calendar

        # 1. Tuesday Oct 27, 2026 -> Wednesday Oct 28, 2026 (Tomorrow)
        tue = datetime.date(2026, 10, 27)
        info_tue = market_calendar.get_next_trading_session_info(tue, market="US")
        self.assertTrue(info_tue["is_tomorrow"])
        self.assertEqual(info_tue["next_date"], datetime.date(2026, 10, 28))
        self.assertIn("domani", info_tue["timing_phrase"])

        # 2. Friday Oct 30, 2026 -> Monday Nov 2, 2026 (Weekend skip)
        fri = datetime.date(2026, 10, 30)
        info_fri = market_calendar.get_next_trading_session_info(fri, market="US")
        self.assertFalse(info_fri["is_tomorrow"])
        self.assertEqual(info_fri["next_date"], datetime.date(2026, 11, 2))
        self.assertIn("lunedì", info_fri["timing_phrase"])
        self.assertNotIn("domani", info_fri["timing_phrase"])

        # 3. Wednesday Nov 25, 2026 -> Friday Nov 27, 2026 (Thanksgiving skipped)
        wed_tg = datetime.date(2026, 11, 25)
        info_tg = market_calendar.get_next_trading_session_info(wed_tg, market="US")
        self.assertFalse(info_tg["is_tomorrow"])
        self.assertEqual(info_tg["next_date"], datetime.date(2026, 11, 27))
        self.assertIn("Thanksgiving Day", info_tg["skipped_holidays"])

    def test_deterministic_gate_blocks_domani_on_friday_close(self):
        """On a Friday close, claiming 'domani a Wall Street' must fail the deterministic gate."""
        import datetime
        with patch("market_calendar.get_next_trading_session_info") as mock_info:
            mock_info.return_value = {
                "is_tomorrow": False,
                "timing_phrase": "alla riapertura dei mercati di lunedì (2 novembre)",
                "next_date": datetime.date(2026, 11, 2),
            }
            friday_post = (
                "🌆 Wall Street ha chiuso in territorio positivo. $SPX500 +0.80% $NSDQ100 +1.20%.\n\n"
                "🔹 $NVDA consolida la leadership con nuovi ordini enterprise.\n\n"
                "🔮 Domani a Wall Street vedremo come reagiranno i tecnologici all'apertura."
            )
            is_clean, issues, _ = verify_post_deterministic(friday_post, session_name="US_CLOSE")
            self.assertFalse(is_clean, "Stating 'domani a Wall Street' on a Friday must fail")
            self.assertTrue(any("Paradosso temporale sul giorno successivo" in i for i in issues))

    def test_deterministic_gate_blocks_hallucinated_earnings_date(self):
        """Claiming a company reports earnings tomorrow when scheduled weeks later must fail."""
        import datetime
        with patch("market_calendar.get_next_trading_session_info") as mock_info, \
             patch("market_calendar.get_upcoming_earnings_calendar") as mock_cal:
            mock_info.return_value = {
                "is_tomorrow": True,
                "timing_phrase": "nella seduta di domani (mercoledì 28 ottobre)",
                "next_date": datetime.date(2026, 10, 28),
            }
            mock_cal.return_value = {
                "NVDA": "2026-11-17",
                "MSFT": "2026-10-28",
            }
            hallucinated_post = (
                "🌆 Wall Street ha chiuso in territorio positivo. $SPX500 $NSDQ100\n\n"
                "🔹 $PLTR accelera.\n\n"
                "🔮 Nella seduta di domani riflettori puntati su $NVDA attesa per la trimestrale del quarto trimestre."
            )
            is_clean, issues, _ = verify_post_deterministic(hallucinated_post, session_name="US_CLOSE")
            self.assertFalse(is_clean, "Hallucinated earnings for NVDA tomorrow must fail")
            self.assertTrue(any("Allucinazione data trimestrale" in i for i in issues))
            self.assertTrue(any("NVDA" in i and "2026-11-17" in i for i in issues))

    def test_deterministic_gate_allows_verified_earnings_and_macro(self):
        """Verified earnings (Microsoft on 2026-10-28) or forward-looking macro must pass."""
        import datetime
        with patch("market_calendar.get_next_trading_session_info") as mock_info, \
             patch("market_calendar.get_upcoming_earnings_calendar") as mock_cal:
            mock_info.return_value = {
                "is_tomorrow": True,
                "timing_phrase": "nella seduta di domani (mercoledì 28 ottobre)",
                "next_date": datetime.date(2026, 10, 28),
            }
            mock_cal.return_value = {
                "MSFT": "2026-10-28",
                "GOOG": "2026-10-28",
            }
            valid_earnings_post = (
                "🌆 Wall Street ha archiviato la seduta in rialzo. $SPX500 $NSDQ100\n\n"
                "🔹 $PLTR consolida i guadagni.\n\n"
                "🔹 $AMZN mostra volumi sostenuti.\n\n"
                "🔮 Nella seduta di domani grande attesa per Microsoft che presenterà i conti trimestrali."
            )
            is_clean, issues, _ = verify_post_deterministic(valid_earnings_post, session_name="US_CLOSE")
            self.assertTrue(is_clean, f"Verified Microsoft earnings should pass: {issues}")


if __name__ == "__main__":
    unittest.main()



