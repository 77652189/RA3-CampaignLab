"""A map sketch (work/mappage/<name>/sketch.json, drawn on the map page's new-map mode: serve.py --new) turned into a
draft map module in the platmap format (LAYOUT / SITES / BORDERS / OBJECTS, like experimental/cnv/maps/himeji.py), then
checked the way cnv_preview checks a map: the design lint (contract.map_design), the contract of an empty mission on
it, the walkable regions (which sites the start cannot reach), and the .map a build would write, measured by
mapstudy and terrainref. ADR 0017: the page only proposes -- the draft stays in work/mappage/<name>/ until the level
line has looked it over and moved it into experimental/cnv/maps/.

  python -I -X utf8 experimental/mappage/sketch2map.py trial                 sketch.json -> trial.py, trial_names.py, report
  python -I -X utf8 experimental/mappage/sketch2map.py trial --from sapporo  write the sketch of an existing map first
  python -I -X utf8 experimental/mappage/sketch2map.py trial --no-map        lint and regions only (no .map, no study)
  python -I -X utf8 experimental/mappage/sketch2map.py trial --check --sketch my.json   take a sketch written anywhere
                              (- = stdin), save it as work/mappage/trial/sketch.json, generate, check, print the summary

The sketch (version 1), world units, +y north, as the map modules write them:
  size [W, H]                 the playable area ('whole' border) when borders are not given; the container is 5000
  base, cliff                 Layout.base (the tier where nothing is drawn) and Layout.cliff (smoothing passes)
  shapes [{kind, at, tier, what}]   painted in order: kind poly (at = [[x, y] ...]), rect ([x0, y0, x1, y1]) or
                              circle ([x, y, r]); tier 0 is water, 1..3 the levels (platmap.TIER)
  walls [{points, width, tier, what}]   cliff walls: a strip along the polyline, painted after the shapes (each segment
                              a quad, each joint a circle): steep on every side, so nobody crosses it (no invisible wall)
  ramps [{low, high, width, what}], roads [{points, width, texture}]      platmap.Ramp / Road
  sites {code: {x, y, r, zh, what, build, cast}}     zh is the Chinese name (<name>_names.py)
  start [x, y]                the player's start (Player_1_Start and the start camera are moved there)
  fields [{name, x, y, facing, twin, base, owner, build}], derricks [[x, y]]     resources.Field: ore made from the pad
  borders {name: [x0, y0, x1, y1]}   the first is the playable area (MAP_SWITCH_BORDER order)
  blocks [{at, use, what, high}], gaps [{x, y, width, what}]     platmap.Block / Gap (at: a shape dict or a rectangle)
  brushes [{op, r, s, dabs, height}]   raise / lower / flatten strokes laid last (platmap.brush, Layout.brushes; the
                              same rule as the existing maps' terrain editor); dabs flat [x0, y0, x1, y1, ...]
  bridges [{a: [x, y], b: [x, y], template}]   a bridge from bank a to bank b (platmap.bridge: a start and an end
                              object, neutral; the deck is platmap.BRIDGE_DECK wide). Both ends on dry ground of one
                              height (the lint says so otherwise); template default HB_Bridge_02
  objects, scenery [{template, x, y, side, name, angle, flags, site}]     placed as they are (walls; props)
Full description, with units and an example an agent can write: docs/shell/sketch-format.md.

The same sketch always gives the same module text (module_text is a pure function of it); a module written by
from_module and generated again reads the same (readings(): heights, walkability, lint, sites, borders, objects) --
tests/test_mappage_sketch.py holds sapporo to that.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CNV = os.path.join(ROOT, 'experimental', 'cnv')
CAMPAIGN = os.path.join(ROOT, 'experimental', 'campaign')
OUT = os.path.join(ROOT, 'work', 'mappage')
VERSION = 1
START_WHAT = "the player's start; the start camera looks here"
BRIDGE = 'HB_Bridge_02'                         # the bridge template a new bridge gets
NEAR = 40.0                                     # two sites closer than this (or a fifth of the smaller radius) are one
WORLD = 5000.0                                  # the container map's width in world units ((560 - 2 * 30) * 10)


def _load(name, path):
    """A module by file (as mappage.py does): this file adds nothing to sys.path (guard G4); build.py puts
    experimental/cnv and experimental/campaign on it when it loads."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


build = _load('build', os.path.join(CNV, 'build.py'))
import contract                                 # noqa: E402  (on the path build.py set)
import parts                                    # noqa: E402
import platmap                                  # noqa: E402
import resources                                # noqa: E402


# ---------------------------------------------------------------- the sketch

def blank(name, size=(WORLD, WORLD)):
    """A new map: flat low ground (tier 1) everywhere, the start in the west, nothing else."""
    w, h = float(size[0]), float(size[1])
    if not (0 < w <= WORLD and 0 < h <= WORLD):
        raise ValueError(f'size {w:g} x {h:g}: the container map is {WORLD:g} x {WORLD:g} at most')
    return {'version': VERSION, 'name': name, 'what': '', 'size': [w, h], 'base': 1, 'cliff': 2,
            'shapes': [], 'walls': [], 'ramps': [], 'roads': [],
            'sites': {}, 'start': [min(1250.0, w / 4), h / 2], 'fields': [], 'derricks': [],
            'borders': {'whole': [0.0, 0.0, w, h]}, 'blocks': [], 'gaps': [], 'brushes': [], 'bridges': [],
            'objects': [], 'scenery': []}


def _f(v):
    return float(v)


def _pts(points):
    return [[_f(x), _f(y)] for x, y in points]


def _shape_out(s):
    at = _pts(s.at) if s.kind == 'poly' else [_f(v) for v in s.at]
    return {'kind': s.kind, 'at': at, 'tier': int(s.tier), 'what': s.what}


def _obj_out(o):
    if o.props:
        raise ValueError(f'{o.template} at ({o.x:g}, {o.y:g}): objects with props are not in sketch version 1')
    d = {'template': o.template, 'x': _f(o.x), 'y': _f(o.y), 'side': o.side}
    for k in ('name', 'site'):
        if getattr(o, k):
            d[k] = getattr(o, k)
    if o.angle is not None:
        d['angle'] = _f(o.angle)
    if o.flags is not None:
        d['flags'] = int(o.flags)
    return d


def _brush_out(st):
    """A height stroke as the sketch keeps it: flat dabs, numbers as floats, height only for flatten."""
    d = {'op': st['op'], 'r': _f(st['r']), 's': _f(st.get('s', 0.0)),
         'dabs': [_f(v) for q in platmap._dab_points(st['dabs']) for v in q]}
    if st['op'] == 'flatten':
        d['height'] = _f(st['height'])
    return d


def _bridge_objs(b):
    """The two objects of a sketch bridge, as the sketch keeps objects (platmap.bridge: start, then end)."""
    t = b.get('template') or BRIDGE
    return [{'template': t, 'x': _f(x), 'y': _f(y), 'side': 'neutral', 'site': 'map', 'angle': _f(a), 'flags': int(fl)}
            for x, y, a, fl in platmap.bridge(tuple(b['a']), tuple(b['b']), t)]


def _bridges_out(objects):
    """Bridges among an existing map's objects: a start right before its end, exactly what platmap.bridge makes of
    their two points (anything else stays a raw object). Returns (bridges, the other objects)."""
    bridges, rest, k = [], [], 0
    while k < len(objects):
        o, q = objects[k], objects[k + 1] if k + 1 < len(objects) else None
        if q and o.get('flags') == platmap.BRIDGE_START and q.get('flags') == platmap.BRIDGE_END:
            b = {'a': [o['x'], o['y']], 'b': [q['x'], q['y']], 'template': o['template']}
            if _bridge_objs(b) == [o, q]:
                bridges.append(b)
                k += 2
                continue
        rest.append(o)
        k += 1
    return bridges, rest


def from_module(mod, names=None):
    """The sketch of an existing platmap map module: what generate() turns back into an equivalent module. The ore and
    the refinery sites are not copied: they are made from FIELDS again (resources.py)."""
    if not hasattr(mod, 'LAYOUT'):
        raise ValueError(f'{mod.__name__}: not a platform map (no LAYOUT)')
    lay = mod.LAYOUT
    fields = list(getattr(mod, 'FIELDS', []))
    derricks = list(getattr(mod, 'DERRICKS', []))
    made = resources.sites(fields)
    names = names or {}
    sites = {}
    for k, s in mod.SITES.items():
        if k in made:
            continue
        d = {'x': _f(s.x), 'y': _f(s.y), 'r': _f(s.r), 'zh': names.get(k, ''), 'what': s.what}
        if s.build:
            d['build'] = _f(s.build)
        if s.cast:
            d['cast'] = _f(s.cast)
        if s.facing is not None:
            raise ValueError(f'site {k!r} has a facing but no field makes it')
        sites[k] = d
    ore = [_obj_out(o) for o in resources.objects(fields, derricks)]
    objects = [_obj_out(o) for o in getattr(mod, 'OBJECTS', [])]
    for o in ore:                                   # the fields' ore and oil, made again: not raw objects
        objects.remove(o)
    bridges, objects = _bridges_out(objects)
    start = getattr(mod, 'START', None) or (mod.SITES['start'].x, mod.SITES['start'].y)
    borders = {k: [_f(v) for v in b] for k, b in getattr(mod, 'BORDERS', {'whole': (0, 0, WORLD, WORLD)}).items()}
    whole = next(iter(borders.values()))
    return {
        'version': VERSION, 'name': mod.__name__.split('.')[-1], 'what': (mod.__doc__ or '').strip().split('\n')[0],
        'size': [whole[2] - whole[0], whole[3] - whole[1]], 'base': int(lay.base), 'cliff': int(lay.cliff),
        'shapes': [_shape_out(s) for s in lay.shapes], 'walls': [],
        'ramps': [{'low': [_f(v) for v in r.low], 'high': [_f(v) for v in r.high], 'width': _f(r.width),
                   'what': r.what} for r in lay.ramps],
        'roads': [{'points': _pts(r.points), 'width': _f(r.width), 'texture': r.texture} for r in lay.roads],
        'sites': sites, 'start': [_f(start[0]), _f(start[1])],
        'fields': [{'name': f.name, 'x': _f(f.x), 'y': _f(f.y), 'facing': _f(f.facing), 'twin': int(f.twin),
                    'base': f.base, 'owner': f.owner, 'build': _f(f.build)} for f in fields],
        'derricks': [[_f(x), _f(y)] for x, y in derricks],
        'borders': borders,
        'blocks': [{'at': _shape_out(b.at) if isinstance(b.at, platmap.Shape) else [_f(v) for v in b.at],
                    'use': b.use, 'what': b.what, 'high': b.high} for b in lay.blocks],
        'gaps': [{'x': _f(g.x), 'y': _f(g.y), 'width': _f(g.width), 'what': g.what} for g in lay.gaps],
        'brushes': [_brush_out(st) for st in getattr(lay, 'brushes', [])],
        'bridges': bridges,
        'objects': objects,
        'scenery': [_obj_out(o) for o in getattr(mod, 'SCENERY', [])],
    }


def check_sketch(s):
    """Problems that stop a sketch from being generated at all (a missing field, a tier that does not exist ...)."""
    out = []
    if s.get('version') != VERSION:
        out.append(f'sketch version {s.get("version")!r}: this generator reads version {VERSION}')
    tiers = set(platmap.TIER)
    for k, sh in enumerate(s.get('shapes', [])):
        if sh.get('kind') not in ('poly', 'rect', 'circle'):
            out.append(f'shape {k + 1}: kind {sh.get("kind")!r} (poly, rect or circle)')
        elif sh['kind'] == 'poly' and len(sh.get('at', [])) < 3:
            out.append(f'shape {k + 1} ({sh.get("what") or "poly"}): a polygon needs 3 points at least')
        if sh.get('tier') not in tiers:
            out.append(f'shape {k + 1}: tier {sh.get("tier")!r} (one of {sorted(tiers)})')
    for k, wl in enumerate(s.get('walls', [])):
        if len(wl.get('points', [])) < 2 or wl.get('width', 0) <= 0:
            out.append(f'wall {k + 1}: two points and a width at least')
        if wl.get('tier', 3) not in tiers:
            out.append(f'wall {k + 1}: tier {wl.get("tier")!r}')
    if s.get('base') not in tiers:
        out.append(f'base tier {s.get("base")!r}')
    for k, r in enumerate(s.get('roads', [])):
        if len(r.get('points', [])) < 2:
            out.append(f'road {k + 1}: two points at least')
    for code in s.get('sites', {}):
        if not code or code != code.strip() or "'" in code or '\\' in code:
            out.append(f'site {code!r}: a code name is plain text without quotes')
    for k, st in enumerate(s.get('brushes', [])):
        if st.get('op') not in platmap.BRUSH_OPS:
            out.append(f'brush {k + 1}: op {st.get("op")!r} (one of {", ".join(platmap.BRUSH_OPS)})')
        elif not (st.get('r', 0) > 0 and st.get('s', 0) >= 0):
            out.append(f'brush {k + 1}: a radius above 0 and a strength of 0 or more')
        elif not st.get('dabs') or len(st['dabs']) % 2:
            out.append(f'brush {k + 1}: dabs are x, y pairs, one at least')
        elif st['op'] == 'flatten' and not isinstance(st.get('height'), (int, float)):
            out.append(f'brush {k + 1}: flatten needs the height it levels to')
    for k, b in enumerate(s.get('bridges', [])):
        try:
            a, c = [(float(p[0]), float(p[1])) for p in (b['a'], b['b'])]
        except (KeyError, TypeError, ValueError, IndexError):
            out.append(f'bridge {k + 1}: two ends a and b, each [x, y]')
            continue
        if math.dist(a, c) < platmap.BRIDGE_DECK:
            out.append(f'bridge {k + 1}: its ends are {math.dist(a, c):.0f} apart (a bridge is longer than it is wide)')
    if not s.get('borders'):
        out.append('no borders: the first one is the playable area')
    for f in s.get('fields', []):
        try:
            resources.Field(f['name'], f['x'], f['y'], f['facing'], f.get('twin', 1))
        except (KeyError, ValueError) as e:
            out.append(f'field {f.get("name")!r}: {e}')
    return out


def wall_shapes(wall):
    """A cliff wall as shapes: a quad per segment and a circle at every point, all of the wall's tier."""
    pts, half, tier = wall['points'], wall['width'] / 2.0, int(wall.get('tier', 3))
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = -(y1 - y0) / d * half, (x1 - x0) / d * half
        out.append({'kind': 'poly', 'at': [[x0 + nx, y0 + ny], [x1 + nx, y1 + ny], [x1 - nx, y1 - ny],
                                           [x0 - nx, y0 - ny]], 'tier': tier, 'what': wall.get('what') or 'cliff wall'})
    for x, y in pts:
        out.append({'kind': 'circle', 'at': [x, y, half], 'tier': tier, 'what': wall.get('what') or 'cliff wall'})
    return out


# ---------------------------------------------------------------- the module text

def _r(v):
    """A number as Python source: exact (repr of the float), integers without the .0."""
    v = float(v)
    return repr(int(v)) if v.is_integer() and abs(v) < 1e15 else repr(v)


def _s(text):
    return repr(str(text))


def _pt(p):
    return f'({_r(p[0])}, {_r(p[1])})'


def _shape_src(sh):
    at = sh['at']
    if sh['kind'] == 'poly':
        body = '(' + ', '.join(_pt(p) for p in at) + (',)' if len(at) == 1 else ')')
    else:
        body = '(' + ', '.join(_r(v) for v in at) + ')'
    return f"Shape({sh['kind']!r}, {body}, {int(sh['tier'])}, {_s(sh.get('what', ''))})"


def _obj_src(o):
    args = [_s(o['template']), _r(o['x']), _r(o['y']), f"side={_s(o.get('side', 'p1'))}"]
    if o.get('name'):
        args.append(f"name={_s(o['name'])}")
    if o.get('angle') is not None:
        args.append(f"angle={_r(o['angle'])}")
    if o.get('flags') is not None:
        args.append(f"flags={int(o['flags'])}")
    if o.get('site'):
        args.append(f"site={_s(o['site'])}")
    return 'Obj(' + ', '.join(args) + ')'


def _wrap(head, items, close=']'):
    if not items:
        return [head + close]
    return [head] + [f'    {x},' for x in items] + [close]


def module_text(s):
    """The map module for sketch s, as text: a pure function of the sketch (the same sketch, the same text)."""
    problems = check_sketch(s)
    if problems:
        raise ValueError('sketch: ' + '; '.join(problems))
    name = s['name']
    shapes = list(s['shapes']) + [sh for wl in s.get('walls', []) for sh in wall_shapes(wl)]
    title = (s.get('what') or '').strip() or f'a new map drawn on the map page ({name})'
    L = [f'"""{title}',
         '',
         f'Generated by experimental/mappage/sketch2map.py from work/mappage/{name}/sketch.json (the map page\'s new-map',
         'mode): do not edit this draft by hand while the sketch is the source -- draw and generate again. Once the',
         'level line has looked it over and moved it into experimental/cnv/maps/ (ADR 0017), the module is the source.',
         '',
         'Published: SITES, PLAYERS, TEAMS, BORDERS, OBJECTS, SCENERY, LAYOUT, FIELDS, DERRICKS, BRIDGES, START.',
         '"""',
         'import struct',
         '',
         'import make_campnew18 as c18',
         'import platmap',
         'import resources',
         'from platmap import Block, Gap, Layout, Ramp, Road, Shape',
         'from maps import island',
         'from parts import Obj, Site',
         '',
         f"START = {_pt(s['start'])}",
         '']
    st = s['sites'].get('start', {})               # the start site stands at START; its radius and words may be drawn
    sites = [f"'start': Site(*START, {_r(st.get('r', 0))}, "
             f"{_s(st.get('what') or START_WHAT)}"
             + ''.join(f', {k}={_r(st[k])}' for k in ('build', 'cast') if st.get(k)) + ')']
    for code, d in s['sites'].items():
        if code == 'start':
            continue
        extra = ''.join(f', {k}={_r(d[k])}' for k in ('build', 'cast') if d.get(k))
        sites.append(f"{_s(code)}: Site({_r(d['x'])}, {_r(d['y'])}, {_r(d.get('r', 0))}, {_s(d.get('what', ''))}{extra})")
    L += _wrap('SITES = {', sites, '}')
    L += _wrap('FIELDS = [', [f"resources.Field({_s(f['name'])}, {_r(f['x'])}, {_r(f['y'])}, {_r(f['facing'])}, "
                              f"{int(f.get('twin', 1))}, base={_s(f.get('base', ''))}, owner={_s(f.get('owner', ''))}, "
                              f"build={_r(f.get('build', 0))})" for f in s.get('fields', [])])
    L += _wrap('DERRICKS = [', [_pt(p) for p in s.get('derricks', [])])
    L += ['SITES.update(resources.sites(FIELDS))']
    L += _wrap('BORDERS = {', [f'{_s(k)}: (' + ', '.join(_r(v) for v in b) + ')' for k, b in s['borders'].items()],
               '}')
    L += ['PLAYERS = island.PLAYERS',
          "TEAMS = dict(island.TEAMS, s1='Soviet_1/teamSoviet_1')",
          '']
    L += _wrap('RAW_OBJECTS = [', [_obj_src(o) for o in s.get('objects', [])])
    L += ['# bridges bank to bank (platmap.bridge: a start object and its end, one right after the other)']
    L += _wrap('BRIDGES = [', [f"({_pt(b['a'])}, {_pt(b['b'])}, {_s(b.get('template') or BRIDGE)})"
                               for b in s.get('bridges', [])])
    L += ["BRIDGE_OBJECTS = [Obj(t, x, y, side='neutral', angle=a, flags=f, site='map')",
          '                  for p, q, t in BRIDGES for x, y, a, f in platmap.bridge(p, q, t)]',
          'OBJECTS = RAW_OBJECTS + BRIDGE_OBJECTS + resources.objects(FIELDS, DERRICKS)', '']
    L += _wrap('SHAPES = [', [_shape_src(sh) for sh in shapes])
    L += _wrap('RAMPS = [', [f"Ramp({_pt(r['low'])}, {_pt(r['high'])}, {_r(r.get('width', 160))}, "
                             f"{_s(r.get('what', ''))})" for r in s.get('ramps', [])])
    L += _wrap('ROADS = [', [f"Road((" + ', '.join(_pt(p) for p in r['points']) + f"), {_r(r.get('width', 120))}, "
                             f"{_s(r.get('texture', 'Pavement_Heidel02'))})" for r in s.get('roads', [])])
    blocks = []
    for b in s.get('blocks', []):
        at = _shape_src(b['at']) if isinstance(b['at'], dict) else '(' + ', '.join(_r(v) for v in b['at']) + ')'
        high = f", high={_s(b['high'])}" if b.get('high') else ''
        blocks.append(f"Block({at}, {_s(b['use'])}, {_s(b.get('what', ''))}{high})")
    L += _wrap('BLOCKS = [', blocks)
    L += _wrap('GAPS = [', [f"Gap({_r(g['x'])}, {_r(g['y'])}, {_r(g['width'])}, {_s(g.get('what', ''))})"
                            for g in s.get('gaps', [])])
    L += ['# hand strokes (raise / lower / flatten, platmap.brush), laid on the ground the shapes and ramps make']
    L += _wrap('BRUSHES = [', ['{' + ', '.join([f"'op': {_s(b['op'])}", f"'r': {_r(b['r'])}", f"'s': {_r(b['s'])}"]
                                            + ([f"'height': {_r(b['height'])}"] if b['op'] == 'flatten' else [])
                                            + ["'dabs': [" + ', '.join(_r(v) for v in b['dabs']) + ']']) + '}'
                               for b in map(_brush_out, s.get('brushes', []))])
    L += [f"LAYOUT = Layout(shapes=SHAPES, ramps=RAMPS, roads=ROADS, base={int(s['base'])}, cliff={int(s['cliff'])}, "
          'blocks=BLOCKS, gaps=GAPS, brushes=BRUSHES)',
          '']
    L += ['# the look: retail objects placed as they are (a new map has none yet: the level line adds platprops)']
    L += _wrap('SCENERY = [', [_obj_src(o) for o in s.get('scenery', [])])
    L += ['',
          '',
          'def terrain(m):',
          '    """CampNew18\'s generate with the platform terrain over its island, and the starts moved to START."""',
          '    import newmap',
          '    c18.generate(m)',
          '    previews, _ = platmap.apply(m, LAYOUT)',
          '    c18.PREVIEWS.update(previews)',
          "    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')",
          '    for k in objs.kids:',
          "        name = newmap.typed_props_of(m, k)[0].get('waypointName', (0, ''))[1]",
          "        if name in ('Player_1_Start', 'InitialCameraPosition', 'Player_2_Start'):",
          "            dx = 60.0 if name == 'Player_2_Start' else 0.0",
          "            k.head = struct.pack('<ff', START[0] + dx, START[1] + dx) + k.head[8:]",
          '',
          '',
          'def like(m, objs, tmpl):',
          '    return island.like(m, objs, tmpl)',
          '']
    return '\n'.join(L)


def names_text(s):
    """<name>_names.py: the Chinese names the map page shows next to each site's code name (mappage.site_names)."""
    rows = [f"    'start': {_s(s['sites'].get('start', {}).get('zh') or '玩家起点')},"]
    rows += [f'    {_s(k)}: {_s(d.get("zh") or k)},' for k, d in s['sites'].items() if k != 'start']
    rows += [f"    {_s(f['name'] + ' refinery')}: {_s((f['name']) + ' 矿场')}," for f in s.get('fields', [])]
    return '\n'.join([f'"""Chinese names for the sites {s["name"]}.py publishes (generated with it by sketch2map.py)."""',
                      '', 'NAMES = {', *rows, '}', ''])


# ---------------------------------------------------------------- generate, load, read

def folder(name):
    return os.path.join(OUT, name)


def sketch_path(name):
    return os.path.join(folder(name), 'sketch.json')


def write_sketch(s, path=None):
    path = path or sketch_path(s['name'])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return path


def read_sketch(name_or_path):
    path = name_or_path if name_or_path.endswith('.json') else sketch_path(name_or_path)
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def generate(s, out=None):
    """Write <name>.py and <name>_names.py for sketch s into out (default work/mappage/<name>/); returns the module path.
    Files are only rewritten when their text changed."""
    out = out or folder(s['name'])
    os.makedirs(out, exist_ok=True)
    paths = {}
    for fn, text in ((f"{s['name']}.py", module_text(s)), (f"{s['name']}_names.py", names_text(s))):
        p = os.path.join(out, fn)
        old = open(p, encoding='utf-8').read() if os.path.exists(p) else None
        if old != text:
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
        paths[fn] = p
    return paths[f"{s['name']}.py"]


def load(path, tag=None):
    """A generated (or any) map module by file, under a name of its own: sketch_<name>_<hash of the text>, so a module
    generated again is loaded again (contract.map_design caches by module name)."""
    text = open(path, 'rb').read()
    base = os.path.splitext(os.path.basename(path))[0]
    name = f'sketch_{base}_{tag or hashlib.sha1(text).hexdigest()[:10]}'
    sys.modules.pop(name, None)
    return _load(name, path)


def heights(mod):
    w, h, b = platmap.CONTAINER
    return platmap.heights(mod.LAYOUT, w, h, b)[0]


def walk_of(mod, e=None):
    return platmap.walkable(mod.LAYOUT, getattr(mod, 'OBJECTS', []), e=heights(mod) if e is None else e)


def _sha(a):
    import numpy as np
    return hashlib.sha1(np.ascontiguousarray(a).tobytes()).hexdigest()


def _obj_key(o):
    return (o.template, float(o.x), float(o.y), o.side, o.name, o.angle, o.flags, o.site)


def readings(mod):
    """What the rules read off a map module: its height field and walkability (hashes), the design lint (sorted), the
    sites, borders, objects and scenery (order-free), the way the blocks use the ground. Two modules with equal
    readings are the same map to every check."""
    e = heights(mod)
    walk = walk_of(mod, e)
    sites = {k: (s.x, s.y, s.r, s.what, s.build, s.facing, s.cast) for k, s in mod.SITES.items()}
    return {
        'heights': _sha(e), 'walkable': _sha(walk),
        'lint': sorted(platmap.lint(mod.LAYOUT, mod.SITES, getattr(mod, 'OBJECTS', []), getattr(mod, 'SCENERY', []))),
        'ore': sorted(platmap.ore_lint(getattr(mod, 'OBJECTS', []))),
        'sites': sites, 'borders': {k: tuple(map(float, v)) for k, v in mod.BORDERS.items()},
        'objects': sorted(map(_obj_key, getattr(mod, 'OBJECTS', [])), key=repr),
        'scenery': sorted(map(_obj_key, getattr(mod, 'SCENERY', [])), key=repr),
        'blocks': platmap.block_use(mod.LAYOUT, mod.SITES, walk) if mod.LAYOUT.blocks else None,
    }


# ---------------------------------------------------------------- the checks

def inside(mod):
    """The container cells inside the map's playable area (its first border): nobody walks past it."""
    import numpy as np
    w, h, b = platmap.CONTAINER
    x0, y0, x1, y1 = next(iter(mod.BORDERS.values()))
    jj, ii = np.mgrid[0:h, 0:w]
    x, y = (ii - b) * platmap.CELL, (jj - b) * platmap.CELL
    return (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)


def regions(mod, e=None):
    """The walkable regions inside the playable area (ground joined to ground, platmap.walkable: dry, not steeper than
    terrain_rules.STEEP, bridges laid, wall pieces out) and the sites in each. A site off walkable ground is put in the region of the
    nearest walkable cell within its radius (or 30), else in none. Returns {'label': the cell labels (container cells,
    0 = not walkable), 'regions': [{id, cells, sites}], 'start': its region id, 'cut off': sites not in the start's}."""
    import numpy as np
    from scipy import ndimage
    w, h, b = platmap.CONTAINER
    e = heights(mod) if e is None else e
    walk = walk_of(mod, e) & inside(mod)
    label, n = ndimage.label(walk)
    near = ndimage.distance_transform_edt(~walk, return_indices=True)
    sizes = np.bincount(label.ravel(), minlength=n + 1)

    def region_at(x, y, r):
        i, j = int(round(x / platmap.CELL)) + b, int(round(y / platmap.CELL)) + b
        if not (0 <= i < w and 0 <= j < h):
            return 0
        if label[j, i]:
            return int(label[j, i])
        if near[0][j, i] * platmap.CELL <= max(r, 30.0):
            return int(label[near[1][0][j, i], near[1][1][j, i]])
        return 0
    at = {k: region_at(s.x, s.y, s.r) for k, s in mod.SITES.items()}
    start = at.get('start') or region_at(*mod.START, 0.0)
    ids = sorted({v for v in at.values() if v} | ({start} if start else set()), key=lambda k: -sizes[k])
    out = [{'id': k, 'cells': int(sizes[k]), 'km2': round(sizes[k] * platmap.CELL ** 2 / 1e6, 2),
            'sites': [s for s, v in at.items() if v == k]} for k in ids]
    return {'label': label, 'count': int(n), 'regions': out, 'start': start,
            'cut off': [s for s, v in at.items() if v != start and s != 'island'],
            'off ground': [s for s, v in at.items() if not v]}


def pathing(mod, pairs, model_dir=None):
    """Whether ground units find a way between pairs of sites, by the engine line's pathfinding model (ADR 0018: the
    private repository RA3-EngineModel, labpaths.ENGINE_MODEL). None when the model is not on this computer -- the
    caller says so and leaves the walkable regions as the answer. The model is still a skeleton (its own README):
    use it when asked (--pathing), not by default."""
    import labpaths
    path = os.path.join(model_dir or labpaths.ENGINE_MODEL, 'ra3model', 'pathing.py')
    if not os.path.exists(path):
        return None
    pf = _load('ra3model_pathing', path)
    w, h, b = platmap.CONTAINER
    walk = walk_of(mod)[b:h - b, b:w - b]               # the playable square, row 0 = south, as the model's y
    k = max(1, int(round(float(pf.CELL_SIZE) / platmap.CELL)))     # the model's cell (RA3: 20) in our 10-unit cells
    n = walk.shape[0] // k
    walk = walk[:n * k, :n * k].reshape(n, k, n, k).all(axis=(1, 3))     # a model cell is clear only if all of it is
    types = [[pf.CLEAR if walk[j, i] else pf.IMPASSABLE for i in range(n)] for j in range(n)]
    grid = pf.classify(pf.Grid(types))
    out = []
    for a, z in pairs:
        sa, sz = mod.SITES[a], mod.SITES[z]
        r = pf.find_path(grid, pf.world_to_cell(sa.x, sa.y), pf.world_to_cell(sz.x, sz.y))
        d = {'from': a, 'to': z, 'found': r.found, 'reason': r.reason, 'cells': len(r.cells), 'at': [sz.x, sz.y]}
        if not r.found and getattr(r, 'approximate', False) and r.goal is not None:
            # RA3's plain move: the unit drives to the searched cell nearest the goal and stops there (pathing.md 1)
            d['stop'] = [float(v) for v in pf.cell_center(*r.goal)]
            d['gap'] = round(float(r.gap) * float(pf.CELL_SIZE), 1)
        out.append(d)
    return out


STOP_WORDS = '游戏不报错，单位会开到半路停住；脚本派兵请分段下令；模型偏保守，可能多报'


def stops(paths, reg):
    """The pairs the walkable regions join but the pathfinding model does not (docs/engine/pathing.md 1: over its
    search budget the game says nothing, the unit drives to the searched cell nearest the goal and stops there). Not
    a failure -- the model is cautious on long detours across a big map (trial2 / trial3: the lake shore reads
    'budget', the game got there in 16 s / 13 s) -- a warning, kept apart from the sites nobody can walk to."""
    if not isinstance(paths, list):
        return []
    cut = set(reg['cut off'])
    return [p for p in paths if not p['found'] and p['to'] not in cut]


NARROW = 50.0       # docs/engine/pathing.md 4: six tanks went through a 50-wide gap; narrower is not measured
NARROW_LONG = 100.0         # a slit shorter than this is a cliff foot's corner, not a lane
NARROW_WORDS = (f'悬崖或墙离地图边只剩窄缝（能走，但比 {NARROW:g} 窄）：车会往缝里开然后卡住；'
                f'要么把墙画到边外封死，要么让出 {NARROW:g} 以上')


def narrow_edges(mod, walk=None):
    """Slits between a cliff (or a wall) and the edge of the playable area: walkable, so the regions join through
    them, but narrower than NARROW -- a vehicle sent along the edge drives in and sticks. Each: {x, y (its middle),
    width, length} in world units, widest-first by length."""
    import numpy as np
    from scipy import ndimage
    walk = (walk_of(mod) if walk is None else walk) & inside(mod)
    rad = NARROW / platmap.CELL / 2
    k = int(math.floor(rad))
    jj, ii = np.mgrid[-k:k + 1, -k:k + 1]
    disk = ii * ii + jj * jj <= rad * rad
    roomy = ndimage.binary_opening(walk, structure=disk)        # where a NARROW-wide body fits
    slit = walk & ~roomy
    to_edge = ndimage.distance_transform_edt(inside(mod)) * platmap.CELL
    across = ndimage.distance_transform_edt(walk) * platmap.CELL
    label, n = ndimage.label(slit)
    near_roomy = ndimage.binary_dilation(roomy, iterations=1)
    w, h, b = platmap.CONTAINER
    out = []
    for k, sl in enumerate(ndimage.find_objects(label), 1):
        part = label[sl] == k
        length = max(part.shape) * platmap.CELL
        if length < NARROW_LONG or (to_edge[sl][part] <= NARROW).mean() < 0.5 or not (near_roomy[sl] & part).any():
            continue                    # a short corner, a slit away from the edge, or one no vehicle can drive into
        js, is_ = np.nonzero(part)
        mid = len(js) // 2
        order = np.lexsort((is_, js))
        j, i = js[order[mid]] + sl[0].start, is_[order[mid]] + sl[1].start
        out.append({'x': float((i - b) * platmap.CELL), 'y': float((j - b) * platmap.CELL),
                    'width': float(round(2 * across[sl][part].max() - platmap.CELL)), 'length': float(length)})
    return sorted(out, key=lambda d: -d['length'])


NEAR_WORDS = '两个地点几乎在同一个位置：多半是重复的（比如 start 和出生点所在的地点），留一个，任务按另一个名字放东西就好'


def near_sites(mod):
    """Pairs of sites that stand nearly on one spot (closer than NEAR, or a fifth of the smaller radius): one is
    probably a copy of the other (Brussels: start and west suburb). Refinery sites are made from FIELDS: left out.
    A warning: it does not make the sketch fail."""
    pts = [(k, s) for k, s in mod.SITES.items() if not k.endswith(' refinery') and k != 'island']   # the container's
    out = []
    for i, (a, p) in enumerate(pts):
        for b, q in pts[i + 1:]:
            d = math.dist((p.x, p.y), (q.x, q.y))
            if d < max(NEAR, min(p.r, q.r) / 5):
                out.append({'a': a, 'b': b, 'gap': round(d, 1), 'x': p.x, 'y': p.y})
    return out


def _mission(mod, name):
    m = parts.Mission(name=f'CampSk{name[:8].title()}', map=mod)
    m.scripts += opening_camera(m)
    return m


def opening_camera(m):
    """K5 (I23, contract.start_camera_inside_the_view): the game opens with its camera on the `start` site, drawn
    where the player starts -- often nearer the map's edge than half a screen, and then the first picture shows the
    black beyond it. So the draft's mission, like a level's Phase 1 (plan.opening_camera), cuts the camera at the start
    to the view point of `start` (held inside model.view_rect of the first border, published in m.views for
    contract.camera_outside_the_view). The start itself stays where it was drawn. No script when it is inside."""
    import model
    borders, start = getattr(m.map, 'BORDERS', None) or {}, (getattr(m.map, 'SITES', None) or {}).get('start')
    if not borders or start is None:
        return []
    rect = model.view_rect([next(iter(borders.values()))])
    x, y = min(max(start.x, rect[0]), rect[2]), min(max(start.y, rect[1]), rect[3])
    if (x, y) == (start.x, start.y):
        return []
    at = f'CNV {m.name} Cam start {x:.0f} {y:.0f}'          # (an asset id: letters, digits and spaces only)
    m.waypoints[at], m.views[at] = (x, y), rect
    return [parts.Script(f'CNV {m.name}{contract.OPENING_CAMERA}', [], [('MOVE_CAMERA_TO', at, 0.1, 0.0, 0.0, 0.0)])]


def _tail(text, n=8):
    return '\n'.join(text.strip().splitlines()[-n:])


def study(path):
    """mapstudy --ours and terrainref on a written .map, the way cnv_preview reads them: (lines, picture path)."""
    lines, pic = [], None
    for script, args in (('mapstudy.py', ['--ours', path]), ('terrainref.py', [path])):
        r = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(CAMPAIGN, script), *args],
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
        if r.returncode:
            lines.append(f'{script} FAILED: {_tail(r.stdout + r.stderr, 5)}')
            continue
        for x in r.stdout.splitlines():
            if x.startswith('PICTURE '):
                pic = x[8:]
            elif script == 'mapstudy.py' or x.startswith('TERRAIN '):
                lines.append(x)
    return lines, pic


def region_png(label, path, start):
    """The regions as a picture, north up, one pixel per cell of the playable square: the start's region green, the
    others in their own colours, the ground nobody walks on clear."""
    import numpy as np
    from PIL import Image
    w, h, b = platmap.CONTAINER
    lab = label[b:h - b, b:w - b][::-1]
    rgba = np.zeros(lab.shape + (4,), np.uint8)
    others = [(230, 80, 60), (70, 130, 230), (230, 170, 40), (170, 80, 210), (40, 190, 190), (220, 90, 160)]
    ids = [k for k in np.unique(lab) if k]
    for n, k in enumerate(ids):
        rgba[lab == k] = (60, 200, 90, 120) if k == start else (*others[n % len(others)], 150)
    Image.fromarray(rgba, 'RGBA').save(path)
    return path


def ground_png(mf, path):
    """The written map's ground from above (maprender, as the map page draws its levels), north up."""
    import maprender
    from PIL import Image
    full = path + '.full.png'
    maprender.render(mf, full, px=1, plain=True)
    Image.open(full).convert('RGB').save(path)
    os.remove(full)
    return path


def report(name, s=None, with_map=True, with_pathing=False, out=None):
    """Generate the draft for sketch s (default: work/mappage/<name>/sketch.json) and check it. Returns a dict the map
    page shows (and the CLI prints): files, lint, contract, regions, map, study, pathing."""
    s = s or read_sketch(name)
    d = out or folder(s['name'])
    out = {'name': s['name'], 'problems': check_sketch(s)}
    if out['problems']:
        out['ok'] = False
        return out
    path = generate(s, d)
    out['module'] = os.path.relpath(path, ROOT).replace(os.sep, '/')
    mod = load(path)
    m = _mission(mod, s['name'])
    out['lint'] = contract.map_design(m)
    out['contract'] = parts.contract(parts.merged(m))
    reg = regions(mod)
    out['regions'] = {k: v for k, v in reg.items() if k != 'label'}
    region_png(reg['label'], os.path.join(d, 'regions.png'), reg['start'])
    out['regions_png'] = 'regions.png'
    out['narrow'] = narrow_edges(mod)
    out['near'] = near_sites(mod)
    if with_pathing:
        pairs = [('start', k) for k in mod.SITES if k not in ('start', 'island') and not k.endswith(' refinery')]
        res = pathing(mod, pairs)
        out['pathing'] = res if res is not None else '引擎线的寻路模型不在这台电脑上（labpaths.ENGINE_MODEL），只看连通区'
    else:
        out['pathing'] = '没跑（--pathing 才跑）'
    out['stops'] = stops(out['pathing'], reg)          # warnings: they do not make the sketch fail
    if with_map:
        try:
            out.update(write_and_study(m, d, s['name'], bool(out['contract'])))
        except ValueError as e:                     # platmap.apply refuses a layout it cannot write (a flat ramp ...)
            out['map_error'] = str(e)
    out['ok'] = not out['lint'] and not out['contract'] and not reg['cut off'] and 'map_error' not in out
    with open(os.path.join(d, 'report.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def write_and_study(m, d, name, broken):
    """The .map a build would write (parts.preview; with a broken contract written anyway -- the ground is still worth a
    look), its ground picture and its study."""
    from mapscript import MapFile
    mp = os.path.join(d, name + '.map')
    if not broken:
        parts.preview(m, out=mp)
    else:
        with open(mp, 'wb') as f:
            f.write(build_map(m).map_file())
    ground_png(MapFile(open(mp, 'rb').read()), os.path.join(d, 'ground.png'))
    lines, _ = study(mp)
    return {'map': os.path.relpath(mp, ROOT).replace(os.sep, '/'), 'ground_png': 'ground.png', 'study': lines}


def build_map(m):
    import make_campnew18 as c18
    from mapscript import MapFile
    _, data = next((p, x) for p, x in c18.c6._map_files() if p.lower().endswith('.map'))
    mf = MapFile(data)
    parts.write_map(mf, m)
    return mf


def map_module(name):
    """An existing map module by its short name (experimental/cnv/maps/<name>.py) and its Chinese names."""
    import importlib
    mod = importlib.import_module(f'maps.{name}')
    p = os.path.join(CNV, 'maps', f'{name}_names.py')
    names = dict(_load(f'{name}_names', p).NAMES) if os.path.exists(p) else {}
    return mod, names


def text_report(r):
    out = [f"草图 {r['name']}: " + ('全部通过' if r.get('ok') else '有问题')]
    if r.get('problems'):
        return '\n'.join(out + ['草图本身: ' + p for p in r['problems']])
    out.append(f"模块草稿 {r['module']}")
    out.append('LINT ' + ('ok' if not r['lint'] else '; '.join(r['lint'])))
    out.append('CONTRACT ' + ('ok' if not r['contract'] else '; '.join(r['contract'])))
    g = r['regions']
    out.append(f"连通区 {g['count']} 块；起点所在 {g['start']}；走不到的地点: " + (', '.join(g['cut off']) or '无'))
    if r.get('map'):
        out.append(f"MAP {r['map']}")
        out += r.get('study', [])
    p = r.get('pathing')
    out.append('寻路 ' + (p if isinstance(p, str) else '; '.join(
        f"{x['from']}→{x['to']} {'通' if x['found'] else '不通 ' + x['reason']}" for x in p)))
    for x in r.get('stops', []):
        at = f"，停在 ({x['stop'][0]:.0f}, {x['stop'][1]:.0f})，离目标 {x['gap']:.0f}" if x.get('stop') else ''
        out.append(f"可能半路停住 {x['from']}→{x['to']}（连通区能到，模型 {x['reason']}{at}）：{STOP_WORDS}")
    for x in r.get('narrow', []):
        out.append(f"贴边窄缝 ({x['x']:.0f}, {x['y']:.0f}) 宽约 {x['width']:.0f}、长 {x['length']:.0f}：{NARROW_WORDS}")
    for x in r.get('near', []):
        out.append(f"地点重合 {x['a']} 和 {x['b']} 相距 {x['gap']:.0f}（({x['x']:.0f}, {x['y']:.0f})）：{NEAR_WORDS}")
    return '\n'.join(out)


def summary(r):
    """The few lines an agent needs: the verdict, each failing check, the warnings, where the files are (the long
    study is in report.json and on the page)."""
    full = text_report(r).split('\n')
    if r.get('problems'):
        return '\n'.join(full)
    keep = ('草图 ', '模块草稿 ', 'LINT ', 'CONTRACT ', '连通区 ', 'MAP ', '可能半路停住 ', '贴边窄缝 ', '地点重合 ')
    out = [x for x in full if x.startswith(keep)]
    if r.get('map_error'):
        out.append('写不出 .map: ' + r['map_error'])
    p = r.get('pathing')
    if isinstance(p, str):
        out.append('寻路 ' + p)
    else:
        bad = [x for x in p if not x['found']]
        out.append(f"寻路 {len(p) - len(bad)}/{len(p)} 通" + (('；不通: ' + ', '.join(f"{x['to']}（{x['reason']}）"
                                                                                     for x in bad)) if bad else ''))
    out.append(f"全文 {os.path.relpath(os.path.join(folder(r['name']), 'report.json'), ROOT).replace(os.sep, '/')}")
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('name')
    ap.add_argument('--from', dest='src', help='write the sketch of this existing map module (maps/<name>.py) first')
    ap.add_argument('--no-map', action='store_true', help='lint and regions only')
    ap.add_argument('--pathing', action='store_true', help="the engine line's pathfinding model too (if present)")
    ap.add_argument('--sketch', metavar='FILE', help='a sketch written anywhere (- = stdin): saved as '
                    'work/mappage/<name>/sketch.json first (docs/shell/sketch-format.md)')
    ap.add_argument('--check', action='store_true', help='print a short summary (verdict, failures, warnings, file '
                    'paths) instead of the whole report; the whole report is in report.json')
    a = ap.parse_args()
    if a.src and a.sketch:
        ap.error('--from or --sketch, not both')
    if a.src:
        mod, names = map_module(a.src)
        s = from_module(mod, names)
        s['name'] = a.name
        print('SKETCH ' + write_sketch(s))
    if a.sketch:
        text = sys.stdin.read() if a.sketch == '-' else open(a.sketch, encoding='utf-8').read()
        try:
            s = json.loads(text)
        except ValueError as e:
            sys.exit(f'草图 {a.sketch}: 不是 JSON（{e}）')
        if not isinstance(s, dict):
            sys.exit(f'草图 {a.sketch}: 要一个 JSON 对象')
        s['name'] = a.name
        print('SKETCH ' + write_sketch(s))
    if a.check:                                 # the build's own prints (terrain, objects counts) are not the summary
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            r = report(a.name, with_map=not a.no_map, with_pathing=a.pathing)
    else:
        r = report(a.name, with_map=not a.no_map, with_pathing=a.pathing)
    print(summary(r) if a.check else text_report(r))
    sys.exit(0 if r.get('ok') else 1)


if __name__ == '__main__':
    main()
