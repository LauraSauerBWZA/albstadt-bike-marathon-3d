# Albstadt Bike Marathon — Interaktive 3D-Karte

Single-File-HTML-Karte für die **Bergwacht Zollernalb**, die die Strecke des
Albstadt Bike Marathons mit allen Streckenposten und 0,5-km-Markern in einer
3D-Geländedarstellung zeigt.

- **Karte:** MapLibre GL JS 4.x (via CDN, kein Build-Tool)
- **Gelände:** AWS Open Data Terrain Tiles (Terrarium-Format, kostenlos)
- **Untergrund:** LGL Baden-Württemberg DOP20 (20 cm Luftbild), umschaltbar auf OpenStreetMap
- **Daten:** aus `ABM 2026-2.kmz` per `prepare_data.py` in vier GeoJSON-Dateien aufbereitet

## Projektstruktur

```
albstadt-bike-marathon-3d/
├── ABM 2026-2.kmz              # Quelldatei (Strecke + Posten + 0,5-km-Marker)
├── prepare_data.py             # Einmaliges KMZ → GeoJSON Aufbereitungs-Skript
├── index.html                  # Single-File 3D-Karte
├── daten/
│   ├── strecke.geojson         # 1 LineString, 1748 Stützpunkte
│   ├── posten.geojson          # 145 Streckenposten
│   ├── marker_500m.geojson     # 164 Marker im 0,5-km-Raster
│   └── zufahrtswege.geojson    # 2 Beispiel-Features (später erweiterbar)
└── README.md
```

## Lokal testen

Wegen CORS (`fetch()` auf lokale GeoJSON funktioniert per `file://` **nicht**):

```bash
cd /Users/laurasauer/claude-sandbox/projects/albstadt-bike-marathon-3d
python3 -m http.server 8000
```

Dann im Browser öffnen:

```
http://localhost:8000/
```

## KMZ neu aufbereiten

```bash
python3 prepare_data.py
```

Schreibt die GeoJSON-Dateien nach `daten/`. Benötigt nur die Python-Standard-Library
— kein `pip install`.

## Hosting auf GitHub Pages

1. Repo auf GitHub anlegen, alles committen + pushen
2. Repo → Settings → Pages → Source: "Deploy from branch", Branch `main`, Folder `/ (root)`
3. Pfade sind alle relativ (`daten/…`), funktioniert direkt unter `https://USER.github.io/REPO/`

## Karten-Untergrund (recherchiert)

**LGL Baden-Württemberg DOP20** funktioniert direkt — kein Token, OpenData:

- Endpoint: `https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DOP_20_C`
- Layer: `IMAGES_DOP_20_RGB`
- CORS: `Access-Control-Allow-Origin: *` ✓
- Web Mercator (`EPSG:3857`) wird unterstützt
- Lizenz: Datenlizenz Deutschland — Namensnennung — 2.0

Verifiziert per GetCapabilities am 2026-05-20. Damit war der DOP20-Fallback auf
basemap.de oder TopPlusOpen nicht nötig. Falls der LGL-Dienst je nicht erreichbar
sein sollte, lässt sich der Untergrund über den OSM-Button rechts unten umschalten.

## Features

| Layer | Stil | Aus/An |
|---|---|---|
| Marathon-Strecke | Bergwacht-Rot `#E30613` mit weißem Halo, zoom-responsive | Checkbox |
| Streckenposten | Farbig nach Kategorie: Start = grün, Verpflegung = orange, Standard = blau | Checkbox + Klick = Popup |
| 0,5-km-Marker | Klein gelb mit km-Label ab Zoom 12,5 | Checkbox (Standard aus) |
| Zufahrtswege | Orange gestrichelt | Checkbox; lädt automatisch wenn `daten/zufahrtswege.geojson` existiert |

**Bedienelemente:**
- **Oben rechts:** Layer-Control
- **Unten links:** Slider für Gelände-Überhöhung (1.0×–2.0×, Default 1.3×) + Untergrund-Toggle
- **Oben links:** Zoom / Pitch-Kompass / Vollbild
- **Unten rechts:** Maßstab + Quellenangaben
- **URL-Hash:** speichert Zoom/Pitch/Lage (`#13.5/48.25/8.99/...`) — teilbar

## Zufahrtswege später ergänzen

Die KMZ enthält bislang nur 2 Zufahrtswege-Features als Beispiel. Wenn aus Google
My Maps ein vollständiges KMZ für die Zufahrtswege exportiert wurde:

1. KMZ entpacken (es ist ein ZIP) und die `doc.kml` öffnen
2. Manuell in GeoJSON umwandeln (z.B. mit `prepare_data.py` als Vorlage —
   die Funktion `extract_zufahrtswege()` lässt sich auf das neue KML anwenden,
   wenn der Folder-Name passt)
3. Das Ergebnis als `daten/zufahrtswege.geojson` ablegen — die Karte zeigt
   den Layer automatisch an (Checkbox wird aktivierbar)

Erwartetes GeoJSON-Schema:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": { "name": "...", "beschreibung": "..." },
      "geometry": { "type": "LineString", "coordinates": [...] }
    }
  ]
}
```

## Bericht (Stand 2026-05-20)

- **Verwendete WMS-Quelle:** LGL Baden-Württemberg DOP20 (Layer
  `IMAGES_DOP_20_RGB`). Endpoint per GetCapabilities verifiziert, CORS aktiv,
  funktioniert direkt im Browser ohne Proxy. Kein Fallback auf BKG TopPlusOpen
  oder basemap.de nötig — der OSM-Toggle ist nur als Komfort-Option drin.
- **Datenmengen aus KMZ:**
  - Strecke: 1 LineString mit 1.748 Stützpunkten
  - Streckenposten: **145** (davon 1 Start, 4 Verpflegungspunkte, 140 Standard)
  - 0,5-km-Marker: **164**
  - Zufahrtswege: 2 Beispiel-Features (1 Linie + 1 Anfahrt-Point)
- **Ladezeit:** ~1–2 s bis zur ersten Anzeige (lokal). DOP20-Kacheln laden
  progressiv, die GeoJSON-Overlays (~100 KB gesamt) sind sofort sichtbar.
- **Lokaler Test:** `python3 -m http.server 8000` → http://localhost:8000/
- **Bekannte Einschränkungen:**
  - 3D-Terrain benötigt einen Browser mit WebGL2 (alle aktuellen Browser ok)
  - Die LGL-WMS-Tiles haben ein Rate-Limit; bei sehr schnellem Pan/Zoom
    können einzelne Kacheln verzögert erscheinen
  - 0,5-km-Marker-Labels werden erst ab Zoom 12,5 angezeigt, um die Karte bei
    Übersichtsansichten nicht zu überfrachten
  - Die Höhenwerte in `strecke.geojson` stammen aus der KML — sie werden im
    aktuellen Renderer für die Visualisierung nicht genutzt (die Linie wird
    auf das Geländemodell projiziert)

## Bewusst nicht enthalten (laut Vorgabe)

- Höhenprofil beim Klick
- DGM1-Pipeline (Bundesland-Daten, später)
- Live-Tracking
