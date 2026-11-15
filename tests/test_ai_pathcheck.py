"""PathfindingCheckType: a ground unit with no way to the target is not recruited (D round 152).

Builds: experimental/cnv/missions/aipathcheck_bench.py (no bridges; a SimpleAttack team aims at the player's yard
across the river), check checks/engine_aipathcheck.py. Bench fixtures tests/fixtures/d_pathcheck/<build>.txt:
's<t> live home across' (the counters from that second) and 'f<frame> team <n>' (the CNVStateGo team's members off
the CNVTeams log from that frame, -1 no team). Bench: not written / QuickDoesAttackPathExist / QuickDoesPathExist --
an empty team every ~90 frames that expires, the four Peacekeepers stay home; None -- all four in the team at f21,
out of the base by s6. The model (ra3model teams.TeamMaker.reach, simai.Brain.reach) drops the units with no way when
it recruits.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
OBSERVED = ROOT / 'tests/fixtures/d_pathcheck'
CHECKED = ('aipfdef', 'aipfatk', 'aipfpath')


def _bench(build):
    path = OBSERVED / (build + '.txt')
    if not path.exists():
        pytest.skip(f'{build} not benched yet')
    counters, team = [], []
    for x in path.read_text(encoding='utf-8').splitlines():
        if x.startswith('s'):
            t, *vals = x.split()
            counters.append((float(t[1:]), dict(zip(('live', 'home', 'across'), map(int, vals)))))
        elif x.startswith('f'):
            f, _, n = x.split()
            team.append((int(f[1:]), int(n)))
    return counters, team


def test_builds_differ_in_the_check_only():
    sys.path[:0] = [str(ROOT / 'experimental/cnv'), str(ROOT / 'experimental/campaign')]
    from missions import aipathcheck_bench as b
    xml = {k: f().assets[0][1] for k, f in b.MISSION.items()}
    for k, v in (('aipfatk', 'QuickDoesAttackPathExist'), ('aipfpath', 'QuickDoesPathExist'), ('aipfnone', 'None')):
        assert xml[k].replace(f' PathfindingCheckType="{v}"', '') == xml['aipfdef']


@pytest.mark.parametrize('build', CHECKED)
def test_bench_no_way_nobody_recruited(build):
    counters, team = _bench(build)
    assert all(r == {'live': 4, 'home': 4, 'across': 0} for _, r in counters)
    assert max(n for _, n in team) == 0                     # teams are made, never get a member
    made = [f for (f, n), (_, was) in zip(team[1:], team) if n == 0 and was == -1]
    # the first gap is shorter (f17 -> f95 on aipfdef); from then on one every 90 frames (the model: 91)
    assert len(made) >= 10 and all(85 <= b - a <= 95 for a, b in zip(made[1:], made[2:]))


def test_bench_none_recruits_and_goes():
    counters, team = _bench('aipfnone')
    assert max(n for _, n in team) == 4
    assert any(r['home'] == 0 and r['live'] == 4 and r['across'] == 0 for _, r in counters)


def _model(build):
    spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
    simai = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(simai)
    w = simai.run(build, 'a', until=40, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    return [dict(zip(labels, v)) for _, v in w.sim.series]


@pytest.mark.parametrize('build', ('aipfdef', 'aipfnone'))
def test_model_replays_the_bench_by_name(build):
    rows = _model(build)
    if build == 'aipfnone':
        assert rows[-1]['步兵在家'] == 0 and rows[-1]['步兵总数'] == 4
    else:
        assert all(r['步兵在家'] == 4 for r in rows)
