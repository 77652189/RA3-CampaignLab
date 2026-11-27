"""Finish a locked layout with retail scenery. Terrain, road geometry and buildings stay fixed."""

from collections import defaultdict, deque
from dataclasses import dataclass, replace
from itertools import pairwise
import math
from random import Random

import numpy as np

from experimental.mapgen.buildings import Shape, TOWN, geometry_shapes
from experimental.mapgen.design import DesignError, point_in_ring
from experimental.mapgen.library import read_shape, read_xml
from experimental.mapgen.paint import KIT_ALIASES
from experimental.mapgen.roads import ROAD_WIDTH
from experimental.mapgen.terrain import CELL, Ground, Piece, strip_coordinates


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
NO_PATH_BLOCK = {'none', 'none?', 'topple', 'foot_topple_noshape'}
KNOWN_BLOCKING = NO_PATH_BLOCK | {'all', 'foot', 'foot_topple', 'rockbig'}
CELL_PAD = CELL / math.sqrt(2)


@dataclass(frozen=True)
class Dressing:
    ground: Ground
    pieces: tuple[Piece, ...]
    facades: tuple[tuple[str, str, int, int], ...]  # block, feature, allowance, used


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


def _passage_edges(sketch):
    for border in sketch.borders:
        for a, b, left, right, name in sketch.border_sections(border):
            yield border, name, left, right, a, b


def _lanes(sketch, layout, roadbed):
    roads = {
        road: tuple(Lane(road, tuple(map(float, a)), tuple(map(float, b)), ROAD_WIDTH[spec['width']] / 2)
                    for a, b in sketch.edges[road])
        for road, spec in sketch.roads.items()
    }
    yield from (lane for group in roads.values() for lane in group)
    for bridge in roadbed.bridges if roadbed is not None else ():
        yield Lane(bridge.road, *bridge.landings, bridge.deck_width / 2)
    for border, name, _, _, a, b in _passage_edges(sketch):
        if any(state.get(name) for state in sketch.state_pass.values()):
            spec = sketch.borders[border]
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


class _Assets:
    def __init__(self, library, sage):
        self.library, self.sage = library, sage
        self.entries, self.resolved = {}, {}
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
            src = self.sage / entry['source'].removeprefix('sdk/SageXML/')
            obj = next(o for o in read_xml(src).iter('GameObject') if o.attrib['id'].casefold() == key)
            data = {'shapes': [read_shape(node) for node in obj.findall('Geometry/Shape')]}
        shapes = geometry_shapes(data['shapes'])
        if not shapes and kind not in NO_PATH_BLOCK:
            return None  # An unknown pathfinding footprint cannot be dressed safely.
        return kind, shapes or (Shape('CYLINDER', (0., 0., 0.), CELL / 2, CELL / 2, 0.),)

    def palette(self, kit, words):
        entries = self.library['kits'][kit]
        names = sorted({e['template'] for k in ('props', 'destructibles') for e in entries[k]}
                       | set(DONORS.get(kit, ())), key=lambda name: (name.casefold(), name))
        return tuple(name for name in dict.fromkeys(n.casefold() for n in names)
                     if name.partition('_')[-1].startswith(words) and not any(
                         bad in name for bad in ('cliff', 'ring', 'grate', 'collapsed', 'collapse', 'dead'))
                     and self.get(name) and self.get(name)[0] in NO_PATH_BLOCK)


def _posed(assets, prop):
    asset = assets.get(prop.template)
    if asset is None:
        raise DesignError(prop.template, 'dressing', 'no verified SDK footprint and blocking class')
    kind, shapes = asset
    return kind, tuple(shape.posed(prop.x, prop.y, prop.angle) for shape in shapes)


def _guard(prop, kind, shapes, lanes):
    pad = CELL_PAD if kind not in NO_PATH_BLOCK else 0.
    for lane in lanes:
        if any(replace(lane, half_width=lane.half_width + pad).touches(s) for s in shapes):
            raise DesignError(lane.name, 'dressing', f'{prop.template} at ({prop.x:g}, {prop.y:g}) enters lane {lane.name}')


def check_lanes(sketch, roadbed, layout, pieces, library, sage):
    """Validate final native placements. A lane infringement identifies the prop and lane."""
    lanes = tuple(_lanes(sketch, layout, roadbed))
    assets = _Assets(library, sage)
    for prop in pieces:
        _guard(prop, *_posed(assets, prop), lanes)


def _mask_shape(grid, shape, border):
    x, y = shape.center[:2]
    rx, ry = shape.support(1, 0) + CELL_PAD, shape.support(0, 1) + CELL_PAD
    i, j = (max(0, math.ceil((p-r) / CELL) + border) for p, r in ((x, rx), (y, ry)))
    k, l = (min(size, math.floor((p+r) / CELL) + border + 1)
            for p, r, size in ((x, rx, grid.shape[1]), (y, ry, grid.shape[0])))
    if k <= i or l <= j:
        return False
    j2, i2 = np.ogrid[j:l, i:k]
    dx, dy = (i2 - border) * CELL - x, (j2 - border) * CELL - y
    if shape.kind == 'BOX':
        c, s = math.cos(shape.angle), math.sin(shape.angle)
        cells = ((abs(c * dx + s * dy) <= shape.half_x + CELL_PAD)
                 & (abs(c * dy - s * dx) <= shape.half_y + CELL_PAD))
    else:
        cells = np.hypot(dx, dy) <= rx
    window = grid[j:l, i:k]
    changed = np.any(window & cells)
    window &= ~cells
    return changed


def walkable(ground, roadbed, layout, border, pieces, library, sage):
    """Conservative grid for infantry and vehicles. Use a cell's full footprint."""
    grid = (ground.raw > ground.waterline) & ~ground.blocked
    if roadbed is not None and roadbed.bridges:
        y, x = (np.indices(grid.shape) - border) * CELL
        for bridge in roadbed.bridges:
            a, b = bridge.landings
            ux, uy, _, length = _axes(a, b)
            along, across = strip_coordinates(x, y, a, (ux, uy))
            grid |= (along >= 0) & (along <= length) & (abs(across) <= bridge.deck_width / 2)
    for _, group in layout.blocks:
        for building in group:
            if building.blocking not in NO_PATH_BLOCK:
                for shape in building.collision:
                    _mask_shape(grid, shape, border)
    assets = _Assets(library, sage)
    for p in pieces:
        kind, shapes = _posed(assets, p)
        if kind not in NO_PATH_BLOCK:
            for shape in shapes:
                _mask_shape(grid, shape, border)
    return grid


def _distance(grid, start, end):
    height, width = grid.shape
    if any(not (0 <= y < height and 0 <= x < width and grid[y, x]) for y, x in (start, end)):
        return None
    queued = np.zeros_like(grid)
    queued[start] = True
    queue = deque([(*start, 0)])
    while queue:
        y, x, steps = queue.popleft()
        if (y, x) == end:
            return steps
        for j, i in ((y-1, x), (y, x-1), (y, x+1), (y+1, x)):
            if 0 <= j < height and 0 <= i < width and grid[j, i] and not queued[j, i]:
                queued[j, i] = True
                queue.append((j, i, steps + 1))
    return None


def _check_routes(finish, layout, pieces):
    """A blocker can only remove cells. Keep each declared ground route's distance."""
    sketch, assets = finish.sketch, finish.assets
    blockers = [p for p in pieces if assets.get(p.template)[0] not in NO_PATH_BLOCK]
    if not blockers:
        return
    endpoints = sketch.blocks | sketch.points
    border = finish.border
    routes = []
    for name, rel in sketch.relations.items():
        if rel.get('who') not in ('foot', 'vehicle', 'amphibian'):
            continue
        sources = ('a', 'b') if rel['type'] == '谁先到' else ('from',)
        if 'to' not in rel:
            continue
        for source in sources:
            routes.append((name, *(
                tuple(round(v / CELL) + border for v in reversed(endpoints[rel[key]]['at']))
                for key in (source, 'to')
            )))
    if not routes:
        return
    grid = walkable(finish.ground, finish.roadbed, layout, border, (), finish.library, assets.sage)
    baseline = [_distance(grid, a, b) for _, a, b in routes]
    for prop in blockers:
        _, shapes = _posed(assets, prop)
        changed = [_mask_shape(grid, s, border) for s in shapes]
        if any(changed):
            for (name, a, b), old in zip(routes, baseline):
                if _distance(grid, a, b) != old:
                    raise DesignError(name, 'dressing', f'{prop.template} changes lane {name}')


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
    def __init__(self, sketch, ground, roadbed, layout, library, kits, sage, border):
        self.sketch, self.ground, self.roadbed, self.library = sketch, ground, roadbed, library
        self.kits, self.border = kits, border
        self.assets = _Assets(library, sage)
        self.lanes = tuple(_lanes(sketch, layout, roadbed))
        self.locked = dict(layout.blocks)
        self.obstacles = [s for _, group in layout.blocks for b in group for s in b.placement + b.collision]
        self.props, self.counts = [], {}
        self.texture = ground.textures.copy()
        self.dry = (ground.raw > ground.waterline) & ~ground.blocked
        self.groups = defaultdict(list)
        for group in (library.get('setpieces') or {}).get('groups', ()):
            if len(group['relative_transforms']) <= SET_PIECE_BUDGET:
                self.groups[group['style_kit']].append(group)

    def put(self, block, facade, budget, props):
        key = block, facade
        used = self.counts.setdefault(key, (budget, 0))[1]
        props = tuple(props)
        if not props or used + len(props) > budget:
            return False
        shapes = []
        for prop in props:
            if self.assets.get(prop.template) is None:
                return False
            kind, footprint = _posed(self.assets, prop)
            point = (prop.x, prop.y)
            if not self.fits(block, point) or any(not self.fits(block, s.center[:2]) for s in footprint):
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
        self.props.extend(props)
        self.obstacles.extend(shapes)
        self.counts[key] = budget, used + len(props)
        return True

    def fits(self, block, point):
        x, y = point
        i, j = round(x / CELL) + self.border, round(y / CELL) + self.border
        return (0 <= j < self.dry.shape[0] and 0 <= i < self.dry.shape[1] and self.dry[j, i]
                and not self.ground.hidden[j, i] and point_in_ring(point, self.sketch.rings[block]) == 1
                and not any(point_in_ring(point, self.sketch.rings[child]) >= 0
                            for child, spec in self.sketch.blocks.items() if spec.get('parent') == block))

    def patch(self, block, at, angle, length, width, material, *, slope=False):
        kit = self.kits[block]
        folder = KIT_ALIASES.get(kit, kit.rsplit('_', 1)[0])
        entries = self.library.get('texture_kits', {}).get(folder, {}).get(material, ())
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

    def dressing(self):
        added = set(self.texture.flat) - set(self.ground.rank)
        ground = replace(self.ground, textures=self.texture, rank=(*self.ground.rank, *sorted(added)))
        return Dressing(ground, tuple(self.props), tuple((*key, *value) for key, value in self.counts.items()))


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
    for _, name, left, right, a, b in spans:
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
            if sketch.blocks[block]['use'] in QUAY:
                for group in groups:
                    if group['use'] == '码头' and finish.put(block, facade, SET_PIECE_BUDGET, _group(group, at, angle)):
                        break
                finish.patch(block, at, angle, 9 * CELL, 5 * CELL, 'Road')
            finish.put(block, facade, SET_PIECE_BUDGET,
                       _sprigs(cover, rng, at, angle, [(-30, 15), (20, 0), (40, 16)]))
            continue

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


def expand(sketch, ground, roadbed, layout, library, kits, sage, border):
    """Place kit scenery after ground, roads, paint and building lock have been resolved."""
    finish = _Finish(sketch, ground, roadbed, layout, library, kits, sage, border)
    edges = defaultdict(list)
    for span in _passage_edges(sketch):
        for block in span[2:4]:
            if block:
                edges[block].append(span)
    for block, spec in sketch.blocks.items():
        if spec.get('kind') == 'water':
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
        if spec['use'] in NATURAL and 'at' in spec:
            at = spec['at']
            angle = rng.uniform(-math.pi, math.pi)
            # One side of an open lot gains a silhouette. Its centre stays available for manoeuvres.
            for sign in (-1, 1):
                center = _offset(at, angle, sign * 10 * CELL, 3 * CELL)
                finish.put(block, 'open lot', SET_PIECE_BUDGET,
                           _sprigs(trees, rng, center, angle, [(-30, 30), (15, 45), (30, -15)]))
                finish.put(block, 'open lot', SET_PIECE_BUDGET,
                           _sprigs(cover, rng, center, angle, [(-27, 12), (18, -20)]))
    result = finish.dressing()
    check_lanes(sketch, roadbed, layout, result.pieces, library, sage)
    _check_routes(finish, layout, result.pieces)
    return result
