"""Lay a base-state v2 road network on expanded terrain, using retail fittings."""

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
import math

import numpy as np

from experimental.mapgen import design, terrain
from experimental.mapgen.campaign_writer import BRIDGE_DECK, bridge as bridge_ends, rules


PORT_TOLERANCE = 1.0  # Probe 5: matching retail socket centres, in world units.
CELL_MARGIN = terrain.CELL / math.sqrt(2)
ROAD_WIDTH = {'alley': 66.22, 'street': 85.48, 'avenue': 172.70}
STRAIGHTS = {'alley': ('HB_StreetSegment30', 50, None),
             'street': ('HV_StreetSegment09', 100, 'HV_StreetSegment17'),
             'avenue': ('HV_StreetSegment01', 100, None)}

# Heights and lengths are from HB_Bridge_02's BridgeBuilder, mesh and geometry.
# The 190-wide structure has a 120-wide walkable corridor (platmap).
BRIDGE_TEMPLATE, BRIDGE_WIDTH = 'HB_Bridge_02', 190
END_CAP, CENTER = 75, 150
UNDERSIDE = 27.46
BOAT_BEAM, BOAT_HEIGHT = 36, 20  # Hydrofoil's geometry in AlliedAntiAirShip.xml.


@dataclass(frozen=True)
class Port:
    xy: tuple
    heading: float  # outward, in radians


@dataclass(frozen=True)
class Placement:
    template: str
    x: float
    y: float
    angle: float
    ports: tuple = ()
    flags: int = 0
    side: str = 'civ'
    z: float = 0.


@dataclass(frozen=True)
class Bridge:
    road: str
    landings: tuple
    span: float
    deck_width: float
    deck_pass: frozenset
    water_pass: frozenset
    channel_width: float
    clearance: float


@dataclass(frozen=True)
class Roadbed:
    kit: str
    placements: tuple
    bridges: tuple
    paved: np.ndarray
    hidden: np.ndarray
    infill: np.ndarray


@dataclass(frozen=True)
class Fitting:
    template: str
    ports: tuple       # (x, y, outward angle in degrees) in model coordinates
    hub: tuple = (0, 0)
    path: tuple = ()   # intermediate centreline samples, in port order


def hv(number, ports, hub=(0, 0), path=()):
    return Fitting(f'HV_StreetSegment{number:02}', ports, hub, path)


WEST, EAST, NORTH, SOUTH = (-50, 0, 180), (50, 0, 0), (0, 50, 90), (0, -50, -90)
ARC = math.degrees(math.atan2(59.57 - 48.37, 37.22 + 48.26))
BENDS = {
    'alley': (Fitting('HB_StreetSegment25', ((-33.11, 0, 180), (0, 33.11, 90)),
                     path=((-9.70, 9.70),)),),
    'street': (
        hv(10, (WEST, NORTH), path=((-26.51, 5.88), (-14.60, 14.70), (-6.13, 26.01))),
        # End sections measured across the mesh. The longitudinal paint line
        # has a circle fit of R=267.90, but its final edges define the sockets.
        hv(19, ((-54.34, -5.52, 180 + ARC), (54.34, -5.52, -ARC)),
           (0, -5.52 + 54.34 * math.tan(math.radians(ARC))),
           ((-26.83, -1.60), (0, 0), (26.83, -1.60))),
    ),
    'avenue': (hv(6, ((0, -100, -90), (100, 0, 0)),
                  path=((7.61, -61.73), (29.29, -29.29), (61.73, -7.61))),),
}
JUNCTIONS = {
    ('alley', 3): Fitting('HB_StreetSegment24', ((0, -50, -90), (0, 50, 90), (-33.11, 0, 180)),
                          (-0.77, 0)),
    ('alley', 4): Fitting('HB_StreetSegment23', ((0, -50, -90), (0, 50, 90),
                                               (-33.11, 0, 180), (33.11, 0, 0)), (-0.77, 0)),
    ('street', 3): hv(15, (WEST, EAST, NORTH)),
    ('street', 4): Fitting('HB_StreetSegment19', (WEST, EAST, NORTH, SOUTH)),
    ('avenue', 3): hv(7, ((-100, 0, 180), (0, 100, 90), (0, -100, -90))),
    ('avenue', 4): hv(5, ((-100, 0, 180), (100, 0, 0), (0, 100, 90), (0, -100, -90))),
}
OFFSETS = (
    hv(13, ((-75, 25, 180), (75, -25, 0)),
       path=((-50.16, 22.55), (-26.28, 15.31), (0, 0), (26.28, -15.31), (50.16, -22.55))),
    hv(14, ((-75, -25, 180), (75, 25, 0)),
       path=((-50.16, -22.55), (-26.28, -15.31), (0, 0), (26.28, 15.31), (50.16, 22.55))),
)

# Tool profiles from Roads.xml. Sidewalks meet the outside of the model curb.
VERGES = {'Heidelberg_HB': ('StPetersburgSidewalk05', 15, ('HeidelbergBricksTrim01', 20)),
          'Havana_HV': ('HavanaSidewalk03', 15, ('HavanaSidewalk04', 5))}
SURFACES = {'alley': ('MtRushmoreRoad02', 40, (0,)),
            'street': ('MtRushmoreRoad01', 55, (0,)),
            # HV01 asphalt runs between offsets about 16.9 and 70.35.
            'avenue': ('MtRushmoreRoad01', 55, (-43.6, 43.6))}


def _add(a, b):
    return a[0] + b[0], a[1] + b[1]


def _scale(a, s):
    return a[0] * s, a[1] * s


def _unit(angle):
    return math.cos(angle), math.sin(angle)


def _heading(a, b):
    x, y = design.subtract(b, a)
    return math.atan2(y, x)


def _turn(a, b):
    return math.remainder(b - a, math.tau)


def _rotate(p, angle):
    x, y = p
    c, s = _unit(angle)
    return x * c - y * s, x * s + y * c


def _move(p, angle, distance):
    return _add(p, _scale(_unit(angle), distance))


def _place(fit, at, angle):
    origin = design.subtract(at, _rotate(fit.hub, angle))
    ports = tuple(Port(_add(origin, _rotate((x, y), angle)), math.radians(h) + angle)
                  for x, y, h in fit.ports)
    middle = tuple(_add(origin, _rotate(p, angle)) for p in fit.path)
    return Placement(fit.template, *origin, angle, ports), middle


def _error(road, point, detail):
    x, y = point
    raise design.DesignError(road, 'road_join', f'at ({float(x):g}, {float(y):g}): {detail}')


def _port_on_ray(port, a, b, width):
    heading = _heading(a, b)
    along, cross = _rotate(design.subtract(port.xy, a), -heading)
    return (-PORT_TOLERANCE <= along <= math.dist(a, b) + PORT_TOLERANCE
            and abs(cross) <= PORT_TOLERANCE
            and abs(math.sin(_turn(heading, port.heading) / 2)) * width <= PORT_TOLERANCE
            and math.cos(_turn(heading, port.heading)) > 0)


def _fit_node(fit, point, neighbors, width):
    if fit is None:
        return None
    for _, _, heading in fit.ports:
        angle = _heading(point, neighbors[0]) - math.radians(heading)
        piece, path = _place(fit, point, angle)
        matches = [tuple(b for b in neighbors if _port_on_ray(p, point, b, width)) for p in piece.ports]
        if all(len(row) == 1 for row in matches) and len({r[0] for r in matches}) == len(neighbors):
            return piece, path, tuple(r[0] for r in matches)
    return None


def _section(path, offset, headings=None):
    """Offset a polyline by intersecting the adjoining parallel lines."""
    angles = [_heading(a, b) for a, b in pairwise(path)]
    first, last = headings or (angles[0], angles[-1])
    for point, a, b in zip(path, [first, *angles], [*angles, last]):
        turn = _turn(a, b)
        yield _move(point, a + math.pi / 2 + turn / 2, offset / math.cos(turn / 2))


def _ribbon(path, width, headings=None):
    return (*_section(path, width / 2, headings), *reversed(tuple(_section(path, -width / 2, headings))))


class _Layout:
    def __init__(self, ground, border, kit):
        y, x = (np.indices(ground.raw.shape) - border) * terrain.CELL
        self.x, self.y = x, y
        self.ground = ground
        self.kit = kit
        self.objects = []
        self.bridges = []
        self.paved = np.zeros(x.shape, bool)
        self.models = np.zeros(x.shape, bool)
        self.infill = np.zeros(x.shape, bool)
        self.model_gaps = np.zeros(x.shape, bool)

    def region(self, points, mask):
        px, py = zip(*points)
        i = np.searchsorted(self.x[0], (min(px) - terrain.CELL, max(px) + terrain.CELL))
        j = np.searchsorted(self.y[:, 0], (min(py) - terrain.CELL, max(py) + terrain.CELL))
        window = np.s_[j[0]:j[1], i[0]:i[1]]
        local = terrain.polygon_mask(np.asarray(points, dtype=float), self.x[window], self.y[window])
        mask[window] |= local

    def covered(self, points):
        mask = np.zeros(self.x.shape, bool)
        self.region(points, mask)
        return mask

    def paint(self, points):
        self.region(points, self.paved)

    def dry_flat(self, points):
        mask = self.covered(points)
        g = self.ground
        z = g.raw[mask]
        return z.size and z.min() == z.max() and np.all(z > g.waterline[mask]) and not g.blocked[mask].any()

    def model(self, piece, polygon):
        self.objects.append(piece)
        self.region(polygon, self.models)

    def tool(self, template, path, width, *, hard=False):
        # Keep each pair consecutive in ObjectsList; common XY forms the bend.
        for i, (a, b) in enumerate(pairwise(path)):
            if math.dist(a, b) < 1e-6:
                continue
            self.paint(_ribbon((a, b), width))
            for p, flag in ((a, 2), (b, 4)):
                self.objects.append(Placement(template, *p, 0, flags=flag | (8 if hard else 0), side='road'))

    def verge(self, path, width, headings=None):
        name, size, (trim, trim_size) = VERGES[self.kit]
        for sign in (-1, 1):
            edge = width / 2
            for template, breadth in ((name, size), (trim, trim_size)):
                self.tool(template, tuple(_section(path, sign * (edge + breadth / 2), headings)),
                          breadth, hard=True)
                edge += breadth

    def finish(self):
        # A terrain quad can be hidden only if its four corners are covered.
        # Compute this after union so an internal model seam never leaves a band.
        model = np.pad(self.models, ((0, 1), (0, 1)))
        hidden = model[:-1, :-1] & model[1:, :-1] & model[:-1, 1:] & model[1:, 1:]
        hidden &= ~self.model_gaps  # a gap smaller than a quad can have four model-covered corners
        g = self.ground
        paved = (self.paved | self.models) & ~g.blocked & (g.raw > g.waterline)
        return Roadbed(self.kit, tuple(self.objects), tuple(self.bridges), paved, hidden, self.infill & paved)


def _junction_verges(layout, ports, width):
    name, sidewalk, (trim, trim_size) = VERGES[layout.kit]
    ordered = sorted(ports, key=lambda p: _turn(0, p.heading))
    for a, b in pairwise([*ordered, ordered[0]]):
        edge = width / 2
        for template, size in ((name, sidewalk), (trim, trim_size)):
            offset = edge + size / 2
            p = _move(a.xy, a.heading + math.pi / 2, offset)
            q = _move(b.xy, b.heading - math.pi / 2, offset)
            # Outer corners of the model are square, including the closed side of a T.
            axis = _unit(a.heading)
            gap = design.subtract(q, p)
            corner = _add(p, _scale(axis, sum(u * v for u, v in zip(axis, gap))))
            if abs(math.cos(_turn(a.heading, b.heading))) < PORT_TOLERANCE / width:
                layout.tool(template, (p, corner, q), size, hard=True)
            else:
                layout.tool(template, (p, q), size, hard=True)
            edge += size


def _fitting_shape(piece, path, width):
    if path:
        a, b = piece.ports
        headings = (a.heading + math.pi, b.heading)
        path = (a.xy, *path, b.xy)
        return _ribbon(path, width, headings), path, headings
    # All the selected junctions fill an axis-aligned rectangle in model space.
    # Their closed side and the sides of the port openings give its extents.
    ports = piece.ports
    corners = [_rotate(design.subtract(_move(p.xy, p.heading + sign * math.pi / 2, width / 2),
                                       (piece.x, piece.y)), -piece.angle)
               for p in ports for sign in (-1, 1)]
    lo, hi = (tuple(f(axis) for axis in zip(*corners)) for f in (min, max))
    box = ((lo[0], lo[1]), (hi[0], lo[1]), hi, (lo[0], hi[1]))
    return tuple(_add((piece.x, piece.y), _rotate(p, piece.angle)) for p in box), (), None


def _offset_fit(a, b, links, claimed):
    if any(len(links[p]) != 2 or p in claimed for p in (a, b)):
        return None
    u, = set(links[a]) - {b}
    v, = set(links[b]) - {a}
    angle = _heading(u, a)
    along, lateral = _rotate(design.subtract(b, a), -angle)
    if not 0 < along < 150:
        return None
    for fit in OFFSETS:
        delta = fit.ports[1][1] - fit.ports[0][1]
        if abs(lateral - delta) > PORT_TOLERANCE:
            continue
        pose = _add(design.midpoint(a, b), _rotate((0, (delta - lateral) / 2), angle))
        piece, path = _place(fit, pose, angle)
        if (_port_on_ray(piece.ports[0], a, u, ROAD_WIDTH['street']) and
                _port_on_ray(piece.ports[1], b, v, ROAD_WIDTH['street'])):
            return piece, path, ((a, u), (b, v))
    return None


def _bridge(layout, sketch, road, run, links, ends):
    a, b = run[0][0], run[-1][1]
    entry = [p for p in links[a] if p != run[0][1]]
    exit_ = [p for p in links[b] if p != run[-1][0]]
    if (len(entry) != 1 or len(exit_) != 1 or
            any(len(links[p]) != 2 for _, p in run[:-1]) or
            any(not design.on_segment(p, a, b) for edge in run for p in edge)):
        _error(road, a, 'bridge needs a straight crossing and one approach at each bank')
    u, = entry
    v, = exit_
    if not (design.on_segment(a, u, b) and design.on_segment(b, a, v)):
        _error(road, a, 'bridge approaches must continue the deck heading')
    passes = sketch.state_pass['base']
    declared = passes[road]
    for p in (a, b):
        for _, opening, left, right in sketch.contacts[p]:
            if left and right and sketch.medium(left) != sketch.medium(right):
                declared &= passes.get(opening, design.LAND)
    if declared != design.LAND:
        _error(road, a, f'{BRIDGE_TEMPLATE} carries {sorted(design.LAND)}; opening declares {sorted(declared)}')
    width = ROAD_WIDTH[sketch.roads[road]['width']]
    if width > BRIDGE_DECK:
        _error(road, a, f'road width {width:g} exceeds the {BRIDGE_DECK:g}-unit walkable bridge deck')
    wet_span = math.dist(a, b)
    span = 2 * END_CAP + max(1, math.ceil(wet_span / CENTER)) * CENTER
    inset = (span - wet_span) / 2
    angle = _heading(a, b)
    start, end = _move(a, angle, -inset), _move(b, angle, inset)
    for bank, approach, landing, heading in ((a, u, start, angle + math.pi), (b, v, end, angle)):
        port = Port(landing, heading)
        if not _port_on_ray(port, bank, approach, width):
            _error(road, bank, f'needs {inset:g} units of straight dry landing for a span of {span:g}')
        ends[bank, approach] = port
    g = layout.ground
    samples = []
    for landing in (start, end):
        pad = _ribbon((_move(landing, angle, -terrain.CELL), _move(landing, angle, terrain.CELL)), BRIDGE_WIDTH)
        if not layout.dry_flat(pad):
            _error(road, landing, 'bridge landing must be dry and flat across the structure')
        i = int(np.abs(layout.x[0] - landing[0]).argmin())
        j = int(np.abs(layout.y[:, 0] - landing[1]).argmin())
        samples.append(float(g.raw[j, i]))
    if samples[0] != samples[1]:
        _error(road, a, 'bridge landings must have the same height')
    c, s = _unit(angle)
    dx, dy = layout.x - start[0], layout.y - start[1]
    along, across = dx * c + dy * s, dy * c - dx * s
    deck = (along >= 0) & (along <= span) & (abs(across) <= BRIDGE_DECK / 2)
    wet = g.raw < g.waterline
    middle = deck & (abs(along - span / 2) <= BOAT_BEAM / 2 + CELL_MARGIN)
    # Use a strip through the whole deck plus a hull length at either end; the
    # recorded channel is the largest such centred clear-water band.
    boat_run = abs(across) <= BRIDGE_WIDTH / 2 + 30
    dry_offsets = abs(along[boat_run & ~wet] - span / 2)
    channel_width = 2 * max(0, float(dry_offsets.min(initial=wet_span / 2)) - CELL_MARGIN)
    if not middle.any() or not wet[middle].all() or channel_width < BOAT_BEAM:
        _error(road, a, 'river has no continuous boat channel below the centre span')
    surface = g.waterline[middle].max() / rules.RAW_PER_WORLD
    clearance = samples[0] / rules.RAW_PER_WORLD - surface - UNDERSIDE
    if clearance < BOAT_HEIGHT:
        _error(road, a, f'only {clearance:g} units of clearance below the deck; a Hydrofoil needs {BOAT_HEIGHT}')
    if (g.blocked[deck & ~wet]).any():
        _error(road, a, 'blocked dry cells on deck approaches')
    layout.bridges.append(Bridge(road, (start, end), span, BRIDGE_DECK,
                                 declared, design.WATER, channel_width, clearance))
    layout.objects.extend(Placement(BRIDGE_TEMPLATE, x, y, heading, flags=flag, side='neutral')
                          for x, y, heading, flag in bridge_ends(start, end))


def _straight_run(layout, road, a, b, start, end, tier, bends):
    p, q = start.xy, end.xy
    width = ROAD_WIDTH[tier]
    direction = _heading(a, b)
    length, skew = _rotate(design.subtract(q, p), -direction)
    if length < -PORT_TOLERANCE:
        _error(road, a, 'adjacent fittings overlap')
    if abs(length) <= PORT_TOLERANCE and abs(skew) <= PORT_TOLERANCE:
        if (math.dist(p, q) <= PORT_TOLERANCE
                and abs(math.sin(_turn(start.heading + math.pi, end.heading) / 2)) * width <= PORT_TOLERANCE):
            return
        _error(road, a, 'adjacent fittings miss each other outside port tolerance')
    heading = _heading(p, q)
    if not (_port_on_ray(start, p, q, width) and _port_on_ray(end, q, p, width)):
        _error(road, a, f'ports face away from straight run ending at {tuple(map(float, b))}')
    length = math.dist(p, q)
    polygon = _ribbon((p, q), width)
    core = layout.covered(_ribbon((p, q), terrain.CELL))
    g = layout.ground
    if np.any(core & (g.blocked | (g.raw <= g.waterline))):
        _error(road, a, f'run to {tuple(map(float, b))} meets blocked or submerged ground')
    layout.paint(polygon)

    def offset_end(point, offset, bend, other, starts):
        if bend not in bends:
            return _move(point, heading + math.pi / 2, offset)
        forward, bisector, miter = bends[bend]
        sign = 1 if (forward == other) == starts else -1
        return _move(bend, bisector + math.pi / 2, sign * miter * offset)

    def tool_line(template, size, offset, start, hard=False):
        layout.tool(template, (offset_end(start, offset, a, b, True),
                               offset_end(q, offset, b, a, False)), size, hard=hard)

    name, sidewalk, (trim, trim_size) = VERGES[layout.kit]
    for sign in (-1, 1):
        tool_line(name, sidewalk, sign * (width + sidewalk) / 2, p, hard=True)
        tool_line(trim, trim_size, sign * ((width + trim_size) / 2 + sidewalk), p, hard=True)
    straight, pitch, crosswalk = STRAIGHTS[tier]
    cursor = p
    while a not in bends and b not in bends:
        remaining = math.dist(cursor, q)
        if remaining < 50 - PORT_TOLERANCE:
            break
        size = pitch if remaining >= pitch - PORT_TOLERANCE else 50
        if size == 50 and pitch != 50 and not crosswalk:
            break
        other = _move(cursor, heading, size)
        shape = _ribbon((cursor, other), width)
        if not layout.dry_flat(shape):
            break
        template = straight if size == pitch else crosswalk
        # HV17 uses the western seam as origin. HV01 runs along local +y.
        origin = cursor if template == 'HV_StreetSegment17' else _move(cursor, heading, size / 2)
        angle = heading - (math.pi / 2 if tier == 'avenue' else 0)
        ports = (Port(cursor, heading + math.pi), Port(other, heading))
        layout.model(Placement(template, *origin, angle, ports), shape)
        cursor = other
        if remaining <= size + PORT_TOLERANCE:
            break
    if math.dist(cursor, q) > PORT_TOLERANCE:
        if layout.kit == 'Heidelberg_HB':
            # Continue the carriageway material under the end of each mesh.
            # Terrain interpolates between vertices, so a sub-cell seam still
            # needs a sample on both sides of the gap.
            _, breadth, offsets = SURFACES[tier]
            for offset in offsets:
                a1 = offset_end(cursor, offset, a, b, True)
                b1 = offset_end(q, offset, b, a, False)
                layout.region(_ribbon((_move(a1, heading, -CELL_MARGIN),
                                       _move(b1, heading, CELL_MARGIN)), breadth), layout.infill)
            # Field 4 addresses the quad at (i,j), not the sample vertex.
            # Unhide only quads whose footprint crosses the exposed span.
            half = terrain.CELL / 2
            pad = half * sum(map(abs, _unit(heading))) - 1e-5  # exclude boundary-only contact
            at = (_move(cursor, heading, -pad), _move(q, heading, pad))
            quad_origins = tuple(design.subtract(p, (half, half)) for p in _ribbon(at, width))
            layout.region(quad_origins, layout.model_gaps)
        else:
            name, size, offsets = SURFACES[tier]
            for offset in offsets:
                tool_line(name, size, offset, cursor)


def _frame_streets(sketch, links, layout, border):
    rim = {p for edge, sides in sketch.sides.items() if None in sides for p in edge}
    limit = tuple(axis[-1 - border] for axis in (layout.x[0], layout.y[:, 0]))
    for point in sorted(rim & links.keys()):
        adjacent = links[point]
        if len(adjacent) != 1:
            continue
        other, road = next(iter(adjacent.items()))
        heading = _heading(other, point)
        tier = sketch.roads[road]['width']
        end = point
        for distance in range(50, terrain.FRAME_MARGIN, 50):
            ahead = _move(point, heading, distance)
            if not all(0 <= p <= cap for p, cap in zip(ahead, limit)):
                break
            polygon = _ribbon((point, ahead), ROAD_WIDTH[tier])
            cells = layout.covered(polygon)
            if (layout.ground.owners[cells] < 0).any() or not layout.dry_flat(polygon):
                break
            end = ahead
        if end != point:
            _straight_run(layout, road, point, end, Port(point, heading), Port(end, heading + math.pi), tier, {})


def crosses_water(sketch, edge):
    """Whether this split road edge needs the bridge fitting pass."""
    sides = set(filter(None, sketch.sides[edge]))
    return bool(sides) and all(sketch.medium(block) == design.WATER for block in sides)


def expand(sketch, ground, border, kit):
    """Return native object placements and two ground masks for a validated v2 design."""
    if not sketch.roads:
        empty = np.zeros_like(ground.blocked)
        return Roadbed(kit, (), (), empty, empty.copy(), empty.copy())
    if kit not in VERGES:
        first = next(iter(sketch.roads))
        _error(first, sketch.lines[first][0], f'no measured street kit for {kit}')
    layout = _Layout(ground, border, kit)
    links = defaultdict(dict)
    for name in sketch.roads:
        for x, y in sketch.lines[name]:
            if not (layout.x[0, 0] <= x <= layout.x[0, -1] and layout.y[0, 0] <= y <= layout.y[-1, 0]):
                _error(name, (x, y), 'road lies outside expanded terrain')
        for a, b in sketch.edges[name]:
            links[a][b] = links[b][a] = name
    ends, used = {}, set()
    bridge_nodes = set()
    # Replace each consecutive wet run by one retail bridge, before fitting its land approaches.
    for name in sketch.roads:
        run = []
        for edge in [*sketch.edges[name], None]:
            if edge is not None and crosses_water(sketch, edge):
                run.append(edge)
                continue
            if run:
                _bridge(layout, sketch, name, run, links, ends)
                bridge_nodes.update(p for edge in run for p in edge)
                used.update(run)
                run = []

    fits = []
    claimed = set(bridge_nodes)
    tool_nodes = {}
    for name, spec in sketch.roads.items():
        if spec['width'] != 'street':
            continue
        for a, b in sketch.edges[name]:
            adjacent = (links[a], links[b])
            if any(sketch.roads[road]['width'] != 'street' for row in adjacent for road in row.values()):
                continue
            match = _offset_fit(a, b, links, claimed)
            if match:
                piece, middle, sockets = match
                polygon, path, headings = _fitting_shape(piece, middle, ROAD_WIDTH['street'])
                if layout.dry_flat(polygon):
                    fits.append((piece, sockets, polygon, path, headings, 'street', (a, b)))
                    claimed.update((a, b))

    for point, adjacent in links.items():
        if point in claimed or len(adjacent) == 1:
            continue
        road = min(adjacent.values())
        tier = sketch.roads[road]['width']
        neighbors = tuple(sorted(adjacent))
        degree = len(neighbors)
        if any(sketch.roads[name]['width'] != tier for name in adjacent.values()):
            _error(road, point, 'no measured fitting relates these different width tiers')
        if degree == 2:
            a, b = neighbors
            if design.on_segment(point, a, b):
                continue
            options = BENDS[tier]
        else:
            options = (JUNCTIONS.get((tier, degree)),)
        for fit in options:
            match = _fit_node(fit, point, neighbors, ROAD_WIDTH[tier])
            if match:
                piece, middle, tracks = match
                polygon, path, headings = _fitting_shape(piece, middle, ROAD_WIDTH[tier])
                if layout.dry_flat(polygon):
                    sockets = tuple((point, p) for p in tracks)
                    fits.append((piece, sockets, polygon, path, headings, tier, None))
                    break
        else:
            if degree != 2:
                _error(road, point, f'no flat {tier} fitting for these {degree} junction arms')
            a, b = neighbors
            turn = abs(_turn(_heading(a, point), _heading(point, b)))
            _, sidewalk, (_, trim) = VERGES[kit]
            setback = (ROAD_WIDTH[tier] / 2 + sidewalk + trim) * math.tan(turn / 2)
            if setback >= min(math.dist(a, point), math.dist(point, b)):
                _error(road, point, 'bend is too tight for the road and verges')
            tool_nodes[point] = (a, b)

    for piece, sockets, polygon, path, headings, tier, internal in fits:
        ends.update(zip(sockets, piece.ports))
        if internal:
            used.add(internal)
        layout.model(piece, polygon)
        if path:
            layout.verge(path, ROAD_WIDTH[tier], headings)
        else:
            _junction_verges(layout, piece.ports, ROAD_WIDTH[tier])

    # Each verge of a tool-only bend follows the same miter on both adjacent runs.
    for p, (a, b) in tool_nodes.items():
        heading, outgoing = _heading(a, p), _heading(p, b)
        half_turn = _turn(heading, outgoing) / 2
        bend_heading = heading + half_turn
        tool_nodes[p] = (b, bend_heading, 1 / math.cos(half_turn))

    for name, spec in sketch.roads.items():
        for a, b in sketch.edges[name]:
            if (a, b) not in used:
                heading = _heading(a, b)
                start = ends.get((a, b), Port(a, heading))
                end = ends.get((b, a), Port(b, heading + math.pi))
                _straight_run(layout, name, a, b, start, end, spec['width'], tool_nodes)
    _frame_streets(sketch, links, layout, border)
    return layout.finish()
