#!/usr/bin/env python3
"""
Telegram Bot Sender
Sends portfolio recap messages to a Telegram bot
"""

import os
import requests

def send_telegram_message(message: str) -> bool:
    """
    Send a message to Telegram bot
    
    Args:
        message: The message text to send
    
    Returns:
        bool: True if successful, False otherwise
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
    
    print(f"📡 Attempting to send message to Telegram API...")
    print(f"API URL: {url[:50]}...")
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        print("🔄 Sending POST request to Telegram...")
        response = requests.post(url, json=payload, timeout=10)
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text[:200]}")
        
        response.raise_for_status()
        print("✅ Message sent to Telegram successfully!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send message to Telegram: {e}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error response status: {e.response.status_code}")
            print(f"Error response body: {e.response.text}")
        return False
        return False

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
