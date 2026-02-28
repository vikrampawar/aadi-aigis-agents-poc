# aigis-agents

Architecture-agnostic AI agents for upstream oil & gas M&A due diligence.

Part of the Aigis Analytics platform. Each agent is a standalone Python function
callable from any orchestration framework (LangGraph, AutoGen, notebook, CLI).

---

## Agents

| # | Agent | Status |
|---|-------|--------|
| 01 | VDR Document Inventory & Gap Analyst | ✅ Complete |
| 02 | Production Data Collator → SQL | Planned |
| 03 | Internal Consistency Auditor | Planned |
| 04 | Upstream Finance Calculator | Planned |
| 05 | Commodity Price Forward Curve Fetcher | Planned |

---

## Quick Start

### Install

```bash
cd aigis-agents
uv sync
```

### Run Agent 01 via CLI

```bash
python -m aigis_agents.agent_01_vdr_inventory \
  --deal-id "your-deal-uuid" \
  --deal-type producing_asset \
  --jurisdiction GoM \
  --vdr-path /path/to/vdr/folder \
  --deal-name "Project Corsair" \
  --buyer "Your Company" \
  --output-dir ./outputs
```

### Call from Python

```python
from aigis_agents import vdr_inventory_agent

result = vdr_inventory_agent(
    deal_id="00000000-0000-0000-0000-c005a1000001",
    deal_type="producing_asset",
    jurisdiction="GoM",
    vdr_path="/path/to/corsair_vdr",
    use_db=True,                          # also query aigis-poc PostgreSQL
    model_key="gpt-4o-mini",
    deal_name="Project Corsair",
    buyer_name="Aigis Test Buyer",
    output_dir="./outputs",
)

print(result["status"])                        # "success"
print(result["findings"]["missing_nth"])       # number of critical missing docs
print(result["outputs"]["drl_docx"])           # path to the Word document
```

### Review Self-Learning Proposals

After running the agent, novel documents found in the VDR are proposed for checklist addition:

```bash
python -m aigis_agents.agent_01_vdr_inventory.accept_proposals --checklist v1.0
```

Follow the interactive prompts to accept (Y) or reject (N) each proposal.
Accepted items are merged into the next checklist version (v1.0 → v1.1).

---

## Outputs (per run)

All files written to `{output_dir}/{deal_id}/01_vdr_inventory/`:

| File | Description |
|------|-------------|
| `01_vdr_inventory.json` | Full file tree with metadata and classification |
| `01_gap_analysis_report.md` | ✅/⚠️/❌ per checklist item + self-learning proposals |
| `01_data_request_list.docx` | Professional email-ready DRL |

---

## Checklist Configuration

The gold-standard checklist lives in `checklists/gold_standard_v1.json`.

It covers 13 categories with ~80 items, each with:
- NTH/GTH tier per deal type (producing_asset, exploration, development, corporate)
- Jurisdiction-specific notes (GoM, UKCS, Norway)
- Search keywords for hybrid matching
- Pre-written DRL request text

To add items manually: edit the JSON. To evolve it via self-learning: use the `accept_proposals` CLI.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required for LLM classification |
| `ANTHROPIC_API_KEY` | — | Optional (for claude-* models) |
| `POSTGRES_HOST` | localhost | aigis-poc PostgreSQL host |
| `POSTGRES_PORT` | 5433 | aigis-poc PostgreSQL port |
| `POSTGRES_PASSWORD` | aigis | aigis-poc PostgreSQL password |

---

## Integration with aigis-poc

When `worker/` is on `PYTHONPATH`, the agent automatically reuses:
- `worker/src/llm.py` — full 17-model registry + cost estimation
- `worker/src/db.py` — database connection
- `worker/src/ingestion/classify.py` — LLM document classification

This avoids duplicating model configuration. Without `worker/` on path, the agent
falls back to direct LangChain instantiation using environment variables.
