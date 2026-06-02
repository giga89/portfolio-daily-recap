#!/usr/bin/env python3
"""
AI Cover Image Generator
Creates AI-generated cover images for each market session using Gemini's image generation.
Overlays Andrea Ravalli's profile photo as a professional circular avatar with branding.
"""

import os
import time
from datetime import datetime

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ── Profile photo path (relative to repo root) ──────────────────────────────
PROFILE_PHOTO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "profile_photo.jpg"
)


# ── Session-specific image style prompts ─────────────────────────────────────

SESSION_STYLES = {
    "European market open": {
        "time_of_day": "early morning golden hour",
        "landmarks": "European financial landmarks (London Big Ben, Frankfurt skyline, Milan Duomo)",
        "mood": "fresh start, anticipation, opportunity",
        "accent_color": "blue and gold tones",
        "icon": "sunrise over European cityscape",
        "overlay_label": "APERTURA MERCATI EU 🇪🇺",
    },
    "U.S. market open": {
        "time_of_day": "bright midday",
        "landmarks": "Wall Street, New York skyline, Nasdaq building",
        "mood": "energy, momentum, action",
        "accent_color": "electric blue and green tones",
        "icon": "Wall Street bull, trading floor energy",
        "overlay_label": "APERTURA WALL STREET 🇺🇸",
    },
    "U.S. market close": {
        "time_of_day": "dramatic sunset / dusk",
        "landmarks": "New York skyline at sunset, Wall Street at closing bell",
        "mood": "reflection, results, summary of the day",
        "accent_color": "warm orange, purple and dark blue tones",
        "icon": "closing bell, sunset over financial district",
        "overlay_label": "CHIUSURA MERCATI 📈",
    },
    "Weekly recap (Sat)": {
        "time_of_day": "calm weekend morning",
        "landmarks": "panoramic world map with financial hubs highlighted",
        "mood": "analysis, review, perspective",
        "accent_color": "calm teal and silver tones",
        "icon": "world markets overview, weekly calendar",
        "overlay_label": "RECAP SETTIMANALE 📊",
    },
    "Weekly recap (Sun)": {
        "time_of_day": "Sunday evening, preparing for the week",
        "landmarks": "global stock exchange collage",
        "mood": "strategic planning, outlook, confidence",
        "accent_color": "deep navy and gold tones",
        "icon": "chess pieces on financial chart, strategic thinking",
        "overlay_label": "CLASSIFICA SETTIMANALE 🏆",
    },
}

# Models to try for image generation (in order of preference)
IMAGE_MODELS = [
    "gemini-2.0-flash-preview-image-generation",
    "gemini-2.0-flash-exp",
]


def _create_circular_avatar(photo_path: str, size: int = 180) -> Image.Image | None:
    """Create a circular avatar with a glowing border from a profile photo."""
    try:
        photo = Image.open(photo_path).convert("RGBA")

        # Crop to square (center crop)
        w, h = photo.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        photo = photo.crop((left, top, left + side, top + side))
        photo = photo.resize((size, size), Image.LANCZOS)

        # Create circular mask
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse([0, 0, size - 1, size - 1], fill=255)

        # Apply mask
        avatar = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        avatar.paste(photo, (0, 0), mask)

        # Add border ring
        border_size = size + 8
        bordered = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(bordered)

        # Outer glow ring (green accent)
        border_draw.ellipse([0, 0, border_size - 1, border_size - 1],
                            outline=(0, 200, 5, 255), width=3)
        # White inner ring
        border_draw.ellipse([2, 2, border_size - 3, border_size - 3],
                            outline=(255, 255, 255, 220), width=2)

        # Paste avatar centered in the bordered image
        bordered.paste(avatar, (4, 4), avatar)

        return bordered

    except Exception as e:
        print(f"⚠️  Could not create circular avatar: {e}")
        return None


def _add_overlay(
    background: Image.Image,
    avatar: Image.Image | None,
    session_label: str,
    perf_text: str,
    date_text: str,
) -> Image.Image:
    """
    Add professional overlay to the AI-generated background:
    - Semi-transparent dark gradient at bottom
    - Circular profile avatar
    - Session label and performance text
    - Branding watermark
    """
    img = background.copy().convert("RGBA")
    width, height = img.size

    # Create overlay layer
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Bottom gradient bar (semi-transparent dark area)
    bar_height = 150
    for y in range(bar_height):
        # Gradient from transparent to semi-opaque
        alpha = int(200 * (y / bar_height))
        draw.line(
            [(0, height - bar_height + y), (width, height - bar_height + y)],
            fill=(10, 10, 15, alpha),
        )

    # Top-left subtle gradient for date
    for y in range(60):
        alpha = int(150 * (1 - y / 60))
        draw.line([(0, y), (width, y)], fill=(10, 10, 15, alpha))

    # Composite overlay onto image
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Try to load a nice font, fallback to default
    font_large = None
    font_medium = None
    font_small = None
    font_tiny = None

    # Try common system font paths
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/segoeui.ttf",  # Windows
        "C:/Windows/Fonts/segoeuib.ttf",
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
    ]

    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font_large = ImageFont.truetype(fp, 32)
                font_medium = ImageFont.truetype(fp, 22)
                font_small = ImageFont.truetype(fp, 16)
                font_tiny = ImageFont.truetype(fp, 12)
                break
            except Exception:
                continue

    if font_large is None:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large
        font_tiny = font_large

    # --- Draw content ---

    # Date in top-left
    draw.text((20, 15), date_text, fill=(255, 255, 255, 200), font=font_small)

    # Performance badge in top-right
    perf_color = (0, 200, 5, 255) if "+" in perf_text else (255, 80, 80, 255)
    bbox = draw.textbbox((0, 0), perf_text, font=font_medium)
    perf_w = bbox[2] - bbox[0]
    # Background pill for perf badge
    pill_x = width - perf_w - 40
    pill_y = 12
    draw.rounded_rectangle(
        [pill_x, pill_y, width - 15, pill_y + 36],
        radius=18,
        fill=(0, 0, 0, 180),
    )
    draw.text((pill_x + 12, pill_y + 6), perf_text, fill=perf_color, font=font_medium)

    # Avatar + text in bottom-left
    text_x = 20
    if avatar:
        avatar_y = height - bar_height + (bar_height - avatar.size[1]) // 2
        img.paste(avatar, (20, avatar_y), avatar)
        text_x = 20 + avatar.size[0] + 15

    # Session label
    label_y = height - bar_height + 25
    draw.text((text_x, label_y), session_label, fill=(255, 255, 255, 255), font=font_large)

    # Name
    draw.text(
        (text_x, label_y + 42),
        "Andrea Ravalli — eToro Investor",
        fill=(200, 200, 200, 220),
        font=font_small,
    )

    # Watermark bottom-right
    draw.text(
        (width - 180, height - 22),
        "etoro.com/people/andrearavalli",
        fill=(150, 150, 150, 150),
        font=font_tiny,
    )

    return img.convert("RGB")


def generate_session_cover(
    session_name: str,
    recap_summary: str = "",
    portfolio_daily: float = 0.0,
    output_path: str = "output/ai_cover.png",
) -> str | None:
    """
    Generate an AI cover image for the given market session.

    Args:
        session_name: Market session name (e.g., "European market open")
        recap_summary: Brief summary of the day's recap for context
        portfolio_daily: Daily portfolio performance percentage
        output_path: Where to save the generated image

    Returns:
        Path to the saved image, or None if generation failed
    """
    if not GENAI_AVAILABLE:
        print("⚠️  google-genai not available, skipping AI cover image generation")
        return None

    if not PIL_AVAILABLE:
        print("⚠️  Pillow not available, skipping AI cover image generation")
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  GEMINI_API_KEY not set, skipping AI cover image generation")
        return None

    # Get session-specific style
    style = SESSION_STYLES.get(session_name, SESSION_STYLES.get("U.S. market close"))

    # Determine market mood from performance
    if portfolio_daily > 1.5:
        market_mood = "strongly bullish, optimistic, celebratory green"
    elif portfolio_daily > 0.3:
        market_mood = "moderately bullish, positive, hopeful green"
    elif portfolio_daily > -0.3:
        market_mood = "neutral, balanced, steady"
    elif portfolio_daily > -1.5:
        market_mood = "slightly bearish, cautious, amber warning tones"
    else:
        market_mood = "bearish, dramatic red, storm clouds"

    # Build the image prompt
    today_str = datetime.now().strftime("%A, %B %d, %Y")

    prompt = f"""Create a stunning, photorealistic editorial-style financial magazine cover image.

SCENE: {style['icon']} during {style['time_of_day']}.
COLOR PALETTE: {style['accent_color']} with {market_mood} undertones.
LANDMARKS: {style['landmarks']}.
MOOD: {style['mood']}, {market_mood}.

STYLE REQUIREMENTS:
- Photorealistic, cinematic quality, high contrast
- Modern financial media aesthetic (like Bloomberg, Financial Times covers)
- Dramatic lighting with lens flare effects
- Include subtle abstract data visualization elements (faint chart lines, candlesticks) overlaid as a semi-transparent layer
- NO text, NO numbers, NO letters, NO watermarks, NO people - purely visual landscape/cityscape
- Wide aspect ratio (16:9)
- Professional, premium look suitable for social media
- Leave the bottom 20% of the image slightly darker (for text overlay later)

The overall feeling should be a premium financial news publication cover that conveys the {market_mood} mood of {today_str}."""

    print(f"🎨 Generating AI cover image for '{session_name}'...")
    print(f"   Performance: {portfolio_daily:+.2f}%")

    try:
        client = genai.Client(api_key=api_key)

        bg_image = None
        for model_name in IMAGE_MODELS:
            try:
                print(f"   Trying model: {model_name}...")

                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
                )

                # Extract image from response
                if response and response.candidates:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data is not None:
                            bg_image = Image.open(BytesIO(part.inline_data.data))
                            print(f"   ✅ Background generated by {model_name} ({bg_image.size})")
                            break

                if bg_image:
                    break

                print(f"   ⚠️ No image in response from {model_name}")

            except Exception as model_error:
                error_msg = str(model_error).lower()
                print(f"   ⚠️ Model {model_name} failed: {model_error}")

                if "quota" in error_msg or "429" in error_msg:
                    print("   Rate limited, waiting 5s...")
                    time.sleep(5)
                continue

        if bg_image is None:
            print("❌ All image models failed — no background generated")
            return None

        # Resize background to 1280x720 (16:9)
        bg_image = bg_image.resize((1280, 720), Image.LANCZOS)

        # Create the circular avatar from profile photo
        avatar = None
        if os.path.exists(PROFILE_PHOTO_PATH):
            avatar = _create_circular_avatar(PROFILE_PHOTO_PATH, size=100)
            if avatar:
                print(f"   ✅ Profile avatar loaded ({avatar.size})")
        else:
            print(f"   ⚠️ Profile photo not found at {PROFILE_PHOTO_PATH}")

        # Build overlay texts
        perf_text = f"{'📈' if portfolio_daily >= 0 else '📉'} {portfolio_daily:+.2f}%"
        date_text = datetime.now().strftime("%d %b %Y • %H:%M")
        session_label = style.get("overlay_label", session_name.upper())

        # Composite the final image
        final_image = _add_overlay(bg_image, avatar, session_label, perf_text, date_text)

        # Save
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        final_image.save(output_path, "PNG", quality=95)

        print(f"✅ AI cover image saved: {output_path} ({final_image.size[0]}x{final_image.size[1]})")
        return output_path

    except Exception as e:
        print(f"❌ Error generating AI cover image: {e}")
        import traceback
        traceback.print_exc()
        return None
