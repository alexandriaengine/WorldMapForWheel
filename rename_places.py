#!/usr/bin/env python3
"""Replace person-like settlement labels with memorable place names."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

MAP = Path("WorldMapForWheel.map")
REPORT = Path("settlement-network-generated.json")
PLAN = Path("settlement-network-plan.json")
RACES = Path("/home/alexandria/simulation-races-named.json")
FIXED = {"City-0x098": "Terra", "City-0x09A": "Yggdrasil", "City-0x099": "Eisenschmiede"}

PLACE_POOLS = {
    0: ["Sauria", "Nagara", "Drakonia", "Kemet", "Tlaloc", "Quetzal", "Krokara", "Miasma", "Lizardia", "Zandria"],
    1: ["Valhalla", "Rohan", "Skyrim", "Midgard", "Barbaria", "Dunholm", "Stormkeep", "Northreach", "Ironmarch", "Frostmark"],
    2: ["Serpentina", "Ophidia", "Lamia", "Nagaia", "Pythonia", "Meduria", "Viperfall", "Coilspire", "Slythera", "Basilisk"],
    3: ["Wildwood", "Fangorn", "Beastia", "Lupinia", "Howling", "Wolfen", "Redfang", "Moonpaw", "Huntgrove", "Pawreach"],
    4: ["Moria", "Erebor", "Khazad", "Ironforge", "Underdeep", "Stonehelm", "Dwarrow", "Goldvein", "Hammerfall", "Deepgate"],
    5: ["Alfheim", "Avalon", "Lothlorien", "Rivendell", "Sylvaris", "Elaria", "Faerieland", "Moonvale", "Starbloom", "Elvendell"],
    6: ["Mechanus", "Gearholm", "Cogfall", "Tinkerreach", "Clockwork", "Brasshaven", "Riveton", "Sparkspire", "Gadgeton", "Coppercoil"],
    7: ["Bastet", "Catara", "Sphinxia", "Moonclaw", "Purrsia", "Whiskerfall", "Leopardia", "Nightpurr", "Clawreach", "Sunmane"],
    8: ["Burrow", "Nestoria", "Warren", "Hollowhive", "Nibbleton", "Tunneldeep", "Ratchet", "Undercrumb", "Mouselow", "Gnawgate"],
    9: ["Hobbiton", "Bree", "Bywater", "The Shire", "Greenhill", "Hobbitown", "Mossend", "Tuckborough", "Pineburrow", "Halflingford"],
    10: ["Agrabah", "Atlantis", "Hyrule", "Alexandria", "Babylon", "Olympus", "Hogwarts", "Camelot", "Eldorado", "Novigrad"],
    11: ["Svartalfheim", "Niflheim", "Deepmoria", "Doomvault", "Blackdelve", "Underhold", "Gloomgate", "Basaltdeep", "Darkvein", "Abyssal"],
    12: ["Argos", "Cerberia", "Houndstead", "Wolfguard", "Barkreach", "Kennelhold", "Dogwatch", "Greyfang", "Howlkeep", "Pawford"],
    13: ["Menzoberranzan", "Nocturnia", "Erebos", "Umbra", "Duskfall", "Shadowdeep", "Nightspire", "Darkmere", "Gloamreach", "Blackveil"],
    14: ["Mordor", "Uruk", "Grond", "Gorath", "Skullcrag", "Warhold", "Bloodmarch", "Ragor", "Doomkeep", "Ironfang"],
    15: ["Atlantis", "Nereidia", "Tritonia", "Nausicaa", "Coralhaven", "Pearlreach", "Lagoonia", "Seabright", "Tidefall", "Bluewater"],
    16: ["Valinor", "Tirion", "Elysium", "Aetheria", "Solaria", "Lorien", "Celestia", "Starhaven", "Dawnspire", "Highreach"],
    17: ["Arcadia", "Avalon", "Hogwarts", "Mystara", "Runestone", "Spellhold", "Arcanum", "Magehaven", "Glyphreach", "Ravenloft"],
    18: ["Avalon", "Eldoria", "Camlann", "Bridgerest", "Mithlond", "Greenvale", "Halfway", "Dawnbridge", "Crossmere", "Twilighton"],
    19: ["Yggdrasil", "Gaia", "Eden", "Dryadell", "Entwood", "Verdantia", "Greenheart", "Rootspire", "Oakenshade", "Leafrest"],
}
SUFFIXES = ["", "ia", "is", "on", "um", "ara", "or", "en", "el", "eth", "os", "ea", "gate", "reach", "hold"]

def make_name(race_id: int, key: str, used: set[str]) -> str:
    rng = random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))
    pool = PLACE_POOLS[race_id][:]
    rng.shuffle(pool)
    for base in pool:
        for suffix in SUFFIXES:
            name = base if not suffix or base.lower().endswith(suffix.lower()) else base + suffix
            if name not in used:
                used.add(name)
                return name
    base = pool[0]
    index = 2
    while f"{base} {index}" in used:
        index += 1
    name = f"{base} {index}"
    used.add(name)
    return name

def main() -> None:
    parts = MAP.read_bytes().decode().split("\r\n")
    burgs = json.loads(parts[15])
    report = json.loads(REPORT.read_text())
    plan = {item["center"]: item for item in json.loads(PLAN.read_text())["centers"]}
    race_names = {int(r["id"]): r["name"] for r in json.loads(RACES.read_text())["races"]}
    used = set(FIXED.values())
    old_to_new: dict[str, str] = {}
    for burg in burgs:
        if isinstance(burg, dict) and burg.get("i", 0) <= 154:
            old = burg["name"]
            if old in FIXED:
                burg["name"] = FIXED[old]
                burg["label"] = {"text": FIXED[old], "group": burg.get("label", {}).get("group", "city")}
                old_to_new[old] = FIXED[old]
                continue
            entry = plan.get(old, {})
            race_id = int(entry.get("dominant_race", 10))
            name = make_name(race_id, old, used)
            burg["name"] = name
            burg["label"] = {"text": name, "group": burg.get("label", {}).get("group", "city")}
            old_to_new[old] = name
    settlement_meta = {s["name"]: s for s in report["settlements"]}
    for burg in burgs:
        if not isinstance(burg, dict) or burg.get("i", 0) <= 154:
            continue
        old = burg["name"]
        meta = settlement_meta[old]
        race_ids = [int(r) for r in meta["race_ids"]]
        rng = random.Random(int(hashlib.sha256(old.encode()).hexdigest()[:16], 16))
        race_id = rng.choice(race_ids)
        name = make_name(race_id, old, used)
        burg["name"] = name
        burg["label"] = {"text": name, "group": burg.get("label", {}).get("group", "city")}
        meta["name"] = name
        meta["name_race_id"] = race_id
        meta["name_race"] = race_names[race_id]
        old_to_new[old] = name
    routes = json.loads(parts[37])
    for route in routes:
        name = str(route.get("name", ""))
        if name.startswith("Schutzkreis "):
            old = name[len("Schutzkreis "):]
            route["name"] = "Schutzkreis " + old_to_new.get(old, old)
    details = {int(d["route"]): d for d in report.get("routes", {}).get("details", [])}
    for route in routes:
        detail = details.get(int(route.get("i", -1)))
        if detail:
            route["name"] = f"Weg {old_to_new.get(detail['settlement'], detail['settlement'])} – {old_to_new.get(detail['center'], detail['center'])}"
    parts[15] = json.dumps(burgs, separators=(",", ":"), ensure_ascii=False)
    parts[37] = json.dumps(routes, separators=(",", ":"), ensure_ascii=False)
    MAP.write_bytes("\r\n".join(parts).encode())
    report["fixed_city_names"] = FIXED
    report["settlements_named"] = len(report["settlements"])
    report["settlements"] = list(settlement_meta.values())
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"named_burgs": len([b for b in burgs if isinstance(b, dict)]), "unique_names": len(used)}))

if __name__ == "__main__":
    main()
