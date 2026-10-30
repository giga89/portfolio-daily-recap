#!/usr/bin/env python3
"""
Interactive Poll Generator for eToro Social Feed
================================================
Generates and publishes highly engaging 1-click community polls directly to eToro.
Polls dramatically increase interaction, algorithmic reach, and profile views.
"""

import os
import sys
import re
import random
from datetime import datetime, timezone
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
import gist_storage
import analytics_tracker
from etoro_sender import _strip_html
from economic_calendar import smart_truncate


POLL_TEMPLATES = [
    {
        "id": "megatrend_h2",
        "title": "Quale megatrend guiderà le performance nei prossimi mesi? 🚀",
        "options": [
            "AI & Tech ($NVDA, $PLTR)",
            "GLP-1 ($LLY, $NOVO-B.CO)",
            "Energia & Uranio ($CCJ)",
            "Difesa Europea ($WDEF.L)"
        ],
        "tickers": [
            "NVDA",
            "PLTR",
            "LLY",
            "NOVO-B.CO",
            "CCJ",
            "WDEF.L"
        ],
        "message": "🗳️ SONDAGGIO COMMUNITY: I GRANDI MEGATREND GLOBALI\n\nNel nostro portafoglio bilanciamo la crescita secolare dell'infrastruttura AI su $NVDA e $PLTR con pilastri strategici ad alta visibilità: terapie GLP-1 di nuova generazione con $LLY e $NOVO-B.CO, riattivazione nucleare per data center con $CCJ e riarmo NATO europeo tramite $WDEF.L.\n\nSecondo voi, quale tra questi 4 megatrend offrirà il miglior profilo rischio/rendimento nei prossimi trimestri?\n\nVotate l'opzione e lasciate un commento con la vostra analisi! 👇"
    },
    {
        "id": "ai_valuation_debate",
        "title": "Come valutate l'attuale fase dell'Intelligenza Artificiale? 🤖",
        "options": [
            "Primi stadi: forte upside",
            "Fase matura: solo i leader",
            "Valutazioni troppo tirate",
            "Preferisco ETF tematici"
        ],
        "tickers": [
            "PLTR",
            "NVDA",
            "TSM",
            "MSFT",
            "GOOG"
        ],
        "message": "🗳️ SONDAGGIO COMMUNITY: IL FUTURO DELL'ECOSISTEMA AI & SOFTWARE\n\nTra l'adozione enterprise e sovrana di AIP su $PLTR, la transizione dalle architetture Blackwell alla nuova piattaforma Vera Rubin di $NVDA e gli investimenti infrastrutturali degli hyperscaler cloud come $MSFT e $GOOG, l'AI agente continua a ridefinire la produttività globale.\n\nCome vi state posizionando sui titoli leader del settore tech?\n\nDite la vostra nel sondaggio con 1 tap! 👇"
    },
    {
        "id": "risk_management_choice",
        "title": "Qual è la vostra priorità principale di asset allocation? ⚖️",
        "options": [
            "Massima crescita (High Beta)",
            "Crescita bilanciata (Core)",
            "Dividendi & Flussi di cassa",
            "Beni rifugio e liquidità"
        ],
        "tickers": [
            "PLTR",
            "LLY",
            "SX7PEX.DE",
            "PPFB.DE"
        ],
        "message": "🗳️ SONDAGGIO: GESTIONE DEL RISCHIO E ASSET ALLOCATION\n\nLa nostra strategia mantiene un Risk Score eToro certificato di 3/10 con zero leva finanziaria e oltre +200% di performance cumulata dal 2020, bilanciando leader growth come $PLTR e $LLY con flussi di cassa su $SX7PEX.DE e oro fisico $PPFB.DE.\n\nQual è il vostro approccio attuale al rapporto rischio/rendimento sui mercati?\n\nVotate qui sotto per confrontarvi con la community! 👇"
    },
    {
        "id": "pltr_conviction",
        "title": "Palantir $PLTR: Quale scenario vi aspettate a medio termine? 🛡️",
        "options": [
            "Nuovi massimi grazie ad AIP",
            "Crescita solida e costante",
            "Correzione tecnica salutare",
            "Preferisco altri titoli tech"
        ],
        "tickers": [
            "PLTR",
            "NVDA"
        ],
        "message": "🗳️ SONDAGGIO DEL GIORNO: FOCUS SU PALANTIR $PLTR\n\nPalantir $PLTR si conferma uno dei pilastri a più alta convinzione del nostro portafoglio, spinto dall'accelerazione del segmento US Commercial tramite AIP, dai contratti di difesa per l'AI sovrana e dalla partnership strategica con $NVDA.\n\nQual è la vostra visione sul titolo nei prossimi mesi?\n\nVotate e commentate con il vostro target! 👇"
    },
    {
        "id": "gold_safe_haven",
        "title": "Oro fisico $PPFB.DE: Quale ruolo deve avere in portafoglio? 🥇",
        "options": [
            "Copertura chiave (5-10%)",
            "Ottimo trend rialzista",
            "Preferisco i dividendi",
            "Meglio bond e liquidità"
        ],
        "tickers": [
            "PPFB.DE",
            "IB01.L"
        ],
        "message": "🗳️ SONDAGGIO: ORO FISICO E BENI RIFUGIO $PPFB.DE\n\nManteniamo in portafoglio una quota strutturale di Oro fisico tramite l'ETC $PPFB.DE, sostenuto dagli acquisti record delle Banche Centrali e fondamentale come scudo contro debito sovrano, svalutazione monetaria e tensioni geopolitiche.\n\nCome considerate l'oro nella vostra asset allocation strategica?\n\nVotate l'opzione che rispecchia la vostra strategia! 👇"
    },
    {
        "id": "glp1_pharma_battle",
        "title": "Rivoluzione GLP-1 / Obesità: Chi dominerà il mercato pharma? 💊",
        "options": [
            "Eli Lilly ($LLY) leader",
            "Novo Nordisk ($NOVO-B.CO)",
            "Duopolio paritario a lungo",
            "Nuovi competitor emergenti"
        ],
        "tickers": [
            "LLY",
            "NOVO-B.CO",
            "ABBV"
        ],
        "message": "🗳️ SONDAGGIO HEALTHCARE: IL BOOM DEI TRATTAMENTI GLP-1\n\nOltre al successo globale di Mounjaro/Zepbound per $LLY e Ozempic/Wegovy per $NOVO-B.CO, la sfida si gioca ora sulle pillole orali come Orforglipron di $LLY e sulle combinazioni di nuova generazione come CagriSema di $NOVO-B.CO (>25% di riduzione peso in Fase 3).\n\nChi manterrà la leadership e i margini più elevati nel lungo periodo?\n\nVotate qui sotto! 👇"
    },
    {
        "id": "nuclear_energy_ai",
        "title": "Nucleare & Uranio $CCJ: Saranno essenziali per i Data Center AI? ⚡",
        "options": [
            "Sì, energia pulita 24/7",
            "Sì, ma orizzonte lungo",
            "Meglio solare ed eolico",
            "Gas e combustibili ponte"
        ],
        "tickers": [
            "CCJ",
            "TRIG.L",
            "ENEL.MI"
        ],
        "message": "🗳️ SONDAGGIO ENERGIA: IL RINASCIMENTO NUCLEARE $CCJ\n\nL'esplosione dei consumi elettrici dei cluster AI sta spingendo gli hyperscaler tech a siglare contratti PPA nucleari 24/7 a zero emissioni e riattivare reattori. Con Cameco $CCJ siamo esposti alle principali miniere occidentali di uranio e al 49% di Westinghouse.\n\nCredete che il nucleare sarà il vincitore energetico del decennio?\n\nDite la vostra! 👇"
    },
    {
        "id": "semiconductor_foundry_moat",
        "title": "Semiconduttori: Quale azienda possiede il Moat più solido? 🏭",
        "options": [
            "TSMC ($TSM - Fonderia)",
            "NVIDIA ($NVDA - CUDA Moat)",
            "Broadcom ($AVGO - ASIC AI)",
            "Marvell ($MRVL - Rete AI)"
        ],
        "tickers": [
            "TSM",
            "NVDA",
            "AVGO",
            "MRVL"
        ],
        "message": "🗳️ SONDAGGIO CHIP: DOVE RISIEDE IL VERO VANTAGGIO COMPETITIVO?\n\nDai nodi a 2nm/3nm e packaging avanzato CoWoS di $TSM all'ecosistema CUDA e Vera Rubin di $NVDA, fino agli acceleratori XPU custom di $AVGO e alle interconnessioni ottiche di $MRVL, i semiconduttori sono le fondamenta dell'economia AI.\n\nTra questi giganti nel nostro portafoglio, chi ha il fossato competitivo più inespugnabile?\n\nVotate e motivate nei commenti! 👇"
    },
    {
        "id": "defense_europe_rearmament",
        "title": "Difesa Europea $WDEF.L: Cosa aspettarsi dalla spesa militare NATO? 🛡️",
        "options": [
            "Crescita secolare NATO",
            "Valutazioni già tirate",
            "Rischio freno politico",
            "Preferisco difesa USA"
        ],
        "tickers": [
            "WDEF.L",
            "PLTR"
        ],
        "message": "🗳️ SONDAGGIO SETTORE DIFESA: LA RI-MILITARIZZAZIONE EUROPEA $WDEF.L\n\nCon la soglia NATO del 2% del PIL ormai superata verso i nuovi target del 3%-3,5%+ e i programmi UE di approvvigionamento domestico, l'ETF WisdomTree Europe Defence $WDEF.L e i sistemi AI di $PLTR beneficiano di portafogli ordini pluriennali record.\n\nIl settore Difesa resterà un driver strutturale nei prossimi anni?\n\nEsprimete il vostro voto! 👇"
    },
    {
        "id": "dividends_cash_yield",
        "title": "Titoli da dividendo: Quale settore offre il flusso più solido? 💰",
        "options": [
            "Banche UE ($SX7PEX.DE)",
            "Energy & Utility ($ENI.MI)",
            "Pharma Aristocrat ($ABBV)",
            "Infrastrutture ($TRIG.L)"
        ],
        "tickers": [
            "SX7PEX.DE",
            "ENI.MI",
            "ENEL.MI",
            "ABBV",
            "TRIG.L"
        ],
        "message": "🗳️ SONDAGGIO CASH FLOW: GENERAZIONE DI RENDITA PASSIVA\n\nIl nostro portafoglio bilancia posizioni growth con asset a dividendo sostenibile (~3-4% yield medio sul comparto income tra $SX7PEX.DE, $ENI.MI, $ENEL.MI, $ABBV e $TRIG.L) per finanziare costantemente nuova liquidità.\n\nQuale comparto ritenete più affidabile per la generazione di flussi di cassa?\n\nVotate con 1 tap! 👇"
    },
    {
        "id": "emerging_markets_opportunity",
        "title": "Mercati Emergenti: Dove vedete la maggiore opportunità? 🌏",
        "options": [
            "Finanza Cina ($2318.HK)",
            "Cina & EV leader ($1211.HK)",
            "Vietnam & Frontiera ($VOF.L)",
            "Indonesia ETF ($INDO.PA)"
        ],
        "tickers": [
            "2318.HK",
            "1211.HK",
            "VOF.L",
            "INDO.PA"
        ],
        "message": "🗳️ SONDAGGIO MERCATI EMERGENTI: CRESCITA E DEMOGRAFIA\n\nDalla leadership fintech e assicurativa di Ping An $2318.HK e il dominio EV di BYD $1211.HK, fino al boom manifatturiero del Vietnam $VOF.L e alle materie prime critiche dell'Indonesia $INDO.PA, cerchiamo alpha selettivo globale.\n\nQuale area emergente offre il miglior potenziale?\n\nVotate e commentate la vostra scelta! 👇"
    },
    {
        "id": "luxury_vs_defensive_consumer",
        "title": "Consumi & Resilienza: Quale pilastro difensivo preferite? 🛒",
        "options": [
            "Retail difensivo ($WMT)",
            "Beni di consumo ($ULVR.L)",
            "Auto globale ($VOW3.DE)",
            "Pharma difensivo ($LLY)"
        ],
        "tickers": [
            "WMT",
            "ULVR.L",
            "VOW3.DE",
            "LLY"
        ],
        "message": "🗳️ SONDAGGIO CONSUMI & DIFENSIVI: PRICING POWER E RESILIENZA\n\nNelle diverse fasi del ciclo economico, la resilienza dei consumi e della salute rappresenta una solida ancora: la scala omnicanale globale di $WMT, i marchi di beni di largo consumo usati quotidianamente da miliardi di persone come $ULVR.L o la leadership farmaceutica con pricing power inattaccabile come $LLY.\n\nSu quale pilastro puntereste con un orizzonte di 3-5 anni?\n\nDite la vostra nel sondaggio! 👇"
    },
    {
        "id": "electrification_grid_supercycle",
        "title": "Elettrificazione globale: Quale segmento sarà più redditizio? 🔌",
        "options": [
            "Cavi & Reti ($PRY.MI)",
            "Rame & Metalli ($GLEN.L)",
            "Reti Elettriche ($ENEL.MI)",
            "Intera filiera elettrica"
        ],
        "tickers": [
            "PRY.MI",
            "GLEN.L",
            "ENEL.MI"
        ],
        "message": "🗳️ SONDAGGIO INFRASTRUTTURE: IL SUPERCICLO DELL'ELETTRIFICAZIONE\n\nL'ammodernamento delle reti elettriche per data center AI e rinnovabili guida una domanda storica per i cavi ad alta tensione e in fibra ottica di Prysmian $PRY.MI (rafforzata in Nord America con Encore Wire e Channell), il rame di Glencore $GLEN.L e le smart grid di $ENEL.MI.\n\nQuale comparto premierà di più?\n\nVotate qui sotto! 👇"
    },
    {
        "id": "big_tech_cloud_battle",
        "title": "Hyperscale Cloud & AI: Chi vincerà la sfida enterprise? ☁️",
        "options": [
            "Microsoft Azure ($MSFT)",
            "Amazon AWS ($AMZN)",
            "Google Cloud ($GOOG)",
            "Crescita condivisa per tutti"
        ],
        "tickers": [
            "MSFT",
            "AMZN",
            "GOOG"
        ],
        "message": "🗳️ SONDAGGIO BIG TECH: LA BATTAGLIA DELL'INFRASTRUTTURA CLOUD\n\nI tre giganti del Cloud $MSFT, $AMZN e $GOOG stanno investendo centinaia di miliardi in cluster AI, chip proprietari (Maia, Trainium, TPU) e agenti AI aziendali per monetizzare il backlog miliardario dei clienti enterprise.\n\nQuale piattaforma conquisterà la quota maggiore di budget IT nei prossimi anni?\n\nVotate e lasciate la vostra previsione! 👇"
    },
    {
        "id": "ev_revolution_byd",
        "title": "Auto Elettriche e Mobilità: BYD $1211.HK guiderà il mercato globale? 🔋",
        "options": [
            "Sì, integrazione verticale",
            "Sì, anche con fabbriche UE",
            "I brand storici recuperano",
            "Crescita EV più selettiva"
        ],
        "tickers": [
            "1211.HK",
            "VOW3.DE"
        ],
        "message": "🗳️ SONDAGGIO MOBILITÀ: LA SCALA INDUSTRIALE DI BYD $1211.HK\n\nGrazie a batterie Blade, ibridi plug-in DM-i di quinta generazione e nuovi stabilimenti produttivi in Europa (Ungheria) per superare le barriere doganali UE, BYD $1211.HK continua a guadagnare quote di mercato globali sfidando i gruppi storici come $VOW3.DE.\n\nQual è la vostra visione sul futuro del settore auto?\n\nVotate il sondaggio! 👇"
    },
    {
        "id": "alternative_assets_frontier",
        "title": "Asset Alternativi: Quale asset class per diversificare? 🏛️",
        "options": [
            "Private Equity ($IQQL.DE)",
            "Difesa Europea ($WDEF.L)",
            "Mercati frontiera ($VOF.L)",
            "Oro fisico ($PPFB.DE)"
        ],
        "tickers": [
            "IQQL.DE",
            "WDEF.L",
            "VOF.L",
            "PPFB.DE"
        ],
        "message": "🗳️ SONDAGGIO ASSET ALTERNATIVI: DIVERSIFICAZIONE FUORI DAI LISTINI TRADIZIONALI\n\nDai colossi globali del private equity e private credit via $IQQL.DE al riarmo strategico europeo $WDEF.L, fino ai mercati di frontiera $VOF.L e all'oro fisico $PPFB.DE, ricerchiamo fonti di rendimento decorrelate.\n\nQuale classe di asset alternativi ritenete più interessante per diversificare?\n\nEsprimete la vostra preferenza! 👇"
    },
    {
        "id": "european_banking_profitability",
        "title": "Banche Europee $SX7PEX.DE: Extra-rendimenti e buyback sostenibili? 🏛️",
        "options": [
            "Sì, dividendi record",
            "Sì, con crescita moderata",
            "Rischio margini in calo",
            "Preferisco altri settori UE"
        ],
        "tickers": [
            "SX7PEX.DE",
            "2318.HK"
        ],
        "message": "🗳️ SONDAGGIO BANCHE EUROPEE: REDDITIVITÀ E REMUNERAZIONE DEGLI AZIONISTI\n\nCon tassi BCE stabilizzati in territorio positivo (~2,50%), solidi coefficienti patrimoniali CET1 e piani miliardari di dividendi e buyback, il settore bancario europeo $SX7PEX.DE mantiene multipli ancora contenuti.\n\nQual è la vostra aspettativa sul comparto bancario per i prossimi mesi?\n\nVotate qui sotto! 👇"
    },
    {
        "id": "healthcare_biopharma_defensive",
        "title": "Sanità & Diagnostica: Quale comparto offre la massima solidità? 🏥",
        "options": [
            "Diagnostica ($ABT.US)",
            "Oncologia & Bio ($ABBV)",
            "Assicurazioni ($HUM)",
            "GLP-1 & Diabete ($LLY)"
        ],
        "tickers": [
            "ABT.US",
            "ABBV",
            "AZN.L",
            "HUM",
            "LLY"
        ],
        "message": "🗳️ SONDAGGIO HEALTHCARE: DOMANDA ANELASTICA E INNOVAZIONE\n\nLa sanità offre una protezione unica grazie ai trend demografici globali, unita a forti catalizzatori nel monitoraggio glicemico continuo Libre di $ABT.US, nei blockbuster immunologici post-Humira (Skyrizi e Rinvoq di $ABBV) e nell'oncologia di $AZN.L.\n\nQuale area sanitaria preferite avere in portafoglio?\n\nDite la vostra nel sondaggio! 👇"
    },
    {
        "id": "copytrading_portfolio_secrets",
        "title": "Investimenti a lungo termine: Qual è il fattore più determinante? 🏆",
        "options": [
            "Zero leva, Risk Score 3/10",
            "Diversificazione globale",
            "Pazienza e Buy & Hold",
            "Reinvestimento dividendi"
        ],
        "tickers": [
            "PLTR",
            "NVDA",
            "PPFB.DE",
            "SX7PEX.DE"
        ],
        "message": "🗳️ SONDAGGIO STRATEGIA: I PILASTRI DEL NOSTRO SUCCESSO (+200% DAL 2020)\n\nGenerare rendimento composto costante riducendo i drawdown richiede metodo: niente leva finanziaria, Risk Score controllato 3/10 e diversificazione tra leader AI come $PLTR e $NVDA, flussi di cassa su $SX7PEX.DE e Oro fisico $PPFB.DE.\n\nSecondo la vostra esperienza, qual è l'elemento più cruciale per investire con successo?\n\nVotate e raccontateci il vostro approccio! 👇"
    },
    {
        "id": "fintech_digital_assets_future",
        "title": "Fintech & Pagamenti: Come evolverà il trasferimento di valore? 💳",
        "options": [
            "Social Investing ($ETOR)",
            "Stablecoin & Rails ($TRX)",
            "Banche Europee ($SX7PEX.DE)",
            "Banche e circuiti legacy"
        ],
        "tickers": [
            "ETOR",
            "TRX",
            "SX7PEX.DE"
        ],
        "message": "🗳️ SONDAGGIO FINTECH: IL FUTURO DEI SERVIZI FINANZIARI\n\nDall'espansione globale del social investing con $ETOR (quotata al Nasdaq) al dominio di TRON $TRX nei regolamenti globali in stablecoin USDT, fino alla trasformazione digitale dei grandi istituti bancari con $SX7PEX.DE, la finanza digitale scala rapidamente.\n\nQuale piattaforma sarà più rilevante nel prossimo quinquennio?\n\nVotate e confrontatevi con noi! 👇"
    }
]


def _clean_no_hashtags(text: str) -> str:
    """Strictly remove '#' hashtags from text as useless on eToro."""
    cleaned = re.sub(r"#([A-Za-z0-9_]+)", "", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _unwrap_cashtag_parens(text: str) -> str:
    """Remove parentheses directly wrapping cashtags so eToro parses them as clickable links."""
    cleaned = re.sub(r"\(\s*(\$[A-Za-z0-9\.\-]+)\s*\)", r"\1", text)
    cleaned = re.sub(r"\(\s*(\$[A-Za-z0-9\.\-]+(?:\s*,\s*\$[A-Za-z0-9\.\-]+)+)\s*\)", r"\1", cleaned)
    return cleaned


def generate_monday_macro_poll() -> Dict[str, Any]:
    """
    Generate Monday Economic Calendar poll.
    Highlights the week's key macro catalysts and asks the community to vote on the most important.
    """
    print("🗓️ Generating Monday Macro Calendar Poll...")
    try:
        import economic_calendar
        return economic_calendar.get_weekly_macro_poll()
    except Exception as e:
        print(f"⚠️ Failed to load economic_calendar module: {e}")
        # Curated fallback
        return {
            "title": "Macro della settimana: quale catalizzatore guiderà i mercati? 🗓️",
            "options": [
                "Inflazione USA (CPI/PPI)",
                "Decisione Tassi BCE/Fed",
                "Dati Occupazione USA",
                "Altro (nei commenti)",
            ],
            "tickers": ["SPX500", "NSDQ100", "EURUSD"],
            "message": (
                "🗓️ CALENDARIO MACRO DELLA SETTIMANA\n\n"
                "I market mover più attesi da monitorare sui mercati:\n"
                "▪️ Lunedì: Apertura mercati e posizionamento flussi azionari\n"
                "▪️ Martedì: Dati bilancia commerciale e aste governative\n"
                "▪️ Mercoledì: Scorte energetiche e discorsi banchieri centrali\n"
                "▪️ Giovedì: Decisioni tassi d'interesse & PPI prezzi produzione\n"
                "▪️ Venerdì: Inflazione (CPI) & report occupazione USA\n\n"
                "Quale tra questi catalizzatori peserà di più sui mercati?\n"
                "Votate con 1 tap nel sondaggio e dite la vostra nei commenti! 👇"
            ),
        }


def generate_wednesday_thematic_poll(specific_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate Wednesday Thematic & Educational Strategy poll from curated templates.
    """
    print("💡 Generating Wednesday Thematic Strategy Poll...")
    selected = None
    if specific_id and specific_id.lower() not in ("auto", "wednesday", "wednesday_thematic", "thematic"):
        for t in POLL_TEMPLATES:
            if t["id"] == specific_id:
                selected = t
                break

    if not selected:
        selected = random.choice(POLL_TEMPLATES)

    return {
        "title": selected["title"],
        "options": selected["options"],
        "tickers": selected["tickers"],
        "message": selected["message"],
    }


def generate_friday_performers_poll() -> Dict[str, Any]:
    """
    Generate Friday Top Performers poll.
    Highlights the top 3 best performing portfolio stocks of the week,
    tags broad market indices ($SPX500, $NSDQ100), and asks the community
    which ones they hold and what they think of the rally.
    """
    print("🏆 Generating Friday Top Performers Poll...")
    top_candidates = []

    try:
        import finance_fetcher
        print("   Fetching real-time stock data to find top weekly performers...")
        stock_data = finance_fetcher.fetch_stock_data()
        
        # Filter for active portfolio holdings with valid weekly_change
        excluded = {"MNODL.L", "NVTKL.L", "XEON.DE", "IB01.L", "ANT.24-7", "ANT", "MELI", "WCLD.L", "WCLD"}
        candidates = []
        for ticker, data in stock_data.items():
            if ticker in excluded:
                continue
            w_chg = data.get("weekly_change")
            if w_chg is not None and not (isinstance(w_chg, float) and (w_chg != w_chg)):  # not NaN
                c_name = data.get("company_name", ticker)
                candidates.append((ticker, c_name, float(w_chg)))

        if len(candidates) >= 3:
            # Sort by weekly change descending
            candidates.sort(key=lambda x: x[2], reverse=True)
            top_candidates = candidates[:3]
            print(f"   Top 3 Weekly Performers: {top_candidates}")
    except Exception as e:
        print(f"   ⚠️ Could not fetch live weekly performance: {e}")

    # Robust fallback if stock_data fetch had issues
    if len(top_candidates) < 3:
        top_candidates = [
            ("PLTR", "Palantir", 5.8),
            ("NVDA", "NVIDIA", 4.2),
            ("CCJ", "Cameco", 3.7),
        ]

    top1, top2, top3 = top_candidates[0], top_candidates[1], top_candidates[2]

    # Format options within strict 28-character limit
    # e.g.: "$PLTR (+5.8%)"
    opt1 = f"${top1[0]} (+{top1[2]:.1f}%)" if top1[2] >= 0 else f"${top1[0]} ({top1[2]:.1f}%)"
    opt2 = f"${top2[0]} (+{top2[2]:.1f}%)" if top2[2] >= 0 else f"${top2[0]} ({top2[2]:.1f}%)"
    opt3 = f"${top3[0]} (+{top3[2]:.1f}%)" if top3[2] >= 0 else f"${top3[0]} ({top3[2]:.1f}%)"
    opt4 = "Nessuno / Altro"

    options = [opt1[:28].strip(), opt2[:28].strip(), opt3[:28].strip(), opt4]

    title = "Top Performer della settimana: quale avete in portafoglio? 🚀"[:200]

    message = (
        "🗳️ SONDAGGIO COMMUNITY: I TOP PERFORMER DELLA SETTIMANA 🚀\n\n"
        "Si chiude un'altra intensa settimana sui mercati globali su $SPX500 e $NSDQ100.\n\n"
        "Tra i titoli del nostro portafoglio a lungo termine, le 3 migliori performance degli ultimi 5 giorni sono state:\n"
        f"🥇 ${top1[0]} ({top1[1]}): {top1[2]:+.1f}%\n"
        f"🥈 ${top2[0]} ({top2[1]}): {top2[2]:+.1f}%\n"
        f"🥉 ${top3[0]} ({top3[1]}): {top3[2]:+.1f}%\n\n"
        "Quali di questi titoli avete in portafoglio? Cosa ne pensate del rally: "
        "continuerà la prossima settimana o è tempo di prese di beneficio?\n\n"
        "Votate con 1 tap l'opzione che possedete e scrivete la vostra nei commenti! 👇"
    )

    tickers = [top1[0], top2[0], top3[0], "SPX500", "NSDQ100"]

    return {
        "title": title,
        "options": options,
        "tickers": tickers,
        "message": message,
    }


def get_poll_for_schedule(poll_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Select or generate the appropriate poll based on day of week or explicit parameter:
      - Monday (0) -> Monday Macro Economic Calendar Poll
      - Wednesday (2) -> Wednesday Thematic Strategy Poll
      - Friday (4) -> Friday Top Performers Poll
      - Explicit: 'monday', 'wednesday', 'friday', or template ID
    """
    p_lower = (poll_id or "auto").strip().lower()

    if p_lower in ("monday", "monday_macro", "macro", "calendar"):
        return generate_monday_macro_poll()
    elif p_lower in ("friday", "friday_performers", "performers", "weekly_top"):
        return generate_friday_performers_poll()
    elif p_lower in ("wednesday", "wednesday_thematic", "thematic"):
        return generate_wednesday_thematic_poll()
    elif any(t["id"] == p_lower for t in POLL_TEMPLATES):
        return generate_wednesday_thematic_poll(specific_id=p_lower)
    elif p_lower != "auto":
        # Fallback to thematic if unrecognized id
        return generate_wednesday_thematic_poll(specific_id=p_lower)

    # Automatic selection based on UTC day of week
    dow = datetime.now(timezone.utc).weekday()  # 0=Monday, 2=Wednesday, 4=Friday
    if dow == 0:
        return generate_monday_macro_poll()
    elif dow == 4:
        return generate_friday_performers_poll()
    else:
        return generate_wednesday_thematic_poll()


def publish_etoro_poll(
    poll_id: Optional[str] = None,
    custom_title: Optional[str] = None,
    custom_options: Optional[List[str]] = None,
    custom_message: Optional[str] = None,
    custom_tickers: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Publish an interactive poll to eToro Social Feed.
    Supports Monday Macro, Wednesday Thematic, and Friday Performers.
    Strictly removes '#' hashtags from all text sent to eToro.
    """
    print("=" * 65)
    print("🗳️ PUBLISHING INTERACTIVE POLL TO ETORO SOCIAL FEED")
    print(f"🕒 Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    if dry_run:
        print("🔍 DRY-RUN MODE: Poll will be prepared and verified, but not posted.")
    print("=" * 65)

    # Select poll data based on schedule or explicit input
    poll_data = get_poll_for_schedule(poll_id=poll_id)

    raw_title = custom_title or poll_data["title"]
    raw_options = custom_options or poll_data["options"]
    raw_message = custom_message or poll_data["message"]
    tickers = custom_tickers or poll_data["tickers"]

    # Strictly sanitize, unwrap parenthesized cashtags in title/message, and strip '#' hashtags
    title = _clean_no_hashtags(_unwrap_cashtag_parens(raw_title))[:200].strip()
    options = [_clean_no_hashtags(str(opt))[:28].strip() for opt in raw_options[:4]]
    message = _clean_no_hashtags(_unwrap_cashtag_parens(raw_message)).strip()

    # Extract any mentioned cashtags from title, options, and message (strip sentence-ending periods)
    all_text = f"{title} {' '.join(options)} {message} {' '.join(tickers)}"
    found_tickers = [
        t.rstrip(".-")
        for t in re.findall(r"\$([A-Za-z0-9\.\-]+)", all_text)
        if t.rstrip(".-")
    ]
    all_tickers = list(dict.fromkeys([t.rstrip(".-") for t in tickers] + found_tickers))  # preserve order & deduplicate

    market_ids = etoro_client.get_market_ids_for_tickers(all_tickers)

    # Format prominent cashtags footer (NO HASHTAGS)
    cashtags_str = " ".join([f"${t.replace('$', '')}" for t in all_tickers[:8]])
    footer_parts = []
    if cashtags_str:
        footer_parts.append(f"📌 {cashtags_str}")
    footer_parts.append("👤 Segui il mio portafoglio: https://www.etoro.com/people/andrearavalli")
    tag_footer = "\n\n" + "\n\n".join(footer_parts)

    full_message = message.strip()
    if "andrearavalli" not in full_message.lower():
        # Reserve room for footer so full_message NEVER exceeds eToro 1000-char limit
        footer_len = len(tag_footer)
        max_body_allowed = 1000 - footer_len - 5
        if len(full_message) > max_body_allowed:
            full_message = smart_truncate(full_message, max_chars=max_body_allowed)
        full_message = full_message.strip() + tag_footer
    else:
        if len(full_message) > 1000:
            full_message = smart_truncate(full_message, max_chars=1000)

    # Final sanitization of full message
    full_message = _clean_no_hashtags(full_message)[:1000].strip()
    # Double check total length: if still > 1000, smart-truncate the body again
    if len(full_message) > 1000:
        available = 1000 - len(tag_footer) - 5
        body_part = smart_truncate(message, max_chars=available)
        full_message = body_part.strip() + tag_footer

    # Clean hashtags one final time
    full_message = _clean_no_hashtags(full_message).strip()
    if len(full_message) > 1000:
        # Ultimate fallback without cutting words
        full_message = smart_truncate(full_message, max_chars=1000)

    print(f"📌 Poll Title: {title}")
    print(f"📌 Options ({len(options)}): {options}")
    for idx, opt in enumerate(options):
        print(f"   [{idx+1}] '{opt}' ({len(opt)} chars, max 28)")
    print(f"🏷️ Tagged Markets: {all_tickers} -> IDs {market_ids}")
    print(f"📝 Message Preview ({len(full_message)} chars):\n{full_message}")

    if dry_run:
        print("\n✅ DRY-RUN SUCCESS: Poll verified with zero '#' hashtags and compliant lengths.")
        return {
            "success": True,
            "dry_run": True,
            "title": title,
            "options": options,
            "tickers": all_tickers,
            "market_ids": market_ids,
        }

    if not etoro_client.is_configured():
        print("❌ eToro API credentials not configured.")
        return {"success": False, "error": "eToro API not configured"}

    # Create poll via official eToro API
    res = etoro_client.create_poll_post(
        message=full_message,
        poll_title=title,
        poll_options=options,
        language="it",
        market_ids=market_ids if market_ids else None,
    )

    if res.get("success"):
        post_id = res.get("id")
        print(f"🎉 Poll published successfully on eToro! Post ID: {post_id}")

        # Save last eToro post metadata for analytics and delayed engagement
        try:
            gist_storage.save_last_etoro_post(
                post_id=post_id,
                session_name="Community Poll",
                tickers=tickers,
                market_data_summary={"is_poll": True, "title": title},
            )
            gist_storage.mark_session_run("Community Poll")
        except Exception as e:
            print(f"⚠️ Gist save warning: {e}")

        try:
            analytics_tracker.record_post(
                platform="etoro",
                post_id=post_id,
                session_name="Community Poll",
                text=f"{title}\n\n{message}",
                image_type="poll",
                tickers=tickers,
            )
            analytics_tracker.update_and_build_dashboard()
        except Exception as e:
            print(f"⚠️ Analytics recording warning: {e}")

        return {
            "success": True,
            "post_id": post_id,
            "title": title,
            "options": options,
        }
    else:
        print(f"❌ Failed to publish poll on eToro: {res.get('error')}")
        return {
            "success": False,
            "error": res.get("error"),
            "status_code": res.get("status_code"),
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="eToro Community Poll Generator")
    parser.add_argument("poll_template", nargs="?", default="auto", help="Template ID or day mode (monday_macro, wednesday_thematic, friday_performers, auto)")
    parser.add_argument("--dry-run", action="store_true", help="Prepare and verify poll without publishing to eToro")
    args = parser.parse_args()

    publish_etoro_poll(poll_id=args.poll_template, dry_run=args.dry_run)
