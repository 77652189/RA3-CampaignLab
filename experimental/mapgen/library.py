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
from functools import lru_cache
from pathlib import Path
from statistics import median
from xml.etree import ElementTree as ET

from experimental.campaign import labpaths


SCHEMA_VERSION = 2
CLIFF_STEP_RAW = 1792
PROBE_STEP = CLIFF_STEP_RAW * 0.04375  # one step in cliffs.json's heights (mapstudy's old scale);
                                       # the game reads raw / 25.6, so one step is 70 world units
ASSET_NS = "{uri:ea.com:eala:asset}"
CATEGORIES = {
    "Buildings": "buildings", "Structures": "buildings",
    "Props": "props", "Optimized_Props": "props", "Shrubbery": "props",
    "Destructible_Props": "destructibles",
}


# Civilian SDK directories normally drop their two-letter suffix. These names
# differ, or have no usable terrain kit in the RA3 atlas sources (e.g. Romania).
KIT_ALIASES = {
    'Floating_Island_FI': 'Tokyo_Harbor', 'Miyako_MI': 'Hawaii',
    'Mount_Fuji_MJ': 'Hot_Springs', 'Northern_Russia_NR': 'Iceland',
    'Osaka_OK': 'Tokyo_Harbor', 'Romania_RM': 'Yucatan', 'Sakhalin_Island_SI': 'Iceland',
    'Shiro_Sanitarium_SS': 'Hot_Springs', 'Snowy_Hot_Springs_SN': 'Hot_Springs',
    'StPetersburg_ST': 'Saint_Petersburg', 'Yosemite_Park_YP': 'Mount_Rushmore',
}
def texture_kit(kit):
    return KIT_ALIASES.get(kit, kit.rsplit('_', 1)[0])


STYLE_DEFAULTS = {
    'places': {'texture_palette': {'count': 3, 'noise': (12, .18, .82), 'fixed_noise': (22, .28, .72)}} | {
               use: {'material': material, 'building_row': use in ('oldtown', 'residential', 'suburb')}
               for material, uses in {
                   'Road': ('oldtown', 'residential', 'industrial', 'dock', 'square'),
                   'Grass': ('suburb', 'park', 'woodland', 'wildland'), 'Dirt': ('farm', 'canyon'),
                   'Sand': ('water',), 'Snow': ('snow', 'snow_woodland', 'ice'),
               }.items() for use in uses},
    'edges': {'building_row': {'anchor_words': ('house',), 'repeat': 3, 'coverage': .25, 'setback': 6, 'gap': 6},
              'shore_surface': {'texture': 'Sand_SantaMonica01', 'material': 'Sand', 'classes': {'Snow': 'Snow'}},
              'cliff_surface': {'material': 'Cliff', 'keep_shoulder': ('Snow',)},
              'ramp_surface': {'material': 'Dirt', 'classes': {'Snow': 'Snow', 'Dirt': 'Rock'},
                               'verge': 'Grass', 'verge_classes': {'Dirt': 'Dirt'}, 'exposed': 'Rock',
                               'keep_shoulder': ('Snow',)}},
}


def style_section(library, kit, section):
    table = library.get('styles', {})
    folder = kit if kit in library.get('texture_kits', {}) else texture_kit(kit)
    result = dict(STYLE_DEFAULTS.get(section, {}))
    for key in dict.fromkeys(('*', folder, kit)):
        for name, entry in table.get(key, {}).get(section, {}).items():
            result[name] = result.get(name, {}) | entry if isinstance(entry, dict) else entry
    return result


def place_recipe(library, kit, use):
    places = style_section(library, kit, 'places')
    return places.get('*', {}) | places.get(use, {})


# Placement measurements from the 150 game probe take precedence over medians.
_BENCHED = {'HB_CliffWall01': (100, -15), 'RM_CliffWall01_GRID': (120, -30)}
_CLIFF_FITTINGS = {
    'Vladivostok_VL': {'VL_CliffWall02': (57, None)},  # Russian Village near-straight minimum: 56.9.
    'Mount_Fuji_MJ': {'MJ_CliffWall01': (None, 'MJ_CliffWall08')},  # Coaxial centres 90 apart.
}


def straight_cliff(library, kit, steps):
    kits = library['kits']
    cliffs = kits.get(kit, {}).get('cliffs', ())
    choices = []
    for entry in cliffs:
        if entry['height_steps'] != steps:
            continue
        name = entry['template']
        source = entry.get('borrowing', {}).get('from', kit)
        label = next((asset.get('editor_name', '') for category in ('props', 'buildings', 'destructibles')
                      for asset in kits[source].get(category, ()) if asset['template'] == name), '')
        if 'Corner' in label or 'Curve' in label:
            continue
        if name.endswith('_GRID') and name not in _BENCHED and not label.endswith('Straight'):
            continue
        length, offset = _BENCHED.get(name, (entry['length'], entry['offset_y']))
        if length and offset is not None and offset <= 0:
            choices.append((name not in _BENCHED, -entry['samples'], name, length, offset, source))
    if not choices:
        return None
    _, _, name, length, offset, source = min(choices)
    if name.endswith('_GRID'):
        length, offset = round(length / 30) * 30, round(offset / 30) * 30
    pitch, filler = _CLIFF_FITTINGS.get(source, {}).get(name, (None, None))
    short = next((entry['length'] for entry in cliffs
                  if entry['template'] == filler and entry['height_steps'] == steps and entry['length']), 0)
    return name, length, offset, pitch or length, filler, short


def cliff_corners(library, kit, steps, straight):
    """Corner profiles are paired with the straight piece whose ends they meet."""
    kits = library['kits']
    style = kits.get(kit, {})
    donor = next((e.get('borrowing', {}).get('from', kit) for e in style.get('cliffs', ())
                  if e['template'] == straight), kit)
    return (entry for entry in style_section(library, donor, 'nodes').get('cliff_fittings', ())
            if entry['steps'] == steps and entry['straight'] == straight)


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


def _revision(path):
    info = path.stat()
    return info.st_mtime_ns, info.st_size


@lru_cache(maxsize=4)
def _load_library(path, revision):
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version', SCHEMA_VERSION) != SCHEMA_VERSION:
        raise ValueError(f'{path}: regenerate the asset library with experimental.mapgen.library')
    return data


def load_library(path):
    """Reuse the read-only catalogue, including its original retail mood chunks."""
    path = Path(path).resolve()
    return _load_library(path, _revision(path))


@lru_cache(maxsize=256)
def _sdk_xml(path, revision):
    return read_xml(path)


def sdk_xml(path):
    """Reuse the read-only SDK document across layout and dressing passes."""
    return _sdk_xml(path, _revision(path))


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


def _sdk_objects(sage, paths, issues):
    for path in sorted(paths):
        relative = path.relative_to(sage)
        source = f"sdk/SageXML/{relative.as_posix()}"
        root = _read(path, source, read_xml, issues)
        if root is not None:
            for obj in root.iter("GameObject"):
                yield relative, source, obj


def sdk_objects(sage):
    """GameObject definitions for retail readers, indexed by case-insensitive ID."""
    objects = defaultdict(list)
    for _, source, obj in _sdk_objects(sage, sage.rglob('*.xml'), set()):
        objects[obj.attrib['id'].casefold()].append((source, obj))
    return objects


def sdk_footprint(objects, template):
    definitions = objects.get(template.casefold(), ())
    if definitions:
        source, obj = definitions[0]
        geometry = _geometry(obj, source, objects, set())
        if geometry is not None:
            return tuple(geometry['footprint'])
    return ()


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
    for relative, source, obj in _sdk_objects(sage, paths, issues):
        objects[obj.attrib['id'].casefold()].append((source, obj))
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


def _borrow_cliffs(kits, rows, source, issues):
    native = {(kit, cliff["template"]): cliff for kit, style in kits.items() for cliff in style["cliffs"]}
    for row in rows:
        kit, donor, template, retail_map = (row[key] for key in ("kit", "from", "template", "map"))
        cliff = native.get((donor, template))
        if (kit not in kits or (kit, template) in native or not cliff or
                not cliff["height_steps"] or not cliff["length"] or cliff["offset_y"] is None or
                retail_map not in cliff["maps"]):
            issues.add(("invalid_cliff_borrowing", source, f"{kit}: {donor}/{template} on {retail_map}"))
            continue
        kits[kit]["cliffs"].append({**cliff, "borrowing": {"from": donor, "map": retail_map, "source": source}})


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


def _corner_blocking(sage, asset):
    """A corner with the unmodified non-colliding base needs no footprint override."""
    path = sage / asset['source'].removeprefix('sdk/SageXML/')
    obj = next(o for o in sdk_xml(path).iter('GameObject') if o.get('id') == asset['template'])
    if obj.get('inheritFrom') != 'BaseCliffWall' or 'KindOf' in obj.attrib or obj.find('Behaviors') is not None:
        return None
    source = 'BaseObjects/BaseCliffWall.xml'
    base = next(sdk_xml(sage / source).iter('GameObject'))
    if 'NO_COLLIDE' in base.get('KindOf', '').split():
        return {'cls': 'none', 'foot': '不挡', 'vehicle': '不挡', 'crush': '—',
                'basis': 'inherits NO_COLLIDE', 'source': f'sdk/SageXML/{source}', 'evidence': 'inferred'}
    return None


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
    borrowing_path = "mapgen_probe/cliff_borrowing.json"
    if (work / borrowing_path).is_file():
        borrowing, source = probe(borrowing_path)
        if borrowing is not None:
            _borrow_cliffs(kits, borrowing, source, issues)
    blocking, source = probe("logs/e266_prop_blocking.json")
    blocking = _blocking(blocking, source, issues) if blocking is not None else {}
    styles = probe("mapgen_probe/dressing.json")[0] or {}
    lots_path = "mapgen_probe/lots.json"
    if (work / lots_path).is_file():
        lots, _ = probe(lots_path)
        for kit, style in (lots or {}).items():
            styles.setdefault(kit, {})['lots'] = style['lots']
    corner_path = "mapgen_probe/cliff_joints.json"
    if (work / corner_path).is_file():
        profiles, source = probe(corner_path)
        for kit, entries in (profiles or {}).items():
            style = kits.get(kit, {})
            assets = {e['template']: e for category in ('props', 'destructibles')
                      for e in style.get(category, ())}
            for entry in entries:
                if {entry['template'], entry['straight']} <= assets.keys():
                    styles.setdefault(kit, {}).setdefault('nodes', {}).setdefault('cliff_fittings', []).append(
                        {**entry, 'source': source, 'evidence': 'measured_from_maps'})
                    key = entry['template'].casefold()
                    if key not in blocking and (basis := _corner_blocking(sage, assets[entry['template']])):
                        blocking[key] = basis
                else:
                    issues.add(('invalid_cliff_corner', source, f'{kit}: {entry["template"]}'))
    setpieces, source = probe("mapgen_probe/setpieces.json")
    if setpieces is not None:
        setpieces = {"units": setpieces["units"], "groups": [
            {**group, "source": source, "evidence": "measured_from_maps"} for group in setpieces["groups"]]}
    mood_path = "mapgen_probe/atmosphere.json"
    moods = probe(mood_path)[0] if (work / mood_path).is_file() else None
    return {
        "schema_version": SCHEMA_VERSION,
        "cliff_step_raw": CLIFF_STEP_RAW,
        "kits": kits,
        "texture_kits": textures,
        "retail_moods": moods or {},
        "setpieces": setpieces,
        "styles": styles,
        "blocking": blocking,
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
