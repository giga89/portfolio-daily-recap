#!/usr/bin/env python3
"""
Track Gemini API usage and generate a usage report.

Data is persisted in the Gist store (key: 'gemini_api_usage') so it survives
across ephemeral GitHub Actions runs.  A local copy is also written to
output/gemini_api_usage.json for the artifact upload.
"""

import json
from datetime import datetime
from pathlib import Path

# File to store API usage data (local, per-run copy for artifact upload)
USAGE_FILE = Path("output/gemini_api_usage.json")

# Gist key used to persist usage across runs
GIST_KEY = "gemini_api_usage"

# Lazy-import gist_storage so this module works even without it
try:
    import gist_storage as _gist
    GIST_AVAILABLE = True
except ImportError:
    GIST_AVAILABLE = False


def load_usage_data() -> dict:
    """Load usage data — prefer Gist for cross-run persistence."""
    # Try Gist first
    if GIST_AVAILABLE:
        try:
            gist_data = _gist.load_data()
            stored = gist_data.get(GIST_KEY)
            if stored and isinstance(stored, dict) and "requests" in stored:
                return stored
        except Exception:
            pass
    # Fallback: local file (current run only)
    if USAGE_FILE.exists():
        try:
            with open(USAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"requests": [], "summary": {}}


def save_usage_data(data: dict) -> None:
    """Persist usage data to both Gist and the local artifact file."""
    # Local file (for artifact upload)
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Gist (persists across runs)
    if GIST_AVAILABLE:
        try:
            gist_data = _gist.load_data()
            gist_data[GIST_KEY] = data
            _gist.save_data(gist_data)
        except Exception as exc:
            print(f"Warning: could not persist API usage to Gist: {exc}")

def log_api_request(model_name: str, success: bool, request_type: str = "recap") -> None:
    """
    Log an API request (both successful and failed ones).

    Args:
        model_name:   Name of the Gemini model attempted.
        success:      True if the request succeeded, False otherwise.
        request_type: Type of request (recap, monthly_recap, cover, etc.)
    """
    data = load_usage_data()
    
    request_info = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "success": success,
        "type": request_type
    }
    
    data["requests"].append(request_info)
    
    # Update summary
    today = datetime.now().strftime("%Y-%m-%d")
    this_month = datetime.now().strftime("%Y-%m")
    
    if "daily" not in data["summary"]:
        data["summary"]["daily"] = {}
    if "monthly" not in data["summary"]:
        data["summary"]["monthly"] = {}
    
    # Daily count
    if today not in data["summary"]["daily"]:
        data["summary"]["daily"][today] = {"total": 0, "successful": 0, "failed": 0, "by_model": {}}
    elif "by_model" not in data["summary"]["daily"][today]:
        data["summary"]["daily"][today]["by_model"] = {}
    
    data["summary"]["daily"][today]["total"] += 1
    if success:
        data["summary"]["daily"][today]["successful"] += 1
    else:
        data["summary"]["daily"][today]["failed"] += 1
    
    # Model specific daily count
    if model_name not in data["summary"]["daily"][today]["by_model"]:
        data["summary"]["daily"][today]["by_model"][model_name] = {"total": 0, "successful": 0, "failed": 0}
    data["summary"]["daily"][today]["by_model"][model_name]["total"] += 1
    if success:
        data["summary"]["daily"][today]["by_model"][model_name]["successful"] += 1
    else:
        data["summary"]["daily"][today]["by_model"][model_name]["failed"] += 1
    
    # Monthly count
    if this_month not in data["summary"]["monthly"]:
        data["summary"]["monthly"][this_month] = {"total": 0, "successful": 0, "failed": 0}
    
    data["summary"]["monthly"][this_month]["total"] += 1
    if success:
        data["summary"]["monthly"][this_month]["successful"] += 1
    else:
        data["summary"]["monthly"][this_month]["failed"] += 1
    
    save_usage_data(data)
    print(f"📊 API usage logged: {model_name} ({'✅' if success else '❌'})")

def generate_usage_report():
    """Generate a human-readable usage report"""
    data = load_usage_data()
    
    if not data["requests"]:
        return "No API usage data available yet."
    
    today = datetime.now().strftime("%Y-%m-%d")
    this_month = datetime.now().strftime("%Y-%m")
    
    # Get today's stats
    daily_stats = data["summary"].get("daily", {}).get(today, {"total": 0, "successful": 0, "failed": 0, "by_model": {}})
    monthly_stats = data["summary"].get("monthly", {}).get(this_month, {"total": 0, "successful": 0, "failed": 0})
    
    # Free tier limit per model is 20 RPD
    FREE_TIER_MODEL_RPD = 20
    
    # Get recent requests
    recent_requests = data["requests"][-10:]  # Last 10 requests
    
    # Model breakdown lines
    if daily_stats.get("by_model"):
        by_model_lines = ""
        for m_name, m_stats in daily_stats.get("by_model", {}).items():
            m_tot = m_stats.get("total", 0)
            status_flag = "⚠️ QUOTA EXCEEDED" if m_tot >= FREE_TIER_MODEL_RPD else "✅ OK"
            by_model_lines += f"│  • {m_name:<22}: {m_tot:>2}/{FREE_TIER_MODEL_RPD} RPD ({status_flag})  │\n"
    else:
        by_model_lines = "│  (No model breakdown yet)                                    │\n"

    report = f"""
╔══════════════════════════════════════════════════════════════╗
║          📊 GEMINI API USAGE REPORT                          ║
╚══════════════════════════════════════════════════════════════╝

📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

┌──────────────────────────────────────────────────────────────┐
│ TODAY'S USAGE ({today})                                  
├──────────────────────────────────────────────────────────────┤
│ Total Requests:     {daily_stats['total']:>4}                               
│ Successful:         {daily_stats['successful']:>4} ✅                           
│ Failed:             {daily_stats['failed']:>4} ❌                           
│                                                              
│ Usage by Model (Free Tier limit: 20 RPD / model):            
{by_model_lines}└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ THIS MONTH'S USAGE ({this_month})                       
├──────────────────────────────────────────────────────────────┤
│ Total Requests:     {monthly_stats['total']:>4}                               
│ Successful:         {monthly_stats['successful']:>4} ✅                           
│ Failed:             {monthly_stats['failed']:>4} ❌                           
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ RECENT REQUESTS (Last 10)                                   
├──────────────────────────────────────────────────────────────┤
"""
    
    for req in recent_requests:
        timestamp = datetime.fromisoformat(req['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        status = "✅" if req['success'] else "❌"
        model = req['model'][:20]  # Truncate long model names
        req_type = req.get('type', 'unknown')[:15]
        report += f"│ {timestamp} {status} {model:<20} {req_type:<15}│\n"
    
    report += """└──────────────────────────────────────────────────────────────┘

📝 NOTES:
• Free Tier limits: 10 RPM / 20 RPD for gemini-2.5-flash-lite, 5 RPM / 20 RPD for 3.5/2.5/3.6/3.7 flash
• Each model has its OWN separate 20 RPD quota bucket
• For exact real-time quotas, check: https://aistudio.google.com/

💡 RECOMMENDATIONS:
  1. Distribute tasks across models (gemini-2.5-flash-lite, 3.5-flash, 2.5-flash)
  2. Set up billing on AI Studio ($0.05 - $0.20/month) to unblock all daily limits
"""
    
    return report

def save_usage_report():
    """Generate and save the usage report to a file"""
    report = generate_usage_report()
    
    report_file = Path("output/gemini_api_usage_report.txt")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"📊 Usage report saved to: {report_file}")
    return report

if __name__ == "__main__":
    # Generate and print report when run directly
    report = save_usage_report()
    print(report)
