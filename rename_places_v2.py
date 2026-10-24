#!/usr/bin/env python3
"""Use famous place names for capitals and two-word race-based settlement names."""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from pathlib import Path

MAP = Path("WorldMapForWheel.map")
REPORT = Path("settlement-network-generated.json")
PLAN = Path("settlement-network-plan.json")
FIXED_IDS = {152: "Terra", 153: "Eisenschmiede", 154: "Yggdrasil"}
FIXED_NAMES = set(FIXED_IDS.values())

CAPITAL_NAMES = [
    "Agrabah", "Atlantis", "Hyrule", "Alexandria", "Babylon", "Alfheim", "Olympus", "Hogwarts", "Camelot", "Avalon",
    "Valhalla", "Asgard", "Midgard", "Troy", "Sparta", "Athens", "Thebes", "Ithaca", "Elysium", "Arcadia", "Erebor",
    "Moria", "Rivendell", "Lothlorien", "Gondor", "Mordor", "Minas Tirith", "Hobbiton", "Bree", "Narnia", "Cair Paravel",
    "Emerald City", "Oz", "Neverland", "Wonderland", "Panem", "Arrakis", "Krypton", "Tatooine", "Coruscant", "Naboo",
    "Alderaan", "Wakanda", "Gotham", "Metropolis", "Xandar", "Rapture", "Midgar", "Novigrad", "Whiterun", "Solitude",
    "Windhelm", "Dalaran", "Stormwind", "Orgrimmar", "Ironforge", "Silvermoon", "Skyrim", "Morrowind", "Cyrodiil", "Riften",
    "Balmora", "Vivec", "Denerim", "Kirkwall", "Thedas", "Kaer Morhen", "Toussaint", "Velen", "Skellige", "Dunwall",
    "Rapture", "Columbia", "Silent Hill", "Night City", "Los Santos", "Vice City", "Haven", "Bright Falls", "Twin Peaks", "Hill Valley",
    "Mos Eisley", "Cloud City", "Mustafar", "Endor", "Dagobah", "Kashyyyk", "Bespin", "Genosha", "Latveria", "Asgardia",
    "Camelot", "Shangri La", "El Dorado", "Mu", "Lemuria", "Hyperborea", "Thule", "Glastonbury", "Tintagel", "Camlann",
    "Tirion", "Valinor", "Elysia", "Mechanus", "Sigil", "Baator", "Pandemonium", "Ravenloft", "Waterdeep", "Baldurs Gate",
    "Neverwinter", "Luskan", "Amn", "Calimshan", "Menzoberranzan", "Phandalin", "Hearthstone", "Tristram", "Westmarch", "Sanctuary",
    "Lordran", "Anor Londo", "Yharnam", "Boletaria", "Drangleic", "Lothric", "Hallownest", "Hyrule Castle", "Termina", "Kakariko",
    "Lumiose", "Piltover", "Zaun", "Demacia", "Noxus", "Ionia", "Bilgewater", "Shurima", "Runeterra", "Azeroth",
    "Gilead", "Erewhon", "Mirkwood", "Fangorn", "Isengard", "Edoras", "Rohan", "Doriath", "Gondolin", "Esgaroth",
]

WORDS = {
    0: (["Sumpf", "Schilf", "Moor", "Fluss", "Drachen", "Schuppen", "Regen", "Lagune"], ["Wacht", "Krone", "Nest", "Auge", "Tor", "Hain", "Burg", "Pfad"]),
    1: (["Iron", "Storm", "Blood", "Frost", "War", "Thunder", "Stone", "Wolf"], ["Camp", "Fang", "Keep", "March", "Hall", "Gate", "Ridge", "Hold"]),
    2: (["Gift", "Schlangen", "Nacht", "Coil", "Viper", "Serpent", "Venom", "Ophid"], ["Zunge", "Nest", "Spire", "Pit", "Reach", "Hall", "Gate", "Crown"]),
    3: (["Red", "Wolf", "Fang", "Wild", "Moon", "Hunt", "Claw", "Beast"], ["Wood", "Den", "Nest", "Vale", "Run", "Gate", "Grove", "Reach"]),
    4: (["Eisen", "Hammer", "Kupfer", "Stahl", "Runen", "Fels", "Gold", "Berg"], ["Schmiede", "Fall", "Hall", "Grat", "Tor", "Wacht", "Ader", "Fest"]),
    5: (["Silver", "Moon", "Star", "Green", "Elven", "Lorien", "Stern", "Blüten"], ["Grove", "Vale", "Hain", "Spire", "Wood", "Tor", "Quell", "Garten"]),
    6: (["Gear", "Copper", "Brass", "Clock", "Tinker", "Spark", "Cog", "Zahn"], ["Hollow", "Works", "Fall", "Tower", "Reach", "Gate", "Nest", "Bau"]),
    7: (["Moon", "Sun", "Cat", "Claw", "Night", "Gold", "Puma", "Sphinx"], ["Paw", "Vale", "Nest", "Reach", "Grove", "Gate", "Crown", "Hain"]),
    8: (["Tunnel", "Waben", "Ratten", "Maus", "Nest", "Krümel", "Burrow", "Hollow"], ["Reich", "Nest", "Hall", "Wacht", "Bau", "Gate", "Vale", "Deep"]),
    9: (["Green", "Moss", "Apple", "Hobbit", "Meadow", "Hill", "Good", "Little"], ["Hill", "Vale", "Dale", "Field", "Ford", "Hollow", "Burrow", "Rest"]),
    10: (["Red", "Golden", "Crown", "River", "New", "High", "Kings", "Sun"], ["Wood", "Vale", "Ford", "Haven", "Gate", "Reach", "Crown", "Field"]),
    11: (["Tiefen", "Basalt", "Dunkel", "Schwarz", "Runen", "Asche", "Gloom", "Deep"], ["Tor", "Hall", "Grat", "Schmiede", "Wacht", "Ader", "Gate", "Hold"]),
    12: (["Red", "Grey", "Wolf", "Hound", "Bark", "Watch", "Moon", "Stone"], ["Gate", "Den", "Ford", "Keep", "Reach", "Vale", "Nest", "Hall"]),
    13: (["Schatten", "Nacht", "Dunkel", "Black", "Gloom", "Nether", "Gift", "Umbra"], ["Hain", "Schleier", "Spire", "Deep", "Gate", "Vale", "Nest", "Court"]),
    14: (["Blut", "Knochen", "Eisen", "War", "Skull", "Black", "Red", "Doom"], ["Feste", "Tor", "Grat", "Camp", "Crag", "Keep", "March", "Hall"]),
    15: (["Coral", "Pearl", "Blue", "Tide", "Reef", "Lagoon", "Sea", "Water"], ["Haven", "Reach", "Fall", "Gate", "Cove", "Vale", "Hall", "Rest"]),
    16: (["Star", "High", "Sun", "Dawn", "Silver", "Sky", "Aether", "Licht"], ["Crown", "Spire", "Vale", "Haven", "Reach", "Grove", "Tor", "Hain"]),
    17: (["Rune", "Arcane", "Spell", "Mystic", "Mana", "Raven", "Stern", "Zauber"], ["Spire", "Hall", "Gate", "Reach", "Turm", "Kreis", "Haven", "Tor"]),
    18: (["Dawn", "Green", "Silver", "Bridge", "West", "Star", "Twilight", "Morgen"], ["Bridge", "Vale", "Ford", "Grove", "Reach", "Haven", "Tor", "Hain"]),
    19: (["Rot", "Grün", "Wurzel", "Eichen", "Blatt", "Dorn", "Green", "Root"], ["Wald", "Herz", "Hain", "Grove", "Wood", "Spire", "Tor", "Vale"]),
}

def pair_name(race: int, key: str, used: set[str]) -> str:
    first, second = WORDS[race]
    pairs = list(itertools.product(first, second))
    rng = random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))
    rng.shuffle(pairs)
    for a, b in pairs:
        name = f"{a} {b}"
        if name not in used:
            used.add(name)
            return name
    index = 2
    base = f"{first[0]} {second[0]}"
    while f"{base}{index}" in used:
        index += 1
    name = f"{base}{index}"
    used.add(name)
    return name

def main() -> None:
    parts = MAP.read_bytes().decode().split("\r\n")
    burgs = json.loads(parts[15])
    report = json.loads(REPORT.read_text())
    plan = {int(x["center_burg_id"]): x for x in json.loads(PLAN.read_text())["centers"]}
    used = set(FIXED_NAMES)
    old_to_new: dict[str, str] = {}
    for burg in burgs:
        if isinstance(burg, dict) and int(burg.get("i", 0)) <= 154:
            old = burg["name"]
            burg_id = int(burg["i"])
            if burg_id in FIXED_IDS:
                name = FIXED_IDS[burg_id]
            else:
                name = None
                start = int(hashlib.sha256(str(burg_id).encode()).hexdigest()[:8], 16) % len(CAPITAL_NAMES)
                for offset in range(len(CAPITAL_NAMES)):
                    candidate = CAPITAL_NAMES[(start + offset) % len(CAPITAL_NAMES)]
                    if candidate not in used:
                        name = candidate
                        break
                if name is None:
                    name = pair_name(10, str(burg_id), used)
            used.add(name)
            burg["name"] = name
            burg["label"] = {"text": name, "group": burg.get("label", {}).get("group", "city")}
            old_to_new[old] = name
    meta = {s["name"]: s for s in report["settlements"]}
    for burg in burgs:
        if not isinstance(burg, dict) or int(burg.get("i", 0)) <= 154:
            continue
        old = burg["name"]
        item = meta[old]
        race = int(item.get("name_race_id", item["race_ids"][0]))
        name = pair_name(race, old, used)
        burg["name"] = name
        burg["label"] = {"text": name, "group": burg.get("label", {}).get("group", "city")}
        item["name"] = name
        item["name_race_id"] = race
        old_to_new[old] = name
    routes = json.loads(parts[37])
    for route in routes:
        route_name = str(route.get("name", ""))
        if route_name.startswith("Schutzkreis "):
            old = route_name[12:]
            route["name"] = "Schutzkreis " + old_to_new.get(old, old)
    details = {int(d["route"]): d for d in report.get("routes", {}).get("details", [])}
    for route in routes:
        d = details.get(int(route.get("i", -1)))
        if d:
            route["name"] = f"Weg {old_to_new.get(d['settlement'], d['settlement'])} – {old_to_new.get(d['center'], d['center'])}"
    parts[15] = json.dumps(burgs, separators=(",", ":"), ensure_ascii=False)
    parts[37] = json.dumps(routes, separators=(",", ":"), ensure_ascii=False)
    MAP.write_bytes("\r\n".join(parts).encode())
    report["fixed_city_names"] = {"City-0x098": "Terra", "City-0x099": "Eisenschmiede", "City-0x09A": "Yggdrasil"}
    report["settlements_named"] = len(report["settlements"])
    report["settlements"] = list(meta.values())
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"named_burgs": len([b for b in burgs if isinstance(b, dict)]), "settlements_two_words": len(meta), "unique_names": len(used)}))

if __name__ == "__main__":
    main()
