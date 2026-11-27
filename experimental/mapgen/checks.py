"""Answer v2 relations against the terrain, decks and locked buildings that will be written."""

from dataclasses import dataclass
from html import escape
from itertools import pairwise
from math import ceil, dist, floor, inf, isfinite, sqrt
from pathlib import Path

import numpy as np
from scipy.ndimage import label

from experimental.mapgen.buildings import Shape, TOWN
from experimental.mapgen.campaign_writer import rules
from experimental.mapgen.roads import ROAD_WIDTH, crosses_water
from experimental.mapgen.terrain import CELL, polygon_mask, strip_coordinates, unit_direction


# SDK: Peacekeeper geometry and weapon, AttributeModifier_Garrisoned, BaseCivilianStructure.
EYE = 13.
GARRISON_RANGE = 150 * 1.75
GARRISON_VISION = 600.
# SkirmishAI/AIData.xml and the Hydrofoil's regular DEEP_WATER locomotor.
SHIP_DEPTH = 35.
UNITS = {'foot': '步兵', 'vehicle': '车辆', 'amphibian': '两栖单位', 'ship': '舰艇'}


@dataclass(frozen=True)
class Witness:
    place: str
    at: tuple[float, float]
    reason: str


@dataclass(frozen=True)
class Answer:
    status: str
    sentence: str
    place: tuple[str, ...]
    decision: str = ''
    witness: Witness | None = None


def _shape_mask(shape, x, y):
    dx, dy = x - shape.center[0], y - shape.center[1]
    if shape.kind != 'BOX':
        return dx * dx + dy * dy <= shape.half_x ** 2
    c, s = np.cos(shape.angle), np.sin(shape.angle)
    return (abs(c * dx + s * dy) <= shape.half_x) & (abs(-s * dx + c * dy) <= shape.half_y)


class _Grid:
    def __init__(self, sketch, ground, roadbed, layout, border, frame, flank_shapes):
        self.sketch, self.border, self.frame = sketch, border, frame
        self.ground, self.roadbed = ground, roadbed
        self.z = ground.raw / rules.RAW_PER_WORLD
        self.x = (np.arange(self.z.shape[1])[None, :] - border) * CELL
        self.y = (np.arange(self.z.shape[0])[:, None] - border) * CELL
        self.buildings = dict(layout.blocks)
        self.solids = [(b, shape) for group in self.buildings.values() for b in group for shape in b.collision]
        solid = np.zeros(self.z.shape, bool)
        foot = solid.copy()
        for building, shape in self.solids:
            if building.blocking in {'none', 'none?', 'topple', 'foot_topple_noshape'}:
                continue
            mask = _shape_mask(shape, self.x, self.y)
            foot |= mask
            if building.blocking not in {'foot', 'foot_topple'}:
                solid |= mask
        for shape in flank_shapes:
            mask = _shape_mask(shape, self.x, self.y)
            solid |= mask
            foot |= mask
        self.dry = ground.raw > ground.waterline
        land = self.dry & ~ground.blocked
        deep_water = (ground.waterline - ground.raw >= SHIP_DEPTH * rules.RAW_PER_WORLD) & ~ground.blocked
        self.deck = np.zeros(self.z.shape, bool)
        for bridge in roadbed.bridges if roadbed is not None else ():
            self.deck |= self.strip(*bridge.landings, bridge.deck_width / 2)
        self.deck &= frame.mask
        # The swim layer has no deck. An amphibian on land can take the separate land route.
        self.grids = {'foot': ((land & ~foot) | self.deck,),
                      'vehicle': ((land & ~solid) | self.deck,), 'ship': (deep_water,),
                      'amphibian': (~ground.blocked & ~solid, (land & ~solid) | self.deck)}
        self.masks = {}

    def strip(self, a, b, half, ends=0.):
        along, across = strip_coordinates(self.x, self.y, a, unit_direction(np.subtract(b, a)))
        return (along >= -ends) & (along <= dist(a, b) + ends) & (abs(across) <= half)

    def area(self, name):
        if name not in self.masks:
            sketch = self.sketch
            if name in sketch.blocks:
                def face(n):
                    ring = tuple(tuple(map(float, p)) for p in sketch.rings[n][:-1])
                    x, y = np.broadcast_arrays(self.x, self.y)
                    return polygon_mask(ring, x, y)

                mask = face(name)
                for child, block in sketch.blocks.items():
                    if block.get('parent') == name:
                        mask &= ~face(child)
            else:
                mask = np.zeros(self.z.shape, bool)
                if name in sketch.roads:
                    for a, b in pairwise(sketch.lines[name]):
                        mask |= self.strip(a, b, ROAD_WIDTH[sketch.roads[name]['width']] / 2)
                    mask &= self.deck | (self.roadbed.paved if self.roadbed is not None else False)
                else:
                    border = name.split('.')[0]
                    for a, b, _, _, section in sketch.border_sections(border):
                        if name in (border, section):
                            # A cell intersecting the cut can cover half a cell diagonal.
                            mask |= self.strip(a, b, CELL / sqrt(2), CELL / 2)
            self.masks[name] = mask
        return self.masks[name]

    def point(self, name):
        return self.sketch.points.get(name, self.sketch.blocks.get(name))['at']

    def cell(self, p):
        return tuple(round(v / CELL) + self.border for v in reversed(p))

    def inside(self, p):
        x0, y0, x1, y1 = self.frame.bounds
        return (x0 * CELL <= p[0] <= x1 * CELL and y0 * CELL <= p[1] <= y1 * CELL
                and self.frame.mask[self.cell(p)])

    def route_layers(self, who, names, without=()):
        points = [self.point(name) for name in names]
        if not all(map(self.inside, points)):
            return
        cells = [self.cell(p) for p in points]
        for layer in self.grids[who]:
            grid = layer & self.frame.mask
            for name in without:
                grid &= ~self.area(name)
            if all(grid[c] for c in cells):
                yield grid, cells

    def reachable(self, who, a, b, without=()):
        for grid, (start, end) in self.route_layers(who, (a, b), without):
            regions = label(grid, structure=np.ones((3, 3), bool))[0]
            if regions[start] == regions[end]:
                return True
        return False

    def bypass_witness(self, rel):
        """Locate the alternate crossing on a route that misses the required opening."""
        from skimage.graph import MCP_Geometric

        only = rel['only_via']
        without = (only, rel['without']) if 'without' in rel else (only,)
        for grid, (start, end) in self.route_layers(rel['who'], (rel['from'], rel['to']), without):
            search = MCP_Geometric(np.where(grid, CELL, inf))
            costs, _ = search.find_costs([start], [end])
            if not isfinite(costs[end]):
                continue
            route = search.traceback(end)
            openings = {name: self.area(name) for spans in self.sketch.spans.values() for name in spans
                        if name not in without}
            unit = UNITS[rel['who']]
            for cell in route:
                for name, mask in openings.items():
                    if mask[cell]:
                        return Witness(name, self.world(cell), f'{unit}从这里绕过 {only}')
            return Witness(f'{rel["from"]} 到 {rel["to"]}', self.world(route[len(route) // 2]),
                           f'{unit}绕开 {only} 后仍能通行')
        return None

    def route_witness(self, rel):
        """Explain a failed positive route using the built cell, not the sketch distance."""
        who, a, b = (rel[k] for k in ('who', 'from', 'to'))
        depth = self.ground.waterline - self.ground.raw
        points = [self.point(name) for name in (a, b)]
        for name, p in zip((a, b), points, strict=True):
            if not self.inside(p):
                return Witness(name, tuple(p), '地点在可玩区外')
            cell = self.cell(p)
            if not any(g[cell] for g in self.grids[who]):
                if who == 'ship' and 0 <= depth[cell] < SHIP_DEPTH * rules.RAW_PER_WORLD:
                    return self.shallows(name, cell, depth)
                return Witness(name, self.world(cell), f'{UNITS[who]}在这个格子无法通行')
        if who != 'ship':
            return None

        # Lower the depth requirement only far enough to connect the two ends.
        # This finds a bottleneck on the best available channel, even when a
        # straight line between the sites crosses a headland.
        start, end = map(self.cell, points)
        swimming = (depth >= 0) & ~self.ground.blocked & self.frame.mask
        if 'without' in rel:
            swimming &= ~self.area(rel['without'])
        thresholds = np.unique(depth[swimming & (depth < SHIP_DEPTH * rules.RAW_PER_WORLD)])
        lo, hi = -1, len(thresholds)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            regions, _ = label(swimming & (depth >= thresholds[mid]), structure=np.ones((3, 3), bool))
            if regions[start] and regions[start] == regions[end]:
                lo = mid
            else:
                hi = mid
        if lo < 0:
            return None
        from skimage.graph import MCP_Geometric

        threshold = thresholds[lo]
        search = MCP_Geometric(np.where(swimming & (depth >= threshold), CELL, inf))
        search.find_costs([start], [end])
        cell = next(c for c in search.traceback(end) if depth[c] == threshold)
        here = rel.get('only_via')
        if here is None or not self.area(here)[cell]:
            here = next((name for name, spec in self.sketch.blocks.items()
                         if spec.get('kind') == 'water' and self.area(name)[cell]), f'{a} 到 {b}')
        return self.shallows(here, cell, depth)

    def world(self, cell):
        return tuple((int(i) - self.border) * CELL for i in reversed(cell))

    def shallows(self, name, cell, depth):
        return Witness(name, self.world(cell),
                       f'航道水深 {depth[cell] / rules.RAW_PER_WORLD:g}，舰艇需要 {SHIP_DEPTH:g}')

    def length(self, who, source, goal, via=None):
        """Route distances only for a race or detour, using weighted diagonal grid legs."""
        from skimage.graph import MCP_Geometric

        best = inf
        for grid, (start, end) in self.route_layers(who, (source, goal)):
            search = MCP_Geometric(np.where(grid, CELL, np.inf))
            if via is None:
                value = search.find_costs([end], [start])[0][start]
            else:
                through = self.area(via)
                outbound = search.find_costs([start])[0][through]
                inbound = search.find_costs([end])[0][through]
                value = (outbound + inbound).min(initial=inf)
            best = min(best, value)
        return best

    def height(self, x, y):
        gx, gy = np.asarray(x) / CELL + self.border, np.asarray(y) / CELL + self.border
        i = np.clip(gx.astype(int), 0, self.z.shape[1] - 2)
        j = np.clip(gy.astype(int), 0, self.z.shape[0] - 2)
        u, v = gx - i, gy - j
        return ((1 - v) * ((1 - u) * self.z[j, i] + u * self.z[j, i + 1])
                + v * ((1 - u) * self.z[j + 1, i] + u * self.z[j + 1, i + 1]))

    def sight(self, a, b, building=None):
        if not (self.inside(a) and self.inside(b)):
            return False
        start = self.height(*a) + EYE
        if building is not None:
            start = building.foundation.z + max(s.height + s.center[2] for s in building.collision)
        end = self.height(*b) + EYE
        n = max(2, ceil(2 * dist(a, b) / CELL))
        t = np.arange(1, n) / n
        x, y = (p + (q - p) * t for p, q in zip(a, b))
        ray = start + (end - start) * t
        if np.any(self.height(x, y) > ray):
            return False
        return not any(np.any(_shape_mask(shape, x, y) & (ray <= bld.foundation.z + shape.center[2] + shape.height))
                       for bld, shape in self.solids if bld is not building and shape.height > 0)

    def cover(self, point, road, by, fraction):
        at = self.point(point)
        block = self.sketch.points[point]['block']
        candidates = [b for b in self.buildings.get(block, ()) if b.garrisonable and b.collision]
        building = next((b for b in candidates if any(s.point_gap(at) <= 0 for s in b.collision)), None)
        if building is None:
            building = next((b for b in candidates if b.protagonist), None)
        if building is None or self.roadbed is None:
            return False
        limit = GARRISON_RANGE if by == 'range' else GARRISON_VISION
        paved = self.roadbed.paved | self.deck
        covered = total = 0.
        for a, b in pairwise(self.sketch.lines[road]):
            length = dist(a, b)
            n = ceil(length / CELL)
            for k in range(n):
                p = tuple(float(u + (v - u) * ((k + .5) / n)) for u, v in zip(a, b))
                total += length / n
                if (self.inside(p) and paved[self.cell(p)]
                        and min(s.point_gap(p) for s in building.collision) <= limit
                        and self.sight((building.x, building.y), p, building)):
                    covered += length / n
        return covered >= fraction * total - 1e-9

    def room(self, point, side):
        x, y = self.point(point)
        half = side / 2
        lo, hi = (x - half, y - half), (x + half, y + half)
        if not (self.inside(lo) and self.inside(hi)):
            return False
        # Include the exact footprint limits and every height sample inside them.
        xx, yy = (np.r_[a, np.arange(ceil(a / CELL) * CELL, b, CELL), b] for a, b in zip(lo, hi))
        i = slice(floor(lo[0] / CELL) + self.border, ceil(hi[0] / CELL) + self.border + 1)
        j = slice(floor(lo[1] / CELL) + self.border, ceil(hi[1] / CELL) + self.border + 1)
        square = Shape('BOX', (x, y, 0.), half, half, 0.)
        return (np.ptp(self.height(xx[None, :], yy[:, None])) <= rules.BUILD_VARIATION
                and np.all(self.dry[j, i] & ~self.ground.blocked[j, i])
                and all(square.gap(s) >= 0 for group in self.buildings.values() for b in group for s in b.placement))


def _answer(grid, rel, held, pending):
    kind = rel['type']
    who = rel.get('who')
    unit = UNITS.get(who)
    a, b = rel.get('from'), rel.get('to')
    point = rel.get('point')
    if kind == '通不通':
        only, avoid = rel.get('only_via'), rel.get('without')
        expected = rel.get('reachable', True)
        places = (a, b, *filter(None, (only, avoid)))
        sentence = f'{unit}从 {a} {"能" if expected else "不能"}到 {b}'
        if only:
            sentence += f'，且只能经过 {only}'
        if avoid:
            sentence += f'，避开 {avoid}'
        order = rel.get('order')
        if order:
            sentence = f'{order} 航令：{sentence}' if who == 'ship' else f'{order} 行动命令：{sentence}'
        if held:
            return not expected, sentence, places, f'在 {rel["state"]} 状态放行 {order}。'
        if pending:
            return False, sentence, places, ''
        without = (avoid,) if avoid else ()
        connected = grid.reachable(who, a, b, without)
        if connected != expected:
            if expected and avoid and not only:
                choice = f'在 {a} 到 {b} 之间留一条绕开 {avoid} 的{unit}路线。'
            elif expected:
                choice = f'把 {only or "两地之间的入口"} 接到两侧可走地面，移开挡路的主角或把起终点放到适合{unit}的地面。'
            elif order:
                choice = f'在 {rel["state"]} 状态扣住 {order} 命令。'
            else:
                choice = f'在 {a} 和 {b} 之间延长崖壁或岸线，封上这条{unit}能走的路。'
            return False, sentence, places, choice
        bypass = only and grid.reachable(who, a, b, (*without, only))
        return not bypass, sentence, places, f'封住绕开 {only} 的口子，让{unit}只能从那里通过。'
    if kind == '谁先到':
        a, b, goal, lead = rel['a'], rel['b'], rel['to'], rel['min_lead']
        left, right = (inf, inf) if pending else (grid.length(who, start, goal) for start in (a, b))
        return (isfinite(left) and isfinite(right) and right - left >= lead,
                f'{unit}从 {a} 去 {goal} 比从 {b} 至少近 {lead:g}', (a, b, goal),
                f'让两边都能到 {goal}，再把 {a} 的入口移近或让 {b} 的来路绕过一段界。')
    if kind == '绕多远':
        via, extra = rel['via'], rel['max_extra']
        best = inf if pending else grid.length(who, a, b)
        detour = inf if pending else grid.length(who, a, b, via)
        return (isfinite(detour) and detour - best <= extra,
                f'{unit}从 {a} 经 {via} 到 {b} 多走不超过 {extra:g}', (a, via, b),
                f'把 {via} 的出入口移向 {a} 到 {b} 的主通路，或移开绕路上的阻挡。')
    if kind == '罩住':
        road, by, fraction = rel['road'], rel['by'], rel['fraction']
        sense = '射程' if by == 'range' else '视野'
        return (not pending and grid.cover(point, road, by, fraction),
                f'{point} 的驻军楼{sense}罩住 {road} 的 {fraction:.0%}',
                (point, road), f'在 {point} 设可驻军的主角楼并朝 {road} 放近，或移开两者之间的遮挡。')
    if kind == '看得见':
        visible = rel['visible']
        start, end = grid.point(a), grid.point(b)
        return (not pending and grid.inside(start) and grid.inside(end) and grid.sight(start, end) == visible,
                f'从 {a} {"看得见" if visible else "看不见"} {b}', (a, b),
                f'调整 {a} 到 {b} 之间的高度档，或{"移开" if visible else "加入"}遮挡物。')
    side = rel['side']
    return (not pending and grid.room(point, side), f'{point} 有边长 {side:g} 的净平地', (point,),
            f'在 {point} 留一块同高的空地，移开侵入的主角，或把集结点移离岸线和坡肩。')


def _layout_dependencies(sketch, has_road_kit):
    road_edges = [edge for road in sketch.roads for edge in sketch.edges[road]]
    frontage = {block for edge in road_edges for block in sketch.sides[edge]}
    buildings = any('protagonist' in spec or (name in frontage and spec['use'] in TOWN)
                    for name, spec in sketch.blocks.items() if spec.get('kind') != 'water')
    bridges = has_road_kit and any(crosses_water(sketch, edge) for edge in road_edges)
    flanks = any('footpath' in cut for spec in sketch.borders.values() for cut in spec.get('segments', {}).values())
    return buildings, bridges, flanks


def _requires_layout(grid, rel, dependencies, has_road_kit):
    buildings, bridges, flanks = dependencies
    kind = rel['type']
    if kind == '罩住':
        return '需要布局：核对驻军楼和实路。'
    if kind == '看得见':
        # Buildings can obscure a clear ray, but cannot clear one blocked by terrain.
        if buildings and grid.sight(grid.point(rel['from']), grid.point(rel['to'])):
            return '需要布局：核对楼房对视线的遮挡。'
    elif kind == '放得下':
        if buildings:
            return '需要布局：核对楼房是否占用净地。'
    elif has_road_kit and any(rel.get(key) in grid.sketch.roads for key in ('via', 'only_via', 'without')):
        return '需要布局：核对实际道路所占的通行格。'
    elif rel['who'] != 'ship' and (buildings or bridges or flanks):
        return '需要布局：核对楼房、桥面或小径侧挡对通行的影响。'
    return ''


def evaluate(sketch, ground, roadbed, layout, border, frame, flank_shapes=(), *, sketch_only=False,
             has_road_kit=False):
    """Answer named orders and check open routes on the exported geometry."""
    if not sketch.relations:
        return {}
    grid = _Grid(sketch, ground, roadbed, layout, border, frame, flank_shapes)
    dependencies = _layout_dependencies(sketch, has_road_kit) if sketch_only else None
    answers = {}
    for name, relation in sketch.relations.items():
        state = relation.get('state', 'base')
        held = sketch.order_held(state, relation.get('order'))
        pending = ''
        if not held:
            if any(table[state] != table['base'] for table in (sketch.state_pass, sketch.state_heights, sketch.playable)):
                pending = f'先把 {state} 的过口、水位或可玩区变动展开成可检查的地图。'
            elif dependencies is not None:
                pending = _requires_layout(grid, relation, dependencies, has_road_kit)
        ok, sentence, places, decision = _answer(grid, relation, held, pending)
        if state != 'base':
            sentence = f'{state} 状态下，{sentence}'
        witness = None
        if not pending and not held and not ok and relation['type'] == '通不通' and relation.get('reachable', True):
            witness = grid.route_witness(relation)
            if witness is None and relation.get('only_via'):
                witness = grid.bypass_witness(relation)
            if witness:
                x, y = witness.at
                decision = f'{witness.place}（{x:g}, {y:g}）{witness.reason}。{decision}'
        status = 'pending' if pending else 'pass' if ok else 'fail'
        answers[name] = Answer(status, sentence, places, pending or ('' if ok else decision), witness)
    return answers


def draw_failures(sketch, answers, path):
    """Draw a named sketch followed by any failed relations and their exact cells."""
    failed = [(name, answer) for name, answer in answers.items() if answer.status == 'fail']
    all_points = [p for line in sketch.lines.values() for p in line]
    xmin, ymin = map(min, zip(*all_points))
    xmax, ymax = map(max, zip(*all_points))
    scale = min(540 / (xmax - xmin), 340 / (ymax - ymin))

    def xy(point):
        return 30 + (float(point[0]) - xmin) * scale, 122 + (ymax - float(point[1])) * scale

    def line(points, color, width):
        run = ' '.join(f'{x:.2f},{y:.2f}' for x, y in map(xy, points))
        return f'<polyline points="{run}" fill="none" stroke="{color}" stroke-width="{width}"/>'

    def text(x, y, label, color='#eee'):
        return f'<text x="{x:.2f}" y="{y:.2f}" fill="{color}">{escape(label)}</text>'

    backdrop = [line(run, '#86badd' if name in sketch.roads else '#81939b', 1)
                for name, run in sketch.lines.items()]
    height = (1 + len(failed)) * 480
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 {height}" '
           'font-family="sans-serif" font-size="15">',
           f'<rect width="640" height="{height}" fill="#23313a"/>']
    svg.extend([text(24, 26, '地图草图'), *backdrop])
    for border in sketch.borders:
        for a, b, _, _, section in sketch.border_sections(border):
            if sketch.base_pass.get(section):
                svg.append(line((a, b), '#f1bd69', 3))
    for name, place in (sketch.blocks | sketch.points).items():
        if 'at' in place:
            x, y = xy(place['at'])
            tooltip = f'<title>{escape(place.get("use", name))}</title>'
            svg.append(f'<g>{tooltip}{text(x + 5, y - 4, name)}</g>')
    for index, (name, answer) in enumerate(failed, 1):
        svg += [f'<g transform="translate(0 {index * 480})">',
                text(24, 26, f'{name} · {answer.sentence}'), *backdrop]
        for place in answer.place:
            if place in sketch.rings:
                svg.append(line(sketch.rings[place], '#f1bd69', 3))
            elif place in sketch.lines:
                svg.append(line(sketch.lines[place], '#f1bd69', 3))
            elif place not in sketch.points:
                border = place.split('.')[0]
                for a, b, _, _, section in sketch.border_sections(border):
                    if section == place:
                        svg.append(line((a, b), '#f1bd69', 3))
            spec = sketch.points.get(place, sketch.blocks.get(place, {}))
            if 'at' in spec:
                x, y = xy(spec['at'])
                svg += [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="#f1bd69"/>',
                        text(x + 7, y - 4, place, '#f1bd69')]
        if answer.witness:
            w = answer.witness
            x, y = xy(w.at)
            px, py = w.at
            svg += [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="8" fill="none" stroke="#ff7777" stroke-width="3" '
                    f'data-world-x="{px:g}" data-world-y="{py:g}"><title>{escape(w.place)} · '
                    f'{escape(w.reason)}</title></circle>']
        message = answer.decision
        svg += [text(24, 50 + 20 * k, message[i:i + 39], '#ffc3b3')
                for k, i in enumerate(range(0, len(message), 39))]
        svg.append('</g>')
    Path(path).write_text('\n'.join([*svg, '</svg>']), encoding='utf-8')
