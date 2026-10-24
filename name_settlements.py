#!/usr/bin/env python3
"""Assign short, memorable race-inspired names to settlements."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

MAP = Path("WorldMapForWheel.map")
REPORT = Path("settlement-network-generated.json")
RACES = Path("/home/alexandria/simulation-races-named.json")

RACE_POOLS = {
    0: ["Sobek", "Anzu", "Kappa", "Hydra", "Naga", "Basil", "Quetz", "Varan", "Krok", "Saur", "Drak", "Ladon", "Mokele", "Tiamat"],
    1: ["Conan", "Ares", "Thor", "Kratos", "Saga", "Edda", "Ragnar", "Beowulf", "Skadi", "Tyr", "Orm", "Hrolf", "Atreus", "Ajax"],
    2: ["Medusa", "Ophion", "Stheno", "Lamia", "Python", "Jormung", "Viper", "Naga", "Sleip", "Apep", "Basil", "Serpens", "Echidna", "Mamba"],
    3: ["Fenrir", "Mowgli", "Balto", "Khan", "Rex", "Hati", "Lupa", "Anubis", "Warg", "Akela", "Nala", "Kiba", "Puck", "Bamse"],
    4: ["Moria", "Gimli", "Durin", "Dain", "Eitri", "Brokkr", "Fafnir", "Volund", "Nibel", "Khazad", "Balin", "Gloin", "Kili", "Thorin"],
    5: ["Avalon", "Arwen", "Luthien", "Elrond", "Legolas", "Mab", "Titania", "Aelwen", "Faerie", "Nimue", "Galad", "Eowyn", "Silmar", "Ithil"],
    6: ["Gizmo", "Tink", "Daedalus", "Mimir", "Watt", "Tesla", "Puck", "Quill", "Cog", "Nox", "Babbage", "Mekka", "Rivet", "Sprocket"],
    7: ["Bastet", "Mau", "Sphinx", "Bagheera", "Cheshire", "Rajah", "Miaou", "Sekhmet", "Tigger", "Puma", "Leona", "Malkin", "Neko", "Kasha"],
    8: ["Ratatosk", "Remy", "Stuart", "Splinter", "Pied", "Rizzo", "Mickey", "Templeton", "Scabbers", "Nibbles", "Fievel", "Whisker", "Rattus", "Pip"],
    9: ["Bilbo", "Frodo", "Pippin", "Samwise", "Brandy", "Bree", "Merry", "Tuck", "Puck", "Hob", "Milo", "Willow", "Dale", "Baggins"],
    10: ["Terra", "Roma", "Athena", "Merlin", "Arthur", "Galahad", "Odysseus", "Sparta", "Avalon", "Hector", "Helios", "Orion", "Nova", "Civitas"],
    11: ["Moria", "Dvergr", "Durin", "Nidav", "Svart", "Khar", "Garm", "Ymir", "Nifl", "Eitri", "Mord", "Deep", "Grot", "Urda"],
    12: ["Argos", "Cerberus", "Hachiko", "Balto", "Laika", "Anubis", "Fenrir", "Sirius", "Mastiff", "Rin", "Kuma", "Akela", "Wolf", "Hound"],
    13: ["Menzob", "Drizzt", "Lolth", "Nyx", "Morgana", "Ereb", "Noctis", "Drow", "Umbra", "Vesper", "Morr", "Shade", "Lira", "Nerez"],
    14: ["Mordor", "Azog", "Grom", "Kull", "Sauron", "Gor", "Grond", "Thrak", "Maug", "Uruk", "Doom", "Karn", "Skull", "Ragor"],
    15: ["Poseidon", "Atlantis", "Nereid", "Triton", "Nausicaa", "Maui", "Manu", "Calypso", "Coral", "Pearl", "Lago", "Maris", "Nami", "Undine"],
    16: ["Valinor", "Tirion", "Eärendil", "Astra", "Aurora", "Solaria", "Alfheim", "Elysia", "Aether", "Varda", "Lorien", "Celest", "Altair", "Dawn"],
    17: ["Merlin", "Gandalf", "Morgana", "Circe", "Hermes", "Astra", "Rune", "Arcana", "Nexus", "Eldritch", "Sage", "Orac", "Myst", "Glyph"],
    18: ["Aragorn", "Arwen", "Eldar", "Bran", "Celt", "Avalon", "Lorien", "Gwen", "Belen", "Mabin", "Macha", "Eira", "Caer", "Danu"],
    19: ["Yggdrasil", "Dryad", "Gaia", "Daphne", "Sylvan", "Entwood", "Nimue", "Flora", "Eden", "Rowan", "Willow", "Oak", "Grove", "Verdant"],
}

FIXED = {"City-0x098": "Terra", "City-0x09A": "Yggdrasil", "City-0x099": "Eisenschmiede"}

def unique_name(race_id: int, key: str, used: set[str]) -> str:
    pool = RACE_POOLS[race_id]
    seed = int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    choices = pool[:]
    rng.shuffle(choices)
    endings = ["", "a", "en", "ia", "on", "or", "is", "os", "um", "el", "ar", "ra", "in", "us"]
    for base in choices:
        for ending in endings:
            candidate = base if not ending or base.endswith(ending) else base + ending
            if candidate not in used:
                used.add(candidate)
                return candidate
    index = 2
    base = choices[0]
    while f"{base} {index}" in used:
        index += 1
    candidate = f"{base} {index}"
    used.add(candidate)
    return candidate

def main() -> None:
    parts = MAP.read_bytes().decode().split("\r\n")
    burgs = json.loads(parts[15])
    report = json.loads(REPORT.read_text())
    race_names = {int(r["id"]): r["name"] for r in json.loads(RACES.read_text())["races"]}
    old_to_new: dict[str, str] = {}
    used = set(FIXED.values())
    for burg in burgs:
        if not isinstance(burg, dict):
            continue
        old = burg["name"]
        if old in FIXED:
            burg["name"] = FIXED[old]
            burg["label"] = {"text": FIXED[old], "group": burg.get("label", {}).get("group", "city")}
            old_to_new[old] = FIXED[old]
    settlement_meta = {s["name"]: s for s in report["settlements"]}
    named = 0
    for burg in burgs:
        if not isinstance(burg, dict) or int(burg.get("i", 0)) <= 154:
            continue
        old = burg["name"]
        meta = settlement_meta[old]
        race_ids = [int(r) for r in meta["race_ids"]]
        rng = random.Random(int(hashlib.sha256(old.encode()).hexdigest()[:16], 16))
        race_id = rng.choice(race_ids)
        name = unique_name(race_id, old, used)
        burg["name"] = name
        burg["label"] = {"text": name, "group": burg.get("label", {}).get("group", "city")}
        meta["name"] = name
        meta["name_race_id"] = race_id
        meta["name_race"] = race_names[race_id]
        old_to_new[old] = name
        named += 1
    routes = json.loads(parts[37])
    for route in routes:
        name = str(route.get("name", ""))
        if name.startswith("Schutzkreis "):
            old = name[len("Schutzkreis "):]
            if old in old_to_new:
                route["name"] = "Schutzkreis " + old_to_new[old]
    detail_by_route = {int(x["route"]): x for x in report.get("routes", {}).get("details", [])}
    for route in routes:
        detail = detail_by_route.get(int(route.get("i", -1)))
        if detail:
            route["name"] = f"Weg {old_to_new.get(detail['settlement'], detail['settlement'])} – {old_to_new.get(detail['center'], detail['center'])}"
    parts[15] = json.dumps(burgs, separators=(",", ":"), ensure_ascii=False)
    parts[37] = json.dumps(routes, separators=(",", ":"), ensure_ascii=False)
    MAP.write_bytes("\r\n".join(parts).encode())
    report["fixed_city_names"] = FIXED
    report["settlements_named"] = named
    report["settlements"] = list(settlement_meta.values())
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"settlements_named": named, "fixed_cities": FIXED, "unique_names": len(used)}))

if __name__ == "__main__":
    main()
