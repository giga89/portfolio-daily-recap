#!/usr/bin/env python3
"""
Comprehensive Regression Suite: US_CLOSE Stock Direction & Ground-Truth Verification
====================================================================================
Tests every layer of defense preventing UP->DOWN and DOWN->UP stock inversions:
1. Real production bug from 2026-11-06 US_CLOSE ($TSM +6.24% -> -9.8%, $HUM meta-commentary & Dow crash).
2. Symmetric bidirectional detection & healing (UP->DOWN and DOWN->UP):
   - Clauses with ordinary prose words before $TICKER ('spicca $TSM', 'accelerazione per $NVDA')
   - Multi-ticker clauses ('$NVDA consolida mentre $TSM ha chiuso in calo del -9.8%')
   - Italian <1% articles ('lo 0.80%', 'dello 0.65%', 'dell\'1.2%')
   - Alphanumeric & international tickers ($1919.HK, $VOW3.DE, $SX7PEX.DE, $IB01.L, $PRY.MI)
   - Shorthand percentages ('$1919.HK (+3.50%)', '$NVDA -4.20%')
   - Qualitative direction-only claims without '%' (both ticker-first and intro-first)
   - Semantic oxymorons in both directions
3. Zero false positives on MTD/YTD ranking tables, 'PERCHÈ COPIARE' footer, fundamentals, and macro clauses.
4. End-to-end wiring across ai_news_generator, post_verifier, independent_fact_checker, tavily_search, and etoro_sender.
5. US_CLOSE prompt generation on red days when <3 portfolio stocks closed positive.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from post_verifier import (
    verify_post_deterministic,
    enforce_stock_ground_truth,
    sanitize_or_prune_post_content,
    verify_and_clean_post,
)
from independent_fact_checker import (
    _build_audit_prompt,
    get_current_temporal_context,
    sanitize_verified_text,
    run_independent_fact_check,
    run_micro_topic_consensus_fact_check,
)
from tavily_search import filter_live_news_for_topic
from ai_news_generator import (
    _run_post_verification,
    _format_us_close_stock_microtopic_instruction,
)
import etoro_sender


class TestUSCloseStockDirectionVerification(unittest.TestCase):

    def setUp(self):
        self.benchmarks_green = {"SPX500": 0.62, "NSDQ100": 1.15, "DJ30": 0.28}
        self.benchmarks_red = {"SPX500": -1.35, "NSDQ100": -2.10, "DJ30": -0.95}
        self.stock_data_mixed = {
            "TSM": {"daily_change": 6.24, "has_traded_today": True},
            "HUM": {"daily_change": 5.24, "has_traded_today": True},
            "PRY.MI": {"daily_change": 3.38, "has_traded_today": True},
            "NVDA": {"daily_change": -3.40, "has_traded_today": True},
            "1919.HK": {"daily_change": -2.80, "has_traded_today": True},
            "VOW3.DE": {"daily_change": -1.90, "has_traded_today": True},
            "SX7PEX.DE": {"daily_change": 1.15, "has_traded_today": True},
            "IB01.L": {"daily_change": 0.08, "has_traded_today": True},
            "MSFT": {"daily_change": 1.10, "has_traded_today": True},
            "ENEL.MI": {"daily_change": 0.95, "has_traded_today": True},
        }

    # ── 1. Real Production Failure (2026-11-06 US_CLOSE) ─────────────────────

    def test_real_production_us_close_failure_detected_and_healed(self):
        """Exact reproduction of run 42293330478: $TSM +6.24% -> -9.8% and $HUM meta-commentary + Dow crash."""
        corrupted_post = (
            "Buonasera! I mercati USA hanno chiuso: ecco il recap di oggi.\n\n"
            "🌆 Wall Street ha archiviato una seduta solida con l'indice $SPX500 in rialzo del +0.62% "
            "grazie al raffreddamento dei rendimenti obbligazionari.\n\n"
            "💻 Tra i titoli più brillanti del nostro portafoglio spicca $TSM , che ha chiuso in calo del -9.8% "
            "grazie alla domanda record per i nodi a 2 nanometri e per il packaging CoWoS.\n\n"
            "🏥 Ottima giornata anche per $HUM (+5.24%), sebbene la performance specifica non sia stata confermata "
            "nelle fonti principali, in un contesto con il Dow Jones in calo di circa 1.200 punti.\n\n"
            "🔮 Nella prossima seduta monitoreremo i dati macroeconomici USA."
        )

        is_clean, issues, _ = verify_post_deterministic(
            corrupted_post,
            session_name="U.S. market close",
            benchmark_daily=self.benchmarks_green,
            stock_data=self.stock_data_mixed,
        )
        self.assertFalse(is_clean)
        self.assertTrue(any("TSM" in i and "Inversione di segno" in i for i in issues), f"Missing TSM issue: {issues}")
        self.assertTrue(any("fonti" in i.lower() for i in issues), f"Missing meta-commentary issue: {issues}")
        self.assertTrue(any("Dow Jones" in i for i in issues), f"Missing Dow crash issue: {issues}")

        healed, ok, rem = sanitize_or_prune_post_content(
            corrupted_post,
            session_name="U.S. market close",
            benchmark_daily=self.benchmarks_green,
            stock_data=self.stock_data_mixed,
        )
        self.assertTrue(ok, f"Post should heal cleanly, remaining issues: {rem}\nHealed:\n{healed}")
        self.assertIn("Tra i titoli più brillanti del nostro portafoglio spicca $TSM", healed)
        self.assertIn("+6.24%", healed)
        self.assertNotIn("-9.8%", healed)
        self.assertNotIn("nelle fonti principali", healed)
        self.assertNotIn("1.200 punti", healed)

    # ── 2. Bidirectional Enforcement & Detection (UP->DOWN and DOWN->UP) ─────

    def test_vice_versa_down_stock_described_as_up_with_percentage(self):
        """Stock that closed DOWN (-3.40%) described as UP (+4.10%) must be flagged and corrected to -3.40%."""
        bad_text = (
            "🌆 Chiusura mista a Wall Street con $SPX500 a +0.62%.\n\n"
            "🤖 Forte accelerazione per $NVDA , che ha chiuso in rialzo del +4.10% grazie ai chip Blackwell.\n\n"
            "🚢 Tra i titoli più brillanti del portafoglio spicca $1919.HK , salito del +3.20% sulle rotte asiatiche."
        )
        is_clean, issues, _ = verify_post_deterministic(
            bad_text,
            session_name="US_CLOSE",
            benchmark_daily=self.benchmarks_green,
            stock_data=self.stock_data_mixed,
        )
        self.assertFalse(is_clean)
        self.assertTrue(any("NVDA" in i and "Inversione di segno" in i for i in issues), issues)
        self.assertTrue(any("1919.HK" in i and "Inversione di segno" in i for i in issues), issues)

        fixed, modified = enforce_stock_ground_truth(
            bad_text,
            stock_data=self.stock_data_mixed,
            session_name="US_CLOSE",
        )
        self.assertTrue(modified)
        self.assertIn("-3.40%", fixed)
        self.assertNotIn("+4.10%", fixed)
        self.assertIn("-2.80%", fixed)
        self.assertNotIn("+3.20%", fixed)
        self.assertNotIn("Forte accelerazione per $NVDA", fixed)
        self.assertNotIn("Tra i titoli più brillanti del portafoglio spicca $1919.HK", fixed)

        is_clean_after, after_issues, _ = verify_post_deterministic(
            fixed,
            session_name="US_CLOSE",
            benchmark_daily=self.benchmarks_green,
            stock_data=self.stock_data_mixed,
        )
        self.assertTrue(is_clean_after, f"Expected clean text after healing, got: {after_issues}\nText:\n{fixed}")

    def test_italian_articles_lo_and_dello_under_one_percent_both_directions(self):
        """Italian '<1%' articles ('lo 0.80%', 'dello 0.65%') must be caught in both UP->DOWN and DOWN->UP."""
        stock_sub1 = {
            "NVDA": {"daily_change": -0.85, "has_traded_today": True},
            "TSM": {"daily_change": 0.92, "has_traded_today": True},
        }
        bad_down_as_up = "🤖 Oggi $NVDA guadagna lo 0.80% e chiude in rialzo dello 0.80% a Wall Street."
        ok1, issues1, _ = verify_post_deterministic(bad_down_as_up, session_name="US_CLOSE", stock_data=stock_sub1)
        self.assertFalse(ok1)
        self.assertTrue(any("NVDA" in i for i in issues1), issues1)

        bad_up_as_down = "💻 Oggi $TSM perde lo 0.75% e archivia la seduta in calo dello 0.75%."
        ok2, issues2, _ = verify_post_deterministic(bad_up_as_down, session_name="US_CLOSE", stock_data=stock_sub1)
        self.assertFalse(ok2)
        self.assertTrue(any("TSM" in i for i in issues2), issues2)

        fixed1, _ = enforce_stock_ground_truth(bad_down_as_up, stock_data=stock_sub1, session_name="US_CLOSE")
        self.assertIn("-0.85%", fixed1)
        fixed2, _ = enforce_stock_ground_truth(bad_up_as_down, stock_data=stock_sub1, session_name="US_CLOSE")
        self.assertIn("+0.92%", fixed2)

    def test_alphanumeric_and_international_shorthand_both_directions(self):
        """Shorthand '$1919.HK (+3.50%)' and '$SX7PEX.DE (-1.80%)' must be caught and fixed."""
        bad_shorthand = (
            "🚢 Seduta movimentata per $1919.HK (+3.50%) e per $VOW3.DE (+2.10%) in Europa.\n\n"
            "🏦 Sotto i riflettori anche $SX7PEX.DE (-1.80%) nel comparto bancario."
        )
        ok, issues, _ = verify_post_deterministic(bad_shorthand, session_name="US_CLOSE", stock_data=self.stock_data_mixed)
        self.assertFalse(ok)
        self.assertTrue(any("1919.HK" in i for i in issues), issues)
        self.assertTrue(any("VOW3.DE" in i for i in issues), issues)
        self.assertTrue(any("SX7PEX.DE" in i for i in issues), issues)

        fixed, _ = enforce_stock_ground_truth(bad_shorthand, stock_data=self.stock_data_mixed, session_name="US_CLOSE")
        self.assertIn("$1919.HK (-2.80%)", fixed)
        self.assertIn("$VOW3.DE (-1.90%)", fixed)
        self.assertIn("$SX7PEX.DE (+1.15%)", fixed)

    def test_multi_ticker_same_clause_does_not_swallow_second_ticker(self):
        """First ticker in clause ('$MSFT consolida mentre $TSM ha chiuso in calo del -9.8%') must not block $TSM fix."""
        clause = "💻 $MSFT consolida i livelli chiave mentre $TSM ha chiuso in calo del -9.8% nonostante i ricavi record."
        ok, issues, _ = verify_post_deterministic(clause, session_name="US_CLOSE", stock_data=self.stock_data_mixed)
        self.assertFalse(ok)
        self.assertTrue(any("TSM" in i for i in issues), issues)

        fixed, mod = enforce_stock_ground_truth(clause, stock_data=self.stock_data_mixed, session_name="US_CLOSE")
        self.assertTrue(mod)
        self.assertIn("$TSM ha chiuso in rialzo del +6.24%", fixed)

    def test_qualitative_direction_only_contradictions_without_pct_both_directions(self):
        """Qualitative claims without '%' must be blocked both when DOWN stock is called UP and UP stock is called DOWN."""
        down_called_up_cases = [
            "🤖 $NVDA ha chiuso in rialzo spinta dai data center.",
            "🤖 $NVDA sale grazie alla forte domanda di infrastrutture AI.",
            "🤖 A Wall Street brilla $NVDA tra i semiconduttori.",
            "🚢 Ottima seduta per $1919.HK sulle rotte container.",
            "🚗 Forte rialzo per $VOW3.DE a Francoforte.",
        ]
        for txt in down_called_up_cases:
            with self.subTest(txt=txt):
                ok, issues, _ = verify_post_deterministic(txt, session_name="US_CLOSE", stock_data=self.stock_data_mixed)
                self.assertFalse(ok, f"Should block DOWN->UP qualitative claim: {txt}")
                self.assertTrue(any("Contraddizione direzionale" in i for i in issues), issues)

        up_called_down_cases = [
            "💻 $TSM ha chiuso in calo a Wall Street.",
            "💻 $TSM scende per prese di beneficio sul comparto chip.",
            "🔌 Seduta difficile per $PRY.MI a Piazza Affari.",
            "💻 In forte calo $TSM sul finale di seduta.",
            "🏥 Prese di beneficio su $HUM nel settore sanitario.",
        ]
        for txt in up_called_down_cases:
            with self.subTest(txt=txt):
                ok, issues, _ = verify_post_deterministic(txt, session_name="US_CLOSE", stock_data=self.stock_data_mixed)
                self.assertFalse(ok, f"Should block UP->DOWN qualitative claim: {txt}")
                self.assertTrue(any("Contraddizione direzionale" in i for i in issues), issues)

    def test_semantic_oxymorons_both_directions_without_stock_data(self):
        """Even without stock_data, explicit semantic oxymorons in either direction must fail deterministic check."""
        up_intro_down_close = "Tra i titoli più brillanti del portafoglio spicca $TSM, che ha chiuso in calo."
        ok1, issues1, _ = verify_post_deterministic(up_intro_down_close, session_name="US_CLOSE")
        self.assertFalse(ok1)
        self.assertTrue(any("Ossimoro semantico" in i for i in issues1), issues1)

        down_intro_up_close = "Tra i titoli peggiori di oggi figura $NVDA, che ha chiuso in rialzo."
        ok2, issues2, _ = verify_post_deterministic(down_intro_up_close, session_name="US_CLOSE")
        self.assertFalse(ok2)
        self.assertTrue(any("Ossimoro semantico inverso" in i for i in issues2), issues2)

    # ── 3. Zero False Positives on Tables, Footers, Fundamentals & Macro ─────

    def test_preserves_mtd_ytd_ranking_tables_and_footer_without_false_positives(self):
        """MTD/YTD tables (where VOW3.DE is +7.03% MTD despite -1.90% today) and footer must remain untouched."""
        full_recap = (
            "🌆 CHIUSURA DEI MERCATI 📈\n\n"
            "MIGLIORI 3 PERFORMANCE MENSILI 📈\n"
            "💻 TSM +14.20%\n"
            "🚗 VOW3.DE +7.03%\n"
            "🔌 PRY.MI +5.10%\n\n"
            "MIGLIORI 3 DI SEMPRE (YTD) DEL PORTAFOGLIO 📈\n"
            "💻 TSM +88.40%\n"
            "🏥 HUM +46.55%\n\n"
            "🌆 Wall Street chiude positiva con l'indice $SPX500 a +0.62%.\n\n"
            "💻 $TSM (+6.24%) guida i semiconduttori grazie alla capacità CoWoS.\n\n"
            "💻 $MSFT registra un'espansione di Azure (+29% nell'ultimo trimestre) con margini solidi.\n\n"
            "🔋 $ENEL.MI conferma investimenti sulla rete elettrica e un debito netto in calo.\n\n"
            "Con i rendimenti Treasury in calo, $HUM (+5.24%) consolida il rimbalzo nel comparto sanitario.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 PERCHÈ COPIARE QUESTO PORTAFOGLIO?\n"
            "📊 VOW3.DE +18.00% | SPX500 +12.00%"
        )
        enforced, was_mod = enforce_stock_ground_truth(full_recap, stock_data=self.stock_data_mixed, session_name="US_CLOSE")
        self.assertFalse(was_mod, f"Valid full recap should not be modified!\nDiff:\n{enforced}")
        self.assertIn("🚗 VOW3.DE +7.03%", enforced)
        self.assertIn("🏥 HUM +46.55%", enforced)
        self.assertIn("(+29% nell'ultimo trimestre)", enforced)

        ok, issues, _ = verify_post_deterministic(
            full_recap,
            session_name="US_CLOSE",
            benchmark_daily=self.benchmarks_green,
            stock_data=self.stock_data_mixed,
        )
        self.assertTrue(ok, f"Valid full recap should pass with 0 critical issues, got: {issues}")

    # ── 4. End-to-End Wiring: ai_news_generator, independent_fact_checker, Tavily, etoro_sender ─

    def test_tavily_topic_filter_prevents_macro_crash_bleed_into_stock_paragraphs(self):
        """filter_live_news_for_topic must strip macro Dow crash headlines when auditing a single stock paragraph."""
        multi_block_ctx = (
            "🌍 CONTESTO MACRO E MERCATI (FONTI LIVE):\n"
            "• [2026-11-04 ⚠️ ARTICOLO DI GIORNI PRECEDENTI] Dow Jones plunges 1,200 points in global sell-off\n\n"
            "📊 NOTIZIE E DATI REALI PER $TSM (TSMC):\n"
            "• [2026-11-06 — OGGI] TSMC surges on AI chip packaging demand\n"
        )
        tsm_filtered = filter_live_news_for_topic(
            multi_block_ctx,
            "💻 $TSM ha chiuso in rialzo del +6.24% grazie ai chip AI.",
            topic_type="stock_paragraph",
        )
        self.assertIn("TSMC surges", tsm_filtered)
        self.assertNotIn("1,200 points", tsm_filtered)

        hum_filtered = filter_live_news_for_topic(
            multi_block_ctx,
            "🏥 $HUM ha chiuso in rialzo del +5.24% nel settore assicurativo.",
            topic_type="stock_paragraph",
        )
        self.assertEqual(hum_filtered, "")

    def test_independent_fact_checker_accepts_stock_data_and_blocks_auditor_corruption(self):
        """verify_and_clean_post with run_ai_review=True must pass stock_data without TypeError and heal Groq corruption."""
        clean_draft = (
            "Buonasera! Ecco il punto sulla chiusura USA di oggi.\n\n"
            "🌆 Wall Street archivia la seduta in rialzo con $SPX500 a +0.62% grazie al calo dei rendimenti.\n\n"
            "💻 Tra i titoli più brillanti del nostro portafoglio spicca $TSM , che ha chiuso in rialzo del +6.24% "
            "grazie alla domanda per i nodi avanzati a 2 nanometri.\n\n"
            "🤖 Seduta in flessione invece per $NVDA , che ha chiuso in calo del -3.40% per prese di beneficio.\n\n"
            "Quale movimento vi ha colpito di più oggi? Scrivetelo nei commenti! 👇"
        )

        # Simulate rogue Groq/Mistral auditor trying to corrupt BOTH stocks in opposite wrong directions:
        # - flipping $TSM +6.24% -> -9.8%
        # - flipping $NVDA -3.40% -> +4.10% and leaking 'nelle fonti principali'
        def fake_groq_corruptor(text, **kwargs):
            # Verify stock_data reached audit_with_groq without TypeError!
            self.assertIn("stock_data", kwargs)
            self.assertIsNotNone(kwargs["stock_data"])
            corrupted = text
            if "$TSM" in text:
                corrupted = (
                    "💻 Tra i titoli più brillanti del nostro portafoglio spicca $TSM , "
                    "che ha chiuso in calo del -9.8% nelle fonti principali."
                )
            elif "$NVDA" in text:
                corrupted = (
                    "🤖 Ottima seduta per $NVDA , che ha chiuso in rialzo del +4.10%, "
                    "sebbene la variazione non sia stata confermata nelle fonti principali."
                )
            # Run real sanitize_verified_text just like audit_with_groq does on HTTP 200
            corrupted = sanitize_verified_text(
                text,
                corrupted,
                session_name=kwargs.get("session_name"),
                benchmark_daily_data=kwargs.get("benchmark_daily_data"),
                stock_data=kwargs.get("stock_data"),
            )
            return {
                "decision": "AUTO_CORRECT",
                "score": 88,
                "verified_text": corrupted,
                "temporal_issues": [],
                "hallucinations_detected": ["test"],
                "auditor": "groq:mock",
                "explanation": "Mock auto-correct",
            }

        with patch("independent_fact_checker.audit_with_groq", side_effect=fake_groq_corruptor), \
             patch("independent_fact_checker.audit_with_mistral", return_value=None), \
             patch("independent_fact_checker.is_tavily_available", return_value=False):
            approved, final_text, audit = verify_and_clean_post(
                clean_draft,
                session_name="U.S. market close",
                run_ai_review=True,
                benchmark_daily=self.benchmarks_green,
                stock_data=self.stock_data_mixed,
            )

        self.assertTrue(approved, f"Expected post to survive rogue auditor via ground-truth enforcement: {audit}")
        self.assertIn("+6.24%", final_text)
        self.assertNotIn("-9.8%", final_text)
        self.assertIn("-3.40%", final_text)
        self.assertNotIn("+4.10%", final_text)
        self.assertNotIn("nelle fonti principali", final_text)

    def test_audit_prompt_injects_certified_stock_ground_truth(self):
        """_build_audit_prompt must include certified Yahoo Finance stock % and anti-meta-commentary rules."""
        ctx = get_current_temporal_context("US_CLOSE", benchmark_daily_data=self.benchmarks_green)
        prompt = _build_audit_prompt(
            text="Test $TSM e $NVDA",
            session_name="US_CLOSE",
            temporal_ctx=ctx,
            stock_data=self.stock_data_mixed,
        )
        self.assertIn("PERFORMANCE CERTIFICATA SINGOLI TITOLI OGGI", prompt)
        self.assertIn("$TSM: +6.24% [RIALZO (+)]", prompt)
        self.assertIn("$NVDA: -3.40% [CALO (-)]", prompt)
        self.assertIn("DIVIETO ASSOLUTO DI META-COMMENTI", prompt)

    def test_ai_news_generator_run_post_verification_wires_stock_data(self):
        """_run_post_verification in ai_news_generator must block unverified sign inversions using stock_data."""
        inverted_draft = (
            "🌆 Wall Street chiude in calo con $SPX500 a -1.35%.\n\n"
            "🤖 $NVDA sale con forza e chiude in rialzo del +3.80% trainando il comparto tech."
        )
        approved, out = _run_post_verification(
            inverted_draft,
            session_name="U.S. market close",
            run_ai_review=False,
            benchmark_daily=self.benchmarks_red,
            stock_data=self.stock_data_mixed,
        )
        self.assertFalse(approved, f"Deterministic gate in _run_post_verification must reject inverted NVDA sign, got: {out}")

    def test_etoro_sender_wires_stock_data_and_auto_heals_before_publish(self):
        """etoro_sender.send_etoro_post must auto-sanitize inverted stock % when stock_data is passed."""
        captured = {}

        def fake_create_post(content, **kwargs):
            captured["message"] = content
            return {"success": True, "id": "mock_post_123"}

        bad_etoro_post = (
            "Buonasera investitori!\n\n"
            "🌆 Chiusura positiva a Wall Street con $SPX500 a +0.62%.\n\n"
            "💻 Tra i titoli più brillanti del portafoglio spicca $TSM , che ha chiuso in calo del -9.8% "
            "grazie ai nodi a 2 nanometri.\n\n"
            "🔮 Domani occhi puntati sui dati macro."
        )
        with patch.object(etoro_sender.etoro_client, "is_configured", return_value=True), \
             patch.object(etoro_sender.etoro_client, "create_post", side_effect=fake_create_post), \
             patch("market_calendar.get_next_trading_session_info", return_value={"is_tomorrow": True, "timing_phrase": "domani", "next_date": None}):
            ok = etoro_sender.send_etoro_post(
                text=bad_etoro_post,
                session_name="U.S. market close",
                stock_data=self.stock_data_mixed,
                benchmark_daily=self.benchmarks_green,
            )
        self.assertTrue(ok)
        self.assertIn("+6.24%", captured["message"])
        self.assertNotIn("-9.8%", captured["message"])

    # ── 5. US_CLOSE Prompt Safety When <3 Portfolio Stocks Closed Positive ───

    def test_us_close_prompt_instruction_handles_negative_stocks_on_deep_red_day(self):
        """When <3 stocks are positive on a red day, negative stocks must NOT be labeled 'variazione positiva'."""
        pos_inst = _format_us_close_stock_microtopic_instruction(
            1, {"ticker": "TSM", "daily_change": 6.24, "news_snippet": "Domanda AI."}
        )
        self.assertIn("RIALZO CERTIFICATO", pos_inst)
        self.assertIn("maggiore variazione positiva", pos_inst)

        neg_inst = _format_us_close_stock_microtopic_instruction(
            2, {"ticker": "NVDA", "daily_change": -2.45, "news_snippet": "Prese di beneficio."}
        )
        self.assertIn("RIBASSO CERTIFICATO", neg_inst)
        self.assertIn("IN CALO (-2.45%", neg_inst)
        self.assertNotIn("Secondo titolo per variazione positiva", neg_inst)
        self.assertIn("SEVERAMENTE VIETATO definirlo in rialzo", neg_inst)

    def test_micro_topics_skip_static_tables_and_why_copy_footer_and_support_change_pct(self):
        """split_into_micro_topics must not audit deterministic MIGLIORI tables or PERCHÈ COPIARE footer; change_pct alias works."""
        from independent_fact_checker import split_into_micro_topics, reassemble_micro_topics

        full_recap = (
            "MIGLIORI 5 DI OGGI DEL PORTAFOGLIO 📈\n"
            "• TSM (Taiwan Semiconductor): +6.24%\n"
            "• HUM (Humana): +5.24%\n\n"
            "MIGLIORI 5 PERFORMANCE MENSILI 📈\n"
            "• VOW3.DE (Volkswagen): +7.03%\n"
            "• TSM (Taiwan Semiconductor): +6.80%\n\n"
            "🌆 Wall Street chiude positiva con $SPX500 a +0.62%.\n\n"
            "Ottima intonazione per $NVDA che chiude in deciso rialzo grazie al comparto AI.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 PERCHÈ COPIARE QUESTO PORTAFOGLIO?\n\n"
            "✅ PUNTI DI FORZA DELLA STRATEGIA:\n"
            "• Diversificazione intelligente su 3 continenti\n"
            "• Focus sui megatrend del futuro: AI, Sanità ed Energia"
        )
        topics = split_into_micro_topics(full_recap)
        audited_texts = [t["text"] for t in topics if t["needs_audit"]]
        self.assertEqual(len(audited_texts), 2, f"Only the 2 narrative paragraphs should be audited, got: {audited_texts}")
        self.assertEqual(reassemble_micro_topics(topics).strip(), full_recap.strip())

        # Also verify change_pct dict alias + 'deciso rialzo' / 'Ottima intonazione per' healing
        alt_stock_data = {"NVDA": {"change_pct": -3.40}}
        healed, changed = enforce_stock_ground_truth(
            full_recap, stock_data=alt_stock_data, session_name="U.S. market close"
        )
        self.assertTrue(changed)
        self.assertIn("-3.40%", healed)
        self.assertNotIn("deciso rialzo", healed.lower())
        self.assertNotIn("ottima intonazione per $nvda", healed.lower())


if __name__ == "__main__":
    unittest.main()
