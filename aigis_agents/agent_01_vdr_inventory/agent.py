"""
Agent 01 — VDR Document Inventory & Gap Analyst
Entry point: vdr_inventory_agent()

Architecture-agnostic: callable from any framework (LangGraph, AutoGen,
standalone script, notebook, FastAPI endpoint).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from aigis_agents.agent_01_vdr_inventory.checklist_manager import (
    add_proposals,
    load_checklist,
)
from aigis_agents.agent_01_vdr_inventory.crawler import (
    crawl_db,
    crawl_filesystem,
    crawl_vdr_export,
    merge_sources,
)
from aigis_agents.agent_01_vdr_inventory.deal_registry import register_run
from aigis_agents.agent_01_vdr_inventory.drl_generator import generate_drl
from aigis_agents.agent_01_vdr_inventory.gap_scorer import score_checklist
from aigis_agents.agent_01_vdr_inventory.matcher import batch_classify
from aigis_agents.agent_01_vdr_inventory.models import (
    AgentOutputPaths,
    AgentResult,
)
from aigis_agents.agent_01_vdr_inventory.novelty_detector import detect_novel_documents
from aigis_agents.agent_01_vdr_inventory.report_generator import generate_gap_report
from aigis_agents.shared.llm_bridge import estimate_cost, get_chat_model
from aigis_agents.agent_01_vdr_inventory.primer import (
    apply_primer_updates,
    load_primer,
    propose_primer_updates,
    save_primer,
)


def vdr_inventory_agent(
    deal_id: str,
    deal_type: Literal["producing_asset", "exploration", "development", "corporate"],
    jurisdiction: Literal["GoM", "UKCS", "Norway", "International"],
    vdr_path: str | Path | None = None,
    vdr_export_csv: str | Path | None = None,
    use_db: bool = True,
    db_connection_string: str | None = None,
    model_key: str = "gpt-4o-mini",
    session_keys: dict[str, str] | None = None,
    output_dir: str | Path = ".",
    checklist_version: str = "v1.0",
    deal_name: str | None = None,
    buyer_name: str | None = None,
    round_number: int = 1,
) -> dict[str, Any]:
    """
    VDR Document Inventory & Gap Analyst.

    Crawls the VDR (filesystem / DB / export CSV), classifies every document
    against a gold-standard checklist, produces gap analysis and a professional
    Data Request List.

    Args:
        deal_id:              Unique deal identifier (used for output folder naming)
        deal_type:            Transaction type — affects NTH/GTH tier classification
        jurisdiction:         Asset jurisdiction — affects applicable checklist items
        vdr_path:             Path to local VDR folder (optional)
        vdr_export_csv:       Path to VDR platform export CSV/XLSX (optional)
        use_db:               Query aigis-poc PostgreSQL DB for pre-ingested docs
        db_connection_string: Postgres connection string; reads from env if None
        model_key:            LLM model for classification and novelty detection
        session_keys:         API keys dict {ENV_VAR: key} (UI session, not persisted)
        output_dir:           Directory to write output files
        checklist_version:    Gold-standard checklist version to use
        deal_name:            Deal name for report headers (defaults to deal_id)
        buyer_name:           Buyer name for DRL cover page
        round_number:         DRL round number (1, 2, etc.)

    Returns:
        dict with keys: status, outputs, findings, proposals, run_timestamp,
                        input_tokens, output_tokens, cost_usd
    """
    run_timestamp = datetime.now(timezone.utc).isoformat()
    deal_name = deal_name or f"Deal {deal_id[:8]}"
    output_base = Path(output_dir) / deal_id / "01_vdr_inventory"
    output_base.mkdir(parents=True, exist_ok=True)

    total_input_tokens = 0
    total_output_tokens = 0

    try:
        # ── Step 0: Load domain knowledge primer ─────────────────────────────
        primer_content = load_primer()

        # ── Step 1: Load checklist ────────────────────────────────────────────
        checklist = load_checklist(checklist_version)

        # ── Step 2: Crawl VDR sources ─────────────────────────────────────────
        source_lists = []

        if vdr_path:
            source_lists.append(crawl_filesystem(vdr_path))

        if vdr_export_csv:
            source_lists.append(crawl_vdr_export(vdr_export_csv))

        if use_db:
            db_files = crawl_db(deal_id, db_connection_string)
            if db_files:
                source_lists.append(db_files)

        if not source_lists:
            return AgentResult(
                status="error",
                error="No VDR source provided. Pass vdr_path, vdr_export_csv, or use_db=True with a valid deal_id.",
                run_timestamp=run_timestamp,
            ).model_dump()

        all_files = merge_sources(source_lists)

        # ── Step 3: Build LLM (used for Stage 3 matching + novelty detection) ──
        try:
            llm = get_chat_model(model_key, session_keys)
        except Exception:
            llm = None  # graceful degradation — Stage 1+2 only

        # ── Step 4: Classify documents (3-stage pipeline) ────────────────────
        classifications = batch_classify(all_files, checklist, llm=llm, primer_content=primer_content)

        # ── Step 5: Score against checklist ──────────────────────────────────
        gap_report = score_checklist(
            classifications=classifications,
            checklist=checklist,
            deal_type=deal_type,
            jurisdiction=jurisdiction,
            deal_id=deal_id,
            deal_name=deal_name,
            run_timestamp=run_timestamp,
        )

        # ── Step 6: Detect novel documents (self-learning) ────────────────────
        proposals = detect_novel_documents(
            classifications=classifications,
            checklist=checklist,
            deal_id=deal_id,
            deal_type=deal_type,
            run_timestamp=run_timestamp,
            llm=llm,
            primer_content=primer_content,
        )
        gap_report.summary.novel_count = len(proposals)

        # Persist proposals for later review
        if proposals:
            add_proposals(proposals)

        # ── Step 6b: Register run + compute gap delta (if repeat run) ─────────
        approx_cost = estimate_cost(model_key, total_input_tokens, total_output_tokens)
        gap_delta = register_run(
            gap_report=gap_report,
            cost_usd=approx_cost,
            output_dir=Path(output_dir),
            deal_name=deal_name,
            deal_type=deal_type,
            jurisdiction=jurisdiction,
            buyer=buyer_name,
        )

        # ── Step 7: Write inventory JSON ──────────────────────────────────────
        inventory_path = output_base / "01_vdr_inventory.json"
        inventory_data = {
            "deal_id": deal_id,
            "deal_name": deal_name,
            "deal_type": deal_type,
            "jurisdiction": jurisdiction,
            "checklist_version": checklist_version,
            "run_timestamp": run_timestamp,
            "total_files": len(all_files),
            "files": [f.model_dump() for f in all_files],
        }
        inventory_path.write_text(
            json.dumps(inventory_data, indent=2, default=str), encoding="utf-8"
        )

        # ── Step 8: Write gap analysis report (Markdown) ─────────────────────
        gap_report_path = output_base / "01_gap_analysis_report.md"
        generate_gap_report(gap_report, proposals, gap_report_path, gap_delta=gap_delta)

        # ── Step 9: Write Data Request List (DOCX) ───────────────────────────
        drl_path = output_base / "01_data_request_list.docx"
        generate_drl(gap_report, drl_path, buyer_name=buyer_name, round_number=round_number)

        # ── Step 10: Propose and apply domain knowledge learnings ─────────────
        # Only runs when an LLM is available and there is something to learn from
        # (unclassified documents or novel proposals). Appends new knowledge to the
        # primer file in an additive-only "LEARNED FROM LIVE VDR RUNS" section.
        primer_updates: list[dict] = []
        if llm is not None and primer_content is not None:
            primer_updates = propose_primer_updates(
                primer_content=primer_content,
                classifications=classifications,
                proposals=proposals,
                gap_report=gap_report,
                deal_id=deal_id,
                deal_type=deal_type,
                jurisdiction=jurisdiction,
                llm=llm,
                run_timestamp=run_timestamp,
            )
            if primer_updates:
                updated_primer = apply_primer_updates(
                    updates=primer_updates,
                    primer_content=primer_content,
                    run_timestamp=run_timestamp,
                    deal_id=deal_id,
                    deal_type=deal_type,
                    jurisdiction=jurisdiction,
                )
                save_primer(updated_primer)

        s = gap_report.summary
        return AgentResult(
            status="success",
            outputs=AgentOutputPaths(
                inventory_json=str(inventory_path.resolve()),
                gap_report_md=str(gap_report_path.resolve()),
                drl_docx=str(drl_path.resolve()),
            ),
            findings=s,
            proposals=proposals,
            gap_delta=gap_delta,
            run_timestamp=run_timestamp,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            cost_usd=approx_cost,
            primer_updates_count=len(primer_updates),
        ).model_dump()

    except Exception as exc:
        return AgentResult(
            status="error",
            error=str(exc),
            run_timestamp=run_timestamp,
        ).model_dump()
