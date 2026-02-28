<!--
=============================================================================
PART 4 OF 5 — Aigis DD Domain Knowledge Document
File: Aigis_DD_DomainKnowledge_PART4_VDR_Workflow_Agent_Mapping.md
Covers: Section 4 VDR Workflow (day-by-day) | Section 5 Agent Mapping & Orchestration
Assembles after PART 3. Before PART 5.
=============================================================================
-->

## SECTION 4: VDR WORKFLOW — DAY-BY-DAY PROCESS

> **For the Aigis System Coordinator:** This section defines exactly what happens inside the Virtual Data Room (VDR) during Phase 3 of the deal. Every agent deployed in a live transaction should operate within this workflow framework. Use this section to understand what the user is doing on any given day and which agents should be active.

### 4.0 VDR Setup — Pre-Access Requirements

Before any team member enters the VDR, the following must be confirmed:

- [ ] NDA executed and countersigned by all team members who will access VDR
- [ ] All team members approved on seller's access list
- [ ] VDR platform confirmed (common platforms: Datasite/Merrill, Intralinks, Ansarada, Dealroom, ShareVault)
- [ ] Download permissions confirmed (essential for Aigis agents to process documents)
- [ ] Q&A module access confirmed — this is the formal channel for all questions to seller
- [ ] Deal code name issued; internal file structure created per the output schema in Section 6.3
- [ ] Internal VDR coordinator assigned: one person routes documents to workstream leads, manages DRL log, tracks Q&A log
- [ ] Aigis deal workspace initialised: `{deal_id}/` folder structure created, all agents initialised for the deal

---

### 4.1 Day 1–2: VDR Triage & Gap Analysis

**Goal:** Understand what is present, what is missing, and issue the first Data Request List (DRL) within 24 hours of access.

**Why this matters:** The gap analysis drives the entire DD process. A complete VDR means faster, more reliable analysis. A sparse VDR means more reliance on management representations — higher risk.

#### Day 1 Actions (Hours 0–8)

| # | Action | Agent | Output |
|---|--------|-------|--------|
| 1 | Run VDR crawler — map full folder structure, count total documents, record filenames | **Agent 01** | `vdr_inventory.json` |
| 2 | Classify all documents into 13 standard categories (see table below) | **Agent 01** | Category counts per folder |
| 3 | Cross-check actual contents vs gold-standard VDR checklist (Appendix A) | **Agent 01** | `gap_analysis_report.md` |
| 4 | Flag any document where filename suggests relevance but content is incomplete or placeholder | **Agent 01** | Flagged items list |
| 5 | Generate numbered DRL: P1 (critical — missing, must have), P2 (important), P3 (useful if available) | **Agent 01** | `data_request_list.docx` |
| 6 | Open internal DD tracker — spreadsheet with one row per expected document, with: workstream, review status (Pending / In Review / Complete / Escalated), findings | Analyst | `dd_tracker.xlsx` |

#### Day 2 Actions (Hours 8–24)

| # | Action | Agent | Output |
|---|--------|-------|--------|
| 7 | Load all production data files into production database | **Agent 02** | `production.db` |
| 8 | First pass consistency check: does CPR WI% match IM WI%? | **Agent 03** (preliminary) | Conflict log |
| 9 | Submit DRL to seller's process manager via VDR Q&A module | Analyst | DRL submitted |
| 10 | Brief all workstream leads: here is the VDR structure, here is what we have, here is what is missing | BD Lead | Team aligned |
| 11 | Set Day 7 milestone: all P1 DRL items must be received or formally rejected by seller | BD Lead | Deadline set |

**Standard VDR 13-Category Classification:**

| # | Category | Primary Agents | Priority |
|---|----------|---------------|----------|
| 1 | Corporate Structure | Agent 16 | P1 |
| 2 | Technical / Reservoir (CPR, logs, seismic) | Agent 02, 07, 17 | P1 |
| 3 | Production Data (monthly actuals) | Agent 02 | P1 |
| 4 | Pressure Data (RFT/MDT/BHP) | Agent 02, 17 | P1 |
| 5 | Commercial / Contracts (JOA, licences, offtake) | Agent 09, 11, 16 | P1 |
| 6 | Financial (accounts, LOS, model, debt) | Agent 04, 12, 15 | P1 |
| 7 | Environmental / HSE | Agent 08 | P1 |
| 8 | ARO / Decommissioning | Agent 10 | P1 |
| 9 | Regulatory (licences, inspections, NOVs) | Agent 11 | P1 |
| 10 | PVT & SCAL (fluid samples, core data) | Agent 02 | P2 |
| 11 | HR / Employment | Manual review | P2 |
| 12 | Insurance (current policies, claims) | Manual review | P2 |
| 13 | IT / Data & Seismic Licences | Agent 09 | P2 |

---

### 4.2 Day 3–7: Parallel Deep Dive

**Goal:** All 6 workstreams conduct primary analysis simultaneously. Every workstream lead produces a preliminary findings note by end of Day 7.

**Key principle:** Parallel execution is what makes the timeline work. No workstream waits for another. Agent 06 (Q&A Synthesis) coordinates cross-workstream questions and prevents duplication.

#### Technical Workstream — Days 3–7

| Day | Task | Agent |
|-----|------|-------|
| Day 3 | Open CPR in full — extract full reserves table (1P/2P/3P by field, by category) into structured data | Agent 02 |
| Day 3 | Extract CPR production forecast (P50) by well by year | Agent 02 |
| Day 4 | Compare actual production (from production DB) to CPR P50 forecast, well-by-well | Agents 02 + 03 |
| Day 4 | Fit independent decline curves to actual production data | Agent 17 |
| Day 5 | Review seismic data licence confirmations — confirm all transferable | Manual + Agent 09 |
| Day 5 | Identify all wells with actual production >10% below CPR forecast since effective date | Agent 07 (preliminary) |
| Day 6 | Review PVT data, fluid contacts, reservoir pressure history | Manual |
| Day 7 | Draft well card summaries for top 10 producing wells | Agent 07 |
| Day 7 | Technical preliminary findings note: top 3 risks, top 3 upside items | Agent 06 synthesis |

#### Financial Workstream — Days 3–7

| Day | Task | Agent |
|-----|------|-------|
| Day 3 | Load audited financials — check auditor opinion, extract EBITDA, cash flow, capex trend | Manual + Agent 04 |
| Day 3 | Load LOS — reconcile revenue to purchaser statements; compute unit costs ($/boe) | Manual + Agent 04 |
| Day 4 | Extract price deck from CPR and IM — run Agent 05 comparison to live market | Agent 05 |
| Day 4 | Extract all debt schedules, covenants, and hedge positions | Agent 12 |
| Day 5 | Begin building buyer's independent financial model (DCF/NAV) | Agent 04 |
| Day 5 | Calculate hedge MTM at current forward curves | Agents 12 + 05 |
| Day 6 | Build preliminary Day-1 liability waterfall | Agent 12 |
| Day 7 | Financial preliminary findings note: seller model gap, key liabilities | Agent 06 synthesis |

#### Legal / Land Workstream — Days 3–7

| Day | Task | Agent |
|-----|------|-------|
| Day 3 | Open all JOAs — extract key terms across all licences | Agent 09 |
| Day 3 | Begin three-way WI% reconciliation: JOA vs CPR vs IM | Agent 16 |
| Day 4 | Pull all licence documents — extract expiry dates, MWOs, extension options | Agent 11 |
| Day 4 | Map all ROFR/ROFO holders across all licences | Agent 09 |
| Day 5 | Begin chain of title trace for all licences — identify any gaps | Agent 16 |
| Day 5 | Review all material commercial contracts (offtake, midstream, SWD) | Agent 09 |
| Day 6 | Build consent-to-assign tracker: all required approvals with timelines | Agent 11 |
| Day 7 | Legal preliminary findings note: title status, ROFR risk, consent timeline | Agent 06 synthesis |

#### HSE / Environmental Workstream — Days 3–7

| Day | Task | Agent |
|-----|------|-------|
| Day 3 | Filter VDR for all HSE and environmental documents | Agent 08 |
| Day 3 | Run HSE Scanner — classify all incidents using IOGP severity matrix | Agent 08 |
| Day 4 | Extract all ARO estimates from VDR — CPR estimate, balance sheet provision, internal study | Agent 10 |
| Day 4 | Run Agent 10 — build preliminary ARO waterfall (P50/P70/P90) | Agent 10 |
| Day 5 | Benchmark ARO against BOEM/NSTA industry data | Agent 10 |
| Day 5 | Review all environmental permits — check currency, exceedances | Manual |
| Day 6 | Review BSEE/NSTA inspection records — flag open findings | Agent 11 |
| Day 7 | HSE preliminary findings note: incident pattern, ARO status, open regulatory items | Agent 06 synthesis |

#### Operational Workstream — Days 3–7

| Day | Task | Agent |
|-----|------|-------|
| Day 3 | Pull org chart, key staff CVs, employee list | Manual |
| Day 4 | Review maintenance backlog reports, integrity inspection records | Manual |
| Day 5 | Assess SCADA/production reporting systems — map TSA requirements | Manual |
| Day 6 | Review planned capex programme — compare well costs to BSEE/NSTA data | Agent 14 |
| Day 7 | Operational preliminary findings note: TSA scope, key person risk, capex validation | Agent 06 synthesis |

#### Strategic / BD Workstream — Days 3–7

| Day | Task | Agent |
|-----|------|-------|
| Day 3 | Monitor emerging findings from all workstreams in real time | Agent 06 |
| Day 3–7 | Submit targeted Q&A questions via VDR Q&A module (limit: 10 per day per process rules) | BD Lead |
| Day 4 | Run comparable transactions search for bid anchoring | Agent 13 |
| Day 5 | Issue second DRL for any additional material gaps identified in Days 1–4 | Agent 01 + Analyst |
| Day 7 | Begin drafting IC memo outline: structure, key sections, open items | BD Lead |

---

### 4.3 Day 8–14: Analysis & Red Flag Review

**Goal:** Complete all primary analysis. Surface every material finding. Convene the Red Flag Meeting. Submit price adjustment requests.

#### Day 8–10 Actions

| # | Action | Agent | Output |
|---|--------|-------|--------|
| 1 | Run full internal consistency audit across all 12 assumption types (see below) | **Agent 03** | `consistency_audit.md` with all 🔴🟡🟢 flags |
| 2 | Finalise all well performance cards — full fleet | **Agent 07** | `well_cards.pdf`, `well_portfolio_summary.xlsx` |
| 3 | Finalise ARO P50/P70/P90 waterfall — compare to balance sheet provision | **Agent 10** | `aro_waterfall.xlsx` |
| 4 | Finalise consent-to-assign tracker with confirmed timelines per regulator | **Agent 11** | `consent_to_assign_tracker.xlsx` |
| 5 | Build preliminary Day-1 liability waterfall — gross debt + hedge MTM + ARO + contingent | **Agent 12** | `day1_liability_waterfall.xlsx` |
| 6 | Complete three-way WI% reconciliation — finalise title chain | **Agent 16** | `wi_reconciliation.xlsx`, `title_chain.md` |

**The 12 Assumption Types — Agent 03 Consistency Audit:**

| # | Assumption | Sources Cross-Checked | Red Flag Threshold |
|---|-----------|----------------------|-------------------|
| 1 | Working Interest % | JOA ↔ CPR ↔ IM | Any mismatch |
| 2 | Net Revenue Interest % | JOA (royalty) ↔ CPR NRI ↔ financial model | Any mismatch |
| 3 | Production forecast (P50) | CPR P50 ↔ IM profile ↔ seller model | >5% divergence |
| 4 | Oil/gas price deck | CPR price deck ↔ IM ↔ live market (Agent 05) | >5% above market |
| 5 | Opex (LOE) $/boe | CPR opex ↔ LOS actuals ↔ seller model | >10% divergence |
| 6 | Capex per well | CPR ↔ IM ↔ technical team's estimate | >15% divergence |
| 7 | ARO / decommissioning | Balance sheet ↔ CPR ↔ internal study ↔ BOEM data | >20% gap |
| 8 | Royalty rate / NRI | JOA ↔ CPR ↔ financial model | Any mismatch |
| 9 | Discount rate | CPR ↔ seller model ↔ buyer's hurdle rate | Note only; expected to differ |
| 10 | Abandonment timing | CPR economic limit ↔ well-by-well modelling | >2 years difference |
| 11 | Reserve category split (1P/2P/3P) | CPR ↔ IM summary ↔ financial model input | Any mismatch |
| 12 | GOR/WC assumptions | CPR assumptions ↔ actual production DB trend | >10% divergence from actual trend |

#### Day 10–12: Management Q&A Session

If the seller's process permits a management meeting or Q&A session, prepare 20 targeted cross-workstream questions:

**Question Construction Rules:**
- Questions should be specific and answerable from VDR data (not open-ended)
- Prioritise questions where a finding is 🔴 Critical — get the explanation before the Red Flag Meeting
- Never ask for information already in the VDR (wastes the session)
- Sequence: technical first (factual), then financial (reconciliation), then legal (confirmation), then HSE/operational

**Sample Cross-Workstream Questions:**
1. *[Technical]* "Well G6 at SM58 is producing ~575 bopd vs the CPR P50 forecast of 280 bopd — can you confirm whether the CPR effective date decline assumption reflects a post-workover rate or a pre-workover rate?"
2. *[Financial]* "The LOS shows LOE of $X/boe but the CPR financial model uses $Y/boe — can you reconcile this difference and confirm which is used in your valuation?"
3. *[Legal]* "For SM71: can you confirm the Otto/Byron parent guarantees are being removed ahead of close, and provide the timeline for Jones Day sign-off?"
4. *[HSE]* "The ARO provision on the balance sheet ($9M) is materially below the CPR P70 estimate ($13.4M) — is there an updated internal decommissioning study that bridges this gap?"
5. *[Operations]* "How many of the listed staff members are employed directly by Byron Energy vs through contractor arrangements, and who will you be seeking to retain?"

#### Day 12–14: Red Flag Meeting

**Purpose:** All workstream leads meet to review every 🔴 Critical finding. Assess deal-breaker risk. Agree price adjustment strategy.

**Red Flag Meeting Agenda (Standard):**

| Workstream | Items to Cover | Decision Required |
|-----------|---------------|------------------|
| Technical | Production underperformance findings; CPR assumption divergences; reservoir risk items | Is any finding a deal-breaker? Should bid be adjusted? |
| Financial | Financial model divergence from seller; debt/hedge liabilities; effective date adjustment | Revised EV range? Price adjustment mechanism? |
| Legal | Title gaps; ROFR exposure; consent timeline risk; material contract red flags | Deal structure change needed? SPA protection required? |
| HSE | HSE incident pattern; ARO understatement gap; open environmental liability | Price adjustment for ARO delta? Indemnity required? |
| Operations | TSA complexity; key person retention risk; maintenance backlog | Retention plan? TSA cost in model? |
| Strategic | Competitive intelligence update; antitrust risk; financing status | Any change to bid strategy? Escalation needed? |

**Red Flag Meeting Outputs:**
- Agreed list of price adjustment requests to submit to seller
- Confirmed list of items requiring SPA indemnity/warranty protection
- Any deal-breaker items → escalation to senior management / IC pre-meeting
- Updated risk register
- Revised EV range if findings warrant

---

### 4.4 Day 15–21: IC Preparation & Synthesis

**Goal:** Aggregate all DD findings into IC-ready deliverables. Complete sensitivity analysis. Finalise comps table. Draft IC memo.

#### Day 15–17: Aggregation

| # | Action | Agent | Output |
|---|--------|-------|--------|
| 1 | Finalise comparable transactions table — 24–36 months of basin-specific deals | **Agent 13** | `comps_table.xlsx`, `comps_narrative.md` |
| 2 | Run full sensitivity analysis — all variables on buyer's base case | **Agent 15** | `sensitivity_analysis.xlsx` |
| 3 | Run base case validation — compare seller model vs buyer's model input-by-input | **Agent 15** | `base_case_validation.md` |
| 4 | Run opex/capex benchmarking — buyer's assumed costs vs BSEE/NSTA industry data | **Agent 14** | `cost_benchmarking.md` |
| 5 | Each workstream lead produces final DD report section (5–15 pages each) | All teams | 6 DD report sections |

#### Day 17–19: Risk Scorecard

Agent 19 (Technical Risk Scoring Engine) aggregates all findings from all agents and produces the IC risk scorecard:

**Risk Scoring Methodology (Agent 19):**

| Dimension | Weight | Sub-Components |
|-----------|--------|---------------|
| Subsurface / Reserves | 25% | CPR reliability, decline rate risk, reservoir uncertainty |
| Production Performance | 20% | Actual vs CPR variance, well integrity, facility uptime |
| Commercial / Contractual | 15% | ROFR risk, contract liabilities, MVC exposure |
| Financial Liabilities | 15% | Debt structure, hedge MTM, ARO gap, contingent liabilities |
| Regulatory / Legal | 15% | Consent timeline risk, title quality, licence status |
| HSE | 5% | Incident history, safety case status, open corrective actions |
| ESG / Carbon | 5% | Carbon intensity, flaring, regulatory carbon cost exposure |

**Scoring:**
- Each dimension scored 0–100 (100 = no risk; 0 = deal-breaker risk)
- Weighted average produces overall deal risk score 0–100
- Traffic light: 🟢 75–100 | 🟡 50–74 | 🔴 0–49

**IC Traffic Light Output (one page):**
```
DEAL RISK SCORECARD — [DEAL CODE NAME]
Overall Score: XX/100 — 🟢/🟡/🔴

Subsurface:     XX/100 🟢/🟡/🔴  [Key finding]
Production:     XX/100 🟢/🟡/🔴  [Key finding]
Commercial:     XX/100 🟢/🟡/🔴  [Key finding]
Liabilities:    XX/100 🟢/🟡/🔴  [Key finding]
Regulatory:     XX/100 🟢/🟡/🔴  [Key finding]
HSE:            XX/100 🟢/🟡/🔴  [Key finding]
ESG/Carbon:     XX/100 🟢/🟡/🔴  [Key finding]

TOP 3 RISKS:
1. [Risk] — [Mitigation] — [Price impact: $XM]
2. [Risk] — [Mitigation] — [Price impact: $XM]
3. [Risk] — [Mitigation] — [Price impact: $XM]

TOP 3 UPSIDES:
1. [Upside] — [Probability] — [NPV: $XM]
2. ...

RECOMMENDATION: [PROCEED / PROCEED WITH CONDITIONS / WITHDRAW]
```

#### Day 19–21: IC Memo Drafting

**IC Memo Standard Structure (BD Lead authors; all workstream leads review their section):**

1. **Executive Summary** (1 page): deal rationale, recommended action, EV range, confidence level
2. **Asset Overview** (2 pages): key production/reserves metrics, geography, operatorship
3. **Technical Summary** (2–3 pages): CPR highlights, buyer's independent view, key sub-surface risks
4. **Financial Summary** (3–4 pages): valuation methodology, buyer's base case NPV, sensitivity table, comps
5. **Risk Summary** (2 pages): risk scorecard (Agent 19), top risks, mitigants, price adjusters
6. **Legal & Regulatory** (1–2 pages): title status, ROFR position, consent timeline, key SPA issues
7. **Strategic Fit** (1 page): portfolio rationale, combined pro-forma
8. **Financing** (1 page): funding structure, leverage impact, hedging plan
9. **Recommendation** (1 page): bid price range, walk-away price, escalation authority
10. **Appendices**: well cards (Agent 07), comps table (Agent 13), sensitivity table (Agent 15), liability waterfall (Agent 12), ARO waterfall (Agent 10), consent tracker (Agent 11)

**Peer Review Protocol:**
- Each workstream lead reviews all sections (not just their own)
- BD lead checks consistency: same numbers used throughout (no version mismatches)
- External legal counsel reviews legal section before submission

---

### 4.5 Day 22–28: IC Submission & Bid

| # | Action | Owner | Deadline |
|---|--------|-------|----------|
| 1 | Present IC memo to Investment Committee | BD Lead | Day 22 |
| 2 | IC decision: approve / conditional / revise / withdraw | IC | Day 22–23 |
| 3 | If approved: finalise binding bid price, structure, and conditions | BD Lead + Finance | Day 23 |
| 4 | Finalise SPA key terms and red lines | External Legal | Day 24 |
| 5 | Submit binding bid letter | BD Lead | Day 25 |
| 6 | File any regulatory pre-notifications (HSR if applicable) | Legal | Day 25 |
| 7 | Initiate Agent 20: begin 100-day integration plan from DD findings | Agent 20 | Day 26 |
| 8 | Initiate SPA negotiations with seller's counsel | Legal | Day 25+ |
| 9 | Monitor for any late Q&A responses from seller — assess materiality | BD Lead | Ongoing |
| 10 | Update risk register for any new information since IC submission | Agent 06 | Ongoing |

---

### 4.6 VDR Q&A Management Protocol

The Q&A module in the VDR is the formal channel between buyer's team and seller/seller's adviser. It creates a written record that forms part of the deal record.

**Rules:**
- Every Q&A question is submitted via the VDR module — not by email (unless platform doesn't support it)
- All questions numbered: Q001, Q002, ... for audit trail
- Questions categorised by workstream: [TECH], [FIN], [LEGAL], [HSE], [OPS]
- All Q&A responses logged in `06_qa_log/` folder
- Agent 06 processes all new Q&A responses as they arrive and flags anything material

**Question Writing Quality Standard:**
- **Specific:** Reference the exact document, section, and page number where the issue was identified
- **Answerable:** Can be answered from existing data — not open-ended requests for information
- **Non-leading:** Do not telegraph the concern in the question — extract the fact first
- **Prioritised:** P1 questions submitted Day 1–3; P2 by Day 7; P3 by Day 14

---

## SECTION 5: AIGIS AGENT MAPPING — DOMAIN TO AGENT

> **For the Aigis System Coordinator:** This section is your operational guide. Use Section 5.1 for the full agent catalogue (what each agent does). Use Section 5.2 for the orchestration architecture (how agents work together). Use Section 5.3 for the query routing table (which agent to call for any given question). Dependency rules in Section 5.4 define the required build order.

---

### 5.1 Full Agent Catalogue

#### 🟢 Sprint 1 — Core Foundation (Deploy First; Required for Any Live Deal)

---

**Agent 01 — VDR Inventory & Gap Analyst**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Crawls the full VDR folder structure. Classifies every document into one of 13 standard categories. Cross-checks actual contents against the gold-standard DD checklist (Appendix A). Generates the Data Request List (DRL) with P1/P2/P3 prioritisation. |
| **Triggered by** | VDR access granted on a new deal; user asks "what is in the VDR?"; user asks "what are we missing?" |
| **Inputs** | VDR folder tree + document metadata; gold-standard checklist |
| **Outputs** | `vdr_inventory.json`, `gap_analysis_report.md`, `data_request_list.docx` |
| **Sprint** | Sprint 1 |
| **Dependencies** | None — always the first agent to run on a new deal |
| **Critical rules** | Must run before any other agent on a new deal. DRL must be issued within 24 hours of VDR access. All subsequent agents reference the inventory index produced here. |

---

**Agent 04 — Upstream Finance Calculator**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Computes 25+ upstream-specific financial metrics on demand. Core metrics: NPV (multiple discount rates), IRR, PV-10, EV/2P, EV/boepd, lifting cost ($/boe), netback, F&D cost, ARO NPV, RLI, payback period, ND/EBITDA. Every calculation includes full audit trail: inputs used, formula, source citations. |
| **Triggered by** | Any financial calculation question; all other agents that produce financial outputs call Agent 04 as a sub-routine |
| **Inputs** | Production data (Agent 02), price curves (Agent 05), fiscal terms (Agent 09), ARO (Agent 10), opex/capex (from LOS + technical) |
| **Outputs** | Structured JSON: `{result, unit, metric, inputs_used, formula, workings, source_citations, confidence}` |
| **Sprint** | Sprint 1 |
| **Dependencies** | Agents 02, 05 must run before Agent 04 produces reliable outputs (can run with manual inputs if DB not yet built) |
| **Critical rules** | NEVER produce a financial output without citing the source of every input. If any input is LOW confidence, the output is flagged LOW confidence. |

---

**Agent 06 — Q&A Synthesis Engine (Orchestrator / Front Door)**

| Attribute | Detail |
|-----------|--------|
| **What it does** | The primary interface for all user queries. Routes any question to the correct specialist agent(s). Synthesises multi-agent responses into a single, coherent, cited answer. Enforces the citation-mandatory output standard (Section 6.1). Logs every query and response in the deal Q&A log. |
| **Triggered by** | Every user query — this is the default entry point for the system |
| **Inputs** | User query + full deal context (from deal workspace) + outputs from specialist agents |
| **Outputs** | Cited, structured answer in the standard output format; updated `qa_log.md` entry |
| **Sprint** | Sprint 1 |
| **Dependencies** | Calls any other agent as needed — the orchestrator depends on all others |
| **Critical rules** | Never answer from memory alone — always route to the appropriate specialist agent. Never fabricate a metric or citation. If a query spans multiple workstreams, call all relevant agents and synthesise. |

---

**Agent 08 — HSE Red Flag Scanner**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Scans all HSE and environmental documents in the VDR. Classifies every incident using the IOGP severity matrix (Tier 1/2 LOPC, LTI, fatality, near miss). Auto-flags: Tier 1 LOPC events, fatalities, open regulatory enforcement actions, expired safety cases, stale decommissioning estimates. Checks BSEE/NSTA public databases for inspection records. |
| **Triggered by** | VDR triage (runs automatically as part of Day 1–2 workflow); any HSE-related user query |
| **Inputs** | All HSE/environmental documents from VDR; BSEE/NSTA public inspection databases |
| **Outputs** | `hse_risk_summary.md` with incident classification, open action items, and severity-ranked finding list |
| **Sprint** | Sprint 1 |
| **Dependencies** | Agent 01 (needs document inventory to know which files to scan) |
| **Critical rules** | Any Tier 1 LOPC or fatality finding triggers a 🔴 Critical flag that must be acknowledged by a human reviewer before downstream use. Never suppress an HSE finding based on management explanation alone — document the explanation alongside the finding. |

---

#### 🟢 Sprint 2 — Data Backbone (Required Before Intelligence Layer)

---

**Agent 02 — Production Data Collator → SQL Database**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Scans the VDR for every production data source: CPR appendices, CSV files, Excel downloads, monthly reporting PDFs, IM summaries. Builds a relational SQL database with the following tables: `wells`, `fields`, `licences`, `production_monthly` (oil/gas/water/NGL by well by month), `reserves` (1P/2P/3P by field), `opex` (by year), `capex` (by year), `aro` (by asset). Detects conflicts between sources and logs them. Provides a natural language query interface on top of the database. |
| **Triggered by** | VDR triage (Day 1); any production-related query |
| **Inputs** | All production data files from VDR (CSV, Excel, PDF tables, CPR appendices) |
| **Outputs** | `production.db` (SQLite), `conflict_log.md`, `data_dictionary.md` |
| **Sprint** | Sprint 2 |
| **Dependencies** | Agent 01 (document inventory to find all production files) |
| **Critical rules** | When two sources give different values for the same well/month, ALWAYS log the conflict and use the more conservative value in downstream calculations. Flag any period with >6 consecutive months of missing data. |

---

**Agent 03 — Internal Consistency Auditor**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Cross-checks 12 key assumption types (listed in Section 4.3) across CPR, IM, management presentation, seller financial model, JOA/licence documents. Assigns severity: 🔴 Critical (>10% variance or any WI% mismatch), 🟡 Moderate (5–10% variance), 🟢 Minor (<5% variance). Produces a full audit matrix and a human-readable summary of all findings. Flags every 🔴 Critical item for human-in-loop review before downstream use. |
| **Triggered by** | Full VDR review (Day 8); any cross-document comparison question |
| **Inputs** | CPR, IM, seller financial model, JOA (from Agent 09), production DB (from Agent 02), price curves (from Agent 05) |
| **Outputs** | `consistency_audit.md`, `consistency_summary.xlsx` |
| **Sprint** | Sprint 2 |
| **Dependencies** | Agents 01, 02, 05, 09 must run first for full consistency audit |
| **Critical rules** | Human acknowledgement required for every 🔴 Critical finding before the finding is used in any downstream calculation. Never auto-resolve a conflict by picking one source — always present both values and flag for human decision. |

---

**Agent 05 — Commodity Price Forward Curve Fetcher**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Fetches live commodity price forward curves from free APIs: EIA (oil, gas, US), CME/NYMEX via yfinance (WTI, Henry Hub), ICE (Brent, UK NBP). Compares the CPR/IM price deck to the current live market. Produces traffic light assessment: 🟢 Conservative (deck ≥5% below market), 🟡 In-line (within 5%), 🔴 Aggressive (deck >5% above market). Also outputs the forward curve data for direct use in Agent 04 financial calculations. |
| **Triggered by** | Price deck question; financial model question; automatically as part of Day 3–4 workflow |
| **Inputs** | CPR price deck (from document), IM price assumptions; live API data |
| **Outputs** | `price_curves.json`, `price_deck_comparison.md` with traffic light ratings |
| **Sprint** | Sprint 2 |
| **Dependencies** | Agent 01 (to locate CPR and IM) |
| **Critical rules** | Always timestamp the fetch — price curves change daily. Never use a price curve fetched >3 trading days ago. If API unavailable, flag and use last available data with clear timestamp disclaimer. |

---

#### 🟡 Sprint 3 — Intelligence Layer (Requires Data Backbone Complete)

---

**Agent 07 — Well Performance Intelligence Cards**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Produces one standardised performance card per well from the production database. Each card contains: current rate (bopd/MMscfd/boepd), cumulative production since CPR effective date, CPR P50 forecast vs actual (variance %), current GOR (scf/bbl) and 12-month trend, current water cut (%) and 12-month trend, EUR estimate at fitted decline rate, well status flag. |
| **Well status flags** | 🟢 Outperformer (>10% above CPR P50) · 🟡 On-track (±10% of CPR P50) · 🔴 Underperformer (>10% below CPR P50) · ⚫ Shut-in (no recent production) |
| **Triggered by** | Well performance question; Day 8 workflow; IC preparation |
| **Inputs** | Production database (Agent 02), CPR production forecast |
| **Outputs** | `well_cards.pdf` (one card per well), `well_portfolio_summary.xlsx` (fleet-level aggregation) |
| **Sprint** | Sprint 3 |
| **Dependencies** | Agent 02 (production DB must be built first) |
| **Critical rules** | Always compare to CPR P50 — not the optimistic CPR scenario. Flag any well where actual cumulative production is >20% below CPR P50 since effective date as 🔴 Critical automatically. |

---

**Agent 09 — JOA / Licence / Contract Key Terms Extractor**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Reads all JOAs, licence documents, and commercial contracts in the VDR. Extracts a standard term set from each document type (see Section 3.3 Focus Areas L2, L3, L7 for the full term lists). Auto-flags: CoC consent requirements, ROFR/ROFO provisions, short licence expiry (<24 months), non-assignable contracts, punitive MVC commitments. Produces a contract summary pack and a red flag register. |
| **Triggered by** | Contract review question; ROFR/ROFO question; licence status question; Day 3 workflow |
| **Inputs** | All JOA, licence, and commercial contract documents from VDR |
| **Outputs** | `contract_summary_pack.docx` (one section per document), `red_flag_register.md` (all flagged terms) |
| **Sprint** | Sprint 3 |
| **Dependencies** | Agent 01 (document inventory to locate all contracts) |
| **Critical rules** | Never infer a term — only report what is explicitly stated in the document. If a standard term (e.g., ROFR) is absent from a JOA, flag as "Not Present — confirm with legal counsel." Always include document filename, section, and page number for every extracted term. |

---

**Agent 10 — ARO / Decommissioning Cost Aggregator**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Extracts ARO estimates from every available source: CPR decommissioning cost estimate (P50 and P90 if given), balance sheet ARO provision, any internal decommissioning cost study in VDR, BOEM financial assurance data (US GoM), NSTA decommissioning programme (UKCS). Builds a P50/P70/P90 ARO waterfall by asset/well/platform. Benchmarks against BOEM/NSTA industry unit costs. Flags when balance sheet provision is materially below CPR P50. |
| **Triggered by** | ARO/decommissioning question; liability schedule question; Day 4 workflow |
| **Inputs** | CPR (decommissioning section), audited accounts (balance sheet), internal ARO study, BOEM/NSTA public data, BSEE well count by field |
| **Outputs** | `aro_summary.md`, `aro_waterfall.xlsx` (P50/P70/P90 by asset) |
| **Sprint** | Sprint 3 |
| **Dependencies** | Agent 01 (to find all relevant documents), Agent 02 (for well count by field) |
| **Critical rules** | ALWAYS use P70 as the base case for financial modelling (not P50) — buyers systematically underestimate ARO. If P90 > 1.5× P50, the estimate carries high uncertainty — flag prominently and recommend price adjustment clause in SPA. |

---

**Agent 11 — Regulatory Licence Status Checker**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Checks the status of all licences and regulatory obligations relevant to the transaction. US GoM: queries BOEM TIMS database for lease status, assignments, ARO bonds. UKCS: checks NSTA data portal for licence status, decommissioning programme. All jurisdictions: maps all required consents to assign (regulator, timeline, conditions). Checks BSEE/NSTA inspection records for open findings and NOVs. |
| **Triggered by** | Regulatory question; consent-to-assign question; licence expiry question; Day 4 workflow |
| **Inputs** | Licence documents (from Agent 09), BOEM/NSTA/NPD public databases (live API) |
| **Outputs** | `regulatory_status.md`, `consent_to_assign_tracker.xlsx` (regulator, requirement, timeline, status) |
| **Sprint** | Sprint 3 |
| **Dependencies** | Agent 01 (documents), Agent 09 (licence term extraction) |
| **Critical rules** | Always query the live regulatory database — do not rely solely on the VDR documents (which may be outdated). Flag any consent where the estimated timeline extends beyond the SPA long-stop date. |

---

**Agent 13 — Comparable Transactions Finder**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Searches free public sources for comparable upstream M&A transactions: SEC EDGAR 8-K filings, public press releases, and any available industry databases. Extracts key deal metrics from each transaction: EV (announced), production at announcement, 2P reserves, EV/2P ($/boe), EV/boepd, deal structure, basin, asset type, date. Produces a formatted comps table and a narrative positioning the subject deal against the market. |
| **Search scope** | Last 24–36 months, same basin (GoM/UKCS/etc), similar asset type and scale |
| **Triggered by** | Valuation question; "what are comparable deals?"; bid strategy question; IC preparation |
| **Inputs** | Deal characteristics (basin, production, reserves, asset type) from production DB and CPR |
| **Outputs** | `comps_table.xlsx`, `comps_narrative.md` |
| **Sprint** | Sprint 3 |
| **Dependencies** | Agent 02 (for deal characteristics to anchor comp search parameters) |
| **Critical rules** | Always cite the source (SEC filing number, press release URL, database reference) for every comparable. Exclude any transaction >36 months old or from a materially different basin without explicit flagging. Note if deal metrics are disclosed vs estimated. |

---

**Agent 14 — Opex & Capex Benchmarking Agent**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Benchmarks the target's cost assumptions (opex $/boe, well costs, lifting cost components) against publicly available industry data: BSEE production cost surveys (US GoM), NSTA performance data (UKCS), EIA drilling cost surveys, Rystad published benchmarks. Produces a traffic light assessment: 🟢 Below median (efficient), 🟡 At median (in-line), 🔴 Above upper quartile (flag for investigation). |
| **Triggered by** | Cost benchmarking question; opex challenge question; capex validation question |
| **Inputs** | LOS opex data (from financial), well cost estimates (from technical), basin and asset type identifiers |
| **Outputs** | `cost_benchmarking.md` with benchmark comparison table and traffic light flags |
| **Sprint** | Sprint 3 |
| **Dependencies** | Agent 02 (for production volumes to compute unit costs) |
| **Critical rules** | Always specify the benchmark vintage — industry costs change year-on-year. Flag if seller's capex estimate predates the most recent rig cost inflation cycle (post-2021). |

---

**Agent 15 — Seller Model Reverse-Engineer & Sensitivity Analyser**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Two functions: (1) Takes the seller's financial model from the VDR and re-runs it with the buyer's independently validated inputs (production from Agent 02, price from Agent 05, opex from LOS, capex from technical, ARO from Agent 10) — producing the "value gap" analysis. (2) Runs a full sensitivity/scenario analysis on the buyer's base case model — all variables, all ranges as defined in Section 3.2 Focus Area F5. |
| **Triggered by** | Valuation question; sensitivity question; bid price calibration; IC preparation |
| **Inputs** | Seller's financial model (from VDR), buyer's base case inputs (all validated agents), sensitivity ranges |
| **Outputs** | `sensitivity_analysis.xlsx` (tornado chart data, NPV/IRR tables), `base_case_validation.md` (seller vs buyer model comparison) |
| **Sprint** | Sprint 3 |
| **Dependencies** | Agents 02, 04, 05, 09, 10 must all run first for complete inputs |
| **Critical rules** | The buyer's base case model must use only independently validated inputs. Never mix seller's assumptions with buyer's — keep them separate and explicitly labelled. Flag every instance where seller's model uses a more optimistic assumption than the buyer's independently validated input. |

---

#### 🟡 Sprint 4 — Synthesis Layer (Requires Intelligence Layer Complete)

---

**Agent 12 — Debt, Hedging & Liability Schedule Builder**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Extracts all debt facilities (amount, maturity, rate, covenants, CoC provisions), all hedge positions (instrument, notional, strike, maturity, counterparty), and all contingent liabilities from the VDR. Computes hedge MTM at current forward curves (uses Agent 05). Builds the complete Day-1 liability waterfall: gross debt + hedge MTM + contingent liabilities + outstanding payables − cash = net Day-1 liability. Flags CoC debt triggers, potential covenant breach at pro-forma leverage. |
| **Triggered by** | Liability question; debt structure question; hedge book question; IC preparation |
| **Inputs** | Debt documents and hedge schedules (from VDR), live forward curves (Agent 05), contingent liability register (from legal DD) |
| **Outputs** | `day1_liability_waterfall.xlsx`, `debt_covenant_tracker.md` |
| **Sprint** | Sprint 4 |
| **Dependencies** | Agent 05 (for live curves to compute hedge MTM), Agent 09 (for debt facility CoC provisions) |
| **Critical rules** | Always use current mark-to-market — not historical or estimated. Hedge book MTM can swing materially with price moves. Timestamp every MTM calculation. Flag any CoC prepayment trigger as 🔴 Critical — it can derail deal timing if not addressed in SPA. |

---

**Agent 16 — Title & Ownership Chain Validator**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Performs the three-way WI% reconciliation: confirms WI% is consistent across JOA (contractual), CPR (engineering), and IM (commercial). Traces the full chain of title for every licence/lease — from original grant through all assignments to current holder. Identifies any gap in the chain (missing executed assignment, unrecorded transfer, unfiled government consent). Flags outstanding ROFR/ROFO holders who have not yet provided waivers. |
| **Triggered by** | Title question; WI% confirmation question; ROFR status question; Day 3 workflow |
| **Inputs** | All licence/lease documents, all JOAs (from Agent 09), all assignment deeds from VDR |
| **Outputs** | `title_chain.md` (narrative chain per licence), `wi_reconciliation.xlsx` (three-way match table) |
| **Sprint** | Sprint 4 |
| **Dependencies** | Agent 09 (JOA term extraction for WI%), Agent 01 (document inventory) |
| **Critical rules** | Any gap in the chain of title is automatically 🔴 Critical — no exception. A missing executed assignment is a deal-breaker until resolved. NEVER assume a gap is a VDR omission without confirmation from the seller's legal team. |

---

**Agent 19 — Technical Risk Scoring Engine (IC Pack Generator)**

| Attribute | Detail |
|-----------|--------|
| **What it does** | The terminal aggregator. Reads the `_master_findings.json` file populated by all specialist agents during the DD process. Applies the weighted risk scoring methodology (Section 4.4) to produce: (a) the one-page IC traffic light scorecard, (b) the full deal risk register with every finding categorised and ranked, (c) the top 3 risks and top 3 upsides with NPV/probability estimates. |
| **Triggered by** | IC preparation (Day 17–19); "what is the overall deal risk?" query |
| **Inputs** | `_master_findings.json` (populated by all agents throughout DD), buyer's base case NPV, sensitivity outputs from Agent 15 |
| **Outputs** | `deal_risk_scorecard.pdf` (one-page IC traffic light), `risk_register.xlsx` (full risk register) |
| **Sprint** | Sprint 4 |
| **Dependencies** | ALL other agents must run before Agent 19 produces a reliable scorecard. It is the terminal agent. |
| **Critical rules** | Never produce an IC scorecard with incomplete agent outputs — flag which agents have not yet run. The scorecard must carry a "completeness indicator" showing which data inputs are present. Any 🔴 Critical unresolved finding from any agent automatically caps the overall score at 49/100 (🔴 territory), regardless of other scores. |

---

**Agent 20 — 100-Day Integration Plan Generator**

| Attribute | Detail |
|-----------|--------|
| **What it does** | Auto-generates the 100-day post-acquisition integration plan by extracting action items from DD findings across all agents. Sources: regulatory consent requirements (Agent 11) → Day-1 filings; contract novation list (Agent 09) → Day 1–30 actions; TSA scope (operational DD) → Day 1–60 milestones; data migration requirements → Day 31–100 workstreams. Each action has: owner (by function), due date (Day 1 / Day 1–30 / Day 31–100), status (Pending/In Progress/Complete), source finding. |
| **Triggered by** | Post-IC or post-signing ("generate integration plan"); close preparation |
| **Inputs** | Outputs from Agents 09, 11, 12, 16; operational DD findings; HR DD findings |
| **Outputs** | `100day_integration_plan.docx`, `day1_action_checklist.xlsx` |
| **Sprint** | Sprint 4 |
| **Dependencies** | Agents 09, 11, 12, 16 must run first |
| **Critical rules** | The Day-1 checklist is the highest-priority output — these are the actions that must complete on closing day. Flag any Day-1 action that does not have a confirmed owner at the time of plan generation. |

---

#### 🔴 Strategic Builds (Post-Sprint 4)

| Agent | Description | Sprint |
|-------|-------------|--------|
| **Agent 17 — CPR Production Decline Modeller** | Independent decline curve fitting using scipy (Python). Exponential, hyperbolic, harmonic decline models. Monte Carlo P10/P50/P90. Compare buyer's fitted decline vs CPR forecast. Challenge b-value assumptions. | Post-Sprint 4 |
| **Agent 18 — ESG & Carbon Liability Scanner** | GHG emissions data extraction. Flaring analysis. Methane intensity calculation vs OGMP 2.0. Carbon cost NPV impact at $30/$50/$80/$150/tonne CO2e scenarios. TCFD alignment assessment. EU/UK ETS compliance check. | Post-Sprint 4 |

---

### 5.2 Agent Orchestration Architecture

```
═══════════════════════════════════════════════════════════════
                   AIGIS AGENTIC MESH — ARCHITECTURE
═══════════════════════════════════════════════════════════════

USER QUERY
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  AGENT 06 — Q&A SYNTHESIS ENGINE (ORCHESTRATOR)             │
│  • Front door for all user queries                          │
│  • Routes to 1 or more specialist agents                    │
│  • Synthesises all agent outputs into one cited response    │
│  • Enforces citation-mandatory output standard              │
└─────────────────────────────────┬───────────────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
    ┌─────────▼──────┐  ┌────────▼───────┐  ┌────────▼──────────┐
    │ DATA FOUNDATION │  │  INTEL LAYER   │  │  SYNTHESIS LAYER  │
    │                │  │                │  │                   │
    │ Agent 01 VDR   │  │ Agent 07 Wells │  │ Agent 12 Liabs    │
    │ Agent 02 Prod  │  │ Agent 09 Contr │  │ Agent 15 Sensitiv │
    │ Agent 03 Audit │  │ Agent 10 ARO   │  │ Agent 16 Title    │
    │ Agent 05 Price │  │ Agent 11 Reg   │  │ Agent 19 Risk ★   │
    │                │  │ Agent 13 Comps │  │ Agent 20 Integr   │
    └────────────────┘  │ Agent 14 Bench │  └───────────────────┘
                        └────────────────┘
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  │
              ┌───────────────────▼───────────────────┐
              │          AGENT 04 — FINANCE CALCULATOR  │
              │  (called as sub-routine by all agents   │
              │   that produce financial outputs)       │
              └───────────────────────────────────────┘
                                  │
              ┌───────────────────▼───────────────────┐
              │         AGENT 08 — HSE SCANNER          │
              │  (runs in parallel with VDR triage;    │
              │   feeds findings into risk register)   │
              └───────────────────────────────────────┘

★ Agent 19 (Risk Scorecard) is the TERMINAL aggregator —
  always the last agent to run; aggregates _master_findings.json

═══════════════════════════════════════════════════════════════
```

---

### 5.3 Query Routing Table

| User Query Pattern | Route to Agent(s) |
|-------------------|------------------|
| "What documents are in the VDR?" | Agent 01 |
| "What's missing from the data room?" | Agent 01 |
| "Generate the data request list" | Agent 01 |
| "What is the production history of [well]?" | Agent 02 → Agent 07 |
| "How does production compare to the CPR forecast?" | Agent 02 + Agent 03 |
| "Are there inconsistencies between the CPR and the IM?" | Agent 03 |
| "What is the NPV / IRR at $[X] oil?" | Agent 04 + Agent 05 |
| "Is the price deck in the CPR aggressive?" | Agent 05 |
| "Show me the current oil forward curve" | Agent 05 |
| "How are the wells performing?" | Agent 07 |
| "Which wells are underperforming?" | Agent 07 |
| "Are there any HSE red flags?" | Agent 08 |
| "What does the safety case say?" | Agent 08 |
| "What does the JOA say about ROFR?" | Agent 09 |
| "Extract the key terms from all contracts" | Agent 09 |
| "When do the licences expire?" | Agent 09 + Agent 11 |
| "What is the ARO liability?" | Agent 10 |
| "What is the decommissioning cost P50 vs balance sheet?" | Agent 10 |
| "What regulatory consents do we need?" | Agent 11 |
| "What is the consent-to-assign timeline?" | Agent 11 |
| "What is the Day-1 liability waterfall?" | Agent 12 |
| "What is the hedge book MTM?" | Agent 12 + Agent 05 |
| "What have comparable deals traded at?" | Agent 13 |
| "Where does this deal sit vs the market?" | Agent 13 |
| "Are the opex assumptions reasonable?" | Agent 14 |
| "Benchmark these well costs vs the basin" | Agent 14 |
| "What is the NPV sensitivity to oil price?" | Agent 15 |
| "Show me the tornado chart" | Agent 15 |
| "Reverse-engineer the seller's financial model" | Agent 15 |
| "Is the WI% consistent across all documents?" | Agent 16 |
| "Trace the chain of title for Licence X" | Agent 16 |
| "What is the overall deal risk?" | Agent 19 |
| "Generate the IC risk scorecard" | Agent 19 |
| "Generate the 100-day integration plan" | Agent 20 |
| Complex / multi-part / cross-workstream question | Agent 06 → routes to all relevant agents |
| Any question not fitting above | Agent 06 — assess and route |

---

### 5.4 Agent Dependency Rules & Build Order

The following rules define the required build order for agents. An agent listed as a dependency must be functional before the dependent agent will produce reliable outputs.

```
BUILD ORDER — SPRINT SEQUENCE

SPRINT 1 (Must be live before any deal work):
  Agent 01 (VDR Inventory) ──────────────────────────► No dependencies
  Agent 04 (Finance Calculator) ─────────────────────► No dependencies (can run with manual inputs)
  Agent 06 (Q&A Synthesis / Orchestrator) ───────────► Calls all others; must be built first as shell
  Agent 08 (HSE Scanner) ────────────────────────────► Agent 01

SPRINT 2 (Build before intelligence layer):
  Agent 02 (Production DB) ──────────────────────────► Agent 01
  Agent 03 (Consistency Auditor) ─────────────────────► Agents 01, 02, 05, 09
  Agent 05 (Price Curves) ────────────────────────────► Agent 01

SPRINT 3 (Intelligence layer — requires Sprint 2 complete):
  Agent 07 (Well Cards) ──────────────────────────────► Agent 02
  Agent 09 (Contract Extractor) ──────────────────────► Agent 01
  Agent 10 (ARO Aggregator) ──────────────────────────► Agents 01, 02
  Agent 11 (Regulatory Checker) ──────────────────────► Agents 01, 09
  Agent 13 (Comps Finder) ────────────────────────────► Agent 02
  Agent 14 (Opex Benchmarking) ───────────────────────► Agent 02
  Agent 15 (Sensitivity Analyser) ─────────────────────► Agents 02, 04, 05, 09, 10

SPRINT 4 (Synthesis layer — requires Sprint 3 complete):
  Agent 12 (Liability Schedule) ──────────────────────► Agents 05, 09
  Agent 16 (Title Validator) ─────────────────────────► Agents 01, 09
  Agent 19 (Risk Scorecard) ──────────────────────────► ALL agents (terminal — runs last)
  Agent 20 (Integration Plan) ────────────────────────► Agents 09, 11, 12, 16

POST-SPRINT 4:
  Agent 17 (Decline Modeller) ─────────────────────────► Agent 02
  Agent 18 (ESG Scanner) ─────────────────────────────► Agents 01, 02
```

### 5.5 Master Findings Schema

All agents write their material findings to a shared `_master_findings.json` file. This is the input to Agent 19 (Risk Scorecard). Every finding entry follows this schema:

```json
{
  "finding_id": "F001",
  "agent_source": "Agent_10",
  "workstream": "HSE",
  "deal_id": "PROJECT_CORSAIR",
  "severity": "CRITICAL",
  "category": "ARO",
  "description": "Balance sheet ARO provision ($9.0M) is 33% below CPR P70 estimate ($13.4M). Gap = $4.4M.",
  "documents_cited": [
    {"filename": "Byron_AnnualReport_2024.pdf", "section": "Note 12 — ARO", "page": 47},
    {"filename": "Byron_CPR_Sep2025.pdf", "section": "Section 8 — Decommissioning", "page": 112}
  ],
  "financial_impact": {"low": 0, "mid": 4400000, "high": 9200000, "currency": "USD"},
  "recommended_action": "Request P70 ARO indemnity or price adjustment in SPA negotiations",
  "status": "OPEN",
  "human_acknowledged": false,
  "timestamp": "2026-02-26T09:15:00Z"
}
```

---

<!--
=============================================================================
END OF PART 4
Next file: Aigis_DD_DomainKnowledge_PART5_Standards_Benchmarks_Glossary_Appendix.md
=============================================================================
-->
