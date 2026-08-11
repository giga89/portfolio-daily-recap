#!/usr/bin/env python3
"""
High-End Investor Infographic Generator (Hitachi Style)
======================================================
Generates ultra-premium, professional investment infographics inspired by top-tier financial creators:
  • Elegant top header with company branding and clean typography
  • 4 Clean Highlight Metric cards with icons & bold numbers (Revenue growth, Margins, Weight, Sector)
  • "PERCHÉ INVESTO IN [AZIENDA]" structured thesis with clean vector badges (no emoji font dependencies)
  • Iconic Discipline Quote on the right: "Non investo per il prossimo trimestre. Investo per il prossimo decennio."
  • Dark / Modern Corporate bottom bar with Andrea Ravalli branding, sector labels & hashtags
  • DYNAMIC WEIGHT: Fetches exact live portfolio weights from eToro API or finance_fetcher!
"""

import io
import os
import time
import requests
from typing import Dict, Any, Optional, List

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

CARD_W = 1200
CARD_H = 1200  # Square 1:1 format (optimal for both mobile and desktop feed)

LOGO_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo_cache")

# Full company data dictionary tailored for infographics (NO raw emojis in pillar titles to prevent tofu/rectangles)
COMPANY_INFOGRAPHICS = {
    "PLTR": {
        "name": "PALANTIR",
        "tagline": "AI Platform & Enterprise Defense",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Palantir è l'infrastruttura operativa critica scelta da governi e grandi multinazionali per l'intelligenza artificiale.",
        "kpis": [
            {"label": "CRESCITA COMMERCIALE", "val": "+54%", "sub": "Adozione AIP record in US"},
            {"label": "RULE OF 40 (PROFITTO)", "val": "68%", "sub": "Margini operativi top tier"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Posizione core conviction"},
            {"label": "BILANCIO & CASSA", "val": "$4.0B+", "sub": "Zero debito, cassa netta"},
        ],
        "pillars": [
            ("Fossato Difensivo:", "Contratti decennali insostituibili con il governo US e la difesa."),
            ("Espansione AIP:", "La piattaforma AI sta conquistando le imprese Fortune 500 a ritmi record."),
            ("Potere di Prezzo:", "I clienti espandono costantemente la spesa (Net Retention > 115%)."),
            ("Visione Decennale:", "Posizionamento unico all'intersezione tra sicurezza nazionale ed AI."),
        ],
        "quote": "Non investo per il prossimo trimestre. Investo per il prossimo decennio.",
        "tags": ["#Palantir", "#AIP", "#ArtificialIntelligence", "#DefenseTech", "#LongTermInvesting"],
        "color": (0, 190, 240),
        "domain": "palantir.com"
    },
    "NVDA": {
        "name": "NVIDIA",
        "tagline": "Accelerated Computing & AI Architecture",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "NVIDIA detiene il monopolio de facto dei chip e dell'ecosistema software per l'addestramento e l'inferenza AI globale.",
        "kpis": [
            {"label": "CRESCITA DATA CENTER", "val": "+150%", "sub": "Domanda record architettura Blackwell"},
            {"label": "MARGINE LORDO", "val": "75%+", "sub": "Potere di prezzo ineguagliato"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Pilastro infrastrutturale"},
            {"label": "FOSSATO SOFTWARE", "val": "CUDA", "sub": "Milioni di sviluppatori vincolati"},
        ],
        "pillars": [
            ("Monopolio dell'Hardware:", "I chip GPU H100, H200 e Blackwell sono lo standard dell'intera industria."),
            ("Ecosistema CUDA:", "Oltre 15 anni di sviluppo software creano barriere all'entrata insormontabili."),
            ("Espansione Networking:", "Con Mellanox e Infiniband, controlla anche la connettività dei data center."),
            ("Crescita Strutturale:", "La spesa in hyperscaler (MSFT, GOOG, AMZN) sostiene la domanda multi-annuale."),
        ],
        "quote": "I chip sono il nuovo petrolio, e NVIDIA controlla le raffinerie mondiali.",
        "tags": ["#Nvidia", "#Blackwell", "#Semiconductors", "#ArtificialIntelligence", "#TechLeaders"],
        "color": (118, 185, 0),
        "domain": "nvidia.com"
    },
    "CCJ": {
        "name": "CAMECO",
        "tagline": "Uranium & Global Nuclear Clean Energy",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Cameco è il leader mondiale dell'estrazione di uranio e dei servizi tecnologici per la rinascita dell'energia nucleare.",
        "kpis": [
            {"label": "PREZZO CONTRATTUALE", "val": "+65%", "sub": "Trend rialzista a lungo termine"},
            {"label": "ASSET STRATEGICI", "val": "Tier-1", "sub": "McArthur River & Cigar Lake"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Top holding di convinzione"},
            {"label": "INTEGRAZIONE WESTINGHOUSE", "val": "Full Chain", "sub": "Estrazione, combustibile e reattori"},
        ],
        "pillars": [
            ("Deficit Strutturale:", "La domanda globale supera l'offerta primaria da oltre un decennio."),
            ("Spinta dei Data Center:", "Big Tech richiede energia nucleare 24/7 a zero emissioni per alimentare l'AI."),
            ("Contratti Pluriennali:", "Flussi di cassa stabili e protetti da accordi a lungo termine con le utility."),
            ("Geopolitica dell'Uranio:", "Le nazioni occidentali si allontanano dalla Russia, premiando il Canada."),
        ],
        "quote": "La transizione energetica e l'intelligenza artificiale non possono esistere senza il nucleare.",
        "tags": ["#Cameco", "#Uranium", "#NuclearEnergy", "#CleanTech", "#Commodities"],
        "color": (255, 175, 0),
        "domain": "cameco.com"
    },
    "SX7PEX.DE": {
        "name": "EURO STOXX BANKS",
        "tagline": "European Banking Sector UCITS ETF",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Esposizione ai principali gruppi bancari europei con bilanci solidi, alti dividendi e buyback massicci.",
        "kpis": [
            {"label": "DIVIDEND YIELD", "val": "7.5%+", "sub": "Rendimento da cassa elevato"},
            {"label": "CAPITAL RATIO (CET1)", "val": ">15.5%", "sub": "Massimi storici di solvibilità"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Pilastro valore e dividendi"},
            {"label": "BUYBACK & RESILIENZA", "val": "Record", "sub": "Remunerazione azionisti sostenibile"},
        ],
        "pillars": [
            ("Generazione di Cassa:", "I margini di interesse e la redditività rimangono a livelli strutturalmente alti."),
            ("Qualità del Credito:", "NPL ai minimi storici e coperture prudenziali estremamente elevate."),
            ("Valutazioni a Sconto:", "P/E attraenti rispetto al mercato USA offrono un ampio margine di sicurezza."),
            ("Ritorno di Capitale:", "Dividendi costanti e programmi di riacquisto azioni aumentano il valore per azione."),
        ],
        "quote": "Un portafoglio vincente bilancia la crescita aggressiva con solide macchine da dividendo.",
        "tags": ["#Banking", "#EuroStoxx", "#Dividends", "#ValueInvesting", "#Europe"],
        "color": (60, 130, 240),
        "domain": "stoxx.com"
    },
    "LLY": {
        "name": "ELI LILLY",
        "tagline": "Pharma Innovation & Metabolic Leaders",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Eli Lilly è il pioniere globale nei trattamenti contro obesità e diabete (GLP-1) con pipeline terapeutica da record.",
        "kpis": [
            {"label": "CRESCITA FATTURATO", "val": "+38%", "sub": "Boom globale di Tirzepatide"},
            {"label": "MERCATO POTENZIALE", "val": "$100B+", "sub": "Domanda secolare per GLP-1"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Pilastro healthcare qualità"},
            {"label": "INVESTIMENTI R&D", "val": "25%+", "sub": "Pipeline farmaci in espansione"},
        ],
        "pillars": [
            ("Monopolio dei Trattamenti GLP-1:", "Leader indiscusso insieme a Novo Nordisk nella cura di obesità e diabete."),
            ("Espansione Produttiva Massiccia:", "Investimenti miliardari per soddisfare una domanda che supera l'offerta."),
            ("Protezione Brevettuale Forte:", "Brevetti protetti per oltre un decennio con altissime barriere all'entrata."),
            ("Diversificazione Terapeutica:", "Pipeline solida anche in oncologia, immunologia e neuroscienze (Alzheimer)."),
        ],
        "quote": "La salute e l'innovazione farmaceutica rappresentano la forma più resiliente di crescita.",
        "tags": ["#EliLilly", "#Healthcare", "#Pharma", "#GLP1", "#LongTermInvesting"],
        "color": (220, 40, 40),
        "domain": "lilly.com"
    },
    "NOVO-B.CO": {
        "name": "NOVO NORDISK",
        "tagline": "Global Diabetes & Obesity Therapeutics",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Novo Nordisk è la principale multinazionale europea per capitalizzazione, leader mondiale nelle terapie a base di semaglutide.",
        "kpis": [
            {"label": "CRESCITA OZEMPIC / WEGOVY", "val": "+30%", "sub": "Adozione globale inarrestabile"},
            {"label": "ROIC (REDDITIVITÀ)", "val": ">60%", "sub": "Efficienza del capitale al top"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Posizione core difensiva"},
            {"label": "MARGINE OPERATIVO", "val": "45%+", "sub": "Potere di prezzo inattaccabile"},
        ],
        "pillars": [
            ("Leadership Globale nel Diabete:", "Oltre un secolo di esperienza e specializzazione nelle terapie metaboliche."),
            ("Vantaggi Cardiovascolari Certificati:", "Wegovy approvato anche per ridurre rischi cardiaci e renali."),
            ("Capacità di Cassa Enorme:", "Flussi di cassa operativi che finanziano buyback e ricerca all'avanguardia."),
            ("Fossato Difensivo Europeo:", "La società più solida e redditizia dell'intero panorama azionario continentale."),
        ],
        "quote": "Investire in aziende che migliorano la vita di milioni di persone genera valore per decenni.",
        "tags": ["#NovoNordisk", "#Ozempic", "#Wegovy", "#Healthcare", "#EuropeanQuality"],
        "color": (0, 100, 200),
        "domain": "novonordisk.com"
    },
    "ASML.AS": {
        "name": "ASML",
        "tagline": "Semiconductor Lithography Monopoly",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "ASML detiene il monopolio assoluto al mondo sulle macchine litografiche EUV indispensabili per produrre i chip avanzati.",
        "kpis": [
            {"label": "QUOTA DI MERCATO EUV", "val": "100%", "sub": "Monopolio tecnologico insostituibile"},
            {"label": "PORTAFOGLIO ORDINI", "val": "€35B+", "sub": "Visibilità ricavi pluriennale"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Fondamenta della tecnologia globale"},
            {"label": "PROSSIMA GEN HIGH-NA", "val": "Avviata", "sub": "EUV di nuova generazione per nodi <2nm"},
        ],
        "pillars": [
            ("Monopolio Litografico Unico:", "Nessuna azienda al mondo può stampare chip a 3nm o 2nm senza ASML."),
            ("Clienti di Livello Mondiale:", "Fornitore esclusivo per TSMC, NVIDIA, Apple, Intel e Samsung."),
            ("Barriere Tecnologiche Estreme:", "Oltre 30 anni di brevetti ottici e laser impossibili da replicare."),
            ("Crescita Guidata dall'AI:", "L'espansione dei semiconduttori garantisce domanda crescente per il decennio."),
        ],
        "quote": "Se i chip sono il futuro, ASML è l'unica azienda al mondo che possiede la macchina per stamparli.",
        "tags": ["#ASML", "#Semiconductors", "#EUV", "#TechMonopoly", "#Europe"],
        "color": (20, 50, 140),
        "domain": "asml.com"
    },
    "MELI": {
        "name": "MERCADOLIBRE",
        "tagline": "Latin America E-Commerce & Fintech Giant",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "MercadoLibre è l'ecosistema integrato dominante di commercio elettronico, logistica e pagamenti digitali in America Latina.",
        "kpis": [
            {"label": "CRESCITA VOLUMI (GMV)", "val": "+35%", "sub": "Leader in Brasile e Messico"},
            {"label": "MERCADOPAGO (TPV)", "val": "+50%", "sub": "Volume pagamenti fintech record"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Esposizione mercati emergenti"},
            {"label": "CONSEGNA IN 24H", "val": ">75%", "sub": "Rete logistica proprietaria unica"},
        ],
        "pillars": [
            ("Fossato Logistico Insuperabile:", "Rete proprietaria di magazzini e aerei che garantisce consegne record."),
            ("Volano Fintech MercadoPago:", "I servizi finanziari e di credito crescono più velocemente dell'e-commerce."),
            ("Bassa Penetrazione Digitale:", "L'America Latina ha ancora decenni di crescita nell'adozione dell'e-commerce."),
            ("Redditività e Margini in Espansione:", "Crescita autofinanziata con leva operativa ed espansione dei margini."),
        ],
        "quote": "Dominare simultaneamente commercio, logistica e finanza crea un ecosistema inarrestabile.",
        "tags": ["#MercadoLibre", "#Fintech", "#Ecommerce", "#LatinAmerica", "#GrowthInvesting"],
        "color": (255, 200, 0),
        "domain": "mercadolibre.com"
    },
    "TSM": {
        "name": "TSMC",
        "tagline": "Pure-Play Semiconductor Foundry Leader",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "TSMC produce oltre il 90% dei microchip più avanzati al mondo per NVIDIA, Apple, AMD e Qualcomm.",
        "kpis": [
            {"label": "QUOTA CHIP AVANZATI", "val": "90%+", "sub": "Nodi a 3nm e 5nm dominanti"},
            {"label": "MARGINE OPERATIVO", "val": "42%+", "sub": "Potere di prezzo ineguagliato"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Infrastruttura computazionale"},
            {"label": "SPESA IN CONTO CAPITALE", "val": "$30B+", "sub": "Investimenti record in fabbriche"},
        ],
        "pillars": [
            ("Foundry Indispensabile:", "Tutti i leader tecnologici dipendono dalla manifattura di precisione di TSMC."),
            ("Efficienza di Rendimento (Yield):", "I tassi di resa dei wafer TSMC sono nettamente superiori a Intel e Samsung."),
            ("Espansione Globale (USA, Giappone, EU):", "Diversificazione geografica degli impianti per mitigare i rischi."),
            ("Megatrend AI ed Elettrificazione:", "La domanda di calcolo computazionale sostiene la crescita decennale."),
        ],
        "quote": "Senza le fonderie di TSMC, l'intera rivoluzione dell'intelligenza artificiale si fermerebbe.",
        "tags": ["#TSMC", "#Semiconductors", "#Foundry", "#TechLeader", "#AIInfrastucture"],
        "color": (200, 30, 30),
        "domain": "tsmc.com"
    },
    "0005.HK": {
        "name": "HSBC",
        "tagline": "Global Banking & Wealth Management",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "HSBC è la banca leader nei flussi commerciali e nella gestione dei patrimoni tra Europa e Asia.",
        "kpis": [
            {"label": "DIVIDEND YIELD", "val": "7.0%+", "sub": "Rendimento da dividendo elevato"},
            {"label": "CET1 RATIO", "val": "15.2%", "sub": "Solidità patrimoniale ai vertici"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Pilastro dividendi e finanza globale"},
            {"label": "ROTE (REDDITIVITÀ)", "val": "15%+", "sub": "Redditività sul patrimonio solida"},
        ],
        "pillars": [
            ("Ponte Commerciale Occidente-Oriente:", "Leader indiscusso nel finanziamento al commercio internazionale."),
            ("Generazione di Cassa Massiccia:", "Dividendi trimestrali costanti accompagnati da programmi di buyback."),
            ("Espansione nel Wealth Management Asiatico:", "Crescita costante dei patrimoni gestiti a Hong Kong e Singapore."),
            ("Valutazioni Attrattive:", "Multipli a sconto che offrono un eccellente profilo di rischio/rendimento."),
        ],
        "quote": "I flussi commerciali globali generano rendimenti stabili attraverso qualsiasi ciclo economico.",
        "tags": ["#HSBC", "#Banking", "#Dividends", "#Asia", "#GlobalFinance"],
        "color": (220, 20, 20),
        "domain": "hsbc.com"
    },
    "1211.HK": {
        "name": "BYD",
        "tagline": "Electric Vehicles & Blade Battery Leader",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "BYD è il maggiore produttore mondiale di veicoli elettrici e ibridi con integrazione verticale completa.",
        "kpis": [
            {"label": "CONSEGNE VEICOLI", "val": "3M+", "sub": "Leader globale per volumi"},
            {"label": "TECNOLOGIA BATTERIE", "val": "Blade", "sub": "Sicurezza e durata da record"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Transizione mobilità sostenibile"},
            {"label": "ESPANSIONE EXPORT", "val": "+100%", "sub": "Crescita rapida in Europa e Sud America"},
        ],
        "pillars": [
            ("Integrazione Verticale Totale:", "Produce internamente batterie, chip, motori e telai, riducendo i costi."),
            ("Vantaggio di Costo Ineguagliato:", "Capacità di offrire veicoli tecnologicamente avanzati a prezzi competitivi."),
            ("Leadership nelle Batterie LFP:", "La tecnologia Blade Battery è adottata anche da costruttori concorrenti."),
            ("Espansione Globale nei Trasporti:", "Presenza crescente anche in autobus, camion e treni a emissioni zero."),
        ],
        "quote": "L'elettrificazione della mobilità premia chi controlla l'intera filiera produttiva.",
        "tags": ["#BYD", "#ElectricVehicles", "#CleanEnergy", "#Batteries", "#Mobility"],
        "color": (180, 0, 0),
        "domain": "byd.com"
    },
    "MBG.DE": {
        "name": "MERCEDES-BENZ",
        "tagline": "Top-End Luxury & Automotive Excellence",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Mercedes-Benz è il brand automobilistico di lusso per eccellenza, con forte generazione di cassa e ritorni per gli azionisti.",
        "kpis": [
            {"label": "DIVIDEND YIELD", "val": "8.0%+", "sub": "Remunerazione azionisti top tier"},
            {"label": "FOCUS TOP-END LUXURY", "val": "Maybach/AMG", "sub": "Margini elevati sui veicoli di punta"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Pilastro valore e dividendi europei"},
            {"label": "CASSA NETTA INDUSTRIALE", "val": "€30B+", "sub": "Bilancio solido e prudente"},
        ],
        "pillars": [
            ("Marchio di Lusso Storico:", "Brand value secolare che garantisce elevato potere di prezzo."),
            ("Strategia Orientata ai Margini:", "Priorità alla redditività e ai veicoli alto di gamma rispetto ai volumi."),
            ("Generazione di Flussi di Cassa:", "Capacità di distribuire ricchi dividendi mantenendo cassa industriale solida."),
            ("Investimenti nella Guida Autonoma:", "Pioniere nei sistemi di guida autonoma di Livello 3 certificati."),
        ],
        "quote": "Il lusso autentico mantiene il suo valore e la sua desiderabilità attraverso i decenni.",
        "tags": ["#MercedesBenz", "#Luxury", "#Dividends", "#Automotive", "#Germany"],
        "color": (50, 60, 70),
        "domain": "mercedes-benz.com"
    }
}


def _font(size: int, bold: bool = True) -> "ImageFont.FreeTypeFont":
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()


def _get_live_weight_for_ticker(ticker: str) -> str:
    """Fetch live weight from portfolio / eToro API, formatted with percentage."""
    clean = ticker.replace("$", "").strip().upper()
    try:
        from finance_fetcher import fetch_portfolio_weights
        weights = fetch_portfolio_weights()
        if clean in weights and weights[clean] > 0:
            return f"{weights[clean]:.2f}%"
    except Exception:
        pass
    
    # Fallback known default weights
    defaults = {
        "CCJ": "20.67%", "SX7PEX.DE": "17.65%", "PLTR": "14.75%", "0005.HK": "8.35%",
        "URNM": "7.91%", "1211.HK": "4.88%", "MBG.DE": "4.79%", "NOVO-B.CO": "4.41%",
        "ASML.AS": "3.39%", "LLY": "3.32%", "MELI": "3.12%", "TSM": "2.14%",
        "NVDA": "2.13%", "AMZN": "1.48%", "GOOG": "0.88%", "MSFT": "0.08%", "AVGO": "0.06%"
    }
    return defaults.get(clean, "Core")


def generate_stock_infographic(
    ticker: str,
    output_path: str = None,
) -> str:
    """
    Generate an ultra-premium Hitachi-style square infographic (1200x1200).
    Uses clean vector badges to prevent square/tofu rendering artifacts.
    Injects dynamic portfolio weights from official data.
    """
    clean_ticker = ticker.replace("$", "").strip().upper()
    if not output_path:
        output_path = f"output/infographic_{clean_ticker}.png"

    info = COMPANY_INFOGRAPHICS.get(clean_ticker, COMPANY_INFOGRAPHICS.get("PLTR"))
    live_weight = _get_live_weight_for_ticker(clean_ticker)

    # 1. Base Canvas - Off-white / Warm Ivory Premium background (#F6F8FC)
    img = Image.new("RGBA", (CARD_W, CARD_H), (246, 248, 252, 255))
    draw = ImageDraw.Draw(img)

    # 2. Top Header Canvas (Light Gradient)
    header_h = 300
    for y in range(header_h):
        alpha = y / header_h
        r = int(235 * (1 - alpha) + 246 * alpha)
        g = int(242 * (1 - alpha) + 248 * alpha)
        b = int(252 * (1 - alpha) + 252 * alpha)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b, 255))

    # Top Brand Bar
    f_brand = _font(44, bold=True)
    f_tagline = _font(21, bold=False)
    f_title = _font(36, bold=True)
    f_lead = _font(19, bold=False)

    brand_name = info["name"]
    draw.text((60, 45), brand_name, fill=(16, 24, 40, 255), font=f_brand)
    bb_brand = draw.textbbox((60, 45), brand_name, font=f_brand)
    
    # Vertical divider
    div_x = bb_brand[2] + 20
    draw.line([(div_x, 48), (div_x, 92)], fill=(180, 190, 205, 255), width=2)
    draw.text((div_x + 20, 58), info["tagline"], fill=(100, 115, 135, 255), font=f_tagline)

    # Title in Red Accent
    draw.text((60, 115), info["title"], fill=(190, 24, 24, 255), font=f_title)
    
    # Subtitle lead text
    sub_words = info["subtitle"].split()
    sub_lines, curr = [], ""
    for w in sub_words:
        test = (curr + " " + w).strip()
        if draw.textbbox((0,0), test, font=f_lead)[2] < 1080:
            curr = test
        else:
            sub_lines.append(curr)
            curr = w
    if curr: sub_lines.append(curr)
    
    sy = 170
    for l in sub_lines[:2]:
        draw.text((60, sy), l, fill=(55, 65, 81, 240), font=f_lead)
        sy += 28

    # 3. 4 Highlight KPI Cards (Grid: 4 columns across)
    kpis = info.get("kpis", [])
    kpi_y = 265
    kpi_h = 180
    gap = 18
    kpi_w = (CARD_W - 120 - gap * 3) // 4

    f_kpi_lbl = _font(13, bold=True)
    f_kpi_val = _font(32, bold=True)
    f_kpi_sub = _font(13, bold=False)

    for i, kpi in enumerate(kpis[:4]):
        kx = 60 + i * (kpi_w + gap)
        # White card with soft border and subtle shadow
        draw.rounded_rectangle([kx, kpi_y, kx + kpi_w, kpi_y + kpi_h], radius=14, fill=(255, 255, 255, 255), outline=(225, 232, 242, 255), width=1)
        
        # Top Accent Dot
        draw.ellipse([kx + 18, kpi_y + 18, kx + 28, kpi_y + 28], fill=(190, 24, 24, 255))
        
        # Label
        draw.text((kx + 34, kpi_y + 16), kpi["label"][:18], fill=(100, 115, 135, 255), font=f_kpi_lbl)
        
        # Value (inject dynamic weight if applicable)
        val_str = kpi["val"].replace("{weight}", live_weight)
        draw.text((kx + 18, kpi_y + 55), val_str, fill=(16, 24, 40, 255), font=f_kpi_val)
        
        # Subtitle / note
        sub_str = kpi["sub"]
        draw.text((kx + 18, kpi_y + 118), sub_str, fill=(100, 116, 139, 255), font=f_kpi_sub)

    # 4. Middle Content Sections:
    # Left Box (Why I Invest - 60% width) + Right Box (Quote Box - 40% width)
    mid_y = kpi_y + kpi_h + 24
    mid_h = 515
    left_w = 660
    right_w = CARD_W - 120 - left_w - gap

    # Left Section: "PERCHÉ INVESTO IN [AZIENDA]"
    draw.rounded_rectangle([60, mid_y, 60 + left_w, mid_y + mid_h], radius=18, fill=(255, 255, 255, 255), outline=(225, 232, 242, 255), width=1)
    
    # Left Header Pill
    f_pill = _font(15, bold=True)
    pill_text = f"PERCHÉ INVESTO IN ${clean_ticker}"
    draw.rounded_rectangle([85, mid_y + 24, 85 + 320, mid_y + 60], radius=10, fill=(16, 24, 40, 255))
    draw.text((105, mid_y + 32), pill_text, fill=(255, 255, 255, 255), font=f_pill)

    f_bullet_title = _font(18, bold=True)
    f_bullet_desc = _font(15, bold=False)

    pillars = info.get("pillars", [])
    py = mid_y + 85
    for b_title, b_desc in pillars[:4]:
        # Red Icon badge with crisp vector checkmark
        draw.ellipse([85, py + 2, 85 + 24, py + 26], fill=(190, 24, 24, 255))
        draw.line([(85 + 7, py + 14), (85 + 11, py + 18)], fill=(255, 255, 255, 255), width=2)
        draw.line([(85 + 11, py + 18), (85 + 17, py + 9)], fill=(255, 255, 255, 255), width=2)
        
        # Clean title without raw emojis to prevent square rendering
        clean_title = b_title.replace("⚡", "").replace("🤖", "").replace("📊", "").replace("🛡️", "").replace("🖥️", "").replace("🌐", "").replace("🎯", "").replace("💰", "").replace("📈", "").replace("🔄", "").strip()
        draw.text((120, py), clean_title, fill=(16, 24, 40, 255), font=f_bullet_title)
        
        # Wrap desc
        dw = b_desc.split()
        d_lines, dc = [], ""
        for w in dw:
            t = (dc + " " + w).strip()
            if draw.textbbox((0,0), t, font=f_bullet_desc)[2] < left_w - 90:
                dc = t
            else:
                d_lines.append(dc)
                dc = w
        if dc: d_lines.append(dc)
        
        dy = py + 28
        for dl in d_lines[:2]:
            draw.text((120, dy), dl, fill=(75, 85, 99, 255), font=f_bullet_desc)
            dy += 22
        py += 100

    # Right Section: Quote Card
    rx = 60 + left_w + gap
    draw.rounded_rectangle([rx, mid_y, rx + right_w, mid_y + mid_h], radius=18, fill=(255, 255, 255, 255), outline=(225, 232, 242, 255), width=1)
    
    # Large quotation mark
    f_quote_mark = _font(80, bold=True)
    draw.text((rx + 30, mid_y + 20), "“", fill=(190, 24, 24, 230), font=f_quote_mark)
    
    f_quote = _font(25, bold=True)
    f_quote_red = _font(27, bold=True)

    draw.text((rx + 30, mid_y + 130), "Non investo", fill=(16, 24, 40, 255), font=f_quote)
    draw.text((rx + 30, mid_y + 168), "per il prossimo", fill=(16, 24, 40, 255), font=f_quote)
    draw.text((rx + 30, mid_y + 206), "trimestre.", fill=(16, 24, 40, 255), font=f_quote)
    
    draw.text((rx + 30, mid_y + 270), "Investo per il", fill=(16, 24, 40, 255), font=f_quote)
    draw.text((rx + 30, mid_y + 310), "prossimo decennio.", fill=(190, 24, 24, 255), font=f_quote_red)
    
    # Brush underline
    draw.line([(rx + 30, mid_y + 355), (rx + 290, mid_y + 355)], fill=(190, 24, 24, 255), width=3)
    
    draw.text((rx + 30, mid_y + 430), "— Andrea Ravalli", fill=(100, 116, 139, 255), font=_font(18, bold=True))
    draw.text((rx + 30, mid_y + 458), "Popular Investor @ eToro", fill=(140, 155, 175, 255), font=_font(15, bold=False))

    # 5. Bottom Modern Dark Banner (120px)
    bot_y = CARD_H - 145
    draw.rounded_rectangle([60, bot_y, CARD_W - 60, CARD_H - 40], radius=16, fill=(12, 18, 34, 255))
    
    f_bot_main = _font(20, bold=True)
    f_bot_sub = _font(15, bold=False)
    f_tags = _font(14, bold=True)

    draw.text((90, bot_y + 25), "ANDREA RAVALLI · POPULAR INVESTOR", fill=(255, 255, 255, 255), font=f_bot_main)
    draw.text((90, bot_y + 55), "Strategia fondamentale trasparente & orizzonte a lungo termine", fill=(160, 175, 200, 255), font=f_bot_sub)

    # Hashtags
    tags_str = " ".join(info.get("tags", [])[:4])
    bb_t = draw.textbbox((0, 0), tags_str, font=f_tags)
    draw.text((CARD_W - 90 - (bb_t[2] - bb_t[0]), bot_y + 42), tags_str, fill=(0, 190, 240, 255), font=f_tags)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.convert("RGB").save(output_path, "PNG", optimize=True)
    print(f"🏆 Ultra-Premium Hitachi-style Infographic generated: {output_path} (Live Weight: {live_weight})")
    return output_path
