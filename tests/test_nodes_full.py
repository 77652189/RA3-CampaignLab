"""B208: AllNearbyNodesFullHeuristic -- named replay of the ainf0 / ainf2 bench (checks/engine_ainodesfull.py).

Bench 2026-11-15 (run_queue, work/logs/b208_bench.log; counters 满态在家 / 常量在家 = the AllNearbyNodesFull state's
Peacekeepers / the constant state's Guardians at home):
  ainf0 (no refinery)        s1-s63 4 4, s73-s173 4 0   -- the Guardians leave, the Peacekeepers stay
  ainf2 (two refineries)     s1-s174 4 4, s194-s279 4 0 -- the Peacekeepers stay too: not 'full'
  ainf1 (one refinery)       s2-s273 4 4 .. s245 4 0 -- the Peacekeepers stay (B209, work/logs/b209_bench.log)
  ainf3 (ainf2 + 2 miners per refinery)  s1-s113 4 4, s116 0 3, s126 0 0 -- full: miners count (B209)
The simulator's rule (simai Brain.open_nodes: an own refinery within 300 serves its nearest node, INFERRED) says
ainf2 is full; the engine's per-node taken / capacity wrapper is unread.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')

LABELS = ('满态在家', '常量在家')


def _rows(build):
    w = simai.run(build, 'a', 120, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    return {second: dict(zip(labels, values)) for second, values in w.sim.series}


def test_open_nodes_keep_the_nodes_full_state_off():
    """ainf0: both east nodes open -> the Peacekeepers stay home, the control's Guardians leave (bench s73 on)."""
    rows = _rows('ainf0')
    assert tuple(rows[8][k] for k in LABELS) == (4, 4)
    for second in range(80, 120):
        assert tuple(rows[second][k] for k in LABELS) == (4, 0), second


@pytest.mark.xfail(strict=True, reason='bench ainf2: two refinery pads facing the two east nodes, the Peacekeepers '
                   'stay home to s279 (4) while the Guardians leave (s194 0); the simulator serves both nodes '
                   '(a refinery within 300, its nearest node) -> full -> 0 from s20. Bench ainf3 (two more miners '
                   'beside each refinery) fills them: it counts miners, threshold unread -- handoff-b 209')
def test_two_refineries_still_leave_a_node_open():
    rows = _rows('ainf2')
    for second in range(80, 120):
        assert rows[second]['满态在家'] == 4, second


def test_one_refinery_leaves_the_side_node_open():
    """ainf1 (bench B209, work/logs/b209_bench.log): one refinery on the field's pad -> s2-s273 the Peacekeepers stay
    home (4) while the Guardians leave (s245 0)."""
    rows = _rows('ainf1')
    for second in range(80, 120):
        assert rows[second]['满态在家'] == 4, second


def test_extra_miners_fill_the_nodes():
    """ainf3 = ainf2 + two AI Ore Collectors beside each refinery (bench B209): s116 the Peacekeepers leave with the
    Guardians (0 3, s126 on 0 0) -- 'full' counts miners (handoff-b 209, H1). The bench's late start (both groups
    sit to s113, also the control) is unexplained; the simulator leaves from s20, so only the end is asserted."""
    rows = _rows('ainf3')
    assert rows[119]['满态在家'] == 0
