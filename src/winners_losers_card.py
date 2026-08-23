#!/usr/bin/env python3
"""
Winners & Losers Card Generator — Landscape 16:9 (1280x720)
=============================================================
Generates a 1280x720 landscape card inspired by modern news/sports banners:
  • 16:9 aspect ratio — optimal for desktop & mobile feeds without cropping
  • Two stacked horizontal rounded cards with neon glow borders
  • Left badge: Circular stock logo
  • Centre: Company Name, Ticker, Sector tag
  • Right: Huge percentage change (+4.82% / -2.31%) with glow effect
"""

import io
import os
import time
import hashlib
from datetime import datetime

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
CARD_H = 720   # 16:9 Landscape — fits perfectly in all feeds without cropping

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
URL_TEXT    = "etoro.com/people/andrearavalli"
AUTHOR_TEXT = "Andrea Ravalli"

SECTOR_TAGS = {
    "NVDA":      "Chip AI · semiconduttori",
    "MSFT":      "Software · cloud · AI",
    "AMZN":      "E-commerce · cloud AWS",
    "GOOG":      "Search · cloud · AI",
    "LLY":       "Farmaceutica · GLP-1",
    "PLTR":      "AI governativa · difesa",
    "AVGO":      "Semiconduttori · networking",
    "TSM":       "Fonderie chip · Taiwan",
    "ABBV":      "Farmaceutica · biotech",
    "ABT.US":    "Dispositivi medici",
    "HUM":       "Assicurazione sanitaria",
    "MELI":      "E-commerce · LatAm",
    "CCJ":       "Uranio · energia nucleare",
    "NET":       "Sicurezza cloud · CDN",
    "PYPL":      "Pagamenti digitali",
    "AZN.L":     "Farmaceutica · oncologia",
    "NOVO-B.CO": "Farmaceutica · diabete",
    "ENEL.MI":   "Utility · energia rinnovabile",
    "ENI.MI":    "Energia · petrolio e gas",
    "PRY.MI":    "Cavi · energia verde",
    "RACE":      "Auto di lusso · motorsport",
    "VOW3.DE":   "Auto · EV",
    "GLEN.L":    "Materie prime · metalli",
    "TRIG.L":    "Energia rinnovabile UK",
    "SX7PEX.DE": "Banche europee ETF",
    "IEUR":      "ETF azionario Europa",
    "WDEF.L":    "ETF dividendi Europa",
    "IB01.L":    "Treasury USA 0-1yr",
    "XEON.DE":   "Liquidità overnight EUR",
    "IQQL.DE":   "ETF quality MSCI World",
    "IEMG":      "ETF mercati emergenti",
    "1211.HK":   "Auto elettriche · BYD",
    "1919.HK":   "Shipping · COSCO",
    "2318.HK":   "Assicurazioni · Cina",
    "TRX":       "Crypto · TRON",
    "ETOR":      "eToro Group",
    "PPFB.DE":   "Metalli fisici ETF",
    "ULVR.L":    "Beni di consumo · Unilever",
    "VOF.L":     "Vietnam · mercati emergenti",
    "INDO.PA":   "Indonesia · ETF",
    "MAU.PA":    "Petrolio · esplorazione",
}

SESSION_LABELS = {
    "European market open": "APERTURA MERCATI EU",
    "U.S. market open":     "APERTURA WALL STREET",
    "U.S. market close":    "CHIUSURA MERCATI",
    "Weekly recap (Sat)":   "RECAP SETTIMANALE",
    "Weekly recap (Sun)":   "CLASSIFICA SETTIMANALE",
    "Monthly recap":        "RESOCONTO MENSILE",
    "Daily recap":          "PORTFOLIO UPDATE",
}

SESSION_METRIC = {
    "European market open": "daily_change",
    "U.S. market open":     "daily_change",
    "U.S. market close":    "daily_change",
    "Weekly recap (Sat)":   "weekly_change",
    "Weekly recap (Sun)":   "weekly_change",
    "Monthly recap":        "monthly_change",
    "Daily recap":          "daily_change",
}

PERIOD_LABELS = {
    "daily_change":   "DEL GIORNO",
    "weekly_change":  "DELLA SETTIMANA",
    "monthly_change": "DEL MESE",
}

_TICKER_DOMAIN_MAP = {
    "NVDA":      "nvidia.com",
    "MSFT":      "microsoft.com",
    "AMZN":      "amazon.com",
    "GOOG":      "google.com",
    "LLY":       "lilly.com",
    "PLTR":      "palantir.com",
    "AVGO":      "broadcom.com",
    "TSM":       "tsmc.com",
    "ABBV":      "abbvie.com",
    "ABT.US":    "abbott.com",
    "ABT":       "abbott.com",
    "HUM":       "humana.com",
    "MELI":      "mercadolibre.com",
    "CCJ":       "cameco.com",
    "NET":       "cloudflare.com",
    "PYPL":      "paypal.com",
    "AZN.L":     "astrazeneca.com",
    "NOVO-B.CO": "novonordisk.com",
    "ENEL.MI":   "enel.com",
    "ENI.MI":    "eni.com",
    "PRY.MI":    "prysmiangroup.com",
    "RACE":      "ferrari.com",
    "VOW3.DE":   "volkswagenag.com",
    "GLEN.L":    "glencore.com",
    "1211.HK":   "byd.com",
    "1919.HK":   "lines.coscoshipping.com",
    "2318.HK":   "pingan.com",
    "WMT":       "walmart.com",
    "MRVL":      "marvell.com",
    "MAU.PA":    "maureletprom.fr",
    "ULVR.L":    "unilever.com",
    "TRIG.L":    "trig-ltd.com",
    "SPCX.RTH":  "spacex.com",
    "VOF.L":     "vinacapital.com",
    "INDO.PA":   "amundi.com",
    "PPFB.DE":   "ishares.com",
    "SX7PEX.DE": "ishares.com",
    "IEUR":      "ishares.com",
    "IQQL.DE":   "ishares.com",
    "IB01.L":    "ishares.com",
    "WDEF.L":    "wisdomtree.com",
    "XEON.DE":   "dws.com",
    "ETOR":      "etoro.com",
    "TRX":       "tron.network",
}


# ─── Font helpers ─────────────────────────────────────────────────────────────

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


# ─── Logo fetching ────────────────────────────────────────────────────────────

def _fetch_logo_url_for_ticker(ticker: str) -> "str | None":
    if not REQUESTS_AVAILABLE:
        return None
    domain = _TICKER_DOMAIN_MAP.get(ticker)
    if domain:
        return f"https://cdn.tickerlogos.com/{domain}"
    try:
        r = _requests.get("https://cdn.tickerlogos.com/api/logo-search/", params={"q": ticker}, timeout=5)
        if r.ok:
            results = r.json().get("results", [])
            if results:
                d = results[0].get("website", "")
                if d: return f"https://cdn.tickerlogos.com/{d}"
    except Exception:
        pass
    return None


def _download_logo(ticker: str, size: int = 100) -> "Image.Image | None":
    if not PIL_AVAILABLE:
        return None
    safe = ticker.replace("/", "_").replace("\\", "_")
    base = safe.split(".")[0]

    # 1. Check local assets/logos under multiple filename variations
    candidates = [f"{safe}.png", f"{base}.png", f"{safe.upper()}.png", f"{base.upper()}.png"]
    for c in candidates:
        repo_path = os.path.join(LOGO_DIR, c)
        if os.path.exists(repo_path) and os.path.getsize(repo_path) > 300:
            try:
                return _make_circular(Image.open(repo_path).convert("RGBA"), size)
            except Exception:
                pass

    if not REQUESTS_AVAILABLE:
        return None

    os.makedirs(LOGO_CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(LOGO_CACHE_DIR, f"{safe}.png")
    if os.path.exists(cache_file):
        if time.time() - os.path.getmtime(cache_file) < 7 * 86400:
            try:
                return _make_circular(Image.open(cache_file).convert("RGBA"), size)
            except Exception:
                pass

    # 2. Try online sources: Google Favicon API and Tickerlogos CDN
    domain = _TICKER_DOMAIN_MAP.get(ticker) or _TICKER_DOMAIN_MAP.get(base)
    urls_to_try = []
    if domain:
        urls_to_try.append(f"https://www.google.com/s2/favicons?domain={domain}&sz=128")
        urls_to_try.append(f"https://cdn.tickerlogos.com/{domain}")
    
    logo_url = _fetch_logo_url_for_ticker(ticker)
    if logo_url and logo_url not in urls_to_try:
        urls_to_try.append(logo_url)

    for url in urls_to_try:
        try:
            r = _requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if r.ok and len(r.content) > 200:
                img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                img.save(cache_file, "PNG")
                return _make_circular(img, size)
        except Exception:
            continue

    return None


def _create_fallback_badge(ticker: str, emoji_char: str = None, size: int = 100) -> "Image.Image":
    """Create a sleek circular badge with ticker initial or emoji as fallback."""
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(out)
    draw.ellipse([0, 0, size - 1, size - 1], fill=(30, 35, 55, 255), outline=(70, 80, 120, 255), width=2)
    display_txt = emoji_char if emoji_char else ticker.split(".")[0][:3]
    f = _font(size // 3)
    bb = draw.textbbox((0, 0), display_txt, font=f)
    w = bb[2] - bb[0]
    h = bb[3] - bb[1]
    draw.text(((size - w) // 2, (size - h) // 2 - 2), display_txt, fill=(240, 240, 255, 255), font=f)
    return out


def _make_circular(img: "Image.Image", size: int) -> "Image.Image":
    # If image is non-square, center on a white square canvas first
    w, h = img.size
    dim = max(w, h)
    sq = Image.new("RGBA", (dim, dim), (255, 255, 255, 255))
    sq.paste(img, ((dim - w) // 2, (dim - h) // 2), img if img.mode == "RGBA" else None)
    sq = sq.resize((size, size), Image.LANCZOS)
    
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(sq, (0, 0), mask)
    return out


def _circular_avatar(path: str, size: int = 50):
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
        ImageDraw.Draw(frame).ellipse([0, 0, size + 3, size + 3], outline=(0, 210, 10, 220), width=2)
        frame.paste(out, (2, 2), out)
        return frame
    except Exception:
        return None


# ─── Main 16:9 Card Generator ─────────────────────────────────────────────────

def generate_winners_losers_card(
    winner: dict,
    loser: dict,
    session_name: str = "U.S. market close",
    emoji_map: dict = None,
    output_path: str = "output/winners_losers.png",
    fetch_logos: bool = True,
) -> "str | None":
    """
    Generate a 1280×720 Landscape card with top & flop performance boxes.
    """
    if not PIL_AVAILABLE:
        print("Warning: Pillow not available")
        return None

    metric = SESSION_METRIC.get(session_name, "daily_change")
    period_label  = PERIOD_LABELS.get(metric, "DEL GIORNO")
    session_label = SESSION_LABELS.get(session_name, session_name.upper())

    # Fetch logos
    LOGO_SIZE = 110
    winner_logo = _download_logo(winner["ticker"], LOGO_SIZE) if fetch_logos else None
    loser_logo  = _download_logo(loser["ticker"],  LOGO_SIZE) if fetch_logos else None

    # Base image: Dark rich background
    img = Image.new("RGBA", (CARD_W, CARD_H), (10, 12, 24, 255))
    draw = ImageDraw.Draw(img)

    # Gradient overlay
    bg_top = (12, 14, 28)
    bg_bot = (22, 18, 42)
    for y in range(CARD_H):
        t = y / CARD_H
        r = int(bg_top[0] * (1 - t) + bg_bot[0] * t)
        g = int(bg_top[1] * (1 - t) + bg_bot[1] * t)
        b = int(bg_top[2] * (1 - t) + bg_bot[2] * t)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b, 255))

    # Decorative top bar
    acc = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    ad  = ImageDraw.Draw(acc)
    for y in range(5):
        a = int(255 * (1 - y / 5))
        ad.line([(0, y), (CARD_W, y)], fill=(210, 168, 40, a))
    img = Image.alpha_composite(img, acc)
    draw = ImageDraw.Draw(img)

    # Fonts
    f_title   = _font(38)
    f_sub     = _reg_font(20)
    f_date    = _reg_font(18)
    f_sess    = _reg_font(18)

    f_box_title = _font(20)   # "▲ MIGLIORE"
    f_co_name   = _font(34)   # "NVIDIA"
    f_ticker    = _reg_font(22) # "$NVDA"
    f_sector    = _reg_font(18) # "Chip AI · semiconduttori"
    f_pct       = _font(64)   # "+4.82%"

    f_author  = _reg_font(18)
    f_url     = _reg_font(16)

    # Colours
    WHITE       = (245, 245, 250, 255)
    MUTED       = (160, 160, 180, 230)
    GOLD        = (225, 180, 45, 255)
    GREEN_GLOW  = (40, 225, 100, 255)
    GREEN_BG    = (15, 45, 28, 220)
    RED_GLOW    = (240, 60, 80, 255)
    RED_BG      = (45, 16, 24, 220)

    # ── Header ────────────────────────────────────────────────────────────────
    date_str = datetime.now().strftime("%d %b %Y").upper()
    draw.text((60, 28), date_str, fill=MUTED, font=f_date)
    bb_s = draw.textbbox((0, 0), session_label, font=f_sess)
    draw.text((CARD_W - bb_s[2] - 60, 28), session_label, fill=MUTED, font=f_sess)

    # Title centred
    title_text = f"TOP & FLOP {period_label}"
    bb_t = draw.textbbox((0, 0), title_text, font=f_title)
    draw.text(((CARD_W - (bb_t[2] - bb_t[0])) // 2, 65), title_text, fill=WHITE, font=f_title)

    # Line under header
    draw.line([(60, 120), (CARD_W - 60, 120)], fill=(60, 60, 85, 180), width=1)

    # ── Box Drawer Helper ─────────────────────────────────────────────────────
    def _draw_row_box(data: dict, logo_img: "Image.Image", y_pos: int, color_glow: tuple, color_bg: tuple, is_winner: bool):
        BOX_W = 1160
        BOX_H = 210
        BOX_X = (CARD_W - BOX_W) // 2
        RADIUS = 20

        # Create overlay for glow and box background
        box_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box_layer)

        # Glow / Border
        # Outer glow border
        bd.rounded_rectangle([BOX_X - 2, y_pos - 2, BOX_X + BOX_W + 2, y_pos + BOX_H + 2], radius=RADIUS + 2, fill=(*color_glow[:3], 40))
        bd.rounded_rectangle([BOX_X - 1, y_pos - 1, BOX_X + BOX_W + 1, y_pos + BOX_H + 1], radius=RADIUS + 1, fill=(*color_glow[:3], 160))
        # Box background
        bd.rounded_rectangle([BOX_X, y_pos, BOX_X + BOX_W, y_pos + BOX_H], radius=RADIUS, fill=color_bg)

        # Composite box background
        nonlocal img
        img = Image.alpha_composite(img, box_layer)
        d = ImageDraw.Draw(img)

        # 1. Left Badge Label (e.g. ▲ MIGLIORE)
        lbl_text = "▲ MIGLIORE" if is_winner else "▼ PEGGIORE"
        d.text((BOX_X + 30, y_pos + 20), lbl_text, fill=color_glow, font=f_box_title)

        # 2. Logo placement
        logo_x = BOX_X + 30
        logo_y = y_pos + 60
        actual_logo = logo_img
        if not actual_logo:
            emoji_char = emoji_map.get(data.get("ticker", ""), "") if emoji_map else ""
            actual_logo = _create_fallback_badge(data["ticker"], emoji_char, LOGO_SIZE)

        img.paste(actual_logo, (logo_x, logo_y), actual_logo)
        text_start_x = logo_x + LOGO_SIZE + 25

        # 3. Company Name & Ticker
        company = data["company_name"]
        company_display = company if len(company) <= 24 else company[:22] + "…"
        ticker = f"${data['ticker']}"
        sector = SECTOR_TAGS.get(data["ticker"], "")

        d.text((text_start_x, y_pos + 62), company_display, fill=WHITE, font=f_co_name)
        d.text((text_start_x, y_pos + 106), ticker, fill=MUTED, font=f_ticker)

        if sector:
            d.text((text_start_x, y_pos + 142), sector, fill=(180, 180, 200, 200), font=f_sector)

        # 4. Right side: Percentage with Glow
        pct_val = data["change"]
        pct_str = f"{pct_val:+.2f}%"
        bb_p = d.textbbox((0, 0), pct_str, font=f_pct)
        pw = bb_p[2] - bb_p[0]
        ph = bb_p[3] - bb_p[1]

        px = BOX_X + BOX_W - pw - 40
        py = y_pos + (BOX_H - ph) // 2 - 10

        # Glow effect behind number
        for dx, dy in [(-3, 3), (3, 3), (0, 4), (-3, -1), (3, -1)]:
            d.text((px + dx, py + dy), pct_str, fill=(*color_glow[:3], 40), font=f_pct)

        d.text((px, py), pct_str, fill=color_glow, font=f_pct)

    # Draw Top Box (Winner)
    _draw_row_box(winner, winner_logo, 155, GREEN_GLOW, GREEN_BG, is_winner=True)

    # Draw Bottom Box (Loser)
    _draw_row_box(loser, loser_logo, 395, RED_GLOW, RED_BG, is_winner=False)

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_y = 635
    draw.line([(60, footer_y), (CARD_W - 60, footer_y)], fill=(60, 60, 85, 180), width=1)

    avatar = _circular_avatar(PROFILE_PHOTO_PATH, 46) if os.path.exists(PROFILE_PHOTO_PATH) else None
    bot_y = footer_y + 16
    tx = 60
    if avatar:
        img.paste(avatar, (60, bot_y), avatar)
        tx = 60 + avatar.size[0] + 12

    bb_auth = draw.textbbox((0, 0), AUTHOR_TEXT, font=f_author)
    auth_h  = bb_auth[3] - bb_auth[1]
    draw.text((tx, bot_y + (46 - auth_h) // 2), AUTHOR_TEXT, fill=(230, 228, 245, 240), font=f_author)

    bb_url = draw.textbbox((0, 0), URL_TEXT, font=f_url)
    draw.text((CARD_W - (bb_url[2] - bb_url[0]) - 60, bot_y + (46 - (bb_url[3] - bb_url[1])) // 2),
              URL_TEXT, fill=(140, 175, 235, 210), font=f_url)

    # Save PNG
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.convert("RGB").save(output_path, "PNG", optimize=True)
    print(f"Winners/Losers card saved: {output_path} ({CARD_W}×{CARD_H})")
    return output_path


def build_card_from_stock_data(
    stock_data: dict,
    session_name: str = "U.S. market close",
    emoji_map: dict = None,
    output_path: str = "output/winners_losers.png",
    fetch_logos: bool = True,
) -> "str | None":
    """
    Convenience wrapper: picks winner and loser from stock_data automatically.
    """
    metric     = SESSION_METRIC.get(session_name, "daily_change")
    is_daily   = metric == "daily_change"
    candidates = {
        t: d for t, d in stock_data.items()
        if (d.get("has_traded_today", True) or not is_daily)
        and metric in d
        and d[metric] is not None
        and t not in {"MNODL.L", "NVTKL.L"}
    }

    if len(candidates) < 2:
        print("Not enough candidates for winners/losers card")
        return None

    sorted_by = sorted(candidates.items(), key=lambda x: x[1][metric], reverse=True)
    top_sym,  top_data  = sorted_by[0]
    bot_sym,  bot_data  = sorted_by[-1]

    return generate_winners_losers_card(
        winner={"ticker": top_sym,  "company_name": top_data.get("company_name", top_sym),
                "change": top_data[metric]},
        loser= {"ticker": bot_sym,  "company_name": bot_data.get("company_name", bot_sym),
                "change": bot_data[metric]},
        session_name=session_name,
        emoji_map=emoji_map,
        output_path=output_path,
        fetch_logos=fetch_logos,
    )
