# Aigis Intelligence Layer — Specification v1.0
## 01 Mar 2026 | Status: Approved

---

## Context

The Aigis agent mesh has 9 self-learning mechanisms but three critical gaps identified in the
`aigis-self-learning-improvements.md` analysis:

1. **DK Router is tag-only** — misses domain knowledge buried in unexpected document types
   (OpCom slides, JV partner notes, management presentations). No semantic search; no
   cross-document contradiction detection.
2. **No shared deal state** — each agent independently re-reads documents. No accumulating
   picture of the deal that persists across agents and pipeline runs.
3. **No buyer model** — the system has zero knowledge of who the acquirer is, what their
   strategy is, or what thresholds/preferences they hold. Every run treats the buyer as unknown.

These improvements are inspired partly by the **cognee** cognitive memory system (hybrid
vector+graph, cross-document proposition linking, contradiction detection).

**Design decisions confirmed:**
- Embedding model: Provider-agnostic (same pattern as `main_model`/`audit_model` — user-selectable)
- Vector store: `sqlite-vec` (zero-infra; integrates with Agent 02's existing SQLite per-deal DB)
- Graph layer: Full hybrid — vectors + lightweight concept graph in SQLite
- DealContext update strategy: Agent-owned sections + append-only run log

---

## Overview — Three Improvements

| # | Name | What it solves | Priority |
|---|------|----------------|----------|
| 1 | **Buyer Profile Layer** | Acquirer preferences, thresholds, strategy completely unknown | Highest — immediate value, smallest footprint |
| 2 | **DealContext.md Shared State** | No accumulating deal picture; agents re-derive same facts | High — enables downstream agents to be faster/smarter |
| 3 | **Semantic DK Router + Concept Graph + Hidden DK Detector** | DK retrieval too narrow; no cross-document contradiction detection | High — infrastructure for future agents |

Implementation phases mirror this priority order: Phase A → Phase B → Phase C → Phase D.

---

## Improvement 1 — Buyer Profile Layer

### Problem

Every analysis is buyer-agnostic. Agents don't know:
- Who the acquirer is or their strategic rationale
- What financial thresholds they apply (min IRR, max LOE/BOE, hurdle rate)
- What price deck they use ($60 flat? Strip?)
- Portfolio state (existing GoM ops? Desired basin?)
- Negotiation preferences (cash deals only? CVR appetite?)

### Solution

A persistent `buyer_profile.md` file + `BuyerProfileManager` class. Two learning pathways:
- **Q&A pathway** — CLI wizard (20 targeted questions) run once to populate the profile
- **Feedback pathway** — during any pipeline run, if the audit layer detects a preference signal
  in user input ("use $60 flat"), it prompts "Remember this preference?" and appends to profile
  if confirmed

### File: `aigis_agents/mesh/buyer_profile_manager.py`

```python
@dataclass
class PreferenceSignal:
    category: str          # "price_deck" | "financial_threshold" | "operational" | "strategic" | "negotiation"
    key: str               # e.g. "oil_price_deck"
    value: str             # e.g. "$60/bbl flat"
    raw_text: str          # verbatim user text that triggered detection
    confidence: float      # 0.0–1.0

class BuyerProfileManager:
    def __init__(self, profile_path: str): ...
    def load_as_context(self) -> str: ...           # full markdown for LLM system prompt injection
    def load_as_dict(self) -> dict: ...             # structured dict for programmatic use
    def update_section(self, section_name: str, content: str) -> None: ...
    def append_learning_log_entry(self, date: str, source: str, preference: str) -> None: ...
    def run_qa_wizard(self) -> None: ...            # CLI interactive Q&A
    def apply_signal(self, signal: PreferenceSignal) -> None: ...  # after human confirms
```

### `buyer_profile.md` Structure (8 sections)

```markdown
# Buyer Profile — [Buyer Name]
*Last updated: YYYY-MM-DD | Version: N*

## 1. Investment Thesis
[Buyer's stated rationale — basin focus, asset type, integration strategy]

## 2. Financial Thresholds
- Minimum unlevered IRR: ____%
- Maximum LOE/BOE: $____/BOE
- Maximum G&A/BOE: $____/BOE
- Hurdle rate (discount rate): ____%
- Maximum ARO exposure: $____mm
- Minimum PDP PV10 coverage ratio: ____×

## 3. Operational Capabilities
- Existing GoM operations: Yes/No
- Operated vs non-operated preference: ____
- Subsea experience: Yes/No
- Maximum WI tolerance on single asset: ____%
- Preferred asset size (BOE/d net): ____

## 4. Price Preferences
- Oil price deck: ____ (e.g. "$65/bbl flat" or "strip")
- Gas price deck: ____ (e.g. "$3.00 flat" or "strip")
- Escalation assumption: ____

## 5. Strategic Premiums
- Will pay premium for: [operatorship / basin consolidation / infrastructure / exploration upside]
- CVR appetite: Yes/No; max CVR as % of bid: ____%
- Non-price factors: ____

## 6. Portfolio State
- Current GoM production (BOE/d net): ____
- Current 2P reserves (MMBoe net): ____
- Existing infrastructure overlap with target: ____

## 7. Negotiation Preferences
- Preferred deal structure: [cash / seller finance / earnout / CVR]
- Max time to close: ____ months
- Key deal-breakers: ____

## 8. Learning Log
| Date | Source | Preference Learned |
|------|--------|--------------------|
```

### Q&A Question List (`BUYER_QA_QUESTIONS`)

20 questions covering all 8 sections:
1. "What is your company's name and how would you describe your investment thesis for GoM assets?"
2. "What is your company's minimum acceptable unlevered IRR for a producing GoM asset?"
3. "What hurdle / discount rate does your company use for DCF valuations?"
4. "What is the maximum LOE/BOE threshold above which a deal is uneconomic for you?"
5. "What is the maximum G&A/BOE your company can absorb in a standalone acquisition?"
6. "Does your company have a maximum ARO exposure threshold per deal?"
7. "What minimum PDP NPV10 coverage ratio (EV/PDP NPV10) do you target?"
8. "What oil price deck does your company use for acquisitions? (e.g. strip, $60 flat, $65 flat)"
9. "What gas price deck does your company use? (e.g. $3.00 flat, strip)"
10. "Does your company currently operate any GoM assets?"
11. "Do you prefer operated or non-operated positions, or no preference?"
12. "Does your company have subsea operations experience (ROV, umbilicals, FPS)?"
13. "What is the maximum working interest (%) your company would consider on a single GoM asset?"
14. "What is your target asset size range in net BOE/d production?"
15. "What strategic premiums would your company pay? (operatorship, basin consolidation, infra, exploration)"
16. "Will your company consider a CVR structure? If so, what maximum % of the bid price?"
17. "What is your current net GoM production (BOE/d) and 2P reserves (MMBoe)?"
18. "Do you have any existing infrastructure overlap or synergies with GoM shelf/deepwater assets?"
19. "What is your preferred deal structure? (all cash, seller finance, earnout, CVR)"
20. "What is the maximum months-to-close your company can accommodate for a GoM transaction?"

### "Remember this?" Flow (in `agent_base.py`)

Add step 9.5 between output audit (step 9) and log to trail (step 10):

```python
# agent_base.py — step 9.5
if mode == "standalone":
    signals = audit_layer.detect_preferences(inputs, raw_output)
    for signal in signals:
        if signal.confidence >= 0.75:
            confirm = input(
                f"\n[Buyer Profile] Detected preference: '{signal.value}' for '{signal.key}'.\n"
                f"Remember this for future runs? [y/N]: "
            )
            if confirm.strip().lower() == "y":
                self._buyer_profile.apply_signal(signal)
```

### `detect_preferences()` (in `audit_layer.py`)

Audit LLM scans `inputs` dict and `result` dict for signals. Patterns detected:
- Price overrides: "use $XX/bbl", "flat price of", "strip pricing"
- Threshold signals: "minimum IRR of", "hurdle rate", "can't exceed $XX/BOE"
- Strategic signals: "we want operatorship", "interested in exploration upside"

Returns `list[PreferenceSignal]`, filtered to `confidence >= 0.5` only.

### Integration into `AgentBase.invoke()`

- `BuyerProfileManager` instantiated once in `AgentBase.__init__`
- Profile injected into every agent's system prompt as `buyer_context` alongside `dk_context`
- Agents reference `buyer_context` when making recommendations, sizing bids, flagging red flags
  vs buyer thresholds

### Implementation Steps — Phase A (Weeks 1–3)

| Step | File | Action |
|------|------|--------|
| A1 | `aigis_agents/mesh/buyer_profile_manager.py` | `BuyerProfileManager`, `PreferenceSignal`, `run_qa_wizard()` |
| A2 | `aigis_agents/memory/buyer_profile.md` | Template file (blank sections) |
| A3 | `aigis_agents/mesh/audit_layer.py` | Add `detect_preferences()` method |
| A4 | `aigis_agents/mesh/agent_base.py` | Inject `buyer_context` into prompt; add step 9.5 "remember this?" |
| A5 | `aigis_agents/mesh/__init__.py` | Export `BuyerProfileManager` |
| A6 | CLI entry: `python -m aigis_agents init-buyer-profile` | Runs `run_qa_wizard()` |
| A7 | Tests: `tests/test_buyer_profile.py` | Wizard, signal detection, profile update, context injection |
| A8 | Update `MEMORY.md` | Add buyer_profile path + description |

---

## Improvement 2 — DealContext.md Shared Pipeline State

### Problem

Agents run independently. If Agent 01 identifies that the CPR is from NSAI using PRMS methodology
with an effective date of 1 Jan 2024, Agent 04 will re-derive that from scratch. No agent builds
on another's findings. The deal picture resets every run.

### Solution

A per-deal `deal_context.md` file that accumulates findings across pipeline runs. Each agent owns
named sections within it. A run log appended after every pipeline run captures key flags and
findings. Agents load this at start of run and use it as prior knowledge.

### File: `aigis_agents/mesh/deal_context.py`

```python
@dataclass
class DealContextSection:
    agent_id: str
    section_name: str
    content: str
    updated_at: str
    run_id: str

class DealContextManager:
    def __init__(self, deal_id: str, memory_root: str): ...
    def load(self) -> str: ...                                         # full markdown for LLM
    def update_section(self, section: DealContextSection) -> None:    # agent writes its section
    def append_run_log(self, agent_id: str, run_id: str,
                       flags: list[str], summary: str) -> None: ...   # append-only
    def get_summary(self, max_tokens: int = 800) -> str: ...          # compressed summary
    def get_section(self, agent_id: str, section_name: str) -> str | None: ...
```

### `deal_context.md` Template

```markdown
# Deal Context — {deal_name}
*Deal ID: {deal_id} | Created: {date} | Last updated: {date}*

---

## Agent 01 — VDR Inventory Summary
*Updated: {timestamp} | Run: {run_id}*
[Agent 01 writes: VDR structure, document count, completeness score, key gaps, critical docs found]

## Agent 02 — Data Store Summary
*Updated: {timestamp} | Run: {run_id}*
[Agent 02 writes: data points ingested, cases found, key financial metrics extracted, conflicts detected]

## Agent 04 — Financial Analysis Summary
*Updated: {timestamp} | Run: {run_id}*
[Agent 04 writes: NPV10 by case, IRR, key sensitivities, recommended bid range, red flags]

---

## Run Log (append-only)
| Timestamp | Agent | Run ID | Key Flags | Summary |
|-----------|-------|--------|-----------|---------|
```

### Agent Integration Pattern

In each agent's `_run()` return dict, add `_deal_context_section` key:

```python
return {
    "npv_10": ...,
    # ...existing output keys...
    "_deal_context_section": {
        "section_name": "Financial Analysis Summary",
        "content": f"NPV10 (Management): ${npv_mgmt}mm | IRR: {irr}% | Bid: ${bid_lo}–${bid_hi}mm"
    }
}
```

`AgentBase.invoke()` detects `_deal_context_section` in result and calls
`DealContextManager.update_section()` automatically (step 10.5, after memory/run log save).

### Temporal Pattern Weighting

Patterns in `learned_patterns.json` gain temporal weight labels:

```python
def get_weight(pattern: dict) -> str:
    days_since_confirm = (now - last_confirmed_date).days
    if days_since_confirm < 90 and confirmation_count >= 2:
        return "HIGH"
    elif days_since_confirm < 365:
        return "MEDIUM"
    else:
        return "STALE"
```

`MemoryManager.load_patterns()` returns patterns sorted HIGH→MEDIUM; STALE patterns excluded
from system prompt injection by default.

### Implementation Steps — Phase B (Weeks 3–6)

| Step | File | Action |
|------|------|--------|
| B1 | `aigis_agents/mesh/deal_context.py` | `DealContextManager`, `DealContextSection` |
| B2 | `aigis_agents/mesh/agent_base.py` | Instantiate `DealContextManager`; add step 10.5; load `deal_context` into system prompt |
| B3 | `aigis_agents/mesh/memory_manager.py` | Add temporal weighting to `load_patterns()` |
| B4 | `aigis_agents/agent_01_vdr_inventory/agent.py` | Return `_deal_context_section` |
| B5 | `aigis_agents/agent_02_data_store/agent.py` | Return `_deal_context_section` |
| B6 | `aigis_agents/agent_04_finance_calculator/agent.py` | Return `_deal_context_section` |
| B7 | Tests: `tests/test_deal_context.py` | Section update, run log append, get_summary, cross-agent accumulation |
| B8 | Update `MEMORY.md` | Add `{deal_id}/deal_context.md` path to output convention |

**Storage path:** `aigis_agents/memory/{deal_id}/deal_context.md`

---

## Improvement 3 — Semantic DK Router + Concept Graph + Hidden DK Detector

### Problem

The current `DomainKnowledgeRouter` is tag-only: each agent declares `DK_TAGS`, router loads
matching markdown files. This misses:
- Relevant DK buried in "unexpected" document types (fiscal terms in management presentations,
  HSE benchmarks in OpCom slides)
- Cross-document contradictions (IM says production is 5,000 BOE/d; CPR says 3,800 BOE/d)
- Richer relational understanding (e.g. "Na Kika FPS" → linked to "subsea tie-back",
  "lease expiry", "ARO obligation")

### Sub-component 3a — Embedding-Based Semantic Search

Provider-agnostic embedding with `sqlite-vec` vector store. Chunk all DK files + VDR documents
at ingestion; allow semantic search at query time.

**New files:**

**`aigis_agents/mesh/embeddings.py`**
```python
class EmbeddingProvider:
    """Supports: "openai/text-embedding-3-small", "voyage/voyage-3", "local/all-MiniLM-L6-v2" """
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def embed_one(self, text: str) -> list[float]: ...

    @staticmethod
    def from_config(embedding_model: str, api_keys: dict) -> "EmbeddingProvider": ...
```

**`aigis_agents/mesh/vector_store.py`**
```python
@dataclass
class VectorHit:
    chunk_id: str; score: float
    metadata: dict    # source_file, chunk_index, text_preview, doc_type, deal_id

class VectorStore:
    """sqlite-vec backed. One DB per deal (reuses Agent 02's 02_data_store.db path)."""
    def upsert(self, chunk_id: str, vector: list[float], metadata: dict) -> None: ...
    def search(self, query_vector: list[float], top_k: int = 8) -> list[VectorHit]: ...
```

**SQLite schema** (added to `02_data_store.db`):
```sql
CREATE VIRTUAL TABLE vec_chunks USING vec0(
    chunk_id TEXT PRIMARY KEY,
    embedding float[{dim}]
);
CREATE TABLE chunk_metadata (
    chunk_id TEXT PRIMARY KEY, source_file TEXT NOT NULL,
    chunk_index INT NOT NULL, text TEXT NOT NULL,
    doc_type TEXT,   -- "dk" | "vdr_doc" | "deal_context"
    deal_id TEXT, created_at TEXT NOT NULL
);
```

**`aigis_agents/mesh/semantic_dk_router.py`** — Two-phase retrieval wrapping `domain_knowledge.py`:
- Phase 1 (fast): tag-based file loading (existing, session-cached)
- Phase 2 (semantic): embed query → search `vec_chunks` → return top-k chunks
Results merged; duplicates deduped by source_file.

### Sub-component 3b — Concept Graph (SQLite)

**`aigis_agents/mesh/concept_graph.py`**

```python
class ConceptGraph:
    def add_node(self, name, node_type, description, deal_id) -> str: ...
    def add_edge(self, source_id, target_id, relationship, weight, source_doc) -> None: ...
    def add_proposition(self, subject, predicate, object_, source_doc, deal_id, page_ref) -> None: ...
    def find_contradictions(self, proposition: str, deal_id: str) -> list[Contradiction]: ...
    def get_entity_context(self, entity_name: str, deal_id: str) -> str: ...
```

**SQLite schema** (added to `02_data_store.db`):
```sql
CREATE TABLE concept_nodes (
    node_id TEXT PRIMARY KEY, name TEXT NOT NULL,
    node_type TEXT NOT NULL,  -- entity | metric | concept | event | risk
    description TEXT DEFAULT '', deal_id TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE concept_edges (
    edge_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES concept_nodes(node_id),
    target_id TEXT NOT NULL REFERENCES concept_nodes(node_id),
    relationship TEXT NOT NULL, weight REAL DEFAULT 1.0,
    source_doc TEXT, deal_id TEXT, created_at TEXT NOT NULL
);
CREATE TABLE propositions (
    prop_id TEXT PRIMARY KEY, subject TEXT NOT NULL,
    predicate TEXT NOT NULL, object TEXT NOT NULL,
    source_doc TEXT NOT NULL, deal_id TEXT NOT NULL,
    page_ref TEXT, confidence TEXT DEFAULT 'HIGH', created_at TEXT NOT NULL
);
```

### Sub-component 3c — Hidden DK Detector

**`aigis_agents/mesh/hidden_dk_detector.py`**

Two jobs:
1. **Hidden DK Discovery** — scan non-standard VDR files for domain-knowledge-relevant content;
   suggest additions to DK files (always requires human confirmation in Phase C/D).
2. **Proposition Contradiction Detection** — after any new document ingested, scan new propositions
   against existing ones using `ConceptGraph.find_contradictions()`. Surface CRITICAL contradictions
   to the audit log + human review queue.

### New Dependencies

| Package | Purpose |
|---------|---------|
| `sqlite-vec` | Vector similarity search in SQLite |
| `openai` | OpenAI embeddings (likely already present) |
| `voyageai` | Voyage embeddings (optional) |
| `sentence-transformers` | Local embeddings (optional) |

### Implementation Steps — Phase C (Weeks 6–12)

| Step | File | Action |
|------|------|--------|
| C1 | `aigis_agents/mesh/embeddings.py` | `EmbeddingProvider` + provider dispatch |
| C2 | `aigis_agents/mesh/vector_store.py` | `VectorStore` with sqlite-vec |
| C3 | `aigis_agents/agent_02_data_store/db_manager.py` | Add `vec_chunks` + `chunk_metadata` tables |
| C4 | `aigis_agents/mesh/semantic_dk_router.py` | Two-phase retrieval |
| C5 | `aigis_agents/mesh/agent_base.py` | Replace `DomainKnowledgeRouter` with `SemanticDKRouter` |
| C6 | CLI: `python -m aigis_agents index-dk` | Index all DK files once |
| C7 | Tests: `tests/test_semantic_dk.py` | Embedding, vector store, router |
| C8 | `pyproject.toml` | Add `sqlite-vec` optional dependency |

### Implementation Steps — Phase D (Weeks 12–20)

| Step | File | Action |
|------|------|--------|
| D1 | `aigis_agents/mesh/concept_graph.py` | `ConceptGraph`, nodes/edges/propositions |
| D2 | `aigis_agents/agent_02_data_store/db_manager.py` | Add concept tables |
| D3 | `aigis_agents/mesh/entity_extractor.py` | LLM entity+proposition extraction |
| D4 | `aigis_agents/agent_02_data_store/agent.py` | Call `entity_extractor` in `ingest_file` |
| D5 | `aigis_agents/mesh/hidden_dk_detector.py` | `HiddenDKDetector` |
| D6 | `aigis_agents/mesh/agent_base.py` | Inject entity context from concept graph |
| D7 | `aigis_agents/mesh/audit_layer.py` | Add contradiction check post-ingestion |
| D8 | Tests: `tests/test_concept_graph.py`, `tests/test_hidden_dk.py` | All functionality |

---

## File Structure — Summary of Changes

```
aigis_agents/
├── mesh/
│   ├── agent_base.py              MODIFY (A4, B2, C5, D6) — buyer_context; deal_context; semantic router; entity graph
│   ├── audit_layer.py             MODIFY (A3, D7) — add detect_preferences(); contradiction check
│   ├── memory_manager.py          MODIFY (B3) — temporal pattern weighting
│   ├── domain_knowledge.py        KEEP — semantic router wraps, does not replace
│   ├── buyer_profile_manager.py   NEW (A1)
│   ├── deal_context.py            NEW (B1)
│   ├── semantic_dk_router.py      NEW (C4)
│   ├── embeddings.py              NEW (C1)
│   ├── vector_store.py            NEW (C2)
│   ├── concept_graph.py           NEW (D1)
│   ├── entity_extractor.py        NEW (D3)
│   └── hidden_dk_detector.py      NEW (D5)
├── memory/
│   ├── buyer_profile.md           NEW (A2) — global, not per-deal
│   └── {deal_id}/
│       └── deal_context.md        NEW (B) — per-deal, accumulating
└── agent_02_data_store/
    └── db_manager.py              MODIFY (C3, D2) — vec_chunks, concept tables
```

---

## Summary Roadmap

| Phase | Weeks | Deliverable |
|-------|-------|-------------|
| A | 1–3 | Buyer Profile Layer (`buyer_profile_manager.py`, `buyer_profile.md`, `audit_layer.py` updates) |
| B | 3–6 | DealContext Shared State (`deal_context.py`, `agent_base.py` step 10.5, temporal weighting) |
| C | 6–12 | Semantic DK Router (`embeddings.py`, `vector_store.py`, `semantic_dk_router.py`, sqlite-vec) |
| D | 12–20 | Concept Graph + Hidden DK (`concept_graph.py`, `entity_extractor.py`, `hidden_dk_detector.py`) |

---

## Verification Checklist

**Phase A:**
- `python -m aigis_agents init-buyer-profile` → Q&A wizard completes; `buyer_profile.md` populated
- Run any agent in standalone mode → audit log contains `buyer_context` injection confirmation
- Pass "use $65 flat" in agent inputs → "Remember this?" prompt appears; profile updates on confirm

**Phase B:**
- Run Agent 01 on a VDR → `deal_context.md` created at `memory/{deal_id}/deal_context.md`
- Run Agent 04 on same deal → Agent 04 section updates without overwriting Agent 01 section
- Run same agent twice → run log has two rows; first row preserved

**Phase C:**
- `python -m aigis_agents index-dk` → `vec_chunks` table populated in `02_data_store.db`
- Run Agent 04 with DK query → semantic search retrieves chunk not matched by tag alone
- Different embedding models (openai/voyage/local) all resolve via `EmbeddingProvider.from_config()`

**Phase D:**
- Ingest two documents with conflicting production figures → `data_conflicts` table entry
  AND `find_contradictions()` returns the contradiction
- Run `hidden_dk_detector` on a management presentation → DK-relevant content flagged for review

---

*Spec v1.0 — 01 Mar 2026*
*All changes additive. No existing agents removed or broken.*
