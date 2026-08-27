#!/usr/bin/env python3
"""
Financial Meme Card Generator — eToro 16:9 Landscape & 1:1 Adaptive Studio
Generates high-engagement, sentiment-matched finance memes for market recap sessions.
Matches market conditions (Bull Extreme, Bull Steady, Sideways, Bear Dip, Bear Crash, Weekend)
with iconic meme templates and dynamic 16:9 landscape framing (1280x720) optimized for eToro,
Twitter/X, Bluesky, Telegram, and LinkedIn without stretching.
"""

import os
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageStat

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMES_DIR = os.path.join(REPO_ROOT, "assets", "memes")
OUTPUT_DIR = os.path.join(REPO_ROOT, "src", "output")
FONTS_DIR = os.path.join(REPO_ROOT, "assets", "fonts")
PROFILE_PHOTO_PATH = os.path.join(REPO_ROOT, "assets", "profile_photo.jpg")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MEMES_DIR, exist_ok=True)

# ── Font Helper ─────────────────────────────────────────────────────────────
def _get_font(size: int, bold: bool = True):
    font_candidates = [
        os.path.join(FONTS_DIR, "Inter-Bold.ttf"),
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ── Meme Scenarios Library ──────────────────────────────────────────────────
MEME_CATALOG = {
    "BULL_EXTREME": [
        {
            "template": "gatsby_cheers.jpg",
            "title": "🥂 CHEERS TO THE BULLS!",
            "top_text": "QUANDO $PLTR E I TECH COMPOUNDER",
            "bottom_text": "GUIDANO IL PORTAFOGLIO A NUOVI MASSIMI 🚀",
            "en_top": "WHEN THE AI & TECH COMPOUNDERS",
            "en_bottom": "CARRY THE ENTIRE PORTFOLIO TO THE MOON 🥂🚀",
            "mood_emoji": "🔥",
            "badge_color": "#10B981"
        },
        {
            "template": "stonks.jpg",
            "title": "📈 STONKS ONLY GO UP",
            "top_text": "CHI FA TRADING A LEVA: LIQUIDATO",
            "bottom_text": "NOI CON 100% AZIONI REALI E RISK 3/10: 📈 STONKS",
            "en_top": "20X LEVERAGE TRADERS: LIQUIDATED",
            "en_bottom": "US WITH 100% REAL ASSETS & RISK SCORE 3/10: 📈 STONKS",
            "mood_emoji": "🚀",
            "badge_color": "#10B981"
        },
        {
            "template": "disaster_girl.jpg",
            "title": "🔥 SHORTS GETTING BURNED",
            "top_text": "I BEAR CHE PREVEDEVANO IL CRASH IMMINENTE",
            "bottom_text": "NOI CHE INCASSIAMO UN ALTRO GREEN DAY 🍀",
            "en_top": "DOOMERS PREDICTING A MARKET CRASH",
            "en_bottom": "US ENJOYING ANOTHER MASSIVE GREEN DAY 🍀🔥",
            "mood_emoji": "😈",
            "badge_color": "#10B981"
        }
    ],
    "BULL_STEADY": [
        {
            "template": "honest_work.png",
            "title": "🌾 HONEST COMPOUNDING",
            "top_text": "+0.75% OGGI. NIENTE LEVE FOLLI 50X",
            "bottom_text": "SOLO 100% AZIONI REALI, DIVIDENDI E COMPOUNDING 🌾",
            "en_top": "+0.75% TODAY. NO CRAZY 50X LEVERAGE",
            "en_bottom": "IT AIN'T MUCH, BUT IT'S HONEST COMPOUND WORK 🌾",
            "mood_emoji": "🌾",
            "badge_color": "#10B981"
        },
        {
            "template": "two_bus_passengers.jpg",
            "title": "🚌 DUE MODI DI VIVERE LA GIORNATA",
            "top_text": "CHI GUARDA IL GRAFICO AD 1 MINUTO CON ANSIA",
            "bottom_text": "CHI FA COPY TRADING A BASSO RISCHIO E DORME SERENO",
            "en_top": "DAY TRADERS STRESSED OVER 1-MIN CANDLES",
            "en_bottom": "LONG-TERM COPY TRADERS ENJOYING THE RIDE WITH 3/10 RISK",
            "mood_emoji": "🌿",
            "badge_color": "#10B981"
        },
        {
            "template": "epic_handshake.jpg",
            "title": "🤝 THE PERFECT ALLIANCE",
            "top_text": "CRESCITA TECNOLOGICA (AI & CHIPS)",
            "bottom_text": "DIVIDENDI SOLIDI & ZERO LEVA = COMPOUNDING 🌿",
            "en_top": "GROWTH MEGATRENDS (AI & TECH)",
            "en_bottom": "CASH FLOW & 0% LEVERAGE = LONG TERM COMPOUNDING 🤝",
            "mood_emoji": "🤝",
            "badge_color": "#06B6D4"
        },
        {
            "template": "expanding_brain.jpg",
            "title": "🧠 INVESTING EVOLUTION",
            "top_text": "INSEGUIRE LE MEME COIN CON LEVA 50X",
            "bottom_text": "COPIARE UN PORTAFOGLIO +200% DAL 2020 SENZA STRESS",
            "en_top": "CHASING RANDOM PENNY STOCKS",
            "en_bottom": "1-CLICK COPYING A +200% TRACK RECORD WITH 3/10 RISK 🧠",
            "mood_emoji": "💡",
            "badge_color": "#8B5CF6"
        },
        {
            "template": "change_my_mind.jpg",
            "title": "☕ CHANGE MY MIND",
            "top_text": "IL COPY TRADING SU AZIONI REALI A BASSO RISCHIO",
            "bottom_text": "BATTE IL 90% DEL TRADING FAI-DA-TE. CHANGE MY MIND. ☕",
            "en_top": "DISCIPLINED LOW-RISK COPY TRADING",
            "en_bottom": "BEATS 90% OF EMOTIONAL DAY TRADING. CHANGE MY MIND. ☕",
            "mood_emoji": "☕",
            "badge_color": "#38BDF8"
        }
    ],
    "SIDEWAYS": [
        {
            "template": "trade_offer.jpg",
            "title": "🤝 TRADE OFFER",
            "top_text": "IO RICEVO: VOLATILITÀ QUASI ZERO",
            "bottom_text": "TU RICEVI: DIVIDENDI ACCUMULATI E TEMPO LIBERO",
            "en_top": "I RECEIVE: FLAT MARKET ACTION",
            "en_bottom": "YOU RECEIVE: SOLID DIVIDENDS & FREE TIME ⏳",
            "mood_emoji": "⚖️",
            "badge_color": "#38BDF8"
        },
        {
            "template": "waiting_skeleton.jpg",
            "title": "⏳ WAITING FOR THE DIP",
            "top_text": "IO CHE ASPETTO CHE IL MERCATO CROLLI",
            "bottom_text": "PERCHÉ 'I GURU HANNO DETTO CHE È TROPPO CARO'",
            "en_top": "WAITING FOR THE BIG CRASH",
            "en_bottom": "BECAUSE 'EXPERTS SAID MARKET IS AT THE TOP' SINCE 2022 ⏳",
            "mood_emoji": "💀",
            "badge_color": "#64748B"
        },
        {
            "template": "two_buttons.jpg",
            "title": "🔴 TOUGH CHOICE",
            "top_text": "COMPRARE ALTRE AZIONI REAL ESTATE & ENERGIA",
            "bottom_text": "O RAFFORZARE I COMPOUNDER TECH SULLA PARITÀ? 🤔",
            "en_top": "ADD MORE DIVIDEND DIVIDENDS",
            "en_bottom": "OR ACCUMULATE CORE TECH LEADERS ON FLAT DAYS? 🤔",
            "mood_emoji": "🤔",
            "badge_color": "#F59E0B"
        },
        {
            "template": "distracted_boyfriend.jpg",
            "title": "👀 DISTRACTED BY COMPOUNDERS",
            "top_text": "TRADING SPECULATIVO E LEVE PAZZE",
            "bottom_text": "NOI: PORTAFOGLIO MULTI-ASSET DIVERSIFICATO 👀",
            "en_top": "HIGH RISK PENNY STOCKS & 20X LEVERAGE",
            "en_bottom": "US: QUALITY MULTI-ASSET COMPOUNDERS 👀",
            "mood_emoji": "👀",
            "badge_color": "#EC4899"
        }
    ],
    "BEAR_DIP": [
        {
            "template": "this_is_fine.jpg",
            "title": "☕ THIS IS FINE",
            "top_text": "IL MERCATO RITRACCIA DEL -0.9%",
            "bottom_text": "NOI CON ZERO LEVA E CASSA PRONTA PER IL DIP ☕",
            "en_top": "MARKET DIPS -0.9% TODAY",
            "en_bottom": "US CHILLING WITH ZERO LEVERAGE & CASH READY ☕",
            "mood_emoji": "☕",
            "badge_color": "#EF4444"
        },
        {
            "template": "woman_yelling_cat.jpg",
            "title": "😼 CALM AS A CAT",
            "top_text": "I TRADER A LEVA CHE VANNO IN PANICO",
            "bottom_text": "NOI SERENI CON ZERO LEVA E RISK SCORE 3/10 😼",
            "en_top": "LEVERAGE TRADERS PANICKING OVER MINOR PULLBACKS",
            "en_bottom": "US CHILLING WITH ZERO LEVERAGE & 3/10 RISK 😼",
            "mood_emoji": "😼",
            "badge_color": "#F59E0B"
        },
        {
            "template": "clown_makeup.jpg",
            "title": "🎪 THE TIMING CYCLE",
            "top_text": "1. Compro il dip · 2. Scende ancora",
            "bottom_text": "3. Vendo sul panico · 4. Rimbalzo +4% il giorno dopo 🤡",
            "en_top": "1. Buy the dip · 2. It dips more",
            "en_bottom": "3. Panic sell the bottom · 4. +4% rally the next morning 🤡",
            "mood_emoji": "🎪",
            "badge_color": "#F59E0B"
        },
        {
            "template": "uno_draw_25.jpg",
            "title": "🃏 UNO DRAW 25",
            "top_text": "VENDERE SUL PANICO PER UN DIP DEL -1%",
            "bottom_text": "OPPURE PESCARE 25 CARTE E MANTENERE IL RISK 3/10 🃏",
            "en_top": "PANIC SELL AT THE FIRST -1% MARKET PULLBACK",
            "en_bottom": "OR DRAW 25 AND STICK TO DISCIPLINED 3/10 RISK 🃏",
            "mood_emoji": "🃏",
            "badge_color": "#EF4444"
        }
    ],
    "BEAR_CRASH": [
        {
            "template": "this_is_fine.jpg",
            "title": "☕ THIS IS FINE (EXTREME)",
            "top_text": "QUANDO TUTTO IL MERCATO È PROFONDAMENTE ROSSO",
            "bottom_text": "MA LA TUA TESI D'INVESTIMENTO A 5 ANNI È INVIOLATA ☕",
            "en_top": "WHEN THE ENTIRE MARKET IS BURNING RED",
            "en_bottom": "BUT YOUR 5-YEAR MULTI-ASSET THESIS REMAINS BULLETPROOF ☕🔥",
            "mood_emoji": "☕",
            "badge_color": "#DC2626"
        },
        {
            "template": "drowning_kid.jpg",
            "title": "🏊‍♂️ MARKET LIQUIDITY",
            "top_text": "IL MERCATO CHE SOSTIENE SOLO IL MOMENTUM",
            "bottom_text": "I SOLIDI COMPOUNDER A SCONTO CHE ASPETTANO IL REBOUND 🏊‍♂️",
            "en_top": "HYPED MOMENTUM STOCKS CRASHING HARD",
            "en_bottom": "SOLID CASH-FLOW LEADERS QUIETLY ACCUMULATING 🏊‍♂️",
            "mood_emoji": "🏊‍♂️",
            "badge_color": "#DC2626"
        },
        {
            "template": "pablo_escobar.jpg",
            "title": "🌧️ WAITING FOR THE REBOUND",
            "top_text": "IO CHE GUARDO IL PORTAFOGLIO OGGI",
            "bottom_text": "SAPENDO CHE DAL 2020 ABBIAMO SUPERATO OGNI TEMPESTA (+200%)",
            "en_top": "LOOKING AT RED CHARTS TODAY",
            "en_bottom": "KNOWING WE'VE COMPOUNDED +200% THROUGH EVERY STORM SINCE 2020",
            "mood_emoji": "🌧️",
            "badge_color": "#EF4444"
        }
    ],
    "WEEKEND": [
        {
            "template": "pablo_escobar.jpg",
            "title": "🛋️ WEEKEND MOOD",
            "top_text": "IO IL SABATO E LA DOMENICA",
            "bottom_text": "ASPETTANDO CHE RIAPRA WALL STREET LUNEDÌ ALLE 15:30",
            "en_top": "ME DURING THE WEEKEND",
            "en_bottom": "WAITING FOR WALL STREET TO REOPEN ON MONDAY",
            "mood_emoji": "🛋️",
            "badge_color": "#6366F1"
        }
    ]
}


def determine_sentiment(portfolio_daily: float, is_weekend: bool = False) -> str:
    """Classify market sentiment key based on daily performance."""
    if is_weekend:
        return "WEEKEND"
    if portfolio_daily >= 1.5:
        return "BULL_EXTREME"
    elif portfolio_daily >= 0.2:
        return "BULL_STEADY"
    elif portfolio_daily > -0.5:
        return "SIDEWAYS"
    elif portfolio_daily > -1.5:
        return "BEAR_DIP"
    else:
        return "BEAR_CRASH"


def generate_meme_card(
    portfolio_daily: float = 1.45,
    top_performers: list = None,
    lang: str = "it",
    is_weekend: bool = False,
    forced_template: str = None,
    aspect_ratio: str = "16:9"  # "16:9" (1280x720) or "1:1" (1080x1080)
) -> str:
    """
    Generate an eToro-native 16:9 Landscape (1280x720) or 1:1 Square meme card.
    The original meme image is NEVER stretched:
      • Analyzes average luminance and dominant tone of the meme image.
      • Generates a rich, blurred ambient depth backdrop matching the meme colors.
      • Places the un-stretched meme sharply inside a rounded studio frame with subtle drop shadow.
      • Header bar with dynamic glowing daily % pill + footer with ticker pills and verified branding.
    """
    sentiment = determine_sentiment(portfolio_daily, is_weekend)
    catalog = MEME_CATALOG.get(sentiment, MEME_CATALOG["BULL_STEADY"])

    if forced_template:
        meme_data = next((m for m in catalog if m["template"] == forced_template), catalog[0])
    else:
        meme_data = random.choice(catalog)

    template_file = meme_data["template"]
    template_path = os.path.join(MEMES_DIR, template_file)

    # ── Canvas Dimensions ────────────────────────────────────────────────────
    if aspect_ratio == "1:1":
        W, H = 1080, 1080
        header_h = 90
        footer_h = 95
        max_mw, max_mh = 920, 640
        top_font_size = 28
        bot_font_size = 26
    else:
        # Default eToro / Web Feed: 16:9 Landscape (1280x720)
        W, H = 1280, 720
        header_h = 74
        footer_h = 76
        max_mw, max_mh = 860, 410
        top_font_size = 25
        bot_font_size = 24

    # ── Load Base Meme Image & Analyze Luminance ─────────────────────────────
    meme_img = None
    is_light_meme = False
    if os.path.exists(template_path):
        try:
            meme_img = Image.open(template_path).convert("RGBA")
            stat = ImageStat.Stat(meme_img.convert("L"))
            is_light_meme = stat.mean[0] > 135
        except Exception as e:
            print(f"⚠️ Error loading meme template {template_path}: {e}")

    # ── Create Adaptive Studio Canvas ───────────────────────────────────────
    card = Image.new("RGBA", (W, H), (10, 15, 30, 255))

    if meme_img is not None:
        # Generate blurred ambient backdrop matching meme colors
        bg_blurred = meme_img.resize((W, H), Image.Resampling.BILINEAR)
        bg_blurred = bg_blurred.filter(ImageFilter.GaussianBlur(38))
        
        # Darken / Tint the blurred backdrop for contrast
        tint = Image.new("RGBA", (W, H), (10, 15, 30, 215) if not is_light_meme else (20, 28, 48, 190))
        bg_blurred.paste(tint, (0, 0), mask=tint)
        card.paste(bg_blurred, (0, 0))
    else:
        # Fallback dark studio gradient
        draw = ImageDraw.Draw(card)
        for y in range(H):
            t = y / H
            r = int(10 * (1 - t) + 15 * t)
            g = int(15 * (1 - t) + 23 * t)
            b = int(30 * (1 - t) + 42 * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    draw = ImageDraw.Draw(card)

    # ── Header Bar ──────────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (W, header_h)], fill=(12, 18, 36, 240))
    draw.line([(0, header_h), (W, header_h)], fill=(255, 255, 255, 30), width=1)

    f_title = _get_font(22, bold=True)
    f_badge = _get_font(20, bold=True)

    title_text = meme_data["title"]
    draw.text((28, (header_h - 26) // 2), title_text, font=f_title, fill="#FFFFFF")

    # Daily Return Pill Badge
    if is_weekend:
        pill_text = "WEEKEND RECAP"
        pill_bg = (99, 102, 241, 255)
    else:
        sign = "+" if portfolio_daily >= 0 else ""
        pill_text = f"{sign}{portfolio_daily:.2f}% {meme_data['mood_emoji']}"
        pill_bg = (16, 185, 129, 255) if portfolio_daily >= 0 else (239, 68, 68, 255)

    pill_w, pill_h = 170, 38
    pill_x, pill_y = W - pill_w - 28, (header_h - pill_h) // 2
    draw.rounded_rectangle([(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)], radius=19, fill=pill_bg)
    
    bbox = draw.textbbox((0, 0), pill_text, font=f_badge)
    tw = bbox[2] - bbox[0]
    draw.text((pill_x + (pill_w - tw) // 2, pill_y + 8), pill_text, font=f_badge, fill="#FFFFFF")

    # ── Center Content Area ─────────────────────────────────────────────────
    content_top = header_h + 12
    content_bottom = H - footer_h - 12

    # 1. Top Punchline Text
    top_text = meme_data["en_top"] if lang == "en" else meme_data["top_text"]
    f_meme_top = _get_font(top_font_size, bold=True)
    top_bbox = draw.textbbox((0, 0), top_text, font=f_meme_top)
    top_tw = top_bbox[2] - top_bbox[0]
    top_th = top_bbox[3] - top_bbox[1]
    
    top_y = content_top + 4
    draw.text(((W - top_tw) // 2, top_y), top_text, font=f_meme_top, fill="#00D4FF")

    # 2. Bottom Punchline Text
    bottom_text = meme_data["en_bottom"] if lang == "en" else meme_data["bottom_text"]
    f_meme_bot = _get_font(bot_font_size, bold=True)
    bot_bbox = draw.textbbox((0, 0), bottom_text, font=f_meme_bot)
    bot_tw = bot_bbox[2] - bot_bbox[0]
    bot_th = bot_bbox[3] - bot_bbox[1]
    bot_y = content_bottom - bot_th - 6
    draw.text(((W - bot_tw) // 2, bot_y), bottom_text, font=f_meme_bot, fill="#FACC15")

    # 3. Sharp Centered Meme Image (Preserving Exact Aspect Ratio)
    if meme_img is not None:
        avail_mh = bot_y - (top_y + top_th + 16) - 10
        avail_mw = max_mw

        scale = min(avail_mw / meme_img.width, avail_mh / meme_img.height)
        mw = int(meme_img.width * scale)
        mh = int(meme_img.height * scale)

        scaled_meme = meme_img.resize((mw, mh), Image.Resampling.LANCZOS)

        mx = (W - mw) // 2
        my = (top_y + top_th + 14) + (avail_mh - mh) // 2

        # Studio Card Frame with Drop Shadow
        shadow_box = [(mx - 6, my - 6), (mx + mw + 6, my + mh + 6)]
        draw.rounded_rectangle(shadow_box, radius=8, fill=(0, 0, 0, 160))

        # Paste un-stretched meme
        card.paste(scaled_meme, (mx, my), mask=scaled_meme)
        
        # Subtle glowing border
        border_color = (0, 212, 255, 120) if not is_light_meme else (255, 255, 255, 160)
        draw.rounded_rectangle([(mx, my), (mx + mw, my + mh)], radius=6, outline=border_color, width=2)

    # ── Footer Bar: Tickers & Branding ──────────────────────────────────────
    footer_y = H - footer_h
    draw.rectangle([(0, footer_y), (W, H)], fill=(12, 18, 36, 245))
    draw.line([(0, footer_y), (W, footer_y)], fill=(255, 255, 255, 25), width=1)

    # Left: Top Tickers Pills
    if top_performers:
        tx = 28
        f_ticker = _get_font(15, bold=True)
        pill_h_foot = 34
        pill_y_foot = footer_y + (footer_h - pill_h_foot) // 2
        for sym, pct in top_performers[:3]:
            arr = "▲" if pct >= 0 else "▼"
            t_str = f"{arr} ${sym} {pct:+.1f}%"
            t_col = (16, 185, 129) if pct >= 0 else (239, 68, 68)
            
            t_box = draw.textbbox((0, 0), t_str, font=f_ticker)
            t_w = t_box[2] - t_box[0] + 16
            
            draw.rounded_rectangle([(tx, pill_y_foot), (tx + t_w, pill_y_foot + pill_h_foot)], radius=10, fill=(24, 32, 54, 255), outline=t_col, width=1)
            draw.text((tx + 8, pill_y_foot + 8), t_str, font=f_ticker, fill=t_col)
            tx += t_w + 10

    # Right: Creator Branding & Verified Avatar
    brand_text = "Andrea Ravalli"
    sub_brand = "eToro Popular Investor"
    f_brand_name = _get_font(16, bold=True)
    f_brand_sub = _get_font(12, bold=False)

    avatar_size = 42
    avatar_x = W - 280
    avatar_y = footer_y + (footer_h - avatar_size) // 2

    if os.path.exists(PROFILE_PHOTO_PATH):
        try:
            avatar = Image.open(PROFILE_PHOTO_PATH).convert("RGBA")
            avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            card.paste(avatar, (avatar_x, avatar_y), mask=mask)
            draw.ellipse((avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size), outline=(0, 212, 255, 200), width=2)
        except Exception:
            pass

    draw.text((avatar_x + avatar_size + 10, avatar_y + 4), brand_text, font=f_brand_name, fill="#FFFFFF")
    draw.text((avatar_x + avatar_size + 10, avatar_y + 22), sub_brand, font=f_brand_sub, fill="#94A3B8")

    # ── Save Output ─────────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"meme_{sentiment.lower()}_{aspect_ratio.replace(':', 'x')}_{timestamp}.png"
    out_path = os.path.join(OUTPUT_DIR, out_name)

    card = card.convert("RGB")
    card.save(out_path, format="PNG", quality=95)
    print(f"✅ Generated 16:9 eToro Meme Card: {out_path} ({sentiment} | {W}x{H})")
    return out_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate sample financial meme cards")
    parser.add_argument("--demo", action="store_true", help="Generate demo memes for all scenarios in 16:9")
    args = parser.parse_args()

    sample_movers = [("PLTR", 5.4), ("NVDA", 3.2), ("CCJ", 2.1)]
    
    if args.demo:
        print("🎨 Generating full gallery of 16:9 eToro-native memes...")
        generate_meme_card(portfolio_daily=2.45, top_performers=sample_movers, lang="it", forced_template="gatsby_cheers.jpg", aspect_ratio="16:9")
        generate_meme_card(portfolio_daily=0.75, top_performers=sample_movers, lang="it", forced_template="honest_work.png", aspect_ratio="16:9")
        generate_meme_card(portfolio_daily=0.85, top_performers=sample_movers, lang="it", forced_template="two_bus_passengers.jpg", aspect_ratio="16:9")
        generate_meme_card(portfolio_daily=0.10, top_performers=sample_movers, lang="it", forced_template="trade_offer.jpg", aspect_ratio="16:9")
        generate_meme_card(portfolio_daily=0.15, top_performers=sample_movers, lang="it", forced_template="distracted_boyfriend.jpg", aspect_ratio="16:9")
        generate_meme_card(portfolio_daily=-0.75, top_performers=[("NVDA", -1.2)], lang="it", forced_template="woman_yelling_cat.jpg", aspect_ratio="16:9")
        generate_meme_card(portfolio_daily=-0.95, top_performers=[("NVDA", -1.2)], lang="it", forced_template="clown_makeup.jpg", aspect_ratio="16:9")
        generate_meme_card(portfolio_daily=-1.85, top_performers=[("TSLA", -3.2), ("AMD", -2.8)], lang="it", forced_template="this_is_fine.jpg", aspect_ratio="16:9")
        generate_meme_card(portfolio_daily=-2.20, top_performers=[("TSLA", -4.1)], lang="it", forced_template="drowning_kid.jpg", aspect_ratio="16:9")
        generate_meme_card(portfolio_daily=3.10, top_performers=sample_movers, lang="en", forced_template="stonks.jpg", aspect_ratio="16:9")
    else:
        generate_meme_card(portfolio_daily=1.45, top_performers=sample_movers, aspect_ratio="16:9")
