#!/usr/bin/env python3
"""
Copy Trading Card Generator — Landscape 16:9 (1280x720)
======================================================
Generates high-impact visual cards dedicated to eToro Copy Trading:
  • Style 1 (DASHBOARD): "Community Trust & KPI Hub" (Live Copiers, Risk Score, 4 Pillars)
  • Style 2 (PROFIT_FOCUS): "100% Copiatori in Profitto" (Mega social proof & confidence badge)
  • Style 3 (HOW_IT_WORKS): "Come Funziona la Copia in 3 Passi" (Step-by-step visual onboarding)

Pulls live certified data from eToro APIs (copiers count, risk score, win ratio, historical return)
and rotates round-robin across daily copy trading post sessions.
"""

import io
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import gist_storage
    GIST_AVAILABLE = True
except ImportError:
    GIST_AVAILABLE = False

try:
    import etoro_client
    ETORO_CLIENT_AVAILABLE = True
except ImportError:
    ETORO_CLIENT_AVAILABLE = False

CARD_W = 1280
CARD_H = 720

PROFILE_PHOTO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "profile_photo.jpg"
)
FONTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "fonts"
)

URL_TEXT = "etoro.com/people/andrearavalli"
AUTHOR_TEXT = "Andrea Ravalli · Popular Investor"

# Luxury Clean Palette
C_WHITE       = (255, 255, 255, 255)
C_MUTED       = (160, 175, 200, 255)
C_DIM         = (110, 125, 150, 255)
C_GREEN       = (0, 230, 118, 255)
C_GREEN_BG    = (12, 45, 28, 220)
C_CYAN        = (56, 189, 248, 255)
C_CYAN_BG     = (15, 38, 56, 220)
C_GOLD        = (250, 204, 21, 255)
C_CARD_BG     = (18, 25, 42, 235)
C_CARD_BORDER = (40, 56, 85, 255)


def _font(size: int) -> "ImageFont.FreeTypeFont":
    paths = [
        os.path.join(FONTS_DIR, "Inter-Bold.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: continue
    return ImageFont.load_default()


def _reg_font(size: int) -> "ImageFont.FreeTypeFont":
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: continue
    return ImageFont.load_default()


def _circular_avatar(path: str, size: int = 56) -> Optional[Image.Image]:
    if not os.path.exists(path):
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
        
        frame = Image.new("RGBA", (size + 6, size + 6), (0, 0, 0, 0))
        ImageDraw.Draw(frame).ellipse([0, 0, size + 5, size + 5], outline=(0, 230, 118, 240), width=3)
        frame.paste(out, (3, 3), out)
        return frame
    except Exception:
        return None


def _create_base_canvas() -> Image.Image:
    """Create a dark slate gradient canvas with subtle spotlights."""
    base = Image.new("RGBA", (CARD_W, CARD_H), (10, 14, 26, 255))
    draw = ImageDraw.Draw(base)

    # Vertical gradient
    bg_top = (11, 16, 28)
    bg_bot = (7, 10, 20)
    for y in range(CARD_H):
        t = y / CARD_H
        r = int(bg_top[0] * (1 - t) + bg_bot[0] * t)
        g = int(bg_top[1] * (1 - t) + bg_bot[1] * t)
        b = int(bg_top[2] * (1 - t) + bg_bot[2] * t)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b, 255))

    # Glow spotlights (Emerald top-right & Cyan bottom-left)
    glow_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    for rad in range(350, 0, -15):
        a = int((350 - rad) / 350 * 22)
        gd.ellipse([CARD_W - 180 - rad, 100 - rad, CARD_W - 180 + rad, 100 + rad], fill=(0, 230, 118, a))
        gd.ellipse([140 - rad, CARD_H - 120 - rad, 140 + rad, CARD_H - 120 + rad], fill=(56, 189, 248, a))
    base = Image.alpha_composite(base, glow_layer)
    draw = ImageDraw.Draw(base)

    # Top accent bar
    for x in range(CARD_W):
        ratio = x / CARD_W
        gr = int(0 * (1 - ratio) + 56 * ratio)
        gg = int(230 * (1 - ratio) + 189 * ratio)
        gb = int(118 * (1 - ratio) + 248 * ratio)
        draw.line([(x, 0), (x, 4)], fill=(gr, gg, gb, 255))

    return base


def _draw_footer(base: Image.Image, footer_y: int = 612):
    """Draw clean branding footer with verified avatar and profile link."""
    draw = ImageDraw.Draw(base)
    draw.line([(80, footer_y), (CARD_W - 80, footer_y)], fill=(35, 48, 72, 180), width=1)

    avatar = _circular_avatar(PROFILE_PHOTO_PATH, size=52)
    if avatar:
        base.paste(avatar, (80, footer_y + 18), avatar)
        draw = ImageDraw.Draw(base)

    f_footer = _font(16)
    f_url    = _reg_font(15)

    draw.text((146, footer_y + 22), AUTHOR_TEXT, fill=C_WHITE, font=f_footer)
    draw.text((146, footer_y + 46), "Profilo Verificato eToro · Strategia Multi-Asset Globale", fill=C_MUTED, font=f_url)

    # Clean profile URL
    url_display = URL_TEXT
    url_bb = draw.textbbox((0, 0), url_display, font=f_footer)
    draw.text((CARD_W - 80 - (url_bb[2] - url_bb[0]), footer_y + 32), url_display, fill=C_GREEN, font=f_footer)


# ══════════════════════════════════════════════════════════════════════════
# STYLE 1: DASHBOARD & SOCIAL PROOF (HERO STATS + 4 PILLARS)
# ══════════════════════════════════════════════════════════════════════════

def generate_copy_dashboard_card(
    copiers_count: int = 36,
    risk_score: int = 3,
    win_rate: float = 67.6,
    historical_return: str = "+200%",
    highlight_badge: str = "100% COPIATORI IN PROFITTO",
    subtitle: str = "REPLICA AUTOMATICA · ZERO COMMISSIONI · PIENO CONTROLLO",
    output_path: str = "output/copy_trading_card.png",
) -> str:
    """Generate Style 1: Dashboard with 2 Hero Stats and 4 Key Pillars."""
    if not PIL_AVAILABLE:
        return ""

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else "output", exist_ok=True)
    base = _create_base_canvas()
    draw = ImageDraw.Draw(base)

    # Fonts
    f_header_tag = _font(14)
    f_main_title = _font(34)
    f_subtitle   = _reg_font(16)
    f_hero_num   = _font(58)
    f_hero_lbl   = _font(21)
    f_hero_sub   = _reg_font(15)
    f_badge      = _font(13)
    f_kpi_num    = _font(32)
    f_kpi_lbl    = _font(14)
    f_kpi_sub    = _reg_font(13)

    # 1. Header
    header_y = 28
    tag_text = "ETORO POPULAR INVESTOR · COPY TRADING"
    tag_bb = draw.textbbox((0, 0), tag_text, font=f_header_tag)
    tag_w = tag_bb[2] - tag_bb[0] + 42
    tag_h = 28
    tag_x = (CARD_W - tag_w) // 2
    
    tag_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    td = ImageDraw.Draw(tag_layer)
    td.rounded_rectangle([tag_x, header_y, tag_x + tag_w, header_y + tag_h], radius=14, fill=(0, 230, 118, 30), outline=(0, 230, 118, 140), width=1)
    # Green dot indicator inside tag
    td.ellipse([tag_x + 14, header_y + 10, tag_x + 22, header_y + 18], fill=C_GREEN)
    base = Image.alpha_composite(base, tag_layer)
    draw = ImageDraw.Draw(base)
    draw.text((tag_x + 28, header_y + 6), tag_text, fill=C_GREEN, font=f_header_tag)

    main_title = "TRASPARENZA & NUMERI DELLA COMMUNITY"
    mt_bb = draw.textbbox((0, 0), main_title, font=f_main_title)
    draw.text(((CARD_W - (mt_bb[2] - mt_bb[0])) // 2, header_y + 36), main_title, fill=C_WHITE, font=f_main_title)

    st_bb = draw.textbbox((0, 0), subtitle, font=f_subtitle)
    draw.text(((CARD_W - (st_bb[2] - st_bb[0])) // 2, header_y + 80), subtitle, fill=C_MUTED, font=f_subtitle)

    draw.line([(80, 148), (CARD_W - 80, 148)], fill=(35, 48, 72, 180), width=1)

    # 2. Hero KPI Cards
    hero_y = 168
    hero_w = 545
    hero_h = 220
    hero_gap = 30
    left_x = (CARD_W - (hero_w * 2 + hero_gap)) // 2
    right_x = left_x + hero_w + hero_gap

    box_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(box_layer)
    bd.rounded_rectangle([left_x - 1, hero_y - 1, left_x + hero_w + 1, hero_y + hero_h + 1], radius=18, fill=(0, 230, 118, 35))
    bd.rounded_rectangle([left_x, hero_y, left_x + hero_w, hero_y + hero_h], radius=18, fill=C_GREEN_BG, outline=(0, 230, 118, 160), width=2)
    bd.rounded_rectangle([right_x - 1, hero_y - 1, right_x + hero_w + 1, hero_y + hero_h + 1], radius=18, fill=(56, 189, 248, 35))
    bd.rounded_rectangle([right_x, hero_y, right_x + hero_w, hero_y + hero_h], radius=18, fill=C_CYAN_BG, outline=(56, 189, 248, 160), width=2)

    base = Image.alpha_composite(base, box_layer)
    draw = ImageDraw.Draw(base)

    # Content Left Hero
    badge_txt = f"{highlight_badge}"
    b_bb = draw.textbbox((0, 0), badge_txt, font=f_badge)
    b_w = b_bb[2] - b_bb[0] + 24
    b_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(b_layer)
    bd.rounded_rectangle([left_x + 24, hero_y + 20, left_x + 24 + b_w, hero_y + 46], radius=13, fill=(0, 230, 118, 45), outline=C_GREEN, width=1)
    base = Image.alpha_composite(base, b_layer)
    draw = ImageDraw.Draw(base)
    draw.text((left_x + 36, hero_y + 26), badge_txt, fill=C_GREEN, font=f_badge)

    draw.text((left_x + 24, hero_y + 58), f"{copiers_count}", fill=C_WHITE, font=f_hero_num)
    draw.text((left_x + 24 + draw.textbbox((0, 0), f"{copiers_count}", font=f_hero_num)[2] + 16, hero_y + 76), "COPIATORI ATTIVI", fill=C_GREEN, font=f_hero_lbl)
    draw.text((left_x + 24, hero_y + 138), "• Investitori reali che replicano ogni operazione in tempo reale.", fill=C_MUTED, font=f_hero_sub)
    draw.text((left_x + 24, hero_y + 164), "• Replicazione proporzionale automatica 1:1 con zero commissioni.", fill=C_MUTED, font=f_hero_sub)

    # Content Right Hero
    r_badge_txt = "GESTIONE DEL RISCHIO DISCIPLINATA"
    rb_bb = draw.textbbox((0, 0), r_badge_txt, font=f_badge)
    rb_w = rb_bb[2] - rb_bb[0] + 24
    rb_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    rbd = ImageDraw.Draw(rb_layer)
    rbd.rounded_rectangle([right_x + 24, hero_y + 20, right_x + 24 + rb_w, hero_y + 46], radius=13, fill=(56, 189, 248, 45), outline=C_CYAN, width=1)
    base = Image.alpha_composite(base, rb_layer)
    draw = ImageDraw.Draw(base)
    draw.text((right_x + 36, hero_y + 26), r_badge_txt, fill=C_CYAN, font=f_badge)

    draw.text((right_x + 24, hero_y + 58), f"{risk_score}/10", fill=C_WHITE, font=f_hero_num)
    draw.text((right_x + 24 + draw.textbbox((0, 0), f"{risk_score}/10", font=f_hero_num)[2] + 16, hero_y + 76), "RISK SCORE (BASSO)", fill=C_CYAN, font=f_hero_lbl)
    draw.text((right_x + 24, hero_y + 138), "• 100% azioni reali ed ETF fisici, zero leva finanziaria.", fill=C_MUTED, font=f_hero_sub)
    draw.text((right_x + 24, hero_y + 164), "• Protezione del capitale e controllo rigoroso della volatilità.", fill=C_MUTED, font=f_hero_sub)

    # 3. Four Lower Pillars
    kpi_y = 412
    kpi_gap = 18
    total_kpi_w = CARD_W - 160
    kpi_w = (total_kpi_w - (kpi_gap * 3)) // 4
    kpi_h = 160

    kpis = [
        {"num": historical_return, "num_color": C_GREEN, "title": "TRACK RECORD", "desc": "Rendimento totale dal 2020 (~18% CAGR annuo)"},
        {"num": f"{win_rate:.1f}%", "num_color": C_CYAN, "title": "WIN RATIO", "desc": "Percentuale posizioni chiuse in profitto"},
        {"num": "100%", "num_color": C_GOLD, "title": "ALLINEAMENTO", "desc": "Investo il mio capitale nelle stesse quote"},
        {"num": "$200", "num_color": C_WHITE, "title": "MINIMO COPIA", "desc": "Consigliati $500+ per replica completa"},
    ]

    cards_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cards_layer)
    for i, kpi in enumerate(kpis):
        cx = 80 + i * (kpi_w + kpi_gap)
        cd.rounded_rectangle([cx, kpi_y, cx + kpi_w, kpi_y + kpi_h], radius=14, fill=C_CARD_BG, outline=C_CARD_BORDER, width=1)
    base = Image.alpha_composite(base, cards_layer)
    draw = ImageDraw.Draw(base)

    for i, kpi in enumerate(kpis):
        cx = 80 + i * (kpi_w + kpi_gap)
        draw.text((cx + 18, kpi_y + 16), kpi["title"], fill=C_DIM, font=f_kpi_lbl)
        draw.text((cx + 18, kpi_y + 42), kpi["num"], fill=kpi["num_color"], font=f_kpi_num)
        words = kpi["desc"].split()
        l1, l2 = "", ""
        for w in words:
            if len(l1) + len(w) < 22 and not l2: l1 += (w + " ")
            else: l2 += (w + " ")
        draw.text((cx + 18, kpi_y + 96), l1.strip(), fill=C_MUTED, font=f_kpi_sub)
        if l2: draw.text((cx + 18, kpi_y + 118), l2.strip(), fill=C_MUTED, font=f_kpi_sub)

    # 4. Footer
    _draw_footer(base, footer_y=612)

    base.convert("RGB").save(output_path, "PNG", quality=95)
    return output_path


# ══════════════════════════════════════════════════════════════════════════
# STYLE 2: PROFIT & SOCIAL PROOF HERO ("100% DEI COPIATORI IN PROFITTO")
# ══════════════════════════════════════════════════════════════════════════

def generate_copy_profit_focus_card(
    copiers_count: int = 36,
    risk_score: int = 3,
    win_rate: float = 67.6,
    historical_return: str = "+200%",
    output_path: str = "output/copy_trading_card_profit.png",
) -> str:
    """Generate Style 2: High impact 100% Copiatori in profitto focus card."""
    if not PIL_AVAILABLE:
        return ""

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else "output", exist_ok=True)
    base = _create_base_canvas()
    draw = ImageDraw.Draw(base)

    f_top_tag = _font(14)
    f_mega_num = _font(54)
    f_hero_desc= _reg_font(18)
    f_col_num  = _font(36)
    f_col_lbl  = _font(16)
    f_col_sub  = _reg_font(14)

    # 1. Header tag
    header_y = 28
    tag_text = "ETORO POPULAR INVESTOR · STATISTICHE VERIFICATE"
    tag_bb = draw.textbbox((0, 0), tag_text, font=f_top_tag)
    tag_w = tag_bb[2] - tag_bb[0] + 42
    tag_x = (CARD_W - tag_w) // 2
    
    tag_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    td = ImageDraw.Draw(tag_layer)
    td.rounded_rectangle([tag_x, header_y, tag_x + tag_w, header_y + 28], radius=14, fill=(0, 230, 118, 30), outline=(0, 230, 118, 140), width=1)
    td.ellipse([tag_x + 14, header_y + 10, tag_x + 22, header_y + 18], fill=C_GREEN)
    base = Image.alpha_composite(base, tag_layer)
    draw = ImageDraw.Draw(base)
    draw.text((tag_x + 28, header_y + 6), tag_text, fill=C_GREEN, font=f_top_tag)

    # 2. Mega Hero Card (Top Banner)
    mega_y = 78
    mega_w = CARD_W - 160
    mega_h = 220
    mega_x = 80

    mega_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    md = ImageDraw.Draw(mega_layer)
    md.rounded_rectangle([mega_x - 1, mega_y - 1, mega_x + mega_w + 1, mega_y + mega_h + 1], radius=20, fill=(0, 230, 118, 40))
    md.rounded_rectangle([mega_x, mega_y, mega_x + mega_w, mega_y + mega_h], radius=20, fill=C_GREEN_BG, outline=C_GREEN, width=2)
    base = Image.alpha_composite(base, mega_layer)
    draw = ImageDraw.Draw(base)

    badge_hero = "TRAGUARDO COMMUNITY ETORO"
    draw.text((mega_x + 36, mega_y + 24), badge_hero, fill=C_GOLD, font=_font(13))
    
    mega_title = "100% DEI COPIATORI IN PROFITTO"
    draw.text((mega_x + 36, mega_y + 54), mega_title, fill=C_WHITE, font=f_mega_num)
    
    mega_desc1 = f"• Tutti i {copiers_count} investitori che copiano attualmente il portafoglio registrano un saldo positivo."
    mega_desc2 = "• Risultato ottenuto grazie a un approccio disciplinato, zero leva e selezione di aziende di qualità globale."
    draw.text((mega_x + 36, mega_y + 132), mega_desc1, fill=C_WHITE, font=f_hero_desc)
    draw.text((mega_x + 36, mega_y + 164), mega_desc2, fill=C_MUTED, font=f_hero_desc)

    # 3. Three Comparison / Pillar Boxes
    box_y = 325
    box_gap = 24
    box_w = (mega_w - (box_gap * 2)) // 3
    box_h = 255

    cols = [
        {
            "badge": "FIDUCIA COMMUNITY",
            "val": f"{copiers_count} Investitori",
            "val_color": C_GREEN,
            "title": "Copia Istantanea 1:1",
            "d1": "Replicazione automatica in tempo reale.",
            "d2": "Minimo $200 (consigliati $500+).",
            "d3": "Zero commissioni di gestione.",
        },
        {
            "badge": "PROTEZIONE CAPITALE",
            "val": f"Risk {risk_score}/10",
            "val_color": C_CYAN,
            "title": "Basso Rischio & No Leva",
            "d1": "100% azioni reali ed ETF fisici.",
            "d2": "Zero CFD a leva speculativa.",
            "d3": "Controllo rigoroso del Max DD.",
        },
        {
            "badge": "STORICO COMPROVATO",
            "val": f"{historical_return} dal 2020",
            "val_color": C_GOLD,
            "title": f"Win Rate {win_rate:.1f}%",
            "d1": "~18% CAGR annuo composto.",
            "d2": "Oltre 8 anni di presenza su eToro.",
            "d3": "Investo il mio capitale personale.",
        },
    ]

    col_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(col_layer)
    for i in range(3):
        cx = mega_x + i * (box_w + box_gap)
        cd.rounded_rectangle([cx, box_y, cx + box_w, box_y + box_h], radius=16, fill=C_CARD_BG, outline=C_CARD_BORDER, width=1)
    base = Image.alpha_composite(base, col_layer)
    draw = ImageDraw.Draw(base)

    for i, col in enumerate(cols):
        cx = mega_x + i * (box_w + box_gap)
        draw.text((cx + 24, box_y + 20), col["badge"], fill=C_DIM, font=_font(13))
        draw.text((cx + 24, box_y + 44), col["val"], fill=col["val_color"], font=f_col_num)
        draw.text((cx + 24, box_y + 96), col["title"], fill=C_WHITE, font=f_col_lbl)
        
        draw.text((cx + 24, box_y + 134), f"• {col['d1']}", fill=C_MUTED, font=f_col_sub)
        draw.text((cx + 24, box_y + 164), f"• {col['d2']}", fill=C_MUTED, font=f_col_sub)
        draw.text((cx + 24, box_y + 194), f"• {col['d3']}", fill=C_MUTED, font=f_col_sub)

    # 4. Footer
    _draw_footer(base, footer_y=612)

    base.convert("RGB").save(output_path, "PNG", quality=95)
    return output_path


# ══════════════════════════════════════════════════════════════════════════
# STYLE 3: HOW IT WORKS STEP-BY-STEP (ONBOARDING & EDUCATIONAL)
# ══════════════════════════════════════════════════════════════════════════

def generate_copy_steps_card(
    copiers_count: int = 36,
    risk_score: int = 3,
    win_rate: float = 67.6,
    historical_return: str = "+200%",
    output_path: str = "output/copy_trading_card_steps.png",
) -> str:
    """Generate Style 3: Visual 3-step onboarding guide."""
    if not PIL_AVAILABLE:
        return ""

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else "output", exist_ok=True)
    base = _create_base_canvas()
    draw = ImageDraw.Draw(base)

    f_top_tag = _font(14)
    f_main_title = _font(34)
    f_sub = _reg_font(16)
    f_step_title = _font(20)
    f_step_body = _reg_font(15)

    # 1. Header
    header_y = 28
    tag_text = "GUIDA RAPIDA · COME FUNZIONA IL COPY TRADING"
    tag_bb = draw.textbbox((0, 0), tag_text, font=f_top_tag)
    tag_w = tag_bb[2] - tag_bb[0] + 42
    tag_x = (CARD_W - tag_w) // 2
    
    tag_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    td = ImageDraw.Draw(tag_layer)
    td.rounded_rectangle([tag_x, header_y, tag_x + tag_w, header_y + 28], radius=14, fill=(0, 230, 118, 30), outline=(0, 230, 118, 140), width=1)
    td.ellipse([tag_x + 14, header_y + 10, tag_x + 22, header_y + 18], fill=C_GREEN)
    base = Image.alpha_composite(base, tag_layer)
    draw = ImageDraw.Draw(base)
    draw.text((tag_x + 28, header_y + 6), tag_text, fill=C_GREEN, font=f_top_tag)

    main_title = "COPIA IL PORTAFOGLIO IN 3 SEMPLICI PASSI"
    mt_bb = draw.textbbox((0, 0), main_title, font=f_main_title)
    draw.text(((CARD_W - (mt_bb[2] - mt_bb[0])) // 2, header_y + 36), main_title, fill=C_WHITE, font=f_main_title)

    sub_txt = f"{copiers_count} Copiatori Attivi  ·  Risk Score {risk_score}/10  ·  {historical_return} dal 2020  ·  Win Rate {win_rate:.1f}%"
    st_bb = draw.textbbox((0, 0), sub_txt, font=f_sub)
    draw.text(((CARD_W - (st_bb[2] - st_bb[0])) // 2, header_y + 80), sub_txt, fill=C_MUTED, font=f_sub)

    draw.line([(80, 145), (CARD_W - 80, 145)], fill=(35, 48, 72, 180), width=1)

    # 2. Three Step Cards
    step_y = 168
    step_gap = 26
    total_w = CARD_W - 160
    step_w = (total_w - (step_gap * 2)) // 3
    step_h = 415

    steps = [
        {
            "step": "PASSO 1",
            "title": "Scegli l'Importo",
            "color": C_GREEN,
            "badge": "Minimo $200 (consigliati $500+)",
            "p1": "Puoi iniziare a copiare con qualsiasi cifra a partire da $200.",
            "p2": "Zero costi di gestione: la copia su eToro è completamente gratuita.",
            "p3": "Il tuo capitale resta sempre nel tuo conto privato, intestato a te.",
        },
        {
            "step": "PASSO 2",
            "title": "Replica Automatica",
            "color": C_CYAN,
            "badge": "Replicazione 1:1 in tempo reale",
            "p1": "Ogni acquisto o ribilanciamento si clona istantaneamente.",
            "p2": "Stesse percentuali e pesi, in proporzione esatta al tuo capitale.",
            "p3": "Zero stress operativo: non devi monitorare i mercati ogni minuto.",
        },
        {
            "step": "PASSO 3",
            "title": "Pieno Controllo",
            "color": C_GOLD,
            "badge": "Libertà & Liquidità immediata",
            "p1": "Puoi aggiungere o ritirare fondi in qualsiasi momento con un click.",
            "p2": "Puoi mettere in pausa o chiudere la copia all'istante, senza penali.",
            "p3": "Trasparenza totale su ogni singola posizione aperta.",
        },
    ]

    steps_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(steps_layer)

    for i, s in enumerate(steps):
        sx = 80 + i * (step_w + step_gap)
        sd.rounded_rectangle([sx, step_y, sx + step_w, step_y + step_h], radius=18, fill=C_CARD_BG, outline=C_CARD_BORDER, width=1)
        sd.rounded_rectangle([sx + 20, step_y + 20, sx + 120, step_y + 50], radius=15, fill=(*s["color"][:3], 35), outline=s["color"], width=1)

    base = Image.alpha_composite(base, steps_layer)
    draw = ImageDraw.Draw(base)

    for i, s in enumerate(steps):
        sx = 80 + i * (step_w + step_gap)
        draw.text((sx + 34, step_y + 26), s["step"], fill=s["color"], font=_font(14))
        draw.text((sx + 20, step_y + 68), s["title"], fill=C_WHITE, font=f_step_title)
        draw.text((sx + 20, step_y + 110), s["badge"], fill=s["color"], font=_font(13))
        draw.line([(sx + 20, step_y + 140), (sx + step_w - 20, step_y + 140)], fill=(40, 56, 85, 180), width=1)

        def _draw_wrapped(text, y_pos):
            words = text.split()
            lines = []
            curr = ""
            for w in words:
                if len(curr) + len(w) < 28: curr += (w + " ")
                else:
                    lines.append(curr.strip())
                    curr = w + " "
            if curr: lines.append(curr.strip())
            for line in lines:
                draw.text((sx + 20, y_pos), line, fill=C_MUTED, font=f_step_body)
                y_pos += 22
            return y_pos + 12

        y = step_y + 160
        y = _draw_wrapped(f"• {s['p1']}", y)
        y = _draw_wrapped(f"• {s['p2']}", y)
        y = _draw_wrapped(f"• {s['p3']}", y)

    # 3. Footer
    _draw_footer(base, footer_y=612)

    base.convert("RGB").save(output_path, "PNG", quality=95)
    return output_path


# ══════════════════════════════════════════════════════════════════════════
# AUTOMATIC ROTATION & LIVE DATA DISPATCHER
# ══════════════════════════════════════════════════════════════════════════

def generate_copy_card_auto(
    rankings_data: Optional[Dict[str, Any]] = None,
    portfolio_perf: Optional[float] = None,
    style: Optional[str] = None,
    output_path: str = "output/copy_trading_card.png",
) -> str:
    """
    Auto-generate the most fitting Copy Trading card with live metrics from eToro.
    Pulls live data if rankings_data is missing.
    Rotates styles round-robin using Gist storage tracking across daily sessions.
    """
    # 1. Fetch live rankings from eToro API if not already provided
    if not rankings_data and ETORO_CLIENT_AVAILABLE:
        try:
            if etoro_client.is_configured():
                rankings_data = etoro_client.fetch_trader_rankings(period="CurrYear")
        except Exception as e:
            print(f"⚠️ Could not fetch live rankings for copy trading card: {e}")

    copiers = 36
    risk = 3
    win_rate = 67.6
    
    if rankings_data:
        copiers = rankings_data.get("copiers", copiers)
        risk = rankings_data.get("riskScore", risk)
        win_rate = rankings_data.get("winRatio", win_rate)

    hist_return = "+200%"
    if portfolio_perf is not None:
        sign = "+" if portfolio_perf >= 0 else ""
        hist_return = f"{sign}{portfolio_perf:.1f}%"

    # 2. Determine Style Rotation (Gist round-robin counter, with weekday fallback)
    if not style:
        if GIST_AVAILABLE:
            try:
                style = gist_storage.get_next_copy_card_style()
            except Exception:
                style = None

        if not style:
            weekday = datetime.utcnow().weekday()
            if weekday in (0, 2, 4): style = "dashboard"
            elif weekday in (1, 5): style = "profit"
            else: style = "steps"

    print(f"🔄 Generating Copy Trading Card [Style: {style}] | Copiers: {copiers} | Risk: {risk} | Win Rate: {win_rate:.1f}% | Return: {hist_return}")

    if style == "profit":
        return generate_copy_profit_focus_card(
            copiers_count=copiers,
            risk_score=risk,
            win_rate=win_rate,
            historical_return=hist_return,
            output_path=output_path,
        )
    elif style == "steps":
        return generate_copy_steps_card(
            copiers_count=copiers,
            risk_score=risk,
            win_rate=win_rate,
            historical_return=hist_return,
            output_path=output_path,
        )
    else:
        return generate_copy_dashboard_card(
            copiers_count=copiers,
            risk_score=risk,
            win_rate=win_rate,
            historical_return=hist_return,
            highlight_badge="100% COPIATORI IN PROFITTO",
            subtitle="REPLICA AUTOMATICA · ZERO COMMISSIONI · PIENO CONTROLLO",
            output_path=output_path,
        )


def generate_all_demo_cards():
    """Generate all 3 styles to test and preview."""
    generate_copy_dashboard_card(output_path="output/copy_trading_card_dashboard.png")
    generate_copy_profit_focus_card(output_path="output/copy_trading_card_profit.png")
    generate_copy_steps_card(output_path="output/copy_trading_card_steps.png")
    print("✅ All 3 Copy Trading card variations generated in output/")


if __name__ == "__main__":
    generate_all_demo_cards()
