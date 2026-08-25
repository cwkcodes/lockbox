# Complete Glossary — Energy, Markets and Finance

**Every acronym spelled out. Every term explained in plain English. No assumed knowledge.**

Organised by theme so you can learn a topic, then alphabetically within each theme so you can
look one up. Terms in **bold** inside a definition are defined elsewhere in this glossary.

**Jump to:** [1. Units](#1-units-and-measurement) · [2. Electricity market](#2-electricity-market-and-system-operation)
· [3. Subsidy & certificates](#3-subsidy-schemes-and-certificates) · [4. Network charges](#4-network-charges-and-connections)
· [5. Contracts & route to market](#5-contracts-and-route-to-market) · [6. Storage](#6-storage-and-flexibility)
· [7. Accounting](#7-accounting-and-corporate-finance) · [8. Project finance](#8-project-finance)
· [9. Valuation & returns](#9-valuation-and-returns) · [10. Transactions](#10-transactions-ma-and-due-diligence)
· [11. Funds & carry](#11-funds-private-equity-and-carried-interest) · [12. Trading](#12-trading-and-risk)
· [13. Institutions](#13-institutions-and-bodies) · [14. Technical/commercial](#14-technical-terms-with-commercial-consequences)

---

## 1. Units and measurement

| Term | Full name | What it means |
|---|---|---|
| **W / kW / MW / GW** | Watt / kilo- / mega- / gigawatt | **Power** — a *rate* of energy flow. 1 kW = 1,000 W; 1 MW = 1,000 kW; 1 GW = 1,000 MW. A "50 MW solar farm" describes its maximum output rate, not how much it produces |
| **kWh / MWh / GWh / TWh** | Kilowatt-hour etc. | **Energy** — power multiplied by time. 1 MW running for 1 hour = 1 MWh. This is what you buy and sell |
| **MWe / MWth** | Megawatts electrical / thermal | Electrical output vs heat output. Combined heat and power plants quote both; confusing them wrecks a model |
| **£/MWh** | Pounds per megawatt-hour | The standard electricity price unit |
| **£/kW/year** | Pounds per kilowatt per year | How **Capacity Market** payments are quoted |
| **$/MW-day** | Dollars per megawatt per day | How US capacity markets (e.g. **PJM**) quote payments |
| **p/therm** | Pence per therm | GB gas price unit. 1 therm = 29.3071 kWh |
| **MMBtu** | Million British thermal units | Global gas and **LNG** unit. 1 MMBtu = 293.071 kWh = 10 therms |
| **Settlement period** | — | The half-hour block GB electricity is traded and settled in. 48 per day, 17,520 per year |
| **Capacity factor** | — | Actual energy produced ÷ (rated capacity × hours). GB indicative: onshore wind ~26–32%, offshore ~40–50%, solar ~10–11% |
| **Load factor** | — | Often used interchangeably with capacity factor in GB, but sometimes means output ÷ *available* capacity. **Always check the definition in the document you are reading** |
| **Availability** | — | The fraction of time the asset was *capable* of running, regardless of whether it did. A contractual term, not a performance one |
| **HHV / LHV** | Higher / Lower Heating Value | Two ways of measuring fuel energy content. LHV ≈ 0.90 × HHV for natural gas. **The US quotes HHV, Europe often LHV** — mixing them mis-states efficiency by ~10% |
| **Heat rate** | — | Fuel energy in ÷ electricity out (Btu/kWh). The inverse of efficiency. HR = 3412.14 ÷ efficiency |
| **bps** | Basis points | One hundredth of a percentage point. 100 bps = 1%. Used for interest rates and margins |
| **CPI / RPI** | Consumer / Retail Prices Index | UK inflation measures. RPI is normally higher. **Which index a contract uses materially changes its value** |

---

## 2. Electricity market and system operation

| Term | Full name | What it means |
|---|---|---|
| **Wholesale market** | — | Where electricity is bought and sold in bulk before reaching consumers |
| **Day-ahead market** | — | The main auction, held ~11:00 daily, setting a clearing price for each **settlement period** of the following day |
| **Intraday market** | — | Continuous trading after the day-ahead auction closes, up to near real time |
| **N2EX** | Nord Pool's GB market | The most-referenced GB day-ahead price index; most **PPAs** settle against it |
| **EPEX SPOT** | European Power Exchange | The other GB day-ahead auction and main intraday platform |
| **MID** | Market Index Data | The Elexon-published price used in **imbalance** settlement. Provider code `APXMIDP` is the N2EX-derived index |
| **Merit order** | — | Generators ranked from cheapest to most expensive **marginal cost**. The system dispatches up the order until demand is met |
| **Marginal pricing** | — | All generators receive the price bid by the *last* (most expensive) unit needed. This is why gas prices set electricity prices even when most generation is renewable |
| **SRMC** | Short-Run Marginal Cost | The cost of producing one more MWh: fuel ÷ efficiency + carbon cost + variable operating cost |
| **BM** | Balancing Mechanism | The market **NESO** uses in the final hour before real time to match supply and demand exactly |
| **BOA** | Bid-Offer Acceptance | NESO's instruction accepting a generator's **bid** or **offer** in the BM |
| **Bid** (BM) | — | A price at which a generator will *reduce* output (or a consumer increase demand) |
| **Offer** (BM) | — | A price at which a generator will *increase* output |
| **Imbalance price** | Also *system price*, *cash-out price* | The price at which the difference between notified and actual volume is settled. GB uses a **single** price for both long and short positions |
| **Imbalance** | — | The gap between what you told the system you would do and what you actually did. It costs money |
| **Curtailment** | — | Being instructed to reduce output, usually because the network cannot carry the power. Central to Scottish wind economics |
| **Constraint** | — | A physical limit on how much power a part of the network can carry |
| **Negative price** | — | A price below zero, occurring when supply exceeds demand and inflexible generation would rather pay to run than shut down |
| **Baseload** | — | (a) Flat, round-the-clock generation or demand; (b) the simple average market price, used as a reference |
| **Peak / off-peak** | — | Traditionally 07:00–19:00 weekdays vs the rest. **In GB this definition is now commercially obsolete** — solar has driven the midday price below the overnight price |
| **Capture price** | — | The **volume-weighted** average price an asset actually achieved. Σ(price × volume) ÷ Σ(volume) |
| **Capture rate** | — | Capture price ÷ **baseload** price. Below 100% means the asset earns less than the market average |
| **Cannibalisation** | — | The self-inflicted price depression caused by many similar assets generating simultaneously. Worsens as more capacity connects |
| **Shape risk** | — | Exposure to *when* you generate versus when you contracted to deliver |
| **Profile risk** | — | Closely related to shape risk; the mismatch between a generation profile and a demand profile |
| **Volume risk** | — | Exposure to producing more or less energy than forecast |
| **Basis risk** | — | When your hedge settles against a different price than your physical exposure |
| **CM** | Capacity Market | Pays generators and storage to *be available* at times of system stress. Cleared at **£27.10/kW/year** for GB delivery year 2029/30 |
| **T-4 / T-1** | — | Capacity Market auctions held four years and one year ahead of delivery |
| **Derating factor** | — | The percentage of nameplate capacity credited in the Capacity Market, reflecting the likelihood of delivering during stress. **1-hour batteries derate heavily; 4-hour batteries much less** |
| **Ancillary services** | — | Products the system operator buys for stability: frequency response, reserve, voltage support, black start |
| **DC / DM / DR** | Dynamic Containment / Moderation / Regulation | NESO's frequency response suite. DC and DM respond in 0.5 seconds for 15 minutes; DR in 2 seconds for 60 minutes |
| **FFR** | Firm Frequency Response | The legacy frequency service, being phased out during 2026 |
| **QR / PQR / NQR** | Quick Reserve / Positive / Negative | The replacement for FFR, released Q4 2025. Positive increases generation; Negative reduces it |
| **BR / SR** | Balancing Reserve / Slow Reserve | Services paying an **availability payment** for holding capacity back from other markets |
| **OBP** | Optimised Balancing Platform | NESO's system that, from January 2026, activates dynamic services directly |
| **Headroom / footroom** | — | Ability to increase / decrease output on instruction |
| **Inertia** | — | Stored rotational energy in spinning generators that slows frequency change. Falling as thermal plant retires — now a purchased service |
| **REMA** | Review of Electricity Market Arrangements | The DESNZ review that, in July 2025, **rejected zonal pricing** and kept a single national GB price |
| **LMP** | Locational Marginal Pricing | Pricing electricity differently at each network node. Used in US markets; **rejected for GB** |
| **PJM** | PJM Interconnection | The largest US regional grid operator, covering 13 states. Its 2027/28 capacity auction cleared at the **$333.44/MW-day cap** and still fell short |

---

## 3. Subsidy schemes and certificates

| Term | Full name | What it means |
|---|---|---|
| **RO** | Renewables Obligation | The legacy GB support scheme. **Closed to new capacity on 31 March 2017**, but existing assets receive support for 20 years from accreditation |
| **ROC** | Renewables Obligation Certificate | A tradeable certificate issued to renewable generators. Suppliers must present them to prove compliance with the RO, so they have value |
| **Buy-out price** | — | The per-certificate penalty a supplier pays instead of presenting a ROC. Sets the ceiling on ROC value. **£69.34 for 1 April 2026 – 31 March 2027** (up from £67.06) |
| **Recycle value** | — | Buy-out money redistributed to suppliers who *did* present ROCs, making a ROC worth **more** than the buy-out price. In 2022/23 total notional worth was £59.76 = £52.88 buy-out + £6.88 recycle |
| **Banding** | — | The number of ROCs issued per MWh, varying by technology and accreditation year. E.g. onshore wind commonly 0.9, offshore 1.8. **Always check the asset's own accreditation** |
| **Mutualisation** | — | If the buy-out fund falls short because a supplier defaults, the shortfall is spread across remaining suppliers |
| **FiT** | Feed-in Tariff | Small-scale scheme (≤5 MW) running April 2010 to 2019. Paid a generation tariff plus an export tariff. Closed to new applicants |
| **CfD** | Contract for Difference | The current GB scheme. A **two-way** contract: if the market price is below the **strike price**, the generator is topped up; if above, **the generator pays money back** |
| **Strike price** | — | The £/MWh the CfD guarantees. **Always ask which year's prices it is quoted in** — AR7 uses 2024 prices; AR6 used 2012 |
| **Reference price** | — | The market price a CfD is compared against — day-ahead for intermittent technologies |
| **AR** | Allocation Round | A CfD auction. **AR7** results: offshore wind **£91/MWh**, onshore wind **£72/MWh**, solar **£65/MWh**, floating offshore **£216.49/MWh** (all 2024 prices) |
| **ASP** | Administrative Strike Price | The maximum price government will accept in an auction — a ceiling, not a target. AR7 solar ASP was £75/MWh; it cleared at £65 |
| **CIB** | Clean Industry Bonus | Extra CfD support for offshore wind developers investing in sustainable UK supply chains. Tangible assets only |
| **Pot 1 / Pot 2 / Pot 3** | — | CfD auction categories. Pot 1 = established technologies (onshore wind, solar); Pot 3 = offshore wind |
| **Merchant tail** | — | The period after a subsidy contract ends, when the asset is fully exposed to market prices. **Often the largest and least certain component of value** |
| **REGO** | Renewable Energy Guarantees of Origin | A certificate proving one MWh came from a renewable source, sold separately from the electricity. **£1–2/MWh in summer 2026**, having peaked at £20–25/MWh in 2023 |
| **GoO** | Guarantee of Origin | The European equivalent of a REGO |
| **RAB** | Regulated Asset Base | A funding model where consumers pay during construction, used for nuclear and some networks. Transfers construction risk to consumers |
| **UK ETS / EU ETS** | UK / EU Emissions Trading Scheme | Carbon markets where emitters must surrender allowances. UK ETS Dec-26 traded around **£58.97/tCO₂e** in August 2026 |
| **UKA / EUA** | UK / EU Allowance | One tonne of CO₂ equivalent under the respective trading scheme |

---

## 4. Network charges and connections

| Term | Full name | What it means |
|---|---|---|
| **TNUoS** | Transmission Network Use of System | Charge for using the high-voltage transmission network. **Locational** — northern Scottish generators pay much more than southern English ones. Average generation tariff **£13.03/kW for 2026/27** |
| **BSUoS** | Balancing Services Use of System | Recovers NESO's costs of balancing the system, including constraint payments. Now a fixed six-monthly tariff: **£13.74/MWh (Apr–Sep 2026), £12.49/MWh (Oct 2026–Mar 2027)** |
| **DUoS** | Distribution Use of System | The equivalent charge for lower-voltage local networks |
| **TCR** | Targeted Charging Review | Ofgem's reform, decided 21 November 2019, moving residual charges to fixed charges and largely ending **embedded benefits** |
| **Embedded generator** | — | One connected to the *distribution* network rather than transmission |
| **Embedded benefits** | — | Historic payments to embedded generators for helping suppliers avoid transmission charges. **Largely removed by the TCR** — check whether an older asset's original business case relied on them |
| **Triad** | — | The three half-hours of highest GB demand between November and February, at least ten days apart. Historically the basis for transmission demand charges; **avoidance payments were cut from April 2018** |
| **Connection agreement** | — | The contract setting out where, when and how much a project may connect |
| **Firm / non-firm connection** | — | Firm = guaranteed capacity. Non-firm = curtailable when the network is constrained. **Non-firm is cheaper and much riskier** |
| **TMO4+** | Target Model Option 4+ | The GB connections queue reform approved by Ofgem on 15 April 2025, replacing first-come-first-served with a "ready and needed" ordered queue |
| **Gate 1 / Gate 2** | — | Stages in the reformed queue. **A Gate 2 offer is now a scarce, valuable asset** — Gate 2 offers are being issued through 2026 |
| **ANM** | Active Network Management | A system that automatically curtails generation to keep the network within limits |
| **Intertrip** | — | An automatic disconnection arrangement triggered by a network fault |
| **Fault level** | — | The maximum current a network fault would produce. Insufficient headroom can block a connection entirely |
| **DNO** | Distribution Network Operator | The regional company running the local network |
| **TO** | Transmission Owner | The company owning the high-voltage network (National Grid Electricity Transmission, SP Transmission, SSEN Transmission) |
| **RIIO** | Revenue = Incentives + Innovation + Outputs | Ofgem's price control framework setting network companies' allowed revenues and returns |

---

## 5. Contracts and route to market

| Term | Full name | What it means |
|---|---|---|
| **PPA** | Power Purchase Agreement | The contract under which a generator sells its output |
| **CPPA** | Corporate PPA | A PPA signed directly with a corporate energy user rather than a utility |
| **Sleeved PPA** | — | A corporate buys from a specific generator while a licensed supplier handles settlement for a fee |
| **Synthetic / virtual PPA** | — | A purely financial contract — no physical power moves; the parties settle the difference against a reference price |
| **Baseload PPA** | — | Requires delivery of a flat volume. **Dangerous for a wind farm**, which must buy power to fill gaps, usually when prices are high |
| **Route to market** | — | The arrangement by which a generator's power reaches the market, since generators cannot participate in settlement directly |
| **PPA discount** | — | The margin the offtaker takes for absorbing imbalance, shape, credit and volume risk. **One of the most commercially important and least public numbers in the sector** |
| **Offtaker** | — | The party buying the power |
| **Tolling agreement** | — | A counterparty pays a fixed fee for the exclusive right to operate an asset and take all its market revenue. **Lower expected revenue, far more debt capacity** |
| **Take-or-pay** | — | An obligation to pay whether or not you take delivery |
| **EPC** | Engineering, Procurement and Construction | A contract where one contractor delivers the whole plant, usually fixed-price and fixed-date |
| **Full-wrap EPC** | — | An EPC in which the contractor takes essentially all construction risk. **Lenders strongly prefer it** |
| **BoP** | Balance of Plant | Everything other than the main generating equipment — civils, foundations, roads, cabling |
| **TSA** | Turbine Supply Agreement | The contract to buy wind turbines |
| **O&M** | Operations and Maintenance | The contract to run and maintain the asset |
| **LTSA / LTMA** | Long-Term Service / Maintenance Agreement | A multi-year maintenance contract, often with availability guarantees |
| **LDs** | Liquidated Damages | Pre-agreed compensation for late delivery or underperformance. **Always check the cap** |
| **Availability warranty** | — | A contractual guarantee that the asset will be capable of running a given percentage of the time. **Not a guarantee of production** |
| **Performance ratio** | — | For solar: actual output ÷ theoretical output given the irradiance received |
| **Degradation** | — | The gradual decline in output over time. Solar ~0.4–0.5%/year; wind ~0.2–0.5%/year |

---

## 6. Storage and flexibility

| Term | Full name | What it means |
|---|---|---|
| **BESS** | Battery Energy Storage System | A grid-connected battery installation |
| **Duration** | — | How long the battery can discharge at full power. A "2-hour" 50 MW battery holds 100 MWh |
| **C-rate** | — | The rate of charge or discharge relative to capacity. 1C = full discharge in one hour |
| **RTE** | Round-Trip Efficiency | Energy out ÷ energy in. Typically 85–92% for lithium-ion systems |
| **SoC** | State of Charge | How full the battery is now, as a percentage |
| **SoH** | State of Health | Remaining capacity relative to when new. Declines with cycling and age |
| **DoD** | Depth of Discharge | How deeply the battery is discharged in a cycle. Deeper cycling accelerates degradation |
| **Cycle life** | — | Number of charge/discharge cycles before capacity falls below a threshold |
| **Calendar ageing** | — | Capacity loss that occurs with time regardless of use |
| **Augmentation** | — | Adding battery cells later in life to restore lost capacity. **A capital cost that must be modelled**, typically year 7–10 |
| **BMS** | Battery Management System | The control system managing cell voltages, temperature and safety |
| **PCS** | Power Conversion System | The inverter converting between the battery's DC and the grid's AC |
| **Arbitrage** | — | Buying energy cheaply and selling it dearly. The core battery revenue |
| **Perfect foresight** | — | An optimisation assuming prices are known in advance. **Produces a theoretical maximum; real optimisers achieve roughly 60–85% of it.** Quoting it as achievable revenue is a classic error |
| **Revenue stacking** | — | Earning from several markets simultaneously — wholesale, BM, ancillary services, Capacity Market |
| **Degradation-aware optimisation** | — | Dispatching a battery with the marginal cost of degradation priced in, rather than maximising short-term revenue |
| **LDES** | Long Duration Energy Storage | Storage of 8+ hours — pumped hydro, compressed air, flow batteries |
| **Pumped hydro** | — | Water pumped uphill when power is cheap and released through turbines when it is expensive. The dominant global storage technology by volume |

---

## 7. Accounting and corporate finance

| Term | Full name | What it means |
|---|---|---|
| **P&L** | Profit and Loss (Income Statement) | Revenue minus costs over a period. **Shows profit, not cash** |
| **Balance sheet** | — | What a company owns and owes at a point in time. Assets = liabilities + equity |
| **Cash flow statement** | — | Where cash actually came from and went. **The one that matters most in project finance** |
| **Revenue / turnover** | — | Money earned from sales before any costs |
| **CAPEX** | Capital Expenditure | Money spent building or buying long-lived assets |
| **OPEX** | Operating Expenditure | Ongoing running costs |
| **EBITDA** | Earnings Before Interest, Tax, Depreciation and Amortisation | A proxy for operating cash generation. **Widely used, widely abused — it is not cash** |
| **EBIT** | Earnings Before Interest and Tax | EBITDA minus depreciation and amortisation. Also called operating profit |
| **Depreciation** | — | Spreading the cost of a physical asset over its useful life. A non-cash accounting charge |
| **Amortisation** | — | The same idea for intangible assets |
| **Capital allowances** | — | The UK **tax** equivalent of depreciation. **Tax depreciation and accounting depreciation are different — treating them as the same is a common and costly modelling error** |
| **Working capital** | — | Short-term assets minus short-term liabilities. Money tied up in day-to-day operations |
| **Free cash flow** | — | Cash generated after operating costs and capital expenditure |
| **Provision** | — | An amount set aside for a known future obligation |
| **ARO** | Asset Retirement Obligation | The provision for decommissioning. **Frequently disputed in renewable transactions** |
| **Impairment** | — | Writing down an asset's carrying value when it is worth less than the books say |
| **Deferred tax** | — | Tax that will be paid or recovered in future because of timing differences between accounting and tax rules |
| **Net debt** | — | Gross debt minus cash, plus debt-like items |
| **Debt-like items** | — | Obligations treated as debt when calculating price — pension deficits, decommissioning provisions, deferred consideration. **A common source of deal disputes** |
| **ROIC / ROCE** | Return on Invested / Capital Employed | Operating profit ÷ capital invested. Measures how efficiently capital is used |
| **Covenant** | — | A condition in a loan agreement. Breaching it gives the lender rights |
| **Credit rating** | — | An agency assessment of the likelihood of default. Investment grade is BBB−/Baa3 or above |

---

## 8. Project finance

| Term | Full name | What it means |
|---|---|---|
| **Project finance** | — | Lending against a single project's cash flows rather than a company's balance sheet |
| **SPV / ProjectCo** | Special Purpose Vehicle | A company created solely to own one project. Legally ring-fences risk |
| **Non-recourse** | — | If the project fails, lenders take the project but **cannot** pursue the sponsor's other assets |
| **Limited-recourse** | — | Some carefully defined recourse to the sponsor, usually during construction only |
| **Sponsor** | — | The equity owner or developer behind the project |
| **CFADS** | Cash Flow Available for Debt Service | Revenue − opex − tax − working capital movement − maintenance capex. **Not EBITDA** |
| **DSCR** | Debt Service Cover Ratio | CFADS ÷ debt service. **The central covenant in project finance.** 1.20–1.30× for contracted renewables; 1.60×+ for merchant BESS |
| **LLCR** | Loan Life Cover Ratio | Present value of CFADS over the remaining loan life ÷ debt outstanding |
| **PLCR** | Project Life Cover Ratio | The same over the whole project life, including the **tail**. Always higher than LLCR |
| **Debt sizing** | — | Determining how much debt a project can carry, driven by the DSCR covenant |
| **Debt sculpting** | — | Deriving the repayment schedule from the cash flow so DSCR stays constant. Debt service = CFADS ÷ target DSCR |
| **Gearing / leverage** | — | The proportion of funding provided by debt |
| **Senior debt** | — | First in line for repayment. Lowest risk, lowest rate |
| **Mezzanine / junior debt** | — | Repaid after senior debt. Higher risk, higher rate |
| **Tenor** | — | The length of a loan |
| **Margin** | — | The lender's spread over the reference rate, quoted in **bps** |
| **SONIA** | Sterling Overnight Index Average | The GB benchmark interest rate |
| **Amortisation** (debt) | — | Gradual repayment of principal over the loan life |
| **Bullet repayment** | — | Principal repaid in a single lump at maturity |
| **IDC** | Interest During Construction | Interest accruing before the asset earns anything. Usually capitalised into the loan. **Creates circularity in the model** |
| **Circularity** | — | When A depends on B and B depends on A — e.g. debt size depends on IDC, which depends on debt size. Resolved by iterative calculation, **never by hardcoding** |
| **Cash waterfall** | — | The strict legal order in which project cash is applied: opex → interest → principal → reserves → junior debt → equity |
| **DSRA** | Debt Service Reserve Account | A reserve holding (typically) six months of debt service as a buffer |
| **MRA** | Maintenance Reserve Account | A reserve for future major maintenance |
| **Distribution lock-up** | — | A DSCR threshold set *above* the default level. Between the two, cash is trapped and equity receives nothing. **The covenant that actually governs equity returns in a stressed case** |
| **Tail** | — | The period between loan maturity and the end of asset life. Lenders want a buffer |
| **Security package** | — | The collateral and step-in rights protecting lenders |
| **Step-in rights** | — | Lenders' right to take over a project to rescue it rather than let it fail |
| **Financial close** | — | The moment all finance documents are signed and funds can be drawn |
| **P50 / P90** | — | Production levels exceeded 50% / 90% of the time. **Lenders size debt on P90, not P50.** P90 = P50 × (1 − 1.2816 × σ) |
| **Refinancing** | — | Replacing debt with cheaper debt once construction risk has passed. **A major and often under-planned value driver** |
| **ECA** | Export Credit Agency | A state body providing finance or guarantees to support exports |

---

## 9. Valuation and returns

| Term | Full name | What it means |
|---|---|---|
| **NPV** | Net Present Value | Future cash flows discounted to today, minus the initial investment. Positive NPV = value created |
| **Discount rate** | — | The rate used to convert future cash to present value. Encodes both time and risk |
| **IRR** | Internal Rate of Return | The discount rate at which NPV = 0. The headline return measure |
| **Project IRR** | Unlevered IRR | Return on project cash flows *before* financing. Measures the asset |
| **Equity IRR** | Levered IRR | Return on the equity investor's cash flows *after* debt. Measures asset **plus** financing structure |
| **MOIC** | Multiple on Invested Capital | Total cash returned ÷ cash invested. **Ignores time completely** |
| **Payback period** | — | Years until cumulative cash flow turns positive. Ignores everything after |
| **Yield** | — | Annual cash distribution ÷ equity invested |
| **WACC** | Weighted Average Cost of Capital | (E/V × cost of equity) + (D/V × cost of debt × (1 − tax rate)). The blended cost of funding |
| **Cost of equity** | — | The return equity investors require. Higher than debt because they are paid last |
| **Hurdle rate** | — | The minimum return required before an investment is approved — or before fund managers earn **carry** |
| **Terminal value** | — | The assumed value at the end of the modelled period |
| **Residual value** | — | What the asset is worth at the end of its contracted or modelled life |
| **EV** | Enterprise Value | The value of the whole business regardless of financing |
| **Equity value** | — | EV minus net debt. What the shareholders' stake is worth |
| **DCF** | Discounted Cash Flow | Valuation by discounting projected cash flows |
| **Comparable companies / precedent transactions** | "Comps" | Valuing by reference to what similar businesses trade at or were sold for |
| **LCOE** | Levelised Cost of Energy | PV(all costs) ÷ PV(all energy). **Useful for screening, misleading for investment decisions** because it ignores *when* energy is produced |
| **Sensitivity analysis** | — | Testing how the answer changes when one input changes |
| **Tornado chart** | — | A chart ranking inputs by their impact on the output. The standard way to show what drives value |
| **Monte Carlo** | — | Running thousands of simulations with randomised inputs to produce a distribution of outcomes |
| **Real vs nominal** | — | Real excludes inflation, nominal includes it. **Discounting nominal cash flows at a real rate is the single most common financial modelling error.** Pick one and be consistent |

---

## 10. Transactions, M&A and due diligence

| Term | Full name | What it means |
|---|---|---|
| **M&A** | Mergers and Acquisitions | Buying, selling and combining companies or assets |
| **SPA** | Sale and Purchase Agreement | The contract selling an asset or shares |
| **Locked box** | — | Price fixed at a historic balance-sheet date; the buyer takes economic benefit from that date |
| **Completion accounts** | — | Price adjusted after closing based on actual cash and working capital |
| **Reps and warranties** | Representations and warranties | Statements of fact by the seller. If untrue, the buyer may claim |
| **Indemnity** | — | A promise to compensate for a specific identified risk |
| **W&I insurance** | Warranty and Indemnity insurance | A policy covering warranty breaches, letting the seller exit cleanly |
| **CP** | Condition Precedent | Something that must happen before completion |
| **Earn-out** | — | Deferred payment contingent on future performance |
| **Data room** | — | The secure document repository buyers review |
| **DD** | Due Diligence | Investigating an asset before buying it |
| **TDD** | Technical Due Diligence | Will the asset physically perform? **Done by engineers** |
| **LTA** | Lender's Technical Adviser | The engineer advising the *banks* rather than the buyer. **The report goes to the credit committee** |
| **CDD** | Commercial Due Diligence | Is the market view sound? |
| **FDD** | Financial Due Diligence | Are the accounts and model right? |
| **LDD** | Legal Due Diligence | Are contracts and title sound? |
| **VDD** | Vendor Due Diligence | Reports the seller commissions for all bidders |
| **Red flag report** | — | A rapid first-pass review identifying deal-breakers |
| **IM** | Information Memorandum | The sales document describing the asset |
| **Teaser** | — | A short anonymised summary sent to potential buyers |
| **NDA** | Non-Disclosure Agreement | Confidentiality agreement signed before accessing the data room |
| **IOI / NBO** | Indication of Interest / Non-Binding Offer | An early, non-committal price indication |
| **Exclusivity** | — | A period in which the seller negotiates with one bidder only |
| **IC** | Investment Committee | The body approving an investment |
| **IC memo / paper** | — | The document putting the case to the IC. **Producing one is the clearest demonstration that you can decide, not just analyse** |
| **LBO** | Leveraged Buyout | Acquiring a company using substantial debt |
| **Bolt-on** | — | A smaller acquisition added to an existing platform |
| **Platform** | — | A company or portfolio acquired as a base for further acquisitions |

---

## 11. Funds, private equity and carried interest

| Term | Full name | What it means |
|---|---|---|
| **PE** | Private Equity | Investing in companies not listed on a stock exchange |
| **GP** | General Partner | The fund management team. Makes the decisions, takes the **carry** |
| **LP** | Limited Partner | The investors supplying the capital — pension funds, insurers, sovereign wealth funds |
| **Fund** | — | The pooled vehicle through which LPs invest |
| **Commitment** | — | The capital an LP promises; drawn down over time as deals are done |
| **Dry powder** | — | Committed but not yet invested capital |
| **Management fee** | — | An annual fee to the GP, typically ~2% of committed capital |
| **Carried interest ("carry")** | — | The GP's share of profits above a hurdle, typically ~20%. **The main mechanism by which fund professionals build substantial wealth** |
| **Hurdle rate / preferred return** | — | The return LPs must receive before the GP earns carry, often ~8% |
| **Catch-up** | — | A provision letting the GP receive a large share after the hurdle until the agreed profit split is reached |
| **Waterfall** (fund) | — | The order in which fund proceeds are distributed: return of capital → preferred return → catch-up → profit split |
| **Vintage** | — | The year a fund began investing |
| **Co-investment** | — | LPs investing directly alongside the fund, usually with reduced fees |
| **Core / core-plus / value-add / opportunistic** | — | Infrastructure risk categories, from fully contracted operating assets (core, ~6–8% returns) to development and repositioning (opportunistic, 15%+) |
| **Promote** | — | A developer's enhanced share of profits after a return threshold. The development-world equivalent of carry |
| **Development equity** | — | A retained stake in a project you originated. **Realistically the most accessible route to substantial personal wealth for a developer** |
| **Exit** | — | Selling an investment to realise the return |
| **Dilution** | — | The reduction in ownership percentage when new shares are issued |
| **Shareholders' agreement** | — | The contract governing how shareholders make decisions |

---

## 12. Trading and risk

| Term | Full name | What it means |
|---|---|---|
| **Spot** | — | Buying or selling for immediate or near-immediate delivery |
| **Forward / futures** | — | Contracts to buy or sell at a set price on a future date. Futures are exchange-traded and standardised; forwards are bilateral |
| **Forward curve** | — | The set of prices for delivery at different future dates |
| **Contango** | — | Forward prices above spot. Usually implies storage is valuable |
| **Backwardation** | — | Forward prices below spot. Usually implies immediate scarcity |
| **Swap** | — | An exchange of a floating price for a fixed price |
| **Option** | — | The right, but not the obligation, to buy (call) or sell (put) at a set price |
| **Strike** (option) | — | The price at which an option can be exercised |
| **Premium** | — | The price paid for an option |
| **Delta / gamma / vega** | "The Greeks" | Sensitivity of an option's value to the underlying price / to delta itself / to volatility |
| **Hedge** | — | A position taken to offset risk in another position |
| **Speculation** | — | Taking a position to profit from price movement, without an underlying exposure |
| **Spread** | — | The difference between two prices. **In energy, the spread is usually the trade, not the outright price** |
| **Spark spread** | — | Power price minus the cost of the gas needed to produce it |
| **Clean spark spread** | — | Spark spread minus the carbon cost. **The number a thermal trader carries in their head** |
| **Dark spread** | — | The coal equivalent |
| **Crack spread** | — | Refined product prices minus crude — a refiner's margin |
| **MTM** | Mark to Market | Revaluing positions at current market prices |
| **P&L** | Profit and Loss | The gain or loss on a position |
| **VaR** | Value at Risk | A statistical estimate of potential loss over a period at a confidence level. **Energy markets have fat tails, so VaR is a limit-administration tool, not a worst-case estimate** |
| **Stress testing** | — | Testing a portfolio against severe but plausible scenarios. **Does the real work that VaR cannot** |
| **Margin** (trading) | — | Collateral posted against a position |
| **Margin call** | — | A demand for more collateral when positions move against you |
| **Counterparty risk** | — | The risk the other side of a trade fails to perform |
| **REMIT** | Regulation on Energy Market Integrity and Transparency | EU/UK rules prohibiting market abuse and requiring disclosure of inside information in energy markets |
| **Originator** | — | Someone who structures bespoke physical or financial deals with counterparties rather than trading standard products |

---

## 13. Institutions and bodies

| Body | Full name | What it does |
|---|---|---|
| **DESNZ** | Department for Energy Security and Net Zero | UK government department. Sets policy, runs CfD allocation rounds and budgets |
| **Ofgem** | Office of Gas and Electricity Markets | GB energy regulator. Licences, network price controls (**RIIO**), code changes, administers the RO |
| **NESO** | National Energy System Operator | Operates the GB electricity system, runs the **BM** and the connections queue. Publicly owned since 2024 |
| **Elexon** | — | Administers the **BSC** and publishes **BMRS** market data. **Your primary free data source** |
| **BSC** | Balancing and Settlement Code | The rulebook governing GB electricity settlement |
| **BMRS** | Balancing Mechanism Reporting Service | Elexon's published market data |
| **LCCC** | Low Carbon Contracts Company | The government-owned counterparty to every **CfD** |
| **ESO / TO / DNO** | Electricity System Operator / Transmission Owner / Distribution Network Operator | System operation vs owning high-voltage vs owning local networks |
| **IEA** | International Energy Agency | Publishes global energy statistics and outlooks |
| **IRENA** | International Renewable Energy Agency | Publishes renewable cost and capacity data |
| **EIA** | US Energy Information Administration | US energy statistics |
| **FERC** | Federal Energy Regulatory Commission | US federal energy regulator |
| **ENTSO-E** | European Network of Transmission System Operators for Electricity | European TSO coordination body and data source |
| **RTO / ISO** | Regional Transmission Organisation / Independent System Operator | US regional grid operators — **PJM**, ERCOT, CAISO, NYISO, ISO-NE, MISO |

---

## 14. Technical terms with commercial consequences

| Term | What it means | Why it matters commercially |
|---|---|---|
| **MCP** | Measure-Correlate-Predict — deriving long-term wind resource from short on-site measurement correlated with a long-term reference | The foundation of the energy yield, which is the foundation of the debt sizing |
| **Weibull distribution** | The statistical distribution describing wind speed frequency | Determines energy yield from a power curve |
| **Power curve** | Turbine output as a function of wind speed | Warranted by the manufacturer; a shortfall is a contractual claim |
| **Wake losses** | Output reduction because upwind turbines slow the air | A layout decision with direct revenue consequences |
| **Uncertainty (σ)** | The standard deviation around the P50 estimate | **Every 1% of uncertainty reduction is worth ~1.28% of debt capacity** |
| **Irradiance** | Solar energy per unit area (W/m²) | The solar equivalent of wind speed |
| **GHI / POA** | Global Horizontal Irradiance / Plane of Array | Measured horizontally vs in the panel's plane. Confusing them mis-states yield |
| **Inverter loading ratio (DC:AC)** | Installed panel capacity vs inverter capacity | Over-sizing DC raises capacity factor but causes clipping |
| **Clipping** | Output lost when DC generation exceeds inverter capacity | An engineering choice that trades peak losses for higher overall yield |
| **Repowering** | Replacing old turbines with new ones on an existing site | Reuses consent and grid connection — **the grid connection is often worth more than the turbines** |
| **Life extension** | Operating beyond original design life after assessment | Extends the merchant tail and adds value cheaply |
| **Decommissioning** | Removing the asset and restoring the site at end of life | A provision, often disputed as a **debt-like item** in transactions |
| **Grid-forming vs grid-following inverter** | Whether the inverter can establish grid voltage and frequency itself | Grid-forming capability is increasingly required and increasingly paid for |
| **Short-circuit level / system strength** | The network's ability to maintain stable voltage | Weak-grid areas constrain how much inverter-based generation can connect |

---

## Sources for the figures quoted

All market data is cited with retrieval dates in the module files. Key primary sources:

- **ROC buy-out price 2026/27** — [Ofgem](https://www.ofgem.gov.uk/data/renewables-obligation-buy-out-price-and-mutualisation-threshold-and-ceilings-2026-2027)
- **RO indexation change (RPI→CPI)** — [DESNZ government response](https://www.gov.uk/government/consultations/renewables-obligation-ro-scheme-indexation-changes/outcome/renewables-obligation-ro-scheme-indexation-changes-government-response-html)
- **RO closure** — [Ofgem](https://www.ofgem.gov.uk/environmental-programmes/ro/about-ro/ro-closure)
- **CfD AR7 results** — [DESNZ](https://assets.publishing.service.gov.uk/media/6966861de8c04eb2919f773a/contracts-for-difference-allocation-round-7-results-.pdf)
- **AR7 reforms (20-year contracts)** — [Flint Global](https://flint-global.com/blog/the-most-important-cfd-round-in-years-what-do-the-major-reforms-mean/)
- **TNUoS 2026/27** — [NESO](https://www.neso.energy/document/376336/download)
- **BSUoS 2026/27** — [Drax](https://energy.drax.com/intelligence/initial-2026-27-bsuos-forecasts-published/)
- **Capacity Market T-4 2029/30** — [Modo Energy](https://modoenergy.com/research/en/gb-capacity-market-t4-2029-30-battery-energy-storage-march-2026)
- **BESS revenue stack** — [Modo Energy](https://modoenergy.com/research/en/how-does-battery-energy-storage-make-money)
- **Ancillary services** — [NESO](https://www.neso.energy/industry-information/balancing-services/frequency-response-services/dynamic-services-dcdmdr)
- **TCR decision** — [Ofgem](https://www.ofgem.gov.uk/decision/targeted-charging-review-decision-and-impact-assessment)
- **REMA / zonal pricing rejection** — [Norton Rose Fulbright](https://www.nortonrosefulbright.com/en/knowledge/publications/4399413b/rema-summer-update-no-to-zonal-pricing-yes-to-reformed-national-pricing)
- **Capture rates** — computed from Elexon BMRS data; see `projects/p1_gb_power_dashboard/`

**Verify before relying on any figure in a live transaction.** Subsidy prices, network
tariffs and derating factors are reset annually.
