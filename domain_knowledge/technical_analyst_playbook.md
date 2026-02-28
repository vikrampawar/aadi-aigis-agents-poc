# Upstream Subsurface & Well Performance Evaluation  
### First‑Principles Checklist and Rules of Thumb for an AI Agent

This document provides structured guidance for evaluating subsurface quality, well performance, and associated constraints for upstream oil and gas assets.  
It is written for an AI assistant supporting technical and commercial due diligence, with a focus on: reserves quality, production performance, decline analysis, facility bottlenecks, NFA cases, water handling, and decommissioning security.

The guidance is **jurisdiction‑agnostic** but draws on PRMS, SEC, North Sea and Norwegian practice as common reference frameworks.[web:11][web:13][web:18][web:17][web:20][web:23]

---

## 0. Core Principles for the Agent

When evaluating an asset, the agent should:

- Separate **facts** (from reports, datasets, legal docs) from **interpretations** and clearly flag interpretations as such.[web:11][web:21]
- Anchor reserves terminology to **PRMS** unless explicitly told the asset is SEC‑reporting only.[web:11][web:13][web:21][web:18]
- Always cross‑check:
  - Reported reserves/resources vs historical production performance.
  - Forecast profiles vs capacity constraints (wells, facilities, export).
  - Operating assumptions vs observed uptime, OPEX, and water handling data.[web:19][web:22][web:24]
- Reduce reliance on any conclusion that:
  - Is not supported by traceable documents (e.g. unreferenced “management slide”),
  - Conflicts with primary sources (e.g. regulator filings, independent reserves reports).[web:11][web:21][web:18]

For each conclusion, the agent should store:  
`{ conclusion, evidence_sources[], confidence (high/med/low), key_assumptions[] }`.

---

## 1. Quality and Reputation of Reserves Report Provider

### 1.1 First‑Principles Questions

When reading a reserves or CPR report, the agent should ask:

- Who prepared it?
  - Is the author a recognized reserves evaluator (e.g. Ryder Scott, GaffneyCline, DeGolyer & MacNaughton, McDaniel, NSAI, RISC)?[web:21]
  - Are they members of SPE/PRMS or SPEE and signatories to relevant professional codes (SPEE, AAPG, etc.)?[web:11][web:14][web:21]
- What classification system and reporting basis?
  - PRMS vs SEC, and which version of PRMS (2007, 2018 update).[web:11][web:13][web:15][web:18][web:21]
  - Use of deterministic vs probabilistic methods.
  - Constant price/cost vs management’s best estimate vs SEC 12‑month historical price.[web:11][web:12][web:15][web:18][web:24]
- What is the scope?
  - Which fields, wells, and projects are covered (developed producing, developed non‑producing, undeveloped, contingent resources, prospective resources).[web:11][web:13][web:21]
  - Are non‑operated interests included and on what data access basis?
- Independence and conflicts:
  - Is the report “independent” or commissioned as “internal management estimate”?
  - Does the report explicitly state that it adheres to PRMS and/or relevant listing/regulatory standards (e.g. SEC, local stock exchange guidance).[web:11][web:18][web:21]

### 1.2 Rules of Thumb for the Agent

- Treat reports by major independent firms, explicitly referencing PRMS and including detailed methodology, as **higher baseline reliability**.[web:11][web:13][web:21]
- Treat management‑only estimates without independent sign‑off as **medium or low reliability**, especially for 2C/3C or prospective resources.
- If PRMS is used:
  - Ensure Reserves satisfy the four criteria: discovered, recoverable, commercial, remaining.[web:11][web:14][web:21]
  - Check explicit demonstration of commerciality: positive net present value under stated prices and costs.[web:11][web:15][web:24]
- If SEC is used:
  - Recognize that “proved reserves” can be more conservative than PRMS 1P (e.g. technology constraints, pricing rules).[web:15][web:18]
  - Do not directly equate SEC proved with PRMS 1P without context; note this explicitly.[web:18]

The agent should downgrade confidence when:

- The report lacks clear price/cost assumptions, project timing, or economic limit criteria.[web:11][web:12][web:24]
- 2P/2C volumes appear very large relative to historical performance with no clear justification (e.g. step‑change technology or re‑development project).

---

## 2. Dependability of Reserves and Resource Estimates

### 2.1 PRMS and Economic Criteria

Under PRMS:

- Reserves require a **reasonable expectation of commercial development**, including positive project economics and no unresolved contingencies.[web:11][web:13][web:21]
- Projects are classified first, and then quantities assigned as 1P/2P/3P or 1C/2C/3C and prospective; splitting a single project across Reserves and Contingent Resources is not allowed.[web:11][web:13][web:21]
- Economic limit tests, prices, fiscal terms and costs must be clearly documented.[web:11][web:12][web:15][web:24]

### 2.2 Red Flags in Volume Estimates

The agent should flag and lower confidence when:

- 1P volumes do not appear economically viable at the stated assumptions (e.g. negative NPV for low case, but still classified as 1P).[web:11][web:21][web:24]
- Large Contingent Resources (2C/3C) have no clear plan to resolve contingencies (e.g. no sanction, no access to capacity, marginal economics).[web:11][web:13][web:21]
- Proved undeveloped (PUD) volumes are booked for projects far in the future without a credible development plan or within regimes requiring development within a certain time frame (e.g. PRMS suggests a 5‑year development benchmark).[web:11]

### 2.3 Cross‑Checking Dependability

The agent should:

- Compare cumulative production + remaining 1P vs OOIP/OGIP and recovery factors; flag implausible recoveries for the reservoir type.
- Cross‑check decline trends vs forecast production profiles:
  - If historical decline is steeper than forecast, require evidence of mitigating actions (infill drilling, workovers, compression, EOR).[web:19][web:22]
- Compare reserves booked at the field vs infrastructure constraints:
  - Export and processing capacity, water handling, gas flaring limits.[web:19][web:22][web:24]

If inconsistencies persist and no supporting explanation is found in the data room, the agent should classify conclusions as **speculative** and highlight specific missing evidence.

---

## 3. Historical Production vs Future Forecasts and Bottlenecks

### 3.1 Production Data Checks

For each well/field, the agent should:

- Extract monthly (or finer) production data:
  - Oil, gas, water rates; cumulative field and well production.[web:19][web:22]
- Identify key events:
  - First oil/gas date, interventions, recompletions, artificial lift installation, facility outages.
- Compute:
  - Decline rates, changes in decline coinciding with operational events.
  - Changes in water cut and gas‑oil ratio over time.[web:19][web:22][web:25]

### 3.2 Relating History to Forecast

The agent should compare:

- Historical decline vs forecast decline:
  - If history shows exponential decline with a given decline rate, forecast flattening (lower decline) must be justified (e.g. new drilling, pressure support).[web:19][web:22]
- Peak rates vs facility/export capacity:
  - Check that forecast plateau rates do not exceed nameplate minus realistic downtime.[web:24]
- Historical uptime vs assumed uptime:
  - If historical uptime is 90% and forecast uses 98%, the agent should demand evidence (major upgrades, reliability programs, redundancy).[web:24]

### 3.3 Bottlenecks and Constraints

Typical potential bottlenecks the agent must check for:

- Subsurface:
  - Pressure depletion, water or gas breakthrough, compartmentalization, faults limiting drainage.
- Wellbore:
  - Tubing size, sand control, artificial lift limitations, maximum drawdown constraints, scaling/asphaltene problems.
- Surface facilities:
  - Oil processing capacity, water handling capacity, gas compression capacity, flaring limits, produced water reinjection capacity.[web:24]
- Export and midstream:
  - Pipeline capacity, downstream processing/terminal limits, export nominations and curtailment.
- Operational:
  - Rig/drilling slot availability, workover capacity, permitting constraints, seasonal weather.

The agent should flag as **under‑considered** if:

- Reserves and forecasts assume higher production than any historical rates without clear facility upgrades.
- Facilities are near or beyond rated capacity when water cut and gas rates are expected to increase, stressing separators, compressors, and water systems.[web:24][web:25]
- Forecast assumes unconstrained operations but regulatory or transportation constraints are documented elsewhere (e.g. flaring caps, export pipeline priorities).

---

## 4. No Further Activity (NFA) Case, Lifting Costs, and Decom

### 4.1 Defining the NFA Case

The NFA case assumes:

- No new wells or major workovers beyond necessary safety and integrity work.
- Minimal sustaining capex, with operations run to economic or technical limit.
- Decommissioning occurs when production reaches economic limit or regulatory cessation of production (CoP) is triggered.[web:11][web:23]

The agent should:

- Derive NFA production trajectory from current wells using decline analysis (section 5) constrained by current facility limits.
- Estimate when the field hits economic limit:
  - When netback per barrel no longer covers variable lifting costs (opex, tariffs, water handling, fuel).[web:24]

### 4.2 Comparing to Lifting Costs and Decom Spend

Key checks:

- Operating cost structure:
  - Fixed vs variable OPEX, water handling and disposal costs, energy costs, logistics and manning, tariffs.[web:24]
- At each future year, compare:
  - Revenue (price net of royalty/fiscal terms) vs lifting costs and tariffs.
  - Add decom provisions post‑CoP.

Rules of thumb:

- If NFA still produces material volumes with positive netbacks, NFA can be a viable “base” case; incremental activity must be justified vs this baseline.
- When late‑life fields show:
  - High fixed OPEX per barrel.
  - Rising water cut with increasing water handling costs.
  - Imminent decom obligations.
  the agent should question whether further investments truly improve economics vs accelerated decom.[web:24][web:23]

### 4.3 Decommissioning Timing and Economics

Under many offshore regimes (e.g. UKCS):

- Decommissioning of offshore installations and pipelines is governed by statutory frameworks (e.g. UK Petroleum Act 1998 Part IV, OSPAR Decision 98/3 prohibiting dumping/abandonment in situ for most structures).[web:23]
- Operators must submit decommissioning programmes and obtain approval prior to removal, with obligations extending to pipelines.[web:23]

For the agent:

- Confirm that forecasts include decom spend in the appropriate time window and that security arrangements cover the predicted cost (see section 7).
- Where data is missing, treat decom timing and quantum as a major uncertainty and avoid strong conclusions.

---

## 5. Water‑Cut and Decline Curve Analysis (Including Log Plots)

### 5.1 Overview of Decline Curve Analysis (DCA)

Decline curve analysis is a standard reservoir engineering method to forecast future production by fitting mathematical models to historical rate data.[web:16][web:19][web:22]

Common models (Arps):

- Exponential decline: constant percentage decline rate.
- Hyperbolic decline: decline rate decreases over time with exponent \(b\).
- Harmonic decline: special case of hyperbolic with \(b = 1\).[web:19][web:22]

### 5.2 Practical Steps for the Agent

For each well/field:

1. Data preparation:
   - Gather time series of rate (q), cumulative production (Np), and water cut (WC) or water‑oil ratio (WOR).[web:19][web:22]
   - Remove periods with clear operational noise (shut‑ins, major facility outages) where appropriate, but keep a log of exclusions.
2. Plots and fits:
   - Plot q vs time on semi‑log (log q vs t) to test exponential behavior; a straight line suggests exponential decline.[web:19][web:22]
   - Plot q vs Np on Cartesian; exponential decline should also give a straight line.[web:19]
   - For hyperbolic decline, use log‑log type curve matching following Fetkovich‑style methods.[web:16]
3. Model selection:
   - Start with exponential; if data shows clear curvature on semi‑log, test hyperbolic and match on log‑log type curves.[web:16][web:19]
   - Ensure model choice is consistent with drive mechanism and reservoir behavior (e.g. strong water drive vs depletion).[web:16][web:19][web:22][web:25]

### 5.3 Log‑Log Type Curve and Water‑Cut Behaviour

Fetkovich‑type analysis:

- Combines decline behavior with type curves on log‑log axes, allowing matching of transient and boundary‑dominated flow periods.[web:16]
- The analyst overlays actual production data on pre‑computed type curves to estimate reservoir parameters and forecast future performance.[web:16]

Water‑cut analysis (especially in water‑drive or waterflood reservoirs):

- Water cut typically rises over time as the waterfront approaches and breakthrough occurs.[web:25]
- High water cut wells may still be productive if facilities can handle water and netbacks remain positive; however, they stress water handling systems and can dominate OPEX.[web:24][web:25]
- WOR or WC vs cumulative production plots can reveal breakthrough and channeling issues and help assess remaining oil saturation and sweep efficiency.[web:19][web:25]

For the agent:

- Identify inflection points where water cut accelerates; check whether forecasts appropriately steepen decline or increase OPEX around those points.[web:19][web:22][web:25]
- If forecasts assume flat or improving water cut in a mature waterflood or water‑drive reservoir without technical justification (e.g. conformance control, new injectors), flag as questionable.

### 5.4 Quality‑Control Rules of Thumb

- Use sufficiently long and stable production periods; avoid early‑time transients for long‑term decline fitting.[web:19][web:16][web:22]
- Ensure operating conditions (choke, tubing, artificial lift) are stable; otherwise you may be fitting operational changes, not reservoir decline.[web:19]
- Cross‑check field‑level DCA with well‑level DCA and volumetric estimates; major inconsistencies require explanation.

---

## 6. Water Handling Capacity and Facility Uptime

### 6.1 Water Handling Systems

Production facilities typically have:

- Oil processing capacity (e.g. bbl/d of total liquids and/or oil).
- Produced water handling capacity:
  - Separation, treatment, disposal/reinjection, overboard discharge within environmental limits.
- Gas handling:
  - Compression, export, gas lift supply, flaring limitations.[web:24]

Key checks for the agent:

- Compare current and forecast water volumes vs nameplate water handling capacity; large increases in water cut may quickly consume capacity.[web:24][web:25]
- Review actual utilization:
  - Are facilities already operating near water handling limits?
  - Have there been historical water‑related constraints (e.g. frequent high‑water shutdowns)?

### 6.2 Uptime and Reliability

The agent should:

- Calculate historical uptime:
  - Percentage of time onstream for the field and key systems.
- Compare to forecast assumptions:
  - If history = 85–90% uptime and forecasts use 95–98%, require evidence (planned debottlenecking, redundancy, new maintenance strategy).[web:24]
- Check for historical:
  - Unplanned shutdowns, chronic equipment issues (compressors, pumps, separators).
  - Regulatory or environmental shutdowns (e.g. produced water discharge violations).

Rule of thumb:

- Use historical uptime as a baseline; only increase it in the base case if concrete projects justify improvement.
- For sensitivity analysis, the agent should easily simulate downside scenarios (e.g. 3–5 percentage points lower uptime).

### 6.3 Integration with Economic and Reserves Assessment

- Higher water cuts and lower uptime:
  - Reduce effective production, increase unit lifting costs, and may accelerate economic limit.[web:24]
- If reserves booking assumes:
  - Unconstrained production, low unit OPEX, and high uptime, but facilities tell a different story, the agent should flag reserves as operationally constrained and potentially overstated.

---

## 7. Decommissioning Security Arrangements and Jurisdictional Rules

### 7.1 General Concept

Decommissioning security arrangements (DSAs) are contractual and regulatory mechanisms to ensure that sufficient funds are available to cover future decommissioning obligations for offshore installations and wells.[web:17][web:20][web:23]

They typically:

- Allocate decom liability among joint venture partners.
- Require provision of security (letters of credit, parent company guarantees, trust accounts) to cover each party’s share of expected decom costs.[web:17][web:20]

### 7.2 UK North Sea Example

In the UK:

- Part IV of the Petroleum Act 1998 sets the framework for decommissioning offshore installations and pipelines.[web:23]
- OSPAR Decision 98/3 prohibits dumping or leaving offshore structures in place, with limited derogations, requiring removal or approved alternative decommissioning measures.[web:23]
- Decommissioning Security Agreements (DSAs) are commonly used in JV arrangements, although not mandatory, to ensure each participator provides security for its share of future decom costs.[web:17]

The UK HMRC Oil Taxation Manual notes:

- DSAs are “standard oil and gas industry agreements” used to agree decom liability and ensure appropriate provision for each company’s share of future decommissioning costs.[web:17]

### 7.3 Norwegian Model Agreement Example

In Norway:

- Petroleum Act Section 5‑3 addresses liability for removal of facilities, including for buyers in licence transfers.
- Norwegian Oil and Gas (Offshore Norge) publishes a recommended model Decommissioning Security Agreement that provides clauses for security for removal obligations and allocation of liability between sellers and buyers.[web:20]

The model agreement:

- Reflects legal provisions under the Petroleum Act and its regulations.
- Suggests that sellers may retain alternative liability for facilities and wells existing at the time of transfer and provides model clauses for decommissioning security in licence transfers.[web:20]

### 7.4 Agent Checks on Decom Security

For any jurisdiction, the agent should:

- Identify regulatory framework:
  - Key statutes and decisions governing decom (e.g. Petroleum Act, OSPAR 98/3 or local equivalents).[web:23][web:20]
- Identify contractual arrangements:
  - DSA or equivalent, JOAs, sale and purchase agreements with decom security clauses.
- Check coverage:
  - Does the estimated decom cost (from decom study or liabilities note) align with the security requirements?
  - Are security mechanisms (e.g. letters of credit) sized and scheduled appropriately, particularly for late‑life assets?
- Flag gaps:
  - If decom obligations are clear but security is absent or inadequate.
  - If a seller retains joint and several or alternative liability without corresponding consideration or security.[web:20][web:17]

The agent should treat decom security coverage as a **key risk dimension** in late‑life acquisitions and should avoid concluding “risk‑free decom” unless security mechanisms and legal frameworks are clearly documented.

---

## 8. How the Agent Should Use This Playbook

When answering questions or running analyses, the agent should:

1. Map the question to the relevant sections above (reserves quality, DCA, water handling, NFA, decom).
2. Extract factual data from:
   - Reserves reports (PRMS/SEC classifications and economics).
   - Production and facility data (time series, uptime, capacities).
   - Contracts and legal documents (DSAs, JOAs, regulatory approvals).
3. Apply the rules of thumb and checks:
   - Cross‑validate reserves vs production vs facilities.
   - Stress‑test uptime, water handling and economic limits.
   - Check decom security adequacy.
4. Return:
   - A structured assessment with explicit references to underlying documents.
   - Confidence levels and key uncertainties.
   - Clear separation between observed data and interpretative commentary.

The agent should never present speculative or weakly‑supported interpretations as facts and must always reference the specific documents or data that underpin any critical conclusion.

---

## 9. Open Points and Local Customization

This playbook provides generic guidance and should be customized where the VDR or asset set has specific characteristics:

- Unconventional plays (shale, tight oil/gas): may require modified decline methods and type curves.
- Heavy oil, EOR projects, complex multi‑layer reservoirs: need different DCA and water‑cut behaviors.
- Specific fiscal regimes and listing requirements: SEC‑only issuers, local exchange rules and company‑specific guidance may alter reserves disclosure practices.[web:18][web:24]

Users should consult relevant specialists and primary documents for decisions and treat this playbook as contextual guidance only.

