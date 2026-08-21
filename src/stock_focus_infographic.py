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
import json
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

LOGO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logos")
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
    "MRVL": {
        "name": "MARVELL",
        "tagline": "AI Data Center Connectivity & Custom Silicon",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Marvell progetta semiconduttori essenziali per la connettività ottica ad altissima velocità e chip custom per i supercomputer AI.",
        "kpis": [
            {"label": "CRESCITA REVENUE AI", "val": "+50%+", "sub": "Domanda record per chip data center"},
            {"label": "LEADERSHIP PAM4 DSP", "val": "Top 1", "sub": "Standard de facto interconnessioni"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Asset strategico infrastruttura AI"},
            {"label": "PIPELINE CUSTOM SILICON", "val": "Tier-1", "sub": "Accordi con i maggiori hyperscaler"},
        ],
        "pillars": [
            ("Monopolio Interconnessioni Ottiche:", "I chip elettro-ottici PAM4 collegano i cluster di GPU con minima latenza."),
            ("Custom ASIC per Hyperscaler:", "Sviluppo di chip proprietari su misura per i maggiori giganti cloud."),
            ("Forte Espansione dei Margini:", "La quota crescente di prodotti AI accelera la redditività operativa."),
            ("Barriere Tecnologiche Elevate:", "Know-how proprietario fondamentale per scalare le reti dei data center."),
        ],
        "quote": "La potenza di calcolo senza connettività ad altissima velocità non può scalare: Marvell è il ponte dell'AI.",
        "tags": ["#Marvell", "#Semiconductors", "#AIDataCenter", "#Networking", "#CustomSilicon"],
        "color": (0, 90, 180),
        "domain": "marvell.com"
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
    "VOW3.DE": {
        "name": "VOLKSWAGEN",
        "tagline": "Global Mobility & Iconic Brand Portfolio",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Volkswagen AG è uno dei maggiori costruttori automobilistici mondiali (Porsche, Audi, VW) con solida cassa e dividendi generosi.",
        "kpis": [
            {"label": "DIVIDEND YIELD", "val": "7.5%+", "sub": "Forte ritorno di capitale"},
            {"label": "MARCHI ICONICI", "val": "Porsche/Audi", "sub": "Presenza in tutti i segmenti"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Pilastro valore e dividendi europei"},
            {"label": "SCALA PRODUTTIVA", "val": "9M+ Veicoli", "sub": "Leadership globale dell'automotive"},
        ],
        "pillars": [
            ("Portafoglio Marchi Leader:", "Ampia diversificazione dai veicoli di massa al lusso e sportivo."),
            ("Piattaforme Unificate:", "Sinergie di scala sui pianali e sulle architetture software di nuova generazione."),
            ("Remunerazione Azionisti:", "Dividendo elevato supportato dalla stabilità dei flussi di cassa industriali."),
            ("Espansione Elettrica & Batterie:", "Investimenti capillari nella produzione di celle e mobilità sostenibile."),
        ],
        "quote": "La scala globale e la solidità patrimoniale guidano la trasformazione della mobilità.",
        "tags": ["#Volkswagen", "#Automotive", "#Dividends", "#ValueInvesting", "#Germany"],
        "color": (0, 70, 150),
        "domain": "volkswagen.com"
    },
    "AMZN": {
        "name": "AMAZON",
        "tagline": "Cloud Infrastructure & Global E-Commerce",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Amazon è il leader mondiale indiscusso nel cloud computing (AWS) e nell'infrastruttura logistica di e-commerce.",
        "kpis": [
            {"label": "CRESCITA AWS", "val": "+19%", "sub": "Accelerazione AI e workload cloud"},
            {"label": "MARGINE OPERATIVO", "val": "11%+", "sub": "Leva operativa ed efficienza record"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Pilastro tecnologia e commercio"},
            {"label": "FLUSSO DI CASSA LIBERO", "val": "$50B+", "sub": "Massiccia generazione di cassa"},
        ],
        "pillars": [
            ("Monopolio AWS nel Cloud:", "AWS è la spina dorsale di internet e dell'infrastruttura AI aziendale."),
            ("Fossato Logistico Globale:", "Rete logistica e programma Prime con altissima fidelizzazione dei clienti."),
            ("Boom della Pubblicità Digitale:", "Il segmento advertising ad altissimo margine cresce oltre il 20%."),
            ("Efficienza Operativa con AI:", "Automazione e robotica nei magazzini aumentano costantemente i margini."),
        ],
        "quote": "Nel business, il miglior modo per avere successo è essere ossessionati dal cliente a lungo termine.",
        "tags": ["#Amazon", "#AWS", "#CloudComputing", "#Ecommerce", "#TechGiant"],
        "color": (255, 153, 0),
        "domain": "amazon.com"
    },
    "GOOG": {
        "name": "ALPHABET / GOOGLE",
        "tagline": "Search, Google Cloud & Gemini AI",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Alphabet controlla l'accesso alle informazioni globali tramite Google Search, YouTube, Android e Google Cloud.",
        "kpis": [
            {"label": "QUOTA GOOGLE SEARCH", "val": ">90%", "sub": "Monopolio globale delle ricerche"},
            {"label": "CRESCITA GOOGLE CLOUD", "val": "+29%", "sub": "Margini cloud in forte espansione"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Leader AI e internet economy"},
            {"label": "CASSA E LIQUIDITÀ", "val": "$100B+", "sub": "Fortezza finanziaria con buyback"},
        ],
        "pillars": [
            ("Fossato Imbattibile nella Ricerca:", "Google Search e YouTube rimangono i punti di riferimento per la pubblicità."),
            ("Accelerazione Google Cloud & AI:", "Gemini e le infrastrutture TPU attraggono le migliori startup e corporate."),
            ("Diversificazione Ecosistema:", "Android, Waymo (guida autonoma) e sottoscrizioni YouTube Premium in crescita."),
            ("Solidità Finanziaria Straordinaria:", "Bilancio blindato con dividendi e continui riacquisti di azioni proprie."),
        ],
        "quote": "L'accesso universale alla conoscenza è la più grande leva di progresso e creazione di valore.",
        "tags": ["#Alphabet", "#Google", "#AI", "#GoogleCloud", "#TechLeader"],
        "color": (66, 133, 244),
        "domain": "google.com"
    },
    "MSFT": {
        "name": "MICROSOFT",
        "tagline": "Enterprise Cloud & AI Ecosystem",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Microsoft è il fornitore essenziale di software enterprise, produttività e cloud infrastructure (Azure) nel mondo.",
        "kpis": [
            {"label": "CRESCITA AZURE", "val": "+30%+", "sub": "Infrastruttura cloud AI leader"},
            {"label": "MARGINE OPERATIVO", "val": "45%", "sub": "Redditività eccezionale"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Infrastruttura software core"},
            {"label": "DIVIDENDO & BUYBACK", "val": "$30B+", "sub": "Crescita costante del dividendo"},
        ],
        "pillars": [
            ("Partnership Esclusiva con OpenAI:", "Integrazione di Copilot e ChatGPT in tutta la suite Microsoft 365 e Azure."),
            ("Fossato Software Enterprise:", "Windows, Office 365, Teams e LinkedIn sono insostituibili per le aziende."),
            ("Azure Cloud Platform:", "Crescita costante e contratti pluriennali con le maggiori multinazionali."),
            ("Rating Creditizio AAA:", "Uno dei rarissimi bilanci al mondo con rating di credito superiore a molti stati sovrani."),
        ],
        "quote": "La nostra missione è consentire a ogni persona e organizzazione di ottenere di più.",
        "tags": ["#Microsoft", "#Azure", "#OpenAI", "#Cloud", "#Software"],
        "color": (0, 164, 239),
        "domain": "microsoft.com"
    },
    "ENI.MI": {
        "name": "ENI",
        "tagline": "Global Energy & Plenitude Transition",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Eni è una delle major energetiche più efficienti al mondo, con modello satellitare e dividendi generosi.",
        "kpis": [
            {"label": "DIVIDEND YIELD", "val": "6.5%+", "sub": "Dividendi trimestrali costanti"},
            {"label": "VALORE SATELLITI", "val": "Plenitude", "sub": "Valorizzazione energie rinnovabili"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Pilastro dividendi e sicurezza energetica"},
            {"label": "BREAK-EVEN BRENT", "val": "<$30/bbl", "sub": "Efficienza nei costi di estrazione"},
        ],
        "pillars": [
            ("Esplorazione e Nuove Scoperte:", "Storico imbattibile nella scoperta di giacimenti a basso costo di sviluppo."),
            ("Strategia Satellitare:", "Quotazione e partnership su asset specifici (Plenitude, Enilive) per sbloccare valore."),
            ("Remunerazione Azionisti Generosa:", "Distribuzione del cash flow tramite dividendi in crescita e buyback continui."),
            ("Transizione e Bioraffinazione:", "Leader europeo nei biocarburanti per aviazione e mobilità sostenibile."),
        ],
        "quote": "L'energia del futuro richiede pragmatismo: sicurezza degli approvvigionamenti e decarbonizzazione.",
        "tags": ["#Eni", "#Energy", "#Dividends", "#OilGas", "#CleanEnergy"],
        "color": (255, 204, 0),
        "domain": "eni.com"
    },
    "PRY.MI": {
        "name": "PRYSMIAN",
        "tagline": "Cabling Systems & Energy Transition",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Prysmian è il leader mondiale assoluto nei cavi per l'elettrificazione, i parchi eolici offshore e la fibra ottica.",
        "kpis": [
            {"label": "ORDER BACKLOG", "val": "€18B+", "sub": "Ordini record per interconnessioni"},
            {"label": "QUOTA MERCATO CAVI", "val": "Leader", "sub": "Numero 1 al mondo per fatturato"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Infrastruttura elettrificazione"},
            {"label": "MARGINI EBITDA", "val": "+15% YoY", "sub": "Leva operativa e sinergie Encore"},
        ],
        "pillars": [
            ("Monopolio nei Cavi Alta Tensione:", "Fornitore insostituibile per i collegamenti tra reti nazionali e parchi eolici."),
            ("Megatrend Elettrificazione & Grid:", "Decenni di investimenti necessari per modernizzare le reti elettriche mondiali."),
            ("Integrazione di Encore Wire:", "Espansione massiccia nel mercato nordamericano con forti sinergie commerciali."),
            ("Barriere all'Entrata Elevatissime:", "Navi posacavi proprietarie e brevetti tecnologici unici al mondo."),
        ],
        "quote": "Non c'è transizione energetica né intelligenza artificiale senza cavi che trasportano potenza e dati.",
        "tags": ["#Prysmian", "#Electrification", "#EnergyGrid", "#Cables", "#Infrastructure"],
        "color": (0, 80, 160),
        "domain": "prysmiangroup.com"
    },
    "BMW.DE": {
        "name": "BMW",
        "tagline": "Premium Automotive & Neue Klasse",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "BMW è il costruttore premium leader mondiale per profittabilità, flessibilità produttiva e brand value.",
        "kpis": [
            {"label": "DIVIDEND YIELD", "val": "6.0%+", "sub": "Solida remunerazione azionisti"},
            {"label": "MARGINE AUTO (EBIT)", "val": "8-10%", "sub": "Ai vertici del settore automobilistico"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Valore e manifattura premium"},
            {"label": "PIATTAFORMA NEUE KLASSE", "val": "2025+", "sub": "Nuova generazione elettrica scalabile"},
        ],
        "pillars": [
            ("Flessibilità Produttiva Unica:", "Capacità di produrre motori termici, ibridi ed elettrici sulla stessa linea."),
            ("Brand Value Iconico:", "Fortissimo potere di prezzo e fedeltà dei clienti in Europa, USA e Asia."),
            ("Generazione di Cassa Industriale:", "Cassa netta solida che finanzia ricerca, dividendi e riacquisto azioni."),
            ("Leadership nell'Innovazione:", "Batterie cilindriche di nuova generazione con maggiore densità ed efficienza."),
        ],
        "quote": "Il piacere di guidare unito all'eccellenza ingegneristica crea un valore intramontabile.",
        "tags": ["#BMW", "#Automotive", "#Luxury", "#Dividends", "#NeueKlasse"],
        "color": (0, 102, 177),
        "domain": "bmwgroup.com"
    },
    "RACE": {
        "name": "FERRARI",
        "tagline": "Ultra-Luxury & High Performance Supercars",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Ferrari è il brand di lusso assoluto con portafoglio ordini blindato per oltre 2 anni e margini incomparabili.",
        "kpis": [
            {"label": "MARGINE EBITDA", "val": "38%+", "sub": "Margini paragonabili all'alta moda"},
            {"label": "ORDER BOOK", "val": "2+ Anni", "sub": "Produzione interamente venduta"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Marchio di lusso e pricing power"},
            {"label": "PERSONALIZZAZIONE", "val": "+20%", "sub": "Optional su misura ad altissimo margine"},
        ],
        "pillars": [
            ("Potere di Prezzo Incomparabile:", "I clienti accettano qualsiasi aumento di prezzo pur di avere una Ferrari."),
            ("Scarsità Controllata:", "Produzione deliberatamente inferiore alla domanda globale per proteggere il valore."),
            ("Elettrificazione ed E-Building:", "Nuovo impianto per supercar ibride e prima Ferrari 100% elettrica nel 2025."),
            ("Resilienza alle Crisi Economiche:", "Clientela ultra-facoltosa totalmente insensibile ai cicli macroeconomici."),
        ],
        "quote": "La Ferrari è un sogno: la gente sogna di possedere questa vettura speciale e per la maggior parte resterà un sogno.",
        "tags": ["#Ferrari", "#Luxury", "#Supercars", "#PricingPower", "#MadeInItaly"],
        "color": (220, 0, 0),
        "domain": "ferrari.com"
    },
    "WMT": {
        "name": "WALMART",
        "tagline": "Global Retail & Omnichannel Ecosystem",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Walmart è il leader mondiale assoluto del retail con una trasformazione digitale ed e-commerce ad altissima redditività.",
        "kpis": [
            {"label": "FATTURATO GLOBALE", "val": "$650B+", "sub": "Scala operativa ineguagliata"},
            {"label": "CRESCITA E-COMMERCE", "val": "+22%", "sub": "Adozione omnichannel in forte accelerazione"},
            {"label": "PESO IN PORTAFOGLIO", "val": "{weight}", "sub": "Pilastro difensivo di consumo di base"},
            {"label": "PUBBLICITÀ (WALMART CONNECT)", "val": "+26%", "sub": "Segmento a più alto margine operativo"},
        ],
        "pillars": [
            ("Fossato Difensivo & Scala:", "La più grande rete logistica e potere contrattuale con i fornitori al mondo."),
            ("Espansione Digitale & Prime:", "Crescita a doppia cifra delle vendite online e dell'abbonamento Walmart+."),
            ("Monetizzazione Dati & Ads:", "Crescita rapida dell'advertising retail ad altissima marginalità."),
            ("Resilienza Macroeconomica:", "Beni di prima necessità a prezzi imbattibili in qualsiasi ciclo economico."),
        ],
        "quote": "La convenienza e la vicinanza al cliente sono i pilastri che non passeranno mai di moda.",
        "tags": ["#Walmart", "#Retail", "#Omnichannel", "#ConsumerStaples", "#ValueInvesting"],
        "color": (0, 113, 206),
        "domain": "walmart.com"
    },
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


def _fetch_logo(ticker: str, domain: str = None) -> Optional["Image.Image"]:
    """Fetch company logo from committed assets/logos/, cache, or remote."""
    if not PIL_AVAILABLE:
        return None
    clean = ticker.replace("$", "").strip().upper()
    base_sym = clean.split(".")[0]

    # 1. Check committed assets/logos/
    for check_sym in [clean, base_sym, f"{clean}.US" if "." not in clean else None]:
        if not check_sym:
            continue
        repo_path = os.path.join(LOGO_DIR, f"{check_sym}.png")
        if os.path.exists(repo_path) and os.path.getsize(repo_path) > 200:
            try:
                return Image.open(repo_path).convert("RGBA")
            except Exception:
                pass

    # 2. Check assets/logo_cache/
    os.makedirs(LOGO_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(LOGO_CACHE_DIR, f"{clean}.png")
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 200:
        try:
            return Image.open(cache_path).convert("RGBA")
        except Exception:
            pass

    # 3. Remote fetch via logo providers
    if not domain:
        domain = f"{clean.lower()}.com"

    urls = [
        f"https://img.logo.dev/{domain}?token=pk_anonymous&size=160&format=png",
        f"https://cdn.tickerlogos.com/{domain}",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200 and len(resp.content) > 300:
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                img.save(cache_path)
                return img
        except Exception:
            continue
    return None


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
    
    # Fallback known actual live portfolio weights
    defaults = {
        "NOVO-B.CO": "4.30%", "CCJ": "4.01%", "ENI.MI": "3.94%", "PRY.MI": "3.86%",
        "AMZN": "3.80%", "SX7PEX.DE": "3.43%", "BMW.DE": "3.30%", "NVDA": "3.30%",
        "HUM": "3.19%", "GOOG": "3.14%", "ENEL.MI": "2.94%", "PLTR": "2.87%",
        "TSM": "2.87%", "MELI": "2.72%", "PYPL": "2.56%",
        "1211.HK": "2.35%", "MSFT": "2.19%", "LLY": "2.19%", "0005.HK": "2.04%",
        "VOW3.DE": "1.24%", "AVGO": "0.05%"
    }
    return defaults.get(clean, "2.50%")


def fetch_dynamic_company_infographic_data(ticker: str) -> dict:
    """
    Fetch structured data for any company. Prioritizes curated dictionary,
    falling back to Gemini AI synthesis or dynamic template.
    """
    clean_ticker = ticker.replace("$", "").strip().upper()

    # 1. First priority: Check curated dictionary for known core holdings
    if clean_ticker in COMPANY_INFOGRAPHICS:
        return COMPANY_INFOGRAPHICS[clean_ticker]

    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "infographics_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{clean_ticker}.json")

    # 2. Check local cache (fresh for 7 days)
    if os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            if (time.time() - mtime) < 7 * 86400:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if cached and "kpis" in cached and "pillars" in cached:
                        return cached
        except Exception:
            pass

    # 3. Resolve company name from portfolio config
    from portfolio_manager import load_config
    config = load_config()
    tickers = config.get("tickers", {})
    yahoo_ticker, company_name = tickers.get(clean_ticker, (clean_ticker, clean_ticker))
    live_weight = _get_live_weight_for_ticker(clean_ticker)

    # 4. Call Gemini AI if API key is available
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            prompt = f"""Analizza in profondità l'azienda {company_name} (${clean_ticker}).
Il peso attuale in portafoglio è: {live_weight}.
Fornisci in formato JSON strutturato (senza markdown extra):
{{
  "name": "{company_name.upper()}",
  "tagline": "Slogan aziendale o posizionamento competitivo (max 5 parole)",
  "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
  "subtitle": "Sintesi chiara della tesi di investimento (max 20 parole)",
  "kpis": [
    {{"label": "KPI 1 (es. CRESCITA RICAVI)", "val": "DATO ATTUALE (es. +25%)", "sub": "breve dettaglio"}},
    {{"label": "KPI 2 (es. MARGINE OPERATIVO)", "val": "DATO ATTUALE (es. 35%)", "sub": "breve dettaglio"}},
    {{"label": "PESO IN PORTAFOGLIO", "val": "{live_weight}", "sub": "Allocazione gestita nel portafoglio"}},
    {{"label": "KPI 4 (es. CASSA / DIVIDENDI)", "val": "DATO ATTUALE (es. $5B+)", "sub": "breve dettaglio"}}
  ],
  "pillars": [
    ["Fossato Competitivo:", "Spiegazione del moat o barriere all'entrata in 1 riga."],
    ["Catalizzatore di Crescita:", "Spiegazione del principale driver di crescita attuale in 1 riga."],
    ["Solidità e Finanze:", "Spiegazione della salute finanziaria / cash flow in 1 riga."],
    ["Visione Decennale:", "Perché è un titolo vincente per il lungo termine in 1 riga."]
  ],
  "quote": "Frase iconica sulla visione strategica di lungo termine (max 18 parole).",
  "tags": ["#{clean_ticker.replace('.', '_')}", "#Investing", "#Portfolio", "#LongTerm", "#Value"],
  "color": [20, 100, 200]
}}"""

            config_gen = types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json"
            )

            models_to_try = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash"]
            for model_name in models_to_try:
                try:
                    res = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config_gen,
                    )
                    if res and res.text:
                        parsed = json.loads(res.text)
                        if parsed.get("name") and parsed.get("kpis"):
                            for k in parsed.get("kpis", []):
                                if "PESO" in k.get("label", "").upper():
                                    k["val"] = live_weight
                            with open(cache_file, "w", encoding="utf-8") as f:
                                json.dump(parsed, f, indent=2, ensure_ascii=False)
                            print(f"✓ Dynamically generated and cached AI infographic data for {clean_ticker} using {model_name}")
                            return parsed
                except Exception as m_err:
                    print(f"   ⚠️ Infographic generation model {model_name} failed: {m_err}")
                    time.sleep(1)
        except Exception as exc:
            print(f"⚠️ Dynamic Gemini infographic generation fallback for {clean_ticker}: {exc}")

    return {
        "name": company_name.upper(),
        "tagline": f"Conviction Holding (${clean_ticker})",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": f"{company_name} (${clean_ticker}) è una posizione strategica selezionata per fondamentali solidi e crescita di lungo termine.",
        "kpis": [
            {"label": "STRATEGIA", "val": "Core", "sub": "Selezione macro & fondamentale"},
            {"label": "PESO IN PORTAFOGLIO", "val": live_weight, "sub": "Allocazione gestita"},
            {"label": "ORIZZONTE", "val": "Lungo Termine", "sub": "Creazione di valore nel tempo"},
            {"label": "MONITORAGGIO", "val": "Attivo", "sub": "Gestione costante del rischio"},
        ],
        "pillars": [
            ("Posizionamento di Settore:", f"{company_name} opera con un solido posizionamento competitivo nel proprio mercato."),
            ("Tesi d'Investimento Chiara:", "Esposizione mirata alla crescita e alla generazione di valore nel lungo termine."),
            ("Gestione del Rischio:", "Dimensionamento calibrato per ottimizzare il profilo rischio/rendimento."),
            ("Integrazione di Portafoglio:", "Contribuisce alla diversificazione globale e alla resilienza della strategia."),
        ],
        "quote": "La qualità dei fondamentali e la visione di lungo periodo sono il vero motore dei rendimenti.",
        "tags": [f"#{clean_ticker.replace('.', '_')}", "#Portfolio", "#Investing", "#LongTerm", "#Value"],
        "color": (20, 100, 200),
        "domain": "etoro.com"
    }


def generate_stock_infographic(
    ticker: str,
    output_path: str = None,
) -> str:
    """
    Generate an ultra-premium Hitachi-style square infographic (1200x1200).
    Uses clean vector badges to prevent square/tofu rendering artifacts.
    Injects dynamic portfolio weights with auto-scaling text and logo support.
    """
    clean_ticker = ticker.replace("$", "").strip().upper()
    if not output_path:
        output_path = f"output/infographic_{clean_ticker}.png"

    # Always fetch data with curated priority or AI synthesis
    info = fetch_dynamic_company_infographic_data(clean_ticker)
    live_weight = _get_live_weight_for_ticker(clean_ticker)

    # Accent color
    accent_color = info.get("color", (190, 24, 24))
    if isinstance(accent_color, list):
        accent_color = tuple(accent_color)

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

    # Top Brand Bar with Company Logo
    f_brand = _font(44, bold=True)
    f_tagline = _font(21, bold=False)
    f_title = _font(36, bold=True)
    f_lead = _font(19, bold=False)

    brand_name = info["name"]
    logo_img = _fetch_logo(clean_ticker, domain=info.get("domain"))

    start_x = 60
    if logo_img:
        try:
            # Draw rounded logo box
            logo_box_size = 58
            logo_resized = logo_img.resize((logo_box_size - 8, logo_box_size - 8), Image.Resampling.LANCZOS)
            draw.rounded_rectangle([60, 42, 60 + logo_box_size, 42 + logo_box_size], radius=12, fill=(255, 255, 255, 255), outline=(215, 225, 238, 255), width=1)
            # Paste logo centered
            img.alpha_composite(logo_resized, (60 + 4, 42 + 4))
            draw = ImageDraw.Draw(img)
            start_x = 60 + logo_box_size + 18
        except Exception:
            start_x = 60

    draw.text((start_x, 45), brand_name, fill=(16, 24, 40, 255), font=f_brand)
    bb_brand = draw.textbbox((start_x, 45), brand_name, font=f_brand)
    
    # Vertical divider
    div_x = bb_brand[2] + 20
    draw.line([(div_x, 48), (div_x, 92)], fill=(180, 190, 205, 255), width=2)
    draw.text((div_x + 20, 58), info.get("tagline", f"Asset ${clean_ticker}"), fill=(100, 115, 135, 255), font=f_tagline)

    # Title in Red Accent
    draw.text((60, 115), info.get("title", "TESI D'INVESTIMENTO & HIGHLIGHTS"), fill=(190, 24, 24, 255), font=f_title)
    
    # Subtitle lead text
    sub_words = info.get("subtitle", "").split()
    sub_lines, curr = [], ""
    for w in sub_words:
        test = (curr + " " + w).strip()
        if draw.textbbox((0, 0), test, font=f_lead)[2] < 1080:
            curr = test
        else:
            sub_lines.append(curr)
            curr = w
    if curr:
        sub_lines.append(curr)
    
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

    for i, kpi in enumerate(kpis[:4]):
        kx = 60 + i * (kpi_w + gap)
        # White card with soft border and subtle shadow
        draw.rounded_rectangle([kx, kpi_y, kx + kpi_w, kpi_y + kpi_h], radius=14, fill=(255, 255, 255, 255), outline=(225, 232, 242, 255), width=1)
        
        # Top Accent Dot
        draw.ellipse([kx + 18, kpi_y + 18, kx + 28, kpi_y + 28], fill=(190, 24, 24, 255))
        
        # Auto-fit Label (never cut off like "PORTAFOGLI")
        lbl_text = kpi.get("label", "").strip()
        lbl_font = _font(13, bold=True)
        for sz in [13, 12, 11, 10]:
            test_f = _font(sz, bold=True)
            if draw.textbbox((0, 0), lbl_text, font=test_f)[2] <= (kpi_w - 44):
                lbl_font = test_f
                break
        draw.text((kx + 34, kpi_y + 16), lbl_text, fill=(100, 115, 135, 255), font=lbl_font)
        
        # Value (inject dynamic weight if placeholder present or if label is PESO)
        raw_val = str(kpi.get("val", ""))
        if "{weight}" in raw_val:
            val_str = raw_val.replace("{weight}", live_weight)
        elif "PESO" in lbl_text.upper():
            val_str = live_weight
        else:
            val_str = raw_val

        # Auto-fit value so it NEVER overflows card width
        val_font = _font(32, bold=True)
        max_val_w = kpi_w - 36
        for sz in [32, 28, 24, 20, 18, 16]:
            test_f = _font(sz, bold=True)
            if draw.textbbox((0, 0), val_str, font=test_f)[2] <= max_val_w:
                val_font = test_f
                break
        draw.text((kx + 18, kpi_y + 55), val_str, fill=(16, 24, 40, 255), font=val_font)
        
        # Subtitle / note (auto-fit or wrap)
        sub_str = kpi.get("sub", "").strip()
        sub_font = _font(13, bold=False)
        for sz in [13, 12, 11]:
            test_f = _font(sz, bold=False)
            if draw.textbbox((0, 0), sub_str, font=test_f)[2] <= max_val_w:
                sub_font = test_f
                break
        draw.text((kx + 18, kpi_y + 118), sub_str, fill=(100, 116, 139, 255), font=sub_font)

    # 4. Middle Content Sections:
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
            if draw.textbbox((0, 0), t, font=f_bullet_desc)[2] < left_w - 90:
                dc = t
            else:
                d_lines.append(dc)
                dc = w
        if dc:
            d_lines.append(dc)
        
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

