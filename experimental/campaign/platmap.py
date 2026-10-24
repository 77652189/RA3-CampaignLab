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


@dataclasses.dataclass
class Layout:
    shapes: list
    ramps: list = dataclasses.field(default_factory=list)
    roads: list = dataclasses.field(default_factory=list)
    base: int = 0                       # the tier everywhere no shape covers (0: sea)
    cliff: int = 2                      # smoothing passes (3 x 3 box): a tier step becomes a cliff ~2 * cliff cells wide


def rect(x0, y0, x1, y1, tier, what=''):
    return Shape('rect', (x0, y0, x1, y1), tier, what)


def poly(points, tier, what=''):
    return Shape('poly', tuple(points), tier, what)


def circle(x, y, r, tier, what=''):
    return Shape('circle', (x, y, r), tier, what)


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


def lint(layout, sites=None, objects=(), dims=CONTAINER):
    """A map's design checked without the game (docs/story/map-language.md): ramps gentle enough, sites meant for
    building (Site.build) flat, the map's own structures (ore, tech) on flat dry ground, every bridge from bank to bank
    of one level with water under its middle. Returns the problems (empty: fine)."""
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
        if not dry(o.x, o.y) or relief(e, o.x, o.y, 60.0, b) > FLAT:
            out.append(f'{o.template} at ({o.x:g}, {o.y:g}): not on flat dry ground')
        k += 1
    return out


def bridge(p, q, template='HB_Bridge_02'):
    """A bridge from p to q (world points on the two banks, the same tier): (x, y, angle, flags) of its start and
    its end object, to be placed one right after the other (retail: start, then end, in the object list; their
    angles vary and seem not to matter; lengths 270 to 1780 on retail maps)."""
    a = math.atan2(q[1] - p[1], q[0] - p[0])
    return [(p[0], p[1], a, BRIDGE_START), (q[0], q[1], a + math.pi, BRIDGE_END)]
