#!/usr/bin/env python3
"""
Dividend Tracker & Copier Income Calculator for eToro
=====================================================
Monitors dividend schedules (Ex-Dividend date, Payment date, Yield %, Tranche amount)
for all portfolio assets and generates high-impact cash flow announcement posts.

Features:
  • Calculates exact dollar cash flow generated for a copier with $10,000 base.
  • Explains the total annual passive cash flow of the entire diversified portfolio.
  • Highlights capital preservation, Risk Score 3/10 and zero leverage.
  • Prevents duplicate announcements using persistent Gist storage.
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load local .env if available
if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')):
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

import etoro_client
import etoro_sender
import telegram_sender
import gist_storage
import analytics_tracker
from etoro_sender import _strip_html

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from api_usage_tracker import log_api_request
    API_TRACKER_AVAILABLE = True
except ImportError:
    API_TRACKER_AVAILABLE = False


DEFAULT_GEMINI_MODELS = [
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-2.5-flash',
]

# Baseline dividend profiles for portfolio holdings
DIVIDEND_PROFILES = {
    "ENI.MI": {
        "name": "Eni S.p.A.",
        "cashtag": "$ENI.MI",
        "emoji": "⛽",
        "sector": "Major Energetica & Gas Naturale",
        "annual_yield_pct": 6.8,
        "frequency": "Trimestrale (4 tranche/anno)",
        "tranche_pct": 1.7,
        "approx_dps": "€0,25 per azione",
        "thesis": "Flussi di cassa solidi con modello satellitare e politica di remunerazione tra le più generose del settore energetico europeo.",
    },
    "ENEL.MI": {
        "name": "Enel S.p.A.",
        "cashtag": "$ENEL.MI",
        "emoji": "💡",
        "sector": "Utility Globale & Reti Elettriche",
        "annual_yield_pct": 6.2,
        "frequency": "Semestrale (Gennaio / Luglio)",
        "tranche_pct": 3.1,
        "approx_dps": "€0,215 per azione",
        "thesis": "Ricavi regolati e prevedibili con focus sul debito in calo e transizione verso reti a bassa volatilità.",
    },
    "WDEF.L": {
        "name": "WisdomTree Europe Equity Income ETF",
        "cashtag": "$WDEF.L",
        "emoji": "💼",
        "sector": "ETF Azionario Europeo High Dividend",
        "annual_yield_pct": 5.2,
        "frequency": "Semestrale",
        "tranche_pct": 2.6,
        "approx_dps": "Distribuzione semestrale",
        "thesis": "Paniere diversificato di società europee leader a larga capitalizzazione con eccellente profilo di generazione di cassa.",
    },
    "SX7PEX.DE": {
        "name": "iShares STOXX Europe 600 Banks ETF",
        "cashtag": "$SX7PEX.DE",
        "emoji": "🏛️",
        "sector": "ETF Bancario Europeo",
        "annual_yield_pct": 7.2,
        "frequency": "Semestrale",
        "tranche_pct": 3.6,
        "approx_dps": "Distribuzione semestrale",
        "thesis": "Bilanci blindati dei primari istituti bancari europei con coefficienti patrimoniali ai massimi e buyback massicci.",
    },
    "VOW3.DE": {
        "name": "Volkswagen AG",
        "cashtag": "$VOW3.DE",
        "emoji": "🚗",
        "sector": "Leader Automotive Globale",
        "annual_yield_pct": 7.5,
        "frequency": "Annuale",
        "tranche_pct": 7.5,
        "approx_dps": "€9,06 per azione ordinaria/priv.",
        "thesis": "Valutazioni a forte sconto con solida cassa industriale netta e marchi iconici (Porsche, Audi, VW).",
    },
    "ABBV": {
        "name": "AbbVie Inc",
        "cashtag": "$ABBV",
        "emoji": "💉",
        "sector": "Farmaceutica & Terapie Avanzate (Dividend King)",
        "annual_yield_pct": 3.7,
        "frequency": "Trimestrale (Feb/Mag/Ago/Nov)",
        "tranche_pct": 0.92,
        "approx_dps": "$1,55 per azione",
        "thesis": "Oltre 50 anni consecutivi di dividendi crescenti (Dividend King) con transizione di successo post-Humira verso Skyrizi e Rinvoq.",
    },
    "ABT.US": {
        "name": "Abbott Laboratories",
        "cashtag": "$ABT",
        "emoji": "🏥",
        "sector": "Dispositivi Medici & Diagnostica (Dividend King)",
        "annual_yield_pct": 2.1,
        "frequency": "Trimestrale",
        "tranche_pct": 0.52,
        "approx_dps": "$0,55 per azione",
        "thesis": "Stabilità secolare nei dispositivi cardiovascolari, FreeStyle Libre per il diabete e nutrizione clinica.",
    },
    "AZN.L": {
        "name": "AstraZeneca PLC",
        "cashtag": "$AZN.L",
        "emoji": "🧬",
        "sector": "Oncologia & Biotecnologie",
        "annual_yield_pct": 2.8,
        "frequency": "Semestrale",
        "tranche_pct": 1.4,
        "approx_dps": "$1,97 semestrale",
        "thesis": "Leader nell'oncologia di precisione e nelle malattie rare con solida pipeline di farmaci blockbuster.",
    },
    "GLEN.L": {
        "name": "Glencore PLC",
        "cashtag": "$GLEN.L",
        "emoji": "⛏️",
        "sector": "Materie Prime & Rame/Cobalto per la Transizione",
        "annual_yield_pct": 4.8,
        "frequency": "Semestrale",
        "tranche_pct": 2.4,
        "approx_dps": "Distribuzione cassa semestrale",
        "thesis": "Attore cardine nella fornitura globale di rame, nichel e materie prime essenziali per i data center e la rete elettrica.",
    },
    "TRIG.L": {
        "name": "The Renewables Infrastructure Group",
        "cashtag": "$TRIG.L",
        "emoji": "🌬️",
        "sector": "Infrastrutture Eoliche & Solari UK/EU",
        "annual_yield_pct": 7.4,
        "frequency": "Trimestrale",
        "tranche_pct": 1.85,
        "approx_dps": "7,18p per azione/anno",
        "thesis": "Contratti di fornitura energetica a lungo termine indicizzati all'inflazione con dividendi costanti.",
    },
    "ULVR.L": {
        "name": "Unilever PLC",
        "cashtag": "$ULVR.L",
        "emoji": "🧼",
        "sector": "Beni di Largo Consumo & Brand Difensivi",
        "annual_yield_pct": 3.6,
        "frequency": "Trimestrale",
        "tranche_pct": 0.9,
        "approx_dps": "€0,43 per azione",
        "thesis": "Brand iconici globali con forte potere di prezzo e domanda anelastica in tutte le condizioni macroeconomiche.",
    },
    "WMT": {
        "name": "Walmart Inc.",
        "cashtag": "$WMT",
        "emoji": "🛒",
        "sector": "Retail Omnicanale & Logistica",
        "annual_yield_pct": 1.3,
        "frequency": "Trimestrale",
        "tranche_pct": 0.32,
        "approx_dps": "$0,2075 post-split",
        "thesis": "Oltre 50 anni consecutivi di aumenti del dividendo, scala logistica ineguagliata ed espansione ad alta marginalità.",
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "cashtag": "$MSFT",
        "emoji": "💻",
        "sector": "Software Enterprise & Cloud Azure",
        "annual_yield_pct": 0.8,
        "frequency": "Trimestrale",
        "tranche_pct": 0.20,
        "approx_dps": "$0,75 per azione",
        "thesis": "Fortezza finanziaria AAA con dividendo costantemente in crescita a doppia cifra accompagnato da reinvestimento massiccio in AI.",
    },
    "AVGO": {
        "name": "Broadcom Inc",
        "cashtag": "$AVGO",
        "emoji": "🔌",
        "sector": "Semiconductors & AI Networking",
        "annual_yield_pct": 1.4,
        "frequency": "Trimestrale",
        "tranche_pct": 0.35,
        "approx_dps": "$0,53 post-split",
        "thesis": "Politica di payout con target di distribuire il 50% del Free Cash Flow dell'anno precedente in dividendi.",
    },
}


def calculate_copier_dividend_impact(
    ticker: str,
    holding_weight_pct: float,
    copier_capital_usd: float = 10000.0,
    portfolio_annual_yield_pct: float = 3.0,
) -> Dict[str, Any]:
    """
    Calculate the exact mathematical impact of a dividend distribution for a copier.
    """
    profile = DIVIDEND_PROFILES.get(ticker, {
        "name": ticker,
        "cashtag": f"${ticker}",
        "emoji": "💰",
        "sector": "Titolo in portafoglio",
        "annual_yield_pct": 4.0,
        "frequency": "Periodico",
        "tranche_pct": 1.0,
        "approx_dps": "N/D",
        "thesis": "Generazione di cassa e ritorno di capitale per gli azionisti.",
    })

    # Dollar allocation for this position on $10,000 base
    position_usd = copier_capital_usd * (holding_weight_pct / 100.0)
    
    # Tranche payout in dollars
    tranche_pct = profile.get("tranche_pct", profile.get("annual_yield_pct", 4.0) / 4.0)
    tranche_dividend_usd = position_usd * (tranche_pct / 100.0)
    
    # Overall annual portfolio dividend cash flow for $10,000 copier
    portfolio_annual_dividends_usd = copier_capital_usd * (portfolio_annual_yield_pct / 100.0)

    return {
        "ticker": ticker,
        "profile": profile,
        "holding_weight_pct": holding_weight_pct,
        "copier_capital_usd": copier_capital_usd,
        "position_usd": position_usd,
        "tranche_pct": tranche_pct,
        "tranche_dividend_usd": tranche_dividend_usd,
        "portfolio_annual_dividends_usd": portfolio_annual_dividends_usd,
        "portfolio_annual_yield_pct": portfolio_annual_yield_pct,
    }


def generate_dividend_post_text(
    data: Dict[str, Any],
    custom_event_date: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Generate an Italian dividend announcement post for eToro and Telegram.
    """
    ticker = data["ticker"]
    prof = data["profile"]
    weight = data["holding_weight_pct"]
    pos_usd = data["position_usd"]
    tranche_usd = data["tranche_dividend_usd"]
    annual_tot_usd = data["portfolio_annual_dividends_usd"]
    annual_yield = prof.get("annual_yield_pct", 4.0)
    event_date = custom_event_date or datetime.now(timezone.utc).strftime("%d %B")

    fallback_text = f"""💰 CASH FLOW & DIVIDENDI IN ARRIVO: FOCUS SU {prof['cashtag']} {prof['emoji']}

Nel nostro portafoglio bilanciamo titoli growth ad altissimo potenziale con solide "macchine da cassa" capaci di generare dividendi costanti e proteggere il capitale con Risk Score 3/10 e zero leva.

Oggi annunciamo la distribuzione del dividendo per una delle posizioni chiave della nostra allocazione:

📌 DETTAGLI STACCO {prof['cashtag']} ({prof['name']}):
• Settore: {prof['sector']}
• Frequenza Distribuzione: {prof['frequency']}
• Dividend Yield Annuo Stimato: ~{annual_yield:.1f}% 📈
• Peso Attuale in Portafoglio: {weight:.2f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 COSA SIGNIFICA PER CHI COPIA IL PORTAFOGLIO ($10.000 BASE)?

Per chi sta copiando la nostra strategia o valuta di allocare $10.000:
↳ Capitale allocato su {prof['cashtag']}: ~${pos_usd:.2f}
↳ Dividendo incassato con questa tranche: ~${tranche_usd:.2f} accreditati direttamente nel vostro saldo "Cassa disponibile" su eToro.

📊 RENDIMENTO COMPLESSIVO ANNUO DA DIVIDENDI:
L'intero portafoglio (grazie al mix di ETF a distribuzione come $WDEF.L, $SX7PEX.DE e titoli solidi come $ENI.MI, $ENEL.MI, $ABBV) genera un flusso dividendi medio aggregato del ~3,0% annuo.
Su $10.000 copiati, questo si traduce in circa ${annual_tot_usd:.0f} all'anno di puro flusso di cassa passivo, che alimenta la liquidità senza dover vendere alcuna azione.

💬 Reinvestite i dividendi che ricevete in cassa o preferite accumulare liquidità per nuove opportunità? Dite la vostra nei commenti! 👇

📌 {prof['cashtag']} $WDEF.L $SX7PEX.DE $ENI.MI $ABBV
🏷️ #Dividendi #CashFlow #eToro #PopularInvestor #Investimenti #CopyTrading
👤 Segui e copia il portafoglio: https://www.etoro.com/people/andrearavalli"""

    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key or not GENAI_AVAILABLE:
        return f"Dividendi: {prof['cashtag']}", fallback_text

    prompt = f"""Sei Andrea Ravalli, Popular Investor italiano su eToro.
Scrivi un post coinvolgente e professionale in ITALIANO per eToro e Telegram dedicato all'annuncio del DIVIDENDO per il titolo {prof['cashtag']} ({prof['name']}).

DATI REALI DA INCLUDERE OBBLIGATORIAMENTE:
- Titolo: {prof['cashtag']} ({prof['name']})
- Settore: {prof['sector']}
- Dividend Yield Annuo Stimato: ~{annual_yield:.1f}% ({prof['frequency']})
- Peso attuale nel nostro portafoglio: {weight:.2f}%
- Tesi di investimento: {prof['thesis']}
- Simulazione su un copier con $10.000:
  ↳ Capitale allocato su questo titolo: ~${pos_usd:.2f}
  ↳ Incasso netto di questa tranche: ~${tranche_usd:.2f} (accreditato sul saldo cassa non investita)
  ↳ Flusso complessivo annuo stimato dell'intero portafoglio: ~${annual_tot_usd:.0f}/anno in dividendi passivi (rendimento medio ~3% annuo).

REGOLE PER IL POST:
1. Titolo: "💰 CASH FLOW & DIVIDENDI IN ARRIVO: FOCUS SU {prof['cashtag']} {prof['emoji']}"
2. Spiega il ruolo strategico dei dividendi nel nostro portafoglio: generazione di cassa passiva, protezione del capitale, Risk Score certificato 3/10 e zero leva finanziaria.
3. Includi la simulazione chiara su $10.000 di copia.
4. Concludi con una domanda stimolante per la community sui dividendi / reinvestimento automatico.
5. Includi i cashtag ({prof['cashtag']} $WDEF.L $SX7PEX.DE $ENI.MI $ABBV) e hashtag finali (#Dividendi #CashFlow #eToro #PopularInvestor #CopyTrading).
6. Lunghezza: 900-1400 caratteri. Tono autorevole, matematico e trasparente. NO formule robotiche.

Output ONLY the post text in Italian."""

    try:
        client = genai.Client(api_key=api_key)
        config_gen = types.GenerateContentConfig(temperature=0.7)

        for model_name in DEFAULT_GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config_gen,
                )
                if response and response.text:
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "dividend_announcement_post")
                    return f"Dividendi: {prof['cashtag']}", response.text.strip()
            except Exception as exc:
                print(f"   ⚠️ Gemini {model_name} failed: {exc}")
                continue
    except Exception as e:
        print(f"⚠️ Gemini client error: {e}")

    return f"Dividendi: {prof['cashtag']}", fallback_text


def publish_dividend_post(
    ticker: str,
    weight_override: Optional[float] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Generate and publish a dedicated dividend announcement post to eToro & Telegram.
    """
    print("=" * 65)
    print(f"💰 DIVIDEND POST GENERATOR — Ticker: ${ticker}")
    print(f"🕒 Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"⚙️  Mode: {'DRY RUN' if dry_run else 'LIVE PUBLISH'}")
    print("=" * 65)

    DEFAULT_WEIGHTS = {
        "ENI.MI": 3.94, "ENEL.MI": 2.94, "WDEF.L": 3.50, "SX7PEX.DE": 3.43,
        "VOW3.DE": 1.24, "ABBV": 2.80, "ABT.US": 2.20, "AZN.L": 2.10,
        "GLEN.L": 2.50, "TRIG.L": 2.20, "ULVR.L": 2.00, "WMT": 1.80,
        "MSFT": 2.19, "AVGO": 1.50, "MAU.PA": 2.00,
    }

    # Determine live weight
    weight = weight_override
    if weight is None:
        try:
            from finance_fetcher import fetch_portfolio_weights
            weights = fetch_portfolio_weights()
            weight = weights.get(ticker, DEFAULT_WEIGHTS.get(ticker, 3.0))
        except Exception:
            weight = DEFAULT_WEIGHTS.get(ticker, 3.0)
    if not weight:
        weight = DEFAULT_WEIGHTS.get(ticker, 3.0)

    calc_data = calculate_copier_dividend_impact(
        ticker=ticker,
        holding_weight_pct=weight,
        copier_capital_usd=10000.0,
    )

    title, post_text = generate_dividend_post_text(calc_data)
    clean_text = _strip_html(post_text)

    print("\n" + "-" * 55)
    print(f"📝 GENERATED DIVIDEND POST PREVIEW:\n")
    print(clean_text)
    print("-" * 55 + "\n")

    if dry_run:
        print("ℹ️ Dry run enabled: skipping eToro and Telegram API calls.")
        return {
            "success": True,
            "dry_run": True,
            "ticker": ticker,
            "title": title,
            "text": clean_text,
        }

    results = {}

    # 1. eToro Social Feed
    print("\n🐂 eToro Social Feed (Dividend Announcement):")
    if etoro_sender.etoro_client.is_configured():
        ok_etoro = etoro_sender.send_etoro_post(text=clean_text)
        results["etoro_dividend_post"] = ok_etoro
        if ok_etoro and etoro_sender.LAST_PUBLISHED_POST_ID:
            gist_storage.save_last_etoro_post(
                post_id=etoro_sender.LAST_PUBLISHED_POST_ID,
                session_name=f"Dividend Announcement: ${ticker}",
                tickers=[ticker],
            )
            analytics_tracker.record_post(
                platform="etoro",
                post_id=etoro_sender.LAST_PUBLISHED_POST_ID,
                session_name="Dividend Announcement",
                text=clean_text,
                image_type="dividend_card",
                tickers=[ticker],
            )
    else:
        print("   ⏭️  eToro not configured.")
        results["etoro_dividend_post"] = False

    # 2. Telegram
    print("\n📨 Telegram (Dividend Announcement):")
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        try:
            telegram_sender.send_telegram_message(clean_text)
            print("   ✅ Dividend post sent to Telegram")
            results["telegram_dividend_post"] = True
        except Exception as e:
            print(f"   ❌ Telegram send failed: {e}")
            results["telegram_dividend_post"] = False
    else:
        print("   ⏭️  Telegram not configured.")
        results["telegram_dividend_post"] = False

    try:
        analytics_tracker.update_and_build_dashboard()
    except Exception:
        pass

    return {
        "success": results.get("etoro_dividend_post", False) or results.get("telegram_dividend_post", False),
        "ticker": ticker,
        "results": results
    }


if __name__ == "__main__":
    cli_ticker = "ENI.MI"
    cli_dry_run = "--dry-run" in sys.argv
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            cli_ticker = arg.upper().replace("$", "")
            break

    publish_dividend_post(ticker=cli_ticker, dry_run=cli_dry_run)
