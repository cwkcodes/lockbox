"""
Project 1 — chart layer.

Every chart carries a title, labelled axes with units, a legend where needed, and a
stated data source with its period.  Charts built on synthetic data say so in the
title.  Run ``python charts.py`` to regenerate all figures into ./figures/.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from gb_power import (
    BatterySpec,
    annualised_arbitrage,
    capture_price,
    capture_rate,
    daily_arbitrage_value,
    fetch_day_ahead_prices,
    fetch_generation_by_fuel,
    peak_offpeak_spread,
)

FIGURES = Path(__file__).parent / "figures"
INK = "#1a1a1a"
GRID = "#d8d8d8"
PALETTE = {
    "price": "#2b6cb0",
    "wind": "#2f855a",
    "solar": "#d69e2e",
    "gas": "#c05621",
    "nuclear": "#6b46c1",
    "baseload": "#718096",
}


def _style(ax, title: str, xlabel: str, ylabel: str, source: str) -> None:
    ax.set_title(title, fontsize=12, fontweight="bold", color=INK, loc="left", pad=12)
    ax.set_xlabel(xlabel, fontsize=9, color=INK)
    ax.set_ylabel(ylabel, fontsize=9, color=INK)
    ax.grid(True, alpha=0.35, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.figure.text(0.01, 0.01, f"Source: {source}", fontsize=7, color="#666", ha="left")


def chart_price_duration(prices, source: str) -> Path:
    """
    Price duration curve — prices sorted high to low.

    Reads like a load duration curve.  The steep left tail is where flexible assets
    make their money; the portion below zero is where inflexible generation pays to
    run.  The shape, not the average, determines a battery's value.
    """
    series = prices["price"].sort_values(ascending=False).reset_index(drop=True)
    pct = series.index / len(series) * 100

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(pct, series.values, color=PALETTE["price"], linewidth=1.8)
    ax.axhline(0, color="#c53030", linestyle="--", linewidth=1)
    ax.axhline(
        series.mean(), color=PALETTE["baseload"], linestyle=":", linewidth=1.4,
        label=f"Baseload mean £{series.mean():.2f}/MWh",
    )
    ax.fill_between(pct, series.values, 0, where=(series.values < 0),
                    color="#c53030", alpha=0.3, label="Negative prices")
    ax.legend(fontsize=8, frameon=False)
    _style(
        ax,
        "GB day-ahead price duration curve",
        "Percentage of settlement periods (%)",
        "Day-ahead price (£/MWh)",
        source,
    )
    fig.tight_layout()
    path = FIGURES / "price_duration_curve.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def chart_intraday_shape(prices, source: str) -> Path:
    """
    Average price by time of day — the single most commercially loaded chart in GB.

    A twin-peaked shape (morning and evening ramps) is the classic pattern.  A flattened
    or inverted midday trough is solar cannibalisation, and it directly determines solar
    capture rates and battery cycling strategy.
    """
    series = prices["price"]
    by_hour = series.groupby(series.index.hour).agg(["mean", "min", "max"])

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(by_hour.index, by_hour["mean"], color=PALETTE["price"], linewidth=2.2,
            marker="o", markersize=4, label="Mean")
    ax.fill_between(by_hour.index, by_hour["min"], by_hour["max"],
                    color=PALETTE["price"], alpha=0.15, label="Min-max range")
    ax.axhline(series.mean(), color=PALETTE["baseload"], linestyle=":", linewidth=1.4,
               label=f"Period baseload £{series.mean():.2f}/MWh")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(fontsize=8, frameon=False)
    _style(
        ax,
        "GB day-ahead price by hour of day",
        "Hour of day (UTC)",
        "Day-ahead price (£/MWh)",
        source,
    )
    fig.tight_layout()
    path = FIGURES / "intraday_shape.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def chart_capture_rates(prices, generation, source: str) -> Path:
    """
    Capture rate by technology — the cannibalisation chart.

    Capture rate = capture price / baseload price.  Below 1.0 means the technology
    earns less than the average market price because it generates when prices are low.
    This single ratio is worth more in a revenue model than any LCOE figure.
    """
    series = prices["price"]
    technologies, rates, captures = [], [], []

    for fuel, colour_key in (("Wind", "wind"), ("Solar", "solar"),
                             ("Nuclear", "nuclear"), ("Fossil Gas", "gas")):
        if fuel in generation.columns:
            volumes = generation[fuel].reindex(series.index).ffill()
            rate = capture_rate(series, volumes)
            if rate == rate:  # not NaN
                technologies.append(fuel)
                rates.append(rate)
                captures.append(capture_price(series, volumes))

    fig, ax = plt.subplots(figsize=(9, 5))
    colours = [PALETTE.get(t.split()[0].lower(), PALETTE["price"]) for t in technologies]
    bars = ax.bar(technologies, rates, color=colours, width=0.55)
    ax.axhline(1.0, color=INK, linestyle="--", linewidth=1.2,
               label="Baseload (capture rate = 1.0)")

    for bar, rate, capture in zip(bars, rates, captures):
        ax.text(bar.get_x() + bar.get_width() / 2, rate + 0.015,
                f"{rate:.1%}\n£{capture:.0f}/MWh", ha="center", fontsize=8.5, color=INK)

    ax.set_ylim(0, max(rates + [1.0]) * 1.25)
    ax.legend(fontsize=8, frameon=False)
    _style(
        ax,
        "Capture rate by technology — evidence of cannibalisation",
        "Technology",
        "Capture rate (capture price ÷ baseload price)",
        source,
    )
    fig.tight_layout()
    path = FIGURES / "capture_rates.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def chart_battery_duration_sensitivity(prices, source: str) -> Path:
    """
    Perfect-foresight arbitrage against battery duration.

    The curve is concave: each additional hour of duration adds less value than the
    last, because the fifth-cheapest and fifth-most-expensive periods are closer
    together than the first.  This concavity is *why* the GB market built 1-2h systems
    first, and why longer duration only becomes attractive when the price distribution
    widens.  Compare the shape against Modo Energy's published duration curves.
    """
    durations = [0.5, 1, 1.5, 2, 3, 4, 6, 8]
    values = [
        annualised_arbitrage(prices["price"], BatterySpec(power_mw=50, duration_h=d))
        for d in durations
    ]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(durations, values, color=PALETTE["price"], linewidth=2.2, marker="o")
    for d, v in zip(durations, values):
        ax.annotate(f"£{v/1000:.0f}k", (d, v), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=8, color=INK)
    ax.legend(
        [f"50 MW, 85% round-trip efficiency\nPERFECT FORESIGHT — ceiling, not achievable"],
        fontsize=8, frameon=False, loc="lower right",
    )
    _style(
        ax,
        "Battery arbitrage value vs duration (wholesale only)",
        "Storage duration (hours)",
        "Perfect-foresight arbitrage (£/MW/year)",
        source,
    )
    fig.tight_layout()
    path = FIGURES / "battery_duration.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main() -> None:
    FIGURES.mkdir(exist_ok=True)
    end = dt.date.today()
    start = end - dt.timedelta(days=30)

    prices = fetch_day_ahead_prices(start, end)
    generation = fetch_generation_by_fuel(start, end)

    source = (
        f"{prices.attrs.get('source', 'unknown')} · "
        f"{start.isoformat()} to {end.isoformat()} · GB · half-hourly"
    )

    paths = [
        chart_price_duration(prices, source),
        chart_intraday_shape(prices, source),
        chart_capture_rates(prices, generation, source),
        chart_battery_duration_sensitivity(prices, source),
    ]
    for path in paths:
        print(f"  wrote {path.relative_to(Path(__file__).parent)}")

    spread = peak_offpeak_spread(prices["price"])
    print(f"\n  peak/off-peak spread: £{spread['spread']:.2f}/MWh")


if __name__ == "__main__":
    main()
