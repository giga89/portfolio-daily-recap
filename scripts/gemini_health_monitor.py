#!/usr/bin/env python3
"""
AI API Health, Quota & Multi-Model Monitor.
Tests all active Gemini models, Groq Fact-Checkers, and Mistral models.
Checks quota availability and dispatches Telegram alerts when quota limits (429)
or service outages occur.
"""

import html
import os
import sys
import time
from datetime import datetime

# Add src/ to path for internal modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Load local .env if available
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from ai_model_cascade import build_http_options, build_thinking_config
except ImportError:
    def build_http_options(types_module, timeout_seconds=45.0, api_version="v1beta"):
        return None
    def build_thinking_config(types_module, model_name, budget=None, fast_mode=False):
        return None

try:
    import tavily_search
    TAVILY_MODULE_AVAILABLE = True
except ImportError:
    tavily_search = None
    TAVILY_MODULE_AVAILABLE = False

try:
    import telegram_sender
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


import json
import urllib.request
import urllib.error

ACTIVE_MODELS = [
    ("gemini-3.6-flash", "3.6 Flash - Primary Flagship (Free Tier)"),
    ("gemini-3.5-flash", "3.5 Flash - Fast General & Reviewer (Free Tier)"),
    ("gemini-4-hydrogen", "4 Hydrogen - Deep Quality Cascade (Free Tier)"),
    ("gemini-3.5-flash-lite", "3.5 Flash-Lite - Fast Comment & Support (Free Tier)"),
    ("gemini-3.1-flash-lite", "3.1 Flash-Lite - High-Quota Reserve (Free Tier)"),
    ("gemini-2.5-flash", "2.5 Flash - Legacy Fallback v1beta (Free Tier)"),
]

ACTIVE_GROQ_MODELS = [
    ("qwen/qwen3.8-27b", "Qwen 3.8 27B - Fact-Checking Principale LPUs (8K TPM / 1K RPD)"),
    ("openai/gpt-oss-120b", "GPT-OSS 120B - Deep Reasoning Fallback (8K TPM / 1K RPD)"),
    ("openai/gpt-oss-20b", "GPT-OSS 20B - Fast LPU Reserve (8K TPM / 1K RPD)"),
]

ACTIVE_MISTRAL_MODELS = [
    ("codestral-latest", "Codestral - Primary Auditor (2 RPM / 40K TPM Free Tier)"),
    ("ministral-14b-latest", "Ministral 14B - Secondary Auditor (2 RPM / 40K TPM Free Tier)"),
    ("ministral-8b-latest", "Ministral 8B - Tertiary Auditor (2 RPM / 40K TPM Free Tier)"),
    ("ministral-3b-latest", "Ministral 3B - Fast Reserve (2 RPM / 40K TPM Free Tier)"),
]


def test_model(api_key: str, model_name: str, client=None) -> dict:
    """Test a single Gemini model with a minimal request (SDK or REST)."""
    t0 = time.time()

    # 1. Try SDK if client provided
    if client is not None:
        try:
            cfg_kwargs = {
                "max_output_tokens": 512,
                "temperature": 0.0,
            }
            thinking_cfg = build_thinking_config(types, model_name, fast_mode=True)
            if thinking_cfg is not None:
                cfg_kwargs["thinking_config"] = thinking_cfg

            response = client.models.generate_content(
                model=model_name,
                contents='Reply with only the word "OK"',
                config=types.GenerateContentConfig(**cfg_kwargs),
            )
            latency = round((time.time() - t0) * 1000)
            if response and getattr(response, "text", None):
                return {"status": "ok", "latency": latency, "detail": response.text.strip()}
            return {"status": "empty", "latency": latency, "detail": "Empty response"}
        except Exception as exc:
            latency = round((time.time() - t0) * 1000)
            err_str = str(exc).lower()
            if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                return {"status": "quota_exceeded", "latency": latency, "detail": "429 Quota Exceeded / Rate Limited"}
            elif "503" in err_str or "unavailable" in err_str or "overloaded" in err_str:
                return {"status": "unavailable", "latency": latency, "detail": "503 Service Temporarily Unavailable"}
            elif "404" in err_str or "not_found" in err_str:
                return {"status": "not_found", "latency": latency, "detail": "404 Model Not Found / Retired"}
            return {"status": "error", "latency": latency, "detail": str(exc)[:80]}

    # 2. Universal REST fallback
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": "Reply with only the word OK"}]}],
        "generationConfig": {"maxOutputTokens": 512, "temperature": 0.0}
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            latency = round((time.time() - t0) * 1000)
            ans = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            return {"status": "ok" if ans else "empty", "latency": latency, "detail": ans or "Empty response"}
    except urllib.error.HTTPError as he:
        latency = round((time.time() - t0) * 1000)
        err_body = he.read().decode()
        if he.code == 429:
            return {"status": "quota_exceeded", "latency": latency, "detail": "429 Quota Exceeded / Rate Limited"}
        elif he.code == 503:
            return {"status": "unavailable", "latency": latency, "detail": "503 Service Overloaded"}
        elif he.code == 404:
            return {"status": "not_found", "latency": latency, "detail": "404 Model Not Found"}
        return {"status": "error", "latency": latency, "detail": f"HTTP {he.code}: {err_body[:60]}"}
    except Exception as exc:
        latency = round((time.time() - t0) * 1000)
        return {"status": "error", "latency": latency, "detail": str(exc)[:80]}


def test_groq_model(api_key: str, model_name: str) -> dict:
    """Test a Groq model using OpenAI-compatible REST API."""
    t0 = time.time()
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Portfolio-Health-Check/1.0",
    }
    body = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Reply OK"}],
        "max_tokens": 300,
        "temperature": 0.0,
    }
    if "gpt-oss" in model_name:
        body["reasoning_effort"] = "low"

    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            latency = round((time.time() - t0) * 1000)
            ans = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            if ans:
                return {"status": "ok", "latency": latency, "detail": ans[:60]}
            return {"status": "empty", "latency": latency, "detail": "Empty response"}
    except urllib.error.HTTPError as he:
        latency = round((time.time() - t0) * 1000)
        err_body = he.read().decode()
        if he.code == 429:
            return {"status": "quota_exceeded", "latency": latency, "detail": "429 Quota Exceeded / Rate Limited"}
        elif he.code == 404:
            return {"status": "not_found", "latency": latency, "detail": "404 Model Not Found"}
        return {"status": "error", "latency": latency, "detail": f"HTTP {he.code}: {err_body[:60]}"}
    except Exception as exc:
        latency = round((time.time() - t0) * 1000)
        return {"status": "error", "latency": latency, "detail": str(exc)[:80]}


def test_mistral_model(api_key: str, model_name: str) -> dict:
    """Test a Mistral model using REST API."""
    t0 = time.time()
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Portfolio-Health-Check/1.0",
    }
    payload = json.dumps({
        "model": model_name,
        "messages": [{"role": "user", "content": "Reply OK"}],
        "max_tokens": 64,
        "temperature": 0.0,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            latency = round((time.time() - t0) * 1000)
            ans = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            if ans:
                return {"status": "ok", "latency": latency, "detail": ans[:60]}
            return {"status": "empty", "latency": latency, "detail": "Empty response"}
    except urllib.error.HTTPError as he:
        latency = round((time.time() - t0) * 1000)
        err_body = he.read().decode()
        if he.code == 429:
            limit_rpm = str(he.headers.get("x-ratelimit-limit-req-minute", "")).strip() if he.headers else ""
            if limit_rpm == "0":
                return {"status": "unverified", "latency": latency, "detail": "429 0 RPM (Non abilitato su account)"}
            return {"status": "quota_exceeded", "latency": latency, "detail": "429 Rate Limited (2 RPM Free Tier)"}
        return {"status": "error", "latency": latency, "detail": f"HTTP {he.code}: {err_body[:60]}"}
    except Exception as exc:
        latency = round((time.time() - t0) * 1000)
        return {"status": "error", "latency": latency, "detail": str(exc)[:80]}


def test_tavily_provider(api_key: str) -> dict:
    """Test Tavily Live Search API (legacy single-key probe)."""
    t0 = time.time()
    url = "https://api.tavily.com/search"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Portfolio-Health-Check/1.0",
    }
    payload = json.dumps({
        "api_key": api_key,
        "query": "Wall Street stock market today",
        "topic": "news",
        "days": 1,
        "max_results": 1,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            latency = round((time.time() - t0) * 1000)
            cnt = len(data.get("results", []))
            return {"status": "ok", "latency": latency, "detail": f"{cnt} notizie verificate trovate"}
    except urllib.error.HTTPError as he:
        latency = round((time.time() - t0) * 1000)
        if he.code in (429, 432):
            return {"status": "quota_exceeded", "latency": latency, "detail": f"HTTP {he.code} Crediti esauriti"}
        return {"status": "error", "latency": latency, "detail": f"HTTP {he.code}"}
    except Exception as exc:
        latency = round((time.time() - t0) * 1000)
        return {"status": "error", "latency": latency, "detail": str(exc)[:80]}


def check_all_tavily_accounts() -> list:
    """Inspect all configured Tavily accounts via GET /usage (0 credits) with REST fallback."""
    if TAVILY_MODULE_AVAILABLE and tavily_search is not None:
        accounts = tavily_search.inspect_tavily_accounts_usage(timeout=10)
        if accounts:
            return accounts

    # Fallback if tavily_search module wasn't imported
    accounts = []
    seen = set()
    candidates = []
    for var in ("TAVILY_API_KEY", "TAVILY_API_KEY_SECONDARY", "TAVILY_API_KEY_FALLBACK", "TAVILY_API_KEY_2", "TAVILY_API_KEY_BACKUP"):
        val = (os.environ.get(var) or "").strip()
        if val and val not in seen:
            seen.add(val)
            candidates.append((var, val))
    for idx, (var, val) in enumerate(candidates, start=1):
        res = test_tavily_provider(val)
        masked = (val[:8] + "..." + val[-4:]) if len(val) > 12 else "***"
        accounts.append({
            "index": idx,
            "env_var": var,
            "masked_key": masked,
            "status": res.get("status", "error"),
            "latency_ms": res.get("latency", 0),
            "detail": res.get("detail", ""),
        })
    return accounts


def format_telegram_health_report(
    results: dict,
    groq_results: dict,
    mistral_results: dict,
    tavily_accounts: list,
    is_alert: bool,
    ok_count: int,
    flash_quota_exceeded_count: int,
) -> str:
    """Render HTML Telegram health alert / report covering Gemini, Groq, Mistral, and ALL Tavily accounts."""
    header_emoji = "🚨" if is_alert else "ℹ️"
    title = "ALLERTA STATO AI API" if is_alert else "REPORT STATO AI API & FACT-CHECKERS"

    lines = [
        f"{header_emoji} <b>{title}</b> {header_emoji}",
        f"📅 <i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>\n",
        "<b>Modelli Generazione Gemini:</b>"
    ]

    for model_name, _descr in ACTIVE_MODELS:
        res = results.get(model_name, {"status": "unknown", "detail": "N/D", "latency": 0})
        detail = html.escape(str(res.get("detail", "N/D")))
        if res["status"] == "ok":
            lines.append(f"• <b>{html.escape(model_name)}</b>: ✅ Attivo ({res['latency']}ms)")
        elif res["status"] == "quota_exceeded":
            if "pro" in model_name.lower():
                lines.append(f"• <b>{html.escape(model_name)}</b>: ℹ️ Non disponibile su Free Tier (Richiede Pay-as-you-go)")
            else:
                lines.append(f"• <b>{html.escape(model_name)}</b>: 🔴 <b>Quota Esaurita (429)</b>")
        elif res["status"] == "unavailable":
            lines.append(f"• <b>{html.escape(model_name)}</b>: ⚠️ Temporaneamente non disponibile (503)")
        else:
            lines.append(f"• <b>{html.escape(model_name)}</b>: ⚠️ Errore ({detail})")

    lines.append("\n<b>Auditor Indipendenti Fact-Checking:</b>")
    if groq_results:
        for m, _descr in ACTIVE_GROQ_MODELS:
            r = groq_results.get(m, {})
            st = r.get("status")
            detail = html.escape(str(r.get("detail", "N/D")))
            if st == "ok":
                lines.append(f"• <b>Groq ({html.escape(m)})</b>: ✅ Attivo ({r['latency']}ms)")
            elif st == "quota_exceeded":
                lines.append(f"• <b>Groq ({html.escape(m)})</b>: 🔴 {detail}")
            else:
                lines.append(f"• <b>Groq ({html.escape(m)})</b>: ⚠️ {detail}")
    else:
        lines.append("• <b>Groq</b>: ⚠️ Non configurato")

    if mistral_results:
        for m, _descr in ACTIVE_MISTRAL_MODELS:
            r = mistral_results.get(m, {})
            st = r.get("status")
            detail = html.escape(str(r.get("detail", "N/D")))
            if st == "ok":
                lines.append(f"• <b>Mistral ({html.escape(m)})</b>: ✅ Attivo ({r['latency']}ms)")
            elif st == "unverified":
                lines.append(f"• <b>Mistral ({html.escape(m)})</b>: ℹ️ 0 RPM ({detail})")
            elif st == "quota_exceeded":
                lines.append(f"• <b>Mistral ({html.escape(m)})</b>: 🟡 {detail}")
            else:
                lines.append(f"• <b>Mistral ({html.escape(m)})</b>: ⚠️ {detail}")
    else:
        lines.append("• <b>Mistral</b>: ℹ️ Non configurato")

    tavily_active_count = sum(1 for a in tavily_accounts if a.get("status") == "ok")
    tavily_exhausted_count = sum(1 for a in tavily_accounts if a.get("status") == "quota_exceeded")

    lines.append("\n<b>Fonti Live Web & Fact-Checking (Tavily):</b>")
    if tavily_accounts:
        for acct in tavily_accounts:
            idx = acct.get("index", 1)
            env_var = html.escape(str(acct.get("env_var", f"TAVILY_API_KEY_{idx}")))
            masked = html.escape(str(acct.get("masked_key", "***")))
            detail = html.escape(str(acct.get("detail", "")))
            lat = acct.get("latency_ms", 0)
            st = acct.get("status")
            acct_label = f"Tavily Account {idx} (<code>{env_var}</code> {masked})"
            if st == "ok":
                lines.append(f"• <b>{acct_label}</b>: ✅ Attivo — {detail} ({lat}ms)")
            elif st == "quota_exceeded":
                lines.append(f"• <b>{acct_label}</b>: 🔴 <b>Crediti Esauriti</b> — {detail}")
            else:
                lines.append(f"• <b>{acct_label}</b>: ⚠️ Errore — {detail}")

        if tavily_exhausted_count > 0 and tavily_active_count > 0:
            lines.append(
                f"  ↳ <i>Failover automatico attivo ({tavily_active_count}/{len(tavily_accounts)} account operativi).</i>"
            )
    else:
        lines.append("• <b>Tavily Live Search</b>: ℹ️ Nessuna API key configurata")

    if results and ok_count == 0:
        lines.append("\n❌ <b>TUTTI I MODELLI GEMINI BLOCCATI!</b> Generazione post a rischio.")
    elif tavily_accounts and tavily_active_count == 0:
        lines.append("\n❌ <b>TUTTI GLI ACCOUNT TAVILY ESAURITI/BLOCCATI!</b> Live web search non disponibile.")
    elif flash_quota_exceeded_count > 0 or (tavily_exhausted_count > 0 and tavily_active_count > 0):
        lines.append(
            f"\n⚠️ <i>Nota: cascade operativo — Gemini {ok_count}/{len(ACTIVE_MODELS)}, "
            f"Tavily {tavily_active_count}/{len(tavily_accounts)} account attivi.</i>"
        )
    else:
        tavily_summary = f"{tavily_active_count}/{len(tavily_accounts)} account" if tavily_accounts else "N/D"
        lines.append(
            f"\n✅ <i>Generatore (Gemini), Fact-Checkers (Groq+Mistral) e Live Search (Tavily {tavily_summary}) operativi.</i>"
        )

    lines.append("\n🔗 <a href='https://tavily.com'>Tavily</a> | <a href='https://console.groq.com'>Groq</a> | <a href='https://aistudio.google.com'>Google AI Studio</a>")
    return "\n".join(lines)


def run_health_check(notify_always: bool = False) -> int:
    """Run health check across all active models (Gemini + Groq + Mistral + all Tavily accounts)."""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    mistral_key = os.environ.get("MISTRAL_API_KEY")

    print("=" * 60)
    print(f"🤖 COMPREHENSIVE AI HEALTH CHECK — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Gemini Models
    results = {}
    ok_count = 0

    print("\n--- 1. Gemini Generation Models ---")
    if gemini_key:
        client = None
        if GENAI_AVAILABLE:
            try:
                http_opts = build_http_options(types, timeout_seconds=45.0)
                client_kwargs = {"api_key": gemini_key}
                if http_opts is not None:
                    client_kwargs["http_options"] = http_opts
                client = genai.Client(**client_kwargs)
            except Exception:
                client = None
        for idx, (model_name, descr) in enumerate(ACTIVE_MODELS):
            print(f"🔍 Testing {model_name} ({descr})...")
            res = test_model(gemini_key, model_name, client=client)
            results[model_name] = res

            status_emoji = "✅" if res["status"] == "ok" else "🔴" if res["status"] == "quota_exceeded" else "⚠️"
            print(f"   {status_emoji} Status: {res['status']} ({res['latency']}ms) — {res['detail']}")

            if res["status"] == "ok":
                ok_count += 1

            if idx < len(ACTIVE_MODELS) - 1:
                time.sleep(1.5)
    else:
        print("   ℹ️ GEMINI_API_KEY non configurata localmente (attiva nei GitHub Actions Secrets).")

    # 2. Groq Independent Fact-Checker
    groq_results = {}
    print("\n--- 2. Groq Independent Fact-Checkers (LPUs) ---")
    if groq_key:
        for idx, (model_name, descr) in enumerate(ACTIVE_GROQ_MODELS):
            print(f"🔍 Testing Groq: {model_name} ({descr})...")
            res = test_groq_model(groq_key, model_name)
            groq_results[model_name] = res
            status_emoji = "✅" if res["status"] == "ok" else "🔴" if res["status"] == "quota_exceeded" else "⚠️"
            print(f"   {status_emoji} Status: {res['status']} ({res['latency']}ms) — {res['detail']}")
            if idx < len(ACTIVE_GROQ_MODELS) - 1:
                time.sleep(0.5)
    else:
        print("   ⚠️ GROQ_API_KEY non configurata.")

    # 3. Mistral Independent Fact-Checker
    mistral_results = {}
    print("\n--- 3. Mistral Independent Fact-Checkers ---")
    if mistral_key:
        for idx, (model_name, descr) in enumerate(ACTIVE_MISTRAL_MODELS):
            print(f"🔍 Testing Mistral: {model_name} ({descr})...")
            res = test_mistral_model(mistral_key, model_name)
            mistral_results[model_name] = res
            status_emoji = "✅" if res["status"] == "ok" else "ℹ️" if res["status"] == "unverified" else "⚠️"
            print(f"   {status_emoji} Status: {res['status']} ({res['latency']}ms) — {res['detail']}")
            # Free Tier enforces 1 RPS across Mistral endpoints
            if idx < len(ACTIVE_MISTRAL_MODELS) - 1:
                time.sleep(1.3)
    else:
        print("   ⚠️ MISTRAL_API_KEY non configurata.")

    # 4. All Configured Tavily Accounts (0-credit /usage check + failover count)
    print("\n--- 4. Tavily Live Search & Ground Truth Accounts ---")
    tavily_accounts = check_all_tavily_accounts()
    if tavily_accounts:
        for acct in tavily_accounts:
            st = acct.get("status")
            status_emoji = "✅" if st == "ok" else "🔴" if st == "quota_exceeded" else "⚠️"
            print(
                f"   {status_emoji} Account {acct['index']} ({acct['env_var']} {acct['masked_key']}): "
                f"{st} ({acct['latency_ms']}ms) — {acct['detail']}"
            )
    else:
        print("   ⚠️ Nessuna API key Tavily configurata.")

    print("\n" + "=" * 60)
    groq_ok = sum(1 for r in groq_results.values() if r.get("status") == "ok")
    mistral_ok = sum(1 for r in mistral_results.values() if r.get("status") == "ok")
    tavily_ok = sum(1 for a in tavily_accounts if a.get("status") == "ok")
    print(
        f"📊 Summary: Gemini {ok_count}/{len(ACTIVE_MODELS)} | Groq {groq_ok}/{len(ACTIVE_GROQ_MODELS)} | "
        f"Mistral {mistral_ok}/{len(ACTIVE_MISTRAL_MODELS)} | Tavily {tavily_ok}/{len(tavily_accounts)} account attivi"
    )
    print("=" * 60)

    flash_quota_exceeded_count = sum(
        1 for m, _ in ACTIVE_MODELS
        if "pro" not in m.lower() and results.get(m, {}).get("status") == "quota_exceeded"
    )

    is_alert = (
        (flash_quota_exceeded_count > 0)
        or (bool(gemini_key) and ok_count == 0)
        or (bool(tavily_accounts) and tavily_ok == 0)
        or (bool(groq_key) and groq_ok == 0 and bool(mistral_key) and mistral_ok == 0)
    )
    should_alert = is_alert or notify_always

    if should_alert:
        print("📡 Preparing Telegram notification...")
        msg = format_telegram_health_report(
            results=results,
            groq_results=groq_results,
            mistral_results=mistral_results,
            tavily_accounts=tavily_accounts,
            is_alert=is_alert,
            ok_count=ok_count,
            flash_quota_exceeded_count=flash_quota_exceeded_count,
        )
        print("\n--- Telegram Message Preview ---\n" + msg + "\n--------------------------------\n")
        if TELEGRAM_AVAILABLE:
            sent = telegram_sender.send_telegram_message(msg)
            if sent:
                print("✅ Telegram notification sent successfully!")
            else:
                print("⚠️ Failed to send Telegram notification")
        else:
            print("⚠️ Telegram sender module not available, skipped sending message")

    return 0 if (ok_count > 0 or (not gemini_key and (groq_ok > 0 or mistral_ok > 0 or tavily_ok > 0))) else 1


if __name__ == "__main__":
    notify = "--notify-always" in sys.argv or os.environ.get("NOTIFY_ALWAYS", "").lower() == "true"
    sys.exit(run_health_check(notify_always=notify))
