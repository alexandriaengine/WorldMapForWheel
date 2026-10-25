#!/usr/bin/env python3
from __future__ import annotations
import json, random, hashlib
from collections import defaultdict
from pathlib import Path

MAP = Path("WorldMapForWheel.map")
REPORT = Path("settlement-network-generated.json")
PLAN = Path("settlement-network-plan.json")

GODS = [
("Ambrosia","Griechisch","Göttliche Speise, Unsterblichkeit"),("Neptun","Römisch","Gott der Meere"),("Ifrit","Arabisch / Spiele","Mächtiger Feuer-Dschinn"),("Dominion","Christliche Engelshierarchie","Himmlische Herrschaft, Ordnung"),("Rah (Ra)","Ägyptisch","Sonnengott"),("Zeus","Griechisch","Blitz, Himmel, Götterherrschaft"),("Hades","Griechisch","Unterwelt, Tote"),("Poseidon","Griechisch","Meer, Erdbeben"),("Ares","Griechisch","Krieg, Blutvergießen"),("Athena","Griechisch","Weisheit, Strategie"),("Thanatos","Griechisch","Tod"),("Nyx","Griechisch","Urgöttin der Nacht"),("Chronos","Griechisch","Verkörperung der Zeit"),("Hekate","Griechisch","Magie, Geister, Kreuzwege"),("Odin","Nordisch","Weisheit, Krieg, Magie"),("Thor","Nordisch","Donner, Stärke"),("Loki","Nordisch","List, Täuschung, Chaos"),("Hel","Nordisch","Herrscherin der Totenwelt"),("Fenrir","Nordisch","Gewaltiger göttlicher Wolf"),("Jörmungandr","Nordisch","Weltenschlange"),("Surtr","Nordisch","Feuerriese, Weltuntergang"),("Freyja","Nordisch","Liebe, Magie, Krieg"),("Anubis","Ägyptisch","Totenriten, Seelengeleit"),("Osiris","Ägyptisch","Jenseits, Wiedergeburt"),("Seth","Ägyptisch","Chaos, Wüste, Stürme"),("Horus","Ägyptisch","Himmel, Königtum"),("Thot","Ägyptisch","Wissen, Schrift, Magie"),("Apophis","Ägyptisch","Chaos, Finsternis"),("Amaterasu","Japanisch","Sonnengöttin"),("Susanoo","Japanisch","Stürme, Meer"),("Izanagi","Japanisch","Schöpfung, Leben"),("Izanami","Japanisch","Schöpfung, Tod"),("Shiva","Hinduistisch","Zerstörung, Erneuerung"),("Vishnu","Hinduistisch","Erhaltung, Weltordnung"),("Kali","Hinduistisch","Zeit, Zerstörung, Schutz"),("Brahma","Hinduistisch","Schöpfung"),("Indra","Vedisch / Hinduistisch","Gewitter, Krieg"),("Quetzalcoatl","Aztekisch","Gefiederte Schlange, Wind, Wissen"),("Tezcatlipoca","Aztekisch","Nacht, Schicksal, Konflikt"),("Tlaloc","Aztekisch","Regen, Fruchtbarkeit"),("Marduk","Babylonisch","Schöpfung, Herrschaft"),("Ishtar","Mesopotamisch","Liebe, Krieg"),("Tiamat","Babylonisch / D&D","Urmeer, Chaosdrache"),("Bahamut","Arabische Legenden / Final Fantasy","Kosmisches Wesen / Drachenkönig"),("Leviathan","Biblisch / Spiele","Gewaltiges Meeresungeheuer"),("Beelzebub","Dämonologie / Spiele","Mächtiger Dämonenfürst"),("Lilith","Jüdische Überlieferung / Diablo","Dämonische Gestalt"),("Asmodeus","Dämonologie / D&D","Dämonenfürst, Verführung"),("Diablo","Diablo-Spielreihe","Herr des Schreckens"),("Aurelion Sol","League of Legends","Kosmischer Sternenschöpfer")
]
RACES = {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19}
AFF = {
1:{5,9,10,18},2:{0,10,15},3:{1,6,13,14},4:{4,5,10,16},5:{5,10,16},6:{1,10,16},7:{11,13,8,14},8:{0,10,15},9:{1,10,14},10:{10,16,5,4},11:{11,13,8,14},12:{13,7,17,5},13:{6,11,5,16},14:{6,13,5},15:{1,10,4,16},16:{1,4,14},17:{13,6,9,3},18:{13,11,8},19:{3,12,14},20:{2,0,15},21:{14,4,13},22:{5,10,7,9},23:{12,13,10},24:{10,9,5},25:{0,14,13,2},26:{10,16,7},27:{6,17,10},28:{2,13,0},29:{5,16,10},30:{15,0,1},31:{10,5,16},32:{13,11,10},33:{17,10,13},34:{5,16,10,9},35:{13,17,10},36:{6,4,10},37:{1,10,16},38:{0,2,5},39:{13,2,17},40:{0,15,9},41:{4,10,1},42:{10,5,7},43:{2,0,13},44:{4,16,10},45:{15,0,2},46:{13,14,8},47:{13,2,17},48:{13,17,10},49:{13,14,11},50:{16,5,17}}

def score(god: int, races: list[int], dominant: int) -> float:
    hits = len(set(races) & AFF.get(god, set()))
    return hits * 4 + (2 if dominant in AFF.get(god, set()) else 0) + (0.5 if len(races) == 1 else 0)

def main() -> None:
    parts = MAP.read_bytes().decode().split("\r\n")
    burgs = json.loads(parts[15])
    report = json.loads(REPORT.read_text())
    plan = json.loads(PLAN.read_text())["centers"]
    plan_by_stable = {x["center"]: x for x in plan}
    burg_by_id = {b["i"]: b for b in burgs if isinstance(b, dict)}
    circles = []
    for x in plan:
        center = burg_by_id[x["center_burg_id"]]
        circles.append({"stable": x["center"], "center": center, "races": x["race_ids"], "dominant": x["dominant_race"]})
    assigned: dict[str, int] = {}
    used_gods: set[int] = set()
    candidates = sorted(((score(g, c["races"], c["dominant"]), g, c["stable"]) for g in range(1, 51) for c in circles), reverse=True)
    for value, god, stable in candidates:
        if god in used_gods or stable in assigned: continue
        assigned[stable] = god; used_gods.add(god)
    loads = defaultdict(int)
    for g in assigned.values(): loads[g] += 1
    for c in circles:
        if c["stable"] in assigned: continue
        ranked = sorted(range(1, 51), key=lambda g: (score(g, c["races"], c["dominant"]) - loads[g] * 0.8, -g), reverse=True)
        assigned[c["stable"]] = ranked[0]; loads[ranked[0]] += 1
    god_by_stable = assigned
    for c in circles:
        god = assigned[c["stable"]]
        c["center"]["god"] = god
    for b in burgs:
        if not isinstance(b, dict) or b.get("i", 0) <= 154: continue
        item = next((s for s in report["settlements"] if s["name"] == b["name"]), None)
        if item and item["center"] in god_by_stable: b["god"] = god_by_stable[item["center"]]
    parts[15] = json.dumps(burgs, separators=(",", ":"), ensure_ascii=False)
    MAP.write_bytes("\r\n".join(parts).encode())
    registry = [{"id": i, "name": n, "origin": o, "domain": d, "assigned_circles": [s for s,g in assigned.items() if g == i]} for i,(n,o,d) in enumerate(GODS, 1)]
    out = {"god_count": 50, "assignment_rule": "race-combination fit with balanced distribution; each god used at least once", "gods": registry, "assignments": [{"circle": s, "god_id": g, "god_name": GODS[g-1][0]} for s,g in assigned.items()]}
    Path("god-registry.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    report["god_assignments"] = {"god_count": 50, "distribution": dict(loads), "reference": "god-registry.json"}
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"circles": len(assigned), "gods_used": len(set(assigned.values())), "min_load": min(loads.values()), "max_load": max(loads.values())}))

if __name__ == "__main__": main()
