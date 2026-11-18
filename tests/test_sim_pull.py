"""R3 step X, path straightening (sim.Ground.pull / clear) against the bench: `engine_pull ways` 2026-11-17
(experimental/cnv/checks/engine_pull.py; CNVProbe tracks read by work/re/scripts/x_pull.py), on the blocked-way probe
map the simulator reads too (maps/probe_block.py: a field-0 wall x 300..900, y 780..820, the way round at its east
end)."""
import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simbench.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simbench', ROOT / 'experimental' / 'cnv' / 'simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)
import sim  # noqa: E402
from maps import probe_block  # noqa: E402

WALL = (300.0, 780.0, 900.0, 820.0)


@pytest.fixture(scope='module')
def ground():
    return sim.Ground(probe_block)


def _off(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / math.hypot(dx, dy)


def _dense(pts, step=5.0):
    out = [pts[0]]
    for p, q in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) // step))
        out += [(p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n) for k in range(1, n + 1)]
    return out


def _to_wall(p):
    x0, y0, x1, y1 = WALL
    return math.hypot(p[0] - min(max(p[0], x0), x1), p[1] - min(max(p[1], y0), y1))


@pytest.mark.parametrize('start', [(3900.0, 1550.0), (3900.0, 1950.0)])
def test_open_ground_is_one_straight_leg(ground, start):
    """Bench: the Guardian and the Peacekeeper sent 800 east, 300 north on open ground went 0.1 off one straight line."""
    goal = (start[0] + 800.0, start[1] + 300.0)
    assert ground.route('ground', start, goal) == [goal]


@pytest.mark.parametrize('start', [(500.0, 550.0), (440.0, 550.0)])
def test_round_a_wall_straight_at_its_end_and_close_by(ground, start):
    """Bench: round the wall's east end each went straight at the end (the tank 6.8 off the line start -> end, the
    man 4.3) and passed it 0-1.2 from the wall: no clearance for its size."""
    way = [start] + ground.route('ground', start, (500.0, 1050.0))
    pts = _dense(way)
    near = min(pts, key=_to_wall)
    assert _to_wall(near) <= 2.0
    first = pts[:pts.index(near) + 1]
    assert max(_off(p, start, near) for p in first) <= 10.0


@pytest.mark.parametrize('start', [(500.0, 550.0), (480.0, 360.0)])
def test_no_bend_on_a_straight_run(ground, start):
    """A bend only where the way turns: (480, 360) comes down a 45-degree run of cells to the wall's corner (equal
    costs along it once bent each cell of a Yari's diagonal in s01's record, 11-17)."""
    way = [start] + ground.route('ground', start, (500.0, 1050.0))
    for a, b, c in zip(way, way[1:], way[2:]):
        assert _off(b, a, c) > 1.0, (a, b, c)


def test_past_the_wall_one_straight_leg_to_the_goal(ground):
    """Bench: from just past the wall's end (about (900, 843)) the tank went one straight line to the goal (before
    the 11-17 rewrite the simulator bent 37 off at (640, 1000): its farthest-seen anchors stopped on the wall's far
    edge, from where the goal is hidden)."""
    goal = (500.0, 1050.0)
    way = [(500.0, 550.0)] + ground.route('ground', (500.0, 550.0), goal)
    past = [p for p in way if p[1] >= 820.0]          # from the anchor on the wall's far edge on
    assert max(_off(p, past[0], goal) for p in _dense(past)) <= 10.0


def test_legs_are_checked_on_the_ten_cells():
    """aiaeson (11-18, B round 205): a 20 cell shut by one of its four 10 cells (a cliff's corner) bent the AI tank's
    first leg out of its yard; its line then passed 12 further from the player's power plant, out of reach, and it
    drove on out of the 900 square the bench's stays in. On the 10 cells (the game's own) the corner is open."""
    import numpy as np
    import simpath
    fine = np.ones((12, 12), bool)
    fine[7, 4] = False                              # one 10 cell of the 20 cell (3, 2)
    grid = fine.reshape(6, 2, 6, 2).all(axis=(1, 3))
    cells = [(5, 5), (4, 4), (3, 3), (2, 2), (2, 1), (1, 0)]
    assert not simpath.clear(grid, (5, 5), (1, 0))  # the folded grid hides the end
    assert simpath.pull(simpath.Sight(fine, 2, grid), cells) == [(1, 0)]


def test_a_diagonal_run_past_a_shut_corner_sample_is_one_leg():
    """On the 10 cells a 45-degree run down one axis crosses a third 20 cell's corner sample; shut, the run is still
    one leg, as on the grid (the 10 cells alone: pull looped forever on retail maps, and s01's #223 bent on its
    diagonal, 11-18). Run with a timeout: the loop does not end."""
    import numpy as np
    import simpath
    fine = np.ones((8, 8), bool)
    fine[3, 1] = False                              # crossed going from (1, 1) to (2, 0); the 20 cell (1, 0) shut
    grid = fine.reshape(4, 2, 4, 2).all(axis=(1, 3))
    assert simpath.pull(simpath.Sight(fine, 2, grid), [(0, 2), (1, 1), (2, 0)]) == [(2, 0)]
