#!/usr/bin/env python3
"""Strict validator for Azgaar Fantasy Map Generator 1.154.2 saves.

This validates the serialized map and the rendered Vanilla SVG skeleton.
It intentionally rejects custom city-name/circle overlays for this project.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED_SECTIONS = 53
EXPECTED_CRLF = 52
REQUIRED_ACTIVE_LAYERS = {"burgIcons", "labels"}
FORBIDDEN_IDS = {"cityNames", "protectionCircles", "protectionBorders"}
SVG_NS = "{http://www.w3.org/2000/svg}"


def fail(message: str) -> None:
    raise ValueError(message)


def load_map(path: Path) -> tuple[list[str], ET.Element]:
    raw = path.read_bytes()
    if b"\r\n" not in raw:
        fail(f"{path}: map has no CRLF section delimiters")
    crlf_count = raw.count(b"\r\n")
    if crlf_count != EXPECTED_CRLF:
        fail(f"{path}: expected {EXPECTED_CRLF} CRLF delimiters, got {crlf_count}")
    parts = raw.decode("utf-8").split("\r\n")
    if len(parts) != EXPECTED_SECTIONS:
        fail(f"{path}: expected {EXPECTED_SECTIONS} sections, got {len(parts)}")
    if not parts[0].startswith("1.154.2|File can be loaded in azgaar.github.io/Fantasy-Map-Generator|"):
        fail(f"{path}: unsupported or malformed header")
    try:
        root = ET.fromstring(parts[5])
    except ET.ParseError as exc:
        fail(f"{path}: embedded SVG is invalid: {exc}")
    return parts, root


def json_section(parts: list[str], index: int):
    try:
        return json.loads(parts[index])
    except json.JSONDecodeError as exc:
        fail(f"section {index}: invalid JSON: {exc}")


def ids(root: ET.Element) -> set[str]:
    return {e.attrib["id"] for e in root.iter() if "id" in e.attrib}


def descendants(root: ET.Element, wanted: str) -> list[ET.Element]:
    return [e for e in root.iter() if e.attrib.get("id") == wanted]


def validate(path: Path, reference: Path | None) -> dict[str, int]:
    parts, root = load_map(path)
    options = json_section(parts, 1)
    burg_data = json_section(parts, 15)
    layers = json_section(parts, 50)
    zones = json_section(parts, 38)
    burgs = [b for b in burg_data if isinstance(b, dict)]
    if not burgs:
        fail("no native burg records in section 15")
    if not REQUIRED_ACTIVE_LAYERS <= set(layers.get("active", [])):
        fail(f"required active layers missing: {REQUIRED_ACTIVE_LAYERS - set(layers.get('active', []))}")
    if zones:
        fail(f"unexpected serialized zones: {len(zones)}; this project uses no continent zones")

    all_ids = ids(root)
    forbidden = sorted(FORBIDDEN_IDS & all_ids)
    if forbidden:
        fail(f"custom overlay IDs are forbidden: {', '.join(forbidden)}")
    if not descendants(root, "burgIcons"):
        fail("missing native #burgIcons group")
    labels_matches = descendants(root, "labels")
    if not labels_matches:
        fail("missing native #labels group")
    labels = labels_matches[0]
    native_labels = [e for e in labels.iter() if e.attrib.get("data-label-type") == "burg"]
    if len(native_labels) != len(burgs):
        fail(f"native burg label count {len(native_labels)} != burg record count {len(burgs)}")
    native_icons = [e for e in root.iter() if e.tag.endswith("use") and e.attrib.get("data-id")]
    if not native_icons:
        fail("no native burg icon uses found")
    valid_groups = {g.get("name") for g in options.get("burgs", {}).get("groups", [])}
    bad_groups = sorted({b.get("group") for b in burgs if b.get("group") not in valid_groups})
    if bad_groups:
        fail(f"burgs use unregistered Vanilla groups: {bad_groups}")

    if reference:
        ref_parts, ref_root = load_map(reference)

        def section_kind(value: str) -> tuple[str, str]:
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return ("raw", "")
            return ("json", type(parsed).__name__)

        # A matching section count is not enough: the Vanilla loader parses
        # specific positions as JSON. Compare the full section grammar so a
        # raw font/string section can never slide into a JSON slot again.
        for index, (actual, expected) in enumerate(zip(parts, ref_parts)):
            if section_kind(actual) != section_kind(expected):
                fail(
                    f"section {index} grammar mismatch: "
                    f"got {section_kind(actual)}, reference has {section_kind(expected)}"
                )

        ref_ids = ids(ref_root)
        # The reference may have different generated geography, but the renderer
        # skeleton must contain the same registered layer containers.
        for required in ("viewbox", "burgIcons", "labels", "borders", "routes"):
            if required in ref_ids and required not in all_ids:
                fail(f"missing reference renderer container: #{required}")

    return {
        "burgs": len(burgs),
        "native_labels": len(native_labels),
        "native_icons": len(native_icons),
        "zones": len(zones),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("map", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.map, args.reference)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS", json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
