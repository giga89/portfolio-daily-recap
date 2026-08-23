#!/usr/bin/env python3
"""
LinkedIn Sender
Posts the WEEKLY portfolio recap to LinkedIn as a professional article-style post.

Supports:
  - Personal profile posts (UGC Share API)
  - Company page posts (if LINKEDIN_COMPANY_ID is set)

Setup:
  1. Go to https://www.linkedin.com/developers/apps/new
  2. Create an app (no business verification required for personal posts)
  3. Add products: "Share on LinkedIn" and optionally "Marketing Developer Platform"
  4. Under "Auth" tab, generate an OAuth 2.0 token with scopes:
       w_member_social   (post on behalf of user)
       r_liteprofile     (read user ID)
  5. Use the token generator or implement OAuth flow

Required env vars:
  LINKEDIN_ACCESS_TOKEN — OAuth 2.0 user access token
  LINKEDIN_PERSON_URN   — your LinkedIn person URN, e.g. "urn:li:person:ABC123"
                          (get it via GET https://api.linkedin.com/v2/me)

Optional:
  LINKEDIN_COMPANY_ID   — if set, posts to Company Page instead of personal profile
"""

import os
import requests


LI_API = "https://api.linkedin.com/v2"


def _get_person_urn(token: str) -> str | None:
    """Fetch the LinkedIn person URN from the API."""
    r = requests.get(
        f"{LI_API}/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.ok:
        uid = r.json().get("id")
        urn = f"urn:li:person:{uid}"
        print(f"   ✅ LinkedIn Person URN: {urn}")
        return urn
    print(f"   ❌ Could not fetch LinkedIn person ID: {r.text[:200]}")
    return None


def _format_professional_post(plain_text: str, weekly_stats: dict = None) -> str:
    """
    Format the recap into a professional LinkedIn post style.
    LinkedIn: max 3,000 chars for personal posts, 700 for company pages.
    Uses clean formatting without excessive emojis.
    """
    # Keep a more professional tone for LinkedIn
    import re

    # Strip emoji clusters (keep max 1 per line, remove excessive repetition)
    def clean_emojis(line: str) -> str:
        # Remove repeated emojis (e.g. "✅ ✅ ✅" → "✅")
        return re.sub(r"([\U00010000-\U0010ffff])\s*\1+", r"\1", line)

    lines = plain_text.splitlines()
    cleaned_lines = [clean_emojis(line) for line in lines]
    body = "\n".join(cleaned_lines).strip()

    # Add LinkedIn-specific professional header
    header = "📊 WEEKLY PORTFOLIO RECAP\n" + "─" * 30 + "\n\n"

    # Add professional footer
    footer = (
        "\n\n" + "─" * 30 + "\n"
        "Questo portfolio è gestito su eToro con una strategia "
        "diversificata su megatrend globali (AI, Sanità ed Energia).\n\n"
        "🌐 Hub & Analisi Dettagliata (Dividendi, Rischio, Simulatore DCA):\n"
        "https://giga89.github.io/portfolio-daily-recap/\n\n"
        "🔗 Segui e copia il portfolio: https://www.etoro.com/people/andrearavalli\n"
        "📩 Iscriviti ad eToro: https://etoro.tw/46qgHLr\n\n"
        "#Portfolio #Investimenti #ETF #eToro #FinanzaPersonale #Mercati"
    )

    full_post = header + body + footer

    # LinkedIn personal post limit: 3000 chars
    if len(full_post) > 2900:
        available = 2900 - len(header) - len(footer)
        body = body[:available - 3] + "..."
        full_post = header + body + footer

    return full_post


def send_linkedin_post(text: str, weekly_stats: dict = None) -> bool:
    """
    Post a professional weekly recap to LinkedIn.

    Args:
        text: Plain text recap (HTML will be stripped)
        weekly_stats: Optional dict with additional weekly data

    Returns:
        bool: True if successful
    """
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.environ.get("LINKEDIN_PERSON_URN")
    company_id = os.environ.get("LINKEDIN_COMPANY_ID")

    print("=" * 50)
    print("💼 Posting to LinkedIn...")
    print(f"   Token present: {bool(token)}")
    print(f"   Person URN present: {bool(person_urn)}")

    if not token:
        print("   ⚠️  LINKEDIN_ACCESS_TOKEN not set — skipping.")
        return False

    # Auto-fetch Person URN if not set
    if not person_urn:
        person_urn = _get_person_urn(token)
        if not person_urn:
            return False

    # Use company page if configured, otherwise personal profile
    if company_id:
        author = f"urn:li:organization:{company_id}"
        print(f"   📄 Posting to Company Page: {company_id}")
    else:
        author = person_urn
        print(f"   👤 Posting to Personal Profile: {person_urn}")

    formatted_text = _format_professional_post(text, weekly_stats)
    print(f"   📝 Post length: {len(formatted_text)} chars")

    # UGC Share API payload
    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": formatted_text
                },
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    try:
        r = requests.post(
            f"{LI_API}/ugcPosts",
            headers=headers,
            json=payload,
            timeout=15,
        )
        print(f"   Response status: {r.status_code}")

        if r.ok:
            post_id = r.headers.get("x-restli-id") or r.json().get("id", "")
            print(f"   ✅ LinkedIn post published! ID: {post_id}")
            return True
        else:
            print(f"   ❌ LinkedIn error: {r.text[:400]}")
            return False
    except Exception as e:
        print(f"   ❌ LinkedIn exception: {e}")
        return False
