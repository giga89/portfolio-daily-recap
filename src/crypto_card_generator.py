#!/usr/bin/env python3
"""
Crypto Daily Recap Card Generator — 16:9 Landscape (1280x720)
=============================================================
Generates a stunning, high-resolution 1280x720 landscape card for eToro & Telegram:
  • 16:9 format — full width, no cropping
  • Modern dark glassmorphism styling with neon accents
  • Top header with Fear & Greed sentiment badge
  • 4 balanced cards (2x2 grid) featuring official crypto logos, live prices, 24h % change, and 24h volume
  • Professional branding footer with Andrea Ravalli's profile link
"""

import os
import io
import time
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import requests as _requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

CARD_W = 1280
CARD_H = 720

PROFILE_PHOTO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "profile_photo.jpg"
)
LOGO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "logos"
)
LOGO_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "logo_cache"
)

URL_TEXT = "etoro.com/people/andrearavalli"
AUTHOR_TEXT = "Andrea Ravalli · Crypto & Portfolio Recap"

CRYPTO_COLORS = {
    "BTC": (247, 147, 26),
    "ETH": (98, 126, 234),
    "SOL": (20, 241, 149),
    "TRX": (235, 0, 41),
    "XRP": (35, 41, 47),
    "ADA": (0, 51, 173),
    "LINK": (55, 91, 210),
    "AVAX": (232, 65, 66),
    "DOGE": (194, 166, 51),
}


def _font(size: int) -> "ImageFont.FreeTypeFont":
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
    ]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()


def _reg_font(size: int) -> "ImageFont.FreeTypeFont":
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()


def _make_circular(img: "Image.Image", size: int = 46) -> "Image.Image":
    img = img.resize((size, size), Image.LANCZOS)
    bg = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    bg.paste(img, (0, 0), img)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(bg, (0, 0), mask)
    return out


def _circular_avatar(path: str, size: int = 44):
    if not PIL_AVAILABLE or not os.path.exists(path):
        return None
    try:
        photo = Image.open(path).convert("RGBA")
        w, h = photo.size
        s = min(w, h)
        photo = photo.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
        photo = photo.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(photo, (0, 0), mask)
        frame = Image.new("RGBA", (size + 4, size + 4), (0, 0, 0, 0))
        ImageDraw.Draw(frame).ellipse([0, 0, size + 3, size + 3], outline=(0, 210, 255, 220), width=2)
        frame.paste(out, (2, 2), out)
        return frame
    except Exception:
        return None


def _get_crypto_logo(symbol: str, size: int = 48) -> "Image.Image":
    """
    Fetch or generate a high-quality circular badge/logo for the cryptocurrency.
    """
    clean = symbol.upper().replace("$", "").replace("-USD", "")
    os.makedirs(LOGO_CACHE_DIR, exist_ok=True)

    # 1. Local assets/logos
    for local_name in [f"{clean}.png", f"{clean}-USD.png"]:
        p = os.path.join(LOGO_DIR, local_name)
        if os.path.exists(p) and os.path.getsize(p) > 200:
            try:
                return _make_circular(Image.open(p).convert("RGBA"), size)
            except Exception:
                pass

    # 2. Cached logo
    cache_path = os.path.join(LOGO_CACHE_DIR, f"{clean}_crypto.png")
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 200:
        try:
            return _make_circular(Image.open(cache_path).convert("RGBA"), size)
        except Exception:
            pass

    # 3. Remote download (Cryptocurrency Icons CDN)
    if REQUESTS_AVAILABLE:
        urls = [
            f"https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/{clean.lower()}.png",
            f"https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@1a63539be033d80abb11483dda8be0e77e1c4793/128/color/{clean.lower()}.png",
        ]
        for u in urls:
            try:
                r = _requests.get(u, headers={"User-Agent": "CryptoRecap/1.0"}, timeout=4)
                if r.ok and len(r.content) > 300:
                    img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                    img.save(cache_path, "PNG")
                    return _make_circular(img, size)
            except Exception:
                continue

    # 4. Fallback: Draw rich custom circular badge with ticker acronym
    color = CRYPTO_COLORS.get(clean, (0, 180, 240))
    badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(badge)
    bdraw.ellipse([0, 0, size - 1, size - 1], fill=(*color, 240), outline=(255, 255, 255, 200), width=2)

    font_sym = _font(15 if len(clean) <= 3 else 12)
    bbox = bdraw.textbbox((0, 0), clean, font=font_sym)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    bdraw.text(((size - tw) // 2, (size - th) // 2 - 1), clean, fill=(255, 255, 255), font=font_sym)
    return badge


def generate_crypto_card(
    crypto_data: Dict[str, Any],
    output_path: str = "output/crypto_recap.png"
) -> Optional[str]:
    """
    Generate 1280x720 16:9 crypto recap card.
    """
    if not PIL_AVAILABLE:
        print("Warning: Pillow not available")
        return None

    # Base background: Deep gradient
    img = Image.new("RGBA", (CARD_W, CARD_H), (10, 14, 28, 255))
    draw = ImageDraw.Draw(img)

    bg_top = (10, 14, 30)
    bg_bot = (18, 24, 48)
    for y in range(CARD_H):
        t = y / CARD_H
        r = int(bg_top[0] * (1 - t) + bg_bot[0] * t)
        g = int(bg_top[1] * (1 - t) + bg_bot[1] * t)
        b = int(bg_top[2] * (1 - t) + bg_bot[2] * t)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b, 255))

    # Top accent cyan/gold gradient bar
    for x in range(CARD_W):
        t = x / CARD_W
        r = int(0 * (1 - t) + 247 * t)
        g = int(210 * (1 - t) + 147 * t)
        b = int(255 * (1 - t) + 26 * t)
        draw.line([(x, 0), (x, 5)], fill=(r, g, b, 255))

    # Fonts
    f_badge     = _font(13)
    f_date      = _reg_font(13)
    f_title     = _font(25)
    f_sent_val  = _font(14)
    f_sym       = _font(22)
    f_name      = _reg_font(13)
    f_price     = _font(21)
    f_pct       = _font(17)
    f_vol_lbl   = _reg_font(12)
    f_vol_val   = _font(13)
    f_author    = _font(14)
    f_url       = _font(14)

    # Header section
    top_y = 22
    lbl_text = "⚡ CRYPTO DAILY PULSE · ETORO TRADABLE ASSETS"
    bb_lbl = draw.textbbox((0, 0), lbl_text, font=f_badge)
    lbl_w = bb_lbl[2] - bb_lbl[0]
    draw.rounded_rectangle([60, top_y, 60 + lbl_w + 20, top_y + 24], radius=6, fill=(0, 180, 240, 40), outline=(0, 200, 255, 120), width=1)
    draw.text((70, top_y + 5), lbl_text, fill=(0, 220, 255), font=f_badge)

    # Date
    now_str = datetime.now().strftime("%d %b %Y · %H:%M UTC").upper()
    bb_d = draw.textbbox((0, 0), now_str, font=f_date)
    draw.text((CARD_W - 60 - (bb_d[2] - bb_d[0]), top_y + 5), now_str, fill=(160, 175, 210), font=f_date)

    # Main title
    title_y = top_y + 36
    draw.text((60, title_y), "MERCATO CRYPTO & SENTIMENT", fill=(255, 255, 255), font=f_title)

    # Sentiment Pill Badge (Fear & Greed)
    sentiment = crypto_data.get("sentiment", {})
    sent_score = sentiment.get("score", 50)
    sent_cls = sentiment.get("classification_it", "Neutrale")

    sent_text = f"FEAR & GREED: {sent_score}/100 · {sent_cls.upper()}"
    bb_s = draw.textbbox((0, 0), sent_text, font=f_sent_val)
    sw = bb_s[2] - bb_s[0]
    
    # Sentiment pill color
    if sent_score >= 55:
        pill_fill = (0, 160, 80, 45)
        pill_border = (0, 220, 100, 180)
        pill_color = (80, 255, 140)
    elif sent_score <= 45:
        pill_fill = (180, 40, 40, 45)
        pill_border = (255, 70, 70, 180)
        pill_color = (255, 100, 100)
    else:
        pill_fill = (160, 140, 20, 45)
        pill_border = (230, 200, 40, 180)
        pill_color = (255, 225, 80)

    draw.rounded_rectangle([CARD_W - 60 - sw - 24, title_y + 2, CARD_W - 60, title_y + 32], radius=15, fill=pill_fill, outline=pill_border, width=1)
    draw.text((CARD_W - 60 - sw - 12, title_y + 9), sent_text, fill=pill_color, font=f_sent_val)

    # ── 2x2 Grid Layout for 4 Crypto Assets ────────────────────────────────────
    cryptos_dict = crypto_data.get("cryptos", {})
    crypto_list = list(cryptos_dict.values())[:4]

    GRID_X = 60
    GRID_Y = 115
    GAP_X = 24
    GAP_Y = 18
    CARD_BOX_W = (CARD_W - 120 - GAP_X) // 2
    CARD_BOX_H = 238

    for idx, c in enumerate(crypto_list):
        col = idx % 2
        row = idx // 2
        bx = GRID_X + col * (CARD_BOX_W + GAP_X)
        by = GRID_Y + row * (CARD_BOX_H + GAP_Y)

        is_pos = c.get("change_24h", 0.0) >= 0
        glow_c = (0, 220, 120) if is_pos else (255, 65, 85)
        bg_card = (22, 28, 55, 220)
        border_c = (glow_c[0], glow_c[1], glow_c[2], 100)

        # Card container with rounded corners
        draw.rounded_rectangle([bx, by, bx + CARD_BOX_W, by + CARD_BOX_H], radius=14, fill=bg_card, outline=border_c, width=1)

        # Symbol, name & cashtag
        sym_str   = c.get("cashtag", f"${c.get('symbol', '')}")
        raw_sym   = c.get("symbol", "BTC")
        name_str  = c.get("name", raw_sym)

        # Paste crisp circular logo
        logo_img = _get_crypto_logo(raw_sym, size=48)
        if logo_img:
            img.paste(logo_img, (bx + 18, by + 18), logo_img)

        draw.text((bx + 76, by + 20), sym_str, fill=(255, 255, 255), font=f_sym)
        draw.text((bx + 76, by + 46), name_str, fill=(160, 175, 210), font=f_name)

        # Right side of top row: 24h Change badge
        chg_val = c.get("change_24h", 0.0)
        chg_str = f"{chg_val:+.2f}%"
        bb_chg = draw.textbbox((0, 0), chg_str, font=f_pct)
        cw = bb_chg[2] - bb_chg[0]
        badge_w = cw + 20
        badge_x = bx + CARD_BOX_W - badge_w - 18
        badge_y = by + 22

        b_fill = (0, 180, 90, 40) if is_pos else (220, 40, 60, 40)
        b_stroke = (0, 220, 100, 160) if is_pos else (255, 70, 90, 160)
        draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + 30], radius=8, fill=b_fill, outline=b_stroke, width=1)
        draw.text((badge_x + 10, badge_y + 6), chg_str, fill=glow_c, font=f_pct)

        # Divider inside card
        draw.line([(bx + 18, by + 76), (bx + CARD_BOX_W - 18, by + 76)], fill=(45, 55, 90, 150), width=1)

        # Price section
        draw.text((bx + 20, by + 88), "PREZZO SPOT", fill=(130, 145, 180), font=f_vol_lbl)
        price_str = c.get("price_formatted", f"${c.get('price_usd', 0):,.2f}")
        draw.text((bx + 20, by + 106), price_str, fill=(245, 248, 255), font=f_price)

        # 24h Volume section
        vol_x = bx + (CARD_BOX_W // 2) + 10
        draw.text((vol_x, by + 88), "VOLUME 24H", fill=(130, 145, 180), font=f_vol_lbl)
        vol_str = c.get("volume_formatted", "$0.00")
        draw.text((vol_x, by + 106), vol_str, fill=(0, 220, 255), font=f_price)

        # Bottom Bar inside card: 24h Range (Low - High)
        draw.line([(bx + 18, by + 155), (bx + CARD_BOX_W - 18, by + 155)], fill=(45, 55, 90, 150), width=1)
        low_s = c.get("low_formatted", "$0")
        high_s = c.get("high_formatted", "$0")
        range_str = f"Range 24h: {low_s} — {high_s}"
        draw.text((bx + 20, by + 168), range_str, fill=(160, 175, 210), font=f_vol_val)

        # eToro tag hint
        if raw_sym == "TRX":
            e_tag = "Disponibile su eToro · In Portafoglio"
            tag_color = (0, 220, 255)
        else:
            e_tag = "Disponibile su eToro · Spot & Copy"
            tag_color = (120, 140, 180)
        draw.text((bx + 20, by + 195), e_tag, fill=tag_color, font=f_vol_lbl)

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_y = 638
    draw.line([(60, footer_y), (CARD_W - 60, footer_y)], fill=(50, 60, 95, 180), width=1)

    avatar = _circular_avatar(PROFILE_PHOTO_PATH, 44)
    bot_y = footer_y + 14
    tx = 60
    if avatar:
        img.paste(avatar, (60, bot_y), avatar)
        tx = 60 + avatar.size[0] + 12

    bb_auth = draw.textbbox((0, 0), AUTHOR_TEXT, font=f_author)
    auth_h  = bb_auth[3] - bb_auth[1]
    draw.text((tx, bot_y + (44 - auth_h) // 2), AUTHOR_TEXT, fill=(230, 235, 250, 240), font=f_author)

    bb_url = draw.textbbox((0, 0), URL_TEXT, font=f_url)
    draw.text((CARD_W - (bb_url[2] - bb_url[0]) - 60, bot_y + (44 - (bb_url[3] - bb_url[1])) // 2),
              URL_TEXT, fill=(0, 210, 255, 220), font=f_url)

    # Save
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.convert("RGB").save(output_path, "PNG", optimize=True)
    print(f"✓ Crypto card generated: {output_path} ({CARD_W}×{CARD_H})")
    return output_path


if __name__ == "__main__":
    import crypto_fetcher
    data = crypto_fetcher.fetch_crypto_daily_data()
    out = generate_crypto_card(data, "output/crypto_recap.png")
    print(f"Card created: {out}")
