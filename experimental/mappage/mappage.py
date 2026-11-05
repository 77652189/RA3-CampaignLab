"""The editable map page (ADR 0017): one level's map, timeline and product-rule results, exported from the sources on
every run -- never typed up by hand -- into one HTML page; the page keeps the viewer's change proposals (drag a site,
draw a block line, pin a note) in its own store, and --pull reads them back as a list the level line works from.

  python -I -X utf8 experimental/mappage/mappage.py a4             -> work/mappage/a4/a4_mappage.html (+ a4.json, a4.png)
  python -I -X utf8 experimental/mappage/mappage.py a4 --no-picture   (skip the top-down picture: seconds faster)
  python -I -X utf8 experimental/mappage/mappage.py a4 --pull [FILE]  the proposals as a readable list
  python -I -X utf8 experimental/mappage/mappage.py a4 --apply-preview [FILE] [--only ID ...]
      the terrain proposals applied to the map a build writes (terrain_edit.py), and which contract rules that turns red

Terrain proposals (raise, lower, flatten, paint the impassable bit) are brush strokes; terrain_edit.py says what a stroke
does and terrain.js, put into the page, is its mirror for the live preview (tests/test_mappage_terrain.py holds them to
the same result). The rules after the ground moves are the engine line's terrain_rules.py.

Where everything comes from:
  - the map: the map module's SITES, BORDERS, OBJECTS (resources.py's ore, oil and pads included), SCENERY, LAYOUT
    (roads, ramps, gaps) and the mission's own placed objects (build.resolve -> Mission);
  - the picture: the map a build would write (package.write_map on the container map) drawn by maprender, ground only;
  - the timeline: sim.simulate's event log (the level's scripts as built, the player doing nothing unless --script);
  - the rules: contract.contract over the merged mission, exactly what `build.py <level> --show` prints, and each rule
    function on its own so the page can draw where it fails.

The page runs on this computer (user 2026-11-04): serve.py writes it, serves it on 127.0.0.1 and keeps its proposals
as files, work/mappage/<level>/proposals/<id>.json; it also answers the page's "every rule" button with preview() below.
The map module stays the one source, changed by the level line. --pull and --apply-preview read that folder by default
(or another folder holding proposals/<id>.json, or one JSON file holding the documents).

  python -I -X utf8 experimental/mappage/serve.py a4        -> open http://127.0.0.1:8765/
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
TERRAIN_JS = os.path.join(HERE, 'terrain.js')
LABELS_JS = os.path.join(HERE, 'labels.js')


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
terrain_edit = _load('terrain_edit', os.path.join(HERE, 'terrain_edit.py'))

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


def built_map(m):
    """The map the build writes (the container map with the mission in it). Written with write_map directly, so a
    mission whose contract fails still gets one."""
    import make_campnew18 as c18
    from mapscript import MapFile
    _, data = next((p, d) for p, d in c18.c6._map_files() if p.lower().endswith('.map'))
    mf = MapFile(data)
    parts.write_map(mf, m)
    return mf


def picture(mf, path):
    """A written map from above, ground only; returns the world rectangle it covers."""
    import maprender
    import mapterrain
    from PIL import Image
    hm = mapterrain.HeightMap(mf)
    png = path + '.full.png'
    maprender.render(mf, png, px=PX, plain=True)
    img = Image.open(png).convert('RGB')
    img.save(path, 'JPEG', quality=82)
    os.remove(png)
    w, h = hm.width - 2 * hm.border, hm.height - 2 * hm.border
    return [0.0, 0.0, w * CELL, h * CELL]


def site_names(mp):
    """The map's Chinese site names: maps/<map>_names.py next to the map module (NAMES), or {} if it has none."""
    short = mp.__name__.split('.')[-1]
    path = os.path.join(CNV, 'maps', f'{short}_names.py')
    if not os.path.exists(path):
        return {}
    return dict(_load(f'{short}_names', path).NAMES)


def export(name, with_picture=True, script=''):
    m, _, mod = build.resolve(name, '')
    m = parts.merged(m, None)
    mp = m.map
    sites = getattr(mp, 'SITES', {})
    out_dir = os.path.join(OUT, name)
    os.makedirs(out_dir, exist_ok=True)
    jpg = os.path.join(out_dir, name + '.jpg')
    world = list(getattr(mp, 'BORDERS', {}).get('whole', (0.0, 0.0, 5000.0, 5000.0)))
    ground = None
    zh = site_names(mp)
    if with_picture:
        mf = built_map(m)
        world = picture(mf, jpg)
        g = terrain_edit.from_map(mf)
        ground = dict(terrain_edit.params(g), **terrain_edit.encode(g))
    d = {
        'level': name, 'mod': mod, 'map': mp.__name__.split('.')[-1], 'world': world,
        'sites': [{'k': k, 'zh': zh.get(k, ''), 'x': _r(s.x), 'y': _r(s.y), 'r': _r(s.r), 'what': s.what, 'cast': _r(s.cast),
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
        'terrain': ground,
    }
    for o in d['map_objects'] + d['objects']:
        o['kind'] = kind_of(o['t'])
    plain = dict(d, terrain=None if ground is None else {k: v for k, v in ground.items() if k not in ('elev', 'bits')})
    json.dump(plain, open(os.path.join(out_dir, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    img = ''
    if os.path.exists(jpg):
        img = 'data:image/jpeg;base64,' + base64.b64encode(open(jpg, 'rb').read()).decode()
    page = open(TEMPLATE, encoding='utf-8').read()
    page = page.replace('__TERRAIN_JS__', open(TERRAIN_JS, encoding='utf-8').read())
    page = page.replace('__LABELS_JS__', open(LABELS_JS, encoding='utf-8').read())
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


def read_proposals(name, path):
    """The level's proposals from a saved file or an ArtifactData out_dir (<path>/proposals/<id>.json, the body only)."""
    if os.path.isdir(path):
        sub = os.path.join(path, 'proposals') if os.path.isdir(os.path.join(path, 'proposals')) else path
        raw = [{'id': f[:-5], 'data': json.load(open(os.path.join(sub, f), encoding='utf-8'))}
               for f in sorted(os.listdir(sub)) if f.endswith('.json')]
    else:
        raw = json.load(open(path, encoding='utf-8'))
    return [p for p in _docs(raw) if p.get('level', name) == name]


OP_NAME = {'raise': '抬高', 'lower': '压低', 'flatten': '整平', 'block': '画不可通行', 'unblock': '擦不可通行'}


def _terrain_line(p, sites):
    """One terrain proposal: its brushes, and where they are (the box they cover, the sites inside or nearest)."""
    sts = p.get('strokes', [])
    pts = [(x, y, float(st['r'])) for st in sts for x, y in terrain_edit.dabs(st['dabs'])]
    if not pts:
        return ['地形：没有笔画']
    x0, y0 = min(x - r for x, y, r in pts), min(y - r for x, y, r in pts)
    x1, y1 = max(x + r for x, y, r in pts), max(y + r for x, y, r in pts)
    n = {}
    for st in sts:
        n[st['op']] = n.get(st['op'], 0) + 1
    inside = [k for k, s in sites.items() if s.r < 1000 and any(math.dist((s.x, s.y), (x, y)) < r for x, y, r in pts)]
    out = [f'地形 {len(sts)} 笔（' + '、'.join(f'{OP_NAME.get(k, k)} {v}' for k, v in n.items()) +
           f'），范围 ({x0:.0f}, {y0:.0f})–({x1:.0f}, {y1:.0f})']
    for st in sts:
        what = f'   {OP_NAME.get(st["op"], st["op"])}：半径 {float(st["r"]):g}'
        if st['op'] in terrain_edit.HEIGHT_OPS:
            what += f'，强度 {float(st["s"]):g}/下'
        if st['op'] == 'flatten':
            what += f'，拉向高度 {float(st["height"]):g}'
        out.append(what + f'，{len(terrain_edit.dabs(st["dabs"]))} 下')
    if inside:
        out.append(f'   刷到的地点：{", ".join(inside)}')
    else:
        out.append(f'   位置：{_where(sites, (x0 + x1) / 2, (y0 + y1) / 2)}')
    return out


def pull(name, path):
    m, _, _ = build.resolve(name, '')
    sites = getattr(m.map, 'SITES', {})
    docs = read_proposals(name, path)
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
        elif p['kind'] == 'terrain':
            first, *rest = _terrain_line(p, sites)
            lines.append(f'{head} {first}')
            lines += rest
        else:
            x, y = p['at_xy']
            lines.append(f'{head} 批注 {_where(sites, x, y)}')
        lines.append(f'   为什么：{why or "（没写）"}' + (f'；状态 {p["status"]}' if p.get('status') else ''))
    return '\n'.join(lines)


def preview_base(name):
    """What every preview of one level starts from, built once (the map build takes seconds; serve.py keeps it): the
    merged mission, its sites, the ground the build writes and the contract on that ground."""
    m, _, _ = build.resolve(name, '')
    m = parts.merged(m, None)
    g0 = terrain_edit.from_map(built_map(m))
    with terrain_edit.lint_on(g0):
        before = parts.contract(m)
    return {'name': name, 'm': m, 'sites': getattr(m.map, 'SITES', {}), 'g0': g0, 'before': before}


def preview(base, docs):
    """The terrain proposals in docs (in the order given) applied with terrain_edit on base's ground, then the contract
    run on the edited ground against the unedited one. Returns the steps, the sites whose flat-enough verdict flips,
    the contract before and after, and which problems go red or clear. The map module is not touched."""
    m, sites, g0 = base['m'], base['sites'], base['g0']
    docs = [p for p in docs if p.get('kind') == 'terrain']
    g, steps = g0, []
    for p in docs:
        g1, _ = terrain_edit.apply_proposals(g, [p])
        steps.append({'id': p.get('id', ''), 'line': _terrain_line(p, sites)[0], 'moved': 0, 'up': 0.0, 'down': 0.0, 'blocked': 0,
                      'opened': 0, **(terrain_edit.summary(p, g, g1) or {})})
        g = g1
    f0, f1 = terrain_edit.flat_sites(g0, sites), terrain_edit.flat_sites(g, sites)
    flips = [{'site': k, 'what': w, 'flat': f1[(k, w)]} for (k, w) in f0 if f0[(k, w)] != f1[(k, w)]]
    before = base['before']
    if docs:
        with terrain_edit.lint_on(g):
            after = parts.contract(m)
    else:
        after = before
    import terrain_rules
    return {'steps': steps, 'flips': flips, 'before': list(before), 'after': list(after),
            'red': [p for p in after if p not in before], 'cleared': [p for p in before if p not in after],
            'must_follow': [k for k, _ in terrain_rules.MUST_FOLLOW]}


def apply_preview(name, path, ids=None, base=None):
    """--apply-preview: the terrain proposals saved in path (all, or those in ids, in the order they were made), as
    text (preview() is the result as data)."""
    docs = [p for p in read_proposals(name, path) if p['kind'] == 'terrain' and (not ids or p.get('id') in ids)]
    lines = [f'{name}：{len(docs)} 条地形提议按先后套在构建出的地图上（{os.path.relpath(path, ROOT)}）']
    if not docs:
        return '\n'.join(lines)
    r = preview(base or preview_base(name), docs)
    for i, s in enumerate(r['steps'], 1):
        lines.append(f'{i}. [{s["id"]}] {s["line"]}')
        lines.append(f'   高度改了 {s["moved"]} 格（最多抬 {max(0.0, s["up"]):.1f}、压 {max(0.0, -s["down"]):.1f}，我们的单位；世界单位 ×'
                     f'{terrain_edit._rules().WORLD_PER_OURS}），新不可通行 {s["blocked"]} 格，新可通行 {s["opened"]} 格')
    lines.append('平不平（terrain_rules.flat_enough，地点的建筑方块和施法圆）：' +
                 ('没有变化' if not r['flips'] else '；'.join(f'{f["site"]} 的{"建筑点" if f["what"] == "build" else "施法点"}'
                                                         f'{"变平了" if f["flat"] else "不再平"}' for f in r['flips'])))
    lines.append(f'contract：改之前 {len(r["before"]) or "ok"}，改之后 {len(r["after"]) or "ok"}'
                 f'（同一套检查，地图设计那部分读改过的地面和画过的通行位）')
    lines += [f'   新红 {p}' for p in r['red']] + [f'   变好 {p}' for p in r['cleared']]
    lines.append('关卡线改地图模块时一起带上：' + '；'.join(r['must_follow']))
    return '\n'.join(lines)


def proposals_dir(name):
    """Where the local page server (serve.py) keeps a level's proposals: work/mappage/<level>/proposals/<id>.json;
    --pull and --apply-preview read this by default."""
    return os.path.join(OUT, name, 'proposals')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--pull', nargs='?', const='', default=None, metavar='FILE',
                    help='list the proposals saved in FILE or folder (default work/mappage/<name>, where serve.py saves)')
    ap.add_argument('--apply-preview', nargs='?', const='', default=None, metavar='FILE',
                    help='apply the terrain proposals (FILE or folder, as --pull) to the built map and run the contract')
    ap.add_argument('--only', nargs='*', default=None, metavar='ID', help='with --apply-preview: just these proposals')
    ap.add_argument('--no-picture', action='store_true')
    ap.add_argument('--script', default='', help="the simulator's player script (sim.py --script)")
    a = ap.parse_args()
    if a.apply_preview is not None:
        print(apply_preview(a.name, a.apply_preview or os.path.join(OUT, a.name), a.only))
        return
    if a.pull is not None:
        print(pull(a.name, a.pull or os.path.join(OUT, a.name)))
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
