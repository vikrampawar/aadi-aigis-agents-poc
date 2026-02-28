# Aigis Analytics — Agent 04: Upstream Finance Knowledge Bank
**Version:** 1.0 | **Date:** 27 February 2026 | **Status:** DRAFT FOR REVIEW  
**Author:** Aaditya Chintalapati | **Purpose:** Canonical formula + definition library for Agent 04 Finance Calculator

---

## ABOUT THIS DOCUMENT

This knowledge bank is the **formula and terminology foundation** for Agent 04 — the Upstream Finance Calculator. Every entry follows a consistent structure:

```
TERM / FORMULA NAME
Definition:     What it is and why it matters
Formula:        Mathematical expression
Inputs:         Each variable, its unit, and where to find it in a VDR
Output:         Result unit and interpretation
Red Flag Range: Values that trigger analyst review
Aliases:        Alternative names found in CPRs, IMs, and deal documents
Notes:          Caveats, common errors, jurisdiction differences
```

The LLM layer uses this document to:
1. **Match** natural-language analyst queries to the correct formula (semantic similarity)
2. **Identify** the required input variables and search the VDR for them
3. **Calculate** with full workings and unit-checked results
4. **Flag** outputs that fall outside expected ranges

---

## SECTION 1 — UNIT CONVERSION RATIOS

> Upstream data arrives in inconsistent units. All conversions below are exact or industry-standard. The calculator must auto-detect and convert before any formula is applied.

---

### 1.1 Volume Conversions

| Convert From | Convert To | Multiply By | Notes |
|---|---|---|---|
| Barrels (bbl) | US Gallons | 42 | Exact |
| Barrels (bbl) | Litres | 158.987 | Exact |
| Barrels (bbl) | Cubic Feet | 5.61458 | Exact |
| Barrels (bbl) | Cubic Metres (m³) | 0.158987 | Exact |
| Thousand Barrels (Mbbl) | Barrels | 1,000 | — |
| Million Barrels (MMbbl) | Barrels | 1,000,000 | — |
| Barrel of Oil Equivalent (boe) | BOE | 1.0 | Base unit |
| Thousand Cubic Feet (Mcf) | BOE | ÷ 6 | SEC standard (6 Mcf = 1 boe); WoodMac uses 5.8 |
| Million Cubic Feet (MMcf) | BOE | ÷ 6 × 1,000 | |
| Billion Cubic Feet (Bcf) | MMboe | ÷ 6 | |
| Trillion Cubic Feet (Tcf) | Bnboe | ÷ 6 | |
| Cubic Metres of gas (m³) | Mcf | × 0.035315 | |
| MMSCFD | MMcf/day | 1:1 (if at standard conditions) | Standard: 14.696 psi, 60°F |
| NGL Barrel | BOE | 1.0 | Treated as 1 boe unless BTU-adjusted |

**Key Notes:**
- The SEC uses **6 Mcf = 1 boe** (energy equivalence). Some operators or CPRs use 5.615 or 5.8. Always note which conversion factor was used.
- GoM gas is predominantly dry gas; conversion sensitivity is material for gas-dominant assets.
- NGLs may be reported in bbl or in gallons (US); check units on every NGL line in LOS statements.

---

### 1.2 Production Rate Conversions

| Convert From | Convert To | Multiply By | Notes |
|---|---|---|---|
| BOPD | Mbbl/month | × 30.44 ÷ 1,000 | Use 30.44 as average days/month |
| BOPD | Mbbl/year | × 365.25 ÷ 1,000 | |
| Mbbl/month | BOPD | × 1,000 ÷ 30.44 | |
| MMSCFD | MMcf/month | × 30.44 | |
| MMSCFD | Bcf/year | × 0.36525 | |
| BOEPD | BOPD + BOEPD-gas | Gas in Mcf/day ÷ 6 + Oil in BOPD | |

---

### 1.3 Energy Conversions

| Convert From | Convert To | Multiply By | Notes |
|---|---|---|---|
| 1 bbl crude oil | BTU | 5,800,000 | Approximate; varies by API gravity |
| 1 Mcf natural gas | BTU | 1,020,000 | Dry gas at standard conditions |
| 1 MMBtu | Mcf | ÷ 1.02 | Approximate |
| 1 boe | MMBtu | 5.8 | WoodMac/energy-equivalent boe |
| 1 tonne crude oil | bbl | 7.33 | For light crude (API ~34); varies with gravity |
| 1 tonne LNG | boe | ~7.5 | Approximate |

---

### 1.4 Currency & Financial Unit Conversions

| From | To | Factor |
|---|---|---|
| USD | kUSD (thousands) | ÷ 1,000 |
| kUSD | MUSD (millions) | ÷ 1,000 |
| MUSD | BUSD (billions) | ÷ 1,000 |
| $/boe | $/bbl | 1:1 for oil-dominant assets |
| $/Mcf | $/boe | × 6 (SEC) or × 5.8 (BTU) |
| $/MMBtu | $/Mcf | × 1.02 |

---

## SECTION 2 — PRODUCTION & RESERVOIR METRICS

---

### 2.1 Net Production to Working Interest Owner

**Definition:** The share of gross field production that flows economically to the WI holder, after royalties and other dedications.

**Formula:**
```
Net Oil Production (bopd) = Gross Production (bopd) × NRI%
```

**Inputs:**
- `Gross Production`: Field or well gross rate (bopd) — from Operator Monthly Report, CPR Production Profile, LOS
- `NRI%` (Net Revenue Interest): Decimal or percentage — from JOA, licence, CPR Fiscal Section

**Output:** bopd (or Mbbl/month, Mbbl/year depending on input period)

**Aliases:** NRI production, net production, working interest production

**Notes:**
- NRI < WI when overriding royalties (ORRIs) are present.
- GoM federal leases: royalty typically 12.5%–18.75% of gross, so NRI = WI × (1 – royalty rate) in simple cases.
- Always confirm NRI from JOA/licence — CPR may use outdated or approximate figures.
- WI% ≠ NRI% unless royalty-free interest.

---

### 2.2 Working Interest vs Net Revenue Interest

**Definition:**
- **WI (Working Interest):** Your share of costs (capex, opex). You pay WI% of all costs.
- **NRI (Net Revenue Interest):** Your share of revenue. NRI = WI × (1 – total royalty burden).
- **ORRI (Overriding Royalty Interest):** Non-cost-bearing royalty carved out of WI; reduces NRI further.

**Formula:**
```
NRI = WI × (1 − Royalty Rate − ORRI Rate)
```

**Example (Project Corsair context):**
```
WI = 20%, Federal Royalty = 18.75%, ORRI = 0%
NRI = 20% × (1 − 0.1875) = 20% × 0.8125 = 16.25%
```

---

### 2.3 Exponential Decline Rate

**Definition:** Standard decline curve model for mature producing fields. Assumes decline rate is proportional to production rate (constant % per unit time).

**Formula:**
```
q(t) = q₀ × e^(−D × t)

Where:
q(t)  = production rate at time t (bopd)
q₀    = initial production rate (bopd)
D     = nominal decline rate (decimal per year, or per month)
t     = time elapsed (years or months, consistent with D)
e     = Euler's number (2.71828...)
```

**Inputs:**
- `q₀`: From CPR production profile or LOS most recent actuals
- `D`: From CPR decline curve analysis or back-calculated from actuals
- `t`: Forecast period in years

**Output:** bopd at time t

**Aliases:** Arps exponential decline, exponential depletion

**Notes:**
- More conservative than hyperbolic decline; appropriate for many mature GoM fields.
- Hyperbolic decline (`q(t) = q₀ / (1 + b×D₀×t)^(1/b)`) used for wells with changing decline rate (unconventionals, early-life wells). Require additional parameter `b` (hyperbolic exponent).
- Harmonic decline = special case of hyperbolic where b = 1.
- Always confirm CPR's assumed decline model (exponential vs hyperbolic vs harmonic).

---

### 2.4 Implied Decline Rate (Back-Calculation)

**Definition:** Calculate the implied annual decline rate from two known production data points.

**Formula:**
```
D_annual = −ln(q₁/q₀) / Δt

Where:
q₀ = production at time 0 (bopd)
q₁ = production at time 1 (bopd)
Δt = time difference in years
```

**Example:**
```
G6 at SM58: q₀ = 650 bopd (Jul-25), q₁ = 575 bopd (Dec-25), Δt = 5/12 years
D_annual = −ln(575/650) / (5/12) = −ln(0.8846) / 0.4167 = 0.1228 / 0.4167 = 29.5% p.a.
```

---

### 2.5 Estimated Ultimate Recovery (EUR)

**Definition:** Total expected recovery from a well or field over its producing life, from first production to economic limit.

**Formula (Exponential Decline):**
```
EUR = q₀ / D

Where:
EUR = estimated ultimate recovery from *current date* (Mbbl or boe)
q₀  = current rate (Mbbl/year or boe/year)
D   = annual nominal decline rate (decimal)
```

**Full EUR from first production:**
```
EUR_total = Cumulative Production to date + Remaining EUR
```

**Notes:**
- Economic limit: the rate at which revenue covers only direct variable opex — typically 5–15 bopd for GoM shallow water wells.
- EUR sensitivity to economic limit can be significant for low-rate wells.

---

### 2.6 Gas-Oil Ratio (GOR)

**Definition:** The ratio of produced gas to produced oil at field/separator conditions.

**Formula:**
```
GOR (scf/bbl) = Gas Production (scf/day) / Oil Production (bbl/day)
              = Gas Production (Mcf/day) × 1,000 / Oil Production (bopd)
```

**Interpretation:**
- < 500 scf/bbl: Oil well (solution gas drive or water drive)
- 500–3,000 scf/bbl: Associated gas; normal for many GoM fields
- > 3,000 scf/bbl: Gas condensate; approaching dew point
- Rising GOR over time: Gas cap encroachment or reservoir pressure depletion — watch carefully

**Aliases:** Producing GOR, field GOR, separator GOR

---

### 2.7 Water Cut (WC)

**Definition:** The fraction of produced fluid that is water.

**Formula:**
```
WC (%) = Water Production (bwpd) / Total Liquid Production (bwpd + bopd) × 100
```

**Interpretation:**
- < 20%: Early life; low impact on economics
- 20–60%: Mid-life; opex begins rising due to water handling
- > 60%: Mature/late life; significant impact on lifting cost; watch for SWD capacity constraints
- Rising WC + rising GOR simultaneously: Strong indicator of reservoir pressure decline or water breakthrough

**Aliases:** BSW (Basic Sediment & Water), water fraction

---

### 2.8 Uptime / Runtime

**Definition:** The fraction of calendar time that a well or facility was actually producing.

**Formula:**
```
Uptime (%) = Actual Production Hours / Total Calendar Hours × 100
```

**Interpretation:**
- > 95%: Excellent
- 85–95%: Normal for mature infrastructure
- < 85%: Investigate — planned vs unplanned downtime split; compressor/topside issues flag

**Notes:**
- CPRs forecast uptime assumptions (typically 92–95% for GoM). Compare to actual from operator monthlies.
- Downtime-adjusted production: `Production_actual = Production_design × Uptime%`

---

### 2.9 Reserve Replacement Ratio (RRR)

**Definition:** Measures how well a company or field replaces produced reserves with new reserve additions.

**Formula:**
```
RRR = Reserve Additions (mmboe) / Production (mmboe) × 100%
```

**Interpretation:**
- > 100%: Growing reserve base
- = 100%: Maintenance (no growth, no decline)
- < 100%: Depleting reserve base — typical for mature assets in run-off

---

### 2.10 Recovery Factor

**Definition:** The fraction of the Original Oil (or Gas) In Place that is ultimately recovered.

**Formula:**
```
Recovery Factor (%) = EUR (mmboe) / OOIP or OGIP (mmboe) × 100%
```

**Typical Ranges:**
- Primary recovery (depletion drive): 10–20%
- Secondary recovery (water/gas injection): 25–45%
- Tertiary recovery (EOR): 35–60%
- GoM shallow water mature fields: typically 20–40% primary/secondary combined

**Note:** OOIP/OGIP sourced from CPR volumetric analysis — high uncertainty; cross-check with stochastic range if available.

---

## SECTION 3 — COST METRICS

---

### 3.1 Lifting Cost (Operating Cost per BOE)

**Definition:** The total operating cost to produce one barrel of oil equivalent. The most commonly referenced field-level efficiency metric.

**Formula:**
```
Lifting Cost ($/boe) = Total Field Opex ($) / Net Production (boe)
```

**Inputs:**
- `Total Field Opex`: From LOS statements, Management Accounts — includes fixed opex, variable opex, workovers (sometimes separated), G&A allocation
- `Net Production`: WI-net production over the same period (boe)

**Typical Ranges:**
- GoM shallow water: $12–25/boe
- GoM deepwater: $8–15/boe (high fixed cost, high volume)
- UKCS: $15–35/boe
- Onshore US: $5–20/boe (highly variable)

**Red Flag:** > $30/boe for mature GoM shallow water; review cost structure for G&A inflation or workover frequency

**Aliases:** Operating cost per barrel, OPEX/boe, cash cost, unit opex

**Notes:**
- Workovers may be capitalised (adds to capex) or expensed (adds to opex) depending on company policy — check accounting notes.
- G&A allocation: corporate overhead may or may not be included; clarify with operator.
- Per-well vs field level: get both where possible.

---

### 3.2 Cash Operating Margin (Netback)

**Definition:** Revenue remaining per barrel after deducting all variable cash costs at field level. Represents the cash flow contribution before corporate overheads and taxes.

**Formula:**
```
Netback ($/bbl) = Oil Price ($/bbl) 
                  − Royalties ($/bbl) 
                  − Transportation & Tariff ($/bbl) 
                  − Variable Opex ($/bbl)
```

**Example (Project Corsair, GoM):**
```
Oil Price:          $75.00/bbl (WTI)
Less: Royalty:      −$9.37/bbl (12.5% federal + state)
Less: Transport:    −$2.00/bbl (pipeline tariff/offshore loading)
Less: Variable Opex:−$12.00/bbl
                    ──────────
Netback:            $51.63/bbl
```

**Aliases:** Field netback, margin per barrel, operating margin per boe

---

### 3.3 Cash Break-Even Price

**Definition:** The minimum oil price at which the asset generates zero operating cash flow (revenue = cash opex + royalties + transport). Below this price, every barrel produced destroys cash.

**Formula:**
```
Cash Break-Even ($/bbl) = (Variable Opex + Fixed Opex/Production + Royalties + Transport)
                        = Lifting Cost + Royalty ($/bbl) + Transport ($/bbl)
```

**Practical Expansion:**
```
Cash Break-Even = (Fixed Opex $ / Net Production boe) + Variable Opex ($/boe) + Royalty ($/boe) + Transport ($/boe)
```

**Interpretation:**
- Break-even < $30/bbl: Highly resilient; survives even severe downturns
- Break-even $30–50/bbl: Moderate resilience; stress-test at $40 WTI
- Break-even > $50/bbl: Vulnerable; assess downside scenario carefully

**Red Flag:** Asset cash break-even within $15/bbl of current forward strip price

---

### 3.4 Full-Cycle Break-Even Price

**Definition:** The oil price required to generate a zero NPV over the full investment cycle, including capex. More conservative than cash break-even.

**Formula:**
```
Full-Cycle Break-Even = Cash Break-Even + Annualised Capex ($ / net production boe)
                      = Cash Break-Even + (Development Capex / EUR × discount factor adjustment)
```

**Aliases:** Economic break-even, full-cost break-even, total-cost break-even

**Notes:**
- For M&A, substitute "Acquisition Price" for "Development Capex" to compute acquisition break-even.
- Acquisition Break-Even = (Purchase Price + Assumed Liabilities) / EUR net boe, expressed as a required oil price.

---

### 3.5 Finding and Development Cost (F&D)

**Definition:** The capital cost incurred to add one unit of proved reserves through exploration, development drilling, and facility investment.

**Formula:**
```
F&D Cost ($/boe) = Total Capital Invested ($) / Reserve Additions (boe)
```

**Variants:**
- **Drill-Bit F&D:** Capex from drilling only (excludes acquisitions)
- **All-Sources F&D:** All capex + acquisition costs / all reserve additions
- **3-Year Average F&D:** Smooth over 3 years to remove lumpy capex effects

**Typical Ranges:**
- GoM shelf: $8–20/boe
- GoM deepwater: $12–30/boe
- UKCS: $10–25/boe

**Red Flag:** F&D cost > $/boe netback — capital destruction signal

---

### 3.6 Recycle Ratio

**Definition:** Measures the efficiency of capital: how much netback is generated per dollar of F&D cost. Ratio > 1.0 means value creation; < 1.0 means capital destruction.

**Formula:**
```
Recycle Ratio = Netback ($/boe) / F&D Cost ($/boe)
```

**Interpretation:**
- > 3.0: Exceptional capital efficiency
- 2.0–3.0: Strong
- 1.0–2.0: Acceptable
- < 1.0: Capital destruction — investigate before sanctioning further drilling

---

### 3.7 ARO (Asset Retirement Obligation) per BOE

**Definition:** Decommissioning liability allocated per unit of production — useful for comparing assets' abandonment burdens.

**Formula:**
```
ARO/boe = Net ARO Estimate (P50 or P70) ($) / Remaining 2P Reserves (boe)
```

**Notes:**
- Use P70 for conservative analysis; P50 for base case.
- GoM ARO is typically regulatory-reviewed; MMS/BSEE filings are the best source.
- ARO should be risk-adjusted: stochastic ARO estimate × probability of full abandonment during holding period.
- Deduct from EV as a liability; do not ignore even if "on books" — frequently understated.

---

## SECTION 4 — VALUATION METRICS & MULTIPLES

---

### 4.1 Net Present Value (NPV)

**Definition:** The discounted present value of future asset net cash flows. Represents the **intrinsic value of the asset** at the specified discount rate.

> **Aigis Convention:** NPV and PV-10 are computed at the **asset level only** — acquisition cost is EXCLUDED from the NPV formula. The acquisition cost is then compared separately against the NPV to determine whether the bid price is commercially attractive. This follows CPR/SEC practice and avoids conflating asset value with investment return.

**Formula:**
```
Asset NPV = Σ [CF_t / (1 + r)^t]

Where:
CF_t  = net cash flow in period t (after opex, royalties, taxes, dev capex, ARO)
r     = discount rate (decimal, e.g., 0.10 for 10%)
t     = time period (years from transaction close)

Acquisition cost is NOT deducted from Asset NPV.
```

**Deal Attractiveness Assessment (separate from NPV):**
```
Value Creation = Asset NPV − Acquisition Cost
  > 0: Paying below intrinsic value — deal creates value at this price/rate assumption
  = 0: Paying exactly at intrinsic value (full price)
  < 0: Paying above intrinsic value — requires conviction in upside (2P/3P, price recovery)

Full-Cycle Breakeven = Oil price at which Asset NPV = Acquisition Cost
  (i.e., the oil price floor required for the investment to break even at the hurdle rate)
```

**IRR vs NPV convention:**
- **Asset NPV** = intrinsic value of cash flows (no acquisition cost)
- **IRR** = investment return = discount rate where (Asset NPV − Acquisition Cost) = 0
- **Payback** = years for cumulative asset CFs to recover acquisition cost

**Mid-Period Convention (Industry Standard):**
```
NPV_mid = Σ [CF_t / (1 + r)^(t−0.5)]
```
> Production CPRs use mid-period convention by default. Agent 04 uses end-of-year convention (conservative).

**Common Discount Rates:**
| Context | Typical Rate |
|---|---|
| SEC PV-10 / SPE-PRMS | 10% |
| Corporate hurdle (E&P major) | 10–15% |
| Independent E&P / private | 12–15% |
| Distressed/high-risk | 15–25% |
| Buyer-side M&A (WACC) | 8–12% |

**Aliases:** PV, discounted cash flow (DCF), present value, PV-10 (at 10%)

---

### 4.2 PV-10

**Definition:** Asset NPV discounted at exactly 10% per annum. The SEC's standard measure of proved reserves value. Represents **intrinsic asset value** — the present worth of the asset's future cash flows at a 10% hurdle rate. Acquisition cost is excluded.

**Formula:**
```
PV-10 = Σ [Net CF_t / (1.10)^t]

Net CF_t = Net Revenue − LOE − G&A − Workovers − Transport − Development CAPEX − Income Tax
(ARO included in final year)

Acquisition cost is NOT deducted. Compare PV-10 to bid price to assess deal attractiveness.
```

**Key Variants Used in Upstream M&A:**
| Term | Description |
|---|---|
| PDP PV-10 | PV-10 of Proved Developed Producing reserves only — most conservative; basis for RBL |
| PDP + PDNP PV-10 | Includes Proved Developed Non-Producing (shut-ins, behind-pipe) |
| 1P PV-10 | Total proved reserves (PDP + PDNP + PUDs) |
| 2P PV-10 | Proved + Probable reserves — the main M&A valuation anchor |
| 3P PV-10 | Proved + Probable + Possible — upper bound; rarely used for deal price |

**Project Corsair Reference Values (25 Feb 2026, per CPR):**
- PDP PV-10: $51.4M
- 1P PV-10: $103.6M
- 2P PV-10: $231.1M
- Statler bid recommendation: $30–34M → Value Creation vs PDP PV-10: +$17–21M

---

### 4.3 Internal Rate of Return (IRR)

**Definition:** The discount rate at which NPV = 0. Represents the effective annualised return on invested capital.

**Formula:**
```
0 = Σ [CF_t / (1 + IRR)^t] − Initial Investment
(Solved iteratively — no closed-form solution)
```

**Interpretation:**
| IRR | Verdict (E&P context) |
|---|---|
| > 25% | Excellent; likely a quick payback / low-risk PDP deal |
| 15–25% | Good; meets most independent E&P hurdles |
| 10–15% | Marginal; acceptable with strategic rationale |
| < 10% | Value-destructive at typical WACC |

**Notes:**
- IRR is not reliable for projects with multiple sign changes in cash flows (e.g., large ARO at end of life). Use NPV instead, or modified IRR (MIRR).
- Always quote IRR alongside the investment period and any assumptions on oil price deck.
- Unleveraged (unlevered) vs levered IRR: specify which is being used.

---

### 4.4 Payback Period

**Definition:** The time from initial investment to full recovery of capital from net operating cash flows.

**Formula (Simple):**
```
Payback Period (years) = Initial Investment ($) / Annual Net Cash Flow ($/year)
```

**Formula (Discounted Payback — more rigorous):**
```
Find t* where: Σ [CF_t / (1+r)^t] = Initial Investment
```

**Interpretation:**
- < 3 years: Excellent for M&A; low oil-price risk exposure
- 3–5 years: Good; typical for GoM producing asset deals
- > 5 years: Long; increases price-risk exposure; requires strong long-dated price conviction

---

### 4.5 EV/EBITDA Multiple

**Definition:** The most commonly used relative valuation multiple. Compares Enterprise Value to operating cash earnings before non-cash and financing items.

**Formula:**
```
EV/EBITDA = Enterprise Value ($) / EBITDA ($/year)

EBITDA = Revenue − Operating Expenses (excl. D&D&A and interest)
       = EBIT + Depreciation, Depletion & Amortisation
```

**Typical Transaction Multiples (Upstream E&P, 2022–2025):**
| Asset Type | EV/EBITDA |
|---|---|
| Mature GoM producing (PDP-heavy) | 3–5× |
| GoM with development upside | 4–7× |
| UKCS producing | 3–6× |
| High-growth onshore US | 5–10× |

**Notes:**
- EBITDAX = EBITDA + Exploration costs (write-offs). Used for exploration-weighted companies.
- Normalise EBITDA: use forward 12-month (NTM) EBITDA, not trailing, for acquisitions of growing assets.
- Cross-check: EBITDA multiple should be consistent with PV-10/production multiple and DCF.

---

### 4.6 EV / 2P Reserves Multiple ($/boe)

**Definition:** Enterprise Value divided by total 2P (Proved + Probable) reserves. The primary metric for comparing deal values on a reserves basis.

**Formula:**
```
EV/2P ($/boe) = Enterprise Value ($) / 2P Reserves (boe)

Enterprise Value = Purchase Price + Assumed Debt + ARO (net present value) − Cash Acquired
```

**Typical Ranges:**
| Asset Type | EV/2P ($/boe) |
|---|---|
| Mature GoM shallow water | $8–18/boe |
| GoM deepwater producing | $12–25/boe |
| UKCS producing | $8–16/boe |
| Onshore US tight oil (PDP) | $4–12/boe |

**Red Flag:** EV/2P > 2P PV-10/boe suggests overpayment vs intrinsic value.

**Aliases:** Price per 2P boe, acquisition cost per boe, $/2P boe

---

### 4.7 EV / 1P Reserves Multiple ($/boe)

**Definition:** Same as EV/2P but using only Proved (1P) reserves. More conservative; used as floor value reference.

**Formula:**
```
EV/1P ($/boe) = Enterprise Value ($) / 1P Reserves (boe)
```

**Notes:**
- PDP PV-10 / production price ÷ PDP reserves gives the most conservative "worst case" acquisition $/boe.
- A deal where EV/1P > 1P PV-10/boe implies buyer is paying more than discounted value of proved reserves — requires strong 2P/3P conviction.

---

### 4.8 EV / Flowing Barrel ($/boepd)

**Definition:** Enterprise Value divided by current daily production. The most common quick-look deal metric — particularly useful for mature PDP acquisitions.

**Formula:**
```
EV/Flowing Barrel ($/boepd) = Enterprise Value ($) / Net Production (boepd)
```

**Typical Ranges:**
| Asset Type | EV/boepd |
|---|---|
| Mature GoM shallow water | $20,000–50,000/boepd |
| GoM deepwater | $30,000–80,000/boepd |
| UKCS mature | $25,000–60,000/boepd |
| Onshore US (PDP) | $10,000–30,000/boepd |

**Notes:**
- Easy sanity check: project days to recover investment at current production × current netback.
- Overstates value for assets with steep decline; undercounts value for assets with development upside.
- Always pair with payback period and decline rate when presenting this metric.

**Aliases:** Price per flowing barrel, acquisition cost per boepd, $/flowing boe

---

### 4.9 Price / Cash Flow Multiple (P/CF)

**Definition:** Acquisition price as a multiple of annual operating cash flow from operations. Used for quickly testing deal economics.

**Formula:**
```
P/CF = Enterprise Value ($) / Annual Operating Cash Flow ($/year)

Annual Operating Cash Flow = Net Revenue − Opex − Production Taxes (pre-income tax)
                           = Production (boe/year) × Netback ($/boe)
```

**Notes:**
- Equivalent to simple payback period (assuming constant cash flows).
- Use LTM (Last Twelve Months) cash flow for producing assets; use forecast CF for development assets.

---

### 4.10 NAV (Net Asset Value)

**Definition:** The intrinsic per-share or total value of an E&P company or asset based on the risk-adjusted present value of all reserves and resources.

**Formula:**
```
NAV = PV of 2P Reserves (post-tax, risked)
    + PV of 2C Resources (post-tax, risked, with exploration/development success probability)
    + PV of Prospective Resources (post-tax, risked)
    − Net Debt (Debt − Cash)
    − NPV of ARO
    − NPV of G&A (corporate overhead)
```

**Key Notes:**
- NAV is the basis for M&A premium analysis: `Premium = (Bid Price − NAV) / NAV × 100%`
- CPR 2P PV-10 is a pre-tax NAV proxy; apply corporate tax rate to convert to post-tax for a closer NAV estimate.
- Resources beyond 1P (2C, Prospective) are typically risked using geological success probability from CPR.

---

## SECTION 5 — FISCAL & ROYALTY TERMS

---

### 5.1 Royalty (Override)

**Definition:** A cost-free share of gross production paid to the mineral rights owner (typically government, surface owner, or previous owner). Royalty owner bears no costs.

**Formula:**
```
Royalty Revenue ($) = Gross Revenue ($) × Royalty Rate (%)
Net Revenue after Royalty = Gross Revenue × (1 − Royalty Rate)
Royalty ($/bbl) = Oil Price ($/bbl) × Royalty Rate (%)
```

**GoM Federal Royalty Rates (Standard):**
- Shallow water (< 200m): 12.5%–16.67%
- Deepwater (≥ 200m, post-2017): 18.75%
- Historical deepwater royalty relief: some fields have royalty-free periods — check licence terms carefully.

**ORRI (Overriding Royalty Interest):**
```
ORRI reduces NRI further:
NRI = WI × (1 − Federal Royalty − ORRI)
```
- Check for any ORRIs in licence assignment history — a common source of missed value leakage.

---

### 5.2 Severance / Production Tax

**Definition:** State-level tax on produced oil and gas at point of severance from the ground.

**Key Rates (US):**
| State | Oil Rate | Gas Rate |
|---|---|---|
| Texas | 4.6% of market value | 7.5% |
| Louisiana | 12.5¢/bbl or 0% for certain wells | Variable |
| Federal OCS (GoM) | None (royalty only) | None |
| Alaska | Variable (up to 35%) | Variable |

**GoM Note:** Federal Outer Continental Shelf (OCS) — no state severance tax. Federal royalty only.

---

### 5.3 Production Sharing Contract (PSC) Mechanics

**Definition:** Fiscal regime common outside the US where the government takes a share of production ("profit oil") after cost recovery. Used in many international upstream deals.

**Key PSC Elements:**
```
1. Cost Oil (Cost Recovery):
   Contractor recovers allowed costs from production up to cost oil cap (e.g., 60–80% of gross).

2. Profit Oil Split:
   Remaining production (gross − cost oil) split between contractor and government per PSC terms.
   Profit oil split = f(cumulative production, R-factor, oil price — varies by PSC)

3. Contractor Take (simplified):
   Net Revenue = Cost Oil Recovery + Contractor Share of Profit Oil
```

**R-Factor (common PSC trigger):**
```
R-Factor = Cumulative Revenue Received / Cumulative Investment Made

R < 1.0: Early life; contractor-favourable split
R = 1.5–2.5: Government take increases
R > 2.5: Maximum government take applies
```

**Notes:** Agent 04 should flag when `jurisdiction = PSC` and prompt for PSC terms before any revenue calculation.

---

### 5.4 Effective Tax Rate (ETR) for Upstream

**Definition:** The actual percentage of pre-tax cash flow paid as income tax, after deducting allowable reliefs (D&A, uplift, investment allowances).

**Formula:**
```
ETR (%) = Total Income Tax Paid ($) / Pre-Tax Income ($) × 100%
```

**Jurisdiction Reference:**
| Jurisdiction | Corporate Tax | Additional Levy | Effective Upstream Rate |
|---|---|---|---|
| US Federal | 21% | None | ~21% (post DD&A deductions) |
| UKCS | 30% ring-fence + 10% SC | Investment Allowance 29% | ~40–75% (variable) |
| Norway | 22% + 56% SP | 78% total; 78% uplift on capex | ~78% marginal, near-zero ETR with uplift |
| Angola | 65.75% | SRTM variable | High |

---

### 5.5 Tax Barrel (Deferred Tax Liability per Barrel)

**Definition:** The income tax cost attributed per barrel produced.

**Formula:**
```
Tax ($/bbl) = (Taxable Income per bbl) × Tax Rate

Taxable Income per bbl = Netback ($/bbl) − DD&A per bbl − Deductible Costs per bbl
```

---

## SECTION 6 — RESERVE & RESOURCE CLASSIFICATION

---

### 6.1 SPE-PRMS Classification Hierarchy

```
TOTAL PETROLEUM INITIALLY IN PLACE (PIIP)
│
├── DISCOVERED PIIP
│   │
│   ├── COMMERCIAL (Reserves)
│   │   ├── 1P — Proved (90% confidence cumulative ≥ 1P)
│   │   │   ├── PDP — Proved Developed Producing
│   │   │   ├── PDNP — Proved Developed Non-Producing
│   │   │   └── PUD — Proved Undeveloped
│   │   ├── 2P — Proved + Probable (50% confidence)
│   │   └── 3P — Proved + Probable + Possible (10% confidence)
│   │
│   └── SUB-COMMERCIAL (Contingent Resources)
│       ├── 2C — Best estimate Contingent Resources
│       ├── 1C — Low estimate
│       └── 3C — High estimate
│
└── UNDISCOVERED PIIP (Prospective Resources)
    ├── Low estimate (P90)
    ├── Best estimate (P50)
    └── High estimate (P10)
```

**Key Definitions:**
- **PDP:** Wells producing at the time of the reserve evaluation. Highest confidence; lowest risk. This is the "money in the bank" value.
- **PDNP:** Proved reserves accessible by existing wells but not currently producing (behind-pipe, shut-in). Higher confidence but requires intervention.
- **PUD:** Proved reserves requiring future well drilling or stimulation. Must have reasonable certainty and be scheduled within 5 years (SEC rule).
- **2C:** Contingent Resources — commercially viable but some obstacle prevents immediate development (regulatory, infrastructure, price). Not bookable as reserves until conditions met.

**SEC vs SPE-PRMS:**
- SEC reserves: deterministic, price-based (12-month trailing average), filed in 10-K
- SPE-PRMS: probabilistic (P90/P50/P10 = 1P/2P/3P), used in CPRs and international transactions

---

### 6.2 Reserves Reconciliation (Waterfall)

**Definition:** The standard reconciliation of how reserves changed over a period.

**Formula:**
```
Closing Reserves = Opening Reserves
                   − Production (actual)
                   + Revisions (technical)
                   + Extensions & Discoveries
                   + Acquisitions
                   − Disposals
```

**Red Flag:** Large negative revisions (downward) without clear explanation — particularly in PUD category. Indicates over-booking of prior reserves or failed development.

---

## SECTION 7 — DCF MODEL COMPONENTS

---

### 7.1 Revenue Build

```
Gross Revenue ($) = Gross Production (boe) × Realised Price ($/boe)
Net Revenue ($)   = Gross Revenue × (1 − Royalty Rate)

Realised Price:
  Oil = WTI (or Brent) ± quality/location differential
  Gas = Henry Hub (or NBP) × realisation factor (typically 75–85% for associated gas)
```

---

### 7.2 Standard E&P Cash Flow Waterfall

```
GROSS REVENUE
  Less: Royalties
= NET REVENUE
  Less: Operating Expenditure (Opex)
  Less: Production Taxes (Severance)
= EBITDAX (Operating Cash Flow pre-exploration)
  Less: Exploration Expense (if applicable)
= EBITDA
  Less: Depreciation, Depletion & Amortisation (DD&A)
= EBIT
  Less: Interest Expense (if applicable)
= EBT (Earnings Before Tax)
  Less: Income Tax
= NET INCOME
  Add back: DD&A
= OPERATING CASH FLOW (unlevered)
  Less: Capex
  Less: ARO Payments
= FREE CASH FLOW (unlevered, pre-debt service)
  Less: Debt Service (principal + interest)
= FREE CASH FLOW TO EQUITY
```

---

### 7.3 DD&A (Depletion, Depreciation & Amortisation)

**Definition:** The non-cash charge that systematically reduces the book value of oil & gas assets as they are produced.

**Unit of Production Method (Standard for O&G):**
```
DD&A per boe = Net Book Value of Asset ($) / Total Remaining Proved Reserves (boe)
DD&A Charge ($) = DD&A per boe × Actual Production (boe)
```

**Notes:**
- Impairment: If asset value drops below book value (e.g., oil price decline), a ceiling test write-down is triggered (SEC full-cost method). Project Corsair had a $45M impairment in Jun-25 — confirm residual book value.
- DD&A rate rises as reserves are depleted — late-life assets have high DD&A per boe.

---

### 7.4 Carried Interest Economics

**Definition:** A carry arrangement where one party (the carried party) has its share of costs paid by the other party (the carrying party) in exchange for a larger share of production or revenue.

**Formula:**
```
Carry Value ($) = WI Carried (%) × Total Capex ($)

After carry repayment, economics revert to underlying WI/NRI.
```

**Types:**
- **Gross carry:** Carrier pays 100% of costs; carried party repays from production (with or without uplift).
- **Net carry:** Carrier pays carried party's net share only.
- **Uplift (gross):** Carried party repays 1.5× or 2× the carry value — factor in as incremental liability.

---

## SECTION 8 — SENSITIVITY & RISK METRICS

---

### 8.1 Oil Price Sensitivity on NPV

**Formula:**
```
ΔNPV = Net Production (boe/year) × ΔOil Price ($/bbl) / Discount Factor Annuity

Simplified: ΔNPV per $1/bbl = Net Annual Production (MMboe) × PV Annuity Factor at r%
```

**Practical Rule of Thumb (producing asset, 10-year life, 10% discount):**
```
Every $1/bbl change in long-term oil price ≈ $3.5–5.5 per flowing barrel NPV impact
```

---

### 8.2 Break-Even Sensitivity Matrix

**Standard Stress Cases for GoM M&A:**
| Scenario | Oil Price | Notes |
|---|---|---|
| Base | Forward strip | Current NYMEX |
| Downside 1 | $55/bbl flat | 2020-style crash scenario |
| Downside 2 | $45/bbl flat | Severe downside |
| Upside | $85/bbl flat | Supply crunch / geopolitical |
| Management Case | As per IM | Test seller's assumptions |

---

### 8.3 ARO Sensitivity

**Definition:** ARO is a significant liability for mature GoM fields. The P50–P90 range creates material valuation uncertainty.

**Formula:**
```
ARO Sensitivity Impact on NPV ($) = (P90 ARO − P50 ARO) / (1+r)^t

Where t = expected decommissioning year
```

**Notes:**
- For Project Corsair: P50 ARO $9.7M; P70 $13.4M; P90 $18.9M. Net NPV of ARO delta (P90−P50) at 10%: ~$9.2M over 15-year decom horizon.
- Buyer should seek ARO cap, insurance, or bonding concession from seller.

---

### 8.4 Production Variance Sensitivity

**Formula:**
```
NPV Sensitivity to Production Decline = ΔNPV if decline rate increases by 5pp

Example: If base case D = 20% p.a., stress to D = 25% p.a.
ΔNPV = Σ [q₀ × (e^−0.25t − e^−0.20t) × Netback / (1+r)^t]
```

---

## SECTION 9 — ACQUISITION STRUCTURE METRICS

---

### 9.1 Bid Value Components

**Definition:** The full economic cost of an acquisition, including all liabilities assumed.

**Formula:**
```
Total Acquisition Cost = Cash Consideration
                        + Assumed Debt (net)
                        + Working Capital Adjustment
                        + ARO Assumed (P70)
                        + Day-1 Liabilities (vendor AP, intercompany balances)
                        − Closing Cash / Receivables
```

**Project Corsair Example (Feb 2026):**
```
Cash bid:              $30–34M
Day-1 liabilities:     ~$8.8M (vendor AP $5M + director/SH loan $3.8M)
ARO (P70):             $13.4M (PV ~$5.5M at 10%)
─────────────────────────────
Total economic cost:   ~$47–52M
vs. PDP PV-10:         $51.4M ✅ Marginal cover
vs. 1P PV-10:          $103.6M ✅ Strong cover
```

---

### 9.2 Enterprise Value vs Equity Value Bridge

**Formula:**
```
Equity Value = Enterprise Value − Net Debt + Cash − ARO (NPV) − Other Liabilities
```

**In M&A (Acquisition Context):**
```
Enterprise Value  = Purchase Price + Assumed Debt + ARO (NPV) − Cash Acquired
Equity Value Paid = Purchase Price (cash consideration only)
```

---

### 9.3 Loan-to-Value (LTV) for RBL Financing

**Definition:** The ratio of debt drawn under a Reserve-Based Lending (RBL) facility to the NPV-based value of the reserves used as collateral.

**Formula:**
```
LTV (%) = RBL Drawn ($) / Borrowing Base ($) × 100%

Borrowing Base = Bank's risked PV (using conservative price deck, haircut on 2P)
               ≈ 50–65% of PDP PV-10 (typical bank case)
```

**Typical RBL Parameters:**
| Parameter | Typical Range |
|---|---|
| Advance rate | 50–65% of PDP PV-10 |
| Price deck | Backwardated; stress-tested at $50–55/bbl WTI |
| Tenor | 5–7 years (within producing life) |
| Redetermination | Semi-annual or annual |

**Notes:**
- Shell prepayment facility in Project Corsair is functionally an RBL — effective rate ~14–14.5%.
- Borrowing base erodes with production and price — model redetermination risk for Year 1–2.

---

### 9.4 Debt Service Coverage Ratio (DSCR)

**Definition:** Ability to service debt from operating cash flows.

**Formula:**
```
DSCR = Operating Cash Flow ($) / Total Debt Service (Principal + Interest) ($)
```

**Interpretation:**
- > 2.0: Comfortable; standard bank covenant
- 1.25–2.0: Adequate; watch if oil price falls
- < 1.25: Covenant breach risk; stress-test immediately

---

### 9.5 Free Cash Flow Yield

**Definition:** Annual free cash flow as a % of acquisition price — useful quick return check.

**Formula:**
```
FCF Yield (%) = Annual Free Cash Flow ($) / Acquisition Price ($) × 100%
```

**Interpretation:**
- > 20%: Excellent — 5-year payback or better
- 10–20%: Good
- < 10%: Check against discount rate; may not clear hurdle

---

## SECTION 10 — DRILLING & WELL ECONOMICS

---

### 10.1 Well Payback Period

**Formula:**
```
Well Payback (years) = Drill + Complete Cost ($) / Annual Net Cash Flow from Well ($/year)
Annual Net CF = Well Production (boe/year) × Netback ($/boe)
```

---

### 10.2 EUR-Based Well Economics (NPV per Well)

**Formula:**
```
NPV_well = EUR (boe) × Netback ($/boe) × DCF Factor − Drill + Complete Cost ($)
```

**Decision rule:** Sanction drilling if NPV_well > 0 at base case; stress-test at $55/bbl.

---

### 10.3 Drilling Risk (Geological Chance of Success)

**Formula:**
```
Expected NPV_well = (CoS × NPV_success) + ((1 − CoS) × NPV_dry_hole)

NPV_dry_hole = −Dry hole cost (drilling cost if target not found or sub-commercial)
CoS = Chance of Success (geological probability; from CPR or G&G team estimate)
```

**Typical CoS Ranges:**
- Development well (proven reservoir): 85–95%
- Near-field exploration (step-out from producing field): 40–70%
- Exploration (unproven play): 10–35%

---

### 10.4 Capex Intensity

**Definition:** Capital expenditure per unit of production — measures how capital-hungry the asset is.

**Formula:**
```
Capex Intensity ($/boe) = Annual Development Capex ($) / Annual Incremental Production (boe)
```

---

## SECTION 11 — KEY UPSTREAM FINANCIAL TERMS (GLOSSARY)

> This section provides semantic anchors for the LLM to match natural-language queries to the correct formula or concept.

| Term | Definition | Aliases |
|---|---|---|
| **AFE** | Authority For Expenditure — pre-approval document for drilling/workover costs | Well AFE, drilling AFE |
| **ARO** | Asset Retirement Obligation — present value of estimated decommissioning cost | Decommissioning liability, abandonment cost, P&A cost |
| **BSEE** | Bureau of Safety and Environmental Enforcement — GoM regulator for OCS operations | MMS (old name) |
| **BTU** | British Thermal Unit — energy content measurement used for gas pricing and conversion | MMBtu, Mcf |
| **Carried Interest** | An interest in an asset where one party's costs are paid by another, to be repaid from production | Carry, gross carry, net carry |
| **COP** | Cessation of Production — the date a well or field stops producing | Field life end, abandonment date |
| **CPR** | Competent Person's Report — independent reserve and resource assessment | Reserve report, technical report |
| **DD&A** | Depreciation, Depletion & Amortisation — non-cash charge reducing book value as reserves are produced | DDA, depletion charge, D&A |
| **EBITDA** | Earnings Before Interest, Tax, Depreciation & Amortisation — approximates operating cash flow | EBITDAX (excludes exploration) |
| **EUR** | Estimated Ultimate Recovery — expected total production over field/well life | EUR, cumulative recovery |
| **EV** | Enterprise Value — total economic value including debt and equity; what an acquirer pays | Total acquisition cost, deal value |
| **FDP** | Field Development Plan — regulatory submission detailing how a field will be developed | Development plan, POD |
| **GOR** | Gas-Oil Ratio — produced gas per barrel of oil | Producing GOR |
| **IM** | Information Memorandum — seller's marketing document describing the asset | CIM, offering memorandum |
| **JOA** | Joint Operating Agreement — contract governing co-ownership and operations | Operating agreement |
| **LOS** | Lease Operating Statement — monthly financial summary of field revenues and expenses | LOE statement, operator statement |
| **LTIEA** | Long-Term Incentive & Equity Award — used in management retention structures | LTIP |
| **NAV** | Net Asset Value — intrinsic value based on risked PV of all reserves/resources net of debt | RNAV (risked NAV) |
| **NRI** | Net Revenue Interest — owner's share of revenue after royalties | Revenue interest |
| **OOIP** | Original Oil In Place — total oil in the reservoir before any production | STOIIP, OIP |
| **OPEX** | Operating Expenditure — cash costs to produce oil and gas (excludes capex) | Opex, lifting cost, LOE |
| **ORRI** | Overriding Royalty Interest — non-cost-bearing royalty carved out of WI | Override |
| **PDPs** | Proved Developed Producing Reserves — see Section 6.1 | PDP reserves |
| **POD** | Plan of Development — synonym for FDP in some jurisdictions | FDP |
| **PSA** | Purchase and Sale Agreement — the binding contract for an asset transaction | SPA (Share Purchase Agreement) |
| **PUD** | Proved Undeveloped Reserves — proved reserves requiring future drilling | Undrilled PUDs |
| **PV-10** | Present Value at 10% discount — SEC standard reserve value metric | PV10, NPV10 |
| **RBL** | Reserve-Based Lending — debt facility secured against proved reserves | Borrowing base facility |
| **ROFR / ROFO** | Right of First Refusal / Right of First Offer — pre-emption rights of co-owners | Pre-emption right |
| **Royalty** | Cost-free share of gross production paid to mineral rights owner | Overriding royalty, landowner royalty |
| **SWD** | Salt Water Disposal — facility/well for disposing of produced water | Disposal well |
| **WI** | Working Interest — owner's share of costs in a licence | Cost interest |
| **WC** | Water Cut — fraction of produced liquid that is water | BSW |
| **Workover** | Well intervention to restore or enhance production | Recompletion, well service |

---

## SECTION 12 — FORMULA QUICK REFERENCE INDEX

| Formula | Section | Input Requirements |
|---|---|---|
| Net Production | 2.1 | Gross production, NRI% |
| WI / NRI Relationship | 2.2 | WI%, royalty%, ORRI% |
| Exponential Decline | 2.3 | q₀, D, t |
| Implied Decline Rate | 2.4 | Two production rates, time interval |
| EUR (Exponential) | 2.5 | q₀, D |
| GOR | 2.6 | Gas prod, oil prod |
| Water Cut | 2.7 | Water prod, total liquid prod |
| Uptime | 2.8 | Actual hours, calendar hours |
| Reserve Replacement | 2.9 | Reserve additions, production |
| Recovery Factor | 2.10 | EUR, OOIP/OGIP |
| Lifting Cost | 3.1 | Total opex, net production |
| Netback | 3.2 | Oil price, royalty, transport, variable opex |
| Cash Break-Even | 3.3 | Opex, royalty, transport, production |
| Full-Cycle Break-Even | 3.4 | Cash break-even + annualised capex |
| F&D Cost | 3.5 | Capital invested, reserve additions |
| Recycle Ratio | 3.6 | Netback, F&D cost |
| ARO/boe | 3.7 | ARO estimate, remaining 2P reserves |
| NPV | 4.1 | Cash flows, discount rate |
| PV-10 | 4.2 | Net revenue cash flows |
| IRR | 4.3 | Cash flows, initial investment |
| Payback Period | 4.4 | Investment, annual cash flows |
| EV/EBITDA | 4.5 | EV, EBITDA |
| EV/2P | 4.6 | EV, 2P reserves |
| EV/1P | 4.7 | EV, 1P reserves |
| EV/Flowing Barrel | 4.8 | EV, net production boepd |
| Price/Cash Flow | 4.9 | EV, annual operating CF |
| NAV | 4.10 | PV of all reserves + resources − liabilities |
| Royalty | 5.1 | Gross revenue, royalty rate |
| Tax Barrel | 5.5 | Netback, DD&A, tax rate |
| DD&A | 7.3 | Net book value, proved reserves |
| Carry Value | 7.4 | WI carried, total capex |
| ARO Sensitivity | 8.3 | P50, P90 ARO, discount rate, decom year |
| Total Acquisition Cost | 9.1 | Cash bid, assumed debt, liabilities, ARO |
| LTV | 9.3 | RBL drawn, borrowing base |
| DSCR | 9.4 | Operating cash flow, debt service |
| FCF Yield | 9.5 | Annual FCF, acquisition price |
| Well Payback | 10.1 | D&C cost, annual CF |
| EUR Well NPV | 10.2 | EUR, netback, DCF factor, D&C cost |
| Drilling Expected NPV | 10.3 | CoS, NPV success, dry hole cost |

---

## SECTION 13 — AGENT 04 IMPLEMENTATION NOTES

**How the LLM should use this document:**

1. **Semantic matching:** When an analyst asks "what's the deal worth per barrel?", match to EV/Flowing Barrel (4.8) AND EV/2P (4.6) — present both.

2. **Input harvesting from VDR:** For each formula, the agent should know exactly which VDR document type to search for each input:
   - `Net Production`: Operator Monthly Report, LOS, CPR Production Profile
   - `NRI%`: JOA, Licence, CPR Fiscal Section
   - `2P Reserves`: CPR Reserves Table (Summary Section)
   - `Opex`: LOS, Management Accounts
   - `ARO`: ARO Study, Balance Sheet Note, CPR Decommissioning Section
   - `Oil Price`: Agent 05 (live forward curve) or CPR/IM price deck

3. **Unit validation before calculation:** Every formula must check that input units match expected units. Common errors to trap:
   - Mbbl vs bbl vs MMbbl confusion
   - BOPD vs Mbbl/month mismatch
   - $/bbl vs $/boe for gas-heavy assets
   - Royalty as a % vs $/bbl

4. **Output always includes:**
   - Result with unit
   - Formula used (symbolic)
   - Inputs used with source document
   - Any caveats or red flags triggered
   - Comparable range (from Section 4 typical ranges)

5. **Calculation cascade:** For complex queries (e.g., "What's the NPV of this acquisition?"), cascade through:
   `Net Production → Netback → Cash Flow → PV-10 → EV Components → NPV`

---

*End of Knowledge Bank v1.0 — 27 February 2026*
*Next version (v1.1) to add: PSC fiscal modelling, UKCS Ring Fence / Supplementary Charge detail, International fiscal regime templates (Angola, Nigeria, Malaysia), Monte Carlo sensitivity framework*
