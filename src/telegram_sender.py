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
    
    if not bot_token or not chat_id:
        print("Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        print("Skipping Telegram notification")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Message sent to Telegram successfully!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send message to Telegram: {e}")
        return False

def send_recap_to_telegram(recap_file_path: str) -> bool:
    """
    Read recap from file and send to Telegram
    
    Args:
        recap_file_path: Path to the recap text file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(recap_file_path, 'r', encoding='utf-8') as f:
            message = f.read()
        
        return send_telegram_message(message)
    except FileNotFoundError:
        print(f"❌ Recap file not found: {recap_file_path}")
        return False
    except Exception as e:
        print(f"❌ Error reading recap file: {e}")
        return False
