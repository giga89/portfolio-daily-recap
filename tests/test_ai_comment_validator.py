#!/usr/bin/env python3
"""
Unit tests for AI Community Comment Responder validation guardrails,
syntax checks, fallback engine, and anti-duplication logic.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import ai_comment_responder
from ai_comment_responder import (
    validate_response_syntax,
    _build_contextual_fallback,
    _detect_language,
    _is_simple_gratitude,
    _build_portfolio_grounding_context,
    generate_ai_comment_reply,
    load_andrea_style_archive,
    DEFAULT_ANDREA_STYLE_SEEDS,
    is_third_party_mention,
    is_ignore_or_opt_out
)
from post_verifier import verify_post_deterministic, verify_and_clean_comment


class TestAICommentValidator(unittest.TestCase):

    def test_reject_truncated_cut_off_phrases(self):
        """Should strictly reject cut-off sentences ending in stop words or lacking punctuation."""
        # Case 1: Short broken phrase (e.g. 29 chars)
        bad_reply_1 = "Ciao @KidShark, grazie per il"
        ok, _, reason = validate_response_syntax(bad_reply_1, "KidShark")
        self.assertFalse(ok)
        self.assertIn("too short", reason.lower())

        # Case 2: Long sentence cut off on dangling preposition
        bad_reply_long = (
            "Ciao @KidShark! Riguardo alla posizione su AMZN e alla recente aggiunta di infrastruttura GPU "
            "di cui parli su Yahoo Finance, pensiamo che la strategia a lungo termine sia molto efficace per il"
        )
        ok, _, reason = validate_response_syntax(bad_reply_long, "KidShark")
        self.assertFalse(ok)
        self.assertIn("cut off on trailing word/preposition", reason)

        # Case 3: Truncated short gratitude without substance
        bad_reply_2 = "Ciao @KidShark, grazie mille"
        ok, _, reason = validate_response_syntax(bad_reply_2, "KidShark")
        self.assertFalse(ok)

        # Case 4: Cut off with comma or dash
        bad_reply_3 = "Ciao @KidShark! Riguardo ad AMZN e alle GPU, pensiamo che la strategia di lungo termine sia valida e coerente con la nostra gestione,"
        ok, _, reason = validate_response_syntax(bad_reply_3, "KidShark")
        self.assertFalse(ok)
        self.assertIn("incomplete punctuation symbol", reason)

        # Case 5: No terminal punctuation/emoji
        bad_reply_4 = "Ciao @KidShark! Riguardo ad AMZN e alle GPU pensiamo che la strategia sia solida e che AWS continuerà a crescere bene"
        ok, _, reason = validate_response_syntax(bad_reply_4, "KidShark")
        self.assertFalse(ok)
        self.assertIn("does not end with terminal punctuation", reason)

    def test_accept_complete_valid_responses(self):
        """Should accept fluent, complete, well-formed responses with proper tags and emojis."""
        good_reply = (
            "Ciao @KidShark! 📊 Riguardo ad $AMZN e ai semiconduttori, riteniamo che l'integrazione di GPU e chip proprietari AWS "
            "rafforzerà i margini nel medio-lungo termine. Con il nostro approccio a Risk Score 3/10 e zero leva, la volatilità di breve termine "
            "rappresenta solo rumore di mercato.\n\n"
            "Un caro saluto e i migliori auguri per la tua vita e per il tuo trading! 📈🤝"
        )
        ok, cleaned, reason = validate_response_syntax(good_reply, "KidShark")
        self.assertTrue(ok, f"Expected valid response, got reason: {reason}")
        self.assertIn("@KidShark", cleaned)
        self.assertNotIn("**", cleaned)

    def test_markdown_bold_stripping(self):
        """Should cleanly strip markdown asterisks without altering words."""
        bold_reply = (
            "Ciao @KidShark! Il nostro **Risk Score 3/10** e la strategia su **$NVDA** rimangono invariati per il lungo termine. "
            "Continuiamo ad accumulare con disciplina e senza alcuna leva finanziaria.\n\n"
            "Un caro saluto e buon trading! 📈🤝"
        )
        ok, cleaned, _ = validate_response_syntax(bold_reply, "KidShark")
        self.assertTrue(ok)
        self.assertNotIn("**", cleaned)
        self.assertIn("Risk Score 3/10", cleaned)
        self.assertIn("$NVDA", cleaned)

    def test_kidshark_specific_comment_fallback(self):
        """Should produce a tailored, rich, complete response for the AMZN/GPU/tech sentiment question."""
        user_comment = "La gestione attiva è chiave. Ho anch'io AMZN e, come riportato da Yahoo Finance, la recente aggiunta di GPU non l'ha aiutata. Ti preoccupa il sentiment sulle tech?"
        author = "KidShark"
        reply = _build_contextual_fallback(user_comment, author, ["AMZN", "NVDA"], "it")

        # Must address AMZN, AWS, Capex / sentiment, and Risk Score
        self.assertIn("@KidShark", reply)
        self.assertTrue("AMZN" in reply or "Amazon" in reply or "AWS" in reply)
        self.assertTrue("Risk Score 3/10" in reply or "3/10" in reply)
        self.assertTrue(reply.endswith("🤝") or reply.endswith("📈") or reply.endswith("."))
        self.assertGreater(len(reply), 150)

    def test_simple_gratitude_handling(self):
        """Short thanks and pure feed compliments should get warm short closing; real questions/topics must return False."""
        self.assertTrue(_is_simple_gratitude("Grazie mille!"))
        self.assertTrue(_is_simple_gratitude("Thanks a lot! 👍"))
        self.assertTrue(_is_simple_gratitude("Ogni giorno un valore aggiunto per il feed 🌟"))
        self.assertTrue(_is_simple_gratitude("Un piacere leggere contenuti così ben curati 👌"))
        self.assertFalse(_is_simple_gratitude("Ho una domanda sui dividendi di PLTR e sulla crescita futura delle tech?"))
        self.assertFalse(_is_simple_gratitude("Cosco Shipping ($1919.HK) garantisce una posizione sui flussi marittimi"))
        self.assertFalse(_is_simple_gratitude("Direi secondo mese difficile 😅"))
        self.assertFalse(_is_simple_gratitude("Ottima fino alle 17..."))

    def test_reject_dca_pac_and_wdef_defensive_mislabeling(self):
        """Deterministic syntax and post verifier gates must reject all DCA/PAC phrasing and WDEF-as-defensive."""
        bad_dca_replies = [
            "Ciao @Alvaro! Con un buon Dollar-Cost Averaging la volatilità diventa un'alleata nel tempo sui nostri asset. Un caro saluto! 📈",
            "Ciao @Luigi! Puoi continuare ad accumulare tramite il nostro DCA mensile con grande serenità e disciplina sui fondamentali. Un saluto! 🤝",
            "Ciao @Marco! Ti suggerisco di impostare un PAC o piano di accumulo con ingressi periodici sul portafoglio nel tempo. Un caro saluto! 📊",
            "Ciao @Sara! Gli ingressi frazionati mensili con versamenti ricorrenti ti aiutano a superare la paura del mercato nel tempo. Un saluto! ✨",
        ]
        for bad in bad_dca_replies:
            ok_syn, _, reason = validate_response_syntax(bad, "UserTest")
            self.assertFalse(ok_syn, f"Syntax validator must reject DCA/PAC reply: {bad}")
            self.assertIn("dca", reason.lower())

            ok_det, issues, _ = verify_post_deterministic(bad)
            self.assertFalse(ok_det, f"Deterministic gate must reject DCA/PAC text: {bad} | {issues}")

            ok_comm, _, _ = verify_and_clean_comment(bad, user_comment="Cosa ne pensi?", user_author="UserTest", run_ai_review=False)
            self.assertFalse(ok_comm, f"Comment gatekeeper must reject DCA/PAC reply: {bad}")

        # Legitimate UCITS ETF distribution policy ("ad accumulazione") MUST remain allowed
        legit_acc = (
            "Ciao @Marco! L'ETF $IB01.L è ad accumulazione (capitalizza automaticamente gli interessi dei Treasury USA nel NAV senza staccare cedole) "
            "e funge da riserva tattica di liquidità nel portafoglio. Un caro saluto! 💵🤝"
        )
        ok_syn_legit, _, err_legit = validate_response_syntax(legit_acc, "Marco")
        self.assertTrue(ok_syn_legit, f"UCITS 'ad accumulazione' must stay allowed: {err_legit}")
        ok_det_legit, det_issues, _ = verify_post_deterministic(legit_acc, primary_ticker="IB01.L")
        self.assertTrue(ok_det_legit, f"UCITS 'ad accumulazione' must pass deterministic gate: {det_issues}")

        # WDEF.L mislabeled as defensive / safe haven must fail; multi-asset post with PPFB defensive must pass
        bad_wdef = (
            "Ciao @Luca! In queste fasi teniamo $WDEF.L come titolo difensivo e bene rifugio per proteggere il portafoglio dai cali del mercato. Un caro saluto! 🛡️"
        )
        ok_wdef_syn, _, _ = validate_response_syntax(bad_wdef, "Luca")
        self.assertFalse(ok_wdef_syn, "WDEF.L called 'titolo difensivo' / 'bene rifugio' must fail syntax check")
        ok_wdef_det, _, _ = verify_post_deterministic(bad_wdef, primary_ticker="WDEF.L")
        self.assertFalse(ok_wdef_det, "WDEF.L called 'titolo difensivo' must fail deterministic gate")

        good_multi = (
            "Ciao @Luca! Nel portafoglio puntiamo sul settore difesa europeo tramite $WDEF.L (ad accumulazione) per catturare il riarmo NATO, "
            "mentre per le coperture difensive ci affidiamo all'oro fisico $PPFB.DE e alla cassa $IB01.L. Un caro saluto! 🛡️🥇"
        )
        ok_multi_syn, _, err_multi = validate_response_syntax(good_multi, "Luca")
        self.assertTrue(ok_multi_syn, f"Distinct WDEF vs PPFB defensive mention should pass: {err_multi}")

    def test_portfolio_grounding_context_resolution(self):
        """Grounding context must resolve holdings with weights, plain company names, and never block general portfolio comments."""
        ctx_cosco = _build_portfolio_grounding_context(
            user_comment="Cosco Shipping ($1919.HK) garantisce posizione sui flussi marittimi",
            post_context="SONDAGGIO COMMUNITY: TOP PERFORMER DELLA SETTIMANA",
            relevant_tickers=["SPX500", "1919.HK", "TRIG.L", "TRX"],
        )
        self.assertIn("$1919.HK", ctx_cosco)
        self.assertIn("IN PORTAFOGLIO", ctx_cosco)
        self.assertIn("$SPX500", ctx_cosco)
        self.assertIn("NON IN PORTAFOGLIO", ctx_cosco)

        ctx_plain_name = _build_portfolio_grounding_context(
            user_comment="Ottima giornata su Cameco e Nvidia, ma $BTC scende.",
            post_context="Apertura Wall Street",
            relevant_tickers=["440", "400"],
        )
        self.assertIn("$CCJ", ctx_plain_name)
        self.assertIn("$NVDA", ctx_plain_name)
        self.assertIn("$BTC", ctx_plain_name)
        self.assertNotIn("$440", ctx_plain_name)
        self.assertNotIn("$400", ctx_plain_name)

        ctx_general = _build_portfolio_grounding_context(
            user_comment="Direi secondo mese difficile",
            post_context="Apertura Wall Street",
            relevant_tickers=[],
        )
        self.assertNotIn("Nessun asset specifico di portafoglio coinvolto", ctx_general)
        self.assertIn("citare titoli reali del portafoglio", ctx_general)

    def test_seeds_and_archive_filter_dca(self):
        """Seeds must contain zero DCA/PAC and Gist archive loader must filter legacy DCA entries."""
        for seed in DEFAULT_ANDREA_STYLE_SEEDS:
            ok_q, _ = ai_comment_responder._contains_forbidden_dca(seed["user_comment"])
            ok_a, _ = ai_comment_responder._contains_forbidden_dca(seed["andrea_reply"])
            self.assertFalse(ok_q, f"Seed {seed['id']} user_comment contains DCA/PAC")
            self.assertFalse(ok_a, f"Seed {seed['id']} andrea_reply contains DCA/PAC")

        fake_archive = [
            {
                "id": "legacy_dca",
                "user_comment": "Conviene fare un PAC?",
                "andrea_reply": "Ciao @utente! Suggerisco sempre un approccio tramite Dollar-Cost Averaging (DCA).",
                "language": "it",
            },
            {
                "id": "clean_nvda",
                "user_comment": "Cosa ne pensi di $NVDA?",
                "andrea_reply": "Ciao @utente! Deteniamo $NVDA per la leadership nell'architettura Blackwell e nei data center. Un saluto! 🚀",
                "language": "it",
            },
        ]
        with patch("ai_comment_responder.gist_storage.get_andrea_style_archive", return_value=fake_archive):
            filtered = load_andrea_style_archive()
            ids = [x["id"] for x in filtered]
            self.assertNotIn("legacy_dca", ids)
            self.assertIn("clean_nvda", ids)

    def test_skip_on_total_ai_failure_no_static_template(self):
        """When all AI providers fail, generate_ai_comment_reply returns None and process_community_replies skips without publishing."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False), \
             patch("ai_comment_responder._generate_reply_with_groq_or_mistral", return_value=(None, None)):
            reply = generate_ai_comment_reply(
                user_comment_text="Ho paura sia un ulteriore finale in rosso profondo...",
                user_author="AlvaroPatrassi",
                post_context="Apertura Wall Street con focus su $MSFT e $CCJ.",
                relevant_tickers=["MSFT", "CCJ"],
            )
            self.assertIsNone(reply)

        fake_unreplied = [{
            "post_id": "post-123",
            "comment_id": "comm-456",
            "author": "AlvaroPatrassi",
            "message": "Ho paura sia un ulteriore finale in rosso profondo...",
            "post_title": "Apertura Wall Street",
            "post_content": "Apertura Wall Street con focus su $MSFT e $CCJ.",
            "tickers": ["MSFT", "CCJ"],
            "created_at": "2026-11-20T15:00:00Z",
        }]
        with patch("ai_comment_responder.find_unreplied_comments", return_value=fake_unreplied), \
             patch("ai_comment_responder.generate_ai_comment_reply", return_value=None), \
             patch("ai_comment_responder.etoro_client.reply_to_comment") as mock_reply, \
             patch("ai_comment_responder.record_answered_comment") as mock_record:
            results = ai_comment_responder.process_community_replies(dry_run=False)
            mock_reply.assert_not_called()
            mock_record.assert_not_called()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["status"], "skipped_ai_unavailable")

    def test_fallback_helper_has_zero_dca_on_fear_comments(self):
        """Even if _build_contextual_fallback is invoked directly on a fear/drawdown comment, it must never mention DCA/PAC."""
        fb_it = _build_contextual_fallback("Ho paura di un ritracciamento forte", "TestUser", [], "it")
        fb_en = _build_contextual_fallback("I fear a market crash soon", "TestUser", [], "en")
        self.assertFalse(ai_comment_responder._contains_forbidden_dca(fb_it)[0], fb_it)
        self.assertFalse(ai_comment_responder._contains_forbidden_dca(fb_en)[0], fb_en)

    def test_language_detection(self):
        """Should detect Italian and English accurately."""
        self.assertEqual(_detect_language("What do you think about the pullback in tech?"), "en")
        self.assertEqual(_detect_language("Cosa ne pensi del ritracciamento del settore tech?"), "it")

    def test_third_party_mention_filter(self):
        """Comments addressed to other users must be recognized as third party."""
        self.assertTrue(is_third_party_mention("@xm49fvqjtm 🤔"))
        self.assertTrue(is_third_party_mention("@Marcofree79 ma volevi una risposta da me?"))
        self.assertFalse(is_third_party_mention("@AndreaRavalli cosa ne pensi di Nvidia?"))
        self.assertFalse(is_third_party_mention("@andrearavalli come vedi i mercati?"))
        self.assertFalse(is_third_party_mention("Cosa ne pensi di NVDA?"))

    def test_ignore_or_opt_out_filter(self):
        """Pure emojis or opt-out phrases must be ignored."""
        self.assertTrue(is_ignore_or_opt_out("🤔"))
        self.assertTrue(is_ignore_or_opt_out("👍"))
        self.assertTrue(is_ignore_or_opt_out("@xm49fvqjtm 🤔"))
        self.assertTrue(is_ignore_or_opt_out("@AndreaRavalli non era rivolto a te il mio emoji."))
        self.assertTrue(is_ignore_or_opt_out("non era per te"))
        self.assertTrue(is_ignore_or_opt_out("non parlavo con te"))
        self.assertFalse(is_ignore_or_opt_out("Come vedi il titolo Cameco nel lungo periodo?"))
        self.assertFalse(is_ignore_or_opt_out("@AndreaRavalli hai notizie su Palantir?"))


if __name__ == "__main__":
    unittest.main()
