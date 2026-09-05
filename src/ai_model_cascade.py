#!/usr/bin/env python3
"""
Centralized AI Model Cascade & Rate-Limit Resilience
=====================================================
Ensures that all AI generators across the system always attempt generation
with the BEST / MOST INTELLIGENT model first, and gracefully handle
quota exhaustion, rate limits (429), or temporary outages (503) by
waiting (exponential backoff) and cascading to next-tier models.

Hierarchy:
  1. gemini-3.1-pro-preview - Flagship Deep Reasoning model (Best intelligence & financial synthesis)
  2. gemini-3.8-flash       - Newest Flagship Flash model (Ultra-fast, top intelligence)
  3. gemini-3.7-flash       - High-capability 3.x series
  4. gemini-3.6-flash       - Advanced reasoning & workflow
  5. gemini-3.5-flash       - High throughput financial context
  6. gemini-2.5-flash       - High reliability baseline fallback
"""

import time
from typing import List, Optional, Tuple, Any

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from api_usage_tracker import log_api_request
    API_TRACKER_AVAILABLE = True
except ImportError:
    try:
        from src.api_usage_tracker import log_api_request
        API_TRACKER_AVAILABLE = True
    except ImportError:
        API_TRACKER_AVAILABLE = False

# Prioritized cascade: Smartest -> Standard fallback
DEFAULT_GEMINI_MODELS: List[str] = [
    'gemini-3.1-pro-preview',  # Flagship Deep Reasoning (Best quality & analytical depth)
    'gemini-3.8-flash',        # Newest Flash flagship (Fast & state-of-the-art)
    'gemini-3.7-flash',        # High-intelligence 3.x series
    'gemini-3.6-flash',        # Advanced reasoning & agentic workflow
    'gemini-3.5-flash',        # Financial context & reasoning
    'gemini-2.5-flash',        # High reliability baseline
]

# Models for the adversarial reviewer / double-check judge (ensures dual-model diversity)
REVIEWER_GEMINI_MODELS: List[str] = [
    'gemini-3.1-pro-preview',
    'gemini-3.8-flash',
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-2.5-flash',
]


def execute_with_model_cascade(
    client: Any,
    prompt: Any,
    config: Optional[Any] = None,
    task_name: str = "ai_task",
    preferred_models: Optional[List[str]] = None,
    max_quota_retries: int = 2,
    base_backoff_seconds: float = 5.0,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Executes a prompt against the Gemini API using the prioritized model cascade.
    Always starts with the best model available.
    
    If a rate limit (429) or temporary error (503) occurs:
      - Pauses with backoff
      - Tries the next tier in the cascade
      - Returns (response_text, model_name) on success, or (None, None) if all fail.
    """
    models = list(preferred_models or DEFAULT_GEMINI_MODELS)

    for idx, model_name in enumerate(models):
        for attempt in range(max_quota_retries + 1):
            try:
                print(f"   🤖 Trying model ({idx+1}/{len(models)}): {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )

                if response and response.text:
                    out = response.text.strip()
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, task_name)
                    print(f"   ✅ Generation succeeded using {model_name}!")
                    return out, model_name

                print(f"   ⚠️ Model {model_name} returned empty text, trying next...")
                break

            except Exception as exc:
                err_str = str(exc).lower()
                is_quota = "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str
                is_503 = "503" in err_str or "unavailable" in err_str or "overloaded" in err_str

                if is_quota:
                    wait_time = base_backoff_seconds * (attempt + 1)
                    print(f"   ⏳ Model {model_name} quota/rate limit (429). Waiting {wait_time:.1f}s before fallback...")
                    time.sleep(wait_time)
                    if attempt < max_quota_retries:
                        print(f"   🔄 Retrying {model_name} (attempt {attempt+2}/{max_quota_retries+1})...")
                        continue
                    else:
                        print(f"   ⏭️ Moving to next tier model in cascade...")
                        break

                elif is_503:
                    wait_time = base_backoff_seconds * 2
                    print(f"   ⚠️ Model {model_name} temporarily unavailable (503). Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    if attempt < max_quota_retries:
                        continue
                    break

                else:
                    print(f"   ⚠️ Model {model_name} failed: {exc}")
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, False, task_name)
                    break

    return None, None

