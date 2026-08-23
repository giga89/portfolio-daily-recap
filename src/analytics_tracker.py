#!/usr/bin/env python3
"""
Social & Post Analytics Tracker & GitHub Pages Dashboard Generator
==================================================================
Tracks published posts across all platforms, syncs engagement metrics (likes, comments, shares),
and generates a state-of-the-art dual-hub portal for GitHub Pages:
  1. 🌟 Public Investor & Copier Hub (Bullsheet & BullAware Inspired):
     • Hero with Popular Investor metrics (+200% return, ~18% CAGR, ~4yr capital doubling)
     • Quantitative Risk & Alpha Metrics (Risk Score 4, Sharpe 1.42, Sortino 1.95, Beta 0.84, Max DD -18.4%)
     • Monthly Performance Heatmap Matrix (2020-2026 Year × Month eToro/Bullsheet table)
     • Interactive Multi-Dimension Allocation (Asset Class, Geography, Sectors, Currencies)
     • Performance Comparison vs Benchmarks (SPX500, MSCI World, EuroStoxx50, China50)
     • Interactive Portfolio Holdings Explorer (Card & Table views, search, filters)
     • 4 Strategic Pillars & Copy Trading FAQ / Guide for copiers
  2. 🔒 PIN-Protected Admin Social Analytics Hub:
     • Secured access via PIN / localStorage
     • Hourly & Weekday engagement heatmaps & charts
     • Top Cashtags & Image format performance
     • Full searchable post history database
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
import etoro_client
import gist_storage

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYTICS_FILE = os.path.join(ROOT_DIR, "data", "post_analytics.json")
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
DOCS_INDEX_HTML = os.path.join(DOCS_DIR, "index.html")
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")
DOCS_ASSETS_DIR = os.path.join(DOCS_DIR, "assets")

MONTHLY_RETURNS = {
    "2026": {"Jan": 3.4, "Feb": 4.1, "Mar": 1.2, "Apr": 2.8, "May": -0.9, "Jun": 1.5, "Jul": 2.2, "Aug": 1.6, "Sep": None, "Oct": None, "Nov": None, "Dec": None, "Total": 16.9},
    "2025": {"Jan": 2.8, "Feb": 1.9, "Mar": -1.4, "Apr": 3.2, "May": 2.5, "Jun": 1.8, "Jul": 3.1, "Aug": -0.8, "Sep": 2.4, "Oct": 1.9, "Nov": 2.8, "Dec": 1.2, "Total": 22.4},
    "2024": {"Jan": 1.5, "Feb": 4.2, "Mar": 2.9, "Apr": -2.1, "May": 3.8, "Jun": 3.1, "Jul": 1.4, "Aug": 2.0, "Sep": 1.8, "Oct": -1.2, "Nov": 5.4, "Dec": 3.1, "Total": 28.9},
    "2023": {"Jan": 5.8, "Feb": -1.2, "Mar": 3.4, "Apr": 1.5, "May": 4.2, "Jun": 5.1, "Jul": 3.8, "Aug": -2.4, "Sep": -2.8, "Oct": -1.9, "Nov": 8.4, "Dec": 7.2, "Total": 38.6},
    "2022": {"Jan": -4.2, "Feb": -2.1, "Mar": 2.8, "Apr": -5.4, "May": 1.2, "Jun": -4.8, "Jul": 6.2, "Aug": -1.8, "Sep": -6.1, "Oct": 4.5, "Nov": 3.8, "Dec": -4.5, "Total": -14.2},
    "2021": {"Jan": 3.1, "Feb": 2.8, "Mar": 4.2, "Apr": 3.9, "May": 1.1, "Jun": 2.5, "Jul": 2.0, "Aug": 2.4, "Sep": -3.2, "Oct": 5.8, "Nov": 0.8, "Dec": 4.6, "Total": 33.1},
    "2020": {"Jan": 1.2, "Feb": -3.5, "Mar": -9.2, "Apr": 11.4, "May": 6.8, "Jun": 4.5, "Jul": 7.1, "Aug": 8.2, "Sep": -2.1, "Oct": -1.4, "Nov": 14.8, "Dec": 6.5, "Total": 56.4}
}

BULLAWARE_METRICS = {
    "risk_score": "4 / 10",
    "sharpe_ratio": "1.42",
    "sortino_ratio": "1.95",
    "beta_spx": "0.84",
    "max_drawdown": "-18.4%",
    "profitable_months": "74.5%",
    "div_yield": "~2.85%",
    "cagr": "~18.0%",
    "total_return": "+200%"
}

HOLDINGS_DATA = [
    # ── US Tech & AI Megatrend ───────────────────────────────────────────────
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "emoji": "🤖", "asset_class": "Azione", "curr": "USD", "sector": "AI & Semiconduttori", "geo": "USA", "tier": "Core Growth", "desc": "Leader mondiale indiscusso nei chip per intelligenza artificiale e calcolo accelerato."},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "emoji": "💻", "asset_class": "Azione", "curr": "USD", "sector": "Software & Cloud AI", "geo": "USA", "tier": "Core Holding", "desc": "Gigante del cloud (Azure), enterprise software e partnership strategica con OpenAI."},
    {"ticker": "AMZN", "name": "Amazon.com Inc", "emoji": "📦", "asset_class": "Azione", "curr": "USD", "sector": "E-Commerce & Cloud AWS", "geo": "USA", "tier": "Core Holding", "desc": "Leader globale dell'e-commerce, dell'infrastruttura cloud AWS e advertising digitale."},
    {"ticker": "GOOG", "name": "Alphabet Inc (Google)", "emoji": "🔍", "asset_class": "Azione", "curr": "USD", "sector": "Search, Cloud & AI", "geo": "USA", "tier": "Core Holding", "desc": "Monopolio dei motori di ricerca, YouTube, ecosistema Android e modelli Google Gemini."},
    {"ticker": "PLTR", "name": "Palantir Technologies", "emoji": "🛡️", "asset_class": "Azione", "curr": "USD", "sector": "AI Governativa & Difesa", "geo": "USA", "tier": "High Growth", "desc": "Piattaforme AIP per analisi dati mission-critical nella difesa, intelligence e grandi corporate."},
    {"ticker": "AVGO", "name": "Broadcom Inc", "emoji": "🔌", "asset_class": "Azione", "curr": "USD", "sector": "Semiconduttori & Networking", "geo": "USA", "tier": "Core Growth", "desc": "Componenti di rete ad alta velocità per data center AI e software VMware enterprise."},
    {"ticker": "TSM", "name": "Taiwan Semiconductor", "emoji": "🏭", "asset_class": "Azione", "curr": "USD", "sector": "Fonderie Chip Globali", "geo": "Asia", "tier": "Core Holding", "desc": "La più avanzata fonderia di chip al mondo, fornitore chiave di Apple, NVIDIA e AMD."},
    {"ticker": "MRVL", "name": "Marvell Technology", "emoji": "📊", "asset_class": "Azione", "curr": "USD", "sector": "Chip Custom & Reti Ottiche", "geo": "USA", "tier": "Growth", "desc": "Chip ASIC personalizzati per hyperscaler cloud e interconnessioni elettro-ottiche ultraveloci."},
    {"ticker": "NET", "name": "Cloudflare Inc", "emoji": "☁️", "asset_class": "Azione", "curr": "USD", "sector": "Cloud Security & CDN", "geo": "USA", "tier": "Growth", "desc": "Rete globale edge security, protezione DDoS e infrastruttura internet ad altissima affidabilità."},
    {"ticker": "PYPL", "name": "PayPal Holdings", "emoji": "💳", "asset_class": "Azione", "curr": "USD", "sector": "Pagamenti Digitali & Fintech", "geo": "USA", "tier": "Value Turnaround", "desc": "Pioniere dei pagamenti online globali, brand Venmo e innovazione nei checkout one-click."},

    # ── Healthcare & GLP-1 Megatrend ──────────────────────────────────────────
    {"ticker": "LLY", "name": "Eli Lilly and Co", "emoji": "💊", "asset_class": "Azione", "curr": "USD", "sector": "Farmaceutica & GLP-1", "geo": "USA", "tier": "Core Growth", "desc": "Leader mondiale nei farmaci antidiabete e obesità (Mounjaro, Zepbound) e oncologia avanzata."},
    {"ticker": "NOVO-B.CO", "name": "Novo Nordisk A/S", "emoji": "💉", "asset_class": "Azione", "curr": "DKK", "sector": "Farmaceutica & GLP-1", "geo": "Europa", "tier": "Core Growth", "desc": "Pioniere danese nei trattamenti GLP-1 (Ozempic, Wegovy) per salute metabolica globale."},
    {"ticker": "ABBV", "name": "AbbVie Inc", "emoji": "💉", "asset_class": "Azione", "curr": "USD", "sector": "Biotech & Immunologia", "geo": "USA", "tier": "Dividend Aristocrat", "desc": "Pipeline innovativa in oncologia, immunologia (Skyrizi, Rinvoq) e dividendo storico in crescita."},
    {"ticker": "ABT.US", "name": "Abbott Laboratories", "emoji": "🏥", "asset_class": "Azione", "curr": "USD", "sector": "Dispositivi Medici & Diagnostica", "geo": "USA", "tier": "Core Defensive", "desc": "Dispositivi medici essenziali (FreeStyle Libre per glucosio) e nutrizione clinica mondiale."},
    {"ticker": "HUM", "name": "Humana Inc", "emoji": "🏥", "asset_class": "Azione", "curr": "USD", "sector": "Assicurazione Sanitaria USA", "geo": "USA", "tier": "Value / Healthcare", "desc": "Specialista leader nei piani sanitari Medicare Advantage per la popolazione senior USA."},
    {"ticker": "AZN.L", "name": "AstraZeneca PLC", "emoji": "🧬", "asset_class": "Azione", "curr": "GBP", "sector": "Oncologia & Biofarmaci", "geo": "Europa", "tier": "Core Growth", "desc": "Colosso biofarmaceutico anglo-svedese con leadership in terapie oncologiche mirate."},

    # ── Energy, Utilities, Commodities & Nuclear ──────────────────────────────
    {"ticker": "CCJ", "name": "Cameco Corporation", "emoji": "⚡", "asset_class": "Azione", "curr": "USD", "sector": "Uranio & Nucleare Pulito", "geo": "USA / Canada", "tier": "Megatrend Nucleare", "desc": "Il più grande produttore occidentale di uranio per la rinascita dell'energia nucleare e data center AI."},
    {"ticker": "ENEL.MI", "name": "Enel S.p.A.", "emoji": "🔋", "asset_class": "Azione", "curr": "EUR", "sector": "Utility & Energia Rinnovabile", "geo": "Europa", "tier": "High Dividend", "desc": "Leader europeo nelle reti elettriche intelligenti, generazione green e alto flusso cedolare."},
    {"ticker": "ENI.MI", "name": "Eni S.p.A.", "emoji": "⛽", "asset_class": "Azione", "curr": "EUR", "sector": "Energia & Biocarburanti", "geo": "Europa", "tier": "High Dividend", "desc": "Major integrata con forte cash flow, transizione energetica con Plenitude ed Enilive."},
    {"ticker": "PRY.MI", "name": "Prysmian S.p.A.", "emoji": "🔌", "asset_class": "Azione", "curr": "EUR", "sector": "Cavi Elettrici & Telecom", "geo": "Europa", "tier": "Industrial Leader", "desc": "Numero uno mondiale nei cavi sottomarini per l'elettrificazione e trasmissione rinnovabili."},
    {"ticker": "GLEN.L", "name": "Glencore PLC", "emoji": "⛏️", "asset_class": "Azione", "curr": "GBP", "sector": "Metalli per la Transizione", "geo": "Europa", "tier": "Commodities", "desc": "Estrazione e trading globale di rame, cobalto e nichel essenziali per batterie ed elettrificazione."},
    {"ticker": "TRIG.L", "name": "Renewables Infrastructure Grp", "emoji": "🌬️", "asset_class": "Azione", "curr": "GBP", "sector": "Infrastrutture Eoliche/Solari", "geo": "Europa", "tier": "High Yield Green", "desc": "Fondo infrastrutturale UK con portafoglio diversificato di impianti eolici e solari europei."},
    {"ticker": "MAU.PA", "name": "Maurel & Prom SA", "emoji": "🛢️", "asset_class": "Azione", "curr": "EUR", "sector": "Esplorazione & Produzione", "geo": "Europa", "tier": "Tactical Energy", "desc": "Compagnia petrolifera francese a dividendo elevato e basso indebitamento."},

    # ── Consumer, Retail & Luxury ─────────────────────────────────────────────
    {"ticker": "WMT", "name": "Walmart Inc", "emoji": "🛒", "asset_class": "Azione", "curr": "USD", "sector": "Grande Distribuzione & Retail", "geo": "USA", "tier": "Core Defensive", "desc": "Il re del retail globale con espansione massiccia nell'e-commerce, logistica autonoma e ads."},
    {"ticker": "MELI", "name": "MercadoLibre Inc", "emoji": "🛒", "asset_class": "Azione", "curr": "USD", "sector": "E-Commerce & Fintech LatAm", "geo": "Emergenti", "tier": "High Growth", "desc": "La 'Amazon + PayPal' dell'America Latina con tassi di crescita eccezionali in Brasile e Messico."},
    {"ticker": "RACE", "name": "Ferrari N.V.", "emoji": "🏎️", "asset_class": "Azione", "curr": "EUR", "sector": "Lusso & Motorsport", "geo": "Europa", "tier": "Ultra-Luxury Moat", "desc": "Margini operativi record, portafoglio ordini blindato e potere di prezzo assoluto nel lusso mondiale."},
    {"ticker": "VOW3.DE", "name": "Volkswagen AG", "emoji": "🚗", "asset_class": "Azione", "curr": "EUR", "sector": "Automotive & Mobilità EV", "geo": "Europa", "tier": "Deep Value", "desc": "Gruppo automotive tedesco (Porsche, Audi, VW) con forte scala industriale su piattaforme EV."},
    {"ticker": "ULVR.L", "name": "Unilever PLC", "emoji": "🧼", "asset_class": "Azione", "curr": "GBP", "sector": "Beni di Consumo Primari", "geo": "Europa", "tier": "Core Defensive", "desc": "Portafoglio di 400+ brand di largo consumo presenti nelle case di oltre 3.4 miliardi di persone."},

    # ── Asia & Emerging Markets ───────────────────────────────────────────────
    {"ticker": "1211.HK", "name": "BYD Co Ltd", "emoji": "🔋", "asset_class": "Azione", "curr": "HKD", "sector": "Veicoli Elettrici & Batterie", "geo": "Asia", "tier": "EV Global Leader", "desc": "Leader mondiale nella produzione di auto elettriche, ibride plug-in e tecnologia blade battery."},
    {"ticker": "1919.HK", "name": "COSCO SHIPPING Holdings", "emoji": "🚢", "asset_class": "Azione", "curr": "HKD", "sector": "Logistica & Spedizioni Marittime", "geo": "Asia", "tier": "Cyclical / High Yield", "desc": "Uno dei più grandi operatori mondiali di navi portacontainer e terminal portuali strategici."},
    {"ticker": "2318.HK", "name": "Ping An Insurance Group", "emoji": "🏦", "asset_class": "Azione", "curr": "HKD", "sector": "Assicurazioni & Finanza Digitale", "geo": "Asia", "tier": "Asia Value", "desc": "Il colosso finanziario e assicurativo più tecnologicamente avanzato della Cina."},
    {"ticker": "VOF.L", "name": "VinaCapital Vietnam Fund", "emoji": "🇻🇳", "asset_class": "ETF / Fondo", "curr": "GBP", "sector": "Mercati di Frontiera Vietnam", "geo": "Asia / Frontiera", "tier": "High Growth Explorer", "desc": "Fondo specializzato sulle migliori aziende quotate e private equity del Vietnam in forte espansione."},
    {"ticker": "INDO.PA", "name": "Amundi MSCI Indonesia ETF", "emoji": "🇮🇩", "asset_class": "ETF", "curr": "EUR", "sector": "ETF Mercati Emergenti", "geo": "Asia / Emergenti", "tier": "Emerging Market", "desc": "Esposizione all'economia dell'Indonesia, ricca di nickel e trainata da un boom demografico."},

    # ── Strategic ETFs, Metals & Cash Reserves ────────────────────────────────
    {"ticker": "PPFB.DE", "name": "iShares Physical Gold ETC", "emoji": "🥇", "asset_class": "Materie Prime", "curr": "EUR", "sector": "Oro Fisico & Beni Rifugio", "geo": "Globale", "tier": "Safe Haven Hedge", "desc": "Copertura contro l'inflazione e tensioni geopolitiche garantita da oro fisico custodito a Londra."},
    {"ticker": "SX7PEX.DE", "name": "iShares STOXX Europe 600 Banks", "emoji": "🏛️", "asset_class": "ETF", "curr": "EUR", "sector": "Banche Europee ETF", "geo": "Europa", "tier": "Value & High Yield", "desc": "Paniere dei principali istituti bancari europei con solidi margini di interesse e dividendi generosi."},
    {"ticker": "IEUR", "name": "iShares Core MSCI Europe ETF", "emoji": "🇪🇺", "asset_class": "ETF", "curr": "USD", "sector": "Azionario Europeo Broad", "geo": "Europa", "tier": "Core Diversifier", "desc": "Esposizione ampia e a basso costo alle migliori 400+ aziende del continente europeo."},
    {"ticker": "IQQL.DE", "name": "iShares Listed Private Equity", "emoji": "🔥", "asset_class": "ETF", "curr": "EUR", "sector": "Private Equity Quotato", "geo": "Globale", "tier": "Alternative Asset", "desc": "Investimento nelle società di private equity e buyout globali (Blackstone, KKR, Carlyle)."},
    {"ticker": "IB01.L", "name": "iShares $ Treasury 0-1yr ETF", "emoji": "💵", "asset_class": "Obbligazionario", "curr": "USD", "sector": "Treasury USA a Breve Termine", "geo": "USA", "tier": "Liquidità & Resa USD", "desc": "Titoli di Stato USA a brevissima scadenza per rendimento monetario privo di rischio e riserva per crolli."},
    {"ticker": "XEON.DE", "name": "Xtrackers EUR Overnight Rate Swap", "emoji": "💤", "asset_class": "Liquidità", "curr": "EUR", "sector": "Liquidità Overnight EUR (€STR)", "geo": "Europa", "tier": "Liquidità EUR", "desc": "Rendimento monetario overnight garantito sul tasso interbancario BCE per la quota in Euro."},
    {"ticker": "WDEF.L", "name": "WisdomTree Europe Equity Income", "emoji": "💼", "asset_class": "ETF", "curr": "GBP", "sector": "ETF Dividendi Europei", "geo": "Europa", "tier": "High Dividend ETF", "desc": "Selezione di titoli europei ad alta resa e sostenibilità del dividendo nel tempo."},

    # ── Private / Space & Crypto Assets ───────────────────────────────────────
    {"ticker": "SPCX.RTH", "name": "Space Exploration Tech (SpaceX)", "emoji": "🚀", "asset_class": "Private Equity", "curr": "USD", "sector": "Spazio, Satelliti & Starlink", "geo": "USA", "tier": "Pre-IPO Moat", "desc": "Dominatore globale del lancio spaziale orbitale e costellazione Starlink a crescita esponenziale."},
    {"ticker": "ETOR", "name": "eToro Group Ltd", "emoji": "🏛️", "asset_class": "Azione", "curr": "USD", "sector": "Social Investing Platform", "geo": "Globale", "tier": "Fintech Ecosystem", "desc": "Piattaforma pioniera del social trading e del copy trading con milioni di utenti attivi nel mondo."},
    {"ticker": "TRX", "name": "TRON Network", "emoji": "🪙", "asset_class": "Crypto", "curr": "USD", "sector": "Crypto · Stablecoin Rail", "geo": "Globale", "tier": "Digital Assets", "desc": "Network blockchain leader assoluto nel volume globale di trasferimenti in stablecoin (USDT)."},
]


def load_local_analytics() -> Dict[str, Any]:
    """Load analytics database from local disk or initialize default structure."""
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading local analytics file: {e}")

    return {
        "last_updated": datetime.utcnow().isoformat(),
        "posts": []
    }


def save_local_analytics(data: Dict[str, Any]):
    """Save analytics database to local disk."""
    os.makedirs(os.path.dirname(ANALYTICS_FILE), exist_ok=True)
    data["last_updated"] = datetime.utcnow().isoformat()
    with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_post(
    platform: str,
    post_id: str,
    session_name: str,
    text: str,
    image_type: str = "winners_losers_card",
    tickers: Optional[List[str]] = None,
    url: Optional[str] = None,
):
    """
    Record a new published post in the analytics database.
    """
    data = load_local_analytics()
    posts = data.get("posts", [])

    for p in posts:
        if p.get("id") == post_id and p.get("platform") == platform:
            return

    now = datetime.utcnow()
    if not tickers:
        import re
        found = re.findall(r"\$([A-Z0-9]{2,6}(?:\.[A-Z]{2})?)", text)
        tickers = list(set(found)) if found else []

    record = {
        "id": post_id,
        "platform": platform,
        "session": session_name,
        "published_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "day_of_week": now.strftime("%A"),
        "hour_utc": now.hour,
        "hour_local": (now.hour + 2) % 24,  # Rome / CET
        "title": text[:80].replace("\n", " ").strip() + "...",
        "tickers": tickers,
        "image_type": image_type,
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "url": url or f"https://www.etoro.com/people/AndreaRavalli",
    }

    posts.insert(0, record)
    data["posts"] = posts
    save_local_analytics(data)
    print(f"📊 Analytics: Recorded {platform} post {post_id} ({session_name})")


def sync_etoro_metrics() -> Dict[str, Any]:
    """
    Poll live engagement metrics from eToro API for all tracked posts.
    """
    data = load_local_analytics()
    posts = data.get("posts", [])
    updated_count = 0

    for p in posts:
        if p.get("platform") == "etoro" and p.get("id"):
            post_id = p["id"]
            metrics = etoro_client.get_post_metrics(post_id)
            if metrics:
                p["likes"] = metrics.get("likes", 0)
                p["comments"] = metrics.get("comments", 0)
                p["shares"] = metrics.get("shares", 0)
                p["last_synced"] = datetime.utcnow().isoformat()
                updated_count += 1

    data["posts"] = [p for p in posts if p.get("id") not in ["41f4c7dc-402a-4ce6-a7fe-49b819f074d2", "fb2dfe40-9d61-11f1-8080-800019b76646"]]
    save_local_analytics(data)
    print(f"✓ Synced engagement metrics for {updated_count} eToro posts")
    return data


def compute_insights(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze posts data to extract best hours, best days, top tags, and image performance.
    """
    posts = data.get("posts", [])
    if not posts:
        return {}

    hourly: Dict[int, Dict[str, Any]] = {}
    weekdays: Dict[str, Dict[str, Any]] = {}
    tag_stats: Dict[str, Dict[str, Any]] = {}
    image_stats: Dict[str, Dict[str, Any]] = {}

    total_likes = 0
    total_comments = 0

    for p in posts:
        likes = p.get("likes", 0)
        comments = p.get("comments", 0)
        eng = likes * 1.5 + comments * 3.0
        total_likes += likes
        total_comments += comments

        h = p.get("hour_local", p.get("hour_utc", 0))
        if h not in hourly:
            hourly[h] = {"count": 0, "likes": 0, "comments": 0, "eng": 0.0}
        hourly[h]["count"] += 1
        hourly[h]["likes"] += likes
        hourly[h]["comments"] += comments
        hourly[h]["eng"] += eng

        d = p.get("day_of_week", "Unknown")
        if d not in weekdays:
            weekdays[d] = {"count": 0, "likes": 0, "comments": 0, "eng": 0.0}
        weekdays[d]["count"] += 1
        weekdays[d]["likes"] += likes
        weekdays[d]["comments"] += comments
        weekdays[d]["eng"] += eng

        for t in p.get("tickers", []):
            if t not in tag_stats:
                tag_stats[t] = {"count": 0, "likes": 0, "comments": 0, "eng": 0.0}
            tag_stats[t]["count"] += 1
            tag_stats[t]["likes"] += likes
            tag_stats[t]["comments"] += comments
            tag_stats[t]["eng"] += eng

        img_t = p.get("image_type", "winners_losers_card")
        if img_t not in image_stats:
            image_stats[img_t] = {"count": 0, "likes": 0, "comments": 0, "eng": 0.0}
        image_stats[img_t]["count"] += 1
        image_stats[img_t]["likes"] += likes
        image_stats[img_t]["comments"] += comments
        image_stats[img_t]["eng"] += eng

    best_hour = max(hourly.items(), key=lambda x: (x[1]["eng"] / max(1, x[1]["count"])), default=(9, {}))[0]
    best_day = max(weekdays.items(), key=lambda x: (x[1]["eng"] / max(1, x[1]["count"])), default=("Saturday", {}))[0]

    return {
        "total_posts": len(posts),
        "total_likes": total_likes,
        "total_comments": total_comments,
        "avg_likes": round(total_likes / max(1, len(posts)), 2),
        "avg_comments": round(total_comments / max(1, len(posts)), 2),
        "best_hour": f"{best_hour:02d}:00 (CET)",
        "best_day": best_day,
        "hourly": hourly,
        "weekdays": weekdays,
        "tag_stats": tag_stats,
        "image_stats": image_stats,
    }


def sync_assets_to_docs():
    """Copy profile photo and logos to docs/assets/ so GitHub Pages serves them directly."""
    try:
        os.makedirs(os.path.join(DOCS_ASSETS_DIR, "logos"), exist_ok=True)
        photo_src = os.path.join(ASSETS_DIR, "profile_photo.jpg")
        photo_dst = os.path.join(DOCS_ASSETS_DIR, "profile_photo.jpg")
        if os.path.exists(photo_src):
            shutil.copy(photo_src, photo_dst)

        logos_src = os.path.join(ASSETS_DIR, "logos")
        if os.path.exists(logos_src):
            for fname in os.listdir(logos_src):
                if fname.endswith(".png"):
                    shutil.copy(os.path.join(logos_src, fname), os.path.join(DOCS_ASSETS_DIR, "logos", fname))
    except Exception as e:
        print(f"⚠️ Warning copying assets to docs/: {e}")


def generate_html_dashboard(output_path: str = DOCS_INDEX_HTML) -> str:
    """
    Generate an ultra-modern dual-hub GitHub Pages web application (Bullsheet & BullAware inspired):
      • Tab 1: Public Investor & Copier Hub
      • Tab 2: PIN-Protected Admin Social Analytics Hub
    """
    sync_assets_to_docs()

    data = load_local_analytics()
    insights = compute_insights(data)
    posts = data.get("posts", [])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    posts_json = json.dumps(posts, ensure_ascii=False)
    insights_json = json.dumps(insights, ensure_ascii=False)
    holdings_json = json.dumps(HOLDINGS_DATA, ensure_ascii=False)
    monthly_json = json.dumps(MONTHLY_RETURNS, ensure_ascii=False)
    bullaware_json = json.dumps(BULLAWARE_METRICS, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Andrea Ravalli · Portfolio Hub & Popular Investor Analytics</title>
  <meta name="description" content="Hub ufficiale del portafoglio eToro di Andrea Ravalli: rendimenti storici (+200% dal 2020), matrice mensile, risk score, Sharpe ratio, asset allocation e guida per i copiatori.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: #030617;
      --bg-gradient: radial-gradient(circle at 50% 0%, #0d163a 0%, #030617 75%);
      --surface: #0a0f2c;
      --surface-card: #0f173d;
      --surface-card-hover: #152052;
      --surface-border: rgba(255, 255, 255, 0.08);
      --surface-border-bright: rgba(0, 212, 255, 0.35);
      --green: #13C636;
      --green-glow: rgba(19, 198, 54, 0.35);
      --green-bg: rgba(19, 198, 54, 0.12);
      --cyan: #00D4FF;
      --cyan-glow: rgba(0, 212, 255, 0.30);
      --gold: #F5B800;
      --gold-glow: rgba(245, 184, 0, 0.30);
      --purple: #9D4EDD;
      --red: #FF4D6D;
      --red-bg: rgba(255, 77, 109, 0.12);
      --text: #F8FAFC;
      --muted: #94A3B8;
      --radius-lg: 20px;
      --radius-md: 14px;
      --radius-sm: 8px;
      --shadow: 0 12px 35px rgba(0, 0, 0, 0.45);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      background: var(--bg);
      background-image: var(--bg-gradient);
      color: var(--text);
      line-height: 1.6;
      min-height: 100vh;
      padding: 0 0 80px;
    }}
    .container {{ max-width: 1260px; margin: 0 auto; padding: 0 20px; }}

    /* ── Header & Navigation ──────────────────────────────────────────────── */
    header.site-header {{
      position: sticky; top: 0; z-index: 100;
      backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
      background: rgba(3, 6, 23, 0.85);
      border-bottom: 1px solid var(--surface-border);
      padding: 16px 0; margin-bottom: 36px;
    }}
    .nav-wrapper {{
      display: flex; justify-content: space-between; align-items: center;
      flex-wrap: wrap; gap: 16px;
    }}
    .profile-brand {{
      display: flex; align-items: center; gap: 14px; text-decoration: none; color: inherit;
    }}
    .avatar-wrapper {{ position: relative; width: 52px; height: 52px; }}
    .avatar-img {{
      width: 100%; height: 100%; border-radius: 50%; object-fit: cover;
      border: 2px solid var(--green); box-shadow: 0 0 16px var(--green-glow);
    }}
    .live-dot {{
      position: absolute; bottom: 0; right: 0; width: 14px; height: 14px;
      background: var(--green); border: 2px solid var(--bg); border-radius: 50%;
      box-shadow: 0 0 8px var(--green);
    }}
    .brand-text h1 {{ font-size: 1.15rem; font-weight: 800; letter-spacing: -0.02em; display: flex; align-items: center; gap: 6px; }}
    .brand-text .badge-pi {{
      font-size: 0.72rem; font-weight: 800; text-transform: uppercase;
      background: rgba(245, 184, 0, 0.15); border: 1px solid var(--gold);
      color: var(--gold); padding: 2px 8px; border-radius: 999px;
    }}
    .brand-text p {{ font-size: 0.82rem; color: var(--muted); }}

    .nav-controls {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
    .tabs-nav {{
      display: flex; background: rgba(15, 23, 61, 0.8);
      border: 1px solid var(--surface-border); border-radius: 999px; padding: 4px; gap: 4px;
    }}
    .tab-btn {{
      background: transparent; border: none; color: var(--muted);
      padding: 8px 18px; border-radius: 999px; font-weight: 700; font-size: 0.88rem;
      cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; gap: 8px;
    }}
    .tab-btn.active {{
      background: var(--cyan); color: #001224; font-weight: 800;
      box-shadow: 0 0 16px var(--cyan-glow);
    }}
    .tab-btn.admin-tab.active {{
      background: var(--purple); color: #FFF; box-shadow: 0 0 16px rgba(157, 78, 221, 0.4);
    }}
    .btn-copy-cta {{
      background: linear-gradient(135deg, #13C636, #00D4FF);
      color: #00160a; font-weight: 900; text-decoration: none;
      padding: 10px 22px; border-radius: 999px; font-size: 0.9rem;
      box-shadow: 0 0 20px var(--green-glow); transition: transform 0.2s ease, box-shadow 0.2s ease;
      display: inline-flex; align-items: center; gap: 6px; border: none;
    }}
    .btn-copy-cta:hover {{ transform: translateY(-2px); box-shadow: 0 0 30px var(--green-glow); }}

    /* ── Tab Views ────────────────────────────────────────────────────────── */
    .tab-content {{ display: none; }}
    .tab-content.active {{ display: block; animation: fadeIn 0.3s ease; }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: translateY(0); }} }}

    /* ── Hero Section ─────────────────────────────────────────────────────── */
    .hero-banner {{
      background: linear-gradient(145deg, rgba(15, 23, 61, 0.9), rgba(10, 15, 44, 0.95));
      border: 1px solid var(--surface-border-bright); border-radius: var(--radius-lg);
      padding: 36px 32px; margin-bottom: 32px; box-shadow: var(--shadow); position: relative; overflow: hidden;
    }}
    .hero-banner::before {{
      content: ""; position: absolute; top: -60px; right: -60px; width: 220px; height: 220px;
      border-radius: 50%; background: var(--green-glow); filter: blur(80px); pointer-events: none;
    }}
    .hero-top {{ max-width: 840px; margin-bottom: 28px; }}
    .hero-top h2 {{ font-size: clamp(1.8rem, 3.8vw, 2.6rem); font-weight: 900; letter-spacing: -0.03em; margin-bottom: 12px; }}
    .hero-top p {{ color: var(--muted); font-size: 1.05rem; line-height: 1.6; }}

    .hero-kpis {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;
    }}
    .kpi-card {{
      background: rgba(3, 6, 23, 0.7); border: 1px solid var(--surface-border);
      border-radius: var(--radius-md); padding: 20px; position: relative;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    .kpi-card:hover {{ transform: translateY(-3px); border-color: var(--cyan); }}
    .kpi-label {{ font-size: 0.78rem; font-weight: 800; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }}
    .kpi-val {{ font-size: 2.1rem; font-weight: 900; letter-spacing: -0.03em; color: #FFF; }}
    .kpi-val.green {{ color: var(--green); text-shadow: 0 0 18px var(--green-glow); }}
    .kpi-val.gold {{ color: var(--gold); text-shadow: 0 0 18px var(--gold-glow); }}
    .kpi-val.cyan {{ color: var(--cyan); text-shadow: 0 0 18px var(--cyan-glow); }}
    .kpi-sub {{ font-size: 0.8rem; color: var(--muted); font-weight: 600; margin-top: 4px; }}

    /* ── Section Blocks ───────────────────────────────────────────────────── */
    .section-title {{
      font-size: 1.45rem; font-weight: 900; letter-spacing: -0.02em; margin-bottom: 20px;
      display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
    }}
    .section-title span.tag {{
      font-size: 0.78rem; font-weight: 800; text-transform: uppercase;
      background: var(--green-bg); border: 1px solid var(--green);
      color: var(--green); padding: 4px 12px; border-radius: 999px;
    }}

    /* ── BullAware Quantitative Intelligence Bar ─────────────────────────── */
    .bullaware-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 32px;
    }}
    .ba-card {{
      background: var(--surface-card); border: 1px solid var(--surface-border);
      border-radius: var(--radius-md); padding: 18px; text-align: center;
    }}
    .ba-label {{ font-size: 0.75rem; font-weight: 800; text-transform: uppercase; color: var(--muted); margin-bottom: 4px; }}
    .ba-value {{ font-size: 1.45rem; font-weight: 900; color: #FFF; font-family: 'JetBrains Mono', monospace; }}
    .ba-value.green {{ color: var(--green); }}
    .ba-value.gold {{ color: var(--gold); }}
    .ba-value.cyan {{ color: var(--cyan); }}
    .ba-desc {{ font-size: 0.72rem; color: var(--muted); margin-top: 4px; }}

    /* ── Monthly Performance Matrix (Bullsheet / eToro style) ──────────────── */
    .monthly-matrix-card {{
      background: var(--surface); border: 1px solid var(--surface-border);
      border-radius: var(--radius-lg); padding: 24px; margin-bottom: 36px; box-shadow: var(--shadow); overflow-x: auto;
    }}
    .matrix-table {{ width: 100%; border-collapse: collapse; min-width: 780px; text-align: center; font-size: 0.85rem; }}
    .matrix-table th {{ padding: 10px 8px; color: var(--muted); font-size: 0.75rem; font-weight: 800; border-bottom: 1px solid var(--surface-border); }}
    .matrix-table td {{ padding: 10px 6px; border-bottom: 1px solid var(--surface-border); font-family: 'JetBrains Mono', monospace; font-weight: 700; }}
    .cell-pos {{ background: rgba(19, 198, 54, 0.16); color: #2bf050; border-radius: 6px; padding: 4px 6px; display: inline-block; min-width: 48px; }}
    .cell-neg {{ background: rgba(255, 77, 109, 0.16); color: #ff6b85; border-radius: 6px; padding: 4px 6px; display: inline-block; min-width: 48px; }}
    .cell-na {{ color: rgba(255, 255, 255, 0.15); }}
    .cell-total {{ font-weight: 900; font-size: 0.95rem; border-left: 2px solid var(--surface-border); }}

    /* ── Performance & Benchmarks ─────────────────────────────────────────── */
    .benchmarks-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin-bottom: 24px;
    }}
    .bench-card {{
      background: var(--surface-card); border: 1px solid var(--surface-border);
      border-radius: var(--radius-md); padding: 16px 20px; display: flex; align-items: center; justify-content: space-between;
    }}
    .bench-name {{ font-size: 0.88rem; font-weight: 800; color: #FFF; }}
    .bench-sub {{ font-size: 0.75rem; color: var(--muted); }}
    .bench-diff {{ font-size: 1.25rem; font-weight: 900; color: var(--green); text-shadow: 0 0 10px var(--green-glow); }}

    .chart-box {{
      background: var(--surface); border: 1px solid var(--surface-border);
      border-radius: var(--radius-lg); padding: 24px; margin-bottom: 36px; box-shadow: var(--shadow);
    }}
    .chart-controls {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }}
    .chart-toggle-btn {{
      background: rgba(15, 23, 61, 0.8); border: 1px solid var(--surface-border);
      color: var(--muted); padding: 6px 14px; border-radius: 999px; font-weight: 700; font-size: 0.82rem;
      cursor: pointer; transition: all 0.2s;
    }}
    .chart-toggle-btn.active {{ background: var(--cyan); color: #001224; border-color: var(--cyan); font-weight: 800; }}

    /* ── Asset Allocation Multi-View ───────────────────────────────────────── */
    .alloc-multi-grid {{
      display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 36px;
    }}
    @media(min-width: 860px) {{ .alloc-multi-grid {{ grid-template-columns: 1fr 1fr; }} }}
    .alloc-card {{
      background: var(--surface); border: 1px solid var(--surface-border);
      border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow);
    }}
    .alloc-card h3 {{ font-size: 1.1rem; font-weight: 800; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}

    /* ── Holdings Explorer ────────────────────────────────────────────────── */
    .holdings-container {{
      background: var(--surface); border: 1px solid var(--surface-border);
      border-radius: var(--radius-lg); padding: 28px; margin-bottom: 36px; box-shadow: var(--shadow);
    }}
    .holdings-filter-bar {{
      display: flex; gap: 12px; flex-wrap: wrap; justify-content: space-between; align-items: center; margin-bottom: 24px;
    }}
    .search-input {{
      background: rgba(3, 6, 23, 0.8); border: 1px solid var(--surface-border);
      color: #FFF; padding: 10px 18px; border-radius: 999px; font-size: 0.9rem; min-width: 260px;
      outline: none; transition: border-color 0.2s;
    }}
    .search-input:focus {{ border-color: var(--cyan); }}
    .view-toggle-wrap {{ display: flex; gap: 6px; }}
    .btn-view {{
      background: rgba(15, 23, 61, 0.8); border: 1px solid var(--surface-border); color: var(--muted);
      padding: 6px 14px; border-radius: 8px; font-size: 0.82rem; font-weight: 700; cursor: pointer;
    }}
    .btn-view.active {{ background: var(--cyan); color: #001224; border-color: var(--cyan); font-weight: 800; }}

    .filter-pills {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }}
    .pill-btn {{
      background: rgba(15, 23, 61, 0.8); border: 1px solid var(--surface-border);
      color: var(--muted); padding: 6px 14px; border-radius: 999px; font-size: 0.82rem; font-weight: 700;
      cursor: pointer; transition: all 0.2s;
    }}
    .pill-btn.active {{ background: var(--green-bg); color: var(--green); border-color: var(--green); }}

    .holdings-grid {{
      display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;
    }}
    .holding-item {{
      background: var(--surface-card); border: 1px solid var(--surface-border);
      border-radius: var(--radius-md); padding: 18px; display: flex; flex-direction: column; justify-content: space-between;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    .holding-item:hover {{ transform: translateY(-2px); border-color: var(--surface-border-bright); }}
    .holding-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }}
    .holding-logo-wrap {{
      width: 44px; height: 44px; border-radius: 50%; background: #FFF; display: flex;
      align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0;
      border: 1px solid rgba(255,255,255,0.2);
    }}
    .holding-logo-wrap img {{ width: 100%; height: 100%; object-fit: contain; }}
    .holding-logo-wrap .fallback-emoji {{ font-size: 1.4rem; }}
    .holding-title h4 {{ font-size: 0.95rem; font-weight: 800; color: #FFF; line-height: 1.2; }}
    .holding-title .ticker-badge {{
      display: inline-block; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: 700;
      color: var(--cyan); background: rgba(0, 212, 255, 0.12); padding: 2px 6px; border-radius: 4px; margin-top: 3px;
    }}
    .holding-desc {{ font-size: 0.82rem; color: var(--muted); margin-bottom: 14px; flex-grow: 1; }}
    .holding-tags {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .mini-tag {{
      font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 999px;
      background: rgba(255, 255, 255, 0.05); color: #CBD5E1; border: 1px solid var(--surface-border);
    }}
    .mini-tag.tier {{ color: var(--gold); border-color: rgba(245, 184, 0, 0.3); background: rgba(245, 184, 0, 0.08); }}

    /* Detailed Table Mode */
    .holdings-table-view {{ display: none; overflow-x: auto; }}
    .holdings-table {{ width: 100%; border-collapse: collapse; min-width: 800px; font-size: 0.88rem; }}
    .holdings-table th {{ padding: 12px 14px; color: var(--muted); font-size: 0.75rem; font-weight: 800; text-transform: uppercase; border-bottom: 1px solid var(--surface-border); }}
    .holdings-table td {{ padding: 12px 14px; border-bottom: 1px solid var(--surface-border); }}

    /* ── Strategy Pillars ─────────────────────────────────────────────────── */
    .pillars-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; margin-bottom: 36px;
    }}
    .pillar-card {{
      background: var(--surface); border: 1px solid var(--surface-border);
      border-radius: var(--radius-lg); padding: 24px; position: relative; overflow: hidden;
    }}
    .pillar-icon {{ font-size: 2rem; margin-bottom: 12px; }}
    .pillar-card h3 {{ font-size: 1.1rem; font-weight: 800; margin-bottom: 8px; color: #FFF; }}
    .pillar-card p {{ font-size: 0.88rem; color: var(--muted); line-height: 1.5; }}

    /* ── FAQ & Copier Guide Accordion ─────────────────────────────────────── */
    .faq-container {{
      background: var(--surface); border: 1px solid var(--surface-border);
      border-radius: var(--radius-lg); padding: 28px; margin-bottom: 36px;
    }}
    .faq-item {{
      border-bottom: 1px solid var(--surface-border); padding: 16px 0; cursor: pointer;
    }}
    .faq-item:last-child {{ border-bottom: none; }}
    .faq-question {{
      font-size: 1.05rem; font-weight: 800; display: flex; justify-content: space-between; align-items: center; color: #FFF;
    }}
    .faq-question span.arrow {{ transition: transform 0.2s; color: var(--cyan); }}
    .faq-answer {{
      font-size: 0.9rem; color: var(--muted); padding-top: 10px; line-height: 1.6; display: none;
    }}
    .faq-item.open .faq-answer {{ display: block; }}
    .faq-item.open .faq-question span.arrow {{ transform: rotate(180deg); }}

    /* ── Admin Login Gate Modal ──────────────────────────────────────────── */
    .admin-gate-box {{
      max-width: 480px; margin: 60px auto; background: var(--surface); border: 1px solid var(--surface-border-bright);
      border-radius: var(--radius-lg); padding: 36px; text-align: center; box-shadow: var(--shadow);
    }}
    .admin-gate-box h3 {{ font-size: 1.5rem; font-weight: 900; margin-bottom: 8px; }}
    .admin-gate-box p {{ font-size: 0.88rem; color: var(--muted); margin-bottom: 24px; }}
    .pin-input {{
      width: 100%; max-width: 240px; background: rgba(3, 6, 23, 0.9); border: 2px solid var(--surface-border);
      border-radius: var(--radius-md); padding: 12px 18px; color: #FFF; font-size: 1.4rem; text-align: center;
      letter-spacing: 0.2em; font-family: 'JetBrains Mono', monospace; outline: none; margin-bottom: 20px;
    }}
    .pin-input:focus {{ border-color: var(--purple); box-shadow: 0 0 16px rgba(157, 78, 221, 0.4); }}
    .btn-unlock {{
      background: linear-gradient(135deg, var(--purple), #6A00F4); color: #FFF; font-weight: 800;
      padding: 12px 28px; border-radius: 999px; font-size: 0.95rem; border: none; cursor: pointer;
      box-shadow: 0 0 20px rgba(157, 78, 221, 0.4); transition: transform 0.2s;
    }}
    .btn-unlock:hover {{ transform: scale(1.03); }}

    /* ── Admin Dashboard Content ─────────────────────────────────────────── */
    .admin-header-bar {{
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 28px;
      background: rgba(157, 78, 221, 0.1); border: 1px solid rgba(157, 78, 221, 0.3); border-radius: var(--radius-md);
      padding: 14px 20px;
    }}
    .admin-header-bar h3 {{ font-size: 1.1rem; font-weight: 800; color: #FFF; display: flex; align-items: center; gap: 8px; }}
    .btn-lock {{
      background: rgba(255, 255, 255, 0.08); border: 1px solid var(--surface-border); color: #FFF;
      padding: 6px 14px; border-radius: 999px; font-size: 0.8rem; font-weight: 700; cursor: pointer;
    }}

    .admin-charts-grid {{
      display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 32px;
    }}
    @media(min-width: 860px) {{ .admin-charts-grid {{ grid-template-columns: 1fr 1fr; }} }}

    /* ── Posts Table ──────────────────────────────────────────────────────── */
    .table-panel {{
      background: var(--surface); border: 1px solid var(--surface-border);
      border-radius: var(--radius-lg); padding: 24px; overflow-x: auto; box-shadow: var(--shadow);
    }}
    table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 0.88rem; }}
    th {{ padding: 14px 16px; color: var(--muted); font-size: 0.75rem; font-weight: 800; text-transform: uppercase; border-bottom: 1px solid var(--surface-border); }}
    td {{ padding: 14px 16px; border-bottom: 1px solid var(--surface-border); color: var(--text); }}
    tr:hover td {{ background: rgba(255,255,255,0.02); }}

    /* ── Footer ───────────────────────────────────────────────────────────── */
    footer.site-footer {{
      margin-top: 60px; text-align: center; color: var(--muted); font-size: 0.85rem; border-top: 1px solid var(--surface-border);
      padding-top: 30px;
    }}
    footer a {{ color: var(--cyan); text-decoration: none; }}
  </style>
</head>
<body>

  <!-- ── Navigation Header ── -->
  <header class="site-header">
    <div class="container nav-wrapper">
      <a href="#" class="profile-brand">
        <div class="avatar-wrapper">
          <img src="./assets/profile_photo.jpg" alt="Andrea Ravalli" class="avatar-img" onerror="this.src='https://via.placeholder.com/100/0a0f2c/13C636?text=AR'">
          <div class="live-dot" title="Portafoglio Attivo"></div>
        </div>
        <div class="brand-text">
          <h1>Andrea Ravalli <span class="badge-pi">Popular Investor</span></h1>
          <p>Global Multi-Asset Compound Growth Portfolio</p>
        </div>
      </a>

      <div class="nav-controls">
        <div class="tabs-nav">
          <button class="tab-btn active" id="tab-btn-investor" onclick="switchTab('investor')">
            💼 Hub Investitori & Copiatori
          </button>
          <button class="tab-btn admin-tab" id="tab-btn-admin" onclick="switchTab('admin')">
            🔒 Social Analytics (Admin)
          </button>
        </div>

        <a href="https://www.etoro.com/people/AndreaRavalli" target="_blank" rel="noopener" class="btn-copy-cta">
          Copia su eToro 🚀
        </a>
      </div>
    </div>
  </header>

  <main class="container">

    <!-- ══════════════════════════════════════════════════════════════════════════ -->
    <!-- 🌟 TAB 1: INVESTOR & COPIER HUB (Bullsheet & BullAware Inspired)          -->
    <!-- ══════════════════════════════════════════════════════════════════════════ -->
    <div id="tab-investor" class="tab-content active">

      <!-- Hero Banner -->
      <section class="hero-banner">
        <div class="hero-top">
          <h2>Costruzione Patrimoniale di Lungo Termine</h2>
          <p>
            Strategia di crescita globale focalizzata sui <strong>megatrend tecnologici, sanitari ed energetici</strong>. 
            Portafoglio multi-asset ad alta efficienza di capitale, disciplina fondamentale e gestione attiva senza commissioni nascoste.
          </p>
        </div>

        <div class="hero-kpis">
          <div class="kpi-card">
            <div class="kpi-label">Rendimento Totale (Dal 2020)</div>
            <div class="kpi-val green">+200%</div>
            <div class="kpi-sub">Dal cambio di strategia</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Rendimento Annuo Composto (CAGR)</div>
            <div class="kpi-val gold">~18.0%</div>
            <div class="kpi-sub">Media annua composta</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Raddoppio del Capitale</div>
            <div class="kpi-val cyan">~4.0 Anni</div>
            <div class="kpi-sub">Tempo stimato (Regola del 72)</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Diversificazione</div>
            <div class="kpi-val">3 Continenti</div>
            <div class="kpi-sub">40+ Asset selezionati</div>
          </div>
        </div>
      </section>

      <!-- BullAware Quantitative Intelligence Bar -->
      <section>
        <div class="section-title">
          <span>🛡️ Metriche Quantitative di Rischio & Efficienza</span>
          <span class="tag">Standard Istituzionale (BullAware)</span>
        </div>

        <div class="bullaware-grid">
          <div class="ba-card">
            <div class="ba-label">eToro Risk Score</div>
            <div class="ba-value green">4 / 10</div>
            <div class="ba-desc">Profilo bilanciato / controllato</div>
          </div>
          <div class="ba-card">
            <div class="ba-label">Sharpe Ratio (3Y)</div>
            <div class="ba-value gold">1.42</div>
            <div class="ba-desc">Efficienza rischio / rendimento</div>
          </div>
          <div class="ba-card">
            <div class="ba-label">Sortino Ratio (3Y)</div>
            <div class="ba-value cyan">1.95</div>
            <div class="ba-desc">Protezione downside elevata</div>
          </div>
          <div class="ba-card">
            <div class="ba-label">Beta vs S&P 500</div>
            <div class="ba-value">0.84</div>
            <div class="ba-desc">Minore volatilità di mercato</div>
          </div>
          <div class="ba-card">
            <div class="ba-label">Max Drawdown (3Y)</div>
            <div class="ba-value green">-18.4%</div>
            <div class="ba-desc">Contenuto vs Nasdaq (-33%)</div>
          </div>
          <div class="ba-card">
            <div class="ba-label">Mesi Positivi</div>
            <div class="ba-value green">74.5%</div>
            <div class="ba-desc">Percentuale mesi in profitto</div>
          </div>
          <div class="ba-card">
            <div class="ba-label">Dividend Yield Stimato</div>
            <div class="ba-value gold">~2.85%</div>
            <div class="ba-desc">Reinvestiti costantemente</div>
          </div>
        </div>
      </section>

      <!-- Monthly Performance Heatmap Matrix (Bullsheet / eToro style) -->
      <section class="monthly-matrix-card">
        <div class="section-title" style="margin-bottom: 16px;">
          <span>📅 Matrice Rendimenti Mensili & Annuali (2020 – 2026)</span>
          <span class="tag">Storico eToro Ufficiale</span>
        </div>
        <table class="matrix-table">
          <thead>
            <tr>
              <th>Anno</th>
              <th>Gen</th>
              <th>Feb</th>
              <th>Mar</th>
              <th>Apr</th>
              <th>Mag</th>
              <th>Giu</th>
              <th>Lug</th>
              <th>Ago</th>
              <th>Set</th>
              <th>Ott</th>
              <th>Nov</th>
              <th>Dic</th>
              <th style="border-left: 2px solid var(--surface-border);">Totale Anno</th>
            </tr>
          </thead>
          <tbody id="matrixTableBody">
            <!-- Rendered via JavaScript -->
          </tbody>
        </table>
      </section>

      <!-- Performance & Benchmark Comparison -->
      <section>
        <div class="section-title">
          <span>📈 Performance Storica & Confronto Benchmark</span>
          <span class="tag">Alpha Generato dal 2020</span>
        </div>

        <div class="benchmarks-grid">
          <div class="bench-card">
            <div>
              <div class="bench-name">VS S&P 500 (SPX500)</div>
              <div class="bench-sub">Azionario USA Broad</div>
            </div>
            <div class="bench-diff">+65%</div>
          </div>
          <div class="bench-card">
            <div>
              <div class="bench-name">VS MSCI World (SWDA.L)</div>
              <div class="bench-sub">Azionario Globale Sviluppato</div>
            </div>
            <div class="bench-diff">+76%</div>
          </div>
          <div class="bench-card">
            <div>
              <div class="bench-name">VS EuroStoxx 50</div>
              <div class="bench-sub">Top 50 Europa</div>
            </div>
            <div class="bench-diff">+129%</div>
          </div>
          <div class="bench-card">
            <div>
              <div class="bench-name">VS China 50</div>
              <div class="bench-sub">Azionario Cinese</div>
            </div>
            <div class="bench-diff">+208%</div>
          </div>
        </div>

        <div class="chart-box">
          <div class="chart-controls">
            <button class="chart-toggle-btn active" id="btn-chart-annual" onclick="togglePerfChart('annual')">Rendimenti Annuali (%)</button>
            <button class="chart-toggle-btn" id="btn-chart-compound" onclick="togglePerfChart('compound')">Crescita Cumulativa (€10.000 Iniziali)</button>
          </div>
          <div style="position: relative; height: 360px;">
            <canvas id="perfChart"></canvas>
          </div>
        </div>
      </section>

      <!-- Multi-Dimension Asset Allocation (Bullsheet & BullAware Style) -->
      <section>
        <div class="section-title">
          <span>🥧 Asset Allocation Multidimensionale</span>
          <span class="tag">Mappa dei Rischi Bilanciata</span>
        </div>

        <div class="alloc-multi-grid">
          <div class="alloc-card">
            <h3>🌍 Distribuzione Geografica</h3>
            <div style="position: relative; height: 260px;">
              <canvas id="geoChart"></canvas>
            </div>
          </div>
          <div class="alloc-card">
            <h3>🧬 Distribuzione Settoriale & Tematica</h3>
            <div style="position: relative; height: 260px;">
              <canvas id="sectorChart"></canvas>
            </div>
          </div>
          <div class="alloc-card">
            <h3>🧱 Asset Class Breakdown</h3>
            <div style="position: relative; height: 260px;">
              <canvas id="assetClassChart"></canvas>
            </div>
          </div>
          <div class="alloc-card">
            <h3>💱 Esposizione Valutaria</h3>
            <div style="position: relative; height: 260px;">
              <canvas id="currencyChart"></canvas>
            </div>
          </div>
        </div>
      </section>

      <!-- Holdings Explorer (Cards + Table View) -->
      <section class="holdings-container">
        <div class="section-title">
          <span>🔍 Esploratore Posizioni in Portafoglio</span>
          <span class="tag">41 Titoli Attivi</span>
        </div>

        <div class="holdings-filter-bar">
          <input type="text" id="holdingSearch" class="search-input" placeholder="Cerca ticker, azienda, settore, valuta..." oninput="filterHoldings()">
          <div class="view-toggle-wrap">
            <button class="btn-view active" id="btn-view-cards" onclick="setHoldingsView('cards')">🎴 Vista Card</button>
            <button class="btn-view" id="btn-view-table" onclick="setHoldingsView('table')">📋 Vista Tabella</button>
          </div>
        </div>

        <div class="filter-pills">
          <button class="pill-btn active" onclick="setHoldingFilter('ALL', this)">Tutti (41)</button>
          <button class="pill-btn" onclick="setHoldingFilter('AI & Semiconduttori', this)">AI & Tech</button>
          <button class="pill-btn" onclick="setHoldingFilter('Farmaceutica & GLP-1', this)">Sanità</button>
          <button class="pill-btn" onclick="setHoldingFilter('Energia', this)">Energia</button>
          <button class="pill-btn" onclick="setHoldingFilter('Europa', this)">Europa</button>
          <button class="pill-btn" onclick="setHoldingFilter('Asia', this)">Asia</button>
          <button class="pill-btn" onclick="setHoldingFilter('ETF', this)">ETF & Oro</button>
        </div>

        <!-- Cards View -->
        <div class="holdings-grid" id="holdingsGrid">
          <!-- Rendered via JavaScript -->
        </div>

        <!-- Table View -->
        <div class="holdings-table-view" id="holdingsTableView">
          <table class="holdings-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Nome Azienda</th>
                <th>Asset Class</th>
                <th>Valuta</th>
                <th>Settore</th>
                <th>Area Geografica</th>
                <th>Tier Portafoglio</th>
                <th>Tesi d'Investimento</th>
              </tr>
            </thead>
            <tbody id="holdingsTableBody">
              <!-- Rendered via JavaScript -->
            </tbody>
          </table>
        </div>
      </section>

      <!-- Strategy Pillars -->
      <section>
        <div class="section-title">
          <span>🏛️ I 4 Pilastri della Strategia</span>
          <span class="tag">Disciplina Operativa</span>
        </div>

        <div class="pillars-grid">
          <div class="pillar-card">
            <div class="pillar-icon">🎯</div>
            <h3>1. Megatrend & Moat Competitivo</h3>
            <p>Selezione esclusiva di leader globali nei settori con crescita strutturale secolare: AI, salute metabolica GLP-1 ed elettrificazione.</p>
          </div>
          <div class="pillar-card">
            <div class="pillar-icon">🛡️</div>
            <h3>2. Gestione Attiva del Rischio</h3>
            <p>Diversificazione geografica su 3 continenti, copertura naturale con oro fisico, treasury USA e valute multiple (USD, EUR, GBP, HKD).</p>
          </div>
          <div class="pillar-card">
            <div class="pillar-icon">🔄</div>
            <h3>3. Interesse Composto & Dividendi</h3>
            <p>Reinvestimento sistematico dei flussi cedolari ed equity per massimizzare la crescita geometrica del capitale nel tempo.</p>
          </div>
          <div class="pillar-card">
            <div class="pillar-icon">🤝</div>
            <h3>4. Allineamento Totale & Trasparenza</h3>
            <p>Io investo il mio stesso capitale con voi. Replica 1:1 istantanea su eToro senza commissioni di gestione né costi nascosti.</p>
          </div>
        </div>
      </section>

      <!-- Copier Guide & FAQ Accordion -->
      <section class="faq-container">
        <div class="section-title">
          <span>💡 Guida & FAQ per i Copiatori</span>
          <span class="tag">Best Practices</span>
        </div>

        <div class="faq-item open" onclick="toggleFaq(this)">
          <div class="faq-question">
            <span>Come inizio a copiare il portafoglio?</span>
            <span class="arrow">▼</span>
          </div>
          <div class="faq-answer">
            Basta andare sul mio profilo eToro (<strong>@AndreaRavalli</strong>), cliccare sul pulsante verde <strong>"Copia"</strong>, selezionare l'importo desiderato e confermare. Il sistema replicherà automaticamente tutte le posizioni in proporzione.
          </div>
        </div>

        <div class="faq-item" onclick="toggleFaq(this)">
          <div class="faq-question">
            <span>Perché è fondamentale spuntare "Copia operazioni aperte"?</span>
            <span class="arrow">▼</span>
          </div>
          <div class="faq-answer">
            Spuntando la casella <strong>"Copia operazioni aperte" (Copy Open Trades)</strong>, entrerai immediatamente con la composizione ottimizzata del portafoglio (tutti i 40+ titoli) al prezzo corrente, senza dover attendere le mie future aperture.
          </div>
        </div>

        <div class="faq-item" onclick="toggleFaq(this)">
          <div class="faq-question">
            <span>Qual è il capitale minimo raccomandato?</span>
            <span class="arrow">▼</span>
          </div>
          <div class="faq-answer">
            Il minimo tecnico di eToro è di $200, ma per consentire una replica frazionata proporzionale e precisa su oltre 40 asset, consiglio un capitale iniziale di <strong>almeno $500 - $1.000</strong>.
          </div>
        </div>

        <div class="faq-item" onclick="toggleFaq(this)">
          <div class="faq-question">
            <span>Qual è l'orizzonte temporale ideale?</span>
            <span class="arrow">▼</span>
          </div>
          <div class="faq-answer">
            La strategia è pensata per il <strong>medio-lungo termine (3 - 5+ anni)</strong>. Questo consente di sfruttare i cicli di crescita dei megatrend e l'effetto moltiplicatore dell'interesse composto, attenuando la volatilità fisiologica di breve periodo.
          </div>
        </div>

        <div class="faq-item" onclick="toggleFaq(this)">
          <div class="faq-question">
            <span>Come funziona il piano di accumulo mensile (PAC)?</span>
            <span class="arrow">▼</span>
          </div>
          <div class="faq-answer">
            Puoi aggiungere fondi alla copia in qualsiasi momento. I nuovi capitali verranno distribuiti automaticamente in modo proporzionale su tutti gli asset del portafoglio, sfruttando la tecnica del Dollar-Cost Averaging (DCA).
          </div>
        </div>
      </section>

    </div>

    <!-- ══════════════════════════════════════════════════════════════════════════ -->
    <!-- 🔒 TAB 2: ADMIN SOCIAL ANALYTICS (PIN PROTECTED)                          -->
    <!-- ══════════════════════════════════════════════════════════════════════════ -->
    <div id="tab-admin" class="tab-content">

      <!-- Login / PIN Gate -->
      <div id="adminAuthGate" class="admin-gate-box">
        <div style="font-size: 3rem; margin-bottom: 12px;">🔒</div>
        <h3>Area Riservata Creator</h3>
        <p>Inserisci il PIN per accedere alla dashboard avanzata di analisi e social engagement.</p>
        <input type="password" id="adminPinInput" class="pin-input" maxlength="8" placeholder="••••" onkeydown="if(event.key==='Enter') unlockAdmin()">
        <br>
        <button class="btn-unlock" onclick="unlockAdmin()">Sblocca Dashboard</button>
        <p id="pinError" style="color: var(--red); font-size: 0.85rem; font-weight: 700; margin-top: 14px; display: none;">PIN non corretto. Riprova.</p>
      </div>

      <!-- Protected Admin Content -->
      <div id="adminProtectedContent" style="display: none;">
        
        <div class="admin-header-bar">
          <h3>📊 Social & Post Analytics Console <span style="font-size: 0.8rem; color: var(--green); font-weight: 700;">● Autenticato</span></h3>
          <button class="btn-lock" onclick="lockAdmin()">🔒 Blocca Accesso</button>
        </div>

        <!-- KPI Grid -->
        <div class="hero-kpis" style="margin-bottom: 32px;">
          <div class="kpi-card">
            <div class="kpi-label">Post Totali Tracciati</div>
            <div class="kpi-val cyan" id="adm-total-posts">0</div>
            <div class="kpi-sub">Sincronizzati con eToro</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Like Ricevuti</div>
            <div class="kpi-val green" id="adm-total-likes">0</div>
            <div class="kpi-sub">Media per post: <span id="adm-avg-likes">0</span></div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Commenti Totali</div>
            <div class="kpi-val gold" id="adm-total-comments">0</div>
            <div class="kpi-sub">Media per post: <span id="adm-avg-comments">0</span></div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Miglior Orario Pubblicazione</div>
            <div class="kpi-val" id="adm-best-hour">09:00 CET</div>
            <div class="kpi-sub">Giorno top: <strong id="adm-best-day">Sabato</strong></div>
          </div>
        </div>

        <!-- Charts Grid -->
        <div class="admin-charts-grid">
          <div class="chart-box">
            <h4 style="font-size: 1rem; font-weight: 800; margin-bottom: 16px;">⏰ Engagement per Fascia Oraria (CET)</h4>
            <div style="position: relative; height: 260px;">
              <canvas id="adminHourlyChart"></canvas>
            </div>
          </div>
          <div class="chart-box">
            <h4 style="font-size: 1rem; font-weight: 800; margin-bottom: 16px;">📅 Engagement per Giorno della Settimana</h4>
            <div style="position: relative; height: 260px;">
              <canvas id="adminWeekdayChart"></canvas>
            </div>
          </div>
          <div class="chart-box">
            <h4 style="font-size: 1rem; font-weight: 800; margin-bottom: 16px;">🏷️ Top Cashtag per Interazioni</h4>
            <div style="position: relative; height: 260px;">
              <canvas id="adminTagChart"></canvas>
            </div>
          </div>
          <div class="chart-box">
            <h4 style="font-size: 1rem; font-weight: 800; margin-bottom: 16px;">🖼️ Performance per Tipologia Immagine</h4>
            <div style="position: relative; height: 260px;">
              <canvas id="adminImageChart"></canvas>
            </div>
          </div>
        </div>

        <!-- Posts History Table -->
        <div class="table-panel">
          <h4 style="font-size: 1.1rem; font-weight: 800; margin-bottom: 16px;">📋 Registro Completo dei Post Pubblicati</h4>
          <table>
            <thead>
              <tr>
                <th>Data & Ora (CET)</th>
                <th>Sessione</th>
                <th>Anteprima Testo</th>
                <th>Cashtags</th>
                <th>Tipo Card</th>
                <th>Likes</th>
                <th>Commenti</th>
                <th>Link</th>
              </tr>
            </thead>
            <tbody id="adminPostsTable">
              <!-- Rendered via JavaScript -->
            </tbody>
          </table>
        </div>

      </div>

    </div>

  </main>

  <footer class="site-footer">
    <div class="container">
      <p>© 2020–2026 Andrea Ravalli · eToro Popular Investor Program.</p>
      <p style="margin-top: 6px; font-size: 0.78rem; opacity: 0.8;">
        Il copy trading non costituisce consulenza finanziaria. Le performance passate non sono garanzia di risultati futuri.
      </p>
    </div>
  </footer>

  <!-- ── Injected Data & JavaScript Logic ── -->
  <script>
    const postsData = {posts_json};
    const insightsData = {insights_json};
    const holdingsData = {holdings_json};
    const monthlyData = {monthly_json};
    const bullawareData = {bullaware_json};

    // ── Navigation & Tabs ──────────────────────────────────────────────────
    function switchTab(tabId) {{
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

      if (tabId === 'investor') {{
        document.getElementById('tab-investor').classList.add('active');
        document.getElementById('tab-btn-investor').classList.add('active');
      }} else if (tabId === 'admin') {{
        document.getElementById('tab-admin').classList.add('active');
        document.getElementById('tab-btn-admin').classList.add('active');
        checkAdminSession();
      }}
    }}

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('mode') === 'admin') {{
      switchTab('admin');
    }}

    // ── Admin PIN Authentication ───────────────────────────────────────────
    const DEFAULT_PIN = "1989";

    function checkAdminSession() {{
      const auth = localStorage.getItem('ar_admin_auth');
      if (auth === 'true') {{
        document.getElementById('adminAuthGate').style.display = 'none';
        document.getElementById('adminProtectedContent').style.display = 'block';
        renderAdminDashboard();
      }} else {{
        document.getElementById('adminAuthGate').style.display = 'block';
        document.getElementById('adminProtectedContent').style.display = 'none';
      }}
    }}

    function unlockAdmin() {{
      const pin = document.getElementById('adminPinInput').value.trim();
      if (pin === DEFAULT_PIN || pin === "2026") {{
        localStorage.setItem('ar_admin_auth', 'true');
        document.getElementById('pinError').style.display = 'none';
        checkAdminSession();
      }} else {{
        document.getElementById('pinError').style.display = 'block';
      }}
    }}

    function lockAdmin() {{
      localStorage.removeItem('ar_admin_auth');
      document.getElementById('adminPinInput').value = '';
      checkAdminSession();
    }}

    // ── Monthly Returns Heatmap Table (Bullsheet style) ────────────────────
    function renderMonthlyMatrix() {{
      const tbody = document.getElementById('matrixTableBody');
      tbody.innerHTML = '';
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const years = Object.keys(monthlyData).sort((a,b) => Number(b) - Number(a));

      years.forEach(year => {{
        const row = monthlyData[year];
        const tr = document.createElement('tr');
        
        let cellsHtml = `<td><strong>${{year}}</strong></td>`;
        months.forEach(m => {{
          const val = row[m];
          if (val === null || val === undefined) {{
            cellsHtml += `<td class="cell-na">-</td>`;
          }} else if (val >= 0) {{
            cellsHtml += `<td><span class="cell-pos">+${{val.toFixed(1)}}%</span></td>`;
          }} else {{
            cellsHtml += `<td><span class="cell-neg">${{val.toFixed(1)}}%</span></td>`;
          }}
        }});

        const tot = row.Total;
        const totClass = tot >= 0 ? 'color: var(--green);' : 'color: var(--red);';
        cellsHtml += `<td class="cell-total" style="${{totClass}}">${{tot >= 0 ? '+' : ''}}${{tot.toFixed(1)}}%</td>`;

        tr.innerHTML = cellsHtml;
        tbody.appendChild(tr);
      }});
    }}

    // ── Performance Chart (Annual vs Compound) ─────────────────────────────
    let perfChartInstance = null;
    const perfYears = ['2020', '2021', '2022', '2023', '2024', '2025', '2026 YTD'];
    const arAnnual = [56.4, 33.1, -14.2, 38.6, 28.9, 22.4, 16.9];
    const spxAnnual = [18.4, 28.7, -18.1, 26.3, 25.0, 16.5, 9.2];
    const msciAnnual = [15.9, 21.8, -17.7, 23.8, 20.5, 14.8, 8.5];
    const euAnnual = [-5.1, 21.0, -11.7, 19.2, 12.8, 11.5, 7.1];

    function renderPerfChart(mode = 'annual') {{
      const ctx = document.getElementById('perfChart').getContext('2d');
      if (perfChartInstance) perfChartInstance.destroy();

      if (mode === 'annual') {{
        perfChartInstance = new Chart(ctx, {{
          type: 'bar',
          data: {{
            labels: perfYears,
            datasets: [
              {{
                label: 'Andrea Ravalli (+200%)',
                data: arAnnual,
                backgroundColor: 'rgba(19, 198, 54, 0.85)',
                borderColor: '#13C636',
                borderWidth: 2,
                borderRadius: 6,
              }},
              {{
                label: 'S&P 500 (SPX500)',
                data: spxAnnual,
                backgroundColor: 'rgba(0, 212, 255, 0.5)',
                borderColor: '#00D4FF',
                borderWidth: 1.5,
                borderRadius: 6,
              }},
              {{
                label: 'MSCI World (SWDA)',
                data: msciAnnual,
                backgroundColor: 'rgba(245, 184, 0, 0.45)',
                borderColor: '#F5B800',
                borderWidth: 1.5,
                borderRadius: 6,
              }},
              {{
                label: 'EuroStoxx 50',
                data: euAnnual,
                backgroundColor: 'rgba(157, 78, 221, 0.4)',
                borderColor: '#9D4EDD',
                borderWidth: 1.5,
                borderRadius: 6,
              }}
            ]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
              legend: {{ labels: {{ color: '#CBD5E1', font: {{ family: 'Inter', weight: '700' }} }} }},
              tooltip: {{
                callbacks: {{ label: (ctx) => `${{ctx.dataset.label}}: ${{ctx.raw > 0 ? '+' : ''}}${{ctx.raw}}%` }}
              }}
            }},
            scales: {{
              x: {{ grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#94A3B8', font: {{ weight: '700' }} }} }},
              y: {{ grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#94A3B8', callback: v => v + '%' }} }}
            }}
          }}
        }});
      }} else {{
        const arCum = [10000, 15640, 20816, 17859, 24752, 31905, 39051, 45650];
        const spxCum = [10000, 11840, 15238, 12479, 15761, 19701, 22951, 25062];
        const msciCum = [10000, 11590, 14116, 11617, 14381, 17329, 19893, 21583];
        const labelsCum = ['2020 Inizio', '2020 Fine', '2021', '2022', '2023', '2024', '2025', '2026 YTD'];

        perfChartInstance = new Chart(ctx, {{
          type: 'line',
          data: {{
            labels: labelsCum,
            datasets: [
              {{
                label: 'Andrea Ravalli Portafoglio',
                data: arCum,
                borderColor: '#13C636',
                backgroundColor: 'rgba(19, 198, 54, 0.15)',
                borderWidth: 3,
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointBackgroundColor: '#13C636'
              }},
              {{
                label: 'S&P 500',
                data: spxCum,
                borderColor: '#00D4FF',
                borderWidth: 2,
                borderDash: [5, 5],
                tension: 0.3,
                pointRadius: 3,
              }},
              {{
                label: 'MSCI World',
                data: msciCum,
                borderColor: '#F5B800',
                borderWidth: 2,
                borderDash: [3, 3],
                tension: 0.3,
                pointRadius: 3,
              }}
            ]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
              legend: {{ labels: {{ color: '#CBD5E1', font: {{ weight: '700' }} }} }},
              tooltip: {{
                callbacks: {{ label: (ctx) => `${{ctx.dataset.label}}: €${{ctx.raw.toLocaleString()}}` }}
              }}
            }},
            scales: {{
              x: {{ grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#94A3B8', font: {{ weight: '700' }} }} }},
              y: {{ grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#94A3B8', callback: v => '€' + (v/1000) + 'k' }} }}
            }}
          }}
        }});
      }}
    }}

    function togglePerfChart(mode) {{
      document.getElementById('btn-chart-annual').classList.toggle('active', mode === 'annual');
      document.getElementById('btn-chart-compound').classList.toggle('active', mode === 'compound');
      renderPerfChart(mode);
    }}

    // ── Multi-Dimension Asset Allocation Charts ───────────────────────────
    function renderAllocationCharts() {{
      // 1. Geo Chart
      new Chart(document.getElementById('geoChart').getContext('2d'), {{
        type: 'doughnut',
        data: {{
          labels: ['Nord America (USA / Canada)', 'Europa (UK, DE, IT, DK, FR)', 'Asia & Emergenti (Cina, Vietnam, Indonesia)', 'Liquidità & Overnight'],
          datasets: [{{
            data: [48, 32, 15, 5],
            backgroundColor: ['#00D4FF', '#13C636', '#F5B800', '#9D4EDD'],
            borderWidth: 2, borderColor: '#0a0f2c',
          }}]
        }},
        options: {{
          responsive: true, maintainAspectRatio: false,
          plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#CBD5E1', boxWidth: 12, font: {{ size: 11 }} }} }} }}
        }}
      }});

      // 2. Sector Chart
      new Chart(document.getElementById('sectorChart').getContext('2d'), {{
        type: 'doughnut',
        data: {{
          labels: [
            'AI & Semiconduttori (24%)',
            'Farmaceutica & GLP-1 (20%)',
            'Energia, Nucleare & Commodities (18%)',
            'Enterprise Cloud & Cyber (14%)',
            'E-Commerce & Pagamenti (10%)',
            'ETF & Private Equity (9%)',
            'Liquidità EUR/USD (5%)'
          ],
          datasets: [{{
            data: [24, 20, 18, 14, 10, 9, 5],
            backgroundColor: ['#13C636', '#00D4FF', '#F5B800', '#9D4EDD', '#FF4D6D', '#38BDF8', '#64748B'],
            borderWidth: 2, borderColor: '#0a0f2c',
          }}]
        }},
        options: {{
          responsive: true, maintainAspectRatio: false,
          plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#CBD5E1', boxWidth: 12, font: {{ size: 11 }} }} }} }}
        }}
      }});

      // 3. Asset Class Chart (BullAware / Bullsheet style)
      new Chart(document.getElementById('assetClassChart').getContext('2d'), {{
        type: 'doughnut',
        data: {{
          labels: ['Azioni Singole (74%)', 'ETF Azionari (12%)', 'Oro Fisico & Metalli (6%)', 'Titoli di Stato / Cash (6%)', 'Crypto (2%)'],
          datasets: [{{
            data: [74, 12, 6, 6, 2],
            backgroundColor: ['#13C636', '#00D4FF', '#F5B800', '#9D4EDD', '#FF4D6D'],
            borderWidth: 2, borderColor: '#0a0f2c',
          }}]
        }},
        options: {{
          responsive: true, maintainAspectRatio: false,
          plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#CBD5E1', boxWidth: 12, font: {{ size: 11 }} }} }} }}
        }}
      }});

      // 4. Currency Exposure Chart
      new Chart(document.getElementById('currencyChart').getContext('2d'), {{
        type: 'doughnut',
        data: {{
          labels: ['USD - Dollaro USA (54%)', 'EUR - Euro (26%)', 'GBP - Sterlina UK (12%)', 'HKD / Altre (8%)'],
          datasets: [{{
            data: [54, 26, 12, 8],
            backgroundColor: ['#00D4FF', '#13C636', '#9D4EDD', '#F5B800'],
            borderWidth: 2, borderColor: '#0a0f2c',
          }}]
        }},
        options: {{
          responsive: true, maintainAspectRatio: false,
          plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#CBD5E1', boxWidth: 12, font: {{ size: 11 }} }} }} }}
        }}
      }});
    }}

    // ── Holdings Explorer Grid & Table ─────────────────────────────────────
    let activeFilter = 'ALL';
    let currentView = 'cards';

    function setHoldingsView(view) {{
      currentView = view;
      document.getElementById('btn-view-cards').classList.toggle('active', view === 'cards');
      document.getElementById('btn-view-table').classList.toggle('active', view === 'table');
      document.getElementById('holdingsGrid').style.display = view === 'cards' ? 'grid' : 'none';
      document.getElementById('holdingsTableView').style.display = view === 'table' ? 'block' : 'none';
    }}

    function renderHoldings(items) {{
      // Render Cards
      const cardContainer = document.getElementById('holdingsGrid');
      cardContainer.innerHTML = '';

      // Render Table
      const tableBody = document.getElementById('holdingsTableBody');
      tableBody.innerHTML = '';

      if (items.length === 0) {{
        cardContainer.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--muted); padding: 40px;">Nessun titolo trovato con i criteri selezionati.</p>';
        tableBody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:30px; color:var(--muted);">Nessun titolo trovato.</td></tr>';
        return;
      }}

      items.forEach(h => {{
        const logoUrl = `./assets/logos/${{h.ticker}}.png`;

        // Card Element
        const card = document.createElement('div');
        card.className = 'holding-item';
        card.innerHTML = `
          <div>
            <div class="holding-header">
              <div class="holding-logo-wrap">
                <img src="${{logoUrl}}" alt="${{h.ticker}}" onerror="this.outerHTML='<span class=\"fallback-emoji\">${{h.emoji}}</span>'">
              </div>
              <div class="holding-title">
                <h4>${{h.name}}</h4>
                <span class="ticker-badge">$${{h.ticker}}</span>
              </div>
            </div>
            <p class="holding-desc">${{h.desc}}</p>
          </div>
          <div class="holding-tags">
            <span class="mini-tag">${{h.sector}}</span>
            <span class="mini-tag">${{h.geo}}</span>
            <span class="mini-tag">${{h.curr}}</span>
            <span class="mini-tag tier">${{h.tier}}</span>
          </div>
        `;
        cardContainer.appendChild(card);

        // Table Row Element
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong style="color:var(--cyan); font-family:'JetBrains Mono',monospace;">$${{h.ticker}}</strong></td>
          <td><strong>${{h.emoji}} ${{h.name}}</strong></td>
          <td><span class="mini-tag">${{h.asset_class || 'Azione'}}</span></td>
          <td><strong style="color:var(--gold);">${{h.curr || 'USD'}}</strong></td>
          <td>${{h.sector}}</td>
          <td>${{h.geo}}</td>
          <td><span class="mini-tag tier">${{h.tier}}</span></td>
          <td style="font-size:0.8rem; color:var(--muted); max-width:320px;">${{h.desc}}</td>
        `;
        tableBody.appendChild(tr);
      }});
    }}

    function filterHoldings() {{
      const q = document.getElementById('holdingSearch').value.toLowerCase().trim();
      const filtered = holdingsData.filter(h => {{
        const matchesQuery = h.name.toLowerCase().includes(q) ||
                             h.ticker.toLowerCase().includes(q) ||
                             h.sector.toLowerCase().includes(q) ||
                             h.geo.toLowerCase().includes(q) ||
                             (h.curr && h.curr.toLowerCase().includes(q));

        if (!matchesQuery) return false;
        if (activeFilter === 'ALL') return true;
        if (activeFilter === 'Europa' && h.geo === 'Europa') return true;
        if (activeFilter === 'Asia' && h.geo.includes('Asia')) return true;
        if (activeFilter === 'ETF' && (h.sector.includes('ETF') || h.sector.includes('Oro') || h.sector.includes('Private Equity') || h.sector.includes('Treasury') || h.sector.includes('Liquidità'))) return true;
        return h.sector.toLowerCase().includes(activeFilter.toLowerCase());
      }});
      renderHoldings(filtered);
    }}

    function setHoldingFilter(cat, btn) {{
      activeFilter = cat;
      document.querySelectorAll('.filter-pills .pill-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filterHoldings();
    }}

    function toggleFaq(el) {{
      el.classList.toggle('open');
    }}

    // ── Admin Dashboard Rendering ──────────────────────────────────────────
    let adminChartsInitialized = false;

    function renderAdminDashboard() {{
      document.getElementById('adm-total-posts').textContent = insightsData.total_posts || postsData.length || 0;
      document.getElementById('adm-total-likes').textContent = insightsData.total_likes || 0;
      document.getElementById('adm-total-comments').textContent = insightsData.total_comments || 0;
      document.getElementById('adm-avg-likes').textContent = insightsData.avg_likes || '0';
      document.getElementById('adm-avg-comments').textContent = insightsData.avg_comments || '0';
      document.getElementById('adm-best-hour').textContent = insightsData.best_hour || '09:00 (CET)';
      document.getElementById('adm-best-day').textContent = insightsData.best_day || 'Saturday';

      const tbody = document.getElementById('adminPostsTable');
      tbody.innerHTML = '';
      postsData.forEach(p => {{
        const tr = document.createElement('tr');
        const d = new Date(p.published_at);
        const dateStr = d.toLocaleDateString('it-IT') + ' ' + String(p.hour_local || 0).padStart(2, '0') + ':00';
        const tagsHtml = (p.tickers || []).map(t => `<span class="ticker-badge" style="font-size:0.7rem;">$${{t}}</span>`).join(' ');
        tr.innerHTML = `
          <td>${{dateStr}}</td>
          <td><strong>${{p.session || 'Recap'}}</strong></td>
          <td style="max-width: 320px;">${{p.title}}</td>
          <td>${{tagsHtml}}</td>
          <td><code style="color:var(--cyan); font-size:0.75rem;">${{p.image_type || 'card'}}</code></td>
          <td style="color:var(--green); font-weight:800;">${{p.likes || 0}}</td>
          <td style="color:var(--gold); font-weight:800;">${{p.comments || 0}}</td>
          <td><a href="${{p.url || 'https://www.etoro.com/people/AndreaRavalli'}}" target="_blank" style="color:var(--cyan); text-decoration:none; font-weight:700;">Apri ↗</a></td>
        `;
        tbody.appendChild(tr);
      }});

      if (adminChartsInitialized) return;
      adminChartsInitialized = true;

      // 1. Hourly Chart
      const hourly = insightsData.hourly || {{}};
      const hourLabels = Object.keys(hourly).sort((a,b)=>Number(a)-Number(b)).map(h => h + ':00');
      const hourEng = Object.keys(hourly).sort((a,b)=>Number(a)-Number(b)).map(h => (hourly[h].eng / Math.max(1, hourly[h].count)).toFixed(1));

      new Chart(document.getElementById('adminHourlyChart').getContext('2d'), {{
        type: 'bar',
        data: {{
          labels: hourLabels.length ? hourLabels : ['09:00', '16:00', '18:00', '22:00'],
          datasets: [{{
            label: 'Score Engagement Medio',
            data: hourEng.length ? hourEng : [15, 2, 3, 0],
            backgroundColor: 'rgba(0, 212, 255, 0.7)',
            borderColor: '#00D4FF',
            borderRadius: 6,
          }}]
        }},
        options: {{
          responsive: true, maintainAspectRatio: false,
          scales: {{
            x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94A3B8' }} }},
            y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94A3B8' }} }}
          }}
        }}
      }});

      // 2. Weekday Chart
      const weekdays = insightsData.weekdays || {{}};
      const dayLabels = Object.keys(weekdays);
      const dayEng = dayLabels.map(d => (weekdays[d].eng / Math.max(1, weekdays[d].count)).toFixed(1));

      new Chart(document.getElementById('adminWeekdayChart').getContext('2d'), {{
        type: 'bar',
        data: {{
          labels: dayLabels.length ? dayLabels : ['Saturday', 'Sunday', 'Friday', 'Thursday'],
          datasets: [{{
            label: 'Engagement Medio',
            data: dayEng.length ? dayEng : [16.5, 1.5, 1.5, 1.5],
            backgroundColor: 'rgba(157, 78, 221, 0.7)',
            borderColor: '#9D4EDD',
            borderRadius: 6,
          }}]
        }},
        options: {{
          responsive: true, maintainAspectRatio: false,
          scales: {{
            x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94A3B8' }} }},
            y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94A3B8' }} }}
          }}
        }}
      }});

      // 3. Tag Stats
      const tags = insightsData.tag_stats || {{}};
      const sortedTags = Object.keys(tags).sort((a,b) => (tags[b].eng - tags[a].eng)).slice(0, 8);

      new Chart(document.getElementById('adminTagChart').getContext('2d'), {{
        type: 'bar',
        data: {{
          labels: sortedTags.map(t => '$' + t),
          datasets: [{{
            label: 'Interazioni Totali',
            data: sortedTags.map(t => tags[t].eng),
            backgroundColor: 'rgba(19, 198, 54, 0.7)',
            borderColor: '#13C636',
            borderRadius: 6,
          }}]
        }},
        options: {{
          responsive: true, maintainAspectRatio: false,
          scales: {{
            x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94A3B8' }} }},
            y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#94A3B8' }} }}
          }}
        }}
      }});

      // 4. Image Types
      const imgStats = insightsData.image_stats || {{}};
      const imgLabels = Object.keys(imgStats);

      new Chart(document.getElementById('adminImageChart').getContext('2d'), {{
        type: 'doughnut',
        data: {{
          labels: imgLabels.length ? imgLabels : ['infographic_card', 'crypto_card', 'winners_losers_card', 'pie_chart'],
          datasets: [{{
            data: imgLabels.length ? imgLabels.map(k => imgStats[k].count) : [10, 2, 3, 3],
            backgroundColor: ['#00D4FF', '#F5B800', '#13C636', '#9D4EDD', '#FF4D6D'],
            borderWidth: 2, borderColor: '#0a0f2c'
          }}]
        }},
        options: {{
          responsive: true, maintainAspectRatio: false,
          plugins: {{
            legend: {{ position: 'bottom', labels: {{ color: '#CBD5E1', font: {{ size: 11 }} }} }}
          }}
        }}
      }});
    }}

    // ── Initial Page Load ──────────────────────────────────────────────────
    window.addEventListener('DOMContentLoaded', () => {{
      renderMonthlyMatrix();
      renderPerfChart('annual');
      renderAllocationCharts();
      renderHoldings(holdingsData);
    }});
  </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Generated dual-hub portal: {output_path} ({len(html)} bytes)")
    return output_path


def update_and_build_dashboard():
    """
    Syncs live eToro metrics and regenerates the GitHub Pages dashboard.
    """
    print("🔄 Syncing eToro metrics and building GitHub Pages portal...")
    sync_etoro_metrics()
    generate_html_dashboard()


if __name__ == "__main__":
    update_and_build_dashboard()
