#!/usr/bin/env python3
"""
Gemini API Health & Quota Monitor.
Tests all active Gemini models, checks quota availability,
and dispatches Telegram alerts when quota limits (429) or service outages occur.
"""

import os
import sys
import time
from datetime import datetime

# Add src/ to path for telegram sender
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    import telegram_sender
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


import json
import urllib.request
import urllib.error

ACTIVE_MODELS = [
    ("gemini-3.7-flash", "3.7 Flash - Massima intelligenza (5 RPM / 20 RPD)"),
    ("gemini-3.6-flash", "3.6 Flash - Alta intelligenza (5 RPM / 20 RPD)"),
    ("gemini-3.5-flash", "3.5 Flash - Veloce e contestualizzato (5 RPM / 20 RPD)"),
    ("gemini-2.5-flash", "2.5 Flash - Standard fallback (5 RPM / 20 RPD)"),
]


def test_model(api_key: str, model_name: str, client=None) -> dict:
    """Test a single model with a minimal request (SDK or REST)."""
    t0 = time.time()
    
    # 1. Try SDK if client provided
    if client is not None:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents='Reply with only the word "OK"',
                config=types.GenerateContentConfig(
                    max_output_tokens=5,
                    temperature=0.0
                )
            )
            latency = round((time.time() - t0) * 1000)
            if response and response.text:
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
        "generationConfig": {"maxOutputTokens": 5, "temperature": 0.0}
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            latency = round((time.time() - t0) * 1000)
            ans = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            return {"status": "ok", "latency": latency, "detail": ans}
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


def run_health_check(notify_always: bool = False) -> int:
    """Run health check across all active models and alert if necessary."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY is not set.")
        if TELEGRAM_AVAILABLE and os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
            telegram_sender.send_telegram_message("🚨 <b>GEMINI HEALTH CHECK ERROR</b>: GEMINI_API_KEY non è impostata nei secrets.")
        return 1

    client = None
    if GENAI_AVAILABLE:
        try:
            client = genai.Client(api_key=api_key)
        except Exception:
            client = None

    print("=" * 60)
    print(f"🤖 GEMINI API HEALTH CHECK — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = {}
    quota_exceeded_count = 0
    ok_count = 0

    for model_name, descr in ACTIVE_MODELS:
        print(f"🔍 Testing {model_name} ({descr})...")
        res = test_model(api_key, model_name, client=client)
        results[model_name] = res

        status_emoji = "✅" if res["status"] == "ok" else "🔴" if res["status"] == "quota_exceeded" else "⚠️"
        print(f"   {status_emoji} Status: {res['status']} ({res['latency']}ms) — {res['detail']}")

        if res["status"] == "ok":
            ok_count += 1
        elif res["status"] == "quota_exceeded":
            quota_exceeded_count += 1

        # Throttle between tests to stay below RPM limit
        time.sleep(2.0)

    print("=" * 60)
    print(f"📊 Summary: {ok_count}/{len(ACTIVE_MODELS)} models operational | {quota_exceeded_count} quota exceeded")
    print("=" * 60)

    # Determine if Telegram notification should be sent
    should_alert = (quota_exceeded_count > 0) or (ok_count == 0) or notify_always

    if should_alert:
        print("📡 Preparing Telegram notification...")
        header_emoji = "🚨" if (quota_exceeded_count > 0 or ok_count == 0) else "ℹ️"
        title = "ALLERTA STATO GEMINI API" if (quota_exceeded_count > 0 or ok_count == 0) else "REPORT STATO GEMINI API"

        lines = [
            f"{header_emoji} <b>{title}</b> {header_emoji}",
            f"📅 <i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>\n",
            "<b>Stato Modelli:</b>"
        ]

        for model_name, descr in ACTIVE_MODELS:
            res = results.get(model_name, {"status": "unknown", "detail": "N/D", "latency": 0})
            if res["status"] == "ok":
                lines.append(f"• <b>{model_name}</b>: ✅ Attivo ({res['latency']}ms)")
            elif res["status"] == "quota_exceeded":
                lines.append(f"• <b>{model_name}</b>: 🔴 <b>Quota Esaurita (429)</b>")
            elif res["status"] == "unavailable":
                lines.append(f"• <b>{model_name}</b>: ⚠️ Temporaneamente non disponibile (503)")
            else:
                lines.append(f"• <b>{model_name}</b>: ⚠️ Errore ({res['detail']})")

        if ok_count == 0:
            lines.append("\n❌ <b>TUTTI I MODELLI SONO BLOCCATI!</b> La generazione post e news AI fallirà fino al reset o attivazione fatturazione.")
        elif quota_exceeded_count > 0:
            lines.append(f"\n⚠️ <i>Nota: {ok_count} modelli sono ancora operativi e interverranno tramite fallback automatico.</i>")
        else:
            lines.append("\n✅ <i>Tutti i bucket di quota sono operativi.</i>")

        lines.append("\n🔗 <a href='https://aistudio.google.com/app/apikey'>Google AI Studio Dashboard</a>")

        msg = "\n".join(lines)
        if TELEGRAM_AVAILABLE:
            sent = telegram_sender.send_telegram_message(msg)
            if sent:
                print("✅ Telegram notification sent successfully!")
            else:
                print("⚠️ Failed to send Telegram notification")
        else:
            print("⚠️ Telegram sender module not available, skipped sending message")

    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    notify = "--notify-always" in sys.argv or os.environ.get("NOTIFY_ALWAYS", "").lower() == "true"
    sys.exit(run_health_check(notify_always=notify))
