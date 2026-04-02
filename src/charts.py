"""Step 3 — Generate two publication-style charts."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

import config

# Publication-style defaults
plt.rcParams.update({
    "figure.facecolor": "#FAFAFA",
    "axes.facecolor": "#FAFAFA",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "font.size": 10,
    "figure.dpi": 150,
})


def _format_date_axis(ax):
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")


def spread_regime_chart(metrics_dict: dict, df: pd.DataFrame) -> str:
    """
    Chart 1 — Clean dark spread vs EUA, twin-axis, 60 days.
    Returns path to saved PNG.
    """
    _, cds_hist = metrics_dict["Clean Dark Spread"]
    eua = df["EUA"].iloc[-60:]

    fig, ax1 = plt.subplots(figsize=(10, 5))

    # Left axis: Clean Dark Spread
    color_cds = "#D85A30"
    ax1.plot(cds_hist.index, cds_hist.values, color=color_cds, linewidth=1.8,
             label="Clean Dark Spread (EUR/MWh)")
    ax1.axhline(0, color="grey", linewidth=0.8, linestyle="-")
    ax1.set_ylabel("Clean Dark Spread (EUR/MWh)", color=color_cds)
    ax1.tick_params(axis="y", labelcolor=color_cds)

    # Mark today
    ax1.plot(cds_hist.index[-1], cds_hist.iloc[-1], "o", color=color_cds, markersize=7)
    ax1.annotate(f"{cds_hist.iloc[-1]:.1f}",
                 xy=(cds_hist.index[-1], cds_hist.iloc[-1]),
                 textcoords="offset points", xytext=(8, 5),
                 fontsize=9, color=color_cds, fontweight="bold")

    # Right axis: EUA
    color_eua = "#178ADD"
    ax2 = ax1.twinx()
    ax2.spines["right"].set_visible(True)
    ax2.plot(eua.index, eua.values, color=color_eua, linewidth=1.8,
             linestyle="--", label="EUA (EUR/tCO₂)")
    ax2.set_ylabel("EUA (EUR/tCO₂)", color=color_eua)
    ax2.tick_params(axis="y", labelcolor=color_eua)

    ax2.plot(eua.index[-1], eua.iloc[-1], "o", color=color_eua, markersize=7)
    ax2.annotate(f"{eua.iloc[-1]:.1f}",
                 xy=(eua.index[-1], eua.iloc[-1]),
                 textcoords="offset points", xytext=(8, -10),
                 fontsize=9, color=color_eua, fontweight="bold")

    ax1.set_title("Clean dark spread vs EUA — 60d", fontsize=13, fontweight="bold")
    _format_date_axis(ax1)

    fig.tight_layout()
    path = str(config.CHARTS_DIR / "spread_regime.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")
    return path


def gas_fundamentals_chart(metrics_dict: dict, df: pd.DataFrame) -> str:
    """
    Chart 2 — Gas tightness dashboard: TTF + rolling stats, storage vs 5yr avg.
    Returns path to saved PNG.
    """
    ttf = df["TTF"].iloc[-60:]
    storage = df["Storage_Fill"].iloc[-60:]

    rolling_mean = df["TTF"].rolling(30).mean().iloc[-60:]
    rolling_std = df["TTF"].rolling(30).std().iloc[-60:]

    # 5-year seasonal average approximation
    day_of_year = storage.index.dayofyear
    five_yr_avg = 55 + 35 * np.sin(2 * np.pi * (day_of_year - 80) / 365)

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # --- Top: TTF + rolling mean + ±1σ band ---
    ax_top.plot(ttf.index, ttf.values, color="#2E86AB", linewidth=1.5,
                label="TTF front-month")
    ax_top.plot(rolling_mean.index, rolling_mean.values, color="#A23B72",
                linewidth=1.2, label="30d rolling mean")
    ax_top.fill_between(
        rolling_mean.index,
        (rolling_mean - rolling_std).values,
        (rolling_mean + rolling_std).values,
        alpha=0.15, color="#A23B72", label="±1σ band",
    )
    ax_top.set_ylabel("TTF (EUR/MWh)")
    ax_top.legend(loc="upper left", fontsize=8, frameon=False)
    ax_top.set_title("Gas fundamentals — TTF & storage", fontsize=13, fontweight="bold")

    # --- Bottom: Storage fill vs 5yr avg ---
    ax_bot.plot(storage.index, storage.values, color="#2E86AB", linewidth=1.5,
                label="EU storage fill %")
    ax_bot.plot(storage.index, five_yr_avg, color="grey", linewidth=1.2,
                linestyle="--", label="5yr seasonal avg (approx)")
    ax_bot.set_ylabel("Storage fill (%)")
    ax_bot.legend(loc="upper left", fontsize=8, frameon=False)
    _format_date_axis(ax_bot)

    fig.tight_layout()
    path = str(config.CHARTS_DIR / "gas_fundamentals.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")
    return path


def generate_charts(metrics_dict: dict, df: pd.DataFrame) -> list[str]:
    """Generate all charts and return list of file paths."""
    print("Generating charts …")
    paths = [
        spread_regime_chart(metrics_dict, df),
        gas_fundamentals_chart(metrics_dict, df),
    ]
    return paths
