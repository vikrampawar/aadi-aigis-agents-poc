#!/usr/bin/env python3
"""Fix Excalidraw files: add missing properties to text elements and add missing standalone text."""

import json
import random
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs" / "diagrams"

# All required base properties for any Excalidraw element
BASE_DEFAULTS = {
    "version": 2,
    "versionNonce": lambda: random.randint(1, 2_000_000_000),
    "isDeleted": False,
    "fillStyle": "solid",
    "strokeWidth": 2,
    "strokeStyle": "solid",
    "roughness": 1,
    "opacity": 100,
    "angle": 0,
    "backgroundColor": "transparent",
    "seed": lambda: random.randint(1, 2_000_000_000),
    "groupIds": [],
    "frameId": None,
    "index": None,
    "roundness": None,
    "boundElements": [],
    "updated": 1772280330286,
    "link": None,
    "locked": False,
}

# Additional required properties for text elements
TEXT_DEFAULTS = {
    "textAlign": "left",
    "verticalAlign": "top",
    "containerId": None,
    "autoResize": True,
    "lineHeight": 1.25,
}


def make_standalone_text(id_, x, y, text, fontSize=16, strokeColor="#e5e5e5", fontFamily=1, **overrides):
    """Create a fully-specified standalone text element."""
    # Estimate width/height based on text content
    lines = text.split("\n")
    max_line_len = max(len(line) for line in lines)
    est_char_width = fontSize * 0.65  # rough estimate for Virgil font
    width = max(int(max_line_len * est_char_width), 50)
    height = int(len(lines) * fontSize * 1.25)

    elem = {
        "type": "text",
        "id": id_,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "text": text,
        "originalText": text,
        "fontSize": fontSize,
        "strokeColor": strokeColor,
        "fontFamily": fontFamily,
    }
    # Apply base defaults
    for k, v in BASE_DEFAULTS.items():
        if k not in elem:
            elem[k] = v() if callable(v) else v
    # Apply text defaults
    for k, v in TEXT_DEFAULTS.items():
        if k not in elem:
            elem[k] = v
    # Apply overrides
    elem.update(overrides)
    return elem


def fix_element_properties(elem):
    """Ensure all required properties exist on any element."""
    for k, v in BASE_DEFAULTS.items():
        if k not in elem:
            elem[k] = v() if callable(v) else v

    if elem["type"] == "text":
        for k, v in TEXT_DEFAULTS.items():
            if k not in elem:
                elem[k] = v
        # Ensure width/height exist
        if "width" not in elem or "height" not in elem:
            text = elem.get("text", "")
            lines = text.split("\n")
            max_line_len = max(len(line) for line in lines) if lines else 1
            fs = elem.get("fontSize", 16)
            if "width" not in elem:
                elem["width"] = max(int(max_line_len * fs * 0.65), 50)
            if "height" not in elem:
                elem["height"] = int(len(lines) * fs * 1.25)
        # Ensure originalText
        if "originalText" not in elem:
            elem["originalText"] = elem.get("text", "")

    if elem["type"] == "arrow":
        for k in ["startBinding", "endBinding", "startArrowhead"]:
            if k not in elem:
                elem[k] = None
        if "lastCommittedPoint" not in elem:
            elem["lastCommittedPoint"] = None

    return elem


def fix_file(filepath):
    """Fix all elements in an Excalidraw file."""
    with open(filepath) as f:
        data = json.load(f)

    for elem in data["elements"]:
        fix_element_properties(elem)

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Fixed: {filepath.name}")


def add_missing_text_to_02():
    """Add missing standalone text elements to 02-agent-01-pipeline.excalidraw."""
    filepath = DOCS / "02-agent-01-pipeline.excalidraw"
    with open(filepath) as f:
        data = json.load(f)

    # Check which standalone text elements already exist
    existing_ids = {e["id"] for e in data["elements"]}

    missing_texts = []

    # Title and subtitle
    if "title" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "title", 180, 5,
            "Agent 01 — VDR Document Classification",
            fontSize=24, strokeColor="#e5e5e5",
        ))
    if "subtitle" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "subtitle", 200, 38,
            "Deterministic-first, LLM-as-fallback",
            fontSize=14, strokeColor="#a0a0a0",
        ))

    # Stage labels on the zone backgrounds
    if "s1label" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "s1label", 255, 82,
            "Stage 1: Keywords",
            fontSize=14, strokeColor="#4ade80",
        ))
    if "s2label" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "s2label", 255, 277,
            "Stage 2: Fuzzy",
            fontSize=14, strokeColor="#fbbf24",
        ))
    if "s3label" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "s3label", 255, 472,
            "Stage 3: LLM",
            fontSize=14, strokeColor="#f87171",
        ))

    # Cost annotations (right side of each zone)
    if "s1cost" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "s1cost", 257, 195,
            "Cost: FREE",
            fontSize=12, strokeColor="#4ade80",
        ))
    if "s2cost" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "s2cost", 257, 390,
            "Cost: FREE",
            fontSize=12, strokeColor="#fbbf24",
        ))
    if "s3cost" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "s3cost", 257, 580,
            "Cost: ~$0.01/doc",
            fontSize=12, strokeColor="#f87171",
        ))

    # Percentage annotations
    if "s1pct" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "s1pct", 257, 210,
            "~40% classified here",
            fontSize=12, strokeColor="#94a3b8",
        ))
    if "s2pct" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "s2pct", 257, 405,
            "~30% classified here",
            fontSize=12, strokeColor="#94a3b8",
        ))
    if "s3pct" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "s3pct", 257, 595,
            "~30% remaining",
            fontSize=12, strokeColor="#94a3b8",
        ))

    # "Classified" label on the tall teal column
    if "classified_lbl" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "classified_lbl", 545, 78,
            "Classified",
            fontSize=16, strokeColor="#5eead4",
        ))

    # "Outputs" label on the outputs zone
    if "outputs_lbl" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "outputs_lbl", 800, 442,
            "Outputs",
            fontSize=16, strokeColor="#5eead4",
        ))

    # Arrow labels: "Match" / "No match"
    if "match1" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "match1", 447, 100,
            "Match",
            fontSize=11, strokeColor="#4ade80",
        ))
    if "nomatch1" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "nomatch1", 445, 185,
            "No match",
            fontSize=11, strokeColor="#ef4444",
        ))
    if "match2" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "match2", 447, 296,
            "Match",
            fontSize=11, strokeColor="#fbbf24",
        ))
    if "nomatch2" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "nomatch2", 445, 380,
            "No match",
            fontSize=11, strokeColor="#ef4444",
        ))
    if "match3" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "match3", 447, 492,
            "Match",
            fontSize=11, strokeColor="#f87171",
        ))

    # "Updates checklist" annotation on feedback arrow
    if "learn_note" not in existing_ids:
        missing_texts.append(make_standalone_text(
            "learn_note", 1020, 290,
            "Updates checklist\nfor next deal",
            fontSize=12, strokeColor="#a0a0a0",
        ))

    if missing_texts:
        data["elements"].extend(missing_texts)
        print(f"  Added {len(missing_texts)} standalone text elements to 02")

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    print("Fixing Excalidraw files...")

    # Step 1: Add missing standalone text to file 02
    add_missing_text_to_02()

    # Step 2: Fix all elements in all files (add missing properties)
    for name in [
        "01-aigis-overview.excalidraw",
        "02-agent-01-pipeline.excalidraw",
        "03-agent-04-waterfall.excalidraw",
        "04-architecture.excalidraw",
    ]:
        fix_file(DOCS / name)

    print("Done!")
