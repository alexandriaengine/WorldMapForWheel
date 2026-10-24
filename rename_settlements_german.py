#!/usr/bin/env python3
"""Give every settlement a unique, German, two-word race-based name."""
from __future__ import annotations

import hashlib
import itertools
import json
import random
import re
from pathlib import Path

MAP = Path("WorldMapForWheel.map")
REPORT = Path("settlement-network-generated.json")

GERMAN_WORDS = {
    0: (["Sumpf", "Schilf", "Moor", "Fluss", "Drachen", "Schuppen", "Regen", "Lagunen", "Nebel", "Kiesel", "Torf", "Kröten"], ["Wacht", "Krone", "Nest", "Auge", "Tor", "Hain", "Burg", "Pfad", "Furt", "Kamm", "Quelle", "Wall"]),
    1: (["Sturm", "Blut", "Frost", "Krieger", "Donner", "Wolf", "Eisen", "Stein", "Feuer", "Hoch", "Nord", "Klingen"], ["Lager", "Fang", "Feste", "Mark", "Hall", "Tor", "Grat", "Wacht", "Berg", "Schild", "Reich", "Wall"]),
    2: (["Gift", "Schlangen", "Nacht", "Viper", "Drachen", "Kiesel", "Schatten", "Spiral", "Fels", "Sumpf", "Silber", "Schuppen"], ["Zunge", "Nest", "Turm", "Grube", "Reich", "Hall", "Tor", "Krone", "Hain", "Kreis", "Wall", "Pfad"]),
    3: (["Rot", "Wolf", "Fang", "Wild", "Mond", "Jagd", "Kralle", "Bestien", "Fährten", "Moos", "Bären", "Fell"], ["Wald", "Höhle", "Nest", "Tal", "Lauf", "Tor", "Hain", "Reich", "Furt", "Kamm", "Wacht", "Pfad"]),
    4: (["Eisen", "Hammer", "Kupfer", "Stahl", "Runen", "Fels", "Gold", "Berg", "Granat", "Zinn", "Bronze", "Kohlen"], ["Schmiede", "Fall", "Hall", "Grat", "Tor", "Wacht", "Ader", "Feste", "Kamm", "Wall", "Burg", "Stollen"]),
    5: (["Silber", "Mond", "Stern", "Grün", "Elfen", "Lorien", "Blüten", "Dämmer", "Licht", "Glas", "Weiden", "Tannen"], ["Hain", "Tal", "Wald", "Turm", "Quelle", "Tor", "Garten", "Pfad", "Krone", "Furt", "Bucht", "Reich"]),
    6: (["Zahnrad", "Kupfer", "Messing", "Uhr", "Tüftler", "Funken", "Kessel", "Dampf", "Schrauben", "Flaschen", "Kiesel", "Werk"], ["Höhle", "Werk", "Fall", "Turm", "Reich", "Tor", "Nest", "Bau", "Hain", "Keller", "Wacht", "Furt"]),
    7: (["Mond", "Sonne", "Katzen", "Kralle", "Nacht", "Gold", "Puma", "Sphinx", "Samt", "Leoparden", "Morgen", "Schatten"], ["Pfote", "Tal", "Nest", "Reich", "Hain", "Tor", "Krone", "Wacht", "Furt", "Burg", "Kamm", "Garten"]),
    8: (["Tunnel", "Waben", "Ratten", "Mäuse", "Nest", "Krümel", "Bau", "Höhlen", "Käse", "Schatten", "Korn", "Nager"], ["Reich", "Nest", "Hall", "Wacht", "Bau", "Tor", "Tal", "Tiefe", "Keller", "Furt", "Wall", "Pfad"]),
    9: (["Grün", "Moos", "Apfel", "Hügel", "Wiesen", "Kleines", "Gutes", "Sommer", "Birnen", "Heide", "Auen", "Friedens"], ["Hügel", "Tal", "Furt", "Feld", "Hain", "Bau", "Dorf", "Wiese", "Garten", "Wacht", "Burg", "Quelle"]),
    10: (["Rot", "Gold", "Kronen", "Fluss", "Neu", "Hoch", "Königs", "Sonnen", "Silber", "Morgen", "Friedens", "Wasser"], ["Wald", "Tal", "Furt", "Hafen", "Tor", "Reich", "Krone", "Feld", "Burg", "Hain", "Markt", "Wacht"]),
    11: (["Tiefen", "Basalt", "Dunkel", "Schwarz", "Runen", "Asche", "Grau", "Grollen", "Magma", "Fels", "Kohlen", "Erd"], ["Tor", "Hall", "Grat", "Schmiede", "Wacht", "Ader", "Wall", "Stollen", "Burg", "Kammer", "Feste", "Grund"]),
    12: (["Rot", "Grau", "Wolf", "Hunde", "Bären", "Wachen", "Mond", "Stein", "Jagd", "Fährten", "Rudel", "Treue"], ["Tor", "Höhle", "Furt", "Wacht", "Reich", "Tal", "Nest", "Hall", "Burg", "Pfad", "Hain", "Wall"]),
    13: (["Schatten", "Nacht", "Dunkel", "Schwarz", "Grau", "Unter", "Gift", "Umbra", "Spinnen", "Klingen", "Dämmer", "Leichen"], ["Hain", "Schleier", "Turm", "Tiefe", "Tor", "Tal", "Nest", "Hof", "Kreis", "Wall", "Burg", "Pfad"]),
    14: (["Blut", "Knochen", "Eisen", "Kriegs", "Schädel", "Schwarz", "Rot", "Doom", "Donner", "Grimm", "Feuer", "Klingen"], ["Feste", "Tor", "Grat", "Lager", "Klippe", "Burg", "Mark", "Hall", "Wall", "Wacht", "Reich", "Pfad"]),
    15: (["Korallen", "Perlen", "Blau", "Gezeiten", "Riff", "Lagunen", "See", "Wasser", "Muschel", "Fluss", "Strömungs", "Salz"], ["Hafen", "Reich", "Fall", "Tor", "Bucht", "Tal", "Hall", "Furt", "Krone", "Hain", "Wacht", "Pfad"]),
    16: (["Stern", "Hoch", "Sonnen", "Morgen", "Silber", "Himmels", "Äther", "Licht", "Gold", "Wolken", "Dämmer", "Kristall"], ["Krone", "Turm", "Tal", "Hafen", "Reich", "Hain", "Tor", "Wacht", "Furt", "Garten", "Burg", "Quelle"]),
    17: (["Runen", "Arkan", "Zauber", "Mystik", "Mana", "Raben", "Stern", "Hexen", "Kristall", "Geister", "Magier", "Weisen"], ["Turm", "Hall", "Tor", "Reich", "Kreis", "Hafen", "Wacht", "Burg", "Quelle", "Hain", "Pfad", "Krone"]),
    18: (["Morgen", "Grün", "Silber", "Brücken", "West", "Stern", "Dämmer", "Zwischen", "Auen", "Friedens", "Wander", "Sonnen"], ["Brücke", "Tal", "Furt", "Hain", "Reich", "Hafen", "Tor", "Wacht", "Burg", "Quelle", "Pfad", "Garten"]),
    19: (["Rot", "Grün", "Wurzel", "Eichen", "Blatt", "Dorn", "Moos", "Wald", "Birken", "Farn", "Blüten", "Baum"], ["Wald", "Herz", "Hain", "Grove", "Holz", "Turm", "Tor", "Tal", "Quelle", "Wacht", "Pfad", "Krone"]),
}

def make_name(race: int, key: str, used: set[str]) -> str:
    first, second = GERMAN_WORDS[race]
    pairs = list(itertools.product(first, second))
    random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)).shuffle(pairs)
    for a, b in pairs:
        name = f"{a} {b}"
        if name not in used:
            used.add(name)
            return name
    raise RuntimeError(f"no unused two-word German name left for race {race}")

def main() -> None:
    parts = MAP.read_bytes().decode().split("\r\n")
    burgs = json.loads(parts[15])
    report = json.loads(REPORT.read_text())
    used = {b["name"] for b in burgs if isinstance(b, dict) and int(b.get("i", 0)) <= 154}
    old_to_new = {}
    meta = {s["name"]: s for s in report["settlements"]}
    for burg in burgs:
        if not isinstance(burg, dict) or int(burg.get("i", 0)) <= 154:
            continue
        old = burg["name"]
        item = meta[old]
        race = int(item.get("name_race_id", item["race_ids"][0]))
        name = make_name(race, old, used)
        burg["name"] = name
        burg["label"] = {"text": name, "group": burg.get("label", {}).get("group", "city")}
        item["name"] = name
        old_to_new[old] = name
    routes = json.loads(parts[37])
    for route in routes:
        route_name = str(route.get("name", ""))
        if route_name.startswith("Weg "):
            detail = next((d for d in report.get("routes", {}).get("details", []) if int(d["route"]) == int(route.get("i", -1))), None)
            if detail:
                route["name"] = f"Weg {old_to_new.get(detail['settlement'], detail['settlement'])}"
    parts[15] = json.dumps(burgs, separators=(",", ":"), ensure_ascii=False)
    parts[37] = json.dumps(routes, separators=(",", ":"), ensure_ascii=False)
    MAP.write_bytes("\r\n".join(parts).encode())
    report["settlements_named"] = len(report["settlements"])
    report["settlements"] = list(meta.values())
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"settlements_named": len(meta), "unique_names": len(used)}))

if __name__ == "__main__":
    main()
