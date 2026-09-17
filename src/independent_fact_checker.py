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


# Tested, verified working models on Groq LPUs
GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
]

MISTRAL_MODELS = [
    "mistral-small-latest",
]

# Circuit breaker: avoids wasting time with HTTP calls if Mistral account has 0 RPM quota
_MISTRAL_AVAILABLE: Optional[bool] = None


def get_current_temporal_context(session_name: Optional[str] = None) -> Dict[str, str]:
    """
    Builds rich temporal anchors for the exact current moment.
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

    return {
        "formatted_date": formatted_date,
        "iso_date": now_rome.strftime("%Y-%m-%d"),
        "rome_time": now_rome.strftime("%H:%M CET/CEST"),
        "ny_time": now_ny.strftime("%H:%M ET"),
        "market_state": market_state,
        "year": str(now_rome.year),
    }


def _build_audit_prompt(
    text: str,
    session_name: Optional[str],
    temporal_ctx: Dict[str, str],
    portfolio_metadata_summary: str = ""
) -> str:
    """Creates the adversarial fact-checker prompt for Groq/Mistral."""
    return f"""Sei un Lead Financial Fact-Checker & Senior Compliance Auditor per un account pubblico di investimenti su eToro.
Il tuo obiettivo è effettuare un AUDIT INDIPENDENTE, CRITICO E SPIETATO sul seguente post prima della pubblicazione.

=========================================
INFORMAZIONI TEMPORALI CERTE (GROUND TRUTH):
=========================================
• DATA CORRENTE: {temporal_ctx.get('formatted_date')} (Anno: {temporal_ctx.get('year')})
• ORA LOCALE ITALIANA: {temporal_ctx.get('rome_time')}
• ORA LOCALE WALL STREET: {temporal_ctx.get('ny_time')}
• STATO DELLA SESSIONE: {temporal_ctx.get('market_state')}

=========================================
METADATI DI PORTAFOGLIO:
=========================================
{portfolio_metadata_summary or "Nessun asset specifico indicato."}

=========================================
TESTO DEL POST DA AUDITARE:
=========================================
{text}

=========================================
REGOLE DI AUDIT INDIPENDENTE (TASSATIVE):
=========================================
1. COERENZA TEMPORALE (CRITICA):
   - Se la sessione è serale o di chiusura (es. US_CLOSE), la seduta di borsa odierna è CONCLUSA.
   - Tutti gli eventi della giornata (es. riunioni o decisioni della Federal Reserve, tassi, conferenze stampa, dati inflazione o occupazione) sono GIÀ AVVENUTI.
   - Se il post parla di un evento di oggi usando verbi al FUTURO (es. "oggi deciderà", "oggi prenderà una decisione", "in attesa dell'annuncio di stasera", "si attende la decisione"), questo è un GRAVISSIMO PARADOSSO TEMPORALE.
   - CORREZIONE: Devi convertire il testo al PASSATO (es. "la Fed ha annunciato", "la decisione sui tassi è arrivata oggi") OPPURE, se l'esito reale non è menzionato con certezza, rimuovere l'affermazione speculativa.

2. VERIFICA CARICHE E FIGURE ISTITUZIONALI:
   - Verifica che le figure istituzionali menzionate (banchieri centrali, ministri, CEO) siano coerenti e non anacronistiche.
   - Se viene attribuita una decisione a una figura che non ricopre più la carica o se c'è un'allucinazione su chi guida un'istituzione, correggi immediatamente o rimuovi il riferimento.

3. DIVIETO ASSOLUTO DI INVENTARE NOTIZIE:
   - Non permettere che il post spacci rumor o allucinazioni per fatti certi. Se un fatto sembra generato per errore, bonificalo.

4. FORMATTAZIONE ETORO:
   - Nessun markdown bold (** o __).
   - Massimo 4 cashtag con prefisso $ (es. $NVDA, $SPX500). Non aggiungere cashtag a titoli citati come testo semplice.

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


def audit_with_groq(
    text: str,
    session_name: Optional[str] = None,
    portfolio_metadata_summary: str = "",
    api_key: Optional[str] = None,
    timeout: int = 10,
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

    temporal_ctx = get_current_temporal_context(session_name)
    prompt = _build_audit_prompt(text, session_name, temporal_ctx, portfolio_metadata_summary)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    for model in GROQ_MODELS:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Sei un Financial Fact-Checker severo e meticoloso. Rispondi SEMPRE e SOLO con un oggetto JSON valido."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            t0 = time.time()
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            elapsed = time.time() - t0

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if "decision" in parsed and "verified_text" in parsed:
                    parsed["auditor"] = f"groq:{model}"
                    parsed["latency_sec"] = round(elapsed, 2)
                    print(f"   ⚡ Groq Independent Audit ({model}) succeeded in {elapsed:.2f}s — Decision: {parsed.get('decision')}")
                    return parsed
            elif resp.status_code == 429:
                print(f"   ⚠️ Groq {model} rate limited (429), trying next Groq model...")
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
    api_key: Optional[str] = None,
    timeout: int = 10,
) -> Optional[Dict[str, Any]]:
    """
    Runs fact-checking audit via Mistral API.
    """
    global _MISTRAL_AVAILABLE
    if _MISTRAL_AVAILABLE is False:
        return None

    if not REQUESTS_AVAILABLE:
        return None

    key = api_key or os.environ.get("MISTRAL_API_KEY")
    if not key:
        return None

    temporal_ctx = get_current_temporal_context(session_name)
    prompt = _build_audit_prompt(text, session_name, temporal_ctx, portfolio_metadata_summary)

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    for model in MISTRAL_MODELS:
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
            "response_format": {"type": "json_object"},
        }

        try:
            t0 = time.time()
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            elapsed = time.time() - t0

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if "decision" in parsed and "verified_text" in parsed:
                    _MISTRAL_AVAILABLE = True
                    parsed["auditor"] = f"mistral:{model}"
                    parsed["latency_sec"] = round(elapsed, 2)
                    print(f"   ⚡ Mistral Independent Audit ({model}) succeeded in {elapsed:.2f}s — Decision: {parsed.get('decision')}")
                    return parsed
            elif resp.status_code == 429:
                _MISTRAL_AVAILABLE = False
                print(f"   ℹ️ Mistral {model} non abilitato (0 RPM / 429). Disattivato per questa sessione per azzerare i tempi.")
                return None
            else:
                print(f"   ⚠️ Mistral {model} returned HTTP {resp.status_code}: {resp.text[:120]}")
        except Exception as exc:
            print(f"   ⚠️ Mistral {model} exception: {exc}")
            continue

    return None


def run_independent_fact_check(
    text: str,
    session_name: Optional[str] = None,
    portfolio_metadata_summary: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the independent fact-checking pipeline across external models.
    Tries Groq -> Mistral -> None (allowing caller to fallback to Gemini).
    """
    # 1. Primary: Groq (fastest, high reasoning)
    groq_audit = audit_with_groq(
        text=text,
        session_name=session_name,
        portfolio_metadata_summary=portfolio_metadata_summary,
    )
    if groq_audit:
        return groq_audit

    # 2. Secondary: Mistral
    mistral_audit = audit_with_mistral(
        text=text,
        session_name=session_name,
        portfolio_metadata_summary=portfolio_metadata_summary,
    )
    if mistral_audit:
        return mistral_audit

    return None
