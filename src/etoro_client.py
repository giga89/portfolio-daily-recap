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
    # Tech, AI & Semiconductors
    "PLTR": 7991,
    "NVDA": 1137,
    "MSFT": 1004,
    "AMZN": 1005,
    "GOOG": 1002,
    "TSM": 4481,
    "AVGO": 4236,
    "MRVL": 4358,

    # Healthcare & Pharma
    "LLY": 1567,
    "NOVO-B.CO": 2260,
    "HUM": 1512,
    "ABBV": 1452,
    "ABT.US": 1552,
    "AZN.L": 2010,

    # Energy, Utilities, Commodities & Nuclear
    "CCJ": 6634,
    "ENI.MI": 1283,
    "ENEL.MI": 1282,
    "MAU.PA": 3585,
    "GLEN.L": 2035,
    "TRIG.L": 2686,
    "MNODL.L": 1352,
    "NVTKL.L": 1353,

    # ETFs, Fixed Income & Cash
    "SX7PEX.DE": 10595,
    "IEUR": 3150,
    "WDEF.L": 3297,
    "PPFB.DE": 2941,
    "IB01.L": 1442,
    "INDO.PA": 15327,
    "IQQL.DE": 2913,
    "VOF.L": 2828,

    # Automotive, Luxury & Industrials
    "RACE": 1917,
    "PRY.MI": 1296,
    "VOW3.DE": 1210,
    "1211.HK": 2380,
    "1919.HK": 13669,
    "ULVR.L": 2093,

    # E-Commerce, Fintech, Pre-IPO, Retail & Crypto
    "MELI": 4108,
    "ETOR": 12200,
    "2318.HK": 2316,
    "WMT": 1035,
    "SPCX.RTH": 15623,
    "TRX": 100026,
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
    """Retrieve eToro credentials from environment or local .env file."""
    user_key = os.environ.get("ETORO_USER_KEY")
    api_key = os.environ.get("ETORO_API_KEY")
    username = os.environ.get("ETORO_USERNAME")

    # Fallback to local .env file if running locally
    if not user_key:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("ETORO_USER_KEY="):
                            user_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        elif line.startswith("ETORO_API_KEY=") and not api_key:
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        elif line.startswith("ETORO_USERNAME=") and not username:
                            username = line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                pass

    api_key = api_key or "sdgdskldFPLGfjHn1421dgnlxdGTbngdflg6290bRjslfihsjhSDsdgGHH25hjf"
    username = username or "AndreaRavalli"
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
    Fetch exact live portfolio weights from GET /api/v1/user-info/people/{username}/portfolio/live.
    Calculates live mark-to-market weighting = investmentPct * (1 + netProfit/100).
    Returns a dictionary of {ticker: weight_percentage}.
    """
    headers = get_headers()
    if not headers:
        return {}

    from collections import defaultdict
    _, _, username = get_credentials()
    username = username or "AndreaRavalli"

    # Known eToro Instrument ID to Ticker mapping derived from authoritative MARKET_IDS
    ID_TO_TICKER = {v: k for k, v in MARKET_IDS.items()}

    url = f"{BASE_URL}/api/v1/user-info/people/{username}/portfolio/live"
    try:
        resp = requests.get(url, headers=headers, timeout=25)
        if resp.status_code != 200:
            print(f"⚠️ eToro API returned HTTP {resp.status_code}: {resp.text}")
            return {}

        data = resp.json()
        positions = data.get("positions", [])
        if not positions:
            return {}

        invested_by_inst = defaultdict(float)
        current_val_by_inst = defaultdict(float)
        total_val = 0.0

        for p in positions:
            iid = p.get("instrumentId")
            inv = p.get("investmentPct", 0.0)
            pnl = p.get("netProfit", 0.0)  # PnL %
            cur_val = inv * (1.0 + pnl / 100.0)
            invested_by_inst[iid] += inv
            current_val_by_inst[iid] += cur_val
            total_val += cur_val

        # Find all unmapped instrument IDs in the current portfolio
        unmapped_iids = [iid for iid in current_val_by_inst.keys() if iid not in ID_TO_TICKER]
        if unmapped_iids:
            print(f"🔎 Dynamically resolving {len(unmapped_iids)} new/unmapped eToro instrument IDs: {unmapped_iids}...")
            try:
                ids_str = ",".join(str(i) for i in unmapped_iids)
                meta_url = f"{BASE_URL}/api/v1/market-data/instruments?instrumentIds={ids_str}"
                meta_resp = requests.get(meta_url, headers=headers, timeout=10)
                if meta_resp.status_code == 200:
                    meta_data = meta_resp.json()
                    for item in meta_data.get("instrumentDisplayDatas", []):
                        iid_res = item.get("instrumentID")
                        sym_res = item.get("symbolFull")
                        name_res = item.get("instrumentDisplayName", sym_res)
                        if iid_res and sym_res:
                            ID_TO_TICKER[iid_res] = sym_res
                            print(f"   ✓ Auto-resolved new eToro asset: ID {iid_res} -> ${sym_res} ({name_res})")
            except Exception as res_err:
                print(f"   ⚠️ Dynamic instrument resolution error: {res_err}")

        weights = {}
        for iid, cur in current_val_by_inst.items():
            ticker = ID_TO_TICKER.get(iid)
            if not ticker:
                print(f"   ⚠️ Skipping unresolved numeric ID {iid} to prevent phantom assets.")
                continue

            w = (cur / total_val) * 100.0 if total_val > 0 else invested_by_inst[iid]
            weights[ticker] = round(w, 2)

        if weights:
            print(f"✓ Fetched {len(weights)} exact live portfolio weights directly from official eToro API")
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


def fetch_trader_rankings(period: str = "CurrYear") -> Optional[Dict[str, Any]]:
    """
    Fetch investor rankings, copier statistics, risk score, and performance from
    GET /api/v2/portfolios/{username}/rankings?period={period}.
    Returns dict containing copiers count, AUM, win ratio, risk score, etc.
    """
    headers = get_headers()
    if not headers:
        return None

    _, _, username = get_credentials()
    username = username or "AndreaRavalli"
    url = f"{BASE_URL}/api/v2/portfolios/{username}/rankings"
    try:
        resp = requests.get(url, headers=headers, params={"period": period}, timeout=25)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            if data:
                copiers = data.get("copiers", 0)
                print(f"✓ Fetched live eToro rankings for {username}: {copiers} copiers, Risk Score {data.get('riskScore')}, AUM ${data.get('aumValue', 0):,}")
            return data
        return None
    except Exception as e:
        print(f"⚠️ Error fetching trader rankings from eToro API: {e}")
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


def get_post_metrics(post_id: str, exclude_author: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch engagement metrics (likes, comments, content) for a specific eToro post.
    Filters out author self-likes and automated author comments if exclude_author is True.
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
            post_owner = data.get("post", {}).get("owner", {})
            my_username = (post_owner.get("username") or "AndreaRavalli").lower()
            my_user_id = str(post_owner.get("id") or "8029424")

            # 1. External Likes (exclude author's own like)
            emotions_data = data.get("emotionsData", {})
            like_data = emotions_data.get("like", {})
            emotions_list = like_data.get("emotions", [])

            if exclude_author and emotions_list:
                external_likes = [
                    e for e in emotions_list
                    if e.get("owner", {}).get("username", "").lower() != my_username
                    and str(e.get("owner", {}).get("id")) != my_user_id
                ]
                likes = len(external_likes)
            else:
                likes = like_data.get("paging", {}).get("totalCount", len(emotions_list))

            # 2. External Comments (exclude author's own/bot comments)
            comments = 0
            try:
                c_url = f"{BASE_URL}/api/v1/posts/{post_id}/comments"
                c_resp = requests.get(c_url, headers=headers, timeout=10)
                if c_resp.status_code == 200:
                    c_data = c_resp.json()
                    c_list = c_data.get("comments", [])
                    if exclude_author:
                        external_comments = [
                            c for c in c_list
                            if c.get("entity", {}).get("owner", {}).get("username", "").lower() != my_username
                            and str(c.get("entity", {}).get("owner", {}).get("id")) != my_user_id
                            and not c.get("requesterContext", {}).get("isOwner", False)
                        ]
                        comments = len(external_comments)
                    else:
                        comments = len(c_list)
                else:
                    comments = 0
            except Exception:
                comments = 0

            summary = data.get("summary", {})
            shares = summary.get("sharedCount", 0)
            return {
                "id": data.get("id"),
                "created": data.get("created"),
                "likes": likes,
                "comments": comments,
                "shares": shares,
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


def create_poll_post(
    message: str,
    poll_title: str,
    poll_options: List[str],
    language: str = "it",
    market_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Create an interactive Poll post on eToro Social Feed via POST /api/v1/posts/polls.
    `poll_options` must have between 2 and 4 options.
    """
    headers = get_headers()
    if not headers:
        return {"success": False, "error": "eToro API not configured"}

    headers["Content-Type"] = "application/json"
    url = f"{BASE_URL}/api/v1/posts/polls"

    opts = [{"index": idx + 1, "text": opt[:28].strip()} for idx, opt in enumerate(poll_options[:4])]
    body: Dict[str, Any] = {
        "message": message[:1000],
        "poll": {
            "title": poll_title[:200],
            "options": opts,
        }
    }
    if market_ids:
        body["marketIds"] = market_ids

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code in (200, 201):
            data = resp.json()
            post_id = data.get("id")
            print(f"✅ Successfully created Poll on eToro! Post ID: {post_id}")
            return {"success": True, "id": post_id, "data": data}
        else:
            print(f"❌ Failed to create poll (HTTP {resp.status_code}): {resp.text}")
            return {"success": False, "status_code": resp.status_code, "error": resp.text}
    except Exception as e:
        print(f"❌ Exception creating poll on eToro: {e}")
        return {"success": False, "error": str(e)}


def like_comment(post_id: str, comment_id: str) -> bool:
    """
    Like a user comment on a post via POST /api/v1/posts/{postId}/comments/{commentId}/likes.
    """
    headers = get_headers()
    if not headers:
        return False
    url = f"{BASE_URL}/api/v1/posts/{post_id}/comments/{comment_id}/likes"
    try:
        resp = requests.post(url, headers=headers, timeout=15)
        return resp.status_code in (200, 201, 204)
    except Exception as e:
        print(f"⚠️ Error liking comment {comment_id}: {e}")
        return False


def like_post(post_id: str) -> bool:
    """
    Like a post via POST /api/v1/posts/{postId}/likes.
    """
    headers = get_headers()
    if not headers:
        return False
    url = f"{BASE_URL}/api/v1/posts/{post_id}/likes"
    try:
        resp = requests.post(url, headers=headers, timeout=15)
        return resp.status_code in (200, 201, 204)
    except Exception as e:
        print(f"⚠️ Error liking post {post_id}: {e}")
        return False


def get_post_comments(post_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all comments on a specific post via GET /api/v1/posts/{postId}/comments.
    """
    headers = get_headers()
    if not headers:
        return []
    url = f"{BASE_URL}/api/v1/posts/{post_id}/comments"
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("comments", []) if isinstance(data, dict) else []
        return []
    except Exception as e:
        print(f"⚠️ Error fetching comments for post {post_id}: {e}")
        return []


def reply_to_comment(post_id: str, comment_id: str, message: str, language: str = "it") -> Dict[str, Any]:
    """
    Reply to a specific comment on an eToro post via POST /api/v1/posts/{postId}/comments/{commentId}/replies.
    """
    headers = get_headers()
    if not headers:
        return {"success": False, "error": "eToro API not configured"}
    headers["Content-Type"] = "application/json"
    url = f"{BASE_URL}/api/v1/posts/{post_id}/comments/{comment_id}/replies"
    body = {"message": message, "language": language}
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=20)
        if resp.status_code in (200, 201):
            data = resp.json()
            return {"success": True, "id": data.get("id"), "data": data}
        return {"success": False, "status_code": resp.status_code, "error": resp.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_comment_replies(post_id: str, comment_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all replies for a specific comment via GET /api/v1/posts/{postId}/comments/{commentId}/replies.
    """
    headers = get_headers()
    if not headers:
        return []
    url = f"{BASE_URL}/api/v1/posts/{post_id}/comments/{comment_id}/replies"
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                return data.get("replies", []) or data.get("comments", []) or []
            elif isinstance(data, list):
                return data
        return []
    except Exception as e:
        print(f"⚠️ Error fetching replies for comment {comment_id}: {e}")
        return []


def delete_comment_reply(post_id: str, comment_id: str, reply_id: str) -> bool:
    """
    Delete a specific reply from a comment via DELETE /api/v1/posts/{postId}/comments/{commentId}/replies/{replyId}.
    """
    headers = get_headers()
    if not headers:
        return False
    url = f"{BASE_URL}/api/v1/posts/{post_id}/comments/{comment_id}/replies/{reply_id}"
    try:
        resp = requests.delete(url, headers=headers, timeout=15)
        if resp.status_code in (200, 204):
            print(f"🗑️ Successfully deleted duplicate reply {reply_id}")
            return True
        print(f"⚠️ Failed to delete reply {reply_id} (HTTP {resp.status_code}): {resp.text}")
        return False
    except Exception as e:
        print(f"⚠️ Error deleting reply {reply_id}: {e}")
        return False




