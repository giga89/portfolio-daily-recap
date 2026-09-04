#!/usr/bin/env python3
"""
Dividend Cash Flow Card Generator — Landscape 16:9 (1280x720)
=============================================================
Generates a modern, high-contrast 1280x720 landscape card for dividend pay days:
  • Circular antialiased company logo badge with emerald & gold neon glow
  • Ticker cashtag (e.g. $WMT, $ENI.MI, $TRIG.L) + Company Name + Sector
  • Portfolio weight & allocation badge
  • 4 high-contrast KPI boxes:
      1. Dividend Per Share (DPS) & Payment Confirmation
      2. Dividend Yield & Cash Flow Sustainability
      3. 100% Automatic Reinvestment (Compounding Effect)
      4. Strategic Role & Capital Preservation
  • Author branding: Andrea Ravalli — Popular Investor
"""

import io
import os
import time
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

from stock_focus_card import TICKER_THEMES, _fetch_logo, _font, _reg_font

CARD_W = 1280
CARD_H = 720

URL_TEXT = "etoro.com/people/andrearavalli"
AUTHOR_TEXT = "Andrea Ravalli · Popular Investor"

# Colors
C_BG = (8, 11, 24)
C_CARD = (13, 19, 38)
C_BOX = (18, 26, 52)
C_GREEN = (0, 230, 118)
C_GREEN_TINT = (16, 42, 28)
C_GOLD = (255, 215, 0)
C_GOLD_TINT = (48, 40, 18)
C_CYAN = (0, 220, 255)
C_CYAN_TINT = (18, 34, 58)
C_WHITE = (255, 255, 255)
C_MUTED = (160, 175, 205)
C_BORDER = (35, 48, 76)


def generate_dividend_card(
    ticker: str,
    company_name: Optional[str] = None,
    pay_date: str = "Sep 08, 2026",
    dps_amount: Optional[str] = None,
    div_yield: Optional[str] = None,
    reinvest_note: Optional[str] = None,
    strategic_role: Optional[str] = None,
    weight_pct: Optional[float] = None,
    output_path: str = "output/dividend_card.png",
    lang: str = "it",
) -> str:
    """
    Generate a 1280x720 landscape Dividend Pay Day Card.
    """
    if not PIL_AVAILABLE:
        print("⚠️ PIL not available for dividend card generation")
        return output_path

    info = TICKER_THEMES.get(ticker, {
        "sector": "Azienda in Portafoglio",
        "domain": f"{ticker.lower()}.com",
        "thesis": "Titolo generatore di flussi di cassa solidi e dividendi sostenibili.",
        "color": (0, 230, 118),
    })

    theme_color = info.get("color", (0, 230, 118))
    sector_name = info.get("sector", "Settore")
    comp_name = company_name or ticker

    # Defaults
    dps_val = dps_amount or "$0.25 / azione"
    yield_val = div_yield or "1.28%"
    reinvest_val = reinvest_note or "100% dei proventi viene automaticamente reinvestito nel portafoglio per accelerare l'interesse composto senza commissioni."
    strat_val = strategic_role or "Generazione di cassa reale che protegge il portafoglio nei cicli di mercato e fornisce liquidità costante."

    # 1. Base Canvas
    img = Image.new("RGBA", (CARD_W, CARD_H), (*C_BG, 255))
    
    # Ambient glows (Emerald & Gold)
    glow_overlay = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_overlay)
    glow_draw.ellipse([(-80, -80), (520, 520)], fill=(0, 230, 118, 32))
    glow_draw.ellipse([(820, 280), (1380, 780)], fill=(255, 215, 0, 25))
    glow_overlay = glow_overlay.filter(ImageFilter.GaussianBlur(radius=60))
    img = Image.alpha_composite(img, glow_overlay)
    draw = ImageDraw.Draw(img)

    # 2. Typography
    f_badge = _font(14)
    f_title = _font(32)
    f_ticker = _font(40)
    f_subtitle = _reg_font(16)
    f_box_title = _font(15)
    f_num = _font(38)
    f_num_sub = _font(15)
    f_body = _reg_font(15)
    f_author = _font(16)
    f_url = _reg_font(15)

    # 3. Top Header Bar
    badge_text = f"DIVIDEND CASH FLOW · PAY DAY: {pay_date.upper()}" if lang == "it" else f"DIVIDEND CASH FLOW · PAY DAY: {pay_date.upper()}"
    tag_bb = draw.textbbox((0, 0), badge_text, font=f_badge)
    tag_w = tag_bb[2] - tag_bb[0] + 36
    draw.rounded_rectangle([60, 38, 60 + tag_w, 72], radius=14, fill=C_GREEN_TINT, outline=C_GREEN, width=1)
    # Green indicator dot
    draw.ellipse([76, 51, 84, 59], fill=C_GREEN)
    draw.text((94, 47), badge_text, fill=C_GREEN, font=f_badge)

    if weight_pct is not None:
        w_text = f"PESO IN PORTAFOGLIO: {weight_pct:.2f}%" if lang == "it" else f"PORTFOLIO WEIGHT: {weight_pct:.2f}%"
        w_bb = draw.textbbox((0, 0), w_text, font=f_badge)
        w_w = w_bb[2] - w_bb[0] + 36
        draw.rounded_rectangle([75 + tag_w, 38, 75 + tag_w + w_w, 72], radius=14, fill=C_CYAN_TINT, outline=C_CYAN, width=1)
        draw.text((75 + tag_w + 18, 47), w_text, fill=C_CYAN, font=f_badge)

    # 4. Main Profile Card Box
    card_x, card_y, card_w, card_h = 60, 88, 1160, 545
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=22, fill=(*C_CARD, 245), outline=C_BORDER, width=1)

    # Circular Logo with smooth antialiased circular mask
    logo_cx, logo_cy, logo_r = card_x + 90, card_y + 80, 56
    draw.ellipse([logo_cx - logo_r - 3, logo_cy - logo_r - 3, logo_cx + logo_r + 3, logo_cy + logo_r + 3], outline=(0, 230, 118, 180), width=2)
    draw.ellipse([logo_cx - logo_r, logo_cy - logo_r, logo_cx + logo_r, logo_cy + logo_r], fill=(22, 28, 52, 255))

    logo = _fetch_logo(ticker, info.get("domain"))
    if logo:
        logo_size = (logo_r * 2 - 16, logo_r * 2 - 16)
        logo_fitted = ImageOps.fit(logo, logo_size, centering=(0.5, 0.5))
        mask = Image.new("L", logo_size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, logo_size[0], logo_size[1]), fill=255)
        logo_fitted.putalpha(mask)
        img.paste(logo_fitted, (logo_cx - logo_r + 8, logo_cy - logo_r + 8), logo_fitted)
    else:
        draw.text((logo_cx - 24, logo_cy - 14), ticker[:3], fill=C_WHITE, font=_font(22))

    # Ticker, Name, Sector
    draw.text((card_x + 175, card_y + 36), f"${ticker}", fill=C_GREEN, font=f_ticker)
    draw.text((card_x + 175, card_y + 85), comp_name, fill=C_WHITE, font=f_title)
    draw.text((card_x + 175, card_y + 128), f"Settore: {sector_name}" if lang == "it" else f"Sector: {sector_name}", fill=C_MUTED, font=f_subtitle)

    # Divider line
    draw.line([(card_x + 35, card_y + 168), (card_x + card_w - 35, card_y + 168)], fill=C_BORDER, width=1)

    # 5. Four High-Contrast KPI Cards (2x2 Grid)
    grid_gap = 24
    grid_w = (card_w - 70 - grid_gap) // 2
    grid_h = 160
    
    # ── BOX 1: DIVIDENDO PER AZIONE (DPS) (Top-Left) ──
    b1_x, b1_y = card_x + 35, card_y + 185
    draw.rounded_rectangle([b1_x, b1_y, b1_x + grid_w, b1_y + grid_h], radius=16, fill=(*C_BOX, 240), outline=C_GREEN, width=1)
    lbl1 = "DIVIDENDO DISTRIBUITO (DPS)" if lang == "it" else "DIVIDEND PER SHARE (DPS)"
    draw.text((b1_x + 20, b1_y + 16), lbl1, fill=C_MUTED, font=f_box_title)
    draw.text((b1_x + 20, b1_y + 48), dps_val, fill=C_GREEN, font=f_num)
    
    # Confirmed badge
    badge_confirmed = "Accredito Confermato" if lang == "it" else "Payment Confirmed"
    conf_bb = draw.textbbox((0, 0), badge_confirmed, font=f_num_sub)
    conf_w = conf_bb[2] - conf_bb[0] + 24
    draw.rounded_rectangle([b1_x + 20, b1_y + 105, b1_x + 20 + conf_w, b1_y + 137], radius=8, fill=C_GREEN_TINT, outline=C_GREEN, width=1)
    draw.text((b1_x + 32, b1_y + 112), badge_confirmed, fill=C_GREEN, font=f_num_sub)
    draw.text((b1_x + 20 + conf_w + 14, b1_y + 114), f"Data: {pay_date}", fill=C_MUTED, font=f_body)

    # ── BOX 2: DIVIDEND YIELD (Top-Right) ──
    b2_x, b2_y = b1_x + grid_w + grid_gap, b1_y
    draw.rounded_rectangle([b2_x, b2_y, b2_x + grid_w, b2_y + grid_h], radius=16, fill=(*C_BOX, 240), outline=C_GOLD, width=1)
    lbl2 = "RENDIMENTO DA DIVIDENDO (YIELD)" if lang == "it" else "DIVIDEND YIELD"
    draw.text((b2_x + 20, b2_y + 16), lbl2, fill=C_MUTED, font=f_box_title)
    draw.text((b2_x + 20, b2_y + 48), yield_val, fill=C_GOLD, font=f_num)
    
    # Yield stability badge
    badge_yield = "Flusso Cassa Stabile" if lang == "it" else "Sustainable Cash Flow"
    y_bb = draw.textbbox((0, 0), badge_yield, font=f_num_sub)
    y_w = y_bb[2] - y_bb[0] + 24
    draw.rounded_rectangle([b2_x + 20, b2_y + 105, b2_x + 20 + y_w, b2_y + 137], radius=8, fill=C_GOLD_TINT, outline=C_GOLD, width=1)
    draw.text((b2_x + 32, b2_y + 112), badge_yield, fill=C_GOLD, font=f_num_sub)
    draw.text((b2_x + 20 + y_w + 14, b2_y + 114), "Generazione reale", fill=C_MUTED, font=f_body)

    # ── BOX 3: REINVESTIMENTO AUTOMATICO (Bottom-Left) ──
    b3_x, b3_y = b1_x, b1_y + grid_h + 16
    draw.rounded_rectangle([b3_x, b3_y, b3_x + grid_w, b3_y + grid_h], radius=16, fill=(*C_BOX, 240), outline=C_CYAN, width=1)
    lbl3 = "INTERESSE COMPOSTO · REINVESTIMENTO 100%" if lang == "it" else "COMPOUNDING · 100% REINVESTED"
    draw.text((b3_x + 20, b3_y + 16), lbl3, fill=C_CYAN, font=f_box_title)
    
    # Wrap text
    words = reinvest_val.split()
    rlines, current = [], ""
    for w in words:
        test = (current + " " + w).strip()
        bb = draw.textbbox((0, 0), test, font=f_body)
        if bb[2] - bb[0] < grid_w - 40:
            current = test
        else:
            rlines.append(current)
            current = w
    if current:
        rlines.append(current)

    ry = b3_y + 52
    for l in rlines[:3]:
        draw.text((b3_x + 20, ry), l, fill=C_WHITE, font=f_body)
        ry += 28

    # ── BOX 4: STRATEGIA & RUOLO IN PORTAFOGLIO (Bottom-Right) ──
    b4_x, b4_y = b2_x, b3_y
    draw.rounded_rectangle([b4_x, b4_y, b4_x + grid_w, b4_y + grid_h], radius=16, fill=(*C_BOX, 240), outline=(0, 230, 118, 120), width=1)
    lbl4 = "RUOLO STRATEGICO & PROTEZIONE DEL CAPITALE" if lang == "it" else "STRATEGIC ROLE & PRESERVATION"
    draw.text((b4_x + 20, b4_y + 16), lbl4, fill=C_GREEN, font=f_box_title)

    # Wrap text
    swords = strat_val.split()
    slines, current = [], ""
    for w in swords:
        test = (current + " " + w).strip()
        bb = draw.textbbox((0, 0), test, font=f_body)
        if bb[2] - bb[0] < grid_w - 40:
            current = test
        else:
            slines.append(current)
            current = w
    if current:
        slines.append(current)

    sy = b4_y + 52
    for l in slines[:3]:
        draw.text((b4_x + 20, sy), l, fill=(230, 235, 245), font=f_body)
        sy += 28

    # 6. Footer Branding
    bot_y = CARD_H - 58
    draw.text((60, bot_y), f"{AUTHOR_TEXT}", fill=(230, 230, 245), font=f_author)
    bb_url = draw.textbbox((0, 0), URL_TEXT, font=f_url)
    draw.text((CARD_W - (bb_url[2] - bb_url[0]) - 60, bot_y), URL_TEXT, fill=C_GREEN, font=f_url)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.convert("RGB").save(output_path, "PNG", optimize=True)
    print(f"✅ Dividend card generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_dividend_card(
        ticker="WMT",
        company_name="Walmart Inc",
        pay_date="08 Set 2026",
        dps_amount="$0.25 / azione",
        div_yield="1.28%",
        reinvest_note="100% del dividendo viene automaticamente reinvestito nel portafoglio per comprare ulteriori quote e alimentare il compounding.",
        strategic_role="Leader mondiale difensivo della grande distribuzione, con cash flow resiliente e oltre 50 anni di crescita ininterrotta del dividendo.",
        weight_pct=4.12,
        output_path="output/dividend_card_wmt.png",
        lang="it",
    )
