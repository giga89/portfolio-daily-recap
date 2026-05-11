#!/usr/bin/env python3
"""
Telegram Bot Sender
Sends portfolio recap messages to a Telegram bot
"""

import os
import requests

TELEGRAM_MAX_CHARS = 4096


def _split_message(message: str, max_length: int = TELEGRAM_MAX_CHARS) -> list[str]:
    """
    Split a long message into chunks that fit within Telegram's character limit.
    Tries to split at double-newlines (paragraphs) first, then at single newlines.
    """
    if len(message) <= max_length:
        return [message]

    chunks = []
    while len(message) > max_length:
        # Try to split at the last paragraph break before the limit
        split_at = message.rfind('\n\n', 0, max_length)
        if split_at == -1:
            # Fall back to last newline
            split_at = message.rfind('\n', 0, max_length)
        if split_at == -1:
            # No newline found, hard-cut at max_length
            split_at = max_length

        chunks.append(message[:split_at].strip())
        message = message[split_at:].strip()

    if message:
        chunks.append(message)

    return chunks


def _send_single_message(url: str, chat_id: str, text: str) -> bool:
    """Send a single text chunk to Telegram. Returns True on success."""
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text[:200]}")
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send message chunk to Telegram: {e}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error response status: {e.response.status_code}")
            print(f"Error response body: {e.response.text}")
        return False


def send_telegram_message(message: str) -> bool:
    """
    Send a message to Telegram bot.
    Automatically splits messages that exceed Telegram's 4096-character limit.

    Args:
        message: The message text to send

    Returns:
        bool: True if all chunks were sent successfully, False otherwise
    """
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')

    # Debug logs to verify environment variables
    print("=" * 50)
    print("🔍 DEBUG: Checking Telegram configuration...")
    print(f"Bot token present: {bool(bot_token)}")
    print(f"Chat ID present: {bool(chat_id)}")

    if bot_token:
        print(f"Bot token length: {len(bot_token)} characters")
        print(f"Bot token starts with: {bot_token[:10]}...")
    else:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN environment variable is not set or empty")

    if chat_id:
        print(f"Chat ID value: {chat_id}")
    else:
        print("❌ ERROR: TELEGRAM_CHAT_ID environment variable is not set or empty")

    print("=" * 50)

    if not bot_token or not chat_id:
        print("⚠️  Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        print("Skipping Telegram notification")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    chunks = _split_message(message)
    total = len(chunks)
    print(f"📡 Message length: {len(message)} chars → {total} chunk(s) to send")

    all_ok = True
    for i, chunk in enumerate(chunks, 1):
        print(f"🔄 Sending chunk {i}/{total} ({len(chunk)} chars)...")
        ok = _send_single_message(url, chat_id, chunk)
        if ok:
            print(f"✅ Chunk {i}/{total} sent successfully!")
        else:
            print(f"❌ Chunk {i}/{total} failed.")
            all_ok = False

    return all_ok

def send_telegram_photo(image_path: str, caption: str = None) -> bool:
    """
    Send a photo to Telegram bot
    """
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("⚠️  Telegram credentials missing, skipping photo.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
    try:
        with open(image_path, 'rb') as f:
            files = {'photo': f}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
                data['parse_mode'] = 'HTML'
                
            print(f"📸 Sending photo to Telegram: {image_path}...")
            response = requests.post(url, data=data, files=files, timeout=30)
            response.raise_for_status()
            print("✅ Photo sent successfully!")
            return True
    except Exception as e:
        print(f"❌ Failed to send photo: {e}")
        return False

def send_recap_to_telegram(recap_file_path: str, image_path: str = None) -> bool:
    """
    Read recap from file and send to Telegram
    
    Args:
        recap_file_path: Path to the recap text file
    
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"📂 Reading recap file: {recap_file_path}")
    
    try:
        with open(recap_file_path, 'r', encoding='utf-8') as f:
            message = f.read()
        
        print(f"📄 Recap file read successfully ({len(message)} characters)")
        
        # Send text message first
        success = send_telegram_message(message)
        
        # Then send image if provided
        if success and image_path and os.path.exists(image_path):
            send_telegram_photo(image_path, caption="📈 Performance Chart (Click to zoom)")
            
        return success
    except FileNotFoundError:
        print(f"❌ Recap file not found: {recap_file_path}")
        return False
    except Exception as e:
        print(f"❌ Error reading recap file: {e}")
        print(f"Error type: {type(e).__name__}")
        return False
