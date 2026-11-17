#!/usr/bin/env python3
"""
Economic Calendar & Weekly Macro Events Module
==============================================
Fetches and structures high-impact macroeconomic catalysts of the week
for Monday morning community polls on eToro Social Feed.

Features:
  1. Live search via Google Gemini + Google Search Grounding (if GEMINI_API_KEY available)
  2. Direct JSON feed fallback (ForexFactory / FairEconomy)
  3. Dynamic rotating macro themes as fail-safe fallback
  4. Strict eToro compliance: options <= 28 chars, no '#' hashtags
"""

import os
import sys
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Ensure src in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────────────────────────────────────
# Resilient Fallback Macro Catalysts (Used if offline / network error)
# ─────────────────────────────────────────────────────────────────────────────
FALLBACK_MACRO_TEMPLATES = [
    {
        "title": "Macro della settimana: quale catalizzatore guiderà i mercati? 🗓️",
        "options": [
            "Inflazione USA (CPI/PPI)",
            "Decisioni Tassi BCE/Fed",
            "Dati Occupazione & NFP",
            "Altro (nei commenti)",
        ],
        "tickers": ["SPX500", "NSDQ100", "EURUSD"],
        "message": (
            "🗓️ CALENDARIO MACRO DELLA SETTIMANA\n\n"
            "I market mover più attesi da monitorare sui mercati:\n"
            "▪️ Lunedì: Apertura mercati e monitoraggio flussi azionari\n"
            "▪️ Martedì: Dati bilancia commerciale e aste governative\n"
            "▪️ Mercoledì: Scorte energetiche e discorsi banchieri centrali\n"
            "▪️ Giovedì: Decisioni tassi d'interesse & PPI prezzi produzione\n"
            "▪️ Venerdì: Inflazione (CPI) & report occupazione USA\n\n"
            "Quale tra questi catalizzatori peserà di più sui mercati?\n"
            "Votate con 1 tap qui sotto e condividete la vostra visione nei commenti! 👇"
        ),
    },
    {
        "title": "Banche Centrali & Tassi: quale catalizzatore peserà di più? 🏦",
        "options": [
            "Tassi & Discorsi Fed",
            "Politica Monetaria BCE",
            "Rendimenti Bond & Spread",
            "Altro (nei commenti)",
        ],
        "tickers": ["SPX500", "NSDQ100", "SX7PEX.DE", "IB01.L"],
        "message": (
            "🗓️ CALENDARIO MACRO: FOCUS BANCHE CENTRALI E TASSI\n\n"
            "I principali appuntamenti monetari della settimana:\n"
            "▪️ Lunedì: Analisi della curva dei rendimenti obbligazionari\n"
            "▪️ Martedì: Interventi esponenti Federal Reserve\n"
            "▪️ Mercoledì: Riunioni preparatorie e minute di politica monetaria\n"
            "▪️ Giovedì: Decisione ufficiale sui tassi d'interesse BCE\n"
            "▪️ Venerdì: Dati su inflazione attesa e fiducia dei consumatori\n\n"
            "Su quale fronte vi aspettate la maggiore volatilità per azioni e bond?\n"
            "Esprimete il vostro voto e commentate la vostra strategia! 👇"
        ),
    },
    {
        "title": "Dati USA vs Europa: quale sorpresa muoverà i mercati? 📊",
        "options": [
            "Inflazione & Consumi USA",
            "PIL & Manifattura Europa",
            "Trimestrali & Outlook",
            "Altro (nei commenti)",
        ],
        "tickers": ["SPX500", "IEUR", "ENI.MI"],
        "message": (
            "🗓️ CALENDARIO MACRO: USA ED EUROPA A CONFRONTO\n\n"
            "Gli appuntamenti economici più attesi dell'ottava:\n"
            "▪️ Lunedì: Reazione iniziale dei listini europei e Wall Street\n"
            "▪️ Martedì: Indici PMI manifatturieri e dei servizi Eurozona\n"
            "▪️ Mercoledì: Dati su consumi e vendite al dettaglio USA\n"
            "▪️ Giovedì: Report inflazione all'ingrosso (PPI) e sussidi disoccupazione\n"
            "▪️ Venerdì: Indice prezzi al consumo (CPI) e sentiment Michigan\n\n"
            "Quale area geografica o catalizzatore determinerà la direzione dei flussi?\n"
            "Votate nel sondaggio e scrivete la vostra analisi nei commenti! 👇"
        ),
    },
]


def _clean_no_hashtags(text: str) -> str:
    """Strictly remove any '#' hashtags from text as required for eToro."""
    cleaned = re.sub(r"#([A-Za-z0-9_]+)", "", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def smart_truncate(text: str, max_chars: int = 700) -> str:
    """
    Truncates text cleanly without cutting mid-word or mid-sentence.
    Prioritizes sentence boundaries (. ! ? \n) to avoid abrupt cutoffs.
    """
    cleaned = text.strip()
    if len(cleaned) <= max_chars:
        return cleaned

    sub = cleaned[:max_chars]

    # Search for sentence terminators (. ! ?) followed by whitespace, newline, or end
    sentence_matches = list(re.finditer(r'([.!?])(\s+|\n+|$)', sub))
    if sentence_matches:
        last_match = sentence_matches[-1]
        cutoff = last_match.start() + 1
        candidate = sub[:cutoff].strip()
        if len(candidate) >= max_chars * 0.25:
            return candidate

    # Fallback to last newline (e.g. at the end of a calendar bullet line)
    last_nl = sub.rfind('\n')
    if last_nl > max_chars * 0.25:
        return sub[:last_nl].strip()

    # Fallback to last word boundary
    last_space = sub.rfind(' ')
    if last_space > 0:
        return sub[:last_space].strip() + "..."

    return sub.strip()


def _sanitize_macro_poll(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize poll data to strictly comply with eToro limits and hashtag prohibition."""
    raw_title = data.get("title") or "Eventi Macro della Settimana: quale guiderà i mercati? 🗓️"
    title = _clean_no_hashtags(raw_title)[:200].strip()
    title = smart_truncate(_clean_no_hashtags(raw_title), 200)

    raw_options = data.get("options") or []
    cleaned_options: List[str] = []
    for opt in raw_options:
        clean_opt = _clean_no_hashtags(str(opt)).strip()
        if clean_opt:
            # Enforce eToro strict limit: <= 28 characters
            cleaned_options.append(clean_opt[:28].strip())

    if len(cleaned_options) < 2:
        cleaned_options = [
            "Inflazione USA (CPI/PPI)",
            "Decisione Tassi BCE/Fed",
            "Dati Occupazione USA",
            "Altro (nei commenti)",
        ]
    cleaned_options = cleaned_options[:4]

    raw_message = data.get("message") or ""
    # Smart truncate cleanly to 700 chars max, leaving abundant space for the footer
    message = smart_truncate(_clean_no_hashtags(raw_message), 700)

    tickers = data.get("tickers") or ["SPX500", "NSDQ100", "EURUSD"]
    clean_tickers = [t.replace("$", "").strip().upper() for t in tickers if t]

    return {
        "title": title,
        "options": cleaned_options,
        "message": message,
        "tickers": clean_tickers,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. Google Gemini with Live Search Grounding
# ─────────────────────────────────────────────────────────────────────────────
def fetch_macro_calendar_gemini() -> Optional[Dict[str, Any]]:
    """
    Use Google Gemini with Google Search tool to find actual scheduled
    macroeconomic events of the current week and return structured poll data.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return None

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None

    today_str = datetime.now(timezone.utc).strftime("%A %d %B %Y")
    prompt = f"""
Sei un analista finanziario professionista e gestore di portafoglio.
Data odierna: {today_str}.

Cerca sul web i principali EVENTI MACROECONOMICI (Economic Calendar) previsti per QUESTA SETTIMANA (da lunedì a venerdì) con particolare attenzione a USA ed Europa (es. CPI inflazione USA, decisioni tassi BCE o Federal Reserve, Non-Farm Payrolls, discorsi Powell/Lagarde, PPI, PIL, vendite al dettaglio).

Genera un sondaggio d'impatto per il feed social di eToro, strutturato in JSON valido.
REGOLE TASSATIVE DI FORMATTAZIONE:
1. 'poll_title': Titolo/domanda del sondaggio (massimo 150 caratteri). Es: "Eventi Macro della Settimana: quale guiderà i mercati? 🗓️"
2. 'options': Array di esattamente 4 opzioni sintetiche degli eventi più importanti.
   ATTENZIONE LIMITE RIGIDO ETORO: CIASCUNA OPZIONE DEVE ESSERE AL MASSIMO DI 28 CARATTERI!
   Esempi validi (<28 car): "Decisione Tassi BCE", "Inflazione USA (CPI)", "Dati Occupazione NFP", "Altro (nei commenti)".
3. 'message': Il post DEVE essere formattato OBBLIGATORIAMENTE come CALENDARIO GIORNO PER GIORNO con elenco puntato da Lunedì a Venerdì, seguito dalla chiamata all'azione per votare.
   Esempio di struttura:
   🗓️ CALENDARIO MACRO DELLA SETTIMANA

   I principali market mover da seguire giorno per giorno:
   ▪️ Lunedì: [sintesi evento o avvio ottava]
   ▪️ Martedì: [sintesi evento]
   ▪️ Mercoledì: [sintesi evento]
   ▪️ Giovedì: [sintesi evento, es. Tassi BCE & PPI USA]
   ▪️ Venerdì: [sintesi evento, es. Inflazione CPI USA]

   Quale tra questi appuntamenti guiderà maggiormente i mercati?
   Votate nel sondaggio qui sotto con 1 tap! 👇

   VINCOLO DI LUNGHEZZA FONDAMENTALE: Il testo del 'message' deve essere tra 400 e 600 caratteri massimi (CONCISO, frasi complete, NESSUNA interruzione o troncamento a metà).
   DIVIETO ASSOLUTO DI HASHTAG: NON usare MAI il carattere '#' né hashtag (es. NO #eToro, NO #Trading). Usa solo cashtag come $SPX500, $NSDQ100.
4. 'tickers': Array di simboli relativi ai mercati impattati (es. ["SPX500", "NSDQ100", "EURUSD"]).

Restituisci SOLO il blocco JSON nel seguente formato:
{{
  "poll_title": "...",
  "options": ["...", "...", "...", "..."],
  "message": "...",
  "tickers": ["SPX500", "NSDQ100", "EURUSD"]
}}
"""

    try:
        from ai_model_cascade import DEFAULT_GEMINI_MODELS, build_http_options, build_thinking_config
    except ImportError:
        try:
            from src.ai_model_cascade import DEFAULT_GEMINI_MODELS, build_http_options, build_thinking_config
        except ImportError:
            DEFAULT_GEMINI_MODELS = [
                "gemini-4-hydrogen",
                "gemini-3.6-flash",
                "gemini-3-flash-preview",
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.1-flash-lite",
                "gemini-2.5-flash",
            ]
            def build_http_options(tm, timeout_seconds=55.0, api_version="v1beta"):
                return tm.HttpOptions(timeout=int(timeout_seconds * 1000), api_version=api_version) if hasattr(tm, "HttpOptions") else None
            def build_thinking_config(tm, m, fast_mode=False, budget=None):
                return None

    try:
        http_opts = build_http_options(types, timeout_seconds=55.0)
        client = genai.Client(api_key=gemini_key, http_options=http_opts) if http_opts else genai.Client(api_key=gemini_key)
        use_search_tool = True
        models_to_try = list(DEFAULT_GEMINI_MODELS)

        for model in models_to_try:
            t_cfg = build_thinking_config(types, model, fast_mode=True)
            cfg_base = {"temperature": 0.3, "max_output_tokens": 3072}
            if t_cfg is not None:
                cfg_base["thinking_config"] = t_cfg
            try:
                cfg = types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())] if use_search_tool else None,
                    **cfg_base,
                )
                resp = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=cfg,
                )
            except Exception as inner_err:
                if use_search_tool and ("429" in str(inner_err) or "quota" in str(inner_err).lower() or "search" in str(inner_err).lower()):
                    use_search_tool = False
                    try:
                        resp = client.models.generate_content(
                            model=model,
                            contents=prompt,
                            config=types.GenerateContentConfig(**cfg_base),
                        )
                    except Exception as e2:
                        print(f"⚠️ Gemini model {model} attempt failed: {e2}")
                        continue
                else:
                    print(f"⚠️ Gemini model {model} attempt failed: {inner_err}")
                    continue

            try:
                if resp and resp.text:
                    text = resp.text.strip()
                    json_match = re.search(r"\{.*\}", text, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        poll_data = {
                            "title": parsed.get("poll_title") or parsed.get("title"),
                            "options": parsed.get("options"),
                            "message": parsed.get("message"),
                            "tickers": parsed.get("tickers") or ["SPX500", "NSDQ100", "EURUSD"],
                        }
                        sanitized = _sanitize_macro_poll(poll_data)
                        print(f"✅ Successfully generated Macro Calendar poll via Gemini ({model})!")
                        return sanitized
            except Exception as e:
                print(f"⚠️ Gemini model {model} parse failed: {e}")
                continue

    except Exception as e:
        print(f"⚠️ Error running Gemini live search for macro calendar: {e}")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 2. FairEconomy / ForexFactory Public JSON Feed
# ─────────────────────────────────────────────────────────────────────────────
def fetch_macro_calendar_feed() -> Optional[Dict[str, Any]]:
    """
    Fetch economic calendar from FairEconomy/ForexFactory JSON feed.
    """
    import urllib.request

    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                high_events = [
                    e for e in data
                    if e.get("impact") == "High" and e.get("country") in ("USD", "EUR", "GBP")
                ]
                if high_events:
                    seen = set()
                    unique = []
                    for e in high_events:
                        title_clean = e["title"].split(" m/m")[0].split(" y/y")[0].strip()
                        key = (e["country"], title_clean)
                        if key not in seen:
                            seen.add(key)
                            unique.append((e["country"], title_clean, e.get("date", "")))

                    options = []
                    details = []
                    for country, title, _ in unique[:3]:
                        # Translate / shorten to <= 28 chars
                        short_title = title
                        if "CPI" in title:
                            short_title = "Inflazione (CPI)"
                        elif "PPI" in title:
                            short_title = "Prezzi Prod. (PPI)"
                        elif "Monetary Policy" in title or "Statement" in title:
                            short_title = "Comunicato Tassi"
                        elif "Refinancing Rate" in title or "Interest Rate" in title:
                            short_title = "Decisione Tassi"
                        elif "Press Conference" in title:
                            short_title = "Conferenza Stampa"
                        elif "Employment" in title or "Payrolls" in title:
                            short_title = "Dati Lavoro (NFP)"
                        elif "GDP" in title:
                            short_title = "Dati PIL"
                        elif "Retail Sales" in title:
                            short_title = "Vendite Dettaglio"
                        elif "PMI" in title:
                            short_title = "Indici PMI"

                        opt_str = f"[{country}] {short_title}".strip()
                        if len(opt_str) > 28:
                            opt_str = opt_str[:28].rstrip()
                        options.append(opt_str)
                        details.append(f"• {country}: {title}")

                    options.append("Altro (nei commenti)")
                    options = options[:4]

                    # Group events into Day-by-Day Calendar
                    day_names = {0: "Lunedì", 1: "Martedì", 2: "Mercoledì", 3: "Giovedì", 4: "Venerdì"}
                    default_descs = {
                        0: "Avvio settimana e monitoraggio flussi azionari",
                        1: "Dati macroeconomici e aste di titoli di stato",
                        2: "Scorte energetiche e discorsi banche centrali",
                        3: "Decisioni tassi BCE e dati prezzi produzione (PPI)",
                        4: "Report inflazione (CPI) e dati sulla fiducia",
                    }
                    day_events: Dict[int, List[str]] = {i: [] for i in range(5)}
                    for e in high_events:
                        dt_val = e.get("date", "")
                        try:
                            dt_obj = datetime.fromisoformat(dt_val)
                            dow = dt_obj.weekday()
                            if dow in day_events:
                                title_c = e["title"].split(" m/m")[0].split(" y/y")[0].strip()
                                ctry = e.get("country", "")
                                if "CPI" in title_c:
                                    item_t = "Inflazione (CPI)"
                                elif "PPI" in title_c:
                                    item_t = "Prezzi Prod. (PPI)"
                                elif "Refinancing Rate" in title_c or "Interest Rate" in title_c:
                                    item_t = f"Tassi {ctry}"
                                elif "Monetary Policy" in title_c:
                                    item_t = f"Comunicato {ctry}"
                                elif "Employment" in title_c or "Payrolls" in title_c:
                                    item_t = f"Dati Lavoro {ctry}"
                                elif "GDP" in title_c:
                                    item_t = f"PIL {ctry}"
                                else:
                                    item_t = f"{title_c} ({ctry})"
                                if item_t not in day_events[dow]:
                                    day_events[dow].append(item_t)
                        except Exception:
                            pass

                    calendar_bullets = []
                    for dow in range(5):
                        dname = day_names[dow]
                        evts = day_events[dow]
                        if evts:
                            line_desc = " & ".join(evts[:2])
                        else:
                            line_desc = default_descs[dow]
                        calendar_bullets.append(f"▪️ {dname}: {line_desc}")

                    message = (
                        "🗓️ CALENDARIO MACRO DELLA SETTIMANA\n\n"
                        "I principali market mover da seguire giorno per giorno:\n"
                        + "\n".join(calendar_bullets)
                        + "\n\nQuale tra questi appuntamenti guiderà maggiormente il trend dei mercati?\n"
                        "Votate con 1 tap nel sondaggio e dite la vostra nei commenti! 👇"
                    )

                    return _sanitize_macro_poll({
                        "title": "Calendario Economico: quale dato guiderà i mercati? 🗓️",
                        "options": options,
                        "message": message,
                        "tickers": ["SPX500", "NSDQ100", "EURUSD"],
                    })
    except Exception as e:
        print(f"ℹ️ FairEconomy JSON feed not available or rate-limited: {e}")

    return None


_DAILY_FEED_CACHE: Dict[str, Any] = {"ts": 0.0, "events": None}


def _fetch_raw_calendar_events() -> List[Dict[str, Any]]:
    """Fetch weekly economic calendar JSON from FairEconomy with a short in-memory cache."""
    import time
    import urllib.request

    now_ts = time.time()
    if _DAILY_FEED_CACHE["events"] is not None and (now_ts - _DAILY_FEED_CACHE["ts"]) < 900.0:
        return _DAILY_FEED_CACHE["events"]

    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    _DAILY_FEED_CACHE["ts"] = now_ts
                    _DAILY_FEED_CACHE["events"] = data
                    return data
    except Exception as e:
        print(f"ℹ️ Daily economic calendar feed unavailable: {e}")
        # Brief negative cache (120s) on rate-limit/errors to avoid hammering upstream in the same run
        _DAILY_FEED_CACHE["ts"] = now_ts - 780.0
        _DAILY_FEED_CACHE["events"] = []
    return []


def get_daily_macro_events_context(focus: str = "EU", target_date: Optional[Any] = None, max_events: int = 8) -> str:
    """
    Returns a grounded summary of today's scheduled macroeconomic releases (EUR/GBP/USD)
    with Italian local times (Europe/Rome), forecast/previous/actual figures, and today's
    confirmed portfolio earnings so Micro-Topic 2 (📅) and independent auditors rely on real data.
    """
    try:
        from zoneinfo import ZoneInfo
        rome_tz = ZoneInfo("Europe/Rome")
    except Exception:
        try:
            import pytz
            rome_tz = pytz.timezone("Europe/Rome")
        except Exception:
            rome_tz = timezone(timedelta(hours=1))

    now_rome = datetime.now(rome_tz)
    t_date = target_date if target_date is not None else now_rome.date()
    focus_upper = (focus or "EU").upper()

    raw_events = _fetch_raw_calendar_events()
    impact_rank = {"High": 0, "Medium": 1, "Low": 2, "Holiday": 3}

    todays_events = []
    for e in raw_events:
        country = str(e.get("country", "")).upper()
        if country not in ("EUR", "GBP", "USD"):
            continue
        dt_str = e.get("date", "")
        if not dt_str:
            continue
        try:
            dt_obj = datetime.fromisoformat(dt_str)
            if dt_obj.tzinfo is None:
                dt_obj = dt_obj.replace(tzinfo=timezone.utc)
            dt_rome = dt_obj.astimezone(rome_tz)
        except Exception:
            continue
        if dt_rome.date() != t_date:
            continue
        # Skip overnight pre-06:00 CET timestamps (previous US afternoon/evening speeches)
        if dt_rome.hour < 6:
            continue

        impact = str(e.get("impact", "Low"))
        if impact == "Holiday":
            continue
        # Priority scoring: lower is higher priority
        imp_score = impact_rank.get(impact, 3)
        if focus_upper == "EU":
            region_score = 0 if country in ("EUR", "GBP") else (1 if imp_score <= 1 else 2)
        else:
            region_score = 0 if country == "USD" else (1 if imp_score <= 1 else 2)

        tz_abbr = dt_rome.tzname() or "CET"
        timing_status = "GIÀ TRASCORSO" if (target_date is None and dt_rome <= now_rome) else "IN AGENDA"

        todays_events.append({
            "sort_key": (imp_score, region_score, dt_rome),
            "time_str": dt_rome.strftime("%H:%M"),
            "tz_abbr": tz_abbr,
            "timing_status": timing_status,
            "country": country,
            "impact": impact,
            "title": str(e.get("title", "")).strip(),
            "forecast": str(e.get("forecast", "") or "").strip(),
            "previous": str(e.get("previous", "") or "").strip(),
            "actual": str(e.get("actual", "") or "").strip(),
        })

    todays_events.sort(key=lambda x: x["sort_key"])
    selected = sorted(todays_events[:max_events], key=lambda x: x["time_str"])

    lines = []
    for ev in selected:
        details = []
        if ev["actual"]:
            details.append(f"uscito: {ev['actual']}")
        if ev["forecast"]:
            details.append(f"atteso: {ev['forecast']}")
        if ev["previous"]:
            details.append(f"prec: {ev['previous']}")
        det_str = f" ({', '.join(details)})" if details else ""
        lines.append(
            f"• {ev['time_str']} {ev['tz_abbr']} [{ev['timing_status']} | {ev['country']} | {ev['impact']}]: {ev['title']}{det_str}"
        )

    # Also check portfolio earnings today
    earnings_str = "Nessuna trimestrale del portafoglio prevista oggi."
    try:
        import market_calendar
        todays_earnings = market_calendar.get_earnings_for_session(t_date)
        if todays_earnings:
            earnings_str = "Trimestrali portafoglio oggi: " + ", ".join(
                f"{e['name']} ({e['ticker']})" for e in todays_earnings
            )
    except Exception:
        pass

    if not lines and earnings_str == "Nessuna trimestrale del portafoglio prevista oggi.":
        return ""

    header = f"CALENDARIO MACRO ODIERNO ({t_date.strftime('%d/%m/%Y')}, orari italiani CET/CEST):"
    body = "\n".join(lines) if lines else "• Nessun dato macro ad alto impatto schedulato per oggi su EUR/GBP/USD."
    return f"{header}\n{body}\n• {earnings_str}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Public Orchestrator
# ─────────────────────────────────────────────────────────────────────────────
def get_weekly_macro_poll() -> Dict[str, Any]:
    """
    Get the weekly economic calendar poll data using resilient multi-tier cascade:
      1. Gemini Live Search
      2. Direct JSON feed
      3. Dynamic rotating fallback
    """
    print("🗓️ Retrieving Economic Calendar for Monday Poll...")

    # Tier 1: Gemini Live Search
    poll = fetch_macro_calendar_gemini()
    if poll:
        return poll

    # Tier 2: Public JSON Feed
    poll = fetch_macro_calendar_feed()
    if poll:
        return poll

    # Tier 3: Curated Dynamic Fallback
    print("   ℹ️ Using curated rotating macro template fallback.")
    import random
    selected = random.choice(FALLBACK_MACRO_TEMPLATES)
    return _sanitize_macro_poll(selected)


if __name__ == "__main__":
    p = get_weekly_macro_poll()
    print("\n--- GENERATED MONDAY MACRO POLL ---")
    print("Title:", p["title"], f"({len(p['title'])} chars)")
    print("Options:")
    for i, o in enumerate(p["options"]):
        print(f"  [{i+1}] {o} ({len(o)} chars)")
    print("Tickers:", p["tickers"])
    print("\nMessage:\n" + p["message"])
