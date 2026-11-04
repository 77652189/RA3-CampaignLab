"""The editable map page (ADR 0017): one level's map, timeline and product-rule results, exported from the sources on
every run -- never typed up by hand -- into one HTML page; the page keeps the viewer's change proposals (drag a site,
draw a block line, pin a note) in its own store, and --pull reads them back as a list the level line works from.

  python -I -X utf8 experimental/mappage/mappage.py a4             -> work/mappage/a4/a4_mappage.html (+ a4.json, a4.png)
  python -I -X utf8 experimental/mappage/mappage.py a4 --no-picture   (skip the top-down picture: seconds faster)
  python -I -X utf8 experimental/mappage/mappage.py a4 --pull [FILE]  the proposals as a readable list

Where everything comes from:
  - the map: the map module's SITES, BORDERS, OBJECTS (resources.py's ore, oil and pads included), SCENERY, LAYOUT
    (roads, ramps, gaps) and the mission's own placed objects (build.resolve -> Mission);
  - the picture: the map a build would write (package.write_map on the container map) drawn by maprender, ground only;
  - the timeline: sim.simulate's event log (the level's scripts as built, the player doing nothing unless --script);
  - the rules: contract.contract over the merged mission, exactly what `build.py <level> --show` prints, and each rule
    function on its own so the page can draw where it fails.

The page only stores proposals (ArtifactData collection 'proposals'); the map module stays the one source, changed by
the level line. --pull reads what an Agent saved of that collection: by default the folder the ArtifactData 'list'
writes with out_dir=work/mappage/<level>/pulled (one <doc id>.json per proposal, under pulled/proposals/), or one JSON
file holding the documents.

  ArtifactData list, url <the page>, collection proposals, out_dir work/mappage/a4/pulled
  python -I -X utf8 experimental/mappage/mappage.py a4 --pull
"""
import argparse
import base64
import importlib.util
import io
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CNV = os.path.join(ROOT, 'experimental', 'cnv')
TEMPLATE = os.path.join(HERE, 'template.html')


def _load(name, path):
    """A module by file (importlib, as testbench/doctor.py does): this file adds nothing to sys.path (guard G4).
    build.py puts experimental/cnv and experimental/campaign on the path itself when it loads."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


build = _load('build', os.path.join(CNV, 'build.py'))
import parts                                    # noqa: E402  (on the path build.py set)
import contract                                 # noqa: E402

CELL = 10.0                                     # world units per map cell (mapterrain.CELL)
PX = 2                                          # picture pixels per cell
OUT = os.path.join(ROOT, 'work', 'mappage')

# The rules the page draws, each one contract function (all of them run inside contract.contract too); the rest of the
# contract's problems are listed without a place.
RULES = [
    ('cast', '施法点', 'cast_points_clear', '冰墙施法点是地图地点、圆里平整可走、没有东西'),
    ('ore', '矿对矿场', 'ore_faces_refinery', '每个矿场正前方 180 有一块矿'),
    ('ore', '矿成组', 'ore_in_groups', '矿一块或一对，而且都是 resources.Field 生成的'),
    ('ore', '油井离营地', 'oil_off_the_camps', '油井离敌方营地至少 400'),
    ('ore', '基地有矿', 'base_has_ore', '基地 1000 以内有一组矿'),
    ('map', '地图设计', 'map_design', '坡道、建筑地基、桥、街区、豁口、布景不挡路'),
    ('camera', '镜头', 'camera_outside_the_view', '镜头看的点都在屏幕不出地图的范围里'),
]
AT = re.compile(r'\((-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?)\)')
SITE_AT = re.compile(r"(?:site|base) '?([\w ]+?)'?[:(]")


def _r(v):
    return round(float(v), 1)


def _obj(o):
    return {'t': o.template, 'x': _r(o.x), 'y': _r(o.y), 'side': o.side, 'name': o.name, 'site': o.site,
            'a': None if o.angle is None else round(o.angle, 3)}


KIND = [('ore', lambda t: t == 'OreNode'), ('oil', lambda t: t.startswith('OilDerrick')),
        ('bridge', lambda t: 'Bridge' in t), ('wall', lambda t: 'Wall' in t and not t.startswith('CNV')),
        ('ice', lambda t: t.startswith('CNV_A4Ice') or 'Sculpture' in t)]


def kind_of(t):
    return next((k for k, f in KIND if f(t)), 'thing')


def locate(text, m, sites):
    """Where on the map one rule problem is: the coordinates it names, else the site (or the spell mark's site)."""
    pts = [(float(x), float(y)) for x, y in AT.findall(text)]
    if pts:
        return pts[0]
    mark = re.search(r"spell mark '([^']+)'", text)
    if mark and m.spells.get(mark.group(1)) in sites:
        s = sites[m.spells[mark.group(1)]]
        return (s.x, s.y)
    for g in SITE_AT.finditer(text):
        name = g.group(1).strip()
        if name in sites:
            return (sites[name].x, sites[name].y)
    return None


def rules(m):
    """contract.contract (the --show line) and each drawn rule on its own, with where each problem is."""
    sites = getattr(m.map, 'SITES', {})
    total = parts.contract(m)
    out, drawn = [], set()
    for group, label, fn, what in RULES:
        found = getattr(contract, fn)(m)
        drawn |= set(found)
        out.append({'group': group, 'label': label, 'fn': fn, 'what': what,
                    'problems': [{'text': p, 'at': locate(p, m, sites)} for p in found]})
    rest = [p for p in total if p not in drawn and not any(p.endswith(d) for d in drawn)]
    out.append({'group': 'other', 'label': '其余接口规则', 'fn': 'contract', 'what': '脚本用到的名字都有人发布、台词走出口等',
                'problems': [{'text': p, 'at': locate(p, m, sites)} for p in rest]})
    return {'show': 'ok' if not total else f'{len(total)} problems', 'total': total, 'rules': out}


def guides(m):
    """What the rules measure, drawn whether they pass or not: each cast circle, each refinery's ore spot, the oil
    clearance round enemy bases, the ore reach round each base."""
    import resources
    sites = getattr(m.map, 'SITES', {})
    casts = [{'mark': wp, 'site': k, 'x': _r(sites[k].x), 'y': _r(sites[k].y), 'r': _r(sites[k].cast)}
             for wp, k in m.spells.items() if k in sites and sites[k].cast]
    pads = [{'site': k, 'x': _r(s.x), 'y': _r(s.y), 'fx': _r(s.x + resources.AXIS * math.cos(s.facing)),
             'fy': _r(s.y + resources.AXIS * math.sin(s.facing)), 'slack': resources.AXIS_SLACK}
            for k, s in sites.items() if s.facing is not None]
    bases = [{'site': k, 'owner': owner, 'x': _r(x), 'y': _r(y), 'ore': resources.BASE_ORE,
              'oil': resources.OIL_CLEAR if owner == 's1' else 0} for k, owner, x, y in contract._bases(m)]
    return {'casts': casts, 'pads': pads, 'bases': bases}


def layout(mp):
    lay = getattr(mp, 'LAYOUT', None)
    if lay is None:
        return {}
    return {'roads': [{'pts': [[_r(x), _r(y)] for x, y in r.points], 'w': _r(r.width)} for r in lay.roads],
            'ramps': [{'low': [_r(v) for v in r.low], 'high': [_r(v) for v in r.high], 'w': _r(r.width), 'what': r.what}
                      for r in lay.ramps],
            'gaps': [{'x': _r(g.x), 'y': _r(g.y), 'w': _r(g.width), 'what': g.what} for g in lay.gaps]}


def timeline(name, script=''):
    """The simulator's events: (seconds, kind, text), units made in one tick folded into one row."""
    sim = _load('sim', os.path.join(CNV, 'sim.py'))
    s = sim.simulate(name, '', script)
    rows, made = [], {}
    for t, k, x in s.log:
        if k == '出现':
            if t not in made:
                made[t] = {'t': round(t, 1), 'k': k, 'x': '', 'n': 0}
                rows.append(made[t])
            made[t]['n'] += 1
            made[t]['x'] = made[t]['x'] or x
            continue
        rows.append({'t': round(t, 1), 'k': k, 'x': x})
    for r in rows:
        if r.get('n', 0) > 1:
            r['x'] = f'{r["n"]} 个：{r["x"]}……'
        r.pop('n', None)
    return {'ending': s.ending_line(), 'rows': rows}


def picture(m, path):
    """The map the build writes (the container map with the mission in it), from above, ground only; returns the world
    rectangle it covers. Written with write_map directly, so a mission whose contract fails still gets a picture."""
    import make_campnew18 as c18
    import maprender
    import mapterrain
    from mapscript import MapFile
    from PIL import Image
    _, data = next((p, d) for p, d in c18.c6._map_files() if p.lower().endswith('.map'))
    mf = MapFile(data)
    parts.write_map(mf, m)
    hm = mapterrain.HeightMap(mf)
    png = path + '.full.png'
    maprender.render(mf, png, px=PX, plain=True)
    img = Image.open(png).convert('RGB')
    img.save(path, 'JPEG', quality=82)
    os.remove(png)
    w, h = hm.width - 2 * hm.border, hm.height - 2 * hm.border
    return [0.0, 0.0, w * CELL, h * CELL]


def export(name, with_picture=True, script=''):
    m, _, mod = build.resolve(name, '')
    m = parts.merged(m, None)
    mp = m.map
    sites = getattr(mp, 'SITES', {})
    out_dir = os.path.join(OUT, name)
    os.makedirs(out_dir, exist_ok=True)
    jpg = os.path.join(out_dir, name + '.jpg')
    world = list(getattr(mp, 'BORDERS', {}).get('whole', (0.0, 0.0, 5000.0, 5000.0)))
    if with_picture:
        world = picture(m, jpg)
    d = {
        'level': name, 'mod': mod, 'map': mp.__name__.split('.')[-1], 'world': world,
        'sites': [{'k': k, 'x': _r(s.x), 'y': _r(s.y), 'r': _r(s.r), 'what': s.what, 'cast': _r(s.cast),
                   'build': _r(s.build), 'pad': s.facing is not None} for k, s in sites.items()],
        'borders': {k: [_r(v) for v in b] for k, b in getattr(mp, 'BORDERS', {}).items()},
        'map_objects': [_obj(o) for o in getattr(mp, 'OBJECTS', ())],
        'objects': [_obj(o) for o in m.objects],
        'scenery': [[_r(o.x), _r(o.y)] for o in getattr(mp, 'SCENERY', ())],
        'areas': [{'k': k, 'pts': [[_r(x), _r(y)] for x, y in pts]} for k, pts in
                  (m.areas.items() if isinstance(m.areas, dict) else [])],
        'layout': layout(mp),
        'guides': guides(m),
        'rules': rules(m),
        'timeline': timeline(name, script),
    }
    for o in d['map_objects'] + d['objects']:
        o['kind'] = kind_of(o['t'])
    json.dump(d, open(os.path.join(out_dir, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    img = ''
    if os.path.exists(jpg):
        img = 'data:image/jpeg;base64,' + base64.b64encode(open(jpg, 'rb').read()).decode()
    page = open(TEMPLATE, encoding='utf-8').read()
    page = page.replace('__DATA__', json.dumps(d, ensure_ascii=False).replace('</', '<\\/')).replace('__IMG__', img).replace('__TITLE__', f'{name.upper()} 地图改动台')
    html = os.path.join(out_dir, f'{name}_mappage.html')
    open(html, 'w', encoding='utf-8', newline='\n').write(page)
    return html, d


# --pull --------------------------------------------------------------------------------------------------------------

def _docs(raw):
    """The proposal documents from what an Agent saved: a list of documents, or {documents|docs|items: [...]}, each a
    document itself or {id, data: {...}}."""
    if isinstance(raw, dict):
        raw = next((raw[k] for k in ('documents', 'docs', 'items', 'results') if k in raw), [raw])
    out = []
    for doc in raw:
        body = doc.get('data', doc) if isinstance(doc, dict) else {}
        if isinstance(body, dict) and body.get('kind'):
            out.append(dict(body, id=doc.get('id', body.get('id', ''))))
    return sorted(out, key=lambda p: p.get('at', ''))


def nearest(sites, x, y, skip=()):
    """The nearest map site to (x, y) that is a place (not the whole island), and how far."""
    best = min(((math.dist((x, y), (s.x, s.y)), k) for k, s in sites.items() if k not in skip and s.r < 1000),
               default=(None, None))
    return best[1], best[0]


def _where(sites, x, y, skip=(), moving=False):
    k, dist = nearest(sites, x, y, skip)
    at = f'({x:.0f}, {y:.0f})'
    if k is None:
        return at
    if moving:
        return f'{at}，旁边最近的别的地点是 {k!r}（{dist:.0f} 远）'
    if dist <= 60:
        return f'{at} = 地点 {k!r}（差 {dist:.0f}）'
    return f'{at}，离它最近的地点是 {k!r}（{dist:.0f} 远）；要用就新建一个地点'


def pull(name, path):
    m, _, _ = build.resolve(name, '')
    sites = getattr(m.map, 'SITES', {})
    if os.path.isdir(path):                     # ArtifactData out_dir: <path>/proposals/<id>.json, the body only
        sub = os.path.join(path, 'proposals') if os.path.isdir(os.path.join(path, 'proposals')) else path
        raw = [{'id': f[:-5], 'data': json.load(open(os.path.join(sub, f), encoding='utf-8'))}
               for f in sorted(os.listdir(sub)) if f.endswith('.json')]
    else:
        raw = json.load(open(path, encoding='utf-8'))
    docs = [p for p in _docs(raw) if p.get('level', name) == name]
    lines = [f'{name} 的改动提议：{len(docs)} 条（{os.path.relpath(path, ROOT)}；地图模块 maps/{m.map.__name__.split(".")[-1]}.py）']
    for i, p in enumerate(docs, 1):
        why = p.get('why') or p.get('text') or ''
        head = f'{i}. [{p.get("id", "")}]'
        if p['kind'] == 'move':
            k = p.get('site', '')
            s = sites.get(k)
            fx, fy = p['from']
            tx, ty = p['to']
            now = '' if s is None else ('' if (abs(s.x - fx) < 1 and abs(s.y - fy) < 1)
                                         else f'（注意：地图里现在是 ({s.x:g}, {s.y:g})，提议之后改过）')
            lines.append(f'{head} 挪地点 {k!r}：({fx:.0f}, {fy:.0f}) -> ({tx:.0f}, {ty:.0f})，'
                         f'挪了 {math.dist((fx, fy), (tx, ty)):.0f}{now}')
            lines.append(f'   新位置：{_where(sites, tx, ty, skip=(k,), moving=True)}')
        elif p['kind'] == 'block':
            pts = p.get('points', [])
            lines.append(f'{head} 画挡路线：{len(pts)} 个点，长 '
                         f'{sum(math.dist(a, b) for a, b in zip(pts, pts[1:])):.0f}')
            for j, (x, y) in enumerate(pts):
                lines.append(f'   {"起" if j == 0 else "终" if j == len(pts) - 1 else "经"}点 {_where(sites, x, y)}')
        else:
            x, y = p['at_xy']
            lines.append(f'{head} 批注 {_where(sites, x, y)}')
        lines.append(f'   为什么：{why or "（没写）"}' + (f'；状态 {p["status"]}' if p.get('status') else ''))
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--pull', nargs='?', const='', default=None, metavar='FILE',
                    help='list the proposals saved in FILE or folder (default work/mappage/<name>/pulled)')
    ap.add_argument('--no-picture', action='store_true')
    ap.add_argument('--script', default='', help="the simulator's player script (sim.py --script)")
    a = ap.parse_args()
    if a.pull is not None:
        print(pull(a.name, a.pull or os.path.join(OUT, a.name, 'pulled')))
        return
    html, d = export(a.name, not a.no_picture, a.script)
    bad = sum(len(r['problems']) for r in d['rules']['rules'])
    print(f'PAGE {os.path.relpath(html, ROOT)} {os.path.getsize(html) // 1024} KB')
    print(f'contract: {d["rules"]["show"]}; drawn rules: ' +
          ', '.join(f'{r["label"]} {len(r["problems"])}' for r in d['rules']['rules']) + f' ({bad} problems)')
    print(f'sites {len(d["sites"])}, objects {len(d["map_objects"]) + len(d["objects"])}, '
          f'timeline {len(d["timeline"]["rows"])} rows ({d["timeline"]["ending"]})')


if __name__ == '__main__':
    main()
