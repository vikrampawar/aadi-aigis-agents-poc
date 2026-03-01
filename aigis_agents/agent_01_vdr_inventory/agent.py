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

from aigis_agents.mesh.agent_base import AgentBase

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


# ── Agent Mesh class ──────────────────────────────────────────────────────────

class Agent01(AgentBase):
    """
    Agent 01 — VDR Document Inventory & Gap Analyst (mesh-enabled).

    Key differences from the legacy vdr_inventory_agent() function:
      - main_llm (from AgentBase.invoke) is injected directly — no internal
        get_chat_model() call, so the analyst controls the model at invocation time.
      - dk_context (from DomainKnowledgeRouter) replaces the local load_primer()
        call; the mesh serves the richer, session-cached knowledge block.
      - Memory patterns (learned_patterns.json) are prepended to the DK context
        so the LLM sees confirmed classifications from previous deals.
      - Novelty proposals from detect_novel_documents() are additionally routed
        through the mesh MemoryManager, making them reviewable via the standard
        review_memory CLI rather than only the agent-specific accept_proposals.py.
      - File writes are skipped in tool_call mode.

    Mesh invocation:
        from aigis_agents.agent_01_vdr_inventory.agent import Agent01

        result = Agent01().invoke(
            mode="standalone",
            deal_id="00000000-0000-0000-0000-c005a1000001",
            deal_type="producing_asset",
            jurisdiction="GoM",
            vdr_path="/path/to/vdr",
            output_dir="./outputs",
            deal_name="Project Corsair",
        )

    The legacy vdr_inventory_agent() function is unchanged and continues
    to work for existing CLI usage.
    """

    AGENT_ID = "agent_01"
    DK_TAGS  = ["vdr_structure", "checklist", "upstream_dd"]

    def _run(
        self,
        deal_id:    str,
        main_llm,
        dk_context: str,
        patterns:   list,
        mode:       str = "standalone",
        output_dir: str = "./outputs",
        # Agent-specific inputs
        deal_type:            str = "producing_asset",
        jurisdiction:         str = "GoM",
        vdr_path:             str | Path | None = None,
        vdr_export_csv:       str | Path | None = None,
        use_db:               bool = True,
        db_connection_string: str | None = None,
        checklist_version:    str = "v1.0",
        deal_name:            str | None = None,
        buyer_name:           str | None = None,
        round_number:         int = 1,
        **_,
    ) -> dict:
        """
        VDR inventory and gap analysis pipeline.

        Replaces load_primer() with dk_context (mesh DK Router).
        Replaces get_chat_model() with the injected main_llm.
        Prepends confirmed learned patterns to the DK context.
        Routes novelty proposals through the mesh memory system.
        Skips file writes in tool_call mode.
        """
        run_timestamp = datetime.now(timezone.utc).isoformat()
        deal_name     = deal_name or f"Deal {deal_id[:8]}"
        output_base   = Path(output_dir) / deal_id / "01_vdr_inventory"

        total_input_tokens  = 0
        total_output_tokens = 0

        # ── Enrich dk_context with confirmed learned patterns ─────────────────
        effective_dk = dk_context or ""
        if patterns:
            pattern_lines = ["", "## LEARNED PATTERNS FROM PREVIOUS DEALS", ""]
            for p in patterns:
                kws    = ", ".join(p.get("trigger_keywords", []))
                cls    = p.get("classification", "?")
                conf   = p.get("confidence", "?")
                source = p.get("source", "")
                pattern_lines.append(
                    f"- Keywords: [{kws}] → Classification: {cls} "
                    f"(Confidence: {conf}, Source: {source})"
                )
            effective_dk = effective_dk + "\n".join(pattern_lines)

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
            return {
                "status":        "error",
                "error_message": "No VDR source provided. Pass vdr_path, vdr_export_csv, or use_db=True with a valid deal_id.",
                "deal_id":       deal_id,
                "deal_name":     deal_name,
            }

        all_files = merge_sources(source_lists)

        # ── Step 3: Use the injected main_llm (mesh-managed) ──────────────────
        # main_llm may be None if the model key failed — degrade gracefully
        llm = main_llm

        # ── Step 4: Classify documents (3-stage pipeline) ─────────────────────
        # dk_context (enriched with patterns) replaces the local primer file
        classifications = batch_classify(
            all_files, checklist, llm=llm, primer_content=effective_dk
        )

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

        # ── Step 6: Detect novel documents ────────────────────────────────────
        proposals = detect_novel_documents(
            classifications=classifications,
            checklist=checklist,
            deal_id=deal_id,
            deal_type=deal_type,
            run_timestamp=run_timestamp,
            llm=llm,
            primer_content=effective_dk,
        )
        gap_report.summary.novel_count = len(proposals)

        # Persist proposals to agent-01's own proposal system (unchanged)
        if proposals:
            add_proposals(proposals)

        # Additionally route proposals through the mesh memory queue so they
        # are reviewable via review_memory.py alongside all other agent suggestions
        for p in proposals:
            try:
                self._memory.queue_suggestion({
                    "from_agent": self.AGENT_ID,
                    "to_agent":   self.AGENT_ID,
                    "deal_id":    deal_id,
                    "suggestion": (
                        f"Novel document pattern: '{p.suggested_category}' — "
                        f"{p.suggested_item_description}. "
                        f"Suggested tier: {p.suggested_tier.value}. "
                        f"Files: {', '.join(p.filenames[:3])}. "
                        f"Reasoning: {p.reasoning}"
                    ),
                    "confidence": 0.75,
                })
            except Exception:
                pass  # never let memory errors block the agent

        # ── Step 6b: Register run ─────────────────────────────────────────────
        approx_cost = estimate_cost("gpt-4.1", total_input_tokens, total_output_tokens)
        gap_delta   = register_run(
            gap_report=gap_report,
            cost_usd=approx_cost,
            output_dir=Path(output_dir),
            deal_name=deal_name,
            deal_type=deal_type,
            jurisdiction=jurisdiction,
            buyer=buyer_name,
        )

        # ── Step 7–10: File I/O and primer updates — standalone only ──────────
        output_paths: dict[str, str] = {}
        primer_updates_count = 0

        if mode == "standalone":
            output_base.mkdir(parents=True, exist_ok=True)

            # Write inventory JSON
            inventory_path = output_base / "01_vdr_inventory.json"
            inventory_data = {
                "deal_id": deal_id, "deal_name": deal_name,
                "deal_type": deal_type, "jurisdiction": jurisdiction,
                "checklist_version": checklist_version,
                "run_timestamp": run_timestamp, "total_files": len(all_files),
                "files": [f.model_dump() for f in all_files],
            }
            inventory_path.write_text(
                json.dumps(inventory_data, indent=2, default=str), encoding="utf-8"
            )
            output_paths["inventory_json"] = str(inventory_path.resolve())

            # Write gap analysis report
            gap_report_path = output_base / "01_gap_analysis_report.md"
            generate_gap_report(gap_report, proposals, gap_report_path, gap_delta=gap_delta)
            output_paths["gap_report_md"] = str(gap_report_path.resolve())

            # Write Data Request List
            drl_path = output_base / "01_data_request_list.docx"
            generate_drl(gap_report, drl_path, buyer_name=buyer_name, round_number=round_number)
            output_paths["drl_docx"] = str(drl_path.resolve())

            # Propose and apply domain knowledge learnings to local primer
            if llm is not None:
                primer_content = load_primer()
                primer_updates_list = propose_primer_updates(
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
                if primer_updates_list:
                    updated_primer = apply_primer_updates(
                        updates=primer_updates_list,
                        primer_content=primer_content,
                        run_timestamp=run_timestamp,
                        deal_id=deal_id,
                        deal_type=deal_type,
                        jurisdiction=jurisdiction,
                    )
                    save_primer(updated_primer)
                    primer_updates_count = len(primer_updates_list)

        # ── Build raw output for mesh envelope ────────────────────────────────
        s = gap_report.summary

        # Build present / missing lists from gap_report items
        from aigis_agents.agent_01_vdr_inventory.models import ChecklistStatus, DocumentTier
        present_nth = [
            i.description for i in gap_report.items
            if i.tier == DocumentTier.need_to_have and i.status == ChecklistStatus.present
        ]
        missing_nth = [
            i.description for i in gap_report.items
            if i.tier == DocumentTier.need_to_have and i.status == ChecklistStatus.missing
        ]
        missing_gth = [
            i.description for i in gap_report.items
            if i.tier == DocumentTier.good_to_have and i.status == ChecklistStatus.missing
        ]

        return {
            "deal_id":       deal_id,
            "deal_name":     deal_name,
            "deal_type":     deal_type,
            "jurisdiction":  jurisdiction,
            "run_timestamp": run_timestamp,
            "total_files":   len(all_files),
            # Coverage metrics — exposed for tool_call consumers
            "coverage_score":   round(
                (s.present_nth + s.partial_nth) / max(s.present_nth + s.partial_nth + s.missing_nth, 1),
                4,
            ),
            "present_nth":  present_nth,
            "missing_nth":  missing_nth,
            "missing_gth":  missing_gth,
            "findings": {
                "present_nth":   s.present_nth,
                "partial_nth":   s.partial_nth,
                "missing_nth":   s.missing_nth,
                "present_gth":   s.present_gth,
                "partial_gth":   s.partial_gth,
                "missing_gth":   s.missing_gth,
                "novel_count":   s.novel_count,
                "total_files":   s.total_files,
            },
            "novel_proposals": [p.model_dump() for p in proposals],
            "gap_delta":       gap_delta,
            "cost_usd":        approx_cost,
            "primer_updates_count": primer_updates_count,
            "output_paths":    output_paths,  # populated in standalone; empty in tool_call
            "_deal_context_section": {
                "section_name": "Agent 01 — VDR Inventory Summary",
                "content": (
                    f"Files: {len(all_files)} | "
                    f"Coverage: {round((s.present_nth + s.partial_nth) / max(s.present_nth + s.partial_nth + s.missing_nth, 1), 3):.1%} | "
                    f"Present NTH: {s.present_nth} | Partial NTH: {s.partial_nth} | "
                    f"Missing NTH: {s.missing_nth} | Novel: {s.novel_count}"
                ),
            },
        }
