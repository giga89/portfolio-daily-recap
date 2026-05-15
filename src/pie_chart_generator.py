#!/usr/bin/env python3
"""
Pie Chart Generator
Creates dark-mode portfolio allocation pie charts for social posts.
Four chart types: allocation by position, by sector, by geography, and P&L by asset type.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Dark theme constants ───────────────────────────────────────────────────────
BG_COLOR    = '#0a0a0a'
TEXT_COLOR  = '#e8e8e8'
GRID_COLOR  = '#1a1a1a'

# Color palettes for each chart type
COLORS_ALLOCATION = [
    '#00C805', '#00A8E8', '#FF6B35', '#FFD23F', '#9B59B6',
    '#1ABC9C', '#E74C3C', '#3498DB', '#F39C12', '#27AE60',
    '#E91E63', '#607D8B',
]
COLORS_SECTOR = [
    '#00C805', '#00A8E8', '#FF6B35', '#FFD23F', '#9B59B6',
    '#1ABC9C', '#E74C3C', '#607D8B',
]
COLORS_GEO = [
    '#00A8E8', '#FF6B35', '#FFD23F', '#9B59B6', '#1ABC9C',
]
COLORS_PNL = [
    '#00C805', '#00A8E8', '#FF6B35', '#E74C3C',
]

# ── Sector and Geography mappings ─────────────────────────────────────────────
# Maps eToro ticker symbols to sector labels
SECTOR_MAP: dict[str, str] = {
    # AI / Tech / Cloud
    'NVDA': 'AI & Semiconductors',
    'AMD':  'AI & Semiconductors',
    'TSM':  'AI & Semiconductors',
    'AVGO': 'AI & Semiconductors',
    'ARM':  'AI & Semiconductors',
    'SNPS': 'AI & Semiconductors',
    'MSFT': 'AI & Tech',
    'GOOG': 'AI & Tech',
    'AMZN': 'AI & Tech',
    'META': 'AI & Tech',
    'AAPL': 'AI & Tech',
    'PLTR': 'AI & Tech',
    'NET':  'AI & Tech',
    # Healthcare / Pharma
    'LLY':     'Healthcare',
    'NVO':     'Healthcare',
    'NOVO-B':  'Healthcare',
    'AZN':     'Healthcare',
    'AZN.L':   'Healthcare',
    'ABT':     'Healthcare',
    'ABT.US':  'Healthcare',
    'ABBV':    'Healthcare',
    'HUM':     'Healthcare',
    # Finance / Insurance
    '2318.HK':  'Finance',
    'SX7PEX.DE': 'Finance',
    'PYPL':    'Finance',
    'ETOR':    'Finance',
    # Energy / Commodities / Materials
    'ENI.MI':  'Energy & Resources',
    'MAU.PA':  'Energy & Resources',
    'GLEN.L':  'Energy & Resources',
    'CCJ':     'Energy & Resources',
    'ENEL.MI': 'Energy & Resources',
    'PRY.MI':  'Energy & Resources',
    'TRIG.L':  'Energy & Resources',
    # Auto
    'VOW3.DE': 'Auto',
    'RACE':    'Auto',
    # Logistics / Shipping
    '1919.HK': 'Logistics',
    # EM / Asia Tech
    '9618.HK': 'Asia Tech',
    'MELI':    'Asia Tech',
    # Crypto
    'TRX':     'Crypto',
    'BTC':     'Crypto',
    # Bonds / Cash
    'IB01.L':  'Bonds & Cash',
    'XEON.DE': 'Bonds & Cash',
    # Global ETF / Diversified
    'SWDA':    'Global ETF',
    'VWCE.L':  'Global ETF',
    'IEMG':    'Global ETF',
    'IEUR':    'Global ETF',
    'IQQL.DE': 'Global ETF',
    'INDO.PA': 'Global ETF',
    'WDEF.L':  'Global ETF',
}

# Maps eToro ticker symbols to geographic labels
GEO_MAP: dict[str, str] = {
    # USA
    'NVDA': 'USA', 'AMD': 'USA', 'AVGO': 'USA', 'MSFT': 'USA', 'GOOG': 'USA',
    'AMZN': 'USA', 'META': 'USA', 'AAPL': 'USA', 'PLTR': 'USA', 'NET': 'USA',
    'LLY': 'USA', 'ABT': 'USA', 'ABT.US': 'USA', 'ABBV': 'USA', 'HUM': 'USA',
    'CCJ': 'USA', 'PYPL': 'USA', 'ETOR': 'USA', 'IEMG': 'USA', 'MELI': 'USA',
    # Europe
    'AZN.L': 'Europe', 'ENEL.MI': 'Europe', 'ENI.MI': 'Europe',
    'GLEN.L': 'Europe', 'VOW3.DE': 'Europe', 'RACE': 'Europe',
    'PRY.MI': 'Europe', 'MAU.PA': 'Europe', 'SX7PEX.DE': 'Europe',
    'TRIG.L': 'Europe', 'WDEF.L': 'Europe', 'IEUR': 'Europe',
    'IB01.L': 'Europe', 'XEON.DE': 'Europe', 'IQQL.DE': 'Europe',
    # Asia / Pacific
    '2318.HK': 'Asia', '9618.HK': 'Asia', '1919.HK': 'Asia', 'TSM': 'Asia',
    'NVO': 'Europe',  # Novo Nordisk - Denmark
    'NOVO-B': 'Europe',
    'ARM': 'Europe',  # UK-headquartered
    # Global / Diversified
    'SWDA': 'Global', 'VWCE.L': 'Global', 'INDO.PA': 'Global',
    # Crypto (no geography)
    'TRX': 'Crypto', 'BTC': 'Crypto',
    # AZN note: AstraZeneca is UK, listed London
    'AZN': 'Europe',
    'SNPS': 'USA',
}


# ── Public chart generators ───────────────────────────────────────────────────

def generate_allocation_pie(
    weights: dict,
    output_path: str = 'output/pie_allocation.png',
    top_n: int = 12,
) -> str:
    """
    Pie chart of current portfolio allocation by position.

    Args:
        weights: {ticker: percentage_weight} from BullAware
        output_path: where to save the PNG
        top_n: show top N positions; bundle the rest into 'Others'

    Returns:
        output_path if successful, else None
    """
    if not weights:
        return None

    sorted_items = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    top     = sorted_items[:top_n]
    others  = sorted_items[top_n:]

    labels = [item[0] for item in top]
    values = [item[1] for item in top]

    if others:
        labels.append('Others')
        values.append(sum(v for _, v in others))

    title = 'Portfolio Allocation'
    return _render_pie(labels, values, COLORS_ALLOCATION, title, output_path)


def generate_sector_pie(
    weights: dict,
    output_path: str = 'output/pie_sector.png',
) -> str:
    """
    Pie chart of portfolio allocation grouped by sector.

    Args:
        weights: {ticker: percentage_weight} from BullAware
        output_path: where to save the PNG

    Returns:
        output_path if successful, else None
    """
    if not weights:
        return None

    sector_weights: dict[str, float] = {}
    for ticker, pct in weights.items():
        # Normalize ticker for lookup (remove exchange suffix for common cases)
        sector = _lookup_sector(ticker)
        sector_weights[sector] = sector_weights.get(sector, 0.0) + pct

    labels = list(sector_weights.keys())
    values = list(sector_weights.values())
    return _render_pie(labels, values, COLORS_SECTOR, 'Portfolio by Sector', output_path)


def generate_geo_pie(
    weights: dict,
    output_path: str = 'output/pie_geo.png',
) -> str:
    """
    Pie chart of portfolio allocation grouped by geography.

    Args:
        weights: {ticker: percentage_weight} from BullAware
        output_path: where to save the PNG

    Returns:
        output_path if successful, else None
    """
    if not weights:
        return None

    geo_weights: dict[str, float] = {}
    for ticker, pct in weights.items():
        geo = _lookup_geo(ticker)
        geo_weights[geo] = geo_weights.get(geo, 0.0) + pct

    labels = list(geo_weights.keys())
    values = list(geo_weights.values())
    return _render_pie(labels, values, COLORS_GEO, 'Portfolio by Geography', output_path)


def generate_pnl_history_pie(
    pnl_by_type: dict,
    output_path: str = 'output/pie_pnl_history.png',
) -> str:
    """
    Pie chart showing cumulative P&L contribution by asset type (from eToro history).
    Separates positive and negative contributions.

    Args:
        pnl_by_type: {'Stocks': 2956.09, 'ETF': 2671.65, 'Crypto': 1877.16, 'CFD': -2414.96}
        output_path: where to save the PNG

    Returns:
        output_path if successful, else None
    """
    if not pnl_by_type:
        return None

    # Split into gains and losses for a two-part visualization
    gains  = {k: v for k, v in pnl_by_type.items() if v > 0}
    losses = {k: abs(v) for k, v in pnl_by_type.items() if v < 0}

    if not gains and not losses:
        return None

    # Build labels and values: show gains, then losses (with suffix)
    labels = list(gains.keys()) + [f"{k} (loss)" for k in losses.keys()]
    values = list(gains.values()) + list(losses.values())

    total_gain = sum(gains.values())
    total_loss = sum(losses.values())
    net        = total_gain - total_loss
    subtitle   = f"Net P&L: {'+'if net>=0 else ''}${net:.0f}"

    colors_ext = COLORS_PNL[:len(gains)] + ['#CC2200', '#FF4444', '#FF6666']
    return _render_pie(
        labels, values, colors_ext,
        f'P&L by Asset Type (since 2020)\n{subtitle}',
        output_path,
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _lookup_sector(ticker: str) -> str:
    """Return sector label for a ticker, with fallback."""
    normalized = ticker.upper().replace('-', '.').split('.')[0]
    # Try exact match first
    if ticker.upper() in SECTOR_MAP:
        return SECTOR_MAP[ticker.upper()]
    # Try base symbol (without exchange suffix)
    if normalized in SECTOR_MAP:
        return SECTOR_MAP[normalized]
    return 'Other'


def _lookup_geo(ticker: str) -> str:
    """Return geography label for a ticker, with fallback."""
    normalized = ticker.upper().replace('-', '.').split('.')[0]
    if ticker.upper() in GEO_MAP:
        return GEO_MAP[ticker.upper()]
    if normalized in GEO_MAP:
        return GEO_MAP[normalized]
    return 'Other'


def _render_pie(
    labels: list,
    values: list,
    colors: list,
    title: str,
    output_path: str,
) -> str:
    """Render and save a dark-mode pie chart."""
    try:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 8), facecolor=BG_COLOR)
        ax.set_facecolor(BG_COLOR)

        # Normalize colors to match number of slices
        num_slices = len(labels)
        slice_colors = (colors * ((num_slices // len(colors)) + 1))[:num_slices]

        # Explode the largest slice slightly
        max_idx  = int(np.argmax(values))
        explode  = [0.03 if i == max_idx else 0.0 for i in range(num_slices)]

        wedges, texts, autotexts = ax.pie(
            values,
            labels=None,
            colors=slice_colors,
            explode=explode,
            autopct=lambda p: f'{p:.1f}%' if p >= 3 else '',
            pctdistance=0.75,
            startangle=90,
            wedgeprops={'linewidth': 1.5, 'edgecolor': BG_COLOR},
        )

        # Style percentage labels
        for autotext in autotexts:
            autotext.set_color(TEXT_COLOR)
            autotext.set_fontsize(9)
            autotext.set_fontweight('bold')

        # Legend on the right
        legend_labels = [
            f"{lbl}  {v:.1f}%" for lbl, v in zip(labels, values)
        ]
        ax.legend(
            wedges,
            legend_labels,
            loc='center left',
            bbox_to_anchor=(1.0, 0.5),
            fontsize=10,
            frameon=True,
            facecolor='#1a1a1a',
            edgecolor='#333333',
            labelcolor=TEXT_COLOR,
        )

        # Title
        ax.set_title(
            title,
            color=TEXT_COLOR,
            fontsize=14,
            fontweight='bold',
            pad=20,
        )

        # Watermark
        fig.text(
            0.98, 0.02,
            'eToro: AndreaRavalli',
            ha='right', va='bottom',
            color='#444444',
            fontsize=8,
        )

        plt.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
        plt.close(fig)
        print(f"🥧 Pie chart saved: {output_path}")
        return output_path

    except Exception as exc:
        print(f"❌ Pie chart generation error: {exc}")
        import traceback
        traceback.print_exc()
        plt.close('all')
        return None
