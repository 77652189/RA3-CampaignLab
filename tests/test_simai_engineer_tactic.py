"""AlliedCaptureTech_MEDIUM's Engineer tactic on stock aiskirm, check et (line A round 203).

Bench 2026-11-13 (work/bench_results/aiskirm__et.json, head 7020cbfc, PASS), counters 工程队 / 油井 / 到油井 / 到矿点:
s1-s127 99 0 0 0 | s128-s143 0 0 0 0 | s144-s215 1 0 0 0 | s216-s221 1 0 1 0 | s222 0 1 0 0 | s223-s284 99 1 0 0.
The team (by its engine name ..._EngineerTactic_0_0) appears empty at s128, takes its engineer at s144, walks it to
the map's one derrick (s216), the derrick is s1's at s222 and the team is gone that second; never at the ore node.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'experimental/cnv'), str(ROOT / 'experimental/campaign')]
import simai  # noqa: E402

WAKE = 11.0                         # the first simulator second the counters are written (missions.aiskirm_bench)


@pytest.fixture(scope='module')
def rows():
    w = simai.run('aiskirm', 'et', until=float(os.environ.get('CNV_ET_UNTIL', 230)),
                  lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    return [(t, dict(zip(labels, values))) for t, values in w.sim.series]


def _first(rows, label, value, after=0.0):
    return next((t for t, r in rows if t >= after and r[label] == value), None)


def test_the_engineer_team_is_read_by_its_engine_name(rows):
    """Bench: absent (99) to s127, empty from s128, one member from s144 (the engineer). The simulator's counters
    start at the wake (s11; before it they hold 0), so the readings are taken from WAKE on. Model fca219e: 0 at
    s131, 1 at s145."""
    made = _first(rows, '工程队', 0, after=WAKE)
    joined = _first(rows, '工程队', 1, after=WAKE)
    assert made is not None and 125 <= made <= 132, made
    assert joined is not None and 141 <= joined <= 147, joined
    assert all(r['工程队'] == 99 for t, r in rows if WAKE <= t < 125)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'Pinned model: ClosestTechBuildingHeuristic takes the nearest neutral STRUCTURE (an OreNode, IMMUNE_TO_CAPTURE), '
    'nothing is captured. Model branch a204-tech-filter (registered tech set) + Brain.act + the land fallback on the '
    'terrain (line A round 205): at the derrick s230, the derrick s1\'s s236, the team gone s236 -- 14 s late. The '
    'simulator walks by land round the north (~3970 long); 72 s at the engineer\'s ~47/s is the straight line '
    '(3386): the game swims, the \'both\' grid has no way off this shore (INFERRED, line A handoff).'))
def test_the_engineer_captures_the_derrick(rows):
    """Bench: at the derrick s216, the derrick s1's s222 and the team gone that second; never at the ore node."""
    assert all(r['到矿点'] == 0 for _, r in rows)
    at = _first(rows, '到油井', 1)
    owned = _first(rows, '油井', 1)
    assert at is not None and 210 <= at <= 222, at
    assert owned is not None and 216 <= owned <= 228, owned
    assert all(r['工程队'] == 99 for t, r in rows if t >= owned + 1)
