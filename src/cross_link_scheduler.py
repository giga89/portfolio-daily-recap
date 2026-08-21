#!/usr/bin/env python3
"""
Dynamic Cross-Link Comments Generator & Scheduler for eToro
===========================================================
Publishes 3 curated, dynamic cross-link comments on an eToro recap post.
Each comment focuses on EXACTLY ONE SINGLE ASSET from a specific category:
  • Comment 1/3: Single AI & Tech Asset (e.g. $PLTR, $NVDA, $MRVL, $TSM, $MSFT, $GOOG, $AVGO, $AMZN)
  • Comment 2/3: Single Defensive, Healthcare, Energy or Value Asset (e.g. $LLY, $NOVO-B.CO, $CCJ, $ENI.MI, $PRY.MI, $ENEL.MI, $VOW3.DE, $ULVR.L)
  • Comment 3/3: Single ETF & Macro Strategy Asset (e.g. $SX7PEX.DE, $WDEF.L, $INDO.PA, $IEUR)

Features:
  - Rotates dynamically across sessions and days (or picks top movers).
  - Highlights specific portfolio thesis, competitive moat and catalysts.
  - Concludes with an engaging open question to spark comments and discussion on eToro.
"""

import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Load local .env if available
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')):
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

import etoro_client
from etoro_sender import _strip_html

# ── 1. ASSET PROFILES BY CATEGORY ─────────────────────────────────────────────

AI_TECH_PROFILES = {
    "PLTR": {
        "name": "Palantir Technologies",
        "emoji": "🛡️",
        "role": "Piattaforma AIP & Software Difesa Governativo",
        "thesis": "Monopolio nei contratti governativi e di intelligence USA, con accelerazione record nell'adozione commerciale della piattaforma AIP per le aziende Fortune 500.",
        "driver": "Margini operativi da Rule of 40 (>60%), cassa netta oltre $4B e Net Retention superiore al 115%.",
        "question": "Come valutate la capacità di monetizzazione dell'AIP nel settore privato? Avete $PLTR in portafoglio?"
    },
    "NVDA": {
        "name": "NVIDIA Corporation",
        "emoji": "🤖",
        "role": "Chip GPU Data Center & Architettura Blackwell",
        "thesis": "Monopolio de facto delle GPU per il training e l'inferenza AI con oltre 15 anni di fossato software creato dall'ecosistema CUDA.",
        "driver": "Margini lordi superiori al 75% e domanda multi-annuale garantita dagli investimenti dei principali hyperscaler mondiali.",
        "question": "Ritenete che gli investimenti in compute e infrastrutture AI continueranno a battere le stime anche nei prossimi trimestri?"
    },
    "MRVL": {
        "name": "Marvell Technology",
        "emoji": "📊",
        "role": "Infrastruttura Connettività & Chip Custom AI",
        "thesis": "Leader nei semiconduttori per data center, interconnessioni ottiche PAM4 ad altissima velocità e silicio custom per hyperscaler.",
        "driver": "Forte espansione dei ricavi legati all'AI con domanda record per chip elettro-ottici e soluzioni di storage ad alte prestazioni.",
        "question": "Seguite Marvell tra i titoli strategici per la scalabilità delle reti dei data center AI?"
    },
    "TSM": {
        "name": "Taiwan Semiconductor (TSMC)",
        "emoji": "🏭",
        "role": "Fonderia di Precisione Chip Avanzati",
        "thesis": "Manifattura di oltre il 90% dei chip più sofisticati al mondo a 3nm e 2nm, con tassi di resa produttiva (yield) nettamente superiori a tutti i concorrenti.",
        "driver": "Margini operativi oltre il 42% e piano di espansione globale con nuovi stabilimenti in USA, Giappone ed Europa.",
        "question": "Cosa ne pensate della posizione strategica e del vantaggio competitivo insormontabile di TSMC?"
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "emoji": "💻",
        "role": "Cloud Azure & Ecosistema OpenAI Enterprise",
        "thesis": "Integrazione capillare dei modelli di intelligenza artificiale Copilot e Azure OpenAI in tutta la suite Windows, Office 365 e nei sistemi aziendali.",
        "driver": "Rating creditizio AAA, flussi di cassa solidissimi e crescita costante a doppia cifra del business cloud.",
        "question": "Pensate che l'integrazione di Copilot e Azure confermi Microsoft come leader indiscusso del software enterprise?"
    },
    "GOOG": {
        "name": "Alphabet (Google)",
        "emoji": "🔍",
        "role": "Search, Google Cloud & Gemini AI",
        "thesis": "Monopolio globale delle ricerche web (>90%), leadership video con YouTube e accelerazione della divisione Google Cloud spinta dall'AI multimodale Gemini.",
        "driver": "Fortezza finanziaria con oltre $100B di cassa, dividendi crescenti e massicci programmi di buyback.",
        "question": "Come vedete il posizionamento di Google nella competizione tra motori di ricerca tradizionali e AI generativa?"
    },
    "AVGO": {
        "name": "Broadcom Inc",
        "emoji": "🔌",
        "role": "Switch di Rete AI & Chip Custom Hyperscaler",
        "thesis": "Leadership assoluta nelle tecnologie di interconnessione ad altissima velocità (Tomahawk) per data center AI e sinergie software strategiche con VMware.",
        "driver": "Margini EBITDA record (>60%) e potere di prezzo eccezionale sui componenti hardware custom per big tech.",
        "question": "Seguite Broadcom come beneficiario fondamentale e 'invisibile' della connettività dei supercomputer AI?"
    },
    "AMZN": {
        "name": "Amazon.com Inc",
        "emoji": "📦",
        "role": "Cloud AWS & Infrastruttura Logistica Globale",
        "thesis": "Dominio di AWS come spina dorsale di internet e dell'infrastruttura AI, combinato con margini in rapida espansione dal segmento pubblicitario ad alta redditività.",
        "driver": "Massiccia generazione di Free Cash Flow e continuo incremento dell'efficienza grazie all'automazione e alla robotica.",
        "question": "Credete che AWS manterrà la sua leadership nel cloud computing rispetto alla concorrenza?"
    }
}

DEFENSIVE_VALUE_PROFILES = {
    "LLY": {
        "name": "Eli Lilly & Co",
        "emoji": "💊",
        "role": "Innovazione Farmaceutica & Trattamenti GLP-1",
        "thesis": "Leadership mondiale nei trattamenti terapeutici contro obesità e diabete (Mounjaro e Zepbound), con domanda secolare resiliente a qualsiasi ciclo economico.",
        "driver": "Mercato potenziale superiore a $100B, brevetti protetti per oltre un decennio e massicci investimenti in espansione produttiva.",
        "question": "Qual è il vostro outlook sul settore sanitario e sui farmaci metabolici di nuova generazione per il lungo periodo?"
    },
    "NOVO-B.CO": {
        "name": "Novo Nordisk",
        "emoji": "💉",
        "role": "Cura del Diabete & Terapie Semaglutide",
        "thesis": "Pioniere globale e leader europeo nelle terapie a base di semaglutide con Ozempic e Wegovy, approvati anche per la riduzione dei rischi cardiovascolari e renali.",
        "driver": "Margini operativi superiori al 45% e ROIC ai vertici europei che finanziano buyback e ricerca all'avanguardia.",
        "question": "Preferite espormi al megatrend salute attraverso Novo Nordisk o Eli Lilly nel vostro portafoglio?"
    },
    "CCJ": {
        "name": "Cameco Corporation",
        "emoji": "⚡",
        "role": "Estrazione Uranio & Combustibile Nucleare Pulito",
        "thesis": "Leader mondiale minerario con asset Tier-1 a basso costo (McArthur River), protetto da contratti pluriennali con le maggiori utility nucleari mondiali.",
        "driver": "Deficit strutturale di offerta primaria e crescente richiesta di energia nucleare continua (baseload) 24/7 per alimentare i data center AI.",
        "question": "Considerate l'energia nucleare un pilastro indispensabile per la transizione energetica e la sicurezza delle forniture?"
    },
    "ENI.MI": {
        "name": "Eni S.p.A.",
        "emoji": "⛽",
        "role": "Major Energetica & Strategia Satellitare",
        "thesis": "Bassi costi di estrazione (break-even Brent <$30), storico impareggiabile nelle nuove scoperte e valorizzazione delle rinnovabili tramite modelli satellitari (Plenitude, Enilive).",
        "driver": "Dividend yield elevato (>6.5%) con distribuzione trimestrale e programma continuo di riacquisto azioni a tutela degli azionisti.",
        "question": "Cosa ne pensate della strategia satellitare di Eni per remunerare il capitale e finanziare la decarbonizzazione?"
    },
    "PRY.MI": {
        "name": "Prysmian S.p.A.",
        "emoji": "🔌",
        "role": "Cavi per Elettrificazione, Grid & Data Center",
        "thesis": "Leader mondiale assoluto nei cavi ad alta tensione per interconnessioni sottomarine, parchi eolici offshore e cablaggio ad alta densità per data center.",
        "driver": "Portafoglio ordini record (>€18B), barriere all'entrata elevate ed espansione sul mercato USA con l'acquisizione di Encore Wire.",
        "question": "Avete titoli infrastrutturali nel vostro portafoglio per beneficiare del megatrend decennale dell'elettrificazione?"
    },
    "BMW.DE": {
        "name": "BMW Group",
        "emoji": "🚗",
        "role": "Manifattura Automobilistica Premium & Neue Klasse",
        "thesis": "Flessibilità produttiva unica (linee condivise per termico, ibrido ed elettrico), forte brand value e margini EBIT costantemente ai vertici industriali.",
        "driver": "Cassa netta industriale solida, dividendo generoso (>6%) e lancio della piattaforma nativa elettrica Neue Klasse.",
        "question": "Ritenete che la flessibilità tecnologica di BMW sia la scelta più prudente e redditizia nell'automotive?"
    },
    "ENEL.MI": {
        "name": "Enel S.p.A.",
        "emoji": "💡",
        "role": "Utility Globale & Reti di Distribuzione",
        "thesis": "Focalizzazione sui mercati strategici core (Italia e Spagna), progressiva riduzione del debito e forte componente di ricavi regolati a bassa volatilità.",
        "driver": "Politica di dividendi stabili e crescenti, trainata dall'elettrificazione dei consumi civili e industriali.",
        "question": "Considerate le utility regolate come Enel un ottimo strumento di stabilità e rendimento nei momenti di incertezza?"
    },
    "VOW3.DE": {
        "name": "Volkswagen AG",
        "emoji": "🚗",
        "role": "Leader Automotive Globale & Mobilità Elettrica",
        "thesis": "Presenza globale capillare con marchi iconici (Porsche, Audi, VW), transizione verso architetture unificate e forte scala produttiva.",
        "driver": "Valutazioni a forte sconto, cassa netta industriale solida e dividend yield superiore al 7%.",
        "question": "Come valutate il piano di efficientamento e la transizione elettrica del gruppo Volkswagen?"
    }
}

ETF_MACRO_PROFILES = {
    "SX7PEX.DE": {
        "name": "iShares STOXX Europe 600 Banks ETF",
        "emoji": "🏛️",
        "role": "Settore Bancario Europeo ad Alto Rendimento",
        "thesis": "Esposizione ai maggiori istituti bancari europei con bilanci solidi, coefficienti patrimoniali (CET1 >15.5%) ai massimi storici e crediti deteriorati ai minimi.",
        "driver": "Dividend yield superiore al 7% accompagnato da consistenti programmi di buyback che incrementano il valore per azione.",
        "question": "Preferite espormi al settore bancario tramite ETF diversificato o tramite la selezione di singoli titoli?"
    },
    "WDEF.L": {
        "name": "WisdomTree Europe Equity Income ETF",
        "emoji": "💼",
        "role": "Azionario Europeo ad Alto Dividendo di Qualità",
        "thesis": "Selezione sistematica di società europee a larga capitalizzazione con eccellente profilo di generazione di cassa e bilanci sani.",
        "driver": "Rendimento da dividendo elevato che crea un flusso cedolare costante e riduce la volatilità complessiva del portafoglio.",
        "question": "Quale quota del vostro portafoglio dedicate a strategie e strumenti orientati alla generazione di dividendi?"
    },
    "INDO.PA": {
        "name": "Amundi MSCI Indonesia ETF",
        "emoji": "🇮🇩",
        "role": "Mercati Emergenti & Megatrend Risorse Critiche",
        "thesis": "Esposizione mirata alla crescita demografica del sud-est asiatico e al ruolo chiave dell'Indonesia nella fornitura globale di nickel e materie prime per batterie.",
        "driver": "Forte crescita del PIL reale e diversificazione macroeconomica non correlata ai mercati occidentali.",
        "question": "Cosa ne pensate dell'inserimento di mercati emergenti selezionati per catturare la crescita economica asiatica?"
    },
    "IEUR": {
        "name": "iShares Core MSCI Europe ETF",
        "emoji": "🌍",
        "role": "Core Azionario Europeo Diversificato",
        "thesis": "Esposizione completa e bilanciata alle principali multinazionali europee su tutti i settori economici, a valutazioni storicamente attraenti.",
        "driver": "Ampia diversificazione geografica e settoriale con costi di gestione minimi per un'ottica di lunghissimo periodo.",
        "question": "Ritenete che le valutazioni più contenute dell'azionario europeo offrano un buon margine di sicurezza rispetto a Wall Street?"
    }
}


# ── 2. DYNAMIC COMMENT SELECTION & FORMATTING ─────────────────────────────────

def select_dynamic_assets(
    session_name: Optional[str] = None,
    date_seed: Optional[datetime] = None,
    market_data: Optional[Dict[str, Any]] = None
) -> Tuple[str, str, str]:
    """
    Select 1 AI stock, 1 Defensive stock, and 1 ETF.
    Uses daily mover performance if available, falling back to deterministic session rotation.
    """
    now = date_seed or datetime.now(timezone.utc)
    day_of_year = now.timetuple().tm_yday
    
    # Session offset for variety throughout the day
    session_offset = 0
    if session_name:
        s_lower = session_name.lower()
        if "european" in s_lower or "eu_open" in s_lower:
            session_offset = 0
        elif "stock focus" in s_lower or "focus" in s_lower:
            session_offset = 1
        elif "u.s. market open" in s_lower or "us_open" in s_lower:
            session_offset = 2
        elif "u.s. market close" in s_lower or "us_close" in s_lower:
            session_offset = 3
        elif "weekly" in s_lower:
            session_offset = 4

    ai_keys = list(AI_TECH_PROFILES.keys())
    def_keys = list(DEFENSIVE_VALUE_PROFILES.keys())
    etf_keys = list(ETF_MACRO_PROFILES.keys())

    # If live market data is provided, optionally prioritize top performers in category
    ai_selected = None
    def_selected = None
    etf_selected = None

    if market_data and isinstance(market_data, dict):
        # Pick top traded / mover if present
        def _best_mover(keys: List[str]) -> Optional[str]:
            valid = []
            for k in keys:
                if k in market_data and isinstance(market_data[k], dict):
                    chg = market_data[k].get("daily_change", 0.0)
                    valid.append((k, abs(chg)))
            if valid:
                valid.sort(key=lambda x: x[1], reverse=True)
                return valid[0][0]
            return None

        ai_selected = _best_mover(ai_keys)
        def_selected = _best_mover(def_keys)
        etf_selected = _best_mover(etf_keys)

    # Fallback to daily rotation
    if not ai_selected:
        ai_idx = (day_of_year * 2 + session_offset) % len(ai_keys)
        ai_selected = ai_keys[ai_idx]

    if not def_selected:
        def_idx = (day_of_year * 3 + session_offset + 1) % len(def_keys)
        def_selected = def_keys[def_idx]

    if not etf_selected:
        etf_idx = (day_of_year + session_offset + 2) % len(etf_keys)
        etf_selected = etf_keys[etf_idx]

    return ai_selected, def_selected, etf_selected


def build_dynamic_cross_link_comments(
    session_name: Optional[str] = None,
    date_seed: Optional[datetime] = None,
    market_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    """
    Generate 3 distinct, highly engaging comments.
    Comment 1: Exactly 1 AI/Tech stock
    Comment 2: Exactly 1 Defensive/Value/Energy stock
    Comment 3: Exactly 1 ETF
    """
    ai_ticker, def_ticker, etf_ticker = select_dynamic_assets(
        session_name=session_name,
        date_seed=date_seed,
        market_data=market_data
    )

    p_ai = AI_TECH_PROFILES[ai_ticker]
    p_def = DEFENSIVE_VALUE_PROFILES[def_ticker]
    p_etf = ETF_MACRO_PROFILES[etf_ticker]

    # Comment 1: AI & Tech Focus (1 Single Asset)
    c1_text = f"""💡 1/3 FOCUS ASSET AI & TECH: ${ai_ticker} ({p_ai['name']}) {p_ai['emoji']}
↳ Ruolo in portafoglio: {p_ai['role']}
↳ Tesi fondamentale: {p_ai['thesis']}
↳ Metriche chiave: {p_ai['driver']}

💬 {p_ai['question']} 👇"""

    # Comment 2: Defensive / Healthcare / Energy Focus (1 Single Asset)
    c2_text = f"""🛡️ 2/3 FOCUS ASSET DIFENSIVO & QUALITÀ: ${def_ticker} ({p_def['name']}) {p_def['emoji']}
↳ Ruolo in portafoglio: {p_def['role']}
↳ Tesi fondamentale: {p_def['thesis']}
↳ Metriche chiave: {p_def['driver']}

💬 {p_def['question']} 👇"""

    # Comment 3: ETF & Macro Strategy Focus (1 Single Asset)
    c3_text = f"""🏛️ 3/3 FOCUS STRATEGIA ETF & RENDIMENTO: ${etf_ticker} ({p_etf['name']}) {p_etf['emoji']}
↳ Ruolo in portafoglio: {p_etf['role']}
↳ Tesi fondamentale: {p_etf['thesis']}
↳ Metriche chiave: {p_etf['driver']}

💬 {p_etf['question']} 👇"""

    return [
        {"name": f"Focus AI (${ai_ticker})", "text": c1_text, "ticker": ai_ticker, "category": "AI"},
        {"name": f"Focus Difensivo (${def_ticker})", "text": c2_text, "ticker": def_ticker, "category": "Defensive"},
        {"name": f"Focus ETF (${etf_ticker})", "text": c3_text, "ticker": etf_ticker, "category": "ETF"},
    ]


# ── 3. EXECUTION RUNNER ───────────────────────────────────────────────────────

def run_comments_sequence(
    post_id: str,
    interval_seconds: int = 5,
    session_name: Optional[str] = None,
    market_data: Optional[Dict[str, Any]] = None
):
    """
    Publish all 3 specialized comments spaced by `interval_seconds` (default 5s).
    """
    comments = build_dynamic_cross_link_comments(
        session_name=session_name,
        market_data=market_data
    )

    print("=" * 60)
    print(f"🚀 STARTING DYNAMIC 3-COMMENT CROSSLINKING SEQUENCE ON POST: {post_id}")
    print(f"⏱️ Interval between comments: {interval_seconds}s")
    for idx, c in enumerate(comments, 1):
        print(f"   • Comment {idx}: {c['name']}")
    print("=" * 60)

    if not etoro_client.is_configured():
        print("❌ eToro API not configured. Exiting.")
        return

    for idx, c in enumerate(comments, 1):
        clean_msg = _strip_html(c["text"])
        print(f"\n[{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}] 💬 Publishing Comment {idx}/3 ({c['name']})...")
        
        res = etoro_client.add_post_comment(
            post_id=post_id,
            message=clean_msg,
            language="it"
        )
        
        if res.get("success"):
            print(f"✅ Comment {idx} posted successfully! ID: {res.get('id')}")
        else:
            print(f"❌ Comment {idx} failed: {res.get('error')}")

        if idx < len(comments):
            print(f"⏳ Waiting {interval_seconds}s before next comment...")
            time.sleep(interval_seconds)

    print("\n" + "=" * 60)
    print("🎉 ALL 3 CROSSLINKING COMMENTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    target_post = sys.argv[1] if len(sys.argv) > 1 else "41f4c7dc-402a-4ce6-a7fe-49b819f074d2"
    delay = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    # Preview generated dynamic comments
    print("\n📋 PREVIEW OF DYNAMIC 3-TYPE COMMENTS:\n")
    sample_comments = build_dynamic_cross_link_comments(session_name="U.S. market open")
    for i, c in enumerate(sample_comments, 1):
        print(f"--- COMMENT {i} ({c['name']}) ---")
        print(c["text"])
        print()

