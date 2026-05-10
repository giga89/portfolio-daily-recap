#!/usr/bin/env python3
"""
Instagram Story Generator
Generates a premium dark-themed vertical story image (1080x1920) with the
daily portfolio performance — suitable for Instagram Stories.

Dependencies: matplotlib (already in requirements)
Output: output/story.png
"""

import os
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch
import numpy as np
from datetime import datetime


ETORO_PROFILE = "etoro.com/people/andrearavalli"
ETORO_REFERRAL = "etoro.tw/46qgHLr"


def _perf_color(pct: float):
    """Return color based on performance."""
    if pct > 2.0:
        return "#00FF88"   # bright green
    elif pct > 0.5:
        return "#4ADE80"   # green
    elif pct >= 0:
        return "#86EFAC"   # light green
    elif pct > -0.5:
        return "#FCD34D"   # yellow
    elif pct > -2.0:
        return "#F87171"   # red
    else:
        return "#EF4444"   # bright red


def _perf_label(pct: float) -> str:
    """Return short label based on performance."""
    if pct > 2.0:
        return "🚀 TO THE MOON"
    elif pct > 0.5:
        return "🍀 GREAT GREEN"
    elif pct >= 0:
        return "🌿 SLIGHT GAINS"
    elif pct > -0.5:
        return "📉 MINOR DIP"
    elif pct > -2.0:
        return "💀 ROUGH"
    else:
        return "🧨 CRASH"


def generate_story_image(
    portfolio_daily: float,
    top_performers: list = None,
    output_path: str = "output/story.png",
) -> str:
    """
    Generate a premium Instagram Story image.

    Args:
        portfolio_daily: Daily portfolio performance (e.g. 1.47)
        top_performers: List of (symbol, pct) tuples for top 3 stocks
        output_path: Where to save the PNG

    Returns:
        Path to the generated image file
    """
    os.makedirs(os.path.dirname(output_path) or "output", exist_ok=True)

    # Story dimensions: 1080x1920 → use 10.8x19.2 inches at 100dpi
    fig = plt.figure(figsize=(10.8, 19.2), dpi=100)
    fig.patch.set_facecolor("#08090F")

    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_facecolor("#08090F")

    # ── Background gradient via multiple rectangles ──────────────────
    gradient_steps = 100
    for i in range(gradient_steps):
        alpha = i / gradient_steps
        color = (
            0.03 + 0.04 * alpha,    # R
            0.04 + 0.06 * alpha,    # G
            0.10 + 0.12 * alpha,    # B
        )
        ax.add_patch(patches.Rectangle(
            (0, i / gradient_steps), 1, 1 / gradient_steps,
            color=color, transform=ax.transAxes, zorder=0
        ))

    # ── Subtle grid lines (Bloomberg feel) ──────────────────────────
    for y in np.linspace(0.1, 0.9, 8):
        ax.axhline(y, color="#FFFFFF", alpha=0.03, linewidth=0.5)

    color = _perf_color(portfolio_daily)
    label = _perf_label(portfolio_daily)

    # ── Top bar ──────────────────────────────────────────────────────
    ax.add_patch(patches.Rectangle(
        (0, 0.91), 1, 0.09,
        color="#0D1117", alpha=0.8, transform=ax.transAxes, zorder=1
    ))
    ax.text(0.5, 0.955, "📊  PORTFOLIO UPDATE", color="#8B9BB4",
            ha="center", va="center", fontsize=16, fontweight="bold",
            transform=ax.transAxes, zorder=2)
    today_str = datetime.now().strftime("%d %B %Y").upper()
    ax.text(0.5, 0.925, today_str, color="#4A5568",
            ha="center", va="center", fontsize=12,
            transform=ax.transAxes, zorder=2)

    # ── Session label ────────────────────────────────────────────────
    ax.text(0.5, 0.86, "🌆 U.S. MARKET CLOSE", color="#8B9BB4",
            ha="center", va="center", fontsize=14, fontstyle="italic",
            transform=ax.transAxes, zorder=2)

    # ── Glowing performance circle ───────────────────────────────────
    # Outer glow rings
    for radius, alpha in [(0.22, 0.04), (0.19, 0.07), (0.16, 0.10)]:
        circle = plt.Circle((0.5, 0.60), radius, color=color, alpha=alpha,
                             transform=ax.transAxes, zorder=3)
        ax.add_patch(circle)

    # Main circle background
    circle_bg = plt.Circle((0.5, 0.60), 0.14, color="#0D1117",
                            transform=ax.transAxes, zorder=4)
    ax.add_patch(circle_bg)

    # Circle border
    circle_border = plt.Circle((0.5, 0.60), 0.14, color=color, alpha=0.8,
                                fill=False, linewidth=3,
                                transform=ax.transAxes, zorder=5)
    ax.add_patch(circle_border)

    # ── Big percentage number ────────────────────────────────────────
    pct_str = f"{portfolio_daily:+.2f}%"
    # Shadow
    ax.text(0.502, 0.598, pct_str, color="#000000", ha="center", va="center",
            fontsize=52, fontweight="bold", alpha=0.5,
            transform=ax.transAxes, zorder=5)
    # Main text
    ax.text(0.5, 0.60, pct_str, color=color, ha="center", va="center",
            fontsize=52, fontweight="bold",
            transform=ax.transAxes, zorder=6)

    # ── Performance label ─────────────────────────────────────────────
    ax.text(0.5, 0.51, label, color=color, ha="center", va="center",
            fontsize=18, fontweight="bold", alpha=0.9,
            transform=ax.transAxes, zorder=6)

    # ── Divider ──────────────────────────────────────────────────────
    ax.plot([0.1, 0.9], [0.47, 0.47], color="#1E2A3A", linewidth=1.5,
            transform=ax.transAxes, zorder=6)

    # ── Top performers (if provided) ─────────────────────────────────
    if top_performers:
        ax.text(0.5, 0.435, "TOP 3 DI OGGI", color="#8B9BB4",
                ha="center", va="center", fontsize=13, fontweight="bold",
                transform=ax.transAxes, zorder=6)

        for i, (symbol, pct) in enumerate(top_performers[:3]):
            y_pos = 0.38 - i * 0.055
            bar_color = _perf_color(pct)

            # Background row
            row_rect = FancyBboxPatch(
                (0.08, y_pos - 0.02), 0.84, 0.04,
                boxstyle="round,pad=0.005",
                facecolor="#0D1117", alpha=0.6,
                edgecolor=bar_color, linewidth=0.8,
                transform=ax.transAxes, zorder=6
            )
            ax.add_patch(row_rect)

            ax.text(0.15, y_pos, f"${symbol}", color="#E2E8F0",
                    ha="left", va="center", fontsize=13, fontweight="bold",
                    transform=ax.transAxes, zorder=7)
            ax.text(0.85, y_pos, f"{pct:+.2f}%", color=bar_color,
                    ha="right", va="center", fontsize=13, fontweight="bold",
                    transform=ax.transAxes, zorder=7)

    # ── Divider 2 ─────────────────────────────────────────────────────
    ax.plot([0.1, 0.9], [0.215, 0.215], color="#1E2A3A", linewidth=1.5,
            transform=ax.transAxes, zorder=6)

    # ── eToro CTA section ─────────────────────────────────────────────
    ax.text(0.5, 0.185, "👤  Segui il mio portfolio su eToro", color="#8B9BB4",
            ha="center", va="center", fontsize=13,
            transform=ax.transAxes, zorder=6)
    ax.text(0.5, 0.155, ETORO_PROFILE, color="#4299E1",
            ha="center", va="center", fontsize=12,
            transform=ax.transAxes, zorder=6)

    # Referral button
    btn = FancyBboxPatch(
        (0.15, 0.085), 0.70, 0.05,
        boxstyle="round,pad=0.005",
        facecolor="#1A365D", alpha=0.9,
        edgecolor="#4299E1", linewidth=1.5,
        transform=ax.transAxes, zorder=6
    )
    ax.add_patch(btn)
    ax.text(0.5, 0.11, f"🎁  Non sei su eToro? Iscriviti gratis →",
            color="#90CDF4", ha="center", va="center",
            fontsize=12, fontweight="bold",
            transform=ax.transAxes, zorder=7)

    # Referral link small
    ax.text(0.5, 0.055, ETORO_REFERRAL, color="#4A5568",
            ha="center", va="center", fontsize=10,
            transform=ax.transAxes, zorder=7)

    # ── Bottom brand bar ──────────────────────────────────────────────
    ax.add_patch(patches.Rectangle(
        (0, 0), 1, 0.035,
        color="#0D1117", alpha=1.0, transform=ax.transAxes, zorder=8
    ))
    ax.text(0.5, 0.018, "andrearavalli  •  eToro Portfolio", color="#2D3748",
            ha="center", va="center", fontsize=10,
            transform=ax.transAxes, zorder=9)

    plt.savefig(output_path, dpi=100, bbox_inches="tight",
                facecolor="#08090F", edgecolor="none")
    plt.close(fig)
    print(f"   ✅ Story image saved: {output_path}")
    return output_path


def generate_post_image(
    portfolio_daily: float,
    top_performers: list = None,
    session_name: str = "U.S. market close",
    output_path: str = "output/ig_post.png",
) -> str:
    """
    Generate a premium square Instagram post image (1080x1080).

    Args:
        portfolio_daily: Daily portfolio performance
        top_performers: List of (symbol, pct) tuples for top 5 stocks
        session_name: Market session name
        output_path: Where to save the PNG

    Returns:
        Path to the generated image file
    """
    os.makedirs(os.path.dirname(output_path) or "output", exist_ok=True)

    fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
    fig.patch.set_facecolor("#08090F")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_facecolor("#08090F")

    # Background gradient
    gradient_steps = 100
    for i in range(gradient_steps):
        alpha = i / gradient_steps
        color = (0.03 + 0.03 * alpha, 0.04 + 0.05 * alpha, 0.10 + 0.10 * alpha)
        ax.add_patch(patches.Rectangle(
            (0, i / gradient_steps), 1, 1 / gradient_steps,
            color=color, transform=ax.transAxes, zorder=0
        ))

    color = _perf_color(portfolio_daily)
    label = _perf_label(portfolio_daily)
    today_str = datetime.now().strftime("%d %B %Y").upper()

    # ── Header ────────────────────────────────────────────────────────
    ax.add_patch(patches.Rectangle(
        (0, 0.88), 1, 0.12,
        color="#0D1117", alpha=0.9, transform=ax.transAxes, zorder=1
    ))
    session_upper = session_name.upper()
    ax.text(0.5, 0.955, f"🌆  {session_upper}  📊", color="#E2E8F0",
            ha="center", va="center", fontsize=16, fontweight="bold",
            transform=ax.transAxes, zorder=2)
    ax.text(0.5, 0.90, today_str, color="#4A5568",
            ha="center", va="center", fontsize=11,
            transform=ax.transAxes, zorder=2)

    # ── Performance banner ────────────────────────────────────────────
    banner = FancyBboxPatch(
        (0.05, 0.76), 0.90, 0.10,
        boxstyle="round,pad=0.005",
        facecolor="#0D1117", alpha=0.9,
        edgecolor=color, linewidth=2,
        transform=ax.transAxes, zorder=3
    )
    ax.add_patch(banner)

    pct_str = f"{portfolio_daily:+.2f}%"
    ax.text(0.5, 0.83, f"{label}   {pct_str}", color=color,
            ha="center", va="center", fontsize=20, fontweight="bold",
            transform=ax.transAxes, zorder=4)

    # ── Top performers ────────────────────────────────────────────────
    performers = top_performers or []
    ax.text(0.5, 0.73, "📈  TOP 5 TODAY", color="#8B9BB4",
            ha="center", va="center", fontsize=13, fontweight="bold",
            transform=ax.transAxes, zorder=4)

    for i, (symbol, pct) in enumerate(performers[:5]):
        y_pos = 0.67 - i * 0.065
        bar_color = _perf_color(pct)

        row = FancyBboxPatch(
            (0.06, y_pos - 0.025), 0.88, 0.05,
            boxstyle="round,pad=0.005",
            facecolor="#0D1117", alpha=0.6,
            edgecolor=bar_color, linewidth=0.8,
            transform=ax.transAxes, zorder=4
        )
        ax.add_patch(row)

        # Rank number
        ax.text(0.11, y_pos, f"#{i+1}", color="#4A5568",
                ha="center", va="center", fontsize=11,
                transform=ax.transAxes, zorder=5)
        ax.text(0.25, y_pos, f"${symbol}", color="#E2E8F0",
                ha="left", va="center", fontsize=13, fontweight="bold",
                transform=ax.transAxes, zorder=5)
        ax.text(0.88, y_pos, f"{pct:+.2f}%", color=bar_color,
                ha="right", va="center", fontsize=13, fontweight="bold",
                transform=ax.transAxes, zorder=5)

    # ── Divider ───────────────────────────────────────────────────────
    ax.plot([0.05, 0.95], [0.31, 0.31], color="#1E2A3A", linewidth=1.5,
            transform=ax.transAxes, zorder=5)

    # ── eToro section ─────────────────────────────────────────────────
    ax.text(0.5, 0.27, "👤  Segui il mio portfolio", color="#8B9BB4",
            ha="center", va="center", fontsize=13,
            transform=ax.transAxes, zorder=5)
    ax.text(0.5, 0.235, ETORO_PROFILE, color="#4299E1",
            ha="center", va="center", fontsize=12,
            transform=ax.transAxes, zorder=5)

    # Referral button
    ref_btn = FancyBboxPatch(
        (0.10, 0.145), 0.80, 0.065,
        boxstyle="round,pad=0.005",
        facecolor="#1A365D", alpha=0.9,
        edgecolor="#4299E1", linewidth=1.5,
        transform=ax.transAxes, zorder=5
    )
    ax.add_patch(ref_btn)
    ax.text(0.5, 0.178, "🎁  Non sei su eToro? Iscriviti gratis!",
            color="#90CDF4", ha="center", va="center",
            fontsize=13, fontweight="bold",
            transform=ax.transAxes, zorder=6)
    ax.text(0.5, 0.155, ETORO_REFERRAL, color="#4A90D9",
            ha="center", va="center", fontsize=11,
            transform=ax.transAxes, zorder=6)

    # ── Bottom bar ────────────────────────────────────────────────────
    ax.add_patch(patches.Rectangle(
        (0, 0), 1, 0.10,
        color="#0D1117", alpha=1.0, transform=ax.transAxes, zorder=7
    ))
    ax.text(0.5, 0.06, "Portfolio automaticamente diversificato", color="#2D3748",
            ha="center", va="center", fontsize=11,
            transform=ax.transAxes, zorder=8)
    ax.text(0.5, 0.03, "@andrearavalli  •  eToro Copy Investor", color="#2D3748",
            ha="center", va="center", fontsize=10,
            transform=ax.transAxes, zorder=8)

    plt.savefig(output_path, dpi=100, bbox_inches="tight",
                facecolor="#08090F", edgecolor="none")
    plt.close(fig)
    print(f"   ✅ Post image saved: {output_path}")
    return output_path
