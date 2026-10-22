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
        fail(f"{path}: unsupported or malformed v1.154.2 header")
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
    if not isinstance(options, dict):
        fail("options section is not an object")
    burg_data = json_section(parts, 15)
    layers = json_section(parts, 50)
    states = json_section(parts, 13)
    provinces = json_section(parts, 14)
    if not isinstance(states, list) or not states or states[0].get("i") != 0 or states[0].get("name") != "Wildlands":
        fail("missing native neutral state 0 (Wildlands)")
    if not isinstance(provinces, list) or not provinces or provinces[0].get("i") != 0 or provinces[0].get("name") != "Neutrals":
        fail("missing native neutral province 0 (Neutrals)")
    burgs = [b for b in burg_data if isinstance(b, dict)]
    zones = json_section(parts, 38)
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
    required_burg_keys = {"cell", "x", "y", "i", "state", "culture", "name", "feature", "capital", "port", "population", "type", "coa", "citadel", "walls", "shanty", "temple", "group", "market", "plaza", "treasury", "product", "production"}
    bad_schema = [b.get("i") for b in burgs if set(b) != required_burg_keys]
    if bad_schema:
        fail(f"burgs do not match Vanilla v1.154.2 schema: {bad_schema[:10]}")
    bad_names = [b.get("i") for b in burgs if not b.get("name") or not b.get("group")]
    if bad_names:
        fail(f"burgs missing native name/group fields: {bad_names[:10]}")

    labels_options = options.get("labels")
    if not isinstance(labels_options, dict):
        fail("labels options section is not an object")
    city_label_groups = [g for g in labels_options.get("groups", []) if isinstance(g, dict) and g.get("name") == "city"]
    if len(city_label_groups) != 1:
        fail("missing unique Vanilla city label group")
    city_zoom = city_label_groups[0].get("zoom", {})
    if not isinstance(city_zoom, dict) or city_zoom.get("min", 999) > 1 or city_zoom.get("max", 0) < 1 or city_label_groups[0].get("isDefault") is not True:
        fail(f"city labels are not default-visible at initial zoom: {city_label_groups[0]}")

    if reference:
        ref_parts, ref_root = load_map(reference)
        for group_id in ("labels", "burgIcons"):
            actual_group = descendants(root, group_id)
            reference_group = descendants(ref_root, group_id)
            if not actual_group or not reference_group:
                fail(f"missing reference renderer group: #{group_id}")
            actual_children = {e.attrib["id"] for e in actual_group[0] if e.attrib.get("id")}
            reference_children = {e.attrib["id"] for e in reference_group[0] if e.attrib.get("id")}
            if actual_group[0].attrib.get("font-size") != reference_group[0].attrib.get("font-size"):
                fail(f"renderer root size differs from Vanilla reference: #{group_id}")
            if not reference_children <= actual_children:
                fail(f"renderer group #{group_id} is missing Vanilla child groups: {sorted(reference_children - actual_children)}")
            if group_id == "labels":
                actual_city = descendants(actual_group[0], "labels-city")
                reference_city = descendants(reference_group[0], "labels-city")
                if not actual_city or not reference_city or actual_city[0].attrib.get("font-size") != reference_city[0].attrib.get("font-size"):
                    fail("city label renderer size differs from Vanilla reference")

        def section_kind(value: str) -> tuple[str, str]:
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return ("raw", "")
            return ("json", type(parsed).__name__)

        # A matching section count is not enough: the Vanilla loader parses
        # specific positions as JSON. Compare the full section grammar.
        for index, (actual, expected) in enumerate(zip(parts, ref_parts)):
            if section_kind(actual) != section_kind(expected):
                fail(
                    f"section {index} grammar mismatch: "
                    f"got {section_kind(actual)}, reference has {section_kind(expected)}"
                )

        ref_ids = ids(ref_root)
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
