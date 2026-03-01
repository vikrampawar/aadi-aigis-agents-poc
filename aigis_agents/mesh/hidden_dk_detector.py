"""
HiddenDKDetector — Find domain knowledge in non-standard VDR documents
and proposition-level contradictions across deal documents.

Two capabilities:

  1. scan_for_hidden_dk()
     Scans a VDR document for content relevant to existing DK topics
     (fiscal terms, regulatory frameworks, technical standards, market data).
     Returns suggestions for DK file additions — all require human review
     before any DK files are modified.

  2. check_contradictions()
     Queries the deal's ConceptGraph for proposition pairs where the same
     (subject, predicate) is stated differently by two source documents.
     Surfaces CRITICAL and WARNING severity contradictions.  Purely DB-driven;
     no LLM required.

Both methods are non-blocking — any failure returns an empty list.

Usage:
    from aigis_agents.mesh.hidden_dk_detector import HiddenDKDetector
    detector = HiddenDKDetector()

    discoveries = detector.scan_for_hidden_dk(
        file_path="management_presentation.pptx",
        dk_root="aigis_agents/domain_knowledge/",
        main_llm=llm,
        text="extracted slide text...",
    )

    contradictions = detector.check_contradictions(
        deal_id="deal_001",
        db_path="./outputs/deal_001/02_data_store.db",
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


_HIDDEN_DK_PROMPT = """\
You are a domain knowledge quality reviewer for upstream oil & gas M&A due diligence.

The text below was extracted from a VDR document that is NOT a standard domain knowledge file.

Your task: identify any content that is generic, reusable domain knowledge that belongs in
permanent reference files — NOT deal-specific facts or projections.

Examples of HIDDEN DK (include these):
  - Generic fiscal terms mechanics (PSC structure, royalty calculation methodology)
  - Regulatory framework descriptions (BSEE lease terms, GoM BOEM requirements)
  - Technical classification standards (PRMS reserve methodology, SPE-PRMS guidelines)
  - Market benchmarking data (typical GoM LOE ranges, well cost benchmarks by water depth)
  - Infrastructure descriptions (general FPS types, subsea tie-back distance norms)

NOT hidden DK (exclude these):
  - Deal-specific financial projections or forecasts
  - Company-specific production or cost data
  - One-time event descriptions or opinions
  - Asset-specific legal terms

Available DK files: {dk_files}

Return ONLY a valid JSON array. Empty array [] if nothing qualifies. Schema:
[{{
  "content_excerpt":   str,   // verbatim excerpt from document (max 200 chars)
  "suggested_dk_file": str,   // filename only (must be one of the available files above)
  "suggested_section": str,   // section heading to insert under
  "confidence":        float  // 0.0–1.0
}}]

Document text:
{text}
"""


@dataclass
class DKDiscovery:
    source_file:           str
    content_excerpt:       str
    suggested_dk_file:     str
    suggested_section:     str
    confidence:            float
    requires_human_review: bool = True   # always True — never auto-applies


class HiddenDKDetector:
    """Detect domain knowledge hidden in non-standard VDR documents,
    and proposition-level contradictions across deal documents.
    """

    def scan_for_hidden_dk(
        self,
        file_path: str | Path,
        dk_root:   str | Path,
        main_llm:  Any,
        text:      str | None = None,
    ) -> list[DKDiscovery]:
        """Scan a VDR document for content matching existing DK topics.

        Args:
            file_path: Path to the VDR document (used for source attribution).
            dk_root:   Root directory of DK markdown files.
            main_llm:  LangChain chat model for classification.
            text:      Pre-extracted text (optional; file is read if absent).

        Returns:
            List of DKDiscovery instances; empty on failure or when nothing found.
            All discoveries have requires_human_review=True.
        """
        try:
            dk_files = _list_dk_files(Path(dk_root))
            if not dk_files:
                return []

            doc_text = text or _read_text(Path(file_path))
            if not doc_text or not doc_text.strip():
                return []

            prompt = _HIDDEN_DK_PROMPT.format(
                dk_files=", ".join(dk_files[:20]),
                text=doc_text[:3_000],
            )

            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=(
                    "You are a precision JSON extraction engine. "
                    "Return only a valid JSON array. No markdown, no explanation."
                )),
                HumanMessage(content=prompt),
            ]
            response = main_llm.invoke(messages)
            raw = response.content if hasattr(response, "content") else str(response)

            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

            items: list[dict] = json.loads(raw)
            if not isinstance(items, list):
                return []

            return [
                DKDiscovery(
                    source_file=str(file_path),
                    content_excerpt=it.get("content_excerpt", "")[:200],
                    suggested_dk_file=it.get("suggested_dk_file", ""),
                    suggested_section=it.get("suggested_section", ""),
                    confidence=float(it.get("confidence", 0.0)),
                )
                for it in items
                if isinstance(it, dict) and float(it.get("confidence", 0.0)) >= 0.5
            ]
        except Exception as exc:
            logger.debug("scan_for_hidden_dk() failed (non-blocking): %s", exc)
            return []

    def check_contradictions(
        self,
        deal_id:    str,
        db_path:    str | Path,
        new_doc_id: str | None = None,
    ) -> list:
        """Find proposition-level contradictions for the given deal.

        Queries the ConceptGraph's propositions table.  Purely DB-driven —
        no LLM required.  Non-blocking; returns empty list on failure.

        Args:
            deal_id:    Deal identifier.
            db_path:    Path to the deal's 02_data_store.db.
            new_doc_id: If set, only return contradictions where at least one
                        proposition's source_doc contains this identifier.

        Returns:
            List of Contradiction dataclass instances from concept_graph.
        """
        try:
            from aigis_agents.mesh.concept_graph import ConceptGraph
            graph = ConceptGraph(db_path=db_path)
            return graph.find_contradictions(deal_id=deal_id, new_doc_id=new_doc_id)
        except Exception as exc:
            logger.debug("check_contradictions() failed (non-blocking): %s", exc)
            return []


# ── Helpers ────────────────────────────────────────────────────────────────────

def _list_dk_files(dk_root: Path) -> list[str]:
    """Return names of DK markdown files under dk_root."""
    try:
        return [p.name for p in sorted(dk_root.rglob("*.md"))]
    except Exception:
        return []


def _read_text(path: Path, max_chars: int = 6_000) -> str:
    """Read file as plain text; return empty string on failure."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""
