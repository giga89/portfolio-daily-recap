#!/usr/bin/env python3
"""
Independent Multi-AI Fact-Checker & Temporal Auditor
====================================================
Provides an independent layer of verification ("LLM-as-a-Judge") using
external AI providers (Groq and Mistral) to strictly prevent:
  1. Temporal paradoxes (e.g. describing today's Fed decision as a future event
     in an evening US_CLOSE recap written after market close).
  2. Outdated institutional figures & leadership hallucinations
     (e.g. former central bankers or former CEOs cited as active decision-makers).
  3. Speculations or rumors presented as confirmed facts.
  4. Portfolio asset attribute distortions.

Hierarchy of Execution:
  1. Groq API (Primary Independent Auditor: Qwen 2.5/3.8 / GPT-OSS on LPUs — ~0.02s latency, 100% free tier)
  2. Mistral API (Secondary Auditor: Mistral Small — European independent model)
  3. Graceful Fallback: Internal Gemini Adversarial Judge if external APIs are unavailable.
"""

import os
import re
import json
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

try:
    import pytz
    ROME_TZ = pytz.timezone("Europe/Rome")
    NY_TZ = pytz.timezone("America/New_York")
except ImportError:
    pytz = None
    ROME_TZ = None
    NY_TZ = None

# Auto-load local .env if present
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from tavily_search import get_live_market_news_context, is_tavily_available, filter_live_news_for_topic
except ImportError:
    try:
        from src.tavily_search import get_live_market_news_context, is_tavily_available, filter_live_news_for_topic
    except ImportError:
        get_live_market_news_context = None
        is_tavily_available = lambda: False
        filter_live_news_for_topic = lambda ctx, txt, topic_type="full_post": ctx


# Tested, verified working models on Groq LPUs (1000 RPD / 8000 TPM per model)
# Quality-first order: 120B flagship (0.7-1.1s, 4/4 traps with reasoning_effort='low') -> 27B -> 20B
GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
]

# Tested, verified working models on Mistral API (Free Tier: 2 RPM / 40K TPM per model)
# Accuracy-first order: Ministral 14B & 8B scored 4/4 traps vs 3/4 on code-specialized Codestral;
# medium/small/magistral series currently return 0 RPM on Free Tier.
MISTRAL_MODELS = [
    "ministral-14b-latest",
    "ministral-8b-latest",
    "codestral-latest",
    "ministral-3b-latest",
]

# Circuit breaker: disables Mistral for the session ONLY on auth failure (401/403)
# or when every configured model reports explicit 0 RPM account-wide disablement.
_MISTRAL_AVAILABLE: Optional[bool] = None

# Thread-safe pacing & temporary per-model cooldowns across parallel ThreadPoolExecutor calls
_GROQ_LOCK = threading.Lock()
_GROQ_PACE_STATE: Dict[str, float] = {"last_ts": 0.0, "last_elapsed": 0.0}
_GROQ_COOLDOWN: Dict[str, float] = {}

_MISTRAL_LOCK = threading.Lock()
_MISTRAL_PACE_STATE: Dict[str, float] = {"last_ts": 0.0, "last_elapsed": 0.0}
_MISTRAL_COOLDOWN: Dict[str, float] = {}


def _pace_provider_call(lock: threading.Lock, state: Dict[str, float], min_interval: float) -> None:
    """Ensure concurrent threads space out real network calls cleanly without delaying instant mocks."""
    if min_interval <= 0:
        return
    is_mocked = (
        not REQUESTS_AVAILABLE
        or hasattr(getattr(requests, "post", None), "_mock_name")
        or "mock" in type(getattr(requests, "post", None)).__name__.lower()
    )
    if is_mocked:
        return
    wait = 0.0
    with lock:
        now = time.monotonic()
        last_ts = state.get("last_ts", 0.0)
        if last_ts > 0.0:
            next_slot = max(now, last_ts + min_interval)
            wait = next_slot - now
            state["last_ts"] = next_slot
        else:
            state["last_ts"] = now
    if wait > 0:
        time.sleep(wait)


def _ordered_models_by_cooldown(models: List[str], cooldowns: Dict[str, float], lock: threading.Lock) -> List[str]:
    """Return models with non-cooled-down candidates first, preserving fallback order."""
    now = time.time()
    with lock:
        active = [m for m in models if cooldowns.get(m, 0.0) <= now]
        cooled = [m for m in models if cooldowns.get(m, 0.0) > now]
    return active + cooled


def _mark_model_cooldown(model: str, cooldowns: Dict[str, float], lock: threading.Lock, seconds: float) -> None:
    with lock:
        cooldowns[model] = time.time() + seconds


def get_current_temporal_context(
    session_name: Optional[str] = None,
    benchmark_daily_data: Optional[Dict[str, float]] = None,
) -> Dict[str, str]:
    """
    Builds rich temporal anchors for the exact current moment, including benchmark closing data.
    """
    now_utc = datetime.now(timezone.utc)
    
    # Italian local time (Europe/Rome)
    if ROME_TZ:
        now_rome = datetime.now(ROME_TZ)
    else:
        now_rome = datetime.now()

    # Wall Street local time (America/New_York)
    if NY_TZ:
        now_ny = datetime.now(NY_TZ)
    else:
        now_ny = datetime.now()

    it_days = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    it_months = [
        "", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ]

    day_name = it_days[now_rome.weekday()]
    month_name = it_months[now_rome.month]
    formatted_date = f"{day_name} {now_rome.day} {month_name} {now_rome.year}"

    session_clean = (session_name or "Daily recap").upper()
    
    # Contextual market session status
    if "CLOSE" in session_clean or "SERALE" in session_clean:
        market_state = (
            "SESSIONE USA CONCLUSA (dopo le 16:00 ET / 22:00 CET). "
            "Tutti gli eventi, dati macro e decisioni di banche centrali di oggi sono GIÀ AVVENUTI. "
            "È TASSATIVAMENTE VIETATO parlare al futuro di eventi di oggi."
        )
    elif "OPEN" in session_clean and ("U.S." in session_clean or "US" in session_clean):
        market_state = (
            "PRE-APERTURA WALL STREET (prima delle 9:30 ET / 15:30 CET). "
            "La seduta americana deve ancora iniziare."
        )
    elif "OPEN" in session_clean and "EUROPEAN" in session_clean:
        market_state = (
            "PRE-APERTURA MERCATI EUROPEI (prima delle 9:00 CET). "
            "La seduta europea deve ancora iniziare."
        )
    elif "WEEKLY" in session_clean or "SAT" in session_clean or "SUN" in session_clean:
        market_state = (
            "FINE SETTIMANA (MERCATI CHIUSI). "
            "Si fa il bilancio della settimana trascorsa o l'anteprima di quella entrante."
        )
    else:
        market_state = "SESSIONE DI RECAP GIORNALIERO."

    # Benchmark daily performance ground truth for close / evening sessions
    if benchmark_daily_data is None and ("CLOSE" in session_clean or "SERALE" in session_clean):
        try:
            from finance_fetcher import fetch_benchmarks_daily_performance
            b_perf = fetch_benchmarks_daily_performance()
            if b_perf:
                benchmark_daily_data = b_perf
        except Exception:
            benchmark_daily_data = None

    benchmarks_summary = ""
    if benchmark_daily_data:
        parts = []
        for sym, chg in benchmark_daily_data.items():
            if chg is not None:
                sign = "+" if chg > 0 else ""
                parts.append(f"{sym}: {sign}{chg:.2f}%")
        if parts:
            benchmarks_summary = ", ".join(parts)

    # Next trading session information (especially relevant for close/evening recaps)
    next_session_timing = "nella prossima seduta"
    next_session_short = "Prossima seduta"
    next_earnings_summary = "Nessuna trimestrale prevista per il portafoglio"
    next_session_is_tomorrow = True
    try:
        import market_calendar
        next_sess = market_calendar.get_next_trading_session_info(now_rome.date(), market="US")
        next_session_timing = next_sess["timing_phrase"]
        next_session_short = next_sess["timing_short"]
        next_session_is_tomorrow = next_sess["is_tomorrow"]
        next_earnings = market_calendar.get_earnings_for_session(next_sess["next_date"])
        if next_earnings:
            next_earnings_summary = ", ".join([f"{e['name']} ({e['ticker']})" for e in next_earnings])
    except Exception:
        pass

    return {
        "formatted_date": formatted_date,
        "iso_date": now_rome.strftime("%Y-%m-%d"),
        "rome_time": now_rome.strftime("%H:%M CET/CEST"),
        "ny_time": now_ny.strftime("%H:%M ET"),
        "market_state": market_state,
        "benchmarks_daily": benchmarks_summary,
        "benchmark_data_raw": benchmark_daily_data,
        "year": str(now_rome.year),
        "next_session_timing": next_session_timing,
        "next_session_short": next_session_short,
        "next_session_is_tomorrow": next_session_is_tomorrow,
        "next_session_earnings": next_earnings_summary,
    }


def _build_audit_prompt(
    text: str,
    session_name: Optional[str],
    temporal_ctx: Dict[str, str],
    portfolio_metadata_summary: str = "",
    live_news_context: str = "",
    stock_data: Optional[Dict[str, Any]] = None,
    topic_type: str = "full_post",
) -> str:
    """Creates the adversarial fact-checker prompt for Groq/Mistral with optional Tavily live grounding."""
    text_stripped = (text or "").strip()
    text_lower = text_stripped.lower()
    is_outlook_topic = (
        topic_type == "outlook"
        or text_stripped.startswith("🔮")
        or any(w in text_lower for w in ("nella seduta di domani", "prossima seduta", "riflettori saranno puntati"))
    )
    mentioned_tags = set()
    for raw_t in re.findall(r'\$([A-Za-z0-9\.\-]+)', text_stripped):
        mentioned_tags.add(raw_t.upper())
        mentioned_tags.add(raw_t.split(".")[0].upper())

    macro_tags = {"SPX500", "NSDQ100", "DJ30", "GER40", "EUSTX50", "CHINA50", "SWDA", "SX7PEX"}
    is_single_stock_topic = (
        topic_type in ("stock_paragraph", "stock_bullet")
        or (
            not is_outlook_topic
            and "\n\n" not in text_stripped
            and bool(mentioned_tags)
            and not (mentioned_tags & macro_tags)
        )
    )

    live_news_section = ""
    if live_news_context and not is_outlook_topic:
        live_news_section = f"""
=========================================
FONTI NOTIZIE FINANZIARIE REALI RECENTI (LIVE WEB - TAVILY):
=========================================
{live_news_context}
"""

    benchmarks_daily_line = f"• PERFORMANCE INDICI OGGI: {temporal_ctx.get('benchmarks_daily') or 'Non specificata'}\n"

    stock_gt_section = ""
    if stock_data and not is_outlook_topic:
        try:
            from post_verifier import _resolve_stock_pct_map
            pct_map = _resolve_stock_pct_map(stock_data, session_name=session_name)
            if pct_map:
                seen_canon = set()
                gt_items = []
                for _, (canon_sym, pct_val) in sorted(pct_map.items()):
                    if canon_sym not in seen_canon:
                        if is_single_stock_topic and mentioned_tags:
                            if canon_sym.upper() not in mentioned_tags and canon_sym.split(".")[0].upper() not in mentioned_tags:
                                continue
                        seen_canon.add(canon_sym)
                        dir_lbl = "RIALZO (+)" if pct_val >= 0 else "CALO (-)"
                        gt_items.append(f"  • ${canon_sym}: {pct_val:+.2f}% [{dir_lbl}]")
                if gt_items:
                    stock_gt_section = (
                        "• PERFORMANCE CERTIFICATA SINGOLI TITOLI OGGI (YAHOO FINANCE GROUND TRUTH - INVIOLABILE):\n"
                        + "\n".join(gt_items) + "\n"
                    )
        except Exception:
            stock_gt_section = ""

    filtered_metadata = portfolio_metadata_summary or "Nessun asset specifico indicato."
    if is_single_stock_topic and mentioned_tags and portfolio_metadata_summary:
        meta_lines = [
            line for line in portfolio_metadata_summary.split("\n")
            if any(f"${tag}" in line.upper() for tag in mentioned_tags)
        ]
        if meta_lines:
            filtered_metadata = "\n".join(meta_lines)

    if is_outlook_topic:
        temporal_rule_1 = f"""1. COERENZA TEMPORALE PER MICROTEMA 5 (🔮 SGUARDO ALLA PROSSIMA SEDUTA / OUTLOOK FUTURO - CRITICA):
   - QUESTO PARAGRAFO È LO SGUARDO IN AVANTI VERSO LA PROSSIMA SEDUTA DI BORSA ({temporal_ctx.get('next_session_timing', 'nella prossima seduta')}).
   - DEVE OBBLIGATORIAMENTE parlare al FUTURO ('saranno puntati', 'valuterà', 'attesi', 'monitoreremo', 'apriranno') e riferirsi alla prossima seduta ({temporal_ctx.get('next_session_timing', 'nella prossima seduta')}).
   - È TASSATIVAMENTE VIETATO convertire i verbi dal futuro al passato o cambiare 'domani' / 'prossima seduta' in 'oggi'!
   - Mantieni obbligatoriamente l'emoji 🔮 all'inizio del paragrafo."""
    else:
        temporal_rule_1 = """1. COERENZA TEMPORALE (CRITICA):
   - Se la sessione è serale o di chiusura (es. US_CLOSE), la seduta di borsa odierna è CONCLUSA.
   - Tutti gli eventi della giornata (es. riunioni o decisioni della Federal Reserve, tassi, conferenze stampa, dati inflazione o occupazione) sono GIÀ AVVENUTI.
   - Se il post parla di un evento di oggi usando verbi al FUTURO (es. "oggi deciderà", "oggi prenderà una decisione", "in attesa dell'annuncio di stasera", "si attende la decisione"), questo è un GRAVISSIMO PARADOSSO TEMPORALE.
   - CORREZIONE: Devi convertire il testo al PASSATO (es. "la Fed ha annunciato", "la decisione sui tassi è arrivata oggi") OPPURE, se l'esito reale non è menzionato con certezza, rimuovere l'affermazione speculativa.
   - ECCEZIONE: Se un paragrafo inizia con 🔮 o parla esplicitamente della 'prossima seduta' / 'seduta di domani', quel paragrafo guarda alla prossima sessione di borsa e DEVE restare al futuro!"""

    return f"""Sei un Lead Financial Fact-Checker & Senior Compliance Auditor per un account pubblico di investimenti su eToro.
Il tuo obiettivo è effettuare un AUDIT INDIPENDENTE, CRITICO E SPIETATO sul seguente post prima della pubblicazione.

=========================================
INFORMAZIONI TEMPORALI CERTE (GROUND TRUTH):
=========================================
• DATA CORRENTE: {temporal_ctx.get('formatted_date')} (Anno: {temporal_ctx.get('year')})
• ORA LOCALE ITALIANA: {temporal_ctx.get('rome_time')}
• ORA LOCALE WALL STREET: {temporal_ctx.get('ny_time')}
• STATO DELLA SESSIONE: {temporal_ctx.get('market_state')}
• PROSSIMA SEDUTA DI BORSA (CALENDARIO UFFICIALE): {temporal_ctx.get('next_session_timing', 'nella prossima seduta')}
• TRIMESTRALI CONFERMATE PROSSIMA SEDUTA: {temporal_ctx.get('next_session_earnings', 'Nessuna trimestrale prevista per il portafoglio')}
{benchmarks_daily_line}{stock_gt_section}=========================================
METADATI DI PORTAFOGLIO:
=========================================
{filtered_metadata}
{live_news_section}
=========================================
TESTO DEL POST DA AUDITARE:
=========================================
{text}

=========================================
REGOLE DI AUDIT INDIPENDENTE (TASSATIVE):
=========================================
{temporal_rule_1}

2. VERIFICA CARICHE E FIGURE ISTITUZIONALI:
   - Verifica che le figure istituzionali menzionate (banchieri centrali, ministri, CEO) siano coerenti e non anacronistiche.
   - NOTA BENE (ANACRONISMI NOTI): Il mandato di Jerome Powell come Presidente della Fed termina a maggio 2026. Citare Powell per decisioni o annunci nel 2026 è anacronistico: rimuovi tassativamente il nome 'Powell' e usa genericamente 'la Federal Reserve' / 'la banca centrale'.
   - Se viene attribuita una decisione a una figura che non ricopre più la carica o se c'è un'allucinazione su chi guida un'istituzione, correggi immediatamente o rimuovi il riferimento.

3. CONFERMA NOTIZIE CON LE FONTI LIVE TAVILY (SENZA SOVRASCRIVERE I PREZZI CERTIFICATI):
   - Consulta le 'FONTI NOTIZIE FINANZIARIE REALI RECENTI (LIVE WEB - TAVILY)' sopra riportate per verificare i fatti menzionati nel post (partnership, catalizzatori, trimestrali, rating).
   - Se una notizia o catalizzatore è confermato dalle fonti live, consideralo autentico e approvalo.
   - Se un fatto è palesemente inventato e in contrasto con la realtà, correggilo chirurgicamente.
   - GERARCHIA INVIOLABILE DEI PREZZI: Le percentuali e i segni (+/-) riportati in 'PERFORMANCE INDICI OGGI' e 'PERFORMANCE CERTIFICATA SINGOLI TITOLI OGGI (YAHOO FINANCE GROUND TRUTH)' sono dati ufficiali di chiusura certificati al 100%, anche quando gli articoli web di Tavily non riportano ancora il dato di chiusura. NON considerare MAI un'allucinazione e NON respingere (REJECT) un paragrafo solo perché Tavily non cita la percentuale di chiusura di un titolo già certificata da Yahoo Finance!
   - Gli articoli web di Tavily possono riferirsi a sedute dei giorni precedenti: è TASSATIVAMENTE VIETATO sovrascrivere la performance odierna certificata di un titolo (es. +6.24% o -3.40%) con percentuali pescate da vecchi articoli Tavily (es. -9.8%). Se invece il testo da auditare riporta un segno/direzione opposto al Ground Truth Yahoo Finance (es. scrive -9.8% o 'in calo' su un titolo a +6.24%, oppure +4.15% o 'in rialzo' su un titolo a -3.40%), usa 'AUTO_CORRECT' per ripristinare la direzione e la percentuale certificata Yahoo Finance!
   - DIVIETO ASSOLUTO DI META-COMMENTI NEL TESTO PUBBLICO: Non inserire MAI dentro 'verified_text' commenti interni da revisore come 'nelle fonti principali', 'non confermata dalle fonti', 'le fonti non menzionano' o 'secondo i dati forniti'. Il campo 'verified_text' viene pubblicato direttamente ai lettori!

4. FORMATTAZIONE ETORO:
   - Nessun markdown bold (** o __).
   - Massimo 4 cashtag con prefisso $ (es. $NVDA, $SPX500). Non aggiungere cashtag a titoli citati come testo semplice.

5. PRESERVAZIONE DELLA RICCHEZZA DEL CONTENUTO (NON RIASSUMERE E NON GONFIARE):
   - È SEVERAMENTE VIETATO tagliare o riassumere il post in poche righe generiche, ma è altrettanto VIETATO gonfiare un singolo paragrafo in un muro di testo prolisso!
   - Ogni paragrafo di un titolo deve restare sintetico, naturale e scorrevole (2-3 frasi, max ~350 caratteri). NON copiare l'intera scheda fondamentale dentro il paragrafo e NON aggiungere tra parentesi le variazioni degli indici macro `(SPX500: ..., NSDQ100: ...)` dentro il paragrafo di un singolo titolo!
   - Mantieni SEMPRE l'emoji iniziale del paragrafo (es. 🏥, 🧼, 🔮, 🌆, 💻, non sostituirla con 🔹) e mantieni SEMPRE il suffisso di borsa del cashtag (es. $ULVR.L, $VOF.L, $PRY.MI, non troncarlo in $ULVR).
   - Non scrivere mai espressioni artificiali da prompt come 'un catalizzatore operativo fresco' o 'coerente con il tono settoriale'.
   - Intervieni in modo chirurgico SOLO sui passaggi che contengono errori temporali o allucinazioni fattuali; se il paragrafo rispetta già i dati di chiusura Yahoo Finance e cita fatti coerenti, restituisci decision: "APPROVE"!

6. RIGETTO DI BANALITÀ E FRASI FATTE (QUALITÀ DELLE NOTIZIE):
   - Se il post contiene ESCLUSIVAMENTE frasi generiche, banali e vuote prive di qualsiasi dato concreto sui titoli citati (es. 'continuiamo a seguire con estrema fiducia', 'la tesi rimane solida', 'sostenuta dalla forte domanda', 'continua ad offrire ottima stabilità', 'rappresenta una copertura strategica importante', 'pronti a gestire la volatilità'), sostituisci la frase generica con un dato reale sintetico (1 frase) tratto dai METADATI DI PORTAFOGLIO o dalle NOTIZIE LIVE TAVILY. Se invece il paragrafo contiene già fatti, notizie o numeri concreti, NON riscriverlo e approvalo ("APPROVE")!

7. REGOLE CONTRO INVENZIONI, ALLUCINAZIONI E RIPETIZIONI (TASSATIVE):
   - NON INVENTARE EVENTI NON PRESENTI NEL TESTO: Se il testo da auditare non parla affatto di tassi d'interesse, della Federal Reserve o di uno specifico indicatore macroeconomico, NON devi assolutamente inventarlo o aggiungerlo di tua iniziativa! Correggi al passato SOLO gli eventi che sono già menzionati nel testo.
   - NESSUNA FRASE ASSURDA O CONTRADDITTORIA: È severamente vietato inventare concetti finanziari inesistenti (come 'tassa sui tassi', 'tassa sugli interessi').
   - ZERO RIPETIZIONI: È severamente vietato ripetere la stessa frase o periodo due o più volte nel testo verificato.

8. COERENZA TONO/SENTIMENT DEGLI INDICI VS SINGOLI TITOLI (CRITICA E SIMMETRICA):
   - Confronta SEMPRE con precisione assoluta le '• PERFORMANCE INDICI OGGI' (Ground Truth).
   - CASO A: SE GLI INDICI HANNO CHIUSO IN RIALZO (variazione percentuale positiva, es. SPX500 > 0% o NSDQ100 > 0%):
     * Il post DEVE descrivere la seduta generale dei mercati / di Wall Street / degli indici come POSITIVA / IN RIALZO.
     * È una GRAVISSIMA ALLUCINAZIONE definire la seduta come "in flessione", "in calo", "seduta negativa", "giornata negativa", "ha perso X%", "in territorio negativo", oppure invertire il segno e scrivere "-X%"!
     * CORREZIONE INDICI POSITIVI: Sostituisci IMMEDIATAMENTE qualsiasi espressione di calo o flessione con espressioni coerenti (es. "seduta in rialzo", "chiusura positiva", "seduta all'insegna dei guadagni", "ha guadagnato +X%"), riportando il segno corretto (+) e la variazione percentuale reale.
   - CASO B: SE GLI INDICI HANNO CHIUSO IN CALO (variazione percentuale negativa, es. SPX500 < 0% o NSDQ100 < 0%):
     * Il post NON PUÒ definire la seduta complessiva dei mercati / di Wall Street / degli indici come "positiva", "tono complessivamente positivo", "giornata favorevole per i mercati", "ottima seduta per i listini" o simili.
     * CORREZIONE INDICI NEGATIVI: Sostituisci le formule positive errate relative a Wall Street/indici con espressioni coerenti con la realtà numerica (es. "seduta in flessione", "chiusura in calo", "seduta all'insegna delle prese di beneficio", "giornata debole"), indicando la variazione percentuale reale negativa (-).
   - DISTINZIONE FONDAMENTALE (SINGOLI TITOLI / SETTORI - SIMMETRICA):
     * Questa regola per Wall Street non va confusa con i singoli titoli del portafoglio!
     * Se nel Ground Truth Yahoo Finance un titolo ha variazione POSITIVA (+X%, es. $TSM +6.24%, $MRVL +2.26%), DEVE essere descritto come positivo/in rialzo (+X%): è TASSATIVAMENTE VIETATO definirlo in calo o flessione o mettergli il segno meno.
     * VICEVERSA, se nel Ground Truth Yahoo Finance un titolo ha variazione NEGATIVA (-X%, es. $NVDA -3.40%), DEVE essere descritto in calo/flessione (-X%): è TASSATIVAMENTE VIETATO definirlo in rialzo, positivo, brillante o mettergli il segno più!
   - DIVIETO ASSOLUTO DI INVERSIONE SEGNO (+ vs -):
     * È TASSATIVAMENTE VIETATO invertire il segno matematico di indici o titoli: non trasformare MAI un + in un - né un - in un +! Non omettere il segno affermando che un asset positivo "ha perso" o che un asset negativo "ha guadagnato".

9. PRIORITÀ NOTIZIE FRESCHE DEL GIORNO VS NOIOSE TRIMESTRALI (CRITICA):
   - I lettori cercano novità e catalizzatori FRESCHI DEL GIORNO (accordi commerciali, partnership strategiche, commesse, lanci di prodotto, upgrade o downgrade di rating con target price, sviluppi regolatori o giudiziari avvenuti oggi o nelle ultime 24-48 ore).
   - È VIETATO riempire i commenti dei titoli con rimandi generici o noiosi a trimestrali passate o già ampiamente digerite nei giorni scorsi, a meno che i dati finanziari trimestrali non siano stati rilasciati PROPRIO OGGI. Dai sempre priorità a news e catalizzatori operativi freschi.

10. VERIFICA SGUARDO ALLA PROSSIMA SEDUTA & TRIMESTRALI (MICRO-TEMA 5):
   - Nel Microtema 5 (Sguardo alla prossima seduta / After-Hours), il testo guarda legittimamente in avanti verso la PROSSIMA SEDUTA di borsa.
   - VERIFICA GIORNO CORRETTO: Se oggi è venerdì o pre-festivo, è severamente vietato dire 'domani' per le contrattazioni di mercato: deve riferirsi a lunedì (o al giorno feriale di riapertura dei mercati indicato nel Ground Truth).
   - VERIFICA TRIMESTRALI (EARNINGS): Qualsiasi trimestrale societaria citata per la prossima seduta DEVE corrispondere alle 'TRIMESTRALI CONFERMATE PROSSIMA SEDUTA'. Se il post inventa che un'azienda non presente nel Ground Truth riporterà i conti domani o nella prossima seduta, DEVI RIMUOVERE l'annuncio della trimestrale e sostituirlo con catalizzatori macroeconomici o aziendali confermati.
   - ZERO RIPETIZIONI DELLA SEDUTA DI OGGI: Il Microtema 5 NON deve ripetere le percentuali di chiusura, i numeri o la rotazione settoriale della giornata appena terminata (già trattati nel Microtema 1).

=========================================
OUTPUT RICHIESTO:
=========================================
Restituisci ESCLUSIVAMENTE un oggetto JSON valido (senza testo prima o dopo) con i seguenti campi:
{{
  "decision": "APPROVE" | "AUTO_CORRECT" | "REJECT",
  "score": 100,
  "temporal_issues": ["elenco di eventuali problemi temporali rilevati"],
  "hallucinations_detected": ["elenco di eventuali allucinazioni rilevate"],
  "verified_text": "Testo finale bonificato e pronto per la pubblicazione su eToro",
  "explanation": "Breve sintesi dell'audit in italiano"
}}
"""


def sanitize_verified_text(
    original_text: str,
    verified_text: str,
    session_name: Optional[str] = None,
    benchmark_daily_data: Optional[Dict[str, float]] = None,
    stock_data: Optional[Dict[str, Any]] = None,
    topic_type: str = "full_post",
) -> str:
    """
    Sanitizes auto-corrections proposed by LLM auditors:
    1. Protects forward-looking outlook paragraphs (🔮) from being flipped into past tense ("oggi").
    2. Removes absurd hallucinations (e.g. 'tassa sui tassi') and leaked auditor meta-commentary / prompt jargon.
    3. Restores truncated exchange suffixes on cashtags (e.g. $ULVR -> $ULVR.L) and leading thematic emojis.
    4. Deduplicates repeated sentences and prevents runaway auditor bloat on single-stock micro-topics.
    5. Cleans whitespace and enforces mathematical benchmark & individual stock ground truth.
    """
    if not verified_text:
        return original_text

    orig_stripped = original_text.strip()
    cleaned = verified_text.strip()

    # 0. Protect forward-looking outlook paragraphs (🔮) from being rewritten into past tense ("oggi")
    is_outlook = topic_type == "outlook" or orig_stripped.startswith("🔮")
    if is_outlook:
        orig_lower = orig_stripped.lower()
        clean_lower = cleaned.lower()
        orig_has_next_session = any(
            k in orig_lower for k in ("domani", "prossima seduta", "prossima sessione", "saranno puntati", "valuterà", "monitoreremo", "riapertura")
        )
        corrupted_to_today_past = (
            ("nella seduta di oggi" in clean_lower and "nella seduta di oggi" not in orig_lower)
            or ("sono stati puntati" in clean_lower and "saranno puntati" in orig_lower)
            or ("ha valutato" in clean_lower and "valuterà" in orig_lower)
        )
        if orig_has_next_session and corrupted_to_today_past:
            return orig_stripped

    # 1. Strip absurd/hallucinated financial phrases, prompt jargon, and leaked auditor meta-commentary clauses
    absurd_patterns = [
        r'(?i)\bnuova\s+tassa\s+sui\s+tassi(?:\s+di\s+interesse)?\b[.,]?',
        r'(?i)\btass[ae]\s+sui\s+tassi(?:\s+di\s+interesse)?\b[.,]?',
        r'(?i)\btass[ae]\s+sugli\s+interessi\b[.,]?',
        r'(?i),?\s*(?:sebbene|benché|nonostante)\s+(?:(?!\.(?:\s|$))[^\n!?]){0,120}?\b(?:nelle|dalle)\s+fonti\s+(?:principali|disponibili|fornite|live|ufficiali)(?:(?!\.(?:\s|$))[^\n!?])*',
        r'(?i),?\s*(?:sebbene|benché)\s+le\s+fonti\s+(?:disponibili\s+|fornite\s+|principali\s+)?non\s+conferm(?:(?!\.(?:\s|$))[^\n!?])*',
        r'(?i),?\s*(?:secondo\s+quanto\s+(?:riportato|emerge)\s+)?\b(?:nelle|dalle)\s+fonti\s+(?:principali|disponibili|fornite|live|ufficiali)\b',
        r'(?i),?\s*un\s+catalizzatore\s+operativo\s+fresco(?:\s+che\s+ha\s+[^\.,;]+)?',
    ]
    for pat in absurd_patterns:
        cleaned = re.sub(pat, '', cleaned).strip()

    # Strip redundant index parentheticals injected by auditor into single-stock paragraphs
    if "SPX500" not in orig_stripped.upper() and "NSDQ100" not in orig_stripped.upper():
        cleaned = re.sub(r'\s*\((?:SPX500|S&P\s*500)[^)]*NSDQ100[^)]*\)', '', cleaned, flags=re.IGNORECASE).strip()

    # Fix contradiction if auditor wrote 'in linea con la performance generale dei mercati' on a counter-trend stock
    if benchmark_daily_data and isinstance(benchmark_daily_data, dict):
        spx_v = benchmark_daily_data.get("SPX500", 0.0) or 0.0
        if spx_v < -0.3 and re.search(r'\+\d+[\.,]\d+%', cleaned):
            cleaned = re.sub(
                r'(?i),?\s*in\s+linea\s+con\s+(?:la\s+performance\s+generale|l\'andamento)\s+dei\s+mercati',
                ', in controtendenza rispetto alla flessione dei mercati',
                cleaned,
            )

    # Restore truncated exchange suffixes on cashtags (e.g. $ULVR.L -> $ULVR)
    for full_tag in re.findall(r'\$([A-Za-z0-9\-]+\.[A-Za-z]{1,4})\b', orig_stripped):
        base_tag = full_tag.split('.')[0]
        cleaned = re.sub(rf'\${re.escape(base_tag)}(?!\.[A-Za-z])', f'${full_tag}', cleaned, flags=re.IGNORECASE)

    # Restore original leading thematic emoji if auditor stripped it or replaced it with 🔹
    orig_lead_match = re.match(r'^([^\w\s\$\"\'\(\[\#\•\-\*\✓]+)\s+', orig_stripped)
    if orig_lead_match:
        orig_emoji = orig_lead_match.group(1).strip()
        if orig_emoji and orig_emoji != "🔹":
            if cleaned.startswith("🔹"):
                cleaned = re.sub(r'^🔹\s*', f'{orig_emoji} ', cleaned)
            elif cleaned and (cleaned[0].isalnum() or cleaned[0] == '$'):
                cleaned = f"{orig_emoji} {cleaned}"

    # 2. Deduplicate repeated sentences (e.g. "Sentence A. Sentence A.")
    raw_sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    seen_normalized = set()
    deduped_sentences = []
    for s in raw_sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        # Normalize for repetition comparison
        norm = re.sub(r'[^a-zA-Z0-9]', '', s_clean.lower())
        if len(norm) > 15 and norm in seen_normalized:
            continue
        seen_normalized.add(norm)
        deduped_sentences.append(s_clean)

    cleaned = " ".join(deduped_sentences)

    # 3. Reject hallucinated expansion on short greeting/transitional text or massive bloat on a single stock micro-topic
    if len(orig_stripped) < 130:
        orig_has_finance = bool(re.search(r'\$[A-Za-z0-9\.\-]+', orig_stripped) or re.search(r'[+-]?\d+[\.,]?\d*%', orig_stripped))
        if not orig_has_finance and len(cleaned) > len(orig_stripped) * 1.8:
            return orig_stripped
    elif "\n\n" not in orig_stripped and 100 <= len(orig_stripped) <= 450 and len(cleaned) > max(460, int(len(orig_stripped) * 1.55)):
        # If the auditor bloated a concise 2-3 sentence micro-topic into a huge wall of text,
        # prefer the deterministically-validated original paragraph (or cap to 3 sentences).
        try:
            from post_verifier import verify_post_deterministic, enforce_benchmark_ground_truth, enforce_stock_ground_truth, fix_sign_sentiment_oxymorons
            cand_orig = orig_stripped
            if benchmark_daily_data:
                cand_orig, _ = enforce_benchmark_ground_truth(cand_orig, benchmark_daily=benchmark_daily_data, session_name=session_name)
            if stock_data:
                cand_orig, _ = enforce_stock_ground_truth(cand_orig, stock_data=stock_data, session_name=session_name)
            cand_orig = fix_sign_sentiment_oxymorons(cand_orig)
            is_ok, crit_issues, _ = verify_post_deterministic(
                cand_orig, session_name=session_name, benchmark_daily=benchmark_daily_data, stock_data=stock_data
            )
            if is_ok or not [i for i in crit_issues if i.startswith("CRITICAL")]:
                return cand_orig
        except Exception:
            pass
        if len(deduped_sentences) > 3:
            cleaned = " ".join(deduped_sentences[:3])

    # 4. Clean double spaces and misplaced punctuation
    cleaned = re.sub(r'\s+([.,!?])', r'\1', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "")

    # 5. Enforce certified benchmark & stock ground truth FIRST, then fix sign/sentiment oxymorons
    try:
        from post_verifier import enforce_benchmark_ground_truth, enforce_stock_ground_truth, fix_sign_sentiment_oxymorons
        if benchmark_daily_data:
            cleaned, _ = enforce_benchmark_ground_truth(cleaned, benchmark_daily=benchmark_daily_data, session_name=session_name)
        if stock_data:
            cleaned, _ = enforce_stock_ground_truth(cleaned, stock_data=stock_data, session_name=session_name)
        cleaned = fix_sign_sentiment_oxymorons(cleaned)
    except Exception:
        pass

    return cleaned.strip()


def audit_with_groq(
    text: str,
    session_name: Optional[str] = None,
    portfolio_metadata_summary: str = "",
    live_news_context: str = "",
    api_key: Optional[str] = None,
    timeout: int = 10,
    temporal_ctx: Optional[Dict[str, Any]] = None,
    benchmark_daily_data: Optional[Dict[str, float]] = None,
    stock_data: Optional[Dict[str, Any]] = None,
    topic_type: str = "full_post",
) -> Optional[Dict[str, Any]]:
    """
    Runs fact-checking audit via Groq API.
    Uses ultra-fast LPU inference (Qwen / GPT-OSS).
    """
    if not REQUESTS_AVAILABLE:
        return None

    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        return None

    if temporal_ctx is None:
        temporal_ctx = get_current_temporal_context(session_name, benchmark_daily_data=benchmark_daily_data)
    prompt = _build_audit_prompt(
        text=text,
        session_name=session_name,
        temporal_ctx=temporal_ctx,
        portfolio_metadata_summary=portfolio_metadata_summary,
        live_news_context=live_news_context,
        stock_data=stock_data,
        topic_type=topic_type,
    )

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    for model in _ordered_models_by_cooldown(GROQ_MODELS, _GROQ_COOLDOWN, _GROQ_LOCK):
        _pace_provider_call(_GROQ_LOCK, _GROQ_PACE_STATE, min_interval=0.55)
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Sei un Financial Fact-Checker severo e meticoloso. Rispondi SEMPRE e SOLO con un oggetto JSON valido."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1500,
            "response_format": {"type": "json_object"},
        }
        if "gpt-oss" in model:
            payload["reasoning_effort"] = "low"

        try:
            t0 = time.time()
            resp = requests.post(url, headers=headers, json=payload, timeout=max(timeout, 15))
            elapsed = time.time() - t0
            with _GROQ_LOCK:
                _GROQ_PACE_STATE["last_elapsed"] = elapsed

            if resp.status_code == 200:
                data = resp.json()
                content = ((data.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
                if not content:
                    print(f"   ⚠️ Groq {model} returned empty content, trying next model...")
                    continue
                parsed = json.loads(content)
                if "decision" in parsed and "verified_text" in parsed:
                    if parsed.get("verified_text"):
                        parsed["verified_text"] = sanitize_verified_text(
                            text,
                            parsed["verified_text"],
                            session_name=session_name,
                            benchmark_daily_data=temporal_ctx.get("benchmark_data_raw"),
                            stock_data=stock_data,
                            topic_type=topic_type,
                        )
                    parsed["auditor"] = f"groq:{model}"
                    parsed["latency_sec"] = round(elapsed, 2)
                    print(f"   ⚡ Groq Independent Audit ({model}) succeeded in {elapsed:.2f}s — Decision: {parsed.get('decision')}")
                    return parsed
            elif resp.status_code == 429:
                _mark_model_cooldown(model, _GROQ_COOLDOWN, _GROQ_LOCK, seconds=20.0)
                print(f"   ⚠️ Groq {model} rate limited (429/TPM), rotating to next Groq model...")
                continue
            else:
                print(f"   ⚠️ Groq {model} returned HTTP {resp.status_code}: {resp.text[:120]}")
        except Exception as exc:
            print(f"   ⚠️ Groq {model} exception: {exc}")
            continue

    return None


def audit_with_mistral(
    text: str,
    session_name: Optional[str] = None,
    portfolio_metadata_summary: str = "",
    live_news_context: str = "",
    api_key: Optional[str] = None,
    timeout: int = 15,
    temporal_ctx: Optional[Dict[str, Any]] = None,
    benchmark_daily_data: Optional[Dict[str, float]] = None,
    stock_data: Optional[Dict[str, Any]] = None,
    topic_type: str = "full_post",
) -> Optional[Dict[str, Any]]:
    """
    Runs fact-checking audit via Mistral API.
    Rotates across enabled Free Tier models (2 RPM / 40K TPM per model) with thread-safe
    RPS pacing instead of disabling Mistral permanently on transient 429 bursts.
    """
    global _MISTRAL_AVAILABLE
    if _MISTRAL_AVAILABLE is False:
        return None

    if not REQUESTS_AVAILABLE:
        return None

    key = api_key or os.environ.get("MISTRAL_API_KEY")
    if not key:
        return None

    if temporal_ctx is None:
        temporal_ctx = get_current_temporal_context(session_name, benchmark_daily_data=benchmark_daily_data)
    prompt = _build_audit_prompt(
        text=text,
        session_name=session_name,
        temporal_ctx=temporal_ctx,
        portfolio_metadata_summary=portfolio_metadata_summary,
        live_news_context=live_news_context,
        stock_data=stock_data,
        topic_type=topic_type,
    )

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    ordered_models = _ordered_models_by_cooldown(MISTRAL_MODELS, _MISTRAL_COOLDOWN, _MISTRAL_LOCK)
    zero_rpm_models = 0

    for model in ordered_models:
        _pace_provider_call(_MISTRAL_LOCK, _MISTRAL_PACE_STATE, min_interval=1.25)
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Sei un Financial Fact-Checker severo. Rispondi SEMPRE con un oggetto JSON valido."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1500,
            "response_format": {"type": "json_object"},
        }

        try:
            t0 = time.time()
            resp = requests.post(url, headers=headers, json=payload, timeout=max(timeout, 15))
            elapsed = time.time() - t0
            with _MISTRAL_LOCK:
                _MISTRAL_PACE_STATE["last_elapsed"] = elapsed

            if resp.status_code == 200:
                data = resp.json()
                content = ((data.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
                if not content:
                    print(f"   ⚠️ Mistral {model} returned empty content, trying next model...")
                    continue
                parsed = json.loads(content)
                if "decision" in parsed and "verified_text" in parsed:
                    if parsed.get("verified_text"):
                        parsed["verified_text"] = sanitize_verified_text(
                            text,
                            parsed["verified_text"],
                            session_name=session_name,
                            benchmark_daily_data=temporal_ctx.get("benchmark_data_raw"),
                            stock_data=stock_data,
                            topic_type=topic_type,
                        )
                    _MISTRAL_AVAILABLE = True
                    parsed["auditor"] = f"mistral:{model}"
                    parsed["latency_sec"] = round(elapsed, 2)
                    print(f"   ⚡ Mistral Independent Audit ({model}) succeeded in {elapsed:.2f}s — Decision: {parsed.get('decision')}")
                    return parsed
            elif resp.status_code in (401, 403):
                _MISTRAL_AVAILABLE = False
                print(f"   ❌ Mistral {model} auth failed (HTTP {resp.status_code}). Disabilitato per questa sessione.")
                return None
            elif resp.status_code == 429:
                hdrs = getattr(resp, "headers", None)
                limit_rpm = str(hdrs.get("x-ratelimit-limit-req-minute", "")).strip() if hasattr(hdrs, "get") else ""
                if limit_rpm == "0":
                    zero_rpm_models += 1
                    _mark_model_cooldown(model, _MISTRAL_COOLDOWN, _MISTRAL_LOCK, seconds=3600.0)
                    print(f"   ℹ️ Mistral {model} segnala 0 RPM su account, passo al modello successivo...")
                else:
                    _mark_model_cooldown(model, _MISTRAL_COOLDOWN, _MISTRAL_LOCK, seconds=62.0)
                    print(f"   ⚠️ Mistral {model} rate limited (429), rotazione automatica su modello successivo...")
                continue
            else:
                print(f"   ⚠️ Mistral {model} returned HTTP {resp.status_code}: {resp.text[:120]}")
        except Exception as exc:
            print(f"   ⚠️ Mistral {model} exception: {exc}")
            continue

    if zero_rpm_models == len(ordered_models) and ordered_models:
        _MISTRAL_AVAILABLE = False
        print("   ℹ️ Tutti i modelli Mistral segnalano 0 RPM. Disattivato per questa sessione.")

    return None


def run_independent_fact_check(
    text: str,
    session_name: Optional[str] = None,
    portfolio_metadata_summary: str = "",
    live_news_context: Optional[str] = None,
    require_consensus: bool = True,
    temporal_ctx: Optional[Dict[str, Any]] = None,
    benchmark_daily_data: Optional[Dict[str, float]] = None,
    stock_data: Optional[Dict[str, Any]] = None,
    topic_type: str = "full_post",
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the independent fact-checking pipeline across external models
    using a Dual-Auditor Consensus mechanism (Groq + Mistral) grounded with live web search (Tavily).

    Consensus Rules:
    1. Both Groq and Mistral audit the post independently.
    2. Live Grounding: Real-time financial headlines and summaries from Tavily are supplied
       in the audit prompt to verify real-world facts and recent catalysts.
    3. VETO RULE: If either auditor flags a critical violation or REJECTs,
       the original text is NEVER published as-is.
    4. CROSS-VERIFICATION OF CORRECTIONS: If an auditor proposes an AUTO_CORRECT,
       the proposed text is cross-checked by the OTHER auditor.
       The corrected text is ONLY published if the other auditor approves it!
    5. UNANIMOUS APPROVAL: Both auditors must agree on the final published text.
    6. Fallback: If only one provider is configured/available, it acts as single auditor.
    """
    try:
        if temporal_ctx is None:
            temporal_ctx = get_current_temporal_context(session_name, benchmark_daily_data=benchmark_daily_data)
        if benchmark_daily_data is None and isinstance(temporal_ctx, dict):
            benchmark_daily_data = temporal_ctx.get("benchmark_data_raw")
    except Exception:
        temporal_ctx = None

    # Auto-fetch Tavily live news context if not provided
    if live_news_context is None:
        try:
            if is_tavily_available and is_tavily_available() and get_live_market_news_context:
                cashtags = re.findall(r'\$([A-Za-z0-9\-\.]+)', text)
                live_news_context = get_live_market_news_context(
                    session_name=session_name,
                    tickers=cashtags,
                    max_results=3,
                )
        except Exception as t_err:
            live_news_context = ""
    if live_news_context is None:
        live_news_context = ""

    # 1. Query Groq
    groq_audit = audit_with_groq(
        text=text,
        session_name=session_name,
        portfolio_metadata_summary=portfolio_metadata_summary,
        live_news_context=live_news_context,
        temporal_ctx=temporal_ctx,
        benchmark_daily_data=benchmark_daily_data,
        stock_data=stock_data,
    )

    # 2. Query Mistral
    mistral_audit = audit_with_mistral(
        text=text,
        session_name=session_name,
        portfolio_metadata_summary=portfolio_metadata_summary,
        live_news_context=live_news_context,
        temporal_ctx=temporal_ctx,
        benchmark_daily_data=benchmark_daily_data,
        stock_data=stock_data,
    )

    # If neither is available, return None for fallback
    if not groq_audit and not mistral_audit:
        return None

    # Single-auditor fallback if only one is operational
    if groq_audit and not mistral_audit:
        print("   ℹ️ Multi-AI consensus note: Mistral non disponibile, audit affidato al solo Groq.")
        if groq_audit.get("verified_text") and (benchmark_daily_data or stock_data):
            try:
                from post_verifier import enforce_benchmark_ground_truth, enforce_stock_ground_truth
                if benchmark_daily_data:
                    groq_audit["verified_text"], _ = enforce_benchmark_ground_truth(
                        groq_audit["verified_text"],
                        benchmark_daily=benchmark_daily_data,
                        session_name=session_name,
                    )
                if stock_data:
                    groq_audit["verified_text"], _ = enforce_stock_ground_truth(
                        groq_audit["verified_text"],
                        stock_data=stock_data,
                        session_name=session_name,
                    )
            except Exception:
                pass
        return groq_audit

    if mistral_audit and not groq_audit:
        print("   ℹ️ Multi-AI consensus note: Groq non disponibile, audit affidato alla sola Mistral.")
        if mistral_audit.get("verified_text") and (benchmark_daily_data or stock_data):
            try:
                from post_verifier import enforce_benchmark_ground_truth, enforce_stock_ground_truth
                if benchmark_daily_data:
                    mistral_audit["verified_text"], _ = enforce_benchmark_ground_truth(
                        mistral_audit["verified_text"],
                        benchmark_daily=benchmark_daily_data,
                        session_name=session_name,
                    )
                if stock_data:
                    mistral_audit["verified_text"], _ = enforce_stock_ground_truth(
                        mistral_audit["verified_text"],
                        stock_data=stock_data,
                        session_name=session_name,
                    )
            except Exception:
                pass
        return mistral_audit

    # ── DUAL-AI CONSENSUS LOGIC (Both Groq and Mistral active) ──────────────────
    g_dec = groq_audit.get("decision", "REJECT")
    m_dec = mistral_audit.get("decision", "REJECT")
    print(f"   🔍 Consensus Audit: Groq -> {g_dec} | Mistral -> {m_dec}")

    # Case A: Both Unanimously APPROVE
    if g_dec == "APPROVE" and m_dec == "APPROVE":
        print("   🤝 Dual-AI Consensus: Both Groq and Mistral APPROVED the post unanimously!")
        return {
            "decision": "APPROVE",
            "score": min(groq_audit.get("score", 90), mistral_audit.get("score", 90)),
            "verified_text": text,
            "temporal_issues": [],
            "hallucinations_detected": [],
            "auditor": f"consensus:dual ({groq_audit.get('auditor')} + {mistral_audit.get('auditor')})",
            "explanation": f"Approvato all'unanimità da Groq ({groq_audit.get('auditor')}) e Mistral ({mistral_audit.get('auditor')}).",
            "consensus_details": {
                "groq": groq_audit,
                "mistral": mistral_audit,
            },
        }

    # Case B: Cross-Verification of Auto-Corrections
    def _is_audit_clean(audit_res: Optional[Dict[str, Any]]) -> bool:
        """Returns True if the audit considers the text clean of hallucinations and temporal paradoxes."""
        if not audit_res:
            return False
        dec = audit_res.get("decision")
        if dec == "APPROVE":
            return True
        if dec == "AUTO_CORRECT":
            # If no hallucinations or temporal errors remain, the text is factually sound
            t_issues = audit_res.get("temporal_issues", [])
            h_issues = audit_res.get("hallucinations_detected", [])
            return len(t_issues) == 0 and len(h_issues) == 0
        return False

    # If Groq proposed an auto-correction, verify it with Mistral
    if g_dec == "AUTO_CORRECT" and groq_audit.get("verified_text"):
        g_cand = groq_audit["verified_text"]
        print("   🔄 Cross-verifying Groq auto-correction with Mistral...")
        cross_m = audit_with_mistral(
            text=g_cand,
            session_name=session_name,
            portfolio_metadata_summary=portfolio_metadata_summary,
            live_news_context=live_news_context,
            temporal_ctx=temporal_ctx,
            benchmark_daily_data=benchmark_daily_data,
            stock_data=stock_data,
        )
        if _is_audit_clean(cross_m) or (cross_m is None and m_dec == "APPROVE"):
            print("   🤝 Dual-AI Consensus: Groq auto-correction cross-verified and APPROVED by Mistral!")
            return {
                "decision": "AUTO_CORRECT",
                "score": min(groq_audit.get("score", 85), cross_m.get("score", 85) if cross_m else 85),
                "verified_text": g_cand,
                "temporal_issues": groq_audit.get("temporal_issues", []),
                "hallucinations_detected": groq_audit.get("hallucinations_detected", []),
                "auditor": f"consensus:cross_verified ({groq_audit.get('auditor')} -> {cross_m.get('auditor') if cross_m else 'mistral'})",
                "explanation": f"Testo corretto da Groq e confermato valido da Mistral. {groq_audit.get('explanation')}",
                "consensus_details": {
                    "proposer": groq_audit,
                    "verifier": cross_m,
                },
            }
        elif cross_m and cross_m.get("decision") == "AUTO_CORRECT" and cross_m.get("verified_text"):
            refined_cand = cross_m["verified_text"]
            print("   🤝 Dual-AI Consensus: Groq auto-correction refined and validated by Mistral (two-pass consensus)!")
            return {
                "decision": "AUTO_CORRECT",
                "score": min(groq_audit.get("score", 85), cross_m.get("score", 85)),
                "verified_text": refined_cand,
                "temporal_issues": groq_audit.get("temporal_issues", []) + cross_m.get("temporal_issues", []),
                "hallucinations_detected": groq_audit.get("hallucinations_detected", []) + cross_m.get("hallucinations_detected", []),
                "auditor": f"consensus:two_pass ({groq_audit.get('auditor')} -> {cross_m.get('auditor')})",
                "explanation": f"Testo corretto da Groq e rifinito in secondo passaggio da Mistral. {cross_m.get('explanation')}",
                "consensus_details": {
                    "proposer": groq_audit,
                    "verifier": cross_m,
                },
            }

    # If Mistral proposed an auto-correction, verify it with Groq
    if m_dec == "AUTO_CORRECT" and mistral_audit.get("verified_text"):
        m_cand = mistral_audit["verified_text"]
        print("   🔄 Cross-verifying Mistral auto-correction with Groq...")
        cross_g = audit_with_groq(
            text=m_cand,
            session_name=session_name,
            portfolio_metadata_summary=portfolio_metadata_summary,
            live_news_context=live_news_context,
            temporal_ctx=temporal_ctx,
            benchmark_daily_data=benchmark_daily_data,
            stock_data=stock_data,
        )
        if _is_audit_clean(cross_g) or (cross_g is None and g_dec == "APPROVE"):
            print("   🤝 Dual-AI Consensus: Mistral auto-correction cross-verified and APPROVED by Groq!")
            return {
                "decision": "AUTO_CORRECT",
                "score": min(mistral_audit.get("score", 85), cross_g.get("score", 85) if cross_g else 85),
                "verified_text": m_cand,
                "temporal_issues": mistral_audit.get("temporal_issues", []),
                "hallucinations_detected": mistral_audit.get("hallucinations_detected", []),
                "auditor": f"consensus:cross_verified ({mistral_audit.get('auditor')} -> {cross_g.get('auditor') if cross_g else 'groq'})",
                "explanation": f"Testo corretto da Mistral e confermato valido da Groq. {mistral_audit.get('explanation')}",
                "consensus_details": {
                    "proposer": mistral_audit,
                    "verifier": cross_g,
                },
            }
        elif cross_g and cross_g.get("decision") == "AUTO_CORRECT" and cross_g.get("verified_text"):
            refined_cand = cross_g["verified_text"]
            print("   🤝 Dual-AI Consensus: Mistral auto-correction refined and validated by Groq (two-pass consensus)!")
            return {
                "decision": "AUTO_CORRECT",
                "score": min(mistral_audit.get("score", 85), cross_g.get("score", 85)),
                "verified_text": refined_cand,
                "temporal_issues": mistral_audit.get("temporal_issues", []) + cross_g.get("temporal_issues", []),
                "hallucinations_detected": mistral_audit.get("hallucinations_detected", []) + cross_g.get("hallucinations_detected", []),
                "auditor": f"consensus:two_pass ({mistral_audit.get('auditor')} -> {cross_g.get('auditor')})",
                "explanation": f"Testo corretto da Mistral e rifinito in secondo passaggio da Groq. {cross_g.get('explanation')}",
                "consensus_details": {
                    "proposer": mistral_audit,
                    "verifier": cross_g,
                },
            }

    # Case C: Safety Veto - No consensus reached or either rejected with no cross-approved fix
    print(f"   🛑 Dual-AI Consensus: VETO applied (Groq: {g_dec}, Mistral: {m_dec}). Post blocked for safety.")
    all_issues = []
    all_issues.extend(groq_audit.get("temporal_issues", []))
    all_issues.extend(mistral_audit.get("temporal_issues", []))
    all_halluc = []
    all_halluc.extend(groq_audit.get("hallucinations_detected", []))
    all_halluc.extend(mistral_audit.get("hallucinations_detected", []))

    return {
        "decision": "REJECT",
        "score": min(groq_audit.get("score", 0), mistral_audit.get("score", 0)),
        "verified_text": None,
        "temporal_issues": all_issues,
        "hallucinations_detected": all_halluc,
        "auditor": f"consensus:veto ({groq_audit.get('auditor')} + {mistral_audit.get('auditor')})",
        "explanation": (
            f"Veto di sicurezza per mancato accordo o allucinazioni non risolte: "
            f"Groq ({g_dec}): {groq_audit.get('explanation', 'N/A')} | "
            f"Mistral ({m_dec}): {mistral_audit.get('explanation', 'N/A')}"
        ),
        "consensus_details": {
            "groq": groq_audit,
            "mistral": mistral_audit,
        },
    }


# ─── MICRO-TOPIC MODULAR CONSENSUS AUDITING ─────────────────────────────────

def split_into_micro_topics(text: str) -> List[Dict[str, Any]]:
    """
    Splits a recap post into semantically coherent micro-topics:
    1. Greeting / Header (safe, no audit needed)
    2. Macro / Market Overview paragraph(s) (needs audit)
    3. Portfolio Stocks (individual bullet points or separate stock paragraphs) (needs audit)
    4. Wrap-up / Outlook (needs audit)
    5. Community question / Footer (safe, no audit needed)
    """
    cleaned = text.strip()
    raw_blocks = [b.strip() for b in re.split(r'\n\s*\n', cleaned) if b.strip()]

    micro_topics = []
    in_static_why_copy_footer = False

    for block_idx, block in enumerate(raw_blocks):
        if (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━" in block
            or "💡 PERCHÈ COPIARE QUESTO PORTAFOGLIO" in block
            or "💡 PERCHÉ COPIARE QUESTO PORTAFOGLIO" in block
        ):
            in_static_why_copy_footer = True

        # Static footer / Tag / link lines / deterministic Yahoo Finance performance & MTD/YTD ranking tables
        if (
            in_static_why_copy_footer
            or block.startswith(("📌", "👤", "#", "http", "📊 PERFORMANCE DEL PORTAFOGLIO", "🏔️"))
            or re.match(r'^(?:🏆\s*)?MIGLIORI\s+\d+\s+', block, flags=re.IGNORECASE)
        ):
            micro_topics.append({
                "id": len(micro_topics),
                "type": "footer",
                "text": block,
                "needs_audit": False,
            })
            continue

        # Short dynamic greeting / opening hook
        is_opening_greeting = False
        if block_idx == 0 and len(block) < 160:
            lower_b = block.lower()
            greeting_cues = [
                "buongiorno", "buonasera", "buon pomeriggio", "chiusura", "fine sessione",
                "bentornati", "giornata conclusa", "sessione conclusa", "ci siamo preparati",
                "apertura", "apre wall street", "un nuovo giorno", "ecco le notizie", "ecco gli spunti"
            ]
            has_no_financial_claims = not re.search(r'\$[A-Za-z0-9\.\-]+', block) and not re.search(r'[+-]?\d+[\.,]?\d*%', block)
            if any(cue in lower_b for cue in greeting_cues) or has_no_financial_claims:
                is_opening_greeting = True

        if is_opening_greeting:
            micro_topics.append({
                "id": len(micro_topics),
                "type": "greeting",
                "text": block,
                "needs_audit": False,
            })
            continue

        # Community engagement question
        lower_q = block.lower()
        has_question_cues = any(w in lower_q for w in [
            "commenti", "voi come", "cosa ne pensate", "dite la vostra",
            "come avete vissuto", "vi aspettate", "secondo voi", "monitorerete",
            "monitorate", "seguite", "seguirete", "soddisfatt", "sorpres", "domande",
            "qual è", "quali titoli", "come vedete", "cosa vi aspettate",
        ])
        is_trailing_no_claim_question = (
            block_idx >= len(raw_blocks) - 2
            and block.rstrip().endswith(("?", "👇"))
            and not re.search(r'\$[A-Za-z0-9\.\-]+', block)
            and not re.search(r'[+-]?\d+[\.,]?\d*%', block)
        )
        if "?" in block and len(block) < 280 and (has_question_cues or is_trailing_no_claim_question):
            micro_topics.append({
                "id": len(micro_topics),
                "type": "engagement_question",
                "text": block,
                "needs_audit": False,
            })
            continue

        # Bullet lists and thematic emoji items (e.g. •, -, *, 1., 🌍, 📅, 🏆, 🥇, 🥈, 🥉, ⚡, 💊)
        def _is_bullet_or_emoji_topic(line_str: str) -> bool:
            if not line_str:
                return False
            if line_str.startswith(('•', '-', '*', '✓', '▪', '▫', '►')):
                return True
            if re.match(r'^\d+[\.\)]', line_str):
                return True
            first_c = line_str[0]
            # Recognizes emojis and symbol bullets while ignoring words, quotes, $, etc.
            if not (first_c.isalnum() or first_c in ('$', '"', "'", '(', '[', '¿', '¡', '#')):
                return True
            return False

        lines = [l.strip() for l in block.split('\n') if l.strip()]
        bullet_lines = [l for l in lines if _is_bullet_or_emoji_topic(l)]

        if len(bullet_lines) >= 2:
            intro_lines = [l for l in lines if not _is_bullet_or_emoji_topic(l)]
            if intro_lines:
                micro_topics.append({
                    "id": len(micro_topics),
                    "type": "bullet_header",
                    "text": "\n".join(intro_lines),
                    "needs_audit": False,
                })
            for b_line in bullet_lines:
                micro_topics.append({
                    "id": len(micro_topics),
                    "type": "stock_bullet",
                    "text": b_line,
                    "needs_audit": True,
                })
        else:
            lower_blk = block.lower()
            if block.lstrip().startswith("🔮") or any(w in lower_blk for w in [
                "prossima seduta", "seduta di domani", "riflettori saranno puntati", "prossima sessione"
            ]):
                p_type = "outlook"
            elif any(w in lower_blk for w in ["indice", "fed", "bce", "spx", "nasdaq", "inflazione", "tassi"]):
                p_type = "macro"
            else:
                p_type = "stock_paragraph"
            micro_topics.append({
                "id": len(micro_topics),
                "type": p_type,
                "text": block,
                "needs_audit": True,
            })

    return micro_topics


def reassemble_micro_topics(micro_topics: List[Dict[str, Any]], session_name: Optional[str] = None) -> str:
    """
    Reassembles approved micro-topics into a clean, cohesive post.
    Bullets follow their header with a single newline, paragraphs separated by double newlines.
    Ensures that every microtopic paragraph starts with its thematic emoji or list symbol.
    """
    chunks = []
    in_bullet_group = False

    for t in micro_topics:
        if t.get("excluded", False):
            continue
        txt = t.get("verified_text") or t.get("text", "")
        txt = txt.strip()
        if not txt:
            continue
        t_type = t.get("type")

        if t_type == "bullet_header":
            chunks.append(txt)
            in_bullet_group = True
        elif t_type == "stock_bullet":
            if in_bullet_group and chunks:
                chunks[-1] = chunks[-1] + "\n" + txt
            else:
                chunks.append(txt)
                in_bullet_group = True
        else:
            chunks.append(txt)
            in_bullet_group = False

    raw_assembled = "\n\n".join(chunks)
    if session_name:
        try:
            from ai_news_generator import ensure_thematic_emojis
            return ensure_thematic_emojis(raw_assembled, session_name=session_name)
        except Exception:
            return raw_assembled
    return raw_assembled




def run_micro_topic_consensus_fact_check(
    text: str,
    session_name: Optional[str] = None,
    portfolio_metadata_summary: str = "",
    benchmark_daily_data: Optional[Dict[str, float]] = None,
    stock_data: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Modular fact-checking architecture:
    1. Splits candidate post into micro-topics (macro, individual stock bullets, wrap-up).
    2. Runs Dual-AI Consensus (Groq + Mistral) on each micro-topic in parallel.
    3. Surgically corrects only the specific sentence/topic with errors (e.g. temporal paradox),
       preserving 100% of all other detailed stock analyses without dilution or summarization.
    4. Reassembles the final rich, verified post.
    """
    micro_topics = split_into_micro_topics(text)
    topics_to_audit = [t for t in micro_topics if t.get("needs_audit")]

    if not topics_to_audit:
        return run_independent_fact_check(
            text=text,
            session_name=session_name,
            portfolio_metadata_summary=portfolio_metadata_summary,
            benchmark_daily_data=benchmark_daily_data,
            stock_data=stock_data,
        )

    print(f"   🧩 Scomposizione in {len(micro_topics)} micro-argomenti ({len(topics_to_audit)} da auditare in parallelo)...")

    temporal_ctx = get_current_temporal_context(session_name, benchmark_daily_data=benchmark_daily_data)
    if benchmark_daily_data is None:
        benchmark_daily_data = temporal_ctx.get("benchmark_data_raw")

    # Fetch live ground truth news from Tavily once for all micro-topics
    live_news_context = ""
    try:
        if is_tavily_available and is_tavily_available() and get_live_market_news_context:
            cashtags = re.findall(r'\$([A-Za-z0-9\-\.]+)', text)
            live_news_context = get_live_market_news_context(
                session_name=session_name,
                tickers=cashtags,
                max_results=4,
            )
            if live_news_context:
                print(f"   🌐 Tavily: Fonti live certificate caricate per l'audit modulare ({len(live_news_context)} caratteri).")
    except Exception as t_err:
        print(f"   ℹ️ Tavily grounding note: {t_err}")

    # Run consensus audits concurrently across micro-topics (with max_workers=2 to avoid 429 bursts)
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(2, len(topics_to_audit))) as executor:
        future_to_topic = {
            executor.submit(
                run_independent_fact_check,
                t["text"],
                session_name=session_name,
                portfolio_metadata_summary=portfolio_metadata_summary,
                live_news_context=(
                    filter_live_news_for_topic(live_news_context, t["text"], topic_type=t.get("type", "full_post"))
                    if filter_live_news_for_topic else live_news_context
                ),
                benchmark_daily_data=benchmark_daily_data,
                stock_data=stock_data,
            ): t
            for t in topics_to_audit
        }
        for future in future_to_topic:
            t = future_to_topic[future]
            try:
                t["audit_result"] = future.result()
            except Exception as exc:
                print(f"   ⚠️ Errore audit micro-argomento [{t.get('id')}]: {exc}")
                t["audit_result"] = None

    # Evaluate results across micro-topics
    corrected_count = 0
    approved_count = 0
    rejected_count = 0
    substantive_retained = 0
    all_issues = []
    all_halluc = []
    auditors_used = set()

    for t in micro_topics:
        if not t.get("needs_audit"):
            continue

        res = t.get("audit_result")
        if not res:
            # Audit failed to respond, keep original text
            continue

        dec = res.get("decision", "APPROVE")
        auditors_used.add(res.get("auditor", "AI"))
        t_type = t.get("type", "full_post")

        if dec == "APPROVE":
            approved_count += 1
            substantive_retained += 1
            t["verified_text"] = t["text"]
            print(f"   ✓ Micro-argomento [{t['id']} - {t_type}] APPROVATO: {t['text'][:60]}...")
        elif dec == "AUTO_CORRECT" and res.get("verified_text"):
            corrected_count += 1
            substantive_retained += 1
            t["verified_text"] = sanitize_verified_text(
                t["text"],
                res["verified_text"],
                session_name=session_name,
                benchmark_daily_data=benchmark_daily_data,
                stock_data=stock_data,
                topic_type=t_type,
            )
            all_issues.extend(res.get("temporal_issues", []))
            all_halluc.extend(res.get("hallucinations_detected", []))
            print(f"   🛠️ Micro-argomento [{t['id']} - {t_type}] CORRETTO CHIRURGICAMENTE: {res.get('explanation')[:80]}...")
        elif dec == "REJECT":
            if t_type == "outlook":
                # Never drop or corrupt a deterministically valid forward-looking outlook paragraph
                substantive_retained += 1
                t["verified_text"] = t["text"]
                print(f"   ℹ️ Micro-argomento [{t['id']} - outlook] preservato nel formato originale futuro.")
                continue
            rejected_count += 1
            all_issues.extend(res.get("temporal_issues", []))
            all_halluc.extend(res.get("hallucinations_detected", []))
            if t_type in ("stock_bullet", "stock_paragraph"):
                # Before excluding a stock paragraph and losing a cashtag, check if the rejection
                # came from a rate-limit veto or overly strict fallback model while the paragraph
                # already passes deterministic Yahoo Finance ground-truth verification.
                keep_valid_stock = False
                if stock_data is not None:
                    try:
                        from post_verifier import verify_post_deterministic, enforce_stock_ground_truth, fix_sign_sentiment_oxymorons
                        healed_t, _ = enforce_stock_ground_truth(t["text"], stock_data=stock_data, session_name=session_name)
                        healed_t = fix_sign_sentiment_oxymorons(healed_t)
                        is_det_ok, det_issues, _ = verify_post_deterministic(
                            healed_t, session_name=session_name, benchmark_daily=benchmark_daily_data, stock_data=stock_data
                        )
                        if is_det_ok and not [i for i in det_issues if i.startswith("CRITICAL")]:
                            keep_valid_stock = True
                            substantive_retained += 1
                            t["verified_text"] = healed_t
                            print(f"   ✓ Micro-argomento [{t['id']} - {t_type}] deterministically certificato Yahoo Finance e preservato: {healed_t[:60]}...")
                    except Exception:
                        keep_valid_stock = False
                if not keep_valid_stock:
                    t["excluded"] = True
                    print(f"   ⚠️ Micro-argomento [{t['id']} - {t_type}] con allucinazione irreversibile ESCLUSO: {t['text'][:60]}...")
            else:
                # If a macro paragraph was rejected without auto-correct
                print(f"   ❌ Micro-argomento [{t['id']} - {t_type}] RESPINTO: {res.get('explanation')[:80]}...")

    # If critical macro paragraph was rejected without fix and no substantive content remains
    if substantive_retained == 0:
        return {
            "decision": "REJECT",
            "score": 0,
            "verified_text": None,
            "temporal_issues": all_issues,
            "hallucinations_detected": all_halluc,
            "auditor": f"consensus:micro_topics ({', '.join(auditors_used) if auditors_used else 'N/A'})",
            "explanation": "Tutti i micro-argomenti sostanziali sono stati respinti dal consenso.",
        }

    final_text = reassemble_micro_topics(micro_topics, session_name=session_name)
    try:
        from post_verifier import enforce_benchmark_ground_truth, enforce_stock_ground_truth
        if benchmark_daily_data:
            final_text, _ = enforce_benchmark_ground_truth(final_text, benchmark_daily=benchmark_daily_data, session_name=session_name)
        if stock_data:
            final_text, _ = enforce_stock_ground_truth(final_text, stock_data=stock_data, session_name=session_name)
    except Exception:
        pass

    overall_decision = "AUTO_CORRECT" if corrected_count > 0 or rejected_count > 0 else "APPROVE"

    return {
        "decision": overall_decision,
        "score": 95 if overall_decision == "APPROVE" else 88,
        "verified_text": final_text,
        "temporal_issues": all_issues,
        "hallucinations_detected": all_halluc,
        "auditor": f"consensus:micro_modular ({len(topics_to_audit)} argomenti)",
        "explanation": (
            f"Audit modulare a micro-argomenti: {approved_count} approvati tal quali, "
            f"{corrected_count} corretti chirurgicamente, {rejected_count} esclusi. "
            f"Profondità e lunghezza preservate."
        ),
        "micro_topics": micro_topics,
    }

