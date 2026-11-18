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
"""
import math

import numpy as np


def pull(g, cells):
    """A way's cells (`cells[0]` the start) over grid g to its legs: the cells after the start where it bends, and
    its last cell. Worked out in two passes: how far along the way each cell sees (from where the cell before it saw
    to: on while it sees, back while it does not), then the cheapest chain over legs within that sight, each leg
    checked. Sight that comes back after a cell it lost is not looked for: on random ways over five maps' grids
    (11-17) 1 way in 8 came out up to 4 cells longer than the very shortest chain, at a fifth of its cost."""
    cells = [(int(c[0]), int(c[1])) for c in cells]
    n = len(cells)
    if n < 2:
        return []
    flat, w = np.ascontiguousarray(g, bool).tobytes(), g.shape[1]
    if sees(flat, w, cells[0], cells[-1]):
        return [cells[-1]]
    reach, k = [0] * n, 1                   # reach[i]: the last cell along the way cells[i] sees
    for i in range(n - 1):
        k = max(k, i + 1)
        if sees(flat, w, cells[i], cells[k]):
            while k + 1 < n and sees(flat, w, cells[i], cells[k + 1]):
                k += 1
        else:
            k -= 1                          # the next cell (i + 1) always sees: they are neighbours
            while k > i + 1 and not sees(flat, w, cells[i], cells[k]):
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
            if i == j - 1 or sees(flat, w, cells[i], cells[j]):
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
