# Part 7 — Practical Portfolio Programme

Ten projects that demonstrate commercial and financial competence. **The portfolio is the
transition mechanism**, not the study. Nobody will hire you for completing modules; they will
hire you because you showed them a model and could defend every assumption in it.

## Order and rationale

| # | Project | Module | Time | Priority | Proves |
|---|---|---|---:|:---:|---|
| **1** | **GB power market dashboard** | B | 25h | ★★★ | You understand price formation and capture — **[BUILT]** |
| **2** | **Renewable project-finance model** | R, D | 60h | ★★★ | You can size and sculpt debt |
| **3** | **Battery investment & dispatch model** | E | 40h | ★★★ | Optimisation + investment case |
| **4** | CCGT commercial model | F | 30h | ★★ | Thermal economics and spreads |
| **9** | **Energy acquisition IC memorandum** | S | 35h | ★★★ | You can make a recommendation |
| **8** | Data-centre power strategy | N | 35h | ★★ | The differentiating intersection |
| 5 | LNG cargo netback model | H | 25h | ★ | Commodity optionality |
| 10 | Simulated trading book | P | 40h | ★ | Risk management literacy |
| 6 | Oil-field economics model | G | 25h | ○ | Decline curves and breakeven |
| 7 | Nuclear investment case | J | 30h | ○ | Construction and political risk |

★★★ = build these three first, in this order. They cover the recommended primary route
completely. **Projects 1, 2 and 9 together are a sufficient portfolio for an infrastructure
debt or fund technical role.** Everything else is optional depth.

---

## Project 1 — GB Power Market Dashboard ✅ BUILT

Specification, code, real results and marking rubric:
[`projects/p1_gb_power_dashboard/`](projects/p1_gb_power_dashboard/)

Already pulling live Elexon BMRS data and producing four charts. **First real finding:** GB
solar has driven the peak/off-peak spread negative (−£1.09/MWh over 26 Jul–25 Aug 2026), with
solar capturing 81.9% of baseload and wind 94.0%. See its README.

---

## Project 2 — Renewable Project-Finance Model ★ the centrepiece

**Learning objective:** build a bankable project-finance model from a blank workbook,
including sculpted debt, and defend every assumption.

**Why it matters most.** This is the artefact that changes how you are perceived. An engineer
who has built a sculpted-debt model with a working DSCR covenant is no longer an engineer who
"knows some finance"; they are a candidate.

**Structure** — separate worksheets, no exceptions:
`Cover` (version, author, purpose) · `Inputs` (every assumption, colour-coded, sourced) ·
`Timeline` (monthly construction, quarterly then semi-annual operations, with period flags) ·
`Construction` (capex drawdown, IDC, fees) · `Energy` (P50, P90, degradation, losses,
availability, curtailment) · `Revenue` (CfD/PPA, merchant tail with capture-rate curve, REGOs,
capacity) · `Opex` (fixed, variable, indexed) · `Tax` (capital allowances ≠ book depreciation)
· `Debt` (sizing, sculpting, DSCR, LLCR, reserve accounts, waterfall) · `Financials` (P&L, BS,
CF) · `Returns` (project IRR, equity IRR, NPV, MOIC, payback) · `Sensitivities` (tornado,
two-way tables) · `Checks` (all of them) · `Sources`.

**Required calculations:** #7, 8, 10, 23–25, 29–35 from `04-calculation-syllabus.md`.

**Required checks:** balance sheet balances · sources = uses · debt closing balance = 0 at
maturity · cash never negative · DSCR ≥ covenant in every period · P90 case still services
debt · no hardcodes inside formulas · circularity converges.

**Data sources.** CfD strike prices: [DESNZ AR7 results](https://assets.publishing.service.gov.uk/media/6966861de8c04eb2919f773a/contracts-for-difference-allocation-round-7-results-.pdf)
(£91/MWh offshore, 2024 prices, announced 14 Jan 2026 [FACT]) · capacity prices: T-4 2029/30
at £27.10/kW/yr [FACT] · capture rates: **from your own Project 1** · CAPEX: BEIS/DESNZ
Electricity Generation Costs, IRENA cost reports · debt terms: recent deal press releases,
Infrastructure Journal, IJGlobal.

**Expected outputs:** equity IRR, project IRR, minimum and average DSCR, LLCR, gearing
achieved, NPV at target WACC, a tornado chart of value drivers, and a P50/P90 comparison.

**Common errors:** real/nominal mixing · debt sized on P50 · flat merchant price instead of a
capture curve · tax depreciation = book depreciation · circularity hardcoded away · no
maintenance capex or decommissioning provision · ignoring the DSCR *lock-up* level (typically
above the default level, restricting distributions before it breaches).

**Presentation:** the workbook plus a **2-page investment summary**. The summary matters more
than the model — it proves you can communicate to a decision-maker.

**Rubric.** *Pass:* runs, checks pass, IRR calculated. *Good:* sculpted debt, P90 case,
sensitivities, sourced assumptions. *Excellent:* merchant tail with a capture-price curve
derived from your own Project 1 data, a defensible view on the discount rate applied to
merchant vs contracted cash flows, and a limitations section that pre-empts the questions a
credit committee would ask.

**What an employer looks for:** whether you sized debt on P90 and whether your merchant tail
is defensible. Those two things separate real models from exercises.

**Time:** 60 hours. Expect the first 20 to feel slow. Build it twice — the second build takes
a third of the time and is where the learning consolidates.

---

## Project 3 — Battery Investment and Dispatch Model

**Head start:** you already have `BESS_Model/` in this repository — a `Battery` class with
capacity, power limits, charge/discharge efficiency and depth-of-discharge limits, plus
half-hourly input data and site metadata. **This is a genuine asset almost no candidate has.**
Extend it rather than restarting.

**Extensions required, in order:**
1. **Degradation** — cycle-based and calendar ageing; track state of health; model augmentation
   capex in year 7–10.
2. **Degradation-aware optimisation** — penalise cycling by its marginal degradation cost.
   *This is the sophisticated bit and the thing worth talking about in interviews*, because it
   is where engineering and commercial optimisation genuinely meet.
3. **Revenue stacking** — wholesale arbitrage + Balancing Mechanism + ancillary services +
   capacity payments on **derated** capacity.
4. **Tolling vs merchant comparison** — same asset, two contract structures, different debt
   capacity. Show why the toll supports more leverage despite lower expected revenue.
5. **Investment case** — capex, opex, debt, DSCR, equity IRR, residual value.

**Benchmark honestly:** 2h GB BESS averaged £73,145/MW/yr over the 12 months to April 2026
across the full stack, with wholesale + BM around 60% [FACT: Modo Energy]. Monthly figures
ranged £41k–£70k/MW/yr in Q1 2026 alone. **If your model produces a smooth revenue line, it
is wrong.**

**Rubric excellence criterion:** the model demonstrates *why* merchant BESS is hard to finance
— by showing the P90 revenue case failing the DSCR covenant — and quantifies what a toll is
worth in additional debt capacity.

---

## Project 9 — Energy Acquisition Investment Memorandum ★ the closer

**Learning objective:** produce the document an investment committee actually reads.

**Why third in priority:** Projects 1 and 2 prove you can analyse. Project 9 proves you can
**decide**. That is the difference between an adviser and a principal, and it is the single
most valuable signal you can send.

**Subject:** use a real, publicly-documented transaction — an operating wind or solar
portfolio, or a BESS platform. Public sources: company announcements, Ofgem's renewables
register, planning portals, Companies House filings.

**Contents:** investment thesis (one page, the whole argument) · asset description · market
analysis · technical assessment (**your strength — make this genuinely better than a generalist
could write**) · commercial contracts · financial returns · debt structure · downside and
stress cases · key risks with mitigations · valuation with methodology · **clear
recommendation with conditions**.

**The discipline that makes it credible:** state what would change your mind. An IC memo that
only argues one side reads as advocacy, not analysis.

**Rubric excellence criterion:** a reader who disagrees with your recommendation can still
follow exactly how you reached it, and can identify which single assumption to attack.

---

## Projects 4, 5, 6, 7, 8, 10 — specifications

Full specifications are delivered with their owning modules. Summary of each:

**Project 4 — CCGT commercial model** (Module F, 30h). Heat rate, gas, carbon, VOM, start
costs, minimum stable generation, clean spark spread, dispatch stack, capacity payments,
asset valuation. *Key output:* hours-in-the-money per year and the resulting gross margin.
*Employer signal:* you understand thermal assets, which most renewables people do not.

**Project 5 — LNG cargo netback** (Module H, 25h). Feedgas, liquefaction fee, shipping,
boil-off, canal costs, regas, destination price, netback comparison, destination optionality
value. *Key output:* which destination is optimal at current TTF/JKM, and the freight rate at
which the answer flips.

**Project 6 — Oil-field economics** (Module G, 25h). Decline curve, reserves, price deck,
royalties, tax, capex, opex, decommissioning, NPV10, breakeven. *Key output:* breakeven
Brent price. *Priority: low for your routes.*

**Project 7 — Nuclear investment case** (Module J, 30h). Construction schedule with overrun
scenarios, capacity factor, 60-year life, CfD vs RAB support, debt, government support,
decommissioning fund. *Key output:* the required strike price under each support model, and
the sensitivity to construction delay. *Insight to demonstrate:* nuclear's risk is
construction and politics, not physics.

**Project 8 — Data-centre power strategy** (Module N, 35h). Grid supply vs on-site generation
vs batteries vs backup; PUE and cooling; reliability; carbon targets; connection constraints;
total cost of energy £/MWh delivered. *Key output:* a recommended procurement strategy for a
specific site with a defensible TCO. *This is your differentiator project* — see route 4.

**Project 10 — Simulated trading book** (Module P, 40h). Paper positions in power and gas
forwards and futures; a hedge against a physical position; mark-to-market; daily P&L
attribution; VaR; stress cases; documented risk limits and what happens when they breach.
*Key output:* a P&L attribution that explains *why* you made or lost money — decomposed into
directional, spread and basis effects. **Never trade real money for this.** The learning is
in the risk framework, not the positions.

---

## Universal standards for every project

**Structure:** inputs / calculations / outputs / sensitivities / charts / checks / sources /
assumptions / limitations — always separated, never mixed.

**Presentation:** every project ships with a README stating what it does, the data sources and
their dates, the assumptions, the limitations, and how to reproduce it. **The limitations
section is the most-read part** — it is where a reviewer decides whether you are honest.

**Publication:** public GitHub repository, clean commit history. Link it from your CV and
LinkedIn. **[OPINION]** Two excellent projects beat six mediocre ones, decisively. A reviewer
opens one thing.

**Validation before you claim completion:** every check passes · units consistent throughout ·
a colleague can run it from the README alone · you can defend every assumption without
looking anything up · you have written down what would change your conclusion.
