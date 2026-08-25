# Part 9 — Implementation Roadmap

Designed to be achievable alongside a full-time consultancy role. Every phase has a
**forcing decision point**, because the dominant failure mode identified in
`03-career-routes.md` §5 is drift, not difficulty.

---

## Study plans by weekly commitment

| | 5 hrs/week | 10 hrs/week | 15 hrs/week |
|---|---|---|---|
| **Weekday** | 2 × 45 min early morning | 3 × 1 hr early morning | 4 × 1.25 hr |
| **Weekend** | 1 × 2.5 hr block | 1 × 4 hr + 1 × 3 hr | 2 × 5 hr blocks |
| **90-day output** | Module A complete, Project 1 v1 | Groups A+B, Project 1 shipped | A+B+Q started, Projects 1 & 2 v1 |
| **12-month** | A, B, Q, R started; 2 projects | A, B, C, Q, R, E; 4 projects | A–F, Q, R, S; 6 projects |
| **To critical path (~340 hrs)** | ~16 months | **~8 months** | ~5.5 months |
| **To full 720 hrs** | ~3.5 years | **~2 years** | ~14 months |
| **Burnout risk** | Low | **Moderate — sustainable** | High alongside deadlines |

**[OPINION] Choose 10 hrs/week.** Five is too slow to build momentum before motivation
decays; fifteen collides with consultancy deadline weeks and produces a boom-bust pattern
that ends in abandonment. Ten survives a bad month.

**Protect the morning block.** Evening study after client work fails reliably. The single
highest-return scheduling decision is putting the hard modelling work before the working day,
not after it.

---

## The 30-day plan

**Theme: prove you will actually do this, and open the internal door.**

| Week | Study (10 hrs) | Action | Evidence produced |
|---|---|---|---|
| 1 | Module A1 §§1–7. Read `01-energy-system-map.md` twice. | **Book the conversation with your line manager about LTA/TDD staffing.** | A1 Excel workbook v1 |
| 2 | A1 §§8–22. Register for Elexon BMRS API key (free). | Request 2 recruiter salary guides. | `a1_units_lcoe.py` running |
| 3 | A1 quiz + §26 case. Start Module A2. | First BMRS data pull; explore the datasets. | Borders case note (2 pages) |
| 4 | A2 complete. Start Module B §§1–6. | 2 informational conversations booked. | Project 1 data pipeline skeleton |

**Day-30 decision point:** did you complete ≥30 of 40 planned hours, and did the internal
conversation happen? If both yes, continue. If the internal conversation did *not* happen,
that is the real finding — it means either the opportunity is not there (which changes the
route recommendation) or you avoided the conversation (which is the thing to fix).

---

## The 90-day plan — detail

**Theme: ship Project 1 and become visibly different at work.**

### Days 1–30 — Foundations (above)

### Days 31–60 — Market fluency

**Knowledge:** Module B §§1–12 — price formation, merit order, marginal pricing, day-ahead,
intraday, balancing mechanism, imbalance settlement, ancillary services, capacity market.
Module U basics — pandas time series, API handling, plotting conventions.

**Calculations to master:** capture price · cannibalisation ratio · imbalance exposure ·
spark and clean spark spread · capacity factor from half-hourly data · peak/off-peak spread.

**Reading:** Elexon's *Balancing and Settlement Code* guidance notes (the plain-English "BSC
in a nutshell" material, not the Code itself); NESO *Future Energy Scenarios* summary;
three Modo Energy monthly BESS research posts; Timera Energy blog archive on GB power.

**People:** 3 informational conversations — one LTA/technical adviser, one infrastructure
debt or PE professional, one BESS optimiser (Flexitricity and Habitat both recruit in
Edinburgh).

**Evidence:** Project 1 pulling live BMRS data and producing four working charts.

### Days 61–90 — Ship and position

**Knowledge:** Module B §§13–20 — route-to-market, PPAs, CfDs, tolling, capture price,
cannibalisation, shape/basis/profile/volume risk. Start Module Q (accounting) in parallel —
it is independent of B and uses different mental energy.

**Calculations:** LCOE from blank · NPV/IRR without a template · DSCR (introduce) · capture
rate from real half-hourly data.

**Courses:** book the project-finance modelling course to start in month 4. This is the one
paid course worth buying (see `02-curriculum-index.md`).

**Applications:** none yet. **Deliberately.** Applying before Project 1 exists wastes your
one chance at a first impression with each employer.

**Internal:** volunteer specifically for — technical due diligence, lender's technical
adviser mandates, revenue/yield assessment for a transaction, PPA review, grid risk
assessment. Say the words "I want transaction work" out loud to someone who staffs projects.

**Evidence at day 90:**
1. Project 1 shipped — public GitHub repo, README, live data, honest limitations section.
2. A1 + A2 deliverables committed.
3. LinkedIn repositioned (see `08-networking-and-positioning.md`).
4. 6+ informational conversations completed and logged.
5. At least one internal request made for transaction-adjacent work.

**Day-90 decision point:** *Has your work content changed at all?* If you have been staffed
on TDD/LTA work → the primary route is validated, continue as planned. If not, and the
conversation went nowhere → the internal bridge is closed, and the plan shifts towards an
external move at month 12–18. **Do not spend a year discovering this.**

---

## The 12-month plan

| Quarter | Modules | Projects | Career actions | Decision point |
|---|---|---|---|---|
| **Q1** (m1–3) | A, B (start), U | **P1 shipped** | Internal LTA request; 6 conversations; LinkedIn | Has work content changed? |
| **Q2** (m4–6) | B complete, Q, R starts. PF modelling course. | P2 started | 8 conversations; 2 industry events; recruiter relationships | Is project finance actually enjoyable? Honest answer required |
| **Q3** (m7–9) | R core, D | **P2 shipped** | First applications — targeted, ~5 not 50. CEng application if not held | Are you getting first-round interviews? If zero from 5 targeted applications, the positioning is wrong, not the market |
| **Q4** (m10–12) | C, E, capstone | **P3 shipped** (extends your existing BESS model) | Interviews; internal promotion conversation | **Stay-or-move decision** |

**12-month realistic outcome [ESTIMATE]:** three portfolio projects, working knowledge of
power markets and project finance, meaningful transaction exposure *if* the internal route
opened, and a genuine choice between internal progression and an external move. **Not**
a completed transition — that is a 2–4 year outcome, and anyone telling you otherwise is
selling something.

---

## The three-year career plan

**Year 1 — Credibility.** Modules A, B, C, D, E, Q, R. Projects 1–3. Transaction exposure
via LTA/TDD. Outcome: you are the person at Locogen who does the commercial technical work.

**Year 2 — Transition.** Modules F, N, S, T. Projects 4, 8, 9. **The move happens here** —
either internally into a transaction-advisory leadership role, or externally into
infrastructure debt, a fund's asset management or technical team, a developer's investment
team, or a data-centre energy role. **[ESTIMATE]** Expect £70–110k depending on route and
location; a sideways or slightly-down move in base pay is acceptable if it buys deal
exposure, and this is a trade worth making.

**Year 3 — Consolidation.** Modules O, P, H as relevant. Projects 5, 10 if trading-adjacent.
First carry or equity participation if the route offers it. **[ESTIMATE]** £90–140k.
Decision: specialise deeper, or begin building the entrepreneurial route in parallel.

**Contingencies.** *If the internal route closes* → external move accelerates to month 12–18;
weight applications towards infrastructure debt and TA firms, where sector expertise
substitutes for a finance CV. *If you relocate to New Jersey* → pivot hard to data-centre
energy and PJM; the US market values the exact combination you have and the capacity scarcity
is documented [FACT]. *If a recession hits* → infrastructure debt and consultancy are the
defensive routes; development and trading are the cyclical ones. *If you burn out* → drop to
5 hrs/week and protect Project delivery over module completion; artefacts persist, reading
does not.

---

## The five-year career and wealth plan

**Years 1–3** as above. **Years 4–5:** senior associate / investment manager / commercial
manager level; first carry allocation or project-level equity; the entrepreneurial track
running in parallel at low intensity (tooling → licensing → co-development).

**[ESTIMATE], central case, and explicitly not a promise:** £120–180k total compensation by
year 5, with the first carry or equity participation granted but not yet realised. Realised
wealth from carry typically arrives in years 6–10, not year 5 — **this lag is the single most
misunderstood feature of investment-side compensation.** Scenarios with full assumptions are
in [`06-wealth-strategy.md`](06-wealth-strategy.md).

**Risks to this plan, ranked by probability × impact:**
1. **Drift** — study without conversion into a different seat. *Mitigation:* the decision
   points above, and the tracker.
2. **Internal door stays shut** — Locogen does not staff you on transaction work.
   *Mitigation:* discovered by day 90, not year 2.
3. **Sector downturn** compressing hiring in years 2–3. *Mitigation:* infrastructure debt and
   consultancy as defensive fallbacks; both are in the route list deliberately.
4. **Overreach** — targeting trading or banking, failing, and losing two years.
   *Mitigation:* the recommendation in Part 6 argues against exactly this.
5. **Life events** — relocation, family. *Mitigation:* the plan is modular; artefacts survive
   interruption in a way that momentum does not.
