"""Load, save, and version the gold-standard checklist JSON."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from aigis_agents.agent_01_vdr_inventory.models import (
    Checklist,
    ChecklistCategory,
    ChecklistItem,
    ChecklistProposal,
    DocumentTier,
)

CHECKLISTS_DIR = Path(__file__).parent.parent.parent / "checklists"
PENDING_PATH = CHECKLISTS_DIR / "pending_additions.json"
REJECTED_PATH = CHECKLISTS_DIR / "rejected_proposals.json"
CHANGE_LOG_PATH = CHECKLISTS_DIR / "change_log.md"


def load_checklist(version: str = "v1.0") -> Checklist:
    """Load checklist from JSON file. Raises FileNotFoundError if version not found."""
    path = CHECKLISTS_DIR / f"gold_standard_{version}.json"
    if not path.exists():
        raise FileNotFoundError(f"Checklist version '{version}' not found at {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    categories = {}
    for cat_key, cat_data in data["categories"].items():
        items = []
        for item_data in cat_data["items"]:
            # Convert tier dict string values to DocumentTier enum
            tier = {k: DocumentTier(v) for k, v in item_data.get("tier", {}).items()}
            item_data = {**item_data, "tier": tier}
            items.append(ChecklistItem(**item_data))
        categories[cat_key] = ChecklistCategory(label=cat_data["label"], items=items)

    return Checklist(
        version=data["version"],
        last_updated=data["last_updated"],
        categories=categories,
    )


def _checklist_to_dict(checklist: Checklist) -> dict:
    """Convert Checklist model back to JSON-serialisable dict."""
    result = {
        "version": checklist.version,
        "last_updated": checklist.last_updated,
        "categories": {},
    }
    for cat_key, cat in checklist.categories.items():
        items = []
        for item in cat.items:
            item_dict = item.model_dump()
            # Convert DocumentTier enum back to string values
            item_dict["tier"] = {k: v.value for k, v in item.tier.items()}
            items.append(item_dict)
        result["categories"][cat_key] = {"label": cat.label, "items": items}
    return result


def save_checklist(checklist: Checklist) -> Path:
    """Save checklist to JSON file (creates new version file, keeps old)."""
    CHECKLISTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHECKLISTS_DIR / f"gold_standard_{checklist.version}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_checklist_to_dict(checklist), f, indent=2)
    return path


def _next_version(current: str) -> str:
    """Increment version string: v1.0 → v1.1, v1.9 → v1.10."""
    try:
        major, minor = current.lstrip("v").split(".")
        return f"v{major}.{int(minor) + 1}"
    except (ValueError, AttributeError):
        return f"{current}.1"


def load_pending_proposals() -> list[ChecklistProposal]:
    if not PENDING_PATH.exists():
        return []
    with open(PENDING_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    return [ChecklistProposal(**p) for p in raw if p.get("status") == "pending"]


def add_proposals(proposals: list[ChecklistProposal]) -> None:
    """Append new proposals to pending_additions.json."""
    CHECKLISTS_DIR.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    if PENDING_PATH.exists():
        with open(PENDING_PATH, encoding="utf-8") as f:
            existing = json.load(f)

    existing_ids = {p["proposal_id"] for p in existing}
    new_records = [p.model_dump() for p in proposals if p.proposal_id not in existing_ids]

    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(existing + new_records, f, indent=2)


def accept_proposal(proposal: ChecklistProposal, checklist: Checklist) -> Checklist:
    """Add an accepted proposal as a new checklist item and return updated checklist."""
    # Find or create the suggested category
    cat_key = proposal.suggested_category.lower().replace(" ", "_").replace("&", "and")
    if cat_key not in checklist.categories:
        checklist.categories[cat_key] = ChecklistCategory(
            label=proposal.suggested_category, items=[]
        )

    # Generate a new item id
    existing_ids = {item.id for _, item in checklist.all_items()}
    prefix = cat_key[:4]
    idx = 1
    while f"{prefix}_{idx:03d}" in existing_ids:
        idx += 1
    new_id = f"{prefix}_{idx:03d}"

    tier = {dt.value: proposal.suggested_tier for dt in proposal.applicable_deal_types}
    new_item = ChecklistItem(
        id=new_id,
        description=proposal.suggested_item_description,
        tier=tier,
        jurisdictions=["all"],
        search_keywords=proposal.filenames[:3],  # use example filenames as seed keywords
        notes=f"Added via self-learning on {proposal.run_timestamp[:10]}. Reasoning: {proposal.reasoning}",
        drl_request_text=f"Please provide {proposal.suggested_item_description.lower()}.",
    )
    checklist.categories[cat_key].items.append(new_item)
    return checklist


def reject_proposal(proposal: ChecklistProposal) -> None:
    """Move a proposal to rejected_proposals.json."""
    existing: list[dict] = []
    if REJECTED_PATH.exists():
        with open(REJECTED_PATH, encoding="utf-8") as f:
            existing = json.load(f)
    proposal.status = "rejected"
    proposal.reviewed_at = datetime.utcnow().isoformat()
    existing.append(proposal.model_dump())
    with open(REJECTED_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def log_checklist_change(old_version: str, new_version: str, accepted: list[ChecklistProposal]) -> None:
    """Append accepted changes to change_log.md."""
    CHECKLISTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"\n## {now} — {old_version} → {new_version}\n",
        f"Accepted {len(accepted)} proposal(s):\n",
    ]
    for p in accepted:
        lines.append(
            f"- **{p.suggested_item_description}** → category: `{p.suggested_category}`, "
            f"tier: `{p.suggested_tier.value}`, "
            f"from deal: `{p.deal_id}` | {p.reasoning}\n"
        )
    with open(CHANGE_LOG_PATH, "a", encoding="utf-8") as f:
        f.writelines(lines)


def finalise_accepted_proposals(
    accepted_ids: list[str],
    current_version: str = "v1.0",
) -> str:
    """
    Load pending proposals, accept the given IDs, update checklist, increment version.
    Returns new checklist version string.
    """
    pending = load_pending_proposals()
    to_accept = [p for p in pending if p.proposal_id in accepted_ids]
    to_reject = [p for p in pending if p.proposal_id not in accepted_ids]

    checklist = load_checklist(current_version)
    for p in to_accept:
        checklist = accept_proposal(p, checklist)

    new_version = _next_version(current_version)
    checklist.version = new_version
    checklist.last_updated = datetime.utcnow().strftime("%Y-%m-%d")
    save_checklist(checklist)

    for p in to_reject:
        reject_proposal(p)

    # Mark accepted as accepted in pending file
    if PENDING_PATH.exists():
        with open(PENDING_PATH, encoding="utf-8") as f:
            all_pending = json.load(f)
        for record in all_pending:
            if record["proposal_id"] in accepted_ids:
                record["status"] = "accepted"
                record["reviewed_at"] = datetime.utcnow().isoformat()
        with open(PENDING_PATH, "w", encoding="utf-8") as f:
            json.dump(all_pending, f, indent=2)

    log_checklist_change(current_version, new_version, to_accept)
    return new_version
