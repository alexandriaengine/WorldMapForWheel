#!/usr/bin/env python3
"""Add native-style land trails from each settlement to its protection-center burg.

The path cost mirrors Azgaar's routes-generator.ts getLandPathCost: water and
uninhabitable cells are blocked; distance, habitability, elevation, existing
connections, and burg presence affect the A* cost. The map's square grid is
used as the serialized grid graph because the .map file does not persist the
runtime packed adjacency arrays.
"""
from __future__ import annotations

import heapq
import json
import math
from pathlib import Path

MAP = Path("WorldMapForWheel.map")
GENERATED = Path("settlement-network-generated.json")
SCALE = 4.828032
RADIUS_MARGIN = 0.25
WIDTH = 408
HEIGHT = 245


def parse_map() -> list[str]:
    raw = MAP.read_bytes()
    if raw.count(b"\r\n") != 52:
        raise ValueError("map must retain 52 CRLF section delimiters")
    return raw.decode("utf-8").split("\r\n")


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def neighbors(cell: int) -> list[int]:
    row, col = divmod(cell, WIDTH)
    result = []
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            if not dr and not dc:
                continue
            if dr * dr + dc * dc > 4:
                continue
            nr, nc = row + dr, col + dc
            if 0 <= nr < HEIGHT and 0 <= nc < WIDTH:
                result.append(nr * WIDTH + nc)
    return result


def point_xy(points: list[list[float]], cell: int) -> tuple[float, float]:
    return float(points[cell][0]), float(points[cell][1])


def land_cost(
    current: int,
    next_cell: int,
    points: list[list[float]],
    heights: list[int],
    biomes: list[int],
    habitability: list[float],
    known_connections: set[tuple[int, int]],
    burg_cells: set[int],
) -> float:
    if heights[next_cell] < 20:
        return math.inf
    hab = habitability[biomes[next_cell]] if 0 <= biomes[next_cell] < len(habitability) else 0
    if not hab:
        return math.inf
    dx = points[current][0] - points[next_cell][0]
    dy = points[current][1] - points[next_cell][1]
    distance_cost = dx * dx + dy * dy
    habitability_modifier = 1 + max(100 - hab, 0) / 1000
    height_modifier = 1 + max(heights[next_cell] - 25, 25) / 25
    connection_modifier = 0.5 if (current, next_cell) in known_connections else 1
    burg_modifier = 1 if next_cell in burg_cells else 3
    return distance_cost * habitability_modifier * height_modifier * connection_modifier * burg_modifier


def find_path(
    start: int,
    target: int,
    center: tuple[float, float],
    radius: float,
    points: list[list[float]],
    heights: list[int],
    biomes: list[int],
    habitability: list[float],
    known_connections: set[tuple[int, int]],
    burg_cells: set[int],
) -> list[int] | None:
    if start == target:
        return None
    limit = radius - RADIUS_MARGIN
    if distance(point_xy(points, start), center) >= limit or distance(point_xy(points, target), center) >= limit:
        return None
    frontier: list[tuple[float, int]] = [(0.0, start)]
    costs = {start: 0.0}
    previous: dict[int, int] = {}
    while frontier:
        current_cost, current = heapq.heappop(frontier)
        if current_cost != costs.get(current):
            continue
        if current == target:
            path = [current]
            while path[-1] != start:
                path.append(previous[path[-1]])
            return list(reversed(path))
        for next_cell in neighbors(current):
            if distance(point_xy(points, next_cell), center) >= limit:
                continue
            step = land_cost(
                current,
                next_cell,
                points,
                heights,
                biomes,
                habitability,
                known_connections,
                burg_cells,
            )
            if math.isinf(step):
                continue
            next_cost = current_cost + step
            if next_cost >= costs.get(next_cell, math.inf):
                continue
            costs[next_cell] = next_cost
            previous[next_cell] = current
            heuristic = distance(point_xy(points, next_cell), point_xy(points, target)) ** 2
            heapq.heappush(frontier, (next_cost + heuristic, next_cell))
    return None


def main() -> None:
    parts = parse_map()
    options = json.loads(parts[1])
    graph = json.loads(parts[6])
    burgs = json.loads(parts[15])
    routes = json.loads(parts[37])
    generated = json.loads(GENERATED.read_text())
    points = graph["points"]
    heights = [int(value) for value in parts[7].split(",")]
    biomes = [0] * len(points)
    habitability = [100.0]
    centers = {burg["name"]: burg for burg in burgs if isinstance(burg, dict) and not burg["name"].startswith("Settlement-")}
    for burg in burgs:
        if isinstance(burg, dict) and burg.get("name", "").startswith("Settlement-"):
            burg["group"] = "fort"
            burg["label"] = {"text": burg["name"], "group": "city"}
    routes_by_center = {route["name"].replace("Schutzkreis ", ""): route for route in routes}
    known_connections = set()
    route_cells = json.loads(parts[36])
    for source, links in route_cells.items():
        for target in links:
            known_connections.add((int(source), int(target)))
    burg_cells: set[int] = set()
    for name, burg in centers.items():
        burg_cells.add(min(range(len(points)), key=lambda i: distance(tuple(points[i]), (burg["x"], burg["y"]))))
    for settlement in generated["settlements"]:
        burg_cells.add(int(settlement["grid_cell"]))

    routes = [route for route in routes if not str(route.get("name", "")).startswith("Settlement trail ")]
    next_route_id = max((int(route.get("i", -1)) for route in routes), default=-1) + 1
    routes_added = []
    skipped = []
    settlements_by_center: dict[str, list[dict]] = {}
    for settlement in generated["settlements"]:
        settlements_by_center.setdefault(settlement["center"], []).append(settlement)

    for center_name, settlements in settlements_by_center.items():
        center = centers[center_name]
        center_cell = min(range(len(points)), key=lambda i: distance(tuple(points[i]), (center["x"], center["y"])))
        route_radius = float(routes_by_center[center_name]["radiusKm"]) / float(options["units"]["distance"]["scale"])
        center_xy = (float(center["x"]), float(center["y"]))
        for settlement in settlements:
            start = int(settlement["grid_cell"])
            path = find_path(
                start,
                center_cell,
                center_xy,
                route_radius,
                points,
                heights,
                biomes,
                habitability,
                known_connections,
                burg_cells,
            )
            if path and len(path) == 2:
                start, target = path
                sx, sy = points[start]
                tx, ty = points[target]
                direct = math.hypot(tx - sx, ty - sy)
                bends = []
                for bend in neighbors(start):
                    if bend == target or heights[bend] < 20 or distance(point_xy(points, bend), center_xy) >= route_radius - RADIUS_MARGIN:
                        continue
                    bx, by = points[bend]
                    bend_distance = math.hypot(bx - tx, by - ty)
                    if bend_distance > direct * 1.8:
                        continue
                    cross = abs((bx - sx) * (ty - sy) - (by - sy) * (tx - sx))
                    bends.append((-(cross), bend_distance, bend))
                if bends:
                    path = [start, min(bends)[2], target]
                else:
                    path = None
            if not path:
                skipped.append({"center": center_name, "settlement": settlement["name"], "reason": "no non-straight land path"})
                continue
            route_id = next_route_id
            next_route_id += 1
            route_points = [[round(points[cell][0], 3), round(points[cell][1], 3), cell] for cell in path]
            routes.append(
                {
                    "i": route_id,
                    "group": "trails",
                    "feature": int(center.get("feature", 0)),
                    "points": route_points,
                }
            )
            for left, right in zip(path, path[1:]):
                route_cells.setdefault(str(left), {})[str(right)] = route_id
                route_cells.setdefault(str(right), {})[str(left)] = route_id
                known_connections.add((left, right))
                known_connections.add((right, left))
            routes_added.append(
                {
                    "route": route_id,
                    "center": center_name,
                    "settlement": settlement["name"],
                    "points": len(path),
                    "group": "trails",
                }
            )

    valid_route_ids = {int(route.get("i", -1)) for route in routes}
    route_cells = {
        str(cell): {str(neighbor): int(route_id) for neighbor, route_id in links.items() if int(route_id) in valid_route_ids}
        for cell, links in route_cells.items()
        if isinstance(links, dict)
        and any(int(route_id) in valid_route_ids for route_id in links.values())
    }
    parts[15] = json.dumps(burgs, separators=(",", ":"), ensure_ascii=False)
    parts[36] = json.dumps(route_cells, separators=(",", ":"), ensure_ascii=False)
    parts[37] = json.dumps(routes, separators=(",", ":"), ensure_ascii=False)
    MAP.write_bytes("\r\n".join(parts).encode("utf-8"))
    generated["routes"] = {
        "algorithm": "Azgaar routes-generator.ts getLandPathCost mirrored over serialized grid",
        "group": "trails",
        "rule": "each settlement connects only to its own protection-center burg",
        "added": len(routes_added),
        "skipped": skipped,
        "details": routes_added,
    }
    GENERATED.write_text(json.dumps(generated, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"added": len(routes_added), "skipped": len(skipped), "centers": len(set(item["center"] for item in routes_added))}))


if __name__ == "__main__":
    main()
