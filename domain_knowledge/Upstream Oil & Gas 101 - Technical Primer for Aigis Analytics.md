# UPSTREAM OIL & GAS 101

A Technical Primer for AI/RAG Development

Prepared for: Aigis Analytics Technical Co-Founder  
Date: February 12, 2026

# TABLE OF CONTENTS

1\. Executive Summary & Purpose  
2\. The Upstream Oil & Gas Value Chain  
3\. Key Industry Terminology & Jargon  
4\. Petroleum Fiscal Regimes  
5\. Reserves & Resources Classification  
6\. Critical VDR Documents & Their Contents  
7\. Valuation Methodologies & Key Heuristics  
8\. M\&A Due Diligence Workflow  
9\. RAG Architecture for O\&G Due Diligence  
10\. Document Parsing & Data Extraction Strategies  
11\. Appendix: Quick Reference Tables

# 1\. Executive Summary & Purpose

This document serves as a comprehensive primer on upstream oil & gas for technical professionals building AI-powered due diligence systems. It is specifically designed for developers with strong AI/ML backgrounds but limited exposure to the petroleum industry.

WHY THIS MATTERS FOR RAG DEVELOPMENT:

The upstream oil & gas sector presents unique challenges for NLP and retrieval systems:  
• Highly technical, domain-specific terminology (reserves classification, fiscal regimes, decline curves)  
• Multi-format data: PDFs (reserves reports), Excel (economic models), legal contracts  
• Structured numerical data embedded in narrative documents  
• Industry-specific heuristics and best practices that must be encoded as context  
• High-stakes decisions: M\&A deals range from $50M to $10B+

Your RAG system isn't just searching documents—it's interpreting technical reserves classifications (1P/2P/3P, PDP/PUD), extracting NPV calculations from Excel waterfalls, cross-referencing Production Sharing Contracts with fiscal models, and detecting red flags that could derail billion-dollar transactions.

# 2\. The Upstream Oil & Gas Value Chain

The oil & gas industry is divided into three segments:

UPSTREAM (Exploration & Production / E\&P)  
• Finding and extracting oil & gas from underground reservoirs  
• Geological surveys, seismic studies, drilling, production  
• THIS IS YOUR FOCUS \- where Aigis Analytics operates  
• Highest risk, highest reward segment  
• Value driver: Hydrocarbon reserves in the ground

MIDSTREAM (Transportation & Storage)  
• Pipelines, shipping, LNG terminals, storage facilities  
• Moving hydrocarbons from wellhead to market  
• Relevant to upstream as transportation costs affect economics

DOWNSTREAM (Refining & Marketing)  
• Refining crude into products (gasoline, diesel, jet fuel)  
• Distribution and retail sales  
• Less relevant to your RAG system

KEY POINT FOR RAG: Documents in a VDR will focus heavily on upstream activities—reserves reports, production data, drilling programs—with midstream contracts (transportation agreements, processing fees) affecting cash flow models. Your system needs to understand how transportation costs and processing fees flow into economic valuations.

# 3\. Key Industry Terminology & Jargon

RESERVES TERMINOLOGY

BOE (Barrels of Oil Equivalent)  
• Standard unit for measuring oil & gas together  
• 1 BOE \= 1 barrel of oil OR \~6,000 cubic feet of natural gas  
• Allows apples-to-apples comparison across different hydrocarbon types

MMBOE / MMBOE (Million Barrels of Oil Equivalent)  
• MM \= Million (Roman numeral convention)  
• Used for large reserve quantities

Reserves vs. Resources  
• RESERVES \= Commercially recoverable hydrocarbons with committed development plans  
• RESOURCES \= Hydrocarbons in ground that MAY become reserves (contingent or prospective)

1P, 2P, 3P (Reserves Categories \- PRMS System)  
• 1P (Proved) \= 90% confidence of recovery | "P90" or "Low estimate"  
• 2P (Proved \+ Probable) \= 50% confidence | "P50" or "Best estimate"  
• 3P (Proved \+ Probable \+ Possible) \= 10% confidence | "P10" or "High estimate"  
• RAG IMPLICATION: When you see "2P reserves of 50 MMBOE", understand there's 50% chance of recovering that much

PDP, PUD, PDNP (Reserves Sub-Categories)  
• PDP (Proved Developed Producing) \= Currently flowing wells | Lowest risk, highest value  
• PUD (Proved Undeveloped) \= Requires drilling but has committed plan | Higher risk  
• PDNP (Proved Developed Non-Producing) \= Drilled but shut-in or behind-pipe  
• RAG IMPLICATION: High PUD% in reserves \= More future capex required, higher execution risk

R/P Ratio (Reserve-to-Production Ratio)  
• Formula: Total Reserves ÷ Annual Production  
• Example: 100 MMBOE reserves ÷ 10 MMBOE/year \= 10-year reserve life  
• Indicates how long reserves will last at current production rates

PRODUCTION & TECHNICAL TERMS

Decline Curve  
• Graph showing how well/field production decreases over time  
• Used to forecast future production  
• Types: Exponential (steady %), Hyperbolic (declining %), Harmonic  
• RAG IMPLICATION: Reserves reports will reference decline rates (e.g., "15% annual decline")

Type Curve  
• Average production profile for wells in similar geology  
• Used to estimate performance of undrilled wells (PUDs)  
• Based on analogue wells in same basin/formation

EUR (Estimated Ultimate Recovery)  
• Total hydrocarbons expected from a well over its life  
• Example: "Average EUR of 500 MBoe per well"

BOEPD / BOEPD (Barrels of Oil Equivalent Per Day)  
• Production rate measurement  
• Example: "Current production: 15,000 BOEPD"

WORKING INTEREST vs. NET REVENUE INTEREST

Working Interest (WI)  
• Ownership % that bears costs and receives revenues BEFORE royalties  
• Example: Company owns 60% WI in a field

Net Revenue Interest (NRI)  
• Ownership % AFTER deducting royalties and overriding royalties  
• Formula: NRI \= WI × (1 \- Royalty Rate)  
• Example: 60% WI with 20% royalty \= 48% NRI  
• RAG IMPLICATION: Economic models use NRI for cash flow calculations

FISCAL & VALUATION TERMS

NPV10, NPV15 (Net Present Value at 10% / 15% discount)  
• Value of future cash flows discounted to present  
• NPV10 \= Standard for reserves reporting  
• Higher discount rate \= Lower NPV (reflects risk/time value)  
• RAG IMPLICATION: Core valuation metric in CPR reports and economic models

PV10 (Present Value at 10%)  
• Similar to NPV10 but BEFORE income tax  
• Used in SEC reporting

EV/BOE (Enterprise Value per Barrel of Oil Equivalent)  
• Transaction multiple \= Deal Value ÷ Total Reserves  
• Example: $500M deal for 50 MMBOE \= $10/BOE  
• Benchmark for comparable transactions

LIFTING COSTS / OPEX  
• Operating costs per barrel produced  
• Example: "$12/BOE lifting costs"  
• Includes labor, power, chemicals, maintenance

F\&D COSTS (Finding & Development Costs)  
• Total capex to find and develop reserves per BOE  
• Efficiency metric for E\&P companies

4\. Petroleum Fiscal Regimes

Different countries use different systems to capture government "take" from oil & gas projects. Your RAG needs to understand these because they dramatically affect cash flows.

THREE MAIN FISCAL SYSTEMS:

1\. TAX & ROYALTY (Concession/License System)  
• Examples: USA, UK, Norway, Canada  
• Company owns produced hydrocarbons  
• Government take via: Royalties \+ Corporate Income Tax \+ Special Petroleum Taxes  
• Company books 100% of reserves (but pays taxes on revenues)  
• RAG IMPLICATION: Look for royalty rates (e.g., "12.5% royalty") and tax rates in contracts

2\. PRODUCTION SHARING CONTRACTS (PSC)  
• Examples: Indonesia, Malaysia, Angola, many Middle East/Africa countries  
• State retains ownership; contractor gets share of production  
• Structure:  
   a. Cost Recovery Oil/Gas \- Contractor recovers costs (subject to cap, e.g., 50% of production)  
   b. Profit Oil/Gas \- Remaining production split between state and contractor  
• Company books only their entitlement share of reserves  
• RAG IMPLICATION: Look for "cost recovery limit", "profit oil split" (e.g., "40/60 contractor/state")

3\. SERVICE CONTRACTS  
• Examples: Mexico (historically), Iran, Iraq  
• State owns everything; contractor paid fee per barrel or fixed payment  
• Contractor may not book reserves  
• RAG IMPLICATION: Less common in M\&A targets

KEY METRICS FOR RAG:

Government Take  
• % of project cash flow captured by state  
• Ranges globally: 40-85%  
• Higher government take \= Lower contractor NPV

Contractor Net Entitlement  
• In PSCs: Volumes/revenues contractor receives after cost recovery and profit split  
• This is what gets valued in M\&A

R-Factor (in some PSCs)  
• Cumulative Revenue ÷ Cumulative Costs  
• Used to trigger sliding profit splits (higher R-factor \= more favorable to state)

5\. Reserves & Resources Classification

Two main systems govern reserves reporting: PRMS (international standard) and SEC (US public companies)

PRMS (Petroleum Resources Management System)  
• Developed by SPE/AAPG/WPC/SPEE  
• Global industry standard  
• Classifies petroleum into: Reserves | Contingent Resources | Prospective Resources

SEC (Securities and Exchange Commission)  
• US regulatory standard for public company reporting  
• More conservative than PRMS  
• Focuses on "Proved Reserves" with "reasonable certainty"  
• Restrictions: 5-year rule for PUD conversion, pricing based on 12-month average

RESERVES HIERARCHY (from most certain to least):

1P (PROVED)  
• 90% confidence of commercial recovery  
• "Reasonable certainty" under existing conditions  
• Sub-categories:  
   \- PDP (Proved Developed Producing) \- Currently producing wells  
   \- PDNP (Proved Developed Non-Producing) \- Wells drilled but shut-in  
   \- PUD (Proved Undeveloped) \- Undrilled locations with committed development plan  
• RAG KEY: This is the "bankable" number \- lowest risk

2P (PROVED \+ PROBABLE)  
• 50% confidence  
• "More likely than not" to be recovered  
• Incremental probable reserves require additional drilling or better reservoir performance  
• RAG KEY: This is the "best estimate" used in most valuations

3P (PROVED \+ PROBABLE \+ POSSIBLE)  
• 10% confidence  
• Optimistic case  
• Requires favorable technical and commercial outcomes  
• RAG KEY: Upside scenario, high uncertainty

CONTINGENT RESOURCES (Not Reserves\!)  
• Discovered quantities that are NOT yet commercial  
• Awaiting: Technical studies, regulatory approval, infrastructure, price improvement  
• Sub-categories: 1C, 2C, 3C (similar confidence levels)  
• RAG KEY: If you see high contingent resources vs. reserves, development is speculative

PROSPECTIVE RESOURCES  
• Undiscovered, estimated volumes in undrilled prospects  
• Requires exploration drilling  
• High risk \- may be dry holes  
• RAG KEY: Pure exploration play, not factored into base valuations

WHY THIS MATTERS FOR RAG:

When your system parses a reserves report and sees:  
• "1P: 50 MMBOE, 2P: 100 MMBOE, 3P: 150 MMBOE"

Understand that:  
• The deal will likely price off 2P (100 MMBOE)  
• Lenders will only lend against 1P (50 MMBOE) \- "Reserves-Based Lending"  
• The upside is 3P (150 MMBOE) but highly uncertain  
• If PUD is \>40% of 1P, that's a red flag \- lots of future drilling capex required

6\. Critical VDR Documents & Their Contents

This section details the KEY document types your RAG system will encounter in upstream M\&A Virtual Data Rooms, what they contain, and how to extract value from them.

DOCUMENT TYPE 1: COMPETENT PERSON'S REPORT (CPR) / RESERVES AUDIT

Format: PDF (100-300 pages typically)  
Prepared by: Independent reserves evaluators (e.g., DeGolyer & MacNaughton, Gaffney Cline, SGS)  
Purpose: Independent assessment of reserves and resources for stock exchange listings, financing, or M\&A

KEY CONTENTS:  
• Executive Summary \- Total 1P/2P/3P reserves by field  
• Reserves tables \- Breakdown by field, well, product type (oil/gas/condensate)  
• Production profiles \- Historical and forecast production curves  
• Price assumptions \- Oil/gas price deck used (base/low/high cases)  
• Cost assumptions \- OPEX, CAPEX, abandonment costs  
• Fiscal terms \- Royalties, taxes, PSC mechanics  
• NPV calculations \- NPV10, NPV15 at different price scenarios  
• Decline curve analysis \- Mathematical models of production decline  
• Technical methodology \- Volumetric, decline curve, or simulation methods  
• Risk factors and uncertainties \- Technical, commercial, regulatory  
• Compliance statement \- PRMS or SEC compliance

RAG PARSING STRATEGY:  
• Extract reserves tables using table detection (often complex multi-level headers)  
• Identify field names as entities for cross-referencing with other documents  
• Parse NPV sensitivities (usually in matrix format: price vs. reserves category)  
• Flag red flags: High PUD %, aggressive price decks, optimistic decline rates  
• Chunk by field or section to enable granular retrieval

CRITICAL METADATA TO CAPTURE:  
• Report date and as-of date (reserves are time-sensitive)  
• Evaluator name (credibility indicator)  
• Compliance standard (PRMS vs. SEC)  
• Price deck effective date

DOCUMENT TYPE 2: ECONOMIC / FINANCIAL MODELS

Format: Excel (.xlsx) \- Often complex multi-tab workbooks  
Prepared by: Seller's internal team or financial advisors  
Purpose: Cash flow forecasting, NPV calculation, scenario analysis

KEY WORKSHEETS/TABS:  
• Assumptions \- Price decks, OPEX, CAPEX, fiscal parameters  
• Production Forecast \- Field-by-field or well-by-well production profiles  
• Revenue \- Gross revenue calculations (volumes × prices)  
• Operating Costs \- Fixed and variable OPEX by field  
• Capital Expenditure \- Development drilling, facilities, workovers  
• Fiscal Calculations \- Royalties, taxes, PSC cost recovery and profit split  
• Cash Flow Waterfall \- From gross revenue to net cash flow  
• NPV & Sensitivity \- Discount rate calculations, tornado charts  
• Debt Service \- If acquisition involves leverage

STRUCTURED DATA TO EXTRACT:  
• NPV at different discount rates and price scenarios  
• Production profiles by year (annual or monthly)  
• CAPEX schedule \- when and how much  
• Breakeven price \- Below which project has negative NPV  
• Peak production year and rate  
• Reserve life / tail production

RAG PARSING STRATEGY:  
• Use openpyxl or similar to read Excel structure  
• Detect table regions (not just A1:Z100 \- models have merged cells, gaps)  
• Identify "output" vs. "input" cells (formulas vs. hardcoded values)  
• Parse sensitivities \- usually 2D tables with row/column headers  
• Extract units (MMBOE, BOEPD, $MM) from headers or nearby cells  
• Link production profiles to reserves categories (PDP, PUD)

CHALLENGES:  
• Non-standard layouts \- Every company builds models differently  
• Hidden sheets and locked cells  
• Circular references and macro-enabled workbooks  
• Multiple scenarios in different columns or sheets

KEY INSIGHT FOR RAG:  
Your system should be able to answer: "What is the NPV10 at $70 Brent?" by finding the sensitivity table and reading the intersection. This requires structured data extraction, not just text embedding.

DOCUMENT TYPE 3: PRODUCTION DATA / WELL FILES

Format: Excel, PDF reports, or CSV exports from production databases  
Source: Operational databases, regulatory filings  
Purpose: Historical production performance, decline validation

KEY DATA ELEMENTS:  
• Monthly/Daily production by well (oil, gas, water rates)  
• Cumulative production to date  
• Well status (producing, shut-in, abandoned)  
• Downtime and interruptions  
• Pressure and temperature data

RAG VALUE:  
• Validate reserves engineer's decline assumptions against actuals  
• Identify underperforming wells or fields  
• Calculate current production rate (run-rate for valuation)

DOCUMENT TYPE 4: LICENSES, LEASES, CONCESSIONS

Format: PDF legal documents  
Issued by: Government authorities, regulatory agencies  
Purpose: Grant rights to explore/produce in specific geographic areas

KEY PROVISIONS:  
• License area (blocks, acreage)  
• Working interest ownership %  
• License term and expiry dates  
• Work commitments (seismic, drilling obligations)  
• Relinquishment requirements  
• Renewal or extension provisions  
• Government participating interest

RAG RED FLAGS TO DETECT:  
• License expiry within 2-3 years without renewal certainty  
• Unfulfilled work commitments that could trigger termination  
• Transfer/assignment restrictions

DOCUMENT TYPE 5: PRODUCTION SHARING CONTRACT (PSC)

Format: PDF legal contract (50-200 pages)  
Parties: State/NOC and Contractor(s)  
Purpose: Defines fiscal terms, cost recovery, profit split

CRITICAL CLAUSES FOR RAG:  
• Cost Recovery Cap \- e.g., "50% of gross production"  
• Profit Oil/Gas Split \- e.g., "40% contractor, 60% state" (may be sliding scale)  
• Allowable Costs \- What OPEX/CAPEX can be recovered  
• Depreciation rules \- Straight-line vs. declining balance  
• Ring-fencing \- Whether costs/profits are pooled across fields  
• Domestic Market Obligation (DMO) \- % sold locally at fixed price  
• Bonus payments \- Signature, discovery, production milestones  
• Tax provisions \- Who pays, at what rate  
• Decommissioning funding \- Security requirements

RAG PARSING APPROACH:  
• NER (Named Entity Recognition) for field names, block numbers, parties  
• Clause extraction for fiscal terms  
• Numerical extraction for percentages, caps, bonus amounts  
• Cross-reference with economic model to validate fiscal calculations

DOCUMENT TYPE 6: JOINT OPERATING AGREEMENT (JOA)

Format: PDF legal contract  
Parties: Multiple working interest owners in a license/field  
Purpose: Governs joint operations, cost-sharing, decision-making

KEY CLAUSES:  
• Operator designation and duties  
• Working interest percentages by party  
• Voting thresholds for major decisions (AFE approvals)  
• Cash calls and default provisions  
• Non-consent and penalty clauses (if partner doesn't fund)  
• Sole risk provisions (one partner funds alone, gets higher WI)  
• Transfer restrictions and preemption rights  
• Dispute resolution mechanisms

RAG IMPORTANCE:  
• Identifies who pays for what  
• Flags potential conflicts or constraints on operations  
• Important for understanding partnership dynamics

DOCUMENT TYPE 7: FINANCIAL STATEMENTS

Format: PDF (audited financials) or Excel  
Standard: IFRS or GAAP  
Purpose: Historical financial performance

KEY SECTIONS:  
• Balance Sheet \- Assets (including PP\&E for oil & gas assets), liabilities (debt, decommissioning provisions)  
• Income Statement \- Revenues, OPEX, depreciation, taxes  
• Cash Flow Statement \- Operating, investing, financing cash flows  
• Notes \- Accounting policies, reserves disclosure, commitments

RAG VALUE:  
• Validate production revenues against production data  
• Assess debt levels and financial health  
• Check decommissioning provisions vs. independent estimates

DOCUMENT TYPE 8: ESG / HSSE REPORTS

Format: PDF reports, data tables  
Content: Environmental, Social, Governance, Health, Safety, Security  
Purpose: Assess non-financial risks and compliance

KEY DATA:  
• Emissions (CO2, methane, flaring volumes)  
• Spills and environmental incidents  
• Safety statistics (TRIR, LTIF)  
• Regulatory violations and fines  
• Decommissioning cost estimates  
• Community relations and local content

RAG RED FLAGS:  
• Major incidents with unresolved remediation  
• Regulatory non-compliance  
• High carbon intensity vs. industry benchmarks  
• Large unfunded decommissioning liabilities

7\. Valuation Methodologies & Key Heuristics

Understanding how upstream assets are valued is critical for your RAG system to contextualize document content and detect red flags.

THREE VALUATION APPROACHES:

1\. INCOME APPROACH (DCF \- Discounted Cash Flow)  
• Most common for upstream assets  
• Values future net cash flows from reserves  
• Key formula: NPV \= Σ \[Cash Flowₜ / (1 \+ discount rate)^ₜ\]  
• Standard discount rates: 10% (NPV10), 15% (NPV15)  
• Sensitivities run on: Oil/gas prices, OPEX, CAPEX, production rates

KEY ASSUMPTIONS TO FLAG:  
• Price deck \- Brent/WTI/Henry Hub forward curves  
• Production profile \- Based on decline curves, type curves  
• Costs \- Lifting costs ($/BOE), development capex, abandonment  
• Fiscal terms \- Royalties, taxes, PSC profit splits

RED FLAGS FOR RAG:  
• Price deck \>20% above forward curve \= Aggressive  
• Decline rates \<10%/year for mature fields \= Optimistic  
• OPEX \<$8/BOE for offshore or\<$5 for onshore \= Questionable  
• No abandonment costs included \= Missing liability

2\. MARKET COMPARABLES (Trading Multiples)  
• Benchmarks against recent M\&A transactions or public company valuations  
• Key multiples:  
   \- EV/BOE (1P) \- Enterprise Value per barrel of Proved reserves  
   \- EV/BOE (2P) \- Usually lower $/BOE than 1P due to higher volumes  
   \- EV/BOEPD \- Enterprise Value per daily production  
   \- EV/EBITDAX \- Enterprise Value to EBITDA before exploration

TYPICAL RANGES (varies by basin, risk, oil vs. gas):  
• EV/1P BOE: $8-20/BOE (low for gas, high for oil, offshore premium)  
• EV/2P BOE: $5-15/BOE  
• EV/BOEPD: $30,000-80,000 per daily barrel

RAG USE CASE:  
When user asks "Is $500M a fair price for 50 MMBOE 2P?"  
Calculate: $500M ÷ 50 MMBOE \= $10/BOE  
Context: "This implies $10/2P BOE, which is mid-range for typical transactions. Need to consider: PDP%, basin, oil/gas mix, and fiscal regime."

3\. ASSET NAV (Net Asset Value)  
• Sum-of-parts valuation  
• Value each field/asset separately using DCF  
• Add non-core assets, subtract debt and decommissioning liabilities

KEY HEURISTICS FOR RAG:

• PDP vs. PUD Mix: \>60% PDP \= Low risk asset. \<40% PDP \= High development capex ahead  
• Reserve Life (R/P Ratio): 5-10 years typical. \<5 years \= Needs reserves replacement. \>15 years \= Long-tail, may include speculative reserves  
• Government Take: 40-50% \= Attractive fiscal regime. \>70% \= Challenging economics  
• Breakeven Price: If breakeven \>$50 Brent, asset is high-cost and vulnerable to price drops  
• Finding & Development Costs: \<$10/BOE \= Efficient. \>$20/BOE \= High-cost plays

9\. RAG Architecture for O\&G Due Diligence

This section provides technical architecture guidance for building a domain-primed RAG system for upstream M\&A.

CORE ARCHITECTURE: HYBRID RAG with DOMAIN CONTEXT \+ DEAL-SPECIFIC RETRIEVAL

LAYER 1: DOMAIN KNOWLEDGE BASE (Pre-loaded Context)

Purpose: Give the model "mental models" of how O\&G works BEFORE seeing any deal documents

Content:  
• Upstream VDR Playbook (the markdown file attached to this conversation)  
• Reserves evaluation methodologies (PRMS, SEC frameworks)  
• Fiscal regime templates (PSC mechanics, royalty/tax systems)  
• Valuation heuristics (typical NPV ranges, decline rates, cost benchmarks)  
• Due diligence checklists ("Golden Questions")

Storage:  
• Separate vector index OR  
• Include as system prompt context (if fits in context window) OR  
• Hybrid: Always-loaded markdown \+ chunked/embedded for retrieval

Retrieval Strategy:  
• When query is general ("What is 2P reserves?"), retrieve from domain KB  
• Use query classification to route: domain-only, deal-only, or hybrid

LAYER 2: VDR DOCUMENT CORPUS (Deal-Specific)

Ingestion Pipeline:

1\. CRAWL & CLASSIFY  
   • Recursive folder traversal of VDR export  
   • Capture folder path as metadata (e.g., "/Reserves\_Technical/CPR/")  
   • Classify document type: CPR, Economic Model, PSC, JOA, Financial Statements  
   • Store: file\_path, folder\_path, doc\_type, upload\_date

2\. PARSE & EXTRACT  
   • PDF: PyMuPDF, pdfplumber (with OCR fallback for scanned docs)  
   • Excel: openpyxl, pandas (structured extraction \- more below)  
   • Word/PPT: python-docx, python-pptx  
   • Email: extract from .msg or .eml formats

3\. CHUNK INTELLIGENTLY  
   • NOT fixed 500-token chunks  
   • Semantic chunking:  
      \- CPR: By field/section (Executive Summary, Field A reserves, Field B reserves)  
      \- PSC: By article/clause (Cost Recovery, Profit Split, Decommissioning)  
      \- Economic Model: By worksheet/table (Assumptions, NPV Summary, Sensitivities)  
   • Preserve hierarchical structure: Doc \> Section \> Subsection  
   • Use headers, table of contents, bold text as chunk boundaries

4\. METADATA ENRICHMENT  
   For each chunk, store:  
   • doc\_id, chunk\_id, doc\_type  
   • file\_path, folder\_path (for source tracing)  
   • page\_number, section\_title  
   • Entities: field\_names ("Field X", "Block Y"), dates, numerical values  
   • Structural tags: is\_table, is\_executive\_summary, is\_assumption

5\. EMBED & INDEX  
   • Embedding model: text-embedding-3-large OR local model (e.g., instructor-xl)  
   • Vector DB: ChromaDB, Qdrant, pgvector  
   • Store vectors \+ metadata \+ original text

LAYER 3: STRUCTURED DATA STORE (for Excel/Financial Data)

Problem: Vector search is poor at finding "NPV10 at $70 Brent \= $450M"  
Solution: Extract tables into structured format

Approach:  
• Parse Excel worksheets into pandas DataFrames  
• Detect table structure (headers, data rows, units)  
• Store in SQL or document DB with schema:  
   \- table\_id, doc\_id, worksheet\_name  
   \- column\_headers (list)  
   \- row\_headers (list)  
   \- data\_matrix (JSON)  
   \- units (e.g., "MMBOE", "$MM")  
• Enable SQL-style queries: "SELECT npv WHERE price=70 AND discount=10%"

Example Tools:  
• NPV Calculator: Extract NPV sensitivity tables, expose as queryable function  
• Production Profile Reader: Extract annual production forecasts  
• Reserves Summary: Extract 1P/2P/3P by field from CPR tables

QUERY PROCESSING FLOW:

1\. QUERY CLASSIFICATION  
   Input: User question  
   Output: Route to appropriate retrieval strategy  
     
   Types:  
   • General Domain Q: "What is 2P reserves?" → Domain KB only  
   • Deal-Specific Q: "What is the 2P for Field X?" → VDR corpus \+ structured data  
   • Hybrid Q: "Is Field X's decline rate reasonable?" → Both (compare deal data to benchmarks)  
   • Calculation Q: "What is NPV10 at $70 Brent?" → Structured data tool

2\. ENTITY EXTRACTION  
   • Identify: Field names, dates, numerical values, document types  
   • Example: "Field X" → Use as filter in vector search metadata  
   • Example: "$70 Brent" → Query price sensitivity table

3\. RETRIEVAL  
   • Hybrid search: Dense (semantic) \+ Sparse (BM25/keyword)  
   • Metadata filtering: doc\_type, field\_name, section  
   • Re-ranking: Cross-encoder for relevance  
   • Top-k chunks (k=5-10) \+ structured data results

4\. ANSWER GENERATION  
   Prompt structure:  
   \`\`\`  
   System: You are an expert upstream oil & gas analyst...  
     
   Domain Context: \[Pre-loaded playbook chunks\]  
     
   Deal Documents: \[Retrieved chunks with metadata\]  
     
   Structured Data: \[Table extracts, NPV calcs\]  
     
   User Question: \[Original query\]  
     
   Instructions:  
   \- Distinguish "general practice" vs. "this deal specifics"  
   \- Cite sources: \[CPR Report, p.15\] or \[Economic Model, NPV Sheet\]  
   \- Flag red flags if assumptions are aggressive  
   \- Admit uncertainty if data is missing  
   \`\`\`

5\. CITATION & TRACEABILITY  
   • Every claim must link back to: doc\_name, page\_number, section  
   • Example output: "2P reserves are 50 MMBOE \[CPR Report, p.8, Table 3\]"  
   • Enable user to click through to source document

KEY IMPLEMENTATION CHOICES:

Local-First Architecture (per your brief):  
• LLM: Llama 3.1 70B or Mistral Large (via Ollama/vLLM)  
• Embeddings: instructor-xl or BGE-large (local)  
• Vector DB: ChromaDB or Qdrant (self-hosted)  
• Orchestration: LangChain or LlamaIndex  
• Benefits: No API costs, data privacy, works offline  
• Tradeoff: Requires GPU infra, slower than GPT-4

Evaluation & Testing:  
• Golden Questions as Test Set  
   \- Curate 50-100 questions with expected answers  
   \- "What is the 2P reserves for the entire portfolio?"  
   \- "What is the cost recovery cap in the PSC?"  
   \- "What is the NPV10 at base case pricing?"  
• Metrics:  
   \- Retrieval: Recall@k, MRR (Mean Reciprocal Rank)  
   \- Generation: Human eval for correctness, citation accuracy  
   \- Red flag detection: Precision/Recall for identifying risks  
• Continuous refinement:  
   \- Log failed queries  
   \- Improve chunking, metadata, or domain playbook  
   \- Retrain embeddings on O\&G corpus if needed

10\. Document Parsing & Data Extraction Strategies

EXCEL PARSING CHALLENGES & SOLUTIONS:

Challenge 1: Non-Standard Layouts  
• Problem: Every company builds models differently \- no standard cell addresses  
• Solution: Heuristic detection  
   \- Scan for keywords: "NPV", "Reserves", "Production", "OPEX"  
   \- Look for table patterns: header row \+ data rows  
   \- Detect merged cells and multi-level headers  
   \- Use font/color/border formatting as hints

Challenge 2: Formula vs. Hardcoded Values  
• Problem: Need to know if cell is input (assumption) or output (calculation)  
• Solution: Use openpyxl to check if cell.value is formula  
   \- If formula: Output/calculated field  
   \- If value: Input/assumption (more important to extract)

Challenge 3: Units and Scales  
• Problem: Is "50" \= 50 BOE or 50 MMBOE? Makes 1,000,000x difference\!  
• Solution: Parse header rows and nearby text for unit indicators  
   \- Keywords: MM, MMM, thousands, millions, MMBOE, BOEPD, $/BBL  
   \- Store units with every extracted number

Challenge 4: Sensitivity Tables (2D lookups)  
• Problem: NPV varies by both price (columns) and reserves (rows)  
• Solution: Detect table structure  
   \- Identify row headers (left column)  
   \- Identify column headers (top row)  
   \- Extract data matrix  
   \- Enable queries: "Get NPV where price=$70 AND reserves=2P"

Sample Parsing Code Structure:  
\`\`\`python  
import openpyxl  
import pandas as pd

def parse\_npv\_sensitivity(workbook\_path, sheet\_name="NPV Summary"):  
    wb \= openpyxl.load\_workbook(workbook\_path)  
    ws \= wb\[sheet\_name\]  
      
    \# Scan for "NPV" keyword  
    npv\_cell \= find\_keyword(ws, "NPV")  
      
    \# Detect table region around keyword  
    table\_range \= detect\_table\_boundaries(ws, npv\_cell)  
      
    \# Extract to DataFrame  
    df \= extract\_table\_to\_df(ws, table\_range)  
      
    \# Detect units  
    units \= detect\_units(ws, table\_range)  
      
    return {  
        'table': df,  
        'units': units,  
        'metadata': {'sheet': sheet\_name, 'source': workbook\_path}  
    }  
\`\`\`

PDF TABLE EXTRACTION:

Tools:  
• pdfplumber \- Good for extracting tables from PDFs  
• camelot-py \- Specialized for tables  
• tabula-py \- Java-based, robust

Challenges:  
• Tables span multiple pages  
• Merged cells and irregular layouts  
• Scanned PDFs require OCR first (tesseract)

Best Practice:  
• Extract table as structured data (DataFrame)  
• Also keep original text chunk for vector search  
• Link: chunk\_id references table\_id in structured DB

11\. APPENDIX: Quick Reference Tables

TABLE A: RESERVES CLASSIFICATION QUICK REFERENCE

Category | Confidence | Definition | Use Case  
\-----------------------------------------------------  
1P (Proved) | 90% (P90) | Reasonable certainty of recovery | Lending base, conservative valuation  
2P (Proved+Probable) | 50% (P50) | More likely than not | M\&A pricing, management planning  
3P (Proved+Probable+Possible) | 10% (P10) | Optimistic case | Upside scenario, resource potential

PDP | \- | Producing wells | Highest value, no capex required  
PDNP | \- | Drilled, shut-in | Medium risk, minimal capex  
PUD | \- | Undrilled, committed plan | Requires development capex

Contingent Resources (1C/2C/3C) | \- | Not yet commercial | Awaiting FID, regulatory approval  
Prospective Resources | \- | Undiscovered | Exploration, high risk

TABLE B: VALUATION BENCHMARKS & RED FLAGS

Metric | Typical Range | Red Flag Threshold | Implication  
\-------------------------------------------------------------------------  
EV/1P BOE | $8-20/BOE | \>$25/BOE or \<$5/BOE | Too expensive or troubled asset  
EV/2P BOE | $5-15/BOE | \>$18/BOE | Aggressive pricing  
EV/BOEPD | $30k-80k/bbl/day | \<$20k | Poor quality reserves

PDP % of 1P | 50-70% | \<40% | High future capex  
R/P Ratio (years) | 5-15 years | \<3 years | Reserve replacement risk  
Decline Rate | 10-25%/year | \<8%/year (mature field) | Optimistic forecast  
OPEX | $5-15/BOE | \<$5 onshore, \<$8 offshore | Underestimated costs  
Government Take | 40-70% | \>75% | Unattractive fiscal regime

TABLE C: DOCUMENT TYPE MATRIX

Document Type | Format | Priority | Key Data to Extract | Parsing Complexity  
\--------------------------------------------------------------------------------------------  
CPR / Reserves Audit | PDF | CRITICAL | 1P/2P/3P by field, NPV10/15, price assumptions | HIGH (tables, charts)  
Economic Model | Excel | CRITICAL | NPV sensitivities, production profiles, costs | VERY HIGH (non-standard)  
Production Data | Excel/CSV | HIGH | Historical production, current rates | MEDIUM  
PSC | PDF | HIGH | Cost recovery cap, profit split, fiscal terms | HIGH (legal text)  
License/Lease | PDF | MEDIUM | Expiry dates, WI%, work commitments | MEDIUM  
JOA | PDF | MEDIUM | WI split, operator, voting thresholds | MEDIUM (legal text)  
Financial Statements | PDF | MEDIUM | Revenue, debt, decom provisions | LOW (standard format)  
ESG/HSSE Reports | PDF | MEDIUM | Emissions, incidents, violations | MEDIUM

TABLE D: KEY ACRONYMS CHEAT SHEET

Acronym | Full Term | Definition  
\-----------------------------------------------------------------------------  
BOE | Barrels of Oil Equivalent | Standard unit (1 barrel oil \= 6,000 cf gas)  
MMBOE | Million Barrels of Oil Equivalent | Large volume measurement  
BOEPD | Barrels of Oil Equivalent Per Day | Production rate  
WI | Working Interest | Ownership % before royalties  
NRI | Net Revenue Interest | Ownership % after royalties  
NPV10 | Net Present Value at 10% | Standard DCF valuation metric  
PSC | Production Sharing Contract | Fiscal system where state owns resources  
JOA | Joint Operating Agreement | Partnership agreement between WI owners  
CPR | Competent Person's Report | Independent reserves audit  
AFE | Authorization for Expenditure | Approval for capital spending  
PRMS | Petroleum Resources Management System | SPE reserves classification standard  
EUR | Estimated Ultimate Recovery | Total hydrocarbons from a well  
R/P | Reserves-to-Production | Reserve life in years  
OPEX | Operating Expenditure | Lifting costs  
CAPEX | Capital Expenditure | Development drilling, facilities

FINAL RECOMMENDATIONS FOR TECHNICAL CO-FOUNDER:

1\. START SIMPLE: Build basic PDF \+ Excel ingestion first, test on sample VDR  
2\. ITERATE ON CHUNKING: Get domain playbook retrieval working before complex structured data  
3\. BUILD GOLDEN QUESTIONS: Create test set with expected answers  
4\. FOCUS ON CITATIONS: Traceability is critical \- users must trust the source  
5\. LOCAL DEPLOYMENT: Prioritize data privacy and offline capability  
6\. MEASURE & IMPROVE: Log failed queries, refine chunking and metadata

