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


@pytest.mark.xfail(strict=True, reason='未对齐: past the wall the game goes one straight leg to the goal; the grid\'s '
                   'folded wall hides it from the anchor on the far edge and the way bends 37 off (handoff-r3 X step)')
def test_past_the_wall_one_straight_leg_to_the_goal(ground):
    """Bench: from just past the wall's end (about (900, 843)) the tank went one straight line to the goal."""
    goal = (500.0, 1050.0)
    way = [(500.0, 550.0)] + ground.route('ground', (500.0, 550.0), goal)
    past = [p for p in way if p[1] >= 820.0]          # from the anchor on the wall's far edge on
    assert max(_off(p, past[0], goal) for p in _dense(past)) <= 10.0
