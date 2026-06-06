#!/usr/bin/env python3
"""
AI News Generator
Generates market news recap using Google Gemini API
"""

import os
import time
import re
from datetime import datetime
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️  google-genai not installed, AI news generation will be disabled")

from config import PORTFOLIO_TICKERS

# Import Gist storage module
try:
    from gist_storage import load_data, save_data, load_recap_history, save_to_history
    GIST_STORAGE_AVAILABLE = True
except ImportError:
    GIST_STORAGE_AVAILABLE = False
    print("⚠️  gist_storage module not available, using fallback")

# Import API usage tracker
try:
    from api_usage_tracker import log_api_request, save_usage_report
    API_TRACKER_AVAILABLE = True
except ImportError:
    API_TRACKER_AVAILABLE = False
    print("⚠️  api_usage_tracker module not available, usage tracking disabled")

# Maximum number of $ tags per post
MAX_TAGS_PER_POST = 4

# Valid eToro symbols for tagging (only use these in posts)
# These are confirmed to exist on eToro platform
# Exclude Russian stocks (sanctioned/untradeable)
_EXCLUDED_FROM_TAGS = {'MNODL.L', 'NVTKL.L'}
ETORO_VALID_SYMBOLS = [t for t in PORTFOLIO_TICKERS.keys() if t not in _EXCLUDED_FROM_TAGS]


def _get_all_portfolio_tags():
    """Get all valid portfolio ticker tags for eToro"""
    # Map to eToro symbols (keys of PORTFOLIO_TICKERS), excluding Russian stocks
    return [t for t in PORTFOLIO_TICKERS.keys() if t not in _EXCLUDED_FROM_TAGS]


def _select_tags_for_rotation(max_tags=MAX_TAGS_PER_POST, excluded_tags=None, allowed_tickers=None):
    """
    Select tags for the current post with rotation to ensure variety.
    
    Args:
        max_tags: Maximum number of tags to select
        excluded_tags: List of tags to exclude (e.g. already used in this post)
        allowed_tickers: Optional list of tickers to restrict the selection to
    
    Returns:
        list: List of selected tags
    """
    all_tags = _get_all_portfolio_tags()
    
    if allowed_tickers:
        allowed_normalized = [t.replace('.', '').upper() for t in allowed_tickers]
        all_tags = [t for t in all_tags if t.replace('.', '').upper() in allowed_normalized]
    
    if excluded_tags:
        # Remove excluded tags from candidates
        excluded_normalized = [t.replace('.', '').upper() for t in excluded_tags]
        all_tags = [t for t in all_tags if t.replace('.', '').upper() not in excluded_normalized]
    
    if max_tags <= 0:
        return []

    try:
        data = load_data()
        used_tags = data.get('used_tags', [])

        # Prioritize tags that haven't been used recently
        unused_tags = [tag for tag in all_tags if tag not in used_tags]

        if len(unused_tags) >= max_tags:
            selected = unused_tags[:max_tags]
        elif unused_tags:
            # Not enough unused — fill the gap from all_tags (least-recently-used first)
            already = set(unused_tags)
            filler = [t for t in all_tags if t not in already]
            selected = unused_tags + filler[:max_tags - len(unused_tags)]
        else:
            # All tags recently used — just take from the full list
            selected = all_tags[:max_tags]

        # Guarantee we always return exactly max_tags (safety net: pool was too small)
        if len(selected) < max_tags:
            # all_tags already had excluded_tags stripped; ignore excluded to fill
            full_pool = _get_all_portfolio_tags()
            if allowed_tickers:
                allowed_normalized = [t.replace('.', '').upper() for t in allowed_tickers]
                full_pool = [t for t in full_pool if t.replace('.', '').upper() in allowed_normalized]
            extra = [t for t in full_pool if t not in selected]
            selected = selected + extra[:max_tags - len(selected)]

        # Update used-tags rotation history (keep last 2 full rounds)
        new_used = used_tags + selected
        max_history = len(_get_all_portfolio_tags()) * 2
        data['used_tags'] = new_used[-max_history:] if len(new_used) > max_history else new_used

        save_data(data)

        return selected

    except Exception as e:
        print(f"⚠️ Error in tag rotation: {e}")
        return all_tags[:max_tags]


def _is_valid_ticker(tag):
    """Check if a tag looks like a valid stock/index ticker after normalization"""
    tag_upper = tag.upper()
    if not (1 <= len(tag_upper) <= 10):
        return False
    # Must be uppercase alphanumeric, dots, or hyphens
    return bool(re.match(r'^[A-Z0-9\-\.]+$', tag_upper))


def _limit_tags_in_text(text, allowed_tags, max_tags=MAX_TAGS_PER_POST):
    """
    Ensure text has at most max_tags $ symbols, and only uses allowed tags.
    Allows at most 1 dynamic trending stock/index tag not in allowed_tags,
    as long as it looks like a valid ticker and fits in the total tag budget.
    
    Args:
        text: The generated text
        allowed_tags: List of allowed portfolio tag symbols (without $)
        max_tags: Maximum number of tags to keep
    
    Returns:
        str: Text with limited and validated tags
    """
    # Find all $ tags in the text
    tag_pattern = r'\$([A-Za-z0-9\-\.]+)'
    
    tags_found = []
    trending_found = False
    
    def tag_replacer(match):
        nonlocal trending_found
        tag = match.group(1)
        # Normalize tag (remove dots and hyphens for comparison)
        tag_normalized = tag.replace('.', '').replace('-', '').upper()
        
        # 1. Check if it's an allowed portfolio tag
        matched_portfolio_tag = None
        for t in allowed_tags:
            if t.replace('.', '').replace('-', '').upper() == tag_normalized:
                matched_portfolio_tag = t
                break
                
        if matched_portfolio_tag:
            # Avoid duplicate tagging of the same symbol in a single post
            if matched_portfolio_tag not in tags_found and len(tags_found) < max_tags:
                tags_found.append(matched_portfolio_tag)
                # Ensure a space before and after the tag as requested by the user
                return f' ${matched_portfolio_tag} '
            else:
                # Exceeded max tags or duplicate, remove the $ prefix
                return matched_portfolio_tag
                
        # 2. Check if it's a valid trending index/stock tag (allow at most 1)
        if not trending_found and _is_valid_ticker(tag):
            tag_upper = tag.upper()
            if tag_upper not in tags_found and len(tags_found) < max_tags:
                tags_found.append(tag_upper)
                trending_found = True
                return f' ${tag_upper} '
            else:
                return tag_upper
                
        # Not allowed, remove the $ prefix
        return tag
            
    result = re.sub(tag_pattern, tag_replacer, text)
    # Collapse multiple spaces created by padding tags into a single space
    result = re.sub(r' +', ' ', result)
    return result


def _remove_intro_text(text):
    """
    Remove introductory sentences that Gemini sometimes adds before the Market Overview.
    Examples: "Here is your concise daily market recap for today, YYYY-MM-DD:"
    
    Args:
        text: The full recap text
    
    Returns:
        str: Text with intro removed
    """
    # Pattern to match common intro formats
    # Match lines that start with "Here is" or similar until the first real section
    intro_patterns = [
        r'^Here is .*?\n+',
        r'^Below is .*?\n+',
        r'^Here\'s .*?\n+',
    ]
    
    cleaned_text = text
    for pattern in intro_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Also remove any leading whitespace after removal
    return cleaned_text.lstrip()


def _remove_market_section_tags(text):
    """
    Remove all $ tags from the MARKET OVERVIEW section.
    Keep tags only in PORTFOLIO FOCUS section.
    
    Args:
        text: The full recap text
    
    Returns:
        str: Text with tags removed from market section
    """
    # Split into sections
    sections = text.split('💼 PORTFOLIO FOCUS')
    
    if len(sections) == 2:
        market_section = sections[0]
        portfolio_section = sections[1]
        
        # Remove all $ tags from market section
        tag_pattern = r'\$([A-Za-z0-9\-\.]+)'
        market_section_clean = re.sub(tag_pattern, r'\1', market_section)
        
        return market_section_clean + '💼 PORTFOLIO FOCUS' + portfolio_section
    
    return text



def get_recent_tags(limit=None):
    """
    Get list of recently used tags from storage.
    Args:
        limit: Return only the last N tags. If None, return all history.
    """
    if not GIST_STORAGE_AVAILABLE:
        return []
    
    try:
        data = load_data()
        tags = data.get('used_tags', [])
        if limit:
            return tags[-limit:]
        return tags
    except Exception:
        return []


def update_rotation_history(new_tags):
    """
    Update the list of used tags in Gist storage.
    Call this when tags are used outside of this module (e.g. in formatter).
    """
    if not GIST_STORAGE_AVAILABLE or not new_tags:
        return

    try:
        # Normalize tags
        normalized_new = [t.replace('$', '').replace('.', '').upper() for t in new_tags]
        
        data = load_data()
        used_tags = data.get('used_tags', [])
        
        # Add new tags
        updated_used = used_tags + normalized_new
        
        # Keep history limited (e.g. 20 items)
        all_tickers = _get_all_portfolio_tags()
        max_history = len(all_tickers) * 2
        
        data['used_tags'] = updated_used[-max_history:] if len(updated_used) > max_history else updated_used
        save_data(data)
        print(f"🔄 Updated tag rotation history with: {normalized_new}")
            
    except Exception as e:
        print(f"⚠️ Error updating tag rotation: {e}")


def generate_monthly_ai_recap(max_tags=MAX_TAGS_PER_POST, excluded_tags=None):
    """
    Generate AI-powered monthly market recap summarizing major events over the past month
    
    Args:
        max_tags: Maximum number of $ tags allowed in the AI output
        excluded_tags: List of tags already used elsewhere in the post
        
    Returns:
        str: Formatted monthly recap or empty string if API key not set
    """
    if not GENAI_AVAILABLE:
        print("⚠️  google-genai package not available, skipping AI monthly recap")
        return ""
    
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("⚠️  Warning: GEMINI_API_KEY not set, skipping AI monthly recap")
        return ""
    
    # Models in order of preference — each belongs to a DIFFERENT quota bucket.
    # Order: 2.0-flash first (more stable at EU open hour), 2.5-flash second
    # (frequently 503-overloaded at 07:00 UTC), 2.0-flash-lite third (smaller
    # model but genuinely independent daily quota — gemini-1.5 is deprecated
    # and returns 404 in API v1beta).
    models_to_try = [
        'gemini-2.0-flash',      # main free-tier bucket, stable
        'gemini-2.5-flash',      # newest bucket, but often 503 at EU peak hours
        'gemini-2.0-flash-lite', # lighter model, independent daily quota
    ]
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Select tags for this post (with rotation)
        selected_tags = []
        selected_tags_str = "None"
        tag_instruction = ""
        
        if max_tags > 0:
            portfolio_budget = max(0, max_tags - 1)
            selected_tags = _select_tags_for_rotation(portfolio_budget, excluded_tags)
            selected_tags_str = ', '.join([f'${tag}' for tag in selected_tags]) if selected_tags else "None"
            tag_instruction = f"""
- IMPORTANT: You MUST dedicate exactly 1 tag of the allowed {max_tags} tags to a highly discussed/trending index or stock of the month that you will discuss in the recap. Choose this tag from popular indices like $NSDQ100, $SPX500 (highly recommended to attract copiers), or if there is major news about a specific hot stock this month (e.g. $TSLA, $AAPL, $BTC, etc.), you can tag and discuss that instead. This index/stock MUST be included and explained in the recap.
- In addition to this trending tag, you can use at most {portfolio_budget} tags from this portfolio list: {selected_tags_str}.
- Never exceed the total limit of {max_tags} tags with the $ symbol in the post.
"""
        else:
            tag_instruction = """
- Do NOT use any $ tags in this section.
"""
        
        # Get current month/year for context
        now = datetime.now()
        current_month = now.strftime('%B %Y')  # e.g., "January 2026"
        
        # Get all portfolio tickers for context (exclude Russian stocks)
        excluded_tickers = {'MNODL.L', 'NVTKL.L'}
        portfolio_symbols = [t for t in PORTFOLIO_TICKERS.keys() if t not in excluded_tickers]
        portfolio_context = ", ".join(portfolio_symbols)
        # Add crypto classification note so AI doesn't confuse TRX with a stock
        portfolio_context += "\nNOTA: TRX è la criptovaluta TRON (non un'azione). Trattalo come crypto nei commenti."
        
        prompt = f"""You are a senior financial analyst. Generate a comprehensive MONTHLY MARKET RECAP for {current_month}.

Use your search tool to find the MAJOR EVENTS and TRENDS that defined this month across:
1. USA Markets (S&P500, Nasdaq, Dow Jones)
2. European Markets (Euro Stoxx, DAX, FTSE)
3. Asian Markets (Shanghai, Nikkei, Hang Seng)
4. Key Economic Data (inflation, employment, GDP, central bank decisions)
5. Major Corporate News (earnings, M&A, product launches)
6. Geopolitical Events (if market-relevant)

PORTFOLIO CONTEXT:
These are the tickers in the portfolio you should focus on for the PORTFOLIO IMPACT section:
{portfolio_context}

Structure your response in TWO sections with a TOPIC-BASED FORMAT:

1. 🌍 MONTHLY MARKET OVERVIEW
Organize this section into MAX 3 MAJOR TOPICS/THEMES that defined {current_month}.
For each topic:
- Use 3 relevant emojis at the start (e.g., 🏛️💵🔔 for Fed decisions, 📊📈💹 for market trends, etc.)
- Write the topic title
- Write a 2-3 sentence summary with specific data points
- IMPORTANT: Do NOT use any $ tags in this section

Example format:
🏛️💵🔔 Fed Rate Decision
The Federal Reserve cut rates by 25bps to 4.25-4.50%, signaling a more dovish stance...

2. 💼 PORTFOLIO IMPACT & OUTLOOK
Organize this section into MAX 5 TOPICS showing how the month's events impacted PORTFOLIO STOCKS listed above.
IMPORTANT: Focus EXCLUSIVELY on the tickers from the portfolio context provided above.
For each topic, if you have available tags from this list: {selected_tags_str}:
- Use 3 relevant emojis + $TAG (e.g., 🤖💡🚀 $NVDA)
- Write a 2-3 sentence summary about impact and outlook
- If no tags available, just use emojis without tags
{tag_instruction}

Example format (when tag is available):
🤖💡🚀 $NVDA
NVIDIA's new AI chip announcement drove 15% gains this month. Looking ahead to strong Q1 earnings...

STRICT LIMITS:
- MAXIMUM 3 topics for MARKET OVERVIEW, 5 for PORTFOLIO IMPACT (total 8 topics max)
- MAXIMUM {MAX_TAGS_PER_POST} $ tags TOTAL across both sections
- Use $ prefix ONLY for the allowed tags listed above
- Focus on HIGH-IMPACT events that shaped the month
- Total character count must stay under 2200 for this AI section
- FOCUS ON PORTFOLIO TICKERS in the Portfolio Impact section

Output format:
🌍 MONTHLY MARKET OVERVIEW

[emoji emoji emoji] Topic Title
Brief summary with data points...

[emoji emoji emoji] Topic Title
Brief summary with data points...

💼 PORTFOLIO IMPACT & OUTLOOK

[emoji emoji emoji] $TAG (if available)
Impact and outlook summary...

[emoji emoji emoji] Topic Title
Impact and outlook summary...
"""
        
        print(f"🤖 Generating monthly AI recap for {current_month}...")
        print(f"   Selected tags: {selected_tags_str}")
        
        # Configure with search tool
        config = None
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7
            )
        except Exception as config_err:
            print(f"⚠️ Search tool unavailable: {config_err}")
            config = types.GenerateContentConfig(temperature=0.7)
        
        # Try models
        for model_name in models_to_try:
            try:
                print(f"   Trying model: {model_name}...")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                
                if response and response.text:
                    print(f"✅ Monthly recap generated using {model_name}!")
                    recap_text = response.text.strip()
                    
                    # Log successful API usage
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "monthly_recap")
                    
                    # Post-process: remove intro text and tags from overview section
                    recap_text = _remove_intro_text(recap_text)
                    recap_text = _remove_market_section_tags(recap_text)
                    
                    # Limit tags
                    recap_text = _limit_tags_in_text(recap_text, selected_tags, MAX_TAGS_PER_POST)
                    
                    return "\n" + recap_text + "\n"
                else:
                    print(f"⚠️  Empty response from {model_name}")
                    continue
                    
            except Exception as model_error:
                error_msg = str(model_error).lower()
                print(f"⚠️  Model {model_name} failed: {model_error}")
                if API_TRACKER_AVAILABLE:
                    log_api_request(model_name, False, "monthly_recap")
                
                # 503 UNAVAILABLE is transient — retry once after a short delay
                if '503' in error_msg or 'unavailable' in error_msg:
                    print(f"   503 transient error on {model_name}, waiting 5s then retrying once...")
                    time.sleep(5)
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=config
                        )
                        if response and response.text:
                            print(f"✅ Monthly recap generated (after 503 retry) using {model_name}!")
                            if API_TRACKER_AVAILABLE:
                                log_api_request(model_name, True, "monthly_recap")
                            recap_text = response.text.strip()
                            recap_text = _remove_intro_text(recap_text)
                            recap_text = _remove_market_section_tags(recap_text)
                            recap_text = _limit_tags_in_text(recap_text, selected_tags, MAX_TAGS_PER_POST)
                            return "\n" + recap_text + "\n"
                    except Exception as e2:
                        print(f"   Retry also failed: {e2}")
                    continue
                
                time.sleep(2)
                
                # Try without tools if not supported (exclude 404 NOT_FOUND from this branch)
                is_tool_issue = ('not supported' in error_msg or 'invalid' in error_msg) and '404' not in error_msg
                if is_tool_issue:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt
                        )
                        if response and response.text:
                            print(f"✅ Monthly recap generated (no tools) using {model_name}!")
                            if API_TRACKER_AVAILABLE:
                                log_api_request(model_name, True, "monthly_recap")
                            recap_text = response.text.strip()
                            recap_text = _remove_intro_text(recap_text)
                            recap_text = _remove_market_section_tags(recap_text)
                            recap_text = _limit_tags_in_text(recap_text, selected_tags, MAX_TAGS_PER_POST)
                            return "\n" + recap_text + "\n"
                    except Exception as e2:
                        print(f"   Retry failed: {e2}")
                
                continue
        
        print("❌ All models failed for monthly recap")
        return ""
        
    except Exception as e:
        print(f"❌ Error generating monthly recap: {e}")
        return ""


def generate_market_news_recap(max_tags=MAX_TAGS_PER_POST, excluded_tags=None, market_session=None):
    """
    Generate AI-powered market news recap for USA, CHINA, and EU markets
    
    Args:
        max_tags: Maximum number of $ tags allowed in the AI output
        excluded_tags: List of tags already used elsewhere in the post
        market_session: Name of the current market session
        
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
    
    # Models in order of preference — each belongs to a DIFFERENT quota bucket.
    # Order: 2.0-flash first (more stable at EU open hour), 2.5-flash second
    # (frequently 503-overloaded at 07:00 UTC), 2.0-flash-lite third (smaller
    # model but genuinely independent daily quota — gemini-1.5 is deprecated
    # and returns 404 in API v1beta).
    models_to_try = [
        'gemini-2.0-flash',      # main free-tier bucket, stable
        'gemini-2.5-flash',      # newest bucket, but often 503 at EU peak hours
        'gemini-2.0-flash-lite', # lighter model, independent daily quota
    ]
    
    if not market_session:
        market_session = os.environ.get('MARKET_SESSION', 'Daily recap')
        
    EUROPEAN_TICKERS = ['ENEL.MI', 'ENI.MI', 'PRY.MI', 'RACE', 'VOW3.DE', 'NOVO-B.CO', 'AZN.L', 'GLEN.L', 'TRIG.L', 'SX7PEX.DE', 'IEUR', 'WDEF.L']
    US_TICKERS = ['AMZN', 'AVGO', 'GOOG', 'LLY', 'MSFT', 'NET', 'PLTR', 'PYPL', 'TSM', 'ABBV', 'ABT', 'ABT.US', 'CCJ', 'HUM', 'MELI', 'IB01.L']
    
    allowed_tickers = None
    session_upper = market_session.upper()
    if "EUROPEAN" in session_upper:
        allowed_tickers = EUROPEAN_TICKERS
    elif "U.S." in session_upper or "US" in session_upper:
        if "OPEN" in session_upper:
            allowed_tickers = US_TICKERS
            
    try:
        # Configure Gemini client
        client = genai.Client(api_key=api_key)
        
        # Build the full list of allowed tickers for tag validation
        # (broader than the rotation-selected subset — any valid portfolio ticker is OK)
        all_allowed_for_validation = list(PORTFOLIO_TICKERS.keys())
        
        # Select tags for this post (with rotation)
        selected_tags = []
        selected_tags_str = "None" # Fix UnboundLocalError
        tag_instruction = ""
        
        if max_tags > 0:
            portfolio_budget = max(0, max_tags - 1)
            selected_tags = _select_tags_for_rotation(portfolio_budget, excluded_tags, allowed_tickers)
            selected_tags_str = ', '.join([f'${tag}' for tag in selected_tags]) if selected_tags else "Nessuno"
            tag_instruction = f"""
- REGOLA ASSOLUTA SUI TAG: devi usare ESATTAMENTE {max_tags} tag con il simbolo $ nel testo. Non uno di meno, non uno di più.
- TAG OBBLIGATORI DEL PORTAFOGLIO ({portfolio_budget}): DEVI includere TUTTI questi tag nel testo, ognuno accompagnato da almeno una frase che lo riguardi: {selected_tags_str}. Non puoi saltarne nessuno.
- TAG TENDENZA OBBLIGATORIO (1): DEVI aggiungere esattamente 1 tag tra i più cercati/discussi del momento, scegliendo tra $NSDQ100 o $SPX500 (preferiti perché attirano copiatori), oppure un titolo di enorme interesse del giorno (es. $TSLA, $NVDA, $AAPL, $BTC). Questo tag DEVE essere spiegato nel testo.
- TOTALE: {portfolio_budget} tag portafoglio + 1 tag tendenza = {max_tags} tag totali. Conta i $ nel testo prima di concludere e verifica che siano esattamente {max_tags}.
"""
        else:
            tag_instruction = """
- IMPORTANTE: Non usare alcun tag con il simbolo $ in questa sezione.
- Scrivi tutti i simboli azionari come testo normale (es. NVDA, MSFT) senza il prefisso $.
"""
        
        # Get all portfolio tickers for context (exclude Russian stocks)
        excluded_tickers = {'MNODL.L', 'NVTKL.L'}
        portfolio_symbols = [t for t in PORTFOLIO_TICKERS.keys() if t not in excluded_tickers]
        portfolio_context = ", ".join(portfolio_symbols)
        # Add crypto classification note so AI doesn't confuse TRX with a stock
        portfolio_context += "\nNOTA: TRX è la criptovaluta TRON (non un'azione). Trattalo come crypto nei commenti."
        
        # Load previous history to avoid repetition
        history = load_recap_history() if GIST_STORAGE_AVAILABLE else []
        previous_topics_str = ""
        if history:
            previous_topics_str = "\nCRITICAL: DO NOT REPEAT the following news which were already reported recently:\n"
            for entry in history:
                previous_topics_str += f"- {entry['content'][:300]}...\n"
        
        # Create prompt based on session
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        if "EUROPEAN" in session_upper and "OPEN" in session_upper:
            prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro. Scrivi un post di buongiorno caldo, professionale e naturale per i tuoi copiatori ed follower prima dell'apertura dei mercati europei.
            
            Usa il tuo strumento di ricerca Google per cercare le notizie finanziarie e gli eventi di mercato più rilevanti delle ultime 12-24 ore relativi ai mercati europei o ai titoli europei nel nostro portafoglio.
            
            CONTESTO PORTAFOGLIO EUROPEO:
            I principali titoli europei del nostro portafoglio su cui concentrarsi sono:
            AstraZeneca (AZN.L), Novo Nordisk (NOVO-B.CO), Enel (ENEL.MI), Eni (ENI.MI), Prysmian (PRY.MI), Ferrari (RACE), Volkswagen (VOW3.DE), Glencore (GLEN.L).
            
            LINEE GUIDA PER IL TESTO:
            - Scrivi in ITALIANO con uno stile estremamente naturale, fluido e colloquiale (come un messaggio personale a degli amici/investitori che si fidano di te). Evita toni eccessivamente formali o robotici.
            - Inizia con un saluto caloroso e naturale (es. "Buongiorno! Iniziamo una nuova giornata sui mercati europei...")
            - Presenta MAX 3 brevi spunti o notizie principali per l'apertura europea, focalizzandoti sulle novità dei nostri titoli in portafoglio o sull'indice Euro Stoxx.
            - {tag_instruction}
            - Usa le emoji in modo spontaneo e naturale (non metterne troppe, massimo 3 o 4 in tutto il post).
            - Mantieni la lunghezza totale di questa sezione generata sotto i 1800 caratteri.
            
            Output format (ONLY return the plain text of the post in Italian):
            [Il tuo messaggio naturale in italiano]
            """
            
        elif "U.S." in session_upper and "OPEN" in session_upper:
            prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro. Scrivi un post di buongiorno/buon pomeriggio caldo, professionale e naturale per i tuoi copiatori ed follower prima dell'apertura di Wall Street (U.S. market open).
            
            Usa il tuo strumento di ricerca Google per cercare le notizie finanziarie e gli eventi di mercato più rilevanti delle ultime 12-24 ore relativi ai mercati americani o ai titoli USA nel nostro portafoglio.
            
            CONTESTO PORTAFOGLIO USA:
            I principali titoli USA del nostro portafoglio su cui concentrarsi sono:
            NVIDIA (NVDA), Microsoft (MSFT), Amazon (AMZN), Eli Lilly (LLY), Palantir (PLTR), Broadcom (AVGO), Cloudflare (NET), PayPal (PYPL), Taiwan Semiconductor (TSM), AbbVie (ABBV), Abbott (ABT).
            
            LINEE GUIDA PER IL TESTO:
            - Scrivi in ITALIANO con uno stile estremamente naturale, fluido e colloquiale (come un messaggio personale a degli amici/investitori che si fidano di te). Evita toni eccessivamente formali o robotici.
            - Inizia con un saluto caloroso e naturale (es. "Buongiorno! Ci prepariamo all'apertura di Wall Street...")
            - Presenta MAX 3 brevi spunti o notizie principali per l'apertura USA, focalizzandoti sulle novità dei nostri titoli in portafoglio o sugli indici americani (S&P 500, Nasdaq).
            - {tag_instruction}
            - Usa le emoji in modo spontaneo e naturale (non metterne troppe, massimo 3 o 4 in tutto il post).
            - Mantieni la lunghezza totale di questa sezione generata sotto i 1800 caratteri.
            
            Output format (ONLY return the plain text of the post in Italian):
            [Il tuo messaggio naturale in italiano]
            """
            
        elif "WEEKLY" in session_upper and "SAT" in session_upper:
            prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro. Scrivi un post di fine settimana caldo, onesto e naturale per i tuoi copiatori ed follower (Weekly Recap - Sabato).
            
            Usa il tuo strumento di ricerca Google per analizzare l'andamento della settimana appena trascorsa sui mercati globali e l'impatto sul nostro portafoglio.
            
            CONTESTO PORTAFOGLIO:
            {portfolio_context}
            
            LINEE GUIDA PER IL TESTO:
            - Scrivi in ITALIANO con uno stile estremamente naturale, fluido ed empatico. Parla apertamente di come è andata la settimana, se è stata verde o rossa, dei risultati ottenuti e delle tue sensazioni.
            - Inizia con un saluto amichevole per il fine settimana (es. "Buon fine settimana! Con i mercati chiusi, facciamo il punto su questa settimana...")
            - Fai un bilancio sincero di cosa ha guidato il portafoglio in questa settimana, menzionando i movimenti principali dei nostri titoli chiave.
            - Spiega brevemente cosa terremo d'occhio per la prossima settimana.
            - {tag_instruction}
            - Usa le emoji in modo spontaneo e naturale (massimo 3 o 4 in tutto il post).
            - Mantieni la lunghezza totale di questa sezione generata sotto i 1800 caratteri.
            
            Output format (ONLY return the plain text of the post in Italian):
            [Il tuo messaggio naturale in italiano]
            """
            
        elif "WEEKLY" in session_upper and "SUN" in session_upper:
            prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro. Scrivi un commento domenicale naturale e professionale per i tuoi copiatori sui migliori titoli della settimana (Weekly Recap - Domenica).
            
            Usa il tuo strumento di ricerca Google per analizzare i motivi del forte rialzo dei migliori titoli del nostro portafoglio durante la settimana appena trascorsa.
            
            CONTESTO PORTAFOGLIO:
            {portfolio_context}
            
            LINEE GUIDA PER IL TESTO:
            - Scrivi in ITALIANO con uno stile naturale e chiaro. Questo post accompagnerà la classifica dei migliori titoli del portafoglio.
            - Inizia in modo naturale (es. "Buona domenica! Oggi diamo un'occhiata più da vicino ai titoli che hanno guidato la classifica delle performance settimanali...")
            - Spiega in modo semplice e chiaro i motivi del successo dei titoli migliori di questa settimana (massimo 2-3 titoli).
            - Collega queste performance alla nostra tesi d'investimento di lungo termine, rassicurando i copiatori sulla bontà delle nostre scelte.
            - {tag_instruction}
            - Usa le emoji in modo spontaneo e naturale (massimo 3 o 4 in tutto il post).
            - Mantieni la lunghezza totale di questa sezione generata sotto i 1800 caratteri.
            
            Output format (ONLY return the plain text of the post in Italian):
            [Il tuo messaggio naturale in italiano]
            """
            
        else:
            prompt = f"""Sei Andrea Ravalli, un investitore privato italiano su eToro. Scrivi un resoconto serale caldo, professionale e naturale per i tuoi copiatori dopo la chiusura dei mercati USA (U.S. market close / fine giornata).
            
            Usa il tuo strumento di ricerca Google per cercare le notizie finanziarie e le performance più rilevanti delle ultime 24 ore sui mercati globali e per i titoli del nostro portafoglio.
            
            {previous_topics_str}
            
            CONTESTO PORTAFOGLIO:
            {portfolio_context}
            
            LINEE GUIDA PER IL TESTO:
            - Scrivi in ITALIANO con uno stile estremamente naturale, fluido e colloquiale (come un resoconto sincero scritto a fine giornata per i tuoi amici e investitori).
            - Inizia in modo amichevole (es. "Buonasera! Ecco il nostro recap di fine giornata per vedere cosa è successo oggi sui mercati...")
            - Presenta un breve quadro della giornata di borsa (S&P 500, Nasdaq, mercati europei) e spiega l'impatto diretto sui titoli del nostro portafoglio.
            - {tag_instruction}
            - Usa le emoji in modo spontaneo e naturale (massimo 3 o 4 in tutto il post).
            - Mantieni la lunghezza totale di questa sezione generata sotto i 1800 caratteri.
            
            Output format (ONLY return the plain text of the post in Italian):
            [Il tuo messaggio naturale in italiano]
            """
        
        print("🤖 Generating AI market news recap...")
        print(f"   Selected tags for this post: {selected_tags_str}")
        
        # Configure search tool if available in the SDK
        config = None
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7
            )
        except Exception as config_err:
            print(f"⚠️ Could not initialize Google Search tool: {config_err}")
            config = types.GenerateContentConfig(temperature=0.7)

        # Try each model until one works
        last_error = None
        for model_name in models_to_try:
            try:
                print(f"   Trying model: {model_name}...")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                
                if response and response.text:
                    print(f"✅ AI news recap generated successfully using {model_name}!")
                    recap_text = response.text.strip()
                    
                    # Log successful API usage
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "daily_recap")
                    
                    # Post-process: remove intro text and any $ tags from market section
                    recap_text = _remove_intro_text(recap_text)
                    recap_text = _remove_market_section_tags(recap_text)
                    
                    # Post-process: ensure only valid portfolio tags are used and limit count
                    recap_text = _limit_tags_in_text(recap_text, all_allowed_for_validation, max_tags)
                    
                    # Update rotation history with the tags actually selected for the post
                    if selected_tags:
                        update_rotation_history(selected_tags)
                    
                    # Save to history (using Gist storage)
                    if GIST_STORAGE_AVAILABLE:
                        save_to_history(recap_text)
                    
                    return "\n" + recap_text + "\n"
                else:
                    print(f"⚠️  Empty response from {model_name}, trying next model...")
                    continue
                    
            except Exception as model_error:
                error_msg = str(model_error).lower()
                print(f"⚠️  Model {model_name} failed: {model_error}")
                if API_TRACKER_AVAILABLE:
                    log_api_request(model_name, False, "daily_recap")
                
                # 503 UNAVAILABLE is a transient server-side error — retry once after a short delay
                # before moving to the next model (different from 429 quota which is hard limit)
                if '503' in error_msg or 'unavailable' in error_msg:
                    print(f"   503 transient error on {model_name}, waiting 5s then retrying once...")
                    time.sleep(5)
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=config
                        )
                        if response and response.text:
                            print(f"✅ AI news recap generated (after 503 retry) using {model_name}!")
                            if API_TRACKER_AVAILABLE:
                                log_api_request(model_name, True, "daily_recap")
                            recap_text = response.text.strip()
                            recap_text = _remove_intro_text(recap_text)
                            recap_text = _remove_market_section_tags(recap_text)
                            recap_text = _limit_tags_in_text(recap_text, all_allowed_for_validation, max_tags)
                            if selected_tags:
                                update_rotation_history(selected_tags)
                            if GIST_STORAGE_AVAILABLE:
                                save_to_history(recap_text)
                            return "\n" + recap_text + "\n"
                    except Exception as e2:
                        print(f"   Retry also failed: {e2}")
                    last_error = model_error
                    continue
                
                time.sleep(2)
                
                # 404 NOT_FOUND may include "not supported" in the message — check for actual
                # tool-compatibility issues (not just model not found) by excluding 404 errors
                is_tool_issue = ('not supported' in error_msg or 'invalid' in error_msg) and '404' not in error_msg
                if is_tool_issue:
                    print(f"   Model {model_name} might not support search tools, trying without...")
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt
                        )
                        if response and response.text:
                            print(f"✅ AI news recap generated successfully (without tools) using {model_name}!")
                            if API_TRACKER_AVAILABLE:
                                log_api_request(model_name, True, "daily_recap")
                            recap_text = response.text.strip()
                            
                            # Post-process
                            recap_text = _remove_intro_text(recap_text)
                            recap_text = _remove_market_section_tags(recap_text)
                            recap_text = _limit_tags_in_text(recap_text, all_allowed_for_validation, max_tags)
                            
                            # Update rotation history with the tags actually selected for the post
                            if selected_tags:
                                update_rotation_history(selected_tags)
                                
                            if GIST_STORAGE_AVAILABLE:
                                save_to_history(recap_text)
                            return "\n" + recap_text + "\n"
                    except Exception as e2:
                        print(f"   Retry failed: {e2}")
                
                if 'quota' in error_msg or 'resource_exhausted' in error_msg or '429' in error_msg:
                    print(f"   Quota exceeded for {model_name}, trying next model...")
                    last_error = model_error
                    continue
                else:
                    last_error = model_error
                    continue
        
        # All models failed
        print(f"❌ All models failed. Last error: {last_error}")
        print("💡 Tip: Wait a few minutes for quota reset, or check your API key at https://makersuite.google.com/")
        return ""
            
    except Exception as e:
        print(f"❌ Error generating AI news recap: {e}")
        print(f"Error type: {type(e).__name__}")
        return ""



def get_why_copy_message(five_year_return=161, avg_yearly_return=32, benchmark_performance=None):
    """
    Returns the fixed message explaining why to copy this portfolio
    
    Args:
        five_year_return: Total return since strategy change (default 161%)
        avg_yearly_return: Average yearly return (default 32%)
        benchmark_performance: Dict of {etoro_ticker: performance_value}
    
    Returns:
        str: Formatted fixed message with performance data
    """
    # Calculate years to double using Rule of 72
    time_to_double = 72 / avg_yearly_return if avg_yearly_return > 0 else 0
    
    benchmark_lines = ""
    if benchmark_performance:
        for ticker, perf in benchmark_performance.items():
            # Calculate the difference (delta) between our return and benchmark
            delta = five_year_return - perf
            perf_label = "(sovraperformance)" if delta >= 0 else "(sottoperformance)"
            benchmark_lines += f"✓ VS {ticker} : {delta:+.0f}% {perf_label}\n"
    else:
        # Fallback if no data
        benchmark_lines = "✓ Sovraperformance vs S&P500\n✓ Sovraperformance vs MSCI World\n✓ Sovraperformance vs Euro Stoxx 50"

    message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 PERCHÈ COPIARE QUESTO PORTAFOGLIO?

📈 STORICO DELLE PERFORMANCE:
+{five_year_return:.0f}% dal cambio di strategia (2020)
~{avg_yearly_return:.0f}% rendimento medio annuo
Raddoppio del capitale stimato in ~{time_to_double:.1f} anni

✅ PUNTI DI FORZA DELLA STRATEGIA:
• Diversificazione intelligente su 3 continenti
• Focus sui megatrend del futuro: AI, Sanità ed Energia
• Mix bilanciato di ETF e azioni individuali ad alto potenziale
• Gestione attiva, trasparente e senza commissioni nascoste

📊 DIFFERENZIALE RISPETTO AI BENCHMARK (Dal 2020):
{benchmark_lines.strip()}

🎯 Strategia di lungo termine basata su fondamentali solidi
🔄 Ribilanciamento periodico per ottimizzare il rapporto rischio/rendimento

🔗 Info & Link per copiarmi: https://bio.mega89.uk/
@AndreaRavalli
━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return message


def generate_decision_post(
    recent_closes_text: str,
    current_weights: dict = None,
    history_stats_text: str = '',
) -> str:
    """
    Generate a "decision of the week" post explaining recent trading choices.
    Uses Gemini to write an empathetic, transparent narrative for copiers.

    Args:
        recent_closes_text: Text summary of recently closed positions (from etoro_history)
        current_weights: Current portfolio weights {ticker: %} from BullAware
        history_stats_text: Short stats summary from etoro_history

    Returns:
        str: Formatted post text, or empty string on failure
    """
    if not GENAI_AVAILABLE:
        return ""

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return ""

    models_to_try = ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-2.0-flash-lite']

    weights_context = ""
    if current_weights:
        top_holdings = sorted(current_weights.items(), key=lambda x: x[1], reverse=True)[:8]
        weights_context = "Current top holdings: " + ", ".join(
            f"{t} ({w:.1f}%)" for t, w in top_holdings
        )

    prompt = f"""You are Andrea Ravalli, an Italian private investor sharing your eToro portfolio journey with your copiers.
You are transparent, humble, and data-driven. You write in a warm, personal tone — like you're talking to friends who trust you with their money.

TODAY'S TASK: Write a "Decision of the Week" post explaining your recent trading decisions.

RECENT CLOSED POSITIONS (last 30 days):
{recent_closes_text if recent_closes_text else 'No recent closes.'}

{weights_context}

PORTFOLIO HISTORY CONTEXT:
{history_stats_text if history_stats_text else ''}

Write a post (max 1400 characters) in ITALIAN that:
1. Opens with a personal, relatable hook (1-2 sentences about the market mood this week)
2. Explains 1-2 specific decisions you made (why you exited or held, what you were thinking)
3. Connects emotionally with copiers ("so che vederlo in rosso fa male, ma...")
4. Ends with your forward-looking thesis (what you're watching next)

TONE: Transparent, confident but humble, empathetic. Never overconfident.
AVOID: Generic phrases, vague claims, percentage promises.
FORMAT: Plain text, no HTML. Use emojis naturally (2-3 max). No bullet lists.

Output ONLY the post text, no introduction or explanation."""

    try:
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(temperature=0.85)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                if response and response.text:
                    print(f"✅ Decision post generated with {model_name}")
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "decision_post")
                    return response.text.strip()
            except Exception as exc:
                print(f"⚠️ Decision post model {model_name} failed: {exc}")
                time.sleep(1)

        print("❌ All models failed for decision post")
        return ""

    except Exception as exc:
        print(f"❌ Error generating decision post: {exc}")
        return ""


def generate_empathy_post(
    portfolio_perf: float,
    weekly_perf: float = None,
    market_context: str = '',
    history_stats_text: str = '',
) -> str:
    """
    Generate an empathetic post for copiers during tough market periods or to celebrate gains.
    Connects emotionally, explains the long-term view, and reinforces trust.

    Args:
        portfolio_perf: Current cumulative portfolio performance % (e.g. 156.0)
        weekly_perf: Weekly performance % (negative = drawdown week)
        market_context: Brief market summary for context
        history_stats_text: Short stats from etoro history

    Returns:
        str: Formatted post text, or empty string on failure
    """
    if not GENAI_AVAILABLE:
        return ""

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return ""

    models_to_try = ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-2.0-flash-lite']

    # Determine emotional context
    if weekly_perf is not None and weekly_perf < -2:
        mood = f"difficult week (portfolio: {weekly_perf:+.1f}% this week)"
        angle = "reassure copiers, explain the bigger picture, normalize short-term pain"
    elif weekly_perf is not None and weekly_perf > 3:
        mood = f"strong week (portfolio: {weekly_perf:+.1f}% this week)"
        angle = "celebrate the gain, remind that discipline drove it, stay humble and grounded"
    else:
        mood = "typical market week"
        angle = "check in with copiers, reinforce the strategy thesis, share your mindset"

    prompt = f"""You are Andrea Ravalli, an Italian private investor on eToro sharing your journey with your copiers.
You have been investing since 2020 and your portfolio is up ~{portfolio_perf:.0f}% cumulative.
You are transparent, humble, and human. You write like you're talking to friends.

TODAY'S TASK: Write a warm, empathetic weekly check-in post.

CURRENT CONTEXT:
- Portfolio cumulative return: +{portfolio_perf:.0f}%
- This week's mood: {mood}
- Your angle: {angle}
- Market context: {market_context if market_context else 'Mixed global markets'}
- Portfolio history note: {history_stats_text[:200] if history_stats_text else ''}

Write a post (max 1200 characters) in ITALIAN that:
1. Opens with a human, relatable moment (something you felt or observed this week)
2. Addresses how the week felt for copiers and validates their emotions
3. Zooms out to the bigger picture (the long-term strategy, the "why")
4. Closes with one concrete thing you are watching next week

TONE: Warm, honest, personal. Like a weekly letter to people who trust you.
AVOID: Generic motivational quotes, exaggerated claims, financial advice promises.
FORMAT: Plain text. 2-4 natural emojis. No bullet lists. Conversational paragraphs.

Output ONLY the post text, no introduction or explanation."""

    try:
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(temperature=0.90)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                if response and response.text:
                    print(f"✅ Empathy post generated with {model_name}")
                    if API_TRACKER_AVAILABLE:
                        log_api_request(model_name, True, "empathy_post")
                    return response.text.strip()
            except Exception as exc:
                print(f"⚠️ Empathy post model {model_name} failed: {exc}")
                time.sleep(1)

        print("❌ All models failed for empathy post")
        return ""

    except Exception as exc:
        print(f"❌ Error generating empathy post: {exc}")
        return ""
