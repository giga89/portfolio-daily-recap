#!/usr/bin/env python3
"""
Comprehensive Unit & Integration Tests for AI Comment Responder
and Andrea Style Archive.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ai_comment_responder
import gist_storage


class TestCommentResponder(unittest.TestCase):

    def test_simple_gratitude_detection(self):
        """Test that pure courtesies return True, while actual inquiries return False."""
        # Genuine pure courtesies
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Grazie!"))
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Grazie mille"))
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Grazie mille Andrea! 🙏"))
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Thanks! 👍"))
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Thank you Andrea"))
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Top! 🚀"))
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Ottimo, grazie"))
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Chiaro, grazie!"))
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Perfetto 👍"))
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Buona giornata e buon trading"))
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Thanks and good luck"))
        self.assertTrue(ai_comment_responder._is_simple_gratitude("Complimenti e a presto!"))

        # Real questions/comments that MUST NOT be classified as pure gratitude
        self.assertFalse(ai_comment_responder._is_simple_gratitude("Grazie, ma cosa fai su NVDA?"))
        self.assertFalse(ai_comment_responder._is_simple_gratitude("Ok, quanto capitale serve per iniziare?"))
        self.assertFalse(ai_comment_responder._is_simple_gratitude("Ottimo post, consiglieresti di entrare ora?"))
        self.assertFalse(ai_comment_responder._is_simple_gratitude("Chiaro, ma come vedi Palantir?"))
        self.assertFalse(ai_comment_responder._is_simple_gratitude("Top! Ma conviene fare un PAC?"))
        self.assertFalse(ai_comment_responder._is_simple_gratitude("Cosa ne pensi del calo di oggi?"))
        self.assertFalse(ai_comment_responder._is_simple_gratitude("$PLTR target price?"))
        self.assertFalse(ai_comment_responder._is_simple_gratitude("Thanks, what is your view on LLY?"))
        self.assertFalse(ai_comment_responder._is_simple_gratitude("Grazie Andrea, hai chiuso la posizione su Cameco?"))

    def test_style_archive_loading_and_formatting(self):
        """Test loading style archive and formatting few-shot prompt blocks."""
        archive = ai_comment_responder.load_andrea_style_archive()
        self.assertGreaterEqual(len(archive), 5)
        print(f"✓ Total style exemplars loaded: {len(archive)}")

        # Test Italian few-shot retrieval for a copy trading question
        formatted_it = ai_comment_responder.format_style_examples_for_prompt(
            user_comment="Quanto capitale serve per iniziare a copiare il portafoglio?",
            lang="it",
            relevant_tickers=[],
            max_examples=3
        )
        self.assertIn("Style Example", formatted_it)
        self.assertIn("Andrea's Authentic Reply", formatted_it)
        self.assertIn("copi", formatted_it.lower())
        print("✓ Italian few-shot examples formatted successfully")

        # Test English few-shot retrieval for an asset thesis question
        formatted_en = ai_comment_responder.format_style_examples_for_prompt(
            user_comment="Why are you holding Cameco and Prysmian in the portfolio?",
            lang="en",
            relevant_tickers=["CCJ", "PRY.MI"],
            max_examples=2
        )
        self.assertIn("Style Example", formatted_en)
        self.assertIn("Cameco", formatted_en)
        print("✓ English few-shot examples formatted successfully")

    def test_upsert_style_replies(self):
        """Test upserting new harvested replies to style archive."""
        new_replies = [
            {
                "id": "test_reply_123",
                "post_id": "post_abc",
                "user_comment": "Cosa ne pensi di ASML?",
                "andrea_reply": "Ciao @utente! ASML detiene un monopolio assoluto nei sistemi litografici EUV, fondamentali per produrre i nodi avanzati. Un caro saluto e buon trading! 📈🤝",
                "language": "it",
                "source": "test"
            }
        ]
        added = gist_storage.upsert_andrea_style_replies(new_replies)
        print(f"✓ Upsert test returned: {added} new item(s)")

    def test_contextual_fallback_richness_and_follow_ups(self):
        """Verify that fallback responses are articulate, complete, and not ultra-short even on follow-ups."""
        test_cases = [
            ("Come vedi NVDA dopo l'ultimo ritracciamento?", "Marco", ["NVDA"], "it", False),
            ("Palantir è troppo cara a questi multipli?", "Luca", ["PLTR"], "it", False),
            ("Come funziona il copy trading e quanto serve?", "Giovanni", [], "it", False),
            ("Ho paura del crollo dei mercati, conviene uscire?", "Matteo", [], "it", False),
            ("What is your view on tech pullback?", "John", ["NVDA"], "en", False),
            ("How to start copy trading your strategy?", "Sarah", [], "en", False),
            # Follow up turn with an actual question
            ("Grazie per la spiegazione, ma per NVDA conviene incrementare adesso?", "Paolo", ["NVDA"], "it", True),
        ]

        for comment, author, tickers, lang, is_follow_up in test_cases:
            reply = ai_comment_responder.generate_ai_comment_reply(
                user_comment_text=comment,
                user_author=author,
                post_context="Test Post Title",
                relevant_tickers=tickers,
                is_follow_up=is_follow_up
            )
            self.assertGreater(len(reply), 100, f"Reply too short for comment: {comment}")
            self.assertIn(f"@{author}", reply)
            print(f"✓ Verified rich response for @{author} [follow_up={is_follow_up}] ({len(reply)} chars)")


if __name__ == "__main__":
    unittest.main()
