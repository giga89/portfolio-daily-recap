#!/usr/bin/env python3
"""
Track Gemini API usage and generate a usage report
"""

import json
from datetime import datetime
from pathlib import Path

# File to store API usage data
USAGE_FILE = Path("output/gemini_api_usage.json")

def load_usage_data():
    """Load existing usage data"""
    if USAGE_FILE.exists():
        try:
            with open(USAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"requests": [], "summary": {}}
    return {"requests": [], "summary": {}}

def save_usage_data(data):
    """Save usage data to file"""
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def log_api_request(model_name, success, request_type="recap"):
    """
    Log an API request
    
    Args:
        model_name: Name of the Gemini model used
        success: Whether the request was successful
        request_type: Type of request (recap, monthly_recap, etc.)
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
        data["summary"]["daily"][today] = {"total": 0, "successful": 0, "failed": 0}
    
    data["summary"]["daily"][today]["total"] += 1
    if success:
        data["summary"]["daily"][today]["successful"] += 1
    else:
        data["summary"]["daily"][today]["failed"] += 1
    
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
    daily_stats = data["summary"].get("daily", {}).get(today, {"total": 0, "successful": 0, "failed": 0})
    monthly_stats = data["summary"].get("monthly", {}).get(this_month, {"total": 0, "successful": 0, "failed": 0})
    
    # Calculate percentages (based on typical free tier limits)
    FREE_TIER_DAILY_LIMIT = 1500  # Requests per day
    FREE_TIER_HOURLY_LIMIT = 15   # Requests per minute * 60 (approximate)
    
    daily_usage_pct = (daily_stats["total"] / FREE_TIER_DAILY_LIMIT) * 100
    monthly_usage_pct = (monthly_stats["total"] / (FREE_TIER_DAILY_LIMIT * 30)) * 100  # Approximate monthly
    
    # Get recent requests
    recent_requests = data["requests"][-10:]  # Last 10 requests
    
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
│ Daily Limit:        {FREE_TIER_DAILY_LIMIT:>4} (Free Tier)                 
│ Usage:              {daily_usage_pct:>5.2f}% of daily limit               
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ THIS MONTH'S USAGE ({this_month})                       
├──────────────────────────────────────────────────────────────┤
│ Total Requests:     {monthly_stats['total']:>4}                               
│ Successful:         {monthly_stats['successful']:>4} ✅                           
│ Failed:             {monthly_stats['failed']:>4} ❌                           
│                                                              
│ Est. Monthly Limit: {FREE_TIER_DAILY_LIMIT * 30:>4} (1500/day * 30)         
│ Usage:              {monthly_usage_pct:>5.2f}% of est. monthly limit       
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
• Free Tier limits: 15 RPM, 1500 RPD for most models
• Usage percentages are estimates based on typical limits
• For exact quotas, check: https://aistudio.google.com/
• Monthly limit is estimated as 1500 requests/day * 30 days

💡 TIPS TO OPTIMIZE USAGE:
  1. Use gemini-2.0-flash-lite instead of flash (same limits but faster)
  2. Add delays between requests if hitting rate limits
  3. Reduce max_output_tokens to save on token usage
  4. Use caching for repeated content

🔗 CHECK DETAILED QUOTA:
  • Google AI Studio: https://aistudio.google.com/app/apikey
  • Cloud Console: https://console.cloud.google.com/apis/dashboard

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
