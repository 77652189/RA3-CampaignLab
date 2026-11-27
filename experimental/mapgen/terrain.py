"""Expand a terrain plan on the container's 10-unit grid, then write its terrain chunks.

XY and water levels use world units. Block steps are absolute; a plane is in world height.
Cliff runs face left (high ground is on the left of the directed line). A ramp starts at its
low landing and points uphill; the rise in steps determines its length. Blocks paint in order.
"""
from collections.abc import Callable
from dataclasses import dataclass
import math

import numpy as np

from experimental.campaign import mapscript as _mapscript  # noqa: F401  (campaign writer's import bootstrap)
from experimental.mapgen.library import CLIFF_STEP_RAW

# The existing campaign writer loads these modules for both the CLI and the map package.
import mapterrain
import newmap
import terrain_rules as rules
from platmap import RAMP_MAX

CELL = rules.CELL
RAMP_LENGTH = 180
SUB_DEPTH = 70              # WorldBuilder manual, docs/research/first-party.md
SHORE_RISE = 4              # world units per cell: 6.4 writer units, below the ramp limit of 6.5
VISIBLE = rules.FIELDS.index('visible')
ON_SHORE = 2 * SHORE_RISE   # two bank cells' rise on each side of the waterline

# These straight pieces have placement measurements from the 150 game probe.
# The catalogue's adjacent-position medians (99/-13 and 119/-30) include hand placements.
_BENCHED = {'HB_CliffWall01': (100, -15), 'RM_CliffWall01_GRID': (120, -30)}


@dataclass(frozen=True)
class Surface:
    id: str
    use: str
    kit: str
    seed: int = 0


@dataclass(frozen=True)
class Block:
    points: tuple
    height: int | tuple      # whole steps, or (world Z at 0,0, rise per world X, rise per world Y)
    texture: str = 'Grass_Heidelberg01'
    surface: Surface | None = None


@dataclass(frozen=True)
class Cliff:
    start: tuple
    end: tuple
    kit: str


@dataclass(frozen=True)
class Ramp:
    low: tuple
    uphill: tuple
    steps: int
    width: float


@dataclass(frozen=True)
class Water:
    points: tuple            # footprint includes the sloping banks
    level: int = 200         # all footprints on a plan use the map's global water level


@dataclass(frozen=True)
class TerrainPlan:
    blocks: tuple = ()
    cliffs: tuple = ()
    ramps: tuple = ()
    water: tuple = ()
    base_steps: int = 3
    ground: str = 'Grass_Heidelberg01'
    cliff: str = 'Cliff_Gibraltar1'
    shore: str = 'Sand_SantaMonica01'


@dataclass(frozen=True)
class Piece:
    template: str
    x: float
    y: float
    angle: float


@dataclass
class Ground:
    raw: np.ndarray
    blocked: np.ndarray
    textures: np.ndarray
    hidden: np.ndarray
    pieces: tuple
    issues: tuple
    owners: np.ndarray
    ramp: np.ndarray
    shore: np.ndarray
    waterline: np.ndarray
    rank: tuple = ()
    edge_texture: Callable[[int, int, int, int, str], str | None] | None = None


def _polygon(points, x, y, distances=False):
    """Even-odd interior including the outline, optionally with distance to its nearest edge."""
    if len(points) < 3:
        raise ValueError('terrain polygons need at least three vertices')
    inside = np.zeros(x.shape, bool)
    distance = np.full(x.shape, np.inf)
    for (a, b), (c, d) in zip(points, (*points[1:], points[0])):
        dx, dy = c - a, d - b
        if dx == dy == 0:
            raise ValueError(f'duplicate polygon vertex {(a, b)}')
        if dy:
            inside ^= ((b > y) != (d > y)) & (x < a + (y - b) * dx / dy)
        t = np.clip(((x - a) * dx + (y - b) * dy) / (dx * dx + dy * dy), 0, 1)
        np.minimum(distance, (x - a - t * dx)**2 + (y - b - t * dy)**2, out=distance)
    inside |= distance < 1e-12
    return (inside, np.sqrt(distance)) if distances else inside


def _direction(vector):
    length = math.hypot(*vector)
    if not length:
        raise ValueError('terrain line has zero length')
    return np.asarray(vector, dtype=float) / length


def _strip(x, y, start, direction):
    dx, dy = x - start[0], y - start[1]
    tx, ty = direction
    return dx * tx + dy * ty, dy * tx - dx * ty


def _step(value):
    if type(value) is not int or not 0 <= value <= 65535 // CLIFF_STEP_RAW:
        raise ValueError(f'height {value!r} is not a valid whole step')
    return value * CLIFF_STEP_RAW


def _ramp_cut(start, tangent, ramp, uphill, run):
    """Interval along a cliff line inside the ramp and its one-cell shoulders."""
    along, cross = _strip(*start, ramp.low, uphill)
    da, dc = _strip(*tangent, (0, 0), uphill)
    half = ramp.width / 2 + CELL
    begin, end = -math.inf, math.inf
    for pos, rate, low, high in ((along, da, 0, run), (cross, dc, -half, half)):
        if abs(rate) < 1e-10:
            if not low <= pos <= high:
                return None
        else:
            a, b = sorted(((low - pos) / rate, (high - pos) / rate))
            begin, end = max(begin, a), min(end, b)
    return (begin, end) if begin < end else None


def _straight(library, kit, steps):
    style = library['kits'].get(kit, {})
    editor_names = {entry['template']: entry.get('editor_name', '')
                    for category in ('props', 'buildings', 'destructibles') for entry in style.get(category, ())}
    choices = []
    for entry in style.get('cliffs', ()):
        name = entry['template']
        if entry['height_steps'] != steps:
            continue
        editor_name = editor_names.get(name, '')
        if name.endswith('_GRID') and name not in _BENCHED and not editor_name.endswith('Straight'):
            continue
        length, offset = _BENCHED.get(name, (entry['length'], entry['offset_y']))
        if length and offset is not None and offset <= 0:
            choices.append((name not in _BENCHED, -entry['samples'], name, length, offset))
    if not choices:
        return None
    _, _, name, length, offset = min(choices)
    if name.endswith('_GRID'):
        length, offset = round(length / 30) * 30, round(offset / 30) * 30
    return name, length, offset


def _cliffs(plan, library, base, at, x, y, ramps):
    pieces, issues = [], []
    cover = np.zeros(x.shape, bool)
    for cliff in plan.cliffs:
        a, b = np.asarray(cliff.start), np.asarray(cliff.end)
        length = math.dist(a, b)
        tangent = _direction(b - a)
        normal = np.array((-tangent[1], tangent[0]))
        label = f'{cliff.kit} {cliff.start} → {cliff.end}'
        # Sample the two sides away from the ends, on the original blocks.
        along = np.linspace(min(CELL, length / 2), max(length - CELL, length / 2),
                            math.ceil(length / CELL) + 1)
        edge = a + along[:, None] * tangent
        lo, hi = (base[at(edge + side * CELL * normal)] for side in (-1, 1))
        if not (np.ptp(lo) == np.ptp(hi) == 0 and hi[0] > lo[0]
                and lo[0] % CLIFF_STEP_RAW == hi[0] % CLIFF_STEP_RAW == 0):
            issues.append(f'{label}: expected constant whole steps, high ground on the left')
            continue
        steps = int((hi[0] - lo[0]) / CLIFF_STEP_RAW)
        spec = _straight(library, cliff.kit, steps)
        if spec is None:
            issues.append(f'{label}: no measured {steps}-step straight piece')
            continue
        template, spacing, offset = spec
        if template.endswith('_GRID') and (
                not np.isclose(tangent.prod(), 0) or np.any(np.mod([a, b], 30))):
            issues.append(f'{label}: GRID runs need cardinal edges on the 30-unit grid')
            continue
        # Subtract the ordered ramp openings before fitting straight pieces.
        spans = [(0., length)]
        for ramp, uphill, run in ramps:
            cut = _ramp_cut(a, tangent, ramp, uphill, run)
            if cut is None:
                continue
            lo, hi = cut
            spans = [(p, q) for start, end in spans
                     for p, q in ((start, min(end, lo)), (max(start, hi), end)) if p < q]
        along_grid, across_grid = _strip(x, y, a, tangent)
        for start, end in spans:
            count = math.floor((end - start + 1e-7) / spacing)
            unused = end - start - count * spacing
            if unused > 1e-7:
                issues.append(f'{label}: {unused:g} units uncovered at ends of [{start:g}, {end:g}]')
            first = start + unused / 2 + spacing / 2
            stop = first + (count - 0.5) * spacing
            if template.endswith('_GRID') and count and np.any(np.mod(a + tangent * first - normal * offset, 30)):
                issues.append(f'{label}: piece origins at [{start:g}, {end:g}] would leave the 30-unit grid')
                continue
            for k in range(count):
                px, py = a + tangent * (first + k * spacing) - normal * offset
                pieces.append(Piece(template, float(px), float(py), math.atan2(tangent[1], tangent[0])))
            if count:
                cover |= ((along_grid >= first - spacing / 2) & (along_grid < stop)
                          & (across_grid >= -CELL) & (across_grid < 0))
    joints = {}
    for cliff in plan.cliffs:
        delta = _direction(np.subtract(cliff.end, cliff.start))
        for point, direction in ((cliff.start, delta), (cliff.end, -delta)):
            joints.setdefault(point, []).append(direction)
    bounds = x.min(), x.max(), y.min(), y.max()
    for (px, py), legs in joints.items():
        if len(legs) == 1:
            if bounds[0] < px < bounds[1] and bounds[2] < py < bounds[3]:
                issues.append(f'cliff end at {(px, py)}: no measured end fitting')
        elif len(legs) != 2 or not np.allclose(legs[0], -legs[1]):
            issues.append(f'cliff corner at {(px, py)}: straight pieces meet without a measured corner fitting')
    return tuple(pieces), tuple(issues), cover


def expand(plan, library, width, height, border):
    """Return raw u16 heights, field-0 bits, texture names and cliff placements. No game or file I/O."""
    y, x = (np.indices((height, width)) - border) * CELL
    raw = np.full(x.shape, _step(plan.base_steps), dtype=float)
    textures = np.full(x.shape, plan.ground, object)
    owners = np.full(x.shape, -1, dtype=np.int32)

    def at(points):
        i, j = np.rint(np.asarray(points) / CELL).astype(int).T + border
        return np.clip(j, 0, height - 1), np.clip(i, 0, width - 1)

    for owner, block in enumerate(plan.blocks):
        mask = _polygon(block.points, x, y)
        if isinstance(block.height, tuple):
            z, dx, dy = block.height
            if max(abs(dx), abs(dy)) * CELL / rules.WORLD_PER_OURS > RAMP_MAX:
                raise ValueError(f'block at {block.points[0]} exceeds the gentle slope limit')
            raw[mask] = (z + dx * x[mask] + dy * y[mask]) * rules.RAW_PER_WORLD
        else:
            raw[mask] = _step(block.height)
        textures[mask] = block.texture
        owners[mask] = owner

    base = raw.copy()
    ramps, ramp_mask = [], np.zeros(x.shape, bool)
    ramp_shoulders = np.zeros(x.shape, bool)
    for ramp in plan.ramps:
        uphill = _direction(ramp.uphill)
        lo = base[at(ramp.low)]
        rise = _step(ramp.steps)
        run = RAMP_LENGTH * ramp.steps
        if not (run and ramp.width >= 2 * CELL):
            raise ValueError(f'ramp at {ramp.low}: needs a positive rise and at least two cells of width')
        along, cross = _strip(x, y, ramp.low, uphill)
        core = abs(cross) <= ramp.width / 2
        on = (along >= 0) & (along <= run)
        pad = abs(cross) <= ramp.width / 2 + CELL
        shoulder = on & pad
        low = (along >= -CELL) & (along <= 0) & pad
        high = (along >= run) & (along <= run + CELL) & pad
        if (lo % CLIFF_STEP_RAW or not low.any() or not high.any()
                or np.any(base[low] != lo) or np.any(base[high] != lo + rise)):
            raise ValueError(f'ramp at {ramp.low}: landings do not meet the specified flat steps')
        if np.any(ramp_shoulders & shoulder):
            raise ValueError(f'ramp at {ramp.low}: overlapping ramp')
        raw[shoulder] = lo + along[shoulder] * rise / run
        ramp_mask |= on & core
        ramp_shoulders |= shoulder
        ramps.append((ramp, uphill, run))

    if len({water.level for water in plan.water}) > 1:
        raise ValueError('terrain water footprints need one common global level')
    waterline = np.full(x.shape, -np.inf)
    for water in plan.water:
        if type(water.level) is not int or water.level < SUB_DEPTH:
            raise ValueError('water level must be a whole world height at least 70 above zero')
        area, edge = _polygon(water.points, x, y, distances=True)
        if np.any(np.isfinite(waterline[area])):
            raise ValueError('standing water footprints overlap')
        floor = math.floor((water.level - SUB_DEPTH) * rules.RAW_PER_WORLD)
        bank = np.maximum(floor, base - edge * SHORE_RISE / CELL * rules.RAW_PER_WORLD)
        if not np.any(area & (bank == floor)):
            raise ValueError('water footprint is too narrow to reach submarine depth')
        if np.any(area & ramp_shoulders):
            raise ValueError('water footprint overlaps a ramp')
        raw[area] = np.minimum(raw[area], bank[area])
        waterline[area] = water.level * rules.RAW_PER_WORLD
        textures[area & (raw < base)] = plan.shore

    if not np.all((raw >= 0) & (raw <= 65535)):
        raise ValueError('terrain height outside unsigned 16-bit range')
    raw = np.rint(raw).astype(np.uint16)
    slope = rules.slope(raw / rules.RAW_PER_OURS)
    if np.any(slope[ramp_mask] > RAMP_MAX):
        raise ValueError('written ramp has a cell steeper than the existing ramp limit')
    if np.any((slope > RAMP_MAX) & np.isfinite(waterline)):
        raise ValueError('water footprint crosses ground too steep for a gentle shore')
    if plan.water and np.any(np.isneginf(waterline) & (raw <= plan.water[0].level * rules.RAW_PER_WORLD)):
        raise ValueError('ground outside the water footprints reaches the global water level')
    blocked = rules.impassable_bits(raw / rules.RAW_PER_OURS, waterline / rules.RAW_PER_OURS)
    textures[blocked] = plan.cliff
    pieces, issues, cover = _cliffs(plan, library, base, at, x, y, ramps)
    if np.any(blocked & ramp_shoulders & ~ramp_mask & ~cover):
        issues += ('ramp sides: exposed steep cells outside the travel lane have no measured edge fitting',)
    shore = np.abs(raw - waterline) <= ON_SHORE * rules.RAW_PER_WORLD
    return Ground(raw, blocked, textures, cover & blocked, pieces, issues, owners, ramp_shoulders, shore,
                  waterline)


def apply(m, plan, ground):
    """Write the expanded ground into the existing map, returning the normal preview TGAs."""
    hm = mapterrain.HeightMap(m)
    if ground.raw.shape != (hm.height, hm.width):
        raise ValueError('terrain ground and map container dimensions differ')
    hm.elev = ground.raw.ravel().tolist()
    hm.store()
    tiles = mapterrain.Tiles(m, hm.width)
    for field in range(8):
        tiles.fill_field(field, field == VISIBLE)
    for field, mask, value in ((rules.IMPASSABLE, ground.blocked, True), (VISIBLE, ground.hidden, False)):
        for j, i in zip(*np.nonzero(mask)):
            tiles.set_bit(field, int(i), int(j), value)
    for name in sorted(set(ground.textures.ravel()).union(ground.rank)):
        tiles.add_texture(name)
    tiles.arrays[3] = [0] * tiles.n
    if tiles.counts[2] != 1:
        raise ValueError('terrain container has custom cliff UVs')
    rank = ground.rank or [plan.cliff, plan.shore, *dict.fromkeys(b.texture for b in plan.blocks), plan.ground]
    newmap.paint_grid(tiles, {(i, j): texture for (j, i), texture in np.ndenumerate(ground.textures)},
                      rank, ground.edge_texture)
    tiles.store()
    points, level = (), 0
    if plan.water:
        points, level = plan.water[0].points, plan.water[0].level
    if len(plan.water) > 1:
        # A common plane covers the basins. The dry grid between them clips the surface.
        x, y = zip(*(point for water in plan.water for point in water.points))
        points = ((min(x), min(y)), (max(x), min(y)), (max(x), max(y)), (min(x), max(y)))
    newmap.set_water_area(m, points, level)
    return {key: newmap.preview_tga(hm, tiles, size, depth)
            for key, size, depth in (('art', 512, 24), ('small', 128, 32))}
