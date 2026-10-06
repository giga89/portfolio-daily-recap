#!/usr/bin/env python3
"""
Educational Card Generator — 16:9 Landscape (1280x720)
======================================================
Generates modern, high-impact landscape cards for the 20-week educational series
on eToro: "Investing Mastery".

Features:
  • Dark luxury theme (#08090F) with thematic glow accents
  • Series header with episode number badge (e.g. "EPISODIO 01/20")
  • Bold title and provocative hook
  • 3 structured content pillars (La Storia, Il Mito, Nel Portafoglio)
  • Cashtags badge pills with glow
  • Verified author branding with profile picture
"""

import os
import math
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CARD_W = 1280
CARD_H = 720

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(ASSETS_DIR, "educational_series")
PROFILE_PHOTO_PATH = os.path.join(ASSETS_DIR, "profile_photo.jpg")
FONT_PATH = os.path.join(ASSETS_DIR, "fonts", "Inter-Bold.ttf")

# Distinct color themes for variety across the 20 weeks
THEME_PALETTES = {
    "cyan": {
        "accent": (0, 220, 255),
        "accent_dim": (0, 70, 95),
        "badge_bg": (8, 38, 52),
        "glow": (0, 180, 220, 35),
    },
    "emerald": {
        "accent": (0, 230, 140),
        "accent_dim": (0, 80, 50),
        "badge_bg": (6, 42, 28),
        "glow": (0, 200, 120, 35),
    },
    "gold": {
        "accent": (255, 195, 45),
        "accent_dim": (90, 65, 15),
        "badge_bg": (48, 36, 8),
        "glow": (240, 180, 30, 35),
    },
    "violet": {
        "accent": (180, 110, 255),
        "accent_dim": (65, 35, 95),
        "badge_bg": (36, 18, 54),
        "glow": (160, 90, 240, 35),
    },
    "ruby": {
        "accent": (255, 85, 105),
        "accent_dim": (95, 25, 35),
        "badge_bg": (50, 14, 20),
        "glow": (240, 60, 85, 35),
    },
    "blue": {
        "accent": (60, 150, 255),
        "accent_dim": (20, 50, 95),
        "badge_bg": (12, 28, 54),
        "glow": (40, 130, 240, 35),
    },
}


def _get_font(size: int) -> ImageFont.ImageFont:
    """Load Inter-Bold font or fallback to PIL default."""
    if os.path.exists(FONT_PATH):
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _draw_rounded_rect(draw: ImageDraw.ImageDraw, box: Tuple[int, int, int, int], radius: int, fill: Any, outline: Any = None, width: int = 1):
    """Draw a smooth rounded rectangle."""
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def generate_educational_card(
    episode: int,
    total_episodes: int,
    title: str,
    subtitle: str,
    pillars: List[Dict[str, str]],
    tickers: List[str],
    palette_name: str = "cyan",
    output_path: str = None,
) -> str:
    """
    Generate a 1280x720 card for an episode of the educational series.

    Args:
        episode: Episode number (1-20)
        total_episodes: Total episodes in series (e.g. 20)
        title: Main bold title
        subtitle: High impact hook or paradox quote
        pillars: List of 3 dicts with keys 'label', 'text'
        tickers: List of 2-4 ticker symbols (e.g. ['IB01', 'AMZN', 'RACE'])
        palette_name: One of 'cyan', 'emerald', 'gold', 'violet', 'ruby', 'blue'
        output_path: Target PNG file path

    Returns:
        output_path
    """
    if output_path is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, f"story_{episode:02d}.png")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    palette = THEME_PALETTES.get(palette_name, THEME_PALETTES["cyan"])
    accent = palette["accent"]
    accent_dim = palette["accent_dim"]
    badge_bg = palette["badge_bg"]

    # Base Canvas
    img = Image.new("RGBA", (CARD_W, CARD_H), (8, 9, 15, 255))
    draw = ImageDraw.Draw(img)

    # ── Background Glow ──────────────────────────────────────────────
    glow_img = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    # Subtle radial glow on top-left and right
    glow_draw.ellipse([(-100, -100), (500, 350)], fill=palette["glow"])
    glow_draw.ellipse([(850, 350), (1350, 750)], fill=(accent[0]//4, accent[1]//4, accent[2]//4, 20))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(70))
    img = Image.alpha_composite(img, glow_img)
    draw = ImageDraw.Draw(img)

    # ── Top Grid / Horizontal accent rule ────────────────────────────
    draw.line([(0, 2), (CARD_W, 2)], fill=accent, width=2)

    # ── Header Bar ───────────────────────────────────────────────────
    # Episode Badge
    font_badge = _get_font(15)
    badge_text = f"EPISODIO {episode:02d} / {total_episodes:02d}"
    badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    badge_w = badge_bbox[2] - badge_bbox[0] + 28
    badge_h = 32
    _draw_rounded_rect(draw, (60, 38, 60 + badge_w, 38 + badge_h), radius=6, fill=badge_bg, outline=accent, width=1)
    draw.text((74, 45), badge_text, font=font_badge, fill=accent)

    # Series Title next to badge
    font_series = _get_font(15)
    series_text = "INVESTING MASTERY · GUIDA ALL'INVESTIMENTO STRATEGICO"
    draw.text((60 + badge_w + 16, 45), series_text, font=font_series, fill=(145, 160, 185))

    # Right branding text
    brand_text = "eToro Social Feed Series"
    brand_font = _get_font(13)
    brand_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
    draw.text((CARD_W - 60 - (brand_bbox[2] - brand_bbox[0]), 46), brand_text, font=brand_font, fill=(90, 105, 125))

    # ── Main Headline ────────────────────────────────────────────────
    font_title = _get_font(38)
    draw.text((60, 92), title, font=font_title, fill=(255, 255, 255))

    # ── Subtitle / Provocative Hook Banner ───────────────────────────
    banner_y = 152
    banner_h = 66
    _draw_rounded_rect(draw, (60, banner_y, CARD_W - 60, banner_y + banner_h), radius=10, fill=(14, 18, 28), outline=accent_dim, width=1)

    # Accent left border indicator
    draw.rectangle([(60, banner_y + 4), (66, banner_y + banner_h - 4)], fill=accent)

    font_sub = _get_font(17)
    sub_lines = _wrap_text(subtitle, font_sub, CARD_W - 170, draw)
    sub_y_start = banner_y + 12 if len(sub_lines) > 1 else banner_y + 22
    for idx, s_line in enumerate(sub_lines[:2]):
        draw.text((82, sub_y_start + idx * 24), s_line, font=font_sub, fill=(225, 235, 245))

    # ── 3 Content Pillar Boxes ───────────────────────────────────────
    pillars_y = 236
    pillar_w = (CARD_W - 120 - 32) // 3  # (1160 - 32) / 3 = 376 px each
    pillar_h = 352

    font_pillar_title = _get_font(15)
    font_pillar_highlight = _get_font(18)
    font_pillar_body = _get_font(15)

    for i, p in enumerate(pillars[:3]):
        px = 60 + i * (pillar_w + 16)
        py = pillars_y

        is_portfolio = (i == 2)
        box_outline = accent if is_portfolio else (32, 42, 60)
        box_bg = (14, 18, 28) if is_portfolio else (11, 15, 24)

        # Pillar Background Box
        _draw_rounded_rect(
            draw,
            (px, py, px + pillar_w, py + pillar_h),
            radius=12,
            fill=box_bg,
            outline=box_outline,
            width=1,
        )

        # Pillar Category Header Pill
        cat_badge_bg = badge_bg if is_portfolio else (18, 24, 36)
        cat_outline = accent if is_portfolio else (38, 48, 68)
        _draw_rounded_rect(
            draw,
            (px + 16, py + 16, px + pillar_w - 16, py + 48),
            radius=6,
            fill=cat_badge_bg,
            outline=cat_outline,
            width=1,
        )

        # Category dot indicator
        dot_color = accent if is_portfolio else (110, 140, 180)
        draw.ellipse([(px + 28, py + 28), (px + 36, py + 36)], fill=dot_color)

        label_color = accent if is_portfolio else (220, 230, 245)
        p_label = p.get("label", f"PUNTO CHIAVE {i+1}").upper()
        draw.text((px + 44, py + 23), p_label, font=font_pillar_title, fill=label_color)

        # Highlight Takeaway / Metric Callout (if present)
        curr_y = py + 62
        highlight_text = p.get("highlight", "")
        if highlight_text:
            _draw_rounded_rect(
                draw,
                (px + 16, curr_y, px + pillar_w - 16, curr_y + 44),
                radius=6,
                fill=(20, 28, 44) if is_portfolio else (16, 22, 34),
                outline=accent_dim if is_portfolio else (28, 36, 52),
                width=1,
            )
            hl_color = accent if is_portfolio else (255, 255, 255)
            draw.text((px + 28, curr_y + 11), highlight_text, font=font_pillar_highlight, fill=hl_color)
            curr_y += 56
        else:
            curr_y += 10

        # Pillar body text wrapping
        p_text = p.get("text", "")
        lines = _wrap_text(p_text, font_pillar_body, pillar_w - 40, draw)
        for line_idx, line in enumerate(lines[:10]):
            text_color = (200, 215, 235) if is_portfolio else (165, 180, 200)
            draw.text((px + 20, curr_y + line_idx * 25), line, font=font_pillar_body, fill=text_color)

    # ── Bottom Bar / Branding & Cashtags ─────────────────────────────
    bot_y = 612
    draw.line([(60, bot_y), (CARD_W - 60, bot_y)], fill=(24, 32, 48), width=1)

    # Profile Avatar
    avatar_loaded = False
    if os.path.exists(PROFILE_PHOTO_PATH):
        try:
            av = Image.open(PROFILE_PHOTO_PATH).convert("RGBA")
            av_size = 56
            av = av.resize((av_size, av_size), Image.Resampling.LANCZOS)
            # Circular mask
            mask = Image.new("L", (av_size, av_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, av_size, av_size), fill=255)
            # Draw glow ring
            draw.ellipse((60 - 2, bot_y + 16 - 2, 60 + av_size + 2, bot_y + 16 + av_size + 2), outline=accent, width=2)
            img.paste(av, (60, bot_y + 16), mask)
            avatar_loaded = True
        except Exception:
            avatar_loaded = False

    avatar_offset = 60 + 56 + 14 if avatar_loaded else 60
    font_author = _get_font(16)
    font_subauthor = _get_font(13)
    draw.text((avatar_offset, bot_y + 22), "Andrea Ravalli", font=font_author, fill=(255, 255, 255))
    draw.text((avatar_offset, bot_y + 44), "Popular Investor su eToro", font=font_subauthor, fill=accent)

    # Cashtags Pills in the center/right
    font_tag = _get_font(14)
    tag_x = 420
    tag_y = bot_y + 24
    draw.text((tag_x, tag_y + 5), "STRUMENTI:", font=_get_font(13), fill=(95, 110, 130))
    curr_tx = tag_x + 95

    for t in tickers[:4]:
        tag_text = f"${t}"
        t_bbox = draw.textbbox((0, 0), tag_text, font=font_tag)
        tw = t_bbox[2] - t_bbox[0] + 20
        th = 28
        _draw_rounded_rect(draw, (curr_tx, tag_y, curr_tx + tw, tag_y + th), radius=6, fill=(16, 24, 38), outline=accent_dim, width=1)
        draw.text((curr_tx + 10, tag_y + 5), tag_text, font=font_tag, fill=(230, 240, 255))
        curr_tx += tw + 10

    # Profile link right aligned
    font_link = _get_font(14)
    link_text = "etoro.com/people/andrearavalli"
    link_bbox = draw.textbbox((0, 0), link_text, font=link_link if 'link_link' in locals() else font_link)
    draw.text((CARD_W - 60 - (link_bbox[2] - link_bbox[0]), bot_y + 31), link_text, font=font_link, fill=(130, 150, 180))

    # Convert to RGB and save
    final_img = img.convert("RGB")
    final_img.save(output_path, "PNG", quality=95)
    return output_path


def generate_all_cards(json_path: str = None) -> List[str]:
    """Generate cards for all 20 episodes defined in JSON."""
    import json
    if json_path is None:
        json_path = os.path.join(BASE_DIR, "data", "etoro_educational_series.json")

    with open(json_path, "r", encoding="utf-8") as f:
        episodes = json.load(f)

    generated = []
    total = len(episodes)
    for ep in episodes:
        num = ep.get("episode", 1)
        title = ep.get("title", "")
        subtitle = ep.get("subtitle", "")
        pillars = ep.get("pillars", [])
        tickers = ep.get("tickers", [])
        palette = ep.get("palette", "cyan")
        out_file = os.path.join(OUTPUT_DIR, f"story_{num:02d}.png")

        path = generate_educational_card(
            episode=num,
            total_episodes=total,
            title=title,
            subtitle=subtitle,
            pillars=pillars,
            tickers=tickers,
            palette_name=palette,
            output_path=out_file,
        )
        generated.append(path)
        print(f"   ✓ Generated Episode {num:02d}/{total:02d}: {out_file}")

    return generated


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        ep_num = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        import json
        json_path = os.path.join(BASE_DIR, "data", "etoro_educational_series.json")
        with open(json_path, "r", encoding="utf-8") as f:
            episodes = json.load(f)
        ep = next((e for e in episodes if e["episode"] == ep_num), episodes[0])
        path = generate_educational_card(
            episode=ep["episode"],
            total_episodes=len(episodes),
            title=ep["title"],
            subtitle=ep["subtitle"],
            pillars=ep["pillars"],
            tickers=ep["tickers"],
            palette_name=ep.get("palette", "cyan"),
        )
        print(f"Generated single card: {path}")
    else:
        print("🎨 Generating all 20 educational series cards...")
        cards = generate_all_cards()
        print(f"🎉 Generated {len(cards)} cards successfully in {OUTPUT_DIR}")
