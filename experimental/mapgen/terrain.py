"""Expand a terrain plan on the container's 10-unit grid, then write its terrain chunks.

XY and water levels use world units. Block steps are absolute; a plane is in world height.
Cliff runs face left (high ground is on the left of the directed line). A ramp starts at its
low landing and points uphill; the rise in steps determines its length. Blocks paint in order.
"""
from collections.abc import Callable
from dataclasses import dataclass, replace
import math

import numpy as np

from experimental.mapgen.design import LAND, STEP_WORLD, DesignError, face_rings, on_segment, point_in_ring
from experimental.mapgen.campaign_writer import RAMP_MAX, mapterrain, newmap, rules
from experimental.mapgen.library import CLIFF_STEP_RAW

CELL = rules.CELL
RAMP_LENGTH = 180
FRAME_MARGIN = 400  # clear the visible edge at the stock camera framing
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
    ground_texture: str | None = None


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
class Quay:
    start: tuple
    end: tuple
    kit: str
    steps: int


@dataclass(frozen=True)
class Water:
    points: tuple            # footprint includes the sloping banks
    level: int = 200         # all footprints on a plan use the map's global water level
    islands: tuple = ()


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
    quays: tuple = ()
    closed_edges: tuple = ()  # same-height land cuts, each an (a, b) world segment


@dataclass(frozen=True)
class Piece:
    template: str
    x: float
    y: float
    angle: float
    z: float = 0.


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
    ramp_edges: np.ndarray
    rank: tuple = ()
    edge_texture: Callable[[int, int, int, int, str], str | None] | None = None


@dataclass(frozen=True)
class DesignFrame:
    mask: np.ndarray
    bounds: tuple[int, int, int, int]  # inclusive rectangle in cells, relative to the playable corner

    def close(self, ground):
        return replace(ground, blocked=ground.blocked | ~self.mask)

    def map_borders(self, padding):
        height, width = self.mask.shape
        whole = (0, 0, width - 2 * padding, height - 2 * padding)
        # The active border clips the scene as well as the camera. Movement
        # still stops at the design faces via close().
        x0, y0, x1, y1 = self.bounds
        pad = int(FRAME_MARGIN / CELL)
        view = (max(0, x0 - pad), max(0, y0 - pad), min(whole[2], x1 + pad), min(whole[3], y1 + pad))
        return [whole] if view == whole else [whole, view]


def design_frame(sketch, ground, background_count, border):
    """The union of design faces, clipped to the map's playable cells."""
    mask = ground.owners >= background_count
    for name, spec in sketch.blocks.items():
        if spec.get('kind') == 'water':
            y, x = (np.indices(mask.shape) - border) * CELL
            ring = tuple(tuple(map(float, p)) for p in sketch.rings[name][:-1])
            mask |= polygon_mask(ring, x, y)
    height, width = mask.shape
    # The east/north boundary vertices are included in the map rectangle.
    mask[:border] = mask[height - border + 1:] = False
    mask[:, :border] = mask[:, width - border + 1:] = False
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if len(rows) < 2 or len(cols) < 2:
        raise DesignError('$', 'playable', 'design has no playable rectangle inside the map')
    bounds = tuple(int(v) - border for v in (cols[0], rows[0], cols[-1], rows[-1]))
    return DesignFrame(mask, bounds)


def _design_water(sketch):
    wet = {name for name, spec in sketch.blocks.items() if spec.get('kind') == 'water'}
    # A line inside continuous water (e.g. the mouth of a port) is a design
    # boundary only. Neither face should build a bank along it.
    edges = {(a, b) if left in wet else (b, a)
             for (a, b), (left, right) in sketch.sides.items() if (left in wet) != (right in wet)}
    outer, other = face_rings(sorted(edges))
    islands = {tuple(ring): [] for ring in outer if (ring[0], ring[1]) in edges}
    for ring in other:
        if (ring[0], ring[1]) in edges:
            parent = next(rim for rim in islands if point_in_ring(ring[0], rim) == 1)
            islands[parent].append(ring)

    def points(ring):
        return tuple(tuple(map(float, point)) for point in ring[:-1])

    return tuple(Water(points(rim), islands=tuple(map(points, holes))) for rim, holes in islands.items())


def frame_apron(sketch, plan, kit, size):
    """Continue the grade at each side of a rectangular dry cut into the camera margin."""
    rim = [(a, b, left or right) for (a, b), (left, right) in sketch.sides.items()
           if bool(left) != bool(right)]
    if not rim or any(sketch.medium(face) != LAND for _, _, face in rim):
        return plan
    axes = tuple(zip(*(p for a, b, _ in rim for p in (a, b))))
    lo, hi = tuple(map(min, axes)), tuple(map(max, axes))
    w, h, pad = size
    far = ((w - 2 * pad) * CELL, (h - 2 * pad) * CELL)
    outside = tuple((max(0., a - FRAME_MARGIN), min(cap, b + FRAME_MARGIN))
                    for a, b, cap in zip(lo, hi, far))

    def extend(p):
        return tuple(float(a if v == first else b if v == last else v)
                     for v, first, last, (a, b) in zip(p, lo, hi, outside))

    apron = []
    surface = Surface('backdrop', 'park', kit, ground_texture=plan.ground)
    for a, b, face in rim:
        # A rim side must lie on the perimeter of the bounding rectangle.
        normal = next((i for i, (u, v, bounds) in enumerate(zip(a, b, zip(lo, hi)))
                       if u == v and u in bounds), None)
        if normal is None:
            return plan
        a, b = tuple(map(float, a)), tuple(map(float, b))
        aa, bb = extend(a), extend(b)
        if aa[normal] != a[normal]:
            apron.append(Block((a, b, bb, aa), sketch.blocks[face]['height'], surface=surface))
    cliffs = []
    for cliff in plan.cliffs:
        a, b = cliff.start, cliff.end
        aa, bb = extend(a), extend(b)
        # Continue a cardinal cliff where it crosses the rim perpendicular
        # to the new strips. Leave unrelated and diagonal runs as drawn.
        if any(p == q and p not in bounds for p, q, bounds in zip(a, b, zip(lo, hi))):
            cliff = Cliff(aa, bb, cliff.kit)
        cliffs.append(cliff)
    return replace(plan, blocks=(*apron, *plan.blocks), cliffs=tuple(cliffs))


def _join_cliffs(cliffs):
    """A straight cliff can be split by a street or a face name without a physical joint."""
    merged = []
    for cliff in cliffs:
        for i in reversed(range(len(merged))):
            other = merged[i]
            if cliff.kit != other.kit:
                continue
            first, second = (other, cliff) if other.end == cliff.start else (cliff, other)
            if first.end == second.start and on_segment(first.end, first.start, second.end):
                cliff = Cliff(first.start, second.end, cliff.kit)
                del merged[i]
        merged.append(cliff)
    return tuple(merged)


def from_design(sketch, plan, kit):
    """Lay out the v2 faces and explicit land openings using the measured cliff and ramp rules."""
    def depth(name):
        parent = sketch.blocks[name].get('parent')
        return 0 if parent is None else 1 + depth(parent)

    faces = {name: tuple(tuple(map(float, p)) for p in sketch.rings[name][:-1])
             for name in sorted(sketch.blocks, key=depth)}
    blocks = tuple(Block(points, spec['height'],
                         surface=Surface(name, spec['use'], spec.get('kit', kit), sketch.block_seed(name),
                                         spec.get('ground_texture')))
                   for name, points in faces.items() if (spec := sketch.blocks[name]).get('kind') != 'water')
    water = plan.water or _design_water(sketch)
    cliffs, ramps, quays, closed_edges = {}, [], [], []
    for border in sketch.borders:
        for (a, b), _, _ in sketch.border_edges[border]:
            left, right = sketch.sides[a, b]
            if sketch.borders[border].get('shore') == 'quay':
                dry, points = (left, (a, b)) if sketch.medium(left) == LAND else (right, (b, a))
                spec = sketch.blocks[dry]
                quays.append(Quay(*(tuple(map(float, p)) for p in points),
                                  spec.get('kit', kit), spec['height']))
            if not left or not right or any(sketch.medium(f) != LAND for f in (left, right)):
                continue
            diff = sketch.blocks[left]['height'] - sketch.blocks[right]['height']
            if diff and not plan.cliffs:
                points = tuple(tuple(map(float, p)) for p in ((a, b) if diff > 0 else (b, a)))
                high = left if diff > 0 else right
                grades = tuple(sorted((sketch.blocks[left]['height'], sketch.blocks[right]['height'])))
                cliffs.setdefault(grades, []).append(Cliff(*points, sketch.blocks[high].get('kit', kit)))
        sections = []
        for a, b, left, right, name in sketch.border_sections(border):
            if left and right and sketch.medium(left) == sketch.medium(right) == LAND:
                diff = sketch.blocks[left]['height'] - sketch.blocks[right]['height']
                if not diff and sketch.base_pass.get(name) == frozenset():
                    closed_edges.append((a, b))
                if not plan.ramps and diff and sketch.base_pass.get(name):
                    if not sections or sections[-1][0] != name or sections[-1][1][-1][1] != a:
                        sections.append((name, []))
                    sections[-1][1].append((a, b, diff))
        for name, parts in sections:
            a, b, diff = parts[0][0], parts[-1][1], parts[0][2]
            tangent = unit_direction(np.subtract(b, a))
            if any(rise != diff or not np.allclose(unit_direction(np.subtract(q, p)), tangent)
                   for p, q, rise in parts):
                raise DesignError(name, 'ramp', 'choose an opening along one straight cliff of constant rise')
            spec = sketch.borders[border]
            opening = spec.get('segments', {}).get(name.split('.')[-1], {}) if name != border else {}
            allowed = sketch.base_pass[name]
            if allowed != LAND and 'footpath' not in opening:
                raise DesignError(name, 'ramp', 'name two landings and solid flanks for a footpath')
            width = opening.get('width', min(math.dist(a, b), spec.get('width', math.inf)))
            if width > math.dist(a, b) + 1e-7:
                raise DesignError(name, 'ramp', 'ramp width exceeds its opening along the cliff')
            uphill = np.array((-tangent[1], tangent[0])) * (1 if diff > 0 else -1)
            low = (np.add(a, b) / 2) - uphill * (RAMP_LENGTH * abs(diff) / 2)
            ramps.append(Ramp(tuple(low), tuple(uphill), abs(diff), width))
    return replace(plan, blocks=(*plan.blocks, *blocks), water=water, quays=(*plan.quays, *quays),
                   cliffs=plan.cliffs or tuple(c for group in cliffs.values() for c in _join_cliffs(group)),
                   ramps=plan.ramps or tuple(ramps),
                   closed_edges=(*plan.closed_edges, *closed_edges))


def polygon_mask(points, x, y, distances=False):
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


def unit_direction(vector):
    length = math.hypot(*vector)
    if not length:
        raise ValueError('terrain line has zero length')
    return np.asarray(vector, dtype=float) / length


def strip_coordinates(x, y, start, direction):
    dx, dy = x - start[0], y - start[1]
    tx, ty = direction
    return dx * tx + dy * ty, dy * tx - dx * ty


def _step(value):
    if type(value) is not int or not 0 <= value <= 65535 // CLIFF_STEP_RAW:
        raise ValueError(f'height {value!r} is not a valid whole step')
    return value * CLIFF_STEP_RAW


def _ramp_cut(start, tangent, ramp, uphill, run):
    """Interval along a cliff line inside the ramp and its one-cell shoulders."""
    along, cross = strip_coordinates(*start, ramp.low, uphill)
    da, dc = strip_coordinates(*tangent, (0, 0), uphill)
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
        tangent = unit_direction(b - a)
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
        along_grid, across_grid = strip_coordinates(x, y, a, tangent)
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
        delta = unit_direction(np.subtract(cliff.end, cliff.start))
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


# The Leningrad straight piece is 100 units tip-to-tip and the front lip
# sits 7 units to the right of its origin (retail placements and model).
_QUAY_PIECES = {'StPetersburg_ST': ('ST_SeaWallPiece01', 100, 7)}


def _quay_edges(plan, x, y):
    for quay in plan.quays:
        length = math.dist(quay.start, quay.end)
        tangent = unit_direction(np.subtract(quay.end, quay.start))
        along, across = strip_coordinates(x, y, quay.start, tangent)
        yield np.hypot(along - np.clip(along, 0, length), across)


def _quay_pieces(plan, library, raw, border):
    pieces = []
    for quay in plan.quays:
        template, length, offset = _QUAY_PIECES.get(quay.kit, ('', 0, 0))
        props = library['kits'].get(quay.kit, {}).get('props', ())
        if not any(p['template'] == template for p in props):
            raise ValueError(f'quay at {quay.start}: {quay.kit} has no measured retaining piece')
        a, b = np.asarray(quay.start), np.asarray(quay.end)
        run = math.dist(a, b)
        tangent = (b - a) / run
        normal = np.array((-tangent[1], tangent[0]))
        count = math.ceil(run / length)
        angle = math.atan2(tangent[1], tangent[0])
        for step in range(count):
            # Keep both tips covered and spread any overlap evenly along a run.
            along = run / 2 if count == 1 else length / 2 + step * (run - length) / (count - 1)
            x, y = a + along * tangent + offset * normal
            ix, iy = np.clip(np.asarray((x, y)) / CELL + border, 0, np.asarray(raw.shape[::-1]) - 1)
            i, j = min(int(ix), raw.shape[1] - 2), min(int(iy), raw.shape[0] - 2)
            u, v = ix - i, iy - j
            z = (np.array([1 - v, v]) @ raw[j:j+2, i:i+2] @ np.array([1 - u, u])) / rules.RAW_PER_WORLD
            pieces.append(Piece(template, float(x), float(y), angle, quay.steps * STEP_WORLD - float(z)))
    return tuple(pieces)


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
        mask = polygon_mask(block.points, x, y)
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
    ramp_edges = np.zeros(x.shape, bool)
    for ramp in plan.ramps:
        uphill = unit_direction(ramp.uphill)
        lo = base[at(ramp.low)]
        rise = _step(ramp.steps)
        run = RAMP_LENGTH * ramp.steps
        if not (run and ramp.width >= 2 * CELL):
            raise ValueError(f'ramp at {ramp.low}: needs a positive rise and at least two cells of width')
        along, cross = strip_coordinates(x, y, ramp.low, uphill)
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
        edge = abs(abs(cross) - ramp.width / 2 - CELL)
        ramp_edges |= (edge <= CELL) & (along >= -CELL) & (along <= run + CELL)
        ramps.append((ramp, uphill, run))

    if len({water.level for water in plan.water}) > 1:
        raise ValueError('terrain water footprints need one common global level')
    waterline = np.full(x.shape, -np.inf)
    sheer = np.zeros(x.shape, bool)
    for water in plan.water:
        if type(water.level) is not int or water.level < SUB_DEPTH:
            raise ValueError('water level must be a whole world height at least 70 above zero')
        area, edge = polygon_mask(water.points, x, y, distances=True)
        for island in water.islands:
            dry, distance = polygon_mask(island, x, y, distances=True)
            area &= ~dry
            np.minimum(edge, distance, out=edge)
        if np.any(np.isfinite(waterline[area])):
            raise ValueError('standing water footprints overlap')
        floor = math.floor((water.level - SUB_DEPTH) * rules.RAW_PER_WORLD)
        bank = np.maximum(floor, base - edge * SHORE_RISE / CELL * rules.RAW_PER_WORLD)
        if np.any(area & ramp_shoulders):
            raise ValueError('water footprint overlaps a ramp')
        for distance in _quay_edges(plan, x, y):
            # Only the bank whose nearest shoreline is the quay becomes vertical.
            cut = area & (distance <= edge + 1e-8) & (bank > floor)
            bank[cut] = floor
            sheer |= cut
        if not np.any(area & (bank == floor)):
            raise ValueError('water footprint is too narrow to reach submarine depth')
        raw[area] = np.minimum(raw[area], bank[area])
        waterline[area] = water.level * rules.RAW_PER_WORLD
        textures[area & (raw < base)] = plan.shore

    if not np.all((raw >= 0) & (raw <= 65535)):
        raise ValueError('terrain height outside unsigned 16-bit range')
    raw = np.rint(raw).astype(np.uint16)
    slope = rules.slope(raw / rules.RAW_PER_OURS)
    if np.any(slope[ramp_mask] > RAMP_MAX):
        raise ValueError('written ramp has a cell steeper than the existing ramp limit')
    quay_bank = rules.edit_region(sheer)
    if np.any((slope > RAMP_MAX) & np.isfinite(waterline) & ~quay_bank):
        raise ValueError('water footprint crosses ground too steep for a gentle shore')
    if plan.water and np.any(np.isneginf(waterline) & (raw <= plan.water[0].level * rules.RAW_PER_WORLD)):
        raise ValueError('ground outside the water footprints reaches the global water level')
    blocked = rules.impassable_bits(raw / rules.RAW_PER_OURS, waterline / rules.RAW_PER_OURS)
    # The field-0 lip stops amphibians from using the face as a beach.
    # Include the wet/dry join, not the deep water alongside the wall.
    lip = quay_bank & (slope > RAMP_MAX) & (raw > waterline)
    # A 20-unit routing cell straddles two 10-unit terrain samples.
    blocked |= rules.edit_region(lip) & (raw > waterline)
    textures[blocked] = plan.cliff
    for a, b in plan.closed_edges:
        along, across = strip_coordinates(x, y, a, unit_direction(np.subtract(b, a)))
        beyond_end = along - np.clip(along, 0, math.dist(a, b))
        # Cover the diagonal of a cell so a diagonal boundary cannot leak.
        blocked |= across**2 + beyond_end**2 <= CELL**2 / 2
    pieces, issues, cover = _cliffs(plan, library, base, at, x, y, ramps)
    pieces += _quay_pieces(plan, library, raw, border)
    cover |= lip
    if np.any(blocked & ramp_shoulders & ~ramp_mask & ~cover):
        issues += ('ramp sides: exposed steep cells outside the travel lane have no measured edge fitting',)
    shore = np.abs(raw - waterline) <= ON_SHORE * rules.RAW_PER_WORLD
    return Ground(raw, blocked, textures, cover & blocked, pieces, issues, owners, ramp_shoulders, shore,
                  waterline, ramp_edges)


def apply(m, plan, ground):
    """Write the expanded ground into the existing map, returning the normal preview TGAs."""
    hm = mapterrain.HeightMap(m)
    if ground.raw.shape != (hm.height, hm.width):
        raise ValueError('terrain ground and map container dimensions differ')
    hm.elev = ground.raw.ravel().tolist()
    hm.store()
    tiles = mapterrain.Tiles(m, hm.width)
    if tiles.counts[2] != 1:
        raise ValueError('terrain container has custom cliff UVs')
    # Every cell is repainted. A template's old textures and blends would still
    # be sent to the SDK atlas even though no cell can use them.
    original_textures, tiles.textures = tiles.textures, {}
    tiles.tex_at = tiles.tex_end
    tiles.counts[0] = tiles.counts[3] = 0
    tiles.descs.clear()
    tiles._known.clear()
    for field in range(8):
        tiles.fill_field(field, field == VISIBLE)
    for field, mask, value in ((rules.IMPASSABLE, ground.blocked, True), (VISIBLE, ground.hidden, False)):
        for j, i in zip(*np.nonzero(mask)):
            tiles.set_bit(field, int(i), int(j), value)
    for name in sorted(set(ground.textures.ravel()).union(ground.rank)):
        size = original_textures[name][1:] if name in original_textures else ()
        tiles.add_texture(name, *size)
    tiles.arrays[3] = [0] * tiles.n
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
