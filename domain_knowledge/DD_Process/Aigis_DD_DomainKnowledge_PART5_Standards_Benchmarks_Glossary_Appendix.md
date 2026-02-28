<!--
=============================================================================
PART 5 OF 5 — Aigis DD Domain Knowledge Document
File: Aigis_DD_DomainKnowledge_PART5_Standards_Benchmarks_Glossary_Appendix.md
Covers: Section 6 Output Standards | Section 7 Industry Benchmarks |
        Section 8 Glossary | Section 9 Regulatory References |
        Section 10 Change Log | Appendix A Gold-Standard VDR Checklist
Assembles after PART 4. This is the final section.
=============================================================================
-->

## SECTION 6: OUTPUT STANDARDS & CITATION REQUIREMENTS

> **For the Aigis System Coordinator:** Every output from every agent must comply with the standards defined in this section. These are non-negotiable. They exist to ensure that every answer is traceable, auditable, and defensible in front of an Investment Committee or a court of law.

---

### 6.1 Citation-Mandatory Standard

**Rule:** Every factual claim in every agent output must carry a source citation. No exceptions. No fact without a source.

This rule exists because:
- Energy M&A is a high-stakes, legally sensitive process
- Mistakes cost millions; unsourced claims cannot be challenged or verified
- The Investment Committee will ask "where does this number come from?" for every material figure
- Post-close litigation risk is real — the DD process must be auditable

**Citation Schema (JSON):**

```json
{
  "fact": "[statement of fact, in plain English]",
  "source_doc": "[exact filename as it appears in VDR]",
  "source_section": "[section title, table name, or description]",
  "page": [page number as integer, or null if not applicable],
  "extracted_verbatim": "[exact quote from document supporting the fact — max 20 words]",
  "confidence": "HIGH | MEDIUM | LOW",
  "conflict_note": "[if this fact conflicts with another source, describe the conflict here — otherwise null]"
}
```

**In human-readable output, citations appear inline:**

> *"The CPR P50 reserve estimate for Field A is 5.2 MMboe."*
> Source: `Byron_CPR_Sep2025.pdf`, Section 4 — Reserve Summary Table, p.47.
> Extracted: *"Total Proved + Probable (2P) — Field A — 5.2 MMboe."*
> Confidence: HIGH (single authoritative source, independently certified).

---

### 6.2 Confidence Level Definitions

| Level | Definition | Action Required |
|-------|-----------|----------------|
| **HIGH** | Single authoritative source. Audited, independently certified, or from a signed regulatory document. No conflicting data from any other source. | Use in calculations and IC memo with confidence. |
| **MEDIUM** | Source is unaudited or management-prepared. Consistent with other sources but not independently verified. No conflict. | Flag as unaudited in outputs. Seek corroborating source if possible. |
| **LOW** | Conflicting data across two or more sources. Agent has selected the most credible/conservative value but uncertainty remains. | 🔴 Flag for human review. Do NOT use in IC calculations without human sign-off. State both values and the conflict in the output. |
| **INFERRED** | No explicit source — value inferred from related data (e.g., NRI inferred from stated WI% and royalty rate). | Clearly label as inferred. State the inference logic. Seek direct source to upgrade to MEDIUM. |

---

### 6.3 Red Flag Severity Classification

All agents apply the following severity classification to every finding:

| Level | Symbol | Criteria | Required Action |
|-------|--------|----------|----------------|
| **Critical** | 🔴 | Variance >10% from expected; any title gap; potential deal-breaker risk; unresolved safety case; ROFR exercise risk; CoC debt trigger; WI% mismatch | Human acknowledgement REQUIRED before downstream use. Surface in IC memo. Consider price adjustment or deal withdrawal. |
| **Moderate** | 🟡 | Variance 5–10% from expected; elevated cost vs benchmark; material contract risk that can be mitigated; licence expiry 12–24 months | Document in risk register. Consider price adjustment request. Include in IC memo risk section. |
| **Minor** | 🟢 | Variance <5% from expected; within normal operating range for this asset type; no financial impact material enough to affect bid | Document in workstream DD report. Include in full risk register for completeness. No IC escalation required. |
| **Informational** | ℹ️ | Noteworthy context with no quantifiable risk — e.g., change in management, industry trends, ESG context | Include in IC memo for completeness and context. No action required. |
| **Data Gap** | ❓ | Expected document not in VDR; expected data field not populated | Raise on DRL as P1/P2/P3. Do not make assumptions in the absence of data — flag the gap explicitly. |

---

### 6.4 Human-in-the-Loop Gates

The following finding types require explicit human review and acknowledgement before any downstream agent uses the finding as an input to calculations or recommendations:

| Trigger | Gate Level | What Human Must Do |
|---------|-----------|-------------------|
| Any 🔴 Critical finding | Mandatory | Acknowledge the finding; confirm whether to proceed, adjust price, or escalate to IC |
| Fatality or Tier 1 LOPC in HSE record | Mandatory | Review full incident report; decide whether to proceed |
| Any WI% mismatch across JOA/CPR/IM | Mandatory | Confirm correct WI% with legal counsel before using in any calculation |
| Any LOW confidence fact used in financial model | Mandatory | Sign off on the assumed value or seek a better source |
| Agent 19 overall score < 50/100 | Mandatory | Senior BD Lead must review scorecard before IC memo is finalised |
| Any CoC debt trigger identified | Mandatory | Legal and finance must confirm resolution plan before bid submission |
| ROFR holder known to be a strategic competitor | Mandatory | BD Lead must assess ROFR exercise probability and brief IC |

**Human acknowledgement is recorded in `_master_findings.json`:** Set `"human_acknowledged": true` with the reviewer's name and timestamp.

---

### 6.5 Output File Structure — Per Deal

All Aigis outputs for a deal are organised in the following standard folder structure. This ensures consistency across all transactions and enables easy navigation during IC preparation and post-close review.

```
{deal_code}/                          ← e.g., PROJECT_CORSAIR/
├── 01_vdr_inventory/
│   ├── vdr_inventory.json
│   ├── gap_analysis_report.md
│   └── data_request_list.docx        ← DRL issued to seller
│
├── 02_production_db/
│   ├── production.db                 ← SQLite database
│   ├── conflict_log.md
│   └── data_dictionary.md
│
├── 03_consistency_audit/
│   ├── consistency_audit.md
│   └── consistency_summary.xlsx
│
├── 04_finance/
│   ├── buyers_base_case_model.xlsx   ← Buyer's independent model
│   └── [calculation_outputs/]        ← Per-query outputs from Agent 04
│
├── 05_price_curves/
│   ├── price_curves.json             ← Timestamped live fetch
│   └── price_deck_comparison.md
│
├── 06_qa_log/
│   └── qa_log.md                     ← All queries + Agent 06 responses
│
├── 07_well_cards/
│   ├── well_cards.pdf
│   └── well_portfolio_summary.xlsx
│
├── 08_hse/
│   └── hse_risk_summary.md
│
├── 09_contracts/
│   ├── contract_summary_pack.docx
│   └── red_flag_register.md
│
├── 10_aro/
│   ├── aro_summary.md
│   └── aro_waterfall.xlsx
│
├── 11_regulatory/
│   ├── regulatory_status.md
│   └── consent_to_assign_tracker.xlsx
│
├── 12_liabilities/
│   ├── day1_liability_waterfall.xlsx
│   └── debt_covenant_tracker.md
│
├── 13_comps/
│   ├── comps_table.xlsx
│   └── comps_narrative.md
│
├── 14_benchmarking/
│   └── cost_benchmarking.md
│
├── 15_sensitivity/
│   ├── sensitivity_analysis.xlsx
│   └── base_case_validation.md
│
├── 16_title/
│   ├── title_chain.md
│   └── wi_reconciliation.xlsx
│
├── 19_risk_scorecard/
│   ├── deal_risk_scorecard.pdf       ← One-page IC traffic light
│   └── risk_register.xlsx           ← Full ranked risk register
│
├── 20_integration_plan/
│   ├── 100day_integration_plan.docx
│   └── day1_action_checklist.xlsx
│
└── _master_findings.json             ← All agent findings aggregated
                                         Input to Agent 19 risk scorecard
```

---

## SECTION 7: INDUSTRY BENCHMARKS REFERENCE

> **For the Aigis System Coordinator:** Use these benchmarks when agents are challenging seller assumptions, benchmarking costs, or flagging metrics as elevated/in-line/conservative. Always cite the source and note the vintage of the benchmark.

---

### 7.1 Production & Operating Cost Benchmarks

**US Gulf of Mexico — Offshore Shelf (<500m water depth)**

| Metric | Low (Efficient) | Typical | High (Flag) | Source |
|--------|----------------|---------|-------------|--------|
| Lifting cost (LOE $/boe) | $8–12 | $15–22 | >$30 | BSEE/EIA |
| G&A allocation ($/boe) | $1–3 | $3–6 | >$8 | EIA |
| Platform opex ($/boe) | $5–10 | $10–18 | >$25 | Rystad |
| Shallow water well cost ($M) | $3–6 | $8–15 | >$20 | BSEE well cost survey |
| Deepwater well cost ($M) | $30–60 | $80–150 | >$200 | BSEE/Rystad |
| Annual production decline | 8–12% | 15–20% | >25% | BSEE production data |
| Initial well rate (bopd, shelf) | 100–500 | 500–2,000 | >3,000 | BSEE TIMS |
| Unplanned downtime (%) | <2% | 3–6% | >8% | IOGP |

**UK Continental Shelf (UKCS)**

| Metric | Low | Typical | High (Flag) | Source |
|--------|-----|---------|-------------|--------|
| Unit opex ($/boe) | $15–20 | $25–35 | >$45 | NSTA performance data |
| Producing well count per field | 2–5 | 5–20 | — | NSTA |
| Average field production (boepd) | 500–2,000 | 2,000–20,000 | — | NSTA |
| UKCS well cost (£M) | £15–25 | £30–50 | >£80 | NSTA/OGA |
| UKCS unplanned downtime | <3% | 4–7% | >10% | NSTA |

---

### 7.2 Decommissioning / ARO Benchmarks

| Asset Type | P50 Estimate | P90 Estimate | Key Drivers | Source |
|-----------|-------------|-------------|-------------|--------|
| GoM shelf well P&A (<200m) | $0.5–2M | $2–5M | Depth, casing, tubulars, well age | BSEE TIMS |
| GoM deepwater well P&A (>200m) | $10–20M | $20–40M | Water depth, subsea equipment | BSEE/Rystad |
| GoM fixed platform removal (small) | $5–20M | $15–40M | Platform size, water depth | BSEE |
| GoM fixed platform removal (large) | $20–80M | $50–150M | Jacket weight, transport | BSEE |
| GoM MOPU/SPAR decommissioning | $100–300M | $200–500M | Mooring, subsea, pipelines | BSEE/industry |
| UKCS fixed platform (small, <10k tonnes) | £20–80M | £40–150M | Topsides weight, jacket, pipeways | NSTA |
| UKCS fixed platform (large, >10k tonnes) | £80–300M | £150–600M | Size, water depth, export routes | NSTA/OGUK |
| UKCS subsea well P&A | £5–15M | £10–30M | Depth, completion type, age | NSTA |
| UKCS FPSO decommissioning | £100–400M | £200–700M | Vessel size, mooring, connections | NSTA/OGUK |
| UKCS pipeline removal (per km) | £0.5–2M | £1–4M | Diameter, burial depth, contents | NSTA |

**Key rule:** If P90 > 1.5× P50, the estimate has high uncertainty → recommend price adjustment clause in SPA rather than accepting P50 at face value.

---

### 7.3 M&A Valuation Benchmarks (2022–2025)

**US Gulf of Mexico**

| Asset Type | EV/2P ($/boe) | EV/1P ($/boe) | EV/boepd ($000s) | Period |
|-----------|--------------|--------------|-----------------|--------|
| GoM shallow shelf (PDP-heavy) | $4–10 | $8–20 | $15–40 | 2022–2025 |
| GoM deepwater (development) | $6–18 | $10–30 | $30–70 | 2022–2025 |
| Distressed GoM shelf assets | $2–6 | $4–12 | $8–20 | 2022–2025 |

**UKCS**

| Asset Type | EV/2P ($/boe) | EV/boepd ($000s) | Period |
|-----------|--------------|-----------------|--------|
| UKCS producing (PDP-heavy) | $4–12 | $15–45 | 2022–2025 |
| UKCS development assets | $3–10 | $10–30 | 2022–2025 |
| UKCS distressed / late-life | $2–6 | $5–20 | 2022–2025 |

**US Onshore (for comparison)**

| Basin | EV/2P ($/boe) | EV/boepd ($000s) | Period |
|-------|--------------|-----------------|--------|
| Permian Basin | $10–30 | $30–70 | 2022–2025 |
| Eagle Ford | $6–18 | $20–50 | 2022–2025 |
| DJ Basin | $5–15 | $15–40 | 2022–2025 |

**Note on using comps:** EV/2P is the most widely used metric for upstream M&A. Always check whether the comparable's reserves are SEC or SPE-PRMS standard, and what proportion of value is PDP vs PUD vs exploration. Like-for-like comparison requires similar reserve category composition.

---

### 7.4 Carbon / GHG Intensity Benchmarks

| Region / Asset Type | Typical Carbon Intensity | Elevated Flag | Source |
|--------------------|------------------------|---------------|--------|
| GoM offshore | 8–15 kgCO2e/boe | >25 kgCO2e/boe | EIA/IOGP |
| UKCS offshore | 15–25 kgCO2e/boe | >40 kgCO2e/boe | NSTA/IOGP |
| Middle East conventional | 5–10 kgCO2e/boe | >15 kgCO2e/boe | IOGP |
| Permian Basin (shale) | 15–30 kgCO2e/boe | >50 kgCO2e/boe | EIA |
| Heavy oil (oil sands) | 50–100+ kgCO2e/boe | >100 kgCO2e/boe | IOGP |

**Carbon Cost NPV Sensitivity (apply in Agent 18 and Agent 04 outputs):**

| Carbon Price Scenario | Source | Application |
|----------------------|--------|-------------|
| $30/tonne CO2e | Current EU ETS / voluntary market floor | Minimum — apply as base case |
| $50/tonne CO2e | IEA Stated Policies 2030 | Central case |
| $80/tonne CO2e | IEA Announced Pledges 2030 | Stress case |
| $150/tonne CO2e | IEA Net Zero Emissions 2030 | Extreme stress / long-dated |

---

### 7.5 Financial Metric Hurdles (Typical Large/Mid-Cap O&G)

| Metric | Minimum Acceptable | Preferred | Notes |
|--------|-------------------|---------|-------|
| Unlevered IRR | 12% | 15–20% | At $65/bbl Brent base case |
| Discount rate (NAV) | 8–10% | 10–12% | Company-specific; verify against WACC |
| Payback period | <8 years | <5 years | At base case oil price and production |
| Post-close ND/EBITDA | <3.0x | <2.0x | Pro-forma at $65/bbl |
| ROCE | >WACC | WACC + 3–5% | Year 3 stabilised ROCE |
| EV/2P premium vs comps | — | <20% above market | Justify premium with synergies or upside |
| Break-even oil price | <$45/bbl | <$35/bbl | Unlevered; full-cycle |

---

### 7.6 Safety / HSSE Benchmarks (IOGP)

| Metric | Industry Benchmark | Elevated Flag | Source |
|--------|-------------------|--------------|--------|
| TRIR (Total Recordable Incident Rate per 200k hrs) | 0.5–1.5 | >2.0 | IOGP Report 2023 |
| LTI Rate | 0.1–0.4 | >0.6 | IOGP Report 2023 |
| Tier 1 LOPC events per 100M hrs | 1–4 | >6 | IOGP/PSER 2023 |
| Tier 2 LOPC events per 100M hrs | 5–20 | >30 | IOGP/PSER 2023 |
| Regulatory INC rate (US GoM) | <5% of inspections | >15% | BSEE annual stats |
| Open corrective actions >6mo old | <10% of total open | >25% | NSTA benchmarks |

---

## SECTION 8: GLOSSARY

| Term | Definition |
|------|-----------|
| **AFE** | Authority for Expenditure — budget approval document for a specific well or project activity. Threshold in JOA triggers partner voting rights. |
| **ARO** | Asset Retirement Obligation — accounting and actual cost to decommission and abandon a well, platform, pipeline, or subsea infrastructure at end of life. |
| **BAFO** | Best and Final Offer — final round binding bid in a competitive M&A process. |
| **BOPD / Boepd** | Barrels of oil per day / Barrels of oil equivalent per day. 1 boe = 1 bbl oil = 6 Mscf gas (US convention). |
| **BOEM** | Bureau of Ocean Energy Management — US federal agency responsible for offshore energy leasing and resource management. |
| **BSEE** | Bureau of Safety and Environmental Enforcement — US federal agency responsible for offshore safety, environmental compliance, and production oversight. |
| **BHP** | Bottom Hole Pressure — pressure measured at the wellbore in the reservoir. Key input to decline modelling and drive mechanism analysis. |
| **CIM / IM** | Confidential Information Memorandum (same as IM — Information Memorandum) — detailed document prepared by seller describing the asset; provided after NDA execution. |
| **CoC** | Change of Control — provision triggered when ownership of a company or a controlling interest changes. Common in JOAs, debt facilities, and material contracts. |
| **CPR** | Competent Person's Report — independent report certifying reserves and resources, prepared by an accredited technical expert (Competent Person). |
| **COP** | Cessation of Production — the point at which an asset stops producing economically. Triggers P&A and decommissioning obligations. |
| **DRL** | Data Request List — numbered list of missing VDR documents requested from seller by buyer's DD team. |
| **EOR** | Enhanced Oil Recovery — any technique to increase recovery beyond primary (depletion drive) and secondary (water/gas injection). Includes CO2 EOR, polymer flooding, surfactant. |
| **EV** | Enterprise Value — total company value = equity market capitalisation + net debt (or bid price + net debt assumed/paid off). The primary M&A pricing metric. |
| **FDP** | Field Development Plan — technical and commercial plan for developing an oil/gas field, submitted to regulator for approval. |
| **F&D Cost** | Finding and Development cost — total exploration/development capex ÷ net reserve additions. $/boe metric for capital efficiency. |
| **GoM** | Gulf of Mexico. |
| **GOR** | Gas-Oil Ratio — cubic feet (or Mscf) of gas produced per barrel of oil. Rising GOR indicates reservoir depletion and gas cap expansion. |
| **GPoS** | Geological Probability of Success — the probability that a well will encounter commercial hydrocarbons. Used to risk prospective resources. |
| **HSR** | Hart-Scott-Rodino — US antitrust pre-merger notification requirement. Required if deal value exceeds the annual threshold (~$111M in 2024). |
| **HAZOP** | Hazard and Operability Study — structured process safety review of a facility's design and operating procedures. |
| **IC** | Investment Committee — the senior decision-making body that approves acquisitions. Typically CFO + CEO + Board level. |
| **ILI** | In-Line Inspection — pipeline integrity inspection using an instrumented "pig" tool. Detects wall thinning, corrosion, and dents. |
| **IOGP** | International Association of Oil and Gas Producers — industry body setting safety, environmental, and operational standards. |
| **JOA** | Joint Operating Agreement — the contractual framework governing co-owners (working interest holders) of a licence. Defines WI%, operatorship, AFE, voting, ROFR, decommissioning. |
| **LOPC** | Loss of Primary Containment — unintended release of a hydrocarbon or other hazardous substance from the primary containment system. |
| **LOE** | Lease Operating Expense — the routine costs to produce from a well or field: chemicals, repair, labour, production taxes, insurance. |
| **LOS** | Lease Operating Statement — asset-level profit and loss account for an oil and gas property. |
| **LTI** | Lost Time Injury — a workplace injury that results in the employee being unable to work for one or more days. |
| **MAC** | Material Adverse Change / Effect — a contractual condition in an SPA allowing a party to walk away if a fundamental change occurs between signing and closing. |
| **MDT / RFT** | Modular Dynamic Tester / Repeat Formation Tester — wireline tools used to measure reservoir pressure and take fluid samples. |
| **MVC** | Minimum Volume Commitment — a minimum throughput obligation in a midstream gathering/processing contract. Non-delivery triggers cash penalties. |
| **NAV** | Net Asset Value — the sum of discounted cash flows from all assets, less all liabilities. The primary valuation methodology for upstream E&P. |
| **NBIO** | Non-Binding Indicative Offer — a first-round bid letter indicating a price range and conditions. Non-binding — no legal obligation to close. |
| **NDA** | Non-Disclosure Agreement — confidentiality agreement signed before receiving deal information. |
| **NPI** | Net Profits Interest — a right to a percentage of net profits (revenues less specified costs) from production. Value depends on profitability. |
| **NPD** | Norwegian Petroleum Directorate — Norwegian regulator for petroleum activities on the Norwegian Continental Shelf. |
| **NRI** | Net Revenue Interest — the working interest holder's share of gross production revenue after deducting all royalties. NRI = WI × (1 − royalty rate). |
| **NSTA** | North Sea Transition Authority — the UK upstream oil and gas regulator (formerly the Oil and Gas Authority / OGA). |
| **NOV** | Notice of Violation — regulatory enforcement notice issued by BSEE, NSTA, EPA, or other authority for non-compliance. |
| **NRD** | Natural Resource Damage — claims by government for damage to public natural resources (wetlands, fisheries, groundwater) caused by contamination. |
| **OWC / GOC** | Oil-Water Contact / Gas-Oil Contact — the depth boundaries between oil, gas, and water in a reservoir. |
| **ORRI** | Overriding Royalty Interest — a royalty interest carved out of a working interest by a prior owner. Reduces the NRI of the current WI holder without reducing their WI%. |
| **P&A** | Plug and Abandon — the permanent decommissioning of a wellbore using cement plugs. Creates legal COP and extinguishes most regulatory obligations for the well. |
| **PDP** | Proved Developed Producing — the most certain category of reserves (wells are already producing). |
| **PDNP** | Proved Developed Non-Producing — wells drilled and completed but not producing (shut-in or behind-pipe). |
| **PSA** | Purchase and Sale Agreement — the legal document governing an asset acquisition in the US. Equivalent to SPA. |
| **PUD** | Proved Undeveloped — undrilled reserves locations within the spacing unit of PDP wells, committed to within 12 months. |
| **PV-10** | Present Value of future net cash flows discounted at 10% per annum. The SEC standard measure for PDP reserves valuation. |
| **RFT** | Repeat Formation Tester — wireline tool measuring reservoir pressure and collecting fluid samples. See MDT. |
| **RLI** | Reserve Life Index — 2P reserves ÷ annual production rate = years of remaining production at current rate. |
| **ROFR** | Right of First Refusal — the contractual right to match any third-party offer for an asset or interest before the seller can accept it. |
| **ROFO** | Right of First Offer — the contractual right to receive a first offer from a selling party before they can market to third parties. |
| **RRR** | Reserve Replacement Ratio — new reserves added ÷ annual production. A ratio >100% indicates reserve growth; <100% indicates depletion of the reserve base. |
| **SCAL** | Special Core Analysis Laboratory — detailed laboratory measurements of reservoir rock properties (relative permeability, capillary pressure) used for reservoir modelling. |
| **SEC** | Securities and Exchange Commission (US). For reserves purposes: the SEC standard requires proved reserves to be based on 12-month average pricing and meet a strict certainty threshold. |
| **SEMS** | Safety and Environmental Management System — the safety management framework required by BSEE for US offshore operators. |
| **SIL** | Safety Integrity Level — a measure of risk reduction provided by a safety system. Rated SIL 1–4. Used in HAZOP/SIL studies. |
| **SPA** | Sale and Purchase Agreement — the binding legal agreement governing a corporate acquisition (share purchase). |
| **SPE-PRMS** | Society of Petroleum Engineers — Petroleum Resources Management System. The international standard for classifying and reporting petroleum resources and reserves. |
| **STOIIP / GIIP** | Stock Tank Oil Initially in Place / Gas Initially in Place — the total volume of hydrocarbons in a reservoir before production begins. Recovery factor × STOIIP = ultimate recoverable reserves. |
| **TIMS** | Technical Information Management System — BSEE's public-facing database for US offshore well, production, and inspection data. |
| **TRIR** | Total Recordable Incident Rate — safety metric: (number of recordable incidents × 200,000) ÷ total hours worked. |
| **TSA** | Transition Services Agreement — agreement for the seller to continue providing specified back-office or operational services to the buyer for a defined period post-close. |
| **TUPE** | Transfer of Undertakings (Protection of Employment) Regulations — UK law automatically transferring employees and their terms and conditions when a business or asset transfer occurs. |
| **VDR** | Virtual Data Room — a secure, access-controlled online repository containing all deal documents made available by the seller to prospective buyers. |
| **VRR** | Voidage Replacement Ratio — ratio of injected fluid volume to produced fluid volume in a waterflood or gas injection scheme. VRR <1 = under-injection = reservoir pressure decline. |
| **W&I Insurance** | Warranty and Indemnity Insurance — insurance policy covering the buyer's loss from warranty breaches by the seller. Commonly used in M&A to provide a clean seller exit and certainty for the buyer. |
| **WC** | Water Cut — the percentage of produced fluid that is water. Rising water cut = increasing aquifer influx or injection water breakthrough = higher disposal costs. |
| **WI** | Working Interest — the percentage ownership interest in a licence or lease. The WI holder bears its proportionate share of all costs. |

---

## SECTION 9: KEY REGULATORY REFERENCES & DATABASES

These are the primary free-to-access regulatory databases that Aigis agents query for live data.

| Authority / Database | Jurisdiction | What to Access | Free? | URL |
|---------------------|-------------|---------------|-------|-----|
| **BOEM** — Bureau of Ocean Energy Management | US GoM (federal offshore) | Lease status, lease assignments, ROFR history, financial assurance orders, block maps | ✅ Free | https://www.boem.gov |
| **BSEE TIMS** | US GoM | Well data, inspection records, incidents, production by field/lease | ✅ Free API | https://www.bsee.gov/tools-and-data |
| **NSTA Data Portal** | UKCS | Licence data, well data, field production, CPRs (some), decommissioning programmes, company profiles | ✅ Free | https://www.nstauthority.co.uk/data-centre |
| **NSTA Field Data** | UKCS | Field-level production, operator history, licence rounds | ✅ Free | https://www.nstauthority.co.uk/exploration-production/fields |
| **NPD Factpages** | Norway | Well, field, company, and production data | ✅ Free | https://www.npd.no/en/facts |
| **SEC EDGAR** | US listed companies | 8-K filings (M&A announcements), 10-K (reserves + financials), 10-Q (quarterly) | ✅ Free | https://www.sec.gov/edgar |
| **EIA — Energy Information Administration** | US | Oil/gas price data, production data, drilling cost surveys, well count | ✅ Free | https://www.eia.gov |
| **CME / NYMEX (via yfinance)** | Global | WTI crude (CL), Henry Hub gas (NG) forward curves | ✅ Free via API | https://www.cmegroup.com |
| **ICE (Intercontinental Exchange)** | Global | Brent crude (B), UK NBP gas forward curves, EU/UK ETS carbon prices | ✅ Limited free; full API paid | https://www.theice.com |
| **World Bank Commodity Markets** | Global | Long-dated oil/gas price forecasts | ✅ Free | https://www.worldbank.org/en/research/commodity-markets |
| **IOGP Safety Data** | Global | TRIR, LOPC rates, safety benchmarks by region | ✅ Free (PDF reports) | https://www.iogp.org/safety-data |
| **OGUK / OEUK** | UKCS | Economic reports, unit operating cost data, decommissioning forecasts | ✅ Free reports | https://www.oeuk.org.uk |

**Paid / Subscription Databases (for future integration):**

| Database | What It Provides | Typical Cost |
|----------|----------------|-------------|
| PLS News Wire | US upstream M&A deal flow, transaction database | $5–15K/year |
| GlobalData O&G | Reserves, production, deals, company financials | $20–50K/year |
| Enverus (Drillinginfo) | US onshore/GoM production, deals, well data | $20–80K/year |
| Wood Mackenzie | Global upstream assets, valuations, market intelligence | $50K–$500K/year |
| Rystad Energy | Global upstream benchmarking, cost data, ARO estimates | $30K–$200K/year |

**Note for Agent development:** Always prioritise free sources first. Only recommend paid sources when free alternatives do not provide sufficient data quality or coverage for the specific task.

---

## SECTION 10: CHANGE LOG

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 26 February 2026 | Aaditya / Aigis Analytics | Initial release. Full 5-part document covering all 6 deal phases, 6 workstreams (10 focus areas each), VDR workflow, 20-agent catalogue, output standards, benchmarks, glossary, regulatory references. |
| | | | *Next scheduled update: after Project Corsair DD completion — incorporate live findings as real-world test cases for each agent's output.* |

**Versioning Convention:**
- `v1.x` — Minor additions/corrections to existing content
- `v2.0` — Major structural revision or addition of new workstream/phase
- `v[X]_[YYYYMMDD].md` — File naming convention

**Update Triggers (when to update this document):**
- After completing a real DD process: incorporate findings as concrete examples per section
- When a new agent is built and validated: add to Section 5.1 with full attribute table
- When industry benchmarks change materially (e.g., post-rig-rate cycle)
- When regulatory changes affect DD process (e.g., new BSEE/NSTA requirements)
- When a new deal type or geography is added to Aigis scope

---

## APPENDIX A: GOLD-STANDARD VDR CHECKLIST

*This is the master checklist used by Agent 01 to generate the gap analysis and Data Request List (DRL). Every item is classified by Priority (P1 = must have; P2 = important; P3 = useful) and Workstream.*

### TECHNICAL (13 Categories)

| # | Document | Priority | Workstream | Notes |
|---|----------|---------|-----------|-------|
| T1 | CPR (Competent Person's Report) — full report with all appendices | P1 | Technical | Include economic model if available |
| T2 | CPR economic model / spreadsheet | P1 | Technical + Financial | Essential for base case validation |
| T3 | Well logs — LAS/DLIS for ALL wells | P1 | Technical | Composite logs, wireline petrophysical logs |
| T4 | Monthly production data by well by stream (oil, gas, water, NGL) — minimum 3 years | P1 | Technical | Foundation of production database |
| T5 | Reservoir pressure history (RFT/MDT/BHP surveys) | P1 | Technical | Critical for drive mechanism |
| T6 | Seismic data: SEG-Y volumes (or access), interpretation reports, structural maps | P1 | Technical | Confirm licence transferability |
| T7 | PVT reports and fluid samples | P1 | Technical | Essential for flow modelling and surface facilities |
| T8 | SCAL data (special core analysis) and routine core analysis | P2 | Technical | Needed for detailed reservoir modelling |
| T9 | Petrophysical analysis (formation evaluation reports, per well) | P1 | Technical | Cross-check to CPR pay/reserves |
| T10 | Facilities engineering: inspection records, topsides drawings, HAZOP, SIL assessments | P1 | Technical + Operations | Key for integrity and ARO assessment |
| T11 | Production chemistry: scale, corrosion, hydrate management records and chemical programmes | P2 | Technical + Operations | Identifies operational cost drivers |
| T12 | Pipeline ILI results, anomaly reports, and repair records | P1 | Technical + HSE | Active corrosion is a potential deal issue |
| T13 | Well integrity files: cement bond logs, casing surveys, annular pressure monitoring | P1 | Technical + HSE | Regulatory obligation; expensive to remediate |
| T14 | Environmental baseline surveys (seabed, water quality) | P2 | HSE | Needed for contamination baseline |
| T15 | Development plans: FDPs, well prognoses, drilling AFEs, long-lead item orders | P1 | Technical + Operations | Validates capex programme |
| T16 | Mudlogs and drilling reports for all wells | P2 | Technical | Secondary data source for formation evaluation |

### COMMERCIAL / LEGAL (12 Items)

| # | Document | Priority | Workstream | Notes |
|---|----------|---------|-----------|-------|
| L1 | All JOAs — executed versions and all amendments | P1 | Legal | Every licence must have its JOA |
| L2 | All licence/lease documents — original + renewals/extensions | P1 | Legal | Confirm expiry and MWO status |
| L3 | Chain of title — all executed assignment deeds since original grant | P1 | Legal | Each must be filed and consented |
| L4 | ROFR correspondence — any notices, waivers, prior exercise history | P1 | Legal | Critical for deal certainty |
| L5 | All offtake / crude sales agreements | P1 | Legal + Commercial | Price, term, ToP, termination |
| L6 | All midstream agreements (gathering, processing, transport) | P1 | Legal + Commercial | MVC exposure, dedication, assignability |
| L7 | All SWD (saltwater disposal) agreements | P2 | Legal + Operations | Rising WC = rising SWD dependency |
| L8 | All active drilling contracts and significant service frame agreements | P1 | Legal + Operations | Commitment and early termination cost |
| L9 | Regulatory correspondence — NOVs, enforcement letters, consents, conditions | P1 | Legal + Regulatory | Open regulatory matters |
| L10 | ROFR/ROFO holders registry (seller-prepared summary) | P1 | Legal | Confirms all pre-emption rights |
| L11 | Historical ROFR waiver records — confirm no outstanding unresolved ROFR history | P2 | Legal | Pattern of exercise is a red flag |
| L12 | Seismic data licence agreements (multi-client and proprietary) | P1 | Legal | Confirm transferability of all data |

### FINANCIAL (9 Items)

| # | Document | Priority | Workstream | Notes |
|---|----------|---------|-----------|-------|
| F1 | Audited financial statements — 3+ years (IFRS or US GAAP) | P1 | Financial | Must include auditor's report |
| F2 | Lease Operating Statements (LOS) — asset-level, 3+ years monthly | P1 | Financial | Foundation for cost validation |
| F3 | Seller's financial model / NAV model | P1 | Financial | Required for reverse-engineering (Agent 15) |
| F4 | All debt facility agreements — executed + all amendments | P1 | Financial | CoC provisions, covenants, maturity |
| F5 | Hedge book schedule — all open commodity and interest rate hedge positions | P1 | Financial | MTM at current prices can be large liability |
| F6 | Tax returns and HMRC/IRS correspondence — 3+ years | P1 | Financial | Deferred tax, NOLs, open enquiries |
| F7 | Annual budget and 5-year business plan | P1 | Financial + Strategic | Baseline for IC assumptions |
| F8 | Working capital schedule — AP, AR, accruals at close | P1 | Financial | Settlement sheet inputs |
| F9 | Management accounts (most recent 12 months monthly) | P2 | Financial | Bridges audited accounts to current trading |

### HSE / ENVIRONMENTAL (8 Items)

| # | Document | Priority | Workstream | Notes |
|---|----------|---------|-----------|-------|
| H1 | Safety Case (offshore) — current, regulator-accepted version | P1 | HSE | Expired safety case = immediate 🔴 |
| H2 | HSSE Management System documentation | P1 | HSE | Maturity and implementation evidence |
| H3 | Incident register — all reportable incidents, 5 years | P1 | HSE | IOGP classification; fatalities auto-flag |
| H4 | ARO estimate / decommissioning cost study (latest version) | P1 | HSE + Financial | Agent 10 input |
| H5 | Environmental permits — SPCC, NPDES, CAA Title V (or minor source) | P1 | HSE | Currency and compliance |
| H6 | BSEE/NSTA inspection records — 3 years | P1 | HSE + Regulatory | Open findings, NOVs, enforcement |
| H7 | Phase I Environmental Site Assessment | P1 | HSE | Baseline contamination |
| H8 | Phase II Environmental Site Assessment (if Phase I identified RECs) | P1 | HSE | Quantifies remediation cost |

### CORPORATE / HR / INSURANCE (7 Items)

| # | Document | Priority | Workstream | Notes |
|---|----------|---------|-----------|-------|
| C1 | Corporate structure chart — full legal entity structure with ownership % | P1 | Legal + Financial | Required for share purchase structure |
| C2 | Employee list — all employees, role, location, remuneration, notice period | P1 | Operations + Legal | TUPE/WARN assessment |
| C3 | Key employment contracts — management team + critical technical staff | P1 | Operations + Legal | Non-compete, notice period, PILON |
| C4 | Pension plan documentation — type, valuation, funding level | P1 | Financial + Legal | DB shortfall = hidden liability |
| C5 | Current insurance policies — all types (E&P liability, D&O, property, workers' comp) | P1 | Legal + Operations | Coverage adequacy vs open claims |
| C6 | Insurance claims history — 5 years | P2 | Legal | Material claims indicate risk profile |
| C7 | Litigation register — all pending, threatened, and recently settled matters | P1 | Legal | Open claims must be quantified |

---

*End of Appendix A.*

---

*This is the end of Part 5 and the full Aigis DD Domain Knowledge Document.*

*To assemble the complete document: concatenate Parts 1 through 5 in order, then remove all assembly instruction comment blocks (marked with `<!-- =====...===== -->`).*

*Document maintained by Aigis Analytics. Version control naming: `Aigis_DD_DomainKnowledge_v[X]_[YYYYMMDD].md`*
*Next update: after Project Corsair DD completion.*

<!--
=============================================================================
END OF PART 5 — END OF FULL DOCUMENT
=============================================================================
-->
