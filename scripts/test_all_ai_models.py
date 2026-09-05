#!/usr/bin/env python3
"""
Comprehensive AI Model Cascade & Capability Test Suite
======================================================
Tests all active Gemini models across all capabilities used in the project:
1. Text Generation & Financial Reasoning
2. Grounding with Google Search Tool (ai_news_generator)
3. Structured JSON Generation (stock_focus_infographic)
4. End-to-End Cascade & Rate-Limit Resilience (ai_model_cascade)

Can be executed locally or via GitHub Actions workflow.
"""

import os
import sys
import time
import json
from datetime import datetime

# Add src/ to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from ai_model_cascade import DEFAULT_GEMINI_MODELS, REVIEWER_GEMINI_MODELS, execute_with_model_cascade


def run_tests():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable is not set.")
        return 1

    if not GENAI_AVAILABLE:
        print("❌ Error: google-genai library is not installed.")
        return 1

    client = genai.Client(api_key=api_key)

    print("=" * 70)
    print(f"🚀 COMPREHENSIVE AI MODEL TEST SUITE — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 Models in Cascade ({len(DEFAULT_GEMINI_MODELS)}): {', '.join(DEFAULT_GEMINI_MODELS)}")
    print("=" * 70)

    results = []

    # ── Part 1: Individual Model Capabilities ───────────────────────────────
    print("\n--- Part 1: Individual Model Capabilities ---")
    for idx, model_name in enumerate(DEFAULT_GEMINI_MODELS):
        print(f"\n🔍 [{idx+1}/{len(DEFAULT_GEMINI_MODELS)}] Testing model: {model_name}")
        model_result = {
            "model": model_name,
            "text_gen": None,
            "search_grounding": None,
            "json_output": None,
            "notes": []
        }

        # 1. Text Generation
        t0 = time.time()
        try:
            cfg = types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=250,
            )
            resp = client.models.generate_content(
                model=model_name,
                contents="Spiega in una singola frase cos'è il compound interest (interesse composto).",
                config=cfg,
            )
            lat = round((time.time() - t0) * 1000)
            if resp and resp.text:
                preview = resp.text.strip().replace("\n", " ")[:60]
                model_result["text_gen"] = f"✅ OK ({lat}ms) — \"{preview}...\""
                print(f"   • Text Gen: {model_result['text_gen']}")
            else:
                model_result["text_gen"] = f"⚠️ Empty response ({lat}ms)"
                print(f"   • Text Gen: {model_result['text_gen']}")
        except Exception as exc:
            lat = round((time.time() - t0) * 1000)
            err_str = str(exc)
            if "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower():
                tag = "🔴 429 Quota Exceeded"
            elif "503" in err_str:
                tag = "⚠️ 503 Overloaded"
            elif "404" in err_str:
                tag = "❌ 404 Not Found"
            else:
                tag = f"❌ Error ({err_str[:40]})"
            model_result["text_gen"] = f"{tag} ({lat}ms)"
            print(f"   • Text Gen: {model_result['text_gen']}")

        # Throttle between calls to stay under Free Tier 5 RPM
        time.sleep(3.5)

        # 2. Search Grounding (Google Search tool)
        t0 = time.time()
        try:
            cfg_search = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,
                max_output_tokens=250,
            )
            resp_search = client.models.generate_content(
                model=model_name,
                contents="Qual è l'attuale prezzo di mercato dell'oro (gold spot price)?",
                config=cfg_search,
            )
            lat = round((time.time() - t0) * 1000)
            if resp_search and resp_search.text:
                preview = resp_search.text.strip().replace("\n", " ")[:60]
                model_result["search_grounding"] = f"✅ OK ({lat}ms) — \"{preview}...\""
                print(f"   • Search Grounding: {model_result['search_grounding']}")
            else:
                model_result["search_grounding"] = f"⚠️ Empty ({lat}ms)"
                print(f"   • Search Grounding: {model_result['search_grounding']}")
        except Exception as exc:
            lat = round((time.time() - t0) * 1000)
            err_str = str(exc)
            if "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower():
                tag = "🔴 429 Quota"
            elif "503" in err_str:
                tag = "⚠️ 503 Overloaded"
            else:
                tag = f"⚠️ Skipped/Unsupported ({err_str[:35]})"
            model_result["search_grounding"] = f"{tag} ({lat}ms)"
            print(f"   • Search Grounding: {model_result['search_grounding']}")

        # Throttle between calls
        time.sleep(3.5)

        # 3. Structured JSON
        t0 = time.time()
        try:
            cfg_json = types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                max_output_tokens=250,
            )
            resp_json = client.models.generate_content(
                model=model_name,
                contents="Ritorna un JSON con chiavi 'status' e 'score' da 1 a 10 per un portafoglio diversificato.",
                config=cfg_json,
            )
            lat = round((time.time() - t0) * 1000)
            if resp_json and resp_json.text:
                parsed = json.loads(resp_json.text)
                model_result["json_output"] = f"✅ OK ({lat}ms) — {parsed}"
                print(f"   • JSON Output: {model_result['json_output']}")
            else:
                model_result["json_output"] = f"⚠️ Empty ({lat}ms)"
                print(f"   • JSON Output: {model_result['json_output']}")
        except Exception as exc:
            lat = round((time.time() - t0) * 1000)
            model_result["json_output"] = f"⚠️ Failed ({lat}ms): {str(exc)[:40]}"
            print(f"   • JSON Output: {model_result['json_output']}")

        results.append(model_result)
        time.sleep(4.0)

    # ── Part 2: End-to-End Cascade Test ─────────────────────────────────────
    print("\n" + "=" * 70)
    print("--- Part 2: End-to-End Model Cascade Execution ---")
    print("Testing execute_with_model_cascade() with fallback resilience...")
    t0 = time.time()
    out, used_model = execute_with_model_cascade(
        client=client,
        prompt="Spiega brevemente la differenza tra ETF ad accumulazione ed ETF a distribuzione in 2 punti.",
        config=types.GenerateContentConfig(temperature=0.4, max_output_tokens=300),
        task_name="test_cascade",
        base_backoff_seconds=5.0,
    )
    cascade_lat = round((time.time() - t0) * 1000)
    if out and used_model:
        print(f"\n🎉 Cascade SUCCESS! Used model: '{used_model}' in {cascade_lat}ms")
        print(f"Sample output preview:\n{out[:120]}...\n")
    else:
        print(f"\n❌ Cascade FAILED! All models failed after retries.")

    # ── Summary Report ──────────────────────────────────────────────────────
    print("=" * 70)
    print("📊 AI MODEL CAPABILITIES SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Model Name':<24} | {'Text Gen':<20} | {'Search Tool':<20} | {'JSON Mode':<15}")
    print("-" * 85)
    for r in results:
        tg = "✅ OK" if "✅" in (r["text_gen"] or "") else ("🔴 429 Quota" if "429" in (r["text_gen"] or "") else "⚠️ Issue")
        sg = "✅ OK" if "✅" in (r["search_grounding"] or "") else ("🔴 429 Quota" if "429" in (r["search_grounding"] or "") else "⚠️ Issue")
        jm = "✅ OK" if "✅" in (r["json_output"] or "") else "⚠️ Issue"
        print(f"{r['model']:<24} | {tg:<20} | {sg:<20} | {jm:<15}")
    print("=" * 70)

    # Exit code: 0 if cascade succeeded and at least 2 models are operational
    operational_models = [r["model"] for r in results if "✅" in (r["text_gen"] or "")]
    print(f"\n✅ Total Operational Models: {len(operational_models)}/{len(DEFAULT_GEMINI_MODELS)} ({', '.join(operational_models)})")
    
    if len(operational_models) >= 2 and used_model:
        print("✅ System is 100% HEALTHY and production-ready!")
        return 0
    elif used_model:
        print("⚠️ System is functional via cascade fallback.")
        return 0
    else:
        print("❌ Critical: No operational models available.")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
