"""Regenerate work/mapgen/library.json with python -X utf8 -m experimental.mapgen.library.

SDK kit keys are the civilian directory names. Texture kits use Terrain.xml's
WBFolder independently. Cliff lengths are observed along-line placement spacing,
and offsets are signed local y coordinates of the edge relative to the piece.
The map measurements come from the local probe exports.
"""

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import median
from xml.etree import ElementTree as ET

from experimental.campaign import labpaths


SCHEMA_VERSION = 1
CLIFF_STEP_RAW = 1792
PROBE_STEP = CLIFF_STEP_RAW * 0.04375  # one step in cliffs.json's heights (mapstudy's old scale);
                                       # the game reads raw / 25.6, so one step is 70 world units
ASSET_NS = "{uri:ea.com:eala:asset}"
CATEGORIES = {
    "Buildings": "buildings", "Structures": "buildings",
    "Props": "props", "Optimized_Props": "props", "Shrubbery": "props",
    "Destructible_Props": "destructibles",
}


def _read(path, source, load, issues):
    try:
        return load(path)
    except (OSError, ValueError, ET.ParseError) as exc:
        kind = "missing_source" if isinstance(exc, FileNotFoundError) else "invalid_source"
        detail = exc.strerror if isinstance(exc, OSError) else str(exc)
        issues.add((kind, source, detail))
        return None


def read_xml(path):
    root = ET.parse(path).getroot()
    for node in root.iter():
        node.tag = node.tag.removeprefix(ASSET_NS)
    return root


def read_shape(node):
    shape = dict(node.attrib)
    for key in ("MajorRadius", "MinorRadius", "Height"):
        if key in shape:
            shape[key] = float(shape[key])
    offset = node.find("Offset")
    if offset is not None:
        shape["Offset"] = {axis: float(value) for axis, value in offset.attrib.items()}
    return shape


def _geometry(obj, source, objects, issues):
    """Use the nearest Geometry, and use its PlacementShape for the footprint if present."""
    seen = set()
    while obj.find("Geometry") is None:
        parent = obj.get("inheritFrom")
        if not parent:
            return None
        key = parent.casefold()
        if key in seen or len(objects.get(key, ())) != 1:
            issues.add(("unresolved_geometry_parent", source, parent))
            return None
        seen.add(key)
        source, obj = objects[key][0]

    node = obj.find("Geometry")
    shapes = [read_shape(shape) for shape in node.findall("Shape")]
    placement = [read_shape(shape) for shape in node.findall("PlacementShape")]
    return {"source": source, "attributes": node.attrib, "shapes": shapes,
            "footprint": placement or shapes}


def _civilian(sage, issues):
    civilian = sage / "Civilian"
    places = {path.name for path in civilian.glob("*_*") if path.is_dir()}
    if not places:
        issues.add(("missing_source", "sdk/SageXML/Civilian", "no civilian kit directories"))
    kits = {place: {"buildings": [], "props": [], "destructibles": [], "cliffs": []}
            for place in sorted(places)}
    objects, members = defaultdict(list), []
    paths = (path for folder in ("Civilian", "BaseObjects", "EP1/BaseObjects")
             for path in (sage / folder).rglob("*.xml"))
    for path in sorted(paths):
        relative = path.relative_to(sage)
        source = f"sdk/SageXML/{relative.as_posix()}"
        root = _read(path, source, read_xml, issues)
        if root is None:
            continue
        for obj in root.iter("GameObject"):
            ident = obj.attrib["id"]
            objects[ident.casefold()].append((source, obj))
            if len(relative.parts) >= 4:
                section, place, folder = relative.parts[:3]
                if section == "Civilian" and place in kits and folder in CATEGORIES:
                    members.append((place, CATEGORIES[folder], source, obj))

    for place, category, source, obj in members:
        entry = {"template": obj.attrib["id"], "source": source, "evidence": "inferred"}
        if "EditorName" in obj.attrib:
            entry["editor_name"] = obj.attrib["EditorName"]
        if category == "buildings":
            entry["geometry"] = _geometry(obj, source, objects, issues)
        kits[place][category].append(entry)
    return kits


def _texture_kits(sage, issues):
    relative = "Terrain/Terrain.xml"
    source = f"sdk/SageXML/{relative}"
    root = _read(sage / relative, source, read_xml, issues)
    kits = {}
    if root is not None:
        for node in sorted(root.iter("TerrainAsset"), key=lambda node: node.attrib["id"]):
            kit = kits.setdefault(node.attrib["WBFolder"], {})
            kit.setdefault(node.attrib["Class"], []).append(
                {**node.attrib, "source": source, "evidence": "inferred"})
    return kits


def _cliff_measurements(rows):
    """Use probe 2a's terrain transects and next-piece rule."""
    maps, drops, offsets, lengths, origins = (defaultdict(list) for _ in range(5))
    for row in rows:
        maps[row["map"]].append(row)
    for row in rows:
        key = row["t"].casefold()
        origins[key].append(f'{row["src"]}/{row["map"]}')
        sx, sy = (sorted((int(k), v) for k, v in row[axis].items()) for axis in ("sx", "sy"))
        x, y = [v for _, v in sx], [v for _, v in sy]
        if None not in x + y:
            transect = x if abs(x[-1] - x[0]) > abs(y[-1] - y[0]) else y
            drops[key].append(max(transect) - min(transect))
        if None in y or max(y) - min(y) < 50:
            continue
        mid = (max(y) + min(y)) / 2
        for (a, low), (b, high) in zip(sy, sy[1:]):
            if low != high and (low - mid) * (high - mid) <= 0:
                offsets[key].append(a + (mid - low) / (high - low) * (b - a))
                break

        c, s = math.cos(row["a"]), math.sin(row["a"])
        nearest = 300
        for other in maps[row["map"]]:
            dx, dy = other["x"] - row["x"], other["y"] - row["y"]
            along, across = dx * c + dy * s, -dx * s + dy * c
            if 1 < along < nearest and abs(across) < 40:
                nearest = along
        if nearest < 300:
            lengths[key].append(nearest)

    measurements = {}
    for key, sources in origins.items():
        heights = sorted(drop / PROBE_STEP for drop in drops[key])
        quartiles = [heights[len(heights) // 4], median(heights), heights[3 * len(heights) // 4]] if heights else []
        # Only publish a discrete step count when the middle half supports it.
        steps = {round(value) for value in quartiles}
        measurements[key] = {
            "maps": sorted(set(sources)), "samples": len(sources),
            "drop_quartiles_steps": [round(value, 3) for value in quartiles],
            "height_steps": next(iter(steps)) if len(steps) == 1 and 0 not in steps else None,
            "length": round(median(lengths[key])) if len(lengths[key]) >= 15 else None,
            "offset_y": round(median(offsets[key])) if len(lengths[key]) >= 15 and offsets[key] else None,
        }
    return measurements


def _add_cliffs(kits, rows, source):
    measurements = _cliff_measurements(rows)
    for kit in kits.values():
        seen = set()
        for entry in kit["props"] + kit["buildings"] + kit["destructibles"]:
            template = entry["template"]
            key = template.casefold()
            if key in seen or key not in measurements:
                continue
            seen.add(key)
            cliff = {"template": template, "source": source, "sdk_source": entry["source"],
                     "evidence": "measured_from_maps", **measurements[key]}
            editor_name = entry.get("editor_name", "")
            if "Transition" in editor_name or (
                    re.search(r"Elev(?:ation)?2", editor_name) and cliff["height_steps"] != 2):
                cliff["height_steps"] = None
            kit["cliffs"].append(cliff)


def _blocking(rows, source, issues):
    table = {}
    for row in rows:
        key = row["template"].casefold()
        entry = {field: row[field] for field in ("cls", "foot", "vehicle", "crush", "basis")}
        entry.update(source=source, evidence="benched" if row["basis"].startswith("台上") else "inferred")
        if table.setdefault(key, entry) != entry:
            issues.add(("conflicting_blocking", source, key))
    for kind, _, key in issues:
        if kind == "conflicting_blocking":
            del table[key]
    return table


def build_library(sage, work):
    """Read SageXML and local probe exports without writing anything."""
    issues = set()
    kits = _civilian(sage, issues)
    textures = _texture_kits(sage, issues)

    def probe(relative):
        source = f"work/{relative}"
        data = _read(work / relative, source, lambda path: json.loads(path.read_text(encoding="utf-8-sig")), issues)
        return data, source

    cliffs, source = probe("mapgen_probe/cliffs.json")
    if cliffs is not None:
        _add_cliffs(kits, cliffs, source)
    setpieces, source = probe("mapgen_probe/setpieces.json")
    if setpieces is not None:
        setpieces = {"units": setpieces["units"], "groups": [
            {**group, "source": source, "evidence": "measured_from_maps"} for group in setpieces["groups"]]}
    blocking, source = probe("logs/e266_prop_blocking.json")
    mood_path = "mapgen_probe/atmosphere.json"
    moods = probe(mood_path)[0] if (work / mood_path).is_file() else None
    return {
        "schema_version": SCHEMA_VERSION,
        "cliff_step_raw": CLIFF_STEP_RAW,
        "kits": kits,
        "texture_kits": textures,
        "retail_moods": moods or {},
        "setpieces": setpieces,
        "blocking": _blocking(blocking, source, issues) if blocking is not None else {},
        "issues": [{"kind": kind, "source": source, "detail": detail} for kind, source, detail in sorted(issues)],
    }


def main():
    work = Path(labpaths.WORK)
    library = build_library(Path(labpaths.SDK3) / "SageXML", work)
    output = work / "mapgen" / "library.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(library, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8", newline="\n")
    print(f"{output}: {len(library['kits'])} civilian kits, {len(library['issues'])} source issues")
    for issue in library["issues"]:
        print(f"{issue['kind']} {issue['source']}: {issue['detail']}")


if __name__ == "__main__":
    main()
