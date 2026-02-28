# Golden Questions for Upstream Oil & Gas Asset Evaluation  
### Technical · Financial · Legal · ESG · Process (VDR Q&A Ready)

This document defines **Golden Questions** an AI agent should ask/answer when evaluating upstream oil & gas asset acquisitions.  
For each topic it provides:

- Representative **valuation / risk questions** for internal analysis.
- **Expected answer characteristics** (what “good” looks like).
- A ready **VDR Q&A question** to raise with the seller if required information is missing.

The agent should always:

- Source answers from traceable documents in the VDR (CPRs, models, contracts, ESG reports, regulatory filings).[web:38][web:43][web:41][web:48][web:53][web:57]
- Flag missing data and automatically assemble the corresponding VDR Q&A questions.

---

## 1. Technical & Reserves

### 1.1 Reserves Basis and Quality

**Golden Question (internal):**  
What is the classification, quality, and economic robustness of the reserves and resources (1P/2P/3P, 1C/2C, prospective) underpinning the asset value?

**Expected answer characteristics:**

- States the reserves classification system (PRMS / SEC) and effective date.[web:26][web:11]
- Breaks out volumes by category and maturity: PDP, PDNP, PUD, 2P, 3P, 2C, prospective.[web:26]
- Links reserves to **economic tests**: price deck used, discount rate, economic limit criteria, and whether all Reserves are commercial.[web:26][web:11]
- Comments on concentration of value in:
  - PDP vs long‑dated PUD/2C.
  - Single vs multiple fields/plays.
- Flags any obvious inconsistencies with historical production (e.g. reserves implying unrealistically high recovery factors or decline reversals).[web:26][web:19]

**VDR Q&A prompt (if unclear):**  
> Please provide the latest independent reserves report(s) for the assets, prepared under PRMS or SEC, including:
> - Detailed breakdown of 1P/2P/3P and PDP/PDNP/PUD by field and reservoir.  
> - Economic assumptions (price deck, OPEX, capex, discount rate, economic limit).  
> - Commentary on key risks and contingencies for undeveloped and contingent resources.

---

### 1.2 Historical Production vs Forecast

**Golden Question (internal):**  
How does historical production performance (rates, decline, water cut) compare to forecast profiles, and are there any unrecognised bottlenecks?

**Expected answer characteristics:**

- Summarises historical oil/gas/water production, decline trends, and key events (workovers, new wells, outages).[web:19][web:22]
- Compares historical decline rates and water‑cut trends with forecast curves; explains any planned mitigation (new drilling, compression, waterflood optimisation).
- Identifies capacity constraints:
  - Well, facility, water handling, gas compression, export.[web:24]
- Flags mismatches: forecasts exceeding historic peak rates or facility capacities without documented debottlenecking projects.[web:19][web:24]

**VDR Q&A prompt (if unclear):**  
> Please provide:
> - Monthly well‑ and field‑level production data (oil, gas, water) since first production.  
> - Forecast profiles used in the reserves/economic cases.  
> - Documentation of any known constraints (facilities, water handling, gas compression, export) and planned debottlenecking projects.

---

### 1.3 NFA (No Further Activity) Case

**Golden Question (internal):**  
What is the realistic NFA (No Further Activity) production and cash‑flow profile and how does it compare to management’s development plan?

**Expected answer characteristics:**

- Clearly defines NFA: no new wells, only integrity/sustaining capex, run to economic limit then decommission.[web:26][web:23]
- Provides a separate NFA production/cash‑flow profile vs the management/FD plan case.
- Quantifies differences in cumulative production, NPV and decom timing between NFA and management plan.

**VDR Q&A prompt (if unclear):**  
> Please provide a clearly defined “No Further Activity” (NFA) case showing production, OPEX, capex (sustaining only), and decom timing, separate from the management development case, together with any supporting technical/economic justification.

---

## 2. Financial & Valuation

### 2.1 Price Decks and Valuation Sensitivities

**Golden Question (internal):**  
What commodity price decks are used (CPR, management, bank/RBL), and how sensitive is value to moving to strip or conservative bank decks?

**Expected answer characteristics:**

- Tabulates:
  - CPR price deck(s).
  - Management planning deck.
  - Bank/RBL deck if available.[web:29][web:30][web:39]
- Compares to current forward strip and typical lender practice (discount to strip, long‑term flat real pricing).[web:29][web:30]
- Shows sensitivity of NPV and key metrics to alternative price decks (e.g. strip, bank deck, ±10–20 USD/bbl scenarios).

**VDR Q&A prompt (if unclear):**  
> Please provide:
> - The commodity price deck(s) underlying the reserves/economic evaluations (oil, gas, NGL), including currency and inflation assumptions.  
> - Any separate bank or RBL “bank case” price deck, if available.  
> - Sensitivity analysis of NPV and key metrics to alternative price decks (e.g. +/- 10–20 USD/bbl).

---

### 2.2 Borrowing Base and Lendability (RBL)

**Golden Question (internal):**  
What is the lendability of the asset under typical RBL structures and how does that compare to targeted leverage?

**Expected answer characteristics:**

- Summarises any **existing** RBL or debt: facility size, borrowing base, covenants, price deck, discount rate.[web:29][web:30]
- Runs an indicative borrowing base:
  - Bank price deck.
  - PDP‑heavy basis; advance rates by category (e.g. ~60–65% PV9 for PDP as reference where applicable).[web:27][web:29][web:33]
- Highlights constraints: short reserve life, concentration risk, tight covenants, decom exposure.

**VDR Q&A prompt (if unclear):**  
> Please provide:
> - Details of any existing or proposed reserve‑based lending facilities (term sheet/credit agreement), including bank price deck, discount rate, advance rates by reserve category, amortisation profile and key covenants.  
> - Any internal or bank analysis of borrowing base headroom and sensitivities.

---

### 2.3 Lifting Costs and Breakeven

**Golden Question (internal):**  
What are the unit lifting costs and breakeven prices under NFA and management cases, and how do they compare to peers?

**Expected answer characteristics:**

- Breaks out historical and forecast lifting costs (ex‑development capex) and total cash operating cost per boe.[web:34][web:37][web:40]
- Distinguishes:
  - Lifting‑only breakeven (keep‑running).
  - Full‑cycle breakeven for new projects.[web:31][web:37]
- Comments on cost trajectory as volumes decline (fixed vs variable OPEX, water‑handling impact) and benchmarks against typical cost ranges where relevant.[web:34][web:37][web:40]

**VDR Q&A prompt (if unclear):**  
> Please provide:
> - Historical and forecast lifting costs and total cash operating costs per boe (with breakdown of major OPEX categories).  
> - Management’s definition and calculation of “breakeven price” for the asset, including whether it is lifting‑only, half‑cycle or full‑cycle.  
> - Any benchmarking of lifting costs vs peer assets or portfolio averages.

---

### 2.4 NFA Downside and Payback

**Golden Question (internal):**  
On a conservative NFA case, what is the next‑3‑year free cash flow and payback on the acquisition price, and how robust is downside protection?

**Expected answer characteristics:**

- Computes 3–5 year FCF under NFA using conservative price deck and realistic OPEX/uptime.[web:29][web:30][web:33]
- Compares cumulative FCF with:
  - Acquisition price.
  - Any acquisition debt (including interest and amortisation).
- Provides simple payback period and downside sensitivities (price/uptime/OPEX).

**VDR Q&A prompt (if unclear):**  
> Please provide an NFA case financial model (under a conservative price deck) showing:  
> - Annual FCF for at least the next 5 years.  
> - Assumed acquisition price and any associated acquisition debt.  
> - Simple payback period of the acquisition price under this NFA case and supporting assumptions.

---

## 3. Legal & Contractual

### 3.1 Licence / PSC Validity and Term

**Golden Question (internal):**  
Are all licences/PSCs and key permits in full force and effect, and is the remaining term sufficient to recover planned reserves?

**Expected answer characteristics:**

- Lists each licence/PSC: grant dates, current phase, expiry dates, any extension rights.[web:38][web:43]
- Confirms “full force and effect” status and absence of uncured defaults or termination notices.[web:38][web:43]
- Compares remaining term to reserves and project timelines, highlighting any time pressure.

**VDR Q&A prompt (if unclear):**  
> Please provide:
> - Copies and summaries of all licences/PSCs and key permits for the assets, including current phase, expiry dates and any extension/renewal rights.  
> - Confirmation of whether they are in full force and effect, and disclosure of any defaults, waiver or termination notices received from authorities.

---

### 3.2 Change‑of‑Control, Pre‑Emption and Consents

**Golden Question (internal):**  
What consents, waivers and pre‑emption processes are required to transfer the interests, and how do they impact deal certainty and timing?

**Expected answer characteristics:**

- Identifies change‑of‑control and assignment restrictions in PSCs, licences, JOAs and key contracts.[web:43][web:38]
- Lists all required:
  - Government/regulator consents.
  - Waivers of pre‑emption / rights of first refusal.
- Links these to conditions precedent and realistic timelines.

**VDR Q&A prompt (if unclear):**  
> Please provide a schedule of all change‑of‑control and assignment restrictions and required consents/waivers (governmental, JV partners, counterparties), together with seller’s assessment of expected timelines and any precedent experience.

---

### 3.3 Warranties, Indemnities and Decom

**Golden Question (internal):**  
What warranties, indemnities and decommissioning security arrangements protect the buyer against title, environmental and decom risks?

**Expected answer characteristics:**

- Summarises SPA warranty package (title, licences, contracts, tax, environment, decom) and key limitations (caps, baskets, survival).[web:49][web:52][web:38]
- Identifies specific indemnities (tax, environmental, decom, litigation) and any RWI.[web:46][web:52]
- Explains decom obligations and security arrangements (DSAs, guarantees, letters of credit) and alignment with regulatory frameworks.[web:23][web:17][web:20]

**VDR Q&A prompt (if unclear):**  
> Please provide:
> - The latest draft SPA (or term sheet) including full warranty and indemnity package and limitations of liability.  
> - Details of decommissioning obligations (including cost estimates and timing) and any decommissioning security agreements or other security arrangements in place.

---

### 3.4 Liens, Litigation and Encumbrances

**Golden Question (internal):**  
Are there any liens, security interests, material litigation or regulatory investigations that could impair the asset value or transferability?

**Expected answer characteristics:**

- Lists:
  - Existing security interests, mortgages or liens over licences/PSCs, infrastructure or receivables.[web:42][web:32]
  - Material litigation and regulatory investigations (HSE, environment, anti‑corruption, tax).[web:38][web:32][web:48]
- States anticipated financial exposure and how risks are addressed (specific indemnities, escrows, price adjustments).

**VDR Q&A prompt (if unclear):**  
> Please provide:
> - A register of all existing security interests, mortgages and liens affecting the assets and confirmation of intended releases at closing.  
> - A schedule of all material litigation, arbitration, claims and regulatory investigations involving the assets or seller, including status, quantum and seller’s assessment of likely outcomes.

---

## 4. ESG & Climate

### 4.1 Jurisdictional Climate/ESG Policy Risk

**Golden Question (internal):**  
What are the key ESG and climate policy drivers in the asset’s jurisdiction and how could they affect costs, production constraints or approvals?

**Expected answer characteristics:**

- Summarises jurisdiction’s climate policy: net‑zero targets, sector decarbonisation plans, methane and flaring rules, carbon pricing mechanisms.[web:66][web:57]
- Highlights any upcoming regulatory changes (e.g. stricter methane/flare rules, climate disclosure, carbon tax increases) relevant to the asset life.[web:66][web:63]
- Qualitative assessment of transition risk level (low/medium/high) over asset life.

**VDR Q&A prompt (if unclear):**  
> Please provide:
> - Seller’s overview of key climate and ESG regulations applicable to the assets (including any carbon pricing, flaring/methane limits, disclosure obligations).  
> - Any internal or external assessments of anticipated regulatory changes that could materially affect costs, production or approvals over the asset life.

---

### 4.2 Carbon Intensity and Mitigation

**Golden Question (internal):**  
What is the asset’s current and projected carbon intensity, and what concrete mitigation measures are in place (flaring, methane, energy efficiency, CCUS)?

**Expected answer characteristics:**

- Provides quantitative metrics: Scope 1/2 emissions and upstream carbon intensity (kg CO₂e/boe), methane and flaring intensity.[web:58][web:61][web:67]
- Benchmarks against operator and peer averages, and against industry initiatives (e.g. OGCI targets).[web:58][web:67]
- Describes mitigation projects:
  - Gas capture, flaring reduction, LDAR, electrification, CCUS, offset use.[web:64][web:66][web:62][web:65]

**VDR Q&A prompt (if unclear):**  
> Please provide:
> - Historical and current GHG emissions data (Scope 1 and 2) and upstream carbon/methane/flaring intensity metrics for the assets.  
> - Details of existing and planned mitigation measures (gas capture, flaring reduction, methane abatement, energy efficiency, CCUS, use of offsets) and any associated targets.

---

### 4.3 Carbon Pricing and Financial Impact

**Golden Question (internal):**  
How are carbon prices and/or carbon credit costs reflected in the models, and what is their impact on opex, breakevens and valuation?

**Expected answer characteristics:**

- Identifies any applicable carbon taxes/ETS and assumed carbon prices in the financial model.[web:66]
- Converts carbon prices and intensity into incremental per‑boe cost and breakeven shifts.[web:66][web:37]
- Describes use of voluntary or compliance credits: volumes, cost assumptions, quality considerations.[web:62][web:59][web:65]

**VDR Q&A prompt (if unclear):**  
> Please provide:
> - Details of any carbon pricing mechanisms (taxes, ETS) applicable to the assets, including current and forecast carbon price assumptions in the financial model.  
> - Assumptions on use and cost of carbon credits/offsets (voluntary or compliance) and how these are reflected in opex and breakeven calculations.

---

### 4.4 Social, Governance and Third‑Party Risks

**Golden Question (internal):**  
Are there material social, human‑rights, community or governance risks (including third‑party integrity) that could disrupt operations or financing?

**Expected answer characteristics:**

- Summarises:
  - Community/land issues, local content obligations, human‑rights risks, security and protest history.[web:66][web:55]
  - Governance and compliance framework: anti‑corruption, sanctions, ESG reporting and controls.[web:60][web:63]
- Notes any controversies or investigations and potential impact on licence to operate or financing costs.[web:66][web:63][web:60]

**VDR Q&A prompt (if unclear):**  
> Please provide:
> - Social impact and stakeholder engagement summaries for the assets (including any historic or ongoing community disputes or resettlement issues).  
> - Details of the operator’s anti‑corruption, sanctions and ESG governance frameworks, including any past violations or investigations relevant to the assets.

---

## 5. Process & VDR Management

### 5.1 Dataset Completeness and Gaps

**Golden Question (internal):**  
Is the VDR complete enough for a robust evaluation, and what are the most critical data gaps that must be addressed via Q&A?

**Expected answer characteristics:**

- Lists key categories present/missing:
  - Technical: CPRs, production data, models, facility reports.  
  - Financial: models, historical financials, price decks, RBL docs.  
  - Legal: licences/PSCs, JOAs, SPAs, contracts, litigation, DSAs.  
  - ESG: emissions data, ESG reports, permits, social/HSSE records.[web:38][web:72][web:70][web:41][web:53][web:57]
- Prioritises missing items by impact and timing (must‑have vs nice‑to‑have).

**VDR Q&A prompt (generic):**  
> Following our initial review, several key datasets/documents appear to be missing or incomplete (see attached list by category: Technical, Financial, Legal, ESG).  
> Please confirm whether these exist and, if so, upload them to the VDR or clarify if they are unavailable and why.

---

### 5.2 Q&A Discipline – Linking Questions to Decisions

**Golden Question (internal):**  
For each major open risk or assumption, has a specific, targeted VDR Q&A been drafted that will materially improve decision‑making if answered?

**Expected answer characteristics:**

- Maintains a **Q&A log** mapping:
  - Risk/assumption → required document or clarification → drafted Q&A prompt → status (asked/answered/pending).
- Ensures Q&A questions are:
  - Precise, scoped, and reference specific documents or data gaps.[web:68][web:72]
- Avoids vague or open‑ended questions unlikely to yield decision‑useful responses within tight timelines.

**VDR Q&A prompt (pattern template):**  
> In relation to [Document/Topic Reference], please provide clarification on the following point(s):  
> - [Specific question 1]  
> - [Specific question 2]  
> Please also indicate whether any additional supporting documents exist (e.g. internal reports, regulatory correspondence) and, if so, upload them to the VDR.

---

## 6. How the Agent Should Use This File

When evaluating any asset, the AI agent should:

1. Run through these Golden Questions, auto‑checking the VDR for required evidence.
2. For each question:
   - Generate an internal answer summary with confidence level and references.
   - If data are missing or ambiguous, attach the relevant pre‑drafted VDR Q&A question.
3. Output:
   - A consolidated **Golden Questions scorecard** indicating which areas are well‑supported, weakly supported, or require seller clarification.
4. Allow human users to:
   - Review and edit Q&A prompts before submission.
   - Add bespoke questions for asset‑ or jurisdiction‑specific issues.

This file is intended as a practical playbook to structure due diligence, not as legal, financial, or technical advice; users should rely on specialists and primary documents for decisions.[web:38][web:43][web:41][web:53][web:57]

