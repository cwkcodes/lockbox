"""
Project 1 — GB Power Market Dashboard
=====================================

Pulls GB electricity market data from the Elexon BMRS (Insights) API and computes the
commercial quantities that matter: capture prices, cannibalisation, peak/off-peak spreads
and battery arbitrage value.

Data source
-----------
Elexon Insights Solution API (BMRS).  Base: https://data.elexon.co.uk/bmrs/api/v1
Most endpoints are open; register a free account at https://www.elexon.co.uk/ for
higher rate limits and for endpoints that require a key.

Design note
-----------
Every function that touches the network degrades to clearly-labelled SYNTHETIC data if
the API is unreachable, so the analysis and charts are always reproducible.  Synthetic
data is flagged in the returned DataFrame's ``.attrs['source']`` and in every chart
title.  Never present synthetic output as real market data.

Units
-----
Prices  £/MWh
Volumes MW (instantaneous) or MWh per settlement period (half-hourly, so MWh = MW / 2)
Periods GB settlement periods, 48 per day (50 or 46 on clock-change days)
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd
import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
TIMEOUT = 30
SETTLEMENT_PERIODS_PER_DAY = 48
HOURS_PER_PERIOD = 0.5

# GB peak definition used by most PPA and trading desks: 07:00-19:00 local, weekdays.
PEAK_START_HOUR, PEAK_END_HOUR = 7, 19


# --------------------------------------------------------------------------- #
# Data acquisition
# --------------------------------------------------------------------------- #

def _get(endpoint: str, params: dict | None = None) -> dict | None:
    """GET an Elexon endpoint, returning None on any failure rather than raising."""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"  ! Elexon request failed ({endpoint}): {exc}")
        return None


def _chunked_dates(start: dt.date, end: dt.date, days: int):
    """Yield (from, to) windows. Elexon rejects long ranges with HTTP 400."""
    cursor = start
    while cursor < end:
        stop = min(cursor + dt.timedelta(days=days), end)
        yield cursor, stop
        cursor = stop


def fetch_day_ahead_prices(start: dt.date, end: dt.date) -> pd.DataFrame:
    """
    Day-ahead (MID — Market Index Data) prices by settlement period, £/MWh.

    Default provider APXMIDP is the N2EX/Nord Pool day-ahead index, the reference
    most GB PPAs and route-to-market contracts settle against.  Requests are chunked
    because the API rejects ranges longer than roughly a week.

    Falls back to clearly-labelled synthetic data if the API is unavailable.
    """
    collected = []
    for window_start, window_end in _chunked_dates(start, end, days=7):
        payload = _get(
            "/datasets/MID",
            {
                "from": window_start.isoformat(),
                "to": window_end.isoformat(),
                "format": "json",
            },
        )
        if payload and payload.get("data"):
            collected.extend(payload["data"])

    if not collected:
        return _synthetic_prices(start, end)

    frame = pd.DataFrame(collected)
    frame = frame[frame["dataProvider"] == "APXMIDP"]
    frame["timestamp"] = pd.to_datetime(frame["startTime"]).dt.tz_localize(None)
    frame = (
        frame[["timestamp", "price", "volume"]]
        .drop_duplicates(subset="timestamp")
        .set_index("timestamp")
        .sort_index()
    )
    frame.attrs["source"] = "Elexon BMRS dataset MID (APXMIDP) — real market data"
    return frame


def fetch_generation_by_fuel(start: dt.date, end: dt.date) -> pd.DataFrame:
    """
    Actual generation by fuel type, resampled to half-hourly means in MW.

    Wide format: one column per PSR type (Wind Onshore, Wind Offshore, Solar,
    Nuclear, Fossil Gas, ...).
    """
    collected = []
    for window_start, window_end in _chunked_dates(start, end, days=7):
        payload = _get(
            "/generation/actual/per-type",
            {
                "from": window_start.isoformat(),
                "to": window_end.isoformat(),
                "format": "json",
            },
        )
        if payload and payload.get("data"):
            collected.extend(payload["data"])

    if not collected:
        return _synthetic_generation(start, end)

    rows = []
    for record in collected:
        timestamp = record.get("startTime")
        for entry in record.get("data", []):
            rows.append(
                {
                    "timestamp": timestamp,
                    "fuel": entry.get("psrType"),
                    "mw": entry.get("quantity"),
                }
            )

    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"]).dt.tz_localize(None)
    wide = (
        frame.pivot_table(index="timestamp", columns="fuel", values="mw", aggfunc="mean")
        .resample("30min")
        .mean()
    )
    # Combine on/offshore wind into a single tradable "Wind" view
    wind_columns = [c for c in wide.columns if "Wind" in c]
    if wind_columns:
        wide["Wind"] = wide[wind_columns].sum(axis=1)
    wide.attrs["source"] = "Elexon BMRS — actual generation per type, real"
    return wide


# --------------------------------------------------------------------------- #
# Synthetic fallbacks — ALWAYS labelled
# --------------------------------------------------------------------------- #

def _half_hourly_index(start: dt.date, end: dt.date) -> pd.DatetimeIndex:
    return pd.date_range(start, end, freq="30min", inclusive="left")


def _synthetic_prices(start: dt.date, end: dt.date) -> pd.DataFrame:
    """
    ILLUSTRATIVE ONLY.  A plausible GB price shape for testing the analysis chain.

    Structure: a flat base, a twin-peaked diurnal shape (morning and evening ramps),
    a weekday/weekend adjustment, and lognormal-ish noise with occasional spikes.
    Calibrated loosely to GB conditions; NOT a forecast and NOT market data.
    """
    index = _half_hourly_index(start, end)
    rng = np.random.default_rng(42)

    hour = index.hour + index.minute / 60
    diurnal = 18 * np.exp(-0.5 * ((hour - 8.0) / 2.0) ** 2)
    diurnal += 30 * np.exp(-0.5 * ((hour - 18.0) / 2.0) ** 2)
    weekend = np.where(index.dayofweek >= 5, -8.0, 0.0)
    noise = rng.normal(0, 12, len(index))
    spikes = rng.random(len(index)) > 0.995

    price = 70 + diurnal + weekend + noise + spikes * rng.uniform(80, 250, len(index))

    frame = pd.DataFrame({"price": price}, index=index)
    frame.index.name = "timestamp"
    frame.attrs["source"] = "SYNTHETIC — illustrative only, not market data"
    return frame


def _synthetic_generation(start: dt.date, end: dt.date) -> pd.DataFrame:
    """ILLUSTRATIVE ONLY. Plausible wind/solar/gas/nuclear shapes in MW."""
    index = _half_hourly_index(start, end)
    rng = np.random.default_rng(7)
    hour = index.hour + index.minute / 60
    n = len(index)

    # Wind: slow-moving autoregressive process, 1-18 GW
    shocks = rng.normal(0, 1, n)
    wind_walk = pd.Series(shocks).ewm(halflife=48).mean().to_numpy()
    wind = np.clip(9000 + wind_walk * 9000, 500, 18000)

    # Solar: daylight-only bell curve, seasonally scaled
    solar = np.clip(11000 * np.exp(-0.5 * ((hour - 13.0) / 3.0) ** 2), 0, None)
    solar *= (index.dayofyear.to_numpy() / 365 * np.pi).clip(0.15, 1.0)

    nuclear = np.full(n, 4200.0) + rng.normal(0, 90, n)
    demand = 30000 + 7000 * np.exp(-0.5 * ((hour - 18.0) / 3.5) ** 2)
    gas = np.clip(demand - wind - solar - nuclear, 500, None)

    frame = pd.DataFrame(
        {"Wind": wind, "Solar": solar, "Nuclear": nuclear, "Fossil Gas": gas},
        index=index,
    )
    frame.index.name = "timestamp"
    frame.attrs["source"] = "SYNTHETIC — illustrative only, not market data"
    return frame


# --------------------------------------------------------------------------- #
# Commercial analysis
# --------------------------------------------------------------------------- #

def capture_price(prices: pd.Series, volumes: pd.Series) -> float:
    """
    Volume-weighted average price achieved by an asset, £/MWh.

        capture price = Σ(pᵢ · vᵢ) / Σ(vᵢ)

    This is the single most important renewable revenue metric.  It is NOT the average
    price: an asset that generates disproportionately in low-price hours captures less
    than baseload, and the gap widens as more correlated capacity connects
    (cannibalisation).
    """
    aligned = pd.concat([prices, volumes], axis=1).dropna()
    if aligned.empty or aligned.iloc[:, 1].sum() == 0:
        return float("nan")
    return float((aligned.iloc[:, 0] * aligned.iloc[:, 1]).sum() / aligned.iloc[:, 1].sum())


def capture_rate(prices: pd.Series, volumes: pd.Series) -> float:
    """Capture price as a fraction of the simple (baseload) mean price.

    < 1.0 means the asset is being cannibalised.  Wind and solar sit below 1;
    dispatchable and storage assets can exceed it.
    """
    baseload = prices.mean()
    if baseload == 0 or np.isnan(baseload):
        return float("nan")
    return capture_price(prices, volumes) / baseload


def peak_offpeak_spread(prices: pd.Series) -> dict[str, float]:
    """Mean peak, off-peak and spread, £/MWh. Peak = 07:00-19:00, weekdays."""
    is_weekday = prices.index.dayofweek < 5
    in_hours = (prices.index.hour >= PEAK_START_HOUR) & (prices.index.hour < PEAK_END_HOUR)
    peak_mask = is_weekday & in_hours

    peak = float(prices[peak_mask].mean())
    offpeak = float(prices[~peak_mask].mean())
    return {"peak": peak, "offpeak": offpeak, "spread": peak - offpeak}


@dataclass
class BatterySpec:
    """Simple two-cycle battery. Extend in Project 3 with degradation and augmentation."""

    power_mw: float = 50.0
    duration_h: float = 2.0
    round_trip_efficiency: float = 0.85

    @property
    def energy_mwh(self) -> float:
        return self.power_mw * self.duration_h


def daily_arbitrage_value(prices: pd.Series, battery: BatterySpec) -> pd.DataFrame:
    """
    Perfect-foresight daily arbitrage value — the theoretical MAXIMUM, not achievable.

    Method: within each day, charge over the N cheapest settlement periods and discharge
    over the N most expensive, where N is the periods needed to fill the battery.

        margin = Σ(discharge prices) · E · η_rt − Σ(charge prices) · E

    Why perfect foresight matters commercially: real optimisers achieve roughly 60-85%
    of this, depending on forecast quality and how much capacity is held back for the
    Balancing Mechanism.  Quoting the perfect-foresight number as achievable revenue is
    a classic and expensive modelling error — this function returns the ceiling so you
    can apply a realistic haircut explicitly.
    """
    periods_needed = max(1, int(round(battery.duration_h / HOURS_PER_PERIOD)))
    energy_per_period = battery.power_mw * HOURS_PER_PERIOD

    results = []
    for day, group in prices.groupby(prices.index.date):
        if len(group) < periods_needed * 2:
            continue
        ordered = group.sort_values()
        charge_cost = ordered.iloc[:periods_needed].sum() * energy_per_period
        discharge_revenue = (
            ordered.iloc[-periods_needed:].sum()
            * energy_per_period
            * battery.round_trip_efficiency
        )
        results.append(
            {
                "date": day,
                "charge_cost": charge_cost,
                "discharge_revenue": discharge_revenue,
                "margin": discharge_revenue - charge_cost,
            }
        )

    frame = pd.DataFrame(results)
    if not frame.empty:
        frame = frame.set_index("date")
    return frame


def annualised_arbitrage(prices: pd.Series, battery: BatterySpec) -> float:
    """Perfect-foresight arbitrage, £/MW/year. Compare against Modo Energy benchmarks."""
    daily = daily_arbitrage_value(prices, battery)
    if daily.empty:
        return float("nan")
    return float(daily["margin"].mean() * 365 / battery.power_mw)


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def validate(prices: pd.DataFrame, generation: pd.DataFrame) -> list[str]:
    """Run the checks any reviewer would run. Returns a list of warnings."""
    warnings: list[str] = []

    if prices.empty:
        warnings.append("CRITICAL: price series is empty")
    else:
        expected = len(pd.date_range(prices.index.min(), prices.index.max(), freq="30min"))
        missing = expected - len(prices)
        if missing > 0:
            warnings.append(f"{missing} missing settlement periods ({missing / expected:.1%})")
        if prices["price"].isna().any():
            warnings.append(f"{int(prices['price'].isna().sum())} NaN prices")
        negative = int((prices["price"] < 0).sum())
        if negative:
            warnings.append(
                f"{negative} negative prices ({negative / len(prices):.2%}) — "
                "expected in GB during high-renewable, low-demand periods, not an error"
            )

    if not generation.empty and (generation < 0).any().any():
        warnings.append("negative generation values present — check sign convention")

    for label, frame in (("prices", prices), ("generation", generation)):
        source = frame.attrs.get("source", "unknown")
        if "SYNTHETIC" in source:
            warnings.append(f"{label}: SYNTHETIC DATA — illustrative only, do not publish")

    return warnings


# --------------------------------------------------------------------------- #

def main() -> None:
    end = dt.date.today()
    start = end - dt.timedelta(days=30)
    print(f"GB Power Market Dashboard — {start} to {end}\n")

    prices = fetch_day_ahead_prices(start, end)
    generation = fetch_generation_by_fuel(start, end)

    print(f"Price source      : {prices.attrs.get('source')}")
    print(f"Generation source : {generation.attrs.get('source')}\n")

    for warning in validate(prices, generation):
        print(f"  [check] {warning}")

    series = prices["price"]
    spread = peak_offpeak_spread(series)

    print(f"\nBaseload mean     : £{series.mean():.2f}/MWh")
    print(f"Peak / off-peak   : £{spread['peak']:.2f} / £{spread['offpeak']:.2f}")
    print(f"Peak spread       : £{spread['spread']:.2f}/MWh")

    for fuel in ("Wind", "Solar"):
        if fuel in generation.columns:
            aligned = generation[fuel].reindex(series.index).ffill()
            print(
                f"{fuel + ' capture':<18}: £{capture_price(series, aligned):.2f}/MWh "
                f"(capture rate {capture_rate(series, aligned):.1%})"
            )

    battery = BatterySpec()
    value = annualised_arbitrage(series, battery)
    print(
        f"\nBESS arbitrage    : £{value:,.0f}/MW/yr "
        f"({battery.duration_h:g}h, {battery.round_trip_efficiency:.0%} RTE, "
        "PERFECT FORESIGHT — apply a 60-85% haircut for realistic dispatch)"
    )
    print(
        "Benchmark         : 2h GB BESS averaged £73,145/MW/yr over the 12 months to "
        "April 2026 across the FULL revenue stack (Modo Energy)"
    )


if __name__ == "__main__":
    main()
