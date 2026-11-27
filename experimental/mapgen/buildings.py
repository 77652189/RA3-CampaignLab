"""Lock civilian buildings against v2 design faces and the written height grid."""

from collections import Counter
from dataclasses import asdict, dataclass, replace
from itertools import pairwise
import json
import math
import random

import numpy as np

from experimental.mapgen.campaign_writer import rules
from experimental.mapgen.design import DesignError, point_in_ring, signed_area_twice
from experimental.mapgen.library import read_xml
from experimental.mapgen.roads import ROAD_WIDTH
from experimental.mapgen.terrain import CELL

# From cityblocks.KINDS: uses with a row, and the rowhouses setback, gap and coverage.
TOWN = {'oldtown', 'town', 'residential', 'suburb', '老城', '老街', '住宅', '郊区',
        'rowhouses', 'shops', 'apartments', 'towers', 'warehouses', 'villas'}
SETBACK, GAP, COVER = 6, 6, 0.25
EPS = 1e-7


def _rotate(x, y, c, s):
    return x * c - y * s, x * s + y * c


def _point_segment(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    x, y = p[0] - a[0], p[1] - a[1]
    t = min(1., max(0., (x * dx + y * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - t * dx, y - t * dy)


@dataclass(frozen=True)
class Shape:
    kind: str
    center: tuple
    half_x: float
    half_y: float
    height: float
    angle: float = 0.

    def posed(self, x, y, angle):
        ox, oy, z = self.center
        dx, dy = _rotate(ox, oy, math.cos(angle), math.sin(angle))
        return replace(self, center=(x + dx, y + dy, z), angle=angle)

    def support(self, nx, ny):
        if self.kind != 'BOX':
            return self.half_x
        a, b = _rotate(nx, ny, math.cos(self.angle), -math.sin(self.angle))
        return abs(a) * self.half_x + abs(b) * self.half_y

    def point_gap(self, p):
        x, y = self.center[:2]
        if self.kind != 'BOX':
            return math.dist((x, y), p) - self.half_x
        u, v = _rotate(p[0] - x, p[1] - y, math.cos(self.angle), -math.sin(self.angle))
        dx, dy = abs(u) - self.half_x, abs(v) - self.half_y
        return math.hypot(max(0., dx), max(0., dy)) + min(0., max(dx, dy))

    def edges(self):
        x, y = self.center[:2]
        c, s = math.cos(self.angle), math.sin(self.angle)
        corners = [(x + u, y + v) for u, v in (
            _rotate(i * self.half_x, j * self.half_y, c, s)
            for i, j in ((-1, -1), (1, -1), (1, 1), (-1, 1)))]
        return pairwise((*corners, corners[0]))

    def segment_gap(self, a, b):
        x, y = self.center[:2]
        if self.kind != 'BOX':
            return _point_segment((x, y), a, b) - self.half_x
        c, s = math.cos(self.angle), math.sin(self.angle)
        u, v = _rotate(a[0] - x, a[1] - y, c, -s)
        p, q = _rotate(b[0] - x, b[1] - y, c, -s)
        # Separating axes for a rectangle and a segment, including the segment normal.
        nx, ny = q - v, u - p
        separation = max(min(u, p) - self.half_x, -max(u, p) - self.half_x,
                         min(v, q) - self.half_y, -max(v, q) - self.half_y,
                         (abs(u * nx + v * ny) - self.half_x * abs(nx)
                          - self.half_y * abs(ny)) / math.hypot(nx, ny))
        if separation <= 0:
            return separation
        return min(self.point_gap(a), self.point_gap(b),
                   *(_point_segment(corner, a, b) for corner, _ in self.edges()))

    def gap(self, other):
        if other.kind != 'BOX':
            return self.point_gap(other.center[:2]) - other.half_x
        if self.kind != 'BOX':
            return other.gap(self)
        return min(min(other.segment_gap(a, b) for a, b in self.edges()),
                   min(self.segment_gap(a, b) for a, b in other.edges()))


def _shapes(entries):
    shapes = []
    for entry in entries:
        kind, radius = entry['Type'], entry['MajorRadius']
        if kind not in {'BOX', 'CYLINDER', 'SPHERE'}:
            raise ValueError(f'unsupported SDK shape {kind}')
        offset = tuple(entry.get('Offset', {}).get(axis, 0.) for axis in 'xyz')
        minor = entry['MinorRadius'] if kind == 'BOX' else radius
        shapes.append(Shape(kind, offset, radius, minor, entry.get('Height', 0.)))
    return tuple(shapes)


@dataclass(frozen=True)
class Foundation:
    z: float
    low: float
    high: float


@dataclass(frozen=True)
class Building:
    template: str
    x: float
    y: float
    angle: float
    street: str
    protagonist: bool
    placement: tuple[Shape, ...]
    collision: tuple[Shape, ...]
    foundation: Foundation
    garrisonable: bool
    blocking: str


@dataclass(frozen=True)
class Layout:
    blocks: tuple[tuple[str, tuple[Building, ...]], ...]

    def to_bytes(self):
        data = {block: [asdict(b) for b in buildings] for block, buildings in self.blocks}
        return (json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


@dataclass(frozen=True)
class _Template:
    name: str
    source: str
    front: float
    placement: tuple[Shape, ...]
    collision: tuple[Shape, ...]

    @property
    def area(self):
        return sum((4 if s.kind == 'BOX' else math.pi) * s.half_x * s.half_y
                   for s in self.placement)


@dataclass(frozen=True)
class _Frontage:
    name: str
    a: tuple
    b: tuple
    half_width: float

    def slots(self, anchor=None):
        length = math.dist(self.a, self.b)
        tx, ty = ((b - a) / length for a, b in zip(self.a, self.b))
        step_count = math.ceil(length / CELL)
        along = [(i + .5) * length / step_count for i in range(step_count)]
        if anchor is not None:
            near = (anchor[0] - self.a[0]) * tx + (anchor[1] - self.a[1]) * ty
            near = min(length, max(0., near))
            along = sorted(set([near, *along]), key=lambda t: (abs(t - near), t))
        for t in along:
            yield (self.a[0] + t * tx, self.a[1] + t * ty), (-ty, tx)


class BuildingPlanner:
    """Expand with a kit per block and measured local front bearings (template to radians).

    A protagonist names a kit template, or asks for any building or any garrisonable
    building. Only templates with a measured front are candidates. The origin and
    rotation published here are the ones to give to the map writer (zero Z offset).
    """

    def __init__(self, design, ground, library, kits, fronts, sage, border):
        self.design, self.ground, self.library = design, ground, library
        self.kits = kits
        self.fronts = {name.casefold(): angle for name, angle in fronts.items()}
        self.sage, self.border = sage, border
        self._sdk = {}
        self._garrisons = {}
        self.rings = {name: tuple((float(x), float(y)) for x, y in ring)
                      for name, ring in design.rings.items()}
        self.junctions = {tuple(map(float, point)) for point, edges in design.junctions.items() if len(edges) >= 3}
        self.roads = []
        self.frontages = {name: [] for name in design.blocks}
        for road, spec in design.roads.items():
            for edge in design.edges[road]:
                a, b = tuple(tuple(map(float, p)) for p in edge)
                half_width = ROAD_WIDTH[spec['width']] / 2
                self.roads.append(_Frontage(road, a, b, half_width))
                for block, start, end in zip(design.sides[edge], (a, b), (b, a)):
                    if block is not None:
                        self.frontages[block].append(_Frontage(road, start, end, half_width))

    def _document(self, path):
        if path not in self._sdk:
            root = read_xml(path)
            objects = {obj.attrib['id'].casefold(): obj for obj in root.iter('GameObject')}
            includes = [node.attrib['source'][5:] for node in root.findall('Includes/Include')
                        if node.get('source', '').startswith('DATA:')]
            self._sdk[path] = objects, includes
        return self._sdk[path]

    def _read_garrison(self, template, source):
        path = self.sage / source.removeprefix('sdk/SageXML/')
        obj = self._document(path)[0][template.casefold()]
        seen = set()
        while obj.attrib['id'] not in seen:
            seen.add(obj.attrib['id'])
            for behavior in obj.findall('Behaviors/*'):
                if behavior.tag in {'ContestableGarrisonContain', 'GarrisonContain'}:
                    return behavior.get('{uri:ea.com:eala:asset:instance}joinAction') != 'Remove'
                if behavior.get('id') == 'ModuleTag_Garrison':
                    return False
            parent = obj.get('inheritFrom')
            if not parent:
                return False
            included = self._document(path)[1]
            paths = (path, *(self.sage / p for p in included if p.casefold().endswith('/' + parent.casefold() + '.xml')),
                     self.sage / 'BaseObjects' / (parent + '.xml'))
            for candidate in paths:
                if candidate.is_file() and parent.casefold() in self._document(candidate)[0]:
                    path, obj = candidate, self._document(candidate)[0][parent.casefold()]
                    break
            else:
                raise ValueError(f'{template}: SDK inheritance cannot resolve {parent}')
        raise ValueError(f'{template}: SDK inheritance cycle')

    def _garrisonable(self, block, template):
        if template.name not in self._garrisons:
            try:
                self._garrisons[template.name] = self._read_garrison(template.name, template.source)
            except (KeyError, ValueError, OSError) as exc:
                raise DesignError(block, 'buildings', f'{template.name}: {exc}') from exc
        return self._garrisons[template.name]

    def _palette(self, block):
        kit = self.kits.get(block)
        if kit not in self.library['kits']:
            raise DesignError(block, 'buildings', f'no civilian kit {kit!r}')
        entries = self.library['kits'][kit]['buildings']
        choices = []
        for entry in sorted(entries, key=lambda e: e['template']):
            name, g = entry['template'], entry['geometry']
            front = self.fronts.get(name.casefold())
            if g and g['footprint'] and front is not None:
                # The library has already followed inheritance and selected PlacementShape.
                choices.append(_Template(name, entry['source'], front,
                                         _shapes(g['footprint']), _shapes(g['shapes'])))
        random.Random(self.design.block_seed(block)).shuffle(choices)
        return choices

    def _foundation(self, shapes, x, y):
        raw = self.ground.raw
        gx, gy = x / CELL + self.border, y / CELL + self.border
        i, j = math.floor(gx), math.floor(gy)
        vertices = raw[j:j + 2, i:i + 2].astype(float)
        if i < 0 or j < 0 or vertices.shape != (2, 2):
            return None, (CELL, 'foundation outside terrain grid')
        # The map object sits at ground level at its origin. Bound terrain relief by
        # the vertices of every cell touched by a shape, including thin/off-grid pieces.
        low, high = vertices.min(), vertices.max()
        z = np.array([1 - (gy - j), gy - j]) @ vertices @ np.array([1 - (gx - i), gx - i])
        for shape in shapes:
            px, py = shape.center[:2]
            rx, ry = shape.support(1, 0), shape.support(0, 1)
            a, b = (math.floor(v / CELL) + self.border for v in (px - rx, py - ry))
            c, d = (math.ceil(v / CELL) + self.border for v in (px + rx, py + ry))
            if min(a, b) < 0 or c >= raw.shape[1] or d >= raw.shape[0]:
                return None, (CELL, 'foundation outside terrain grid')
            patch = raw[b:d + 1, a:c + 1]
            if np.ptp(patch):
                yy, xx = np.ogrid[b:d, a:c]
                dx, dy = (xx + .5 - self.border) * CELL - px, (yy + .5 - self.border) * CELL - py
                half = CELL / 2
                if shape.kind == 'BOX':
                    co, si = math.cos(shape.angle), math.sin(shape.angle)
                    margin = half * (abs(co) + abs(si))
                    cells = ((abs(co * dx + si * dy) <= shape.half_x + margin)
                             & (abs(-si * dx + co * dy) <= shape.half_y + margin)
                             & (abs(dx) <= rx + half) & (abs(dy) <= ry + half))
                else:
                    cells = np.hypot(np.maximum(abs(dx) - half, 0.),
                                     np.maximum(abs(dy) - half, 0.)) <= rx
                for view in (patch[:-1, :-1], patch[1:, :-1], patch[:-1, 1:], patch[1:, 1:]):
                    if cells.any():
                        values = view[cells]
                        low, high = min(low, values.min()), max(high, values.max())
            else:
                low, high = min(low, patch.min()), max(high, patch.max())
        low, high, z = (float(h) / rules.RAW_PER_WORLD for h in (low, high, z))
        spread = high - low
        return Foundation(z, low, high), (spread - rules.BUILD_VARIATION, f'foundation relief {spread:.3f}')

    def _fit(self, block, rings, placed, template, frontage, kerb, inward, depth, *, clear_corners=False):
        nx, ny = inward
        angle = (math.atan2(-ny, -nx) - template.front) % math.tau
        angle = round(angle, 12) % math.tau
        placement, collision = (tuple(shape.posed(0., 0., angle) for shape in group)
                                for group in (template.placement, template.collision))
        setback = frontage.half_width + SETBACK
        reach = max(s.support(nx, ny) - s.center[0] * nx - s.center[1] * ny
                    for s in placement + collision)
        offset = setback + reach + depth
        x, y = (round(p + n * offset, 9) for p, n in zip(kerb, inward))
        placement, collision = (tuple(replace(s, center=(s.center[0] + x, s.center[1] + y, s.center[2]))
                                      for s in group) for group in (placement, collision))
        shapes = tuple(dict.fromkeys(placement + collision))
        worst = (0., '')
        corners = [end for end in (frontage.a, frontage.b) if end in self.junctions] if clear_corners else ()
        tx, ty = ny, -nx
        for s in shapes:
            # Leave an alley's width across the mouth of a junction. The gap
            # is for seeing the turn and moving a squad through it, so test the
            # complete footprint, including wings away from the origin.
            for a, b in corners:
                along = abs((s.center[0] - a) * tx + (s.center[1] - b) * ty)
                worst = max(worst, (ROAD_WIDTH['alley'] / 2 + s.support(tx, ty) - along, 'junction clearance'))
            for index, ring in enumerate(rings):
                gap = min(s.segment_gap(a, b) for a, b in pairwise(ring))
                if (point_in_ring(s.center[:2], ring) == 1) != (index == 0) and gap > 0:
                    gap = -gap
                worst = max(worst, (SETBACK - gap, 'face setback'))
            for road in self.roads:
                gap = s.segment_gap(road.a, road.b)
                worst = max(worst, (road.half_width + SETBACK - gap, f'road {road.name} setback'))
            for building in placed:
                for other in building.placement + building.collision:
                    worst = max(worst, (GAP - s.gap(other), f'{building.template} clearance'))
        if worst[0] > EPS:
            return None, worst
        foundation, miss = self._foundation(shapes, x, y)
        if miss[0] > EPS:
            return None, miss
        garrisonable = self._garrisonable(block, template)
        blocking = self.library['blocking'].get(template.name.casefold(), {}).get('cls', 'unknown')
        return Building(template.name, x, y, angle, frontage.name, not placed, placement,
                        collision, foundation, garrisonable, blocking), None

    def lock_block(self, block):
        spec = self.design.blocks[block]
        request = spec.get('protagonist')
        town = spec['use'] in TOWN
        if request is None and (not town or spec.get('kind') == 'water'):
            return ()
        frontage = self.frontages[block]
        if request is not None and (not frontage or spec.get('kind') == 'water'):
            raise DesignError(block, 'buildings', f'{request!r}: no dry street frontage')
        if not frontage:
            return ()
        ring = self.rings[block]
        rings = (ring, *(self.rings[k] for k, v in self.design.blocks.items() if v.get('parent') == block))
        palette = self._palette(block)
        placed = []
        if request is not None:
            key = request.strip().casefold()
            candidates = [t for t in palette if t.name.casefold() == key]
            if key in {'building', '楼'}:
                candidates = palette
            elif key in {'garrison', 'garrisonable', '驻军楼'}:
                candidates = [t for t in palette if self._garrisonable(block, t)]
            if not candidates:
                raise DesignError(block, 'buildings', f'{request!r}: no kit candidate with a footprint and measured front')
            anchor = spec['at']
            slots = [(kerb, normal, f) for f in frontage for kerb, normal in f.slots(anchor)]
            slots.sort(key=lambda slot: math.dist(anchor, slot[0]))
            xs, ys = zip(*ring)
            depth_count = math.ceil(math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / CELL)
            tightest = (math.inf, '', '')
            for step in range(depth_count + 1):
                for kerb, normal, f in slots:
                    for t in candidates:
                        b, miss = self._fit(block, rings, [], t, f, kerb, normal, step * CELL)
                        if b is not None:
                            placed.append(b)
                            break
                        tightest = min(tightest, (*miss, t.name))
                    if placed:
                        break
                if placed:
                    break
            if not placed:
                amount, reason, template = tightest
                raise DesignError(block, 'buildings', f'{request!r}: tightest miss {template}, {reason}, {amount:.3f} world units')
        if town:
            rows = [t for t in palette if 'house' in t.name.casefold()]
            rows.sort(key=lambda t: -t.area)
            coverage = COVER * (signed_area_twice(ring) - sum(map(signed_area_twice, rings[1:]))) / 2
            used = Counter(b.template for b in placed)
            built = sum(t.area for t in palette if used[t.name])
            for f in frontage:
                for kerb, normal in f.slots():
                    if built >= coverage:
                        break
                    for t in rows:
                        if used[t.name] >= 3:
                            continue
                        b, _ = self._fit(block, rings, placed, t, f, kerb, normal, 0., clear_corners=True)
                        if b is not None:
                            placed.append(replace(b, protagonist=False))
                            used[t.name] += 1
                            built += t.area
                            break
        return tuple(placed)

    def lock(self):
        return Layout(tuple((block, self.lock_block(block)) for block in sorted(self.design.blocks)))

    def relock(self, layout, block):
        buildings = self.lock_block(block)
        return Layout(tuple((name, buildings if name == block else old) for name, old in layout.blocks))
