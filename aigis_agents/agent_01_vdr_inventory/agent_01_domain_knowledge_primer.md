# AGENT 01 — VDR INVENTORY & GAP ANALYST
## Domain Knowledge Primer: Upstream Oil & Gas Virtual Data Rooms

**Purpose:** Prime the Agent 01 LLM with domain knowledge to support (a) document classification,
(b) quality assessment of documents found vs. expected, and (c) intelligent gap identification
and DRL generation for upstream oil & gas M&A transactions.

**Version:** 1.0 | **Date:** 27 February 2026 | **Source:** Aigis Analytics Domain Knowledge Library

---

## SECTION 1: AGENT 01 MANDATE & SCOPE

Agent 01 is the **first agent to run on any new deal**. Before any analysis can happen, the team
needs to know what it has and what it is missing. Agent 01's job is:

1. **Crawl** — map the full VDR folder structure and every document in it
2. **Classify** — assign each document to one of 13 standard categories
3. **Score** — determine if each gold-standard checklist item is Present ✅ / Partial ⚠️ / Missing ❌
4. **Assess quality** — flag documents that are present but not fit-for-purpose
5. **Prioritise gaps** — issue a numbered DRL with P1 (critical) / P2 (important) / P3 (useful) ratings
6. **Self-learn** — propose novel document patterns for checklist enrichment

**Key principle:** A sparse or low-quality VDR does not just slow down analysis — it transfers
risk to the buyer. The buyer cannot verify what it cannot see. The DRL is the primary mechanism
for managing this risk. Issue the first DRL within 24 hours of VDR access.

---

## SECTION 2: THE 13 STANDARD VDR CATEGORIES

Use these categories to classify every document found. A document should be assigned to the
**single most relevant** category based on its primary content.

| # | Category | What belongs here | Primary Agents Downstream |
|---|----------|-------------------|--------------------------|
| 1 | **Corporate Structure** | Company reg docs, shareholder agreements, org charts, board minutes, entity tree | Agent 16 |
| 2 | **Technical / Reservoir** | CPR, reserve reports, well logs (LAS/DLIS), seismic interpretation, PVT reports, SCAL data, petrophysical studies, FDPs | Agents 02, 07, 17 |
| 3 | **Production Data** | Monthly production tables (oil/gas/water by well), allocation statements, production databases, well test reports | Agent 02 |
| 4 | **Pressure Data** | RFT/MDT/BHP surveys, pressure build-up tests, production logs, PLT data | Agents 02, 17 |
| 5 | **Commercial / Contracts** | JOAs, licence/PSC/lease documents, offtake/crude sales agreements, midstream agreements, SWD contracts, drilling contracts | Agents 09, 11, 16 |
| 6 | **Financial** | Audited accounts, LOS (Lease Operating Statements), management accounts, seller financial model, debt facilities, hedge book, tax returns, budget/5yr plan | Agents 04, 12, 15 |
| 7 | **Environmental / HSE** | Safety Case, HSSE management system docs, incident registers, HAZOP/SIL studies, environmental permits, Phase I/II ESAs, pipeline ILI reports | Agent 08 |
| 8 | **ARO / Decommissioning** | Decommissioning cost studies, ARO estimates, DSAs (Decommissioning Security Agreements), BOEM/NSTA decommissioning programme submissions | Agent 10 |
| 9 | **Regulatory** | Licence documents, BSEE/NSTA inspection records, NOVs (Notices of Violation), regulatory correspondence, consents to assign, BOEM lease status | Agent 11 |
| 10 | **PVT & SCAL** | Fluid sample lab reports, core analysis data, special core analysis, EOR fluid studies | Agent 02 |
| 11 | **HR / Employment** | Employee lists, key employment contracts, pension docs, TUPE/WARN notices, HR policies | Manual |
| 12 | **Insurance** | Current policies (E&P liability, D&O, property, workers' comp), claims history | Manual |
| 13 | **IT / Data & Seismic Licences** | Seismic data licence agreements, software licence agreements, IT systems descriptions, multi-client seismic confirmations | Agent 09 |

**When a document spans two categories** (e.g., a CPR with a financial model appendix): assign
to the primary/dominant category and note the secondary content in the inventory record.

---

## SECTION 3: GOLD-STANDARD VDR CHECKLIST — REFERENCE GUIDE

The gold-standard checklist (loaded at runtime as `gold_standard_v1.2.json`) defines the ideal
document set for an upstream oil & gas acquisition VDR. This section provides qualitative guidance
on **what "present" actually means** for each major checklist group.

### 3.1 Competent Person's Report (CPR) — The Most Important Document

**What it is:** An independent technical report certifying reserves and resources, prepared by an
accredited Competent Person (e.g., Ryder Scott, Gaffney Cline, DeGolyer & MacNaughton, NSAI, RISC).

**Minimum "Present ✅" standard:**
- Covers all producing fields/assets in the transaction
- States the reserves classification system (PRMS or SEC) and effective date
- Contains 1P/2P/3P breakdown by field and by reserve category (PDP/PDNP/PUD)
- Includes economic assumptions: price deck, discount rate, opex, capex
- Includes production forecast (P50 minimum) by field and ideally by well
- Signed by an accredited Competent Person with stated credentials

**Partial ⚠️ — downgrade to Partial if:**
- Report is >18 months old with no update or bridge note
- Report covers some but not all fields
- Economic model/spreadsheet is missing (just the narrative PDF)
- No production forecast tables (reserves stated but no profile)
- Prepared by internal management, not an independent firm
- Price deck assumptions are absent or clearly out of date vs market

**Missing ❌:** No independent reserves report of any kind; only management slide deck summaries.

**Quality red flags:**
- Very large 2C/3C relative to 1P (market-facing CPRs overstate upside)
- PUDs booked with no credible FDP or drilling commitment timeline
- Price deck >10% above current market forward strip
- Reserves not cross-checked against historical production trends

### 3.2 Production Data — The Most Verifiable Data

**What it is:** Monthly actual production by well and by fluid stream (oil, gas, water, NGL)
since first production (or minimum 3 years historical).

**Minimum "Present ✅" standard:**
- Monthly volumes, not just annual summaries
- Separated by well (not just aggregated at field level)
- Oil, gas, and water all present (water is often omitted — flag this)
- Dated consistently and reconcilable to LOS revenue figures
- Covers the period from CPR effective date to present

**Partial ⚠️:** Field-level only (no well-level split), or missing water volumes, or
significant gaps in the time series (>3 consecutive months missing).

**Missing ❌:** Only IM summary slides with round numbers; no raw data files.

**Quality red flags:**
- Data ends well before the CPR effective date (seller hiding recent decline)
- Unusually "clean" numbers (suspiciously round) — suggests manual re-entry, not raw export
- Large discrepancies between IM-stated rates and the data files

### 3.3 Joint Operating Agreement (JOA) — The Legal Foundation of the Asset

**What it is:** The contract governing co-owners of a licence. Defines working interests,
operatorship, voting thresholds, cash calls, ROFR/ROFO, default mechanics, decommissioning.

**Minimum "Present ✅" standard:**
- Executed version (signed by all parties), not just a draft
- Includes all subsequent amendments (amendments are often buried separately)
- Covers every licence/lease in the transaction — a separate JOA per licence is normal
- Key terms are legible: WI%, NRI%, ROFR holders, consent-to-assign provisions

**Partial ⚠️:** Draft only (not executed); missing one or more amendments; covers
some but not all licences.

**Missing ❌:** No JOA provided; only a summary table of WI% in the IM.

**Quality red flags:**
- ROFR holders include known strategic competitors → high exercise risk
- Very low voting thresholds for major expenditures → operator can commit non-ops
- Punitive cash call default/forfeiture provisions
- Assignment requires unanimous partner consent → deal risk if one partner is hostile

### 3.4 Licence/Lease Documents

**What it is:** The government-issued instrument granting rights to explore/produce in a
specific area (concession licence, lease, PSC, service agreement).

**Minimum "Present ✅" standard:**
- Original grant document (not just the licence number)
- All renewal/extension letters and government correspondence
- Current phase confirmed (exploration / development / production)
- Expiry dates visible and remaining term calculable
- Minimum Work Obligations (MWOs) visible for current phase

**Key jurisdiction signals to detect from document:**
- **US GoM:** Lease number format (e.g., SM-70 = Ship Shoal Block 70); BOEM-issued
- **UKCS:** Licence number format (e.g., P.xxx); NSTA/OGA-issued; North Sea
- **Norway:** Licence/Production Licence format; NPD-issued
- **International PSC:** Look for "Production Sharing Contract/Agreement" header;
  terms include "contractor," "cost oil/gas," "profit oil/gas"

### 3.5 Financial Documents — The Economic Reality Check

**Audited Accounts — "Present ✅" standard:**
- Minimum 3 years; signed audit opinion (unqualified preferred — any qualification is 🔴)
- P&L, balance sheet, cash flow statement, notes (especially Note: ARO/decommissioning)
- Under IFRS or US GAAP (note which — affects ARO treatment)

**Lease Operating Statements (LOS):**
- Asset-level (not just consolidated) — this is the source for cost validation
- Monthly granularity, minimum 24 months
- Shows: gross revenue, royalties, net revenue, LOE by category, production taxes, net income
- Essential for computing lifting cost $/boe

**Seller Financial Model:**
- The actual model file (Excel/.xlsx), not a PDF printout
- Enables Agent 15 to reverse-engineer and compare vs buyer's independent inputs
- A PDF printout without the model file → score as Partial ⚠️

### 3.6 HSE / Safety Documents

**Safety Case (offshore assets only):**
- Must be the current, regulator-accepted version
- Typically 200–1,000+ pages; should reference specific platform/facility
- **Expired safety case = immediate 🔴 Critical flag** — operations may be in breach
- If no safety case but asset is onshore: note this is expected (onshore assets don't require Safety Cases)

**HSSE Incident Register:**
- 5 years minimum
- Must classify incidents (LTI, RIF, near miss, LOPC Tier 1/2)
- Any Tier 1 LOPC event or fatality → 🔴 Critical automatic flag
- A "nil incidents" register is suspicious unless the asset is very small/new

**Environmental Permits:**
- SPCC (Spill Prevention), NPDES (discharge), CAA Title V (air) — US GoM
- Check currency: an expired permit is an active regulatory violation

### 3.7 ARO / Decommissioning Documents

**Why this matters:** ARO is often the largest hidden liability in late-life asset acquisitions.
Sellers systematically underestimate; buyers often accept P50 when P70 is more appropriate.

**Minimum "Present ✅" standard:**
- An internal or independent decommissioning cost study (not just a balance sheet footnote)
- P50 and ideally P70/P90 range
- Well-by-well and platform/structure breakdown
- Timing assumptions (CoP by well/platform)

**If only a balance sheet ARO note is present → Partial ⚠️:** The accounting provision
(often IFRS PV-based at the risk-free rate) is not the same as the actual cost estimate.

**Rule:** Always compare the balance sheet provision to the CPR decommissioning section.
If the balance sheet provision is >20% below CPR P50 → 🔴 flag for Agent 10.

---

## SECTION 4: VDR QUALITY SIGNALS — BEYOND PRESENCE/ABSENCE

A document can be present but still not fit for purpose. Agent 01 should assess **quality**
where the content is accessible, not just presence.

### 4.1 Positive Quality Signals (well-prepared seller VDR)

- Consistent naming conventions throughout (dates, version numbers, asset names)
- Documents indexed with a cover sheet or table of contents at folder level
- CPR economic model provided alongside the narrative PDF
- Production data exported directly from the production system (not manually re-keyed)
- JOA and licence documents include cover sheets explaining each document's role
- Q&A module pre-populated with seller-initiated clarifications
- Data room index provided by seller (cross-reference against actual contents)
- Multiple data formats provided (PDF for reading + Excel/CSV for analysis)
- Documents updated within the last 3–6 months (check file creation/modification dates)

### 4.2 Negative Quality Signals (poorly-prepared or obstructive seller VDR)

- Large number of "placeholder" folders with no content
- Production data provided only in PDF format (not exportable to database)
- CPR provided without economic model or appendices
- Old documents: accounts >2 years old, production data ending 12+ months ago
- Inconsistent working interest figures across different documents (suggests internal confusion)
- Key contracts provided as unsigned drafts only
- Safety Case present but date-stamped >5 years old without a revision history
- Seismic data referenced in CPR but no licence agreement or data access confirmed
- All regulatory correspondence absent (too convenient — likely being withheld)
- Financial model locked/password-protected (treat as "Missing" for analysis purposes)
- Documents named generically (e.g., "Document1.pdf", "Report.xlsx")

### 4.3 Jurisdiction-Specific Completeness Flags

**US Gulf of Mexico (GoM):**
- BOEM/BSEE financial assurance documentation should be present (ARO bonding orders)
- SEMS (Safety and Environmental Management System) documentation required
- SPCC Plan is mandatory for offshore facilities
- Production data can be cross-checked against public BSEE TIMS database
- Lease status and assignments can be verified via public BOEM GIS data
- If seller has SM70 or similar leases expiring in <3 years → flag expiry against MWOs

**UK Continental Shelf (UKCS):**
- Safety Case (installation/pipeline) is a regulatory requirement — must be present
- NSTA Stewardship Survey responses (if available) provide independent view on field management
- Field Development Plan (FDP) approval letter from NSTA should be in VDR for development assets
- Decommissioning Programme submission to NSTA should be available for late-life assets
- TUPE regulations apply to any employees — employment roster essential

**International / PSC regimes:**
- PSC document is paramount — must include: cost recovery cap, profit split mechanism,
  work obligation schedule, state participation terms, stabilisation clause
- Host government consent to assign is almost always required (often takes 3–6 months)
- Local content requirements should be documented
- Flag if PSC is close to exploration phase expiry without declared commerciality

---

## SECTION 5: DRL PRIORITISATION FRAMEWORK

When generating the Data Request List, every missing or partial item must be tagged P1, P2, or P3.

### P1 — Must Have (issue within 24 hours; deal cannot proceed without)

A document is P1 if its absence creates one or more of:
- **Inability to value the asset** (no CPR, no production data, no financial model)
- **Unverifiable title** (no JOA, no licence, no chain of title)
- **Unknown regulatory exposure** (no safety case, no environmental permits for operating facility)
- **Hidden liability risk** (no ARO estimate, no decommissioning study for late-life asset)
- **Legal closing risk** (no identification of consent-to-assign requirements)

**Default P1 documents:** CPR (full + model), production data (monthly/well-level), audited
accounts (3yr), JOAs (all licences), licence documents (all), LOS (24mo), financial model,
safety case (offshore), ARO study, environmental permits (H1, H7 equivalents in checklist).

### P2 — Important (request by Day 3; will constrain analysis quality)

A document is P2 if its absence:
- Limits the quality/precision of analysis but doesn't block valuation
- Creates known uncertainty that must be disclosed at IC
- Is a standard document any well-run E&P operator should have

**Typical P2:** SCAL data, PVT reports, pipeline ILI results, well integrity files, detailed
opex breakdown by category, individual well AFEs, drilling contracts, insurance policies,
claims history, BSEE/NSTA inspection records.

### P3 — Useful (request by Day 7; enhances analysis but absence is acceptable)

A document is P3 if:
- Absence doesn't materially change valuation or risk conclusion
- Data can be reasonably proxied from other sources
- Useful context but not decision-critical

**Typical P3:** Mudlogs and drilling reports, production chemistry records, secondary technical
studies, management accounts (if audited accounts present), pension plan detail (if small liability),
operator HSE performance reports, historical well workover records.

### Priority Override Rules

- Any document that resolves a 🔴 Critical finding is **automatically P1**, regardless of category
- Any document required to satisfy a regulatory filing deadline is **automatically P1**
- If a consent-to-assign is required from a specific party (JV partner, regulator), all documents
  defining that consent requirement are **automatically P1**

---

## SECTION 6: DOCUMENT CLASSIFICATION GUIDANCE — COMMON CASES

### 6.1 Documents That Are Easy to Misclassify

| Document | Common Mistake | Correct Classification |
|----------|---------------|----------------------|
| CPR economic model (Excel) | Classified as "Financial" | **Technical/Reservoir** — it supports the CPR |
| Decommissioning cost study | Classified as "Financial" | **ARO/Decommissioning** |
| LOS (Lease Operating Statement) | Classified as "Operations" | **Financial** |
| BSEE inspection reports | Classified as "HSE" | **Regulatory** (primary); HSE (secondary) |
| DSA (Decommissioning Security Agreement) | Classified as "ARO" | **Commercial/Contracts** — it's a contract |
| Well integrity files | Classified as "Technical" | **Environmental/HSE** — regulatory obligation |
| Pipeline ILI report | Classified as "Operations" | **Environmental/HSE** — integrity/safety |
| Management presentation / IM | Hard to classify | **Do not classify to a single category** — flag as "Seller Marketing Material" and note what it contains |
| Hedge book schedule | Classified as "Financial" | Correct ✅ |
| BOEM financial assurance letter | Classified as "Regulatory" | Correct ✅ (also relevant to ARO) |

### 6.2 Document Name Patterns to Recognise

These filename patterns are strong signals for classification:

| Pattern | Likely Category | Examples |
|---------|----------------|---------|
| CPR, Competent Person, Reserve Report, Resources Report | Technical/Reservoir | `CPR_Byron_Sep2025.pdf` |
| LAS, DLIS, well log | Technical/Reservoir | `SM070_G6_Composite_Log.las` |
| Production, Monthly Report, Allocation, ProStar | Production Data | `Monthly_Production_Oct2025.xlsx` |
| JOA, Joint Operating | Commercial/Contracts | `SM070_JOA_Executed_2018.pdf` |
| Lease, Licence, P.xxxx, OCS-G, SM, GC, MC | Commercial/Contracts | `OCS-G-36137_Lease.pdf` |
| LOS, Lease Operating, LOE | Financial | `Byron_LOS_2025_Monthly.xlsx` |
| SEMS, Safety Case, HAZOP, SIL | Environmental/HSE | `SM070_Safety_Case_Rev3.pdf` |
| ARO, Decom, P&A Cost, Abandonment | ARO/Decommissioning | `GoM_ARO_Study_P&A_2024.xlsx` |
| SPCC, NPDES, NOV, CAA, Permit | Regulatory/Environmental | `SPCC_Plan_SM070_2023.pdf` |
| Audit, Annual Report, 10-K, 10-Q, Financial Statements | Financial | `Byron_Audited_Accounts_2024.pdf` |
| PVT, Fluid Sample, EOS, MDT | PVT & SCAL | `SM058_PVT_Report_Well_G6.pdf` |
| ILI, Pig Run, Pipeline Inspection | Environmental/HSE | `SM070_Pipeline_ILI_2024.pdf` |

---

## SECTION 7: WHAT "BEST-IN-CLASS" LOOKS LIKE — REFERENCE STANDARDS

### 7.1 Ideal VDR for a GoM Producing Asset Acquisition (~$20–50M deal)

A best-in-class VDR for a Gulf of Mexico shallow-water producing asset acquisition (2–5 fields,
5–20 wells, $20–50M deal size) should contain:

**Technical (expect 50–150 files):**
- Independent CPR covering all fields + separate economic model spreadsheet
- Well logs (LAS) for all producing wells
- Monthly production data by well by fluid stream, 5+ years history
- PVT reports for each reservoir
- Facility drawings (P&IDs, topsides layout)
- Pipeline ILI results and anomaly reports
- Well integrity assessments (casing surveys, cement bond logs)
- Seismic interpretation reports + data licence confirmations

**Commercial/Legal (expect 30–80 files):**
- Executed JOA + all amendments, for every licence
- BOEM lease documents for every OCS block
- Full chain of title (all assignment deeds back 10+ years)
- Offtake/crude sales agreement (current)
- All midstream/gathering agreements
- SWD agreements (if applicable)
- Drilling/workover frame agreements
- ROFR history and waiver correspondence

**Financial (expect 20–40 files):**
- 3 years audited accounts
- 24 months LOS (monthly)
- Seller financial model (Excel)
- All debt facility agreements (if any)
- Hedge book schedule (if any)
- Current year budget
- AP and AR ageing schedules

**HSE/Regulatory (expect 30–60 files):**
- SEMS documentation (US GoM requirement)
- 5-year incident register
- Environmental permits (SPCC, NPDES, CAA)
- BSEE inspection history and all open findings
- ARO/decommissioning cost study (internal or independent)
- Phase I ESA

**Corporate/HR/Insurance (expect 10–20 files):**
- Corporate structure chart
- Employee list + key contracts
- Current insurance policies

**Total expected files for a well-prepared GoM producing asset VDR: 150–350 files**

If a VDR has <50 files for this deal type: flag as severely incomplete; DRL will be extensive.
If a VDR has 100–200 files: typical; expect material gaps in 2–4 areas.
If a VDR has >350 files with clear naming: well-prepared seller; gaps likely manageable.

### 7.2 Comparable Standard for UKCS Asset

A UKCS producing asset VDR of equivalent size will differ in:
- Safety Case replaces SEMS (NSTA regulatory requirement — must be present)
- NSTA correspondence replaces BSEE (different format; look for OGA/NSTA letterhead)
- Petroleum licence replaces BOEM lease (P.xxxx format)
- TUPE documentation required (vs WARN Act in US)
- Decommissioning Programme submission (NSTA) may already be initiated for late-life assets
- ARO estimates often in GBP (£), not USD — note currency

---

## SECTION 8: RESERVE CATEGORIES — QUICK REFERENCE FOR CLASSIFICATION

When classifying documents, these reserve terms appear frequently and signal document relevance:

| Term | Full Name | What it means for VDR context |
|------|-----------|-------------------------------|
| **1P / Proved** | Proved reserves | Most conservative, most bankable; PDP is the bank's primary collateral |
| **PDP** | Proved Developed Producing | Currently producing wells — highest certainty |
| **PDNP** | Proved Developed Non-Producing | Drilled but shut-in — verify reason |
| **PUD** | Proved Undeveloped | Undrilled locations; requires FDP and drill commitment |
| **2P** | Proved + Probable | Primary M&A metric (EV/2P is the standard multiple) |
| **3P** | Proved + Probable + Possible | Upside case; should not drive bid price |
| **2C** | Best Estimate Contingent Resources | Not yet sanctioned — classify as upside only |
| **Prospective** | Undiscovered resources | Exploration upside — speculative |
| **NRI** | Net Revenue Interest | WI% × (1 − royalty rate) — the economic ownership % |
| **WI%** | Working Interest | Gross ownership % — bears all costs |

**PRMS vs SEC — important for classification:**
- Most international transactions use **SPE-PRMS** (Petroleum Resources Management System)
- US-listed companies may also report under **SEC** rules (more conservative on PUDs)
- If a document uses "12-month average pricing" → likely SEC reporting
- If a document shows 1C/2C/3C categories → PRMS classification in use

---

## SECTION 9: KEY FINANCIAL TERMS FOR DOCUMENT RECOGNITION

These terms help the agent recognise financially relevant documents and assess their quality:

| Term | What it means | Why Agent 01 cares |
|------|--------------|-------------------|
| **PV-10 / NPV10** | Present value discounted at 10% | Core valuation metric — must be in CPR |
| **EV** | Enterprise Value = bid price + net debt | Used in comps (EV/2P, EV/boepd) |
| **LOE** | Lease Operating Expense | Per-boe cost driver — must reconcile LOS to CPR |
| **RBL** | Reserve-Based Lending | Bank debt secured by reserves — look for facility agreement |
| **Borrowing Base** | Max RBL draw against reserves | Check vs CPR and bank price deck |
| **Netback** | Revenue minus royalties, transport, opex per boe | Profitability per barrel — lifting cost benchmark |
| **ARO** | Asset Retirement Obligation | Decom cost — often understated on balance sheet |
| **DSA** | Decommissioning Security Agreement | Allocates ARO liability — critical for late-life |
| **Hedge MTM** | Mark-to-market of hedge positions | Can be large liability or asset |
| **Day-1 liabilities** | Vendor AP + debt + hedge MTM + ARO = net cost on close | Settlement sheet input |
| **NFA** | No Further Activity (base case) | Minimum downside — must be modellable from VDR data |
| **TRIR** | Total Recordable Incident Rate | HSE benchmark; from incident register |

---

## SECTION 10: COMMON RED FLAGS — AUTOMATIC ESCALATION TRIGGERS

The following patterns should be automatically escalated to 🔴 Critical in the gap analysis report,
regardless of what other documents are present:

| Pattern | Why it's Critical |
|---------|-----------------|
| No CPR or reserves report of any kind | Cannot value the asset independently |
| CPR effective date >18 months ago, no update | Material production history unverified |
| Production data ends >6 months before CPR effective date | Cannot validate CPR starting rates |
| Safety Case absent for an operating offshore platform | Probable regulatory non-compliance |
| Well integrity files absent for wells >15 years old | High probability of hidden integrity issues |
| No JOA for any licence | WI%, ROFR, and voting rights all unverifiable |
| ROFR holders not disclosed | Pre-emption risk entirely unquantified |
| No financial data beyond 1 year | Cannot validate cost assumptions |
| Balance sheet ARO materially below CPR decom section | Classic underprovision — expect price adjustment |
| Licence expiry within 24 months | Must confirm extension rights before bidding |
| NOV (Notice of Violation) in regulatory files with no close-out letter | Active enforcement action |
| Fatality or Tier 1 LOPC in HSE record | Material operational and reputational risk |
| Any WI% inconsistency across JOA/CPR/IM | Title or calculation error — must resolve pre-bid |
| Seller financial model is locked/password-protected | Agent 15 cannot reverse-engineer — request unlock |
| Debt facility with explicit CoC trigger and no waiver process documented | Deal may require full debt repayment on close |

---

## SECTION 11: SELF-LEARNING — PROPOSAL QUALITY CRITERIA

When Agent 01 encounters a document pattern not in the current gold-standard checklist, it should
propose a new checklist item if the document meets ALL of these criteria:

1. **Recurs:** The document type (not a specific one-off file) would plausibly appear in other
   upstream VDRs of similar deal type (GoM/UKCS/onshore/offshore)
2. **Material:** The absence of this document type would meaningfully affect analysis in at least
   one of the 6 workstreams (Technical, Financial, Legal, HSE, Operations, Strategic)
3. **Classifiable:** The document type can be reliably identified from filename patterns or
   brief content inspection (i.e., future instances would be consistently classified)
4. **Non-duplicate:** The document type is not already covered by an existing checklist item,
   even if labelled differently

**Proposal format:** Name | Category | Priority (P1/P2/P3) | Brief rationale (1–2 sentences)

**Calibration rules for proposals:**
- PSC-specific items (e.g., "Government Participation Letter") → tag as `International/PSC` scope;
  downgrade from P1 to P2 for US GoM or UKCS asset-only deals
- SWD (Saltwater Disposal) agreements → GoM relevance is high; UKCS relevance low
- Corporate debt instruments → P1 for corporate M&A; P2 for asset-only deals
- Seismic data licences → P1 for all offshore; P2 for onshore (where seismic is less critical)

---

## SECTION 12: OUTPUT QUALITY STANDARD FOR AGENT 01

Every output from Agent 01 must meet the following standards:

**`vdr_inventory.json`:** Every file in the VDR must appear exactly once. Each record must include:
filename, folder path, category (1–13), checklist_item_id (if matched), match_method
(keyword/fuzzy/llm/unclassified), and confidence (high/medium/low).

**`gap_analysis_report.md`:** Must clearly show for every gold-standard checklist item:
status (Present/Partial/Missing), matched file(s), and quality notes. The report must contain
a quantitative summary: items present, partial, and missing by workstream, and an overall
VDR completeness score.

**`data_request_list.docx`:** Every Missing or Partial item must appear on the DRL.
P1 items must appear first. Each DRL entry must include: item number, description, why it matters
(one sentence), and a suggested Q&A prompt for the seller's VDR Q&A module.

**Citation discipline:** When the LLM is used to classify or assess a document, the classification
must be accompanied by a brief explanation of the key signals observed (e.g., "Classified as
Technical/Reservoir based on presence of PRMS reserve categories and CPR methodology section").

---

*End of Agent 01 Domain Knowledge Primer v1.0*
*Next update: after Project Corsair and Project Coulomb DD completion — incorporate live VDR patterns as real-world classification examples.*
*Maintained by: Aigis Analytics | aigis-agents/agent_01_vdr_inventory/*
