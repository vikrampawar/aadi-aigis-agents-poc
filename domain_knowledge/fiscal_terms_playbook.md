# Aigis Analytics — Global Fiscal Terms Domain Knowledge Playbook
**Version:** 1.0 | **Date:** 27 February 2026
**Purpose:** Reference for the Financial Calculator Agent to model post-tax cash flows across global upstream petroleum fiscal regimes.

---

## 1. TAXONOMY OF FISCAL REGIMES

### 1.1 Three Fundamental Types

| Type | How Costs Are Recovered | Who Owns the Resource | Where Used |
|---|---|---|---|
| **Concessionary (Royalty/Tax)** | Tax deductions on profits | Private company (at wellhead) | USA, UK, Norway, Canada, Australia, most OECD |
| **Production Sharing Contract (PSC/PSA)** | Cost oil allocation from gross production | State retains ownership | Nigeria, Angola, Indonesia, Malaysia, Iraq (some), East Africa |
| **Service Contract (Risk/Pure)** | Fixed fee per barrel produced | State | Iraq (TSC), Iran, Mexico (historically), Kuwait |

**Agent rule:** Identify regime type FIRST before modelling any cash flows. Wrong regime type = completely invalid output.

---

## 2. CONCESSIONARY (ROYALTY/TAX) SYSTEMS

### 2.1 Core Cash Flow Structure

```
Gross Revenue (Production × Price)
  LESS: Royalty (% of gross or netback revenue)
= Revenue After Royalty
  LESS: Operating Costs (Opex)
  LESS: Depreciation/Depletion of Capex
= Taxable Income (may include uplift/allowances)
  LESS: Income Tax / Petroleum Profits Tax / Supplemental Tax
= Contractor Net Cash Flow
```

### 2.2 Key Fiscal Instruments

#### Royalties
- Applied to **gross production value** (top-line, before any cost deduction) — the most regressive instrument
- Can be flat (fixed %) or sliding-scale linked to price, production volume, or water depth
- May be paid **in cash** or **in kind** (government takes barrels)
- Royalties are NOT recoverable as a cost in PSC systems (unless specifically allowed)
- **Quirk:** Royalties create a minimum government revenue floor even on loss-making projects — IOCs must pay even in early low-revenue years

#### Capital Cost Depreciation/Amortisation
- Controls the pace at which capex enters the tax base
- Methods: straight-line, unit-of-production (UOP), declining balance
- **Investment Uplift:** Some regimes allow an extra % on capex for tax purposes (e.g. 15% uplift = 115% of capex as a tax deduction). This compensates for cost of capital and incentivises investment. Used in UK UKCS regime (historically).
- **Investment Tax Credit (ITC):** Direct credit against tax liability (e.g. 10% ITC = 10 cents off every dollar of tax owed). More valuable than a deduction.

#### Resource Rent Tax (RRT) / Windfall Tax
- Additional profits-based tax imposed when IRR exceeds a threshold
- Applied on top of corporate income tax
- **Progressive by design:** high government take at high prices/returns, low take at low returns
- Examples: Australia PRRT (40%), Norway (78% effective rate total), UK EPL/Energy Profits Levy
- **Formula:** RRT is often applied on accumulated net cash flows once they turn positive (or once IRR threshold crossed)

#### Ring-Fencing
- **Ring-fenced:** Costs from one field cannot offset profits from another; each field taxed independently → government captures rent per-field
- **Non-ring-fenced:** Company can offset losses across portfolio → more exploration incentive
- Critical distinction when modelling: ring-fencing makes loss-carry-forward field-specific

### 2.3 Country Profiles — Concessionary Regimes

#### United States (Offshore GoM / Onshore)
- Regime type: Royalty/Tax
- **Royalty:** 12.5–18.75% on offshore federal leases (historically; new leases 18.75%); state varies onshore
- **Corporate Income Tax (CIT):** 21% federal; state varies
- **No dedicated petroleum windfall tax** (EPAct bonus depreciation, IDC deductions available)
- **IDC (Intangible Drilling Costs):** 100% deductible in year incurred for domestic operators (major tax incentive)
- **Depletion Allowance:** 15% of gross income (for independent producers; not available to majors)
- **Ring-fencing:** No — losses across US operations fully consolidated
- **Local content / preferential terms for domestic companies:** No formal preference; Jones Act applies to marine operations

#### United Kingdom (UKCS)
- Regime type: Royalty/Tax (PRT-era contracts) + Special Tax for windfall
- **Ring Fence Corporation Tax (RFCT):** 30% on upstream ring-fenced profits
- **Supplementary Charge (SC):** 10% on same profits (effective rate 40% before EPL)
- **Energy Profits Levy (EPL):** 35% from May 2022 (initially 25%); extended to March 2030 under Labour government — pushes effective rate to ~75% for incumbents
- **Investment Allowances:** 29p in £1 of investment expenditure claimed against EPL (though reduced vs prior regime)
- **PRT:** 50% on pre-1993 fields; most now abandoned
- **Ring-fencing:** Yes — UKCS activities ring-fenced from non-UK operations
- **Quirk:** EPL investment allowance effectively makes new investment more valuable than incremental production. Model capex timing carefully.
- **Decommissioning Relief:** Tax relief clawback risk on asset sales — deferred decommissioning relief agreements (DDRAs) required

#### Norway
- Regime type: Royalty/Tax (no royalties on most fields; instead SO tax)
- **Corporate Tax:** 22% general; petroleum companies additionally pay **Special Petroleum Tax (SPT)** of 71.8% on upstream income → effective rate ~78% nominal
- **Uplift:** 17.69% of capex deductible against SPT (spread over 3 years) — very generous; designed to make investment break-even tax-neutral
- **Losses:** Carried forward with interest; exploration costs can be refunded annually by state
- **No ring-fencing** between fields on the NCS — portfolio consolidation
- **State Direct Financial Interest (SDFI):** Petoro manages the Norwegian state's working interests (not a tax — directly participates as WI holder); sits alongside IOC share
- **Quirk:** The 78% rate looks terrifying but uplift + loss refund = highly capital-efficient for IOCs; post-tax break-even price often only $30–40/bbl

#### Australia
- Regime type: Royalty/Tax + PRRT
- **CIT:** 30%
- **Royalties:** 10–12.5% for onshore/coastal; territory-specific
- **PRRT (Petroleum Resource Rent Tax):** 40% on extractable petroleum profits once accumulated cashflows positive; threshold based on uplift rate (LTBR + 5% for general, LTBR + 15% for exploration)
- **PRRT Base:** Revenue minus allowable deductions minus augmented costs (augmentation = carrying forward undeducted costs at uplift rate)
- **Quirk (post-2023 reform):** PRRT uplift rate reduced for offshore projects; increases government take on LNG. North West Shelf grandfathered under different rules. Model carefully.
- **Ring-fencing:** Yes — PRRT is per-project ring-fenced

#### Canada (Various Provinces)
- Regime type: Royalty/Tax
- Federal CIT: 15% + provincial (varies: AB ~8%, SK ~12%, BC ~12%)
- Alberta Crown Royalty: sliding scale 5–40% based on production volume and price
- **Oil sands royalty:** Pre-payout: 1–9% of gross; Post-payout: 25–40% of net
- **Quirk:** Payout threshold replaces the simple gross royalty; makes Alberta more like a hybrid PSC once payout reached

---

## 3. PRODUCTION SHARING CONTRACT (PSC) SYSTEMS

### 3.1 Core Cash Flow Structure — Step by Step

```
STEP 1: GROSS PRODUCTION (barrels/day × price)
  LESS: Royalty (if applicable — some PSCs have none)
= AVAILABLE PRODUCTION (post-royalty)

STEP 2: FIRST TRANCHE PETROLEUM (FTP) — if applicable
  → Some % of gross goes to government/NOC off the top before cost oil
  → Varies by country; Indonesia uses FTP at 20% for 1st-gen PSCs

STEP 3: COST OIL ALLOCATION
  → Contractor draws from remaining production to recover costs
  → Subject to COST RECOVERY CEILING (typically 40–90% of available production)
  → Allowable cost categories: Opex, Capex amortisation, abandonment, sometimes financing
  → CARRY-FORWARD RULE: Unrecovered costs carry to next period (no time limit typically)
  → Royalties & bonuses usually NOT cost-recoverable

STEP 4: PROFIT OIL = Available Production − Cost Oil Recovered
  → Split between Government/NOC and Contractor per PSC agreed percentages
  → Split can be:
     a) Fixed flat percentage
     b) Sliding scale on daily production rate (production tranches)
     c) R-Factor based (see Section 4)
     d) IRR/Rate of Return based (see Section 5)

STEP 5: INCOME TAX ON CONTRACTOR SHARE
  → Contractor pays CIT on (cost oil recovered + contractor profit oil share − allowable deductions)
  → In some regimes (Indonesia), "tax paid by government" on behalf of contractor from government profit oil share
  → In some regimes (Angola), profit oil alone is the tax base

STEP 6: CONTRACTOR NET = Cost Oil + Contractor Profit Oil − Tax Paid

CONTRACTOR ENTITLEMENT (barrels) = Cost Oil Barrels + Contractor Profit Oil Barrels
```

### 3.2 Key PSC Terms — Definitions

| Term | Definition | Agent Note |
|---|---|---|
| **Cost Oil** | Portion of production set aside to recover contractor costs | Always check if there is an annual ceiling (e.g. 40% of gross). Uncovered costs carry forward. |
| **Cost Recovery Ceiling** | Max % of gross production available for cost recovery per period | Low ceiling = slower recovery, earlier government revenue. High = more IOC-friendly. |
| **Profit Oil** | Remaining production after royalty and cost oil deduction | This is split between government and contractor per PSC. |
| **FTP (First Tranche Petroleum)** | % of gross production taken by government/NOC before cost oil | A "floor royalty" — reduces effective cost oil available; common in Indonesia, some West Africa |
| **Cost Uplift** | Additional % on capex for recovery purposes (e.g. 120% recovery of capex) | Compensates for time value; not all PSCs offer this |
| **Government Carry** | State/NOC equity interest carried by contractor through exploration | Contractor bears NOC's exploration risk; NOC pays back from production |
| **Back-in Rights** | Government/NOC right to acquire WI interest after commercial discovery | Dilutes IOC economics; model at time of FID |
| **Signature Bonus** | Lump sum paid to government on contract signing | NOT cost-recoverable; pure sunk cost |
| **Production Bonus** | Payment at specified production milestones | NOT cost-recoverable; reduces IRR |
| **Training Levy** | Annual contribution to government training fund | Varies from $200K to $0.15/bbl produced |

### 3.3 Country Profiles — PSC Regimes

#### Nigeria (PIA 2021 — New Framework)
- Regime type: PSC (offshore) / Concession (JV onshore)
- **Hydrocarbon Tax (HT):** Replaces PPT
  - Onshore/Shallow water: 30% (crude oil)
  - Deepwater (>200m): 0% HT (only CIT applies)
  - Mid-offshore (shallow): 15%
- **CIT:** 30% (all companies)
- **Royalty by volume (Oil):**
  - Onshore/Shallow: 10% (<10k boepd) to 25% (>25k boepd)
  - Deepwater (>800m): 0% before PIA; now tiered 0–10%
- **Royalty by price:** Additional royalty layer kicking in >$50/bbl; sliding up to 10% at $150/bbl; indexed +2%/yr
- **Production Allowance (replaces ITC/ITA):** $2.50–$8/bbl produced depending on area/type
- **Cost recovery ceiling:** ~70–80% for PSAs
- **R-Factor profit oil split:** Based on ROR mechanism in PSAs
- **NNPC Limited:** Commercialised NOC; requires JV participation
- **Local Content (NCDA 2010):** Mandatory; NCDMB monitors
  - 5–10% reserved activity categories (e.g. pipeline surveying)
  - 70%+ targets for Nigerians in various job categories
  - Preference/mandatory local procurement for listed items
  - **Foreign company disadvantage:** NCDMB tender preferences strongly favour Nigerian-registered entities; JVs with >51% Nigerian ownership get priority access

#### Angola
- Regime type: PSC (most offshore via Sonangol as concessionaire)
- **Petroleum Income Tax (PIT):** 50% on profit oil
- **Royalty:** 10% on gross production (some contracts have production-linked sliding scale)
- **Cost recovery ceiling:** 50–65% of gross (field dependent; older contracts have lower limits)
- **Profit oil split:** Negotiated, often linked to ROR or R-Factor; government take typically 65–85%
- **FTP:** Not common in Angola PSCs (royalty used instead)
- **Signature bonuses:** Very large in Angola — model as Year 0 negative cash flow; not recoverable
- **ITC:** Some early contracts provide investment tax credits
- **Sonangol EP:** Acts as both NOC and concessionaire; all contracts flow through Sonangol
- **Taxes unique to Angola:** Petroleum Production Tax (ISOP), Consumption Tax on services
- **Local content (Decree 271/20):**
  - Exclusivity list: Certain services only "Angolan Companies" (100% Angolan-owned)
  - Preference list: Preference to Angolan companies over JVCO (mixed-ownership) companies
  - Free competition: Remaining activities open to foreign companies
  - 70% workforce must be Angolan nationals
  - $0.15/bbl training levy annually (exploration phase: $200K fixed)
  - All contracts must include local content clause
  - **Agent flag:** Model procurement costs at higher rate for local-only services; assume some premium for compliance

#### Ghana
- Regime type: PSC + concession hybrid
- **CIT:** 35% (petroleum companies)
- **Royalty:** 5–10% on gross (field-specific; typically 7.5%)
- **Additional Oil Entitlement (AOE):** Extra government share when IOC exceeds target IRR — sliding scale from 0% (below target) to significant % (above target)
- **Cost recovery ceiling:** 60–70% of gross
- **Profit oil split:** 40–60% to government (field size dependent)
- **GNPC (Ghana National Petroleum Corporation):** Carries up to 15% state interest (carried through exploration; back-in at development)
- **Decommissioning:** ARO fund contributions required
- **Local content (LI 2204/2013):** Mandatory
  - At least 5% equity participation by indigenous Ghanaian companies in all petroleum agreements with foreign IOCs
  - 80% of executive/senior management must be Ghanaian for "indigenous company" classification
  - 50% local procurement target within 10 years of production start
  - **Agent flag:** IOC must carry Ghanaian equity partner; dilution factor on cash flows

#### Indonesia
- Regime type: PSC (Cost Recovery or Gross Split variant)
- **Historical Cost Recovery PSC:**
  - Cost recovery ceiling: 80% of gross production
  - FTP: 20% to government before cost oil
  - After FTP and cost oil: 85/15 split (government/contractor) for oil
  - Tax: 48% CIT on contractor profits (but "assumed div" tax reduces net)
  - Effective after-tax contractor share: ~15% of gross after FTP; looks low but recovery of costs makes it workable
- **Gross Split PSC (introduced 2017, revised 2023):**
  - No cost recovery mechanism — contractor takes its % of gross production and bears all costs
  - Base split: 43–57% government / 43–57% contractor (crude oil, varies by field size/type)
  - Variable components: adjust split for field characteristics (pressure, depth, location, API)
  - Simpler to administer; reduces goldplating incentive
  - **Quirk:** Gross split PSC transferring full cost risk to contractor; unattractive for marginal fields and deepwater due to high costs relative to gross split share
- **SKK Migas:** Upstream regulatory body; manages PSC compliance
- **Local content:**
  - Preference for Indonesian goods/services (Investment Law)
  - Quota targets for Indonesian employment in management
  - **No formal preferential fiscal terms for local vs. foreign companies** in PSC contracts, but procurement preferences exist

#### Malaysia
- Regime type: PSC (PETRONAS as counterparty)
- **CIT:** 25% on contractor profits
- **Royalty:** 10% on gross production (state royalty paid to states)
- **Cost recovery ceiling:** 60% of gross production
- **Cost oil:** Covers opex + capex amortisation (typically 20–25% per year declining balance)
- **R-Factor profit oil split:** Malaysia uses R-Factor (called R/C ratio — Revenue/Cost cumulative) to determine both profit oil shares AND cost recovery ceiling adjustments. Separate tables for oil and gas.
- **Profit oil split example (Malaysia oil):**
  - R < 1.0: Contractor 70% / Government 30%
  - R = 1.0–1.5: Contractor 50% / Government 50%
  - R > 1.5: Contractor 30% / Government 70%
- **Excess cost oil:** Cost oil not needed for recovery in a period → also subject to split
- **PETRONAS:** Fully controls block awards; all PSCs negotiated with/through PETRONAS
- **Special Petroleum Tax (SPT):** 20% on chargeable income before CIT
- **Local content (PETRONAS guidelines):**
  - Malaysian-registered entities preferred for goods/services
  - PETRONAS vendor development programme; mandatory use of Bumiputera (Malay/indigenous) companies for certain service categories
  - **Significant preferential treatment for Bumiputera companies** — explicit Malaysian government policy
  - Foreign companies often form JVs with PETRONAS or local partners to meet quotas

#### Iraq
- Regime type: Technical Service Contract (TSC) for major fields
- **Remuneration fee:** Fixed USD per barrel of incremental production above baseline
- **Cost recovery:** Costs recovered from production revenues; government retains risk
- **Tax paid by government** on behalf of contractor
- **Government take:** Very high (85–95%) but IOC gets contracted fee return
- **Local content:** Mandatory Iraqi workforce targets; preference for Iraqi-owned service companies

---

## 4. R-FACTOR CALCULATION METHODOLOGY

### 4.1 Definition and Formula

**R-Factor (R)** = Cumulative Cash Receipts ÷ Cumulative Cash Expenditures

Where:
- **Cumulative Cash Receipts** = Sum of (Contractor Cost Oil Recovered + Contractor Profit Oil) from contract inception to period t
- **Cumulative Cash Expenditures** = Sum of (Exploration Capex + Development Capex + Operating Costs) from contract inception to period t

**Some jurisdictions exclude opex from denominator** (only capex counted) — READ THE CONTRACT.

```
R(t) = Σ [Cost Oil(i) + Contractor Profit Oil(i)] / Σ [Capex(i) + Opex(i)]
         i=1..t                                          i=1..t
```

### 4.2 Interpretation

| R Value | Meaning | Typical Effect |
|---|---|---|
| R < 1.0 | Contractor has not yet recovered total investment | Contractor gets maximum profit oil share |
| R = 1.0 | **Payout point** — contractor has exactly recovered all costs | Split threshold triggers |
| R > 1.0 | Contractor is in profit above cost recovery | Government share increases |
| R = 1.5+ | Highly profitable project | Government captures most profit oil |

### 4.3 Stair-Step vs. Linear Interpolation

- **Stair-step (common in older contracts):** Profit oil split jumps abruptly at R thresholds
  - Creates incentive to manipulate spending to stay below next threshold ("goldplating")
  - Example Nigeria PSA: R<1 → 20% contractor; 1≤R<2 → 15% contractor; R≥2 → 10%
- **Linear interpolation (better design):** Split moves smoothly between thresholds
  - Formula: Contractor% = Max% − [(R − R_low) / (R_high − R_low)] × (Max% − Min%)
  - Eliminates cliff-edge incentive to manipulate costs

### 4.4 Calculation Frequency
- Typically calculated **annually** (at year-end); ratio applies for the following year
- Some contracts: quarterly calculation
- **Agent rule:** Check PSC for calculation period — annual is default assumption

### 4.5 Country Variations in R-Factor Definition

| Country | Numerator | Denominator | Notes |
|---|---|---|---|
| Generic | Cumulative cost oil + profit oil | Cumulative capex + opex | Standard definition |
| Malaysia | Cumulative revenues (post-royalty) | Cumulative costs | Separate tables for oil/gas |
| Nigeria PSA | Cumulative cost oil + profit oil | Cumulative capex + opex | Linear interpolation used |
| Chad | Cumulative revenues | Cumulative costs | Stair-step |
| Turkmenistan | Cumulative cost oil + profit oil | Cumulative costs | Negotiable thresholds |
| India NELP (IM) | Cum cost + profit petroleum – opex – royalty | Exploration + development costs | Investment Multiple; opex excluded |

**Agent rule:** When R-Factor is the mechanism, ALWAYS check: (a) definition of numerator/denominator, (b) whether stair-step or interpolated, (c) calculation frequency, (d) whether bonuses/royalties are excluded from numerator

---

## 5. RATE OF RETURN (IRR/ROR) BASED MECHANISMS

### 5.1 Overview
Rather than a cumulative ratio, ROR-based systems trigger higher government take when the project's internal rate of return (IRR) exceeds a specified threshold.

### 5.2 Mechanics
```
1. Compute cumulative net cash flows (NCF) for contractor to date
2. If cumulative NCF > 0 AND IRR > threshold → higher government take kicks in
3. Negative cumulative NCFs carry forward, often with an "uplift" (hurdle rate) applied to unrecovered amounts
4. As IRR crosses successive thresholds, government share of profit oil increases
```

### 5.3 Countries Using ROR Mechanisms
Australia (PRRT), Angola (some blocks), Uganda, Equatorial Guinea, Kazakhstan (some agreements), Papua New Guinea

### 5.4 Key Difference vs. R-Factor
- R-Factor: Simple ratio, does not consider time value of money
- ROR: Accounts for time value; theoretically more progressive and efficient
- R-Factor is easier to audit/administer; ROR more complex but more equitable

---

## 6. COST RECOVERY MECHANICS — DETAILED GUIDE

### 6.1 Allowable vs. Non-Allowable Costs

| Typically ALLOWED | Typically NOT ALLOWED |
|---|---|
| Exploration drilling costs (seismic, wells) | Signature/production bonuses |
| Development drilling & completion | Royalties (unless contract-specific) |
| Production equipment/facilities (amortised) | Head office overhead beyond agreed cap |
| Opex (lifting, processing, maintenance) | Interest on loans/financing costs |
| Abandonment/decommissioning (may be accrued) | Fines, penalties, tax payments |
| G&A (capped — typically 3–5% of opex) | Marketing costs (unless cost-plus basis) |
| Training levies (if PSC allows) | Costs incurred before contract effective date |

### 6.2 Depreciation/Amortisation Schedule for Capex

- **Straight-line:** Equal annual amortisation over N years (typically 5–10 years)
- **Unit of Production (UOP):** Capex × (Annual Production / Total Reserves) — preferred for production profiles with steep declines
- **Declining Balance:** Faster front-end recovery; favoured by contractors

### 6.3 Cost Recovery Carry-Forward
- Costs unrecovered in Year N (because ceiling hit) carry forward to Year N+1
- No time limit unless contract specifies (rare)
- **No interest paid on unrecovered costs** (unlike ROR uplift approach)
- **Agent rule:** Model cost carry-forward account separately; track each period

### 6.4 "Gold-Plating" Risk
- PSC cost recovery creates incentive to over-spend (costs recovery dilutes profit oil government gets)
- Modern contracts counteract this with: cost ceilings, ex ante capex approval by joint management committee (JMC), operating cost benchmarks, and shifting to Gross Split (Indonesia)
- **Agent flag:** In due diligence, compare operator capex/opex vs. independent benchmarks; material deviation is a red flag

---

## 7. KEY FINANCIAL METRICS FOR FISCAL COMPARISON

| Metric | Definition | Agent Use |
|---|---|---|
| **Government Take (GT%)** | State's total share of pre-tax project value | Primary cross-country comparison metric |
| **Effective Tax Rate (ETR)** | Total taxes paid / pre-tax profit | More useful than nominal rate |
| **Front-end Loading Index (FLI)** | PV(government revenues) / Total government revenues | High FLI = government collects early; bad for IOC NPV |
| **Break-Even Oil Price** | Minimum oil price for project to generate positive NPV after tax | Key investment decision metric |
| **Contractor IRR (post-tax)** | IRR on contractor's net cash flows after all fiscal takes | Must exceed WACC/hurdle rate |
| **Payback Period** | Years to recover total investment from contractor net cash | R-Factor payout ≡ Payback Period when R=1 |

---

## 8. LOCAL CONTENT AND PREFERENTIAL TERMS BY REGION

### 8.1 Africa — Summary Matrix

| Country | Local Co. Preference | Foreign IOC Restriction | Key Rules |
|---|---|---|---|
| **Nigeria** | Strong — NCDMB enforces | Mandatory ≥5% Nigerian equity in blocks | NCDA 2010; 53 reserved activities; job category targets |
| **Angola** | Very strong — tiered exclusivity/preference | 100% Angolan-owned for exclusivity services | Decree 271/20; 70% workforce must be Angolan; JVCO treated differently to full Angolan company |
| **Ghana** | Moderate-strong | Min 5% indigenous equity in any petroleum agreement | LI 2204/2013; 80% senior mgmt must be Ghanaian; GNPC carries state interest |
| **Mozambique** | Moderate | Preference for local companies | Decree Law 2014; modelled on Angolan framework |
| **Tanzania** | Moderate | Succession plans required for foreign workers | 2013 Local Content Policy; preference for Tanzanian goods/services |
| **Senegal/Mauritania** | Emerging | Evolving framework (newer producers) | PETROSEN / SMH carry interests; local employment targets |

### 8.2 Asia — Summary Matrix

| Country | Local Co. Preference | Key Rules |
|---|---|---|
| **Indonesia** | Moderate | Preference for local goods/services; no hard fiscal preference for local IOCs in PSC terms; Gross Split PSC uniform |
| **Malaysia** | Strong (Bumiputera policy) | PETRONAS vendor programme; Bumiputera companies get priority for service categories; foreign companies often form JVs with local partners |
| **India** | Moderate | DGH approval for block ops; preference for Indian goods/services in contracts |
| **Myanmar** | Moderate | MOGE participation (15–25% carried); local procurement preferences |
| **Vietnam** | Moderate-strong | PetroVietnam carries 15%+ interest; local suppliers favoured |

### 8.3 Middle East

- Most Gulf states use **service contracts** not PSCs/concessions → IOC has no equity in resource
- **Saudi Arabia (ARAMCO):** No formal IOC equity — JV arrangements only for downstream/gas
- **Iraq TSC:** Iraqi-owned service entities preferred for subcontracting; local employment quotas
- **UAE:** Limited IOC access; ADNOC concession with restricted terms
- **Qatar:** Predominantly QatarEnergy JV model; IOC as minority partner

### 8.4 Latin America

| Country | Regime Type | Key Note |
|---|---|---|
| **Brazil** | PSC (pre-salt) + R/T (post-salt) | Petrobras mandatory operator for pre-salt; local content required (30–70% by category) |
| **Colombia** | R/T concession | No NOC mandatory carry (Ecopetrol bids commercially) |
| **Ecuador** | Service contract | Petroecuador retains all resource; IOC receives service fee |
| **Trinidad & Tobago** | PSC (various vintages) | Heritage (NOC) participates; local content regulations evolving |

---

## 9. AGENT CALCULATION FORMULAS — QUICK REFERENCE

### 9.1 Royalty (Concessionary)
```
Royalty = Production Volume × Oil Price × Royalty Rate
```
For sliding scale:
```
If Production < Threshold_1: Royalty_Rate = Rate_1
If Threshold_1 ≤ Production < Threshold_2: Royalty_Rate = Rate_2
... etc.
```

### 9.2 PSC Cash Flow — Annual Period Calculation

```python
# Inputs:
# gross_prod = barrels produced in period
# oil_price = $/bbl
# royalty_rate = decimal (e.g. 0.10)
# ftp_rate = decimal (0 if no FTP)
# cost_ceiling = decimal (e.g. 0.60)
# costs_current = opex + capex amortisation in period
# carry_forward_costs = unrecovered costs from prior periods
# govt_profit_oil_pct = decimal (from split table or R-Factor)

gross_revenue = gross_prod × oil_price
royalty = gross_revenue × royalty_rate
post_royalty_revenue = gross_revenue − royalty

ftp = post_royalty_revenue × ftp_rate
available_for_cost = post_royalty_revenue − ftp

cost_oil_ceiling = available_for_cost × cost_ceiling
total_recoverable = costs_current + carry_forward_costs
cost_oil_taken = min(total_recoverable, cost_oil_ceiling)
carry_forward_new = total_recoverable − cost_oil_taken

profit_oil = available_for_cost − cost_oil_taken
contractor_profit_oil = profit_oil × (1 − govt_profit_oil_pct)
govt_profit_oil = profit_oil × govt_profit_oil_pct

contractor_taxable_income = cost_oil_taken + contractor_profit_oil − allowable_deductions
income_tax = contractor_taxable_income × cit_rate

contractor_net = cost_oil_taken + contractor_profit_oil − income_tax
```

### 9.3 R-Factor Calculation

```python
# At end of each period t:
# Cumulative from contract inception

cum_receipts[t] = cum_receipts[t-1] + cost_oil_taken[t] + contractor_profit_oil[t]
cum_expenditures[t] = cum_expenditures[t-1] + capex[t] + opex[t]

R_factor[t] = cum_receipts[t] / cum_expenditures[t]

# Apply to next period's profit oil split:
# (Using stair-step example)
if R_factor[t] < 1.0:
    contractor_pct = 0.40
elif R_factor[t] < 1.5:
    contractor_pct = 0.25
elif R_factor[t] < 2.0:
    contractor_pct = 0.15
else:
    contractor_pct = 0.10
```

For linear interpolation between R_low and R_high:
```python
contractor_pct = max_pct − ((R_factor[t] − R_low) / (R_high − R_low)) × (max_pct − min_pct)
contractor_pct = max(min_pct, min(max_pct, contractor_pct))
```

### 9.4 Resource Rent Tax (RRT) — Australian PRRT Style

```python
# Carried-forward undeducted costs are augmented by uplift rate each year
augmented_costs[t] = undeducted_costs[t-1] × (1 + uplift_rate) + new_costs[t]
augmented_deductions_available = augmented_costs[t]

prrt_base = max(0, gross_receipts[t] − augmented_deductions_available)
prrt = prrt_base × prrt_rate  # 40% for Australia

# If prrt_base = 0, remaining costs carry to next year:
undeducted_costs[t] = max(0, augmented_costs[t] − gross_receipts[t])
```

### 9.5 Government Take (GT) Calculation

```python
# For a full project lifecycle:
government_take = (Total Royalties + Total Govt Profit Oil + Total Tax) / Total Pre-Tax Project Value
# Pre-tax project value = PV of gross revenues - PV of costs (undiscounted or at specified discount rate)
```

---

## 10. CRITICAL QUIRKS & RED FLAGS BY REGIME

### 10.1 PSC-Specific Traps

| Trap | Why It Matters |
|---|---|
| **Cost ceiling too low** | If 40% ceiling and opex already uses 35%, new capex cannot recover quickly → NPV impact severe |
| **No uplift on cost recovery** | Time value of money means late recovery = economic loss; check if contract provides uplift % |
| **Bonuses front-loaded** | Large signature/production bonuses wipe out early-period cash; model these explicitly at Year 0 |
| **FTP reduces cost oil base** | Even before cost recovery, government takes FTP from production → double-layered take |
| **Stair-step R-factor cliffs** | Dramatic drop in contractor share at threshold creates incentive to over-invest near threshold |
| **Income tax on cost oil + profit oil** | If CIT applies to both recovered costs AND profit share, effective rate is much higher than nominal |

### 10.2 Concessionary-Specific Traps

| Trap | Why It Matters |
|---|---|
| **Ring-fencing prevents loss consolidation** | If field-specific ring-fence, losses cannot offset gains elsewhere → investor cannot reduce tax via portfolio |
| **Windfall tax on incremental production** | UK EPL/Energy Profits Levy retroactively changes economics of existing projects |
| **Royalty at peak production** | Gross royalty can exceed pre-tax profit at low oil prices (regressive) |
| **Decommissioning relief tax clawback** | In UK, ARO relief claimed is clawed back on field sale → price adjustment may be needed |

### 10.3 Local Content Financial Impacts

| Issue | Quantification Approach |
|---|---|
| **Local procurement premium** | Assume 10–20% cost premium for locally-sourced services vs. international market (country-specific) |
| **NOC/State back-in dilution** | Model NOC carry interest as dilution of contractor working interest; carried costs reduce net revenue entitlement |
| **Training levy** | Nigeria: included in opex. Angola: $0.15/bbl on production or $200K/yr exploration |
| **JV partner requirement** | Treat local JV partner share as equity dilution; check whether they contribute capex or are carried |

### 10.4 General Evaluation Checklist

Before modelling any PSC:
- [ ] Identify regime type (PSC / R/T / Service Contract)
- [ ] Confirm royalty rate, basis (gross/net), and payment form (cash/kind)
- [ ] Identify cost recovery ceiling %
- [ ] List allowable vs. non-allowable costs
- [ ] Identify amortisation schedule for capex
- [ ] Confirm profit oil split mechanism (fixed/production-tranche/R-Factor/ROR)
- [ ] If R-Factor: confirm numerator/denominator definitions, thresholds, interpolation method, calculation frequency
- [ ] Confirm income tax rate and base
- [ ] Identify FTP, if any
- [ ] Identify bonuses (signature, production) and note as non-recoverable
- [ ] Confirm NOC/state participation interest + carry terms
- [ ] Identify local content obligations ($ quantification)
- [ ] Confirm ring-fencing scope
- [ ] Check for windfall/resource rent tax and trigger conditions
- [ ] Identify ARO/decommissioning requirements and recovery eligibility

---

## 11. REFERENCE: GOVERNMENT TAKE RANGES BY REGION

| Region / Country | Regime | Typical Government Take |
|---|---|---|
| Norway | R/T + SPT | 78–82% (designed to be neutral pre-tax) |
| UK (post-EPL) | R/T + EPL | 70–75% |
| UK (pre-EPL) | R/T | 40–50% |
| USA (Federal offshore) | R/T | 40–55% |
| Australia (PRRT) | R/T + PRRT | 55–70% |
| Canada (Alberta) | R/T sliding | 40–60% |
| Nigeria (deepwater PSA) | PSC | 60–75% |
| Nigeria (onshore JV) | R/T + PPT | 70–85% |
| Angola (deepwater) | PSC | 65–80% |
| Ghana | PSC | 60–75% |
| Indonesia (cost recovery PSC) | PSC | 70–85% |
| Indonesia (gross split) | PSC | 55–70% |
| Malaysia | PSC | 65–80% |
| Iraq (TSC) | Service | 85–95% |
| Trinidad & Tobago | PSC / R/T | 55–70% |
| Brazil (pre-salt) | PSC | 65–80% |

---

## 12. SOURCE NOTES & FURTHER REFERENCE

- EY Global Oil & Gas Tax Guide (annual; downloadable free from ey.com)
- PwC Global Oil & Gas Tax Guide for Africa (2017 + annual updates)
- KPMG Africa Fiscal Guide (annual)
- IMF Fiscal Affairs Department: "Fiscal Regimes for Extractive Industries" (2012)
- Oxford Institute for Energy Studies: "Fundamental Petroleum Fiscal Considerations" (Johnston, 2015)
- Oxford Academic JWELB: "Oil and Gas Contracts Utilizing R Factors and Rates of Return" (2017)
- World Bank: "Local Content Policies in the Oil and Gas Sector" (2013)
- Nigeria PIA 2021 — Chapter 4 Fiscal Framework
- Angola: Presidential Decree 271/20 (Local Content)
- Ghana: LI 2204/2013 (Local Content)

---

*This playbook is a living document. Update when: new country PSC terms are encountered, fiscal laws change (especially Nigeria, UK, Angola), or new regime types are modelled.*
