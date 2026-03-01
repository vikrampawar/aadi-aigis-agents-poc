# Board-Level Due Diligence Report — Playbook
*Aigis Analytics | Domain Knowledge | Last updated: 28 Feb 2026*

---

## Purpose

This playbook defines the standard structure, methodology, and conventions for Aigis Analytics board-level DD reports on upstream oil & gas M&A transactions. Use this when asked to produce a deal summary, DD report, investment memo, or similar output for a buyer evaluating a producing asset.

---

## Standard Report Structure (14 Sections)

Every board-level DD report should follow this structure in order. Adapt section depth to available data, but never omit sections — note data gaps explicitly.

| # | Section Title | Key Content |
|---|---------------|-------------|
| 1 | Executive Summary | Deal overview, seller/asset, recommended bid range, key upside, key risks, verdict |
| 2 | Transaction Structure | Sale process type, seller background, legal entity, transaction structure (shares vs assets), deal timeline, headline ask price if known |
| 3 | Asset Portfolio | Asset-by-asset description: field name, location, vintage, working interest (WI%), net revenue interest (NRI%), current production by product, key wells, infrastructure, offshore vs onshore |
| 4 | VDR Quality Assessment | VDR coverage completeness, information gaps (prioritised), data room red flags, missing documents that must be requested before signing |
| 5 | Reserve Analysis | 1P/2P/3P reserves (MBO, MMCF, MMboe) and NPV10 by category, PDP/PNP/PUD sub-classification, reserve engineer name and effective date, CPR methodology notes, case comparison (CPR vs management) |
| 6 | Historical Production | Production history by field and total: monthly/annual rates, peak vs current, decline trends, water cut trend, operational uptime and downtime events |
| 7 | Financial Overview (LTM) | Last 12 months: revenue, LOE, G&A, EBITDAX, capex, FCF; key per-unit metrics (LOE/boe, G&A/boe); working capital assessment |
| 8 | 5-Year Financial Model | CPR base case: annual production, revenue, costs, CAPEX, FCF, cumulative FCF; model assumptions (price deck, cost escalation, discount rate) |
| 9 | Development CAPEX Programme | Well-by-well capital programme: well name, spud timing, gross cost, net cost, expected IP rate, target horizon, sanction status |
| 10 | SWOT Analysis | Strengths, weaknesses, opportunities, threats — structured bullet points; link each item to specific data source |
| 11 | Valuation Benchmarks & Deal Multiples | Implied valuation at various price points vs PDP/1P/2P NPV10; EV/boed; market comparables (recent regional transactions); bid convention guidance; recommended bid range |
| 12 | Decommissioning / ARO | ARO P50 liability, active field count and vintage, regulatory framework, operator decom track record, BSEE/MMS bonding requirements |
| 13 | Management & People | Key personnel, operational continuity risk, buyer transition requirements, any change-of-control provisions |
| 14 | Key Diligence Actions (Pre-Sign) | Prioritised list of remaining DD items with owner, criticality (🔴/🟡/🟢), and deadline |

---

## Section 5 — Reserve Analysis: Detailed Guidance

### Reserve Categories to Report (Always)

Report reserves in this sequence, matching SPE-PRMS classification:

| Category | Code | Description |
|----------|------|-------------|
| Proved Developed Producing | PDP | Producing wells, current zone; safest estimate |
| Proved Non-Producing / Behind Pipe | PNP | Proved but awaiting workover or zone switch |
| Proved Undeveloped | PUD | Approved/committed new wells or zones |
| **Total Proved** | **1P** | PDP + PNP + PUD |
| Probable (2P incremental) | 2P-inc | Additional probable reserves over 1P |
| **Total Proved + Probable** | **2P** | 1P + 2P-inc |
| Possible (3P incremental) | 3P-inc | Additional possible reserves over 2P |
| **Total Proved + Probable + Possible** | **3P** | 2P + 3P-inc |
| Prospective Resources | PR | Undrilled exploration/appraisal; not reserves |

### Gas Conversion
Use **6 mcf = 1 boe** (SPE/SEC standard for US assets). Some CPR reports may use 5.8 or 6.0 — note which convention is used and be consistent throughout.

### NPV10 Presentation
Always report NPV10 (net present value discounted at 10% per annum) alongside volumes. This is the industry-standard discount rate for reserve valuation.

---

## Section 11 — Valuation Benchmarks: Detailed Guidance

### GoM Bid Convention (Producing Assets)

**Standard practice for US Gulf of Mexico producing asset M&A:**

1. **Bid base = PDP PV10 at current NYMEX strip pricing** — Buyers anchor bids to the risked, producing-only value. The strip price (6–12 month forward curve) is used, not a long-term flat price deck.

2. **Upside sharing for near-term planned drilling** — If the seller has committed near-term wells (within 12–18 months) that are not yet PDP but are high-confidence (e.g., behind-pipe workovers, step-out wells from existing wellbores), some portion of the upside is shared via:
   - A higher headline bid price with contingent payments, OR
   - A participation structure (buyer/seller cost-share on first well), OR
   - A higher fixed price that prices in part of the well upside

3. **PUD and resource upside = buyer optionality**, not typically priced into base bid. Sellers may ask for contingent payments or carried interests to capture this upside.

4. **ARO haircut** — A dollar-for-dollar deduction for PV of ARO liability (P50 estimate at 10% discount) is typical. Buyers do not pay for future obligations.

### Typical EV/PV10 Multiples by Reserve Category (US GoM Shelf)

These benchmarks reflect historical transaction data for GoM shelf producing assets (late 2020s vintage):

| Category | Low | Mid | High | Notes |
|----------|-----|-----|------|-------|
| EV / PDP PV10 | 0.35× | 0.60× | 0.90× | Lower for heavy ARO; higher for clean, long-life PDP with low decline |
| EV / 1P PV10 | 0.25× | 0.50× | 0.75× | — |
| EV / 2P PV10 | 0.15× | 0.35× | 0.55× | — |
| EV / boed (net) | $8,000 | $14,000 | $22,000 | Wider range for GoM shelf (infrastructure-heavy) |

**Calibration factors (adjust multiple up/down):**

| Factor | Multiple Uplift | Multiple Discount |
|--------|----------------|-------------------|
| ARO exposure | — | Heavy ARO: −0.10–0.20× on EV/PDP |
| Near-term development inventory (committed wells) | +0.05–0.15× | — |
| % Oil vs gas (oil-weighted commands premium) | +0.05–0.10× | — |
| Production decline rate | — | High decline (>20% pa): −0.10× |
| Infrastructure ownership | +0.05–0.10× | — |
| Operator control | Operator premium: +0.05× | — |
| Fiscal regime clarity | — | Disputed royalties/taxes: −0.10× |

### Reference Transactions (GoM, 2020–2025)

| Transaction | Year | EV ($mm) | Production (boed) | EV/boed | Notes |
|-------------|------|----------|-------------------|---------|-------|
| Talos Energy / Enven Energy | 2022 | ~$1,100 | ~30,000 | ~$37,000 | Deep GoM; not shelf comp |
| Fieldwood Energy (Chapter 11 assets reorg) | 2021 | Various | Various | Distressed | Post-bankruptcy restructuring |
| W&T Offshore / ANKOR Energy (ANKOR acreage) | 2022 | ~$75 | ~2,500 | ~$30,000 | Deep GoM |
| Cox Oil / Castex Energy assets | 2022–2024 | Various | GoM shelf | ~$10–18k | Private shelf comps |
| Byron / Project Corsair (this deal) | 2026 | Bid TBD | ~1,350 net | TBD | Low-ARO, oil-weighted shelf |

*Note: Pure GoM shelf comparables at <5,000 boed are sparse in public records. Use EV/PDP PV10 as primary metric; EV/boed as secondary. Always validate against current strip pricing.*

### Recommended Bid Construction Methodology

```
Step 1: Establish PDP PV10 at strip → bid floor anchor
Step 2: Apply location/ARO/decline adjustment factor (0.5–0.85×)
Step 3: Add NPV of near-term committed wells at risked recovery (50% haircut)
Step 4: Subtract PV of net ARO liability (P50, discounted at 10%)
Step 5: Add strategic premium for platform/infrastructure ownership (if applicable)
Step 6: Sense-check against EV/boed and EV/1P PV10

Bid range = Step 4 result ± strategic premium

Do NOT price in PUD or PR upside in base bid → contingent payment mechanism instead
```

---

## Section 8 — Management Case vs CPR Analysis

### Always Present Both Cases When Available

When a seller provides both an independent CPR/reserve report and a management case financial model:

1. **Source both in the report** — CPR = independent view, management model = seller's operating/development assumptions
2. **Delta decomposition** — identify the primary drivers of NPV difference:
   - Production volume assumptions (decline rates, well IP rates)
   - CAPEX timing and cost per well
   - New prospects/assets included in management case but not CPR (e.g., prospective resources)
   - Price deck differences (management may use different price assumptions)
   - Cost structure assumptions
3. **Verify CAPEX alignment** — management's CAPEX plan must be internally consistent (wells drilled = CAPEX spent = production added)
4. **Flag prospective resources risk** — if management case includes PR (prospective resources), this is undrilled, speculative upside; should be treated as buyer option not base value
5. **Use CPR as the conservative base** for bid construction; management case informs upside case

### Format for Management Case Comparison Table

| Metric | 2025 ROY | 2026E | 2027E | 2028E | 2029E | 2030E | Cumulative |
|--------|----------|-------|-------|-------|-------|-------|------------|
| CPR: Daily Prod (boed) | | | | | | | — |
| MGMT: Daily Prod (boed) | | | | | | | — |
| Delta (%) | | | | | | | — |
| CPR: Revenue ($mm) | | | | | | | |
| MGMT: Revenue ($mm) | | | | | | | |
| CPR: CAPEX ($mm) | | | | | | | |
| MGMT: CAPEX ($mm) | | | | | | | |
| CPR: FCF ($mm) | | | | | | | |
| MGMT: FCF ($mm) | | | | | | | |
| CPR: Cumulative FCF ($mm) | | | | | | | |
| MGMT: Cumulative FCF ($mm) | | | | | | | |

### NPV Delta Attribution Framework

When management NPV >> CPR NPV, decompose delta into:
- **Volume delta** — production rate assumptions (primary driver in most cases)
- **New asset delta** — assets in management but not CPR (e.g., prospective resources, undrilled prospects)
- **CAPEX delta** — timing and cost differences (front-loading vs back-loading capex)
- **Price delta** — if models use different price decks
- **Residual** — rounding, structure, terminal value differences

---

## Document Reading Workflow (for Aigis Agent)

When producing a board DD report, read documents in this order:

1. **Information Memorandum (IM)** — Overview, asset descriptions, production summary, financial highlights, development plans, ARO
2. **CPR / Reserve Report** — Independent reserve volumes and NPV10 by category (PDP/PNP/PUD/1P/2P/3P/PR), effective date, price deck used, key assumptions
3. **Corporate Financial Model (CPR case)** — Annual projections: production, revenue, costs, CAPEX, FCF; validate consistency with CPR reserve report
4. **Management Case Financial Model** (if separate) — Same structure; identify additions vs CPR case
5. **Historical Financials (P&L)** — Monthly/quarterly revenue, LOE, G&A, EBITDAX; calculate LTM
6. **Production Data** — Monthly/annual well-level and field-level production; validate against financial model
7. **Legal / Title documents** — WI%, NRI%, lease expiry, preferential rights, change-of-control provisions (if available in VDR)
8. **Technical reports** — Well logs, seismic, engineering studies (if available)

---

## Key Metrics to Always Include

| Metric | Formula | Benchmark (GoM shelf) |
|--------|---------|----------------------|
| LOE per boe | Total LOE / Total boe produced | $12–25/boe |
| G&A per boe | Total G&A / Total boe produced | $3–8/boe |
| EBITDAX margin | EBITDAX / Revenue | 50–75% typical |
| Netback per boe | Revenue − LOE − G&A per boe | $20–45/boe at $70 WTI |
| Production decline (YoY) | (Prod_Y1 − Prod_Y0) / Prod_Y0 | 10–25% pa for mature shelf |
| ARO / boe (2P) | Total ARO P50 / 2P reserves (boe) | <$5/boe healthy |
| NPV10 per boe (PDP) | PDP NPV10 / PDP reserves (boe) | $20–50/boe for shelf |

---

## Red Flags to Always Check

- [ ] CPR effective date >12 months old → request update
- [ ] Material difference between CPR NPV and management model NPV (>30%) without clear explanation
- [ ] Management case includes prospective resources (PR) as base case production → high risk
- [ ] ARO/abandonment liability not quantified or understated
- [ ] Wells with suspended production not accounted for in abandonment schedule
- [ ] No audited financials (only management accounts) → financial risk
- [ ] Production decline rate accelerating → potential reservoir depletion or water breakthrough
- [ ] WI ≠ NRI (royalty burden higher than expected) → revenue haircut
- [ ] Lease expiry risk within deal period
- [ ] BSEE/MMS compliance issues, outstanding NOVs (Notice of Violation)
- [ ] Environmental incidents not disclosed in VDR

---

*This playbook should be referenced by: Agent 05 (Q&A Synthesis), Agent 06 (Report Generator), and any agent producing investment-grade DD output.*
*DK tag to use: `board_dd_report`*
