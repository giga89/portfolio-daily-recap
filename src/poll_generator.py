#!/usr/bin/env python3
"""
Interactive Poll Generator for eToro Social Feed
================================================
Generates and publishes highly engaging 1-click community polls directly to eToro.
Polls dramatically increase interaction, algorithmic reach, and profile views.
"""

import os
import sys
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load local .env if available
if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')):
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

import etoro_client
import gist_storage
import analytics_tracker
from etoro_sender import _strip_html


POLL_TEMPLATES = [
    {
        "id": "megatrend_h2",
        "title": "Quale megatrend guiderà le performance nei prossimi 6-12 mesi? 🚀",
        "options": [
            "AI & Supercomputing ($NVDA, $PLTR)",
            "Sanità & GLP-1 ($LLY, $NOVO)",
            "Energia Nucleare & Grid ($CCJ, $PRY)",
            "Dividendi & Oro ($WDEF, $PPFB)",
        ],
        "tickers": ["NVDA", "PLTR", "LLY", "CCJ"],
        "message": (
            "🗳️ SONDAGGIO COMMUNITY: PROSPETTIVE SUI MEGATREND GLOBALI\n\n"
            "Nel nostro portafoglio bilanciamo crescita esponenziale (AI & Semiconduttori) con pilastri difensivi e generazione di cassa (Sanità, Energia, Oro ed ETF).\n\n"
            "Secondo voi, quale tra questi settori offrirà il miglior rapporto rendimento/rischio nei prossimi trimestri?\n\n"
            "Votate qui sotto e lasciate un commento con la vostra motivazione! 👇"
        )
    },
    {
        "id": "ai_valuation_debate",
        "title": "Come valutate l'attuale fase dell'Intelligenza Artificiale? 🤖",
        "options": [
            "Primi stadi: ancora forte upside",
            "Fase matura: selezionare i leader",
            "Valutazioni eccessivamente tirate",
            "Preferisco diversificare su ETF",
        ],
        "tickers": ["PLTR", "NVDA", "TSM", "MSFT"],
        "message": (
            "🗳️ SONDAGGIO: IL FUTURO DELL'ECOSISTEMA AI & SOFTWARE\n\n"
            "Tra contratti enterprise, chip Blackwell e modelli multimodali, l'AI rimane il traino principale del mercato azionario.\n\n"
            "Come vi state posizionando sui titoli tech ($NVDA, $PLTR, $TSM, $MSFT)?\n\n"
            "Votate il sondaggio con 1 tap! 👇"
        )
    },
    {
        "id": "risk_management_choice",
        "title": "Qual è la vostra priorità principale nel portafoglio oggi? ⚖️",
        "options": [
            "Massima crescita (High Beta/Tech)",
            "Crescita con basso rischio (Risk Score < 4)",
            "Rendimento da dividendi costanti",
            "Accumulo liquidità per storni",
        ],
        "tickers": ["PLTR", "LLY", "SX7PEX.DE", "WDEF.L"],
        "message": (
            "🗳️ SONDAGGIO: GESTIONE DEL RISCHIO E ASSET ALLOCATION\n\n"
            "La nostra strategia mantiene un Risk Score eToro certificato di 3/10 con zero leva finanziaria e +195% di performance cumulata dal 2020.\n\n"
            "Qual è il vostro approccio attuale al rapporto rischio/rendimento sui mercati?\n\n"
            "Dite la vostra nel sondaggio qui sotto! 👇"
        )
    },
    {
        "id": "pltr_conviction",
        "title": "Palantir ($PLTR): Quale target vi aspettate a medio termine? 🛡️",
        "options": [
            "Forte rialzo (AIP leader enterprise)",
            "Consolidamento sui livelli attuali",
            "Possibile correzione tecnica",
            "Non seguo / preferisco altri titoli",
        ],
        "tickers": ["PLTR", "NVDA"],
        "message": (
            "🗳️ SONDAGGIO DEL GIORNO: FOCUS SU $PLTR\n\n"
            "Palantir si conferma uno dei titoli chiave del nostro portafoglio, spinto dalla continua espansione dei contratti commerciali AIP e margini operativi solidissimi.\n\n"
            "Qual è la vostra previsione sul titolo nei prossimi mesi?\n\n"
            "Votate l'opzione che rispecchia la vostra analisi! 👇"
        )
    }
]


def publish_etoro_poll(
    poll_id: Optional[str] = None,
    custom_title: Optional[str] = None,
    custom_options: Optional[List[str]] = None,
    custom_message: Optional[str] = None,
    custom_tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Publish an interactive poll to eToro Social Feed.
    """
    print("=" * 65)
    print("🗳️ PUBLISHING INTERACTIVE POLL TO ETORO SOCIAL FEED")
    print(f"🕒 Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 65)

    if not etoro_client.is_configured():
        print("❌ eToro API credentials not configured.")
        return {"success": False, "error": "eToro API not configured"}

    # Select template or use custom inputs
    selected = None
    if poll_id:
        for t in POLL_TEMPLATES:
            if t["id"] == poll_id:
                selected = t
                break

    if not selected:
        selected = random.choice(POLL_TEMPLATES)

    title = custom_title or selected["title"]
    options = custom_options or selected["options"]
    message = custom_message or selected["message"]
    tickers = custom_tickers or selected["tickers"]

    market_ids = etoro_client.get_market_ids_for_tickers(tickers)
    print(f"📌 Poll Title: {title}")
    print(f"📌 Options ({len(options)}): {options}")
    print(f"🏷️ Tagged Markets: {tickers} -> IDs {market_ids}")

    # Create poll via official eToro API
    res = etoro_client.create_poll_post(
        message=message,
        poll_title=title,
        poll_options=options,
        language="it",
        market_ids=market_ids if market_ids else None,
    )

    if res.get("success"):
        post_id = res.get("id")
        print(f"🎉 Poll published successfully on eToro! Post ID: {post_id}")
        
        # Save last eToro post metadata for analytics and delayed engagement
        try:
            gist_storage.save_last_etoro_post(
                post_id=post_id,
                session_name="Community Poll",
                tickers=tickers,
                market_data_summary={"is_poll": True, "title": title}
            )
        except Exception as e:
            print(f"⚠️ Gist save warning: {e}")

        try:
            analytics_tracker.record_post(
                platform="etoro",
                post_id=post_id,
                session_name="Community Poll",
                text=f"{title}\n\n{message}",
                image_type="poll",
                tickers=tickers,
            )
            analytics_tracker.update_and_build_dashboard()
        except Exception as e:
            print(f"⚠️ Analytics recording warning: {e}")

        return {
            "success": True,
            "post_id": post_id,
            "title": title,
            "options": options,
        }
    else:
        print(f"❌ Failed to publish poll on eToro: {res.get('error')}")
        return {
            "success": False,
            "error": res.get("error"),
            "status_code": res.get("status_code"),
        }


if __name__ == "__main__":
    p_id = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    publish_etoro_poll(poll_id=p_id)
