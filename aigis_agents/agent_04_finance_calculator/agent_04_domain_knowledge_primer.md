# Agent 04 — Upstream Finance Calculator: Domain Knowledge Primer
**Version:** 1.0 | **Date:** 27 February 2026 | **Status:** Reference for Implementation & LLM Context  
**Scope:** Financial calculation engine for upstream oil & gas M&A due diligence  
**Not in scope:** Document classification, checklist scoring, VDR gap analysis (→ Agent 01)

---

## 1. AGENT MANDATE

Agent 04 is a **shared calculation tool** — a pure financial engine callable by any other agent in the mesh. It does not read VDR documents directly. It receives structured numeric inputs, executes upstream finance calculations, and returns results with full formula transparency and unit declarations.

**Callers:** Agent 06 (Q&A front door), Agent 07 (Well Cards), Agent 10 (ARO), Agent 12 (Liability Builder), Agent 15 (Sensitivity Analyser), Agent 19 (IC Scorecard)

**Core contract:**
- Every output shows: result, unit, formula, and inputs used
- Every input is validated before calculation; bad units raise a descriptive error, never a silent wrong answer
- No hardcoded price or cost assumptions — all rates passed as arguments

---

## 2. FOUNDATIONAL CONCEPTS

### 2.1 Cash Flow Spine

All upstream valuations are built on a **net cash flow** per period:

```
Net CF = Revenue − Royalties − Operating Costs − Capital Expenditure − Taxes − ARO Cash Outflows
```

Where:
- **Revenue** = Net production (boe) × Realised price ($/boe), adjusted for quality differentials and transport
- **Royalties** = Gross revenue × Royalty rate (%) — passed as input; varies by licence/jurisdiction
- **Operating Costs** = Fixed OPEX ($/month) + Variable OPEX ($/boe × production)
- **Capex** = Scheduled by period; includes drilling, workovers, facilities, sustaining
- **Taxes** = Taxable income × Effective tax rate — passed as input
- **ARO** = Decommissioning cash outflows in terminal period(s)

Agent 04 computes metrics derived from this spine. It does **not** build the full cash flow model — that is the seller's model or Agent 15's job. It ingests a pre-built cash flow array and computes the requested metric.

### 2.2 Two Mandatory Cases

Every financial analysis must distinguish:

| Case | Definition | Capex included |
|---|---|---|
| **NFA (No Further Activity)** | Existing wells only; sustaining/HSSE capex only; run to economic limit then decom | Sustaining only |
| **Management Plan** | Full development programme; all growth wells and facilities | Full capex schedule |

NFA is the **downside anchor** — the minimum value an acquirer can expect without executing any growth programme. It is the primary input for RBL borrowing base sizing and payback analysis.

### 2.3 Reserve Categories (Financial Relevance Only)

| Category | Certainty | RBL Credit | Equity Value |
|---|---|---|---|
| PDP (Producing) | Highest | Primary collateral | Downside |
| PDNP (Non-producing) | High | Partial credit | Base |
| PUD (Proved undeveloped) | Moderate | Limited/conditional | Base-upside |
| 2P (Prob.) | Moderate | Rarely | Upside |
| 3P (Poss.) | Low | None | Blue-sky |

Rule: **When in doubt, value PDP first.** PDP NPV is the most defensible number in any deal.

### 2.4 Discounting Convention

**Mid-period discounting** is the standard for upstream oil and gas:

```
PV = CF_t / (1 + r)^(t − 0.5)
```

Where `t` = period number (1 = Year 1), `r` = annual discount rate.

This reflects that cash flows are received throughout the year, not at year end. Use mid-period unless caller explicitly specifies end-of-period (e.g. for debt service schedules where payments are at period end).

---

## 3. METRICS LIBRARY

### 3.1 Valuation Metrics

---

#### `NPV(cash_flows, discount_rate, convention="mid")`
**Net Present Value**

```
NPV = Σ [ CF_t / (1 + r)^(t − 0.5) ]    [mid-period]
NPV = Σ [ CF_t / (1 + r)^t ]              [end-of-period]
```

- `cash_flows`: array of net cash flows, one value per period (annual or monthly)
- `discount_rate`: decimal (e.g. 0.10 for 10%)
- `convention`: "mid" (default) or "end"
- **Returns:** NPV in same currency unit as input cash flows

Rules:
- Year 0 cash flows (e.g. acquisition price as negative CF) are NOT discounted — they occur at t=0
- Always label output: "NPV at X% discount rate, mid-period convention"
- If monthly cash flows supplied, use monthly discount rate = `(1 + annual_rate)^(1/12) − 1`

---

#### `PV10(cash_flows)`
**PV at 10% discount — SEC standard**

Alias for `NPV(cash_flows, 0.10, "end")`. SEC rules require **end-of-period** discounting for standardised measure. Flag this distinction in output.

Common usage: PDP PV-10 is the primary valuation anchor for US GoM assets and the most-cited metric in M&A IM documents.

---

#### `IRR(cash_flows)`
**Internal Rate of Return**

The discount rate `r` at which NPV = 0. Solved numerically (Newton-Raphson or numpy `irr`).

```
0 = Σ [ CF_t / (1 + IRR)^t ]
```

- Input cash flows must include a negative value (investment) in Year 0 or early periods
- **Returns:** IRR as a decimal; display as percentage
- **Caveat output if:** multiple sign changes in cash flow array (multiple IRR problem) — flag to caller

---

#### `payback_period(investment, annual_cash_flows)`
**Simple Payback**

```
Payback = Year in which cumulative CF first ≥ investment
```

- `investment`: positive scalar (absolute value of acquisition price / initial outlay)
- `annual_cash_flows`: array of post-acquisition net cash flows (pre-debt)
- **Returns:** payback in years (interpolated to one decimal, e.g. 3.4 years)
- Also return cumulative CF table for audit trail

---

#### `EV_2P(EV, reserves_2P_mmboe)`
**EV per 2P boe — Primary M&A Valuation Metric**

```
EV/2P = EV ($) / (2P Reserves (MMboe) × 1,000,000)
```

- **Returns:** $/boe
- Context: GoM shallow water producing assets typically trade at $3–15/2P boe. Deep or HPHT commands premium. Late-life with heavy ARO trades at discount.
- Always also compute `EV_1P` alongside for reference

---

#### `EV_1P(EV, reserves_1P_mmboe)`
**EV per 1P boe**

```
EV/1P = EV ($) / (1P Reserves (MMboe) × 1,000,000)
```

- **Returns:** $/boe
- Primary lender reference metric (RBL sizing anchors to 1P)

---

#### `EV_production(EV, production_boepd)`
**EV per flowing barrel — Secondary Valuation Metric**

```
EV/boepd = EV ($) / production (boepd)
```

- **Returns:** $/boepd
- Context: GoM mature producing assets typically $5,000–$25,000/boepd depending on decline rate, ARO, and upside. High ARO burden suppresses this metric.

---

#### `EV_EBITDA(EV, EBITDA)`
**EV / EBITDA**

```
EV/EBITDA = EV ($) / annual EBITDA ($)
```

- **Returns:** multiple (e.g. 3.5×)
- Less common in upstream asset deals (NPV-based preferred) but used for corporate M&A comparisons

---

### 3.2 Cost Metrics

---

#### `lifting_cost(total_opex, production_boe)`
**Lifting Cost per boe — Core Efficiency Metric**

```
Lifting Cost = Total Operating Expenditure ($) / Total Production (boe)
```

- Both inputs must cover the **same period** (monthly or annual)
- `total_opex`: all cash operating costs; excludes capex, DD&A, ARO accretion
- **Returns:** $/boe
- Compute separately for: fixed components ($/month ÷ production) and variable components ($/boe)

When to flag:
- Lifting cost trending up while production declining = cost structure risk (fixed cost absorption problem)
- Lifting cost > 50% of realised price = approaching economic limit

---

#### `cash_breakeven(opex_per_boe, royalty_rate, production_tax_rate, transport_per_boe=0)`
**Cash Breakeven Price — Keep-Running Threshold**

```
Cash Breakeven = (Opex/boe + Transport/boe) / (1 − Royalty_rate − Production_tax_rate)
```

- All rates as decimals
- **Returns:** $/boe (minimum price for positive operating cash flow)
- This is a **lifting-cost breakeven** — does NOT include capex or G&A unless explicitly passed in
- Caller must specify what "breakeven" means: lifting-only, half-cycle (+ drilling cost), or full-cycle (+ exploration + return on capital)

---

#### `full_cycle_breakeven(opex_per_boe, capex_per_boe, royalty_rate, production_tax_rate, transport_per_boe=0, target_return=0.10)`
**Full-Cycle Breakeven — Investment Decision Threshold**

```
Full_Cycle_BE = (Opex/boe + Capex/boe + Transport/boe) / (1 − Royalty − Prod_Tax)
```

Where `Capex/boe = annualised capex / annual production`.

- `target_return` is NOT included in this simplified formula (it converts to a DCF problem — use NPV/IRR instead)
- **Returns:** $/boe; note this is a static metric and does not capture timing

---

#### `netback(oil_price, royalty_rate, transport_per_boe, variable_opex_per_boe, production_tax_rate=0)`
**Netback — Field-Level Economic Margin**

```
Netback = Realised_Price × (1 − Royalty_rate) − Transport/boe − Variable_Opex/boe − Production_Tax/boe
```

- **Returns:** $/boe net operating margin at field gate
- Strong netback (>$20/boe at $70/bbl oil) = resilient field; weak (<$10/boe) = sensitive to price/cost swings

---

#### `finding_dev_cost(capex, reserve_additions_mmboe)`
**Finding & Development Cost**

```
F&D Cost = Capex ($) / (Reserve Additions (MMboe) × 1,000,000)
```

- **Returns:** $/boe added
- Rule of thumb: F&D < $10/boe = competitive for shallow water GoM; $15–$25/boe for deepwater; >$30/boe = expensive

---

### 3.3 Production Metrics

---

#### `exponential_decline(q0, D_annual, t_months)`
**Production Rate at Time t — Exponential Decline**

```
q(t) = q0 × e^(−D × t/12)
```

- `q0`: initial rate (bopd or boepd)
- `D_annual`: annual nominal decline rate (decimal, e.g. 0.20 for 20%/year)
- `t_months`: time elapsed in months
- **Returns:** production rate at time t, same units as q0

When to use exponential: conventional reservoirs in decline, most GoM mature wells. Use hyperbolic only if caller provides b-factor (b > 0).

---

#### `hyperbolic_decline(q0, D_initial, b, t_months)`
**Hyperbolic Decline**

```
q(t) = q0 / (1 + b × D_initial × t/12)^(1/b)
```

- `b`: hyperbolic exponent (0 < b < 1 for most oil wells; b = 0 → exponential; b = 1 → harmonic)
- Shale wells: b often 1.2–2.0 in early life, converging to terminal exponential
- **Flag if b > 1:** signal to caller that EUR may be sensitive to b-value assumption

---

#### `decline_rate(prod_t0, prod_t1, months_elapsed)`
**Observed Decline Rate — Fitted from Actuals**

```
D_annual = −(12 / months_elapsed) × ln(prod_t1 / prod_t0)
```

- **Returns:** annual nominal decline rate as decimal
- Use this to back-calculate observed D from historical production data before applying to forecasts

---

#### `EUR(q0, D_annual, q_economic_limit, b=0)`
**Estimated Ultimate Recovery**

Exponential case (b = 0):
```
EUR = q0 / D_annual × (1 − e^(−D × t_eol/12))    where t_eol = −(12/D) × ln(q_econ/q0)
```

Simplified approximation:
```
EUR ≈ q0 / D_annual    (in annual production units)
```

- `q_economic_limit`: minimum rate at which field remains cash-positive (link to cash_breakeven output)
- **Returns:** EUR in same volumetric units as q0 (annualised)
- Convert to boe at caller's specified GOR/shrinkage

---

#### `GOR(gas_prod_mmscfd, oil_prod_bopd)`
**Gas-Oil Ratio**

```
GOR = Gas Production (Mscf/day) / Oil Production (bopd)
```

- **Returns:** Mscf/bbl (standard US unit) or scf/bbl
- Rising GOR = reservoir pressure depletion or gas cap expansion; watch for correlation with declining oil rate
- Flag if GOR > 5,000 scf/bbl: may signal approaching dew point or gas cap breakthrough

---

#### `water_cut(water_prod_bwpd, total_liquid_bpd)`
**Water Cut**

```
WC = Water Production (bwpd) / (Oil + Water) (bpd)
```

- **Returns:** decimal (e.g. 0.65 = 65% water cut)
- High and rising WC drives up lifting cost; economic limit approached when WC approaches 1.0 given fixed water disposal capacity and costs
- Flag if WC > 0.80: SWD capacity and disposal cost become critical inputs

---

#### `reserve_replacement(reserve_additions_mmboe, annual_production_mmboe)`
**Reserve Replacement Ratio**

```
RRR = Reserve Additions (MMboe) / Annual Production (MMboe)
```

- **Returns:** ratio (e.g. 0.8 = 80% replacement)
- RRR < 1.0 = reserve base declining; for NFA / mature asset context this is expected — flag as context not red flag

---

### 3.4 Fiscal Metrics — Jurisdiction-Agnostic

All fiscal rates are **caller-supplied inputs**. No rates are hardcoded. The caller (orchestrator LLM or analyst) must extract rates from the JOA, licence, or fiscal summary before invoking Agent 04.

---

#### `royalty_net(gross_revenue, royalty_rate)`
**Net Revenue After Royalty**

```
Net_Revenue = Gross_Revenue × (1 − Royalty_rate)
```

- `royalty_rate`: decimal; extracted from licence / JOA / PSC
- **Returns:** net revenue in same currency as gross_revenue

NRI (Net Revenue Interest) note: Some JOAs express this as NRI directly:
```
Net_Revenue = Gross_Revenue × NRI_pct
```
Pass `royalty_rate = 1 − NRI_pct` if working from NRI. Clarify in output which was used.

---

#### `WI_net_production(gross_production, WI_pct, NRI_pct)`
**Net Production to Working Interest Holder**

```
Net_Production = Gross_Production × WI_pct    [cost responsibility]
Net_Revenue_Production = Gross_Production × NRI_pct    [revenue entitlement]
```

- WI ≥ NRI always (royalty burden makes NRI < WI)
- **Returns both:** net production for cost purposes AND net production for revenue purposes
- Flag if caller uses only one — most valuation errors in upstream M&A come from confusing gross, WI, and NRI

---

#### `tax_barrel(taxable_income_per_boe, effective_tax_rate)`
**Tax Per Barrel**

```
Tax/boe = Taxable_Income/boe × Effective_Tax_rate
```

- `taxable_income_per_boe`: net revenue/boe minus allowable deductions (passed by caller; deductions vary by regime)
- `effective_tax_rate`: blended rate (income tax + special petroleum taxes, net of uplifts/allowances) — caller-supplied
- **Returns:** $/boe tax burden

---

#### `carry_value(carry_pct, total_capex, carrier_WI)`
**Economic Value of a Carried Interest**

```
Carry_Value = Carry_pct × Total_Capex × (1 / Carrier_WI)
```

- `carry_pct`: fraction of partner's capex being funded by the carrying party
- Caller must specify: is this a full carry (100% of partner share) or partial?
- **Returns:** total dollar value of carry obligation
- Also compute NPV of carry: treat as a stream of capex payments; discount at caller-supplied rate

---

### 3.5 Leverage & RBL Metrics

---

#### `borrowing_base(pdp_cash_flows, discount_rate, advance_rate, bank_price_deck_applied=True)`
**Indicative RBL Borrowing Base**

```
PV_PDP = NPV(pdp_cash_flows, discount_rate, convention="end")    [banks use end-of-period]
Borrowing_Base = PV_PDP × Advance_rate
```

Standard parameters (illustrative — always defer to actual term sheet):
- Discount rate: 9–10% (PV9 or PV10)
- Advance rate on PDP: 55–65%
- PDNP/PUD: lower advance rates or zero, depending on term sheet
- **Returns:** borrowing base in $; flag that actual sizing requires banker's own technical note

Rules:
- Always label price deck used: "Management deck", "Bank deck (approx.)", "Strip"
- If bank deck not supplied, note that result is indicative only
- Bank PDP cash flows only — exclude 2P/3P unless caller explicitly confirms lender credits them

---

#### `loan_life_coverage_ratio(PV_remaining_reserves, outstanding_debt)`
**LLCR — Key RBL Covenant**

```
LLCR = PV of remaining reserve cash flows / Outstanding debt balance
```

- Computed at each period; covenant typically requires LLCR ≥ 1.3–1.5× (pass threshold as input)
- **Returns:** LLCR at each period + flag where breached

---

#### `debt_service_coverage_ratio(EBITDA, annual_debt_service)`
**DSCR**

```
DSCR = EBITDA / (Interest + Principal repayment in period)
```

- **Returns:** ratio per period; flag if < 1.0 (cash shortfall) or below covenant threshold (pass as input)

---

## 4. SENSITIVITY ANALYSIS

### 4.1 Single-Variable Range Table

`run_range_sensitivity(metric_name, base_inputs, sensitivity_var, low_val, high_val, steps=5)`

Varies one input across a range; holds all others at base case.

**Output format:**
```
Sensitivity: NPV10 vs Oil Price
Base case: $70/bbl → NPV10 = $XXM

| Oil Price ($/bbl) | NPV10 ($M) | Change vs Base ($M) | Change vs Base (%) |
|---|---|---|---|
| 50 | ... | ... | ... |
| 60 | ... | ... | ... |
| 70 | BASE | — | — |
| 80 | ... | ... | ... |
| 90 | ... | ... | ... |
```

Rules:
- Always include base case row, labelled "BASE"
- Monetary outputs in $M to 1 decimal place
- Rate outputs (IRR, decline rate) to 1 decimal place as %

---

### 4.2 Tornado Chart (Multi-Variable Ranking)

`run_tornado(metric_name, base_inputs, variable_ranges)`

Runs each variable independently through its low/high range; ranks by absolute NPV impact.

`variable_ranges` input format:
```json
{
  "oil_price": {"low": 55, "high": 85, "unit": "$/bbl"},
  "discount_rate": {"low": 0.08, "high": 0.15, "unit": "decimal"},
  "opex_per_boe": {"low": 15, "high": 35, "unit": "$/boe"},
  "production_decline": {"low": 0.10, "high": 0.30, "unit": "annual decimal"},
  "ARO_cost": {"low_multiplier": 0.7, "high_multiplier": 1.5}
}
```

**Output format:**
```
Tornado: NPV10 sensitivity — base case $XXM

Variable             | Low Case | High Case | Swing ($M) | Swing (%)
---------------------|----------|-----------|------------|----------
Oil Price            | $XXM     | $XXM      | $XXM       | XX%        ← widest bar
Production/Decline   | $XXM     | $XXM      | $XXM       | XX%
Lifting Cost/Opex    | $XXM     | $XXM      | $XXM       | XX%
Discount Rate        | $XXM     | $XXM      | $XXM       | XX%
ARO Cost             | $XXM     | $XXM      | $XXM       | XX%
```

Rules:
- Sort descending by absolute swing (widest bar first)
- Include low-case and high-case labels showing which direction is adverse
- Note which variables are **correlated** (oil price and royalty revenue both move with price — caller should not run them independently if price-linked)

Standard upstream tornado variable order (typical ranking for mature GoM producers):
1. Oil price / realised price
2. Production volume / decline rate
3. Lifting cost / opex
4. Discount rate
5. Capex timing / cost
6. ARO cost
7. Royalty / fiscal terms

---

## 5. INPUT/OUTPUT CONVENTIONS

### 5.1 Unit Validation Rules

Agent 04 must validate units before computing. Reject with descriptive error if mismatch detected.

| Metric Group | Acceptable Volume Units | Acceptable Time Units |
|---|---|---|
| Production rates | bopd, boepd, bpd, mmscfd | per day |
| Cumulative volumes | bbl, boe, Mbbl, Mboe, MMbbl, MMboe, bcf, tcf | — |
| Cash flows | $, $K, $M, $MM | per month or per year |
| Costs | $/bbl, $/boe, $/Mbbl, $/Mscf | — |
| Reserves | Mboe, MMboe, bcf | — |

**Auto-conversion rules (silent, logged):**
- Mboe → boe: × 1,000
- MMboe → boe: × 1,000,000
- $M → $: × 1,000,000
- bbl (oil) → boe: 1:1
- Mscf → boe: ÷ 6 (standard gas conversion; flag if caller has asset-specific BTU factor)
- Monthly CF array → annual: sum 12 months (do NOT annualise by multiplying month 1 × 12)

**Never auto-convert without logging.** Every unit conversion must appear in `workings` field of output.

### 5.2 Output Format Standard (Every Call)

```python
{
  "metric": "EV_2P",
  "result": 13.33,
  "unit": "$/boe",
  "inputs_used": {
    "EV": {"value": 32000000, "unit": "$"},
    "reserves_2P": {"value": 2.4, "unit": "MMboe"}
  },
  "formula": "EV / (2P MMboe × 1,000,000) = 32,000,000 / 2,400,000 = $13.33/boe",
  "workings": "Enterprise Value of $32.0M divided by 2P reserves of 2.4 MMboe at 1,000,000 boe/MMboe conversion.",
  "caveats": ["2P reserves sourced from CPR — confirm effective date", "EV excludes ARO — confirm if Day-1 ARO liabilities are netted"],
  "confidence": "HIGH",
  "unit_conversions_applied": []
}
```

Fields:
- `metric`: function name called
- `result`: scalar or array depending on metric
- `unit`: always explicit
- `inputs_used`: all inputs with values and units
- `formula`: LaTeX-style or plain text equation with numbers substituted
- `workings`: plain English explanation of calculation
- `caveats`: list of assumptions or data-quality notes; empty list `[]` if none
- `confidence`: HIGH (all inputs from primary docs) | MEDIUM (some inputs estimated) | LOW (proxy inputs used)
- `unit_conversions_applied`: list any auto-conversions performed

### 5.3 Precision Rules

| Output Type | Precision |
|---|---|
| NPV / PV values | Round to nearest $0.1M; display as "$XXX.XM" |
| EV multiples ($/boe, $/boepd) | 2 decimal places |
| IRR, decline rates, WC, GOR | 1 decimal place as % or stated unit |
| Royalty / tax rates | 1 decimal place as % |
| Lifting cost / netback | 2 decimal places ($/boe) |
| Payback period | 1 decimal place (years) |

---

## 6. FINANCIAL QUALITY FLAGS

Agent 04 must append quality flags where inputs or results trigger known red-flag patterns. These are not errors — they are analyst alerts.

| Flag | Trigger | Severity |
|---|---|---|
| `NEGATIVE_NETBACK` | Netback ≤ 0 at current price inputs | 🔴 Critical |
| `ECONOMIC_LIMIT_NEAR` | Lifting cost > 70% of realised price | 🔴 Critical |
| `HIGH_WATER_CUT` | WC > 80% | 🟡 Moderate |
| `RISING_GOR` | GOR > 3,000 scf/bbl and trending up | 🟡 Moderate |
| `IRR_MULTIPLE_SOLUTIONS` | CF sign changes > 1 | 🟡 Moderate — flag multiple IRR risk |
| `BORROWING_BASE_AGGRESSIVE` | BB > 65% of PDP PV10 | 🟡 Moderate |
| `ARO_EXCEEDS_PDP_VALUE` | ARO NPV > PDP NPV | 🔴 Critical |
| `CARRY_EXCEEDS_CAPEX` | Carry value > total project capex | 🟡 Moderate — check carry definition |
| `HIGH_B_FACTOR` | b > 1.2 in hyperbolic decline | 🟡 Moderate — EUR sensitive to b |
| `LLCR_BREACH` | LLCR < threshold in any period | 🔴 Critical — covenant breach |
| `PAYBACK_EXCEEDS_RESERVE_LIFE` | Payback > reserve life (1P) | 🔴 Critical |
| `NRI_GT_WI` | NRI > WI passed as inputs | 🔴 Critical — data error |
| `WI_NRI_MISMATCH` | (1 − NRI/WI) ≠ royalty_rate ± 2% | 🟡 Moderate — check inputs |

---

## 7. INTER-AGENT DEPENDENCIES

| Calling Agent | What It Needs from Agent 04 | Key Inputs Agent 04 Requires |
|---|---|---|
| **Agent 06** (Q&A) | Any metric on demand from analyst question | Structured inputs extracted from VDR by analyst or Agent 02/03 |
| **Agent 07** (Well Cards) | `decline_rate`, `GOR`, `water_cut`, `lifting_cost`, `netback` per well | Agent 02 production DB query results |
| **Agent 10** (ARO) | `NPV` of ARO cash flows at P50/P70/P90 | ARO cost schedule from Agent 10's extraction |
| **Agent 12** (Liability Builder) | `NPV` of debt service, hedge MTM | Cash flow schedules from debt facility docs |
| **Agent 15** (Sensitivity) | `run_range_sensitivity`, `run_tornado` on NPV/IRR | Base case inputs from seller model or Agent 03 validated assumptions |
| **Agent 19** (IC Scorecard) | `EV_2P`, `EV_1P`, `EV_production`, `lifting_cost`, `cash_breakeven`, `payback_period` | EV, reserves, production, costs from Agent 02 + Agent 03 |

**Data flow rule:** Agent 04 never reads VDR documents. All inputs must be pre-extracted and structured by the calling agent. If inputs are missing, Agent 04 returns a descriptive `input_error` and halts.

---

## 8. COMMON CALCULATION ERRORS IN UPSTREAM FINANCE

These are the most frequent mistakes Agent 04 must guard against:

| Error | Prevention |
|---|---|
| Confusing gross, WI, and NRI production | Always confirm which basis before computing revenue or cost |
| Using end-of-period discounting for asset NPV | Default to mid-period; SEC PV-10 is the exception (end-of-period) |
| Annualising monthly cash flows by × 12 on Month 1 | Always sum actual monthly CFs; never extrapolate single month |
| Including capex in lifting cost | Lifting cost = opex only; flag if caller conflates them |
| Applying royalty to net (post-opex) revenue | Royalty always applies to gross revenue before any deductions |
| Double-counting ARO in NFA cash flows | Confirm ARO not already netted in cash flow array before adding separately |
| Treating b > 0 hyperbolic as exponential | Check b-factor; if > 0, use hyperbolic formula |
| Confusing nominal and real prices | Confirm with caller whether cash flows are nominal (escalated) or real (flat); discount rate must match |
| EV/2P without ARO-netting | Always caveat EV/2P: "EV should be adjusted for Day-1 ARO" if ARO not reflected in EV |
| IRR on unlevered vs levered cash flows | Confirm: are cash flows pre-debt (asset IRR) or post-debt (equity IRR)? Label explicitly |

---

## 9. QUICK REFERENCE: KEY UPSTREAM BENCHMARKS

These are **general orientation ranges only** — not hardcoded assumptions. Agent 04 uses caller-supplied inputs. These help identify when inputs are implausible.

| Metric | Plausible Range | Flag if Outside |
|---|---|---|
| GoM shallow water lifting cost | $8–$35/boe | < $5 or > $50 |
| GoM deepwater lifting cost | $15–$50/boe | < $10 or > $70 |
| UKCS lifting cost | $15–$45/boe | < $10 or > $60 |
| Cash breakeven (mature field) | $20–$50/bbl | < $10 or > $70 |
| EV/2P (GoM mature producing) | $3–$15/boe | < $1 or > $25 |
| EV/boepd (GoM mature producing) | $5,000–$25,000 | < $2,000 or > $40,000 |
| GoM well decline rate (conventional) | 10–30%/yr | < 5% or > 60% |
| GoM GOR (oil well) | 500–5,000 scf/bbl | > 10,000 (flag gas cap issue) |
| RBL advance rate on PDP PV10 | 55–65% | > 70% (aggressive) |
| LLCR covenant (typical) | ≥ 1.3–1.5× | < 1.0 = breach |

---

## 10. ERROR HANDLING

Agent 04 returns a structured error — never a silent wrong answer.

```python
{
  "status": "input_error",
  "metric_attempted": "NPV",
  "error_code": "UNIT_MISMATCH",
  "message": "Cash flows supplied in $/boe but must be in $ per period for NPV. Please convert using production volume before passing to finance_calc.",
  "suggested_fix": "Multiply $/boe by production (boe per period) to get CF per period."
}
```

Error codes:
- `UNIT_MISMATCH`: wrong units for metric
- `MISSING_INPUT`: required argument not supplied
- `IMPLAUSIBLE_INPUT`: value outside benchmark range (warning, not hard stop — proceeds with flag)
- `SIGN_ERROR`: cash flow array has unexpected sign pattern (e.g. all positive — no investment)
- `MULTIPLE_IRR`: multiple sign changes, IRR ambiguous
- `DIVISION_BY_ZERO`: production, reserves, or denominator is zero

---

*End of Document — v1.0 | 27 February 2026 | Aigis Analytics — Confidential*  
*Agent 04 domain primer. No VDR classification content. All fiscal rates caller-supplied.*
