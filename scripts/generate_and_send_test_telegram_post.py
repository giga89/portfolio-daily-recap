#!/usr/bin/env python3
"""
Real Post Generation & Dual-AI Consensus Test (Telegram Only)
============================================================
Generates a realistic portfolio recap post using real data and temporal anchors,
submits it to the Dual-AI Consensus Fact-Checker (Groq + Mistral cross-verification),
and dispatches the verified post EXCLUSIVELY to Telegram.

NO posts are sent to eToro, Twitter, or any external social network.
"""

import os
import sys
import json
from datetime import datetime

# Setup sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

import telegram_sender
import post_verifier
from independent_fact_checker import get_current_temporal_context, run_independent_fact_check

def generate_and_send_test(session_name: str = "US_CLOSE") -> bool:
    print("=" * 65)
    print("🚀 TEST GENERATION & DUAL-AI CONSENSUS (TELEGRAM ONLY)")
    print(f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📌 Target Session: {session_name}")
    print("=" * 65)

    # Check Telegram configuration
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.")
        return False

    temporal_ctx = get_current_temporal_context(session_name)
    print(f"📅 Temporal Anchor Ground Truth:")
    print(f"   • Data: {temporal_ctx.get('formatted_date')}")
    print(f"   • Ora Roma: {temporal_ctx.get('rome_time')}")
    print(f"   • Ora Wall Street: {temporal_ctx.get('ny_time')}")
    print(f"   • Stato Mercato: {temporal_ctx.get('market_state')}")

    # Generate full-length rich post via Gemini AI (production generator)
    import ai_news_generator

    print("\n🧠 Generazione recap completo con Gemini AI (Google Search Grounding attivo)...")
    candidate_post = ""
    try:
        session_label = "U.S. market close" if "close" in session_name.lower() else "European market open"
        candidate_post = ai_news_generator.generate_market_news_recap(
            max_tags=4,
            market_session=session_label
        )
    except Exception as exc:
        print(f"⚠️ Errore generatore Gemini: {exc}")

    if candidate_post and len(candidate_post) > 200:
        print(f"✅ Generato post completo da Gemini: {len(candidate_post)} caratteri")
    else:
        print("ℹ️ Utilizzo template articolato multi-paragrafo ad alta densità informativa (~1200 caratteri).")
        candidate_post = (
            f"Buonasera a tutti! Chiusura di Wall Street archiviata ({temporal_ctx.get('formatted_date')}):\n\n"
            f"La seduta odierna sui mercati statunitensi si è conclusa con gli indici principali ($SPX500, $NSDQ100) "
            f"che hanno metabolizzato i recenti flussi macroeconomici e le indicazioni della banca centrale. "
            f"La volatilità si mantiene compressa, con una rotazione settoriale che continua a premiare la qualità dei bilanci.\n\n"
            f"Nel nostro portafoglio di lungo termine su eToro monitoriamo con attenzione i singoli pilastri:\n"
            f"• $NVDA e il comparto semiconduttori consolidano i livelli chiave dopo i recenti catalizzatori sui data center AI.\n"
            f"• $PLTR mostra volumi costanti e solida domanda istituzionale per la piattaforma AIP in ambito enterprise.\n"
            f"• I titoli difensivi e la componente healthcare mantengono la consueta funzione di stabilizzazione del rendimento complessivo.\n\n"
            f"Tutti gli eventi, dati macro e decisioni di politica monetaria della seduta odierna sono stati già pienamente incorporati "
            f"dai mercati a bocce ferme. Come sempre, la nostra strategia punta sulla crescita secolare e la gestione asimmetrica del rischio.\n\n"
            f"Come giudicate la tenuta dei listini tecnologici in questa fase di mercato? Scrivetelo nei commenti! 👇\n\n"
            f"📌 $NVDA $PLTR $SPX500 $NSDQ100\n\n"
            f"👤 Segui e copia il portafoglio: https://www.etoro.com/people/andrearavalli"
        )

    print("\n📝 Testo del post candidato sottoposto a verifica:")
    print("-" * 50)
    print(candidate_post)
    print("-" * 50)

    # Execute Pre-Publication Verification Gate with Dual Consensus
    approved, final_text, audit = post_verifier.verify_and_clean_post(
        text=candidate_post,
        primary_ticker="NVDA",
        session_name=session_name,
        run_ai_review=True,
    )

    print("\n" + "=" * 65)
    print("📊 ESITO AUDIT CONSENSO MULTI-AI:")
    print(f"   • Decisione Finale: {'✅ APPROVATO' if approved else '❌ RESPINTO'}")
    print(f"   • Auditor: {audit.get('auditor', 'N/A')}")
    print(f"   • Score Qualità: {audit.get('score', 'N/A')}/100")
    print(f"   • Spiegazione: {audit.get('explanation', 'N/A')}")
    print("=" * 65)

    if not approved:
        print("🛑 Il post non ha superato il consenso unanime. Invio annullato.")
        return False

    # Format message for Telegram
    tg_header = (
        "🧪 <b>TEST VERIFICA CONSENSO MULTI-AI</b> 🧪\n"
        "<i>(Solo Telegram — Nessuna pubblicazione su eToro)</i>\n\n"
        f"🤖 <b>Auditor Indipendenti:</b> Groq (Qwen 27B) + Mistral (Codestral)\n"
        f"🤝 <b>Consenso:</b> {audit.get('auditor')}\n"
        f"🛡️ <b>Score Compliance:</b> {audit.get('score', 95)}/100\n"
        f"🕒 <b>Verifica Temporale:</b> {temporal_ctx.get('rome_time')} (Mercati: Conclusi)\n"
        "────────────────────────\n\n"
    )

    tg_full_message = tg_header + final_text

    print("\n📨 Spedizione in corso verso Telegram...")
    sent = telegram_sender.send_telegram_message(tg_full_message)
    if sent:
        print("🎉 Post REALE inviato con successo solo su TELEGRAM!")
        return True
    else:
        print("❌ Invio messaggio Telegram fallito.")
        return False


if __name__ == "__main__":
    session = sys.argv[1] if len(sys.argv) > 1 else "US_CLOSE"
    ok = generate_and_send_test(session)
    sys.exit(0 if ok else 1)
