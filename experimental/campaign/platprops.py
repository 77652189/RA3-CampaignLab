r"""Scenery for the platform maps (platmap), retail objects only (art last: nothing of our own): trees, bushes,
rocks, fences, lamps and civilian buildings, placed the way the retail campaign maps place them
(docs/story/map-language.md 4: ~2250 props and ~68 civilian buildings a map) -- woods and clumps on open ground,
rows along roads and plaza edges, rocks at cliff feet -- and kept off everything the levels use.

A map module declares its scenery from the generators here (scatter, clumps, along, cliff_feet), each giving
candidates (template, x, y, angle); place() keeps those standing on dry ground of the right slope and clear of
the map's ways and places (clearance(): every road and ramp strip, every site circle and building square, the
map's own ore, tech buildings and bridges, each widened by a margin), and thins them so no two overlap. lint()
checks a finished list against the same clearance with no margin: what a test asks of the map in a second.

Templates are named as the retail maps spell them; CATALOG gives each a kind and a footprint radius (world units:
buildings from their SageXML geometry, the rest as they sit on retail maps).
"""
import math
import random

import numpy as np

import mapterrain
import newmap
import platmap

CELL = mapterrain.CELL

# kind, footprint radius. tree / bush / rock / fence / lamp / deco: crushable or small, kept off ways only;
# house: a civilian building -- flat ground under its square, clear of every way by its radius
CATALOG = {
    # trees
    'HB_Tree03': ('tree', 14), 'HB_Tree04': ('tree', 14), 'HB_Tree05': ('tree', 14), 'HB_TREE09': ('tree', 14),
    'HB_Tree02': ('tree', 14), 'MR_Redwood01': ('tree', 16), 'MR_Tree04': ('tree', 14), 'MR_TREE01': ('tree', 14),
    'MR_Tree05': ('tree', 14), 'MR_Tree06': ('tree', 14), 'YP_Tree02': ('tree', 14), 'CC_Tree03': ('tree', 14),
    'OK_Tree01': ('tree', 14), 'OK_Tree02': ('tree', 14), 'TH_Tree01': ('tree', 12), 'TH_Tree02': ('tree', 12),
    # bushes, grass, ferns
    'CC_Bush01': ('bush', 8), 'CC_BUSH02': ('bush', 8), 'OK_Shrub01': ('bush', 8), 'OK_Shrub04': ('bush', 8),
    'YP_Fern01': ('bush', 6), 'CC_Grass01': ('bush', 5), 'CC_GRASS06': ('bush', 5), 'HB_GRASS02': ('bush', 5),
    'YU_BUSH05': ('bush', 8), 'ST_PLANT09': ('bush', 6), 'GC_Bush01': ('bush', 8),
    # rocks, logs
    'YU_LARGEROCKS02': ('rock', 26), 'YU_SMALLROCKS01': ('rock', 10), 'YU_SMALLROCKS02': ('rock', 10),
    'HA_GardenRock01': ('rock', 12), 'OK_GARDENROCK03': ('rock', 12), 'YP_LOG01': ('rock', 14),
    'YP_LOG02': ('rock', 14),
    # fences, lamps, street and festival things
    'CC_WOODFENCE01': ('fence', 16), 'CC_WOODFENCE02': ('fence', 16), 'OK_StoneFence01': ('fence', 16),
    'TH_JAPANFENCE01': ('fence', 16), 'TH_LAMPPOST04': ('lamp', 4), 'OK_LANTERN01': ('lamp', 6),
    'MJ_WOODLANTERN01': ('lamp', 6), 'TH_LAMPDECO03': ('lamp', 6), 'MJ_BANNER01': ('deco', 6),
    'MJ_BANNER02': ('deco', 6), 'GE_BENCH': ('deco', 10), 'TH_PLANTER01': ('deco', 10), 'YP_PICNIC01': ('deco', 14),
    'TH_JAPANCRATE01': ('deco', 10), 'TH_JAPANOILDRUM01': ('deco', 6),
    'OK_ARCH01': ('deco', 12),                                                    # a torii
    # civilian buildings, ones retail maps place (SageXML geometry: the box's half sides -> its half diagonal)
    'YP_Cabin': ('house', 44), 'YP_RSTATION': ('house', 50), 'YP_WatchTower': ('house', 35),
    'CCHOUSE02D': ('house', 77), 'HV_Shop01': ('house', 43), 'HB_House03': ('house', 57), 'HB_HOUSE04': ('house', 36),
    'TH_PHpagoda_01': ('house', 56), 'TH_PHpagoda_02': ('house', 42), 'TH_PHpagoda_04': ('house', 54),
    'MJ_Structure_02': ('house', 37), 'MJ_Structure_04': ('house', 60), 'MJ_GUARDHOUSE01': ('house', 20),
    'HA_Building16_02': ('house', 41), 'HA_Building16_03': ('house', 41), 'TH_SushiBar_01': ('house', 37),
    'TH_Fish_Market02': ('house', 25), 'TH_Fish_Market03': ('house', 39), 'TH_FISH_MARKET04': ('house', 34),
    'TH_harbor_crane01': ('house', 42), 'OK_Pagoda01': ('house', 64),
}
# what units knock over or pass through (SageXML: BaseTree, BaseTopple, BaseOptimizedProp -- NO_COLLIDE --,
# BaseSimulatedProp): these may stand in the outer part of a site's circle (SOFT of it), the rest -- big rocks
# (BaseRockBig), garden rocks, buildings -- keep off the whole circle
SOFT = 0.5
CRUSHABLE = {t for t, (k, _) in CATALOG.items() if k != 'house'} - {'YU_LARGEROCKS02', 'TH_LAMPDECO03',
                                                                     'HA_GardenRock01', 'OK_GARDENROCK03'}
# KindOf STRUCTURE (SageXML: buildings, BaseTopple's fences / lamps / banners / benches, BaseRockBig): counted by
# a kind-in-area count, which counts every player's (parts.counted), so a map whose checks count structures that
# way (the island: CampKinds) places none of these
STRUCTURE = {t for t, (k, _) in CATALOG.items() if k == 'house'} | {
    'CC_WOODFENCE01', 'CC_WOODFENCE02', 'TH_LAMPPOST04', 'MJ_WOODLANTERN01', 'MJ_BANNER01', 'MJ_BANNER02', 'GE_BENCH',
    'TH_PLANTER01', 'TH_JAPANOILDRUM01', 'YU_LARGEROCKS02', 'TH_LAMPDECO03'}
SLOPE = {'tree': 6.0, 'bush': 6.0, 'rock': 99.0, 'fence': 3.0, 'lamp': 3.0, 'deco': 3.0, 'house': 0.0}
# how much further off a way or place than lint() requires each kind keeps: woods and rocks well off (units walk
# round them), the things that line a street (lamps, fences, benches) close by, buildings a little off
MARGIN = {'tree': 60.0, 'bush': 40.0, 'rock': 60.0, 'fence': 8.0, 'lamp': 8.0, 'deco': 8.0, 'house': 30.0}


def kind(template):
    return CATALOG[template][0]


def radius(template):
    return CATALOG[template][1]


# ---------------------------------------------------------------- what scenery keeps off
WHOLE = 1000.0                  # a site this wide or wider is a whole-map area ('island'), not a place to keep clear


def clearance(layout, sites=None, objects=(), avoid=()):
    """The map's ways and places as circles (x, y, r) and strips (p, q, width): every ramp and road, every site
    (its circle, or for a building site the circle round its square; not the whole-map ones), the map's own objects
    (ore, tech, bridges: a bridge's deck as a strip from its start to its end, its two ends a circle each), and the
    map's own `avoid` places: circles (x, y, r) -- a base's building ground -- and strips (p, q, width) -- a
    raised plaza, its middle line and its width)."""
    strips = [a for a in avoid if isinstance(a[0], (tuple, list))]
    circles = [a for a in avoid if not isinstance(a[0], (tuple, list))]
    for r in (layout.ramps if layout else ()):
        dx, dy = r.high[0] - r.low[0], r.high[1] - r.low[1]
        ln = math.hypot(dx, dy) or 1.0
        ux, uy = dx / ln, dy / ln
        strips.append(((r.low[0] - ux * 60, r.low[1] - uy * 60), (r.high[0] + ux * 60, r.high[1] + uy * 60),
                       r.width + 40))
    for rd in (layout.roads if layout else ()):
        strips += [(p, q, rd.width + 20) for p, q in zip(rd.points, rd.points[1:])]
    for s in (sites or {}).values():
        if s.r >= WHOLE:
            continue
        build = getattr(s, 'build', 0) * 0.75
        circles.append((s.x, s.y, max(s.r, build, 40.0), max(s.r * SOFT, build, 40.0)))
    objs = list(objects)
    k = 0
    while k < len(objs):
        o = objs[k]
        if getattr(o, 'flags', None) == platmap.BRIDGE_START and k + 1 < len(objs):
            q = objs[k + 1]
            strips.append(((o.x, o.y), (q.x, q.y), 160.0))
            circles += [(o.x, o.y, 140.0), (q.x, q.y, 140.0)]
            k += 2
            continue
        circles.append((o.x, o.y, 120.0 if 'Ore' in o.template else 160.0))
        k += 1
    return circles, strips


def _seg_dist(x, y, p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    t = max(0.0, min(1.0, ((x - p[0]) * dx + (y - p[1]) * dy) / max(dx * dx + dy * dy, 1e-9)))
    return math.hypot(x - p[0] - t * dx, y - p[1] - t * dy)


def blocked(x, y, r, zones, margin=0.0, soft=False):
    """What a prop of radius r at (x, y) stands in (a description), or '' if it is clear. soft: a thing units knock
    over or walk through (CRUSHABLE kinds) may stand in the outer part of a site's circle."""
    circles, strips = zones
    for c in circles:
        cx, cy, cr = c[0], c[1], (c[3] if soft and len(c) > 3 else c[2])
        if math.hypot(x - cx, y - cy) < cr + r + margin:
            return f'the place at ({cx:g}, {cy:g})'
    for p, q, w in strips:
        if _seg_dist(x, y, p, q) < w / 2 + r + margin:
            return f'the way ({p[0]:g}, {p[1]:g})-({q[0]:g}, {q[1]:g})'
    return ''


# ---------------------------------------------------------------- candidates
def _pick(rnd, templates):
    """templates: a name, a list (equal odds) or {name: weight}."""
    if isinstance(templates, str):
        return templates
    if isinstance(templates, dict):
        names, weights = zip(*templates.items())
        return rnd.choices(names, weights)[0]
    return rnd.choice(list(templates))


def _inside(shape, x, y):
    if shape is None:
        return True
    kind_, at = shape
    if kind_ == 'circle':
        return math.hypot(x - at[0], y - at[1]) <= at[2]
    if kind_ == 'rect':
        return at[0] <= x <= at[2] and at[1] <= y <= at[3]
    inside, pts = False, at                                      # 'poly': even-odd rule
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def area(kind_, at):
    """A region for the generators: ('circle', (x, y, r)), ('rect', (x0, y0, x1, y1)), ('poly', [points])."""
    return (kind_, tuple(at) if kind_ != 'poly' else list(at))


def scatter(region, templates, spacing, seed, density=1.0, patches=0.0):
    """Woods and open scatter: a jittered grid `spacing` apart over the region, each point kept with odds
    `density`. patches (0..1): that share of the region left as clearings -- the woods grow in stands, thick
    inside, with open ground between (smooth noise ~400 across), as retail woods do."""
    rnd = random.Random(seed)
    stand = newmap.value_noise(seed + 101, 400.0)
    k, at = region
    if k == 'circle':
        x0, y0, x1, y1 = at[0] - at[2], at[1] - at[2], at[0] + at[2], at[1] + at[2]
    elif k == 'rect':
        x0, y0, x1, y1 = at
    else:
        xs, ys = [p[0] for p in at], [p[1] for p in at]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    out = []
    y = y0
    while y <= y1:
        x = x0
        while x <= x1:
            px, py = x + rnd.uniform(-0.45, 0.45) * spacing, y + rnd.uniform(-0.45, 0.45) * spacing
            odds = density if not patches else density * min(1.0, max(0.0, (stand(px, py) - patches) / 0.12))
            if rnd.random() < odds and _inside(region, px, py):
                out.append((_pick(rnd, templates), px, py, rnd.uniform(-math.pi, math.pi)))
            x += spacing
        y += spacing
    return out


def clumps(region, n, spread, count, templates, seed):
    """n clumps (thickets, rock piles) in the region, each `count` things within `spread` of its middle."""
    rnd = random.Random(seed)
    centres = scatter(region, ['x'], max(1.0, math.sqrt(_size(region) / max(n, 1))), seed + 7)
    rnd.shuffle(centres)
    out = []
    for _, cx, cy, _ in centres[:n]:
        for _ in range(count):
            a, d = rnd.uniform(0, 2 * math.pi), spread * math.sqrt(rnd.random())
            out.append((_pick(rnd, templates), cx + d * math.cos(a), cy + d * math.sin(a),
                        rnd.uniform(-math.pi, math.pi)))
    return out


def _size(region):
    k, at = region
    if k == 'circle':
        return math.pi * at[2] ** 2
    if k == 'rect':
        return (at[2] - at[0]) * (at[3] - at[1])
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(at, at[1:] + at[:1]))) / 2


def along(points, templates, every, offset, seed, sides=(1, -1), face=False, jitter=0.15):
    """Rows along a polyline (an avenue's trees, a street's lamps, a fence round a field): one every `every`,
    `offset` to each side (sides 1 left, -1 right). face: the thing turned to the line (a house to its street,
    a fence along it); otherwise turned at random."""
    rnd = random.Random(seed)
    out = []
    for p, q in zip(points, points[1:]):
        dx, dy = q[0] - p[0], q[1] - p[1]
        ln = math.hypot(dx, dy)
        if ln < 1:
            continue
        ux, uy = dx / ln, dy / ln
        a = math.atan2(dy, dx)
        s = every / 2
        while s < ln:
            for side in sides:
                t = s + rnd.uniform(-jitter, jitter) * every
                x, y = p[0] + ux * t - uy * offset * side, p[1] + uy * t + ux * offset * side
                ang = (a + (math.pi / 2 if side > 0 else -math.pi / 2)) if face else rnd.uniform(-math.pi, math.pi)
                out.append((_pick(rnd, templates), x, y, ang))
            s += every
    return out


def _grow(mask, n):
    out = mask.copy()
    for dj in range(-n, n + 1):
        for di in range(-n, n + 1):
            out |= np.roll(np.roll(mask, dj, 0), di, 1)
    return out


def cliff_feet(ground, templates, every, seed, region=None):
    """Rocks and scrub where a cliff meets the ground below it, one about every `every` along the foot (retail
    maps dress most cliff lines so)."""
    e = ground.e
    steep = ground.slope > platmap.STEEP
    lower = e < np.maximum.reduce([np.roll(e, 3, 0), np.roll(e, -3, 0), np.roll(e, 3, 1), np.roll(e, -3, 1)]) - 20
    return _along_cells(ground, _grow(steep, 2) & ~steep & lower & (e > newmap.WATERLINE + 10), templates, every,
                        seed, region)


def shore(ground, templates, every, seed, near=(3, 9), region=None):
    """Reeds, rocks and trees along the water's edge: dry ground `near` cells (from, to) off the water."""
    wet = ground.e <= newmap.WATERLINE + 10
    band = _grow(wet, near[1]) & ~_grow(wet, near[0])
    return _along_cells(ground, band & (ground.slope <= platmap.STEEP), templates, every, seed, region)


def _along_cells(ground, cells, templates, every, seed, region):
    b = ground.b
    jj, ii = np.nonzero(cells)
    rnd = random.Random(seed)
    order = list(range(len(jj)))
    rnd.shuffle(order)
    out, taken = [], {}
    cell = max(1, int(every / CELL))
    for k in order:
        i, j = int(ii[k]), int(jj[k])
        key = (i // cell, j // cell)
        if key in taken:
            continue
        x, y = (i - b) * CELL, (j - b) * CELL
        if region is not None and not _inside(region, x, y):
            continue
        taken[key] = 1
        out.append((_pick(rnd, templates), x, y, rnd.uniform(-math.pi, math.pi)))
    return out


# ---------------------------------------------------------------- keeping the good ones
class Ground:
    """A map's heights and slopes (elevation / 16, the container's cells), asked by world point: the layout's, or
    a height field given outright (a map with no layout: the noise island)."""

    def __init__(self, layout=None, dims=platmap.CONTAINER, e=None):
        self.w, self.h, self.b = dims
        self.e = e if e is not None else platmap.heights(layout, self.w, self.h, self.b)[0]
        self.slope = platmap.slope_of(self.e)

    def cell(self, x, y):
        i, j = int(round(x / CELL)) + self.b, int(round(y / CELL)) + self.b
        return (i, j) if 0 <= i < self.w and 0 <= j < self.h else None

    def dry(self, x, y):
        c = self.cell(x, y)
        return c is not None and self.e[c[1], c[0]] > newmap.WATERLINE + 10

    def steep(self, x, y, r):
        """The steepest cell under a footprint of radius r."""
        c = self.cell(x, y)
        n = max(0, int(round(r / CELL)))
        win = self.slope[max(0, c[1] - n):c[1] + n + 1, max(0, c[0] - n):c[0] + n + 1]
        return float(win.max())

    def relief(self, x, y, r):
        return platmap.relief(self.e, x, y, 2 * r, self.b)


def problem(ground, zones, template, x, y, margin=0.0):
    """Why this prop may not stand here ('' if it may)."""
    if template not in CATALOG:
        return f'{template}: not in the scenery catalog'
    k, r = CATALOG[template]
    if ground.cell(x, y) is None:
        return f'{template} at ({x:.0f}, {y:.0f}): off the map'
    if not ground.dry(x, y):
        return f'{template} at ({x:.0f}, {y:.0f}): in the water'
    if k == 'house' and ground.relief(x, y, r) > platmap.FLAT:
        return f'{template} at ({x:.0f}, {y:.0f}): not on flat ground'
    if k != 'house' and ground.steep(x, y, min(r, 10)) > SLOPE[k]:
        return f'{template} at ({x:.0f}, {y:.0f}): on a slope'
    hit = blocked(x, y, r if k == 'house' else min(r, 12), zones, margin, soft=template in CRUSHABLE)
    return f'{template} at ({x:.0f}, {y:.0f}): on {hit}' if hit else ''


def place(candidates, layout, sites=None, objects=(), keep=(), avoid=(), ground=None, must=False):
    """The candidates that may stand where they are (problem() with MARGIN to spare, off the `avoid` circles too),
    thinned so no two footprints overlap; `keep` (already placed) counts for the thinning. Returns
    [(template, x, y, angle)]. must: every candidate is a landmark placed by hand -- one that may not stand where
    it is raises (ValueError, every one and why), not dropped unseen as a generator's are."""
    ground = ground or Ground(layout)
    zones = clearance(layout, sites, objects, avoid)
    grid, out, refused = {}, [], []
    widest = [0.0]

    def free(x, y, r):
        n = int(math.ceil((r + widest[0]) * 0.9 / 100))            # as far as two footprints can reach
        gx, gy = int(x // 100), int(y // 100)
        for i in range(gx - n, gx + n + 1):
            for j in range(gy - n, gy + n + 1):
                for ox, oy, orr in grid.get((i, j), ()):
                    if math.hypot(x - ox, y - oy) < (r + orr) * 0.9:
                        return False
        return True

    def take(x, y, r):
        widest[0] = max(widest[0], r)
        grid.setdefault((int(x // 100), int(y // 100)), []).append((x, y, r))
    for t, x, y, _ in keep:
        take(x, y, radius(t))
    for t, x, y, a in candidates:
        r = radius(t)
        why = problem(ground, zones, t, x, y, MARGIN[kind(t)]) or (
            '' if free(x, y, r) else f'{t} at ({x:.0f}, {y:.0f}): on another prop')
        if why:
            refused.append(why)
            continue
        take(x, y, r)
        out.append((t, x, y, a))
    if must and refused:
        raise ValueError('landmarks that may not stand where they are placed: ' + '; '.join(refused))
    return out


def lint(layout, sites=None, objects=(), scenery=(), dims=platmap.CONTAINER, ground=None):
    """Every prop of the map's scenery known, on dry ground, buildings flat, nothing on a way or a place."""
    ground = ground or Ground(layout, dims)
    zones = clearance(layout, sites, objects)
    out = []
    for o in scenery:
        p = problem(ground, zones, o.template, o.x, o.y)
        if p:
            out.append('scenery ' + p)
    return out[:12] + ([f'... {len(out) - 12} more'] if len(out) > 12 else [])
