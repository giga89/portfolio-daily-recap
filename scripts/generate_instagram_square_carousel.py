#!/usr/bin/env python3
"""
Ultra-Minimalist Instagram Square Carousel Generator (1080x1080 px)
===================================================================
Strictly adheres to Instagram viral best practices:
- STRICT micro-copy: Under 15-20 words per slide.
- Giant typography (52-68pt headlines, 24-30pt text) for instant 1.5s mobile readability.
- Second-chance hook on slide 2.
- Clean visual Save-trigger on slide 5.
- Zero clutter, massive breathing room, ultra-punchy bullets.
"""

import os
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = "output/carousel_instagram_square"
ASSETS_DIR = "assets"
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

WIDTH = 1080
HEIGHT = 1080

# Sleek obsidian palette
BG_TOP = (11, 15, 25)
BG_BOTTOM = (6, 8, 14)

CARD_BG = (17, 24, 38)
CARD_BORDER = (42, 56, 78)

ACCENT_GREEN = (0, 230, 118)      # #00E676
ACCENT_CYAN = (56, 189, 248)      # #38BDF8
ACCENT_GOLD = (245, 158, 11)      # #F59E0B
ACCENT_RED = (248, 113, 113)      # #F87171
ACCENT_PURPLE = (168, 85, 247)    # #A855F7

TEXT_WHITE = (255, 255, 255)
TEXT_SUB = (215, 225, 240)
TEXT_MUTED = (148, 163, 184)


def get_font(name: str, size: int):
    """Safely load font."""
    paths = [
        os.path.join(FONTS_DIR, name),
        os.path.join(FONTS_DIR, "Outfit-Bold.ttf" if "Bold" in name else "Outfit-Regular.ttf"),
        os.path.join(FONTS_DIR, "Inter-Bold.ttf" if "Bold" in name else "Inter-Regular.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if "Bold" in name else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def create_base_canvas() -> Image.Image:
    """Create clean 1080x1080 canvas with smooth dark gradient."""
    base = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    draw = ImageDraw.Draw(base)

    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    for rad in range(280, 0, -12):
        alpha = int((280 - rad) / 280 * 22)
        glow_draw.ellipse(
            [WIDTH - 120 - rad, 100 - rad, WIDTH - 120 + rad, 100 + rad],
            fill=(0, 230, 118, alpha)
        )

    base = Image.alpha_composite(base.convert("RGBA"), glow).convert("RGB")
    return base


def draw_rounded_card(
    draw: ImageDraw.Draw,
    rect: tuple,
    radius: int = 22,
    fill_color=CARD_BG,
    border_color=CARD_BORDER,
    border_width: int = 1
):
    """Draw smooth rounded rectangle card."""
    x0, y0, x1, y1 = rect
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=radius,
        fill=fill_color,
        outline=border_color,
        width=border_width
    )


def draw_badge_icon(draw: ImageDraw.Draw, xy: tuple, icon_type: str, color, size: int = 28):
    """Draw vector icon badge."""
    x, y = xy
    r = size // 2
    cx, cy = x + r, y + r
    bg_fill = (color[0] // 5, color[1] // 5, color[2] // 5)
    draw.ellipse((x, y, x + size, y + size), fill=bg_fill, outline=color, width=2)
    
    if icon_type == "cross":
        pad = int(size * 0.28)
        draw.line([(x + pad, y + pad), (x + size - pad, y + size - pad)], fill=color, width=3)
        draw.line([(x + size - pad, y + pad), (x + pad, y + size - pad)], fill=color, width=3)
    elif icon_type == "check":
        p1 = (cx - int(r * 0.5), cy)
        p2 = (cx - int(r * 0.1), cy + int(r * 0.45))
        p3 = (cx + int(r * 0.55), cy - int(r * 0.45))
        draw.line([p1, p2, p3], fill=color, width=3)
    elif icon_type == "star":
        draw.polygon([(cx, y + 5), (x + size - 5, cy), (cx, y + size - 5), (x + 5, cy)], fill=color)


def draw_header_and_footer(img: Image.Image, slide_num: int, total_slides: int = 6):
    """Ultra-clean header and footer."""
    draw = ImageDraw.Draw(img)

    photo_path = os.path.join(ASSETS_DIR, "andrea_central_park.png")
    if os.path.exists(photo_path):
        try:
            pimg = Image.open(photo_path).convert("RGBA")
            pimg = pimg.resize((50, 50), Image.Resampling.LANCZOS)
            mask = Image.new("L", (50, 50), 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.ellipse((0, 0, 50, 50), fill=255)
            img.paste(pimg, (60, 42), mask)
            draw.ellipse((58, 40, 112, 94), outline=ACCENT_GREEN, width=2)
        except Exception:
            pass

    font_name = get_font("Outfit-Bold.ttf", 22)
    font_sub = get_font("Inter-Medium.ttf", 15)
    draw.text((125, 44), "Andrea Ravalli", font=font_name, fill=TEXT_WHITE)
    draw.text((125, 70), "@AndreaRavalli • Popular Investor", font=font_sub, fill=ACCENT_CYAN)

    counter_rect = (WIDTH - 170, 46, WIDTH - 60, 88)
    draw.rounded_rectangle(counter_rect, radius=21, fill=(18, 26, 42), outline=(45, 60, 84), width=1)
    font_counter = get_font("Outfit-Bold.ttf", 18)
    counter_text = f"0{slide_num} / 0{total_slides}"
    draw.text((WIDTH - 115, 67), counter_text, font=font_counter, fill=TEXT_WHITE, anchor="mm")

    draw.line([(60, 108), (WIDTH - 60, 108)], fill=(30, 42, 60), width=1)
    draw.line([(60, HEIGHT - 85), (WIDTH - 60, HEIGHT - 85)], fill=(30, 42, 60), width=1)

    font_foot = get_font("Inter-Medium.ttf", 16)
    font_btn = get_font("Outfit-Bold.ttf", 17)
    draw.text((60, HEIGHT - 52), "eToro: @AndreaRavalli", font=font_foot, fill=TEXT_MUTED)

    if slide_num < total_slides:
        swipe_rect = (WIDTH - 190, HEIGHT - 68, WIDTH - 60, HEIGHT - 30)
        draw.rounded_rectangle(swipe_rect, radius=19, fill=(14, 32, 28), outline=ACCENT_GREEN, width=1)
        draw.text((WIDTH - 125, HEIGHT - 49), "Scorri >", font=font_btn, fill=ACCENT_GREEN, anchor="mm")
    else:
        save_rect = (WIDTH - 200, HEIGHT - 68, WIDTH - 60, HEIGHT - 30)
        draw.rounded_rectangle(save_rect, radius=19, fill=(35, 26, 15), outline=ACCENT_GOLD, width=1)
        draw.text((WIDTH - 130, HEIGHT - 49), "Salva Post", font=font_btn, fill=ACCENT_GOLD, anchor="mm")


def paste_photo_hero(img: Image.Image, photo_path: str, rect: tuple, radius: int = 24):
    """Pastes rounded photo into specified bounding box."""
    if not os.path.exists(photo_path):
        return
    try:
        pimg = Image.open(photo_path).convert("RGBA")
        x0, y0, x1, y1 = rect
        w = x1 - x0
        h = y1 - y0
        
        img_ratio = pimg.width / pimg.height
        target_ratio = w / h
        if img_ratio > target_ratio:
            new_w = int(pimg.height * target_ratio)
            crop_x = (pimg.width - new_w) // 2
            pimg = pimg.crop((crop_x, 0, crop_x + new_w, pimg.height))
        else:
            new_h = int(pimg.width / target_ratio)
            crop_y = (pimg.height - new_h) // 2
            pimg = pimg.crop((0, crop_y, pimg.width, crop_y + new_h))
            
        pimg = pimg.resize((w, h), Image.Resampling.LANCZOS)
        mask = Image.new("L", (w, h), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
        img.paste(pimg, (x0, y0), mask)
        
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=None, outline=(50, 70, 100), width=2)
    except Exception as e:
        print("Error pasting photo:", e)


# ==============================================================================
# SLIDE 1: HOOK / COVER (Max impact, minimal words)
# ==============================================================================
def render_slide_1() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 1)

    # Giant Bold Typography
    font_h1 = get_font("Outfit-ExtraBold.ttf", 64)
    font_sub = get_font("Inter-SemiBold.ttf", 24)

    draw.text((60, 140), "DA -58% A", font=font_h1, fill=TEXT_WHITE)
    draw.text((60, 210), "+200% SU ETORO", font=font_h1, fill=ACCENT_GREEN)
    draw.text((60, 290), "Cosa ho imparato triplicando il capitale:", font=font_sub, fill=TEXT_SUB)

    # Big Central Photo Card
    photo_rect = (60, 345, 520, 830)
    photo_path = os.path.join(ASSETS_DIR, "andrea_central_park.png")
    paste_photo_hero(img, photo_path, photo_rect, radius=24)

    # Right 2 Huge Stat Cards
    rx0, rx1 = 550, WIDTH - 60
    
    # Card 1: +200%
    draw_rounded_card(draw, (rx0, 345, rx1, 575), radius=22, fill_color=CARD_BG, border_color=ACCENT_GREEN, border_width=2)
    f_num = get_font("Outfit-ExtraBold.ttf", 52)
    f_lbl = get_font("Outfit-Bold.ttf", 20)
    f_sub = get_font("Inter-Regular.ttf", 16)
    draw.text((rx0 + 25, 385), "+200.5%", font=f_num, fill=ACCENT_GREEN)
    draw.text((rx0 + 25, 455), "CAPITALE TRIPLICATO", font=f_lbl, fill=TEXT_WHITE)
    draw.text((rx0 + 25, 495), "Portafoglio Verificato", font=f_sub, fill=TEXT_MUTED)

    # Card 2: 0% LEVA
    draw_rounded_card(draw, (rx0, 600, rx1, 830), radius=22, fill_color=CARD_BG, border_color=CARD_BORDER, border_width=1)
    draw.text((rx0 + 25, 640), "0% LEVA", font=f_num, fill=ACCENT_CYAN)
    draw.text((rx0 + 25, 710), "RISCHIO MINIMO (3/4)", font=f_lbl, fill=TEXT_WHITE)
    draw.text((rx0 + 25, 750), "Popular Investor Elite", font=f_sub, fill=TEXT_MUTED)

    # Swipe Prompt Bottom Line
    draw_rounded_card(draw, (60, 860, WIDTH - 60, 960), radius=18, fill_color=(16, 25, 40), border_color=(34, 197, 94), border_width=1)
    f_sw = get_font("Outfit-Bold.ttf", 22)
    draw_badge_icon(draw, (85, 882), "star", ACCENT_GREEN, size=24)
    draw.text((125, 895), "Non e' stato facile: ecco i 3 errori iniziali >", font=f_sw, fill=TEXT_WHITE, anchor="lm")

    return img


# ==============================================================================
# SLIDE 2: SECOND CHANCE HOOK / THE BRUTAL MISTAKES (< 20 words)
# ==============================================================================
def render_slide_2() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 2)

    font_h1 = get_font("Outfit-Bold.ttf", 52)
    draw.text((60, 140), "I Primi 2 Anni: Il Disastro", font=font_h1, fill=TEXT_WHITE)

    # 2 Loss Badges
    b1_rect = (60, 220, 520, 360)
    b2_rect = (560, 220, WIDTH - 60, 360)
    draw_rounded_card(draw, b1_rect, radius=20, fill_color=(32, 16, 22), border_color=(185, 28, 28), border_width=2)
    draw_rounded_card(draw, b2_rect, radius=20, fill_color=(32, 16, 22), border_color=(185, 28, 28), border_width=2)

    f_yr = get_font("Outfit-Bold.ttf", 22)
    f_loss = get_font("Outfit-ExtraBold.ttf", 54)

    draw.text((90, 255), "2018", font=f_yr, fill=TEXT_MUTED)
    draw.text((90, 310), "-58.17%", font=f_loss, fill=ACCENT_RED, anchor="lm")

    draw.text((590, 255), "2019", font=f_yr, fill=TEXT_MUTED)
    draw.text((590, 310), "-16.95%", font=f_loss, fill=ACCENT_RED, anchor="lm")

    # 3 Mistakes with vector cross badges
    mistakes = [
        "FOMO (Comprare sui massimi)",
        "Troppa Leva Finanziaria",
        "Trading Emotivo Ogni Giorno",
    ]

    card_y = 390
    f_m = get_font("Outfit-Bold.ttf", 26)
    for m in mistakes:
        rect = (60, card_y, WIDTH - 60, card_y + 115)
        draw_rounded_card(draw, rect, radius=18, fill_color=CARD_BG, border_color=(50, 65, 90), border_width=1)
        draw_badge_icon(draw, (90, card_y + 44), "cross", ACCENT_RED, size=28)
        draw.text((135, card_y + 57), m, font=f_m, fill=TEXT_WHITE, anchor="lm")
        card_y += 135

    # Bottom Callout
    draw_rounded_card(draw, (60, 815, WIDTH - 60, 960), radius=20, fill_color=(24, 30, 48), border_color=ACCENT_GOLD, border_width=1)
    f_bot_t = get_font("Outfit-Bold.ttf", 22)
    f_bot_q = get_font("Inter-Medium.ttf", 20)
    draw.text((90, 850), "La dura lezione:", font=f_bot_t, fill=ACCENT_GOLD)
    draw.text((90, 900), "\"Il mercato azzera chi non rispetta il rischio.\"", font=f_bot_q, fill=TEXT_WHITE)

    return img


# ==============================================================================
# SLIDE 3: THE TURNING POINT (< 20 words)
# ==============================================================================
def render_slide_3() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 3)

    font_h1 = get_font("Outfit-Bold.ttf", 52)
    draw.text((60, 140), "Nel 2020 Ho Cambiato Tutto", font=font_h1, fill=TEXT_WHITE)

    # 2 Win Badges
    b1_rect = (60, 220, 520, 360)
    b2_rect = (560, 220, WIDTH - 60, 360)
    draw_rounded_card(draw, b1_rect, radius=20, fill_color=(14, 32, 24), border_color=(22, 101, 52), border_width=2)
    draw_rounded_card(draw, b2_rect, radius=20, fill_color=(14, 32, 24), border_color=(22, 101, 52), border_width=2)

    f_yr = get_font("Outfit-Bold.ttf", 22)
    f_win = get_font("Outfit-ExtraBold.ttf", 54)

    draw.text((90, 255), "2020", font=f_yr, fill=TEXT_MUTED)
    draw.text((90, 310), "+47.40%", font=f_win, fill=ACCENT_GREEN, anchor="lm")

    draw.text((590, 255), "2021", font=f_yr, fill=TEXT_MUTED)
    draw.text((590, 310), "+16.26%", font=f_win, fill=ACCENT_GREEN, anchor="lm")

    # 3 Shifts with vector check badges
    shifts = [
        "0% Leva (Solo Cassa Reale)",
        "Orizzonte Decennale (No Trading)",
        "Solo Grandi Monopoli con Cassa",
    ]

    card_y = 390
    f_s = get_font("Outfit-Bold.ttf", 26)
    for s in shifts:
        rect = (60, card_y, WIDTH - 60, card_y + 115)
        draw_rounded_card(draw, rect, radius=18, fill_color=CARD_BG, border_color=(40, 60, 85), border_width=1)
        draw_badge_icon(draw, (90, card_y + 44), "check", ACCENT_GREEN, size=28)
        draw.text((135, card_y + 57), s, font=f_s, fill=TEXT_WHITE, anchor="lm")
        card_y += 135

    # Bottom Quote
    draw_rounded_card(draw, (60, 815, WIDTH - 60, 960), radius=20, fill_color=(14, 25, 38), border_color=ACCENT_GREEN, border_width=1)
    f_bot_t = get_font("Outfit-Bold.ttf", 22)
    f_bot_q = get_font("Inter-SemiBold.ttf", 21)
    draw.text((90, 850), "Il nuovo principio:", font=f_bot_t, fill=ACCENT_GREEN)
    draw.text((90, 900), "\"Non investo per 1 mese. Investo per 10 anni.\"", font=f_bot_q, fill=TEXT_WHITE)

    return img


# ==============================================================================
# SLIDE 4: THE BEAR MARKET TEST (< 25 words)
# ==============================================================================
def render_slide_4() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 4)

    font_h1 = get_font("Outfit-Bold.ttf", 52)
    draw.text((60, 140), "2022: Il Bear Market", font=font_h1, fill=TEXT_WHITE)

    # Narrative Card
    draw_rounded_card(draw, (60, 220, WIDTH - 60, 480), radius=22, fill_color=CARD_BG, border_color=(50, 70, 100), border_width=1)
    
    f_big = get_font("Outfit-Bold.ttf", 28)
    f_hi = get_font("Outfit-ExtraBold.ttf", 34)
    draw.text((95, 265), "Mentre tutti vendevano nel panico...", font=f_big, fill=TEXT_SUB)
    draw.text((95, 320), "IO HO CONTINUATO AD ACCUMULARE.", font=f_hi, fill=ACCENT_GREEN)

    # Ticker Chips inside
    chips = ["NVDA", "PLTR", "AVGO", "CCJ", "LLY"]
    f_chip = get_font("Outfit-Bold.ttf", 18)
    cx = 95
    cy = 390
    for sym in chips:
        tw = f_chip.getbbox(sym)[2] - f_chip.getbbox(sym)[0]
        cw, ch = tw + 28, 42
        draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=12, fill=(26, 38, 58), outline=ACCENT_CYAN, width=1)
        draw.text((cx + cw // 2, cy + ch // 2), sym, font=f_chip, fill=TEXT_WHITE, anchor="mm")
        cx += cw + 14

    # 4-Year Stats Grid
    grid = [
        ("2022", "-18.7%", "Resistito al crash", ACCENT_RED),
        ("2023", "+20.8%", "Ripartenza solida", ACCENT_GREEN),
        ("2024", "+25.1%", "Consolidamento", ACCENT_GREEN),
        ("2025-26", "+28.6% / +11%", "Nuovi Massimi", ACCENT_GREEN),
    ]

    card_w = (WIDTH - 120 - 18) // 2
    card_h = 135

    for i, (yr, pct, desc, col) in enumerate(grid):
        row = i // 2
        col_idx = i % 2
        cx0 = 60 + col_idx * (card_w + 18)
        cy0 = 510 + row * (card_h + 14)
        cx1 = cx0 + card_w
        cy1 = cy0 + card_h

        draw_rounded_card(draw, (cx0, cy0, cx1, cy1), radius=18, fill_color=CARD_BG, border_color=(40, 55, 75), border_width=1)
        f_yr = get_font("Outfit-Bold.ttf", 20)
        f_p = get_font("Outfit-ExtraBold.ttf", 34)
        f_d = get_font("Inter-Regular.ttf", 14)

        draw.text((cx0 + 18, cy0 + 26), yr, font=f_yr, fill=TEXT_MUTED)
        draw.text((cx1 - 18, cy0 + 26), pct, font=f_p, fill=col, anchor="ra")
        draw.text((cx0 + 18, cy0 + 82), desc, font=f_d, fill=TEXT_SUB)

    # Result Banner
    draw_rounded_card(draw, (60, 830, WIDTH - 60, 960), radius=20, fill_color=(12, 32, 24), border_color=ACCENT_GREEN, border_width=2)
    f_res = get_font("Outfit-ExtraBold.ttf", 26)
    draw.text((WIDTH // 2, 895), "RISULTATO: +200.5% COMPLESSIVO", font=f_res, fill=ACCENT_GREEN, anchor="mm")

    return img


# ==============================================================================
# SLIDE 5: THE PORTFOLIO BLUEPRINT (SAVE TRIGGER • Super Visual)
# ==============================================================================
def render_slide_5() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 5)

    font_h1 = get_font("Outfit-Bold.ttf", 46)
    font_sub = get_font("Outfit-Bold.ttf", 22)

    draw.text((60, 140), "Come e' Diviso il Portafoglio", font=font_h1, fill=TEXT_WHITE)
    draw.text((60, 205), "SALVA QUESTO POST PER DOPO", font=font_sub, fill=ACCENT_GOLD)

    # 4 Visual Bar Cards with clean vector dots
    pillars = [
        ("Tech & AI Leaders", "40%", ["NVDA", "PLTR", "AVGO", "GOOGL", "MSFT", "TSM"], ACCENT_CYAN),
        ("Risorse & Difesa", "25%", ["Cameco", "Difesa UE", "Oro Fisico"], ACCENT_GOLD),
        ("Healthcare & Dividendi", "20%", ["Eli Lilly", "AbbVie", "Novo Nordisk"], ACCENT_GREEN),
        ("Liquidita' Remunerata", "15%", ["XEON (Monetario EUR)", "IB01 (Treasury US)"], ACCENT_PURPLE),
    ]

    card_y = 265
    card_h = 150
    f_pname = get_font("Outfit-Bold.ttf", 22)
    f_pw = get_font("Outfit-ExtraBold.ttf", 24)
    f_chip = get_font("Outfit-SemiBold.ttf", 15)

    for name, weight, chips, color in pillars:
        rect = (60, card_y, WIDTH - 60, card_y + card_h)
        draw_rounded_card(draw, rect, radius=20, fill_color=CARD_BG, border_color=(45, 60, 85), border_width=1)
        
        # Indicator dot
        draw_badge_icon(draw, (85, card_y + 20), "dot", color, size=20)
        draw.text((115, card_y + 30), name, font=f_pname, fill=TEXT_WHITE, anchor="lm")
        
        # Weight badge
        w_rect = (WIDTH - 180, card_y + 16, WIDTH - 80, card_y + 54)
        draw.rounded_rectangle(w_rect, radius=14, fill=(color[0] // 5, color[1] // 5, color[2] // 5), outline=color, width=2)
        draw.text(((WIDTH - 180 + WIDTH - 80) // 2, card_y + 35), weight, font=f_pw, fill=color, anchor="mm")

        # Chips
        cx = 85
        cy = card_y + 78
        for chip_text in chips:
            tw = f_chip.getbbox(chip_text)[2] - f_chip.getbbox(chip_text)[0]
            cw = tw + 24
            ch = 38
            draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=10, fill=(24, 34, 54), outline=(55, 75, 105), width=1)
            draw.text((cx + cw // 2, cy + ch // 2), chip_text, font=f_chip, fill=TEXT_WHITE, anchor="mm")
            cx += cw + 12

        card_y += card_h + 20

    # Bottom summary tag
    draw_rounded_card(draw, (60, 940, WIDTH - 60, 985), radius=12, fill_color=(14, 20, 32), border_color=(35, 48, 68), border_width=1)
    f_ft = get_font("Inter-Medium.ttf", 14)
    draw.text((WIDTH // 2, 962), "0% Leva • 100% Posizioni Long • Massima Diversificazione Asimmetrica", font=f_ft, fill=TEXT_MUTED, anchor="mm")

    return img


# ==============================================================================
# SLIDE 6: THE GOLDEN RULE & CTA (< 20 words)
# ==============================================================================
def render_slide_6() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 6)

    # Big Golden Quote Card
    draw_rounded_card(draw, (60, 140, WIDTH - 60, 440), radius=24, fill_color=(16, 26, 42), border_color=ACCENT_GOLD, border_width=2)
    f_qt = get_font("Outfit-Bold.ttf", 22)
    f_qm = get_font("Outfit-ExtraBold.ttf", 36)
    f_sub = get_font("Inter-Medium.ttf", 20)

    draw.text((95, 185), "LA REGOLA DEFINITIVA:", font=f_qt, fill=ACCENT_GOLD)
    draw.text((95, 245), "\"Il tempo sui mercati", font=f_qm, fill=TEXT_WHITE)
    draw.text((95, 295), "batte il timing del mercato.\"", font=f_qm, fill=ACCENT_GREEN)
    draw.text((95, 365), "Chi resta calmo e non usa leva, vince sempre.", font=f_sub, fill=TEXT_SUB)

    # Final CTA Card with Photo Avatar
    cta_rect = (60, 480, WIDTH - 60, 960)
    draw_rounded_card(draw, cta_rect, radius=24, fill_color=(14, 22, 38), border_color=ACCENT_GREEN, border_width=2)

    photo_path = os.path.join(ASSETS_DIR, "andrea_central_park.png")
    if os.path.exists(photo_path):
        try:
            pimg = Image.open(photo_path).convert("RGBA")
            pimg = pimg.resize((100, 100), Image.Resampling.LANCZOS)
            mask = Image.new("L", (100, 100), 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.ellipse((0, 0, 100, 100), fill=255)
            img.paste(pimg, (WIDTH // 2 - 50, 520), mask)
            draw.ellipse((WIDTH // 2 - 52, 518, WIDTH // 2 + 52, 622), outline=ACCENT_GREEN, width=3)
        except Exception:
            pass

    f_cta_h = get_font("Outfit-ExtraBold.ttf", 30)
    f_cta_b = get_font("Inter-Medium.ttf", 20)
    f_btn = get_font("Outfit-Bold.ttf", 24)

    draw.text((WIDTH // 2, 665), "Vuoi Copiare la Strategia?", font=f_cta_h, fill=TEXT_WHITE, anchor="mm")
    draw.text((WIDTH // 2, 715), "Portafoglio 100% pubblico e verificato su eToro.", font=f_cta_b, fill=TEXT_SUB, anchor="mm")

    # Big CTA Button
    btn_rect = (WIDTH // 2 - 270, 770, WIDTH // 2 + 270, 845)
    draw.rounded_rectangle(btn_rect, radius=24, fill=(12, 44, 32), outline=ACCENT_GREEN, width=2)
    draw.text((WIDTH // 2, 807), "eToro: @AndreaRavalli", font=f_btn, fill=ACCENT_GREEN, anchor="mm")

    draw.text((WIDTH // 2, 895), "Link diretto nel primo commento e in bio", font=get_font("Inter-SemiBold.ttf", 18), fill=TEXT_MUTED, anchor="mm")

    return img


def generate_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    slides = [
        (1, render_slide_1),
        (2, render_slide_2),
        (3, render_slide_3),
        (4, render_slide_4),
        (5, render_slide_5),
        (6, render_slide_6),
    ]

    generated_paths = []
    for num, render_func in slides:
        print(f"Generating Square Slide {num}...")
        img = render_func()
        path = os.path.join(OUTPUT_DIR, f"slide_{num}.png")
        img.save(path, "PNG", quality=98)
        generated_paths.append(path)
        print(f"Saved: {path}")

    print("\nAll 6 Ultra-Minimal Square Instagram slides generated successfully in:", OUTPUT_DIR)
    return generated_paths


if __name__ == "__main__":
    generate_all()
