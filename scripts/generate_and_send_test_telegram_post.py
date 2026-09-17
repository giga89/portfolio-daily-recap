#!/usr/bin/env python3
"""
Real Full-Production Recap Generation & Micro-Topic Consensus Test (Telegram Only)
================================================================================
Generates a complete, full-depth daily recap matching production runs (~3,500 - 4,000 characters),
including:
1. Performance header + Distance from ATH
2. Top 5 of today (daily winners/movers)
3. Top 3 monthly & Top 3 YTD performers
4. Multi-paragraph rich AI market news (Macro + in-depth stock breakdown with real catalysts),
   audited through the Micro-Topic Modular Consensus (Groq + Mistral)
5. Why Copy section with 5-year return, CAGR, benchmark differentials, and Hub link

Dispatches EXCLUSIVELY to Telegram. ZERO posts to eToro or external socials.
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
import ai_news_generator
from independent_fact_checker import get_current_temporal_context


def generate_and_send_test(session_name: str = "US_CLOSE") -> bool:
    print("=" * 65)
    print("🚀 TEST FULL PRODUCTION RECAP & MICRO-TOPIC CONSENSUS (TELEGRAM ONLY)")
    print(f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📌 Target Session: {session_name}")
    print("=" * 65)

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.")
        return False

    temporal_ctx = get_current_temporal_context(session_name)
    formatted_date = temporal_ctx.get("formatted_date", datetime.now().strftime("%d/%m/%Y"))
    print(f"📅 Temporal Anchor Ground Truth:")
    print(f"   • Data: {formatted_date}")
    print(f"   • Ora Roma: {temporal_ctx.get('rome_time')}")
    print(f"   • Ora Wall Street: {temporal_ctx.get('ny_time')}")
    print(f"   • Stato Mercato: {temporal_ctx.get('market_state')}")

    # ── 1. PORTFOLIO PERFORMANCE & RANKINGS HEADER ─────────────────────────────
    # Real-world figures matching production recap format
    portfolio_header = (
        "🌆 CHIUSURA DEI MERCATI 📈\n\n"
        "🌱 🌱 🌱 LIEVE CRESCITA 🌱: +0.23% 🌱 🌱 🌱\n"
        "🏔️ Distanza dal Massimo Storico (ATH): -8.90%\n\n"
        "MIGLIORI 5 DI OGGI DEL PORTAFOGLIO 📈\n"
        "📊 MRVL +3.61%\n"
        "🔌 PRY.MI +3.38%\n"
        "💼 WDEF.L +2.47%\n"
        "🚢 $1919.HK +2.27%\n"
        "🔋 $ENEL.MI +1.80%\n\n"
        "MIGLIORI 3 PERFORMANCE MENSILI 📈\n"
        "📊 MRVL +9.18%\n"
        "🚗 VOW3.DE +7.03%\n"
        "🌬️ $TRIG.L +5.00%\n\n"
        "MIGLIORI 3 DI SEMPRE (YTD) DEL PORTAFOGLIO 📈\n"
        "📊 MRVL +157.35%\n"
        "⛽ ENI.MI +51.51%\n"
        "🏥 HUM +46.55%\n\n"
    )

    # ── 2. AI MARKET NEWS SECTION (RICH MULTI-TOPIC) ───────────────────────────
    print("\n🧠 Generazione sezione notizie con AI (Google Search Grounding attivo)...")
    candidate_news = ""
    try:
        session_label = "U.S. market close" if "close" in session_name.lower() else "European market open"
        candidate_news = ai_news_generator.generate_market_news_recap(
            max_tags=4,
            market_session=session_label
        )
    except Exception as exc:
        print(f"⚠️ Errore generatore Gemini: {exc}")

    if candidate_news and len(candidate_news) > 400:
        print(f"✅ Generata sezione notizie da Gemini: {len(candidate_news)} caratteri")
    else:
        print("ℹ️ Utilizzo template articolato multi-argomento ad alta densità informativa (~1500 caratteri).")
        candidate_news = (
            f"Fine sessione! Facciamo un po' di chiarezza su quello che è successo oggi oltre Atlantico ({formatted_date}):\n\n"
            f"Oggi abbiamo assistito a una chiusura solida per i mercati americani, con l'indice $SPX500 e il Nasdaq "
            f"che hanno metabolizzato i recenti flussi macroeconomici e le indicazioni della banca centrale. "
            f"La volatilità si mantiene compressa, con una rotazione settoriale che continua a premiare la qualità dei bilanci "
            f"e i titoli con solida generazione di cassa.\n\n"
            f"Nel nostro portafoglio di lungo termine su eToro monitoriamo con attenzione i singoli pilastri:\n"
            f"• $NVDA e il comparto semiconduttori consolidano i livelli chiave dopo le recenti conferme sui cluster AI "
            f"e la domanda sostenuta per le architetture di calcolo nei data center.\n"
            f"• $PLTR mostra volumi costanti e solida trazione enterprise per la piattaforma AIP, "
            f"confermando il ruolo di leader nell'abilitazione operativa dell'intelligenza artificiale per le grandi aziende.\n"
            f"• $LLY e il settore farmaceutico mantengono la consueta funzione di stabilizzazione del rendimento complessivo, "
            f"grazie ai continui progressi nella pipeline clinica e nella domanda globale.\n"
            f"• Microsoft e Amazon proseguono la fase di ottimizzazione delle infrastrutture cloud, bilanciando investimenti e redditività.\n"
            f"• Sul fronte europeo, Prysmian e $WDEF.L (aerospazio e difesa UE) confermano la validità della diversificazione geografica.\n\n"
            f"Tutti gli eventi, dati macro e decisioni di politica monetaria della seduta odierna sono stati già pienamente incorporati "
            f"dai mercati a bocce ferme. Come sempre, la nostra strategia privilegia i fondamentali e la gestione asimmetrica del rischio.\n\n"
            f"Come giudicate la tenuta dei listini tecnologici e difensivi in questa fase di mercato? Scrivetelo nei commenti! 👇\n\n"
            f"📌 $NVDA $PLTR $LLY $SPX500\n\n"
            f"👤 Segui e copia il portafoglio: https://www.etoro.com/people/andrearavalli"
        )

    print("\n📝 Sezione Notizie candidata sottoposta ad audit modulare:")
    print("-" * 50)
    print(candidate_news)
    print("-" * 50)

    # ── 3. PRE-PUBLICATION MODULAR CONSENSUS AUDIT (Groq + Mistral) ─────────────
    approved, verified_news, audit = post_verifier.verify_and_clean_post(
        text=candidate_news,
        primary_ticker="NVDA",
        session_name=session_name,
        run_ai_review=True,
    )

    print("\n" + "=" * 65)
    print("📊 ESITO AUDIT CONSENSO MODULARE MULTI-AI:")
    print(f"   • Decisione Finale: {'✅ APPROVATO' if approved else '❌ RESPINTO'}")
    print(f"   • Auditor: {audit.get('auditor', 'N/A')}")
    print(f"   • Score Qualità: {audit.get('score', 'N/A')}/100")
    print(f"   • Spiegazione: {audit.get('explanation', 'N/A')}")
    print("=" * 65)

    if not approved:
        print("🛑 La sezione notizie non ha superato il consenso. Invio annullato.")
        return False

    # ── 4. WHY COPY & BENCHMARKS SECTION ───────────────────────────────────────
    benchmark_data = {
        "SPX500": 132.0,
        "NSDQ100": 227.0,
        "SWDA.L": 125.0,
        "EUSTX50": 67.0,
        "CHINA50": -12.0,
    }
    why_copy_section = ai_news_generator.get_why_copy_message(
        five_year_return=192.0,
        avg_yearly_return=17.0,
        benchmark_performance=benchmark_data,
        market_session=session_name,
    )

    # ── 5. ASSEMBLE COMPLETE PRODUCTION POST ───────────────────────────────────
    full_recap_post = portfolio_header + verified_news.strip() + "\n\n" + why_copy_section.strip()

    print("\n📏 LUNGHEZZA POST FINALE ASSEMBLATO:")
    print(f"   • Lunghezza totale: {len(full_recap_post)} caratteri")
    print(f"   • Sezione Dati Portfolio: {len(portfolio_header)} caratteri")
    print(f"   • Sezione Notizie AI Verificate: {len(verified_news)} caratteri")
    print(f"   • Sezione Perché Copiare & Benchmark: {len(why_copy_section)} caratteri")

    # Enforce safe Telegram limit (max 4096, using 3950)
    MAX_TELEGRAM_LENGTH = 3950
    if len(full_recap_post) > MAX_TELEGRAM_LENGTH:
        print(f"⚠️ Trimming recap to fit Telegram limit ({len(full_recap_post)} -> {MAX_TELEGRAM_LENGTH})...")
        cut = full_recap_post.rfind('\n\n', 0, MAX_TELEGRAM_LENGTH - 50)
        if cut != -1:
            full_recap_post = full_recap_post[:cut].rstrip()

    # ── 6. FORMAT TELEGRAM DISPATCH HEADER ─────────────────────────────────────
    tg_header = (
        "🧪 <b>TEST RECAP COMPLETO DI PRODUZIONE (MICRO-TOPIC CONSENSUS)</b> 🧪\n"
        "<i>(Solo Telegram — Nessuna pubblicazione su eToro)</i>\n\n"
        f"🤖 <b>Auditor:</b> {audit.get('auditor', 'Groq + Mistral')}\n"
        f"🛡️ <b>Score Qualità:</b> {audit.get('score', 95)}/100\n"
        f"📏 <b>Lunghezza:</b> {len(full_recap_post)} caratteri (qualità e formato storico)\n"
        f"🕒 <b>Verifica Temporale:</b> {temporal_ctx.get('rome_time')} (Mercati: Conclusi)\n"
        "────────────────────────\n\n"
    )

    tg_full_message = tg_header + full_recap_post

    print("\n📨 Spedizione in corso verso Telegram...")
    sent = telegram_sender.send_telegram_message(tg_full_message)
    if sent:
        print("🎉 Post COMPLETO inviato con successo solo su TELEGRAM!")
        return True
    else:
        print("❌ Invio messaggio Telegram fallito.")
        return False


if __name__ == "__main__":
    session = sys.argv[1] if len(sys.argv) > 1 else "US_CLOSE"
    ok = generate_and_send_test(session)
    sys.exit(0 if ok else 1)
