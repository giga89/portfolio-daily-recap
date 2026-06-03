#!/usr/bin/env python3
"""
Cover Image Generator
Generates a clean PIL-based cover image for each market session.
No AI required — uses only local assets and live portfolio data.

Layout (1280x720, 16:9):
  ┌─────────────────────────────────────────────────────────┐
  │  Session Label                          Date (top-right) │
  │                                                          │
  │                                                          │
  │                   +1.23%  (big, centered)               │
  │                   "Performance oggi"                     │
  │                                                          │
  │  [avatar]  Andrea Ravalli             etoro.com/...      │
  └─────────────────────────────────────────────────────────┘
"""

import os
import random
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Width / Height of the output image
IMAGE_W = 1280
IMAGE_H = 720

# Profile photo path (relative to repo root)
PROFILE_PHOTO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "profile_photo.jpg"
)

# Session accent colours (top-left label gradient seed)
SESSION_PALETTE = {
    "European market open": ((15, 25, 55), (35, 50, 100)),   # deep blue
    "U.S. market open":     ((10, 30, 25), (20, 60, 50)),    # deep teal/green
    "U.S. market close":    ((35, 15, 10), (80, 35, 15)),    # warm dark orange
    "Weekly recap (Sat)":   ((10, 30, 35), (20, 55, 65)),    # teal
    "Weekly recap (Sun)":   ((10, 12, 30), (25, 30, 65)),    # navy
    "Daily recap":          ((20, 20, 40), (35, 35, 70)),    # neutral purple
}

SESSION_LABELS = {
    "European market open": "APERTURA MERCATI EU",
    "U.S. market open":     "APERTURA WALL STREET",
    "U.S. market close":    "CHIUSURA MERCATI",
    "Weekly recap (Sat)":   "RECAP SETTIMANALE",
    "Weekly recap (Sun)":   "CLASSIFICA SETTIMANALE",
    "Daily recap":          "PORTFOLIO UPDATE",
}

URL_TEXT = "etoro.com/people/andrearavalli"
AUTHOR_TEXT = "Andrea Ravalli"


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    """Try to load a system TTF font; fall back to PIL default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _find_regular_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a regular (non-bold) font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _build_gradient_bg(c1: tuple, c2: tuple) -> "Image.Image":
    """Create a dark vertical gradient background with subtle chart lines."""
    img = Image.new("RGB", (IMAGE_W, IMAGE_H))
    draw = ImageDraw.Draw(img)

    for y in range(IMAGE_H):
        t = y / IMAGE_H
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        draw.line([(0, y), (IMAGE_W, y)], fill=(r, g, b))

    # Faint horizontal grid lines
    overlay = Image.new("RGBA", (IMAGE_W, IMAGE_H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    for y in range(100, IMAGE_H - 100, 70):
        odraw.line([(40, y), (IMAGE_W - 40, y)], fill=(255, 255, 255, 10), width=1)

    # Fake candlestick chart strip
    random.seed(99)
    x = 60
    prev_y = IMAGE_H // 2 + 50
    while x < IMAGE_W - 60:
        direction = random.choice([-1, 1])
        body_h = random.randint(8, 35)
        y = prev_y + direction * random.randint(4, 25)
        y = max(120, min(IMAGE_H - 160, y))
        y_end = y + body_h * direction
        y_top, y_bot = min(y, y_end), max(y, y_end)
        bar_color = (0, 200, 80, 18) if direction > 0 else (200, 50, 50, 18)
        odraw.rectangle([x, y_top, x + 10, y_bot], fill=bar_color)
        odraw.line([(x + 5, y_top - 12), (x + 5, y_bot + 12)], fill=bar_color, width=1)
        prev_y = y
        x += random.randint(18, 30)

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    return img


def _circular_avatar(photo_path: str, size: int = 100) -> "Image.Image | None":
    """Load the profile photo and render it as a circular avatar with a border ring."""
    try:
        photo = Image.open(photo_path).convert("RGBA")
        w, h = photo.size
        side = min(w, h)
        photo = photo.crop(((w - side) // 2, (h - side) // 2,
                             (w + side) // 2, (h + side) // 2))
        photo = photo.resize((size, size), Image.LANCZOS)

        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)

        avatar = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        avatar.paste(photo, (0, 0), mask)

        # Bordered frame
        frame_size = size + 8
        frame = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
        fdraw = ImageDraw.Draw(frame)
        fdraw.ellipse([0, 0, frame_size - 1, frame_size - 1],
                      outline=(0, 210, 10, 255), width=3)
        fdraw.ellipse([2, 2, frame_size - 3, frame_size - 3],
                      outline=(255, 255, 255, 200), width=2)
        frame.paste(avatar, (4, 4), avatar)
        return frame
    except Exception as exc:
        print(f"   Warning: could not load avatar — {exc}")
        return None


def generate_cover(
    session_name: str,
    portfolio_daily: float = 0.0,
    output_path: str = "output/cover.png",
) -> str | None:
    """
    Generate a clean cover image for the given market session.

    Args:
        session_name:    Market session identifier.
        portfolio_daily: Daily portfolio performance in percent.
        output_path:     Destination file path.

    Returns:
        Saved file path, or None on failure.
    """
    if not PIL_AVAILABLE:
        print("Warning: Pillow not available, skipping cover generation")
        return None

    # ── Background ──────────────────────────────────────────────────────────
    c1, c2 = SESSION_PALETTE.get(session_name, SESSION_PALETTE["Daily recap"])
    img = _build_gradient_bg(c1, c2).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # ── Dark gradient bar at the bottom ────────────────────────────────────
    bar_h = 110
    bar_overlay = Image.new("RGBA", (IMAGE_W, IMAGE_H), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bar_overlay)
    for y in range(bar_h):
        alpha = int(220 * (y / bar_h))
        bdraw.line([(0, IMAGE_H - bar_h + y), (IMAGE_W, IMAGE_H - bar_h + y)],
                   fill=(8, 8, 12, alpha))
    img = Image.alpha_composite(img, bar_overlay)
    draw = ImageDraw.Draw(img)

    # ── Fonts ───────────────────────────────────────────────────────────────
    font_perf_big   = _find_font(180)         # giant % number
    font_label_sub  = _find_regular_font(22)  # small label under the number
    font_session    = _find_font(20)          # top-left session label
    font_date       = _find_regular_font(18)  # top-right date
    font_author     = _find_regular_font(18)  # bottom-center author name
    font_url        = _find_regular_font(16)  # bottom-right URL

    # ── Colours ─────────────────────────────────────────────────────────────
    perf_color = (60, 210, 80, 255) if portfolio_daily >= 0 else (230, 55, 55, 255)
    perf_text  = f"{portfolio_daily:+.2f}%"
    sub_label  = "Performance di oggi"

    # ── Centre: big % number ────────────────────────────────────────────────
    bbox = draw.textbbox((0, 0), perf_text, font=font_perf_big)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    center_x = (IMAGE_W - tw) // 2 - bbox[0]
    center_y = (IMAGE_H - th) // 2 - 40 - bbox[1]   # slightly above center

    # Soft glow shadow
    shadow_color = (*perf_color[:3], 40)
    for dx, dy in [(-3, 3), (3, 3), (-3, -3), (3, -3), (0, 6), (0, -6)]:
        draw.text((center_x + dx, center_y + dy), perf_text,
                  fill=shadow_color, font=font_perf_big)
    draw.text((center_x, center_y), perf_text, fill=perf_color, font=font_perf_big)

    # Sub-label under the number
    bbox_sub = draw.textbbox((0, 0), sub_label, font=font_label_sub)
    sub_x = (IMAGE_W - (bbox_sub[2] - bbox_sub[0])) // 2
    sub_y = center_y + th + 10
    draw.text((sub_x, sub_y), sub_label, fill=(200, 200, 200, 200), font=font_label_sub)

    # ── Top-left: session label ──────────────────────────────────────────────
    label_text = SESSION_LABELS.get(session_name, session_name.upper())
    draw.text((28, 22), label_text, fill=(255, 255, 255, 220), font=font_session)

    # ── Top-right: date ─────────────────────────────────────────────────────
    date_text = datetime.now().strftime("%d %b %Y  •  %H:%M")
    bbox_date = draw.textbbox((0, 0), date_text, font=font_date)
    date_x = IMAGE_W - (bbox_date[2] - bbox_date[0]) - 28
    draw.text((date_x, 22), date_text, fill=(200, 200, 200, 180), font=font_date)

    # ── Bottom-left: circular avatar + author name ───────────────────────────
    avatar = None
    if os.path.exists(PROFILE_PHOTO_PATH):
        avatar = _circular_avatar(PROFILE_PHOTO_PATH, size=72)

    bottom_y = IMAGE_H - bar_h + (bar_h - 78) // 2    # vertically centred in bar
    text_x = 24

    if avatar:
        img.paste(avatar, (24, bottom_y), avatar)
        text_x = 24 + avatar.size[0] + 12

    bbox_auth = draw.textbbox((0, 0), AUTHOR_TEXT, font=font_author)
    auth_h = bbox_auth[3] - bbox_auth[1]
    draw.text(
        (text_x, bottom_y + (78 - auth_h) // 2),
        AUTHOR_TEXT,
        fill=(240, 240, 240, 240),
        font=font_author,
    )

    # ── Bottom-right: URL ────────────────────────────────────────────────────
    bbox_url = draw.textbbox((0, 0), URL_TEXT, font=font_url)
    url_w = bbox_url[2] - bbox_url[0]
    url_h = bbox_url[3] - bbox_url[1]
    url_x = IMAGE_W - url_w - 28
    url_y = IMAGE_H - bar_h + (bar_h - url_h) // 2
    draw.text((url_x, url_y), URL_TEXT, fill=(160, 200, 240, 200), font=font_url)

    # ── Save ────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    final = img.convert("RGB")
    final.save(output_path, "PNG", optimize=True)

    print(f"Cover image saved: {output_path} ({IMAGE_W}x{IMAGE_H})")
    return output_path
