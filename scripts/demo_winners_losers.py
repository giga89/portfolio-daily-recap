#!/usr/bin/env python3
"""
Demo: generates 3 example Winners & Losers cards with hardcoded data.
Run from the repo root:
    python3 scripts/demo_winners_losers.py
Output: output/demo_wl_*.png
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from winners_losers_card import generate_winners_losers_card

EMOJIS = {
    "NVDA":      "🤖",
    "MSFT":      "💻",
    "LLY":       "💊",
    "PLTR":      "🛡️",
    "ENI.MI":    "⛽",
    "VOW3.DE":   "🚗",
    "GLEN.L":    "⛏️",
    "HUM":       "🏥",
    "ABBV":      "💉",
    "NOVO-B.CO": "💉",
    "GOOG":      "🔍",
    "AMZN":      "📦",
    "AZN.L":     "🧬",
    "TSM":       "🏭",
    "CCJ":       "⚡",
    "RACE":      "🏎️",
    "AVGO":      "💻",
    "MELI":      "🛒",
    "ENEL.MI":   "🔋",
    "IB01.L":    "💵",
}

EXAMPLES = [
    {
        "filename": "output/demo_wl_positive_day.png",
        "session":  "U.S. market close",
        "winner":   {"ticker": "NVDA",   "company_name": "NVIDIA",            "change": +4.82},
        "loser":    {"ticker": "ENI.MI", "company_name": "Eni S.p.A.",         "change": -2.31},
    },
    {
        "filename": "output/demo_wl_tough_day.png",
        "session":  "U.S. market close",
        "winner":   {"ticker": "IB01.L", "company_name": "iShares Treasury 0-1yr", "change": +0.08},
        "loser":    {"ticker": "PLTR",   "company_name": "Palantir Technologies",   "change": -5.70},
    },
    {
        "filename": "output/demo_wl_weekly.png",
        "session":  "Weekly recap (Sat)",
        "winner":   {"ticker": "LLY",     "company_name": "Eli Lilly & Co",   "change": +7.34},
        "loser":    {"ticker": "VOW3.DE", "company_name": "Volkswagen",        "change": -3.88},
    },
]

os.makedirs("output", exist_ok=True)

for ex in EXAMPLES:
    print(f"\n=== Generating: {ex['filename']} ===")
    path = generate_winners_losers_card(
        winner=ex["winner"],
        loser=ex["loser"],
        session_name=ex["session"],
        emoji_map=EMOJIS,
        output_path=ex["filename"],
        fetch_logos=True,
    )
    print(f"  → {path}")

print("\nDone! Open output/demo_wl_*.png to preview.")
