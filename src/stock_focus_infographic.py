#!/usr/bin/env python3
"""
High-End Investor Infographic Generator (Hitachi Style)
======================================================
Generates ultra-premium, professional investment infographics inspired by top-tier financial creators:
  • Elegant top header with company branding and thematic illustration backdrop
  • 4 Clean Highlight Metric cards with icons & bold numbers (Revenue growth, Margins, Weight, Sector)
  • "PERCHÉ INVESTO IN [AZIENDA]" structured thesis with red/cyan accent badges
  • Iconic Discipline Quote on the right: "Non investo per il prossimo trimestre. Investo per il prossimo decennio."
  • Dark / Modern Corporate bottom bar with Andrea Ravalli branding, sector icons & hashtags
"""

import io
import os
import time
import requests
from typing import Dict, Any, Optional, List

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

CARD_W = 1200
CARD_H = 1200  # Square 1:1 format (optimal for both mobile and desktop feed)

LOGO_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo_cache")

# Full company data dictionary tailored for infographics
COMPANY_INFOGRAPHICS = {
    "PLTR": {
        "name": "PALANTIR",
        "tagline": "AI Platform & Enterprise Defense",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Palantir è l'infrastruttura operativa critica scelta da governi e grandi multinazionali per l'intelligenza artificiale.",
        "kpis": [
            {"label": "CRESCITA COMMERCIALE", "val": "+54%", "sub": "Adozione AIP record in US"},
            {"label": "RULE OF 40 (PROFITTO)", "val": "68%", "sub": "Margini operativi top tier"},
            {"label": "PESO IN PORTAFOGLIO", "val": "14.75%", "sub": "Posizione core conviction"},
            {"label": "BILANCIO & CASSA", "val": "$4.0B+", "sub": "Zero debito, cassa netta"},
        ],
        "pillars": [
            ("⚡ Fossato Difensivo:", "Contratti decennali insostituibili con il governo US e la difesa."),
            ("🤖 Espansione AIP:", "La piattaforma AI sta conquistando le imprese Fortune 500 a ritmi record."),
            ("📊 Potere di Prezzo:", "I clienti espandono costantemente la spesa (Net Retention > 115%)."),
            ("🛡️ Visione Decennale:", "Posizionamento unico all'intersezione tra sicurezza nazionale ed AI."),
        ],
        "quote": "Non investo per il prossimo trimestre. Investo per il prossimo decennio.",
        "tags": ["#Palantir", "#AIP", "#ArtificialIntelligence", "#DefenseTech", "#LongTermInvesting"],
        "color": (0, 190, 240),
        "domain": "palantir.com"
    },
    "NVDA": {
        "name": "NVIDIA",
        "tagline": "Accelerated Computing & AI Architecture",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "NVIDIA detiene il monopolio de facto dei chip e dell'ecosistema software per l'addestramento e l'inferenza AI globale.",
        "kpis": [
            {"label": "CRESCITA DATA CENTER", "val": "+150%", "sub": "Domanda record architettura Blackwell"},
            {"label": "MARGINE LORDO", "val": "75%+", "sub": "Potere di prezzo ineguagliato"},
            {"label": "PESO IN PORTAFOGLIO", "val": "Core Tech", "sub": "Pilastro infrastrutturale"},
            {"label": "FOSSATO SOFTWARE", "val": "CUDA", "sub": "Milioni di sviluppatori vincolati"},
        ],
        "pillars": [
            ("⚡ Monopolio dell'Hardware:", "I chip GPU H100, H200 e Blackwell sono lo standard dell'intera industria."),
            ("🖥️ Ecosistema CUDA:", "Oltre 15 anni di sviluppo software creano barriere all'entrata insormontabili."),
            ("🌐 Espansione Networking:", "Con Mellanox e Infiniband, controlla anche la connettività dei data center."),
            ("🎯 Crescita Strutturale:", "La spesa in hyperscaler (MSFT, GOOG, AMZN) sostiene la domanda multi-annuale."),
        ],
        "quote": "I chip sono il nuovo petrolio, e NVIDIA controlla le raffinerie mondiali.",
        "tags": ["#Nvidia", "#Blackwell", "#Semiconductors", "#ArtificialIntelligence", "#TechLeaders"],
        "color": (118, 185, 0),
        "domain": "nvidia.com"
    },
    "CCJ": {
        "name": "CAMECO",
        "tagline": "Uranium & Global Nuclear Clean Energy",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Cameco è il leader mondiale dell'estrazione di uranio e dei servizi tecnologici per la rinascita dell'energia nucleare.",
        "kpis": [
            {"label": "PREZZO CONTRATTUALE", "val": "+65%", "sub": "Trend rialzista a lungo termine"},
            {"label": "ASSET STRATEGICI", "val": "Tier-1", "sub": "McArthur River & Cigar Lake"},
            {"label": "PESO IN PORTAFOGLIO", "val": "20.67%", "sub": "Top holding di convinzione"},
            {"label": "INTEGRAZIONE WESTINGHOUSE", "val": "Full Chain", "sub": "Estrazione, combustibile e reattori"},
        ],
        "pillars": [
            ("⚡ Deficit Strutturale:", "La domanda globale supera l'offerta primaria da oltre un decennio."),
            ("🤖 Spinta dei Data Center:", "Big Tech richiede energia nucleare 24/7 a zero emissioni per alimentare l'AI."),
            ("🛡️ Contratti Pluriennali:", "Flussi di cassa stabili e protetti da accordi a lungo termine con le utility."),
            ("🌍 Geopolitica dell'Uranio:", "Le nazioni occidentali si allontanano dalla Russia, premiando il Canada."),
        ],
        "quote": "La transizione energetica e l'intelligenza artificiale non possono esistere senza il nucleare.",
        "tags": ["#Cameco", "#Uranium", "#NuclearEnergy", "#CleanTech", "#Commodities"],
        "color": (255, 175, 0),
        "domain": "cameco.com"
    },
    "SX7PEX.DE": {
        "name": "EURO STOXX BANKS",
        "tagline": "European Banking Sector UCITS ETF",
        "title": "TESI D'INVESTIMENTO & HIGHLIGHTS",
        "subtitle": "Esposizione ai principali gruppi bancari europei con bilanci solidi, alti dividendi e buyback massicci.",
        "kpis": [
            {"label": "DIVIDEND YIELD", "val": "7.5%+", "sub": "Rendimento da cassa elevato"},
            {"label": "CAPITAL RATIO (CET1)", "val": ">15.5%", "sub": "Massimi storici di solvibilità"},
            {"label": "PESO IN PORTAFOGLIO", "val": "17.65%", "sub": "Pilastro valore e dividendi"},
            {"label": "BUYBACK & RESILIENZA", "val": "Record", "sub": "Remunerazione azionisti sostenibile"},
        ],
        "pillars": [
            ("💰 Generazione di Cassa:", "I margini di interesse e la redditività rimangono a livelli strutturalmente alti."),
            ("🛡️ Qualità del Credito:", "NPL ai minimi storici e coperture prudenziali estremamente elevate."),
            ("📈 Valutazioni a Sconto:", "P/E attraenti rispetto al mercato USA offrono un ampio margine di sicurezza."),
            ("🔄 Ritorno di Capitale:", "Dividendi costanti e programmi di riacquisto azioni aumentano il valore per azione."),
        ],
        "quote": "Un portafoglio vincente bilancia la crescita aggressiva con solide macchine da dividendo.",
        "tags": ["#Banking", "#EuroStoxx", "#Dividends", "#ValueInvesting", "#Europe"],
        "color": (60, 130, 240),
        "domain": "stoxx.com"
    }
}


def _font(size: int, bold: bool = True) -> "ImageFont.FreeTypeFont":
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()


def _fetch_company_logo(ticker: str, domain: str) -> Optional[Image.Image]:
    os.makedirs(LOGO_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(LOGO_CACHE_DIR, f"{ticker}_hq.png")
    if os.path.exists(cache_path):
        try: return Image.open(cache_path).convert("RGBA")
        except: pass

    urls = [
        f"https://img.logo.dev/{domain}?token=pk_anonymous&size=200&format=png",
        f"https://logo.clearbit.com/{domain}?size=200",
    ]
    for u in urls:
        try:
            r = requests.get(u, timeout=4)
            if r.status_code == 200 and len(r.content) > 300:
                im = Image.open(io.BytesIO(r.content)).convert("RGBA")
                im.save(cache_path)
                return im
        except: continue
    return None


def generate_stock_infographic(
    ticker: str,
    output_path: str = None,
) -> str:
    """
    Generate an ultra-premium Hitachi-style square infographic (1200x1200).
    """
    if not output_path:
        output_path = f"output/infographic_{ticker}.png"

    info = COMPANY_INFOGRAPHICS.get(ticker, COMPANY_INFOGRAPHICS["PLTR"])
    brand_color = info.get("color", (0, 190, 240))

    # 1. Base Canvas - Off-white / Warm Ivory Premium background (#F7F8FA)
    img = Image.new("RGBA", (CARD_W, CARD_H), (246, 248, 252, 255))
    draw = ImageDraw.Draw(img)

    # 2. Top Header Canvas (Light Gradient with soft mountain / tech landscape vibe)
    header_h = 320
    # Soft sky gradient on top
    for y in range(header_h):
        alpha = y / header_h
        r = int(235 * (1 - alpha) + 246 * alpha)
        g = int(242 * (1 - alpha) + 248 * alpha)
        b = int(252 * (1 - alpha) + 252 * alpha)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b, 255))

    # Top Brand Bar
    f_brand = _font(46, bold=True)
    f_tagline = _font(22, bold=False)
    f_title = _font(38, bold=True)
    f_lead = _font(20, bold=False)

    brand_name = info["name"]
    draw.text((60, 45), brand_name, fill=(16, 24, 40, 255), font=f_brand)
    bb_brand = draw.textbbox((60, 45), brand_name, font=f_brand)
    
    # Vertical divider
    div_x = bb_brand[2] + 20
    draw.line([(div_x, 50), (div_x, 95)], fill=(180, 190, 205, 255), width=2)
    draw.text((div_x + 20, 60), info["tagline"], fill=(100, 115, 135, 255), font=f_tagline)

    # Title in Red / Brand Accent
    draw.text((60, 120), info["title"], fill=(190, 24, 24, 255), font=f_title)
    
    # Subtitle lead text
    sub_words = info["subtitle"].split()
    sub_lines, curr = [], ""
    for w in sub_words:
        test = (curr + " " + w).strip()
        if draw.textbbox((0,0), test, font=f_lead)[2] < 1080:
            curr = test
        else:
            sub_lines.append(curr)
            curr = w
    if curr: sub_lines.append(curr)
    
    sy = 180
    for l in sub_lines[:2]:
        draw.text((60, sy), l, fill=(55, 65, 81, 240), font=f_lead)
        sy += 30

    # 3. 4 Highlight KPI Cards (Grid: 4 columns across)
    kpis = info.get("kpis", [])
    kpi_y = 285
    kpi_h = 175
    gap = 18
    kpi_w = (CARD_W - 120 - gap * 3) // 4

    f_kpi_lbl = _font(13, bold=True)
    f_kpi_val = _font(32, bold=True)
    f_kpi_sub = _font(13, bold=False)

    for i, kpi in enumerate(kpis[:4]):
        kx = 60 + i * (kpi_w + gap)
        # White card with soft border and subtle shadow
        draw.rounded_rectangle([kx, kpi_y, kx + kpi_w, kpi_y + kpi_h], radius=14, fill=(255, 255, 255, 255), outline=(225, 232, 242, 255), width=1)
        
        # Top Accent Dot
        draw.ellipse([kx + 18, kpi_y + 18, kx + 28, kpi_y + 28], fill=(190, 24, 24, 255))
        
        # Label
        draw.text((kx + 34, kpi_y + 16), kpi["label"][:18], fill=(100, 115, 135, 255), font=f_kpi_lbl)
        # Value
        draw.text((kx + 18, kpi_y + 55), kpi["val"], fill=(16, 24, 40, 255), font=f_kpi_val)
        # Subtitle / note
        draw.text((kx + 18, kpi_y + 115), kpi["sub"], fill=(100, 116, 139, 255), font=f_kpi_sub)

    # 4. Middle Content Sections:
    # Left Box (Why I Invest - 60% width) + Right Box (Quote Box - 40% width)
    mid_y = kpi_y + kpi_h + 26
    mid_h = 495
    left_w = 660
    right_w = CARD_W - 120 - left_w - gap

    # Left Section: "WHY I INVEST IN [COMPANY]"
    draw.rounded_rectangle([60, mid_y, 60 + left_w, mid_y + mid_h], radius=18, fill=(255, 255, 255, 255), outline=(225, 232, 242, 255), width=1)
    
    # Left Header Pill
    f_pill = _font(15, bold=True)
    pill_text = f"PERCHÉ INVESTO IN ${ticker}"
    draw.rounded_rectangle([85, mid_y + 24, 85 + 320, mid_y + 60], radius=10, fill=(16, 24, 40, 255))
    draw.text((105, mid_y + 32), pill_text, fill=(255, 255, 255, 255), font=f_pill)

    f_bullet_title = _font(18, bold=True)
    f_bullet_desc = _font(16, bold=False)

    pillars = info.get("pillars", [])
    py = mid_y + 85
    for b_title, b_desc in pillars[:4]:
        # Red Icon badge
        draw.ellipse([85, py + 2, 85 + 24, py + 26], fill=(190, 24, 24, 255))
        draw.text((93, py + 4), "✓", fill=(255, 255, 255, 255), font=_font(14, bold=True))
        
        draw.text((120, py), b_title, fill=(16, 24, 40, 255), font=f_bullet_title)
        
        # Wrap desc
        dw = b_desc.split()
        d_lines, dc = [], ""
        for w in dw:
            t = (dc + " " + w).strip()
            if draw.textbbox((0,0), t, font=f_bullet_desc)[2] < left_w - 90:
                dc = t
            else:
                d_lines.append(dc)
                dc = w
        if dc: d_lines.append(dc)
        
        dy = py + 28
        for dl in d_lines[:2]:
            draw.text((120, dy), dl, fill=(75, 85, 99, 255), font=f_bullet_desc)
            dy += 24
        py += 96

    # Right Section: Quote Card
    rx = 60 + left_w + gap
    draw.rounded_rectangle([rx, mid_y, rx + right_w, mid_y + mid_h], radius=18, fill=(255, 255, 255, 255), outline=(225, 232, 242, 255), width=1)
    
    # Large quotation mark
    f_quote_mark = _font(80, bold=True)
    draw.text((rx + 30, mid_y + 20), "“", fill=(190, 24, 24, 230), font=f_quote_mark)
    
    f_quote = _font(25, bold=True)
    f_quote_red = _font(27, bold=True)

    draw.text((rx + 30, mid_y + 130), "Non investo", fill=(16, 24, 40, 255), font=f_quote)
    draw.text((rx + 30, mid_y + 168), "per il prossimo", fill=(16, 24, 40, 255), font=f_quote)
    draw.text((rx + 30, mid_y + 206), "trimestre.", fill=(16, 24, 40, 255), font=f_quote)
    
    draw.text((rx + 30, mid_y + 270), "Investo per il", fill=(16, 24, 40, 255), font=f_quote)
    draw.text((rx + 30, mid_y + 310), "prossimo decennio.", fill=(190, 24, 24, 255), font=f_quote_red)
    
    # Brush underline
    draw.line([(rx + 30, mid_y + 355), (rx + 290, mid_y + 355)], fill=(190, 24, 24, 255), width=3)
    
    draw.text((rx + 30, mid_y + 420), "— Andrea Ravalli", fill=(100, 116, 139, 255), font=_font(18, bold=True))
    draw.text((rx + 30, mid_y + 448), "Popular Investor @ eToro", fill=(140, 155, 175, 255), font=_font(15, bold=False))

    # 5. Bottom Modern Dark Banner (120px)
    bot_y = CARD_H - 150
    draw.rounded_rectangle([60, bot_y, CARD_W - 60, CARD_H - 45], radius=16, fill=(12, 18, 34, 255))
    
    f_bot_main = _font(20, bold=True)
    f_bot_sub = _font(15, bold=False)
    f_tags = _font(14, bold=True)

    draw.text((90, bot_y + 25), "ANDREA RAVALLI · POPULAR INVESTOR", fill=(255, 255, 255, 255), font=f_bot_main)
    draw.text((90, bot_y + 55), "Strategia fondamentale trasparente & orizzonte a lungo termine", fill=(160, 175, 200, 255), font=f_bot_sub)

    # Hashtags
    tags_str = " ".join(info.get("tags", [])[:4])
    bb_t = draw.textbbox((0, 0), tags_str, font=f_tags)
    draw.text((CARD_W - 90 - (bb_t[2] - bb_t[0]), bot_y + 42), tags_str, fill=(0, 190, 240, 255), font=f_tags)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.convert("RGB").save(output_path, "PNG", optimize=True)
    print(f"🏆 Ultra-Premium Hitachi-style Infographic generated: {output_path}")
    return output_path
