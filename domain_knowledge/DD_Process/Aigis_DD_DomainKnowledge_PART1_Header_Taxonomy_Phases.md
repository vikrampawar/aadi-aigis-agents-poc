# Aigis Analytics — Upstream O&G M&A Due Diligence: Full Domain Knowledge Document

<!--
=============================================================================
ASSEMBLY INSTRUCTIONS — READ BEFORE COMBINING
=============================================================================
This document is split into 5 parts. To assemble the full file:

  PART 1 → Aigis_DD_DomainKnowledge_PART1_Header_Taxonomy_Phases.md
           [THIS FILE] — Header + How to Use + Section 1 + Section 2

  PART 2 → Aigis_DD_DomainKnowledge_PART2_Workstreams_Technical_Financial_Legal.md
           Section 3.1 Technical | 3.2 Financial | 3.3 Legal

  PART 3 → Aigis_DD_DomainKnowledge_PART3_Workstreams_HSE_Operational_Strategic.md
           Section 3.4 HSE | 3.5 Operational | 3.6 Strategic

  PART 4 → Aigis_DD_DomainKnowledge_PART4_VDR_Workflow_Agent_Mapping.md
           Section 4 VDR Workflow | Section 5 Agent Mapping & Orchestration

  PART 5 → Aigis_DD_DomainKnowledge_PART5_Standards_Benchmarks_Glossary_Appendix.md
           Section 6 Output Standards | Section 7 Benchmarks | Section 8 Glossary
           Section 9 Regulatory References | Section 10 Change Log | Appendix A

To assemble: open a blank .md file, then paste each part in order 1 → 5.
Remove these assembly instruction comments after merging.
=============================================================================
-->

**Version:** 1.0
**Date:** 26 February 2026
**Author:** Aigis Analytics — compiled from live BD practice + published industry frameworks
**Purpose:** Dual-use document —
  (1) Human reference for Aigis BD team — navigate by phase or workstream
  (2) System coordinator context / domain knowledge for the Aigis Agentic Mesh
**Scope:** Upstream oil & gas M&A — corporate acquisitions, asset deals, JV entries, distressed sales
**Sources:** Lexology M&A Legal DD Framework · EAG Inc. DD Process Guide · Embark O&G DD Tips ·
            EIA M&A Analysis · BSEE TIMS API · NSTA Industry Stewardship · SPE-PRMS Reserves
            Standard · ThoughtTrace O&G DD · CapLinked VDR Best Practices · Jones Day Energy M&A ·
            Latham & Watkins Energy M&A · Wood Mackenzie DD Framework · IOGP Safety Standards

---

## HOW TO USE THIS DOCUMENT

### For Human Users (BD Team / Analysts)
- Navigate by **phase** (Section 2) for deal-stage-specific guidance
- Navigate by **function** (Section 3) for workstream checklists and red-flag criteria
- Use **Section 4** for the VDR day-by-day workflow
- Use **Section 7** for benchmark numbers when challenging seller assumptions
- Use **Section 8** (Glossary) for unfamiliar terms

### For the Aigis Agentic Mesh System Coordinator
This document is your primary domain knowledge base. When a user submits a query:

1. **Identify deal phase** — which of the 6 phases in Section 2 are they in?
2. **Identify workstream(s)** — which of the 6 functions in Section 3 does the query belong to?
3. **Select agent(s)** — use the routing table in Section 5.3 to select the right agent(s)
4. **Frame response** — use the terminology, red-flag criteria, and benchmarks defined in this document
5. **Cite everything** — apply the citation-mandatory standard in Section 6.1
6. **Escalate 🔴 findings** — any Critical finding must be surfaced before downstream use

**Key Coordinator Rules:**
- Agent 06 (Q&A Synthesis Engine) is always the front door for user queries — route through it
- Agent 01 (VDR Inventory) should be run first on any new deal before other agents
- Agent 19 (Risk Scorecard) is the terminal aggregator — only call after all other agents have run
- When in doubt, call Agent 06 and let it route — never guess at agent selection
- Never fabricate a metric or citation — if unsure, flag LOW confidence and request human review

---

## SECTION 1: DEAL TAXONOMY & CORE CONCEPTS

### 1.1 Deal Types

| Type | Description | Key DD Differences vs Standard |
|------|-------------|-------------------------------|
| **Corporate M&A** | Acquiring the entire company / all shares (share purchase) | Inherits ALL liabilities — disclosed and undisclosed. Broader legal/employment/tax scope. W&I insurance common. Full balance sheet scrutiny. |
| **Asset Acquisition** | Acquiring specific licences, leases, wells, or infrastructure | Cleaner — buyer selects which assets and liabilities to take. More precise price adjustment mechanism. Title defects more easily ring-fenced. |
| **JV Entry / Farm-In** | Acquiring a working interest in an existing licence | Requires JOA amendment or new JOA. Existing operator often remains. ROFR exercise risk from co-venturers. Narrower DD scope (no corporate). |
| **Distressed / Receivership** | Asset or company sold under financial pressure (administration, Chapter 11) | Compressed timeline. Seller provides minimal reps and warranties. Higher execution risk. Potential for unrecorded liabilities. Lower price floor — but higher risk premium required. |

### 1.2 Upstream Asset Type Hierarchy

| Asset Type | SPE-PRMS Class | Characteristics | Primary DD Focus |
|-----------|----------------|----------------|-----------------|
| **PDP** (Proved Developed Producing) | 1P subset | Producing wells. Cash flow Day 1. | Decline rate, GOR/WC trends, facility condition, actual vs forecast production. |
| **PDNP** (Proved Developed Non-Producing) | 1P subset | Wells drilled but shut-in or behind-pipe. | Workover cost, reason for shut-in, reservoir pressure support, timing of first production. |
| **PUD** (Proved Undeveloped) | 1P subset | Undrilled locations within offsetting units. 12-month drill commitment. | Drill cost, rig availability, capital commitment schedule, technical risk. |
| **Probable (2P)** | 2P increment | Lower certainty undrilled or upside. | G&G quality, analogue performance, CPR risking methodology. |
| **Possible (3P)** | 3P increment | Speculative upside. | Play concept, seismic support, unrisked vs risked NPV. |
| **Contingent Resources (2C)** | Contingent | Development not yet sanctioned. | FDP pathway, regulatory approvals needed, timeline to sanction. |
| **Prospective Resources** | Prospective | Undrilled exploration. | Seismic data quality, play concept, GPoS (geological probability of success). |

### 1.3 Key Financial Metrics — Definitions for Agent Use

| Metric | Formula / Definition | Red Flag Threshold | Benchmark Source |
|--------|---------------------|-------------------|-----------------|
| **PV-10** | NPV of future net cash flows discounted at 10% | Bid > 80% of PDP PV-10 without clear upside justification | SPE / SEC |
| **EV/2P** | Enterprise Value ÷ 2P reserves ($/boe) | >$12/boe GoM shallow; >$18/boe GoM deepwater — check vs comps | PLS/SEC filings |
| **EV/boepd** | Enterprise Value ÷ current daily production | >$40K/boepd mature GoM; >$60K deepwater — check vs comps | PLS/SEC filings |
| **Lifting cost** | Total LOE ÷ net boe produced ($/boe) | >$25/boe GoM shelf is elevated; >$35/boe requires explanation | BSEE/EIA |
| **Netback** | Realised price − royalty − lifting cost − transport ($/boe) | Negative netback = value destruction; flag immediately | Calculated |
| **F&D cost** | Capex ÷ reserve additions ($/boe) | >$15/boe for GoM PUD additions requires justification | BSEE/Rystad |
| **IRR** | Internal rate of return on total investment (%) | <12% unlevered IRR at $65 Brent = below most company hurdles | Company disclosures |
| **RLI** | 2P reserves ÷ annual production (years) | <5 years = high decline risk; >15 years = comfortable | Calculated |
| **Decline rate** | % annual production reduction (exponential) | >25%/yr = high decline; material capital required to sustain | CPR / production DB |
| **GOR trend** | Gas-Oil Ratio (scf/bbl) — rising = depletion signal | Rising >10%/yr = early depletion flag; approaching bubble point | Production DB |
| **Water cut trend** | % of produced fluid that is water — rising = influx | >70% WC with rising trend = escalating disposal costs | Production DB |
| **ND/EBITDA** | Net debt ÷ EBITDA (leverage ratio) | >3.0x post-close = stress territory; >2.5x = caution | Rating agencies |

### 1.4 Reserves Classification Standards

**SPE-PRMS (Society of Petroleum Engineers — Petroleum Resources Management System)**
Used for: most independent CPR work; international transactions; reservoir engineers' standard.

| Class | Probability | Definition |
|-------|------------|-----------|
| **1P (Proved)** | P90 — ≥90% probability | Only PDP + PDNP + PUD within 12-month programme. Conservative. |
| **2P (Proved + Probable)** | P50 — ≥50% probability | Primary valuation metric for upstream M&A. |
| **3P (Proved + Probable + Possible)** | P10 — ≥10% probability | Upside / optimistic case. |
| **2C (Best Estimate Contingent)** | Mid-case | Development not sanctioned — excluded from reserves until FID. |

**SEC Standard**
Used for: US publicly listed companies (10-K SEC filings); more conservative than SPE-PRMS.
- Uses 12-month average pricing (not forward curve)
- Requires reasonable certainty for each category
- PV-10 computed using SEC pricing → typically lower than SPE-PRMS PV-10

**Critical for Aigis agents:** Always confirm which standard a CPR is using before comparing numbers across documents. CPR under SPE-PRMS and SEC will give different 2P numbers for the same asset.

### 1.5 Fiscal Terms Reference

| Term | Definition | Where It Appears in DD |
|------|-----------|----------------------|
| **Working Interest (WI)** | % ownership in the licence/lease. Bears % of all costs. | JOA, licence, CPR, IM, financial model — must match across all |
| **Net Revenue Interest (NRI)** | WI × (1 − royalty rate). The % of gross revenue actually received. | Critical for financial model. NRI < WI = royalty burden. |
| **ORRI** | Overriding Royalty Interest — royalty carved from WI by prior owner. Reduces NRI without reducing WI. | Legal DD — reduces buyer's economics; often undisclosed |
| **Royalty** | Government or landowner share of production. Deducted before NRI. | US GoM federal leases: 12.5–18.75% |
| **ROFR** | Right of First Refusal — right to match any third-party offer before a partner can sell. | JOA/licence — major deal risk; must map all ROFR holders |
| **ROFO** | Right of First Offer — right to receive first offer before marketing to third parties. | JOA/licence — less restrictive than ROFR but still creates friction |
| **AFE** | Authority for Expenditure — budget approval document for a well or project. Threshold triggers JOA voting rights. | JOA — AFE threshold determines non-consent risk |
| **Non-Consent** | Right of a JOA partner to opt out of an AFE. Consenting parties recoup a penalty (typically 300–500%) before non-consenting party recovers. | JOA — affects drilling programme execution risk |
| **Sole Risk** | Right of one party to drill a prospect outside the JOA at their own cost. | JOA — creates complex ownership situations |
| **Carried Interest** | One party (carrier) pays a share of another party's (carried) costs in exchange for WI or a promote. | Farm-in/JV structures — affects economics and obligations |
| **Net Profits Interest (NPI)** | Right to a % of net profits above a threshold. Value depends on profitability. | Legal DD — affects economics in downside scenarios |

---

## SECTION 2: DEAL PHASES — END-TO-END PROCESS

> **For the Aigis System Coordinator:** Use this section to identify which phase a user is in when they ask a question. The phase determines which agents are most relevant and what outputs are expected.

---

### Phase 1: Origination & Screening

**Typical Duration:** 1–2 weeks
**Objective:** Identify and triage the opportunity. Decide whether to commit resources to a detailed evaluation.
**Trigger:** Inbound teaser/CIM, proactive sell-side outreach, off-market approach, public announcement.

**Key Activities:**
1. Review teaser / CIM (Confidential Information Memorandum) — initial IM provided by seller or broker
2. Execute NDA to access further materials (process letter, more detailed IM)
3. Screen against corporate strategy: asset type, geography, commodity mix, operatorship preference, deal size
4. High-level financial screen: approximate EV range using public production/reserves data + IM headline numbers
5. Check antitrust pre-clearance requirements (HSR, EU/UK merger control) at indicative deal size
6. Competitive assessment: who else is in the process? What is seller motivation and timeline?
7. Internal approval to proceed to Phase 2 — typically VP/SVP corporate development level
8. Establish deal team: BD lead, technical, financial, legal, operations
9. Open deal code name. Initiate confidentiality and Chinese wall protocols.
10. Engage external advisers if needed: independent CPR firm, external legal counsel, M&A bank

**Key Documents Available at Phase 1:**
- Teaser (1–2 pages: headline production, reserves, geography, asking guidance)
- CIM/IM (20–80 pages: detailed asset description, summary financials, CPR headlines, process instructions)
- Any publicly available CPR (if target is a listed public company — ASX, LSE, NYSE)
- BOEM/NSTA/NPD public licence and production data
- Comparable transaction data (SEC 8-K filings, press releases, PLS database)

**Go/No-Go Criteria for Phase 2:**
- Strategic fit confirmed (asset type, geography, commodity mix match portfolio strategy)
- Approximate EV range fits within capital budget
- No obvious deal-killer visible at screen level (extreme ARO, zero operability, antitrust hard stop)
- Regulatory consent pathway exists (BOEM, NSTA, any national government)
- Competitive dynamics manageable (not a sealed auction with >10 bidders at same price sensitivity)

**Aigis Agents Active at Phase 1:**
- Agent 06 (Q&A Synthesis): answering questions from the IM/teaser
- Agent 13 (Comps Finder): finding comparable transactions for initial bid anchoring
- Agent 04 (Finance Calculator): running initial EV screens from IM headline numbers
- Agent 05 (Price Curves): checking IM/CPR price deck vs current market

---

### Phase 2: Preliminary Evaluation

**Typical Duration:** 2–3 weeks
**Objective:** Develop initial valuation range. Submit Non-Binding Indicative Offer (NBIO) if process requires it.

**Key Activities:**
1. Review IM in full depth. Build financial screening model from IM data only.
2. Technical team: review CPR summary, headline production profiles, reserves by category
3. Legal team: review licence summary, JOA summary terms, known regulatory constraints from public data
4. Financial team: build indicative P&L, cash flow, NAV from IM assumptions; compute indicative EV range
5. Develop preliminary bid strategy: indicative price range (low / mid / stretch) + walk-away
6. Identify key assumptions requiring validation in full DD (list of highest-impact uncertainties)
7. Prepare NBIO / indicative bid letter: price range, conditions, timeline, exclusivity request
8. Internal IC approval for NBIO submission (VP/Director level typically sufficient for NBIO)
9. Prepare questions for management meeting / site visit (if seller grants access pre-full DD)
10. Confirm process rules with seller/adviser: first-round deadline, exclusivity timing, DD access terms

**Key Outputs:**
- Indicative screening model (financial — not final model)
- NBIO letter (or go/no-go memo if no formal NBIO required)
- Preliminary risk register (qualitative — based on IM information only)
- Priority DD question list (organised by workstream)
- Preliminary comps table (Agent 13)

**Aigis Agents Active at Phase 2:**
- Agent 04 (Finance Calculator): indicative EV, EV/2P, EV/boepd from IM data
- Agent 05 (Price Curves): price deck challenge
- Agent 13 (Comps Finder): comparable transactions table
- Agent 06 (Q&A Synthesis): all questions from the IM

---

### Phase 3: VDR Deep Dive & Full Due Diligence

**Typical Duration:** 4–6 weeks (compressed to 3 in competitive processes)
**Objective:** Validate ALL assumptions from Phase 2. Identify deal-breakers, price adjustments, and risk mitigants. Prepare IC memo and binding bid.

> **This is the primary phase for Aigis agent deployment. See Section 4 for the VDR day-by-day workflow. See Section 5 for full agent mapping.**

**Sub-phases:**
| Sub-Phase | Days | Focus |
|-----------|------|-------|
| VDR Triage | Day 1–2 | Access, document inventory, gap analysis, first DRL |
| Parallel Deep Dive | Day 3–7 | All 6 workstreams running concurrently in VDR |
| Analysis & Red Flag Review | Day 8–14 | Findings synthesis, management Q&A, red flag meeting |
| IC Preparation | Day 15–21 | Risk scorecard, comps, IC memo drafting, peer review |
| Bid Submission | Day 22–28 | IC approval, binding bid, legal red lines, SPA heads |

**Key Outputs (Full List):**
- VDR inventory and gap analysis report (Agent 01)
- Production database with consistency audit (Agents 02 + 03)
- Buyer's independent financial model (Agents 04, 05, 15)
- Well performance cards, fleet summary (Agent 07)
- HSE risk summary (Agent 08)
- Contract key terms extraction, red flag register (Agent 09)
- ARO waterfall P50/P70/P90 (Agent 10)
- Consent-to-assign tracker (Agent 11)
- Day-1 liability waterfall (Agent 12)
- Comparable transactions table (Agent 13)
- Cost benchmarking report (Agent 14)
- Sensitivity analysis and base case validation (Agent 15)
- Title chain and WI reconciliation (Agent 16)
- Technical risk scorecard — IC-ready (Agent 19)
- Individual DD reports per workstream (6 reports, 5–15 pages each)
- IC memo (deal rationale + valuation range + key risks + bid recommendation)
- Binding bid letter

---

### Phase 4: Bid Calibration & Investment Committee

**Typical Duration:** 1–2 weeks
**Objective:** Obtain IC approval for binding bid. Finalise bid strategy and SPA approach.

**IC Memo Standard Structure:**
1. Executive Summary: deal rationale, recommended action, EV range, confidence level
2. Asset Overview: key metrics, current production, reserves (1P/2P/3P), location, operatorship
3. Technical Summary: CPR highlights, buyer's independent view, key technical risks
4. Financial Summary: valuation methodology (NAV, comps, EV/2P), buyer's base case NPV, sensitivity
5. Risk Summary: key risks ranked, mitigants, price adjusters proposed, deal-breakers resolved
6. Legal & Regulatory: key legal risks, ROFR position, consent-to-assign timeline, SPA key issues
7. Strategic Fit: portfolio rationale, combined company pro-forma metrics
8. Financing Plan: funding structure, leverage impact, hedging
9. Recommendation: bid price range, walk-away price, escalation authority

**IC Decision Outcomes:**
- ✅ Approve: proceed with binding bid at recommended price
- ✅ Conditional: proceed subject to resolution of specific items (e.g., ARO indemnity, ROFR waiver)
- ⚠️ Revise: re-run analysis with revised assumptions or structure before resubmitting
- ❌ Withdraw: deal economics or risks do not meet company hurdles

**Aigis Agents Active at Phase 4:**
- Agent 19 (Risk Scorecard): providing one-page IC traffic light
- Agent 15 (Sensitivity Analyser): final bid pricing scenarios
- Agent 13 (Comps Finder): bid positioning vs market

---

### Phase 5: Negotiation & Signing

**Typical Duration:** 2–6 weeks
**Objective:** Negotiate and execute SPA/PSA. Obtain all required consents. Confirm financing.

**Key Activities:**
1. SPA/PSA negotiation: reps & warranties, indemnities, price adjustment mechanism, effective date, MAC
2. ROFR/ROFO process: notify all partners with rights; manage pre-emption timeline (typically 30 days notice + 15 days to match)
3. Regulatory consents: submit BOEM/NSTA/NPD applications for consent to assign; antitrust filing if required
4. Financing: execute credit agreement, confirm equity funding, bind hedging strategy
5. W&I (Warranty & Indemnity) insurance: if applicable, instruct insurer, complete underwriting due diligence, bind policy
6. SPA signing (typically conditioned on regulatory consents being obtained)
7. TUPE/WARN employee notifications if required
8. Initiate 100-day integration plan development (Agent 20)

**Critical SPA Terms to Negotiate (Red Lines):**

| Term | Buyer's Typical Red Line | Seller's Typical Red Line |
|------|------------------------|--------------------------|
| **Effective Date** | Set as early as possible (buyer wants production from effective date) | Set as late as possible |
| **Locked-Box vs Completion Accounts** | Locked-box (price certainty) | Completion accounts (protection against leakage) |
| **Fundamental Reps Survival** | Indefinite survival | 6–12 months |
| **General Reps Survival** | 24–36 months | 12–18 months |
| **Indemnity Cap** | 100%+ of purchase price | 20–30% of purchase price |
| **De Minimis Claim** | Low (to capture small claims) | High (to exclude small claims) |
| **MAC Definition** | Broad trigger, few exclusions | Narrow trigger, many exclusions (esp. commodity price) |
| **Price Adjustment — ARO** | Adjust against P90 | No adjustment; fixed price |
| **Title Reps** | Broad, long survival, uncapped | Narrow, limited to known issues |

---

### Phase 6: Close & Post-Acquisition Integration

**Typical Duration:** 4–8 weeks to close from signing; 100 days post-close for integration
**Objective:** Complete all conditions to closing. Transition operations. Integrate asset into buyer's portfolio.

**Pre-Close Conditions Checklist:**
- [ ] All regulatory consents received (BOEM/NSTA assignment consent, antitrust clearance)
- [ ] All ROFR periods expired or waivers received from all ROFR holders
- [ ] Financing confirmed and commitment letters in place
- [ ] All material conditions in SPA satisfied or waived
- [ ] Technical data room fully received, catalogued, and loaded into buyer's systems
- [ ] Day-1 insurance policy bound
- [ ] Employee notifications complete (TUPE/WARN)
- [ ] Day-1 operational plan approved and distributed

**100-Day Post-Close Framework:**

| Period | Priority Actions |
|--------|----------------|
| **Day 1** | Legal transfer executed · Bank mandates signed · Licence transfer notifications filed with BOEM/NSTA · JV partner notifications sent · Insurance effective · Emergency response takes over |
| **Day 1–30** | AP/AR transition · Payroll transfer · SCADA and production reporting live · Vendor contract novation · HSE management system handover complete |
| **Day 31–100** | IT systems integration · Vendor renegotiation · G&A rationalisation starts · First post-close production report vs IC case · 100-day integration review meeting |
| **Day 100+** | Synergy tracking vs business case · Post-acquisition review vs IC assumptions · Reserve report update · Strategy for Year 1 drilling programme |

**Aigis Agents Active at Phase 6:**
- Agent 20 (Integration Plan): generating the 100-day plan from DD findings
- Agent 19 (Risk Scorecard): monitoring against IC assumptions post-close

---

<!--
=============================================================================
END OF PART 1
Next file: Aigis_DD_DomainKnowledge_PART2_Workstreams_Technical_Financial_Legal.md
=============================================================================
-->
