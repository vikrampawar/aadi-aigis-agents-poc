"""
ConceptGraph — SQLite-backed knowledge graph for Aigis deal intelligence.

Stores entities (nodes), relationships (edges), and factual propositions
extracted from VDR documents during Agent 02 ingestion.

Schema is additive to the existing deal DB (02_data_store.db) via three
tables: concept_nodes, concept_edges, propositions.  All created with
IF NOT EXISTS guards so existing DBs are unaffected until first write.

Design:
  - Nodes:        named entities (assets, companies, basins, wells, contracts)
  - Edges:        typed directed relationships between entities
  - Propositions: subject–predicate–object factual statements with source

Contradiction detection:
  Groups propositions by (subject, predicate).  Where two different source
  documents state different object values, a Contradiction is raised.
  Severity is CRITICAL when numeric values differ by >20%; WARNING otherwise.

Usage:
    from aigis_agents.mesh.concept_graph import ConceptGraph
    g = ConceptGraph(db_path="./outputs/deal_001/02_data_store.db")
    g.add_node("Na Kika FPS", "asset", "Deepwater FPS in Garden Banks area")
    g.add_proposition("Na Kika FPS", "current_production", "15,000 BOE/d",
                      source_doc="mgmt_case.xlsx", deal_id="deal_001")
    context = g.get_deal_context_summary("deal_001")
"""

from __future__ import annotations

import logging
import re
import sqlite3
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class ConceptNode:
    node_id:     str
    name:        str
    node_type:   str    # entity | metric | concept | event | risk | asset | company | basin
    description: str
    deal_id:     str | None


@dataclass
class ConceptEdge:
    edge_id:      str
    source_id:    str
    target_id:    str
    relationship: str
    weight:       float
    source_doc:   str


@dataclass
class Contradiction:
    subject:       str
    predicate:     str
    proposition_a: str
    source_a:      str
    page_a:        str
    proposition_b: str
    source_b:      str
    page_b:        str
    severity:      str   # "CRITICAL" | "WARNING"


# ── Schema DDL ─────────────────────────────────────────────────────────────────

_CONCEPT_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS concept_nodes (
    node_id     TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    node_type   TEXT NOT NULL,
    description TEXT DEFAULT '',
    deal_id     TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concept_edges (
    edge_id      TEXT PRIMARY KEY,
    source_id    TEXT NOT NULL,
    target_id    TEXT NOT NULL,
    relationship TEXT NOT NULL,
    weight       REAL DEFAULT 1.0,
    source_doc   TEXT DEFAULT '',
    deal_id      TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS propositions (
    prop_id     TEXT PRIMARY KEY,
    subject     TEXT NOT NULL,
    predicate   TEXT NOT NULL,
    object      TEXT NOT NULL,
    source_doc  TEXT NOT NULL,
    deal_id     TEXT NOT NULL,
    page_ref    TEXT DEFAULT '',
    confidence  TEXT DEFAULT 'HIGH',
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cn_name_deal  ON concept_nodes(name, deal_id);
CREATE INDEX IF NOT EXISTS idx_ce_source     ON concept_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_ce_target     ON concept_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_prop_subj     ON propositions(subject, predicate, deal_id);
CREATE INDEX IF NOT EXISTS idx_prop_deal     ON propositions(deal_id);
"""


# ── ConceptGraph ───────────────────────────────────────────────────────────────

class ConceptGraph:
    """SQLite-backed knowledge graph for deal entities, relationships, and facts.

    Shares the deal's 02_data_store.db file (schema added additively).
    Safe to instantiate when the DB does not yet exist — writes create it.

    Args:
        db_path: Path to the deal's SQLite DB file.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        # Create tables only if the DB already exists (avoid creating
        # an empty DB just because AgentBase instantiated ConceptGraph early)
        if self._db_path.exists():
            self._setup_schema()

    # ── Public API ──────────────────────────────────────────────────────────────

    def add_node(
        self,
        name:        str,
        node_type:   str,
        description: str = "",
        deal_id:     str | None = None,
    ) -> str:
        """Insert or update a concept node.  Returns node_id."""
        self._ensure_schema()
        conn = self._connect()
        try:
            existing = conn.execute(
                "SELECT node_id FROM concept_nodes "
                "WHERE name = ? AND (deal_id = ? OR deal_id IS NULL)",
                [name, deal_id],
            ).fetchone()
            if existing:
                node_id = existing[0]
                conn.execute(
                    "UPDATE concept_nodes SET description=?, updated_at=? WHERE node_id=?",
                    [description, _now(), node_id],
                )
            else:
                node_id = str(uuid.uuid4())[:8]
                now = _now()
                conn.execute(
                    """INSERT INTO concept_nodes
                       (node_id, name, node_type, description, deal_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    [node_id, name, node_type, description, deal_id, now, now],
                )
            conn.commit()
            return node_id
        finally:
            conn.close()

    def add_edge(
        self,
        source_id:    str,
        target_id:    str,
        relationship: str,
        weight:       float = 1.0,
        source_doc:   str = "",
        deal_id:      str | None = None,
    ) -> None:
        """Add a directed edge between two nodes (upsert by composite key)."""
        self._ensure_schema()
        edge_id = f"{source_id[:8]}-{target_id[:8]}-{relationship}"[:60]
        conn = self._connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO concept_edges
                   (edge_id, source_id, target_id, relationship, weight,
                    source_doc, deal_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [edge_id, source_id, target_id, relationship, weight,
                 source_doc, deal_id, _now()],
            )
            conn.commit()
        finally:
            conn.close()

    def add_proposition(
        self,
        subject:    str,
        predicate:  str,
        object_:    str,
        source_doc: str,
        deal_id:    str,
        page_ref:   str = "",
        confidence: str = "HIGH",
    ) -> str:
        """Store a factual statement (subject–predicate–object).  Returns prop_id."""
        self._ensure_schema()
        conn = self._connect()
        try:
            prop_id = str(uuid.uuid4())[:8]
            conn.execute(
                """INSERT INTO propositions
                   (prop_id, subject, predicate, object, source_doc,
                    deal_id, page_ref, confidence, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [prop_id, subject, predicate, object_, source_doc,
                 deal_id, page_ref, confidence, _now()],
            )
            conn.commit()
            return prop_id
        finally:
            conn.close()

    def neighbours(self, node_id: str, max_hops: int = 2) -> list[ConceptNode]:
        """Return all nodes reachable from *node_id* within *max_hops* edges."""
        if not self._db_path.exists():
            return []
        conn = self._connect()
        try:
            visited: set[str] = {node_id}
            frontier: set[str] = {node_id}
            for _ in range(max_hops):
                if not frontier:
                    break
                placeholders = ",".join("?" * len(frontier))
                rows = conn.execute(
                    f"""SELECT DISTINCT target_id FROM concept_edges
                        WHERE source_id IN ({placeholders})
                        UNION
                        SELECT DISTINCT source_id FROM concept_edges
                        WHERE target_id IN ({placeholders})""",
                    list(frontier) * 2,
                ).fetchall()
                new_ids = {r[0] for r in rows} - visited
                visited |= new_ids
                frontier = new_ids

            visited.discard(node_id)
            if not visited:
                return []

            placeholders = ",".join("?" * len(visited))
            node_rows = conn.execute(
                f"SELECT node_id, name, node_type, description, deal_id "
                f"FROM concept_nodes WHERE node_id IN ({placeholders})",
                list(visited),
            ).fetchall()
            return [
                ConceptNode(
                    node_id=r[0], name=r[1], node_type=r[2],
                    description=r[3], deal_id=r[4],
                )
                for r in node_rows
            ]
        finally:
            conn.close()

    def find_contradictions(
        self,
        deal_id:     str,
        new_doc_id:  str | None = None,
    ) -> list[Contradiction]:
        """Find proposition-level contradictions for the given deal.

        Groups propositions by (subject, predicate).  Where two different
        source_docs state different object values, a Contradiction is raised.

        Args:
            deal_id:    Deal to scan.
            new_doc_id: If set, only return contradictions where at least
                        one proposition's source_doc contains this string.

        Returns:
            List of Contradiction objects; empty when no data or no contradictions.
        """
        if not self._db_path.exists():
            return []
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT subject, predicate, object, source_doc, page_ref
                   FROM propositions WHERE deal_id = ?
                   ORDER BY subject, predicate, created_at""",
                [deal_id],
            ).fetchall()
        finally:
            conn.close()

        # Group by (subject, predicate)
        groups: dict[tuple, list] = defaultdict(list)
        for r in rows:
            groups[(r[0], r[1])].append({
                "object": r[2], "source": r[3], "page": r[4] or "",
            })

        contradictions: list[Contradiction] = []
        for (subject, predicate), props in groups.items():
            if len(props) < 2:
                continue
            seen: set[frozenset] = set()
            for i, a in enumerate(props):
                for b in props[i + 1:]:
                    if a["source"] == b["source"]:
                        continue
                    if a["object"].strip().lower() == b["object"].strip().lower():
                        continue
                    pair_key = frozenset([a["source"], b["source"]])
                    if pair_key in seen:
                        continue
                    seen.add(pair_key)
                    # Filter by new_doc_id if given
                    if new_doc_id and new_doc_id not in a["source"] and new_doc_id not in b["source"]:
                        continue
                    severity = _contradiction_severity(a["object"], b["object"])
                    contradictions.append(Contradiction(
                        subject=subject,
                        predicate=predicate,
                        proposition_a=a["object"],
                        source_a=a["source"],
                        page_a=a["page"],
                        proposition_b=b["object"],
                        source_b=b["source"],
                        page_b=b["page"],
                        severity=severity,
                    ))

        return contradictions

    def get_entity_context(self, entity_name: str, deal_id: str) -> str:
        """Return a formatted markdown context block for a single entity."""
        if not self._db_path.exists():
            return ""
        conn = self._connect()
        try:
            node_row = conn.execute(
                "SELECT node_id, node_type, description FROM concept_nodes "
                "WHERE name = ? AND (deal_id = ? OR deal_id IS NULL)",
                [entity_name, deal_id],
            ).fetchone()
            if not node_row:
                return ""
            node_id, node_type, description = node_row

            props = conn.execute(
                "SELECT predicate, object, source_doc, page_ref "
                "FROM propositions WHERE subject = ? AND deal_id = ? "
                "ORDER BY predicate LIMIT 8",
                [entity_name, deal_id],
            ).fetchall()
        finally:
            conn.close()

        lines = [f"**{entity_name}** ({node_type}): {description}"]
        for p in props:
            page_part = f" p.{p[3]}" if p[3] else ""
            lines.append(f"  - {p[0]}: {p[1]}{page_part} [{Path(p[2]).name}]")

        nbrs = self.neighbours(node_id, max_hops=1)
        if nbrs:
            lines.append(f"  - Related: {', '.join(n.name for n in nbrs[:5])}")

        return "\n".join(lines)

    def get_deal_context_summary(
        self,
        deal_id:   str,
        max_nodes: int = 12,
    ) -> str:
        """Return a markdown summary of key entities and facts for the deal.

        Called by AgentBase step 5.7 to inject into agent system prompts.
        Returns empty string when no entity data has been populated.
        """
        if not self._db_path.exists():
            return ""
        conn = self._connect()
        try:
            nodes = conn.execute(
                "SELECT node_id, name, node_type, description FROM concept_nodes "
                "WHERE deal_id = ? OR deal_id IS NULL "
                "ORDER BY updated_at DESC LIMIT ?",
                [deal_id, max_nodes],
            ).fetchall()
            if not nodes:
                return ""
            prop_count = conn.execute(
                "SELECT COUNT(*) FROM propositions WHERE deal_id = ?",
                [deal_id],
            ).fetchone()[0]
        finally:
            conn.close()

        sections = [
            f"## Entity Graph — {len(nodes)} entities, {prop_count} propositions\n"
        ]
        for node in nodes:
            ctx = self.get_entity_context(node[1], deal_id)
            if ctx:
                sections.append(ctx)

        return "\n\n".join(sections)

    def node_count(self) -> int:
        """Return total number of nodes in the store."""
        if not self._db_path.exists():
            return 0
        conn = self._connect()
        try:
            return conn.execute("SELECT COUNT(*) FROM concept_nodes").fetchone()[0]
        finally:
            conn.close()

    def proposition_count(self) -> int:
        """Return total number of propositions in the store."""
        if not self._db_path.exists():
            return 0
        conn = self._connect()
        try:
            return conn.execute("SELECT COUNT(*) FROM propositions").fetchone()[0]
        finally:
            conn.close()

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(self._db_path))

    def _ensure_schema(self) -> None:
        """Create concept tables (idempotent; also creates DB if absent)."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._setup_schema()

    def _setup_schema(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_CONCEPT_SCHEMA_DDL)
            conn.commit()
        finally:
            conn.close()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _contradiction_severity(val_a: str, val_b: str) -> str:
    """Estimate severity by comparing numeric values when present."""
    nums_a = re.findall(r"[-+]?\d*\.?\d+", val_a)
    nums_b = re.findall(r"[-+]?\d*\.?\d+", val_b)
    try:
        if nums_a and nums_b:
            a, b = float(nums_a[0]), float(nums_b[0])
            if b != 0:
                diff_pct = abs(a - b) / abs(b)
                return "CRITICAL" if diff_pct > 0.20 else "WARNING"
    except (ValueError, ZeroDivisionError):
        pass
    return "WARNING"
