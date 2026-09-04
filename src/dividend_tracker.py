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
try:
    from ai_model_cascade import DEFAULT_GEMINI_MODELS
except ImportError:
    try:
        from src.ai_model_cascade import DEFAULT_GEMINI_MODELS
    except ImportError:
        DEFAULT_GEMINI_MODELS = [
            'gemini-3.1-pro',
            'gemini-3.8-flash',
            'gemini-3.7-flash',
            'gemini-3.6-flash',
            'gemini-3.5-flash',
            'gemini-2.5-flash',
        ]


# Baseline dividend profiles for portfolio holdings
from portfolio_manager import get_asset_metadata

# Baseline dividend profiles for verified dividend-paying portfolio holdings
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
        "sector": "ETF Bancario Europeo ad Alto Rendimento",
        "annual_yield_pct": 7.2,
        "frequency": "Semestrale",
        "frequency": "Semestrale (Giugno / Dicembre)",
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
        "frequency": "Trimestrale (Feb/Mag/Ago/Nov)",
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
        "frequency": "Semestrale (Febbraio / Agosto)",
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
        "frequency": "Semestrale (Maggio / Settembre)",
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
        "frequency": "Trimestrale (Mar/Giu/Set/Dic)",
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
        "frequency": "Trimestrale (Mar/Giu/Set/Dic)",
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
        "frequency": "Trimestrale (Mar/Mag/Ago/Dic)",
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
        "frequency": "Trimestrale (Feb/Mag/Ago/Nov)",
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
        "frequency": "Trimestrale (Mar/Giu/Set/Dic)",
        "tranche_pct": 0.35,
        "approx_dps": "$0,53 post-split",
        "thesis": "Politica di payout con target di distribuire il 50% del Free Cash Flow dell'anno precedente in dividendi.",
    },
    "1919.HK": {
        "name": "COSCO SHIPPING Holdings Co Ltd",
        "cashtag": "$1919.HK",
        "emoji": "🚢",
        "sector": "Logistica Marittima Globale & Terminal Portuali",
        "annual_yield_pct": 6.2,
        "frequency": "Semestrale (Giugno / Ottobre)",
        "tranche_pct": 3.1,
        "approx_dps": "Distribuzione cassa semestrale",
        "thesis": "Spina dorsale del commercio marittimo mondiale con cassa netta massiccia e dividendi straordinari.",
    },
    "MAU.PA": {
        "name": "Etablissements Maurel & Prom SA",
        "cashtag": "$MAU.PA",
        "emoji": "🛢️",
        "sector": "Esplorazione & Produzione Idrocarburi",
        "annual_yield_pct": 4.5,
        "frequency": "Annuale (Luglio)",
        "tranche_pct": 4.5,
        "approx_dps": "€0,30 per azione",
        "thesis": "Produttore petrolifero indipendente a cassa netta positiva e dividendi generosi.",
    },
    "NOVO-B.CO": {
        "name": "Novo Nordisk A/S",
        "cashtag": "$NOVO-B.CO",
        "emoji": "💉",
        "sector": "Farmaceutica & Trattamenti GLP-1",
        "annual_yield_pct": 1.4,
        "frequency": "Semestrale (Marzo / Agosto)",
        "tranche_pct": 0.7,
        "approx_dps": "Distribuzione semestrale DKK",
        "thesis": "Leadership mondiale nel diabete e obesità con crescita continua della remunerazione.",
    },
    "2318.HK": {
        "name": "Ping An Insurance Group",
        "cashtag": "$2318.HK",
        "emoji": "🏦",
        "sector": "Assicurazioni & Finanza Digitale Asia",
        "annual_yield_pct": 6.5,
        "frequency": "Semestrale (Giugno / Ottobre)",
        "tranche_pct": 3.25,
        "approx_dps": "Distribuzione semestrale HKD",
        "thesis": "Colosso assicurativo asiatico con dividendi costanti e multipli a forte sconto.",
    },
    "IQQL.DE": {
        "name": "iShares Listed Private Equity ETF",
        "cashtag": "$IQQL.DE",
        "emoji": "🔥",
        "sector": "Private Equity Quotato & Gestori Alternativi",
        "annual_yield_pct": 3.5,
        "frequency": "Semestrale (Maggio / Novembre)",
        "tranche_pct": 1.75,
        "approx_dps": "Distribuzione semestrale EUR",
        "thesis": "Accesso liquido ai giganti del private equity mondiale con stacco cedolare semestrale.",
    },
    "IEUR": {
        "name": "iShares Core MSCI Europe ETF",
        "cashtag": "$IEUR",
        "emoji": "🇪🇺",
        "sector": "Azionario Europeo Broad Market",
        "annual_yield_pct": 2.5,
        "frequency": "Semestrale (Giugno / Dicembre)",
        "tranche_pct": 1.25,
        "approx_dps": "Distribuzione semestrale USD",
        "thesis": "Esposizione diversificata alle blue chip europee con stacchi semestrali.",
    },
    "VOF.L": {
        "name": "VinaCapital Vietnam Opportunity Fund",
        "cashtag": "$VOF.L",
        "emoji": "🇻🇳",
        "sector": "Azionario Frontier Market Vietnam",
        "annual_yield_pct": 1.5,
        "frequency": "Semestrale (Marzo / Ottobre)",
        "tranche_pct": 0.75,
        "approx_dps": "Distribuzione semestrale USD/GBP",
        "thesis": "Fondo chiuso sulla crescita manifatturiera del Vietnam con dividendo semestrale.",
    },
}

# Calendar mapping for dividend distribution ex-dates (month, approx_day, tranche_label)
# NOTE: Accumulating ETFs (e.g. WDEF.L, INDO.PA, IB01.L, XEON.DE) and Commodities (PPFB.DE) are EXCLUDED.
# NOTE: Accumulating ETFs (e.g. WDEF.L, INDO.PA, IB01.L) and Commodities (PPFB.DE) are EXCLUDED.
DIVIDEND_CALENDAR = {
    "ENI.MI": [(3, 23, "Tranche 3"), (5, 20, "Saldo"), (9, 21, "Tranche 1"), (11, 20, "Tranche 2")],
    "ENEL.MI": [(1, 22, "Acconto"), (7, 22, "Saldo")],
    "WDEF.L": [(6, 15, "Semestrale H1"), (12, 15, "Semestrale H2")],
    "SX7PEX.DE": [(6, 15, "Semestrale H1"), (12, 15, "Semestrale H2")],
    "VOW3.DE": [(5, 25, "Annuale")],
    "ABBV": [(1, 15, "Q1"), (4, 15, "Q2"), (7, 15, "Q3"), (10, 15, "Q4")],
    "ABT.US": [(1, 14, "Q1"), (4, 14, "Q2"), (7, 14, "Q3"), (10, 14, "Q4")],
    "AZN.L": [(2, 20, "Interim"), (8, 15, "Final")],
    "GLEN.L": [(5, 10, "Tranche 1"), (9, 10, "Tranche 2")],
    "TRIG.L": [(3, 15, "Q1"), (6, 15, "Q2"), (9, 15, "Q3"), (12, 15, "Q4")],
    "ULVR.L": [(2, 20, "Q1"), (5, 20, "Q2"), (8, 20, "Q3"), (11, 20, "Q4")],
    "WMT": [(3, 15, "Q1"), (5, 15, "Q2"), (8, 15, "Q3"), (12, 15, "Q4")],
    "MSFT": [(2, 15, "Q1"), (5, 15, "Q2"), (8, 15, "Q3"), (11, 15, "Q4")],
    "AVGO": [(3, 20, "Q1"), (6, 20, "Q2"), (9, 21, "Q3"), (12, 20, "Q4")],
    "1919.HK": [(6, 10, "Final"), (10, 15, "Interim")],
    "MAU.PA": [(7, 5, "Annuale")],
    "NOVO-B.CO": [(3, 25, "Final"), (8, 15, "Interim")],
    "2318.HK": [(6, 5, "Final"), (10, 20, "Interim")],
    "IQQL.DE": [(5, 15, "Semestrale H1"), (11, 15, "Semestrale H2")],
    "IEUR": [(6, 20, "Semestrale H1"), (12, 20, "Semestrale H2")],
    "VOF.L": [(3, 15, "Interim"), (10, 15, "Final")],
}


def find_next_dividend_candidate(days_ahead: int = 25) -> Optional[Tuple[str, str, Dict[str, Any]]]:
    """
    Search across all portfolio dividend holdings for an upcoming ex-dividend date
    within the next `days_ahead` days that has not yet been announced in Gist storage.
    Returns: (ticker, cycle_key, candidate_info) or None
    """
    now = datetime.now(timezone.utc)
    current_year = now.year
    candidates = []

    for ticker, dates in DIVIDEND_CALENDAR.items():
        for month, day, tranche in dates:
            # Check for ex-date in current year
            try:
                ex_date = datetime(current_year, month, day, tzinfo=timezone.utc)
            except ValueError:
                continue

            delta_days = (ex_date - now).total_seconds() / 86400.0

            # If the date has passed this year, check for early next year if near year end
            if delta_days < -1:
                try:
                    ex_date = datetime(current_year + 1, month, day, tzinfo=timezone.utc)
                    delta_days = (ex_date - now).total_seconds() / 86400.0
                except ValueError:
                    continue

            # Check if within window (e.g. 0 to 25 days before ex-date)
            if 0 <= delta_days <= days_ahead:
                cycle_key = f"{ex_date.year}_{month}"
                if not gist_storage.is_dividend_announced(ticker, cycle_key):
                    candidates.append({
                        "ticker": ticker,
                        "cycle_key": cycle_key,
                        "ex_date": ex_date,
                        "delta_days": delta_days,
                        "tranche": tranche,
                    })

    if not candidates:
        return None

    # Sort candidates by closest upcoming ex-date
    candidates.sort(key=lambda c: c["delta_days"])
    top = candidates[0]
    return top["ticker"], top["cycle_key"], top


def fetch_dynamic_dividend_metrics(ticker: str) -> Dict[str, Any]:
    """
    Fetch real-time dynamic dividend metrics (live price, exact 12m dividend sum,
    live dynamic yield %, last dividend date, and actual tranche amount) from Yahoo Finance API.
    """
    import urllib.request
    import json
    from datetime import datetime, timezone

    clean_sym = ticker.replace('$', '').strip()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_sym}?events=div&interval=1mo&range=1y"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = data.get('chart', {}).get('result', [])
            if result:
                res = result[0]
                meta = res.get('meta', {})
                events = res.get('events', {}).get('dividends', {})
                price = meta.get('regularMarketPrice') or meta.get('previousClose') or 0.0
                currency = meta.get('currency', 'USD')
                
                div_sum = sum(float(v.get('amount', 0.0)) for v in events.values())
                yield_pct = (div_sum / price * 100.0) if (price and price > 0 and div_sum > 0) else None

                last_event = list(events.values())[-1] if events else {}
                last_amt = float(last_event.get('amount', 0.0)) if last_event else 0.0
                last_ts = last_event.get('date')
                last_dt_str = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime('%d %B %Y') if last_ts else None
                last_tranche_pct = (last_amt / price * 100.0) if (price and price > 0 and last_amt > 0) else None

                return {
                    "live_price": price,
                    "currency": currency,
                    "live_annual_dividend_sum": div_sum,
                    "live_yield_pct": yield_pct,
                    "last_dividend_amount": last_amt,
                    "last_dividend_date": last_dt_str,
                    "last_tranche_pct": last_tranche_pct,
                    "dividends_count_1y": len(events),
                }
    except Exception as e:
        print(f"ℹ️ Dynamic dividend fetch fallback for {clean_sym} ({e})")

    return {}


def calculate_copier_dividend_impact(
    ticker: str,
    holding_weight_pct: float,
    copier_capital_usd: float = 10000.0,
    portfolio_annual_yield_pct: float = 3.0,
) -> Dict[str, Any]:
    """
    Calculate the exact mathematical impact of a dividend distribution for a copier,
    dynamically overriding yield, tranche %, and DPS with live financial data when available.
    """
    profile = dict(DIVIDEND_PROFILES.get(ticker, {
        "name": ticker,
        "cashtag": f"${ticker}",
        "emoji": "💰",
        "sector": "Titolo in portafoglio",
        "annual_yield_pct": 4.0,
        "frequency": "Periodico",
        "tranche_pct": 1.0,
        "approx_dps": "N/D",
        "thesis": "Generazione di cassa e ritorno di capitale per gli azionisti.",
    }))

    # Dynamically fetch live metrics and override baseline if available
    live_data = fetch_dynamic_dividend_metrics(ticker)
    if live_data:
        if live_data.get("live_yield_pct") and live_data["live_yield_pct"] > 0:
            profile["annual_yield_pct"] = round(live_data["live_yield_pct"], 2)
            print(f"   📈 Live Dynamic Dividend Yield for {ticker}: {profile['annual_yield_pct']}%")
        if live_data.get("last_tranche_pct") and live_data["last_tranche_pct"] > 0:
            profile["tranche_pct"] = round(live_data["last_tranche_pct"], 2)
        if live_data.get("last_dividend_amount") and live_data["last_dividend_amount"] > 0:
            curr = live_data.get("currency", "USD")
            curr_sym = "€" if curr == "EUR" else "$" if curr == "USD" else curr
            profile["approx_dps"] = f"{curr_sym}{live_data['last_dividend_amount']:.2f} per azione"
        if live_data.get("last_dividend_date"):
            profile["last_dividend_date"] = live_data["last_dividend_date"]
        if live_data.get("live_price"):
            profile["live_price"] = live_data["live_price"]

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
L'intero portafoglio (grazie al mix di ETF a distribuzione come $SX7PEX.DE e titoli solidi come $ENI.MI, $ENEL.MI, $ABBV, $TRIG.L) genera un flusso dividendi medio aggregato del ~3,0% annuo.
Su $10.000 copiati, questo si traduce in circa ${annual_tot_usd:.0f} all'anno di puro flusso di cassa passivo, che alimenta la liquidità senza dover vendere alcuna azione.

💬 Reinvestite i dividendi che ricevete in cassa o preferite accumulare liquidità per nuove opportunità? Dite la vostra nei commenti! 👇

📌 {prof['cashtag']} $WDEF.L $SX7PEX.DE $ENI.MI $ABBV
📌 {prof['cashtag']} $SX7PEX.DE $ENI.MI $ENEL.MI $ABBV $TRIG.L
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
5. Includi i cashtag ({prof['cashtag']} $SX7PEX.DE $ENI.MI $ENEL.MI $ABBV $TRIG.L) e hashtag finali (#Dividendi #CashFlow #eToro #PopularInvestor #CopyTrading).
6. Lunghezza: 900-1400 caratteri. Tono autorevole, matematico e trasparente. NO formule robotiche.
7. NON usare mai il markdown per il grassetto (NON usare **testo** o asterischi).

Output ONLY the post text in Italian."""

    try:
        client = genai.Client(api_key=api_key)
        config_gen = types.GenerateContentConfig(temperature=0.7)
        config_gen = types.GenerateContentConfig(temperature=0.5)

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
        for idx, model_name in enumerate(DEFAULT_GEMINI_MODELS):
            for attempt in range(2):
                try:
                    print(f"   🤖 Trying dividend model ({idx+1}/{len(DEFAULT_GEMINI_MODELS)}): {model_name}...")
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
                    err_s = str(exc).lower()
                    if "429" in err_s or "quota" in err_s or "resource_exhausted" in err_s:
                        wait_t = 3.0 * (attempt + 1)
                        print(f"   ⏳ Model {model_name} quota/rate limit (429). Pausing {wait_t:.1f}s...")
                        time.sleep(wait_t)
                        continue
                    print(f"   ⚠️ Gemini {model_name} failed: {exc}")
                    break
    except Exception as e:
        print(f"⚠️ Gemini client error: {e}")

    return f"Dividendi: {prof['cashtag']}", fallback_text


def publish_dividend_post(
    ticker: str,
    weight_override: Optional[float] = None,
    dry_run: bool = False,
    cycle_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate and publish a dedicated dividend announcement post to eToro & Telegram.
    Attaches high-impact dividend infographic.
    """
    print("=" * 65)
    print(f"💰 DIVIDEND POST GENERATOR — Ticker: ${ticker}")
    print(f"🕒 Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"⚙️  Mode: {'DRY RUN' if dry_run else 'LIVE PUBLISH'}")
    print("=" * 65)

    # Validate dividend paying eligibility
    meta = get_asset_metadata(ticker)
    if not meta.get("is_dividend_paying", False) and ticker not in DIVIDEND_PROFILES:
        print(f"❌ REJECTED: {ticker} ({meta.get('name')}) is NOT a dividend-distributing asset.")
        print(f"   Policy: {meta.get('dividend_policy')}")
        return {
            "success": False,
            "error": f"{ticker} is not a dividend paying asset ({meta.get('dividend_policy')})",
            "ticker": ticker
        }

    DEFAULT_WEIGHTS = {
        "ENI.MI": 3.94, "ENEL.MI": 2.94, "WDEF.L": 3.50, "SX7PEX.DE": 3.43,
        "ENI.MI": 3.94, "ENEL.MI": 2.94, "SX7PEX.DE": 3.43,
        "VOW3.DE": 1.24, "ABBV": 2.80, "ABT.US": 2.20, "AZN.L": 2.10,
        "GLEN.L": 2.50, "TRIG.L": 2.20, "ULVR.L": 2.00, "WMT": 1.80,
        "MSFT": 2.19, "AVGO": 1.50, "MAU.PA": 2.00,
        "MSFT": 2.19, "AVGO": 1.50, "MAU.PA": 2.00, "1919.HK": 2.12,
        "NOVO-B.CO": 2.00, "2318.HK": 1.06,
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

    # Generate dedicated dividend infographic (e.g. ENI_DIVIDEND)
    card_path = f"output/infographic_{ticker}_DIVIDEND.png"
    try:
        import stock_focus_infographic
        card_key = f"{ticker}_DIVIDEND" if f"{ticker}_DIVIDEND" in stock_focus_infographic.COMPANY_INFOGRAPHICS else ticker
        card_path = stock_focus_infographic.generate_stock_infographic(
            ticker=card_key,
            output_path=card_path,
        )
    except Exception as exc:
        print(f"ℹ️ Dedicated dividend infographic fallback: {exc}")
        if not os.path.exists(card_path):
            card_path = None

    try:
        from post_verifier import verify_and_clean_post
        approved, verified_text, audit = verify_and_clean_post(
            clean_text,
            primary_ticker=ticker,
            session_name=f"Dividend: {ticker}",
            run_ai_review=True,
        )
        if not approved:
            print(f"❌ Dividend post rejected by post_verifier: {audit.get('explanation')}")
            return {
                "success": False,
                "error": f"Post verifier rejected: {audit.get('explanation')}",
                "ticker": ticker
            }
        clean_text = verified_text
    except Exception as v_err:
        print(f"⚠️ Post verifier check warning: {v_err}")

    print("\n" + "-" * 55)
    print(f"📝 GENERATED DIVIDEND POST PREVIEW:\n")
    print(clean_text)
    if card_path and os.path.exists(card_path):
        print(f"🖼️ Attached Infographic: {card_path}")
    print("-" * 55 + "\n")

    if dry_run:
        print("ℹ️ Dry run enabled: skipping eToro and Telegram API calls.")
        return {
            "success": True,
            "dry_run": True,
            "ticker": ticker,
            "title": title,
            "text": clean_text,
            "card_path": card_path,
        }

    results = {}

    # 1. eToro Social Feed
    print("\n🐂 eToro Social Feed (Dividend Announcement):")
    if etoro_sender.etoro_client.is_configured():
        ok_etoro = etoro_sender.send_etoro_post(
            text=clean_text,
            image_path=card_path if (card_path and os.path.exists(card_path)) else None,
        )
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
            # Mark dividend announced in Gist dedup storage
            now_utc = datetime.now(timezone.utc)
            actual_cycle = cycle_key or f"{now_utc.year}_{now_utc.month}"
            gist_storage.mark_dividend_announced(ticker, actual_cycle, etoro_sender.LAST_PUBLISHED_POST_ID)
            print(f"   🔒 Recorded dividend announcement dedup key: {ticker}_{actual_cycle}")
    else:
        print("   ⏭️  eToro not configured.")
        results["etoro_dividend_post"] = False

    # 2. Telegram
    print("\n📨 Telegram (Dividend Announcement):")
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        try:
            if card_path and os.path.exists(card_path) and hasattr(telegram_sender, "send_telegram_photo"):
                telegram_sender.send_telegram_photo(card_path, caption=clean_text)
            else:
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
    cli_dry_run = "--dry-run" in sys.argv
    cli_auto = "--auto" in sys.argv
    cli_ticker = None

    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            cli_ticker = arg.upper().replace("$", "")
            break

    if cli_auto or not cli_ticker or cli_ticker == "AUTO":
        print("🤖 Autonomous Dividend Announcement Scan Mode...")
        candidate = find_next_dividend_candidate(days_ahead=25)
        if candidate:
            target_ticker, c_key, c_info = candidate
            print(f"🎯 Found upcoming dividend to announce: ${target_ticker} (Ex-date: {c_info['ex_date'].strftime('%d %B %Y')}, in {c_info['delta_days']:.1f} days, Tranche: {c_info['tranche']})")
            publish_dividend_post(ticker=target_ticker, dry_run=cli_dry_run, cycle_key=c_key)
        else:
            print("ℹ️ No upcoming dividends within announcement window or all already announced. Exiting cleanly.")
            sys.exit(0)
    else:
        publish_dividend_post(ticker=cli_ticker, dry_run=cli_dry_run)
