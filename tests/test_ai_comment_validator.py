#!/usr/bin/env python3
"""
Unit tests for AI Community Comment Responder validation guardrails,
syntax checks, fallback engine, and anti-duplication logic.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from ai_comment_responder import (
    validate_response_syntax,
    _build_contextual_fallback,
    _detect_language,
    _is_simple_gratitude,
    generate_ai_comment_reply
)


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
        """Short thanks should get warm short closing."""
        self.assertTrue(_is_simple_gratitude("Grazie mille!"))
        self.assertTrue(_is_simple_gratitude("Thanks a lot! 👍"))
        self.assertFalse(_is_simple_gratitude("Ho una domanda sui dividendi di PLTR e sulla crescita futura delle tech?"))

    def test_language_detection(self):
        """Should detect Italian and English accurately."""
        self.assertEqual(_detect_language("What do you think about the pullback in tech?"), "en")
        self.assertEqual(_detect_language("Cosa ne pensi del ritracciamento del settore tech?"), "it")


if __name__ == "__main__":
    unittest.main()
