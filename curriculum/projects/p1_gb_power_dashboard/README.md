# Project 1 — GB Power Market Dashboard

**Status:** working, pulling live Elexon BMRS data.
**Learning objective:** stop treating "the power price" as one number. Learn to read the
*shape* of GB prices and convert that shape into asset revenue.

---

## Why this is the first project

Every energy revenue model you will ever build rests on an assumed power price. Almost
every bad energy model rests on a *flat* assumed power price. This project makes the
consequences of that assumption impossible to ignore, using real data.

It is also the fastest credible portfolio artefact: a public repo pulling live market data
and computing capture rates is a better opening line with an infrastructure investor than
any certificate.

---

## Quick start

```bash
pip install pandas numpy requests matplotlib
python gb_power.py     # analysis to stdout
python charts.py       # writes figures/ (4 charts)
```

No API key is required for the endpoints used. Register free at
[elexon.co.uk](https://www.elexon.co.uk/) for higher rate limits.
If the API is unreachable, both scripts fall back to **clearly labelled synthetic data** so
the analysis chain always runs — synthetic output is flagged in `.attrs['source']`, in the
validation warnings and in every chart title. **Never present it as market data.**

---

## Data

| Item | Value |
|---|---|
| Provider | Elexon Insights (BMRS), `https://data.elexon.co.uk/bmrs/api/v1` |
| Datasets | `MID` (Market Index Data, provider `APXMIDP` = N2EX day-ahead); `/generation/actual/per-type` |
| Geography | Great Britain |
| Resolution | Half-hourly settlement periods (48/day) |
| Units | Prices £/MWh; generation MW |
| Range limit | The API rejects long windows — requests are chunked into 7-day blocks |
| Cleaning | On/offshore wind summed into `Wind`; duplicates dropped on timestamp; timezone stripped to naive UTC |

---

## What the first run found — 26 July to 25 August 2026

Real data, retrieved 25 August 2026. Reproduce with `python gb_power.py`.

| Metric | Value |
|---|---|
| Baseload mean | **£123.00/MWh** |
| Peak mean (07:00–19:00 weekdays) | £122.29/MWh |
| Off-peak mean | £123.38/MWh |
| **Peak/off-peak spread** | **−£1.09/MWh** |
| Wind capture price | £115.57/MWh (**capture rate 94.0%**) |
| Solar capture price | £100.69/MWh (**capture rate 81.9%**) |
| Negative price periods | 28 (1.94%) |
| 2h BESS perfect-foresight arbitrage | £47,176/MW/yr |

### The finding worth understanding

**The peak/off-peak spread is negative.** A conventional PPA structured on a 07:00–19:00
peak definition would have been priced *below* off-peak power over this period.

The cause is visible in `figures/intraday_shape.png`: GB summer solar has carved a midday
trough down to **~£88/MWh at 10:00–13:00**, while the evening ramp peaks at **~£164/MWh at
18:00**. The traditional peak window contains the solar trough; the off-peak window contains
the evening peak. **The definition has become obsolete faster than the contracts using it.**

**Commercial consequences — this is the part to internalise:**

1. **Peak/off-peak PPA structures are mispriced** relative to the shape they are meant to
   capture. Anyone still quoting a "peak" premium in GB summer is quoting yesterday's market.
2. **Solar's 81.9% capture rate is cannibalisation, measured, not theorised.** Solar earns
   18% less than baseload because it generates into the trough it creates. Apply a flat
   baseload price to solar volume and you overstate revenue by ~18% *before* any curtailment.
3. **Wind at 94.0% is materially better than solar** over this window — but this is a summer
   month; run it over a winter period and compare. Seasonality in capture rates is itself a
   modelling insight.
4. **The evening ramp from £88 to £164 in six hours is the battery's revenue.** That
   £76/MWh spread, not the £123 average, is what a BESS monetises.

**Limitation to state honestly:** 30 days is a short window and a seasonally atypical one.
Do not generalise these capture rates to an annual model. Re-run over 12 months before using
any figure here in a valuation. The code supports it; the API chunking handles it.

---

## Charts produced

| File | What it shows | What to learn from it |
|---|---|---|
| `intraday_shape.png` | Mean price by hour with min–max range | The duck curve; where the battery earns; why peak definitions are stale |
| `price_duration_curve.png` | Prices sorted high to low | The tails matter more than the mean; negative price share |
| `capture_rates.png` | Capture rate by technology vs baseload | Cannibalisation, quantified per technology |
| `battery_duration.png` | Arbitrage value vs storage duration | Concavity — why GB built 1–2h systems first |

---

## Validation checks implemented

Missing settlement periods · NaN prices · negative price count (expected, not an error —
flagged so it is not silently treated as a bug) · negative generation (sign convention) ·
synthetic-data flag. Run `validate()` before trusting any output.

---

## Common errors this project exists to prevent

1. Using baseload price for renewable revenue — **the most expensive routine error in the
   industry**.
2. Quoting perfect-foresight arbitrage as achievable battery revenue. Real optimisers reach
   roughly 60–85% of it. The function returns the ceiling deliberately so the haircut is
   explicit rather than hidden.
3. Ignoring negative prices, or treating them as data errors.
4. Comparing a wholesale-only arbitrage figure against Modo's full-stack benchmark. The
   £47k/MW/yr here is **wholesale arbitrage only**; Modo's £73,145/MW/yr for 2h GB BESS
   (12 months to April 2026) includes the Balancing Mechanism, ancillary services and
   capacity payments. Comparing them directly is not like-for-like.
5. Timezone errors — GB settlement is in UTC but clock-change days have 46 or 50 periods.

---

## Extensions — in order of value

1. **Run over 12 months** and chart capture rates by month. Seasonality is the finding.
2. Add **imbalance prices** (`/balancing/settlement/system-prices`) and compute the cost of
   a forecast error — this is the bridge to route-to-market economics.
3. Add **gas (NBP) and carbon (UKA)** prices and compute a live **clean spark spread**;
   overlay the dispatch threshold on the price duration curve.
4. Add **constraint/curtailment indicators** (`/datasets/DISBSAD`, bid-offer acceptances with
   the SO flag) — the closest public proxy for constraint cost, and directly relevant to
   Scottish wind valuation.
5. Add **interconnector flows** and test whether GB prices follow or lead the continent.
6. Rebuild as a Streamlit app with date-range, technology and battery-spec controls.

---

## Marking rubric

| Grade | Criteria |
|---|---|
| **Fail** | Runs but uses only synthetic data; no validation; charts unlabelled |
| **Pass** | Live data; capture rates computed; charts labelled with sources and units |
| **Good** | Adds imbalance or spark spread; 12-month range; limitations stated explicitly |
| **Excellent** | All of the above plus a written 2-page market note interpreting the findings commercially, with a defensible view on what it means for a specific asset's valuation |

**What an employer looks for:** not the code. They look for whether your README shows you
know what the numbers *mean* — specifically whether you noticed the capture-rate gap and
could explain its consequence for a revenue model without being prompted.
