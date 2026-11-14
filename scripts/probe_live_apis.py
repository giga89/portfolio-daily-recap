#!/usr/bin/env python3
"""
Live API Discovery & Capability Probe for GitHub Actions Runners.

Queries actual live model catalogs, response latencies, rate-limit headers,
reasoning/JSON capabilities, Google Search grounding status, image models,
and multi-account Tavily usage/search endpoints using environment secrets.
"""

import importlib.metadata
import inspect
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

# Ensure project src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

AUDIT_SYSTEM_PROMPT = (
    "Sei un revisore finanziario rigoroso. Rispondi SOLO in JSON valido con chiavi: "
    '{"verdict": "APPROVE"|"REJECT", "caught_error": true|false, '
    '"reason": "breve spiegazione in italiano", "corrected_sentence": "frase corretta in italiano"}.'
)

AUDIT_USER_PROMPT = (
    "DATI CERTIFICATI DI MERCATO:\n"
    "- TSM (TSMC): +2.10% nella seduta odierna.\n\n"
    "TESTO DA VERIFICARE:\n"
    '"Seduta difficile per $TSM che chiude in calo del -2.10% nonostante i solidi ordini AI."\n\n'
    "Verifica se il testo contraddice i dati certificati."
)


def _mask_key(val: str) -> str:
    if not val:
        return "<empty>"
    if len(val) <= 8:
        return f"***{val[-2:]} (len={len(val)})"
    return f"***{val[-4:]} (len={len(val)})"


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def probe_environment() -> None:
    print("=" * 72)
    print("0. RUNTIME & SDK DIAGNOSTICS")
    print("=" * 72)
    print(f"Python: {sys.version.split()[0]}")
    for pkg in ("google-genai", "requests", "tavily-python", "yfinance"):
        try:
            ver = importlib.metadata.version(pkg)
            print(f"  - {pkg}: {ver}")
        except importlib.metadata.PackageNotFoundError:
            print(f"  - {pkg}: <not installed>")

    try:
        from google.genai import types
        if hasattr(types, "HttpOptions"):
            src = inspect.getsource(types.HttpOptions)
            timeout_lines = [line.strip() for line in src.splitlines() if "timeout" in line.lower()]
            print(f"  - HttpOptions timeout annotations: {timeout_lines[:4]}")
    except Exception as exc:
        print(f"  - HttpOptions inspect failed: {exc}")


def probe_gemini() -> None:
    print("\n" + "=" * 72)
    print("1. GOOGLE GEMINI / GEMMA LIVE DISCOVERY & PROBE")
    print("=" * 72)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("❌ GEMINI_API_KEY non impostata.")
        return

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        print(f"❌ google-genai import failed: {exc}")
        return

    http_opts = types.HttpOptions(timeout=25000) if hasattr(types, "HttpOptions") else None
    client = genai.Client(api_key=api_key, http_options=http_opts) if http_opts else genai.Client(api_key=api_key)

    discovered: List[Dict[str, Any]] = []
    try:
        for m in client.models.list():
            raw_name = getattr(m, "name", "") or ""
            short_name = raw_name.replace("models/", "")
            actions = list(getattr(m, "supported_actions", None) or [])
            discovered.append(
                {
                    "name": short_name,
                    "display_name": getattr(m, "display_name", ""),
                    "actions": actions,
                    "in_tok": getattr(m, "input_token_limit", None),
                    "out_tok": getattr(m, "output_token_limit", None),
                }
            )
    except Exception as exc:
        print(f"❌ client.models.list() failed: {exc}")
        return

    print(f"📋 Totale modelli restituiti da client.models.list(): {len(discovered)}")
    for item in discovered:
        if any(k in item["name"] for k in ("gemini", "gemma", "imagen", "nano", "banana")):
            print(
                f"  • {item['name']:<42} | in={item['in_tok']} out={item['out_tok']} | actions={item['actions']}"
            )

    all_names = {item["name"]: item for item in discovered}

    # Candidate text models: include current cascade + newest Gemini 4 / 3.x / 2.5 / Gemma 4/3
    preferred_order = [
        "gemini-4-hydrogen",
        "gemini-4-argon",
        "gemini-4-carbon",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-pro-preview",
        "gemini-3-flash-preview",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
        "gemma-4-31b-it",
        "gemma-4-26b-a4b-it",
        "gemma-3-27b-it",
    ]
    # Add any extra unversioned gemini-4 / gemini-3 / gemma-4 generateContent models found in list()
    for item in discovered:
        n = item["name"]
        if n in preferred_order:
            continue
        if "generateContent" not in item["actions"] and item["actions"]:
            continue
        if any(skip in n for skip in ("embedding", "tts", "audio", "robotics", "computer-use", "deep-research", "live", "image", "veo", "lyria", "-001", "-002")):
            continue
        if re.match(r"^(gemini-(?:4|3|2\.5)|gemma-4)", n):
            preferred_order.append(n)

    # Probe listed models + verify aliases if absent in list()
    candidates: List[str] = []
    for m in preferred_order:
        if m in all_names or m in ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash"):
            if m not in candidates:
                candidates.append(m)

    candidates = candidates[:18]
    print(f"\n🧪 Probing {len(candidates)} Gemini/Gemma text candidates (HttpOptions timeout=25000ms):")
    working_gemini: List[str] = []

    for model_name in candidates:
        t0 = time.monotonic()
        is_gemma = model_name.startswith("gemma-")
        try:
            cfg_kwargs: Dict[str, Any] = {
                "temperature": 0.0,
                "max_output_tokens": 512,
            }
            if not is_gemma:
                cfg_kwargs["system_instruction"] = AUDIT_SYSTEM_PROMPT
                cfg_kwargs["response_mime_type"] = "application/json"
                prompt_text = AUDIT_USER_PROMPT
            else:
                prompt_text = f"{AUDIT_SYSTEM_PROMPT}\n\n{AUDIT_USER_PROMPT}"

            resp = client.models.generate_content(
                model=model_name,
                contents=prompt_text,
                config=types.GenerateContentConfig(**cfg_kwargs),
            )
            elapsed = time.monotonic() - t0
            txt = (getattr(resp, "text", None) or "").strip()
            parsed = _extract_json(txt)
            usage = getattr(resp, "usage_metadata", None)
            u_info = ""
            if usage:
                u_info = (
                    f"in={getattr(usage, 'prompt_token_count', '?')}, "
                    f"out={getattr(usage, 'candidates_token_count', '?')}, "
                    f"think={getattr(usage, 'thoughts_token_count', None)}"
                )
            caught = parsed.get("caught_error") if isinstance(parsed, dict) else None
            verdict = parsed.get("verdict") if isinstance(parsed, dict) else None
            print(
                f"  ✅ {model_name:<30} | {elapsed:5.2f}s | json={'OK' if parsed else 'BAD'} | "
                f"verdict={verdict} caught={caught} | {u_info}"
            )
            if not is_gemma:
                working_gemini.append(model_name)
        except Exception as exc:
            elapsed = time.monotonic() - t0
            err_short = str(exc).replace("\n", " ")[:180]
            print(f"  ❌ {model_name:<30} | {elapsed:5.2f}s | ERR: {err_short}")
        time.sleep(1.2)

    # Probe Google Search grounding on up to 4 working non-Gemma models
    search_candidates = working_gemini[:4]
    if search_candidates:
        print(f"\n🔎 Probing google_search grounding tool on top {len(search_candidates)} working models:")
        for model_name in search_candidates:
            t0 = time.monotonic()
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents="What is NVIDIA (NVDA) latest stock news headline today? Reply in 1 short sentence.",
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.0,
                        max_output_tokens=200,
                    ),
                )
                elapsed = time.monotonic() - t0
                txt = (getattr(resp, "text", None) or "").strip().replace("\n", " ")[:110]
                gm = None
                if getattr(resp, "candidates", None):
                    gm = getattr(resp.candidates[0], "grounding_metadata", None)
                chunks = len(getattr(gm, "grounding_chunks", None) or []) if gm else 0
                print(f"  ✅ search {model_name:<25} | {elapsed:5.2f}s | chunks={chunks} | '{txt}'")
            except Exception as exc:
                elapsed = time.monotonic() - t0
                err_short = str(exc).replace("\n", " ")[:180]
                print(f"  ❌ search {model_name:<25} | {elapsed:5.2f}s | ERR: {err_short}")
            time.sleep(1.2)

    # Image models discovery check (probe up to 2 promising non-legacy image models only)
    img_models = [
        item["name"]
        for item in discovered
        if any(k in item["name"] for k in ("image", "imagen", "banana"))
    ]
    print(f"\n🖼️ Discovered Image models ({len(img_models)}): {img_models}")
    probe_imgs = [
        m for m in ("gemini-2.5-flash-image", "gemini-2.0-flash-preview-image-generation", "gemini-3-pro-image-preview", "gemini-3.1-flash-image-preview")
        if m in all_names
    ]
    if not probe_imgs:
        probe_imgs = [m for m in img_models if "gemini-" in m and "image" in m][:2]
    for model_name in probe_imgs[:2]:
        t0 = time.monotonic()
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents="Generate a minimal dark navy abstract financial background, no text.",
                config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
            )
            elapsed = time.monotonic() - t0
            has_img = False
            for part in (resp.candidates[0].content.parts if resp.candidates else []):
                if getattr(part, "inline_data", None):
                    has_img = True
                    break
            print(f"  {'✅' if has_img else '⚠️'} img {model_name:<35} | {elapsed:5.2f}s | has_image={has_img}")
        except Exception as exc:
            elapsed = time.monotonic() - t0
            print(f"  ❌ img {model_name:<35} | {elapsed:5.2f}s | ERR: {str(exc).replace(chr(10), ' ')[:170]}")
        time.sleep(1.0)


def _probe_openai_compat(
    provider_name: str,
    models_url: str,
    chat_url: str,
    api_key: str,
    min_delay: float,
    skip_substrings: Tuple[str, ...],
    extra_priority: List[str],
    max_candidates: int = 10,
) -> None:
    print("\n" + "=" * 72)
    print(f"PROBE: {provider_name}")
    print("=" * 72)
    if not api_key:
        print(f"❌ API key per {provider_name} non impostata.")
        return

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        r = requests.get(models_url, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"❌ GET {models_url} -> HTTP {r.status_code}: {r.text[:250]}")
            return
        data = r.json().get("data", [])
    except Exception as exc:
        print(f"❌ Model list failed for {provider_name}: {exc}")
        return

    print(f"📋 Totale modelli live su {provider_name}: {len(data)}")
    model_ids: List[str] = []
    seen = set()
    for m in sorted(data, key=lambda x: str(x.get("id", ""))):
        mid = str(m.get("id", ""))
        if not mid or mid in seen:
            continue
        seen.add(mid)
        model_ids.append(mid)
        ctx = m.get("context_window") or m.get("max_context_length") or "?"
        active = m.get("active", True)
        print(f"  • {mid:<45} | ctx={ctx} | active={active}")

    candidates: List[str] = []
    for p in extra_priority:
        if p in seen and p not in candidates:
            candidates.append(p)
    for mid in model_ids:
        low = mid.lower()
        if any(sk in low for sk in skip_substrings):
            continue
        if mid not in candidates:
            candidates.append(mid)
    candidates = candidates[:max_candidates]

    print(f"\n🧪 Probing {len(candidates)} {provider_name} candidate models (delay={min_delay}s):")
    for idx, mid in enumerate(candidates):
        if idx > 0:
            time.sleep(min_delay)

        payload: Dict[str, Any] = {
            "model": mid,
            "messages": [
                {"role": "system", "content": AUDIT_SYSTEM_PROMPT},
                {"role": "user", "content": AUDIT_USER_PROMPT},
            ],
            "temperature": 0.0,
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
        }
        t0 = time.monotonic()
        try:
            resp = requests.post(chat_url, headers=headers, json=payload, timeout=25)
            elapsed = time.monotonic() - t0
            used_json_mode = True
            if resp.status_code == 400 and "response_format" in resp.text:
                time.sleep(min_delay)
                payload.pop("response_format", None)
                t0 = time.monotonic()
                resp = requests.post(chat_url, headers=headers, json=payload, timeout=25)
                elapsed = time.monotonic() - t0
                used_json_mode = False

            rl_headers = {
                k: v
                for k, v in resp.headers.items()
                if "ratelimit" in k.lower() or "retry-after" in k.lower()
            }
            if resp.status_code != 200:
                print(
                    f"  ❌ {mid:<36} | HTTP {resp.status_code} | {elapsed:5.2f}s | "
                    f"{resp.text[:160]} | rl={rl_headers}"
                )
                continue

            body = resp.json()
            msg = body.get("choices", [{}])[0].get("message", {})
            content = (msg.get("content") or "").strip()
            reasoning = (msg.get("reasoning") or "").strip()
            usage = body.get("usage", {})
            parsed = _extract_json(content)
            verdict = parsed.get("verdict") if isinstance(parsed, dict) else None
            caught = parsed.get("caught_error") if isinstance(parsed, dict) else None
            print(
                f"  ✅ {mid:<36} | {elapsed:5.2f}s | json_mode={used_json_mode} "
                f"parsed={'OK' if parsed else 'BAD'} | verdict={verdict} caught={caught} | "
                f"tok={usage.get('completion_tokens', '?')} (reason_chars={len(reasoning)}) | rl={rl_headers}"
            )
            if not parsed:
                print(f"     raw_content[:140]={content[:140]!r}")
        except Exception as exc:
            print(f"  ❌ {mid:<36} | ERR: {exc}")


def probe_tavily() -> None:
    print("\n" + "=" * 72)
    print("4. TAVILY MULTI-ACCOUNT USAGE & LIVE SEARCH PROBE")
    print("=" * 72)
    try:
        from tavily_search import get_tavily_api_keys
        ordered_keys = get_tavily_api_keys()
    except Exception as exc:
        print(f"⚠️ Could not import tavily_search.get_tavily_api_keys: {exc}")
        ordered_keys = []

    env_map: Dict[str, List[str]] = {}
    for k, v in sorted(os.environ.items()):
        if k.startswith("TAVILY_API_KEY") and v and v.strip():
            env_map.setdefault(v.strip(), []).append(k)

    print(f"📋 Env vars Tavily valorizzate: {[names for names in env_map.values()]}")
    print(f"📋 Chiavi uniche ordinate da get_tavily_api_keys(): {len(ordered_keys)}")

    for idx, api_key in enumerate(ordered_keys, 1):
        names = env_map.get(api_key, ["TAVILY_API_KEYS"])
        label = ", ".join(names)
        print(f"\n--- Account {idx}/{len(ordered_keys)} ({label}, {_mask_key(api_key)}) ---")
        try:
            u_resp = requests.get(
                "https://api.tavily.com/usage",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            print(f"  GET /usage -> HTTP {u_resp.status_code}: {u_resp.text[:400]}")
        except Exception as exc:
            print(f"  GET /usage ERR: {exc}")

        try:
            t0 = time.monotonic()
            s_resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": "NVIDIA stock news",
                    "max_results": 1,
                    "search_depth": "basic",
                    "include_answer": False,
                },
                timeout=15,
            )
            elapsed = time.monotonic() - t0
            if s_resp.status_code == 200:
                results = s_resp.json().get("results", [])
                print(f"  POST /search -> HTTP 200 in {elapsed:.2f}s | results={len(results)}")
            else:
                print(f"  POST /search -> HTTP {s_resp.status_code} in {elapsed:.2f}s: {s_resp.text[:200]}")
        except Exception as exc:
            print(f"  POST /search ERR: {exc}")


def probe_deep() -> None:
    print("=" * 72)
    print("DEEP PROBE: THINKING CONFIG, LATENCY, NEW LITE MODELS, COMMENT QUALITY & ERRORS")
    print("=" * 72)
    probe_environment()

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key:
        from google import genai
        from google.genai import types

        if hasattr(types, "ThinkingLevel"):
            print(f"  - ThinkingLevel values: {[e.value for e in types.ThinkingLevel]}")

        http_opts = types.HttpOptions(timeout=60000) if hasattr(types, "HttpOptions") else None
        client = genai.Client(api_key=api_key, http_options=http_opts) if http_opts else genai.Client(api_key=api_key)

        deep_tests = [
            # (model, kwargs_for_GenerateContentConfig, label, is_gemma)
            ("gemini-4-hydrogen", {"max_output_tokens": 2048}, "4-hydrogen default 60s", False),
            ("gemini-4-hydrogen", {"max_output_tokens": 2048, "thinking_budget": 0}, "4-hydrogen think=0", False),
            ("gemini-4-hydrogen", {"max_output_tokens": 2048, "thinking_level": "LOW"}, "4-hydrogen think=LOW", False),
            ("gemini-3.8-flash", {"max_output_tokens": 2048, "thinking_budget": 0}, "3.8-flash think=0", False),
            ("gemini-3.7-flash", {"max_output_tokens": 2048, "thinking_budget": 0}, "3.7-flash think=0", False),
            ("gemini-3.7-flash", {"max_output_tokens": 2048, "thinking_budget": 256}, "3.7-flash think=256", False),
            ("gemini-3.6-flash", {"max_output_tokens": 2048, "thinking_budget": 0}, "3.6-flash think=0", False),
            ("gemini-3.6-flash", {"max_output_tokens": 2048, "thinking_budget": 256}, "3.6-flash think=256", False),
            ("gemini-3.5-flash", {"max_output_tokens": 2048}, "3.5-flash default 2048tok", False),
            ("gemini-3.5-flash", {"max_output_tokens": 2048, "thinking_budget": 0}, "3.5-flash think=0", False),
            ("gemini-3.5-flash-lite", {"max_output_tokens": 2048}, "3.5-flash-lite default", False),
            ("gemini-3.1-flash-lite", {"max_output_tokens": 2048}, "3.1-flash-lite default", False),
            ("gemini-3.1-flash-lite-preview", {"max_output_tokens": 2048}, "3.1-flash-lite-preview", False),
            ("gemini-omni-1.2-flash", {"max_output_tokens": 2048}, "omni-1.2-flash", False),
            ("gemini-2.5-flash", {"max_output_tokens": 2048, "thinking_budget": 0}, "2.5-flash think=0", False),
            ("gemma-4-26b-a4b-it", {"max_output_tokens": 2048}, "gemma-4-26b 2048tok", True),
            ("gemma-4-31b-it", {"max_output_tokens": 2048}, "gemma-4-31b 2048tok", True),
        ]

        print("\n🧪 Deep Gemini/Gemma Matrix (60s HttpOptions, 2048 max_output_tokens):")
        for model_name, extra, label, is_gemma in deep_tests:
            t0 = time.monotonic()
            try:
                cfg: Dict[str, Any] = {
                    "temperature": 0.0,
                    "max_output_tokens": extra["max_output_tokens"],
                }
                if not is_gemma:
                    cfg["system_instruction"] = AUDIT_SYSTEM_PROMPT
                    cfg["response_mime_type"] = "application/json"
                    prompt_text = AUDIT_USER_PROMPT
                else:
                    prompt_text = f"{AUDIT_SYSTEM_PROMPT}\n\n{AUDIT_USER_PROMPT}"

                t_cfg = {}
                if "thinking_budget" in extra:
                    t_cfg["thinking_budget"] = extra["thinking_budget"]
                if "thinking_level" in extra and hasattr(types, "ThinkingLevel"):
                    lvl = extra["thinking_level"]
                    if hasattr(types.ThinkingLevel, lvl):
                        t_cfg["thinking_level"] = getattr(types.ThinkingLevel, lvl)
                if t_cfg and hasattr(types, "ThinkingConfig"):
                    cfg["thinking_config"] = types.ThinkingConfig(**t_cfg)

                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt_text,
                    config=types.GenerateContentConfig(**cfg),
                )
                elapsed = time.monotonic() - t0
                txt = (getattr(resp, "text", None) or "").strip()
                parsed = _extract_json(txt)
                usage = getattr(resp, "usage_metadata", None)
                in_t = getattr(usage, "prompt_token_count", "?") if usage else "?"
                out_t = getattr(usage, "candidates_token_count", "?") if usage else "?"
                th_t = getattr(usage, "thoughts_token_count", None) if usage else None
                print(
                    f"  ✅ {label:<26} | {elapsed:5.2f}s | json={'OK' if parsed else 'BAD'} | "
                    f"verdict={parsed.get('verdict') if isinstance(parsed, dict) else None} "
                    f"caught={parsed.get('caught_error') if isinstance(parsed, dict) else None} | "
                    f"tok(in={in_t},out={out_t},think={th_t})"
                )
            except Exception as exc:
                elapsed = time.monotonic() - t0
                print(f"  ❌ {label:<26} | {elapsed:5.2f}s | ERR: {str(exc).replace(chr(10), ' ')[:260]}")
            time.sleep(1.2)

        print("\n🔎 Inspect full 429 error for google_search & image quota:")
        for m in ("gemini-3.5-flash-lite", "gemini-2.5-flash"):
            try:
                client.models.generate_content(
                    model=m,
                    contents="Latest NVDA news today in 1 sentence.",
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        max_output_tokens=150,
                    ),
                )
                print(f"  ✅ google_search on {m}: SUCCEEDED!")
            except Exception as exc:
                print(f"  ❌ google_search on {m}: {str(exc)[:600]}")
            time.sleep(1.0)

        try:
            r_img = client.models.generate_content(
                model="gemini-3.1-flash-lite-image",
                contents="Minimalist dark navy abstract geometric background, no text.",
                config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
            )
            has_img = any(getattr(p, "inline_data", None) for p in (r_img.candidates[0].content.parts if r_img.candidates else []))
            print(f"  ✅ img gemini-3.1-flash-lite-image: has_image={has_img}")
        except Exception as exc:
            print(f"  ❌ img gemini-3.1-flash-lite-image: {str(exc)[:450]}")

    # Realistic Italian comment-reply quality benchmark across top candidates
    reply_system = (
        "Sei Andrea Ravalli, Popular Investor su eToro. Rispondi in italiano naturale, competente e sobrio "
        "(max 2-3 frasi, niente consigli finanziari personalizzati, nessuna promessa di rendimenti)."
    )
    reply_user = (
        "Mio post originale: 'Chiusura USA mista: Nasdaq in lieve calo (-0.4%) con prese di profitto sui semiconduttori ($NVDA -1.8%), "
        "mentre il comparto difesa e utilities tiene bene il portafoglio.'\n"
        "Commento utente (@Marco88): 'Ciao Andrea, pensi che convenga entrare su NVDA adesso dopo questo -1.8% o aspettare la trimestrale?'"
    )
    print("\n💬 ITALIAN COMMENT REPLY BENCHMARK:")
    if api_key:
        for gm in ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash"):
            try:
                t0 = time.monotonic()
                cfg_args: Dict[str, Any] = {
                    "system_instruction": reply_system,
                    "temperature": 0.4,
                    "max_output_tokens": 400,
                }
                if gm == "gemini-3.6-flash" and hasattr(types, "ThinkingConfig"):
                    cfg_args["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                r = client.models.generate_content(
                    model=gm, contents=reply_user, config=types.GenerateContentConfig(**cfg_args)
                )
                print(f"  • {gm:<24} ({time.monotonic()-t0:.2f}s): {(r.text or '').strip()}")
            except Exception as exc:
                print(f"  • {gm:<24} ERR: {str(exc)[:180]}")
            time.sleep(1.0)

    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_key:
        for gmodel, extra_body in [
            ("qwen/qwen3.8-27b", {}),
            ("openai/gpt-oss-120b", {"reasoning_effort": "low"}),
        ]:
            try:
                t0 = time.monotonic()
                body = {
                    "model": gmodel,
                    "messages": [
                        {"role": "system", "content": reply_system},
                        {"role": "user", "content": reply_user},
                    ],
                    "temperature": 0.4,
                    "max_tokens": 500,
                    **extra_body,
                }
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json=body,
                    timeout=20,
                )
                if resp.status_code == 200:
                    msg = resp.json()["choices"][0]["message"]
                    print(f"  • groq:{gmodel:<19} ({time.monotonic()-t0:.2f}s): {(msg.get('content') or '').strip()}")
                else:
                    print(f"  • groq:{gmodel:<19} HTTP {resp.status_code}: {resp.text[:220]}")
            except Exception as exc:
                print(f"  • groq:{gmodel:<19} ERR: {exc}")
            time.sleep(0.8)

    mistral_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if mistral_key:
        for idx, mmodel in enumerate(("codestral-latest", "ministral-14b-latest", "ministral-8b-latest")):
            if idx > 0:
                time.sleep(2.2)
            try:
                t0 = time.monotonic()
                resp = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"},
                    json={
                        "model": mmodel,
                        "messages": [
                            {"role": "system", "content": reply_system},
                            {"role": "user", "content": reply_user},
                        ],
                        "temperature": 0.4,
                        "max_tokens": 400,
                    },
                    timeout=20,
                )
                if resp.status_code == 200:
                    msg = resp.json()["choices"][0]["message"]
                    print(f"  • mistral:{mmodel:<16} ({time.monotonic()-t0:.2f}s): {(msg.get('content') or '').strip()}")
                else:
                    print(f"  • mistral:{mmodel:<16} HTTP {resp.status_code}: {resp.text[:220]}")
            except Exception as exc:
                print(f"  • mistral:{mmodel:<16} ERR: {exc}")


def main() -> int:
    if "--deep" in sys.argv:
        probe_deep()
        return 0
    probe_environment()
    probe_gemini()
    _probe_openai_compat(
        provider_name="2. GROQ LIVE DISCOVERY & AUDIT PROBE",
        models_url="https://api.groq.com/openai/v1/models",
        chat_url="https://api.groq.com/openai/v1/chat/completions",
        api_key=os.environ.get("GROQ_API_KEY", "").strip(),
        min_delay=0.7,
        skip_substrings=("whisper", "playai", "orpheus", "guard", "safeguard", "compound"),
        extra_priority=[
            "qwen/qwen3.8-27b",
            "qwen/qwen3-32b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "moonshotai/kimi-k2-instruct",
            "llama-3.1-8b-instant",
        ],
        max_candidates=12,
    )
    _probe_openai_compat(
        provider_name="3. MISTRAL LIVE DISCOVERY & AUDIT PROBE",
        models_url="https://api.mistral.ai/v1/models",
        chat_url="https://api.mistral.ai/v1/chat/completions",
        api_key=os.environ.get("MISTRAL_API_KEY", "").strip(),
        min_delay=1.5,
        skip_substrings=("embed", "ocr", "moderation", "voxtral", "transcribe", "lean", "240"),
        extra_priority=[
            "codestral-latest",
            "mistral-small-latest",
            "mistral-medium-latest",
            "mistral-large-latest",
            "ministral-8b-latest",
            "ministral-14b-latest",
            "ministral-3b-latest",
            "magistral-small-latest",
            "magistral-medium-latest",
        ],
        max_candidates=10,
    )
    probe_tavily()
    print("\n✅ Live discovery probe completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
