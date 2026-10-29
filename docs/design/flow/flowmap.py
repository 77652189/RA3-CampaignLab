"""The sketch map (示意图) drawn on the real map. A flow script whose 示意图 names a map module (地图: sapporo, one
of experimental/cnv/maps) has its places where the map has them -- a place's 块 is one of the map's land-use blocks
(LAYOUT.blocks, by its `what`), its 点 one of the map's named sites -- over the map's own ground (height tiers,
water, roads, the blocks coloured by their use), and each segment's 可玩区 (a name in the map's BORDERS) is the
playable area: what the player can see and reach in that segment. Without 地图 the sketch stays on its 100x60 grid
and 可玩区 is a rectangle on it, [x0, y0, x1, y1].

flowcheck asks problems(); flowview asks drawn() for a copy of the sketch with everything in drawing units.
Reads the map modules only.
"""
import copy
import importlib
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
GRID = (100, 60)
WIDTH = 100                     # a real map is drawn this wide; its height follows the map's shape


def load(name):
    """The map module experimental/cnv/maps/<name>.py, or None."""
    for sub in ('experimental/cnv', 'experimental/campaign'):
        p = str(ROOT / sub)
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        return importlib.import_module(f'maps.{name}')
    except ImportError:
        return None


def _frame(mod):
    return mod.BORDERS['whole']


def grid_of(mod):
    x0, y0, x1, y1 = _frame(mod)
    return WIDTH, round(WIDTH * (y1 - y0) / (x1 - x0))


def _tf(mod):
    """World (x east, y north) to drawing units (x east, y south)."""
    x0, y0, x1, y1 = _frame(mod)
    w, h = grid_of(mod)
    return lambda x, y: ((x - x0) / (x1 - x0) * w, h - (y - y0) / (y1 - y0) * h)


def _points(at):
    """A platmap Shape or an (x0, y0, x1, y1) rectangle as world points."""
    if isinstance(at, tuple) and len(at) == 4 and all(isinstance(v, (int, float)) for v in at):
        x0, y0, x1, y1 = at
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if at.kind == 'rect':
        return _points(tuple(at.at))
    if at.kind == 'circle':
        x, y, r = at.at
        return [(x + r * math.cos(a * math.pi / 16), y + r * math.sin(a * math.pi / 16)) for a in range(32)]
    return list(at.at)


def _blocks(mod):
    return {b.what: b for b in getattr(mod.LAYOUT, 'blocks', [])}


def _world_box(mod, pl):
    """A place's box in world units (x0, y0, x1, y1) from its 块 or 点, or None."""
    if pl.get('块') in _blocks(mod):
        pts = _points(_blocks(mod)[pl['块']].at)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)
    sites = _sites(pl)
    if sites and all(n in mod.SITES for n in sites):
        boxes = [(s.x - max(s.r, 120.0), s.y - max(s.r, 120.0), s.x + max(s.r, 120.0), s.y + max(s.r, 120.0))
                 for s in (mod.SITES[n] for n in sites)]
        return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes),
                max(b[3] for b in boxes))
    return None


def _sites(pl):
    """A place's 点: one site or a list of them (the box takes them all)."""
    v = pl.get('点')
    return [] if v is None else [v] if isinstance(v, str) else list(v)


def _route_point(mod, sk, n):
    """A 路线 stop in world units: a site of the map, or the middle of one of the sketch's places."""
    if n in mod.SITES:
        return mod.SITES[n].x, mod.SITES[n].y
    for pl in sk.get('地方') or []:
        if pl.get('名') == n and (box := _world_box(mod, pl)):
            return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return None


def _inside(box, border):
    """A box's middle inside a border (both x0, y0, x1, y1)."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return border[0] <= cx <= border[2] and border[1] <= cy <= border[3]


def problems(p, where):
    """What is wrong with the sketch's link to its map: 地图, 块, 点 and 可玩区 naming what exists, every segment
    with its 可玩区, every place inside the playable area of the segment it opens in."""
    sk = p.get('示意图') or {}
    segs = [s.get('名') for s in p.get('段') or []]
    zones = sk.get('可玩区') or {}
    out = []
    for k in zones:
        if k not in segs:
            out.append(f'{where} 示意图/可玩区: {k} is not a segment')
    for s in segs:
        if s not in zones:
            out.append(f'{where} 示意图/可玩区: segment {s} has no 可玩区 (what the player can see then)')
    if not sk.get('地图'):
        for k, v in zones.items():
            if not (isinstance(v, list) and len(v) == 4 and v[0] < v[2] and v[1] < v[3]):
                out.append(f'{where} 示意图/可玩区/{k}: without 地图 it is [x0, y0, x1, y1] on the grid, got {v}')
        for pl in sk.get('地方') or []:
            zone = zones.get(pl.get('开'))
            pos, size = pl.get('位'), pl.get('大')
            if isinstance(zone, list) and len(zone) == 4 and pos and size and pl.get('用途') != '远景':
                box = (pos[0] - size[0] / 2, pos[1] - size[1] / 2, pos[0] + size[0] / 2, pos[1] + size[1] / 2)
                if not _inside(box, zone):
                    out.append(f'{where} 示意图/{pl.get("名")}: opens in {pl.get("开")} but lies outside its 可玩区')
        return out
    mod = load(sk['地图'])
    if mod is None:
        return out + [f'{where} 示意图/地图: no map module experimental/cnv/maps/{sk["地图"]}.py']
    for k, v in zones.items():
        if v not in mod.BORDERS:
            out.append(f'{where} 示意图/可玩区/{k}: {v} is not a border of {sk["地图"]} ({"/".join(mod.BORDERS)})')
    blocks = _blocks(mod)
    for pl in sk.get('地方') or []:
        name = f'{where} 示意图/{pl.get("名")}'
        if '块' in pl and pl['块'] not in blocks:
            out.append(f'{name}: 块 {pl["块"]} is not a block of {sk["地图"]}')
        elif '块' in pl and blocks[pl['块']].use != pl.get('用途'):
            out.append(f'{name}: 用途 {pl.get("用途")} but the map has block {pl["块"]} as {blocks[pl["块"]].use}')
        for n in _sites(pl):
            if n not in mod.SITES:
                out.append(f'{name}: 点 {n} is not a site of {sk["地图"]}')
        if '块' not in pl and '点' not in pl and not (pl.get('位') and pl.get('大')):
            out.append(f'{name}: on a real map a place needs 块 (a block) or 点 (a site)')
        box, zone = _world_box(mod, pl), mod.BORDERS.get(zones.get(pl.get('开')))
        if box and zone and pl.get('用途') != '远景' and not _inside(box, zone):
            out.append(f'{name}: opens in {pl.get("开")} but lies outside its 可玩区 {zones.get(pl.get("开"))}')
    for n in sk.get('路线') or []:
        if _route_point(mod, sk, n) is None:
            out.append(f'{where} 示意图/路线: {n} is neither a place of the sketch nor a site of {sk["地图"]}')
    return out


def _d(pts, tf):
    return 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in (tf(*q) for q in pts)) + ' Z'


def drawn(p):
    """A copy of the sketch in drawing units for flowview: 格 [w, h]; every place's 位 and 大; 可玩区框 {segment:
    [x, y, w, h]}; with 地图 also 底图: the ground (地: tier and path), the land-use blocks (块: use and path), the
    roads (路面: path and width) and 底 (the tier where no shape is: 0 is sea)."""
    sk = copy.deepcopy(p.get('示意图') or {})
    zones = sk.get('可玩区') or {}
    mod = load(sk['地图']) if sk.get('地图') else None
    if mod is None:
        sk['格'] = list(GRID)
        sk['可玩区框'] = {k: [v[0], v[1], v[2] - v[0], v[3] - v[1]] for k, v in zones.items()
                       if isinstance(v, list) and len(v) == 4}
        return sk
    tf = _tf(mod)
    sk['格'] = list(grid_of(mod))
    for pl in sk.get('地方') or []:
        box = _world_box(mod, pl)
        if box:
            (ax, ay), (bx, by) = tf(box[0], box[3]), tf(box[2], box[1])
            pl['位'] = [round((ax + bx) / 2, 1), round((ay + by) / 2, 1)]
            pl['大'] = [round(bx - ax, 1), round(by - ay, 1)]
    frames = {}
    for k, v in zones.items():
        if v in mod.BORDERS:
            x0, y0, x1, y1 = mod.BORDERS[v]
            (ax, ay), (bx, by) = tf(x0, y1), tf(x1, y0)
            frames[k] = [round(ax, 1), round(ay, 1), round(bx - ax, 1), round(by - ay, 1)]
    sk['可玩区框'] = frames
    stops = [_route_point(mod, sk, n) for n in sk.get('路线') or []]
    sk['路线点'] = [[round(v, 1) for v in tf(*q)] for q in stops if q]
    lay = mod.LAYOUT
    w = grid_of(mod)[0] / (_frame(mod)[2] - _frame(mod)[0])
    sk['底图'] = {
        '底': getattr(lay, 'base', 0),
        '地': [{'t': s.tier, 'd': _d(_points(s), tf)} for s in lay.shapes],
        '块': [{'use': b.use, 'd': _d(_points(b.at), tf)} for b in getattr(lay, 'blocks', [])],
        '路面': [{'w': round(r.width * w, 2), 'd': 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in
                                                                 (tf(*q) for q in r.points))}
               for r in getattr(lay, 'roads', [])],
    }
    return sk
