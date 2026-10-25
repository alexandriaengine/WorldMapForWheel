# WorldMapForWheel

## Karte in Azgaar Vanilla laden

Im Vanilla-Generator nicht die GitHub-Seite oder die `blob`-URL verwenden. In **Load map from URL** muss die direkte Raw-URL eingetragen werden:

```text
https://raw.githubusercontent.com/alexandriaengine/WorldMapForWheel/main/WorldMapForWheel.map
```

Diese URL liefert die aktuelle öffentliche `WorldMapForWheel.map` direkt aus dem `main`-Branch. Nach einem Update des Branches lädt dieselbe URL den aktualisierten Kartenstand.

Voraussetzungen:

- Das Repository muss öffentlich sein.
- Die URL muss mit `https://raw.githubusercontent.com/` beginnen.
- Nicht verwenden:
  - `https://github.com/.../blob/...`
  - die Repository-Startseite
  - eine lokale Datei-URL

Die Karte wird in Azgaar über **Options → Load map from URL** geladen.

## Aktueller Kartenstand

Die Datei ist eine Azgaar-Fantasy-Map-Generator-Karte im Format `1.154.2`. Die Repository-Validierung erfolgt mit:

```bash
python3 validate_vanilla_map.py WorldMapForWheel.map
```
