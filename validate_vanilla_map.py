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
FORBIDDEN_IDS = {"cityNames", "protectionBorders"}
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
    if b"\r" in raw.replace(b"\r\n", b""):
        fail(f"{path}: contains a lone CR line ending")
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
    distance_units = options.get("units", {}).get("distance", {})
    if distance_units.get("unit") != "km" or abs(float(distance_units.get("scale", 0)) - 4.828032) > 1e-9:
        fail("map distance scale is not configured in kilometres")
    burg_data = json_section(parts, 15)
    layers = json_section(parts, 50)
    religions = json_section(parts, 29)
    provinces_runtime = json_section(parts, 30)
    if not isinstance(religions, list) or not religions or religions[0].get("i") != 0 or religions[0].get("name") != "No religion":
        fail("missing native neutral religion 0 (No religion)")
    if not isinstance(provinces_runtime, list) or len(provinces_runtime) < 2 or provinces_runtime[0] != 0:
        fail("missing native runtime province table")
    cultures = json_section(parts, 13)
    states = json_section(parts, 14)
    if not isinstance(cultures, list) or len(cultures) < 2 or cultures[0].get("i") != 0 or cultures[1].get("i") != 1:
        fail("missing native culture 0/1 tables")
    if not isinstance(states, list) or not states or states[0].get("i") != 0 or states[0].get("name") != "Neutrals":
        fail("missing native neutral state 0")
    burgs = [b for b in burg_data if isinstance(b, dict)]
    zones = json_section(parts, 38)
    try:
        cell_burg = [int(v) for v in parts[17].split(",") if v != ""]
    except ValueError:
        fail("section 17 contains invalid cell-burg values")
    land_cell_count = len([v for v in parts[16].split(",") if v != ""])
    if len(cell_burg) != land_cell_count:
        fail("section 17 cell-burg length does not match land-cell array")
    bad_cell_links = [b.get("i") for b in burgs if not 0 <= int(b.get("cell", -1)) < len(cell_burg) or cell_burg[int(b["cell"])] != b.get("i")]
    if bad_cell_links:
        fail(f"burg cell links are missing or incorrect: {bad_cell_links[:10]}")
    try:
        cell_culture = [int(v) for v in parts[19].split(",") if v != ""]
        cell_state = [int(v) for v in parts[25].split(",") if v != ""]
    except ValueError:
        fail("section 19 contains invalid cell-state values")
    bad_state_links = [b.get("i") for b in burgs if int(b.get("state", 0)) != 0 or int(b.get("cell", -1)) >= len(cell_state) or cell_state[int(b["cell"])] != 0]
    if bad_state_links:
        fail(f"burg state links are missing or incorrect: {bad_state_links[:10]}")
    bad_culture_links = [b.get("i") for b in burgs if int(b.get("culture", 0)) != 1 or int(b.get("cell", -1)) >= len(cell_culture) or cell_culture[int(b["cell"])] != 1]
    if bad_culture_links:
        fail(f"burg culture links are missing or incorrect: {bad_culture_links[:10]}")
    if not burgs:
        fail("no native burg records in section 15")
    if not REQUIRED_ACTIVE_LAYERS <= set(layers.get("active", [])):
        fail(f"required active layers missing: {REQUIRED_ACTIVE_LAYERS - set(layers.get('active', []))}")
    if set(layers.get("active", [])) & {"states", "borders", "zones"}:
        fail("states, borders and zones must be inactive for label-only baseline")
    if zones:
        fail("zones must be empty for native protection routes")
    routes = json_section(parts, 37)
    protection_routes = [r for r in routes if isinstance(r, dict) and str(r.get("name", "")).startswith("Schutzkreis ")]
    center_burgs = [b for b in burgs if not str(b.get("name", "")).startswith("Settlement-")]
    protection_names = {str(r.get("name", ""))[len("Schutzkreis "):] for r in protection_routes}
    center_names = {b.get("name") for b in center_burgs}
    if len(protection_routes) != len(center_burgs) or protection_names != center_names:
        fail("native protection routes do not match protection-center burgs")
    if any(
        len(r.get("points", [])) != 73
        or r["points"][0] != r["points"][-1]
        or float(r.get("radiusKm", 0)) < 50
        for r in protection_routes
    ):
        fail("native protection routes are missing, open, or have invalid radii")
    settlement_routes = [r for r in routes if isinstance(r, dict) and not str(r.get("name", "")).startswith("Schutzkreis ")]
    if any(r.get("group") != "trails" or len(r.get("points") or []) < 2 for r in settlement_routes):
        fail("settlement routes are not native land trails")
    route_ids = {int(r.get("i")) for r in routes if isinstance(r, dict)}
    route_cells = json_section(parts, 36)
    if not isinstance(route_cells, dict):
        fail("section 36 route index is not an object")
    if any(
        int(route_id) not in route_ids
        for entry in route_cells.values()
        for route_id in (entry if isinstance(entry, dict) else {}).values()
    ):
        fail("section 36 contains orphaned route references")

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
    if not native_labels:
        fail("no native burg labels in saved renderer")
    native_icons = [e for e in root.iter() if e.tag.endswith("use") and e.attrib.get("data-id")]
    if not native_icons:
        fail("no native burg icon uses found")
    circles = [e for e in root.iter() if e.tag.endswith("circle") and e.attrib.get("id", "").startswith("protectionCircle")]
    if circles and (len(circles) != len(burgs) or any(abs(float(c.attrib.get("r", "nan")) - 24.854847689493358) > 1e-6 for c in circles)):
        fail("SVG protection circles do not match 120 km radius")
    valid_groups = {g.get("name") for g in options.get("burgs", {}).get("groups", [])}
    bad_groups = sorted({b.get("group") for b in burgs if b.get("group") not in valid_groups})
    if bad_groups:
        fail(f"burgs use unregistered Vanilla groups: {bad_groups}")
    required_burg_keys = {"cell", "x", "y", "i", "state", "culture", "name", "feature", "capital", "port", "population", "type", "coa", "citadel", "walls", "shanty", "temple", "group", "market", "plaza", "treasury", "product", "production"}
    allowed_burg_keys = required_burg_keys | {"label"}
    bad_schema = [b.get("i") for b in burgs if not required_burg_keys <= set(b) or not set(b) <= allowed_burg_keys]
    if bad_schema:
        fail(f"burgs do not match Vanilla v1.154.2 schema: {bad_schema[:10]}")
    bad_names = [b.get("i") for b in burgs if not b.get("name") or not b.get("group") or not isinstance(b.get("population"),(int,float)) or b.get("population") <= 0]
    if bad_names:
        fail(f"burgs missing visible name/group/population fields: {bad_names[:10]}")
    if any(b.get("state") != 0 for b in burgs):
        fail("burgs must remain in neutral state when political layers are disabled")

    labels_options = options.get("labels")
    if not isinstance(labels_options, dict):
        fail("labels options section is not an object")
    city_label_groups = [g for g in labels_options.get("groups", []) if isinstance(g, dict) and g.get("name") == "city"]
    if len(city_label_groups) != 1:
        fail("missing unique Vanilla city label group")
    city_zoom = city_label_groups[0].get("zoom", {})
    city_min = city_zoom.get("min") if isinstance(city_zoom, dict) else None
    city_max = city_zoom.get("max") if isinstance(city_zoom, dict) else None
    if not isinstance(city_zoom, dict) or (city_min is not None and city_min > 1) or (city_max is not None and city_max < 1) or city_label_groups[0].get("isDefault") is not True:
        fail(f"city labels are not default-visible at initial zoom: {city_label_groups[0]}")

    if reference:
        ref_parts, ref_root = load_map(reference)
        runtime_styles = json_section(parts, 48)
        reference_styles = json_section(ref_parts, 48)
        if runtime_styles.get("labels") != reference_styles.get("labels") or runtime_styles.get("burgIcons") != reference_styles.get("burgIcons"):
            fail("labels/burgIcons runtime styles differ from Vanilla reference")
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
        for required in ("viewbox", "deftemp", "textPaths", "burgIcons", "labels", "borders", "routes"):
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
