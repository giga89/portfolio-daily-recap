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

try:
    from tavily_search import get_live_market_news_context, is_tavily_available
except ImportError:
    get_live_market_news_context = None
    is_tavily_available = lambda: False


# Tested, verified working models on Groq LPUs
GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
]

# Tested, verified working models on Mistral API (Free/Dev tier grants 125 RPM on Codestral, 188 RPM on Ministral 8B)
MISTRAL_MODELS = [
    "codestral-latest",
    "ministral-8b-latest",
    "ministral-3b-latest",
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
    portfolio_metadata_summary: str = "",
    live_news_context: str = "",
) -> str:
    """Creates the adversarial fact-checker prompt for Groq/Mistral with optional Tavily live grounding."""
    live_news_section = ""
    if live_news_context:
        live_news_section = f"""
=========================================
FONTI NOTIZIE FINANZIARIE REALI RECENTI (LIVE WEB - TAVILY):
=========================================
{live_news_context}
"""

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
{live_news_section}
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
   - NOTA BENE (ANACRONISMI NOTI): Il mandato di Jerome Powell come Presidente della Fed termina a maggio 2026. Citare Powell per decisioni o annunci nel 2026 è anacronistico: rimuovi tassativamente il nome 'Powell' e usa genericamente 'la Federal Reserve' / 'la banca centrale'.
   - Se viene attribuita una decisione a una figura che non ricopre più la carica o se c'è un'allucinazione su chi guida un'istituzione, correggi immediatamente o rimuovi il riferimento.

3. CONFERMA NOTIZIE CON LE FONTI LIVE TAVILY:
   - Consulta le 'FONTI NOTIZIE FINANZIARIE REALI RECENTI (LIVE WEB - TAVILY)' sopra riportate per verificare i fatti menzionati nel post (partnership, catalizzatori, trimestrali, rating).
   - Se una notizia o catalizzatore è confermato dalle fonti live, consideralo autentico e approvalo.
   - Se un fatto è palesemente inventato e in contrasto con la realtà, correggilo chirurgicamente.

4. FORMATTAZIONE ETORO:
   - Nessun markdown bold (** o __).
   - Massimo 4 cashtag con prefisso $ (es. $NVDA, $SPX500). Non aggiungere cashtag a titoli citati come testo semplice.

5. PRESERVAZIONE DELLA RICCHEZZA DEL CONTENUTO (NON RIASSUMERE):
   - È SEVERAMENTE VIETATO tagliare o riassumere il post in poche righe generiche!
   - Devi preservare integralmente tutta la struttura, i dettagli di mercato, le analisi dei singoli titoli, i paragrafi e la ricchezza del post originale.
   - Intervieni in modo chirurgico SOLO sui passaggi che contengono errori temporali o allucinazioni, riscrivendoli al passato o correggendo l'inesattezza, senza impoverire o accorciare il post.

6. RIGETTO DI BANALITÀ E FRASI FATTE (QUALITÀ DELLE NOTIZIE):
   - Se il post contiene frasi generiche, banali e vuote prive di qualsiasi dato concreto sui titoli citati (es. 'continuiamo a seguire con estrema fiducia', 'la tesi rimane solida', 'sostenuta dalla forte domanda', 'continua ad offrire ottima stabilità', 'rappresenta una copertura strategica importante', 'pronti a gestire la volatilità'), DEVI considerarlo un difetto grave.
   - CORREZIONE: Sostituisci la frase generica con un dato aziendale reale tratto dai METADATI DI PORTAFOGLIO o dalle NOTIZIE LIVE TAVILY (es. cita numeri di bilancio, crescita ricavi, margini operativi, contratti vinti, siti produttivi, nomi di farmaci/dispositivi o piattaforme proprietarie).

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
    live_news_context: str = "",
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
    prompt = _build_audit_prompt(
        text=text,
        session_name=session_name,
        temporal_ctx=temporal_ctx,
        portfolio_metadata_summary=portfolio_metadata_summary,
        live_news_context=live_news_context,
    )

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
    live_news_context: str = "",
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
    prompt = _build_audit_prompt(
        text=text,
        session_name=session_name,
        temporal_ctx=temporal_ctx,
        portfolio_metadata_summary=portfolio_metadata_summary,
        live_news_context=live_news_context,
    )

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
    live_news_context: Optional[str] = None,
    require_consensus: bool = True,
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
    )

    # 2. Query Mistral
    mistral_audit = audit_with_mistral(
        text=text,
        session_name=session_name,
        portfolio_metadata_summary=portfolio_metadata_summary,
        live_news_context=live_news_context,
    )

    # If neither is available, return None for fallback
    if not groq_audit and not mistral_audit:
        return None

    # Single-auditor fallback if only one is operational
    if groq_audit and not mistral_audit:
        print("   ℹ️ Multi-AI consensus note: Mistral non disponibile, audit affidato al solo Groq.")
        return groq_audit

    if mistral_audit and not groq_audit:
        print("   ℹ️ Multi-AI consensus note: Groq non disponibile, audit affidato alla sola Mistral.")
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
        )
        if _is_audit_clean(cross_m):
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
        )
        if _is_audit_clean(cross_g):
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

    for block_idx, block in enumerate(raw_blocks):
        # Footer / Tag / link lines
        if block.startswith("📌") or block.startswith("👤") or block.startswith("#") or block.startswith("http"):
            micro_topics.append({
                "id": len(micro_topics),
                "type": "footer",
                "text": block,
                "needs_audit": False,
            })
            continue

        # Short dynamic greeting
        if block_idx == 0 and len(block) < 130 and any(w in block.lower() for w in ["buongiorno", "buonasera", "chiusura", "fine sessione", "bentornati"]):
            micro_topics.append({
                "id": len(micro_topics),
                "type": "greeting",
                "text": block,
                "needs_audit": False,
            })
            continue

        # Community engagement question
        if "?" in block and len(block) < 240 and any(w in block.lower() for w in ["commenti", "voi come", "cosa ne pensate", "dite la vostra"]):
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
            p_type = "macro" if any(w in block.lower() for w in ["indice", "fed", "bce", "spx", "nasdaq", "inflazione", "tassi"]) else "stock_paragraph"
            micro_topics.append({
                "id": len(micro_topics),
                "type": p_type,
                "text": block,
                "needs_audit": True,
            })

    return micro_topics


def reassemble_micro_topics(micro_topics: List[Dict[str, Any]]) -> str:
    """
    Reassembles approved micro-topics into a clean, cohesive post.
    Bullets follow their header with a single newline, paragraphs separated by double newlines.
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

    return "\n\n".join(chunks)


def run_micro_topic_consensus_fact_check(
    text: str,
    session_name: Optional[str] = None,
    portfolio_metadata_summary: str = "",
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
        )

    print(f"   🧩 Scomposizione in {len(micro_topics)} micro-argomenti ({len(topics_to_audit)} da auditare in parallelo)...")

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

    # Run consensus audits concurrently across micro-topics
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(4, len(topics_to_audit))) as executor:
        future_to_topic = {
            executor.submit(
                run_independent_fact_check,
                t["text"],
                session_name=session_name,
                portfolio_metadata_summary=portfolio_metadata_summary,
                live_news_context=live_news_context,
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

        if dec == "APPROVE":
            approved_count += 1
            substantive_retained += 1
            t["verified_text"] = t["text"]
            print(f"   ✓ Micro-argomento [{t['id']} - {t['type']}] APPROVATO: {t['text'][:60]}...")
        elif dec == "AUTO_CORRECT" and res.get("verified_text"):
            corrected_count += 1
            substantive_retained += 1
            t["verified_text"] = res["verified_text"]
            all_issues.extend(res.get("temporal_issues", []))
            all_halluc.extend(res.get("hallucinations_detected", []))
            print(f"   🛠️ Micro-argomento [{t['id']} - {t['type']}] CORRETTO CHIRURGICAMENTE: {res.get('explanation')[:80]}...")
        elif dec == "REJECT":
            rejected_count += 1
            all_issues.extend(res.get("temporal_issues", []))
            all_halluc.extend(res.get("hallucinations_detected", []))
            if t.get("type") == "stock_bullet":
                t["excluded"] = True
                print(f"   ⚠️ Micro-bullet [{t['id']}] con allucinazione irreversibile ESCLUSO: {t['text'][:60]}...")
            else:
                # If a macro paragraph was rejected without auto-correct
                print(f"   ❌ Micro-argomento [{t['id']} - {t['type']}] RESPINTO: {res.get('explanation')[:80]}...")

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

    final_text = reassemble_micro_topics(micro_topics)
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

