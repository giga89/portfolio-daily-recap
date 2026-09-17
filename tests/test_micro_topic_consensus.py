#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from independent_fact_checker import (
    split_into_micro_topics,
    reassemble_micro_topics,
    run_micro_topic_consensus_fact_check,
)


class TestMicroTopicConsensus(unittest.TestCase):
    def setUp(self):
        self.sample_recap = (
            "Buonasera a tutti! Chiusura di Wall Street archiviata:\n\n"
            "La seduta odierna sui mercati statunitensi si è conclusa con gli indici principali "
            "($SPX500, $NSDQ100) che hanno metabolizzato i recenti flussi macroeconomici e le indicazioni della banca centrale.\n\n"
            "Nel nostro portafoglio di lungo termine su eToro monitoriamo con attenzione i singoli pilastri:\n"
            "• $NVDA consolida i livelli chiave dopo i recenti catalizzatori sui data center AI.\n"
            "• $PLTR mostra volumi costanti e solida domanda enterprise per la piattaforma AIP.\n"
            "• $LLY e il comparto healthcare mantengono la funzione di stabilizzazione del portafoglio.\n\n"
            "Manteniamo la consueta disciplina di asset allocation senza rincorrere i movimenti di breve termine.\n\n"
            "Come giudicate la tenuta dei tecnologici in questa fase? Dite la vostra nei commenti! 👇\n\n"
            "📌 $NVDA $PLTR $LLY $SPX500\n\n"
            "👤 Segui e copia la strategia: https://www.etoro.com/people/andrearavalli"
        )

    def test_split_into_micro_topics(self):
        topics = split_into_micro_topics(self.sample_recap)
        self.assertGreaterEqual(len(topics), 7)
        
        types = [t["type"] for t in topics]
        self.assertIn("greeting", types)
        self.assertIn("macro", types)
        self.assertIn("bullet_header", types)
        self.assertIn("stock_bullet", types)
        self.assertIn("engagement_question", types)
        self.assertIn("footer", types)

        bullets = [t for t in topics if t["type"] == "stock_bullet"]
        self.assertEqual(len(bullets), 3)
        self.assertTrue(all(b["needs_audit"] for b in bullets))

    def test_reassemble_micro_topics_exact(self):
        topics = split_into_micro_topics(self.sample_recap)
        reassembled = reassemble_micro_topics(topics)
        self.assertEqual(reassembled.strip(), self.sample_recap.strip())

    def test_reassemble_with_excluded_bullet(self):
        topics = split_into_micro_topics(self.sample_recap)
        # Exclude the PLTR bullet
        for t in topics:
            if t["type"] == "stock_bullet" and "$PLTR" in t["text"]:
                t["excluded"] = True

        reassembled = reassemble_micro_topics(topics)
        self.assertNotIn("$PLTR mostra volumi", reassembled)
        self.assertIn("$NVDA consolida", reassembled)
        self.assertIn("$LLY e il comparto healthcare", reassembled)
        self.assertIn("Buonasera a tutti!", reassembled)

    @patch("independent_fact_checker.run_independent_fact_check")
    def test_run_micro_topic_consensus_approved(self, mock_audit):
        mock_audit.return_value = {
            "decision": "APPROVE",
            "score": 95,
            "verified_text": "mocked text",
            "temporal_issues": [],
            "hallucinations_detected": [],
            "auditor": "consensus:dual (groq + mistral)",
            "explanation": "Tutto verificato e pulito.",
        }

        res = run_micro_topic_consensus_fact_check(self.sample_recap, session_name="US_CLOSE")
        self.assertIsNotNone(res)
        self.assertEqual(res["decision"], "APPROVE")
        self.assertIn("verified_text", res)
        self.assertTrue(len(res["verified_text"]) > 300)

    @patch("independent_fact_checker.run_independent_fact_check")
    def test_run_micro_topic_consensus_surgical_correction(self, mock_audit):
        def side_effect(text, *args, **kwargs):
            if "metabolizzato" in text:
                return {
                    "decision": "AUTO_CORRECT",
                    "score": 85,
                    "verified_text": text.replace("metabolizzato", "incorporato con successo"),
                    "temporal_issues": [],
                    "hallucinations_detected": [],
                    "auditor": "consensus:cross_verified",
                    "explanation": "Sostituito termine.",
                }
            return {
                "decision": "APPROVE",
                "score": 95,
                "verified_text": text,
                "temporal_issues": [],
                "hallucinations_detected": [],
                "auditor": "consensus:dual",
                "explanation": "OK",
            }

        mock_audit.side_effect = side_effect
        res = run_micro_topic_consensus_fact_check(self.sample_recap, session_name="US_CLOSE")
        self.assertIsNotNone(res)
        self.assertEqual(res["decision"], "AUTO_CORRECT")
        self.assertIn("incorporato con successo", res["verified_text"])
        self.assertIn("$NVDA", res["verified_text"])
        self.assertIn("$PLTR", res["verified_text"])
        self.assertIn("$LLY", res["verified_text"])


if __name__ == "__main__":
    unittest.main()
