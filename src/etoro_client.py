#!/usr/bin/env python3
"""
eToro Public API Client
=======================
Client module for the official eToro Public API (https://public-api.etoro.com).
Supports:
  • Account and user info validation (/api/v1/me)
  • Real portfolio holdings and weight percentages (/api/v2/trading/info/instrument-breakdown)
  • Real-time account PnL (/api/v1/trading/info/real/pnl)
  • Monthly gain history (/api/v2/portfolios/{username}/gain/monthly)
  • Media attachment upload (/api/v1/attachments)
  • Social Feed post creation (/api/v1/posts)
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List, Tuple

import uuid

BASE_URL = "https://public-api.etoro.com"

MARKET_IDS = {
    "PLTR": 7991,
    "NVDA": 1137,
    "MSFT": 1004,
    "AMZN": 1005,
    "GOOG": 1002,
    "CCJ": 6634,
    "URNM": 75677,
    "LLY": 1567,
    "NOVO-B.CO": 2260,
    "SX7PEX.DE": 10595,
    "MELI": 4108,
    "ASML.AS": 1500,
    "TSM": 4481,
    "AVGO": 4236,
    "MBG.DE": 1133,
    "0005.HK": 5472,
    "1211.HK": 2380,
    "01211.HK": 2380,
    "RACE": 1917,
    "ENEL.MI": 1282,
    "ENI.MI": 1283,
    "PRY.MI": 1296,
    "VOW3.DE": 1210,
    "AZN.L": 2010,
    "GLEN.L": 2035,
    "TRIG.L": 2686,
    "VOF.L": 2828,
    "IEUR": 3150,
    "IQQL.DE": 2913,
    "WDEF.L": 3297,
    "PPFB.DE": 2941,
    "XEON.DE": 10559,
    "IB01.L": 1442,
    "HUM": 1512,
    "ABBV": 1452,
    "ABT.US": 1552,
}


def get_market_ids_for_tickers(tickers: List[str]) -> List[int]:
    """Resolve a list of ticker symbols into eToro numeric market IDs."""
    ids = []
    for t in tickers:
        clean = t.replace("$", "").strip().upper()
        if clean in MARKET_IDS:
            ids.append(MARKET_IDS[clean])
    return ids


def get_credentials() -> Tuple[Optional[str], Optional[str], str]:
    """Retrieve eToro credentials from environment."""
    user_key = os.environ.get("ETORO_USER_KEY")
    api_key = os.environ.get("ETORO_API_KEY", "sdgdskldFPLGfjHn1421dgnlxdGTbngdflg6290bRjslfihsjhSDsdgGHH25hjf")
    username = os.environ.get("ETORO_USERNAME", "AndreaRavalli")
    return user_key, api_key, username


def get_headers() -> Optional[Dict[str, str]]:
    """Build request headers with authentication and fresh x-request-id."""
    user_key, api_key, _ = get_credentials()
    if not user_key:
        return None
    return {
        "User-Agent": "PortfolioRecapBot/1.0 (Mozilla/5.0)",
        "x-user-key": user_key.strip(),
        "x-api-key": api_key.strip(),
        "x-request-id": str(uuid.uuid4()),
    }


def is_configured() -> bool:
    """Check if eToro API credentials are configured."""
    user_key, _, _ = get_credentials()
    return bool(user_key and user_key.strip())


def verify_connection() -> Dict[str, Any]:
    """
    Verify eToro credentials by calling GET /api/v1/me.
    Returns dict with user info and scopes if successful, or error details.
    """
    headers = get_headers()
    if not headers:
        return {"success": False, "error": "ETORO_USER_KEY not configured"}

    url = f"{BASE_URL}/api/v1/me"
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "username": data.get("username"),
                "realCid": data.get("realCid"),
                "scopes": data.get("scopes", []),
            }
        else:
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": resp.text,
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_portfolio_weights() -> Dict[str, float]:
    """
    Fetch exact portfolio weights from GET /api/v2/trading/info/instrument-breakdown.
    Returns a dictionary of {ticker: weight_percentage}.
    """
    headers = get_headers()
    if not headers:
        return {}

    url = f"{BASE_URL}/api/v2/trading/info/instrument-breakdown"
    try:
        resp = requests.get(url, headers=headers, timeout=25)
        if resp.status_code != 200:
            print(f"⚠️ eToro API returned HTTP {resp.status_code}: {resp.text}")
            return {}

        data = resp.json()
        instruments = data.get("instruments", [])
        weights = {}

        for inst in instruments:
            sym = inst.get("symbol")
            totals = inst.get("totals", {})
            weight = totals.get("weightPercent")

            if sym and weight is not None:
                try:
                    w = float(weight)
                    if w > 0:
                        # Normalize HK tickers if needed (e.g. 0005.HK -> standard format)
                        if sym.endswith(".HK"):
                            numeric_part = sym[:-3]
                            if len(numeric_part) == 5 and numeric_part[0] == "0":
                                sym = numeric_part[1:] + ".HK"
                        weights[sym] = w
                except (ValueError, TypeError):
                    continue

        if weights:
            print(f"✓ Fetched {len(weights)} exact portfolio weights directly from official eToro API")
        return weights

    except Exception as e:
        print(f"⚠️ Error fetching portfolio weights from eToro API: {e}")
        return {}


def fetch_portfolio_breakdown() -> Optional[Dict[str, Any]]:
    """Fetch full instrument breakdown details including PnL, margin and positions."""
    headers = get_headers()
    if not headers:
        return None

    url = f"{BASE_URL}/api/v2/trading/info/instrument-breakdown"
    try:
        resp = requests.get(url, headers=headers, timeout=25)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        print(f"⚠️ Error fetching portfolio breakdown from eToro API: {e}")
        return None


def fetch_gain_history(granularity: str = "monthly") -> Optional[List[Dict[str, Any]]]:
    """
    Fetch investor gain history time series from GET /api/v2/portfolios/{username}/gain/{granularity}.
    """
    headers = get_headers()
    if not headers:
        return None

    _, _, username = get_credentials()
    url = f"{BASE_URL}/api/v2/portfolios/{username}/gain/{granularity}"
    try:
        resp = requests.get(url, headers=headers, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", [])
        return None
    except Exception as e:
        print(f"⚠️ Error fetching gain history from eToro API: {e}")
        return None


def upload_attachment(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Upload an image/media attachment to POST /api/v1/attachments.
    Returns attachment metadata dict with 'id', 'type', 'url' if successful.
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found for attachment upload: {file_path}")
        return None

    headers = get_headers()
    if not headers:
        print("❌ eToro API credentials not configured for attachment upload")
        return None

    url = f"{BASE_URL}/api/v1/attachments"
    filename = os.path.basename(file_path)
    content_type = "image/png"
    if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
        content_type = "image/jpeg"
    elif filename.lower().endswith(".webp"):
        content_type = "image/webp"

    try:
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, content_type)}
            # Note: Do not specify Content-Type header manually when using files in requests
            upload_headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}
            resp = requests.post(url, headers=upload_headers, files=files, timeout=35)

        if resp.status_code in (200, 201):
            data = resp.json()
            print(f"✅ Uploaded attachment to eToro: ID {data.get('id')} ({data.get('type')})")
            return data
        else:
            print(f"❌ Failed to upload attachment to eToro (HTTP {resp.status_code}): {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Exception uploading attachment to eToro: {e}")
        return None


def create_post(
    content: str,
    language: str = "it",
    attachment_ids: Optional[List[str]] = None,
    attachment_objects: Optional[List[Dict[str, Any]]] = None,
    market_ids: Optional[List[int]] = None,
    tagged_user_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Publish a post to the eToro Social Feed via POST /api/v1/posts.

    For attachments, pass the full upload response objects via attachment_objects.
    The legacy attachment_ids parameter is kept for backward compatibility but
    attachment_objects is the correct way to attach images.
    """
    headers = get_headers()
    if not headers:
        return {"success": False, "error": "ETORO_USER_KEY not configured"}

    headers["Content-Type"] = "application/json"
    url = f"{BASE_URL}/api/v1/posts"

    body: Dict[str, Any] = {
        "message": content,
        "language": language,
    }

    if attachment_objects:
        body["attachments"] = attachment_objects
    elif attachment_ids:
        body["attachments"] = [{"id": att_id, "type": "Image"} for att_id in attachment_ids]
    if market_ids:
        body["marketIds"] = market_ids
    if tagged_user_ids:
        body["taggedUserIds"] = tagged_user_ids

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code in (200, 201):
            data = resp.json()
            post_id = data.get("id")
            print(f"✅ Successfully posted to eToro Social Feed! Post ID: {post_id}")
            return {
                "success": True,
                "id": post_id,
                "data": data,
            }
        else:
            print(f"❌ Failed to post to eToro (HTTP {resp.status_code}): {resp.text}")
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": resp.text,
            }
    except Exception as e:
        print(f"❌ Exception posting to eToro: {e}")
        return {"success": False, "error": str(e)}


def get_post_metrics(post_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch engagement metrics (likes, comments, content) for a specific eToro post.
    GET /api/v1/posts/{postId}
    """
    headers = get_headers()
    if not headers:
        return None

    url = f"{BASE_URL}/api/v1/posts/{post_id}"
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            emotions = data.get("emotions", {})
            comments = data.get("comments", {})
            return {
                "id": data.get("id"),
                "created": data.get("created"),
                "likes": emotions.get("total", 0),
                "comments": comments.get("total", 0),
                "word_count": data.get("wordCount", 0),
                "reading_time": data.get("readingTimeMinutes", 0),
                "raw": data,
            }
        else:
            print(f"⚠️ Failed to get metrics for post {post_id} (HTTP {resp.status_code})")
            return None
    except Exception as e:
        print(f"⚠️ Error fetching post metrics: {e}")
        return None


def add_post_comment(
    post_id: str,
    message: str,
    language: str = "it",
    attachment_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Add a comment to an existing eToro post.
    POST /api/v1/posts/{postId}/comments
    """
    headers = get_headers()
    if not headers:
        return {"success": False, "error": "eToro API not configured"}

    headers["Content-Type"] = "application/json"
    url = f"{BASE_URL}/api/v1/posts/{post_id}/comments"

    body: Dict[str, Any] = {
        "message": message,
        "language": language,
    }
    if attachment_ids:
        body["attachments"] = [{"id": att_id, "type": "Image"} for att_id in attachment_ids]

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=20)
        if resp.status_code in (200, 201):
            data = resp.json()
            comment_id = data.get("id")
            print(f"✅ Comment added to eToro post {post_id}! Comment ID: {comment_id}")
            return {"success": True, "id": comment_id, "data": data}
        else:
            print(f"❌ Failed to add comment (HTTP {resp.status_code}): {resp.text}")
            return {"success": False, "status_code": resp.status_code, "error": resp.text}
    except Exception as e:
        print(f"❌ Exception adding comment to eToro: {e}")
        return {"success": False, "error": str(e)}


