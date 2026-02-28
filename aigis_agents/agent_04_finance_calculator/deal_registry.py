"""
Cross-deal registry for Agent 04 — Finance Calculator.

Stores headline financial metrics per deal/run in deals_registry_04.json.
Enables cross-deal benchmarking and run tracking.
Same pattern as Agent 01's deal_registry.py.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from aigis_agents.agent_04_finance_calculator.models import (
    AgentRegistry,
    AgentRegistryStats,
    DealRecord,
    FinancialAnalysisSummary,
    FinancialInputs,
    RunRecord,
)

REGISTRY_FILENAME = "deals_registry_04.json"


# ── I/O ───────────────────────────────────────────────────────────────────────

def load_registry(output_dir: Path) -> AgentRegistry:
    """Load deals_registry_04.json. Returns empty registry if absent."""
    path = Path(output_dir) / REGISTRY_FILENAME
    if not path.exists():
        return AgentRegistry()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return AgentRegistry(**data)


def _save_registry(registry: AgentRegistry, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    registry.generated_at = datetime.now(timezone.utc).isoformat()
    path = output_dir / REGISTRY_FILENAME
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry.model_dump(), f, indent=2)


# ── Run Record ────────────────────────────────────────────────────────────────

def _compute_inputs_hash(inputs: FinancialInputs) -> str:
    """MD5 hash of serialised inputs — used to detect changed assumptions vs same run."""
    serialised = json.dumps(inputs.model_dump(), sort_keys=True, default=str)
    return hashlib.md5(serialised.encode()).hexdigest()[:12]


def _build_run_record(
    inputs: FinancialInputs,
    summary: FinancialAnalysisSummary,
    cost_usd: float,
) -> RunRecord:
    return RunRecord(
        run_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        inputs_hash=_compute_inputs_hash(inputs),
        headline_metrics=summary,
        cost_usd=cost_usd,
        flag_count_critical=summary.flag_count_critical,
    )


# ── Main Entry Point ──────────────────────────────────────────────────────────

def register_run(
    inputs: FinancialInputs,
    summary: FinancialAnalysisSummary,
    output_dir: Path,
    cost_usd: float = 0.0,
) -> None:
    """
    Register a completed Finance Calculator run in deals_registry_04.json.

    - First run for a deal_id: creates new DealRecord
    - Repeat run: appends RunRecord (metrics history visible in --list-deals)
    - Always updates agent-level aggregate stats
    """
    output_dir = Path(output_dir)
    registry = load_registry(output_dir)

    curr_run = _build_run_record(inputs, summary, cost_usd)
    now_ts = curr_run.timestamp

    deal = registry.get_deal(inputs.deal_id)

    if deal is None:
        deal = DealRecord(
            deal_id=inputs.deal_id,
            deal_name=inputs.deal_name,
            deal_type=inputs.deal_type.value,
            jurisdiction=inputs.jurisdiction.value,
            buyer=inputs.buyer,
            first_run_timestamp=now_ts,
            last_run_timestamp=now_ts,
            run_count=1,
            runs=[curr_run],
        )
        registry.deals.append(deal)
    else:
        deal.runs.append(curr_run)
        deal.run_count += 1
        deal.last_run_timestamp = now_ts
        deal.deal_name = inputs.deal_name  # allow name update

    # Recalculate agent-level stats
    all_runs = [run for d in registry.deals for run in d.runs]
    timestamps = sorted(r.timestamp for r in all_runs)
    registry.agent_stats = AgentRegistryStats(
        total_deals=len(registry.deals),
        total_runs=len(all_runs),
        first_run_timestamp=timestamps[0] if timestamps else None,
        last_run_timestamp=timestamps[-1] if timestamps else None,
    )

    _save_registry(registry, output_dir)
