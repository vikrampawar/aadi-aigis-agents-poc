"""
BuyerProfileManager — Persistent buyer / acquirer profile for the Aigis mesh.

The Aigis mesh was previously buyer-agnostic: every analysis treated the acquirer
as unknown.  This module gives every agent access to a rich, persistent model of
who the buyer is and what they want, so recommendations, bid sizing, and red-flag
thresholds can all be calibrated to the actual buyer.

Two learning pathways:

  1. Q&A Wizard  — run `python -m aigis_agents init-buyer-profile` once to answer
     20 structured questions and populate the profile sections.

  2. Feedback Loop — during any pipeline run, the AuditLayer scans inputs/outputs
     for preference signals (price deck mentions, threshold overrides, etc.) and
     prompts "Remember this preference?" in standalone mode.  Confirmed signals are
     appended to the profile via apply_signal().

Storage:
  aigis_agents/memory/buyer_profile.md   (single global file — not per-deal)

The profile is injected into every agent's system prompt as a `buyer_context`
block alongside the domain knowledge context.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Paths ──────────────────────────────────────────────────────────────────────

# aigis_agents/mesh/buyer_profile_manager.py → parent.parent = aigis_agents/
_AGENTS_ROOT  = Path(__file__).parent.parent
_PROFILE_PATH = _AGENTS_ROOT / "memory" / "buyer_profile.md"

# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class PreferenceSignal:
    """A buyer preference detected in agent inputs or outputs."""
    category: str       # "price_deck" | "financial_threshold" | "operational" | "strategic" | "negotiation"
    key: str            # e.g. "oil_price_deck", "min_irr", "max_loe_per_boe"
    value: str          # e.g. "$60/bbl flat", "15%", "$18/BOE"
    raw_text: str       # verbatim text that triggered detection
    confidence: float   # 0.0–1.0; only signals >= 0.5 are reported by detect_preferences()


# ── Q&A questions ──────────────────────────────────────────────────────────────

BUYER_QA_QUESTIONS: list[dict] = [
    # --- Investment Thesis ---
    {
        "section": "Investment Thesis",
        "key": "buyer_name_and_thesis",
        "question": (
            "What is your company's name and how would you describe your investment "
            "thesis for GoM E&P acquisitions? (e.g. basin consolidator, pure-play shelf, "
            "deepwater specialist)"
        ),
    },
    # --- Financial Thresholds ---
    {
        "section": "Financial Thresholds",
        "key": "min_irr_pct",
        "question": (
            "What is your company's minimum acceptable unlevered IRR for a "
            "producing GoM asset? (e.g. 15%, 20%)"
        ),
    },
    {
        "section": "Financial Thresholds",
        "key": "hurdle_rate_pct",
        "question": (
            "What hurdle / discount rate does your company use for DCF valuations? "
            "(e.g. 10%, 12%)"
        ),
    },
    {
        "section": "Financial Thresholds",
        "key": "max_loe_per_boe",
        "question": (
            "What is the maximum LOE/BOE threshold ($/BOE) above which a deal "
            "is uneconomic for you? (e.g. $22/BOE)"
        ),
    },
    {
        "section": "Financial Thresholds",
        "key": "max_ga_per_boe",
        "question": (
            "What is the maximum G&A/BOE your company can absorb in a standalone "
            "acquisition? (e.g. $5/BOE)"
        ),
    },
    {
        "section": "Financial Thresholds",
        "key": "max_aro_exposure_mm",
        "question": (
            "Does your company have a maximum ARO exposure threshold per deal? "
            "If so, what is it? (e.g. $100mm gross)"
        ),
    },
    {
        "section": "Financial Thresholds",
        "key": "min_pdp_coverage_ratio",
        "question": (
            "What minimum PDP NPV10 coverage ratio (EV / PDP NPV10) do you require? "
            "(e.g. 0.5×, 0.7×)"
        ),
    },
    # --- Price Preferences ---
    {
        "section": "Price Preferences",
        "key": "oil_price_deck",
        "question": (
            "What oil price deck does your company use for acquisitions? "
            "(e.g. strip, $60/bbl flat, $65/bbl flat, $70 declining)"
        ),
    },
    {
        "section": "Price Preferences",
        "key": "gas_price_deck",
        "question": (
            "What gas price deck do you use? "
            "(e.g. $3.00/MMBtu flat, $3.50/MMBtu, strip)"
        ),
    },
    # --- Operational Capabilities ---
    {
        "section": "Operational Capabilities",
        "key": "existing_gom_ops",
        "question": (
            "Does your company currently operate any GoM assets? (Yes/No — "
            "and if yes, briefly describe the existing portfolio)"
        ),
    },
    {
        "section": "Operational Capabilities",
        "key": "operated_preference",
        "question": (
            "Do you prefer operated positions, non-operated, or no preference? "
            "Is there a minimum working interest you require for operated deals?"
        ),
    },
    {
        "section": "Operational Capabilities",
        "key": "subsea_experience",
        "question": (
            "Does your company have subsea operations experience? "
            "(ROV, umbilicals, FPS, FPSO — Yes/No/Limited)"
        ),
    },
    {
        "section": "Operational Capabilities",
        "key": "max_wi_pct",
        "question": (
            "What is the maximum working interest (%) your company would consider "
            "on a single GoM asset? (e.g. 100%, 50%)"
        ),
    },
    {
        "section": "Operational Capabilities",
        "key": "target_asset_size_boepd",
        "question": (
            "What is your target asset size range in net BOE/d production? "
            "(e.g. 1,000–10,000 BOE/d)"
        ),
    },
    # --- Strategic Premiums ---
    {
        "section": "Strategic Premiums",
        "key": "strategic_premiums",
        "question": (
            "For which strategic factors would your company pay a premium above PDP NPV10? "
            "(operatorship, basin consolidation, infrastructure access, exploration upside, "
            "near-term development wells)"
        ),
    },
    {
        "section": "Strategic Premiums",
        "key": "cvr_appetite",
        "question": (
            "Will your company consider a CVR (contingent value right) structure? "
            "If so, what maximum % of the bid price would you assign to a CVR?"
        ),
    },
    # --- Portfolio State ---
    {
        "section": "Portfolio State",
        "key": "current_gom_production",
        "question": (
            "What is your current net GoM production (BOE/d) and 2P reserves (MMBoe)? "
            "(Approximate is fine; this helps calibrate relative deal size)"
        ),
    },
    {
        "section": "Portfolio State",
        "key": "infrastructure_overlap",
        "question": (
            "Do you have any existing infrastructure overlap or synergies with GoM "
            "shelf or deepwater assets? (e.g. existing platform ties, pipeline capacity)"
        ),
    },
    # --- Negotiation Preferences ---
    {
        "section": "Negotiation Preferences",
        "key": "preferred_deal_structure",
        "question": (
            "What is your preferred deal structure? "
            "(all cash, partial seller finance, earnout, CVR, combination)"
        ),
    },
    {
        "section": "Negotiation Preferences",
        "key": "max_months_to_close",
        "question": (
            "What is the maximum months-to-close your company can accommodate "
            "for a GoM transaction? (e.g. 3 months, 6 months)"
        ),
    },
]


# ── Profile template ──────────────────────────────────────────────────────────

_PROFILE_TEMPLATE = """\
# Buyer Profile
*Last updated: {now} | Version: 1*

---

## 1. Investment Thesis

*Not yet configured. Run `python -m aigis_agents init-buyer-profile` to set up.*

---

## 2. Financial Thresholds

- Minimum unlevered IRR: *(not set)*
- Maximum LOE/BOE: *(not set)*
- Maximum G&A/BOE: *(not set)*
- Hurdle rate (discount rate): *(not set)*
- Maximum ARO exposure: *(not set)*
- Minimum PDP NPV10 coverage ratio: *(not set)*

---

## 3. Operational Capabilities

- Existing GoM operations: *(not set)*
- Operated vs non-operated preference: *(not set)*
- Subsea experience: *(not set)*
- Maximum WI tolerance on single asset: *(not set)*
- Preferred asset size (BOE/d net): *(not set)*

---

## 4. Price Preferences

- Oil price deck: *(not set)*
- Gas price deck: *(not set)*
- Escalation assumption: *(not set)*

---

## 5. Strategic Premiums

- Will pay premium for: *(not set)*
- CVR appetite: *(not set)*
- Non-price factors: *(not set)*

---

## 6. Portfolio State

- Current GoM production (BOE/d net): *(not set)*
- Current 2P reserves (MMBoe net): *(not set)*
- Existing infrastructure overlap with target: *(not set)*

---

## 7. Negotiation Preferences

- Preferred deal structure: *(not set)*
- Max time to close: *(not set)*
- Key deal-breakers: *(not set)*

---

## 8. Learning Log

| Date | Source | Preference Learned |
|------|--------|--------------------|
"""


# ── BuyerProfileManager ───────────────────────────────────────────────────────

class BuyerProfileManager:
    """Read, update, and query the buyer profile markdown file.

    This is a thin wrapper around the flat markdown file.  All writes are atomic
    (temp file + rename) to prevent corruption on interrupted writes.

    Typical usage in AgentBase:
        buyer_profile = BuyerProfileManager()
        buyer_context = buyer_profile.load_as_context()
        # inject buyer_context into agent system prompt
    """

    def __init__(self, profile_path: str | Path | None = None) -> None:
        self._path = Path(profile_path) if profile_path else _PROFILE_PATH
        self._ensure_profile_exists()

    # ── Public API ─────────────────────────────────────────────────────────────

    def load_as_context(self) -> str:
        """Return the full profile markdown for injection into an agent system prompt."""
        if not self._path.exists():
            return "## Buyer Profile\n*(No buyer profile configured.)*\n"
        return self._path.read_text(encoding="utf-8")

    def load_as_dict(self) -> dict:
        """Return a structured dict of the profile for programmatic use.

        Parses each level-2 section header and its content.  Content is returned
        as raw text (not further parsed), so callers can inspect or re-format.
        """
        text = self.load_as_context()
        sections: dict[str, str] = {}
        current_section = ""
        current_lines: list[str] = []

        for line in text.splitlines():
            if line.startswith("## "):
                if current_section:
                    sections[current_section] = "\n".join(current_lines).strip()
                current_section = line[3:].strip()
                current_lines = []
            elif current_section:
                current_lines.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_lines).strip()

        return sections

    def update_section(self, section_name: str, content: str) -> None:
        """Replace the content of *section_name* with *content*.

        If the section does not exist, it is appended before the Learning Log.
        Preserves all other sections unchanged.
        """
        text = self._path.read_text(encoding="utf-8") if self._path.exists() else \
               _PROFILE_TEMPLATE.format(now=_now_date())

        # Find section header (## 1. Investment Thesis or ## Investment Thesis)
        pattern = re.compile(
            rf"(##\s+(?:\d+\.\s+)?{re.escape(section_name)}\s*\n)(.*?)(?=\n##|\Z)",
            re.DOTALL | re.IGNORECASE,
        )
        replacement = rf"\g<1>\n{content}\n"

        if pattern.search(text):
            new_text = pattern.sub(replacement, text)
        else:
            # Append before Learning Log, or at end
            log_header = "\n## 8. Learning Log\n"
            if log_header in text:
                new_text = text.replace(
                    log_header,
                    f"\n## {section_name}\n\n{content}\n{log_header}",
                )
            else:
                new_text = text + f"\n## {section_name}\n\n{content}\n"

        # Update the "Last updated" line
        new_text = re.sub(
            r"\*Last updated:.*?\*",
            f"*Last updated: {_now_date()} | Version: {self._next_version(text)}*",
            new_text,
        )
        self._atomic_write(new_text)

    def append_learning_log_entry(self, date: str, source: str, preference: str) -> None:
        """Append one row to the Learning Log table."""
        text = self._path.read_text(encoding="utf-8") if self._path.exists() else \
               _PROFILE_TEMPLATE.format(now=_now_date())

        # Escape any pipe characters in values
        safe_date  = date.replace("|", "\\|")
        safe_src   = source.replace("|", "\\|")
        safe_pref  = preference.replace("|", "\\|")
        new_row    = f"| {safe_date} | {safe_src} | {safe_pref} |"

        # Insert before the end of the file (after the table header if present)
        if "| Date | Source |" in text:
            # Find end of table — append after last table row
            lines = text.splitlines()
            last_table_line = max(
                (i for i, l in enumerate(lines) if l.startswith("|")),
                default=len(lines) - 1,
            )
            lines.insert(last_table_line + 1, new_row)
            new_text = "\n".join(lines) + "\n"
        else:
            new_text = text + f"\n## 8. Learning Log\n\n| Date | Source | Preference Learned |\n|------|--------|--------------------||\n{new_row}\n"

        self._atomic_write(new_text)

    def apply_signal(self, signal: PreferenceSignal) -> None:
        """Write a confirmed preference signal into the appropriate profile section
        and append a learning log entry."""
        section_map = {
            "price_deck":           "4. Price Preferences",
            "financial_threshold":  "2. Financial Thresholds",
            "operational":          "3. Operational Capabilities",
            "strategic":            "5. Strategic Premiums",
            "negotiation":          "7. Negotiation Preferences",
        }
        target_section = section_map.get(signal.category, "2. Financial Thresholds")

        # Read current section content and add/update the key
        current_sections = self.load_as_dict()
        section_text = current_sections.get(target_section, "")

        # Attempt to update an existing line that starts with the key, or append
        key_pattern = re.compile(
            rf"^(- {re.escape(signal.key)}[^:]*:).*$",
            re.MULTILINE | re.IGNORECASE,
        )
        if key_pattern.search(section_text):
            new_section_text = key_pattern.sub(rf"\g<1> {signal.value}", section_text)
        else:
            new_section_text = section_text.rstrip() + f"\n- {signal.key}: {signal.value}"

        self.update_section(target_section, new_section_text)
        self.append_learning_log_entry(
            date=_now_date(),
            source=f"agent_feedback (confidence={signal.confidence:.2f})",
            preference=f"{signal.key} = {signal.value}",
        )

    def run_qa_wizard(self) -> None:
        """Interactive CLI Q&A wizard to populate the buyer profile.

        Prints each question, collects the user's answer, and writes answers
        into the appropriate sections.  Skip a question by pressing Enter.
        """
        print("\n" + "=" * 70)
        print("  Aigis Buyer Profile Setup Wizard")
        print("  Press Enter to skip any question.")
        print("=" * 70 + "\n")

        answers: dict[str, str] = {}
        for i, q in enumerate(BUYER_QA_QUESTIONS, 1):
            print(f"Q{i}/{len(BUYER_QA_QUESTIONS)}: {q['question']}")
            answer = input("  > ").strip()
            if answer:
                answers[q["key"]] = answer
                print(f"  Saved: {q['key']} = {answer}\n")
            else:
                print("  (skipped)\n")

        # Group answers by section and write
        section_answers: dict[str, list[str]] = {}
        for q in BUYER_QA_QUESTIONS:
            if q["key"] in answers:
                sec = q["section"]
                section_answers.setdefault(sec, [])
                section_answers[sec].append(f"- {q['key']}: {answers[q['key']]}")

        # Find numeric prefix from BUYER_QA_QUESTIONS ordering
        section_order = {
            "Investment Thesis":     "1. Investment Thesis",
            "Financial Thresholds":  "2. Financial Thresholds",
            "Operational Capabilities": "3. Operational Capabilities",
            "Price Preferences":     "4. Price Preferences",
            "Strategic Premiums":    "5. Strategic Premiums",
            "Portfolio State":       "6. Portfolio State",
            "Negotiation Preferences": "7. Negotiation Preferences",
        }

        for section_raw, lines in section_answers.items():
            full_section = section_order.get(section_raw, section_raw)
            self.update_section(full_section, "\n".join(lines))

        self.append_learning_log_entry(
            date=_now_date(),
            source="qa_wizard",
            preference=f"Initial profile configured ({len(answers)} answers provided)",
        )

        print("\nBuyer profile saved to:", self._path)
        print("Run agents to start getting buyer-aware analysis.\n")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _ensure_profile_exists(self) -> None:
        """Create a blank profile if one doesn't exist yet."""
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(_PROFILE_TEMPLATE.format(now=_now_date()))

    def _atomic_write(self, content: str) -> None:
        """Write *content* to the profile file atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, self._path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    @staticmethod
    def _next_version(text: str) -> int:
        """Extract the current version number from the profile and increment it."""
        m = re.search(r"Version:\s*(\d+)", text)
        if m:
            return int(m.group(1)) + 1
        return 1


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
