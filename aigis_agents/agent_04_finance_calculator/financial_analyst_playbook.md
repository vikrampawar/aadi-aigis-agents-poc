# Financial Evaluation of Upstream Oil & Gas Assets  
### First‑Principles Framework and Rules of Thumb for an AI Agent

This document provides a **financial** lens on upstream oil and gas assets for use by an AI assistant.  
It assumes that subsurface and well performance are being handled elsewhere and focuses on value, cash flows, leverage capacity, pricing assumptions and downside protection.[web:26][web:29][web:30][web:33][web:36]

---

## 0. Core Financial Principles

The agent should:

- Anchor all analysis in **cash flows from reserves** (not just volumes), using transparent price, cost and timing assumptions.[web:26][web:29][web:33][web:36]
- Distinguish clearly between:
  - Proved vs probable vs possible reserves/resources.
  - Developed vs undeveloped.
  - Base (No Further Activity, NFA) vs management plan with capex.[web:26][web:29][web:33]
- Treat **NFA** as the key downside case: no new drilling, only essential sustaining capex, run the field to economic limit and then decommission.[web:26][web:29]
- Always cross‑check:
  - Management decks vs independent reserve reports vs bank/RBL “banking case”.
  - Price assumptions vs forward strip and typical bank price decks.
  - Lifting costs and breakevens vs peer data and public benchmarks.[web:26][web:29][web:30][web:31][web:34][web:37][web:40]

---

## 1. Quality of Reserves and Resources from a Financial Perspective

### 1.1 Financial Relevance of Reserve Categories

From a financier’s perspective, reserves quality is about **cash flow certainty and timing**:

- Proved developed producing (PDP) and producing 1P reserves are the primary collateral base for reserve‑based lending (RBL), especially in North America.[web:26][web:29][web:33]
- Proved developed non‑producing (PDNP) and proved undeveloped (PUD) may be given some credit, but often at higher haircuts and subject to development milestones.[web:26][web:29][web:30]
- Probable and possible reserves (2P/3P) tend to be **equity upside** or carry very conservative lending credit outside diversified portfolios.[web:26][web:29]

Key checks for the agent:

- How much value (PV at a relevant discount rate) sits in PDP vs PDNP vs PUD vs 2P/3P?
- What fraction of NPV10 (or bank PV9) is in:
  - Short‑cycle, developed reserves vs long‑dated, undeveloped projects?
- Are the economic assumptions (prices, costs, fiscal terms) consistent across categories?[web:26][web:33][web:36]

### 1.2 Reserves Quality Indicators

Financially “high‑quality” reserves typically exhibit:

- Stable, predictable decline and low operational risk (e.g. conventional PDP).[web:26][web:29]
- Low lifting costs vs expected realized prices (strong margin headroom).[web:34][web:37][web:40]
- Limited dependence on large, lumpy capex to unlock value (especially in a tight capital or regulatory environment).[web:26][web:29]
- Tenure security: licence terms, PSC duration or lease expiry leave sufficient time to recover booked reserves.[web:38]

The agent should downgrade financial quality where:

- A large portion of NPV sits in long‑dated PUD or contingent projects with uncertain sanction or regulatory risk.[web:26][web:29]
- Forecasts assume materially higher uptime, lower OPEX, or higher prices than historical experience or market benchmarks support.[web:29][web:30][web:24]

---

## 2. Commodity Price Assumptions vs Strip and Bank Price Decks

### 2.1 Understanding Price Decks

A **price deck** is a forward curve of price assumptions used for valuation and lending.[web:39][web:30]

Key decks:

- Market **forward strip** (e.g. NYMEX/ICE futures adjusted for quality/location differentials).
- Bank or lender **RBL price deck**, usually conservative vs strip and updated regularly (often at least quarterly).[web:39][web:30]
- Management’s **internal planning deck**, which may be more optimistic for budgeting or strategy.

Regulatory guidance for banks on reserve‑based energy lending emphasises:

- Bank price decks should be conservative, analytically supported, and benchmarked to market indices such as NYMEX strip.[web:30][web:39]
- Decks must be refreshed frequently to protect against price declines.[web:30]

### 2.2 Agent Checks on Price Assumptions

For any evaluation, the agent should:

- Extract the **price deck** used in:
  - Independent reserves report / CPR.
  - Management case model.
  - Bank or RBL term sheet (if available).
- Compare to:
  - Current and historical forward strip.
  - Typical lender behaviour in the region (e.g. discount to strip, long‑term real price flatlining).[web:29][web:30][web:39][web:33]

Rules of thumb:

- If management prices are materially above strip and bank decks, the agent should:
  - Treat valuation as **optimistic** and run a downside case using strip/bank prices.
- If a CPR or banking case uses the same prices for 1P, 2P, 3P, note that price uncertainty is not captured; only volume/timing is.[web:26]
- Where no explicit bank deck is provided, the agent may approximate:
  - Short‑term prices close to strip, transitioning to a conservative long‑term real price (e.g. flat or modest escalation) in line with regulatory guidance.[web:30][web:39][web:33]

---

## 3. Lendability and Borrowing Base (RBL) Calculations

### 3.1 How RBLs Use Reserves

Reserve‑based loans use reserves as collateral and size the **borrowing base** as a fraction of the discounted value of approved reserves.[web:26][web:29][web:33]

Common practice:

- Europe/UK:
  - Smaller, single‑asset companies: RBL often based on 1P only.
  - Larger, diversified portfolios: may use 2P for some assets, with more conservative haircuts.[web:26]
- North America:
  - Typically based on PDP and PDNP, with limited PUD credit.[web:26][web:29][web:33]

Banks usually:

- Take a CPR, field development plan and other inputs to build their own **Banking Case** and technical note, which may differ from management’s case.[web:26][web:29]
- Use discount rates around 9–10% for PV (e.g. PV9, PV10) in sizing borrowing bases.[web:26][web:27][web:33]

### 3.2 Borrowing Base Mechanics

A stylised borrowing base calculation:

- Start with forecast cash flows from eligible reserves under the bank price deck and bank case production/cost assumptions.[web:26][web:29][web:30][web:33]
- Discount at a bank‑specified rate (often around 9–10%).[web:33]
- Apply advance rates / haircuts by reserve category (illustrative):
  - 60–65% of PV for PDP.
  - Lower percentages (or zero) for PDNP/PUD/2P depending on term sheet.[web:26][web:29][web:27][web:30]
- The resulting number is the **borrowing base**, subject to limits such as:
  - Facility cap.
  - Ratio tests (e.g. loan‑life coverage ratio, reserve life index constraints).[web:29][web:30][web:33]

Some practitioners describe setting the borrowing base at ~60% of PV9 for PDP under the bank price deck as a rule of thumb, but this is always subject to specific term sheets and credit judgement.[web:27][web:29][web:33]

### 3.3 Agent Tasks on Lendability

The agent should:

- Identify all existing and proposed debt facilities:
  - RBL, term loans, notes, vendor loans, mezzanine, trader pre‑payments.
- For each RBL:
  - Extract base case, price deck, discount rate, advance rates, coverage ratios, amortisation profile and covenants from term sheets or credit agreements.[web:29][web:30]
- Independently recompute an indicative borrowing base using:
  - Bank deck (if available) or conservative deck approximating bank practices.
  - PDP‑focused cash flows for single‑asset or concentrated portfolios.
- Flag where:
  - Management’s expected debt capacity exceeds typical RBL sizing logic.
  - Banking case volumes or costs are more conservative than reserves/CPR.[web:26][web:29][web:30][web:33]

---

## 4. Lifting Costs and Breakeven Prices (NFA vs Management Plan)

### 4.1 Definitions

Key cost concepts:

- **Lifting cost**: operating costs required to keep existing wells producing (labour, routine maintenance, utilities, chemicals, routine workovers), excluding new drilling and major development capex.[web:34][web:40]
- **Cash operating cost per barrel**: lifting cost plus variable transportation/tariffs, production taxes and other per‑barrel burdens.[web:34][web:37][web:40]
- **Full‑cycle breakeven**: price required to cover all costs including exploration, development capex and an appropriate return on capital.[web:31][web:37]
- **Field‑in‑decline breakeven**: price at which it is still worthwhile to keep producing existing wells (no growth capex); lifting cost is the primary reference.[web:37][web:34][web:40]

Empirical benchmarks:

- Large, low‑cost producers like Saudi Aramco can have lifting costs in the ~3–6 USD/bbl range.[web:40]
- Majors such as ExxonMobil and Chevron report lifting costs roughly in the low‑teens USD/bbl range.[web:40]
- Shale and higher‑cost basins may exhibit significantly higher full‑cycle breakevens, often cited in the 40–60 USD/bbl range for a 10% return depending on play and period.[web:31][web:37]

### 4.2 NFA vs Management Plan

For each asset, the agent should construct at least two cost views:

- **NFA Case**:
  - No new drilling or major growth capex.
  - Only sustaining/HSSE‑critical capex and lifting costs.
  - Field treated as a “cash cow” in decline.[web:37][web:26]
- **Management Plan**:
  - Includes proposed drilling, workovers, facility expansions and associated capex.
  - May result in higher short‑term capex but higher production and reserves.[web:26][web:36]

For each case, compute:

- Lifting cost per barrel (and per boe), both historical and forecast.[web:34][web:40]
- Economic limit price:
  - The minimum price (net of royalties and production taxes) at which operating cash flow remains positive.[web:37][web:31][web:40]

The Schlumberger/MIT work emphasises that lifting cost is the most appropriate breakeven metric for late‑life fields treated as cash cows, while full‑cycle metrics are relevant for investments in new wells and developments.[web:37]

### 4.3 Agent Checks and Rules of Thumb

The agent should:

- Compare:
  - Forecast lifting costs vs historical actuals.
  - Projected costs vs peer benchmarks (where available) to sense‑check realism.[web:34][web:37][web:40]
- Identify:
  - Fixed vs variable OPEX; rising water cut or aging infrastructure may push unit costs up as volumes decline.[web:24][web:31][web:34]
- Evaluate:
  - Whether management’s claimed breakeven prices are:
    - Lifting‑only (keep‑running).
    - “Half‑cycle” (drilling only).
    - Full‑cycle (including exploration, G&A and return on capital).[web:31][web:37][web:40]

Where the documentation is ambiguous (“our breakeven is 15 USD/bbl”), the agent should ask “**which breakeven?**” and re‑derive the relevant metric.[web:31][web:40]

---

## 5. Marketing Contracts, Offtake and Mezzanine / Trader Financing

### 5.1 Importance of Marketing Contracts

For upstream assets, **offtake and sales contracts** underpin realised price, exposure to basis differentials, and suitability for trader or mezzanine financing.[web:32][web:38]

Key contract types:

- Crude oil / gas / condensate sales agreements.
- Transportation and pipeline agreements.
- Processing and FPSO/FSO contracts.
- PSCs and concession/lease agreements where title transfer and lifting entitlements are defined.[web:38]

Due diligence guidance highlights the need to:

- Verify contracts are in full force and effect and review expiry dates and renewal provisions.[web:38]
- Understand pricing formulas (indexation, differentials, quality adjustments, discounts/premiums).[web:38][web:32]
- Assess whether remaining reserves and facility life are sufficient to achieve planned returns within contract terms.[web:38]

### 5.2 Trader / Mezzanine Financing

Commodity traders and specialist mezzanine funds may offer:

- **Pre‑payment or pre‑export finance** backed by future deliveries under sales contracts.
- **Stretch financing** where traditional banks are constrained, often at higher cost but with flexible structures.

They typically require:

- Clear, enforceable sales contracts with creditworthy counterparties.
- Transparent production forecasts and reserves to support delivery schedules.
- Robust security over export proceeds and appropriate hedging.[web:29][web:30][web:39]

Agent tasks:

- Identify all marketing and transportation contracts, including:
  - Volume commitments, take‑or‑pay clauses, destination and counterparty credit quality.[web:38]
- Map contract expiry vs reserves life and facilities life.
- Assess whether the offtake structure (e.g. fixed differentials, transparent indexation) is suitable for:
  - Bank RBLs (clear netback).
  - Trader pre‑payments (deliverability and price risk manageable).[web:29][web:30][web:38][web:39]

---

## 6. Payback, NFA Downside Protection and Near‑Term Cash Generation

### 6.1 Payback and Cash‑on‑Cash Metrics

From an acquirer’s standpoint, key questions include:

- How quickly is the **acquisition price** paid back from free cash flow?
- What is the downside cash generation on an NFA case over the next 3 years?

The agent should compute:

- Annual and cumulative **free cash flow** (FCF) under:
  - NFA case (no growth capex, only sustaining and decom where required).
  - Management case (with capex and growth).
- Simple payback period:
  - Years until cumulative FCF ≈ purchase price.
- Leverage‑adjusted metrics:
  - Debt paydown capacity from FCF, coverage of interest and amortisation.[web:29][web:30][web:33][web:36]

### 6.2 NFA Downside Protection

For downside protection analysis, the NFA case is often the key lens:

- Use conservative price deck (e.g. bank deck) and realistic uptime/opex assumptions.
- Run out the existing wells to economic limit and then include decom cash outflows.[web:29][web:30][web:23]

The agent should focus on:

- Aggregate NFA FCF over the first 3–5 years vs:
  - Acquisition price.
  - Any assumed debt used to fund the acquisition.
- Sensitivities:
  - Lower prices (e.g. minus 10–20 USD/bbl scenarios).
  - Lower uptime.
  - Higher opex/lifting cost.[web:29][web:30][web:33]

If the acquisition price can be substantially repaid from NFA FCF over the near term under conservative assumptions, the transaction may have strong downside protection; if not, risk is higher and more reliance is placed on growth projects.

---

## 7. Other Key Financial Focus Areas

### 7.1 Balance Sheet, Liquidity and Capital Structure

Due diligence checklists emphasise:

- Reviewing historical financial statements (3–5 years) for revenue, profitability, cash generation, leverage and liquidity.[web:32][web:35]
- Understanding existing debt instruments, covenants, maturity profile, hedging and any cross‑default or change‑of‑control provisions.[web:29][web:30]
- Assessing the ability to fund planned capex internally vs externally (RBL, bonds, equity, vendor financing, trader pre‑payments).[web:29][web:30][web:36]

### 7.2 Fiscal Terms and Tax

Financial performance is strongly affected by:

- Royalty rates, production taxes, severance and ad valorem taxes.
- Income tax, uplift allowances, ring‑fencing and loss carry‑forward rules.
- Special petroleum taxes and investment incentives in some regimes.

The agent should:

- Extract fiscal terms from PSCs, licences and legal summaries.[web:38]
- Ensure these terms are adequately reflected in cash‑flow and breakeven calculations, particularly for NFA vs management cases.

### 7.3 Environmental, Decommissioning and Regulatory Liabilities

Late‑life assets can carry significant **decommissioning** obligations and environmental liabilities:

- Regulatory frameworks (e.g. UK Petroleum Act, OSPAR 98/3) require approved decommissioning programmes and removal of installations, with cost often borne by licensees.[web:23]
- Decommissioning security agreements (DSAs) and similar arrangements allocate liability and require security to cover future decom costs.[web:17][web:20]

Financially, the agent should:

- Verify decom costs and timing are included in projections.
- Examine DSAs and SPAs for retained or joint liabilities.
- Consider the impact of decom on net asset value, NFA downside and RBL borrowing base availability.[web:23][web:17][web:20][web:29][web:30]

### 7.4 Contract, Legal and Operational Risks

Other financially material areas include:

- Material contracts: drilling, service, FPSO/FSO, pipeline, processing, JOAs, PSCs; termination rights and change‑of‑control clauses.[web:38][web:32][web:35]
- Litigation and disputes: contractual, tax, regulatory, environmental; potential contingent liabilities.[web:32][web:38]
- Infrastructure and logistics constraints: bottlenecks in transportation and storage that can cause curtailments or pricing discounts.[web:32][web:35]

The agent should treat these as **qualitative adjustments** to cash‑flow risk, potentially warranting higher discount rates or lower loan advance rates.

---

## 8. How the AI Agent Should Apply This Playbook

When evaluating an asset, the agent should:

1. Map the user’s question to the relevant sections (reserves quality, price assumptions, RBL, breakevens, offtake, NFA downside, other risks).
2. Extract factual inputs from:
   - CPRs/reserves reports, financial statements, models and RBL term sheets.
   - Price decks, hedging summaries, marketing contracts and DSAs.
3. Build structured cases:
   - NFA (downside) vs management plan (base/upside), each with transparent price, cost and capex assumptions.
   - RBL/banking case consistent with lender practices and covenants.[web:26][web:29][web:30][web:33]
4. Assess:
   - Reserves quality and cash‑flow certainty.
   - Lendability and borrowing base.
   - Lifting cost breakevens and NFA downside protection.
   - Contractual, fiscal, decom and operational risks.
5. Present:
   - Clear, referenced conclusions with confidence levels and sensitivities.
   - Explicit separation of observed data vs interpretation.
   - Reduced reliance on any conclusion not anchored in traceable documents or cross‑checked with multiple sources.

This playbook is intended as contextual guidance only; users should rely on specialist advisors and primary documents for investment and financing decisions.[web:26][web:29][web:30][web:33][web:23]

