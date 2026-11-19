"""The peak-load benchmark's guard (ADR 0034 item 10, docs/engine/sim-modules.md 9.3; experimental/cnv/simbench_peak.py):
one world, a skirmish's busiest stretch (two bases, 300 units a side in a fight, the factories working), 60 simulated
seconds. Slow (a couple of minutes): listed in tests/replay_tests.txt, so only the full run takes it.

The hard requirement is faster than real time at the peak: the slowest 10 s slice (the first, while both armies are
whole; the whole run's multiple flatters it as they thin out). The simulator is not there yet (B0 11-17: WORST), so
that test is a strict xfail and turns red (XPASS) the day it gets there -- then drop the mark. Until then the baseline ratchet keeps
a step from making it much slower: the run is one, on a shared machine, so its margin is wide (a 10 % step is for
simrecord's `time` and the benchmark run by hand, before and after)."""
import json
import sys

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simbench_peak  # noqa: E402
import simloop  # noqa: E402
import simsmall  # noqa: E402

BASELINE = 1.13         # the whole run's simulated / wall seconds at 016c411a (B0 11-17; raise it as steps speed up)
WORST = 0.45            # the slowest 10 s then (the first): the peak, the one under real time
MARGIN = 0.75           # one run on a shared machine: red below 75 % of the baseline


@pytest.fixture(scope='module')
def peak():
    return simbench_peak.run()


def test_the_scene_is_a_peak(peak):
    """What it measures is what it says: armies of hundreds, both losing units in the fight, the factories making."""
    assert peak['units'] >= 200 and peak['secs'] == simbench_peak.SECS
    assert all(peak['units'] * 0.2 < n < peak['units'] for n in peak['alive'].values()), peak['alive']
    assert peak['made'] > 0
    assert peak['cells'] and set(peak['cells']) == set(simloop.FRAME)


def test_the_peak_keeps_to_its_baseline(peak):
    assert peak['multiple'] >= BASELINE * MARGIN, peak


@pytest.mark.xfail(strict=True, reason='B0 11-17: the slowest 10 s (the first, both armies whole) runs slower than '
                                       'real time (WORST); the refactor\'s sleeping modules and no every-frame sweeps '
                                       'are to get it there (ADR 0034)')
def test_the_peak_runs_faster_than_real_time(peak):
    assert peak['worst'] > 1.0, peak


def test_ai_cli_passes_secs_and_writes_ai_result(monkeypatch, tmp_path, capsys):
    result = {'rev': 'abc', 'secs': 2, 'model': True, 'wall': 1, 'multiple': 2, 'worst': 2, 'slices': [2],
              'bodies': 3, 'made': 1, 'alive': {}, 'cells': {}, 'inside': {}, 'ms_frame': 33.333}

    def run_ai(secs):
        assert secs == 2
        return result

    monkeypatch.setattr(simbench_peak, 'run_ai', run_ai)
    monkeypatch.setattr(sys, 'argv', ['simbench_peak.py', '--ai', '--secs', '2', '--out', str(tmp_path)])

    assert simbench_peak.main() == 0
    assert json.loads((tmp_path / 'peak_ai_abc.json').read_text(encoding='utf-8')) == result
    assert 'aiskrand/s, 33.33 ms/frame' in capsys.readouterr().out


def test_timed_cells_run_the_same_frame():
    """simloop.timed: the same cells in the same order, each clocked; a tick through them leaves the world as the
    plain loop does."""
    units = [('a', 'AlliedAntiInfantryInfantry', 'Player_1', 2000.0, 2300.0),
             ('s', 'SovietAntiInfantryInfantry', 'Soviet_1', 2150.0, 2300.0)]
    plain, timed = simsmall.small_world(units, model=False), simsmall.small_world(units, model=False)
    totals = {}
    cells = simloop.timed(totals)
    assert [c.__name__ for c in cells] == ['run'] * len(simloop.FRAME)
    for _ in range(20):
        simloop.step(plain)
        simloop.step(timed, cells)
        plain.t = timed.t = round(plain.t + simloop.DT, 3)
    assert set(totals) == set(simloop.FRAME)
    for name in ('a', 's'):
        p, t = plain.bodies[name], timed.bodies[name]
        assert (p.x, p.y, p.hp) == (t.x, t.y, t.hp)
