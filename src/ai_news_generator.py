#!/usr/bin/env python3
"""
AI News Generator
Generates market news recap using Google Gemini API
"""

import os
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️  google-genai not installed, AI news generation will be disabled")

from config import PORTFOLIO_TICKERS


def generate_market_news_recap():
    """
    Generate AI-powered market news recap for USA, CHINA, and EU markets
    
    Returns:
        str: Formatted news recap or empty string if API key not set
    """
    if not GENAI_AVAILABLE:
        print("⚠️  google-genai package not available, skipping AI news generation")
        return ""
    
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("⚠️  Warning: GEMINI_API_KEY not set, skipping AI news generation")
        return ""
    
    try:
        # Configure Gemini client
        client = genai.Client(api_key=api_key)
        
        # Extract portfolio context
        portfolio_symbols = list(PORTFOLIO_TICKERS.keys())
        portfolio_context = ", ".join(portfolio_symbols[:15])  # First 15 tickers
        
        # Create prompt
        prompt = f"""You are a financial market analyst. Generate a brief, concise daily market recap for investors.

Focus on these 3 markets: USA, CHINA, EU

Portfolio context (my holdings include): {portfolio_context}

Requirements:
- Keep it VERY SHORT (max 5-6 sentences total)
- Highlight TODAY's most important market movements
- Mention key sectors: Tech, Healthcare, Energy, Financials if relevant
- Use a professional but engaging tone
- Include specific indices if relevant (S&P500, Nasdaq, Shanghai Composite, Euro Stoxx)
- Format for Telegram (plain text, use emoji sparingly)

Output format:
🌍 MARKET NEWS RECAP

[Your 5-6 sentence recap here covering USA, CHINA, EU markets]
"""
        
        print("🤖 Generating AI market news recap...")
        
        # Generate content using the new API
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        
        if response and response.text:
            print("✅ AI news recap generated successfully!")
            return "\n" + response.text.strip() + "\n"
        else:
            print("⚠️  AI response was empty")
            return ""
            
    except Exception as e:
        print(f"❌ Error generating AI news recap: {e}")
        print(f"Error type: {type(e).__name__}")
        return ""



def get_why_copy_message():
    """
    Returns the fixed message explaining why to copy this portfolio
    
    Returns:
        str: Formatted fixed message
    """
    message = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 PERCHÉ COPIARE QUESTO PORTAFOGLIO?

✅ +161% dal 2020 (cambio strategia)
✅ Media +32% annuo (raddoppi in ~2 anni)
✅ Diversificazione intelligente su 3 continenti
✅ Focus su megatrend: AI, Healthcare, Energy
✅ Mix ETF + singoli titoli ad alto potenziale
✅ Gestione attiva e trasparente

📊 Performance migliore dell'S&P500 e MSCI World
🎯 Strategia long-term basata su fondamentali solidi
🔄 Ribilanciamento periodico per ottimizzare risk/reward

@AndreaRavalli
━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return message
