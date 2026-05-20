#!/usr/bin/env python3
"""
Albstadt Bike Marathon — KMZ → GeoJSON Aufbereitung

Entpackt `ABM 2026-2.kmz`, parst die enthaltene `doc.kml` und schreibt
saubere GeoJSON-Dateien nach `daten/`:

  daten/strecke.geojson        — Marathon-Strecke (LineString mit Z)
  daten/posten.geojson         — ~145 Streckenposten (Points)
  daten/marker_500m.geojson    — 0,5-km-Marker (Points)
  daten/zufahrtswege.geojson   — Zufahrtswege Rettungsmittel
                                 (LineStrings + Points, soweit in KMZ vorhanden)

Standard-Library only — kein Pip-Install nötig.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

KMZ_PATH = Path(__file__).parent / "ABM 2026-2.kmz"
OUT_DIR = Path(__file__).parent / "daten"
KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}


def read_kml_from_kmz(kmz_path: Path) -> str:
    with zipfile.ZipFile(kmz_path) as zf:
        # KMZ kann mehrere KMLs enthalten; die Haupt-Datei heißt per Konvention doc.kml
        kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
        if not kml_names:
            raise RuntimeError("Keine .kml in KMZ gefunden")
        target = "doc.kml" if "doc.kml" in kml_names else kml_names[0]
        return zf.read(target).decode("utf-8")


def parse_coords(text: str) -> list[list[float]]:
    """KML coordinates → [[lon, lat, ele], ...]"""
    coords: list[list[float]] = []
    for token in text.replace("\n", " ").split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        lon = float(parts[0])
        lat = float(parts[1])
        ele = float(parts[2]) if len(parts) >= 3 else 0.0
        coords.append([lon, lat, ele])
    return coords


def classify_post(name: str, style: str) -> str:
    """Leite semantische Kategorie aus Name/Style ab."""
    n = name.strip().lower()
    if n in ("start", "ziel"):
        return n
    if n.startswith("verpflegung"):
        return "verpflegung"
    return "posten"


def get_text(el: ET.Element, tag: str) -> str | None:
    child = el.find(f"kml:{tag}", KML_NS)
    return child.text.strip() if child is not None and child.text else None


def find_top_level_folders(doc: ET.Element) -> list[ET.Element]:
    """Direkte Folder unter <Document>."""
    return doc.findall("kml:Folder", KML_NS)


def folder_name(folder: ET.Element) -> str:
    return get_text(folder, "name") or ""


def extract_strecke(folders: list[ET.Element]) -> dict:
    """Erste Originalstrecke-Folder mit LineString."""
    features = []
    seen = False
    for folder in folders:
        if folder_name(folder).lower() != "originalstrecke" or seen:
            continue
        for pm in folder.findall("kml:Placemark", KML_NS):
            line = pm.find("kml:LineString", KML_NS)
            if line is None:
                continue
            coords_el = line.find("kml:coordinates", KML_NS)
            if coords_el is None or not coords_el.text:
                continue
            coords = parse_coords(coords_el.text)
            features.append({
                "type": "Feature",
                "properties": {
                    "name": get_text(pm, "name") or "Originalstrecke",
                    "kategorie": "strecke",
                },
                "geometry": {"type": "LineString", "coordinates": coords},
            })
        seen = True
    return {"type": "FeatureCollection", "features": features}


def extract_posten(folders: list[ET.Element]) -> dict:
    """Erste Streckenposten-Folder. Pro Placemark Name + Style → Kategorie."""
    features = []
    seen = False
    for folder in folders:
        if folder_name(folder).lower() != "streckenposten" or seen:
            continue
        for pm in folder.findall("kml:Placemark", KML_NS):
            point = pm.find("kml:Point", KML_NS)
            if point is None:
                continue
            coords_el = point.find("kml:coordinates", KML_NS)
            if coords_el is None or not coords_el.text:
                continue
            coords = parse_coords(coords_el.text)
            if not coords:
                continue
            name = get_text(pm, "name") or ""
            style = get_text(pm, "styleUrl") or ""
            kategorie = classify_post(name, style)
            desc = get_text(pm, "description")
            props = {"name": name, "kategorie": kategorie, "styleUrl": style}
            if desc:
                props["beschreibung"] = desc
            features.append({
                "type": "Feature",
                "properties": props,
                "geometry": {"type": "Point", "coordinates": coords[0]},
            })
        seen = True
    return {"type": "FeatureCollection", "features": features}


def extract_marker_500m(folders: list[ET.Element]) -> dict:
    """Kilometerabschnitte alle 0,5 km."""
    features = []
    for folder in folders:
        if "kilometerabschnitte" not in folder_name(folder).lower():
            continue
        for pm in folder.findall("kml:Placemark", KML_NS):
            point = pm.find("kml:Point", KML_NS)
            if point is None:
                continue
            coords_el = point.find("kml:coordinates", KML_NS)
            if coords_el is None or not coords_el.text:
                continue
            coords = parse_coords(coords_el.text)
            if not coords:
                continue
            name = get_text(pm, "name") or ""
            km_match = re.match(r"\s*([\d.,]+)\s*km", name)
            km_value = float(km_match.group(1).replace(",", ".")) if km_match else None
            props = {"name": name, "kategorie": "marker_500m"}
            if km_value is not None:
                props["km"] = km_value
            features.append({
                "type": "Feature",
                "properties": props,
                "geometry": {"type": "Point", "coordinates": coords[0]},
            })
        break
    return {"type": "FeatureCollection", "features": features}


def extract_zufahrtswege(folders: list[ET.Element]) -> dict:
    """Zufahrtswege Rettungsmittel (LineStrings + Points)."""
    features = []
    for folder in folders:
        if "zufahrtswege" not in folder_name(folder).lower():
            continue
        for pm in folder.findall("kml:Placemark", KML_NS):
            name = get_text(pm, "name") or ""
            desc = get_text(pm, "description")
            line = pm.find("kml:LineString", KML_NS)
            point = pm.find("kml:Point", KML_NS)
            geom = None
            if line is not None:
                coords_el = line.find("kml:coordinates", KML_NS)
                if coords_el is not None and coords_el.text:
                    geom = {"type": "LineString", "coordinates": parse_coords(coords_el.text)}
            elif point is not None:
                coords_el = point.find("kml:coordinates", KML_NS)
                if coords_el is not None and coords_el.text:
                    coords = parse_coords(coords_el.text)
                    if coords:
                        geom = {"type": "Point", "coordinates": coords[0]}
            if geom is None:
                continue
            props = {"name": name, "kategorie": "zufahrtsweg"}
            if desc:
                props["beschreibung"] = desc
            features.append({"type": "Feature", "properties": props, "geometry": geom})
    return {"type": "FeatureCollection", "features": features}


def write_geojson(path: Path, fc: dict) -> int:
    path.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")))
    return len(fc["features"])


def main() -> int:
    if not KMZ_PATH.exists():
        print(f"FEHLER: {KMZ_PATH} nicht gefunden", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(exist_ok=True)
    kml_text = read_kml_from_kmz(KMZ_PATH)
    root = ET.fromstring(kml_text)
    document = root.find("kml:Document", KML_NS)
    if document is None:
        print("FEHLER: <Document> nicht gefunden", file=sys.stderr)
        return 1

    folders = find_top_level_folders(document)

    strecke = extract_strecke(folders)
    posten = extract_posten(folders)
    marker = extract_marker_500m(folders)
    zufahrtswege = extract_zufahrtswege(folders)

    n_strecke = write_geojson(OUT_DIR / "strecke.geojson", strecke)
    n_posten = write_geojson(OUT_DIR / "posten.geojson", posten)
    n_marker = write_geojson(OUT_DIR / "marker_500m.geojson", marker)
    n_zufahrt = write_geojson(OUT_DIR / "zufahrtswege.geojson", zufahrtswege)

    n_line_points = 0
    if strecke["features"]:
        n_line_points = len(strecke["features"][0]["geometry"]["coordinates"])

    print(f"Strecke:       {n_strecke} Feature(s), {n_line_points} Stützpunkte")
    print(f"Posten:        {n_posten} Feature(s)")
    print(f"0,5-km-Marker: {n_marker} Feature(s)")
    print(f"Zufahrtswege:  {n_zufahrt} Feature(s)")
    print(f"\nGeschrieben nach: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
