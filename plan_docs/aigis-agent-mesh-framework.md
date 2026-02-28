# Aigis Agent Mesh — Architecture Framework Spec
**Version:** 1.1 | **Date:** 28 Feb 2026 | **Status:** Approved
**Author:** Aaditya Chintalapati

---

## Context & Objectives

Agent 01 (VDR Inventory) and Agent 04 (Finance Calculator) exist as standalone tools. The goal is to convert the full Aigis suite into a **true agent mesh** — where every agent is composable, domain-aware, self-auditing, and memory-persistent. This spec defines the framework all future agents will be built on top of.

The spec covers five requirements:
1. **Agent Toolkit Registry** — live reference file for all agents
2. **Domain Knowledge Integration** — every agent draws on the `domain_knowledge/` repo (cached per session)
3. **Dual Output Modes** — human-readable MD vs structured JSON per invocation type
4. **Dual-LLM Quality Layer** — configurable main LLM + cheaper audit LLM per agent
5. **Persistent Memory + Human-Reviewed Improvement Loop** — agents learn, others suggest, humans approve, approval rate tracked toward future auto-apply option

---

## Design Principles

| # | Principle | Meaning |
|---|-----------|---------|
| 1 | **Stack-agnostic** | Agents are logical units with typed I/O. No vendor lock-in. Implementable on any orchestration framework. |
| 2 | **Composable** | Every agent is a registered callable tool. Any agent can call any other. |
| 3 | **Human-in-the-loop** | All 🔴 Critical findings require analyst acknowledgement before downstream use. All improvement suggestions require human review (auto-apply is a future opt-in). |
| 4 | **Citation-mandatory** | Every extracted fact carries: source doc, section, page, verbatim quote, confidence. |
| 5 | **Free-first data sources** | Free public APIs are primary; paid upgrades noted where material. |
| 6 | **Dual-mode output** | Standalone call → human-readable MD. Tool-call → compact JSON. Same agent, same logic. |
| 7 | **Dual-LLM per agent** | Main LLM: user-selectable, handles core reasoning. Audit LLM: cheaper model, handles input/output quality checks. Both API-key configurable at invocation time. |
| 8 | **Memory-persistent** | Agents accumulate learned patterns across deals. Other agents can file improvement suggestions. All suggestions are human-reviewed; approval history is tracked and can unlock auto-apply. |
| 9 | **Domain-grounded** | Each agent loads only the domain knowledge files tagged as relevant to its task. DK is cached for the session duration. |
| 10 | **Transparent workings** | Every calculation, extraction, and classification shows its reasoning, formula, and source. |

---

## Mesh Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AIGIS AGENT MESH                            │
│                                                                       │
│  ┌──────────────┐   ┌────────────────────┐   ┌───────────────────┐  │
│  │  toolkit.    │   │  domain_knowledge/ │   │  memory/          │  │
│  │  json        │   │  (session-cached)  │   │  (per-agent +     │  │
│  │  (Registry)  │   │  DK Router         │   │   global)         │  │
│  └──────┬───────┘   └──────────┬─────────┘   └────────┬──────────┘  │
│         │                      │                        │             │
│  ┌──────▼──────────────────────▼────────────────────────▼─────────┐  │
│  │                         AgentBase                                │  │
│  │  invoke(mode, deal_id, main_model, main_api_key,                │  │
│  │          audit_model, audit_api_key, **inputs)                  │  │
│  │                                                                  │  │
│  │  ┌──────────────────┐        ┌───────────────────────────────┐  │  │
│  │  │  Main LLM        │        │  Audit LLM (cheaper)          │  │  │
│  │  │  (user-selected) │        │  ┌─────────────┐              │  │  │
│  │  │  Core reasoning  │        │  │ Input Audit │              │  │  │
│  │  │  Classification  │        │  │ runs BEFORE │              │  │  │
│  │  │  Extraction      │        │  └─────────────┘              │  │  │
│  │  │  Generation      │        │  ┌──────────────┐             │  │  │
│  │  └──────────────────┘        │  │ Output Audit │             │  │  │
│  │                              │  │ runs AFTER   │             │  │  │
│  │                              │  └──────────────┘             │  │  │
│  │                              └───────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │ Agent 01 │  │ Agent 02 │  │ Agent 04 │  │ Agent 06 │  ...      │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Agent Toolkit Registry (`toolkit.json`)

### Location
`aigis_agents/toolkit.json` — tracked in git, updated on every new agent merge. CI check validates schema on PR.

### Schema (per agent entry)

```json
{
  "version": "1.1",
  "last_updated": "2026-02-28",
  "agents": {
    "agent_01": {
      "id": "agent_01",
      "name": "VDR Document Inventory & Gap Analyst",
      "description": "Enumerates VDR contents, scores against gold-standard checklist, generates Data Request List.",
      "status": "production",
      "agent_version": "1.2",
      "module_path": "aigis_agents.agent_01_vdr_inventory.agent",
      "llm_defaults": {
        "main_model": "gpt-4.1",
        "audit_model": "gpt-4.1-mini"
      },
      "input_params": {
        "deal_id":       {"type": "str",  "required": true,  "description": "UUID for the deal"},
        "deal_type":     {"type": "str",  "required": true,  "enum": ["producing_asset", "exploration", "development", "corporate"]},
        "jurisdiction":  {"type": "str",  "required": true,  "enum": ["GoM", "UKCS", "Norway", "International"]},
        "vdr_path":      {"type": "str",  "required": false, "description": "Local folder path to VDR files"},
        "output_dir":    {"type": "str",  "required": false, "default": "./outputs"},
        "main_model":    {"type": "str",  "required": false, "default": "gpt-4.1",      "description": "LLM for core agent logic"},
        "main_api_key":  {"type": "str",  "required": false, "description": "API key for main model (falls back to env var)"},
        "audit_model":   {"type": "str",  "required": false, "default": "gpt-4.1-mini", "description": "LLM for quality auditing"},
        "audit_api_key": {"type": "str",  "required": false, "description": "API key for audit model (falls back to env var)"}
      },
      "output": {
        "standalone": {
          "files": ["01_vdr_inventory.json", "01_gap_analysis_report.md", "01_data_request_list.docx"],
          "summary_keys": ["total_files", "coverage_score", "critical_missing_count"]
        },
        "tool_call": {
          "schema": {
            "status": "str",
            "coverage_score": "float",
            "present": "list[str]",
            "missing_nth": "list[str]",
            "missing_gth": "list[str]",
            "citations": "list[Citation]"
          }
        }
      },
      "dependencies": {
        "agents": [],
        "domain_knowledge_tags": ["vdr_structure", "checklist", "upstream_dd"],
        "external_apis": []
      },
      "memory_keys": ["learned_classifications", "checklist_proposals", "novel_doc_types"]
    }
  }
}
```

### Key conventions
- `status`: `"production"` | `"beta"` | `"planned"` | `"deprecated"`
- All agents listed even if `status = "planned"` — immediately discoverable by the mesh and Agent 06 (Q&A)
- `llm_defaults.main_model` and `llm_defaults.audit_model` are the fallbacks when not provided at invocation time
- API keys checked in order: invocation param → environment variable → descriptive error

---

## Component 2: Domain Knowledge Router (Session-Cached)

### Design
Each agent declares `domain_knowledge_tags` in its toolkit entry. The DK Router maps tags to file paths, loads the matching files **once per session**, and serves them from memory on subsequent calls. A `refresh_dk=True` param forces reload.

### Tag → File Mapping

| Tag | File(s) Loaded |
|-----|---------------|
| `vdr_structure` | `domain_knowledge/DD_Process/PART4_VDR_Workflow_Agent_Mapping.md` |
| `checklist` | `domain_knowledge/DD_Process/PART1_Header_Taxonomy_Phases.md` |
| `upstream_dd` | `domain_knowledge/upstream_vdr_playbook.md` |
| `financial` | `domain_knowledge/financial_analyst_playbook.md`, `domain_knowledge/fiscal_terms_playbook.md` |
| `technical` | `domain_knowledge/technical_analyst_playbook.md` |
| `legal` | `domain_knowledge/legal_analyst_playbook.md` |
| `esg` | `domain_knowledge/esg_analyst_playbook.md` |
| `golden_questions` | `domain_knowledge/golden_question_checklist.md` |
| `dd_process_full` | All 5 `DD_Process/PART*.md` files |
| `oil_gas_101` | `domain_knowledge/Upstream Oil & Gas 101*.md` |

### Interface

```python
class DomainKnowledgeRouter:
    """Session-scoped singleton. Loads each file once; serves from cache thereafter."""

    _cache: dict[str, str] = {}   # class-level: filename → content, lives for process lifetime

    def load(self, tags: list[str], refresh: bool = False) -> dict[str, str]:
        """Returns {filename: content} for tags. Uses cache unless refresh=True."""

    def build_context_block(self, tags: list[str], refresh: bool = False) -> str:
        """Returns formatted string ready for LLM prompt injection."""
```

### Usage in Agent

```python
class Agent01(AgentBase):
    DK_TAGS = ["vdr_structure", "checklist", "upstream_dd"]

    def _run(self, dk_context: str, ...):
        # dk_context is pre-built by AgentBase.invoke() and passed in
        # inject into classification + gap-scoring prompts
        prompt = CLASSIFY_PROMPT.format(dk_context=dk_context, ...)
```

---

## Component 3: Dual Output Mode Contract

### Invocation Signature (all agents)

```python
result = agent.invoke(
    mode="standalone",          # or "tool_call"
    deal_id="...",
    main_model="gpt-4.1",       # optional — falls back to toolkit default
    main_api_key="sk-...",      # optional — falls back to env var
    audit_model="gpt-4.1-mini", # optional — falls back to toolkit default
    audit_api_key="sk-...",     # optional — falls back to env var
    refresh_dk=False,           # set True to force domain knowledge reload
    **agent_specific_inputs
)
```

### Mode: `standalone` (direct analyst call)

**Triggers:** CLI call (default mode); notebook or script use by an analyst.

**Behaviour:**
- Writes full output files to `{output_dir}/{deal_id}/`
- Prints structured progress to stdout
- Returns summary dict with file paths and audit score

**Output file header format:**
```markdown
# Agent 01: VDR Document Inventory & Gap Analyst
**Deal:** Project Corsair | **Deal ID:** 00000000-0000-0000-0000-c005a1000001
**Run Date:** 2026-02-28 14:32 UTC | **Run ID:** a1b2c3d4
**Main Model:** gpt-4.1 | **Audit Model:** gpt-4.1-mini
**Audit Score:** 94/100 | **Agent Version:** 1.2

---
## Executive Summary
[3–5 sentence plain-English summary of findings]

## Key Metrics
| Metric | Value |
...

## Findings
[Full structured output with citations]

## Confidence & Caveats
[Audit layer output, unresolved flags, quality score]
```

### Mode: `tool_call` (called by another agent)

**Triggers:** Called programmatically via `AgentBase.call_agent("agent_01", mode="tool_call", ...)`.

**Behaviour:**
- No file writes, no stdout output
- Audit still runs; results embedded in response
- Returns compact, typed JSON immediately

```json
{
  "agent": "agent_01",
  "status": "success",
  "deal_id": "...",
  "run_id": "a1b2c3d4",
  "data": {
    "coverage_score": 0.42,
    "present": ["Corporate/Ownership Structure", "JOA Main Agreement"],
    "missing_nth": ["Competent Person Report", "Audited Accounts (3yr)"],
    "missing_gth": ["Insurance Policy Schedule"]
  },
  "citations": [
    {
      "fact": "JOA Amendment 2023 found in Commercial folder",
      "source_doc": "JOA_Amendment_2023.pdf",
      "source_section": "Commercial/Legal",
      "confidence": "HIGH"
    }
  ],
  "audit": {
    "input_valid": true,
    "output_confidence": "HIGH",
    "output_score": 91,
    "flags": [],
    "main_model": "gpt-4.1",
    "audit_model": "gpt-4.1-mini"
  },
  "run_metadata": {
    "duration_s": 23.4,
    "main_llm_cost_usd": 0.038,
    "audit_llm_cost_usd": 0.004,
    "total_cost_usd": 0.042
  }
}
```

### Error Response (both modes)

```json
{
  "agent": "agent_01",
  "status": "error",
  "error_type": "input_validation_failed" | "execution_error" | "output_audit_failed",
  "message": "...",
  "details": { "issues": [...] }
}
```

---

## Component 4: Dual-LLM Quality Layer

### Two LLMs, Two Roles

Every agent run uses two separate LLM instances:

| Role | Default Model | Controlled By | Purpose |
|------|--------------|---------------|---------|
| **Main LLM** | `gpt-4.1` | `main_model` + `main_api_key` params | Core reasoning — classification, extraction, generation, analysis |
| **Audit LLM** | `gpt-4.1-mini` | `audit_model` + `audit_api_key` params | Input/output quality checking — simpler structured prompts, lower cost |

Main and audit model costs are tracked separately and reported in every run's output.

### API Key Resolution Order (applied to both LLMs independently)

```
1. Explicit param at invocation  (main_api_key / audit_api_key)
2. Environment variable           (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
3. Raise descriptive error       — never silently fail or share keys across providers
```

The existing `shared/llm_bridge.py` handles resolution; no changes needed.

### Two-Stage Audit Flow

```
  inputs
    │
    ▼
┌───────────────────────────────────────┐
│  INPUT AUDITOR  (Audit LLM)           │
│  Checks: completeness, plausibility,  │
│  unit consistency, purpose fit        │
└───────────────┬───────────────────────┘
                │ valid=true → proceed
                │ valid=false → return error immediately
                ▼
┌───────────────────────────────────────┐
│  AGENT CORE LOGIC  (Main LLM)         │
│  Classification / Extraction /        │
│  Calculation / Generation             │
└───────────────┬───────────────────────┘
                │ raw outputs
                ▼
┌───────────────────────────────────────┐
│  OUTPUT AUDITOR  (Audit LLM)          │
│  Checks: citations, consistency,      │
│  missed red flags, value ranges       │
│  → queues improvement suggestions     │
└───────────────┬───────────────────────┘
                │
                ▼
        formatted output (mode-dependent)
        appended to {deal_id}/_audit_log.jsonl
```

### Input Auditor Prompt

```
You are the Input Quality Auditor for {agent_name}.
Agent purpose: {agent_description}
Domain: Upstream oil & gas M&A due diligence

Inputs received:
{inputs_json}

Review for:
1. COMPLETENESS — all required parameters present and non-null?
2. PLAUSIBILITY — values within reasonable ranges for upstream O&G?
   (production rates, prices, discount rates, WI percentages, etc.)
3. PURPOSE ALIGNMENT — does this invocation make sense for this agent?
4. UNIT CONSISTENCY — flag likely mismatches (bopd vs Mbbl/month, etc.)

Return ONLY valid JSON:
{
  "valid": true|false,
  "confidence": "HIGH"|"MEDIUM"|"LOW",
  "issues": [
    {"field": "field_name", "severity": "ERROR"|"WARNING", "message": "..."}
  ],
  "notes": "..."
}
```

**Behaviour:** Any `ERROR` severity → agent aborts, returns error response. `WARNING` → agent runs, warnings appended to output.

### Output Auditor Prompt

```
You are the Output Quality Auditor for {agent_name}.
Agent purpose: {agent_description}

Inputs summary: {inputs_summary}
Outputs produced: {outputs_summary}

Audit for:
1. CITATION COMPLETENESS — every extracted fact has source_doc, section, page, confidence?
2. INTERNAL CONSISTENCY — outputs internally consistent? Conclusions follow from data?
3. RED FLAG COVERAGE — any obvious risks missed given domain context?
4. REASONABLENESS — values within expected ranges for this asset type/jurisdiction?
5. IMPROVEMENT SUGGESTIONS — what concrete changes would improve future runs?

Return ONLY valid JSON:
{
  "confidence_score": 0-100,
  "confidence_label": "HIGH"|"MEDIUM"|"LOW",
  "citation_coverage": 0.0-1.0,
  "flags": [
    {
      "type": "missing_citation"|"inconsistency"|"missed_red_flag"|"out_of_range",
      "severity": "CRITICAL"|"WARNING"|"INFO",
      "detail": "..."
    }
  ],
  "improvement_suggestions": [
    {
      "target_agent": "agent_01",
      "suggestion": "...",
      "confidence": 0.0-1.0
    }
  ],
  "auditor_notes": "..."
}
```

**Behaviour:** `confidence_score < 60` → output flagged, human review required before downstream use. Any `CRITICAL` flag → HITL gate triggered.

### Audit Log Format

Appended to `{deal_id}/_audit_log.jsonl` (one JSON record per line):

```json
{
  "run_id": "a1b2c3d4",
  "agent": "agent_01",
  "timestamp": "2026-02-28T14:32:11Z",
  "mode": "standalone",
  "main_model": "gpt-4.1",
  "audit_model": "gpt-4.1-mini",
  "input_audit": {"valid": true, "issues": [], "confidence": "HIGH"},
  "output_audit": {
    "confidence_score": 94,
    "flags": [],
    "improvement_suggestions": [],
    "citation_coverage": 1.0
  },
  "cost": {
    "main_llm_usd": 0.038,
    "audit_llm_usd": 0.004,
    "total_usd": 0.042
  }
}
```

---

## Component 5: Persistent Memory + Human-Reviewed Improvement Loop

### Per-Agent Memory Structure

```
aigis_agents/
└── agent_01_vdr_inventory/
    └── memory/
        ├── learned_patterns.json       # Confirmed classification/extraction patterns
        ├── improvement_history.json    # All suggestions ever filed + human review outcomes
        └── run_history.json            # Performance log across deals and time
```

### Memory File Schemas

**learned_patterns.json** (Agent 01 example):
```json
{
  "version": "1.0",
  "last_updated": "2026-02-28",
  "patterns": [
    {
      "pattern_id": "p001",
      "trigger_keywords": ["shareholder loan", "intercompany", "affiliated party"],
      "classification": "Financial/Intercompany",
      "checklist_item": "Shareholder Loan Agreements",
      "confidence": "HIGH",
      "confirmed_deals": ["Project Corsair"],
      "source": "human_approved_suggestion",
      "added_date": "2026-01-15"
    }
  ]
}
```

**improvement_history.json** — permanent record of every suggestion + its human review outcome:
```json
{
  "auto_apply_enabled": false,
  "auto_apply_threshold": null,
  "approval_stats": {
    "total_suggestions": 12,
    "approved_as_suggested": 9,
    "approved_with_modifications": 2,
    "rejected": 1,
    "pending": 0,
    "approval_rate": 0.917
  },
  "suggestions": [
    {
      "suggestion_id": "s001",
      "from_agent": "agent_03",
      "to_agent": "agent_01",
      "deal_id": "00000000-0000-0000-0000-c005a1000001",
      "run_id": "a1b2c3d4",
      "submitted_date": "2026-02-28T14:32:11Z",
      "suggestion": "Agent 01 classified 'LOS_Q3_2025.xlsx' as Financial/Operating. Agent 03 found it contains production data inconsistent with that classification. Suggest adding 'LOS' keyword to Production category.",
      "audit_confidence": 0.87,
      "status": "approved_as_suggested",
      "reviewed_by": "Aaditya",
      "review_date": "2026-03-01T09:15:00Z",
      "review_notes": "Correct — LOS = Lease Operating Statement, always production context."
    }
  ]
}
```

**run_history.json**:
```json
{
  "runs": [
    {
      "run_id": "a1b2c3d4",
      "deal_id": "...",
      "timestamp": "2026-02-28T14:32:11Z",
      "file_count": 312,
      "coverage_score": 0.42,
      "audit_score": 94,
      "duration_s": 23.4,
      "total_cost_usd": 0.042,
      "main_model": "gpt-4.1",
      "audit_model": "gpt-4.1-mini"
    }
  ]
}
```

### Global Memory (Cross-Agent Pending Queue)

```
aigis_agents/memory/
└── cross_agent_suggestions.json   # Pending suggestions across all agents, awaiting review
```

Same schema as `improvement_history.json.suggestions[]` but contains only pending items. When a suggestion is resolved, it moves to the target agent's `improvement_history.json`.

### Auto-Apply Opt-In (Future Capability — Inert at Launch)

`auto_apply_enabled` and `auto_apply_threshold` fields are present in `improvement_history.json` from day one, but set to `false` and `null`. The system continuously tracks `approval_rate = approved_as_suggested / total_reviewed`.

**Unlock trigger:** When `approval_rate >= 0.80` AND `total_suggestions >= 10` for a given agent, the memory review CLI surfaces the following prompt:

```
═══════════════════════════════════════════════════════════════
  Agent 01 — Improvement Suggestion Review Stats
  Total reviewed: 12  |  Approval rate: 91.7% (11/12)
  ───────────────────────────────────────────────────────────
  Your approval rate is consistently high. You can now enable
  auto-application of suggestions above a confidence threshold.

  [Y] Enable auto-apply at default threshold (0.85 confidence)
  [C] Set a custom confidence threshold
  [N] Keep manual review for all suggestions (current setting)
═══════════════════════════════════════════════════════════════
```

If enabled: `auto_apply_enabled: true`, `auto_apply_threshold: 0.85` written to file. Suggestions above threshold are applied without human review but logged as `status: "auto_applied"` for full traceability. User can disable at any time.

### Memory Manager Interface

```python
class MemoryManager:
    # Patterns
    def load_patterns(self, agent_id: str) -> list[dict]: ...
    def save_pattern(self, agent_id: str, pattern: dict) -> None: ...

    # Run logging
    def log_run(self, agent_id: str, run_record: dict) -> None: ...

    # Suggestion lifecycle
    def queue_suggestion(self, suggestion: dict) -> str: ...           # returns suggestion_id
    def get_pending(self, agent_id: str | None = None) -> list[dict]: ...
    def approve(self, suggestion_id: str, notes: str = "", modified: bool = False) -> None: ...
    def reject(self, suggestion_id: str, notes: str = "") -> None: ...

    # Auto-apply management
    def get_approval_stats(self, agent_id: str) -> dict: ...
    def check_auto_apply_eligibility(self, agent_id: str) -> bool: ...
    def enable_auto_apply(self, agent_id: str, threshold: float) -> None: ...
    def disable_auto_apply(self, agent_id: str) -> None: ...
```

### Memory Review CLI

```bash
# List all pending suggestions across all agents
python -m aigis_agents.mesh.review_memory --list

# Filter by specific agent
python -m aigis_agents.mesh.review_memory --list --agent agent_01

# Interactive review of a specific suggestion
python -m aigis_agents.mesh.review_memory --review s001

# Approval statistics + auto-apply eligibility check
python -m aigis_agents.mesh.review_memory --stats

# Enable / disable auto-apply
python -m aigis_agents.mesh.review_memory --enable-auto-apply agent_01 --threshold 0.85
python -m aigis_agents.mesh.review_memory --disable-auto-apply agent_01
```

---

## AgentBase Class Interface

All agents inherit from `AgentBase`. Subclasses implement only `_run()` and declare `AGENT_ID` and `DK_TAGS`:

```python
class AgentBase:
    AGENT_ID: str                    # e.g. "agent_01" — declared in each subclass
    DK_TAGS: list[str] = []         # domain knowledge tags — declared in each subclass

    def __init__(self):
        self.toolkit = ToolkitRegistry.load()
        self.dk_router = DomainKnowledgeRouter()   # session-scoped singleton
        self.memory = MemoryManager()

    def invoke(
        self,
        mode: str,                          # "standalone" | "tool_call"
        deal_id: str,
        main_model: str | None = None,      # falls back to toolkit default
        main_api_key: str | None = None,    # falls back to env var
        audit_model: str | None = None,     # falls back to toolkit default
        audit_api_key: str | None = None,   # falls back to env var
        refresh_dk: bool = False,
        **inputs
    ) -> dict:
        # 1. Resolve models from params → toolkit defaults
        defaults = self.toolkit["agents"][self.AGENT_ID]["llm_defaults"]
        _main_model  = main_model  or defaults["main_model"]
        _audit_model = audit_model or defaults["audit_model"]

        # 2. Instantiate both LLMs
        main_llm  = get_chat_model(_main_model,  session_keys={"API_KEY": main_api_key})
        audit_llm = get_chat_model(_audit_model, session_keys={"API_KEY": audit_api_key})
        audit_layer = AuditLayer(audit_llm)

        # 3. Input audit (Audit LLM)
        input_result = audit_layer.check_inputs(self.AGENT_ID, inputs)
        if not input_result["valid"]:
            return self._error_response("input_validation_failed", input_result)

        # 4. Load domain knowledge (session-cached; refresh if requested)
        dk_context = self.dk_router.build_context_block(self.DK_TAGS, refresh=refresh_dk)

        # 5. Load agent memory
        patterns = self.memory.load_patterns(self.AGENT_ID)

        # 6. Core logic (Main LLM — implemented by subclass)
        raw_output = self._run(
            deal_id=deal_id, main_llm=main_llm,
            dk_context=dk_context, patterns=patterns, **inputs
        )

        # 7. Output audit (Audit LLM)
        output_result = audit_layer.check_outputs(self.AGENT_ID, inputs, raw_output)

        # 8. Queue improvement suggestions for human review
        for s in output_result.get("improvement_suggestions", []):
            s.update({"from_agent": self.AGENT_ID, "deal_id": deal_id})
            self.memory.queue_suggestion(s)

        # 9. Log to deal audit trail
        audit_layer.log(self.AGENT_ID, deal_id, mode, inputs,
                        input_result, output_result, _main_model, _audit_model)

        # 10. Format and return by mode
        return self._format_output(mode, deal_id, raw_output, output_result)

    def _run(self, deal_id: str, main_llm, dk_context: str,
             patterns: list, **inputs) -> dict:
        """Override in each subclass — core business logic."""
        raise NotImplementedError

    def call_agent(self, agent_id: str, deal_id: str,
                   main_model: str | None = None, **inputs) -> dict:
        """Call another agent in tool_call mode."""
        agent_cls = ToolkitRegistry.get_agent_class(agent_id)
        return agent_cls().invoke(mode="tool_call", deal_id=deal_id,
                                  main_model=main_model, **inputs)
```

---

## File Structure

### New additions to the repo

```
aigis_agents/
├── toolkit.json                          # NEW — agent registry (all agents, incl. planned)
├── mesh/                                 # NEW — mesh infrastructure
│   ├── __init__.py
│   ├── agent_base.py                     # AgentBase class
│   ├── audit_layer.py                    # Dual-LLM input/output auditors + log writer
│   ├── domain_knowledge.py              # Session-cached DK Router
│   ├── memory_manager.py                # JSON-backed memory + auto-apply logic
│   ├── toolkit_registry.py             # Loads toolkit.json; resolves agent classes
│   └── review_memory.py                # CLI for reviewing suggestions + auto-apply mgmt
├── memory/                               # NEW — cross-agent pending suggestion queue
│   └── cross_agent_suggestions.json
├── agent_01_vdr_inventory/
│   ├── memory/                           # NEW — agent-specific persistent memory
│   │   ├── learned_patterns.json
│   │   ├── improvement_history.json
│   │   └── run_history.json
│   └── ... (all existing files unchanged)
├── agent_04_finance_calculator/
│   ├── memory/                           # NEW
│   │   ├── learned_patterns.json
│   │   ├── improvement_history.json
│   │   └── run_history.json
│   └── ... (all existing files unchanged)
└── shared/
    ├── llm_bridge.py                     # EXISTING — no changes needed
    └── db_bridge.py                      # EXISTING — no changes needed
```

### Unchanged
- `domain_knowledge/` — no changes; correctly structured
- All agent-internal logic files — no changes until respective migration phase

---

## Migration Plan for Existing Agents

### Phase 1 — Infrastructure Only (~3 days, zero risk)
1. Create `aigis_agents/mesh/` with all six modules
2. Create `aigis_agents/toolkit.json` (agents 01 + 04 as `production`, all planned agents as `planned`)
3. Create memory directory stubs (empty JSON files with correct schema) for agents 01 + 04
4. **No changes to existing agent code** — agents continue to work exactly as before

### Phase 2 — Agent 04 Migration (~2 days)
Agent 04 is simpler (pure math; Main LLM used only for sensitivity narrative generation).
1. Subclass `AgentBase` in `agent_04/agent.py`; declare `AGENT_ID = "agent_04"` and `DK_TAGS = ["financial", "oil_gas_101"]`
2. Move core calculation logic into `_run()`; thread `main_llm` through for narrative steps
3. Implement dual-mode output: standalone writes MD/JSON files; tool_call returns compact JSON
4. Test: existing CLI invocation unchanged; `mode="tool_call"` returns correct JSON schema

### Phase 3 — Agent 01 Migration (~3 days)
Agent 01 is more complex (LLM already embedded throughout pipeline).
1. Subclass `AgentBase` in `agent_01/agent.py`; declare `AGENT_ID = "agent_01"` and `DK_TAGS`
2. Move core logic into `_run()`; replace internal `get_chat_model()` calls with passed-in `main_llm`
3. Inject `dk_context` into classification + gap-scoring prompts
4. Wire `novelty_detector.py` output → `memory.queue_suggestion()` (existing self-learning now uses the mesh suggestion pipeline)
5. Test: existing CLI unchanged; tool-call mode works; audit layer fires and logs correctly

### Phase 4 — All New Agents
Start from `AgentBase` by default. No migration step needed.

---

## Implementation Sequence

| Step | Deliverable | Depends On |
|------|------------|-----------|
| 1 | `toolkit.json` scaffold | Nothing |
| 2 | `mesh/toolkit_registry.py` | Step 1 |
| 3 | `mesh/domain_knowledge.py` (session-cached DK Router) | Nothing |
| 4 | `mesh/memory_manager.py` (JSON + auto-apply) | Nothing |
| 5 | `mesh/audit_layer.py` (dual-LLM auditors + log) | `shared/llm_bridge.py` |
| 6 | `mesh/agent_base.py` | Steps 2–5 |
| 7 | `mesh/review_memory.py` (CLI) | Step 4 |
| 8 | Memory stubs for agents 01 + 04 | Step 4 |
| 9 | Agent 04 migrated to AgentBase | Step 6 |
| 10 | Agent 01 migrated to AgentBase | Step 6 |

---

## Resolved Design Decisions

| # | Question | Decision |
|---|----------|---------|
| 1 | **Audit model selection** | Two configurable LLMs per agent: `main_model` (user-selectable at invocation, default `gpt-4.1`) for core reasoning; `audit_model` (cheaper, default `gpt-4.1-mini`) for quality checks. Each has its own API key resolution chain. Costs tracked separately. |
| 2 | **Memory storage backend** | JSON files — portable, zero infra. `MemoryManager` is a clean interface so the swap to SQLite is a single-file change when agent count warrants it. |
| 3 | **Improvement review gate** | Always human review. All suggestions and outcomes logged to `improvement_history.json`. When `approval_rate ≥ 0.80` and `n ≥ 10` reviews, the CLI surfaces an optional auto-apply toggle at a user-defined confidence threshold. Auto-applied items are logged as `status: "auto_applied"` — full audit trail always maintained. |
| 4 | **Domain knowledge caching** | Session-cached in `DomainKnowledgeRouter._cache` (class-level dict, lives for the process lifetime). `refresh_dk=True` param forces reload at any point. |

---

*Aigis Analytics — Confidential | v1.1 | 28 Feb 2026*
