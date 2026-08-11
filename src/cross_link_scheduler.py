#!/usr/bin/env python3
"""
Cross-Link Comments Scheduler for eToro
=======================================
Publishes 3 curated cross-link comments spaced 10 minutes apart on a target eToro post:
  • Comment 1: Tech & AI Leaders ($PLTR, $NVDA, $MSFT)
  • Comment 2: Nuclear Energy & Value ($CCJ, $URNM, $SX7PEX.DE)
  • Comment 3: Healthcare & Global Growth ($LLY, $NOVO-B.CO, $MELI)
"""

import os
import sys
import time
from datetime import datetime

# Load local .env if available
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')):
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

import etoro_client
from etoro_sender import _strip_html

COMMENTS_SEQUENCE = [
    {
        "name": "Tech & AI Leaders",
        "text": """💡 1/3 FOCUS TECH & AI LEADERS 🤖
Per chi vuole approfondire i titoli tecnologici e di intelligenza artificiale del portafoglio:

1️⃣ $PLTR · Palantir Technologies
   ↳ Leader nel software AI per difesa e forte crescita commerciale con AIP.

2️⃣ $NVDA · NVIDIA Corporation
   ↳ Monopolio datacenter e GPU acceleratrici con architettura Blackwell.

3️⃣ $MSFT · Microsoft
   ↳ Integrazione strategica di OpenAI su Azure e suite enterprise.

👉 Trovi tutti i dettagli e le tesi complete sul mio profilo @AndreaRavalli! 🎯"""
    },
    {
        "name": "Nuclear Energy & Strategic Value",
        "text": """⚡ 2/3 FOCUS ENERGIA NUCLEARE & VALORE 🌍
Ecco gli approfondimenti sui settori strategici e di transizione energetica in portafoglio:

1️⃣ $CCJ · Cameco Corporation
   ↳ Deficit strutturale di offerta globale di uranio per i reattori nucleari.

2️⃣ $URNM · Sprott Uranium Miners ETF
   ↳ Esposizione bilanciata ai principali produttori e detentori fisici di uranio.

3️⃣ $SX7PEX.DE · STOXX Europe 600 Banks ETF
   ↳ Cash flow elevati, solidità patrimoniale e dividendi costanti.

👉 Condividi la tua opinione nei commenti o segui il portafoglio su eToro! 🚀"""
    },
    {
        "name": "Healthcare & Global Megatrends",
        "text": """🏥 3/3 FOCUS HEALTHCARE & E-COMMERCE GLOBALE 💊
I pilastri difensivi e a forte crescita globale:

1️⃣ $LLY · Eli Lilly
   ↳ Leadership mondiale nei trattamenti metabolici e GLP-1 (Mounjaro).

2️⃣ $NOVO-B.CO · Novo Nordisk
   ↳ Pioniere nel settore diabete e obesità con Ozempic e Wegovy.

3️⃣ $MELI · MercadoLibre
   ↳ Il gigante indiscusso dell'e-commerce e fintech in America Latina.

💬 Quale di questi titoli preferisci per il lungo termine? Lascia un commento qui sotto! 👇"""
    }
]


def run_comments_sequence(post_id: str, interval_seconds: int = 600):
    """
    Publish all 3 comments spaced by `interval_seconds` (default 600s = 10 minutes).
    """
    print("=" * 60)
    print(f"🚀 STARTING 3-COMMENT CROSSLINKING SEQUENCE ON POST: {post_id}")
    print(f"⏱️ Interval between comments: {interval_seconds}s ({interval_seconds // 60} minutes)")
    print("=" * 60)

    if not etoro_client.is_configured():
        print("❌ eToro API not configured. Exiting.")
        return

    for idx, c in enumerate(COMMENTS_SEQUENCE, 1):
        clean_msg = _strip_html(c["text"])
        print(f"\n[{datetime.utcnow().strftime('%H:%M:%S UTC')}] 💬 Publishing Comment {idx}/3 ({c['name']})...")
        
        res = etoro_client.add_post_comment(
            post_id=post_id,
            message=clean_msg,
            language="it"
        )
        
        if res.get("success"):
            print(f"✅ Comment {idx} posted successfully! ID: {res.get('id')}")
        else:
            print(f"❌ Comment {idx} failed: {res.get('error')}")

        if idx < len(COMMENTS_SEQUENCE):
            print(f"⏳ Waiting {interval_seconds // 60} minutes before next comment...")
            time.sleep(interval_seconds)

    print("\n" + "=" * 60)
    print("🎉 ALL 3 CROSSLINKING COMMENTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    target_post = sys.argv[1] if len(sys.argv) > 1 else "41f4c7dc-402a-4ce6-a7fe-49b819f074d2"
    delay = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    run_comments_sequence(target_post, delay)
