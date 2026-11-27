"""Finish a locked layout with retail scenery. Terrain, road geometry and buildings stay fixed."""

from collections import defaultdict
from dataclasses import dataclass, replace
import hashlib
from itertools import pairwise
import math
from random import Random
import re

import numpy as np

from experimental.mapgen.buildings import Footprint, NO_PATH_BLOCK, Shape, TOWN, geometry_shapes
from experimental.mapgen.design import DesignError, ROUTING_CELL, point_in_ring
from experimental.mapgen.library import read_shape, sdk_xml, texture_kit
from experimental.mapgen.paint import USE_CLASS
from experimental.mapgen.roads import ROAD_WIDTH
from experimental.mapgen.terrain import CELL, Ground, Piece


# Heidelberg uses these imported Yucatan plants alongside its own trees.
# Rushmore likewise shares the Yosemite and Yucatan foliage and scree.
DONORS = {
    'Heidelberg_HB': ('YU_BUSH05', 'YU_BUSH04', 'YU_SMALLROCKS01', 'YU_SMALLROCKS02'),
    'Mount_Rushmore_MR': ('YP_Tree02', 'YU_SMALLROCKS01', 'YU_SMALLROCKS02', 'CC_GRASS08'),
}
NATURAL = {'park', 'woodland', 'wildland', 'canyon', 'farm', '公园', '林地'}
QUAY = {'dock', 'industrial', '码头'}
# An ornamental group is one WorldBuilder set piece. A secondary frontage
# gets one, a busy entrance or a wooded edge has room for several.
SET_PIECE_BUDGET = 6
KNOWN_BLOCKING = NO_PATH_BLOCK | {'all', 'foot', 'foot_topple', 'rockbig'}
CELL_PAD = CELL / math.sqrt(2)


@dataclass(frozen=True)
class Dressing:
    ground: Ground
    pieces: tuple[Piece, ...]
    facades: tuple[tuple[str, str, int, int], ...]  # block, feature, allowance, used
    slots: dict[str, Piece]
    footprints: tuple[Footprint, ...]


@dataclass(frozen=True)
class Lane:
    name: str
    start: tuple
    end: tuple
    half_width: float

    def touches(self, shape):
        if self.start == self.end:
            return shape.point_gap(self.start) <= self.half_width
        return shape.segment_gap(self.start, self.end) <= self.half_width


def _axes(a, b):
    dx, dy = (float(y - x) for x, y in zip(a, b))
    length = math.hypot(dx, dy)
    return dx / length, dy / length, math.atan2(dy, dx), length


def _offset(at, angle, along, across):
    c, s = math.cos(angle), math.sin(angle)
    return (float(at[0]) + along * c - across * s, float(at[1]) + along * s + across * c)


def _nearest(at, a, b):
    ux, uy, angle, length = _axes(a, b)
    along = (at[0] - a[0]) * ux + (at[1] - a[1]) * uy
    return _offset(a, angle, min(length, max(0., along)), 0)


def _lanes(sketch, layout, roadbed):
    roads = {
        road: tuple(Lane(road, tuple(map(float, a)), tuple(map(float, b)), ROAD_WIDTH[spec['width']] / 2)
                    for a, b in sketch.edges[road])
        for road, spec in sketch.roads.items()
    }
    yield from (lane for group in roads.values() for lane in group)
    for bridge in roadbed.bridges if roadbed is not None else ():
        yield Lane(bridge.road, *bridge.landings, bridge.deck_width / 2)
    for border, spec in sketch.borders.items():
        for a, b, _, _, name in sketch.border_sections(border):
            if any(state.get(name) for state in sketch.state_pass.values()):
                span = spec.get('segments', {}).get(name.removeprefix(border + '.'), {})
                width = span.get('width', spec.get('width', 0))
                yield Lane(name, a, b, max(width / 2, 2 * CELL))
    for name, point in sketch.points.items():
        yield Lane(name, point['at'], point['at'], 2 * CELL)
    for name, group in layout.blocks:
        for b in group:
            if b.garrisonable and b.street in roads:
                at = (b.x, b.y)
                entry = min((_nearest(at, lane.start, lane.end) for lane in roads[b.street]),
                            key=lambda xy: math.dist(at, xy))
                yield Lane(f'{name} garrison entrance', entry, at, CELL)
    for name, relation in sketch.relations.items():
        if relation['type'] == '放得下':
            at = sketch.points[relation['point']]['at']
            yield Lane(name, at, at, relation['side'] / math.sqrt(2))
        elif relation['type'] == '看得见':
            a, b = (sketch.points.get(relation[side], sketch.blocks.get(relation[side]))['at']
                    for side in ('from', 'to'))
            yield Lane(name, a, b, CELL)


class Assets:
    def __init__(self, library, sage):
        self.library, self.sage = library, sage
        self.entries = {'orenode': {'source': 'Neutral/Structures/OreNode.xml'}}
        self.resolved = {}
        for kit in library['kits'].values():
            for category in ('buildings', 'destructibles', 'props'):
                for e in kit[category]:
                    self.entries[e['template'].casefold()] = e

    def get(self, template):
        key = template.casefold()
        if key not in self.resolved:
            self.resolved[key] = self._read(key)
        return self.resolved[key]

    def _read(self, key):
        entry = self.entries.get(key)
        kind = self.library['blocking'].get(key, {}).get('cls')
        if entry is None or kind not in KNOWN_BLOCKING:
            return None
        data = entry.get('geometry')
        if data is None:
            src = self.sage / entry.get('source', '').removeprefix('sdk/SageXML/')
            if not src.is_file():
                return None
            obj = next((o for o in sdk_xml(src).iter('GameObject') if o.attrib['id'].casefold() == key), None)
            if obj is None:
                return None
            data = {'shapes': [read_shape(node) for node in obj.findall('Geometry/Shape')],
                    'footprint': [read_shape(node) for node in obj.findall('Geometry/PlacementShape')]}
        shapes = geometry_shapes(data['shapes'])
        if not shapes and kind not in NO_PATH_BLOCK:
            return None  # An unknown pathfinding footprint cannot be dressed safely.
        # A generic Geometry/Shape on a non-blocking road or cliff is
        # an editor/model bound. An explicit PlacementShape can still occupy ground.
        placement = geometry_shapes(data['footprint']) if data.get('footprint') else ()
        return Footprint(kind, placement or (shapes if kind not in NO_PATH_BLOCK else ()), shapes)

    def posed(self, prop):
        asset = self.get(prop.template)
        if asset is None:
            raise DesignError(prop.template, 'dressing',
                              f'at ({prop.x:g}, {prop.y:g}): no verified SDK footprint and blocking class')
        placement, collision = (tuple(s.posed(prop.x, prop.y, prop.angle) for s in group)
                                for group in (asset.placement, asset.collision))
        return Footprint(asset.blocking, placement, collision)

    def occupied(self, pieces):
        return tuple(asset for prop in pieces if
                     (asset := self.posed(prop)).placement or asset.blocking not in NO_PATH_BLOCK)

    def palette(self, kit, words):
        entries = self.library['kits'][kit]
        names = sorted({e['template'] for k in ('props', 'destructibles') for e in entries[k]}
                       | set(DONORS.get(kit, ())), key=lambda name: (name.casefold(), name))
        return tuple(name for name in dict.fromkeys(n.casefold() for n in names)
                     if name.partition('_')[-1].startswith(words) and not any(
                         bad in name for bad in ('cliff', 'ring', 'grate', 'collapsed', 'collapse', 'dead'))
                     and self.get(name) and self.get(name).blocking in NO_PATH_BLOCK)


def _guard_shapes(footprint, prop):
    return footprint.collision or footprint.placement or (
        Shape('CYLINDER', (prop.x, prop.y, 0.), CELL / 2, CELL / 2, 0.),)


def footpath_flanks(sketch, assets):
    """Use real solid props to frame the tread, with their SDK collision edges facing it."""
    for border, spec in sketch.borders.items():
        for item in sketch.spans[border]:
            opening = spec.get('segments', {}).get(item.split('.', 1)[1], {})
            if 'footpath' not in opening:
                continue
            asset = assets.get(opening['footpath'])
            if asset is None or asset.blocking != 'rockbig' or len(asset.collision) != 1:
                raise DesignError(item, 'footpath', 'choose a solid, uncrushable retail prop with one footprint')
            shape, = asset.collision
            sections = [(a, b) for a, b, _, _, section in sketch.border_sections(border) if section == item]
            a, b = sections[0][0], sections[-1][1]
            ux, uy, angle, length = _axes(a, b)
            if any(abs((q[0] - p[0]) * uy - (q[1] - p[1]) * ux) > 1e-6 for p, q in sections):
                raise DesignError(item, 'footpath', 'choose a straight stretch of the border')
            center = _offset(a, angle, length / 2, 0)
            if shape.half_x * 2 < (length - ROUTING_CELL) / 2:
                raise DesignError(item, 'footpath', 'choose a prop that reaches from the tread to its shoulder')
            for sign in (-1, 1):
                x, y = _offset(center, angle, sign * (ROUTING_CELL / 2 + shape.half_x) - shape.center[0],
                               -shape.center[1])
                prop = Piece(opening['footpath'], x, y, angle)
                yield item, prop


def _guard(prop, kind, shapes, lanes):
    pad = CELL_PAD if kind not in NO_PATH_BLOCK else 0.
    for lane in lanes:
        if any(replace(lane, half_width=lane.half_width + pad).touches(s) for s in shapes):
            raise DesignError(lane.name, 'dressing', f'{prop.template} at ({prop.x:g}, {prop.y:g}) enters lane {lane.name}')


def check_flanks(sketch, roadbed, layout, flanks, assets):
    lanes = tuple(_lanes(sketch, layout, roadbed))
    for opening, prop in flanks:
        footprint = assets.posed(prop)
        other = (lane for lane in lanes if lane.name != opening)
        _guard(prop, footprint.blocking, footprint.collision, other)


def _group(group, at, angle, locked=False, depth=1.):
    rows = group['relative_transforms']
    front = min((r['dy'] for r in rows if r['dy']), key=abs, default=0.)
    for row in rows:
        if locked and row['template'].casefold() == group['anchor'].casefold() and not (row['dx'] or row['dy']):
            continue
        dy = front + (row['dy'] - front) * depth
        yield Piece(row['template'], *_offset(at, angle, row['dx'], dy),
                    angle + math.radians(row['angle_deg']))


class _Finish:
    def __init__(self, sketch, ground, roadbed, layout, assets, kits, border, frame, fixed):
        self.sketch, self.ground, self.roadbed = sketch, ground, roadbed
        self.kits, self.border = kits, border
        self.assets, self.fixed = assets, fixed
        self.lanes = tuple(_lanes(sketch, layout, roadbed))
        self.locked = dict(layout.blocks)
        self.obstacles = [s for obj in (*fixed, *(b for _, group in layout.blocks for b in group))
                          for s in obj.placement + obj.collision]
        self.slots, self.counts = {}, {}
        self.texture = ground.textures.copy()
        self.dry = (ground.raw > ground.waterline) & ~ground.blocked
        self.frame = frame
        self.groups = defaultdict(list)
        for group in (assets.library.get('setpieces') or {}).get('groups', ()):
            if len(group['relative_transforms']) <= SET_PIECE_BUDGET:
                self.groups[group['style_kit']].append(group)

    def put(self, block, facade, budget, props, *, shoulder=False, frame_block=None):
        key = block, facade
        used = self.counts.setdefault(key, (budget, 0))[1]
        props = tuple(props)
        if not props or used + len(props) > budget:
            return False
        shapes = []
        for prop in props:
            if self.assets.get(prop.template) is None:
                return False
            asset = self.assets.posed(prop)
            kind, footprint = asset.blocking, _guard_shapes(asset, prop)
            point = (prop.x, prop.y)
            on_edge = shoulder and kind in NO_PATH_BLOCK
            if not self.fits(block, point, shoulder=on_edge) or any(
                    not self.fits(block, s.center[:2], shoulder=on_edge) for s in footprint):
                return False
            if any(s.gap(b) <= 0 for s in footprint for b in self.obstacles
                   if math.dist(s.center[:2], b.center[:2]) <= math.hypot(s.half_x, s.half_y)
                   + math.hypot(b.half_x, b.half_y)):
                return False
            try:
                _guard(prop, kind, footprint, self.lanes)
            except DesignError:
                return False  # A candidate may miss its site; the output below is checked independently.
            shapes.extend(footprint)
        feature = re.sub(r'[^A-Za-z0-9_-]+', '-', facade.split(' (', 1)[0]).strip('-') or 'prop'
        for prop in props:
            identity = f'{facade}:{prop.template}:{prop.x:.9f}:{prop.y:.9f}:{prop.angle:.9f}'
            digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:12]
            slot = f'{block or frame_block}.scenery.{feature}-{digest}'
            while slot in self.slots:
                slot += '-next'
            self.slots[slot] = prop
        self.obstacles.extend(shapes)
        self.counts[key] = budget, used + len(props)
        return True

    def fits(self, block, point, *, shoulder=False):
        x, y = point
        i, j = round(x / CELL) + self.border, round(y / CELL) + self.border
        if block is None:
            pad = max(1, self.border)
            return (pad <= j < self.dry.shape[0] - pad and pad <= i < self.dry.shape[1] - pad
                    and not self.frame.mask[j, i] and self.ground.raw[j, i] > self.ground.waterline[j, i]
                    and (self.roadbed is None or not self.roadbed.paved[j, i])
                    and np.ptp(self.ground.raw[j - 1:j + 2, i - 1:i + 2]) == 0)
        return (0 <= j < self.dry.shape[0] and 0 <= i < self.dry.shape[1]
                and (self.dry[j, i] or (shoulder and self.ground.ramp_edges[j, i]))
                and not self.ground.hidden[j, i] and point_in_ring(point, self.sketch.rings[block]) == 1
                and not any(point_in_ring(point, self.sketch.rings[child]) >= 0
                            for child, spec in self.sketch.blocks.items() if spec.get('parent') == block))

    def patch(self, block, at, angle, length, width, material, *, slope=False):
        spec = self.sketch.blocks[block]
        if spec.get('ground_texture') is not None or (material == 'Dirt' and USE_CLASS.get(spec['use']) == 'Snow'):
            return  # Keep the authored surface or the paint layer's scoured snow.
        folder = texture_kit(self.kits[block])
        entries = self.assets.library.get('texture_kits', {}).get(folder, {}).get(material, ())
        names = sorted(e['id'] for e in entries if not e['id'].startswith(('Transition', 'Cliff')))
        if not names:
            return
        name = next((n for n in names if n.startswith('Gravel')), names[0])
        x, y = at
        radius = math.hypot(length, width)
        i, j = (math.floor((v - radius) / CELL) + self.border for v in (x, y))
        k, l = (math.ceil((v + radius) / CELL) + self.border + 1 for v in (x, y))
        j, i = max(j, 0), max(i, 0)
        yy, xx = np.ogrid[j:min(l, self.dry.shape[0]), i:min(k, self.dry.shape[1])]
        dx, dy = (xx - self.border) * CELL - x, (yy - self.border) * CELL - y
        c, s = math.cos(angle), math.sin(angle)
        mask = ((dx * c + dy * s) / length)**2 + ((dy * c - dx * s) / width)**2 <= 1
        window = np.s_[j:min(l, self.dry.shape[0]), i:min(k, self.dry.shape[1])]
        mask &= self.dry[window] & ~self.ground.hidden[window]
        if self.roadbed is not None:
            mask &= ~self.roadbed.paved[window]
        if not slope:
            mask &= ~self.ground.ramp[window]
        for row, col in zip(*np.nonzero(mask)):
            p = ((i + col - self.border) * CELL, (j + row - self.border) * CELL)
            if self.fits(block, p):
                self.texture[j + row, i + col] = name

    def dressing(self, flanks):
        slots = self.slots
        for name, patch in self.sketch.patches.items():
            slot = patch['slot']
            if slot not in slots:
                raise DesignError(name, 'slot', f'no scenery placement for {slot}')
            prop = slots[slot]
            if patch['op'] == 'delete':
                del slots[slot]
            elif patch['op'] == 'move':
                slots[slot] = replace(prop, x=patch['at'][0], y=patch['at'][1])
            else:
                slots[slot] = replace(prop, template=patch['with'])
        posed = tuple((prop, self.assets.posed(prop)) for prop in slots.values())
        for prop, footprint in posed:
            _guard(prop, footprint.blocking, _guard_shapes(footprint, prop), self.lanes)
        added = set(self.texture.flat) - set(self.ground.rank)
        ground = replace(self.ground, textures=self.texture, rank=(*self.ground.rank, *sorted(added)))
        return Dressing(ground, (*slots.values(), *flanks),
                        tuple((*key, *value) for key, value in self.counts.items()), slots,
                        (*self.fixed, *(footprint for _, footprint in posed)))


def _sprigs(palette, rng, at, angle, offsets):
    if palette:
        for along, across in offsets:
            yield Piece(rng.choice(palette), *_offset(at, angle, along, across), rng.uniform(-math.pi, math.pi))


def _front(finish, block, groups, palette, rng):
    sketch, kit = finish.sketch, finish.kits[block]
    building = next((b for b in finish.locked.get(block, ()) if b.protagonist), None)
    if building is not None:
        at = building.x, building.y
        finish.patch(block, at, building.angle, 6 * CELL, 7 * CELL, 'Road')
        for group in groups:
            if group['anchor'].casefold() == building.template.casefold():
                for depth in (1., .5):
                    if finish.put(block, 'yard', SET_PIECE_BUDGET,
                                  _group(group, at, building.angle, locked=True, depth=depth)):
                        break

    lamps = finish.assets.palette(kit, ('lamp', 'light01'))
    seats = [g for g in groups if any(word in g['anchor'].casefold() for word in ('bench', 'planter'))]
    for road, spec in sketch.roads.items():
        edges = [edge if sides[0] == block else edge[::-1] for edge in sketch.edges[road]
                 if block in (sides := sketch.sides[edge])]
        if not edges:
            continue
        budget = SET_PIECE_BUDGET * (2 if building and road == building.street else 1)
        for a, b in edges:
            _, _, angle, length = _axes(a, b)
            edge = ROAD_WIDTH[spec['width']] / 2
            # Work outward from the junction. Keep its turning space and the front door legible.
            for node, step in ((a, 1), (b, -1)):
                if len(sketch.junctions.get(node, ())) < 3:
                    continue
                for setback in (3, 7, 12):
                    at = _offset(node, angle, 10 * CELL * step, edge + setback * CELL)
                    if any(finish.put(block, road, budget, _group(group, at, angle)) for group in seats):
                        finish.patch(block, at, angle, 5 * CELL, 4 * CELL, 'Road')
                        break
            for start in range(0, math.floor(length / CELL), 14):
                along = (start + rng.uniform(5, 9)) * CELL
                if along >= length - 3 * CELL:
                    break
                at = _offset(a, angle, along, edge + 2 * CELL)
                props = _sprigs(lamps if start == 0 and lamps else palette, rng, at, angle, [(0, 0)])
                finish.put(block, road, budget, props)


def _edges(finish, block, spans, groups, cover, rocks, trees, rng):
    sketch = finish.sketch
    heights = sketch.state_heights['base']
    corners = defaultdict(list)
    for a, b, left, right, name, hard_quay in spans:
        other = right if left == block else left
        if other is None:
            continue
        high = heights[block] > heights[other]
        shore = sketch.blocks[other].get('kind') == 'water'
        if heights[block] == heights[other] and not shore:
            continue
        if block == right:
            a, b = b, a
        _, _, angle, length = _axes(a, b)
        facade = f'{name} ({a[0]:g},{a[1]:g})–({b[0]:g},{b[1]:g})'
        opened = any(state.get(name) for state in sketch.state_pass.values())
        if opened and shore:
            continue  # The landing stays visually and physically open.
        if shore:
            at = _offset(a, angle, length / 2, 7 * CELL)
            if hard_quay and sketch.blocks[block]['use'] in QUAY:
                for group in groups:
                    if group['use'] == '码头' and finish.put(block, facade, SET_PIECE_BUDGET, _group(group, at, angle)):
                        break
                finish.patch(block, at, angle, 9 * CELL, 5 * CELL, 'Road')
            finish.put(block, facade, SET_PIECE_BUDGET,
                       _sprigs(cover, rng, at, angle, [(-30, 15), (20, 0), (40, 16)]))
            continue
        if not opened:
            corners[a].append(angle)
            corners[b].append(angle)

        # End clumps turn square corners and bracket ramp mouths. The crest
        # gets foliage behind the rock lip; the toe gets low scree and scrub.
        stations = [min(2 * CELL, length / 2), max(length - 3 * CELL, length / 2)]
        if not opened:
            stations.extend((start + rng.uniform(4, 9)) * CELL for start in
                            range(10, math.floor(length / CELL - 9), 14))
        budget = SET_PIECE_BUDGET * (2 if opened else 3)
        for along in stations:
            at = _offset(a, angle, along, (3 if high else 4) * CELL)
            finish.patch(block, at, angle, 5 * CELL, 3 * CELL, 'Dirt', slope=opened)
            low = ([(0, 0), (2 * CELL, CELL)] if high else [(-CELL, 0), (CELL, CELL)])
            scrub = tuple(_sprigs(cover, rng, at, angle, low))
            scree = tuple(_sprigs(rocks, rng, at, angle, [(-CELL, 0)]))
            if not finish.put(block, facade, budget, (*scrub, *scree)):
                finish.put(block, facade, budget, scrub)
            if high and not opened:
                tree = (3 * CELL, rng.uniform(1.5, 5.5) * CELL)
                finish.put(block, facade, budget, _sprigs(trees, rng, at, angle, [tree]))
        if opened:
            # Follow the raised banks beyond the mouth on both sides. Low
            # scrub can sit on the non-travel slope, but cannot enter a lane.
            for point, sign in ((a, -1), (b, 1)):
                for i in range(1, 4):
                    at = _offset(point, angle, sign * rng.uniform(1.2, 2.1) * CELL, i * 2 * CELL)
                    finish.put(block, facade, budget, _sprigs(cover, rng, at, angle, [(0, 0)]), shoulder=True)

    for point, angles in corners.items():
        if len(angles) != 2 or abs(math.sin(angles[1] - angles[0])) < 1e-8:
            continue
        # A real change in cliff direction gets one cluster across the bend.
        # Split face names on a straight cliff do not create a new cluster.
        a, b = angles
        bisector = math.atan2(math.cos(a) + math.cos(b), -math.sin(a) - math.sin(b))
        at = _offset(point, bisector, 4 * CELL, 0)
        key = f'cliff corner {point}'
        finish.patch(block, at, bisector, 4 * CELL, 2 * CELL, 'Dirt')
        for palette, offsets in ((trees, [(2 * CELL, 0)]),
                                 (cover, [(0, -CELL), (0, CELL)]),
                                 (rocks, [(-CELL, 0)])):
            for prop in _sprigs(palette, rng, at, bisector, offsets):
                finish.put(block, key, SET_PIECE_BUDGET, (prop,))


def _woodland(finish, block, trees, rng):
    # Start from the irregular woodland outline. Groups overlap visually
    # inward, while the established lane and flat-pad guards reserve openings.
    ring = finish.sketch.rings[block]
    for a, b in pairwise(ring):
        _, _, angle, length = _axes(a, b)
        for station in range(5 * int(CELL), int(length), 12 * int(CELL)):
            edge = _offset(a, angle, station + rng.uniform(-CELL, CELL), 0)
            for layer, depth in enumerate((rng.uniform(2, 6), rng.uniform(7, 21))):
                at = _offset(edge, angle, 0, depth * CELL)
                group = _sprigs(trees, rng, at, angle, [(-22, 4), (2, -9), (24, 16)])
                finish.put(block, f'woods {a} {station} {layer}', SET_PIECE_BUDGET, group)


def _dress_frame(finish, block, cover, trees, rng):
    for edge, sides in finish.sketch.sides.items():
        if set(sides) != {block, None}:
            continue
        a, b = edge if sides[0] == block else edge[::-1]
        _, _, angle, length = _axes(a, b)
        for start in range(0, int(length / CELL) - 6, 18):
            along = min((start + rng.uniform(4, 12)) * CELL, length - 3 * CELL)
            at = _offset(a, angle, along, -rng.uniform(6, 13) * CELL)
            key = f'frame grove {a} {start}'
            for palette, offsets in ((trees, [(-30, -20), (0, 0), (25, -40)]),
                                     (cover, [(12, 24), (-26, 4)])):
                for prop in _sprigs(palette, rng, at, angle, offsets):
                    finish.put(None, key, SET_PIECE_BUDGET, (prop,), frame_block=block)


def expand(sketch, ground, roadbed, layout, library, kits, sage, border, frame=None, *, assets=None,
           native=(), flanks=()):
    """Place kit scenery after ground, roads, paint and building lock have been resolved."""
    assets = assets or Assets(library, sage)
    finish = _Finish(sketch, ground, roadbed, layout, assets, kits, border, frame, native)
    edges = defaultdict(list)
    for border, spec in sketch.borders.items():
        for section in sketch.border_sections(border):
            for block in section[2:4]:
                if block:
                    edges[block].append((*section, spec.get('shore') == 'quay'))
    for block, spec in sketch.blocks.items():
        if spec.get('kind') == 'water' or spec['use'] == 'ice':
            continue
        kit = kits[block]
        rng = Random(sketch.block_seed(block))
        groups = finish.groups[kit]
        cover = finish.assets.palette(kit, ('bush', 'shrub', 'grass', 'fern'))
        rocks = finish.assets.palette(kit, ('rock', 'smallrock', 'gardenrock'))
        trees = finish.assets.palette(kit, ('tree', 'redwood', 'palm'))
        if spec['use'] in TOWN | {'square', 'park'} or finish.locked.get(block):
            _front(finish, block, groups, cover, rng)
        _edges(finish, block, edges[block], groups, cover, rocks, trees, rng)
        if spec['use'] in {'woodland', 'snow_woodland'}:
            _woodland(finish, block, trees, rng)
        elif spec['use'] in NATURAL and 'at' in spec:
            at = spec['at']
            angle = rng.uniform(-math.pi, math.pi)
            # One side of an open lot gains a silhouette. Its centre stays available for manoeuvres.
            for sign in (-1, 1):
                center = _offset(at, angle, sign * 10 * CELL, 3 * CELL)
                finish.put(block, 'open lot', SET_PIECE_BUDGET,
                           _sprigs(trees, rng, center, angle, [(-30, 30), (15, 45), (30, -15)]))
                finish.put(block, 'open lot', SET_PIECE_BUDGET,
                           _sprigs(cover, rng, center, angle, [(-27, 12), (18, -20)]))
        if frame is not None:
            # A snow wood carries trees only, past the frame as inside it.
            _dress_frame(finish, block, () if spec['use'] == 'snow_woodland' else cover, trees,
                         Random(f'{sketch.block_seed(block)}:frame'))
    return finish.dressing(tuple(prop for _, prop in flanks))
