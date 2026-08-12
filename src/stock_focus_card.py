#!/usr/bin/env python3
"""
Stock Focus Card Generator — Landscape 16:9 (1280x720)
======================================================
Generates a modern, high-contrast 1280x720 landscape card for single-stock deep dives:
  • Circular company logo badge with cyan neon glow
  • Ticker cashtag (e.g. $PLTR) + Company Name
  • Sector / Industry pill
  • Portfolio weight & allocation badge
  • 3 Key Focus pillars: Business Model, Bullish Catalyst, Risk / Key Factor
  • Author branding: Andrea Ravalli — Popular Investor
"""

import io
import os
import time
import hashlib
from typing import Dict, Any, Optional

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
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
AUTHOR_TEXT = "Andrea Ravalli · Popular Investor"

TICKER_THEMES = {
    "PLTR": {"sector": "Enterprise AI & Difesa Governativo", "domain": "palantir.com", "thesis": "Dominio nei contratti governativi US e rapida espansione commerciale con AIP.", "color": (0, 220, 255)},
    "NVDA": {"sector": "Chip AI & Acceleratori Grafici", "domain": "nvidia.com", "thesis": "Monopolio dell'ecosistema CUDA e architetture Blackwell per data center.", "color": (118, 185, 0)},
    "MSFT": {"sector": "Cloud Azure & Software Enterprise", "domain": "microsoft.com", "thesis": "Integrazione di OpenAI in tutto l'ecosistema Windows, Office e Azure.", "color": (0, 164, 239)},
    "AMZN": {"sector": "E-Commerce Globale & Cloud AWS", "domain": "amazon.com", "thesis": "Leadership assoluta di AWS e margini in forte espansione dalla pubblicità.", "color": (255, 153, 0)},
    "GOOG": {"sector": "Search, Cloud & Intelligenza Artificiale", "domain": "google.com", "thesis": "Fossato difensivo nei motori di ricerca, YouTube e crescita di Google Cloud.", "color": (66, 133, 244)},
    "CCJ":  {"sector": "Uranio & Combustibile Nucleare", "domain": "cameco.com", "thesis": "Deficit strutturale di offerta globale di uranio per la transizione nucleare.", "color": (255, 180, 0)},
    "URNM": {"sector": "ETF Uranio & Minerari Nucleari", "domain": "sprott.com", "thesis": "Esposizione diversificata ai principali produttori e detentori fisici di uranio.", "color": (255, 160, 50)},
    "LLY":  {"sector": "Farmaceutica & Trattamenti GLP-1", "domain": "lilly.com", "thesis": "Leadership nei farmaci antidiabete e obesità con Mounjaro e Zepbound.", "color": (230, 40, 40)},
    "NOVO-B.CO": {"sector": "Biotecnologie & Cura del Diabete", "domain": "novonordisk.com", "thesis": "Pioniere mondiale del GLP-1 con Ozempic e Wegovy, forte pipeline clinica.", "color": (0, 110, 200)},
    "SX7PEX.DE": {"sector": "ETF Bancario Europeo", "domain": "stoxx.com", "thesis": "Elevati dividendi, solidità patrimoniale e redditività da tassi d'interesse.", "color": (70, 130, 240)},
    "MELI": {"sector": "E-Commerce & Fintech America Latina", "domain": "mercadolibre.com", "thesis": "Leader indiscusso del commercio elettronico e dei pagamenti con Mercado Pago.", "color": (255, 220, 0)},
    "ASML.AS": {"sector": "Litografia EUV per Semiconduttori", "domain": "asml.com", "thesis": "Monopolio mondiale nei macchinari litografici a ultravioletti estremi.", "color": (15, 45, 140)},
    "TSM":  {"sector": "Fonderia di Chip Avanzati", "domain": "tsmc.com", "thesis": "Produce oltre il 90% dei chip più avanzati al mondo a 3nm e 2nm.", "color": (220, 50, 50)},
    "AVGO": {"sector": "Chip Custom & Networking AI", "domain": "broadcom.com", "thesis": "Dominio negli switch per cluster AI e integrazione strategica di VMware.", "color": (204, 0, 0)},
    "MBG.DE": {"sector": "Auto di Lusso & Premium Mobility", "domain": "mercedes-benz.com", "thesis": "Potere di prezzo nei segmenti top-end, transizione elettrica e dividendi.", "color": (160, 175, 190)},
    "0005.HK": {"sector": "Banca Globale & Wealth Management Asia", "domain": "hsbc.com", "thesis": "Hub finanziario chiave per i flussi di capitale tra Europa e Asia.", "color": (219, 0, 17)},
    "1211.HK": {"sector": "Veicoli Elettrici & Batterie EV", "domain": "byd.com", "thesis": "Integrazione verticale completa dalle batterie alla produzione su larga scala.", "color": (30, 144, 255)},
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


def _fetch_logo(ticker: str, domain: str = None) -> Optional[Image.Image]:
    """Fetch high-res logo from committed assets/logos/, cache, or remote."""
    if not PIL_AVAILABLE or not REQUESTS_AVAILABLE:
        return None
    clean = ticker.replace("$", "").strip().upper()
    base_sym = clean.split(".")[0]

    # 1. Check committed assets/logos/
    for check_sym in [clean, base_sym, f"{clean}.US" if "." not in clean else None]:
        if not check_sym:
            continue
        repo_path = os.path.join(LOGO_DIR, f"{check_sym}.png")
        if os.path.exists(repo_path) and os.path.getsize(repo_path) > 200:
            try:
                return Image.open(repo_path).convert("RGBA")
            except Exception:
                pass

    # 2. Check assets/logo_cache/
    os.makedirs(LOGO_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(LOGO_CACHE_DIR, f"{clean}.png")
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 200:
        try:
            return Image.open(cache_path).convert("RGBA")
        except Exception:
            pass

    # 3. Remote fetch via logo providers
    if not domain:
        domain = TICKER_THEMES.get(clean, {}).get("domain", f"{clean.lower()}.com")

    urls = [
        f"https://img.logo.dev/{domain}?token=pk_anonymous&size=160&format=png",
        f"https://cdn.tickerlogos.com/{domain}",
    ]
    for url in urls:
        try:
            resp = _requests.get(url, timeout=3)
            if resp.status_code == 200 and len(resp.content) > 300:
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                img.save(cache_path)
                return img
        except Exception:
            continue
    return None


def generate_stock_focus_card(
    ticker: str,
    company_name: str = None,
    weight_pct: float = None,
    output_path: str = "output/stock_focus.png",
) -> str:
    """
    Generate a 1280x720 16:9 Stock Focus Card.
    """
    if not PIL_AVAILABLE:
        print("⚠️ PIL not available for stock focus card generation")
        return output_path

    info = TICKER_THEMES.get(ticker, {
        "sector": "Azienda in Portafoglio",
        "domain": f"{ticker.lower()}.com",
        "thesis": "Titolo selezionato con tesi di crescita fondamentale e vantaggio competitivo.",
        "color": (0, 200, 255),
    })

    theme_color = info.get("color", (0, 200, 255))
    sector_name = info.get("sector", "Settore")
    thesis_text = info.get("thesis", "")
    comp_name = company_name or ticker

    # 1. Base Canvas (Dark Navy Gradient)
    img = Image.new("RGBA", (CARD_W, CARD_H), (8, 11, 24, 255))
    draw = ImageDraw.Draw(img)

    # Subtle background ambient glow on left
    glow_overlay = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_overlay)
    glow_draw.ellipse([(-100, -100), (550, 550)], fill=(*theme_color[:3], 35))
    glow_draw.ellipse([(800, 300), (1400, 800)], fill=(19, 198, 54, 25))
    glow_overlay = glow_overlay.filter(ImageFilter.GaussianBlur(radius=60))
    img = Image.alpha_composite(img, glow_overlay)
    draw = ImageDraw.Draw(img)

    # 2. Header Bar
    f_badge = _font(15)
    f_title = _font(34)
    f_ticker = _font(42)
    f_subtitle = _reg_font(18)
    f_body = _reg_font(19)
    f_label = _font(14)
    f_author = _font(16)
    f_url = _reg_font(15)

    # Top Tag
    badge_text = "🔍 FOCUS ASSET · ANALISI TITOLO"
    draw.rounded_rectangle([60, 42, 380, 74], radius=16, fill=(20, 32, 60, 220), outline=(*theme_color[:3], 140), width=1)
    draw.text((80, 50), badge_text, fill=(*theme_color[:3], 255), font=f_badge)

    if weight_pct is not None:
        w_text = f"PESO PORTAFOGLIO: {weight_pct:.2f}%"
        draw.rounded_rectangle([400, 42, 680, 74], radius=16, fill=(19, 198, 54, 30), outline=(19, 198, 54, 150), width=1)
        draw.text((420, 50), w_text, fill=(19, 198, 54, 255), font=f_badge)

    # 3. Main Center Card
    card_x, card_y, card_w, card_h = 60, 95, 1160, 520
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=24, fill=(13, 19, 38, 235), outline=(255, 255, 255, 28), width=1)

    # Logo Badge (Left Circle)
    logo_cx, logo_cy, logo_r = card_x + 100, card_y + 110, 68
    draw.ellipse([logo_cx - logo_r - 4, logo_cy - logo_r - 4, logo_cx + logo_r + 4, logo_cy + logo_r + 4], outline=(*theme_color[:3], 180), width=3)
    draw.ellipse([logo_cx - logo_r, logo_cy - logo_r, logo_cx + logo_r, logo_cy + logo_r], fill=(22, 28, 52, 255))

    logo = _fetch_logo(ticker, info.get("domain"))
    if logo:
        logo_resized = logo.resize((logo_r * 2 - 24, logo_r * 2 - 24), Image.Resampling.LANCZOS)
        # Paste centered
        img.paste(logo_resized, (logo_cx - logo_r + 12, logo_cy - logo_r + 12), logo_resized)
    else:
        # Ticker fallback
        draw.text((logo_cx - 30, logo_cy - 16), ticker[:3], fill=(255, 255, 255, 240), font=_font(26))

    # Ticker & Name
    draw.text((card_x + 200, card_y + 60), f"${ticker}", fill=(*theme_color[:3], 255), font=f_ticker)
    draw.text((card_x + 200, card_y + 115), comp_name, fill=(255, 255, 255, 250), font=f_title)
    draw.text((card_x + 200, card_y + 160), f"Settore: {sector_name}", fill=(160, 175, 205, 230), font=f_subtitle)

    # Divider line
    draw.line([(card_x + 40, card_y + 215), (card_x + card_w - 40, card_y + 215)], fill=(255, 255, 255, 25), width=1)

    # 4. Thesis & Highlights Boxes (3 columns)
    col_w = (card_w - 80 - 40) // 2
    
    # Left Column: Tesi di Investimento & Catalizzatori
    bx1, by1 = card_x + 40, card_y + 235
    draw.rounded_rectangle([bx1, by1, bx1 + col_w, by1 + 245], radius=16, fill=(18, 26, 52, 180), outline=(*theme_color[:3], 90), width=1)
    draw.text((bx1 + 22, by1 + 20), "💡 PERCHÉ È IN PORTAFOGLIO", fill=(*theme_color[:3], 255), font=f_label)
    
    # Wrap text for thesis
    words = thesis_text.split()
    lines, current_line = [], ""
    for w in words:
        test_line = (current_line + " " + w).strip()
        bb = draw.textbbox((0, 0), test_line, font=f_body)
        if bb[2] - bb[0] < col_w - 44:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = w
    if current_line:
        lines.append(current_line)

    ty = by1 + 55
    for l in lines[:5]:
        draw.text((bx1 + 22, ty), l, fill=(230, 235, 245, 240), font=f_body)
        ty += 30

    # Right Column: Gestione Rischio & Orizzonte
    bx2 = bx1 + col_w + 40
    draw.rounded_rectangle([bx2, by1, bx2 + col_w, by1 + 245], radius=16, fill=(18, 26, 52, 180), outline=(19, 198, 54, 90), width=1)
    draw.text((bx2 + 22, by1 + 20), "🎯 ORIZZONTE & DISCIPLINA", fill=(19, 198, 54, 255), font=f_label)

    bullets = [
        ("Strategia:", "Accumulo sui ribassi e posizionamento long-term."),
        ("Orizzonte:", "Multi-annuale con ribilanciamento periodico."),
        ("Fattore chiave:", "Solidità dei flussi di cassa e margini operativi."),
    ]
    ry = by1 + 55
    for b_title, b_desc in bullets:
        draw.text((bx2 + 22, ry), f"• {b_title}", fill=(255, 255, 255, 240), font=_font(17))
        draw.text((bx2 + 22, ry + 24), b_desc, fill=(160, 175, 205, 230), font=_reg_font(16))
        ry += 58

    # 5. Footer Branding
    bot_y = CARD_H - 75
    draw.text((60, bot_y + 12), f"👤 {AUTHOR_TEXT}", fill=(230, 230, 245, 230), font=f_author)
    bb_url = draw.textbbox((0, 0), URL_TEXT, font=f_url)
    draw.text((CARD_W - (bb_url[2] - bb_url[0]) - 60, bot_y + 12), URL_TEXT, fill=(140, 175, 235, 210), font=f_url)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.convert("RGB").save(output_path, "PNG", optimize=True)
    print(f"✅ Stock Focus card generated: {output_path}")
    return output_path
