#!/usr/bin/env python3
"""
Educational Series Publisher for eToro
=====================================
Rotational publisher for the 20-week educational series "Investing Mastery".

Features:
  • Rotates sequentially through episodes 1 to 20
  • Tracks publication state in GitHub Gist (with local file fallback)
  • Attaches high-impact 1280x720 card generated for each episode
  • Resolves cashtags to eToro market IDs
  • Supports --dry-run for testing and CLI inspection
  • Designed to be triggered weekly (e.g. Wednesday 14:30 CET) via GitHub Actions
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

sys.path.insert(0, SRC_DIR)

import etoro_client
import etoro_sender
from educational_card_generator import generate_educational_card

SERIES_DATA_PATH = os.path.join(DATA_DIR, "etoro_educational_series.json")
LOCAL_STATE_PATH = os.path.join(DATA_DIR, "educational_series_state.json")
SERIES_IMG_DIR = os.path.join(ASSETS_DIR, "educational_series")


def load_series_episodes() -> list:
    """Load all episodes from JSON data."""
    if not os.path.exists(SERIES_DATA_PATH):
        raise FileNotFoundError(f"Series data not found at {SERIES_DATA_PATH}")
    with open(SERIES_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_series_state() -> Dict[str, Any]:
    """Load state from Gist or fallback to local JSON."""
    default_state = {
        "last_published_episode": 0,
        "last_published_date": None,
        "total_published_count": 0,
        "history": []
    }

    try:
        import gist_storage
        gist_data = gist_storage.load_data()
        if "educational_series" in gist_data:
            return gist_data["educational_series"]
    except Exception as e:
        print(f"ℹ️  Could not load state from Gist: {e}")

    if os.path.exists(LOCAL_STATE_PATH):
        try:
            with open(LOCAL_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return default_state


def save_series_state(state: Dict[str, Any]) -> bool:
    """Save state to local JSON and try to persist in Gist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(LOCAL_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Failed saving local state: {e}")

    try:
        import gist_storage
        gist_data = gist_storage.load_data()
        gist_data["educational_series"] = state
        gist_storage.save_data(gist_data)
        print("✅ Saved educational series state to GitHub Gist")
        return True
    except Exception as e:
        print(f"ℹ️  Could not save state to Gist (using local state): {e}")
        return False


def get_next_episode_number(state: Dict[str, Any], total_episodes: int) -> int:
    """Determine the next episode in sequential rotation (1..total, then loop)."""
    last_ep = state.get("last_published_episode", 0)
    next_ep = last_ep + 1
    if next_ep > total_episodes:
        next_ep = 1
    return next_ep


def ensure_card_image(ep: Dict[str, Any], total_episodes: int) -> str:
    """Ensure the card PNG image exists on disk, generate if missing."""
    ep_num = ep.get("episode", 1)
    os.makedirs(SERIES_IMG_DIR, exist_ok=True)
    img_path = os.path.join(SERIES_IMG_DIR, f"story_{ep_num:02d}.png")

    if not os.path.exists(img_path):
        print(f"🖼️ Card image missing for episode {ep_num}, generating...")
        generate_educational_card(
            episode=ep_num,
            total_episodes=total_episodes,
            title=ep.get("title", ""),
            subtitle=ep.get("subtitle", ""),
            pillars=ep.get("pillars", []),
            tickers=ep.get("tickers", []),
            palette_name=ep.get("palette", "cyan"),
            output_path=img_path,
        )
    return img_path


def publish_episode(
    episode_num: Optional[int] = None,
    dry_run: bool = False,
    force: bool = False,
) -> bool:
    """
    Publish an educational series post to eToro.

    Args:
        episode_num: Specific episode (1-20), or None to pick next in rotation
        dry_run: If True, do not actually call the eToro API
        force: If True, skip same-day duplicate check

    Returns:
        bool: True on success
    """
    episodes = load_series_episodes()
    total = len(episodes)
    state = get_series_state()

    if episode_num is None:
        target_ep_num = get_next_episode_number(state, total)
    else:
        target_ep_num = episode_num

    ep = next((e for e in episodes if e["episode"] == target_ep_num), None)
    if not ep:
        print(f"❌ Episode {target_ep_num} not found in series data.")
        return False

    # Check same-day run unless forced
    today_str = datetime.now().strftime("%Y-%m-%d")
    last_date = state.get("last_published_date")
    if last_date == today_str and not force and not dry_run:
        print(f"⚠️ Episode was already published today ({today_str}). Use --force to override.")
        return False

    img_path = ensure_card_image(ep, total)
    content = ep.get("post_content", "")
    title = ep.get("title", "")
    tickers = ep.get("tickers", [])

    print(f"\n==================================================")
    print(f"📚 INVESTING MASTERY · EPISODIO {target_ep_num:02d} / {total:02d}")
    print(f"📌 Titolo: {title}")
    print(f"🏷️  Cashtags: {', '.join(['$' + t for t in tickers])}")
    print(f"🖼️  Immagine allegata: {img_path}")
    print(f"==================================================\n")

    if dry_run:
        print("🔍 [DRY-RUN MODE] Post content preview:\n")
        print(content)
        print("\n🔍 [DRY-RUN MODE] Post not published to eToro. Image verified.\n")
        return True

    # Publish to eToro Feed
    success = etoro_sender.send_etoro_post(
        text=content,
        image_path=img_path,
        language="it"
    )

    if success:
        # Update state
        state["last_published_episode"] = target_ep_num
        state["last_published_date"] = today_str
        state["total_published_count"] = state.get("total_published_count", 0) + 1
        state.setdefault("history", []).append({
            "episode": target_ep_num,
            "title": title,
            "date": datetime.now().isoformat(),
            "post_id": etoro_sender.LAST_PUBLISHED_POST_ID,
        })
        save_series_state(state)
        print(f"🎉 Episode {target_ep_num} published and recorded in series rotation!")
        return True
    else:
        print(f"❌ Failed to publish episode {target_ep_num} to eToro.")
        return False


def print_status():
    """Print current series status and next scheduled episode."""
    episodes = load_series_episodes()
    total = len(episodes)
    state = get_series_state()
    last_ep = state.get("last_published_episode", 0)
    last_date = state.get("last_published_date", "Mai")
    total_pub = state.get("total_published_count", 0)
    next_ep = get_next_episode_number(state, total)

    next_data = next((e for e in episodes if e["episode"] == next_ep), None)

    print("\n📊 STATO SERIE EDUCATIONAL ETORO: 'INVESTING MASTERY'")
    print(f"─────────────────────────────────────────────────────")
    print(f"• Episodi totali disponibili: {total}")
    print(f"• Ultimo episodio pubblicato: #{last_ep:02d} ({last_date})")
    print(f"• Totale pubblicazioni finora: {total_pub}")
    print(f"• Prossimo in rotazione:      #{next_ep:02d} — {next_data.get('title') if next_data else ''}")
    if next_data:
        print(f"  ↳ Tickers collegati:       {', '.join(['$' + t for t in next_data.get('tickers', [])])}")
    print(f"─────────────────────────────────────────────────────\n")


def main():
    parser = argparse.ArgumentParser(description="Educational Series Publisher for eToro")
    parser.add_argument("--publish", action="store_true", help="Publish the next episode in rotation")
    parser.add_argument("--episode", type=int, default=None, help="Publish a specific episode number (1-20)")
    parser.add_argument("--status", action="store_true", help="Show current rotation status")
    parser.add_argument("--dry-run", action="store_true", help="Simulate publication without calling eToro API")
    parser.add_argument("--force", action="store_true", help="Force publication even if already published today")

    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.publish or args.dry_run or args.episode is not None:
        publish_episode(episode_num=args.episode, dry_run=args.dry_run, force=args.force)
    else:
        print_status()


if __name__ == "__main__":
    main()
