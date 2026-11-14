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

from ai_model_cascade import (
    DEFAULT_GEMINI_MODELS,
    FAST_GEMINI_MODELS,
    REVIEWER_GEMINI_MODELS,
    build_http_options,
    build_thinking_config,
    execute_with_model_cascade,
)


def run_tests():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable is not set.")
        return 1

    if not GENAI_AVAILABLE:
        print("❌ Error: google-genai library is not installed.")
        return 1

    http_opts = build_http_options(types, timeout_seconds=55.0)
    client = genai.Client(api_key=api_key, http_options=http_opts) if http_opts else genai.Client(api_key=api_key)

    print("=" * 70)
    print(f"🚀 COMPREHENSIVE AI MODEL TEST SUITE — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 Post Cascade ({len(DEFAULT_GEMINI_MODELS)}): {', '.join(DEFAULT_GEMINI_MODELS)}")
    print(f"⚡ Fast Cascade ({len(FAST_GEMINI_MODELS)}): {', '.join(FAST_GEMINI_MODELS)}")
    print(f"🔍 Reviewer Cascade ({len(REVIEWER_GEMINI_MODELS)}): {', '.join(REVIEWER_GEMINI_MODELS)}")
    print("=" * 70)

    results = []

    # ── Part 1: Individual Model Capabilities ───────────────────────────────
    print("\n--- Part 1: Individual Gemini Model Capabilities ---")
    for idx, model_name in enumerate(DEFAULT_GEMINI_MODELS):
        print(f"\n🔍 [{idx+1}/{len(DEFAULT_GEMINI_MODELS)}] Testing model: {model_name}")
        model_result = {
            "model": model_name,
            "text_gen": None,
            "search_grounding": None,
            "json_output": None,
            "notes": []
        }

        # 1. Text Generation (bounded thinking + generous output cap)
        t0 = time.time()
        try:
            cfg_kwargs = {
                "temperature": 0.3,
                "max_output_tokens": 1024,
            }
            think_cfg = build_thinking_config(types, model_name, budget=256)
            if think_cfg is not None:
                cfg_kwargs["thinking_config"] = think_cfg

            resp = client.models.generate_content(
                model=model_name,
                contents="Spiega in una singola frase cos'è il compound interest (interesse composto).",
                config=types.GenerateContentConfig(**cfg_kwargs),
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
                tag = f"❌ Error ({err_str[:60]})"
            model_result["text_gen"] = f"{tag} ({lat}ms)"
            print(f"   • Text Gen: {model_result['text_gen']}")

        time.sleep(2.5)

        # 2. Search Grounding (Google Search tool — optional on Free Tier when Tavily is primary)
        t0 = time.time()
        try:
            cfg_search = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,
                max_output_tokens=1024,
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
                print(f"   • Search Tool: {model_result['search_grounding']}")
            else:
                model_result["search_grounding"] = f"⚠️ Empty ({lat}ms)"
                print(f"   • Search Tool: {model_result['search_grounding']}")
        except Exception as exc:
            lat = round((time.time() - t0) * 1000)
            err_str = str(exc)
            if "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower():
                tag = "ℹ️ 429 Free-Tier (Tavily primary)"
            elif "503" in err_str:
                tag = "⚠️ 503 Overloaded"
            else:
                tag = f"⚠️ Unsupported ({err_str[:35]})"
            model_result["search_grounding"] = f"{tag} ({lat}ms)"
            print(f"   • Search Tool: {model_result['search_grounding']}")

        time.sleep(2.5)

        # 3. Structured JSON
        t0 = time.time()
        try:
            json_kwargs = {
                "temperature": 0.1,
                "response_mime_type": "application/json",
                "max_output_tokens": 1024,
            }
            think_cfg_json = build_thinking_config(types, model_name, budget=256)
            if think_cfg_json is not None:
                json_kwargs["thinking_config"] = think_cfg_json

            resp_json = client.models.generate_content(
                model=model_name,
                contents="Ritorna un JSON con chiavi 'status' e 'score' da 1 a 10 per un portafoglio diversificato.",
                config=types.GenerateContentConfig(**json_kwargs),
            )
            lat = round((time.time() - t0) * 1000)
            if resp_json and resp_json.text:
                raw_json = resp_json.text.strip()
                if raw_json.startswith("```"):
                    raw_json = raw_json.split("```")[1].lstrip("json").strip()
                parsed = json.loads(raw_json)
                model_result["json_output"] = f"✅ OK ({lat}ms) — {parsed}"
                print(f"   • JSON Output: {model_result['json_output']}")
            else:
                model_result["json_output"] = f"⚠️ Empty ({lat}ms)"
                print(f"   • JSON Output: {model_result['json_output']}")
        except Exception as exc:
            lat = round((time.time() - t0) * 1000)
            model_result["json_output"] = f"⚠️ Failed ({lat}ms): {str(exc)[:50]}"
            print(f"   • JSON Output: {model_result['json_output']}")

        results.append(model_result)
        time.sleep(2.5)

    # ── Part 2: End-to-End Cascade Tiers (Post / Fast Comment / Reviewer) ──
    print("\n" + "=" * 70)
    print("--- Part 2: End-to-End Model Cascade Execution (All 3 Tiers) ---")

    tier_checks = [
        ("post_cascade", DEFAULT_GEMINI_MODELS, "Spiega brevemente la differenza tra ETF ad accumulazione ed ETF a distribuzione in 2 punti.", False),
        ("fast_comment_cascade", FAST_GEMINI_MODELS, "Rispondi in italiano in 2 frasi cordiali a chi chiede come diversificare un portafoglio azionario.", True),
        ("reviewer_cascade", REVIEWER_GEMINI_MODELS, "Verifica se questa frase ha errori logici: 'L'interesse composto fa crescere i rendimenti nel tempo.' Rispondi OK.", True),
    ]
    tier_results = {}
    for t_name, t_models, t_prompt, t_fast in tier_checks:
        t0 = time.time()
        first_model = t_models[0]
        cfg_t = {
            "temperature": 0.3,
            "max_output_tokens": 1500,
        }
        think_t = build_thinking_config(types, first_model, fast_mode=t_fast)
        if think_t is not None:
            cfg_t["thinking_config"] = think_t
        out, used_model = execute_with_model_cascade(
            client=client,
            prompt=t_prompt,
            config=types.GenerateContentConfig(**cfg_t),
            preferred_models=t_models,
            task_name=t_name,
            base_backoff_seconds=4.0,
        )
        cascade_lat = round((time.time() - t0) * 1000)
        tier_results[t_name] = (out, used_model, cascade_lat)
        if out and used_model:
            print(f"🎉 {t_name} SUCCESS via '{used_model}' in {cascade_lat}ms: {out.strip()[:90]}...")
        else:
            print(f"❌ {t_name} FAILED after full cascade ({cascade_lat}ms)!")

    # ── Part 3: External Fact-Checkers & Multi-Account Tavily Search ───────
    print("\n--- Part 3: External Fact-Checkers & Live Search Grounding ---")

    # Groq (all configured models + audit_with_groq)
    groq_key = os.environ.get("GROQ_API_KEY")
    groq_status = "⚠️ Not configured"
    if groq_key:
        try:
            import requests as _req
            from independent_fact_checker import GROQ_MODELS, audit_with_groq
            groq_ok_models = []
            for gm in GROQ_MODELS:
                t0 = time.time()
                payload = {
                    "model": gm,
                    "messages": [{"role": "user", "content": "Rispondi JSON {\"status\": \"ok\"}"}],
                    "temperature": 0.0,
                    "max_tokens": 300,
                    "response_format": {"type": "json_object"},
                }
                if "gpt-oss" in gm:
                    payload["reasoning_effort"] = "low"
                r = _req.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=15,
                )
                lat = round((time.time() - t0) * 1000)
                if r.status_code == 200:
                    groq_ok_models.append(f"{gm} ({lat}ms)")
                else:
                    print(f"   ⚠️ Groq model {gm} -> HTTP {r.status_code}")
                time.sleep(0.5)
            g_res = audit_with_groq("Il mercato USA ha chiuso regolarmente oggi.", session_name="US_CLOSE")
            if g_res and "decision" in g_res:
                groq_status = f"✅ OK ({g_res.get('auditor')}, {g_res.get('latency_sec', 0)}s -> {g_res.get('decision')}); Attivi: {', '.join(groq_ok_models)}"
            else:
                groq_status = f"⚠️ audit_with_groq failed (probe OK: {groq_ok_models})"
        except Exception as e:
            groq_status = f"❌ Error: {e}"
    print(f"🔍 Groq LPU Auditor: {groq_status}")

    # Mistral (all configured models paced cleanly + audit_with_mistral)
    mistral_key = os.environ.get("MISTRAL_API_KEY")
    mistral_status = "⚠️ Not configured"
    if mistral_key:
        try:
            import requests as _req
            from independent_fact_checker import MISTRAL_MODELS, audit_with_mistral
            mistral_ok_models = []
            for idx_m, mm in enumerate(MISTRAL_MODELS):
                t0 = time.time()
                r = _req.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"},
                    json={
                        "model": mm,
                        "messages": [{"role": "user", "content": "Reply OK"}],
                        "temperature": 0.0,
                        "max_tokens": 32,
                    },
                    timeout=15,
                )
                lat = round((time.time() - t0) * 1000)
                if r.status_code == 200:
                    mistral_ok_models.append(f"{mm} ({lat}ms)")
                else:
                    print(f"   ⚠️ Mistral model {mm} -> HTTP {r.status_code}")
                time.sleep(1.3)
            m_res = audit_with_mistral("Il mercato USA ha chiuso regolarmente oggi.", session_name="US_CLOSE")
            if m_res and "decision" in m_res:
                mistral_status = f"✅ OK ({m_res.get('auditor')}, {m_res.get('latency_sec', 0)}s -> {m_res.get('decision')}); Attivi: {', '.join(mistral_ok_models)}"
            else:
                mistral_status = f"⚠️ audit_with_mistral None (probe OK: {mistral_ok_models})"
        except Exception as e:
            mistral_status = f"❌ Error: {e}"
    print(f"🔍 Mistral Auditor: {mistral_status}")

    # Tavily (ALL accounts via GET /usage + failover search verification)
    tavily_status = "⚠️ Not configured"
    tavily_ok_accounts = 0
    tavily_total_accounts = 0
    try:
        from tavily_search import inspect_tavily_accounts_usage, search_tavily
        accounts = inspect_tavily_accounts_usage(timeout=10)
        tavily_total_accounts = len(accounts)
        if accounts:
            for acct in accounts:
                st = acct["status"]
                icon = "✅" if st == "ok" else ("🔴" if st == "quota_exceeded" else "⚠️")
                print(f"   {icon} Tavily Account {acct['index']} ({acct['env_var']} {acct['masked_key']}): {acct['detail']}")
                if st == "ok":
                    tavily_ok_accounts += 1
            t_res = search_tavily("Wall Street market close today", max_results=2)
            if t_res:
                tavily_status = f"✅ Failover OK ({len(t_res)} news retrieved, {tavily_ok_accounts}/{tavily_total_accounts} accounts active)"
            else:
                tavily_status = f"⚠️ Search returned empty ({tavily_ok_accounts}/{tavily_total_accounts} accounts active)"
    except Exception as e:
        tavily_status = f"❌ Error: {e}"
    print(f"🌐 Tavily Live Search: {tavily_status}")

    # ── Part 4: Live End-to-End Post Generation + Parallel Triple-Check ─────
    print("\n--- Part 4: Live Post Generation & Parallel Triple-Check (Groq+Mistral+Tavily) ---")
    e2e_post_ok = False
    e2e_consensus_ok = False
    try:
        import ai_news_generator
        from independent_fact_checker import run_micro_topic_consensus_fact_check

        sim_stocks = {
            "NVDA": {"daily_change": 1.45, "company_name": "NVIDIA"},
            "MSFT": {"daily_change": 0.92, "company_name": "Microsoft"},
            "AVGO": {"daily_change": 1.18, "company_name": "Broadcom"},
            "AMZN": {"daily_change": -0.45, "company_name": "Amazon"},
        }
        t0 = time.time()
        cand_post = ai_news_generator.generate_market_news_recap(
            max_tags=4,
            market_session="U.S. market close",
            stock_data=sim_stocks,
        )
        gen_lat = round((time.time() - t0) * 1000)
        if cand_post and len(cand_post) > 250:
            e2e_post_ok = True
            print(f"✅ End-to-End Post Generation: OK ({len(cand_post)} chars in {gen_lat}ms)")
            t1 = time.time()
            audit_res = run_micro_topic_consensus_fact_check(
                cand_post,
                session_name="US_CLOSE",
                stock_data=sim_stocks,
            )
            audit_lat = round((time.time() - t1) * 1000)
            if audit_res and audit_res.get("decision"):
                e2e_consensus_ok = True
                print(
                    f"✅ Parallel Micro-Topic Triple-Check: OK ({audit_res.get('decision')}, "
                    f"auditor={audit_res.get('auditor')}) in {audit_lat}ms"
                )
            else:
                print(f"⚠️ Parallel Micro-Topic Triple-Check returned {audit_res} in {audit_lat}ms")
        else:
            print(f"❌ End-to-End Post Generation failed or too short ({gen_lat}ms)")
    except Exception as e:
        print(f"❌ Part 4 exception: {e}")

    # ── Summary Report ──────────────────────────────────────────────────────
    print("=" * 70)
    print("📊 AI MODEL CAPABILITIES SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Model Name':<24} | {'Text Gen':<20} | {'Search Tool':<24} | {'JSON Mode':<15}")
    print("-" * 90)
    for r in results:
        tg = "✅ OK" if "✅" in (r["text_gen"] or "") else ("🔴 429 Quota" if "429" in (r["text_gen"] or "") else "⚠️ Issue")
        sg = (
            "✅ OK" if "✅" in (r["search_grounding"] or "")
            else ("ℹ️ 429 Free-Tier" if "429" in (r["search_grounding"] or "") else "⚠️ Issue")
        )
        jm = "✅ OK" if "✅" in (r["json_output"] or "") else "⚠️ Issue"
        print(f"{r['model']:<24} | {tg:<20} | {sg:<24} | {jm:<15}")
    print("=" * 70)

    operational_models = [r["model"] for r in results if "✅" in (r["text_gen"] or "")]
    all_tiers_ok = all(bool(out and mdl) for out, mdl, _ in tier_results.values())
    tavily_healthy = (tavily_total_accounts == 0) or (tavily_ok_accounts > 0 and "✅" in tavily_status)
    print(f"\n✅ Operational Gemini Models: {len(operational_models)}/{len(DEFAULT_GEMINI_MODELS)} ({', '.join(operational_models)})")
    print(f"📝 Live E2E Post Gen: {'✅ OK' if e2e_post_ok else '❌ FAILED'} | Triple-Check Consensus: {'✅ OK' if e2e_consensus_ok else '⚠️ Partial'}")

    if len(operational_models) >= 2 and all_tiers_ok and tavily_healthy and e2e_post_ok:
        print("✅ System is 100% HEALTHY and production-ready!")
        return 0
    elif operational_models and all_tiers_ok and e2e_post_ok:
        print("⚠️ System is functional via cascade fallback (check optional alerts above).")
        return 0
    else:
        print("❌ Critical: Model cascade or required tier failed.")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
