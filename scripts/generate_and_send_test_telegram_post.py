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

    # Realistic post candidate for session
    candidate_post = (
        f"Chiusura mercati USA archiviata ({temporal_ctx.get('formatted_date')}):\n\n"
        f"La seduta a Wall Street si è conclusa con una buona tenuta dei tecnologici. "
        f"Nel nostro portafoglio di lungo termine su eToro, $NVDA e $MSFT hanno registrato scambi regolari, "
        f"mentre $PLTR consolida la forza dell'ecosistema software aziendale.\n\n"
        f"Tutti i dati e catalizzatori macroeconomici della giornata odierna sono stati già pienamente assorbiti "
        f"dagli indici ($SPX500, $NSDQ100). Il portafoglio mantiene una disciplina rigorosa su diversificazione "
        f"e qualità degli utili.\n\n"
        f"📌 $NVDA $MSFT $PLTR $SPX500 $NSDQ100\n\n"
        f"👤 Segui e copia la strategia: https://www.etoro.com/people/andrearavalli"
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
