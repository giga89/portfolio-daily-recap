#!/usr/bin/env python3
"""
Interactive Poll Generator for eToro Social Feed
================================================
Generates and publishes highly engaging 1-click community polls directly to eToro.
Polls dramatically increase interaction, algorithmic reach, and profile views.
"""

import os
import sys
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


POLL_TEMPLATES = [
    {
        "id": "megatrend_h2",
        "title": "Quale megatrend guiderà le performance nei prossimi mesi? 🚀",
        "options": [
            "AI & Tech ($NVDA, $PLTR)",
            "Sanità & GLP-1 ($LLY, $NOVO)",
            "Energia & Uranio ($CCJ)",
            "Difesa & Aerospazio ($WDEF)",
        ],
        "tickers": ["NVDA", "PLTR", "LLY", "CCJ", "WDEF.L"],
        "message": (
            "🗳️ SONDAGGIO COMMUNITY: I GRANDI MEGATREND GLOBALI\n\n"
            "Nel nostro portafoglio bilanciamo crescita secolare (AI & Semiconduttori) con pilastri strategici ad alta visibilità (Sanità, Energia nucleare e Difesa europea).\n\n"
            "Secondo voi, quale tra questi 4 megatrend offrirà il miglior profilo rischio/rendimento nei prossimi trimestri?\n\n"
            "Votate l'opzione e lasciate un commento con la vostra analisi! 👇"
        )
    },
    {
        "id": "ai_valuation_debate",
        "title": "Come valutate l'attuale fase dell'Intelligenza Artificiale? 🤖",
        "options": [
            "Primi stadi: forte upside",
            "Fase matura: solo veri leader",
            "Valutazioni troppo tirate",
            "Preferisco ETF diversificati",
        ],
        "tickers": ["PLTR", "NVDA", "TSM", "MSFT"],
        "message": (
            "🗳️ SONDAGGIO COMMUNITY: IL FUTURO DELL'ECOSISTEMA AI & SOFTWARE\n\n"
            "Tra contratti enterprise AIP ($PLTR), architetture Blackwell ($NVDA) e hyperscaler cloud ($MSFT, $GOOGL), l'AI continua a ridefinire la produttività globale.\n\n"
            "Come vi state posizionando sui titoli leader del settore tech?\n\n"
            "Dite la vostra nel sondaggio con 1 tap! 👇"
        )
    },
    {
        "id": "risk_management_choice",
        "title": "Qual è la vostra priorità principale di asset allocation? ⚖️",
        "options": [
            "Massima crescita (High Beta)",
            "Crescita bilanciata (Core)",
            "Dividendi & Flussi di cassa",
            "Beni rifugio e liquidità",
        ],
        "tickers": ["PLTR", "LLY", "SX7PEX.DE", "PPFB.DE"],
        "message": (
            "🗳️ SONDAGGIO: GESTIONE DEL RISCHIO E ASSET ALLOCATION\n\n"
            "La nostra strategia mantiene un Risk Score eToro certificato di 3/10 con zero leva finanziaria e +200% di performance cumulata dal 2020.\n\n"
            "Qual è il vostro approccio attuale al rapporto rischio/rendimento sui mercati?\n\n"
            "Votate qui sotto per confrontarvi con la community! 👇"
        )
    },
    {
        "id": "pltr_conviction",
        "title": "Palantir ($PLTR): Quale scenario vi aspettate a medio termine? 🛡️",
        "options": [
            "Forte rialzo (AIP leader)",
            "Consolidamento sui massimi",
            "Correzione tecnica salutare",
            "Preferisco altri titoli tech",
        ],
        "tickers": ["PLTR", "NVDA"],
        "message": (
            "🗳️ SONDAGGIO DEL GIORNO: FOCUS SU PALANTIR ($PLTR)\n\n"
            "Palantir si conferma uno dei pilastri a più alta convinzione del nostro portafoglio, spinto dalla continua adozione commerciale di AIP e margini operativi solidissimi.\n\n"
            "Qual è la vostra visione sul titolo nei prossimi mesi?\n\n"
            "Votate e commentate con il vostro target! 👇"
        )
    },
    {
        "id": "gold_safe_haven",
        "title": "Oro fisico ($PPFB.DE): Quale ruolo deve avere in portafoglio? 🥇",
        "options": [
            "Copertura indispensabile (5-10%)",
            "Ottimo trend rialzista",
            "Preferisco titoli a dividendo",
            "Meglio bond/liquidità ($IB01)",
        ],
        "tickers": ["PPFB.DE", "IB01.L"],
        "message": (
            "🗳️ SONDAGGIO: ORO FISICO E BENI RIFUGIO ($PPFB.DE)\n\n"
            "Manteniamo in portafoglio una quota strutturale di Oro fisico tramite ETC ($PPFB.DE) come scudo contro svalutazione monetaria e shock macroeconomici.\n\n"
            "Come considerate l'oro nella vostra asset allocation strategica?\n\n"
            "Votate l'opzione che rispecchia la vostra strategia! 👇"
        )
    },
    {
        "id": "glp1_pharma_battle",
        "title": "Rivoluzione GLP-1 / Obesità: Chi dominerà il mercato pharma? 💊",
        "options": [
            "Eli Lilly ($LLY)",
            "Novo Nordisk ($NOVO-B)",
            "Duopolio paritario a lungo",
            "Nuovi competitor emergenti",
        ],
        "tickers": ["LLY", "NOVO-B.CO", "ABBV"],
        "message": (
            "🗳️ SONDAGGIO HEALTHCARE: IL BOOM DEI TRATTAMENTI GLP-1\n\n"
            "Il mercato dei farmaci contro obesità e patologie metaboliche ($LLY con Mounjaro/Zepbound e $NOVO-B con Ozempic/Wegovy) rappresenta uno dei trend terapeutici più redditizi del decennio.\n\n"
            "Chi secondo voi manterrà la leadership e i margini più elevati nel lungo periodo?\n\n"
            "Votate qui sotto! 👇"
        )
    },
    {
        "id": "nuclear_energy_ai",
        "title": "Nucleare & Uranio ($CCJ): Saranno essenziali per i Data Center AI? ⚡",
        "options": [
            "Sì, energia pulita 24/7 cruciale",
            "Sì, ma orizzonte molto lungo",
            "Meglio solare/eolico ($TRIG)",
            "Gas e combustibili transitori",
        ],
        "tickers": ["CCJ", "TRIG.L", "ENEL.MI"],
        "message": (
            "🗳️ SONDAGGIO ENERGIA: IL RINASCIMENTO NUCLEARE ($CCJ)\n\n"
            "L'esplosione dei consumi energetici per l'Intelligenza Artificiale sta spingendo i giganti tech verso contratti nucleari baseload a zero emissioni. Con Cameco ($CCJ) siamo esposti al principale produttore occidentale di uranio.\n\n"
            "Credete che il nucleare sarà il vincitore energetico del decennio?\n\n"
            "Dite la vostra! 👇"
        )
    },
    {
        "id": "semiconductor_foundry_moat",
        "title": "Semiconduttori: Quale azienda possiede il Moat più solido? 🏭",
        "options": [
            "TSMC ($TSM - Monopolio fonderia)",
            "NVIDIA ($NVDA - Ecosistema CUDA)",
            "Broadcom ($AVGO - Custom ASIC)",
            "Marvell ($MRVL - Connettività)",
        ],
        "tickers": ["TSM", "NVDA", "AVGO", "MRVL"],
        "message": (
            "🗳️ SONDAGGIO CHIP: DOVE RISIEDE IL VERO VANTAGGIO COMPETITIVO?\n\n"
            "Dai nodi a 2nm/3nm di TSMC ai chip ASIC custom di Broadcom per hyperscaler, i semiconduttori sono le fondamenta irrinunciabili della trasformazione digitale.\n\n"
            "Tra questi giganti nel nostro portafoglio, chi ha il fossato competitivo più inespugnabile?\n\n"
            "Votate e motivate nei commenti! 👇"
        )
    },
    {
        "id": "defense_europe_rearmament",
        "title": "Difesa Europea ($WDEF): Cosa aspettarsi dalla spesa militare NATO? 🛡️",
        "options": [
            "Crescita secolare pluriennale",
            "Valutazioni già incorporate",
            "Forte dipendenza dalla politica",
            "Preferisco difesa USA",
        ],
        "tickers": ["WDEF.L", "PLTR"],
        "message": (
            "🗳️ SONDAGGIO SETTORE DIFESA: LA RI-MILITARIZZAZIONE EUROPEA ($WDEF)\n\n"
            "Con i budget NATO in aumento verso e oltre il 2% del PIL e la ricostituzione degli inventari strategici europei, l'ETF WisdomTree Europe Defence ($WDEF.L) cattura i leader industriali del continente.\n\n"
            "Ritenete che il settore Difesa rimarrà un driver strutturale di rendimento nei prossimi anni?\n\n"
            "Esprimete il vostro voto! 👇"
        )
    },
    {
        "id": "dividends_cash_yield",
        "title": "Titoli da dividendo: Quale settore offre il flusso più solido? 💰",
        "options": [
            "Banche Europee ($SX7PEX.DE)",
            "Energy & Utilities ($ENI, $ENEL)",
            "Pharma & Aristocrats ($ABBV)",
            "Infrastrutture Green ($TRIG)",
        ],
        "tickers": ["SX7PEX.DE", "ENI.MI", "ENEL.MI", "ABBV", "TRIG.L"],
        "message": (
            "🗳️ SONDAGGIO CASH FLOW: GENERAZIONE DI RENDITA PASSIVA\n\n"
            "Il nostro portafoglio bilancia posizioni growth con asset a dividendo sostenibile (~3-4% yield medio sul comparto income) per finanziare costantemente nuova liquidità.\n\n"
            "Quale comparto ritenete più affidabile per la generazione di flussi di cassa?\n\n"
            "Votate con 1 tap! 👇"
        )
    },
    {
        "id": "emerging_markets_opportunity",
        "title": "Mercati Emergenti: Dove vedete la maggiore opportunità? 🌏",
        "options": [
            "America Latina ($MELI)",
            "Cina & EV leader ($1211.HK)",
            "Vietnam & Frontiera ($VOF.L)",
            "Indonesia & Materie prime ($INDO)",
        ],
        "tickers": ["MELI", "1211.HK", "VOF.L", "INDO.PA"],
        "message": (
            "🗳️ SONDAGGIO MERCATI EMERGENTI: CRESCITA E DEMOGRAFIA\n\n"
            "Dall'espansione e-commerce e fintech di MercadoLibre ($MELI) al boom manifatturiero del Vietnam ($VOF.L) e alle riserve indonesiane ($INDO.PA), cerchiamo alpha selettivo globale.\n\n"
            "Quale area geografica emergente offre il miglior potenziale di rivalutazione?\n\n"
            "Votate e commentate la vostra scelta! 👇"
        )
    },
    {
        "id": "luxury_vs_defensive_consumer",
        "title": "Consumi & Pricing Power: Quale modello di business preferite? 🏎️",
        "options": [
            "Ultra-Luxury Moat ($RACE Ferrari)",
            "Retail di massa difensivo ($WMT)",
            "Beni di consumo primari ($ULVR)",
            "Auto globale in transizione ($VOW3)",
        ],
        "tickers": ["RACE", "WMT", "ULVR.L", "VOW3.DE"],
        "message": (
            "🗳️ SONDAGGIO CONSUMI: PRICING POWER E RESILIENZA\n\n"
            "Nelle diverse fasi di mercato, due strategie spiccano: l'inimitabile pricing power del lusso estremo ($RACE con liste d'attesa pluriennali) o la scala dei colossi dei consumi quotidiani ($WMT, $ULVR.L).\n\n"
            "Su quale modello puntereste con un orizzonte di 3-5 anni?\n\n"
            "Dite la vostra nel sondaggio! 👇"
        )
    },
    {
        "id": "electrification_grid_supercycle",
        "title": "Elettrificazione globale: Quale segmento sarà più redditizio? 🔌",
        "options": [
            "Cavi & Reti alta tensione ($PRY)",
            "Rame & Metalli critici ($GLEN)",
            "Generazione e rinnovabili ($ENEL)",
            "Intera catena dell'elettrificazione",
        ],
        "tickers": ["PRY.MI", "GLEN.L", "ENEL.MI"],
        "message": (
            "🗳️ SONDAGGIO INFRASTRUTTURE: IL SUPERCICLO DELL'ELETTRIFICAZIONE\n\n"
            "Il potenziamento delle reti elettriche per data center, rinnovabili e mobilità elettrica genera una domanda senza precedenti per cavi sottomarini (Prysmian $PRY.MI) e rame industriale (Glencore $GLEN.L).\n\n"
            "Quale comparto beneficerà maggiormente di questo mega-trend infrastrutturale?\n\n"
            "Votate qui sotto! 👇"
        )
    },
    {
        "id": "big_tech_cloud_battle",
        "title": "Hyperscale Cloud & AI: Chi vincerà la sfida enterprise? ☁️",
        "options": [
            "Microsoft Azure ($MSFT)",
            "Amazon AWS ($AMZN)",
            "Google Cloud ($GOOGL)",
            "Crescita condivisa per tutti",
        ],
        "tickers": ["MSFT", "AMZN", "GOOG"],
        "message": (
            "🗳️ SONDAGGIO BIG TECH: LA BATTAGLIA DELL'INFRASTRUTTURA CLOUD\n\n"
            "I tre giganti del Cloud ($MSFT, $AMZN, $GOOGL) stanno investendo centinaia di miliardi per dotare le proprie infrastrutture dei migliori cluster di accelerazione AI.\n\n"
            "Quale piattaforma conquisterà la quota maggiore di budget IT aziendali nei prossimi anni?\n\n"
            "Votate e lasciate la vostra previsione! 👇"
        )
    },
    {
        "id": "ev_revolution_byd",
        "title": "Auto Elettriche e Mobilità: BYD ($1211.HK) guiderà il mercato globale? 🔋",
        "options": [
            "Sì, integrazione verticale totale",
            "Sì, ma frenata da dazi e geopolitica",
            "I marchi tradizionali recupereranno",
            "Crescita EV più lenta del previsto",
        ],
        "tickers": ["1211.HK", "VOW3.DE"],
        "message": (
            "🗳️ SONDAGGIO MOBILITÀ: LA SCALA INDUSTRIALE DI BYD ($1211.HK)\n\n"
            "Con la tecnologia Blade Battery, produzione proprietaria di semiconduttori e prezzi ultra-competitivi, BYD sta espandendo la propria quota di mercato a livello globale.\n\n"
            "Come valutate il posizionamento di BYD rispetto all'automotive tradizionale ($VOW3.DE)?\n\n"
            "Votate il sondaggio! 👇"
        )
    },
    {
        "id": "private_equity_space_frontier",
        "title": "Asset Alternativi & Spazio: Quale frontiera è più promettente? 🚀",
        "options": [
            "Economia spaziale ($SPCX SpaceX)",
            "Private Equity globale ($IQQL.DE)",
            "Mercati di frontiera ($VOF.L)",
            "Preferisco azioni quotate standard",
        ],
        "tickers": ["SPCX.RTH", "IQQL.DE", "VOF.L"],
        "message": (
            "🗳️ SONDAGGIO ASSET ALTERNATIVI: CRESCITA FUORI DAI LISTINI TRADIZIONALI\n\n"
            "Dalla rivoluzione aerospaziale e Starlink ($SPCX.RTH SpaceX) ai giganti del private equity (Blackstone, KKR via $IQQL.DE), ricerchiamo fonti di rendimento non correlate.\n\n"
            "Quale classe di asset alternativi ritenete più interessante per diversificare?\n\n"
            "Esprimete la vostra preferenza! 👇"
        )
    },
    {
        "id": "european_banking_profitability",
        "title": "Banche Europee ($SX7PEX.DE): Extra-rendimenti e buyback sostenibili? 🏛️",
        "options": [
            "Sì, dividendi e buyback record",
            "Sì, ma con crescita moderata",
            "Rischio pressione sui margini",
            "Preferisco altri settori europei",
        ],
        "tickers": ["SX7PEX.DE", "2318.HK"],
        "message": (
            "🗳️ SONDAGGIO BANCHE EUROPEE: REDDITIVITÀ E REMUNERAZIONE DEGLI AZIONISTI\n\n"
            "Il settore bancario europeo ($SX7PEX.DE) continua a offrire flussi di cassa solidi, distribuzioni di capitale generose e valutazioni a multipli contenuti.\n\n"
            "Qual è la vostra aspettativa sul comparto bancario per i prossimi mesi?\n\n"
            "Votate qui sotto! 👇"
        )
    },
    {
        "id": "healthcare_biopharma_defensive",
        "title": "Sanità & Diagnostica: Quale comparto offre la massima solidità? 🏥",
        "options": [
            "Dispositivi e diagnostica ($ABT)",
            "Immunologia & Oncologia ($ABBV, $AZN)",
            "Assicurazioni sanitarie ($HUM)",
            "Terapie metaboliche & GLP-1 ($LLY)",
        ],
        "tickers": ["ABT.US", "ABBV", "AZN.L", "HUM", "LLY"],
        "message": (
            "🗳️ SONDAGGIO HEALTHCARE: DOMANDA ANELASTICA E INNOVAZIONE\n\n"
            "La sanità offre una protezione unica grazie ai trend demografici globali, unita a catalizzatori di crescita nell'oncologia, monitoraggio glicemico ($ABT) e blockbuster biologici ($ABBV, $AZN.L).\n\n"
            "Quale area sanitaria preferite avere in portafoglio?\n\n"
            "Dite la vostra nel sondaggio! 👇"
        )
    },
    {
        "id": "copytrading_portfolio_secrets",
        "title": "Investimenti a lungo termine: Qual è il fattore più determinante? 🏆",
        "options": [
            "Zero leva e Risk Score basso (3/10)",
            "Diversificazione globale e settoriale",
            "Pazienza e Buy & Hold pluriennale",
            "Reinvestimento continuo dei proventi",
        ],
        "tickers": ["PLTR", "NVDA", "PPFB.DE", "SX7PEX.DE"],
        "message": (
            "🗳️ SONDAGGIO STRATEGIA: I PILASTRI DEL NOSTRO SUCCESSO (+200% DAL 2020)\n\n"
            "Generare rendimento composto costante riducendo i drawdown richiede metodo: niente leva finanziaria, Risk Score controllato 3/10 e diversificazione tra Growth, Valore e Oro.\n\n"
            "Secondo la vostra esperienza, qual è l'elemento più cruciale per investire con successo?\n\n"
            "Votate e raccontateci il vostro approccio! 👇"
        )
    },
    {
        "id": "fintech_digital_assets_future",
        "title": "Fintech & Pagamenti: Come evolverà il trasferimento di valore? 💳",
        "options": [
            "Social Investing Platform ($ETOR)",
            "Stablecoin & Blockchain rails ($TRX)",
            "E-commerce & Fintech LatAm ($MELI)",
            "Banche e circuiti tradizionali",
        ],
        "tickers": ["ETOR", "TRX", "MELI"],
        "message": (
            "🗳️ SONDAGGIO FINTECH: IL FUTURO DEI SERVIZI FINANZIARI\n\n"
            "Dall'evoluzione del social trading ($ETOR) all'utilizzo massivo di stablecoin per settlement istantanei su rete TRON ($TRX), fino alle super-app di credito e pagamenti digitali ($MELI), i canali finanziari cambiano rapidamente.\n\n"
            "Quale tecnologia/piattaforma sarà più rilevante nel prossimo quinquennio?\n\n"
            "Votate e confrontatevi con noi! 👇"
        )
    },
]


def publish_etoro_poll(
    poll_id: Optional[str] = None,
    custom_title: Optional[str] = None,
    custom_options: Optional[List[str]] = None,
    custom_message: Optional[str] = None,
    custom_tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Publish an interactive poll to eToro Social Feed.
    """
    print("=" * 65)
    print("🗳️ PUBLISHING INTERACTIVE POLL TO ETORO SOCIAL FEED")
    print(f"🕒 Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 65)

    if not etoro_client.is_configured():
        print("❌ eToro API credentials not configured.")
        return {"success": False, "error": "eToro API not configured"}

    # Select template or use custom inputs
    selected = None
    if poll_id and poll_id.lower() != "auto":
        for t in POLL_TEMPLATES:
            if t["id"] == poll_id:
                selected = t
                break

    if not selected:
        selected = random.choice(POLL_TEMPLATES)

    title = custom_title or selected["title"]
    options = custom_options or selected["options"]
    message = custom_message or selected["message"]
    tickers = custom_tickers or selected["tickers"]

    # Extract any mentioned cashtags from title, options, and message
    import re
    all_text = f"{title} {' '.join(options)} {message} {' '.join(tickers)}"
    found_tickers = re.findall(r"\$([A-Za-z0-9\.\-]+)", all_text)
    all_tickers = list(dict.fromkeys(tickers + found_tickers))  # preserve order & deduplicate

    market_ids = etoro_client.get_market_ids_for_tickers(all_tickers)

    # Format prominent cashtags and hashtags footer for maximum feed discovery
    cashtags_str = " ".join([f"${t.replace('$', '')}" for t in all_tickers[:8]])
    tag_footer = (
        f"\n\n📌 {cashtags_str}\n"
        f"🏷️ #eToro #Sondaggio #Investimenti #CopyTrading #PopularInvestor\n\n"
        f"👤 Segui il mio portafoglio: https://www.etoro.com/people/andrearavalli"
    )

    full_message = message.strip()
    if not any(tag.lower() in full_message.lower() for tag in ["#etoro", "#sondaggio"]):
        full_message += tag_footer

    print(f"📌 Poll Title: {title}")
    print(f"📌 Options ({len(options)}): {options}")
    print(f"🏷️ Tagged Markets: {all_tickers} -> IDs {market_ids}")

    # Create poll via official eToro API
    res = etoro_client.create_poll_post(
        message=full_message[:1000],
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
                market_data_summary={"is_poll": True, "title": title}
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
    p_id = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    publish_etoro_poll(poll_id=p_id)
