#!/usr/bin/env python3
"""
Centralized AI Model Cascade & Rate-Limit Resilience
=====================================================
Ensures that all AI generators across the system always attempt generation
with verified high-reliability models first, and gracefully handle quota
exhaustion (429), deadlines (504), or temporary outages (503) by cascading
across tiers.

Verified Hierarchy (Live GitHub Actions Probe):
  1. gemini-4-hydrogen      - Gemini 4 Free Tier flagship (9-20s, separate RPD bucket; needs >=45s HTTP timeout and ThinkingLevel.LOW for bounded budgets)
  2. gemini-3.6-flash       - High-capability 3.x Flash flagship (20 RPD Free Tier, strong Italian)
  3. gemini-3-flash-preview - 3.x preview flagship (2-13s, rich narrative, separate Free Tier quota)
  4. gemini-3.5-flash       - Fast 3.5 series (20 RPD Free Tier, strong JSON structured output)
  5. gemini-3.5-flash-lite  - Sub-second Lite tier (high reliability & high RPD bucket)
  6. gemini-3.1-flash-lite  - Sub-second 3.1 Lite fallback
  7. gemini-2.5-flash       - Stable baseline fallback (explicit v1beta, supports google_search)
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

# Prioritized quality-first cascade for long-form posts and rich synthesis (verified operational on Free Tier)
DEFAULT_GEMINI_MODELS: List[str] = [
    'gemini-4-hydrogen',       # Google Gemini 4 Free Tier flagship (9-20s, crispest Italian & separate RPD bucket)
    'gemini-3.6-flash',        # Reliable 3.x flagship (5-19s, 20 RPD Free Tier)
    'gemini-3-flash-preview',  # 3.x preview flagship (2-13s, rich narrative, separate Free Tier quota)
    'gemini-3.5-flash',        # Fast 3.5 series (2-8s with bounded thinking, 20 RPD Free Tier)
    'gemini-3.5-flash-lite',   # Sub-second Lite tier (high-quota reliability safety net)
    'gemini-3.1-flash-lite',   # Sub-second 3.1 Lite fallback
    'gemini-2.5-flash',        # Legacy baseline fallback (via v1beta)
]

# Prioritized quality-first cascade for community comment replies and catalyst notes (uses ThinkingLevel.LOW on G4)
COMMENT_GEMINI_MODELS: List[str] = [
    'gemini-4-hydrogen',       # Gemini 4 flagship with ThinkingLevel.LOW (3-6s, richest compliant Italian)
    'gemini-3.6-flash',        # Verified 3.6 flagship (5-8s, nuanced portfolio explanations)
    'gemini-3-flash-preview',  # 3.x preview flagship (separate Free Tier quota)
    'gemini-3.5-flash',        # 3.5 Flash fallback
    'gemini-3.5-flash-lite',   # High-quota sub-second Lite safety net
    'gemini-3.1-flash-lite',   # Sub-second 3.1 Lite reserve
    'gemini-2.5-flash',        # Legacy baseline fallback
]

# Prioritized cascade for low-latency / high-RPD utility tasks (health checks, rigid JSON extraction)
FAST_GEMINI_MODELS: List[str] = [
    'gemini-3.5-flash-lite',   # Sub-second natural Italian & JSON
    'gemini-3.1-flash-lite',   # Sub-second 3.1 Lite
    'gemini-3.5-flash',        # ~2s when thinking budget is bounded
    'gemini-4-hydrogen',       # Gemini 4 with ThinkingLevel.LOW (~2.5-4s)
    'gemini-3.6-flash',        # High intelligence fallback
    'gemini-2.5-flash',        # Baseline fallback
]

# Models for the adversarial reviewer / double-check judge (flagship accuracy first + dual-model diversity)
REVIEWER_GEMINI_MODELS: List[str] = [
    'gemini-3.6-flash',        # Primary cross-check reviewer when gemini-4-hydrogen generates
    'gemini-4-hydrogen',       # Gemini 4 deep reviewer (4/4 hard traps at 2.5s with ThinkingLevel.LOW)
    'gemini-3-flash-preview',  # 3.x preview flagship (4/4 traps in 2.1s, separate Free Tier quota)
    'gemini-3.5-flash',        # Fast 3.5 series (4/4 traps in 2.1s, 20 RPD)
    'gemini-3.5-flash-lite',   # High-quota verified JSON auditor fallback
    'gemini-2.5-flash',        # Baseline reviewer fallback
]

# google.genai.types.HttpOptions expects MILLISECONDS (passing seconds causes immediate TLS timeouts).
DEFAULT_HTTP_TIMEOUT_SECONDS: float = 45.0


def build_http_options(
    types_module: Any = None,
    timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
    api_version: Optional[str] = "v1beta",
) -> Any:
    """Build ``google.genai.types.HttpOptions`` safely with millisecond timeout.

    `google.genai.types.HttpOptions.timeout` expects an integer in milliseconds.
    Explicit ``api_version="v1beta"`` ensures system instructions, tools, and
    2.5/3.x/4.x features remain consistent across SDK 1.x and 3.x.
    """
    tmod = types_module or (types if GENAI_AVAILABLE else None)
    if tmod is None or not hasattr(tmod, "HttpOptions"):
        return None
    timeout_ms = int(max(1000, round(float(timeout_seconds) * 1000)))
    kwargs: dict = {"timeout": timeout_ms}
    if api_version:
        kwargs["api_version"] = api_version
    try:
        return tmod.HttpOptions(**kwargs)
    except TypeError:
        try:
            return tmod.HttpOptions(timeout=timeout_ms)
        except Exception:
            return None


def build_thinking_config(
    types_module: Any,
    model_name: str,
    fast_mode: bool = False,
    budget: Optional[int] = None,
) -> Any:
    """Return a safe ``ThinkingConfig`` preventing thinking overhead/choking, or ``None``."""
    tmod = types_module or (types if GENAI_AVAILABLE else None)
    if tmod is None or not hasattr(tmod, "ThinkingConfig"):
        return None
    low = (model_name or "").lower()
    if "lite" in low or "gemma" in low:
        return None

    # Gemini 4 ignores thinking_budget=0; use ThinkingLevel.LOW whenever a fast or
    # bounded budget is requested so thinking does not consume 2000+ output tokens.
    if "gemini-4" in low or "hydrogen" in low:
        if fast_mode or budget is not None:
            try:
                return tmod.ThinkingConfig(thinking_level="LOW")
            except Exception:
                return None
        return None

    # Preview 3-flash models already stay compact (~380 think tokens on audit) and
    # may reject unverified thinking_budget=0; only configure when budget is explicit.
    if "3-flash" in low or "gemini-3-flash" in low:
        if budget is None:
            return None

    if budget is not None:
        target_budget = budget
    elif fast_mode:
        target_budget = 128 if "3.6" in low else 0
    else:
        target_budget = None
    if target_budget is None:
        return None

    try:
        return tmod.ThinkingConfig(thinking_budget=int(target_budget))
    except Exception:
        return None


def execute_with_model_cascade(
    client: Any,
    prompt: Any,
    config: Optional[Any] = None,
    task_name: str = "ai_task",
    preferred_models: Optional[List[str]] = None,
    max_quota_retries: int = 1,
    base_backoff_seconds: float = 3.0,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Executes a prompt against the Gemini API using the prioritized model cascade.
    Always starts with the best model available.

    If a rate limit (429), timeout (504), or temporary error (503) occurs:
      - Pauses briefly when retryable
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

                if response and getattr(response, "text", None):
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
                is_zero_quota = (
                    "pro" in model_name.lower()
                    or "limit: 0" in err_str
                    or "limit:0" in err_str
                )

                if is_quota:
                    if is_zero_quota:
                        # Zero-quota models on Free Tier (Pro previews / limit: 0 features) fail immediately
                        print(f"   ℹ️ Model {model_name} returned 429 (0 quota on Free Tier). Cascading immediately...")
                        if API_TRACKER_AVAILABLE:
                            log_api_request(model_name, False, task_name)
                        break

                    wait_time = base_backoff_seconds * (attempt + 1)
                    print(f"   ⏳ Model {model_name} quota/rate limit (429). Waiting {wait_time:.1f}s before fallback...")
                    time.sleep(wait_time)
                    if attempt < max_quota_retries:
                        print(f"   🔄 Retrying {model_name} (attempt {attempt+2}/{max_quota_retries+1})...")
                        continue
                    print("   ⏭️ Moving to next tier model in cascade...")
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, False, task_name)
                    break

                if is_503:
                    if attempt < max_quota_retries:
                        wait_time = base_backoff_seconds * 2
                        print(f"   ⚠️ Model {model_name} temporarily unavailable (503). Waiting {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, False, task_name)
                    break

                print(f"   ⚠️ Model {model_name} failed: {exc}")
                if API_TRACKER_AVAILABLE:
                    log_api_request(model_name, False, task_name)
                break

    return None, None

