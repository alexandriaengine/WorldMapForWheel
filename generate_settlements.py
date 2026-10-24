#!/usr/bin/env python3
"""Generate race-pattern settlements inside native protection circles."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

MAP = Path("WorldMapForWheel.map")
PLAN = Path("settlement-network-plan.json")
OUTPUT = Path("settlement-network-generated.json")
SCALE = 4.828032
MIN_RADIUS_MARGIN = 0.25
MIN_SEPARATION = 2.2


def parse_map() -> list[str]:
    raw = MAP.read_bytes()
    if raw.count(b"\r\n") != 52:
        raise ValueError("map must retain 52 CRLF section delimiters")
    return raw.decode("utf-8").split("\r\n")


def stable_fraction(text: str) -> float:
    return int(hashlib.sha256(text.encode()).hexdigest()[:12], 16) / 16**12


def pattern_point(strategy: str, index: int, total: int, radius: float, seed: float) -> tuple[float, float]:
    angle = 2 * math.pi * index / total + seed * 0.37
    fraction = 0.42 + 0.42 * ((index % 3) / 2)
    if "Delta" in strategy or "Feuchtgebiet" in strategy:
        angle += 0.32 * math.sin(index)
        fraction = 0.35 + 0.48 * ((index % 4) / 3)
    elif "Halbmond" in strategy or "Kette" in strategy:
        angle = math.pi * (index + 1) / (total + 1) + seed
        fraction = 0.55 + 0.25 * (index % 2)
    elif "Hexagonal" in strategy or "Netz" in strategy or "Knoten" in strategy:
        fraction = 0.38 + 0.22 * (index % 3)
    elif "Achteck" in strategy:
        angle = 2 * math.pi * index / 8 + seed
        fraction = 0.58 + 0.18 * (index // 8)
    elif "Spiral" in strategy or "Spiralf" in strategy:
        angle += index * 0.48
        fraction = 0.25 + 0.58 * (index + 1) / total
    elif "Stern" in strategy:
        angle = 2 * math.pi * (index % 8) / 8 + seed
        fraction = 0.48 + 0.38 * (index // 8)
    elif "Doppel" in strategy:
        angle = (math.pi if index % 2 else 0.0) + math.pi * (index // 2 + 1) / (total // 2 + 1) + seed
        fraction = 0.45 + 0.32 * (index % 2)
    elif "Lin" in strategy:
        angle = seed + (index - (total - 1) / 2) * 0.22
        fraction = 0.34 + 0.5 * index / max(1, total - 1)
    return radius * fraction * math.cos(angle), radius * fraction * math.sin(angle)


def choose_candidates(
    center: dict,
    route: dict,
    points: list[list[float]],
    heights: list[int],
    occupied: list[tuple[float, float]],
    count: int,
    strategy: str,
) -> list[tuple[int, float, float]]:
    radius = float(route["radiusKm"]) / SCALE
    candidates = []
    for grid_cell, (x, y) in enumerate(points):
        if heights[grid_cell] < 20:
            continue
        distance = math.hypot(x - center["x"], y - center["y"])
        if distance >= radius - MIN_RADIUS_MARGIN:
            continue
        if any(math.hypot(x - ox, y - oy) < MIN_SEPARATION for ox, oy in occupied):
            continue
        candidates.append((grid_cell, x, y, distance))
    if len(candidates) < count:
        raise ValueError(f"{center['name']}: only {len(candidates)} valid land cells, need {count}")

    seed = stable_fraction(center["name"])
    selected: list[tuple[int, float, float]] = []
    remaining = candidates[:]
    for index in range(count):
        ideal_x, ideal_y = pattern_point(strategy, index, count, radius, seed)
        scored = sorted(
            remaining,
            key=lambda item: math.hypot(
                item[1] - (center["x"] + ideal_x), item[2] - (center["y"] + ideal_y)
            ),
        )
        chosen = scored[0]
        selected.append((chosen[0], chosen[1], chosen[2]))
        remaining = [item for item in remaining if item[0] != chosen[0]]
    return selected


def main() -> None:
    parts = parse_map()
    options = json.loads(parts[1])
    graph = json.loads(parts[6])
    features = json.loads(parts[12])
    burgs = json.loads(parts[15])
    routes = json.loads(parts[37])
    plan = json.loads(PLAN.read_text())
    plan_by_name = {entry["center"]: entry for entry in plan["centers"]}
    centers = [burg for burg in burgs if isinstance(burg, dict)]
    route_by_name = {route["name"].replace("Schutzkreis ", ""): route for route in routes}
    heights = [int(value) for value in parts[7].split(",")]
    if len(heights) != len(graph["points"]):
        raise ValueError("grid point and height arrays differ")
    land_features = [feature["i"] for feature in features if isinstance(feature, dict) and feature.get("land")]
    if not land_features:
        raise ValueError("no land feature available")

    pack_cell_count = len([value for value in parts[16].split(",") if value != ""])
    cell_burg = [int(value) for value in parts[17].split(",") if value != ""]
    free_cells = [index for index, burg_id in enumerate(cell_burg) if burg_id == 0]
    if len(free_cells) < 2 * len(centers):
        raise ValueError("not enough free native pack cells")
    occupied = [(float(center["x"]), float(center["y"])) for center in centers]
    new_settlements: list[dict] = []
    skipped_centers: list[dict] = []
    next_burg_id = max(int(center["i"]) for center in centers) + 1
    new_cell_index = 0
    template = dict(centers[0])
    for center in centers:
        plan_entry = plan_by_name.get(center["name"])
        if not plan_entry:
            raise ValueError(f"missing race strategy for {center['name']}")
        strategy = plan_entry["strategy"]
        available_hint = int(2 + stable_fraction(center["name"] + ":count") * 11)
        radius = float(route_by_name[center["name"]]["radiusKm"]) / SCALE
        count_candidates = sum(
            1
            for grid_cell, (x, y) in enumerate(graph["points"])
            if heights[grid_cell] >= 20
            and math.hypot(x - center["x"], y - center["y"]) < radius - MIN_RADIUS_MARGIN
            and all(math.hypot(x - ox, y - oy) >= MIN_SEPARATION for ox, oy in occupied)
        )
        count = min(available_hint, count_candidates)
        if count < 2:
            skipped_centers.append(
                {
                    "center": center["name"],
                    "strategy": strategy,
                    "valid_land_cells": count_candidates,
                    "reason": "fewer than 2 land cells strictly inside the protection circle",
                }
            )
            continue
        chosen = choose_candidates(center, route_by_name[center["name"]], graph["points"], heights, occupied, count, strategy)
        for grid_cell, x, y in chosen:
            pack_cell = free_cells[new_cell_index]
            new_cell_index += 1
            name = f"Settlement-{next_burg_id:04X}"
            record = dict(template)
            record.update(
                {
                    "i": next_burg_id,
                    "cell": pack_cell,
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "state": 0,
                    "culture": 1,
                    "name": name,
                    "capital": 0,
                    "port": 0,
                    "population": 1,
                    "feature": land_features[0],
                    "group": "fort",
                    "label": {"text": name, "group": "fort"},
                }
            )
            burgs.append(record)
            cell_burg[pack_cell] = next_burg_id
            new_settlements.append(
                {
                    "name": name,
                    "center": center["name"],
                    "race_ids": plan_entry["race_ids"],
                    "dominant_race": plan_entry["dominant_race"],
                    "strategy": strategy,
                    "grid_cell": grid_cell,
                    "cell": pack_cell,
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "radius_km": round(float(route_by_name[center["name"]]["radiusKm"]), 3),
                    "land": True,
                }
            )
            occupied.append((x, y))
            next_burg_id += 1

    parts[15] = json.dumps(burgs, separators=(",", ":"), ensure_ascii=False)
    parts[16] = ",".join(parts[16].split(","))
    parts[17] = ",".join(map(str, cell_burg))
    parts[19] = ",".join("1" if value else "0" for value in parts[19].split(","))
    parts[20] = ",".join("0" for _ in parts[20].split(","))
    MAP.write_bytes("\r\n".join(parts).encode("utf-8"))
    OUTPUT.write_text(
        json.dumps(
            {
                "version": 2,
                "centers": len(centers),
                "new_settlements": len(new_settlements),
                "range": [2, 12],
                "criteria": ["strictly inside native protection circle", "grid height >= 20 (land)", "race strategy pattern"],
                "skipped_centers": skipped_centers,
                "settlements": new_settlements,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(json.dumps({"centers": len(centers), "new_settlements": len(new_settlements)}))


if __name__ == "__main__":
    main()
