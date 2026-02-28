<!--
=============================================================================
PART 2 OF 5 — Aigis DD Domain Knowledge Document
File: Aigis_DD_DomainKnowledge_PART2_Workstreams_Technical_Financial_Legal.md
Covers: Section 3.1 Technical | 3.2 Financial | 3.3 Legal
Assembles after PART 1. Before PART 3.
=============================================================================
-->

## SECTION 3: FUNCTIONAL WORKSTREAMS — 10 KEY FOCUS AREAS EACH

> **For the Aigis System Coordinator:** Each workstream below defines what the team is trying to accomplish, the 10 critical focus areas, red-flag criteria, VDR-specific tasks, and the pro-forma combined-company lens. Use this section to:
> - Understand which workstream a user query belongs to
> - Know what a correct, expert-level response looks like
> - Apply the correct red-flag criteria and benchmarks
> - Select the right Aigis agents (see Section 5 for full agent routing)

---

### 3.1 Technical / Subsurface Workstream

**Team:** Reservoir engineers, geoscientists, facilities engineers, production technologists
**Primary Objective:** Independently validate reserves and production forecasts. Challenge CPR assumptions. Quantify subsurface risk and upside.
**Aigis Agents:** Agent 02 (Production DB) · Agent 03 (Consistency Auditor) · Agent 07 (Well Cards) · Agent 17 (Decline Modeller)

---

#### Focus Area T1: CPR Review & Reserves Audit

**What the team does:**
- Scrutinise CPR: effective date, certifying firm, methodology (SPE-PRMS vs SEC), scope
- Confirm certifier is genuinely independent (not a company-prepared CPR dressed as independent)
- Extract reserves table: 1P, 2P, 3P by field, by well, by category (PDP/PDNP/PUD/Probable/Possible)
- Challenge b-values in hyperbolic decline curves — sellers systematically use high b-values (>0.8) to slow modelled decline and inflate 2P reserves
- Verify abandonment timing assumptions — premature cessation of production artificially boosts NPV
- Confirm the price case used in CPR and compare to current forward market (Agent 05)
- Calculate 2P/1P ratio — if >3x, upside is heavily weighted to lower-confidence categories

**Red Flags 🔴:**
- CPR effective date >12 months old at time of DD (reserves may be materially different now)
- Certifying firm has no experience in the relevant basin (GoM, UKCS, etc.)
- 2P/1P ratio >3× without a compelling drilling programme justification
- b-value >0.8 for any well without reservoir evidence (e.g., strong water drive) justifying it
- Prospective resources comprise >60% of total CPR value — highly uncertain; discount heavily
- CPR uses a price deck more than 5% above current CME/EIA forward curve (see Agent 05 output)
- CPR effective date post-dates a production anomaly that reduced actual performance

---

#### Focus Area T2: Independent Production Decline Modelling

**What the team does:**
- Obtain all historical production data (monthly actuals, by well, by stream: oil/gas/water/NGL)
- Fit decline curves independently using actual data:
  - Exponential: constant percentage decline — most conservative and most common for depletion drive
  - Hyperbolic: b-value determines curvature — b=0 is exponential; b=1 is harmonic
  - Harmonic: slowest decline; only justified with strong aquifer support
- Generate buyer-side P10/P50/P90 production forecasts from fitted decline parameters
- Compare buyer's independent forecast to CPR P50 forecast, well by well
- CPR vs Actual variance: flag wells where actual production since CPR effective date is >10% below CPR forecast
- Run Monte Carlo on key parameters if data supports it (Agent 17)

**Red Flags 🔴:**
- CPR uses hyperbolic decline (b>0.5) where exponential fits the actual production data equally well
- Production history shows a step-change decline not reflected or explained in CPR
- GOR rising faster than CPR modelled — indicates faster reservoir depletion than assumed
- Multiple wells with actual production >15% below CPR P50 since effective date
- Seller model uses P10 production profile in base case financial model (presented as P50)

---

#### Focus Area T3: Reservoir & Geoscience Data Review

**What the team does:**
- Review all seismic volumes: 3D coverage, vintage, processing, interpretation reports
- Assess structural maps: are closures robust? What is the uncertainty on STOIIP/GIIP estimates?
- Petrophysical analysis: net pay, porosity, permeability, water saturation (Sw) — are cutoffs reasonable?
- Fluid contacts: OWC, GOC — confirm consistency across wells and CPR model
- Reservoir heterogeneity: barriers, baffles, compartmentalisation — does CPR account for connectivity risk?
- Pressure data: is reservoir pressure close to bubble point (oil) or dew point (gas)? Drive mechanism?
- Validate STOIIP/GIIP: recompute using reported parameters; flag >15% difference from CPR

**Red Flags 🔴:**
- Seismic data >10 years old with no reprocessing and no reinterpretation since acquisition
- Large OWC uncertainty (>20m) in thin reservoirs — significant impact on STOIIP
- Reservoir pressure at or below bubble point without gas cap management plan
- No formation water analysis — injection compatibility unknown for future waterflooding
- Compartmentalisation risk high but CPR assumes full connectivity (check depletion survey)

---

#### Focus Area T4: Well Performance Analysis

**What the team does:**
- Compare actual production to CPR forecast, per well, from CPR effective date to present (Agent 07)
- Compute variance: (Actual − CPR Forecast) / CPR Forecast × 100% per well
- Flag all wells with cumulative underperformance >10% since CPR effective date as Moderate 🟡
- Flag all wells with cumulative underperformance >20% since CPR effective date as Critical 🔴
- Analyse GOR trend: rising GOR indicates reservoir depletion, possible gas cap expansion into oil column
- Analyse water cut (WC) trend: rising WC indicates aquifer influx or injection breakthrough
- Review mechanical well integrity: tubing condition, casing surveys, surface equipment condition
- Assess shut-in wells: why shut-in? What is the cost and timeline to return to production?

**Output (Well Card — Agent 07):**
- Current rate (bopd / MMscfd / boepd)
- Cumulative production vs CPR forecast
- Current GOR (scf/bbl) and trend
- Current water cut (%) and trend
- Status: 🟢 Outperformer · 🟡 On-track · 🔴 Underperformer · ⚫ Shut-in

**Red Flags 🔴:**
- >30% of producing wells showing cumulative underperformance >15% since CPR effective date
- Rapid GOR increase (>15%/year) across multiple wells simultaneously
- Unexplained shut-in wells that were performing above expectations before shutdown
- Mechanical failures in multiple wells suggesting systemic integrity issues

---

#### Focus Area T5: Development / Drilling Inventory Assessment

**What the team does:**
- Review all PUD locations in CPR: description, target interval, depth, lateral length (shale), expected rate, cost
- Challenge drill costs: compare to BSEE/NSTA well cost data for the specific area
  - GoM shelf well: typically $5–20M depending on depth and complexity
  - GoM deepwater well: typically $50–200M
  - UKCS well: typically £15–50M
- Assess inventory depth: how many years of drillable PUD locations at planned pace?
- Model NPV per PUD location at buyer's assumptions (Agent 04)
- Verify rig availability at assumed dayrate: has the seller contracted a rig, or is it assumed?
- Assess quality of 2P/3P drilling locations: G&G support, analogues, offset well performance

**Red Flags 🔴:**
- PUD costs based on pre-2020 dayrates (now materially higher in most basins)
- Drilling programme assumes a specific rig not yet contracted
- Long-lead items (wellheads, trees, umbilicals) not ordered — 18–24 month lead time
- Inventory depth <3 years at planned drilling pace
- 2P/3P locations have no offset well analogues in the same reservoir

---

#### Focus Area T6: Facility & Infrastructure Condition

**What the team does:**
- Review facility design basis vs current operations (nameplate capacity vs actual throughput)
- Assess topside and subsea equipment age and condition reports
- Review planned maintenance and capex forecasts — is the deferred maintenance backlog included?
- Identify operational bottlenecks: compression capacity, water handling limits, gas lift capacity
- Pipeline integrity: ILI (in-line inspection) results, wall thickness measurements, anomaly history
- Assess remaining productive life of facilities vs CPR economic limit
- Topsides life extension: cost and risk if facilities need to operate past design life

**Red Flags 🔴:**
- Facilities >30 years old without documented major life extension programme
- Open Tier 1 integrity findings from BSEE/NSTA inspection with no close-out plan
- Water handling at or near capacity with rising WC forecast (will require costly upgrade)
- ILI results showing active external or internal corrosion not in repair programme
- Compression failures causing chronic production downtime not reflected in CPR

---

#### Focus Area T7: Data Room Completeness — Technical

**VDR Technical Checklist (13 categories — Agent 01 checks against this list):**

| # | Category | Key Documents Expected |
|---|----------|----------------------|
| 1 | CPR & Appendices | Full CPR PDF + all technical appendices + economic model if available |
| 2 | Well Logs | LAS/DLIS files for ALL wells; wireline logs; mudlog; composite logs |
| 3 | Production Data | Monthly actuals by well by stream (oil, gas, water, NGL) — minimum 3 years |
| 4 | Pressure Data | RFT/MDT data, BHP surveys, reservoir pressure history, pressure decline analysis |
| 5 | Seismic | SEG-Y volumes, interpretation reports, maps, seismic data licence confirmations |
| 6 | PVT & SCAL | PVT reports, EOS model, core analysis, SCAL data, fluid samples |
| 7 | Facilities Engineering | Inspection reports, HAZOP, SIL assessments, topsides drawings, mechanical datasheets |
| 8 | Production Chemistry | Scale programme, corrosion programme, hydrate management, chemical injection records |
| 9 | Regulatory — Technical | BSEE/NSTA inspection records (3yr), open findings, CAI, NOVs |
| 10 | Pipeline Integrity | ILI results, anomaly reports, repair records, cathodic protection surveys |
| 11 | Well Integrity | Cement records (bond logs), casing surveys, annular pressure records, mechanical status |
| 12 | Environmental Baseline | Seabed surveys, water quality monitoring, habitat assessments |
| 13 | Development Plans | FDPs, well prognoses, drilling AFEs, rig contracts, supply chain commitments |

Any missing document from this list triggers a P1 item on the Data Request List (DRL).

---

#### Focus Area T8: Reservoir Pressure & Drive Mechanism

**What the team does:**
- Identify the primary drive mechanism from pressure and production data:
  - **Solution gas drive (depletion drive):** Reservoir pressure declines rapidly. GOR rises as pressure drops below bubble point. High recovery risk without injection.
  - **Water drive:** Aquifer supports pressure. Lower GOR rise. Rising WC is the tradeoff. Recovery can be high if swept efficiently.
  - **Gas cap drive:** Gas cap expands into oil column. GOR rises. Must manage gas cap carefully to prevent early gas breakthrough.
  - **Compaction drive:** Rock compaction drives production. Common in chalk and unconsolidated sands (e.g., Valhall, GoM deepwater). Subsidence risk.
  - **Pressure maintenance (injection):** Waterflooding or gas injection maintains pressure. Most controlled drive mechanism.
- Current reservoir pressure vs initial (depletion %) — calculate and compare to CPR assumption
- If waterflood: VRR (Voidage Replacement Ratio): injection volumes vs production volumes. VRR <1 = under-injection = pressure decline.
- EOR potential: quantify upside from CO2-EOR, polymer flooding, surfactant — only risked upside

**Red Flags 🔴:**
- Depletion drive only with pressure well below bubble point and no injection programme
- No injection history on a field producing >5 years with declining pressure
- Compaction risk present but not quantified in subsidence study
- VRR <0.8 on an active waterflood (significant under-injection)

---

#### Focus Area T9: Seismic Data Licensing & Ownership

**What the team does:**
- Confirm for every seismic dataset: is it owned outright by the target entity, or licensed?
  - **Owned:** typically acquired by target company or predecessor; free to transfer
  - **Licensed (multi-client):** licensed from TGS, CGG Veritas, PGS, Schlumberger WesternGeco — check the licence agreement for assignability
- Confirm all interpretation products, processed volumes, and software licences are transferable
- If licensed: identify the licensor, confirm they will grant transfer/consent, and assess transfer fee

**Red Flags 🔴:**
- Key seismic licensed from TGS/CGG/PGS with no-transfer clause — transfer fee can be $2–10M+
- Proprietary seismic data owned by seller's parent company (not the entity being sold) — requires separate licence negotiation
- Critical exploration areas with no seismic coverage at all
- Software licences for interpretation (Petrel, Kingdom) not transferable — buyer needs own licences

---

#### Focus Area T10: Post-Acquisition Upside Mapping

**What the team does:**
- Map all prospective resources identified in CPR and any internal exploration studies
- Quantify unrisked NPV (no chance of success applied) at buyer's assumptions
- Apply buyer's GPoS (geological probability of success) to compute risked NPV
- Identify near-term, lower-risk opportunities: behind-pipe, bypassed pay, recompletions, sidetracks
- Cost each opportunity: workover cost, expected production uplift, payback period
- Prioritise by risked NPV — this forms the basis of the post-acquisition drilling inventory

**Output:** Unrisked / Risked NPV by opportunity; opportunity matrix (cost vs risked NPV); Year 1 priority list

**Red Flags 🔴:**
- All upside requires frontier exploration (GPoS <10%) — speculative; high discount required in valuation
- Upside relies on unproven play concepts without analogue well control in the basin
- Behind-pipe intervals identified but no downhole data (logs, cores) to confirm commerciality

**Pro-Forma Technical View:**
- Combined company 1P/2P/3P reserves and RLI (years)
- Pro-forma production profile: decline curve applied to combined portfolio
- Portfolio-level decline mitigation: how does new asset extend group production life?
- Combined drilling inventory depth (years of locations at planned pace)

---

### 3.2 Financial / Commercial Workstream

**Team:** Finance analysts, corporate development, FP&A, tax specialists
**Primary Objective:** Build an independent financial model. Validate or challenge all seller economics. Determine the value range and optimal bid strategy.
**Aigis Agents:** Agent 04 (Finance Calculator) · Agent 05 (Price Curves) · Agent 12 (Liability Schedule) · Agent 13 (Comps Finder) · Agent 15 (Sensitivity Analyser)

---

#### Focus Area F1: Historical Financials Audit (3–5 Years)

**What the team does:**
- Obtain audited financial statements (IFRS or US GAAP) for last 3–5 fiscal years
- Review auditor's report: unqualified (clean), qualified (specific issues), emphasis of matter, going concern
- Assess accounting policies: revenue recognition, reserve estimation methodology, policy changes, impairment triggers
- Analyse trend analysis: revenue, EBITDA, operating cash flow, capex vs budget, free cash flow
- Verify all royalty and production tax payments are current — outstanding obligations = Day-1 liability
- Review any restatements, accounting changes, or corrections — flag for legal and financial model

**Red Flags 🔴:**
- Qualified auditor opinion or going concern language — implies financial stress
- Significant recent impairment (e.g., $45M impairment on failed PUDs — signals written-off drilling programme)
- Mid-period accounting standard changes that make year-over-year comparison misleading
- Large, recurring "non-recurring" items — suggests systematic financial issues presented as one-offs
- Royalty payments in arrears — creates statutory liability that accrues interest

---

#### Focus Area F2: LOS (Lease Operating Statement) Validation

The LOS is the asset-level P&L for oil and gas properties. It is the starting point for all financial analysis.

**What the team does:**
- Obtain LOS for all assets covered by the transaction — minimum 3 years of monthly data
- Reconcile LOS revenue lines to actual purchaser statements: cash receipts from oil/gas buyers must tie to LOS
- Any gap between LOS and actual cash receipts = unverified revenue (discount it)
- Verify opex categories:
  - LOE (Lease Operating Expense): routine production costs
  - Well workover: one-off intervention costs — are they truly one-off?
  - Facilities maintenance: routine vs capital
  - Production taxes: severance, ad valorem
  - Insurance
  - G&A allocation: is the overhead allocation appropriate for a standalone asset?
- Compute unit costs: $/boe by category for each year — identify trends
- Normalise for non-recurring items to get a run-rate view of true operating cost

**Red Flags 🔴:**
- LOS carries a disclaimer: "unaudited" or "not verified" — all data requires independent confirmation
- G&A allocation appears underallocated (seller keeping some costs in parent entity to inflate asset economics)
- Workovers presented as one-off but recurring in every year — structural cost, not exceptional
- Revenue not reconcilable to purchaser statements — potential undisclosed deductions (transport, processing)

---

#### Focus Area F3: Buyer's Independent Financial Model

**What the team does:**
Build a DCF/NAV model from scratch using ONLY independently validated inputs (NOT seller's model):

| Input | Source |
|-------|--------|
| Production forecast | Agent 02 (production DB) — buyer's independent decline model |
| Oil/gas price deck | Agent 05 (live CME/ICE/EIA forward curves) |
| Royalties and NRI | Agent 09 (contract extractor) — from actual JOA/licence documents |
| Opex (LOE, G&A) | Validated LOS + Agent 14 (benchmarking) |
| Capex (wells, facilities) | Technical team's independent cost estimate |
| ARO | Agent 10 — P50 base case, P90 for sensitivity |
| Fiscal terms | Tax analysis from legal/tax team |
| Discount rates | 8%, 10%, 12%, 15% — produce output at all four |

**Key model outputs:**
- PV-10 (SEC standard — PDP only at 12-month average pricing)
- NAV at multiple discount rates (8/10/12/15%)
- IRR (unlevered)
- Payback period
- EV/2P at modelled EV

This model is the FOUNDATION for all bid pricing. It is the buyer's truth. Everything is sourced and cited.

---

#### Focus Area F4: Seller Model Reverse-Engineering

**What the team does (Agent 15):**
- Obtain seller's financial model or NAV summary from VDR
- Re-run the model with buyer's validated inputs — identify the "value gap"
- Compute the seller premium: how much of the seller's NAV is based on aggressive assumptions?

**Common sources of seller optimism:**
| Assumption | Seller's Version | Buyer's Version | Typical Gap |
|-----------|-----------------|----------------|------------|
| Production profile | Uses P10 or CPR optimistic case | Uses independently fitted P50 | 10–25% |
| Oil price deck | Uses long-dated strip + $5 premium | Uses CME forward curve | 5–15% EV impact |
| Opex | Excludes G&A overhead | Includes standalone G&A | 10–20% |
| Capex | Pre-inflation rig cost assumptions | Current market dayrates | 10–30% |
| ARO | P50 or below | P70 for conservatism | $2–10M gap |
| Discount rate | 8% | 10–12% | 15–25% NAV gap |

**Red Flags 🔴:**
- Seller's model uses P10 production but labels it P50 — must be identified and called out
- Seller's NAV >30% above buyer's independently derived NAV at same oil price — structural disagreement requiring resolution
- No financial model provided (opacity = risk)

---

#### Focus Area F5: Sensitivity & Scenario Analysis

**What the team does (Agent 15 + Agent 04):**
Build full tornado / scenario analysis on buyer's base case.

**Variables to sensitise:**

| Variable | Base Case | Downside | Severe Downside |
|---------|-----------|---------|----------------|
| Oil price | Forward curve | −$10/bbl | −$20/bbl |
| Production | Base | −10% | −20% |
| Opex | Base | +15% | +30% |
| Capex | Base | +20% | +40% |
| ARO | P50 | P70 | P90 |
| Decline rate | CPR P50 | +5%/yr | +10%/yr |
| First production | On schedule | +6 months | +12 months |
| Discount rate | 10% | 12% | 15% |

**Key outputs:**
- Tornado chart: top 3 value drivers, top 3 value risks
- NPV/IRR at each scenario
- Break-even price: at what oil price does the acquisition break even at the bid price?
- Break-even production: at what % production shortfall does the IRR drop below WACC?
- Maximum viable bid price: at each downside scenario, what is the maximum price that keeps IRR ≥ hurdle?

---

#### Focus Area F6: Working Capital & Effective Date Adjustments

**What the team does:**
- Confirm effective date: the economic date from which production revenue and costs accrue to buyer
  - Typically 3–6 months before signing in competitive processes
  - All production revenue and costs from effective date to close belong to the buyer (locked-box) or are settled in a completion accounts adjustment
- Calculate production revenue from effective date to close:
  - Net production (boe) × realised price ($/boe) − royalties − opex = net cash
- Identify all liabilities outstanding at close: vendor AP, director loans, shareholder loans, intercompany balances
- Identify all receivables at close: unpaid production invoices, insurance claims, tax refunds
- Build settlement sheet: Purchase Price ± effective date adjustment ± net liabilities

**Key formula:**
```
Adjusted Purchase Price = Headline EV
  + Net liabilities at close (debt + hedge MTM + contingent)
  − Net receivables at close
  ± Effective date revenue/cost adjustment
  ± Working capital normalisation
```

**Red Flags 🔴:**
- Large vendor AP not disclosed in IM — undisclosed liability
- Significant deferred maintenance capex accruing between effective date and close (increases effective price)
- Working capital peg not clearly defined in SPA — creates post-close dispute risk

---

#### Focus Area F7: Tax Structure & Fiscal Terms

**What the team does:**
- Identify corporate tax position: current liability, deferred tax assets (DTA), deferred tax liabilities (DTL), NOL carryforwards
- Assess change-of-control tax triggers:
  - Does acquisition trigger recognition of DTLs?
  - Can buyer obtain a step-up in tax basis (asset deal vs corporate M&A — critical difference)
- Review all royalty obligations: government, landowner, ORRI holders — each reduces NRI
- Severance tax and ad valorem tax obligations — verify current payments
- International: withholding taxes on dividends/interest if cross-border structure

**Asset deal advantage:** Buyer gets a step-up in tax basis to purchase price. All future depreciation/depletion is based on acquisition cost = higher tax shield. Typically worth 10–20% of purchase price in NPV terms.

**Corporate M&A:** Buyer inherits seller's existing tax history and basis. No automatic step-up. Lower headline cost but losing the step-up benefit.

**Red Flags 🔴:**
- Unquantified deferred tax liabilities that crystallise on CoC
- NOL carryforwards subject to Section 382 limitation (US) post-acquisition — value may be constrained
- Unknown ORRI/royalty holders further reducing NRI below JOA/CPR assumed

---

#### Focus Area F8: Debt, Hedging & Liability Schedule

**What the team does (Agent 12):**
- Extract all debt facilities: amount, maturity, interest rate, covenants, CoC provisions
- Check every credit agreement for: change of control definition, prepayment obligation, consent requirements
- Extract hedge book: all commodity hedges (oil/gas) and interest rate swaps — notional, instrument type, strike price, maturity, counterparty
- Calculate hedge MTM (Mark to Market) at current forward curves (Agent 05 provides live curves):
  - Positive MTM = asset (hedge is in the money for seller)
  - Negative MTM = liability (hedge is out of the money for seller) — buyer inherits this at close
- Build Day-1 liability waterfall:
  1. Gross debt (face value of all facilities)
  2. + Hedge MTM (if negative = liability)
  3. + Contingent liabilities (litigation, ARO shortfall, tax)
  4. + Other payables (vendor AP, director loans, shareholder loans)
  5. = Total Day-1 liabilities
  6. − Cash and equivalents at close
  7. = Net Day-1 liability

**Red Flags 🔴:**
- CoC clause in credit facility triggers full prepayment — requires immediate refinancing at close
- Hedge book deeply out-of-the-money: negative MTM >15% of bid price
- Covenants breach at combined entity's pro-forma leverage (requires lender consent)
- Undisclosed related-party loans (director, shareholder, parent) — common in founder-led businesses

---

#### Focus Area F9: Pro-Forma Combined Company Financials

**What the team does:**
- Build combined entity balance sheet as of Day-1: buyer's existing + acquired assets
- Deduct acquisition price and financing to get opening leverage position
- Model combined EBITDA and free cash flow for 5-year outlook
- Quantify synergies:
  - G&A overlap: which seller corporate functions are duplicated?
  - Infrastructure sharing: combined throughput reduces unit opex
  - Procurement leverage: larger volumes reduce well service costs
  - Technology/operational efficiency transfer from buyer to acquired asset
- Stress-test leverage: compute ND/EBITDA at $50, $65, $80, $100/bbl Brent
- Assess dividend/buyback capacity: is deal accretive or dilutive to shareholder returns?
- Compute NAV/share accretion or dilution at various bid levels

---

#### Focus Area F10: Bid Construct & Walk-Away Price

**What the team does:**
Establish EV range using multiple methodologies — never rely on just one:

| Methodology | What It Measures | Weight Typical |
|------------|-----------------|---------------|
| **DCF/NAV** | Buyer's base case NPV at 10% | High weight — fundamental value |
| **PV-10** | SEC standard PDP only | Moderate — conservative floor |
| **EV/2P comps** | Market pricing of 2P reserves | High weight — what market pays |
| **EV/boepd comps** | Market pricing of current production | Moderate — useful for PDP-heavy assets |
| **EV/EBITDA** | For corporate M&A with full financials | High for corporate; low for asset deal |

- **Walk-away price:** Maximum price at which the acquisition still meets all return hurdles (IRR, ROCE, payback)
- **Bid price:** What to submit as the binding offer — typically below walk-away to leave room for negotiation
- **Stretch price:** Maximum price that could be justified under very favourable assumptions — only reach for this if needed to win
- **Escalation authority:** Who can approve bid above bid price up to walk-away; above walk-away requires Board approval

**Pro-Forma Financial View:**
- Combined NAV/share and EPS accretion/dilution at various bid levels
- Post-close leverage at $65 Brent base case
- Synergy NPV and timeline (discounted to Day-1 value)
- Reserve Replacement Ratio (RRR) improvement from acquisition

---

### 3.3 Legal / Land Workstream

**Team:** In-house legal counsel, external energy M&A counsel, land/title specialists
**Primary Objective:** Confirm the target owns what it claims to own. Map all consents, liabilities, and deal-certainty risks. Negotiate SPA protection.
**Aigis Agents:** Agent 09 (Contract Extractor) · Agent 11 (Regulatory Checker) · Agent 16 (Title Validator) · Agent 06 (Q&A Synthesis)

---

#### Focus Area L1: Title & Chain of Ownership

**What the team does:**
- Obtain the full chain of title for every licence, lease, well, and pipeline in scope
- Trace every assignment in the chain from the original grant to the current holder
- Each assignment must be: (a) executed by all parties, (b) filed with the relevant regulator, (c) consented by government if required
- Verify WI% three-way match — must be consistent across ALL three sources:
  1. JOA (the contractual source of WI%)
  2. CPR (the engineering source — must use the correct NRI to compute revenue)
  3. IM / financial model (the commercial source)
  Even a 0.5% discrepancy in WI% is material on a large asset — flag immediately.
- Identify any cloud on title: liens, mortgages, encumbrances, adverse claims, lis pendens
- Look for deeds of covenant: prior owners may have ongoing obligations that affect title

**Three-Way WI% Reconciliation Table (Agent 16 output):**
| Licence | Well | JOA WI% | CPR WI% | IM WI% | Status |
|---------|------|---------|---------|--------|--------|
| Licence A | Well 1 | 50.00 | 50.00 | 50.00 | ✅ Match |
| Licence B | Well 4 | 37.50 | 37.50 | 37.00 | 🔴 Mismatch |

**Red Flags 🔴:**
- Missing executed assignment anywhere in the chain — creates title gap that may be uninsurable
- WI% mismatch across JOA, CPR, and IM — signals an error in one or more documents
- Expired lease with no renewal in place — asset technically not owned by seller
- Lien or mortgage on a producing licence — must be discharged at or before close
- Unresolved adverse title claim or litigation involving the licence

---

#### Focus Area L2: JOA Key Terms Extraction

**What the team does (Agent 09):**
Extract and summarise the following terms from every Joint Operating Agreement:

| JOA Term | Why It Matters | What to Flag |
|----------|---------------|-------------|
| WI% and NRI% per party | Revenue and cost split — must match CPR and IM | Any mismatch with CPR/IM |
| Operator designation | Who runs the asset — will buyer be operator? | Operator removal provisions (can buyer remove existing operator?) |
| AFE threshold | Below which non-consent is triggered | Low AFE threshold = frequent partner votes on every spend |
| Non-consent penalty | Recoupment multiplier before non-consenting party recovers | >500% penalty = aggressive deterrent to non-consent |
| ROFR/ROFO trigger | What triggers partner pre-emption rights | Asset sale vs corporate M&A — does chosen structure avoid trigger? |
| ROFR exercise period | Days to exercise pre-emption right | Long period (>60 days) = deal timeline risk |
| Decommissioning cost-sharing | How ARO is split between parties | Ensure obligations consistent with ARO model |
| Governing law | Jurisdiction for dispute resolution | English law / Texas law / Norwegian law — affects interpretation |
| Insurance requirements | Minimum coverage required of operator | Ensure buyer can meet requirements from Day 1 |
| Default cure period | Grace period before a partner is in default | Short cure period = exposure to technical default |

**Red Flags 🔴:**
- ROFR held by a strategic competitor — high probability of exercise
- CoC clause triggers ROFR even on corporate M&A structure — requires waiver or restructuring
- AFE threshold <$100K — means partner approval required for almost every spend
- No clear operator removal provision — buyer may be stuck with existing operator
- Governing law from a jurisdiction buyer's legal team is unfamiliar with (e.g., unusual African jurisdiction)

---

#### Focus Area L3: Licence & Permit Status

**What the team does (Agent 11):**
For every licence/lease in scope:

| Check | Source | Red Flag |
|-------|--------|----------|
| Expiry date | Licence document | Expiry within 24 months with no extension plan |
| Extension options | Licence document | No extension right; discretionary renewal only |
| Minimum Work Obligations (MWO) | Licence document + regulator | Outstanding MWO not disclosed in IM |
| Relinquishment obligations | Licence document | Upcoming relinquishment of prospective acreage |
| Government back-in rights | Licence document / PSC | Government right to acquire WI at specified terms |
| Change of Control consent | Licence document + regulator | Required — must be obtained before close |
| Operator qualification | Regulator | Buyer may need to demonstrate competency to regulator |

**US GoM specific:**
- BOEM: consent to assign a federal OCS lease is mandatory
- BSEE: operator qualification assessment
- Financial assurance (ARO bond): BOEM may require additional bonding upon assignment

**UKCS specific:**
- NSTA: consent to assign under Petroleum Act 1998 — mandatory
- NSTA financial fitness assessment: buyer must demonstrate financial capability
- Change of operator: separate NSTA process; can take 60–120 days

**Red Flags 🔴:**
- Licence has outstanding MWOs that must be completed before expiry — capital commitment not in seller's capex plan
- Government back-in right exercisable at acquisition — significantly reduces WI
- Regulator has previously indicated concern about buyer's financial fitness for this basin

---

#### Focus Area L4: ROFR / ROFO — Partner Pre-Emption Risk

**What the team does:**
- Map ALL partners in ALL licences and confirm whether they hold ROFR or ROFO rights
- Confirm the trigger: does the proposed transaction structure trigger the ROFR?
  - **Asset deal:** almost always triggers ROFR (direct transfer of WI)
  - **Corporate M&A (share purchase):** may or may not trigger, depending on JOA wording
  - **Chevron/Hess/Exxon case study (2024):** Chevron structured deal as corporate M&A believing ROFR didn't apply; ExxonMobil (Hess's GoM co-venturer) argued it did; went to arbitration — illustrates the risk
- Estimate likelihood of ROFR exercise: does the partner have:
  - Financial capacity to match the bid?
  - Strategic interest in the asset?
  - History of exercising ROFR in this basin?
- Mitigation strategies:
  1. Negotiate ROFR waiver from each holder (seller typically leads this process)
  2. Structure transaction to avoid trigger (if legally defensible)
  3. Price the deal knowing ROFR may reduce final acquired WI

**Timeline impact of ROFR:**
- Typical notice period: 30 days from notification
- Matching period: 15–30 days after notice
- ROFR exercise can delay close by 60–90 days minimum

**Red Flags 🔴:**
- Strategic competitor holds ROFR and has publicly stated interest in GoM/UKCS consolidation
- Multiple ROFR holders — probability of at least one exercising increases with each additional holder
- JOA contains "piggyback" ROFR — one partner's exercise entitles others to join

---

#### Focus Area L5: Regulatory Consent to Assign

**What the team does (Agent 11):**
Build the **Consent-to-Assign Tracker** — the gating document for deal timeline:

| Regulator | Jurisdiction | Requirement | Typical Timeline | Gating? |
|-----------|-------------|------------|-----------------|---------|
| BOEM | US GoM | Consent to assign federal OCS lease | 90–120 days | ✅ Hard gate to close |
| BSEE | US GoM | Operator qualification (if assuming operatorship) | 30–60 days | ✅ Hard gate |
| NSTA | UKCS | Consent to assign under Petroleum Act | 60–90 days | ✅ Hard gate |
| NPD | Norway | Ministry of Petroleum consent | 90–120 days | ✅ Hard gate |
| FTC/DOJ | US antitrust | HSR filing if deal >$111M | 30 days Phase 1; up to 12 months Phase 2 | Sometimes |
| CMA | UK antitrust | If UK turnover >£70M | 40 working days Phase 1 | Sometimes |

**Key questions per consent:**
- What information does the regulator require from buyer? (Financial statements, business plan, track record)
- Has the buyer obtained consent from this regulator before in this basin?
- Are there any pending regulatory issues with the selling entity that could slow consent?
- Are any conditions likely (e.g., BOEM requiring additional ARO bond posting)?

**Red Flags 🔴:**
- Buyer has no prior track record with BOEM/NSTA — consent process will be more intensive
- Seller has outstanding NOVs or enforcement actions pending with BOEM/BSEE/NSTA — may complicate consent
- HSR threshold triggered: deal likely to attract scrutiny if combined market share >25% in any basin

---

#### Focus Area L6: Environmental Liability & Permitting

**What the team does:**
- Review all environmental permits: current, valid, and applicable to ongoing operations
  - SPCC (Spill Prevention, Control & Countermeasure Plan) — must be current, PE-certified
  - NPDES (National Pollutant Discharge Elimination System) — produced water discharge
  - Clean Air Act Title V or minor source permits
- Check EPA and state agency databases for open enforcement actions, NOVs, fines
- Review Phase I Environmental Site Assessment (ESA): identifies recognised environmental conditions (RECs)
- Review Phase II ESA if Phase I identified RECs: sampling and analysis of soil/groundwater
- Identify any ongoing remediation: scope, cost estimate, regulatory sign-off timeline, indemnity provisions
- Assess Natural Resource Damage (NRD) exposure: if contamination has affected public resources, NRD claims can be large and uncertain

**Red Flags 🔴:**
- Active EPA or state agency enforcement action with uncapped liability
- Soil or groundwater contamination with no Phase II and no cost estimate
- SPCC plan not updated after facility modification — regulatory violation
- Outstanding NOVs not disclosed in IM (Agent 11 or Agent 08 should have flagged)
- NRD claim filed or anticipated — value uncertain; consider escrow or price reduction

---

#### Focus Area L7: Material Contracts Review

**What the team does (Agent 09):**

**Priority contract categories for extraction:**

| Contract Type | Key Terms to Extract | Red Flag |
|--------------|---------------------|----------|
| **Offtake/Crude Sales** | Pricing (index, premium/discount), term, termination, ToP obligations, CoC clause | Above-market price commitment expiring shortly (revenue at risk); ToP with volume above forecast |
| **Gas Sales Agreement** | Pricing, take-or-pay %, delivery point, quality specs, term, force majeure | Take-or-pay commitment requiring delivery buyer cannot achieve |
| **Gathering/Processing** | MVC (minimum volume commitment), dedication (all production must flow), rates, capital reimbursements, term | Punitive MVC penalties; full dedication preventing alternate routes |
| **Transportation** | Tariff, capacity reservation, shipper status, firm vs interruptible | Above-market capacity reservation with no release mechanism |
| **SWD (Saltwater Disposal)** | Disposal rates, capacity, exclusivity, term, CoC clause | Insufficient SWD capacity for rising WC volumes |
| **Drilling contracts** | Rig dayrate, contract duration, early termination fee, CoC clause, assignability | Multi-year above-market commitment; early termination fee >$20M |
| **Helicopter/Marine logistics** | Term, rates, exclusivity, assignability | Non-assignable critical logistics contract |

**Red Flags 🔴:**
- Midstream MVC penalties capable of exceeding free cash flow in a production shortfall scenario
- Full field dedication (all production must flow through one midstream provider) — no flex, no competition
- Non-assignable contracts requiring third-party consent with no indication of willingness to consent
- Early termination fees in drilling or logistics contracts materially impacting deal economics

---

#### Focus Area L8: Employment & Key Personnel

**What the team does:**
- Identify all employees associated with the assets (if asset deal) or the target entity (if corporate M&A)
- TUPE (UK Transfer of Undertakings — Protection of Employment): all employees whose work is "mainly connected" with the assets transfer automatically; cannot be dismissed for transfer-related reasons
- WARN Act (US): if >100 employees and >50 lose jobs, 60-day advance written notice required
- Map critical skill dependencies: who holds unique knowledge (subsurface models, regulatory relationships, operational know-how)?
- Assess retention risk: are key people likely to leave post-announcement? What is the cost of their departure?
- Review pension plans: defined benefit shortfalls are a hidden liability; defined contribution is clean
- Non-compete and non-solicitation: are they enforceable in the relevant jurisdiction? Adequate duration?

**Red Flags 🔴:**
- Critical subsurface geologist or reservoir engineer has no non-compete and has received competing offers
- Defined benefit pension plan with material funding deficit not quantified in IM
- TUPE consultation not completed before announcement — constructive dismissal risk
- Key technical staff have short notice periods (1 month) — competitor could immediately hire them post-announcement

---

#### Focus Area L9: Litigation & Contingent Liabilities

**What the team does:**
- Obtain litigation register: all pending, threatened, and recently settled cases
- Categories most common in upstream E&P:
  1. Personal injury (worker or contractor) — GoM has significant litigation exposure
  2. Environmental claims (soil, water, marine contamination)
  3. Contractual disputes (JOA, midstream, service contracts)
  4. Royalty underpayment (class actions in US onshore; individual claims offshore)
  5. Regulatory enforcement (BSEE, EPA, OSHA)
- Obtain legal counsel's assessment of: likelihood of adverse outcome, estimated range (low/high)
- Check insurance coverage: E&P liability, D&O, environmental — is the claimed amount within coverage?
- Check survival of seller's indemnity: if corporate acquisition, buyer needs seller to indemnify for pre-close claims
- **Class action risk:** Royalty underpayment class actions can be $50M+ for large GoM producers — check for any indication

**Red Flags 🔴:**
- Personal injury litigation with >10 claimants and no insurance coverage
- Royalty underpayment class action filed or threatened
- Environmental enforcement proceeding with potential criminal exposure for officers
- Open litigation involving JOA partners — affects ability to operate or drill

---

#### Focus Area L10: SPA / PSA Drafting & Red Lines

**What the team does:**
- Lead the negotiation of the Sale and Purchase Agreement (SPA) or Purchase and Sale Agreement (PSA)
- Establish and defend buyer's non-negotiable positions (red lines)
- Seek standard upstream M&A protections; be prepared for seller resistance

**Buyer's Standard Red-Line Positions:**

| Term | Buyer's Standard Position | Why |
|------|--------------------------|-----|
| Fundamental reps (title, authority, anti-bribery, environmental) | Indefinite survival; uncapped indemnity | These represent existential risk to the investment |
| General business reps survival | 24–36 months | Standard market; enough time to discover issues |
| General reps indemnity cap | 100% of purchase price | Market standard; anything below 50% is seller-friendly |
| Environmental indemnity | 7-year survival; 100% cap | Contamination issues take years to surface |
| MAC (Material Adverse Change) | Broadly defined; commodity price fluctuation NOT excluded from reps | Protects against deterioration in asset between sign and close |
| Price adjustment for ARO | Adjust to P70 at close | P50 is most likely but P70 provides buffer |
| W&I Insurance | Strongly preferred | Provides clean exit for both parties; underwriting cost 1–1.5% of coverage |
| Effective date | As early as possible | Captures more production revenue for buyer |
| Completion accounts | Locked-box with agreed leakage provisions | Provides price certainty; avoids post-close disputes |

**Pro-Forma Legal View:**
- Combined entity JOA rationalisation (overlapping interests in same licences)
- Group-level ROFR exposure across combined portfolio
- Intercompany agreement clean-up (eliminate related-party arrangements)
- Combined regulatory consent calendar (all consents required across combined portfolio)

---

<!--
=============================================================================
END OF PART 2
Next file: Aigis_DD_DomainKnowledge_PART3_Workstreams_HSE_Operational_Strategic.md
=============================================================================
-->
