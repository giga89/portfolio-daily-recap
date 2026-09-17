#!/usr/bin/env python3
"""
Real Full-Production Recap Generation & Micro-Topic Consensus Test (Telegram Only)
================================================================================
Generates complete, full-depth daily recaps according to the new 5 Thematic Emoji Micro-Topics structure:
- EU_OPEN: Macro sentiment, Day's agenda, 2 Follower favorites (rotation), 1 Niche holding.
- US_OPEN: US sentiment, Day's agenda, 2 Follower favorites (rotation), 1 Niche holding.
- US_CLOSE: Index wrap-up, 4 Top daily positive movers with verified catalysts/news.

Audited through the Multi-AI Consensus engine (Gemini + Tavily + Groq + Mistral).
Dispatches EXCLUSIVELY to Telegram. ZERO posts to eToro or external socials.
"""

import os
import sys
import time
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

import telegram_sender
import post_verifier
import ai_news_generator
from independent_fact_checker import get_current_temporal_context


def generate_and_send_test(session_name: str = "US_CLOSE") -> bool:
    session_upper = session_name.upper()
    print("=" * 65)
    print("🚀 TEST PRODUZIONE: 5 MICROTEMI TEMATICI (TELEGRAM ONLY)")
    print(f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📌 Sessione Target: {session_upper}")
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
    if "EU" in session_upper:
        session_label = "European market open"
        session_num = "1/3"
        session_display_name = "APERTURA MERCATI EUROPEI (EU OPEN)"
        session_badge_emoji = "🌅"
        session_flag_emoji = "🇪🇺"
        portfolio_header = (
            "🌅 APERTURA MERCATI EUROPEI 🇪🇺\n\n"
            "🌱 🌱 🌱 LIEVE CRESCITA 🌱: +0.42% 🌱 🌱 🌱\n"
            "🏔️ Distanza dal Massimo Storico (ATH): -8.70%\n\n"
        )
        simulated_stock_data = None
    elif "OPEN" in session_upper:
        session_label = "U.S. market open"
        session_num = "2/3"
        session_display_name = "APERTURA WALL STREET (US OPEN)"
        session_badge_emoji = "🌅"
        session_flag_emoji = "🇺🇸"
        portfolio_header = (
            "🌅 APERTURA WALL STREET 🇺🇸\n\n"
            "✅ ✅ ✅ OTTIMA GIORNATA! 🟢: +0.86% ✅ ✅ ✅\n"
            "🏔️ Distanza dal Massimo Storico (ATH): -8.20%\n\n"
        )
        simulated_stock_data = None
    else:
        session_label = "U.S. market close"
        session_num = "3/3"
        session_display_name = "CHIUSURA MERCATI USA (US CLOSE)"
        session_badge_emoji = "🌆"
        session_flag_emoji = "📈"
        portfolio_header = (
            "🌆 CHIUSURA DEI MERCATI 📈\n\n"
            "🌱 🌱 🌱 LIEVE CRESCITA 🌱: +0.23% 🌱 🌱 🌱\n"
            "🏔️ Distanza dal Massimo Storico (ATH): -8.90%\n\n"
            "MIGLIORI 5 DI OGGI DEL PORTAFOGLIO 📈\n"
            "📊 MRVL +3.61%\n"
            "🔌 PRY.MI +3.38%\n"
            "💼 WDEF.L +2.47%\n"
            "🚢 1919.HK +2.27%\n"
            "🔋 ENEL.MI +1.80%\n\n"
            "MIGLIORI 3 PERFORMANCE MENSILI 📈\n"
            "📊 MRVL +9.18%\n"
            "🚗 VOW3.DE +7.03%\n"
            "🌬️ TRIG.L +5.00%\n\n"
            "MIGLIORI 3 DI SEMPRE (YTD) DEL PORTAFOGLIO 📈\n"
            "📊 MRVL +157.35%\n"
            "⛽ ENI.MI +51.51%\n"
            "🏥 HUM +46.55%\n\n"
        )
        # Real/representative gainers for realistic simulation of top performers
        simulated_stock_data = {
            'MRVL': {'daily_change': 3.61, 'company_name': 'Marvell Technology'},
            'PRY.MI': {'daily_change': 3.38, 'company_name': 'Prysmian'},
            'WDEF.L': {'daily_change': 2.47, 'company_name': 'WisdomTree Europe Defence'},
            '1919.HK': {'daily_change': 2.27, 'company_name': 'COSCO Shipping'},
            'ENEL.MI': {'daily_change': 1.80, 'company_name': 'Enel'},
            'NVDA': {'daily_change': 1.45, 'company_name': 'NVIDIA'},
        }

    # ── 2. AI MARKET NEWS SECTION (5 THEMATIC EMOJI MICRO-TOPICS) ─────────────
    print(f"\n🧠 Generazione 5 Microtemi con AI ({session_label})...")
    candidate_news = ""
    try:
        candidate_news = ai_news_generator.generate_market_news_recap(
            max_tags=4,
            market_session=session_label,
            stock_data=simulated_stock_data,
        )
    except Exception as exc:
        print(f"⚠️ Errore generatore Gemini: {exc}")

    if candidate_news and len(candidate_news) > 400:
        print(f"✅ Generata sezione notizie da Gemini: {len(candidate_news)} caratteri")
    else:
        print("ℹ️ Utilizzo fallback strutturato sui 5 microtemi tematici.")
        if "EU" in session_upper:
            candidate_news = (
                f"Buongiorno! I mercati europei stanno per aprire, ecco i punti chiave di oggi ({formatted_date}): ☕\n\n"
                f"🌍 Apertura cauta per i listini del Vecchio Continente, con l'indice bancario europeo $SX7PEX.DE "
                f"in lieve rialzo dell'1.1% sostenuto dai flussi creditizi stabili e dal petrolio Brent a quota 78 dollari.\n\n"
                f"📅 Sul fronte macro, gli investitori attendono la pubblicazione dei dati PMI manifatturieri dell'Eurozona "
                f"e i commenti dei banchieri centrali della BCE per valutare il ritmo dei prossimi allentamenti sui tassi d'interesse.\n\n"
                f"🧬 $AZN.L continua a rafforzare la pipeline oncologica, forte di recenti approvazioni regolatorie europee "
                f"per i trattamenti di precisione e di investimenti strategici per oltre 1.5 miliardi in R&D.\n\n"
                f"🔋 $ENEL.MI accelera sugli investimenti di rete in Italia e Spagna, con il piano industriale 2024-2026 "
                f"che conferma una remunerazione cedolare attraente e un debito netto in costante riduzione.\n\n"
                f"🚢 Sul fronte di nicchia e logistica globale, $1919.HK (COSCO Shipping) beneficia della tenuta delle tariffe "
                f"nolo container sulle rotte Asia-Europa e di un bilancio solido con abbondante liquidità operativa.\n\n"
                f"Quale catalizzatore europeo seguirete con più attenzione questa mattina? Scrivetelo nei commenti! 👇\n\n"
                f"📌 $AZN.L $ENEL.MI $1919.HK $SX7PEX.DE\n\n"
                f"👤 Segui e copia il portafoglio: https://www.etoro.com/people/andrearavalli"
            )
        elif "OPEN" in session_upper:
            candidate_news = (
                f"Buon pomeriggio! Tra poco apre Wall Street: facciamo il punto sulla sessione americana ({formatted_date}): ☕\n\n"
                f"🇺🇸 Futures positivi a New York prima della campana, con l'indice $NSDQ100 che guadagna lo 0.7% "
                f"trainato dal rimbalzo tecnologico, mentre i rendimenti dei Treasury a 10 anni si attestano al 4.12%.\n\n"
                f"📅 L'agenda di oggi prevede l'uscita delle richieste settimanali di sussidi di disoccupazione "
                f"e le dichiarazioni di esponenti della Federal Reserve, determinanti per valutare la traiettoria economica USA.\n\n"
                f"🤖 Nel nostro portafoglio $NVDA consolida la leadership nelle architetture GPU avanzate per data center, "
                f"con una domanda senza sosta per i cluster di calcolo e margini lordi superiori al 74%.\n\n"
                f"💻 $MSFT registra una continua espansione delle entrate cloud Azure (+29% nell'ultimo trimestre), "
                f"grazie all'adozione crescente dei servizi Copilot enterprise integrati nell'ecosistema software.\n\n"
                f"⚡ Tra le posizioni strategiche di nicchia, $CCJ beneficia della domanda strutturale globale per l'uranio "
                f"e dei contratti a lungo termine stipulati con le utility nucleari a prezzi crescenti.\n\n"
                f"Vi aspettate un'apertura sprint o una seduta di consolidamento per Wall Street? Dite la vostra nei commenti! 👇\n\n"
                f"📌 $NVDA $MSFT $CCJ $NSDQ100\n\n"
                f"👤 Segui e copia il portafoglio: https://www.etoro.com/people/andrearavalli"
            )
        else:
            candidate_news = (
                f"Fine sessione! Facciamo un po' di chiarezza su quello che è successo oggi oltre Atlantico ({formatted_date}):\n\n"
                f"🌆 Chiusura solida per Wall Street: l'S&P 500 ha chiuso in territorio positivo metabolizzando i dati "
                f"macroeconomici e le indicazioni sui tassi d'interesse, con una rotazione che ha premiato tecnologia e semiconduttori.\n\n"
                f"🏆 $MRVL (+3.61%) guida i rialzi del nostro portafoglio: il titolo ha beneficiato degli annunci sulle architetture "
                f"di silicio custom per l'intelligenza artificiale e della forte guidance per il segmento data center electro-optics.\n\n"
                f"🥇 $PRY.MI (+3.38%) prosegue il trend positivo grazie all'annuncio di nuove commesse industriali per il cablaggio "
                f"sottomarino offshore e alla progressiva integrazione sinergica delle attività americane di Encore Wire.\n\n"
                f"🥈 $WDEF.L (+2.47%) mette a segno un'ottima performance sostenuta dagli ordini crescenti per i programmi "
                f"aerospaziali europei e dagli impegni di bilancio dei Paesi NATO per la difesa continentale.\n\n"
                f"🥉 $1919.HK (+2.27%) chiude tra i top mover forte dei volumi di carico stabili e del dividendo straordinario "
                f"approvato dai vertici societari.\n\n"
                f"Quale titolo vi ha sorpreso di più nella sessione di oggi? Scrivetelo nei commenti! 👇\n\n"
                f"📌 $MRVL $PRY.MI $WDEF.L $1919.HK\n\n"
                f"👤 Segui e copia il portafoglio: https://www.etoro.com/people/andrearavalli"
            )

    print("\n📝 Sezione Notizie candidata per l'audit modulare:")
    print("-" * 50)
    print(candidate_news)
    print("-" * 50)

    # ── 3. PRE-PUBLICATION MODULAR CONSENSUS AUDIT (Groq + Mistral) ─────────────
    primary_ticker = "NVDA" if "OPEN" in session_upper else "MRVL"
    approved, verified_news, audit = post_verifier.verify_and_clean_post(
        text=candidate_news,
        primary_ticker=primary_ticker,
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

    # ── 5. ASSEMBLE COMPLETE POST ──────────────────────────────────────────────
    full_recap_post = portfolio_header + verified_news.strip() + "\n\n" + why_copy_section.strip()

    # Enforce safe Telegram limit (max 4096, using 3950)
    MAX_TELEGRAM_LENGTH = 3950
    if len(full_recap_post) > MAX_TELEGRAM_LENGTH:
        print(f"⚠️ Trimming recap to fit Telegram limit ({len(full_recap_post)} -> {MAX_TELEGRAM_LENGTH})...")
        cut = full_recap_post.rfind('\n\n', 0, MAX_TELEGRAM_LENGTH - 50)
        if cut != -1:
            full_recap_post = full_recap_post[:cut].rstrip()

    # ── 6. FORMAT TELEGRAM DISPATCH HEADER ─────────────────────────────────────
    tg_header = (
        f"{session_badge_emoji} <b>SIMULAZIONE RECAP {session_num}: {session_display_name}</b> {session_flag_emoji}\n"
        f"<i>(I 5 Microtemi con Emoticon Tematiche • Esclusivo Telegram • Zero eToro)</i>\n\n"
        f"🤖 <b>Auditor:</b> {audit.get('auditor', 'Groq + Mistral')}\n"
        f"🛡️ <b>Score Qualità:</b> {audit.get('score', 95)}/100\n"
        f"📏 <b>Lunghezza:</b> {len(full_recap_post)} caratteri\n"
        f"🕒 <b>Orario Simulato:</b> {temporal_ctx.get('rome_time')} (Mercati: {temporal_ctx.get('market_state')})\n"
        "────────────────────────\n\n"
    )

    tg_full_message = tg_header + full_recap_post

    print(f"\n📨 Spedizione simulazione {session_num} in corso verso Telegram...")
    sent = telegram_sender.send_telegram_message(tg_full_message)
    if sent:
        print(f"🎉 Simulazione {session_num} ({session_name}) inviata con successo su TELEGRAM!")
        return True
    else:
        print(f"❌ Invio simulazione {session_name} su Telegram fallito.")
        return False


def main():
    arg = sys.argv[1].upper() if len(sys.argv) > 1 else "ALL"

    if arg in ["ALL", "ALL_THREE", "3", "TUTTI"]:
        print("🚀 AVVIO SIMULAZIONE DI TUTTI E 3 I RECAP SU TELEGRAM IN SEQUENZA...")
        sessions = ["EU_OPEN", "US_OPEN", "US_CLOSE"]
        success_count = 0
        for s in sessions:
            ok = generate_and_send_test(s)
            if ok:
                success_count += 1
            print("\n⏳ Pausa di 4 secondi tra le simulazioni per rispettare i rate limit...\n")
            time.sleep(4.0)
        print("=" * 65)
        print(f"🏁 ESITO FINALE: {success_count}/{len(sessions)} simulazioni inviate a Telegram.")
        print("=" * 65)
        sys.exit(0 if success_count == len(sessions) else 1)
    else:
        ok = generate_and_send_test(arg)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
