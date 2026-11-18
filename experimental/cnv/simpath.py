"""L2 path straightening (ADR 0029, docs/engine/sim-layers.md; R3 step X, re-derived on the bench, ADR 0032 item 5):
a way found over a routing grid's cells (sim.Ground.way / closest / within) to the straight legs a unit drives.

The rule, from the bench (2026-11-17 `engine_pull ways`, checks/engine_pull.py; CNVProbe tracks read by
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
checks/engine_drop.py; read by work/re/scripts/x_drop.py), units of one kind sent one after another to one point:
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


class Sight:
    """Which straight lines between a way's cells are clear, asked on a finer mask: `mask` walkable cells d to a
    way's cell a side (way cell c's point is mask cell c * d, as sim.Ground.world puts it). Ground's routing cells are
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
    def of(cls, grid, fine, blocked):
        """For a way over `grid` (sim.Ground's GRID cells of one surface) with `fine` its CELL cells unfolded and
        `blocked` what stands in the way (GRID cells, as the way sees it on both)."""
        d = fine.shape[0] // grid.shape[0]
        return cls(fine & ~blocked.repeat(d, 0).repeat(d, 1), d, grid & ~blocked)

    def __call__(self, c0, c1):
        d = self.d
        if self.gflat is not None and sees(self.gflat, self.gw, c0, c1):
            return True
        return sees(self.flat, self.w, (c0[0] * d, c0[1] * d), (c1[0] * d, c1[1] * d))


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
    sr, sq = (dr > 0) - (dr < 0), (dq > 0) - (dq < 0)
    nr, nq = abs(dr), abs(dq)
    i = j = 0                       # row and column lines crossed; the k-th at t = (2k + 1) / (2n) along the line
    while i < nr or j < nq:
        a, b = (2 * i + 1) * nq, (2 * j + 1) * nr       # compare the next crossings' t without division
        if j >= nq or (i < nr and a < b):
            r, i = r + sr, i + 1
        elif i >= nr or b < a:
            q, j = q + sq, j + 1
        else:                                           # through a corner point
            r, q, i, j = r + sr, q + sq, i + 1, j + 1
        if not flat[r * w + q]:
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
    checks/engine_column.py; read by work/re/scripts/x_column.py), Peacekeepers sent by one MOVE_TEAM_TO:
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
