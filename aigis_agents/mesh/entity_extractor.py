"""
EntityExtractor — LLM-driven extraction of entities and propositions.

Extracts named entities, typed relationships, and factual propositions
from document text and stores them in the ConceptGraph.

Called by Agent 02 during document ingestion (Phase D, step D4).
All methods are non-blocking: any LLM failure returns an empty result so
ingestion is never blocked by extraction errors.

Supported entity types:
    asset | company | basin | well | contract | metric | concept

Proposition predicates (examples):
    current_production, reserve_class, operator, water_depth, irr,
    npv10, loe_per_boe, working_interest, royalty_rate, aro_estimate,
    lease_expiry, bid_date, effective_date

Usage:
    from aigis_agents.mesh.entity_extractor import EntityExtractor
    extractor = EntityExtractor()
    count = extractor.extract_and_store(
        text="Na Kika FPS is operated by Shell with current production of 15,000 BOE/d",
        llm=main_llm,
        graph=concept_graph,
        source_doc="management_presentation.pdf",
        deal_id="deal_001",
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_MAX_TEXT_CHARS = 3_000

_EXTRACTION_PROMPT = """\
You are an information extraction engine for upstream oil & gas M&A due diligence.

Extract from the document excerpt below:

1. ENTITIES — named assets, companies, basins, wells, contracts, people
   Types: "asset" | "company" | "basin" | "well" | "contract" | "metric" | "concept"

2. PROPOSITIONS — factual subject–predicate–object statements
   Predicate examples: current_production, reserve_class, operator, water_depth, irr,
   npv10, loe_per_boe, working_interest, royalty_rate, aro_estimate, lease_expiry,
   bid_date, water_depth, platform_type, jurisdiction, ownership

3. RELATIONSHIPS — typed links between entities
   Relationship examples: operated_by, tied_back_to, located_in, governed_by,
   owned_by, produces, hosts, competes_with

Rules:
- Extract ONLY facts explicitly stated; never infer or extrapolate.
- Normalise entity names consistently (e.g. "Na Kika FPS" not "na kika").
- Include numeric units in object fields (e.g. "15,000 BOE/d" not "15000").
- Limit output: max 5 entities, 10 propositions, 5 relationships.
- Return ONLY valid JSON matching this schema — no markdown, no explanation:

{{
  "entities":      [{{"name": str, "type": str, "description": str}}],
  "propositions":  [{{"subject": str, "predicate": str, "object": str, "page_ref": str, "confidence": "HIGH"|"MEDIUM"|"LOW"}}],
  "relationships": [{{"source": str, "target": str, "relationship": str, "weight": float}}]
}}

Document text:
{text}
"""


@dataclass
class ExtractionResult:
    entities:      list[dict] = field(default_factory=list)
    propositions:  list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.entities or self.propositions or self.relationships)


class EntityExtractor:
    """Extract entities and propositions from document text using an LLM.

    All methods are non-blocking — failures return empty results.
    """

    def extract(self, text: str, llm: Any) -> ExtractionResult:
        """Extract entities and propositions from text.

        Args:
            text: Raw or summarised document text (truncated to 3,000 chars).
            llm:  LangChain chat model.

        Returns:
            ExtractionResult; empty on failure.
        """
        if not text or not text.strip():
            return ExtractionResult()

        prompt = _EXTRACTION_PROMPT.format(text=text[:_MAX_TEXT_CHARS])

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=(
                    "You are a precision JSON extraction engine. "
                    "Return only valid JSON. No markdown, no explanation."
                )),
                HumanMessage(content=prompt),
            ]
            response = llm.invoke(messages)
            raw = response.content if hasattr(response, "content") else str(response)

            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

            data = json.loads(raw)
            return ExtractionResult(
                entities=data.get("entities", []),
                propositions=data.get("propositions", []),
                relationships=data.get("relationships", []),
            )
        except Exception as exc:
            logger.debug("EntityExtractor.extract() failed (non-blocking): %s", exc)
            return ExtractionResult()

    def extract_and_store(
        self,
        text:       str,
        llm:        Any,
        graph:      Any,   # ConceptGraph
        source_doc: str,
        deal_id:    str,
    ) -> int:
        """Extract entities/propositions and persist to ConceptGraph.

        Args:
            text:       Document text to extract from.
            llm:        LangChain chat model.
            graph:      ConceptGraph instance to write into.
            source_doc: Source document identifier (filename or path).
            deal_id:    Deal identifier for scoping.

        Returns:
            Total count of items stored (nodes + propositions + edges).
        """
        result = self.extract(text, llm)
        if result.is_empty:
            return 0

        count = 0
        node_name_to_id: dict[str, str] = {}

        for ent in result.entities:
            name = ent.get("name", "").strip()
            if not name:
                continue
            try:
                node_id = graph.add_node(
                    name=name,
                    node_type=ent.get("type", "entity"),
                    description=ent.get("description", ""),
                    deal_id=deal_id,
                )
                node_name_to_id[name] = node_id
                count += 1
            except Exception as exc:
                logger.debug("add_node(%s) failed: %s", name, exc)

        for prop in result.propositions:
            subject   = prop.get("subject", "").strip()
            predicate = prop.get("predicate", "").strip()
            obj       = prop.get("object", "").strip()
            if not (subject and predicate and obj):
                continue
            try:
                graph.add_proposition(
                    subject=subject,
                    predicate=predicate,
                    object_=obj,
                    source_doc=source_doc,
                    deal_id=deal_id,
                    page_ref=prop.get("page_ref", ""),
                    confidence=prop.get("confidence", "HIGH"),
                )
                count += 1
            except Exception as exc:
                logger.debug("add_proposition() failed: %s", exc)

        for rel in result.relationships:
            src_name = rel.get("source", "").strip()
            tgt_name = rel.get("target", "").strip()
            relationship = rel.get("relationship", "related_to").strip()
            if not (src_name and tgt_name):
                continue
            src_id = node_name_to_id.get(src_name)
            tgt_id = node_name_to_id.get(tgt_name)
            if src_id and tgt_id:
                try:
                    graph.add_edge(
                        source_id=src_id,
                        target_id=tgt_id,
                        relationship=relationship,
                        weight=float(rel.get("weight", 1.0)),
                        source_doc=source_doc,
                        deal_id=deal_id,
                    )
                    count += 1
                except Exception as exc:
                    logger.debug("add_edge() failed: %s", exc)

        return count
