"""Finish a locked layout with retail scenery. Terrain, road geometry and buildings stay fixed."""

from collections import defaultdict
from dataclasses import dataclass, replace
import hashlib
from itertools import pairwise
import math
from random import Random
import re

import numpy as np

from experimental.mapgen.buildings import Footprint, NO_PATH_BLOCK, Shape, geometry_shapes
from experimental.mapgen.design import DesignError, point_in_ring
from experimental.mapgen.library import place_recipe, read_shape, sdk_xml, style_section, texture_kit
from experimental.mapgen.roads import ROAD_WIDTH
from experimental.mapgen.terrain import CELL, Ground, Piece


# WorldBuilder limits ornamental set pieces to six members.
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

    def palette(self, kit, spec):
        entries = self.library['kits'][kit]
        names = set(spec.get('include', ()))
        prefixes = tuple(spec.get('prefixes', ()))
        if prefixes:
            names.update(e['template'] for category in ('props', 'destructibles') for e in entries[category]
                         if e['template'].casefold().partition('_')[-1].startswith(prefixes))
        return tuple(name for name in sorted({n.casefold() for n in names})
                     if not any(word in name for word in spec.get('exclude', ()))
                     and self.get(name) and self.get(name).blocking in NO_PATH_BLOCK)


def _guard_shapes(footprint, prop):
    return footprint.collision or footprint.placement or (
        Shape('CYLINDER', (prop.x, prop.y, 0.), CELL / 2, CELL / 2, 0.),)


def _guard(prop, kind, shapes, lanes):
    pad = CELL_PAD if kind not in NO_PATH_BLOCK else 0.
    for lane in lanes:
        if any(replace(lane, half_width=lane.half_width + pad).touches(s) for s in shapes):
            raise DesignError(lane.name, 'dressing', f'{prop.template} at ({prop.x:g}, {prop.y:g}) enters lane {lane.name}')


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

    def put(self, block, facade, budget, props, *, shoulder=False):
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
            slot = f'{self.block}.scenery.{feature}-{digest}'
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
        if self.sketch.blocks[block].get('ground_texture') is not None or material in self.recipe.get('keep_ground', ()):
            return
        folder = texture_kit(self.kits[block])
        entries = self.assets.library.get('texture_kits', {}).get(folder, {}).get(material, ())
        prefixes = tuple(self.texture_policy.get('patch_exclude', ()))
        names = sorted(e['id'] for e in entries if not e['id'].startswith(prefixes))
        if not names:
            return
        name = next((n for n in names if n.startswith(self.texture_policy.get('patch_prefer', ''))), names[0])
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
        return Dressing(ground, tuple(slots.values()),
                        tuple((*key, *value) for key, value in self.counts.items()), slots,
                        (*self.fixed, *(footprint for _, footprint in posed)))

    def fill(self, block, recipe, rng):
        if outline := recipe.get('outline'):
            for a, b in pairwise(self.sketch.rings[block]):
                self.strip(block, '', a, b, self.edges[outline], rng)
        if 'at' in self.sketch.blocks[block] and (interior := recipe.get('interior')):
            self.node(block, interior, self.sketch.blocks[block]['at'], rng.uniform(-math.pi, math.pi), rng,
                      self.nodes[interior])

    def strip(self, block, name, a, b, treatment, rng, *, kerb=0., anchored=False, outside=False):
        _, _, angle, length = _axes(a, b)
        budget = SET_PIECE_BUDGET * treatment.get('anchor_budget' if anchored else 'budget', 1)
        unit = treatment.get('unit', CELL)
        target = None if outside else block

        def endpoints(kind):
            if kind is None:
                return
            fitting = self.nodes[kind]
            for point, sign in ((a, 1), (b, -1)):
                if len(self.sketch.junctions.get(point, ())) >= fitting.get('degree', 0):
                    self.node(block, name, point, angle, rng, fitting, budget, kerb=kerb, sign=sign)

        def stations():
            if treatment.get('middle'):
                yield 0, length / 2
            for end in treatment.get('ends', ()):
                yield 0, min(end * unit, length / 2) if end >= 0 else max(length + end * unit, length / 2)
            if 'step' in treatment:
                first, margin, pitch = treatment['step']
                for start in range(first, math.floor(length / unit - margin), pitch):
                    jitter = _sample(treatment.get('jitter', 0), rng)
                    along = (start + jitter) * unit
                    tail = length - treatment.get('tail', 0) * unit
                    if treatment.get('clamp'):
                        along = min(along, tail)
                    elif 'tail' in treatment and along >= tail:
                        break
                    yield start, along

        endpoints(treatment.get('before'))
        sites = tuple(stations()) if treatment.get('sample_first') else stations()
        cycle = treatment['cycle'] if 'cycle' in treatment else (treatment['node'],)
        phase = rng.randrange(len(cycle)) if len(cycle) > 1 else 0
        for index, (start, along) in enumerate(sites):
            # Sample all depths before emitting any of the clusters at this station.
            depths = [_sample(depth, rng) * CELL for depth in treatment.get('depths', (0,))]
            node = cycle[(index + phase) % len(cycle)]
            if index == 0:
                node = treatment.get('first') or node
            for layer, depth in enumerate(depths):
                at = _offset(a, angle, along, depth + kerb)
                key = treatment['slot'].format(a=a, start=start, layer=layer) if 'slot' in treatment else name
                self.node(target, key, at, angle, rng, self.nodes[node], budget)
        endpoints(treatment.get('after'))

    def node(self, block, name, at, angle, rng, fitting, budget=SET_PIECE_BUDGET, *,
             kerb=0., sign=1, building=None):
        for along, across in fitting.get('offsets', ((0, 0),)):
            point = _offset(at, angle, _sample(along, rng) * sign * CELL,
                            kerb + _sample(across, rng) * CELL)
            for action in fitting['actions']:
                if 'patch' in action:
                    length, width, material = action['patch']
                    self.patch(block, point, angle, length * CELL, width * CELL, material,
                               slope=action.get('slope', False))
                elif 'group' in action:
                    selection = action['group']
                    for group in self.groups[self.kits[block]]:
                        anchor = group['anchor'].casefold()
                        if (building and anchor != building.template.casefold() or
                                'id' in selection and selection['id'] != group.get('id') or
                                'use' in selection and group['use'] != selection['use'] or
                                'anchor_words' in selection and not any(w in anchor for w in selection['anchor_words'])):
                            continue
                        depths = selection.get('depths', (1.,))
                        if any(self.put(block, name, budget, _group(group, point, angle, bool(building), depth))
                               for depth in depths) and building is None:
                            if follow := action.get('on_success'):
                                self.node(block, name, point, angle, rng, self.nodes[follow], budget)
                            if fitting.get('first_fit'):
                                return
                            break
                else:
                    batches = []
                    for names, offsets in action['sprigs']:
                        palette = next((self.palettes[key] for key in names if self.palettes.get(key)), ())
                        unit = action.get('unit', 1)
                        offsets = [(x * unit, _sample(y, rng) * unit, heading) for x, y, *heading in offsets]
                        batches.append(tuple(Piece(rng.choice(palette),
                                                   *_offset(point, angle, x, y),
                                                   angle + math.radians(heading[0]) if heading else
                                                   rng.uniform(-math.pi, math.pi))
                                             for x, y, heading in offsets if palette))
                    props = tuple(p for batch in batches for p in batch)
                    if action.get('single'):
                        for prop in props:
                            self.put(block, name, budget, (prop,))
                    elif self.put(block, name, budget, props, shoulder=action.get('shoulder', False)):
                        if fitting.get('first_fit'):
                            return
                    elif action.get('trim'):
                        self.put(block, name, budget, batches[0])


def _sample(value, rng):
    return rng.uniform(*value) if isinstance(value, (tuple, list)) else value


def expand(sketch, ground, roadbed, layout, library, kits, sage, border, frame=None, *, assets=None,
           native=()):
    """Place kit scenery after ground, roads, paint and building lock have been resolved."""
    assets = assets or Assets(library, sage)
    finish = _Finish(sketch, ground, roadbed, layout, assets, kits, border, frame, native)
    edges = defaultdict(list)
    for border in sketch.borders:
        for section in sketch.border_sections(border):
            for block in filter(None, section[2:4]):
                edges[block].append((*section, border in sketch.quays))
    heights = sketch.state_heights['base']
    for block, spec in sketch.blocks.items():
        kit = kits[block]
        recipe = finish.recipe = place_recipe(library, kit, spec['use'])
        if spec.get('kind') == 'water' or recipe.get('bare'):
            continue
        finish.block = block
        finish.edges = treatments = style_section(library, kit, 'edges')
        finish.nodes = nodes = style_section(library, kit, 'nodes')
        places = style_section(library, kit, 'places')
        finish.texture_policy = places['texture_palette']
        palette = places.get('prop_palettes', {})
        finish.palettes = {key: assets.palette(kit, entry | {'exclude': palette.get('exclude', ())})
                           for key, entry in palette.items() if key != 'exclude'}
        rng = Random(sketch.block_seed(block))
        locked = finish.locked.get(block, ())
        building = next((b for b in locked if b.protagonist), None)
        if building and 'door' in nodes:
            finish.node(block, 'yard', (building.x, building.y), building.angle, rng, nodes['door'], building=building)
        if (recipe.get('street') or locked) and 'street' in treatments:
            for road, road_spec in sketch.roads.items():
                for edge in sketch.edges[road]:
                    sides = sketch.sides[edge]
                    if block in sides:
                        a, b = edge if sides[0] == block else edge[::-1]
                        finish.strip(block, road, a, b, treatments['street'], rng, kerb=ROAD_WIDTH[road_spec['width']] / 2,
                                     anchored=building is not None and building.street == road)

        corners = defaultdict(list)
        for a, b, left, right, name, hard_quay in edges[block]:
            other = right if left == block else left
            if other is None:
                continue
            shore = sketch.blocks[other].get('kind') == 'water'
            opened = any(state.get(name) for state in sketch.state_pass.values())
            if (shore and opened) or (not shore and heights[block] == heights[other]):
                continue
            high = heights[block] > heights[other]
            if block == right:
                a, b = b, a
            if not shore and not opened:
                _, _, angle, _ = _axes(a, b)
                corners[a].append(angle)
                corners[b].append(angle)
            if shore:
                role = recipe.get('hard_shore', 'shore') if hard_quay else 'shore'
            else:
                role = ('ramp_crest' if high else 'ramp_toe') if opened else ('crest' if high else 'toe')
            if role in treatments:
                facade = f'{name} ({a[0]:g},{a[1]:g})–({b[0]:g},{b[1]:g})'
                finish.strip(block, facade, a, b, treatments[role], rng)
        if 'cliff_corner' in nodes:
            for point, angles in corners.items():
                if len(angles) == 2 and abs(math.sin(angles[1] - angles[0])) >= 1e-8:
                    a, b = angles
                    angle = math.atan2(math.cos(a) + math.cos(b), -math.sin(a) - math.sin(b))
                    finish.node(block, f'cliff corner {point}', point, angle, rng, nodes['cliff_corner'])
        finish.fill(block, recipe, rng)
        if frame is not None and (treatment := recipe.get('frame')):
            frame_rng = Random(f'{sketch.block_seed(block)}:frame')
            for edge, sides in sketch.sides.items():
                if set(sides) == {block, None}:
                    a, b = edge if sides[0] == block else edge[::-1]
                    finish.strip(block, '', a, b, treatments[treatment], frame_rng, outside=True)
    return finish.dressing()
