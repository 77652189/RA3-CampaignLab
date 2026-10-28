r"""Platform terrain, the retail campaign way (docs/story/map-language.md): flat tiers, narrow cliffs between them,
a few ramps, water cut in where the ground army must not cross -- instead of the noise island's rolling slopes.

A Layout is declared by a map module (experimental/cnv/maps): shapes painted in order (each fills a polygon, rectangle
or circle with one tier's height), then cliffs (the stepped field smoothed over a few cells), then ramps (a straight
strip from a low point to a high point, its height interpolated), then roads (a ground texture, the heights stay).
apply(m, layout) writes heights, ground textures, passability (steep dry ground impassable, as retail) and the radar
pictures into the container map. The map's objects (ore, tech buildings, bridges) are the map module's to publish.

Heights are elevation / 16 like newmap (world height = that * 0.7): TIER 1 / 2 / 3 stand at world ~238 / 318 / 399,
retail's three usual levels (220 / 300 / 380 above sea floor, water at 200) a little higher; TIER 0 is sea floor.
A bridge (bridge()) is two objects, as retail: its start flagged 16, its end flagged 32, next to each other in the
object list; the game builds the deck and its segments between them (BridgeBuilder: end caps 75, centre pieces 150).
"""
import dataclasses
import math

import numpy as np
from PIL import Image, ImageDraw

import mapterrain
import newmap

CELL = mapterrain.CELL
TIER = {0: 220.0, 1: 340.0, 2: 455.0, 3: 570.0}
STEEP = 9.0                     # rise per cell (elevation / 16) above which dry ground is impassable (newmap)
RAMP_MAX = 6.5                  # a ramp's rise per cell: well under STEEP, so its middle stays passable
BRIDGE_START, BRIDGE_END = 16, 32


@dataclasses.dataclass
class Shape:
    """Ground of one tier: kind 'poly' (points), 'rect' (x0, y0, x1, y1) or 'circle' (x, y, r), world units."""
    kind: str
    at: tuple
    tier: int
    what: str = ''


@dataclasses.dataclass
class Ramp:
    """A straight ramp from `low` (x, y) to `high` (x, y), `width` across; both ends on flat ground of their tiers."""
    low: tuple
    high: tuple
    width: float = 160.0
    what: str = ''


@dataclasses.dataclass
class Road:
    """A ground texture along a polyline (world points), `width` across; heights are left alone."""
    points: tuple
    width: float = 120.0
    texture: str = 'Pavement_Heidel02'


USES = ('前线', '支线', '通道', '后方', '远景')
EMPTY_MOST = 0.25               # of the ground the player can walk to, at most this much in no block (P24; retail 17 %)
BACKDROP_MOST = 0.01            # km2 of a 远景 block the player may still walk to (a cliff foot's sliver)


@dataclasses.dataclass
class Block:
    """A part of the playable area and what it is for (docs/design/principles.md P24): use 前线 (the enemy or the
    main objective), 支线 (a bonus, a tech building, a strongpoint), 通道 (the way between), 后方 (the base), 远景
    (backdrop: nobody can walk there). at: a Shape, or a rectangle (x0, y0, x1, y1)."""
    at: object
    use: str
    what: str = ''


@dataclasses.dataclass
class Gap:
    """A way through -- a gate, a street's mouth, a wall's opening -- and how wide it is meant to be: lint measures
    the walkable width across (x, y) (cliffs, water and the map's wall pieces close it), e.g. a plaza's gate 120 wide
    so an ice wall 200 long shuts it."""
    x: float
    y: float
    width: float
    what: str = ''


@dataclasses.dataclass
class Layout:
    shapes: list
    ramps: list = dataclasses.field(default_factory=list)
    roads: list = dataclasses.field(default_factory=list)
    base: int = 0                       # the tier everywhere no shape covers (0: sea)
    cliff: int = 2                      # smoothing passes (3 x 3 box): a tier step becomes a cliff ~2 * cliff cells wide
    blocks: list = dataclasses.field(default_factory=list)     # [Block]: lint holds the map to them (P24)
    gaps: list = dataclasses.field(default_factory=list)       # [Gap]: lint measures each


def rect(x0, y0, x1, y1, tier, what=''):
    return Shape('rect', (x0, y0, x1, y1), tier, what)


def poly(points, tier, what=''):
    return Shape('poly', tuple(points), tier, what)


def circle(x, y, r, tier, what=''):
    return Shape('circle', (x, y, r), tier, what)


def wobble(points, amp, seed, step=90.0, keep=(), closed=True):
    """A polygon's (or a polyline's) edges made irregular, the way retail shores and cliff lines run: each edge cut
    every `step` and its inner points pushed across it by smooth noise of the place (two octaves: about `amp`,
    twice that at most),
    so two shapes sharing an edge with one seed share its bends. The given points stay; so does everything within
    a `keep` circle (x, y, r) -- a bridge's end, a ramp's foot -- easing back to straight over r."""
    big, small = newmap.value_noise(seed, 420.0), newmap.value_noise(seed + 1, 110.0)
    pts = list(points)
    out = []
    for k in range(len(pts) if closed else len(pts) - 1):
        (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % len(pts)]
        length = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(length // step))
        nx, ny = (y1 - y0) / max(length, 1e-9), -(x1 - x0) / max(length, 1e-9)
        out.append((x0, y0))
        for s in range(1, n):
            t = s / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            d = amp * (1.2 * (2 * big(x, y) - 1) + 0.8 * (2 * small(x, y) - 1)) * min(1.0, 8 * t * (1 - t))
            for kx, ky, kr in keep:
                d *= min(1.0, max(0.0, math.hypot(x - kx, y - ky) / kr - 1.0))
            out.append((x + nx * d, y + ny * d))
    if not closed:
        out.append(pts[-1])
    return out


def _mask(shape, w, h, b):
    img = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(img)
    c = lambda x, y: (x / CELL + b, y / CELL + b)          # noqa: E731  -- rows are j (north up the array)
    if shape.kind == 'rect':
        x0, y0, x1, y1 = shape.at
        d.rectangle([c(x0, y0), c(x1, y1)], fill=1)
    elif shape.kind == 'poly':
        d.polygon([c(x, y) for x, y in shape.at], fill=1)
    elif shape.kind == 'circle':
        x, y, r = shape.at
        (i, j), rr = c(x, y), r / CELL
        d.ellipse([i - rr, j - rr, i + rr, j + rr], fill=1)
    else:
        raise ValueError(shape.kind)
    return np.asarray(img, bool)


def _strip(p, q, width, w, h, b):
    """Cells within width / 2 of segment p-q: (mask, t along it 0..1)."""
    jj, ii = np.mgrid[0:h, 0:w]
    x, y = (ii - b) * CELL, (jj - b) * CELL
    dx, dy = q[0] - p[0], q[1] - p[1]
    length2 = dx * dx + dy * dy
    t = ((x - p[0]) * dx + (y - p[1]) * dy) / length2
    px, py = p[0] + t * dx, p[1] + t * dy
    near = np.hypot(x - px, y - py) <= width / 2
    return near & (t >= 0) & (t <= 1), np.clip(t, 0, 1)


def heights(layout, w, h, b):
    """The height field (elevation / 16), rows j, columns i, and the problems found (ramps too steep ...)."""
    e = np.full((h, w), TIER[layout.base], np.float32)
    for s in layout.shapes:
        e[_mask(s, w, h, b)] = TIER[s.tier]
    for _ in range(layout.cliff):                           # tier steps -> narrow cliffs
        p = np.pad(e, 1, mode='edge')
        e = sum(p[1 + dj:h + 1 + dj, 1 + di:w + 1 + di] for dj in (-1, 0, 1) for di in (-1, 0, 1)) / 9.0
    problems = []
    for r in layout.ramps:
        at = lambda x, y: e[int(round(y / CELL)) + b, int(round(x / CELL)) + b]       # noqa: E731
        lo, hi = float(at(*r.low)), float(at(*r.high))
        cells = math.hypot(r.high[0] - r.low[0], r.high[1] - r.low[1]) / CELL
        rise = abs(hi - lo) / max(cells, 1)
        if rise > RAMP_MAX:
            problems.append(f'ramp {r.what or r.low}: rises {rise:.1f} per cell (most {RAMP_MAX}): make it longer')
        if abs(hi - lo) < 30:
            problems.append(f'ramp {r.what or r.low}: both ends on one level ({lo:.0f} / {hi:.0f})')
        near, t = _strip(r.low, r.high, r.width, w, h, b)
        e[near] = (lo + (hi - lo) * t)[near]
    return e, problems


def slope_of(e):
    p = np.pad(e, 1, mode='edge')
    c = p[1:-1, 1:-1]
    return np.maximum.reduce([abs(p[1:-1, 2:] - c), abs(p[1:-1, :-2] - c), abs(p[2:, 1:-1] - c), abs(p[:-2, 1:-1] - c)])


def apply(m, layout, seed=11):
    """Write the layout into the container map: heights, textures, passability, water area, radar pictures.
    Returns (previews {'art', 'small'}, problems)."""
    hm = mapterrain.HeightMap(m)
    w, h, b = hm.width, hm.height, hm.border
    e, problems = heights(layout, w, h, b)
    if problems:
        raise ValueError('layout: ' + '; '.join(problems))
    hm.elev = [max(0, min(65535, int(round(v * mapterrain.SCALE)))) for v in e.ravel()]
    hm.store()
    tiles = mapterrain.Tiles(m, w)
    for f in range(8):
        tiles.fill_field(f, f == 4)                         # field 4 is set nearly everywhere on retail maps
    slope = slope_of(e)
    patch = newmap.value_noise(seed, 150.0)
    road = np.zeros((h, w), object)
    for r in layout.roads:
        for p, q in zip(r.points, r.points[1:]):
            near, _ = _strip(p, q, r.width, w, h, b)
            road[near] = r.texture
    grid = {}
    for j in range(h):
        for i in range(w):
            v, s = float(e[j, i]), float(slope[j, i])
            grid[(i, j)] = road[j, i] if road[j, i] and s <= STEEP and v > newmap.WATERLINE + 10 else \
                newmap.texture_for(v, s, (i - b) * CELL, (j - b) * CELL, patch)
            if s > STEEP and v > newmap.WATERLINE:
                tiles.set_bit(0, i, j, True)
    newmap.paint_grid(tiles, grid, newmap.RANK + sorted({r.texture for r in layout.roads}))
    tiles.store()
    size = (w - 2 * b) * CELL
    newmap.set_water(m, -300.0, -300.0, size + 300.0, size + 300.0)
    return {'art': newmap.preview_tga(hm, tiles, 512, 24), 'small': newmap.preview_tga(hm, tiles, 128, 32)}, problems


CONTAINER = (560, 560, 30)      # Heidelberg's height map (the container every generated map is written into)
FLAT = 8.0                      # elevation / 16 a building's square may rise across and still be built on (newmap
                                # flags 9 per cell impassable; bench 2026-10-23: nothing built mid-ramp)


def relief(e, x, y, side, b=CONTAINER[2]):
    """How much the ground rises across the square of `side` around (x, y) (elevation / 16)."""
    h = max(1, int(round(side / CELL / 2)))
    i, j = int(round(x / CELL)) + b, int(round(y / CELL)) + b
    win = e[max(0, j - h):j + h + 1, max(0, i - h):i + h + 1]
    return float(win.max() - win.min())


def lint(layout, sites=None, objects=(), scenery=(), dims=CONTAINER):
    """A map's design checked without the game (docs/story/map-language.md): ramps gentle enough, sites meant for
    building (Site.build) flat, the map's own structures (ore, tech) on flat dry ground, every bridge from bank to bank
    of one level with water under its middle, the scenery (platprops) clear of all that. Returns the problems (empty:
    fine)."""
    w, h, b = dims
    e, out = heights(layout, w, h, b)
    dry = lambda x, y: e[int(round(y / CELL)) + b, int(round(x / CELL)) + b] > newmap.WATERLINE + 10   # noqa: E731
    for name, s in (sites or {}).items():
        if getattr(s, 'build', 0) and relief(e, s.x, s.y, s.build, b) > FLAT:
            out.append(f'site {name}: the {s.build:g} square to build on rises {relief(e, s.x, s.y, s.build, b):.0f}'
                       f' (most {FLAT:g})')
    objs = list(objects)
    k = 0
    while k < len(objs):
        o = objs[k]
        if getattr(o, 'flags', None) == BRIDGE_START:
            q = objs[k + 1] if k + 1 < len(objs) else None
            if q is None or q.flags != BRIDGE_END:
                out.append(f'bridge {o.template} at ({o.x:g}, {o.y:g}): its end (flags {BRIDGE_END}) must follow it')
            else:
                ends = [e[int(round(p.y / CELL)) + b, int(round(p.x / CELL)) + b] for p in (o, q)]
                if not all(dry(p.x, p.y) for p in (o, q)) or abs(ends[0] - ends[1]) > FLAT:
                    out.append(f'bridge at ({o.x:g}, {o.y:g}): its ends must stand on dry ground of one level '
                               f'({ends[0]:.0f} / {ends[1]:.0f})')
                if dry((o.x + q.x) / 2, (o.y + q.y) / 2):
                    out.append(f'bridge at ({o.x:g}, {o.y:g}): dry ground under its middle -- a bridge over nothing')
            k += 2
            continue
        # a wall piece only on dry ground: it runs up to a cliff's foot to close a courtyard (retail walls follow
        # the ground), where the rest must stand flat
        if not dry(o.x, o.y) or (o.template not in WALLS and relief(e, o.x, o.y, 60.0, b) > FLAT):
            out.append(f'{o.template} at ({o.x:g}, {o.y:g}): not on flat dry ground')
        k += 1
    walk = walkable(layout, objs, dims, e)
    out += block_lint(layout, sites, walk, dims) + gap_lint(layout, walk, dims)
    if scenery:
        import platprops
        out += platprops.lint(layout, sites, objects, scenery, dims)
    return out


# ---- what the player can walk to, the blocks' use, the gaps' width
WALLS = {'MJ_PalaceWall01': (60.0, 20.0)}       # wall pieces that bar the way (bench 2026-10-27 fence bar: the palace
                                                # wall held infantry, retail's fences did not): length, thickness
BRIDGE_DECK = 120.0                             # a bridge's walkable width laid over the water


def _cells(dims):
    w, h, b = dims
    jj, ii = np.mgrid[0:h, 0:w]
    return (ii - b) * CELL, (jj - b) * CELL


def walkable(layout, objects=(), dims=CONTAINER, e=None):
    """Cells a ground unit can stand on: dry, not steeper than STEEP (the passability apply() writes), bridges laid
    over the water from start to end, the map's wall pieces (WALLS) taken out."""
    w, h, b = dims
    if e is None:
        e, _ = heights(layout, w, h, b)
    ok = (e > newmap.WATERLINE + 10) & (slope_of(e) <= STEEP)
    objs = list(objects)
    for o, q in zip(objs, objs[1:]):
        if getattr(o, 'flags', None) == BRIDGE_START and getattr(q, 'flags', None) == BRIDGE_END:
            near, _ = _strip((o.x, o.y), (q.x, q.y), BRIDGE_DECK, w, h, b)
            ok |= near
    x, y = _cells(dims)
    for o in objs:
        if o.template in WALLS:
            length, thick = WALLS[o.template]
            a = o.angle or 0.0
            u = (x - o.x) * math.cos(a) + (y - o.y) * math.sin(a)
            v = -(x - o.x) * math.sin(a) + (y - o.y) * math.cos(a)
            ok &= ~((abs(u) <= length / 2) & (abs(v) <= thick / 2))
    return ok


def reach(walk, x, y, dims=CONTAINER):
    """The walkable cells joined by ground to (x, y): what a player starting there can get to."""
    from scipy import ndimage
    w, h, b = dims
    comp, _ = ndimage.label(walk)
    i, j = int(round(x / CELL)) + b, int(round(y / CELL)) + b
    k = comp[j, i]
    if not k:                                   # the start on a cliff's edge: the nearest walkable cell's ground
        d = ndimage.distance_transform_edt(~walk, return_indices=True)[1]
        k = comp[d[0][j, i], d[1][j, i]]
    return comp == k


def block_mask(block, dims=CONTAINER):
    w, h, b = dims
    at = block.at if isinstance(block.at, Shape) else Shape('rect', tuple(block.at), 0)
    return _mask(at, w, h, b)


def block_use(layout, sites, walk, dims=CONTAINER):
    """How the ground the player can walk to (from the start site) is used: km2 walkable, the share in each use and
    in no block (空地), and each 远景 block's walkable km2. None when the layout declares no blocks."""
    if not layout.blocks or 'start' not in (sites or {}):
        return None
    s = sites['start']
    got = reach(walk, s.x, s.y, dims)
    n = max(1, int(got.sum()))
    km2 = CELL * CELL / 1e6
    covered = np.zeros_like(got)
    share, backdrop = {}, {}
    for bl in layout.blocks:
        mk = block_mask(bl, dims)
        if bl.use == '远景':
            backdrop[bl.what or str(bl.at)] = round(float((got & mk).sum()) * km2, 3)
            continue
        new = got & mk & ~covered
        share[bl.use] = share.get(bl.use, 0.0) + float(new.sum()) / n
        covered |= mk
    share['空地'] = float((got & ~covered).sum()) / n
    return dict(walkable=round(n * km2, 2), share={k: round(v, 2) for k, v in share.items()}, backdrop=backdrop)


def block_lint(layout, sites, walk, dims=CONTAINER):
    """P24: every block's use one of USES; of the ground the player can walk to, at most EMPTY_MOST in no block; no
    远景 block one can walk to."""
    out = [f'block {bl.what or bl.at}: use {bl.use!r} is none of {"/".join(USES)}' for bl in layout.blocks
           if bl.use not in USES]
    use = block_use(layout, sites, walk, dims)
    if use is None:
        return out
    if use['share']['空地'] > EMPTY_MOST:
        out.append(f'blocks: {use["share"]["空地"]:.0%} of the ground the player can walk to is in no block '
                   f'(empty; most {EMPTY_MOST:.0%}): give it a use, or make it backdrop (water, cliff, the border)')
    out += [f'block {k} (远景): {v:g} km2 of it can be walked to (most {BACKDROP_MOST:g})'
            for k, v in use['backdrop'].items() if v > BACKDROP_MOST]
    return out


GAP_SLACK = 2 * CELL                            # a gap measured within this of what it is meant to be


def gap_width(walk, x, y, dims=CONTAINER):
    """The walkable width across (x, y): the shortest walkable run through it, over directions every 15 degrees
    (0 when (x, y) itself cannot be walked on)."""
    w, h, b = dims
    on = lambda px, py: (0 <= int(round(py / CELL)) + b < h and 0 <= int(round(px / CELL)) + b < w   # noqa: E731
                         and walk[int(round(py / CELL)) + b, int(round(px / CELL)) + b])
    if not on(x, y):
        return 0.0
    best = math.inf
    for k in range(12):
        a = math.pi * k / 12
        dx, dy = math.cos(a), math.sin(a)
        run = 0.0
        for sgn in (1, -1):
            t = 0.0
            while t < 2000 and on(x + sgn * dx * (t + CELL / 2), y + sgn * dy * (t + CELL / 2)):
                t += CELL / 2
            run += t
        best = min(best, run)
    return best


def gap_lint(layout, walk, dims=CONTAINER):
    out = []
    for g in layout.gaps:
        got = gap_width(walk, g.x, g.y, dims)
        if abs(got - g.width) > GAP_SLACK:
            out.append(f'gap {g.what or (g.x, g.y)}: {got:.0f} wide where it is meant to be {g.width:g}'
                       + (' (shut: no walkable ground there)' if not got else ''))
    return out


# ---- strongpoints and walls: the map's own objects, (template, x, y, angle) for the map module to place
GARRISON = 'MJ_Structure_04'    # a retail Japanese house a squad can garrison (BaseCivilianStructureSmall)
WALL_PIECE = 'MJ_PalaceWall01'


def strongpoint(x, y, angle=0.0, template=GARRISON):
    """A building a squad can garrison at (x, y): the map places it as one of its OBJECTS (named, published in its
    STRONGPOINTS so a mission refers to it by name)."""
    return (template, x, y, angle)


def wall_line(points, gaps=(), template=WALL_PIECE):
    """Wall pieces along a polyline (world points), corner to corner, an opening left at each gap ((x, y, width):
    the point projected onto the line, the opening that wide between the pieces' ends). Each run between openings is
    filled end to end, the pieces 0.9 of their length apart (they overlap: bench fence bar, the ring that held)."""
    length = WALLS[template][0]
    segs, s0 = [], 0.0
    for p, q in zip(points, points[1:]):
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        segs.append((p, q, s0, d))
        s0 += d
    total = s0

    def along(x, y):                            # arc length of the nearest point on the line
        best = (math.inf, 0.0)
        for p, q, s, d in segs:
            t = max(0.0, min(1.0, ((x - p[0]) * (q[0] - p[0]) + (y - p[1]) * (q[1] - p[1])) / max(d * d, 1e-9)))
            px, py = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
            best = min(best, (math.hypot(x - px, y - py), s + t * d))
        return best[1]

    holes = sorted((along(x, y) - wd / 2, along(x, y) + wd / 2) for x, y, wd in gaps)
    runs, at = [], 0.0
    for a, b_ in holes:
        if a > at:
            runs.append((at, a))
        at = max(at, b_)
    if at < total:
        runs.append((at, total))
    out = []
    for a, b_ in runs:
        if b_ - a < length / 2:
            continue                            # too short a stub for a piece
        n = max(1, math.ceil((b_ - a - length) / (0.9 * length)) + 1)
        for k in range(n):
            s = a + length / 2 + (b_ - a - length) * (k / (n - 1) if n > 1 else 0.5)
            p, q, s_, d = next(sg for sg in segs if sg[2] <= s <= sg[2] + sg[3] + 1e-6) if s <= total else segs[-1]
            t = (s - s_) / max(d, 1e-9)
            out.append((template, p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t,
                        math.atan2(q[1] - p[1], q[0] - p[0])))
    # a piece on every corner not in an opening: the runs' pieces lie straight along one side each and left a crack
    # where two sides meet (sapporo plaza 2: ~10 open at a corner, the courtyard reached with its gate shut)
    closed = math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) < 1e-6
    corners = [(segs[k][0], segs[k][2]) for k in range(1, len(segs))] + ([(points[0], 0.0)] if closed else [])
    for (cx, cy), s in corners:
        if any(a <= s <= b_ for a, b_ in holes) or (closed and s == 0.0 and any(a <= total <= b_ for a, b_ in holes)):
            continue
        p, q = next((sg[0], sg[1]) for sg in segs if abs(sg[2] - s) < 1e-6)
        out.append((template, cx, cy, math.atan2(q[1] - p[1], q[0] - p[0])))
    return out


REFINERY_REACH = 250.0      # retail (Tokyo Harbor, Heidelberg, Havana): each refinery ~180 from the ore node it faces


def ore_lint(objects):
    """Every refinery placed (the map's or a mission's, any side) by an ore node: retail stands each one ~180 from
    the node it mines (user 2026-10-27: ore and its refinery belong together). Returns the problems."""
    ore = [o for o in objects if o.template == 'OreNode']
    out = []
    for o in objects:
        if o.template.endswith('Refinery'):
            near = min((math.hypot(o.x - n.x, o.y - n.y) for n in ore), default=None)
            if near is None or near > REFINERY_REACH:
                out.append(f'{o.template} at ({o.x:g}, {o.y:g}): no ore node within {REFINERY_REACH:g}'
                           + ('' if near is None else f' (nearest {near:.0f})'))
    return out


def bridge(p, q, template='HB_Bridge_02'):
    """A bridge from p to q (world points on the two banks, the same tier): (x, y, angle, flags) of its start and
    its end object, to be placed one right after the other (retail: start, then end, in the object list; their
    angles vary and seem not to matter; lengths 270 to 1780 on retail maps)."""
    a = math.atan2(q[1] - p[1], q[0] - p[0])
    return [(p[0], p[1], a, BRIDGE_START), (q[0], q[1], a + math.pi, BRIDGE_END)]
