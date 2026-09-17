#!/usr/bin/env python3
"""
Unit tests for 5 Thematic Emoji Micro-Topics & Dynamic Ticker Selection
"""

import unittest
from unittest.mock import patch
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

import ai_news_generator
from independent_fact_checker import split_into_micro_topics


class TestThematicMicroTopics(unittest.TestCase):
    def test_select_rotation_favorites_and_niche_eu_asia(self):
        tickers = ['AZN.L', 'NOVO-B.CO', 'ENEL.MI', 'ENI.MI', 'PRY.MI', '1919.HK', '1211.HK', 'TRIG.L']
        favs, niche = ai_news_generator._select_rotation_favorites_and_niche(tickers, count_favorites=2, count_niche=1)
        self.assertEqual(len(favs), 2)
        self.assertEqual(len(niche), 1)
        # Ensure no overlap
        self.assertEqual(len(set(favs + niche)), 3)

    def test_select_rotation_favorites_and_niche_us(self):
        tickers = ['NVDA', 'MSFT', 'AMZN', 'GOOG', 'PLTR', 'MRVL', 'CCJ', 'HUM']
        favs, niche = ai_news_generator._select_rotation_favorites_and_niche(tickers, count_favorites=2, count_niche=1)
        self.assertEqual(len(favs), 2)
        self.assertEqual(len(niche), 1)
        self.assertEqual(len(set(favs + niche)), 3)

    def test_get_top_gainers_with_news_sorting_and_fallback(self):
        mock_stock_data = {
            'MRVL': {'daily_change': 4.5, 'company_name': 'Marvell Technology'},
            'PRY.MI': {'daily_change': 3.2, 'company_name': 'Prysmian'},
            'WDEF.L': {'daily_change': 2.8, 'company_name': 'WisdomTree Europe Defence'},
            'ENEL.MI': {'daily_change': 1.9, 'company_name': 'Enel'},
            'NVDA': {'daily_change': 0.5, 'company_name': 'NVIDIA'},
        }
        gainers = ai_news_generator._get_top_gainers_with_news(mock_stock_data, count=4)
        self.assertEqual(len(gainers), 4)
        # Verify sorted descending
        self.assertTrue(gainers[0]['daily_change'] >= gainers[1]['daily_change'])
        self.assertTrue(gainers[1]['daily_change'] >= gainers[2]['daily_change'])
        self.assertTrue(gainers[2]['daily_change'] >= gainers[3]['daily_change'])
        # Verify news snippets exist
        for g in gainers:
            self.assertTrue(len(g.get('news_snippet', '')) > 0)

    def test_split_thematic_emoji_micro_topics(self):
        sample_post = (
            "Buongiorno! I mercati europei stanno per aprire, ecco i punti chiave di oggi: ☕\n\n"
            "🌍 Apertura cauta per i listini del Vecchio Continente, con l'indice $SX7PEX.DE in lieve rialzo dell'1.1%.\n\n"
            "📅 Sul fronte macro, gli investitori attendono i dati PMI manifatturieri e i commenti della BCE.\n\n"
            "🧬 $AZN.L continua a rafforzare la pipeline oncologica con oltre 1.5 miliardi di investimenti in R&D.\n\n"
            "🔋 $ENEL.MI accelera sugli investimenti di rete confermando cedole in crescita e debito sotto controllo.\n\n"
            "🚢 $1919.HK beneficia della tenuta delle tariffe container e di un bilancio ricco di liquidità operativa.\n\n"
            "Quale titolo seguirete oggi? Scrivetelo nei commenti! 👇\n\n"
            "📌 $AZN.L $ENEL.MI $1919.HK $SX7PEX.DE\n\n"
            "👤 Segui e copia il portafoglio: https://www.etoro.com/people/andrearavalli"
        )
        topics = split_into_micro_topics(sample_post)
        self.assertGreaterEqual(len(topics), 7)
        audited_topics = [t for t in topics if t["needs_audit"]]
        self.assertEqual(len(audited_topics), 5)  # The 5 micro-topics to audit

    def test_split_micro_topics_recognizes_giornata_conclusa_greeting(self):
        post = (
            "Giornata conclusa! Analizziamo insieme i movimenti di oggi su Wall Street...\n\n"
            "🌆 Wall Street ha chiuso in lieve rialzo dopo una seduta volatile.\n\n"
            "📊 Ottima performance per $MRVL (+3.61%).\n\n"
            "🔌 In forte rialzo anche $PRY.MI (+3.38%).\n\n"
            "🛡️ È salito anche $WDEF.L (+2.47%).\n\n"
            "🚢 Ha chiuso in positivo $1919.HK (+2.27%).\n\n"
            "Come avete vissuto questa seduta? Dite la vostra nei commenti!"
        )
        topics = split_into_micro_topics(post)
        self.assertEqual(topics[0]["type"], "greeting")
        self.assertFalse(topics[0]["needs_audit"])
        audited = [t for t in topics if t["needs_audit"]]
        self.assertEqual(len(audited), 5)

    def test_sanitize_verified_text_filters_hallucinated_phrase_and_duplicates(self):
        from independent_fact_checker import sanitize_verified_text
        orig = "Giornata conclusa! Analizziamo insieme i movimenti di oggi su Wall Street..."
        hallucinated = (
            "Giornata conclusa! Analizziamo insieme i movimenti di oggi su Wall Street. "
            "La Fed ha annunciato una nuova tassa sui tassi di interesse. "
            "Il mercato è in attesa delle decisioni della Fed sugli interessi. "
            "La Fed ha annunciato una nuova tassa sui tassi di interesse. "
            "Il mercato è in attesa delle decisioni della Fed sugli interessi."
        )
        sanitized = sanitize_verified_text(orig, hallucinated)
        self.assertNotIn("tassa sui tassi", sanitized)
        self.assertNotIn("tassa sugli interessi", sanitized)
        # Verify it safely reverted or eliminated duplicates and kept clean text
        self.assertTrue(len(sanitized) <= len(orig) + 10)

    def test_ensure_thematic_emojis(self):
        from ai_news_generator import ensure_thematic_emojis
        raw_post = (
            "Ci siamo preparati per l'apertura americana. Ecco le notizie chiave:\n\n"
            "I futures di Wall Street mostrano un rimbalzo con l'indice $NSDQ100 in recupero.\n\n"
            "Nell'agenda macroeconomica di oggi analizziamo i dati sui sussidi di disoccupazione.\n\n"
            "🤖 Per $NVDA i fari sono puntati sui nuovi chip Blackwell.\n\n"
            "Su $PLTR l'attenzione è rivolta alla crescita dei bootcamp AIP.\n\n"
            "È salito anche $WDEF.L (+2.47%), trainato dai budget per la difesa.\n\n"
            "Voi come vi state posizionando? Scrivetelo nei commenti!"
        )
        formatted = ensure_thematic_emojis(raw_post, session_name="US_OPEN")
        lines = [p.strip() for p in formatted.split("\n\n") if p.strip()]
        # Greeting kept
        self.assertTrue(lines[0].startswith("Ci siamo"))
        # Macro got 🇺🇸
        self.assertTrue(lines[1].startswith("🇺🇸"))
        # Agenda got 📅
        self.assertTrue(lines[2].startswith("📅"))
        # NVDA kept 🤖
        self.assertTrue(lines[3].startswith("🤖"))
        # PLTR got 🛡️ from EMOJI_MAP
        self.assertTrue(lines[4].startswith("🛡️"))
        # WDEF.L got 🛡️ from EMOJI_MAP
        self.assertTrue(lines[5].startswith("🛡️"))
        # Question kept
        self.assertTrue("?" in lines[6])


if __name__ == "__main__":
    unittest.main()

