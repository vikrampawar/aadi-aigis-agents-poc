# Aigis Agent Mesh — Self-Learning: Current State & Improvement Roadmap
**Prepared: 01 March 2026 | Status: For Review**

---

## Part 1 — Current Self-Learning Inventory

The mesh currently implements **9 distinct learning mechanisms**, all of which operate post-run and are human-gated before application.

| # | Mechanism | Trigger | Persisted To | Applied When |
|---|-----------|---------|-------------|-------------|
| 1 | **Learned Patterns** | Human approves a suggestion | `{agent}/memory/learned_patterns.json` | Every subsequent run (`patterns` param) |
| 2 | **Improvement Suggestions** | Every run — output auditor LLM | `{agent}/improvement_history.json` + global queue | On human approval → seeds patterns |
| 3 | **Approval Rate Tracking** | Every suggestion resolution | `improvement_history.json → approval_stats` | Gates auto-apply eligibility |
| 4 | **Auto-Apply Eligibility** | Rate ≥ 80%, n ≥ 10 | Computed from approval_stats | User offered toggle |
| 5 | **Auto-Apply Toggle** | User CLI command | `improvement_history.json` (flags + threshold) | Future runs above confidence threshold |
| 6 | **Run History** | Every agent run | `{agent}/memory/run_history.json` | Performance tracking / debugging |
| 7 | **Audit JSONL Log** | Every agent run | `{deal_id}/_audit_log.jsonl` | Compliance / query; input fail → abort |
| 8 | **Domain Knowledge Cache** | First tag request per session | In-memory class dict | All subsequent requests in session |
| 9 | **Cross-Agent Suggestion Routing** | Output auditor detects cross-agent issue | Target agent history + global queue | On approval by human reviewer |

**What this gives us today:** A human-supervised, audit-trailed system that accumulates classification and extraction patterns across deals, with a pathway to cautious automation. It is correct, trustworthy, and conservative by design.

**What it does not yet give us:**
- Any model of *who the buyer is* or *what they are trying to achieve*
- Semantic or query-specific retrieval of domain knowledge
- Accumulation of context across agents within a single pipeline run
- Learning from bid outcomes (did the company win? was the DD right?)
- Comparative framing against similar past deals

The remainder of this document addresses those gaps.

---

## Part 2 — Gap Analysis by Dimension

### 2.1 Information Retrieval

**Current behaviour:** `DomainKnowledgeRouter` matches `DK_TAGS` by string → loads entire matching files → concatenates into one context block → injects into every agent run. There is no query-specific filtering, no ranking by relevance, no chunking.

**Root cause of gap:** The original design correctly prioritised session-level caching (for speed) over semantic precision (for accuracy). This was the right trade-off at launch but becomes limiting as DK grows.

**Specific problems that manifest:**

| Problem | Consequence |
|---------|------------|
| Full files always loaded regardless of query | When generating a bid recommendation, the agent receives all of `upstream_vdr_playbook.md` — most of which is irrelevant — consuming context window and diluting signal |
| No retrieval based on deal-specific parameters | A deepwater GoM deal and an onshore US deal both load the same DK files because both match the `upstream_dd` tag |
| No knowledge of which DK sections are *used* | There is no feedback loop telling us whether the injected DK actually influenced the output, so we cannot learn which sections are high-utility |
| DK gaps are invisible | When an agent produces a low-confidence answer because no relevant DK exists, that gap is flagged in the audit but not queued as a "please add this to DK" action |
| Historical deal data (Agent 02 SQLite) is not DK | The richest source of comparable data — prior deals run through the system — is inaccessible to the DK router |

---

### 2.2 Contextualisation of Data

**Current behaviour:** Each agent receives: (a) the DK context string, (b) its own learned patterns, (c) the raw inputs from the calling agent or user. There is no shared context object that accumulates as agents run in sequence.

**Root cause of gap:** Agents were built as independent tools before the mesh existed. The mesh framework added tool-calling and suggestions, but did not add a shared deal-level context layer.

**Specific problems that manifest:**

| Problem | Consequence |
|---------|------------|
| No cumulative deal context | When Agent 06 (report generator) runs, it does not automatically have Agent 02's extracted financials. It must either re-extract or have them passed manually |
| Pattern learning is keyword-level, not semantic | Patterns say "files matching `LOE_*.xlsx` → category `Technical/LOS`". They cannot express "this deal's LOE/boe is 40% above GoM benchmark, flag for audit" |
| No temporal weighting of patterns | A pattern confirmed once on one deal 2 years ago is weighted the same as a pattern confirmed across 15 deals last quarter |
| No comparative framing | When the system reports "PDP NPV10 = $1,026mm", it has no way to say "this is the 95th percentile of all GoM deepwater deals we have seen" — because it doesn't track that cross-deal statistic |
| Agent outputs are siloed | Agent 04 calculates NPV10; Agent 06 cannot access it without being explicitly passed the result. The deal-level knowledge is lost between agent calls |

---

### 2.3 Strategic Fit / Company's View of Offer Basis

This is the most material gap and the one with the highest commercial value to address.

**Current behaviour:** Bid recommendations use generic GoM market multiples drawn from the `board_dd_report_playbook.md`. The system has no knowledge of:
- Who the acquirer is
- What they are trying to achieve
- What return thresholds they apply
- What they have bid before, and at what prices
- How their portfolio affects the value they place on a specific asset

**Root cause of gap:** The current architecture has a domain knowledge layer (what oil & gas industry does) and an agent layer (how to analyse a VDR), but **no buyer layer** (who is making this decision and why).

**Consequence:** The bid recommendation of "$700–800mm" for Project Coulomb is market-correct but not *company-specific*. For BP (who co-owns Na Kika FPS), the same asset might rationally be worth $950–1,100mm due to infrastructure synergies. For an onshore US operator with no deepwater capability, it might not be worth bidding at all. The current system cannot distinguish between these cases.

**Specific gaps:**

| Gap | Consequence |
|----|------------|
| No acquirer investment thesis | System cannot distinguish "strategic fit" from "market multiple" — two very different bid drivers |
| No operational capability model | System cannot flag "this buyer cannot operate this asset" before significant DD spend |
| No return threshold model | System uses market multiples; real acquirers use IRR hurdles and NPV/CAPEX thresholds that vary by buyer |
| No bid history / calibration | System has no way to learn "this acquirer consistently bids 0.65× PDP NPV10, not 0.75×" |
| No portfolio context | System cannot assess whether an asset creates concentration risk, fills a production gap, or adds diversification value |
| No competitive intelligence | System cannot model that Coulomb has a very limited buyer pool (deepwater operators only), which should shift bid strategy vs. a shelf asset with 20 qualified buyers |
| No outcome feedback loop | System never learns whether its DD was right — whether the NPV10 was realised, whether the flagged red flags materialised |

---

## Part 3 — Proposed Improvements

### Priority Framework

Each improvement is rated on:
- **Value:** Strategic impact on output quality and buyer differentiation (1–5)
- **Effort:** Engineering complexity to implement (S/M/L/XL)
- **Dependency:** What must exist first

---

### 3.1 Acquirer Profile Layer ⭐ Highest Priority

**Value: 5/5 | Effort: M | Dependency: None**

**The problem:** The system treats every company using Aigis as the same generic buyer. In reality, a PE firm, an NOC, and an independent operator all value the same asset very differently.

**The solution:** A structured `acquirer_profile.json` document (one per Aigis deployment / per client) that the agents inject alongside DK context. It captures the *buyer's lens* — their strategy, thresholds, and constraints.

**Proposed structure:**
```json
{
  "acquirer_name": "Tamarind Upstream Capital",
  "profile_version": "1.2",
  "last_updated": "2026-03-01",

  "investment_thesis": {
    "primary_objective": "production_growth",
    "secondary_objective": "infrastructure_control",
    "rationale": "Building a mid-tier GoM operator platform; targeting assets with existing infrastructure ownership and 10-30 kboed production range",
    "asset_preferences": ["GoM shelf", "GoM deepwater tie-back", "mature producing"],
    "asset_avoid": ["onshore US", "exploration-stage", "heavy ARO >$20/2P boe"]
  },

  "financial_thresholds": {
    "minimum_irr_pct": 15.0,
    "minimum_npv_multiple": 1.3,
    "maximum_ev_pdp_npv10_multiple": 0.85,
    "maximum_ev_boed_usd": 28000,
    "preferred_deal_size_mm": {"min": 50, "max": 800},
    "maximum_leverage_ratio": 2.5,
    "required_payback_years_max": 6
  },

  "operational_capabilities": {
    "can_operate_deepwater": true,
    "max_water_depth_ft": 8000,
    "can_operate_subsea_tieback": true,
    "has_bsee_operator_cert": true,
    "regions": ["GoM", "UKCS"],
    "minimum_staff_for_ops": 5,
    "max_concurrent_drilling_programmes": 2
  },

  "strategic_premiums": {
    "operator_role": 0.05,
    "infrastructure_ownership_platform": 0.08,
    "production_gap_fill_30pct_uplift": 0.12,
    "portfolio_diversification_benefit": 0.04
  },

  "portfolio_context": {
    "current_production_boed": 8500,
    "target_production_boed": 25000,
    "current_leverage_x": 1.8,
    "existing_assets": ["GoM shelf: Block A", "GoM shelf: Block B"],
    "committed_capex_next_3yr_mm": 120
  },

  "negotiation_preferences": {
    "prefers_asset_sale_over_share_sale": true,
    "willing_to_use_cvr_structures": true,
    "max_deferred_consideration_pct": 20,
    "preferred_warranty_period_months": 18
  }
}
```

**How it integrates:**
- `acquirer_profile.json` is loaded by `AgentBase` alongside DK context
- It is injected into every valuation, SWOT, and recommendation prompt
- Specific fields drive automatic adjustments:
  - If `current_production_boed = 8,500` and `target = 25,000`, a deal adding 27,000 boepd scores highly on strategic fit
  - If `max_water_depth_ft = 8,000` and the asset is at 7,565 ft, the agent automatically notes this is at the capability boundary
  - If `minimum_irr_pct = 15%` and the deal IRR at mid-case is 12%, the agent flags this as below threshold

**New output this enables:** Instead of "Recommended bid: $700–800mm (market multiples)", the system produces: "Recommended bid: $820–880mm reflecting: (a) strategic production gap fill (+12% premium), (b) Na Kika infrastructure play (+8%), offset by (c) capability boundary risk at 7,565 ft (–5%). This exceeds your standard EV/PDP multiple of 0.75× — board must explicitly approve the strategic premium."

---

### 3.2 Deal Context Object (Shared Pipeline State) ⭐ High Priority

**Value: 4/5 | Effort: M | Dependency: None**

**The problem:** Each agent in a pipeline run starts fresh. Agent 06 (report generator) cannot read Agent 02's extracted financials without them being explicitly re-passed. Context fragments are lost between agent calls.

**The solution:** A lightweight `DealContext` object initialised when a pipeline starts and passed through every agent call. Each agent reads from it (prior agent outputs) and writes to it (its own outputs).

**Proposed structure:**
```python
@dataclass
class DealContext:
    deal_id: str
    asset_fingerprint: dict     # type, geography, water_depth, operator, reserves_mmboe
    vdr_summary: dict           # Agent 01 output (file inventory, gaps, quality score)
    extracted_data: dict        # Agent 02 output (key metrics, latest values)
    financial_model: dict       # Agent 04 output (NPV10, IRR, bid range)
    comparables: list[dict]     # Matched historical deals from comp database
    agent_flags: list[dict]     # Accumulated risk flags across all agents
    accumulated_narrative: str  # Running deal summary for context injection
```

**How it integrates:**
- Each `AgentBase.invoke()` call accepts an optional `deal_context: DealContext`
- At the end of each run, the agent contributes its outputs back to the shared object
- When running a full pipeline (Agent 01 → 02 → 04 → 06), the `DealContext` is passed through and enriches at each step

**New capability this enables:**
- Agent 06 automatically has Agent 02's NPV figures without re-extraction
- Agent 04's bid recommendation is informed by Agent 01's VDR quality score ("VDR rated 6/10 — apply additional uncertainty discount of 5% to NPV")
- The final report can cite "Agent 02 extracted LOE/boe of $4.51 from P&L; Agent 04 validated this against NSAI operating expense model"

---

### 3.3 Query-Specific DK Retrieval

**Value: 4/5 | Effort: L | Dependency: Chunked DK files**

**The problem:** The DK router loads entire files matched by tag. A 5,000-word playbook is injected even when only one section is relevant to the current query.

**The solution (two-phase):**

**Phase A — Structural chunking (M effort, high immediate value):**
- Split each DK file into sections at `## ` heading boundaries
- Store a chunk registry: `{file: [{heading, first_line, word_count, key_terms}]}`
- At query time, the agent specifies `dk_query: str` alongside `DK_TAGS`
- DK router uses a lightweight LLM call (or TF-IDF) to select top-3 relevant sections per file
- Inject only the selected sections, with breadcrumb: `[Excerpt from: board_dd_report_playbook.md § GoM Bid Convention]`

**Phase B — Embedding-based retrieval (L effort, high long-term value):**
- Pre-embed all DK chunks using a small embedding model (text-embedding-3-small)
- At query time, embed the agent's current task description and retrieve top-k chunks by cosine similarity
- Enable cross-file retrieval: the most relevant chunk from any DK file, regardless of tag

**Immediate win even without Phase B:** Phase A (structural chunking) can be built with no new infrastructure, using existing LLM calls. A 10× reduction in DK context length means more of the context window is available for actual deal data.

---

### 3.4 DK Gap Detection & Enhancement Queue

**Value: 3/5 | Effort: S | Dependency: 3.3 Phase A**

**The problem:** When an agent produces a low-confidence answer because no relevant DK exists, the system flags it in the audit log but creates no actionable demand signal.

**The solution:**
- Extend the output auditor prompt with: "If any part of this answer relied on general reasoning rather than domain knowledge, identify the specific DK gap and describe what a DK document would need to cover."
- Auditor outputs `dk_gap_suggestions: list[{topic, rationale, suggested_source}]`
- These are written to a new file: `aigis_agents/memory/dk_enhancement_queue.json`
- A simple CLI command surfaces the queue: `review_memory.py --dk-gaps`

**Example output this generates:**
```
DK Gap: "Na Kika FPS life extension CAPEX benchmarks"
Rationale: Agent recommended bid discount for life extension risk but no DK section
covers historical deepwater FPS life extension costs, so estimate was speculative.
Suggested source: Add TSB/Petrofac deepwater FPS decom/life-extension cost benchmarks
                  to technical_analyst_playbook.md § Facility Life Extension.
```

**Value:** Turns passive knowledge gaps into active DK improvement requests. Over time, the DK library grows in exactly the areas where the system is weakest.

---

### 3.5 Comparable Deal Database & Cross-Deal Pattern Learning

**Value: 5/5 | Effort: L | Dependency: Agent 02 at scale (multiple deals processed)**

**The problem:** Every deal is treated as entirely new. The system has no way to say "this asset looks like Project Corsair but with 20× the reserves — here's how the analysis differed."

**The solution:**
- Extend Agent 02's database schema with a `deal_fingerprints` table:
  ```sql
  CREATE TABLE deal_fingerprints (
    deal_id, asset_type, geography, water_depth_ft,
    operator, pdp_npv10_mm, reserves_2p_mboe,
    aro_per_boe, loe_per_boe, oil_fraction_pct,
    bid_recommended_mm, bid_actual_mm, outcome,
    outcome_date, post_acq_npv10_mm
  );
  ```
- When a new deal is assessed, automatically query for the 3 nearest neighbours by fingerprint (using weighted Euclidean distance on normalised fields)
- Return comp summary as structured context: "3 comparable deals found: [summary table]"
- Feed comps into Agent 04 bid calibration: "vs. comps, this asset's NPV/boe is 12% premium — adjust multiple accordingly"

**Payoff grows with deal volume:** The first deal has no comps. After 5 deals, it's mildly useful. After 20 deals, it becomes the richest calibration source in the system. **Start building this structure now even with no data — the design decision to collect it is more important than having the data yet.**

---

### 3.6 Bid History & Outcome Feedback Loop

**Value: 5/5 | Effort: M | Dependency: 3.1 (Acquirer Profile) + deals over time**

**The problem:** The system makes bid recommendations but never learns whether they were right. The feedback loop — bid submitted, deal won/lost, asset performance vs. model — does not exist.

**The solution:** A structured `bid_history.json` file per acquirer (part of their profile):
```json
{
  "deal_id": "project_coulomb",
  "deal_name": "Project Coulomb",
  "asset_fingerprint": {...},
  "aigis_recommended_bid_mm": 770,
  "aigis_recommended_multiple": 0.75,
  "actual_bid_submitted_mm": 800,
  "outcome": "lost",
  "estimated_winning_bid_mm": 920,
  "lesson_learned": "Na Kika strategic premium underweighted — BP strategic buyer",
  "pdp_npv10_at_bid_mm": 1026,
  "actual_pdp_npv10_post_acq_mm": null
}
```

**How the learning loop closes:**
1. After each deal, user logs outcome in the bid history (5-minute task)
2. Before the next bid recommendation, Agent 04 loads bid history and runs pattern analysis:
   - "In 3 of 4 lost bids, Aigis recommended below winning price by average 18%"
   - "In all 4 won bids, recommended multiple was within 0.05× of actual bid"
   - "Deepwater GoM bids consistently underestimated strategic premium to existing operators"
3. System recalibrates its multiple recommendations accordingly

**This turns Aigis from a market-benchmarking tool into a company-specific bidding intelligence engine.** After 10–15 deals, the bid recommendations will be calibrated to the specific acquirer's revealed preferences — a capability no generic tool can replicate.

---

### 3.7 Portfolio Fit Scoring

**Value: 4/5 | Effort: S | Dependency: 3.1 (Acquirer Profile)**

**The problem:** The SWOT analysis describes deal-specific strengths/weaknesses but has no portfolio-level perspective. The board needs to know "is this a good deal in isolation, or a good deal for us specifically?"

**The solution:** Add a `PortfolioFit` section to every report, automatically scored against the acquirer profile:

```markdown
## Portfolio Fit Assessment

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Geographic alignment | 9/10 | GoM deepwater matches target geography |
| Asset type alignment | 10/10 | Subsea tie-back — preferred operating model |
| Operational capability | 7/10 | Within deepwater capability but at boundary (7,565 ft vs 8,000 ft max) |
| Production gap fill | 10/10 | +27,000 boepd → reaches 35,500 vs 25,000 target |
| Financial return alignment | 6/10 | Mid-case IRR 14.2% vs 15% threshold (marginal) |
| Capital allocation fit | 7/10 | $800mm base bid ± committed pipeline = 2.3× leverage (within 2.5× limit) |

**Overall portfolio fit: 8.2/10 — STRONG FIT**
*Primary concern: return threshold marginally below hurdle at current strip pricing.*
*Recommend: proceed if $750mm bid approved; stress test at $55 WTI.*
```

This is a relatively simple calculation once the acquirer profile exists. The scoring model is a weighted average of pre-defined dimensions. The output is immediately board-readable.

---

### 3.8 Competitive Intelligence Module

**Value: 3/5 | Effort: M | Dependency: Asset fingerprint from 3.5**

**The problem:** Bid strategy should vary based on the competitive landscape. Coulomb (limited to deepwater operators) has a very different competitive dynamic than a GoM shelf asset with 15 qualified bidders.

**The solution:** For each deal, automatically model the likely buyer universe:
- **Capability filter:** Who has the technical capability to operate this asset? (use publicly known operator certifications + BSEE operator lists)
- **Capital filter:** Who has the capital? (use public debt ratings, recent deal activity)
- **Strategic filter:** Who would pay a strategic premium? (Na Kika co-owner, adjacent acreage holders)
- **Output:** "Estimated 3–6 qualified buyers. BP likely strategic premium buyer. Recommend aggressive bid; limited competition means seller cannot achieve a competitive auction premium."

**Data sources available publicly:** BSEE operator database, SEC filings for operator production levels, public deal announcements for recent M&A activity.

---

### 3.9 Temporal Pattern Weighting

**Value: 2/5 | Effort: S | Dependency: None (enhancement to existing patterns)**

**The problem:** A pattern confirmed on a single deal 3 years ago is weighted identically to a pattern confirmed across 10 deals last month.

**The solution:** Add two fields to each pattern in `learned_patterns.json`:
- `days_since_last_confirmed: int`
- `confirmation_count: int`

Apply a decay function when loading patterns: patterns older than 365 days are flagged as `stale`; patterns confirmed in the last 90 days get `weight: HIGH`; others get `weight: MEDIUM`.

The agent prompt is adjusted: "High-weight patterns should be applied with high confidence. Medium-weight patterns should be applied but flagged for user confirmation. Stale patterns are informational only."

---

## Part 4 — Architecture: The Buyer Intelligence Stack

The most important structural addition is layering a **Buyer Intelligence Stack** above the existing Mesh. This can be visualised as three new layers sitting between DK and agents:

```
┌─────────────────────────────────────────────────────────────────┐
│                    BUYER INTELLIGENCE STACK                      │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Acquirer Profile │  │  Bid History /  │  │   Comparable    │  │
│  │  (static, v-c'd) │  │  Outcome Log    │  │   Deal DB       │  │
│  │                  │  │  (grows over    │  │  (grows over    │  │
│  │  Investment thesis  │  time)          │  │  time)          │  │
│  │  Return thresholds  │                 │  │                 │  │
│  │  Capabilities    │  │  Won/lost/price │  │  Fingerprints   │  │
│  │  Portfolio state │  │  Calibration    │  │  Comp tables    │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           └───────────────────┬┘───────────────────┘            │
│                               │                                   │
│              ┌────────────────▼────────────────┐                 │
│              │       Deal Context Object        │                 │
│              │   (shared pipeline state, deal-  │                 │
│              │    scoped, enriched by each agent) │               │
│              └────────────────┬────────────────┘                 │
└───────────────────────────────┼─────────────────────────────────┘
                                │ injected into each agent call
┌───────────────────────────────▼─────────────────────────────────┐
│                        AGENT MESH                                 │
│  Agent 01 → Agent 02 → Agent 04 → Agent 05 → Agent 06 → ...     │
│                                                                   │
│  Each agent: reads DealContext + writes outputs back to it       │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│              DOMAIN KNOWLEDGE LAYER (enhanced)                   │
│  Tags → Chunked sections → Query-specific retrieval              │
│  DK Gap Queue → Enhancement prioritisation                        │
└─────────────────────────────────────────────────────────────────┘
```

The Buyer Intelligence Stack changes the system's output from:
> *"At market multiples, this asset is worth $700–800mm"*

to:

> *"Given your investment thesis, portfolio gap, and historical bidding patterns, we recommend $820–870mm. This is 7% above your standard multiple to capture the infrastructure synergy value — which your 3 comparable deals show you have consistently under-priced. Your implied IRR at this level is 16.2%, above your 15% hurdle, assuming the NSAI 2P case. Walk away if the auction exceeds $950mm (0.93× PDP NPV10 — at this level you are paying for Probable reserves with proved-level certainty, inconsistent with your historical risk appetite)."*

---

## Part 5 — Implementation Roadmap

### Phase A — Foundation (Weeks 1–4) — Do Now

| # | Item | Effort | Who |
|---|------|--------|-----|
| A1 | Define and populate `acquirer_profile.json` schema + one instance for first client | S | Aaditya (strategy) + Vikram (schema) |
| A2 | Add acquirer profile injection to `AgentBase` (alongside DK context) | S | Vikram |
| A3 | Add portfolio fit scoring section to Agent 06 report template | S | Vikram |
| A4 | Add bid history file — structure only, start logging from next deal | S | Aaditya |
| A5 | Add `deal_fingerprints` table to Agent 02 schema (even if empty at first) | S | Vikram |

**Deliverable:** The Coulomb report re-run would include a portfolio fit section and a buyer-context-adjusted bid recommendation. Immediate, visible client value.

---

### Phase B — Deal Context Object (Weeks 4–8)

| # | Item | Effort | Who |
|---|------|--------|-----|
| B1 | Design `DealContext` dataclass + pass-through protocol in `AgentBase` | M | Vikram |
| B2 | Agent 01 → write VDR summary + quality score to DealContext | S | Vikram |
| B3 | Agent 02 → write extracted key metrics to DealContext | S | Vikram |
| B4 | Agent 04 → write NPV10 + bid recommendation to DealContext | S | Vikram |
| B5 | Agent 06 → read DealContext as primary source; VDR only for citations | M | Vikram |

**Deliverable:** Full pipeline runs once end-to-end with shared context; no re-extraction between agents.

---

### Phase C — DK Retrieval Enhancement (Weeks 8–16)

| # | Item | Effort | Who |
|---|------|--------|-----|
| C1 | Chunked DK index — parse all DK files by `##` headings, build chunk registry | M | Vikram |
| C2 | Query-specific DK selection — lightweight LLM call at agent invocation time | M | Vikram |
| C3 | DK gap detection in audit layer — structured gap suggestion output | S | Vikram |
| C4 | `dk_enhancement_queue.json` + CLI surface command | S | Vikram |
| C5 | Embed DK chunks (text-embedding-3-small or equivalent) for Phase C later | L | Vikram |

**Deliverable:** 60–70% reduction in DK context per agent call; gap detection creates systematic DK improvement backlog.

---

### Phase D — Comp Database & Outcome Learning (Weeks 16–32, ongoing)

| # | Item | Effort | Who |
|---|------|--------|-----|
| D1 | Populate deal fingerprints for Corsair + Coulomb (initial seed data) | S | Aaditya |
| D2 | Comp retrieval logic in Agent 04 — query fingerprint DB for nearest neighbours | M | Vikram |
| D3 | Comp table injection in bid recommendation prompt | S | Vikram |
| D4 | Bid history logging — log outcome for each deal processed | Ongoing | Aaditya |
| D5 | Bid calibration analysis — Agent 04 reads bid history and adjusts multiples | L | Vikram |
| D6 | Post-acquisition variance tracking — compare NPV10 at bid vs actual at 12mo | M | Aaditya + Vikram |

**Deliverable:** After ~10 deals, the system has company-specific calibrated bid recommendations. After ~20 deals, this is a proprietary competitive advantage that no off-the-shelf tool can replicate.

---

## Part 6 — What Makes This a Genuine Moat

The improvements above are technically achievable, but the **real value** is not in the technology — it's in the proprietary data that accumulates over time. Each element of the Buyer Intelligence Stack becomes more valuable with use:

| Data Asset | After 5 Deals | After 20 Deals | After 50 Deals |
|------------|-------------|---------------|---------------|
| Acquirer profile | Static document | Partially validated against outcomes | Continuously refined by outcome data |
| Bid history | 5 data points | Regression-grade calibration | Predictive model of company's bid behaviour |
| Comp database | 5 comps | Meaningful peer group | Proprietary regional benchmark database |
| DK library | Static playbooks | Enhanced by 10–20 gap-filling additions | The deepest sector-specific DK available |
| Pattern library | Classification patterns | Valuation patterns + risk patterns | Full DD pattern library across asset types |

**The strategic insight:** A PE firm or NOC that runs 10 GoM deals per year through Aigis will, by Year 3, have an intelligence layer that is genuinely proprietary and not reproducible by a new entrant running the same software on their first deal. This is the platform value of the mesh architecture — it gets smarter the more it is used, in a way that is unique to each client.

---

## Summary: Priority Order

| Priority | Item | Why Now |
|----------|------|---------|
| **1** | Acquirer Profile Layer (§3.1) | Highest value; S effort; transforms every output immediately |
| **2** | Portfolio Fit Scoring (§3.7) | S effort; requires profile; board-readable output |
| **3** | Deal Context Object (§3.2) | Enables all future cross-agent intelligence |
| **4** | DK Chunking + Query Retrieval (§3.3) | Context quality improvement; no new infra required |
| **5** | Deal Fingerprint DB (§3.5) | Structure now; data comes with deals |
| **6** | DK Gap Detection (§3.4) | S effort; compounds DK value over time |
| **7** | Bid History Logging (§3.6) | Start immediately; analysis becomes possible after 10 deals |
| **8** | Comparative Framing (§3.5 query logic) | Needs 5+ deals in DB |
| **9** | Competitive Intelligence (§3.8) | Needs acquirer profile + public data integration |
| **10** | Temporal Pattern Decay (§3.9) | S effort; needs 12+ months of data to matter |

---

*Document prepared by Aigis Analytics — Aigis Agent Mesh v2.0*
*For review by: Aaditya Chintalapati and Vikram Pawar*
*Next action: Approve acquirer profile schema; define first client instance (Tamarind / Aigis own use for Byron / Coulomb)*
