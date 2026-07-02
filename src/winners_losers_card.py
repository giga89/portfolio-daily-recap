#!/usr/bin/env python3
"""
Winners & Losers Card Generator — v2
======================================
Generates a 1080×1350 (4:5) card — the optimal format for eToro/Instagram
feed posts on mobile. Shows the best and worst performing stocks with:
  • Stock logo fetched from cdn.tickerlogos.com (no API key needed)
  • Company name, ticker, performance % (big)
  • Proportional bar
  • One-line sector tag

Layout (1080×1350, portrait — better mobile feed coverage):
  ┌─────────────────────────────────────────────────────────┐
  │  02 Jul 2025                        CHIUSURA MERCATI    │
  │                                                          │
  │   TOP  &  FLOP  DEL  GIORNO                             │
  │   ─────────────────────────────────────────────────     │
  │                                                          │
  │   🏆  MIGLIORE                                           │
  │   [logo]  NVIDIA                     NVDA               │
  │                  +4.82%                                  │
  │            ████████████░░░░░                             │
  │            Chip AI · semiconduttori                      │
  │                                                          │
  │   ─────────────────────────────────────────────────     │
  │                                                          │
  │   📉  PEGGIORE                                           │
  │   [logo]  Eni S.p.A.                ENI.MI               │
  │                  -2.31%                                  │
  │            █████░░░░░░░░░                                │
  │            Energia · petrolio e gas                      │
  │                                                          │
  │  [avatar] Andrea Ravalli         etoro.com/...           │
  └─────────────────────────────────────────────────────────┘
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

CARD_W = 1080
CARD_H = 1350   # 4:5 — optimal for eToro / Instagram feed posts

PROFILE_PHOTO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "profile_photo.jpg"
)
LOGO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "logos"
)
# Fallback runtime cache (for tickers not yet committed to repo)
LOGO_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "logo_cache"
)
URL_TEXT    = "etoro.com/people/andrearavalli"
AUTHOR_TEXT = "Andrea Ravalli"

# ─── Sector descriptions ─────────────────────────────────────────────────────
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

# Hardcoded domain map for tickers that need special handling
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
    "VOW3.DE":   "volkswagen.com",
    "GLEN.L":    "glencore.com",
    "1211.HK":   "bydglobal.com",
    "1919.HK":   "coscoshipping.com.cn",
    "2318.HK":   "pingan.com",
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

def _logo_cache_path(ticker: str) -> str:
    key = hashlib.md5(ticker.encode()).hexdigest()[:8]
    return os.path.join(LOGO_CACHE_DIR, f"{ticker.replace('/', '_')}_{key}.png")


def _fetch_logo_url_for_ticker(ticker: str) -> "str | None":
    """
    Resolve the logo URL for a ticker using:
    1. Hardcoded domain map (fastest, no network)
    2. cdn.tickerlogos.com search API (free, no key)
    Returns the final image URL or None.
    """
    if not REQUESTS_AVAILABLE:
        return None

    # 1. Hardcoded map
    domain = _TICKER_DOMAIN_MAP.get(ticker)
    if domain:
        return f"https://cdn.tickerlogos.com/{domain}"

    # 2. Search API
    try:
        r = _requests.get(
            "https://cdn.tickerlogos.com/api/logo-search/",
            params={"q": ticker},
            timeout=5,
        )
        if r.ok:
            results = r.json().get("results", [])
            if results:
                domain = results[0].get("website", "")
                if domain:
                    return f"https://cdn.tickerlogos.com/{domain}"
    except Exception:
        pass

    return None


def _download_logo(ticker: str, size: int = 100) -> "Image.Image | None":
    """
    Load a logo for the given ticker. Priority:
      1. assets/logos/{ticker}.png  — committed to repo, zero network
      2. assets/logo_cache/{ticker}  — runtime disk cache (7 days)
      3. cdn.tickerlogos.com         — live download, saved to cache

    Returns a circular PIL image or None on failure.
    """
    if not PIL_AVAILABLE:
        return None

    safe = ticker.replace("/", "_").replace("\\", "_")

    # 1. Committed repo logo (fastest path — no network)
    repo_path = os.path.join(LOGO_DIR, f"{safe}.png")
    if os.path.exists(repo_path) and os.path.getsize(repo_path) > 500:
        try:
            return _make_circular(Image.open(repo_path).convert("RGBA"), size)
        except Exception:
            pass   # fall through to next source

    if not REQUESTS_AVAILABLE:
        return None

    # 2. Runtime cache (< 7 days old)
    os.makedirs(LOGO_CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(LOGO_CACHE_DIR, f"{safe}.png")
    if os.path.exists(cache_file):
        age = time.time() - os.path.getmtime(cache_file)
        if age < 7 * 86400:
            try:
                return _make_circular(Image.open(cache_file).convert("RGBA"), size)
            except Exception:
                pass

    # 3. Live download from CDN
    logo_url = _fetch_logo_url_for_ticker(ticker)
    if not logo_url:
        return None
    try:
        r = _requests.get(logo_url, timeout=8)
        if r.ok and len(r.content) > 200:
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            img.save(cache_file, "PNG")
            return _make_circular(img, size)
        return None
    except Exception as exc:
        print(f"   ⚠️ Logo fetch failed for {ticker}: {exc}")
        return None


def _make_circular(img: "Image.Image", size: int) -> "Image.Image":
    """Resize to square and apply circular mask with white background."""
    img = img.resize((size, size), Image.LANCZOS)
    # White background (for logos with transparency)
    bg = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    bg.paste(img, (0, 0), img)
    # Circular mask
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(bg, (0, 0), mask)
    return out


# ─── Draw helpers ─────────────────────────────────────────────────────────────

def _centered(draw, text, cx, y, font, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (bb[2] - bb[0]) // 2 - bb[0], y), text, fill=fill, font=font)
    return bb[3] - bb[1]


def _bar(draw, x, y, w, h, pct, color, max_pct=5.0):
    ratio = min(abs(pct) / max_pct, 1.0)
    filled = int(w * ratio)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=(35, 33, 50))
    if filled > 0:
        draw.rounded_rectangle([x, y, x + filled, y + h], radius=h // 2, fill=color)


def _circular_avatar(path: str, size: int = 56):
    try:
        photo = Image.open(path).convert("RGBA")
        w, h = photo.size
        s = min(w, h)
        photo = photo.crop(((w - s) // 2, (h - s) // 2,
                             (w + s) // 2, (h + s) // 2))
        photo = photo.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(photo, (0, 0), mask)
        frame = Image.new("RGBA", (size + 6, size + 6), (0, 0, 0, 0))
        ImageDraw.Draw(frame).ellipse([0, 0, size + 5, size + 5],
                                      outline=(0, 210, 10, 220), width=2)
        frame.paste(out, (3, 3), out)
        return frame
    except Exception:
        return None


# ─── Main card generation ─────────────────────────────────────────────────────

def generate_winners_losers_card(
    winner: dict,
    loser: dict,
    session_name: str = "U.S. market close",
    emoji_map: dict = None,
    output_path: str = "output/winners_losers.png",
    fetch_logos: bool = True,
) -> "str | None":
    """
    Generate a 1080×1350 (4:5) card with best and worst performers.

    Args:
        winner:       {'ticker': str, 'company_name': str, 'change': float}
        loser:        {'ticker': str, 'company_name': str, 'change': float}
        session_name: Controls label and period text
        emoji_map:    Optional {ticker: emoji}
        output_path:  Where to save the PNG
        fetch_logos:  If True, download stock logos from CDN

    Returns:
        Saved file path, or None on failure.
    """
    if not PIL_AVAILABLE:
        print("Warning: Pillow not available")
        return None

    metric = SESSION_METRIC.get(session_name, "daily_change")
    period_label  = PERIOD_LABELS.get(metric, "DEL GIORNO")
    session_label = SESSION_LABELS.get(session_name, session_name.upper())

    # ── Pre-fetch logos (network, may take a second) ──────────────────────────
    LOGO_SIZE = 110
    winner_logo = _download_logo(winner["ticker"], LOGO_SIZE) if fetch_logos else None
    loser_logo  = _download_logo(loser["ticker"],  LOGO_SIZE) if fetch_logos else None

    # ── Background: very dark charcoal gradient ──────────────────────────────
    bg_top = (10, 10, 18)
    bg_bot = (20, 16, 36)
    img = Image.new("RGB", (CARD_W, CARD_H))
    draw = ImageDraw.Draw(img)
    for y in range(CARD_H):
        t = y / CARD_H
        r = int(bg_top[0] * (1 - t) + bg_top[0] * (1 - t) + bg_bot[0] * t)
        g = int(bg_top[1] * (1 - t) + bg_bot[1] * t)
        b = int(bg_top[2] * (1 - t) + bg_bot[2] * t)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))

    img = img.convert("RGBA")

    # Gold accent bar at very top
    acc = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    ad  = ImageDraw.Draw(acc)
    for y in range(6):
        a = int(255 * (1 - y / 6))
        ad.line([(0, y), (CARD_W, y)], fill=(200, 168, 30, a))
    img = Image.alpha_composite(img, acc)
    draw = ImageDraw.Draw(img)

    # ── Fonts ─────────────────────────────────────────────────────────────────
    f_date    = _reg_font(18)
    f_sess    = _reg_font(18)
    f_title   = _font(36)
    f_period  = _reg_font(20)
    f_section = _font(22)     # "🏆 MIGLIORE"
    f_company = _font(38)     # company name
    f_ticker  = _reg_font(24) # ticker symbol beside company
    f_pct     = _font(100)    # big % number
    f_sector  = _reg_font(22) # sector tag
    f_author  = _reg_font(20)
    f_url     = _reg_font(16)

    # ── Colours ───────────────────────────────────────────────────────────────
    WHITE        = (245, 245, 250, 255)
    MUTED        = (150, 148, 168, 220)
    GOLD         = (210, 168, 40, 240)
    GREEN        = (45, 215, 100, 255)
    GREEN_DIM    = (30, 100, 60, 255)
    RED          = (230, 55, 75, 255)
    RED_DIM      = (110, 25, 40, 255)
    DIVIDER      = (55, 50, 80, 200)

    # ── Header ────────────────────────────────────────────────────────────────
    y = 26
    date_str = datetime.now().strftime("%-d %b %Y")
    draw.text((40, y), date_str, fill=MUTED, font=f_date)
    bb = draw.textbbox((0, 0), session_label, font=f_sess)
    draw.text((CARD_W - bb[2] - 40, y), session_label, fill=MUTED, font=f_sess)
    y += 60

    # ── Main title ────────────────────────────────────────────────────────────
    _centered(draw, "TOP  &  FLOP", CARD_W // 2, y, f_title, GOLD)
    y += 50
    _centered(draw, period_label, CARD_W // 2, y, f_period, MUTED)
    y += 38

    # Separator
    draw.line([(60, y), (CARD_W - 60, y)], fill=DIVIDER, width=1)
    y += 36

    # ── Helper: draw one stock block ──────────────────────────────────────────
    def _draw_block(data: dict, y_start: int, color: tuple, label_text: str, label_emoji: str) -> int:
        """Draw a single winner/loser block. Returns the y position after the block."""
        ticker  = data["ticker"]
        company = data["company_name"]
        change  = data["change"]
        sector  = SECTOR_TAGS.get(ticker, "")
        logo    = winner_logo if color == GREEN else loser_logo

        cx  = CARD_W // 2
        PAD = 60
        y   = y_start

        # Section label (e.g. "🏆  MIGLIORE")
        lbl = f"{label_emoji}  {label_text}"
        draw.text((PAD, y), lbl, fill=color, font=f_section)
        y += 38

        # ── Logo + Company name + Ticker on one row ───────────────────────────
        row_h = LOGO_SIZE + 10
        logo_x = PAD
        text_x = PAD + (LOGO_SIZE + 20 if logo else 0)

        if logo:
            img.paste(logo, (logo_x, y), logo)

        # Company name (may be long — truncate if needed)
        company_display = company if len(company) <= 22 else company[:20] + "…"
        bb_co = draw.textbbox((0, 0), company_display, font=f_company)
        co_h  = bb_co[3] - bb_co[1]
        co_y  = y + (LOGO_SIZE - co_h) // 2 - 14

        draw.text((text_x, co_y), company_display, fill=WHITE, font=f_company)

        # Ticker in muted below company
        draw.text((text_x, co_y + co_h + 4), ticker, fill=MUTED, font=f_ticker)

        y += row_h + 18

        # ── Big % number centred ──────────────────────────────────────────────
        pct_str = f"{change:+.2f}%"
        bb_pct  = draw.textbbox((0, 0), pct_str, font=f_pct)
        pw = bb_pct[2] - bb_pct[0]
        ph = bb_pct[3] - bb_pct[1]
        px = cx - pw // 2 - bb_pct[0]
        # Glow
        for dx, dy in [(-4, 4), (4, 4), (0, 5), (-4, -2), (4, -2)]:
            draw.text((px + dx, y + dy), pct_str, fill=(*color[:3], 30), font=f_pct)
        draw.text((px, y), pct_str, fill=color, font=f_pct)
        y += ph + 24

        # ── Progress bar ──────────────────────────────────────────────────────
        bar_w = CARD_W - PAD * 2
        bar_h = 16
        _bar(draw, PAD, y, bar_w, bar_h, change, color, max_pct=5.0)
        y += bar_h + 18

        # ── Sector tag ────────────────────────────────────────────────────────
        if sector:
            _centered(draw, sector, cx, y, f_sector, MUTED)
            y += 32

        return y

    # Draw winner
    y = _draw_block(winner, y, GREEN, "MIGLIORE", "🏆")
    y += 20

    # Separator between blocks
    draw.line([(60, y), (CARD_W - 60, y)], fill=DIVIDER, width=1)
    y += 36

    # Draw loser
    _draw_block(loser, y, RED, "PEGGIORE", "📉")

    # ── Bottom bar with branding ──────────────────────────────────────────────
    bar_bot_h = 90
    bot_ov = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bot_ov)
    for y in range(bar_bot_h):
        a = int(220 * (y / bar_bot_h))
        bd.line([(0, CARD_H - bar_bot_h + y), (CARD_W, CARD_H - bar_bot_h + y)],
                fill=(6, 5, 15, a))
    img = Image.alpha_composite(img, bot_ov)
    draw = ImageDraw.Draw(img)

    avatar = _circular_avatar(PROFILE_PHOTO_PATH, 56) if os.path.exists(PROFILE_PHOTO_PATH) else None
    bot_y  = CARD_H - bar_bot_h + (bar_bot_h - 62) // 2
    tx = 30
    if avatar:
        img.paste(avatar, (30, bot_y), avatar)
        tx = 30 + avatar.size[0] + 10

    bb_auth = draw.textbbox((0, 0), AUTHOR_TEXT, font=f_author)
    auth_h  = bb_auth[3] - bb_auth[1]
    draw.text((tx, bot_y + (62 - auth_h) // 2), AUTHOR_TEXT,
              fill=(230, 228, 245, 240), font=f_author)

    bb_url = draw.textbbox((0, 0), URL_TEXT, font=f_url)
    draw.text((CARD_W - bb_url[2] - 30,
               CARD_H - bar_bot_h + (bar_bot_h - (bb_url[3] - bb_url[1])) // 2),
              URL_TEXT, fill=(130, 170, 230, 200), font=f_url)

    # ── Save ──────────────────────────────────────────────────────────────────
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
