#!/usr/bin/env python3
"""
Test script to generate previews for all 5 Italian natural recap sessions
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import formatter
import ai_news_generator

def generate_mock_stock_data():
    """Generate mock stock data for testing previews"""
    return {
        'NVDA': {
            'company_name': 'NVIDIA',
            'daily_change': 4.32,
            'weekly_change': 5.21,
            'monthly_change': 15.67,
            'yearly_change': 68.73,
            'has_traded_today': True
        },
        'LLY': {
            'company_name': 'Eli Lilly & Co',
            'daily_change': 2.85,
            'weekly_change': 3.12,
            'monthly_change': 12.34,
            'yearly_change': 55.42,
            'has_traded_today': True
        },
        'PLTR': {
            'company_name': 'Palantir Technologies Inc',
            'daily_change': 1.45,
            'weekly_change': 12.45,
            'monthly_change': 11.89,
            'yearly_change': 115.79,
            'has_traded_today': True
        },
        'MSFT': {
            'company_name': 'Microsoft',
            'daily_change': 1.20,
            'weekly_change': 4.20,
            'monthly_change': 5.42,
            'yearly_change': 22.15,
            'has_traded_today': True
        },
        'AMZN': {
            'company_name': 'Amazon',
            'daily_change': 1.10,
            'weekly_change': 3.85,
            'monthly_change': 6.85,
            'yearly_change': 31.42,
            'has_traded_today': True
        },
        'GOOG': {
            'company_name': 'Alphabet',
            'daily_change': 1.98,
            'weekly_change': 2.15,
            'monthly_change': 4.12,
            'yearly_change': 68.73,
            'has_traded_today': True
        },
        'AVGO': {
            'company_name': 'Broadcom Inc',
            'daily_change': 1.52,
            'weekly_change': 1.10,
            'monthly_change': 8.92,
            'yearly_change': 42.15,
            'has_traded_today': True
        },
        'NOVO-B.CO': {
            'company_name': 'Novo Nordisk',
            'daily_change': 0.85,
            'weekly_change': 8.12,
            'monthly_change': 9.20,
            'yearly_change': 38.12,
            'has_traded_today': True
        },
        'AZN.L': {
            'company_name': 'AstraZeneca',
            'daily_change': 1.20,
            'weekly_change': 1.85,
            'monthly_change': -2.15,
            'yearly_change': 5.42,
            'has_traded_today': True
        },
        'ENEL.MI': {
            'company_name': 'Enel',
            'daily_change': 0.45,
            'weekly_change': 1.12,
            'monthly_change': 3.12,
            'yearly_change': 14.15,
            'has_traded_today': True
        },
        'PRY.MI': {
            'company_name': 'Prysmian',
            'daily_change': 0.65,
            'weekly_change': 3.10,
            'monthly_change': 4.15,
            'yearly_change': 28.12,
            'has_traded_today': True
        }
    }

def print_session_preview(session_name, mock_ai_commentary=None):
    """Generate and print the preview for a session"""
    print("\n" + "=" * 80)
    print(f"🎬 PREVIEW FOR SESSION: {session_name}")
    print("=" * 80)
    
    # Set the environment variable for market session
    os.environ['MARKET_SESSION'] = session_name
    
    # Generate mock stock data
    stock_data = generate_mock_stock_data()
    
    # Setup mock input parameters
    portfolio_daily = 1.15
    portfolio_weekly = 3.25
    portfolio_monthly = 5.12
    
    sheets_data = {
        'five_year_return': 156.0,
        'monthly_performance': 5.12,
        'yearly_performance': 12.3,
        'dividend': None
    }
    
    benchmark_data = {
        'SPX500': 85.0,
        'NSDQ100': 110.0,
        'SWDA.L': 75.0,
        'EUSTX50': 60.0
    }
    
    ath_distance = -1.23
    
    # Temporarily override generate_market_news_recap to return our custom mock text if API key is not present
    original_func = ai_news_generator.generate_market_news_recap
    
    if not os.environ.get('GEMINI_API_KEY') and mock_ai_commentary:
        # Define a mock lambda wrapper
        def mock_generate(*args, **kwargs):
            return "\n" + mock_ai_commentary + "\n"
        ai_news_generator.generate_market_news_recap = mock_generate
        
    try:
        # Call the formatter
        recap = formatter.generate_recap(
            stock_data=stock_data,
            portfolio_daily=portfolio_daily,
            sheets_data=sheets_data,
            benchmark_data=benchmark_data,
            portfolio_weekly=portfolio_weekly,
            portfolio_monthly=portfolio_monthly,
            ath_distance=ath_distance
        )
        
        print(recap)
        print("-" * 80)
        print(f"📊 Length: {len(recap)} characters (Telegram limit: 4000)")
        
        # Verify tag count
        import re
        tags = re.findall(r'\$[A-Za-z0-9\-\.]+', recap)
        # Unique tags
        unique_tags = list(set(tags))
        print(f"🏷️ Unique stock tags used ({len(unique_tags)}): {', '.join(unique_tags)}")
        
    finally:
        # Restore original function
        ai_news_generator.generate_market_news_recap = original_func

def main():
    print("🔮 GENERATING 5 MESSAGE PREVIEWS IN NATURAL ITALIAN 🔮")
    
    # 1. European Market Open
    eu_open_mock = (
        "Buongiorno! Iniziamo una nuova giornata sui mercati europei con un clima piuttosto positivo. "
        "Oggi gli occhi sono tutti puntati su $NOVO-B.CO, che continua a far parlare di sé grazie ai dati "
        "eccezionali sulle vendite dei suoi trattamenti contro l'obesità. Nel settore energetico, $ENEL.MI "
        "mostra una buona intonazione in avvio grazie ad alcune indiscrezioni su nuove collaborazioni "
        "europee per le rinnovabili, mentre $AZN.L beneficia di un upgrade da parte di una primaria banca "
        "d'affari. Troviamo anche un buon riscontro per $PRY.MI, trainata dalla domanda globale di "
        "infrastrutture di rete. Seguiamo con attenzione la sessione!"
    )
    print_session_preview("European market open", eu_open_mock)
    
    # 2. U.S. Market Open
    us_open_mock = (
        "Buongiorno! Ci prepariamo all'apertura di Wall Street con un'atmosfera frizzante. "
        "Riflettori accesi su $NVDA, che ieri sera ha sorpreso ancora una volta il mercato con una trimestrale "
        "da record e stime sulla domanda di chip IA ben superiori alle attese. Ottimo avvio previsto anche per "
        "$MSFT, spinta dalle novità sull'integrazione di Copilot nei servizi cloud. Nel frattempo, seguiamo con "
        "interesse $PLTR dopo l'annuncio di un nuovo importante contratto con il governo federale, e "
        "$AMZN che beneficia del sentiment positivo sui consumi. Vediamo come si comporterà il mercato americano oggi!"
    )
    print_session_preview("U.S. market open", us_open_mock)
    
    # 3. U.S. Market Close / Daily Recap
    us_close_mock = (
        "Buonasera! Ecco il nostro recap di fine giornata al termine di una sessione davvero entusiasmante per "
        "il nostro portafoglio. Wall Street ha vissuto un rally importante, guidato ancora una volta dal settore "
        "tecnologico. La stella indiscutibile della giornata è stata $NVDA, che ha registrato un eccezionale "
        "+4.32% a seguito del sentiment favorevole sui semiconduttori. Ottima performance anche per $LLY, "
        "che ha chiuso in rialzo del +2.85% grazie a nuove approvazioni regolatorie per i suoi farmaci innovativi. "
        "In territorio molto positivo anche $GOOG, che consolida la sua posizione di forza con un +1.98%. "
        "Una chiusura in grande stile che rafforza la nostra strategia di lungo termine!"
    )
    print_session_preview("U.S. market close", us_close_mock)
    
    # 4. Weekly Recap (Sat)
    sat_recap_mock = (
        "Buon fine settimana! Con i mercati chiusi, facciamo il punto su questa settimana davvero molto positiva "
        "per il nostro portafoglio, che consolida un guadagno del +3.25%. A guidare i rialzi è stata la straordinaria "
        "forza di $PLTR, protagonista assoluta grazie a eccellenti trimestrali e all'espansione dei suoi contratti "
        "commerciali nel settore privato. Nel comparto sanitario, $NOVO-B.CO ha registrato progressi significativi "
        "sostenuta dall'approvazione di nuovi impianti di produzione in Europa. Ottima settimana anche per $MSFT "
        "e $AMZN, che continuano a beneficiare di flussi d'acquisto solidi e costanti. Chiudiamo la settimana "
        "in una posizione ottimale, pronti e fiduciosi per le prossime sfide di mercato!"
    )
    print_session_preview("Weekly recap (Sat)", sat_recap_mock)
    
    # 5. Weekly Recap (Sun)
    sun_recap_mock = (
        "Buona domenica! Oggi diamo un'occhiata più da vicino ai titoli che hanno guidato la classifica delle "
        "performance settimanali del nostro portafoglio. In cima alla classifica troviamo una strepitosa $PLTR "
        "con un balzo del +12.45%, spinta dall'incredibile slancio nell'adozione commerciale della sua piattaforma AIP. "
        "Medaglia d'argento per $NOVO-B.CO (+8.12%), che consolida la sua leadership indiscussa nel settore biofarmaceutico "
        "globale grazie a una domanda che supera di gran lunga l'offerta. Al terzo posto si piazza $MSFT (+4.20%), "
        "che continua a dimostrare come la sua strategia legata all'intelligenza artificiale generativa stia "
        "producendo ricavi reali e crescenti. Questa classifica dimostra ancora una volta la forza dei nostri megatrend!"
    )
    print_session_preview("Weekly recap (Sun)", sun_recap_mock)

    # 6. Daily Stock Focus Deep-Dive
    stock_focus_mock = (
        "🔍 FOCUS ASSET: Perché ho in portafoglio Eni S.p.A. ($ENI.MI / $E)\n\n"
        "La nostra posizione su $ENI.MI si basa su una tesi di transizione energetica bilanciata e rendimento elevato.\n\n"
        "🚀 POSSIBILI UPSIDE:\n"
        "1. Solido dividend yield superiore al 6% con piano di buyback attivo.\n"
        "2. Crescita del modello 'Satellite' (Plenitude e Enilive).\n\n"
        "⚠️ POSSIBILI DOWNSIDE:\n"
        "1. Volatilità del prezzo del greggio Brent e gas naturale.\n"
        "2. Rallentamento della domanda globale di raffinazione.\n\n"
        "Competitor di settore da monitorare: $SHEL, $TTE, $BP."
    )
    print_session_preview("Stock focus", stock_focus_mock)

    # 7. Saturday Weekly Portfolio Outlook
    portfolio_outlook_mock = (
        "📅 ANTEPRIMA SETTIMANALE: I catalizzatori dei nostri titoli per la prossima settimana\n\n"
        "La prossima settimana si preannuncia ricca di eventi aziendali per i principali titoli in portafoglio. "
        "In primo piano le trimestrali di $NVDA e $MSFT, che forniranno dettagli cruciali sulla spesa in infrastrutture AI. "
        "Nel settore salute, attesi aggiornamenti dai trial clinici di $LLY e $AZN.L."
    )
    print_session_preview("Weekly portfolio outlook", portfolio_outlook_mock)

    # 8. Saturday Weekly Macro Outlook
    macro_outlook_mock = (
        "🌍 MACRO OUTLOOK: Il calendario e gli eventi chiave della prossima settimana sui mercati\n\n"
        "I mercati globali ($S&P500, $NSDQ100) si preparano a una settimana decisiva sul fronte macroeconomico. "
        "Attesa per la riunione della FED sui tassi di interesse e per i nuovi dati sull'inflazione CPI in USA ed Europa. "
        "Un quadro fondamentale per capire la traiettoria dei tassi nella seconda metà dell'anno."
    )
    print_session_preview("Weekly macro outlook", macro_outlook_mock)

if __name__ == '__main__':
    main()
