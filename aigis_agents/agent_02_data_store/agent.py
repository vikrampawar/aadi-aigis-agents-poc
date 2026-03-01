"""
Agent 02 — VDR Financial & Operational Data Store.

Single source of truth for all numerical data extracted from a VDR.
Merges planned Agent 02 (Production Data Collator) and Agent 03 (Internal
Consistency Auditor) into one comprehensive data store agent.

Three operation modes:
  - ingest_vdr:   Walk full VDR, classify files via Agent 01, extract all data
  - ingest_file:  Ingest a single specified file
  - query:        Return data from the deal DB as structured JSON
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from aigis_agents.mesh.agent_base import AgentBase
from aigis_agents.agent_02_data_store import db_manager as db
from aigis_agents.agent_02_data_store import (
    excel_ingestor,
    pdf_ingestor,
    csv_ingestor,
    semantic_classifier,
    unit_normaliser,
    file_selector,
    consistency_checker,
    formula_engine,
    query_engine,
    report_generator,
)


class Agent02(AgentBase):
    AGENT_ID = "agent_02"
    DK_TAGS  = ["financial", "technical", "upstream_dd", "oil_gas_101"]

    # ── Core logic ─────────────────────────────────────────────────────────────

    def _run(
        self,
        deal_id: str,
        main_llm: Any,
        dk_context: str,
        patterns: list,
        mode: str = "standalone",
        output_dir: str = "./outputs",
        # operation dispatch
        operation: str = "ingest_vdr",
        # ingest_vdr
        vdr_path: str | None = None,
        deal_type: str = "producing_asset",
        jurisdiction: str = "GoM",
        checklist_version: str = "v1.0",
        case_name: str | None = None,
        overwrite: bool = False,
        file_filter: list[str] | None = None,
        # ingest_file
        file_path: str | None = None,
        file_type: str | None = None,
        source_doc_hint: str | None = None,
        sheet_names: list[str] | None = None,
        run_consistency_check: bool = True,
        pg_sync: bool = False,
        pg_dsn: str | None = None,
        # query
        query_text: str | None = None,
        query_sql: str | None = None,
        data_type: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        format: str = "json",
        include_metadata: bool = True,
        scenario: dict | None = None,
        **_,
    ) -> dict:
        db_path = db.ensure_db(deal_id, output_dir)
        conn = db.get_connection(deal_id, output_dir)

        # Ensure deal row exists
        db.upsert_deal(conn, deal_id,
                       deal_name=f"Deal {deal_id[:8]}",
                       deal_type=deal_type,
                       jurisdiction=jurisdiction)

        try:
            if operation == "ingest_vdr":
                return self._ingest_vdr(
                    conn=conn, deal_id=deal_id, main_llm=main_llm,
                    dk_context=dk_context, output_dir=output_dir,
                    mode=mode, vdr_path=vdr_path, deal_type=deal_type,
                    jurisdiction=jurisdiction, case_name=case_name,
                    overwrite=overwrite, file_filter=file_filter,
                    pg_sync=pg_sync, pg_dsn=pg_dsn,
                )
            elif operation == "ingest_file":
                return self._ingest_file(
                    conn=conn, deal_id=deal_id, main_llm=main_llm,
                    dk_context=dk_context, output_dir=output_dir,
                    mode=mode, file_path=file_path, file_type=file_type,
                    case_name=case_name, source_doc_hint=source_doc_hint,
                    sheet_names=sheet_names, run_consistency_check=run_consistency_check,
                    pg_sync=pg_sync, pg_dsn=pg_dsn,
                )
            elif operation == "query":
                return self._query(
                    conn=conn, deal_id=deal_id, main_llm=main_llm,
                    query_text=query_text, query_sql=query_sql,
                    data_type=data_type, case_name=case_name,
                    period_start=period_start, period_end=period_end,
                    include_metadata=include_metadata, scenario=scenario,
                )
            else:
                return {"error": f"Unknown operation: {operation!r}. Use ingest_vdr | ingest_file | query"}
        finally:
            conn.close()

    # ── ingest_vdr ─────────────────────────────────────────────────────────────

    def _ingest_vdr(
        self,
        conn, deal_id: str, main_llm: Any, dk_context: str, output_dir: str,
        mode: str, vdr_path: str | None, deal_type: str, jurisdiction: str,
        case_name: str | None, overwrite: bool, file_filter: list[str] | None,
        pg_sync: bool, pg_dsn: str | None,
    ) -> dict:
        if not vdr_path:
            return {"error": "vdr_path is required for ingest_vdr operation"}

        run_id = str(uuid.uuid4())
        stats = {"operation": "ingest_vdr", "files_processed": 0,
                 "data_points_added": 0, "conflicts": {}, "errors": []}

        # Get Agent 01 instance (optional dependency)
        agent01 = None
        try:
            agent01 = self.call_agent("agent_01", deal_id=deal_id,
                                      vdr_path=vdr_path, deal_type=deal_type,
                                      jurisdiction=jurisdiction)
        except Exception:
            pass  # Fall back to heuristic selection

        # Select files
        files = file_selector.select_files_for_ingestion(
            vdr_path=vdr_path,
            agent01=None,  # use heuristic (Agent01 result above isn't directly usable as callable)
            deal_id=deal_id,
            deal_type=deal_type,
            jurisdiction=jurisdiction,
            file_filter=file_filter,
        )

        # Ingest each file
        new_doc_ids: list[str] = []
        for file_info in files:
            try:
                result = self._ingest_single_file(
                    conn=conn, deal_id=deal_id, main_llm=main_llm,
                    dk_context=dk_context, file_path=file_info["path"],
                    file_type=file_info["file_type"],
                    case_name=case_name or file_info.get("doc_label"),
                    source_doc_hint=file_info.get("doc_label"),
                    sheet_names=None, overwrite=overwrite,
                )
                if "doc_id" in result:
                    new_doc_ids.append(result["doc_id"])
                stats["files_processed"] += 1
                stats["data_points_added"] += result.get("data_points_extracted", 0)
                if result.get("errors"):
                    stats["errors"].extend(result["errors"])
            except Exception as e:
                stats["errors"].append(f"{file_info['filename']}: {e}")

        # Consistency check across all new docs
        conflict_stats = consistency_checker.run_consistency_check(conn, deal_id, new_doc_ids)
        stats["conflicts"] = conflict_stats

        # Log ingestion
        db.log_ingestion(conn, {
            "id":                 str(uuid.uuid4()),
            "deal_id":            deal_id,
            "operation":          "ingest_vdr",
            "run_id":             run_id,
            "timestamp":          datetime.now(timezone.utc).isoformat(),
            "files_processed":    stats["files_processed"],
            "data_points_added":  stats["data_points_added"],
            "conflicts_detected": conflict_stats.get("total", 0),
            "status":             "complete",
            "errors":             str(stats["errors"][:10]) if stats["errors"] else None,
        })

        # Standalone mode: write reports
        if mode == "standalone":
            report_generator.generate_ingestion_report(conn, deal_id, output_dir, stats, conflict_stats)
            report_generator.generate_conflict_report(conn, deal_id, output_dir)
            stats["output_paths"] = {
                "db":              str(db.ensure_db(deal_id, output_dir)),
                "ingestion_report": str(Path(output_dir) / deal_id / "02_ingestion_report.md"),
                "conflict_report":  str(Path(output_dir) / deal_id / "02_conflict_report.md"),
            }

        # Optional PostgreSQL sync
        if pg_sync:
            from aigis_agents.agent_02_data_store import pg_sync as pg
            sync_conn = db.get_connection(deal_id, output_dir)
            try:
                pg_result = pg.sync_to_postgres(sync_conn, deal_id, pg_dsn or pg.DEFAULT_PG_DSN)
                stats["pg_sync"] = pg_result
            finally:
                sync_conn.close()

        stats["_deal_context_section"] = {
            "section_name": "Agent 02 — Data Store Summary",
            "content": (
                f"Files processed: {stats.get('files_processed', 0)} | "
                f"Data points added: {stats.get('data_points_added', 0)} | "
                f"Conflicts detected: {conflict_stats.get('total', 0)} "
                f"({conflict_stats.get('critical', 0)} critical, "
                f"{conflict_stats.get('warning', 0)} warning)"
            ),
        }
        return stats

    # ── ingest_file ────────────────────────────────────────────────────────────

    def _ingest_file(
        self,
        conn, deal_id: str, main_llm: Any, dk_context: str, output_dir: str,
        mode: str, file_path: str | None, file_type: str | None,
        case_name: str | None, source_doc_hint: str | None,
        sheet_names: list[str] | None, run_consistency_check: bool,
        pg_sync: bool, pg_dsn: str | None,
    ) -> dict:
        if not file_path:
            return {"error": "file_path is required for ingest_file operation"}

        run_id = str(uuid.uuid4())
        result = self._ingest_single_file(
            conn=conn, deal_id=deal_id, main_llm=main_llm,
            dk_context=dk_context, file_path=file_path,
            file_type=file_type, case_name=case_name,
            source_doc_hint=source_doc_hint, sheet_names=sheet_names,
            overwrite=True,
        )
        result["operation"] = "ingest_file"

        if run_consistency_check and result.get("doc_id"):
            conflict_stats = consistency_checker.run_consistency_check(
                conn, deal_id, [result["doc_id"]]
            )
            result["conflicts"] = conflict_stats

        # ── Entity extraction (non-blocking) ─────────────────────────────────
        if result.get("doc_id") and file_path:
            try:
                from aigis_agents.mesh.entity_extractor import EntityExtractor
                from aigis_agents.mesh.concept_graph import ConceptGraph

                graph = ConceptGraph(db_path=db.db_path_for_deal(deal_id, output_dir))
                text_summary = _build_extraction_text(file_path, source_doc_hint, case_name, result)
                n_extracted = EntityExtractor().extract_and_store(
                    text=text_summary,
                    llm=main_llm,
                    graph=graph,
                    source_doc=Path(file_path).name,
                    deal_id=deal_id,
                )
                if n_extracted:
                    result["entities_extracted"] = n_extracted
            except Exception as _exc:
                logger.debug("Entity extraction skipped (non-blocking): %s", _exc)

        db.log_ingestion(conn, {
            "id":                 str(uuid.uuid4()),
            "deal_id":            deal_id,
            "operation":          "ingest_file",
            "run_id":             run_id,
            "timestamp":          datetime.now(timezone.utc).isoformat(),
            "files_processed":    1,
            "data_points_added":  result.get("data_points_extracted", 0),
            "conflicts_detected": result.get("conflicts", {}).get("total", 0),
            "status":             "complete" if not result.get("errors") else "partial",
            "errors":             str(result.get("errors", [])[:5]) or None,
        })

        if mode == "standalone":
            result["output_paths"] = {
                "db": str(db.ensure_db(deal_id, output_dir)),
            }

        conflicts = result.get("conflicts", {})
        result["_deal_context_section"] = {
            "section_name": "Agent 02 — Data Store Summary",
            "content": (
                f"File: {Path(file_path).name} | "
                f"Data points: {result.get('data_points_extracted', 0)} | "
                f"Conflicts: {conflicts.get('total', 0)} "
                f"({conflicts.get('critical', 0)} critical)"
            ),
        }
        return result

    # ── query ──────────────────────────────────────────────────────────────────

    def _query(
        self,
        conn, deal_id: str, main_llm: Any,
        query_text: str | None, query_sql: str | None,
        data_type: str | None, case_name: str | None,
        period_start: str | None, period_end: str | None,
        include_metadata: bool, scenario: dict | None,
    ) -> dict:
        # Build scenario evaluation function if scenario provided
        formula_engine_fn = None
        if scenario:
            def formula_engine_fn(overrides: dict) -> dict:
                return {"note": "Scenario evaluation requires workbook_path — use ingest_file first"}

        # Get audit LLM lazily (re-use main_llm as audit fallback)
        result = query_engine.run_query(
            conn=conn, deal_id=deal_id,
            query_text=query_text, query_sql=query_sql,
            data_type=data_type, case_name=case_name,
            period_start=period_start, period_end=period_end,
            include_metadata=include_metadata,
            main_llm=main_llm, audit_llm=main_llm,
            scenario=scenario,
            formula_engine_fn=formula_engine_fn,
        )
        return result

    # ── Single file ingestion ──────────────────────────────────────────────────

    def _ingest_single_file(
        self,
        conn,
        deal_id: str,
        main_llm: Any,
        dk_context: str,
        file_path: str,
        file_type: str | None,
        case_name: str | None,
        source_doc_hint: str | None,
        sheet_names: list[str] | None,
        overwrite: bool,
    ) -> dict:
        """Parse and ingest a single file. Returns per-file stats dict."""
        path = Path(file_path)
        ext  = path.suffix.lower()
        ftype = file_type or file_selector._ext_to_type(ext)

        # Register in source_documents
        doc_id = str(uuid.uuid4())
        db.insert_source_document(conn, {
            "doc_id":           doc_id,
            "deal_id":          deal_id,
            "filename":         path.name,
            "folder_path":      str(path.parent),
            "file_type":        ftype,
            "doc_category":     source_doc_hint,
            "doc_label":        source_doc_hint,
            "ingest_timestamp": datetime.now(timezone.utc).isoformat(),
            "ingest_run_id":    doc_id,
            "case_name":        case_name,
            "status":           "ingesting",
        })

        result: dict[str, Any] = {"doc_id": doc_id, "filename": path.name, "errors": []}

        try:
            if ftype == "excel":
                classify_fn = semantic_classifier.make_classify_fn(main_llm, dk_context)
                stats = excel_ingestor.ingest_excel(
                    file_path=path, deal_id=deal_id, doc_id=doc_id,
                    conn=conn, case_name=case_name,
                    sheet_names=sheet_names, classify_fn=classify_fn,
                )
                result.update(stats)
                result["data_points_extracted"] = stats.get("cells_written", 0)

            elif ftype == "pdf":
                stats = pdf_ingestor.ingest_pdf(
                    file_path=path, deal_id=deal_id, doc_id=doc_id,
                    conn=conn, case_name=case_name,
                    main_llm=main_llm, dk_context=dk_context,
                )
                result.update(stats)
                result["data_points_extracted"] = stats.get("data_points_extracted", 0)

            elif ftype == "csv":
                stats = csv_ingestor.ingest_csv(
                    file_path=path, deal_id=deal_id, doc_id=doc_id,
                    conn=conn, case_name=case_name,
                    main_llm=main_llm, dk_context=dk_context,
                )
                result.update(stats)
                result["data_points_extracted"] = stats.get("data_points_extracted", 0)

            else:
                result["errors"].append(f"Unsupported file type: {ftype}")

            # Update source_document status
            conn.execute(
                "UPDATE source_documents SET status = 'complete', "
                "cell_count = ? WHERE doc_id = ?",
                (result.get("data_points_extracted", 0), doc_id),
            )
            conn.commit()

        except Exception as e:
            result["errors"].append(str(e))
            conn.execute(
                "UPDATE source_documents SET status = 'error', error_message = ? WHERE doc_id = ?",
                (str(e), doc_id),
            )
            conn.commit()

        return result


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_extraction_text(
    file_path:       str,
    source_doc_hint: str | None,
    case_name:       str | None,
    result:          dict,
) -> str:
    """Build a concise text summary from ingestion metadata for entity extraction."""
    from pathlib import Path as _Path
    parts = [f"Document: {_Path(file_path).name}"]
    if source_doc_hint:
        parts.append(f"Category: {source_doc_hint}")
    if case_name:
        parts.append(f"Case: {case_name}")
    n_dp = result.get("data_points_extracted", result.get("cells_written", 0))
    if n_dp:
        parts.append(f"Data points extracted: {n_dp}")
    if result.get("text_excerpt"):
        parts.append(f"Content excerpt: {result['text_excerpt'][:500]}")
    return " | ".join(parts)
