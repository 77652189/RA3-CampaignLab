"""B208: AllNearbyNodesFullHeuristic -- named replay of the ainf0 / ainf2 bench (checks/engine_ainodesfull.py).

Bench 2026-11-15 (run_queue, work/logs/b208_bench.log; counters 满态在家 / 常量在家 = the AllNearbyNodesFull state's
Peacekeepers / the constant state's Guardians at home):
  ainf0 (no refinery)        s1-s63 4 4, s73-s173 4 0   -- the Guardians leave, the Peacekeepers stay
  ainf2 (two refineries)     s1-s174 4 4, s194-s279 4 0 -- the Peacekeepers stay too: not 'full'
  ainf1 (one refinery)       s2-s273 4 4 .. s245 4 0 -- the Peacekeepers stay (B209, work/logs/b209_bench.log)
  ainf3 (ainf2 + 2 miners per refinery)  s1-s113 4 4, s116 0 3, s126 0 0 -- full: miners count (B209)
  ainf4 (ainf2 + 1 miner per refinery)   s1-s69 4 4, s80-s184 4 0 -- not full (B210, work/logs/b210_bench.log)
  ainf5 (ainf1 + 2 miners)               s1-s68 4 4, s76-s168 4 0 -- the side node stays open (B210)
A placed refinery brings its own collector, so a refinery's node holds 1 / 2 / 3 collectors on ainf2 / ainf4 / ainf3:
full at 3 (simai NODE_MINERS, INFERRED the engine's per-node taken / capacity wrapper, unread; the simulator pools the
collectors over the served nodes).
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')

LABELS = ('满态在家', '常量在家')


def _rows(build):
    w = simai_run.run(build, 'a', 120, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    return {second: dict(zip(labels, values)) for second, values in w.sim.series}


def test_open_nodes_keep_the_nodes_full_state_off():
    """ainf0: both east nodes open -> the Peacekeepers stay home, the control's Guardians leave (bench s73 on)."""
    rows = _rows('ainf0')
    assert tuple(rows[8][k] for k in LABELS) == (4, 4)
    for second in range(80, 120):
        assert tuple(rows[second][k] for k in LABELS) == (4, 0), second


@pytest.mark.parametrize('build', ['ainf2', 'ainf4', 'ainf5'])
def test_too_few_miners_leave_a_node_open(build):
    """Bench ainf2 (s1-s279 4), ainf4 (s1-s184 4), ainf5 (s1-s168 4): the Peacekeepers stay home -- one or two
    collectors a refinery (ainf2 / ainf4), or three at one refinery with the side node unserved (ainf5)."""
    rows = _rows(build)
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
