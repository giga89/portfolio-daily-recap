#!/usr/bin/env python3
"""
Instagram Carousel Generator (v2): +200% eToro Milestone Story (6 Slides)
========================================================================
- Instagram-native: visual, minimal text, impactful typography, human-centric.
- Prominently features Andrea's Central Park photo.
- Clean luxury dark gradient background (NO checkerboard / grid artifacts).
- Perfectly aligned stat cards and unified chip styling for portfolio assets.
- Clear, intuitive representation for Liquidity (XEON, IB01).
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = "output/carousel_200pct"
ASSETS_DIR = "assets"
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
LOGOS_DIR = os.path.join(ASSETS_DIR, "logos")

WIDTH = 1080
HEIGHT = 1350

# Luxury Clean Palette (Deep Obsidian & Night Blue)
BG_TOP = (10, 14, 23)
BG_BOTTOM = (5, 7, 12)

CARD_BG = (17, 24, 38)
CARD_BG_ELEVATED = (22, 31, 48)
CARD_BORDER = (35, 48, 68)
CARD_BORDER_ACCENT = (56, 189, 248, 180)

ACCENT_GREEN = (0, 230, 118)      # #00E676
ACCENT_CYAN = (56, 189, 248)      # #38BDF8
ACCENT_GOLD = (245, 158, 11)      # #F59E0B
ACCENT_RED = (248, 113, 113)      # #F87171
ACCENT_PURPLE = (168, 85, 247)    # #A855F7

TEXT_WHITE = (255, 255, 255)
TEXT_SUB = (210, 220, 235)        # #D2DCEB
TEXT_MUTED = (148, 163, 184)      # #94A3B8
TEXT_DIM = (100, 116, 139)        # #64748B


def get_font(name: str, size: int):
    """Safely load font with fallback."""
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
    """Create canvas with smooth, rich dark slate vertical gradient and soft ambient glows (NO checkerboard / NO grid)."""
    base = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    draw = ImageDraw.Draw(base)

    # Clean Vertical Gradient
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Soft glowing radial spotlights (RGB mode overlay without alpha checkerboards)
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    # Emerald glow at top-right
    for rad in range(320, 0, -12):
        alpha = int((320 - rad) / 320 * 20)
        glow_draw.ellipse(
            [WIDTH - 150 - rad, 120 - rad, WIDTH - 150 + rad, 120 + rad],
            fill=(0, 230, 118, alpha)
        )
    # Cyan glow at bottom-left
    for rad in range(300, 0, -12):
        alpha = int((300 - rad) / 300 * 18)
        glow_draw.ellipse(
            [100 - rad, HEIGHT - 100 - rad, 100 + rad, HEIGHT - 100 + rad],
            fill=(56, 189, 248, alpha)
        )

    base = Image.alpha_composite(base.convert("RGBA"), glow).convert("RGB")
    return base


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list:
    """Wraps text into lines that fit within max_width."""
    lines = []
    paragraphs = text.split("\n")
    for para in paragraphs:
        if not para.strip():
            lines.append("")
            continue
        words = para.split(" ")
        curr_line = []
        for word in words:
            test_line = " ".join(curr_line + [word])
            bbox = font.getbbox(test_line)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                curr_line.append(word)
            else:
                if curr_line:
                    lines.append(" ".join(curr_line))
                    curr_line = [word]
                else:
                    lines.append(word)
                    curr_line = []
        if curr_line:
            lines.append(" ".join(curr_line))
    return lines


def draw_multiline_wrapped(
    draw: ImageDraw.Draw,
    xy: tuple,
    text: str,
    font: ImageFont.ImageFont,
    fill,
    max_width: int,
    spacing: int = 6,
    align: str = "left"
) -> int:
    """Draws wrapped text and returns total height."""
    lines = wrap_text(text, font, max_width)
    x, y = xy
    total_h = 0
    for line in lines:
        if align == "center":
            bbox = font.getbbox(line)
            w = bbox[2] - bbox[0]
            lx = x - w // 2
        elif align == "right":
            bbox = font.getbbox(line)
            w = bbox[2] - bbox[0]
            lx = x - w
        else:
            lx = x
        draw.text((lx, y + total_h), line, font=font, fill=fill)
        bbox = font.getbbox("Ay")
        line_h = (bbox[3] - bbox[1]) + spacing
        total_h += line_h
    return total_h


def draw_rounded_card(
    draw: ImageDraw.Draw,
    rect: tuple,
    radius: int = 24,
    fill_color=CARD_BG,
    border_color=CARD_BORDER,
    border_width: int = 1
):
    """Draw clean smooth rounded rectangle card with solid border."""
    x0, y0, x1, y1 = rect
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=radius,
        fill=fill_color,
        outline=border_color,
        width=border_width
    )


def draw_badge_icon(draw: ImageDraw.Draw, xy: tuple, icon_type: str, color, size: int = 24):
    """Draw vector icon badge (check, cross, star, dot, arrow) without emojis or font glitches."""
    x, y = xy
    r = size // 2
    cx, cy = x + r, y + r
    
    # Outer circle with solid fill
    bg_fill = (color[0] // 5, color[1] // 5, color[2] // 5)
    draw.ellipse((x, y, x + size, y + size), fill=bg_fill, outline=color, width=2)
    
    if icon_type == "cross":
        pad = int(size * 0.28)
        draw.line([(x + pad, y + pad), (x + size - pad, y + size - pad)], fill=color, width=2)
        draw.line([(x + size - pad, y + pad), (x + pad, y + size - pad)], fill=color, width=2)
    elif icon_type == "check":
        p1 = (cx - int(r * 0.5), cy)
        p2 = (cx - int(r * 0.1), cy + int(r * 0.45))
        p3 = (cx + int(r * 0.55), cy - int(r * 0.45))
        draw.line([p1, p2, p3], fill=color, width=2)
    elif icon_type == "arrow":
        p1 = (cx - int(r * 0.4), cy)
        p2 = (cx + int(r * 0.4), cy)
        draw.line([p1, p2], fill=color, width=2)
        draw.line([(cx + int(r * 0.1), cy - int(r * 0.35)), p2, (cx + int(r * 0.1), cy + int(r * 0.35))], fill=color, width=2)
    elif icon_type == "dot":
        draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=color)
    elif icon_type == "star":
        draw.polygon([(cx, y + 4), (x + size - 4, cy), (cx, y + size - 4), (x + 4, cy)], fill=color)


def draw_header_and_footer(img: Image.Image, slide_num: int, total_slides: int = 6):
    """Draw consistent solid top bar and bottom footer on every slide."""
    draw = ImageDraw.Draw(img)

    # --- TOP BAR ---
    # User Photo Circle (using the Central Park photo)
    photo_path = os.path.join(ASSETS_DIR, "andrea_central_park.png")
    if not os.path.exists(photo_path):
        photo_path = os.path.join(ASSETS_DIR, "profile_photo.jpg")

    if os.path.exists(photo_path):
        try:
            pimg = Image.open(photo_path).convert("RGBA")
            pimg = pimg.resize((56, 56), Image.Resampling.LANCZOS)
            mask = Image.new("L", (56, 56), 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.ellipse((0, 0, 56, 56), fill=255)
            
            img.paste(pimg, (60, 46), mask)
            draw.ellipse((58, 44, 118, 104), outline=ACCENT_GREEN, width=2)
        except Exception:
            pass

    font_name = get_font("Outfit-Bold.ttf", 22)
    font_sub = get_font("Inter-Medium.ttf", 15)
    draw.text((130, 50), "Andrea Ravalli", font=font_name, fill=TEXT_WHITE)
    draw.text((130, 77), "@AndreaRavalli • Popular Investor Elite", font=font_sub, fill=ACCENT_CYAN)

    # Right: Slide counter solid pill
    counter_rect = (WIDTH - 180, 50, WIDTH - 60, 96)
    draw.rounded_rectangle(counter_rect, radius=23, fill=(18, 26, 42), outline=(45, 60, 84), width=1)
    font_counter = get_font("Outfit-Bold.ttf", 20)
    counter_text = f"0{slide_num} / 0{total_slides}"
    draw.text((WIDTH - 120, 73), counter_text, font=font_counter, fill=TEXT_WHITE, anchor="mm")

    # Top separator line
    draw.line([(60, 118), (WIDTH - 60, 118)], fill=(30, 42, 60), width=1)

    # --- FOOTER ---
    draw.line([(60, HEIGHT - 105), (WIDTH - 60, HEIGHT - 105)], fill=(30, 42, 60), width=1)
    
    font_foot_left = get_font("Inter-Medium.ttf", 16)
    font_foot_right = get_font("Outfit-Bold.ttf", 18)

    draw.text((60, HEIGHT - 72), "eToro: etoro.com/people/andrearavalli", font=font_foot_left, fill=TEXT_MUTED)
    
    if slide_num < total_slides:
        swipe_rect = (WIDTH - 210, HEIGHT - 88, WIDTH - 60, HEIGHT - 44)
        draw.rounded_rectangle(swipe_rect, radius=22, fill=(14, 32, 28), outline=ACCENT_GREEN, width=1)
        draw.text((WIDTH - 135, HEIGHT - 66), "Scorri >", font=font_foot_right, fill=ACCENT_GREEN, anchor="mm")
    else:
        save_rect = (WIDTH - 220, HEIGHT - 88, WIDTH - 60, HEIGHT - 44)
        draw.rounded_rectangle(save_rect, radius=22, fill=(35, 26, 15), outline=ACCENT_GOLD, width=1)
        draw.text((WIDTH - 140, HEIGHT - 66), "Salva il Post", font=font_foot_right, fill=ACCENT_GOLD, anchor="mm")


def paste_photo_hero(img: Image.Image, photo_path: str, rect: tuple, radius: int = 24):
    """Pastes rounded photo into specified bounding box."""
    if not os.path.exists(photo_path):
        return
    try:
        pimg = Image.open(photo_path).convert("RGBA")
        x0, y0, x1, y1 = rect
        w = x1 - x0
        h = y1 - y0
        
        # Center-crop to fit ratio
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
        
        # Border
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=None, outline=(50, 70, 100), width=2)
    except Exception as e:
        print("Error pasting hero photo:", e)


# ==============================================================================
# SLIDE 1: THE COVER (High impact, lifestyle photo, +200% milestone)
# ==============================================================================
def render_slide_1() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 1)

    # Top Category Pill (Solid fill, no checkerboard)
    pill_rect = (60, 142, 440, 186)
    draw.rounded_rectangle(pill_rect, radius=22, fill=(12, 32, 24), outline=ACCENT_GREEN, width=1)
    font_pill = get_font("Outfit-Bold.ttf", 17)
    draw_badge_icon(draw, (75, 153), "star", ACCENT_GREEN, size=22)
    draw.text((265, 164), "TRAGUARDO STORICO", font=font_pill, fill=ACCENT_GREEN, anchor="mm")

    # Main Headline (Big & Bold)
    font_h1_small = get_font("Outfit-Bold.ttf", 46)
    font_h1_huge = get_font("Outfit-ExtraBold.ttf", 76)
    font_sub = get_font("Inter-Regular.ttf", 22)

    draw.text((60, 205), "DA -58% A", font=font_h1_small, fill=TEXT_WHITE)
    draw.text((60, 258), "+200.5% SU ETORO", font=font_h1_huge, fill=ACCENT_GREEN)
    
    sub_text = "8 anni di errori, disciplina e la strategia che ha triplicato il capitale."
    draw.text((60, 355), sub_text, font=font_sub, fill=TEXT_SUB)

    # Large Photo Card Hero (Central Park Photo)
    photo_rect = (60, 410, WIDTH - 60, 830)
    photo_path = os.path.join(ASSETS_DIR, "andrea_central_park.png")
    paste_photo_hero(img, photo_path, photo_rect, radius=24)

    # Floating Glass Overlay on Photo (bottom-left badge)
    draw_rounded_card(draw, (85, 745, 480, 810), radius=16, fill_color=(10, 16, 26), border_color=ACCENT_GREEN, border_width=2)
    font_badge_t = get_font("Outfit-Bold.ttf", 20)
    draw.text((105, 777), "CAPITALE TRIPLICATO (+200%)", font=font_badge_t, fill=ACCENT_GREEN, anchor="lm")

    # 3 Stat Cards below (Properly sized with generous padding to prevent overflowing!)
    # Total width available = 1080 - 120 = 960. 3 cards of width 300 with 30 gap = 300*3 + 60 = 960!
    card_w = 300
    card_h = 160
    card_gap = 30
    stats = [
        ("+200.5%", "Rendimento Totale", "100% Verificato", ACCENT_GREEN),
        ("0% LEVA", "Gestione Rischio", "Solo Azioni Reali", ACCENT_CYAN),
        ("ELITE", "Popular Investor", "36+ Copiers", ACCENT_GOLD),
    ]

    for i, (val, title, desc, col) in enumerate(stats):
        cx0 = 60 + i * (card_w + card_gap)
        cx1 = cx0 + card_w
        cy0 = 860
        cy1 = cy0 + card_h
        
        draw_rounded_card(draw, (cx0, cy0, cx1, cy1), radius=20, fill_color=CARD_BG, border_color=CARD_BORDER, border_width=1)
        
        f_val = get_font("Outfit-ExtraBold.ttf", 36)
        f_t = get_font("Outfit-Bold.ttf", 17)
        f_d = get_font("Inter-Regular.ttf", 14)

        draw.text((cx0 + card_w // 2, cy0 + 42), val, font=f_val, fill=col, anchor="mm")
        draw.text((cx0 + card_w // 2, cy0 + 95), title, font=f_t, fill=TEXT_WHITE, anchor="mm")
        draw.text((cx0 + card_w // 2, cy0 + 130), desc, font=f_d, fill=TEXT_MUTED, anchor="mm")

    # Short Punchy Takeaway Card at bottom
    bot_rect = (60, 1050, WIDTH - 60, 1200)
    draw_rounded_card(draw, bot_rect, radius=22, fill_color=(15, 22, 35), border_color=(34, 197, 94), border_width=1)

    f_bot_t = get_font("Outfit-Bold.ttf", 22)
    f_bot_d = get_font("Inter-Regular.ttf", 18)

    draw_badge_icon(draw, (90, 1075), "check", ACCENT_GREEN, size=24)
    draw.text((125, 1087), "La verità che nessuno ti dice:", font=f_bot_t, fill=ACCENT_GREEN, anchor="lm")
    
    t_lines = "I primi due anni ho perso molti soldi per colpa della fretta e della leva.\nNelle prossime slide ti spiego come ho cambiato tutto."
    draw_multiline_wrapped(draw, (90, 1125), t_lines, f_bot_d, TEXT_SUB, max_width=WIDTH - 180, spacing=6)

    return img


# ==============================================================================
# SLIDE 2: 2018-2019 GLI INIZI E LE BATOSTE (-58% & -17%)
# ==============================================================================
def render_slide_2() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 2)

    # Top Category Pill (Solid fill, no checkerboard)
    pill_rect = (60, 142, 420, 186)
    draw.rounded_rectangle(pill_rect, radius=22, fill=(35, 16, 20), outline=ACCENT_RED, width=1)
    font_pill = get_font("Outfit-Bold.ttf", 17)
    draw_badge_icon(draw, (75, 153), "cross", ACCENT_RED, size=22)
    draw.text((255, 164), "GLI INIZI (2018-2019)", font=font_pill, fill=ACCENT_RED, anchor="mm")

    # Main Headline
    font_h1 = get_font("Outfit-Bold.ttf", 46)
    font_sub = get_font("Inter-Regular.ttf", 22)

    draw.text((60, 205), "Le Batoste da Principiante", font=font_h1, fill=TEXT_WHITE)
    draw.text((60, 265), "Quando pensavo che investire fosse prevedere le notizie del giorno.", font=font_sub, fill=TEXT_SUB)

    # Two Big Loss Cards
    b1_rect = (60, 325, 520, 425)
    b2_rect = (560, 325, WIDTH - 60, 425)
    draw_rounded_card(draw, b1_rect, radius=20, fill_color=(28, 16, 22), border_color=(127, 29, 29), border_width=1)
    draw_rounded_card(draw, b2_rect, radius=20, fill_color=(28, 16, 22), border_color=(127, 29, 29), border_width=1)

    f_b_year = get_font("Outfit-Bold.ttf", 22)
    f_b_loss = get_font("Outfit-ExtraBold.ttf", 44)
    f_b_sub = get_font("Inter-Regular.ttf", 14)

    draw.text((90, 355), "ANNO 2018", font=f_b_year, fill=TEXT_MUTED)
    draw.text((90, 400), "-58.17%", font=f_b_loss, fill=ACCENT_RED, anchor="lm")

    draw.text((590, 355), "ANNO 2019", font=f_b_year, fill=TEXT_MUTED)
    draw.text((590, 400), "-16.95%", font=f_b_loss, fill=ACCENT_RED, anchor="lm")

    # 3 Error Cards (Short, clean, punchy)
    errors = [
        ("FOMO & Rincorsa dei Prezzi", "Comprare ai massimi ciò che saliva di più per paura di 'perdere il treno', e vendere in preda al panico sui primi ritracciamenti."),
        ("Leva Finanziaria & Overtrading", "Fare decine di operazioni al giorno con posizioni troppo grandi, credendo di poter anticipare il mercato minuto per minuto."),
        ("Zero Analisi dei Fondamentali", "Comprare su 'consigli' trovati online invece di guardare bilanci, margini e vantaggi competitivi reali."),
    ]

    card_y = 455
    card_h = 165
    f_err_title = get_font("Outfit-Bold.ttf", 22)
    f_err_desc = get_font("Inter-Regular.ttf", 16)

    for title, desc in errors:
        rect = (60, card_y, WIDTH - 60, card_y + card_h)
        draw_rounded_card(draw, rect, radius=20, fill_color=CARD_BG, border_color=(45, 58, 80), border_width=1)
        
        draw_badge_icon(draw, (85, card_y + 22), "cross", ACCENT_RED, size=24)
        draw.text((120, card_y + 34), title, font=f_err_title, fill=ACCENT_RED, anchor="lm")
        draw_multiline_wrapped(draw, (85, card_y + 68), desc, f_err_desc, TEXT_SUB, max_width=WIDTH - 170, spacing=4)
        card_y += card_h + 16

    # Bottom Big Lesson Box
    lesson_rect = (60, 1025, WIDTH - 60, 1200)
    draw_rounded_card(draw, lesson_rect, radius=22, fill_color=(20, 26, 40), border_color=(245, 158, 11), border_width=1)

    f_l_t = get_font("Outfit-Bold.ttf", 21)
    f_l_d = get_font("Inter-Medium.ttf", 17)

    draw_badge_icon(draw, (85, 1055), "star", ACCENT_GOLD, size=24)
    draw.text((120, 1067), "La Lezione Decisiva:", font=f_l_t, fill=ACCENT_GOLD, anchor="lm")
    
    msg = "\"Il mercato finanziario trasferisce ricchezza dagli impazienti ai pazienti. Quelle perdite sono state il mio master più caro, ma mi hanno costretto a cambiare tutto.\""
    draw_multiline_wrapped(draw, (85, 1105), msg, f_l_d, TEXT_WHITE, max_width=WIDTH - 170, spacing=5)

    return img


# ==============================================================================
# SLIDE 3: 2020-2021 IL CAMBIO DI ROTTA (+47.4% & +16.3%)
# ==============================================================================
def render_slide_3() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 3)

    # Top Category Pill
    pill_rect = (60, 142, 420, 186)
    draw.rounded_rectangle(pill_rect, radius=22, fill=(12, 32, 42), outline=ACCENT_CYAN, width=1)
    font_pill = get_font("Outfit-Bold.ttf", 17)
    draw_badge_icon(draw, (75, 153), "check", ACCENT_CYAN, size=22)
    draw.text((255, 164), "LA SVOLTA (2020-2021)", font=font_pill, fill=ACCENT_CYAN, anchor="mm")

    # Main Headline
    font_h1 = get_font("Outfit-Bold.ttf", 46)
    font_sub = get_font("Inter-Regular.ttf", 22)

    draw.text((60, 205), "Ho Resettato Tutto", font=font_h1, fill=TEXT_WHITE)
    draw.text((60, 265), "Basta trading compulsivo. Benvenuto investimento a lungo termine.", font=font_sub, fill=TEXT_SUB)

    # Two Big Win Cards
    b1_rect = (60, 325, 520, 425)
    b2_rect = (560, 325, WIDTH - 60, 425)
    draw_rounded_card(draw, b1_rect, radius=20, fill_color=(12, 28, 22), border_color=(22, 101, 52), border_width=1)
    draw_rounded_card(draw, b2_rect, radius=20, fill_color=(12, 28, 22), border_color=(22, 101, 52), border_width=1)

    f_b_year = get_font("Outfit-Bold.ttf", 22)
    f_b_win = get_font("Outfit-ExtraBold.ttf", 44)

    draw.text((90, 355), "ANNO 2020", font=f_b_year, fill=TEXT_MUTED)
    draw.text((90, 400), "+47.40%", font=f_b_win, fill=ACCENT_GREEN, anchor="lm")

    draw.text((590, 355), "ANNO 2021", font=f_b_year, fill=TEXT_MUTED)
    draw.text((590, 400), "+16.26%", font=f_b_win, fill=ACCENT_GREEN, anchor="lm")

    # 3 Shift Cards
    shifts = [
        ("Da 'Prevedere' a 'Compounding'", "Smettere di indovinare cosa farà Wall Street domani. Iniziare a comprare quote di aziende leader monopolistiche per tenerle 5-10 anni."),
        ("Abolizione Totale della Leva (100% Equity)", "Zero prestiti, zero derivati. Solo azioni ed ETF reali. Questo protegge da qualsiasi liquidazione e permette di dormire sonni tranquilli."),
        ("Focus sui Grandi Megatrend Globali", "Concentrare il capitale sui temi dominanti: intelligenza artificiale, difesa, healthcare e risorse energetiche strategiche."),
    ]

    card_y = 455
    card_h = 165
    f_shift_title = get_font("Outfit-Bold.ttf", 22)
    f_shift_desc = get_font("Inter-Regular.ttf", 16)

    for title, desc in shifts:
        rect = (60, card_y, WIDTH - 60, card_y + card_h)
        draw_rounded_card(draw, rect, radius=20, fill_color=CARD_BG, border_color=(45, 58, 80), border_width=1)
        
        draw_badge_icon(draw, (85, card_y + 22), "check", ACCENT_CYAN, size=24)
        draw.text((120, card_y + 34), title, font=f_shift_title, fill=ACCENT_CYAN, anchor="lm")
        draw_multiline_wrapped(draw, (85, card_y + 68), desc, f_shift_desc, TEXT_SUB, max_width=WIDTH - 170, spacing=4)
        card_y += card_h + 16

    # Bottom Quote Box
    quote_rect = (60, 1025, WIDTH - 60, 1200)
    draw_rounded_card(draw, quote_rect, radius=22, fill_color=(14, 25, 36), border_color=ACCENT_GREEN, border_width=1)

    f_q_t = get_font("Outfit-Bold.ttf", 21)
    f_q_d = get_font("Inter-Medium.ttf", 20)

    draw_badge_icon(draw, (85, 1055), "check", ACCENT_GREEN, size=24)
    draw.text((120, 1067), "Il Mio Nuovo Principio:", font=f_q_t, fill=ACCENT_GREEN, anchor="lm")
    
    q_msg = "\"Non investo per il prossimo mese.\nInvesto per il prossimo decennio.\""
    draw_multiline_wrapped(draw, (85, 1110), q_msg, f_q_d, TEXT_WHITE, max_width=WIDTH - 170, spacing=6)

    return img


# ==============================================================================
# SLIDE 4: 2022-2026 BEAR MARKET & NUOVI MASSIMI
# ==============================================================================
def render_slide_4() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 4)

    # Top Category Pill
    pill_rect = (60, 142, 450, 186)
    draw.rounded_rectangle(pill_rect, radius=22, fill=(35, 25, 12), outline=ACCENT_GOLD, width=1)
    font_pill = get_font("Outfit-Bold.ttf", 17)
    draw_badge_icon(draw, (75, 153), "star", ACCENT_GOLD, size=22)
    draw.text((270, 164), "RESILIENZA (2022-2026)", font=font_pill, fill=ACCENT_GOLD, anchor="mm")

    # Main Headline
    font_h1 = get_font("Outfit-Bold.ttf", 46)
    font_sub = get_font("Inter-Regular.ttf", 22)

    draw.text((60, 205), "Superare il Panico e Vincere", font=font_h1, fill=TEXT_WHITE)
    draw.text((60, 265), "La differenza tra chi molla e chi vince si vede nei momenti di crollo.", font=font_sub, fill=TEXT_SUB)

    # 4-Year Track Record Grid (2x2 perfectly balanced cards)
    grid_data = [
        ("2022", "-18.72%", "Resistito al bear market (Nasdaq -33%)", ACCENT_RED),
        ("2023", "+20.76%", "Ripartenza solida & convinzione", ACCENT_GREEN),
        ("2024", "+25.13%", "Consolidamento e Popular Investor Elite", ACCENT_GREEN),
        ("2025-26", "+28.6% / +11%", "Nuovi massimi e milestone +200%", ACCENT_GREEN),
    ]

    card_w = (WIDTH - 120 - 24) // 2
    card_h = 145

    for i, (yr, pct, note, col) in enumerate(grid_data):
        row = i // 2
        col_idx = i % 2
        cx0 = 60 + col_idx * (card_w + 24)
        cy0 = 330 + row * (card_h + 16)
        cx1 = cx0 + card_w
        cy1 = cy0 + card_h

        draw_rounded_card(draw, (cx0, cy0, cx1, cy1), radius=18, fill_color=CARD_BG, border_color=(45, 58, 80), border_width=1)
        
        f_yr = get_font("Outfit-Bold.ttf", 20)
        f_pct = get_font("Outfit-ExtraBold.ttf", 36)
        f_nt = get_font("Inter-Regular.ttf", 14)

        draw.text((cx0 + 20, cy0 + 30), yr, font=f_yr, fill=TEXT_MUTED)
        draw.text((cx1 - 20, cy0 + 30), pct, font=f_pct, fill=col, anchor="ra")
        draw_multiline_wrapped(draw, (cx0 + 20, cy0 + 75), note, f_nt, TEXT_SUB, max_width=card_w - 40, spacing=3)

    # Key Secrets Box
    bot_rect = (60, 680, WIDTH - 60, 1200)
    draw_rounded_card(draw, bot_rect, radius=24, fill_color=(15, 23, 38), border_color=ACCENT_CYAN, border_width=1)

    f_h_title = get_font("Outfit-Bold.ttf", 23)
    draw_badge_icon(draw, (85, 710), "star", ACCENT_CYAN, size=24)
    draw.text((120, 722), "Cosa ha fatto davvero la differenza?", font=f_h_title, fill=ACCENT_CYAN, anchor="lm")

    secrets = [
        ("1. Tenere e Comprare nei Ribassi", "Nel 2022 tutti svendevano per panico. Ho mantenuto i nervi saldi e incrementato sui leader: NVIDIA, Palantir, Broadcom, Cameco ed Eli Lilly."),
        ("2. Risk Score 3/4 Sempre Basso", "Non ho mai fatto scommesse binarie. La crescita è arrivata da posizioni bilanciate e zero debito."),
        ("3. Trasparenza Totale con i Copiers", "Ogni operazione è visibile in tempo reale su eToro. La fiducia si costruisce con i risultati e la disciplina negli anni."),
    ]

    py = 770
    f_st = get_font("Outfit-Bold.ttf", 19)
    f_sd = get_font("Inter-Regular.ttf", 15)

    for st_title, st_desc in secrets:
        draw.text((85, py), st_title, font=f_st, fill=TEXT_WHITE)
        draw_multiline_wrapped(draw, (85, py + 28), st_desc, f_sd, TEXT_SUB, max_width=WIDTH - 170, spacing=4)
        py += 135

    return img


# ==============================================================================
# SLIDE 5: I 4 PILASTRI (Clean, unified chips, clear liquidity representation)
# ==============================================================================
def render_slide_5() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 5)

    # Top Category Pill
    pill_rect = (60, 142, 450, 186)
    draw.rounded_rectangle(pill_rect, radius=22, fill=(12, 32, 24), outline=ACCENT_GREEN, width=1)
    font_pill = get_font("Outfit-Bold.ttf", 17)
    draw_badge_icon(draw, (75, 153), "check", ACCENT_GREEN, size=22)
    draw.text((270, 164), "LA MIA STRATEGIA OGGI", font=font_pill, fill=ACCENT_GREEN, anchor="mm")

    # Main Headline
    font_h1 = get_font("Outfit-Bold.ttf", 46)
    font_sub = get_font("Inter-Regular.ttf", 22)

    draw.text((60, 205), "I 4 Pilastri del Portafoglio", font=font_h1, fill=TEXT_WHITE)
    draw.text((60, 265), "Una struttura asimmetrica pensata per massimizzare il rendimento e ridurre i rischi:", font=font_sub, fill=TEXT_SUB)

    # 4 Clean Cards with modern unified chip tags
    pillars = [
        (
            "AI & Megatrend Tech",
            "35 - 45%",
            "Infrastrutture AI, semiconduttori e monopoli tech insostituibili.",
            ["NVDA", "PLTR", "AVGO", "GOOGL", "MSFT", "TSM"],
            ACCENT_CYAN
        ),
        (
            "Risorse Critiche & Difesa",
            "20 - 25%",
            "Nucleare ed energia (Cameco), difesa europea, oro e metalli strategici.",
            ["CCJ (Uranio)", "WDEF (Difesa)", "PPFB (Oro)", "GLEN (Rame)"],
            ACCENT_GOLD
        ),
        (
            "Healthcare & Dividendi",
            "15 - 20%",
            "Farmaceutica blockbuster (GLP-1), beni essenziali e flussi costanti.",
            ["LLY (Eli Lilly)", "ABBV (AbbVie)", "NOVO", "ULVR"],
            ACCENT_GREEN
        ),
        (
            "Liquidità Remunerata",
            "10 - 15%",
            "Cassa remunerata al 3-4% annuo, pronta per comprare i crolli di mercato.",
            ["XEON (Monetario EUR)", "IB01 (Treasury US 0-1y)"],
            ACCENT_PURPLE
        ),
    ]

    card_y = 320
    card_h = 205
    f_p_name = get_font("Outfit-Bold.ttf", 22)
    f_p_weight = get_font("Outfit-Bold.ttf", 17)
    f_p_desc = get_font("Inter-Regular.ttf", 15)
    f_chip = get_font("Outfit-SemiBold.ttf", 14)

    for name, weight, desc, chips, color in pillars:
        rect = (60, card_y, WIDTH - 60, card_y + card_h)
        draw_rounded_card(draw, rect, radius=20, fill_color=CARD_BG, border_color=(45, 58, 80), border_width=1)
        
        # Category indicator dot
        draw_badge_icon(draw, (85, card_y + 18), "dot", color, size=20)
        draw.text((115, card_y + 28), name, font=f_p_name, fill=TEXT_WHITE, anchor="lm")
        
        # Weight badge on right
        w_pill_rect = (WIDTH - 210, card_y + 16, WIDTH - 85, card_y + 48)
        draw.rounded_rectangle(w_pill_rect, radius=16, fill=(color[0] // 5, color[1] // 5, color[2] // 5), outline=color, width=1)
        draw.text(((WIDTH - 210 + WIDTH - 85) // 2, card_y + 32), weight, font=f_p_weight, fill=color, anchor="mm")

        # Description
        draw_multiline_wrapped(draw, (85, card_y + 62), desc, f_p_desc, TEXT_SUB, max_width=WIDTH - 170, spacing=3)

        # Unified modern chip tags
        chip_x = 85
        chip_y = card_y + 130
        for chip_text in chips:
            # Measure chip text
            bbox = f_chip.getbbox(chip_text)
            tw = bbox[2] - bbox[0]
            chip_w = tw + 24
            chip_h = 32
            
            # Check if exceeds line
            if chip_x + chip_w > WIDTH - 85:
                break
                
            draw.rounded_rectangle(
                [chip_x, chip_y, chip_x + chip_w, chip_y + chip_h],
                radius=10,
                fill=(24, 34, 52),
                outline=(55, 72, 98),
                width=1
            )
            draw.text((chip_x + chip_w // 2, chip_y + chip_h // 2), chip_text, font=f_chip, fill=TEXT_WHITE, anchor="mm")
            chip_x += chip_w + 10

        card_y += card_h + 16

    # Bottom summary bar
    draw_rounded_card(draw, (60, 1170, WIDTH - 60, 1215), radius=14, fill_color=(14, 20, 32), border_color=(35, 48, 68), border_width=1)
    f_foot_txt = get_font("Inter-Medium.ttf", 15)
    draw.text((WIDTH // 2, 1192), "0% Leva • 100% Posizioni Long • Diversificazione Asimmetrica", font=f_foot_txt, fill=TEXT_MUTED, anchor="mm")

    return img


# ==============================================================================
# SLIDE 6: LEZIONI & CALL TO ACTION (Aspirational, lifestyle, clear invite)
# ==============================================================================
def render_slide_6() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_header_and_footer(img, 6)

    # Top Category Pill
    pill_rect = (60, 142, 440, 186)
    draw.rounded_rectangle(pill_rect, radius=22, fill=(12, 32, 24), outline=ACCENT_GREEN, width=1)
    font_pill = get_font("Outfit-Bold.ttf", 17)
    draw_badge_icon(draw, (75, 153), "star", ACCENT_GREEN, size=22)
    draw.text((265, 164), "LE REGOLE D'ORO", font=font_pill, fill=ACCENT_GREEN, anchor="mm")

    # Main Headline
    font_h1 = get_font("Outfit-Bold.ttf", 46)
    font_sub = get_font("Inter-Regular.ttf", 22)

    draw.text((60, 205), "Cosa Ho Imparato in 8 Anni", font=font_h1, fill=TEXT_WHITE)
    draw.text((60, 265), "3 principi che valgono più di qualsiasi previsione di mercato:", font=font_sub, fill=TEXT_SUB)

    # 3 Golden Rules (Clean & impactful)
    rules = [
        ("1. Il Tempo Batte il Timing", "Non serve comprare e vendere ogni ora. Lascia che i migliori business del pianeta facciano il lavoro per te mese dopo mese."),
        ("2. La Psicologia Conta Più dei Grafici", "Il vero segreto non è non sbagliare mai, ma tagliare gli errori in fretta e non farsi prendere dal panico durante le correzioni."),
        ("3. La Sopravvivenza Prima del Guadagno", "Chi usa leva prima o poi si azzera. Chi rispetta il rischio ed evita il debito resta sul mercato e vince sul lungo periodo."),
    ]

    card_y = 320
    card_h = 160
    f_r_title = get_font("Outfit-Bold.ttf", 22)
    f_r_desc = get_font("Inter-Regular.ttf", 16)

    for title, desc in rules:
        rect = (60, card_y, WIDTH - 60, card_y + card_h)
        draw_rounded_card(draw, rect, radius=20, fill_color=CARD_BG, border_color=(45, 58, 80), border_width=1)
        
        draw_badge_icon(draw, (85, card_y + 20), "check", ACCENT_CYAN, size=24)
        draw.text((120, card_y + 32), title, font=f_r_title, fill=ACCENT_CYAN, anchor="lm")
        draw_multiline_wrapped(draw, (85, card_y + 68), desc, f_r_desc, TEXT_SUB, max_width=WIDTH - 170, spacing=4)
        card_y += card_h + 16

    # Big Final CTA Card with Andrea photo preview
    cta_rect = (60, 850, WIDTH - 60, 1200)
    draw_rounded_card(draw, cta_rect, radius=24, fill_color=(15, 24, 40), border_color=ACCENT_GREEN, border_width=2)

    # Small thumbnail of Andrea on top of CTA
    photo_path = os.path.join(ASSETS_DIR, "andrea_central_park.png")
    if os.path.exists(photo_path):
        try:
            pimg = Image.open(photo_path).convert("RGBA")
            pimg = pimg.resize((84, 84), Image.Resampling.LANCZOS)
            mask = Image.new("L", (84, 84), 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.ellipse((0, 0, 84, 84), fill=255)
            
            img.paste(pimg, (WIDTH // 2 - 42, 880), mask)
            draw.ellipse((WIDTH // 2 - 44, 878, WIDTH // 2 + 44, 966), outline=ACCENT_GREEN, width=2)
        except Exception:
            pass

    f_cta_head = get_font("Outfit-ExtraBold.ttf", 28)
    f_cta_body = get_font("Inter-Medium.ttf", 17)
    f_cta_btn = get_font("Outfit-Bold.ttf", 22)

    draw.text((WIDTH // 2, 990), "Vuoi Seguire o Copiare la Strategia?", font=f_cta_head, fill=TEXT_WHITE, anchor="mm")
    
    cta_text = "Il mio portafoglio è pubblico, verificato e trasparente su eToro.\nPuoi copiare le posizioni in automatico con un click."
    draw_multiline_wrapped(draw, (WIDTH // 2, 1030), cta_text, f_cta_body, TEXT_SUB, max_width=WIDTH - 180, align="center", spacing=4)

    # Button Pill
    btn_rect = (WIDTH // 2 - 270, 1095, WIDTH // 2 + 270, 1155)
    draw.rounded_rectangle(btn_rect, radius=24, fill=(12, 40, 30), outline=ACCENT_GREEN, width=2)
    draw.text((WIDTH // 2, 1125), "eToro: @AndreaRavalli", font=f_cta_btn, fill=ACCENT_GREEN, anchor="mm")

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
        print(f"Generating Slide {num}...")
        img = render_func()
        path = os.path.join(OUTPUT_DIR, f"slide_{num}.png")
        img.save(path, "PNG", quality=98)
        generated_paths.append(path)
        print(f"Saved: {path}")

    print("\nAll 6 Carousel slides generated successfully in:", OUTPUT_DIR)
    return generated_paths


if __name__ == "__main__":
    generate_all()
