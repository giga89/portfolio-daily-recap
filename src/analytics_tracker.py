#!/usr/bin/env python3
"""
Social & Post Analytics Tracker
===============================
Tracks published posts across all platforms, syncs engagement metrics (likes, comments, shares),
and generates an interactive HTML dashboard for GitHub Pages.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import etoro_client
import gist_storage

ANALYTICS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "post_analytics.json"
)
DOCS_INDEX_HTML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "index.html"
)


def load_local_analytics() -> Dict[str, Any]:
    """Load analytics database from local disk or initialize default structure."""
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading local analytics file: {e}")

    # Fallback / Default structure
    return {
        "last_updated": datetime.utcnow().isoformat(),
        "posts": [
            {
                "id": "41f4c7dc-402a-4ce6-a7fe-49b819f074d2",
                "platform": "etoro",
                "session": "U.S. market close",
                "published_at": "2026-08-11T08:22:38Z",
                "day_of_week": "Tuesday",
                "hour_utc": 8,
                "hour_local": 10,
                "title": "Recap Portafoglio & Top/Flop",
                "tickers": ["PLTR", "NVDA", "CCJ", "SX7PEX.DE"],
                "image_type": "winners_losers_card",
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "url": "https://www.etoro.com/people/AndreaRavalli",
            }
        ]
    }


def save_local_analytics(data: Dict[str, Any]):
    """Save analytics database to local disk."""
    os.makedirs(os.path.dirname(ANALYTICS_FILE), exist_ok=True)
    data["last_updated"] = datetime.utcnow().isoformat()
    with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_post(
    platform: str,
    post_id: str,
    session_name: str,
    text: str,
    image_type: str = "winners_losers_card",
    tickers: Optional[List[str]] = None,
    url: Optional[str] = None,
):
    """
    Record a new published post in the analytics database.
    """
    data = load_local_analytics()
    posts = data.get("posts", [])

    # Avoid duplicate entry by ID and platform
    for p in posts:
        if p.get("id") == post_id and p.get("platform") == platform:
            return

    now = datetime.utcnow()
    # Extract cashtags from text if not provided
    if not tickers:
        import re
        found = re.findall(r"\$([A-Z]{2,6}(?:\.[A-Z]{2})?)", text)
        tickers = list(set(found)) if found else []

    record = {
        "id": post_id,
        "platform": platform,
        "session": session_name,
        "published_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "day_of_week": now.strftime("%A"),
        "hour_utc": now.hour,
        "hour_local": (now.hour + 2) % 24,  # Rome / CET (UTC+2 in summer)
        "title": text[:80].replace("\n", " ").strip() + "...",
        "tickers": tickers,
        "image_type": image_type,
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "url": url or f"https://www.etoro.com/people/AndreaRavalli",
    }

    posts.insert(0, record)
    data["posts"] = posts
    save_local_analytics(data)
    print(f"📊 Analytics: Recorded {platform} post {post_id} ({session_name})")


def sync_etoro_metrics() -> Dict[str, Any]:
    """
    Poll live engagement metrics from eToro API for all tracked posts.
    """
    data = load_local_analytics()
    posts = data.get("posts", [])
    updated_count = 0

    for p in posts:
        if p.get("platform") == "etoro" and p.get("id"):
            post_id = p["id"]
            metrics = etoro_client.get_post_metrics(post_id)
            if metrics:
                p["likes"] = metrics.get("likes", 0)
                p["comments"] = metrics.get("comments", 0)
                p["shares"] = metrics.get("shares", 0)
                p["last_synced"] = datetime.utcnow().isoformat()
                updated_count += 1

    # Remove any old seed/deleted posts that returned 404
    data["posts"] = [p for p in posts if p.get("id") not in ["41f4c7dc-402a-4ce6-a7fe-49b819f074d2", "fb2dfe40-9d61-11f1-8080-800019b76646"]]
    save_local_analytics(data)
    print(f"✓ Synced engagement metrics for {updated_count} eToro posts")
    return data


def compute_insights(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze posts data to extract best hours, best days, top tags, and image performance.
    """
    posts = data.get("posts", [])
    if not posts:
        return {}

    # 1. Hourly Engagement
    hourly: Dict[int, Dict[str, Any]] = {}
    # 2. Weekday Engagement
    weekdays: Dict[str, Dict[str, Any]] = {}
    # 3. Tickers / Tags
    tag_stats: Dict[str, Dict[str, Any]] = {}
    # 4. Image Types
    image_stats: Dict[str, Dict[str, Any]] = {}

    total_likes = 0
    total_comments = 0

    for p in posts:
        likes = p.get("likes", 0)
        comments = p.get("comments", 0)
        eng = likes * 1.5 + comments * 3.0  # Comments have higher weight
        total_likes += likes
        total_comments += comments

        # Hour
        h = p.get("hour_local", p.get("hour_utc", 0))
        if h not in hourly:
            hourly[h] = {"count": 0, "likes": 0, "comments": 0, "eng": 0.0}
        hourly[h]["count"] += 1
        hourly[h]["likes"] += likes
        hourly[h]["comments"] += comments
        hourly[h]["eng"] += eng

        # Day of week
        d = p.get("day_of_week", "Unknown")
        if d not in weekdays:
            weekdays[d] = {"count": 0, "likes": 0, "comments": 0, "eng": 0.0}
        weekdays[d]["count"] += 1
        weekdays[d]["likes"] += likes
        weekdays[d]["comments"] += comments
        weekdays[d]["eng"] += eng

        # Tickers
        for t in p.get("tickers", []):
            if t not in tag_stats:
                tag_stats[t] = {"count": 0, "likes": 0, "comments": 0, "eng": 0.0}
            tag_stats[t]["count"] += 1
            tag_stats[t]["likes"] += likes
            tag_stats[t]["comments"] += comments
            tag_stats[t]["eng"] += eng

        # Image type
        img_t = p.get("image_type", "winners_losers_card")
        if img_t not in image_stats:
            image_stats[img_t] = {"count": 0, "likes": 0, "comments": 0, "eng": 0.0}
        image_stats[img_t]["count"] += 1
        image_stats[img_t]["likes"] += likes
        image_stats[img_t]["comments"] += comments
        image_stats[img_t]["eng"] += eng

    # Best hour
    best_hour = max(hourly.items(), key=lambda x: (x[1]["eng"] / max(1, x[1]["count"])), default=(22, {}))[0]
    # Best day
    best_day = max(weekdays.items(), key=lambda x: (x[1]["eng"] / max(1, x[1]["count"])), default=("Tuesday", {}))[0]

    return {
        "total_posts": len(posts),
        "total_likes": total_likes,
        "total_comments": total_comments,
        "avg_likes": round(total_likes / max(1, len(posts)), 2),
        "avg_comments": round(total_comments / max(1, len(posts)), 2),
        "best_hour": f"{best_hour:02d}:00 (CET)",
        "best_day": best_day,
        "hourly": hourly,
        "weekdays": weekdays,
        "tag_stats": tag_stats,
        "image_stats": image_stats,
    }


def generate_html_dashboard(output_path: str = DOCS_INDEX_HTML) -> str:
    """
    Generate an interactive GitHub Pages dashboard for post analytics.
    """
    data = load_local_analytics()
    insights = compute_insights(data)
    posts = data.get("posts", [])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    posts_json = json.dumps(posts, ensure_ascii=False)
    insights_json = json.dumps(insights, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Portfolio Recap · Social Analytics & Success Hub</title>
  <meta name="description" content="Dashboard interattiva di analisi dei post, orari migliori e performance dei contenuti del portfolio eToro di Andrea Ravalli.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: #000021;
      --surface: #0a0a2e;
      --surface2: #121242;
      --surface3: #1a1a54;
      --green: #13C636;
      --green-glow: rgba(19, 198, 54, 0.25);
      --cyan: #00D4FF;
      --cyan-glow: rgba(0, 212, 255, 0.25);
      --purple: #8A2BE2;
      --red: #FF4D4D;
      --text: #FFFFFF;
      --muted: #9AA8C2;
      --line: rgba(255, 255, 255, 0.10);
      --radius: 18px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 30px 20px 80px;
    }}
    .container {{ max-width: 1240px; margin: 0 auto; }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 20px;
      padding-bottom: 28px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 32px;
    }}
    .brand {{ display: flex; align-items: center; gap: 14px; }}
    .brand-icon {{
      width: 48px; height: 48px; border-radius: 14px;
      background: linear-gradient(135deg, var(--green), var(--cyan));
      display: grid; place-items: center; font-size: 1.5rem; font-weight: 900; color: #00140a;
      box-shadow: 0 0 24px var(--green-glow);
    }}
    h1 {{ font-size: clamp(1.5rem, 3.5vw, 2.2rem); font-weight: 900; letter-spacing: -0.03em; }}
    .subtitle {{ color: var(--muted); font-size: 0.95rem; }}
    .badge {{
      display: inline-flex; align-items: center; gap: 8px;
      background: rgba(19, 198, 54, 0.1); border: 1px solid var(--green);
      color: var(--green); padding: 6px 14px; border-radius: 999px; font-size: 0.78rem; font-weight: 800;
      text-transform: uppercase; letter-spacing: 0.08em;
    }}
    .kpi-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px; margin-bottom: 32px;
    }}
    .kpi-card {{
      background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
      padding: 22px; position: relative; overflow: hidden;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      transition: transform 0.15s ease, border-color 0.15s ease;
    }}
    .kpi-card:hover {{ transform: translateY(-2px); border-color: var(--cyan); }}
    .kpi-card::before {{
      content: ""; position: absolute; top: -30px; right: -30px; width: 90px; height: 90px;
      border-radius: 50%; background: var(--cyan-glow); filter: blur(30px); pointer-events: none;
    }}
    .kpi-label {{ color: var(--muted); font-size: 0.82rem; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; }}
    .kpi-value {{ font-size: 2.1rem; font-weight: 900; letter-spacing: -0.03em; color: #fff; }}
    .kpi-sub {{ color: var(--green); font-size: 0.82rem; font-weight: 700; margin-top: 4px; }}

    .insights-box {{
      background: linear-gradient(145deg, var(--surface2), var(--surface));
      border: 1px solid rgba(0, 212, 255, 0.35); border-radius: var(--radius);
      padding: 24px; margin-bottom: 32px; box-shadow: 0 12px 35px var(--cyan-glow);
    }}
    .insights-title {{ font-size: 1.15rem; font-weight: 800; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; color: var(--cyan); }}
    .insights-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
    .insight-pill {{ background: rgba(0,0,33,0.6); padding: 14px 18px; border-radius: 14px; border: 1px solid var(--line); }}
    .insight-pill strong {{ color: #FFF; }}

    .charts-grid {{ display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 32px; }}
    @media(min-width: 860px) {{ .charts-grid {{ grid-template-columns: 1fr 1fr; }} }}
    .chart-panel {{
      background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
      padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }}
    .panel-title {{ font-size: 1.1rem; font-weight: 800; margin-bottom: 18px; display: flex; align-items: center; justify-content: space-between; }}

    .table-panel {{
      background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
      padding: 24px; overflow: hidden; margin-bottom: 32px;
    }}
    table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }}
    th {{ padding: 14px 16px; color: var(--muted); font-size: 0.78rem; font-weight: 800; text-transform: uppercase; border-bottom: 1px solid var(--line); }}
    td {{ padding: 16px; border-bottom: 1px solid var(--line); color: var(--text); }}
    tr:hover td {{ background: rgba(255,255,255,0.03); }}
    .ticker-tag {{
      display: inline-block; background: rgba(0, 212, 255, 0.12); color: var(--cyan);
      border: 1px solid rgba(0, 212, 255, 0.3); padding: 2px 8px; border-radius: 6px; font-weight: 700;
      font-size: 0.78rem; margin-right: 4px;
    }}
    .btn-link {{
      display: inline-flex; align-items: center; gap: 6px;
      color: var(--green); font-weight: 700; text-decoration: none; font-size: 0.85rem;
    }}
    .btn-link:hover {{ text-decoration: underline; }}
    footer {{ text-align: center; color: var(--muted); font-size: 0.82rem; margin-top: 40px; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="brand-icon">📈</div>
        <div>
          <h1>Social Analytics & Success Hub</h1>
          <p class="subtitle">Ottimizzazione orari, tag e formati dei post per il portfolio di Andrea Ravalli</p>
        </div>
      </div>
      <div>
        <span class="badge">Live eToro API Connected</span>
      </div>
    </header>

    <!-- Top KPI Cards -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Post Totali Tracciati</div>
        <div class="kpi-value">{insights.get('total_posts', 0)}</div>
        <div class="kpi-sub">Multi-platform feed</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Like Totali Ricevuti</div>
        <div class="kpi-value" style="color: #FF4D79;">❤️ {insights.get('total_likes', 0)}</div>
        <div class="kpi-sub">Media: {insights.get('avg_likes', 0)} like / post</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Commenti Ricevuti</div>
        <div class="kpi-value" style="color: var(--cyan);">💬 {insights.get('total_comments', 0)}</div>
        <div class="kpi-sub">Media: {insights.get('avg_comments', 0)} commenti / post</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Miglior Orario Pubblicazione</div>
        <div class="kpi-value" style="color: var(--green);">{insights.get('best_hour', '22:00')}</div>
        <div class="kpi-sub">Fascia con picco di engagement</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Miglior Giorno Settimana</div>
        <div class="kpi-value" style="color: var(--purple);">{insights.get('best_day', 'Martedì')}</div>
        <div class="kpi-sub">Engagement score massimo</div>
      </div>
    </div>

    <!-- Optimization Insights Box -->
    <div class="insights-box">
      <div class="insights-title">💡 Insight Strategici & Formula Engagement</div>
      <div class="insights-grid">
        <div class="insight-pill">
          <strong>📊 Formula Engagement Score:</strong>
          <code>(Like × 1.5) + (Commenti × 3.0)</code>. I commenti hanno peso doppio perché su eToro generano visibilità organica e fanno salire il post nel feed.
        </div>
        <div class="insight-pill">
          <strong>⏰ Orari Chiave per eToro:</strong>
          Le <strong>16:15</strong> (apertura Wall Street) e le <strong>22:45</strong> (chiusura US) attirano il massimo volume di lettori e investitori attivi.
        </div>
        <div class="insight-pill">
          <strong>🖼️ Formato Immagine Top:</strong>
          La <strong>Hitachi-style Infographic</strong> e le <strong>Card 16:9</strong> garantiscono visualizzazione ad altissima risoluzione su app mobile eToro.
        </div>
      </div>
    </div>

    <!-- Charts Grid -->
    <div class="charts-grid">
      <div class="chart-panel">
        <div class="panel-title">
          <span>🕒 Engagement per Orario di Pubblicazione (CET)</span>
        </div>
        <canvas id="chartHours" height="220"></canvas>
      </div>
      <div class="chart-panel">
        <div class="panel-title">
          <span>📅 Engagement per Giorno della Settimana</span>
        </div>
        <canvas id="chartDays" height="220"></canvas>
      </div>
    </div>

    <!-- Post History Table -->
    <div class="table-panel">
      <div class="panel-title">
        <span>📜 Storico Post Pubblicati & Metriche Live</span>
      </div>
      <div style="overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>Data & Ora</th>
              <th>Piattaforma / Sessione</th>
              <th>Titoli & Tag</th>
              <th>Formato Immagine</th>
              <th>Like</th>
              <th>Commenti</th>
              <th>Azione</th>
            </tr>
          </thead>
          <tbody id="postsTableBody">
          </tbody>
        </table>
      </div>
    </div>

    <footer>
      Portfolio Daily Recap Analytics · Aggiornato automaticamente via GitHub Actions & eToro Public API
    </footer>
  </div>

  <script>
    const postsData = {posts_json};
    const insightsData = {insights_json};

    // Render Table
    const tbody = document.getElementById('postsTableBody');
    postsData.forEach(p => {{
      const tr = document.createElement('tr');
      const tagsHtml = (p.tickers || []).map(t => `<span class="ticker-tag">$${{t}}</span>`).join(' ');
      const dateStr = p.published_at ? new Date(p.published_at).toLocaleString('it-IT') : 'Recente';
      tr.innerHTML = `
        <td><strong>${{dateStr}}</strong></td>
        <td><span style="color: var(--green); font-weight:700;">${{p.platform.toUpperCase()}}</span> · ${{p.session}}</td>
        <td>${{tagsHtml || '—'}}</td>
        <td><code>${{p.image_type || 'winners_losers_card'}}</code></td>
        <td><strong>❤️ ${{p.likes || 0}}</strong></td>
        <td><strong>💬 ${{p.comments || 0}}</strong></td>
        <td><a class="btn-link" href="${{p.url}}" target="_blank">Apri Post ↗</a></td>
      `;
      tbody.appendChild(tr);
    }});

    // Render Hours Chart (Dynamic from insightsData)
    const ctxHours = document.getElementById('chartHours').getContext('2d');
    const hoursSlots = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23];
    const hoursLabels = hoursSlots.map(h => String(h).padStart(2, '0') + ':00');
    const hoursData = hoursSlots.map(h => {{
      const entry = (insightsData.hourly && insightsData.hourly[String(h)]) || (insightsData.hourly && insightsData.hourly[h]);
      return entry ? Math.round((entry.eng || 0) * 10) / 10 : 0;
    }});

    new Chart(ctxHours, {{
      type: 'bar',
      data: {{
        labels: hoursLabels,
        datasets: [{{
          label: 'Engagement Score',
          data: hoursData,
          backgroundColor: 'rgba(0, 212, 255, 0.75)',
          borderRadius: 8,
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#9AA8C2' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#9AA8C2' }} }}
        }}
      }}
    }});

    // Render Days Chart (Dynamic from insightsData)
    const ctxDays = document.getElementById('chartDays').getContext('2d');
    const dayMap = [
      {{ name: 'Lunedì', key: 'Monday' }},
      {{ name: 'Martedì', key: 'Tuesday' }},
      {{ name: 'Mercoledì', key: 'Wednesday' }},
      {{ name: 'Giovedì', key: 'Thursday' }},
      {{ name: 'Venerdì', key: 'Friday' }},
      {{ name: 'Sabato', key: 'Saturday' }},
      {{ name: 'Domenica', key: 'Sunday' }}
    ];
    const daysLabels = dayMap.map(d => d.name);
    const daysData = dayMap.map(d => {{
      const entry = insightsData.weekdays && insightsData.weekdays[d.key];
      return entry ? Math.round((entry.eng || 0) * 10) / 10 : 0;
    }});

    new Chart(ctxDays, {{
      type: 'line',
      data: {{
        labels: daysLabels,
        datasets: [{{
          label: 'Engagement Score Totale',
          data: daysData,
          borderColor: '#13C636',
          backgroundColor: 'rgba(19, 198, 54, 0.15)',
          fill: true,
          tension: 0.4,
          pointRadius: 6,
          pointBackgroundColor: '#13C636'
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          y: {{ grid: {{ color: 'rgba(255,255,255,0.06)' }}, ticks: {{ color: '#9AA8C2' }} }},
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#9AA8C2' }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Analytics dashboard HTML generated at: {output_path}")
    return output_path


def update_and_build_dashboard():
    """Sync metrics from API and regenerate the dashboard HTML."""
    sync_etoro_metrics()
    generate_html_dashboard()
