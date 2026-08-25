# Part 4 — Calculation Syllabus

The 50 calculations you must be able to do from a blank sheet. This is the spine of
technical credibility: in an interview or an investment committee, the person who can
compute the number in their head sets the terms of the discussion.

**Format for each:** variables · units · logic · numerical example · Excel · Python ·
common errors · how it drives a decision. Worked examples are delivered inside the module
that owns each calculation; this file is the master index, ordered by learning sequence,
with the four foundation calculations worked in full here.

---

## Mastery ladder

| Tier | Calculations | Standard | Module |
|---|---|---|---|
| **1 — Foundation** | 1–10 | From memory, no reference | A1–A4 |
| **2 — Market** | 11–22 | From memory | B, F, O |
| **3 — Finance** | 23–36 | From blank workbook | Q, R |
| **4 — Asset-specific** | 37–46 | With reference | D–N |
| **5 — Trading** | 47–50 | With reference | P |

---

## Tier 1 — Foundation *(worked in Module A1)*

| # | Calculation | Formula | Trap |
|---|---|---|---|
| 1 | Energy ↔ power | E = P × t | Rate vs quantity |
| 2 | Fuel-energy conversion | See A1 §6.2 | HHV vs LHV |
| 3 | Heat rate | HR = 3412.14/η (Btu/kWh) | Basis mismatch |
| 4 | Capacity factor | CF = E/(P×8760) | ≠ availability |
| 5 | Availability | Uptime / period | Contract definition varies |
| 6 | Generation marginal cost | fuel/η + (EF/η)×carbon + VOM | Omitting carbon |
| 7 | Annuity factor | (1−(1+r)⁻ⁿ)/r | — |
| 8 | **LCOE** | PV(costs)/PV(energy) | **Not discounting energy** |
| 9 | Grid losses | Applied at each voltage level | Compounding, not adding |
| 10 | P50/P90 | P90 = P50 × (1 − z·σ) | Which uncertainty is included |

### Worked: #10 — P50 and P90

Your existing skill, restated in the form lenders use.

**Logic.** Annual energy production is treated as approximately normal. P50 is the median.
P90 is the level exceeded with 90% probability — the **downside** case a lender sizes debt to.

**P90 = P50 × (1 − 1.2816 × σ)** where σ is the *combined* uncertainty as a fraction of P50.

**[CALC]** P50 = 140,160 MWh, combined uncertainty σ = 12%:
P90 = 140,160 × (1 − 1.2816 × 0.12) = 140,160 × 0.84621 = **118,606 MWh**

That is 84.6% of P50 — a 15.4% haircut. **Commercial consequence:** debt is sized on 118,606
MWh, not 140,160. Every 1 percentage point of uncertainty reduction is worth roughly 1.28% of
debt capacity, which is why reducing measurement uncertainty has direct financial value —
and why sponsors pay for another year of met mast data.

**Excel:** `=P50*(1-NORM.S.INV(0.9)*sigma)` **Python:** `p50*(1-scipy.stats.norm.ppf(0.9)*sigma)`

**Common errors:** combining uncertainties by adding rather than in quadrature
(σ_total = √(Σσᵢ²)); confusing P90 of *annual* energy with P90 of *ten-year average* energy
(lenders use both, for different covenants); applying a P90 haircut to a price as well as
volume and double-counting conservatism.

**Note the distinction that catches people out:** P90 one-year and P90 ten-year are different
numbers because inter-annual variability averages out over time. Lenders test debt service
against the one-year P90 and overall repayment against the ten-year.

---

## Tier 2 — Market *(Modules B, F, O)*

| # | Calculation | Formula | Trap |
|---|---|---|---|
| 11 | **Capture price** | Σ(pᵢvᵢ)/Σvᵢ | Using simple mean |
| 12 | Capture rate | capture ÷ baseload | Period-dependent |
| 13 | Cannibalisation | Capture rate decline vs penetration | Non-linear |
| 14 | Spark spread | power − gas/η | Basis |
| 15 | **Clean spark spread** | spark − (EF/η)×carbon | Omitting carbon |
| 16 | Dark spread | power − coal/η | Coal units (GJ vs t) |
| 17 | Crack spread | Σ(product×yield) − crude | 3:2:1 conventions |
| 18 | Peak/off-peak spread | mean(peak) − mean(offpeak) | **Definition now stale in GB** |
| 19 | Battery arbitrage | Σ(sell) − Σ(buy)/η_rt | Perfect foresight |
| 20 | Imbalance exposure | (vol − notified) × imbalance price | Sign convention |
| 21 | Curtailment | Lost MWh × capture price | Compensated or not? |
| 22 | Capacity payment | £/kW/yr × derated MW | **Derating factor** |

**#22 trap, worth stating:** capacity payments are on *derated* capacity, and derating
factors vary sharply by technology and duration — a 1h battery derates far below a 4h one.
GB's T-4 for 2029/30 cleared at £27.10/kW/yr [FACT]; a 50 MW 1h battery does not earn
50 × 27,100.

---

## Tier 3 — Finance *(Modules Q, R, S)* — the highest-value tier

| # | Calculation | Formula | Trap |
|---|---|---|---|
| 23 | NPV | Σ CFₜ/(1+r)ᵗ | Mid-year vs year-end convention |
| 24 | IRR | r where NPV = 0 | Multiple roots on sign changes |
| 25 | **WACC** | (E/V)kₑ + (D/V)k_d(1−t) | Using book not market weights |
| 26 | MOIC | Total distributions ÷ invested | Ignores time |
| 27 | Enterprise value | Equity + net debt + minorities − associates | Forgetting provisions/ARO |
| 28 | Equity value | EV − net debt | Debt-like items |
| 29 | **CFADS** | EBITDA − tax − Δworking capital − maintenance capex | **≠ EBITDA** |
| 30 | **DSCR** | CFADS ÷ (principal + interest) | Timing of the period |
| 31 | LLCR | PV(CFADS over loan life) ÷ debt outstanding | Discount rate choice |
| 32 | PLCR | PV(CFADS over project life) ÷ debt | Includes the tail |
| 33 | **Debt sculpting** | Debt service ₜ = CFADSₜ ÷ target DSCR | **Circularity with IDC** |
| 34 | Interest during construction | Compounded on drawn balance | Fee capitalisation |
| 35 | Tax depreciation | Capital allowances per regime | Accounting ≠ tax depreciation |
| 36 | LBO returns | Exit equity ÷ entry equity | Debt paydown vs multiple expansion |

### Worked: #30 and #33 — DSCR and sculpting *(previewed; full treatment in Module R)*

**DSCR = CFADS ÷ debt service.** A lender covenants a minimum — typically 1.20–1.35x for
contracted renewables, higher for merchant.

**[CALC]** CFADS £8.5m, debt service £6.8m → DSCR = 8.5/6.8 = **1.25x**. There is £1.7m of
headroom before the covenant breaches at 1.00x — a 20% fall in CFADS.

**Sculpting** reverses this. Rather than a fixed repayment schedule, you *derive* the
schedule so DSCR is constant:

**Debt serviceₜ = CFADSₜ ÷ target DSCR**

**[CALC]** CFADS £8.5m, target 1.30x → allowable debt service = 8.5/1.30 = **£6.538m**.
The maximum debt is the present value of that stream at the debt rate. Over 15 years at 6%:
AF = 9.712 → **maximum debt ≈ £63.5m**.

**Why this matters more than any other calculation in the programme:** it determines
leverage, leverage determines the equity cheque, and the equity cheque determines the return.
**Debt sizing is where value is created or destroyed in infrastructure — not in the energy
yield.** An engineer who can sculpt debt is a different professional from one who cannot.

**The circularity:** interest during construction depends on the drawn balance, which depends
on total debt, which depends on the sculpted profile, which depends on CFADS after
interest. Excel resolves this with iterative calculation enabled (File → Options → Formulas →
Enable iterative calculation) or with an explicit convergence macro. **Handling circularity
cleanly is a standard project-finance modelling test.**

---

## Tier 4 — Asset-specific *(Modules D–N)*

| # | Calculation | Module |
|---|---|---|
| 37 | LNG netback | H — destination − shipping − regas − liquefaction − feedgas |
| 38 | Shipping cost | H — charter + fuel + boil-off + canal |
| 39 | Gas storage value | H — intrinsic (spread) + extrinsic (optionality) |
| 40 | Battery degradation | E — cycle + calendar ageing, SOH trajectory |
| 41 | Oil-field decline | G — exponential, hyperbolic, harmonic |
| 42 | Oil-field breakeven | G — price where NPV10 = 0 |
| 43 | Reserve valuation | G — NPV10 of 2P |
| 44 | Mine economics | M — grade × recovery × price − costs |
| 45 | Electrolyser / H₂ LCOH | K — capex + power/efficiency, load-factor sensitive |
| 46 | Data-centre demand | N — IT load × PUE; annual MWh; connection sizing |

**#46 — the one to learn early**, because it is simple and immediately useful:
**Facility load (MW) = IT load (MW) × PUE**. Annual MWh = facility load × 8760 × utilisation.
A 100 MW IT load at PUE 1.25 draws 125 MW, or ~1,095 GWh/yr at full utilisation — roughly
0.4% of GB annual demand from *one* campus. That arithmetic is why data centres are
reshaping power markets.

---

## Tier 5 — Trading *(Module P)*

| # | Calculation | Note |
|---|---|---|
| 47 | Futures P&L | (exit − entry) × lots × contract size; watch tick value |
| 48 | Forward curve | Contango/backwardation; carry = storage + finance − convenience yield |
| 49 | Option payoff & delta hedge | max(S−K,0) − premium; hedge ratio = delta × position |
| 50 | VaR & stress testing | Parametric, historical, Monte Carlo — and why VaR fails in energy |

**#50 warning worth carrying:** VaR assumes a distribution that energy markets routinely
violate. Gas and power have fat tails and regime changes. **VaR is a risk-limit
administration tool, not a statement about worst-case loss.** Stress and scenario testing do
the real work. Anyone who quotes a 99% VaR as a maximum loss in an energy context has
misunderstood it.

---

## Common errors across all tiers

1. **Unit and basis mismatches** — HHV/LHV, MWth/MWe, $/€/£, real vs nominal.
2. **Real vs nominal confusion** — discounting nominal cash flows at a real rate is the single
   most common financial modelling error. Pick one and be consistent throughout.
3. **Discounting energy inconsistently** in LCOE.
4. **Flat price assumptions** for shaped generation — see Project 1's measured 81.9% solar
   capture rate.
5. **EBITDA used as CFADS** — ignores tax, working capital and maintenance capex.
6. **P50 for debt sizing** instead of P90.
7. **Circularity broken by hardcoding** rather than iterating.
8. **Perfect foresight** in storage optimisation quoted as achievable.
9. **Derated vs nameplate** capacity in capacity market revenue.
10. **Sign conventions** — imbalance, cash flow direction, short positions.

**Build a personal error log.** Every time you make one of these, record it. The log is
worth more than any textbook, because it is calibrated to your own failure modes.
