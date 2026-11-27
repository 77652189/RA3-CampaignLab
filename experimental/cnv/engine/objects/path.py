"""L2 path straightening (ADR 0029, docs/engine/sim-layers.md; R3 step X, re-derived on the bench, ADR 0032 item 5):
a way found over a routing grid's cells (Ground.way / closest / within, below) to the straight legs a unit drives.

The rule, from the bench (2026-11-17 `engine_pull ways`, benches/movement/pathing/checks.py#engine_pull; CNVProbe tracks read by
work/re/scripts/x_pull.py): the shortest chain of straight legs through the way's cells, each leg crossing walkable
cells only (`clear`) -- a taut string. Readings: on open ground a Guardian and a Peacekeeper sent 800 east, 300 north
went one straight line (0.1 off it); sent round a field-0 wall's end, each went straight at the end (the tank 6.8 off
the line start -> end), passed it 0-1.2 from the wall (no clearance for its size), and from just past the end (about
(900, 843)) went one straight line to the goal. The bends are taken from the way's own cells (INFERRED: the bench
shows the legs, not how the game picks its corners). Before any pulling a way ran on the grid's rows: a goal moved 30
aside (HOLD_SPOTS) kept the unit on the next row the whole way, where the game goes in one slant line (a4's trucks 2
and 3 on the halt area's edges, 2026-11-09). Tests: tests/test_sim_pull.py.

Also the goal's spot (`spot`, R3 step X second part): where on the grid a ground unit sent to a point stops, kept off
the spots others hold. The rule, from the bench (2026-11-17 `engine_drop lanes`, `engine_dropring tens`,
benches/movement/pathing/checks.py#engine_drop; read by work/re/scripts/x_drop.py), units of one kind sent one after another to one point:
  - the point is snapped to the 20-unit grid by the unit's footprint, n = floor(2 r / 20 + 0.3) cells (a Guardian 2,
    a Peacekeeper 1): an even one to the nearest cell corner, an odd one to the centre of the cell the point is in --
    the first one sent stops there with nobody about (Guardians at (3000, 2000) and (3013, 3007) at (3001, 2001) and
    (3021, 3001); Peacekeepers at (3000, 4500) and (3600, 2800) at (3010, 4510) and (3610, 2810));
  - a held spot is one whose footprint square overlaps (side n cells, round its centre); then the first free one of
    rings k = 1, 2, ... of eight spots k footprints off, in the order east, north, west, north-east, north-west,
    south-west, south, south-east (world axes): ten Guardians from the west and ten Peacekeepers from the south both
    stood in exactly that order, the tanks 40 apart, the men 20 (not the two radii, 46.6 / 14), the tenth two
    footprints east; six Guardians from the north and six from the west the same as each other.
INFERRED: ring 2 past its first spot (only the tenth unit read), how far it searches (RINGS), a footprint's ground
read at its centre only, the bench's +1 on the tanks' spots (all of them, both axes; not modelled), and the rule for
units bigger than a Guardian or on water (a02's Akula subs, footprint 5: rings 100 apart; no bench yet). Tests:
tests/test_sim_spot.py.
"""
import math

import numpy as np

from engine.world.handle import GRID


def topple_blocks_ground(body):
    """Whether a topple prop qualifies for an infantry routing footprint."""
    # engine_topple b: infantry crosses OK_Lantern01. E266/E269 measured the fence controls;
    # treating other shaped CRUSHABLE_OBSTACLE props as infantry blockers is INFERRED.
    return body.template.lower() != 'ok_lantern01' and 'CRUSHABLE_OBSTACLE' in body.kinds and bool(body.radius)


class RouteGrid:
    """One map's open cells and endpoint results for one surface and obstacle version.

    This is derived data, not STATE. Ground owns the cache per map instance and clears it
    on obstacle changes and snapshot restore. Surface is the locomotor's only input to
    this grid: hull size and crush level affect movement elsewhere, not endpoint snapping.
    No unit size in the way either (bench 11-24 engine_paths size: a Guardian and an
    Apocalypse went straight through a 30 gap with a 150 one open nearby).
    """

    ENDPOINT_LIMIT = 32_768

    def __init__(self, grid, blocked):
        self.cells = grid & ~blocked
        self.endpoints = {}
        self.components = None

    def endpoint(self, cell):
        try:
            return self.endpoints[cell]
        except KeyError:
            result = open_cell(self.cells, cell)
            if len(self.endpoints) < self.ENDPOINT_LIMIT:
                self.endpoints[cell] = result
            return result

    def connected(self, a, z):
        if self.components is None:
            from scipy.ndimage import label
            # MCP_Geometric is fully connected by default: a diagonal can
            # pass between two blocked orthogonal neighbours.
            self.components, _ = label(self.cells, structure=np.ones((3, 3), bool))
        return bool(self.components[a] == self.components[z])


def route_grid(ground, surface):
    key = ('route grid', ground.version, surface)
    try:
        return ground.cache[key]
    except KeyError:
        grid = RouteGrid(ground.grids[surface], ground.shut(surface))
        ground.cache[key] = grid
        return grid


def can_way(ground, surface, p, q, closest=False):
    """Whether Ground.way returns a path, using exactly its snapped endpoints."""
    grid = route_grid(ground, surface)
    a, z = grid.endpoint(ground.cell(*p)), grid.endpoint(ground.cell(*q))
    # Ground.closest always has at least a itself to fall back to (an empty path).
    return a is not None and z is not None and (bool(closest) or a == z or grid.connected(a, z))


def amphibian_on_land(ground, p):
    """Test the raw start cell against terrain or deck, even on a factory footprint.

    The 'both' grid omits decks so swimmers cannot climb onto them. A unit already on land
    or a deck may still take the land route (aiskirm:et, rounds 205 and 239).
    """
    c, g = ground.cell(*p), ground.grids['ground']
    return 0 <= c[0] < g.shape[0] and 0 <= c[1] < g.shape[1] and bool(g[c] or ground.deck[c])


def can_route(ground, surface, p, q):
    """Whether Ground.route finds a way to q with closest=False."""
    return (surface == 'air' or ground.can_way(surface, p, q)
            or (surface == 'both' and amphibian_on_land(ground, p) and ground.can_way('ground', p, q)))


class Sight:
    """Which straight lines between a way's cells are clear, asked on a finer mask: `mask` walkable cells d to a
    way's cell a side (way cell c's point is mask cell c * d, as Ground.world puts it). Ground's routing cells are
    20 (GRID), each shut when any of its 10 map cells (CELL, the game's own pathfinding cell) is; a leg checked on the
    20 cells clips corners the 10 cells leave open -- aiaeson (11-18): the AI's tank leaving its yard, one 20 cell a
    cliff's corner shut by one of its four 10 cells, bent the first leg, its line ran 12 further from the player's
    power plant (353 from it against 341), out of its reach, and it drove on out of the 900 square where the bench's
    stays in it (B round 205; the old quarter-cell samples had missed the corner). A line is clear when it is on the
    way's own grid `g` or on the finer mask: only lines the folding shut are let through. The finer mask alone does
    not do: way cell c's point is its 2 x 2 block's corner sample, so a diagonal step down one axis crosses a third
    20 cell's sample -- shut, neighbours no longer saw each other (pull looped forever on retail maps) and a 45-degree
    run of cells bent (s01's #223, 11-18). INFERRED: a line clear on the grid but over a shut 10 cell is driven as
    before. g None: the mask is the way's own grid (d = 1)."""

    def __init__(self, mask, d=1, g=None):
        mask = np.ascontiguousarray(mask, bool)
        self.flat, self.w, self.d = mask.tobytes(), mask.shape[1], d
        g = None if g is None else np.ascontiguousarray(g, bool)
        self.gflat, self.gw = (None, None) if g is None else (g.tobytes(), g.shape[1])

    @classmethod
    def of(cls, grid, fine, blocked, fblocked):
        """For a way over `grid` (Ground's GRID cells of one surface) with `fine` its CELL cells unfolded;
        `blocked` / `fblocked` what stands in the way on each, every cell's own point inside a shape (`covered`).
        Not the GRID mask repeated onto the CELL cells: a GRID cell's 2 x 2 block lies north-east of its point, so a
        building's CELL footprint came out a cell further north and east than south and west -- engine_seal attack
        (11-18): the peacekeeper's two ways round the row's ends, mirror images, came out 5 apart, the south one the
        shorter, and fire_spot sent it round the south end; the bench's goes round the north (a tie goes north)."""
        d = fine.shape[0] // grid.shape[0]
        return cls(fine & ~fblocked, d, grid & ~blocked)

    def __call__(self, c0, c1):
        d = self.d
        if self.gflat is not None and sees(self.gflat, self.gw, c0, c1):
            return True
        return sees(self.flat, self.w, (c0[0] * d, c0[1] * d), (c1[0] * d, c1[1] * d))


def covered(shapes, x, y, side=0.0):
    """Cells whose point (x, y: world coordinates, x along axis 1 and y along axis 0, both rising) is inside any of
    `shapes`: (x, y, angle, length, thick[, centres]) a bar, or (x, y, r) a round building (Ground.set_blocks).
    Each shape is tested on the cells of its own bounding box only. A bar marked `centres` (a measured prop of BARS)
    thinner than the game's 10 cell (CELL) is tested on the centres of the CELL cells in each cell's `side` square
    north-east of its point instead (any one inside shuts it): bench 11-22 engine_block gn / gr, GV_Ring02 bars 5.3
    thick in a line on y = 800 left the way open (both 10), a line on a cell's edge misses both centres (795 / 805)
    -- on the points (on 800) it shut the way; three rows 5 apart (gd) went round. Other thin bars (a mission's own
    wall) keep the points (review vv #2: a 5.3 wall of ours on y = 800 is not walked through). INFERRED."""
    import platmap
    m = np.zeros(x.shape, bool)
    xs, ys = x[0], y[:, 0]
    for s in shapes:
        r = s[2] if len(s) == 3 else math.hypot(s[3], s[4]) / 2
        offs = (0.0,) if len(s) < 6 or not s[5] or s[4] >= platmap.CELL or not side else \
            np.arange(platmap.CELL / 2, side, platmap.CELL)
        j0, j1 = np.searchsorted(ys, s[1] - r - side), np.searchsorted(ys, s[1] + r, 'right')
        i0, i1 = np.searchsorted(xs, s[0] - r - side), np.searchsorted(xs, s[0] + r, 'right')
        for ox in offs:
            for oy in offs:
                bx, by = x[j0:j1, i0:i1] + ox - s[0], y[j0:j1, i0:i1] + oy - s[1]
                if len(s) == 3:
                    m[j0:j1, i0:i1] |= bx ** 2 + by ** 2 <= r ** 2
                else:
                    u, v = bx * math.cos(s[2]) + by * math.sin(s[2]), -bx * math.sin(s[2]) + by * math.cos(s[2])
                    m[j0:j1, i0:i1] |= (abs(u) <= s[3] / 2) & (abs(v) <= s[4] / 2)
    return m


def open_cell(g, c):
    """Cell c of grid g if walkable, else the nearest walkable one within 15 cells (None: none) -- a way's ends."""
    if 0 <= c[0] < g.shape[0] and 0 <= c[1] < g.shape[1] and g[c]:
        return c
    jj, ii = np.nonzero(g[max(0, c[0] - 15):c[0] + 16, max(0, c[1] - 15):c[1] + 16])
    if not len(jj):
        return None
    k = int(np.argmin((jj + max(0, c[0] - 15) - c[0]) ** 2 + (ii + max(0, c[1] - 15) - c[1]) ** 2))
    return (int(jj[k] + max(0, c[0] - 15)), int(ii[k] + max(0, c[1] - 15)))


def pull(g, cells):
    """A way's cells (`cells[0]` the start) over grid g (a Sight, or a mask: its own cells) to its legs: the cells
    after the start where it bends, and its last cell. Worked out in two passes: how far along the way each cell sees
    (from where the cell before it saw to: on while it sees, back while it does not), then the cheapest chain over
    legs within that sight, each leg checked. Sight that comes back after a cell it lost is not looked for: on random
    ways over five maps' grids (11-17) 1 way in 8 came out up to 4 cells longer than the very shortest chain, at a
    fifth of its cost."""
    cells = [(int(c[0]), int(c[1])) for c in cells]
    n = len(cells)
    if n < 2:
        return []
    see = g if isinstance(g, Sight) else Sight(g)
    if see(cells[0], cells[-1]):
        return [cells[-1]]
    reach, k = [0] * n, 1                   # reach[i]: the last cell along the way cells[i] sees
    for i in range(n - 1):
        k = max(k, i + 1)
        if see(cells[i], cells[k]):
            while k + 1 < n and see(cells[i], cells[k + 1]):
                k += 1
        else:
            k -= 1                          # the next cell (i + 1) always sees: they are neighbours
            while k > i + 1 and not see(cells[i], cells[k]):
                k -= 1
        reach[i] = k
    reach[n - 1] = n - 1
    reach = np.array(reach)
    r = np.array([c[0] for c in cells], float)
    q = np.array([c[1] for c in cells], float)
    best, back = np.zeros(n), [0] * n       # best[j]: the shortest chain start -> cells[j], back[j] its last bend
    for j in range(1, n):
        cost = best[:j] + np.hypot(r[j] - r[:j], q[j] - q[:j])
        cost[reach[:j] < j] = np.inf
        while True:
            # of equal costs the earliest: cells in one line cost the same in sums, and the last of them (rounding)
            # would bend the leg at each (s01's Yari on a diagonal, 11-17)
            i = int(np.flatnonzero(cost <= cost.min() + 1e-6)[0])
            if i == j - 1 or see(cells[i], cells[j]):
                break
            cost[i] = np.inf
        best[j], back[j] = cost[i], i
    out, j = [], n - 1
    while j:
        out.append(cells[j])
        j = back[j]
    return out[::-1]


def clear(g, c0, c1):
    """The straight line between the centres of cells c0 and c1 crosses walkable cells of g only: every cell whose
    inside it passes, in order (a line through a corner point only touches the two cells beside it, as a diagonal step
    of the way does). No margin: a leg may run along a wall's cells (engine_pull ways: the game's units passed a wall's
    end 0-1.2 from it). c0 itself is taken as walkable (the way's own cell)."""
    return sees(np.ascontiguousarray(g, bool).tobytes(), g.shape[1], c0, c1)


def sees(flat, w, c0, c1):
    """`clear` on g's cells as bytes, row after row, w a row (pull asks many lines of one grid)."""
    r, q = c0
    dr, dq = c1[0] - r, c1[1] - q
    major, minor = abs(dr), abs(dq)
    step_major, step_minor = w if dr > 0 else -w, 1 if dq > 0 else -1
    if major < minor:
        major, minor = minor, major
        step_major, step_minor = step_minor, step_major

    # Compare the next crossings at (2k + 1) / (2n) without division.
    # Keep the difference of their cross-products and update it after each crossing.
    diff = minor - major
    add_major, sub_minor = 2 * minor, 2 * major
    add_corner = add_major - sub_minor
    step_corner = step_major + step_minor
    offset = r * w + q
    # The major axis has the last crossing (possibly tied). An exhausted minor axis
    # has no crossing before it, so it needs no separate counter.
    while major:
        if diff < 0:
            offset += step_major
            diff += add_major
            major -= 1
        elif diff > 0:
            offset += step_minor
            diff -= sub_minor
        else:
            offset += step_corner
            diff += add_corner
            major -= 1
        if not flat[offset]:
            return False
    return True


RING = ((1, 0), (0, 1), (-1, 0), (1, 1), (-1, 1), (-1, -1), (0, -1), (1, -1))    # the bench's order round a spot
RINGS = 12                                                                         # INFERRED: how far it looks


def footprint(radius, grid):
    """Cells a side of a unit's footprint: floor(2 r / grid + 0.3), at least one."""
    return max(1, math.floor(2.0 * radius / grid + 0.3 + 1e-9))


def snap(p, n, grid):
    """`p` on the grid for a footprint of n cells: an even one to the nearest cell corner, an odd one to the centre
    of the cell it is in."""
    if n % 2 == 0:
        return (round(p[0] / grid) * grid, round(p[1] / grid) * grid)
    return (math.floor(p[0] / grid) * grid + grid / 2, math.floor(p[1] / grid) * grid + grid / 2)


def spot(want, radius, held, open_at, grid, on_grid=True):
    """Where a ground unit of `radius` sent to `want` stops (the module docstring's rule): `want` snapped to the grid
    by its footprint, or the first spot round that of the rings that is open_at(x, y) and overlaps no footprint square
    of `held` ((x, y, radius) each). None: none free within RINGS, or the snapped point not open. on_grid=False:
    `want` itself, not snapped, and the rings round it (INFERRED: the bench sent units to empty ground only; moves
    to a thing's place -- a waypoint leg, a building, a unit chased -- keep their exact point)."""
    n = footprint(radius, grid)
    p = snap(want, n, grid) if on_grid else (float(want[0]), float(want[1]))
    if not open_at(*p):
        return None
    side = n * grid
    squares = [(x, y, footprint(r, grid) * grid) for x, y, r in held]

    def free(q):
        return all(abs(q[0] - x) * 2 >= side + s or abs(q[1] - y) * 2 >= side + s for x, y, s in squares)
    if free(p):
        return p
    for k in range(1, RINGS + 1):
        for dx, dy in RING:
            q = (p[0] + dx * k * side, p[1] + dy * k * side)
            if free(q) and open_at(*q):
                return q
    return None


BLOCK = 40.0    # bench engine_column: an infantry group's rows and files stand 40 apart (two cells), every count


def block(starts, point):
    """Where each of a group of infantry sent to `point` as one team stands (the R3 step X third part), as unsnapped
    spots in the order of `starts` ((x, y) each); each is then a move's goal like any other (`spot`: snapped by the
    footprint). The rule, from the bench (2026-11-17 `engine_column lanes`, `engine_crowd big`, `engine_colgate two`,
    benches/movement/pathing/checks.py#engine_column; read by work/re/scripts/x_column.py), Peacekeepers sent by one MOVE_TEAM_TO:
      - any group of two or more, however near (two men, side by side or one behind the other, stood side by side 40
        apart; six sent 20 short of the point stood in the same block as six sent from 500);
      - ceil(sqrt(n)) files across (2, 3 -> 2, 6 -> 3, 10 -> 4, 16 -> 4), rows BLOCK back, files BLOCK apart, each row
        centred on the point (the last one too: 10 men 4 + 4 + 2, 3 men 2 + 1); the front row on the point, the rest
        behind it -- the group's middle short of the point (6 men: 20; a01's squad, 2026-11-08, ~18-23);
      - the block turned with the way in (from the north and from the south-west the same block, turned): every
        stop is point + the turned offset snapped to the centre of the cell it is in, the 45-degree lane included;
      - the men taken nearest the point first along the way in for the rows, and in each row by where they stand
        across it (right to left as they walk in) for the files;
      - the way in from the men's middle to the point: six men standing anyhow (no two level or abreast, their middle
        7 off the straight line in) stood man for man where this puts them, the slightly turned block snapped.
    INFERRED: the way in over a first leg round a wall (the bench's ground was open), which of two men level along or
    abreast goes first (the bench's blocks tie; kept in `starts`' order), and a group of infantry with vehicles (the
    vehicles keep order_group's offsets)."""
    n = len(starts)
    mx, my = sum(x for x, _ in starts) / n, sum(y for _, y in starts) / n
    ux, uy = point[0] - mx, point[1] - my
    d = math.hypot(ux, uy)
    ux, uy = (ux / d, uy / d) if d > 1e-6 else (1.0, 0.0)
    lx, ly = -uy, ux
    files = math.ceil(math.sqrt(n) - 1e-9)
    ahead = sorted(range(n), key=lambda k: -(starts[k][0] * ux + starts[k][1] * uy))
    out = [None] * n
    for row in range(0, n, files):
        men = sorted(ahead[row:row + files], key=lambda k: starts[k][0] * lx + starts[k][1] * ly)
        back = -(row // files) * BLOCK
        for i, k in enumerate(men):
            side = (i - (len(men) - 1) / 2) * BLOCK
            out[k] = (point[0] + back * ux + side * lx, point[1] + back * uy + side * ly)
    return out


def formation_spots(world, movers, p):
    """Where each of a group sent to `p` as one goes, before order_move keeps its goal off held spots
    (free_spot): [(body, (x, y))], nearest `p` first. The vehicles keep the group's shape: each goes to `p` plus where
    it stands from their middle (bench 11-21 engine_seqteam:t, A289: two tanks 612 apart sent 300 past the nearer one
    each drove ~600 and arrived together, neither in W2's 150 square -- not Generals' nearest-as-centre with the
    offset cut to 6 radii, which stood both on it); engine_acts_near's two 1600 apart both ended within 400 of the
    point: the offset is cut (SPREAD). INFERRED: the middle as the mean, the cut's size within its bracket, the
    line check from the goal to the spot. Two or more infantry stand in their block instead (`block`, bench
    2026-11-17 engine_column; bench engine_colgate: 2 men, and 6 sent 20 short, stand in the block too), first."""
    movers = sorted(movers, key=lambda b: (b.x - p[0]) ** 2 + (b.y - p[1]) ** 2)
    foot = [b for b in movers if 'INFANTRY' in b.kinds]
    out = []
    if len(foot) >= 2:
        world.used.add('column march')
        out = list(zip(foot, block([(b.x, b.y) for b in foot], p)))
        movers = [b for b in movers if b not in foot]
    if movers:
        mx, my = sum(b.x for b in movers) / len(movers), sum(b.y for b in movers) / len(movers)
        for b in movers:
            vx, vy = b.x - mx, b.y - my
            k = min(1.0, SPREAD * b.radius / (math.hypot(vx, vy) or 1.0))
            out.append((b, (p[0] + vx * k, p[1] + vy * k)))
    return out


SPREAD = 15     # a group member's offset from the middle is cut to this many radii: the benches put it between 13
#                 and 17 for Guardians (seqteam's 306 kept, both in at f254; engine_acts_near's 800 cut under 400)


HOLD_SPOTS = True              # every move's goal kept off other units' spots (claims): the game's (bench 11-09,
                               # a01's two infantry; benches/movement/pathing/checks.py#engine_spots, three trucks sent alone to one point)
BARS = {'GV_Ring02': {'length': 26.6892, 'thick': 5.32658, 'centres': True}}  # retail props in the way as their SDK box (Sim.blocks;
# the long axis along the facing, bench 11-22 engine_block gr), not platprops' 40 round; INFERRED for other props
ORE_PLATE = (60.0, 45.0)        # an ore node's base plate, half-extents (OreNode.xml's last BOX): goal_off_nodes


def claims(world, b, skip=()):
    """The spots other mobile ground units hold (x, y, radius): where they are going, or where they stand; none for
    aircraft in the air or for `skip`; none unless HOLD_SPOTS. free_spot (simpath.spot) keeps a move's goal off
    them (bench 2026-11-17 benches/movement/pathing/checks.py#engine_drop: allies sent one after another to one point stood in the rings'
    order, each off every one before it -- all of them there already; that a goal is held while its unit is
    still on its way is from engine_spots 'same' below). Benched 11-09: the rule is the game's (a01, two
    infantry sent alone to one point stood ~22 apart),
    and the game's a4 gets all trucks to the 80-wide halt area (checks/a4.py hold PASS). The simulator's trucks
    2 and 3, their goals moved 30 aside, ran on grid rows 40 off the road's middle the whole way, on the halt
    area's edges, and drove past it: its ways were not pulled straight (Ground.pull since; now 2854,2479 and
    2794,2521 at the halt at s315, like the switch off). On since bench 11-09 benches/movement/pathing/checks.py#engine_spots: three
    trucks on teams of their own sent to one point (at once, or 20 s apart) end one on it, two 10-80 off (the
    simulator 0 / 50 / 44.7). With it the a4 proxy's army stands apart, beats the second wave at x~1950 (off: all
    three trucks shot there at s232-240, lost at s248), the convoy halts alive, and the run goes to the clock:
    the proxy has no base-vehicle deploy, builds nothing and never takes 北营's command post (the level line's
    to-do, docs/story/handoff-phase4.md). j7 / a3's compiled plays ended 0.5-3.6 s off their own scripts
    (j7 126.9 vs 130.5): the script's 派 went straight to `send`, past this; it is order_move now, as its compiled
    ATTACK_MOVE_NAMED_UNIT_TO (test_playcheck). The script's 走 is a group move (order_group) but compiles to one
    MOVE_NAMED_UNIT_TO per unit -- no play has 走 for several units yet.
    Whose spots: an ally's (own units too) goal always; an enemy's or a neutral's only where it stands still and b
    cannot crush it -- a moving enemy's goal and a crushable one's spot are b's to take (INFERRED: no bench sent a
    unit onto an enemy's spot yet; the crush case is aicrush1's, below). Until 11-11 every unit's spot was held:
    aicrush1's first Crush move (benches/ai/tactics/checks.py#engine_aicrush, work/re/c_crush_path_report.md) had its goal, the
    guard's own spot, moved 31.6 aside, and the tank drove past the guard it was sent over."""
    if b.surface == 'air' or not HOLD_SPOTS:
        return []
    out = []
    for o in world.living():
        if o is b or o in skip or o.speed <= 0 or o.surface == 'air' or o.scenery:
            continue
        moving = bool(o.path and o.dest)
        if world.relation(b.owner, o.owner) != 'ALLIES' and (
                moving or (b.crusher is not None and o.crushable is not None and b.crusher > o.crushable)):
            continue
        out.append(tuple(o.dest if moving else (o.x, o.y)) + (o.radius,))
    return out


def goal_off_nodes(world, b, want):
    """A ground move's goal whose footprint touches an ore node's: the nearest goal clear of every node, on the
    pathfinder's GRID cells (D round 176). The footprint is simpath.footprint, floor(2 r / GRID + 0.3) cells, an
    even one round a cell corner, an odd one round a cell centre (bench 2026-11-17 benches/movement/pathing/checks.py#engine_drop: Guardians
    2 cells, Peacekeepers 1, snapped so); a node's is its base plate (OreNode.xml's 60 x 45 half-extent box, every other shape of it inside),
    turned with the node, and a cell touching it is shut. Bench aiexpb50n (only node 44 by the slot, D175): the
    miner sent to its slot (4215, 3039), 7 off the plate's edge, turned off its straight way 37 short and stood
    at (4221, 3061) -- this rule's (4220, 3060), the nearest corner whose four cells clear the plate. Not yet
    explained: aiexpb50 (node 45 too) stood at (4201, 3081), the rule's (4180, 3060)."""
    if b.surface == 'air' or 'ORE_NODE' in b.kinds:
        return want
    nodes = [(o.x, o.y, o.angle) for o in world.living() if 'ORE_NODE' in o.kinds]
    if not nodes:
        return want
    hx, hy = ORE_PLATE
    diam = max(1, math.floor(2 * b.radius / GRID + 0.3))
    m, off = diam * GRID / 2, 0.0 if diam % 2 == 0 else GRID / 2

    def clear(x, y):
        for nx, ny, a in nodes:
            u = (x - nx) * math.cos(a) + (y - ny) * math.sin(a)
            v = -(x - nx) * math.sin(a) + (y - ny) * math.cos(a)
            if abs(u) < hx + m and abs(v) < hy + m:
                return False
        return True
    if clear(*want):
        return want
    cx, cy = round((want[0] - off) / GRID), round((want[1] - off) / GRID)
    spots = [((cx + i) * GRID + off, (cy + j) * GRID + off) for i in range(-8, 9) for j in range(-8, 9)]
    spots = [s for s in spots if clear(*s) and world.ground.open(Ground.walks(b), *s)]
    if not spots:
        return want
    return min(spots, key=lambda s: (s[0] - want[0]) ** 2 + (s[1] - want[1]) ** 2)


def free_spot(world, b, want, held, on_grid=False):
    """simpath.spot (L2: the goal snapped to the grid by b's footprint, off the spots `held`; bench engine_drop):
    aircraft in the air, or no spot (none free, or `want` off its ground: the way finder's closest point decides,
    R7) -> `want`."""
    if b.surface == 'air':
        return want
    at = spot(want, b.radius, held, lambda x, y: world.ground.open(Ground.walks(b), x, y), GRID, on_grid)
    return want if at is None else at


class Ground:
    """The map's routing grids (GRID cells): ground (dry, not too steep, bridges over), water, both; paths by
    least cost, cached per surface and goal cell."""

    def __init__(self, mapmod):
        import platmap
        dims = getattr(mapmod, 'DIMS', platmap.CONTAINER)       # a retail map's own size (retail.Terrain)
        w, h, b = dims
        if hasattr(mapmod, 'LAYOUT'):
            e, _ = platmap.heights(mapmod.LAYOUT, w, h, b)
            walk = platmap.walkable(mapmod.LAYOUT, getattr(mapmod, 'OBJECTS', []), dims, e)
            bridge = walk & ~platmap.walkable(mapmod.LAYOUT, [], dims, e)    # walkable only for a bridge laid on it
        else:
            e = mapmod.ground().e
            import newmap
            walk = (e > getattr(mapmod, 'WATERLINE', newmap.WATERLINE) + 10) & (platmap.slope_of(e) <= platmap.STEEP)
            if hasattr(mapmod, 'impassable'):                   # a probe's field-0 cells (maps/probe_block.py)
                walk &= ~mapmod.impassable()
            bridge = np.zeros_like(walk)
        import newmap
        import terrain_rules
        waterline = getattr(mapmod, 'WATERLINE', newmap.WATERLINE)
        self.waterline = waterline
        # the water's logic edge in our height units (terrain_rules: 320 on our maps, not the routing's WATERLINE);
        # a retail map's (DIMS, retail.Terrain) own water height is not read (INFERRED: its WATERLINE)
        self.water = waterline if hasattr(mapmod, 'DIMS') else float(terrain_rules.ours(terrain_rules.WATER_WORLD))
        water = e < waterline - 5
        d = int(GRID // platmap.CELL)
        hh, ww = h // d, w // d
        fold = lambda a: a[:hh * d, :ww * d].reshape(hh, d, ww, d)            # noqa: E731
        self.b, self.d = b, d
        self.e = e                                                          # ground height (CELL cells)
        self.zgrid = e[:hh * d:d, :ww * d:d]                                # the same at each GRID cell's corner
        self.grids ={'ground': fold(walk).all(axis=(1, 3)), 'water': fold(water).all(axis=(1, 3))}
        # the shore's shallows (between the water's edge and 'dry'): platmap.apply blocks only steep ground, so an
        # amphibian goes ashore through them; left out they cut every slip (a5, 2026-11-04)
        shallow = (e >= waterline - 5) & (e <= waterline + 10) & (platmap.slope_of(e) <= platmap.STEEP)
        # R7: an amphibian does not take a bridge -- its deck is up over the water, it swims under (bench 2026-11-07
        # engine_land: the A4 transport went straight at the quay, 89 frames to the shore area, where the simulator
        # had it drive out of the water onto the southern bridge's deck and round, 346)
        land = walk & ~bridge
        self.grids['both'] = (fold(land).all(axis=(1, 3)) | self.grids['water'] |
                              fold(land | water | shallow).all(axis=(1, 3)))
        self.fine = {k: a[:hh * d, :ww * d] for k, a in (('ground', walk), ('water', water), ('both', land | water | shallow))}
        # 'foot', infantry's ground: its cells, shut also by what only infantry goes round (set_blocks' foot)
        self.grids['foot'], self.fine['foot'] = self.grids['ground'], self.fine['ground']
        self.cache, self.borders = {}, tuple(getattr(mapmod, 'BORDERS', {}).values())    # borders: (x0, y0, x1, y1)
        self.blocked = self.foot = np.zeros(self.grids['ground'].shape, bool)
        self.placed = self.blocked          # what a new structure's placement sees as taken (set_blocks' place)
        self.version = 0
        # a bridge's deck: what stands on it blocks nobody (bench 2026-10-27, reroute: the warriors walked through an
        # ice wall on the deck)
        self.deck = np.zeros_like(self.blocked)
        objs = list(getattr(mapmod, 'OBJECTS', []))
        jj, ii = np.mgrid[0:self.blocked.shape[0], 0:self.blocked.shape[1]]
        self.xy, self.shapes, self.foot_shapes = self.world((jj, ii)), [], []
        for o, q in zip(objs, objs[1:]):
            if getattr(o, 'flags', None) == platmap.BRIDGE_START and getattr(q, 'flags', None) == platmap.BRIDGE_END:
                self.deck |= self.strip((o.x, o.y), (q.x, q.y), platmap.BRIDGE_DECK, 0.0)

    def strip(self, p, q, width, over):
        """Cells within width / 2 of segment p-q, the segment `over` longer at both ends."""
        x, y = self.xy
        dx, dy = q[0] - p[0], q[1] - p[1]
        n = max(math.hypot(dx, dy), 1e-6)
        ux, uy = dx / n, dy / n
        u = (x - p[0]) * ux + (y - p[1]) * uy
        v = -(x - p[0]) * uy + (y - p[1]) * ux
        return (u >= -over) & (u <= n + over) & (abs(v) <= width / 2)

    def set_blocks(self, shapes, place=None, foot=()):
        """What stands in the way now: [(x, y, angle, length, thick) a bar, or (x, y, r) a round building]; off a
        bridge's deck. Routes are worked out anew. place: the shapes a structure's placement sees (open(place=True)),
        None = the same. foot: what stands in the way of surface 'foot' (infantry) only."""
        m = self._mask(shapes)
        f = m | self._mask(foot) if foot else m
        self.placed = m if place is None else self._mask(place)
        if (m != self.blocked).any() or (f != self.foot).any():
            self.blocked, self.foot, self.version, self.cache = m, f, self.version + 1, {}
            self.shapes, self.foot_shapes = list(shapes), list(shapes) + list(foot)
            return True
        return False

    @staticmethod
    def walks(b):
        """The surface b's ways are found on: infantry's ground is 'foot' (set_blocks' foot, E256 engine_a1toll)."""
        return 'foot' if b.surface == 'ground' and 'INFANTRY' in b.kinds else b.surface

    def shut(self, surface):
        """The routing cells shut now for that surface."""
        return self.foot if surface == 'foot' else self.blocked

    def _mask(self, shapes):
        return covered(shapes, *self.xy, GRID) & ~self.deck

    def open(self, surface, x, y, place=False):
        """A world point a unit of that surface may stand on now (its routing cell walkable and not blocked); place:
        a structure's placement's view (set_blocks' place)."""
        if surface == 'air':
            return True
        c, g = self.cell(x, y), self.grids[surface]
        return (0 <= c[0] < g.shape[0] and 0 <= c[1] < g.shape[1] and bool(g[c])
                and not (self.placed if place else self.shut(surface))[c])

    def stand(self, surface, x, y):
        """A ground unit may stand in the CELL cell [x, x + CELL) x [y, y + CELL): its four corners dry (as 'ground'
        walk) and within STEEP of each other, and not blocked now -- the engine's own 10-cell test of a knocked
        body's landing (Physics P3, bench 11-11 engine_knock_water far: (2500, 3280) at the top of the far bank's
        slope is standable, which the 20 routing cell round it is not). Other surfaces: open()."""
        import platmap
        if surface != 'ground':
            return self.open(surface, x, y)
        corners, free = self.corners(x, y)
        return bool(corners is not None and corners.min() > self.waterline + 10 and
                    corners.max() - corners.min() <= platmap.STEEP and free)

    KNOCK_SEARCH = 15               # lattice steps the nearest-standable search reaches (INFERRED: the search routine is unread, work/re/handoff.md)

    def landing(self, x, y, surface=None):
        """Physics P3 (bench 11-11 engine_knock_water, work/re/a_physics_plan.md): where a body knocked to (x, y) comes
        down -- (x, y, moved), or None when no cell within KNOCK_SEARCH steps of 20 will do. A man (`surface`: his) on
        a landing he cannot stand on (water, a cliff) goes to the nearest one he can, not back along the line: man
        2220 -> 2080 on his bank, far 2420 -> 2500 the far bank's top. A vehicle (None; ra3ext.log `build ... land=`)
        lands on the men's 20 grid point + 10 in x and y (2460.5 -> 2470, 3338.5 -> 3330; all nine landings), one it
        cannot land on (stand_vehicle: the water) on the nearest it can on that lattice (tank: 2410 in the trench ->
        2490 on the far bank's slope; the lattice INFERRED -- the 10 grid gives the same); whether it drowns: drowns."""
        if surface is None:
            x, y, ok = math.floor(x / 20) * 20 + 10, math.floor(y / 20) * 20 + 10, self.stand_vehicle
        else:
            ok = lambda px, py: self.stand(surface, px, py)
        if ok(x, y):
            return x, y, False
        step, best = 20.0, None
        for j in range(-self.KNOCK_SEARCH, self.KNOCK_SEARCH + 1):
            for i in range(-self.KNOCK_SEARCH, self.KNOCK_SEARCH + 1):
                px, py = x + i * step, y + j * step
                d = math.hypot(px - x, py - y)
                if (best is None or d < best[0]) and ok(px, py):
                    best = (d, px, py)
        return None if best is None else (best[1], best[2], True)

    def corners(self, x, y):
        """(the four corner heights of the CELL cell [x, x + CELL) x [y, y + CELL) or None off the map, not blocked now)."""
        import platmap
        j, i = math.floor(y / platmap.CELL + self.b), math.floor(x / platmap.CELL + self.b)
        if not (0 <= j < self.e.shape[0] - 1 and 0 <= i < self.e.shape[1] - 1):
            return None, False
        c = self.cell(x, y)
        free = not (0 <= c[0] < self.blocked.shape[0] and 0 <= c[1] < self.blocked.shape[1]) or not self.blocked[c]
        return self.e[j:j + 2, i:i + 2], free

    def stand_vehicle(self, x, y):
        """A knocked vehicle may land in the CELL cell at (x, y): its four corners over the water, no slope limit
        (Physics P3, bench 11-11 engine_knock_water tank: the landing in the trench went to (2490, 3330), the bank's
        slope cell 325 / 340 ours, 15 a cell -- not 2470 (295 / 310) nor 2480 (310 / 325); the threshold between 310
        and 325 is INFERRED as the water itself), and not blocked now."""
        corners, free = self.corners(x, y)
        return bool(corners is not None and corners.min() > self.water and free)

    def drowns(self, x, y):
        """A knocked vehicle landing in the CELL cell at (x, y) is gone the frame it lands: a corner within 10 of the
        water (bench 11-11 engine_knock_water: tank's 2490, 5 over, dies; edge's 2510, 20 over, and ramp's 2470 on a
        dry slope, 65 over, live -- so not the slope, not a footprint round the cell; the 10 is INFERRED, the men's
        stand margin)."""
        corners, _ = self.corners(x, y)
        return corners is None or bool(corners.min() <= self.water + 10)

    def z_smooth(self, x, y):
        """The ground's height at a world point, bilinear between the CELL corners (a curve's terrain test)."""
        import platmap
        fy, fx = y / platmap.CELL + self.b, x / platmap.CELL + self.b
        j = min(max(math.floor(fy), 0), self.e.shape[0] - 2)
        i = min(max(math.floor(fx), 0), self.e.shape[1] - 2)
        v, u = min(max(fy - j, 0.0), 1.0), min(max(fx - i, 0.0), 1.0)
        q = self.e[j:j + 2, i:i + 2]
        return float((q[0, 0] * (1 - u) + q[0, 1] * u) * (1 - v) + (q[1, 0] * (1 - u) + q[1, 1] * u) * v)

    def cell(self, x, y):
        import platmap
        return (int(round((y / platmap.CELL + self.b) / self.d)), int(round((x / platmap.CELL + self.b) / self.d)))

    def shore(self, x, y, water):
        """GRID x the length from (x, y)'s cell to the nearest cell of the other kind (water for one on land, not water
        afloat), the AI's CloseToShore distance (the game's disc of cells, work/re b1127_shore.md); inf with none.
        INFERRED: the 'water' grid stands for the game's water / deep water cell types."""
        key = ('shore', bool(water))
        if key not in self.cache:
            from scipy.ndimage import distance_transform_edt
            a = self.grids['water'] == bool(water)          # nonzero: of its own kind, measured to the nearest other
            self.cache[key] = distance_transform_edt(a) * GRID if (~a).any() else np.full(a.shape, np.inf)
        j, i = self.cell(x, y)
        a = self.cache[key]
        return float(a[j, i]) if 0 <= j < a.shape[0] and 0 <= i < a.shape[1] else math.inf

    def z(self, x, y):
        """The ground's height at a world point (the nearest CELL)."""
        import platmap
        j = min(max(int(round(y / platmap.CELL + self.b)), 0), self.e.shape[0] - 1)
        i = min(max(int(round(x / platmap.CELL + self.b)), 0), self.e.shape[1] - 1)
        return float(self.e[j, i])

    def world(self, c):
        import platmap
        return ((c[1] * self.d - self.b) * platmap.CELL, (c[0] * self.d - self.b) * platmap.CELL)

    def can_way(self, surface, p, q, closest=False):
        """Whether way() would return a path, including an empty closest path."""
        return can_way(self, surface, p, q, closest)

    def can_route(self, surface, p, q):
        return can_route(self, surface, p, q)

    def route(self, surface, p, q, closest=False):
        """World points from p to q (None: no way); aircraft fly straight. closest: no way to q -- the way to the
        nearest point it can reach instead (a unit's move, R7; the static checks ask for q itself)."""
        if surface == 'air':
            return [q]
        got = self.way(surface, p, q, False)
        if got is None and surface == 'both' and amphibian_on_land(self, p):
            # R7: try the dry route before settling for the closest point on the amphibious grid.
            # Round 205: the engineer out of the barracks at (4067,3562) took the closest way and stopped at
            # (2900,3280) without reaching the derrick. Round 239: the periodic path check kicked it off the
            # team at s165 on the deck at (2929,2952). On the bench it walked on and captured the derrick at s222.
            got = self.way('ground', p, q, False)
        if got is None and closest:
            got = self.way(surface, p, q, True)
        return got

    def way(self, surface, p, q, closest):
        from skimage import graph
        grid = route_grid(self, surface)
        a, z = grid.endpoint(self.cell(*p)), grid.endpoint(self.cell(*q))
        if a is None or z is None:
            return None
        key = (surface, z)
        if key not in self.cache:
            m = graph.MCP_Geometric(np.where(grid.cells, 1.0, np.inf))
            cost, _ = m.find_costs([z])
            self.cache[key] = (m, cost)
        m, cost = self.cache[key]
        if not np.isfinite(cost[a]):
            return self.closest(grid.cells, a, z, surface) if closest else None
        legs = ('legs', surface, a, z)              # the same way asked again (an AI's path checks: 23670 asks,
        if legs not in self.cache:                  # 320 ways in simrecord's ai_open); set_blocks clears the cache
            cells = m.traceback(a)[::-1]            # traceback runs from the goal (the costs' source) to a
            self.cache[legs] = pull(self.sight(surface), cells)
        pts = [self.world(c) for c in self.cache[legs]]
        if pts and math.hypot(pts[-1][0] - q[0], pts[-1][1] - q[1]) <= GRID:
            pts.pop()                               # the goal's own cell: q itself ends the way
        return pts + [q]

    def sight(self, surface):
        """Sight.of `surface`'s grid and CELL cells now (the shapes on each cell's own point; a deck's CELL
        cells its GRID cell's, INFERRED); cached until set_blocks."""
        if ('sight', surface) not in self.cache:
            import platmap
            fine, d = self.fine[surface], self.d
            jj, ii = np.mgrid[0:fine.shape[0], 0:fine.shape[1]]
            fb = covered(self.foot_shapes if surface == 'foot' else self.shapes, (ii - self.b) * platmap.CELL,
                         (jj - self.b) * platmap.CELL, platmap.CELL)
            fb &= ~self.deck.repeat(d, 0).repeat(d, 1)
            self.cache['sight', surface] = Sight.of(self.grids[surface], fine, self.shut(surface), fb)
        return self.cache['sight', surface]

    def closest(self, g, a, z, surface):
        """R7: the goal out of reach -- the way to the cell it can reach nearest the goal (bench 2026-11-07
        engine_land: the A4 transport sent to the quay's top went straight to its foot and stayed; the Generals
        pathfinder's closest path; bench 2026-11-08 engine_seal move: a peacekeeper walled in, sent 600 out, walked
        to the wall's inside nearest the goal and stood). [] when that is where it stands: it stays (not stuck)."""
        from skimage import graph
        m = graph.MCP_Geometric(np.where(g, 1.0, np.inf))
        cost, _ = m.find_costs([a])
        jj, ii = np.nonzero(np.isfinite(cost))
        k = int(np.argmin((jj - z[0]) ** 2 + (ii - z[1]) ** 2))
        end = (int(jj[k]), int(ii[k]))
        if end == tuple(a):
            return []
        return [self.world(c) for c in pull(self.sight(surface), m.traceback(end))] or [self.world(end)]

    def within(self, surface, p, q, reach):
        """R3: an attacker's way -- to the cell it reaches soonest from which q is within `reach` (Generals' attack
        path: the way to a spot in range, not to the target; bench 2026-11-07 a4 smash: the Ghost King at the ice wall
        12 s after landing, not round the wall to its far side). [] when p is in range already, None when no cell is."""
        import platmap
        if math.hypot(q[0] - p[0], q[1] - p[1]) <= reach:
            return []
        if surface == 'air':
            return [q]
        from skimage import graph
        grid = route_grid(self, surface)
        a = grid.endpoint(self.cell(*p))
        if a is None:
            return None
        m = graph.MCP_Geometric(np.where(grid.cells, 1.0, np.inf))
        cost, _ = m.find_costs([a])
        jj, ii = np.nonzero(np.isfinite(cost))
        x = (ii * self.d - self.b) * platmap.CELL
        y = (jj * self.d - self.b) * platmap.CELL
        ok = np.hypot(x - q[0], y - q[1]) <= reach
        if not ok.any():
            return None
        k = int(np.flatnonzero(ok)[np.argmin(cost[jj[ok], ii[ok]])])
        end = (int(jj[k]), int(ii[k]))
        return [self.world(c) for c in pull(self.sight(surface), m.traceback(end))] or [self.world(end)]
