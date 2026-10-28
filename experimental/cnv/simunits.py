r"""What the plan simulator (sim.py) needs of a unit, from the game's own data: how fast it goes, on what (ground,
water, both, air), how far it sees, its KindOf. Retail templates from the SDK's SageXML (the index mapstudy keeps:
work\sagexml_gameobjects.json gives each template's file and KindOf; the file its LocomotorSet's NORMAL Speed and its
VisionRange / ShroudClearingRange), cached in work\sim_units.json. Our own units (a mission's Unit: its XML) are read
the same way from their XML; a template found nowhere gets its kind's default (DEFAULTS) and is listed as guessed.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
import labpaths  # noqa: E402

CACHE = os.path.join(labpaths.WORK, 'sim_units.json')
INDEX = os.path.join(labpaths.WORK, 'sagexml_gameobjects.json')
SAGEXML = os.path.join(labpaths.SDK3, 'SageXML')
LOCOMOTORS = os.path.join(SAGEXML, 'GlobalData', 'Locomotor.xml')

# a kind's guess when the data has nothing (world units per second; vision): retail infantry 40-60, vehicles 60-120
DEFAULTS = {'INFANTRY': (50.0, 200.0), 'VEHICLE': (90.0, 250.0), 'AIRCRAFT': (150.0, 300.0), 'SHIP': (70.0, 250.0),
            'STRUCTURE': (0.0, 250.0), '': (0.0, 100.0)}


def _surfaces():
    """Locomotor template id -> its Surfaces (GROUND, WATER, AIR ...)."""
    if not os.path.exists(LOCOMOTORS):
        return {}
    text = open(LOCOMOTORS, encoding='utf-8', errors='replace').read()
    out = {}
    for m in re.finditer(r'<LocomotorTemplate\b(.*?)>', text, re.S):
        head = m.group(1)
        i, s = re.search(r'\bid="([^"]+)"', head), re.search(r'\bSurfaces="([^"]+)"', head)
        if i:
            out[i.group(1)] = s.group(1).split() if s else []
    return out


def read_xml(text, kindof='', surfaces=None):
    """One unit's numbers from its XML text: speed (the NORMAL LocomotorSet), surface, vision, kinds."""
    surfaces = surfaces if surfaces is not None else {}
    speed, surf = None, []
    for m in re.finditer(r'<LocomotorSet\b(.*?)/?>', text, re.S):
        a = m.group(1)
        cond = re.search(r'\bCondition="([^"]+)"', a)
        if cond and cond.group(1) != 'NORMAL':
            continue
        sp, lo = re.search(r'\bSpeed="([\d.]+)"', a), re.search(r'\bLocomotor="([^"]+)"', a)
        if sp and speed is None:
            speed = float(sp.group(1))
            surf = surfaces.get(lo.group(1), []) if lo else []
    vis = re.search(r'(?<![A-Za-z])VisionRange="([\d.]+)"', text)
    shroud = re.search(r'(?<![A-Za-z])ShroudClearingRange="([\d.]+)"', text)
    kinds = set(kindof.split())
    if not kindof:
        k = re.search(r'\bKindOf="([^"]+)"', text)
        kinds = set(k.group(1).split()) if k else set()
    return dict(speed=speed, surface=surface_of(surf, kinds), vision=float(vis.group(1)) if vis else None,
                shroud=float(shroud.group(1)) if shroud else None, kinds=sorted(kinds))


def surface_of(surf, kinds):
    s = set(surf)
    if 'AIRCRAFT' in kinds or 'AIR' in s:
        return 'air'
    if 'AMPHIBIOUS' in kinds or {'GROUND', 'WATER'} <= s:
        return 'both'
    if 'WATER' in s and 'GROUND' not in s:
        return 'water'
    return 'ground'


def _build():
    idx = json.load(open(INDEX, encoding='utf-8')) if os.path.exists(INDEX) else {}
    surfaces = _surfaces()
    out = {}
    for t, e in idx.items():
        f = e.get('file', '')
        if e.get('EditorSorting') not in ('UNIT', 'STRUCTURE') or not f.startswith('DATA:'):
            continue
        path = os.path.join(SAGEXML, *f[5:].split('/'))
        if not os.path.exists(path):
            continue
        # the index writes inherited KindOf as +X / -X edits: keep the added ones; a building is sorted STRUCTURE
        kindof = ' '.join([k.lstrip('+') for k in e.get('KindOf', '').split() if not k.startswith('-')]
                          + (['STRUCTURE'] if e.get('EditorSorting') == 'STRUCTURE' else []))
        out[t] = read_xml(open(path, encoding='utf-8', errors='replace').read(), kindof, surfaces)
    return out


_table = None


def table():
    global _table
    if _table is None:
        if os.path.exists(CACHE):
            _table = json.load(open(CACHE, encoding='utf-8'))
        else:
            _table = _build()
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            json.dump(_table, open(CACHE, 'w', encoding='utf-8'), indent=0)
    return _table


def kind_of(kinds):
    for k in ('STRUCTURE', 'AIRCRAFT', 'SHIP', 'INFANTRY', 'VEHICLE'):
        if k in kinds:
            return k
    return ''


def stats(template, own=None):
    """{speed, surface, vision, shroud, kinds, guessed} for a template; own: {id: xml text} of the mission's units."""
    if own and template in own:
        e = read_xml(own[template], surfaces=_surfaces())
    else:
        e = dict(table().get(template.lower()) or {})
    guessed = []
    kinds = set(e.get('kinds') or [])
    speed, vision = DEFAULTS[kind_of(kinds)]
    if e.get('speed') is None:
        if 'STRUCTURE' not in kinds:            # a building does not move: nothing guessed
            guessed.append('speed')
        e['speed'] = speed
    if e.get('vision') is None:
        guessed.append('vision')
        e['vision'] = vision
    e.setdefault('surface', 'ground')
    e.setdefault('shroud', None)
    e['kinds'] = sorted(kinds)
    e['guessed'] = guessed if e.get('kinds') or own else ['all']
    return e
