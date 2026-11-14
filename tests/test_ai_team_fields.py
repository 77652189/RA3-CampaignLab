"""GatherWaypoint, MaxTypesOfUnits, Priority=HOTSPOT: each pair's on / off effect, bench and model (D round 148).

Builds: experimental/cnv/missions/aiteamfields_bench.py, check checks/engine_aiteamfields.py (counter readings in its
docstring). Bench fixtures tests/fixtures/d_teamfields/<build>.txt keep the counter series (one 's<t> v1 v2 v3' a
change).
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
OBSERVED = ROOT / 'tests/fixtures/d_teamfields'


def _model(build, until=72):
    w = simai.run(build, 'a', until=until, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    return [(t, dict(zip(labels, values))) for t, values in w.sim.series]


def _bench(build):
    path = OBSERVED / (build + '.txt')
    if not path.exists():       # D148: aimaxty3 / aihot* hit a full C: drive (OSError 28), not benched yet
        pytest.skip(f'{build} not benched yet')
    lines = [x for x in path.read_text(encoding='utf-8').splitlines() if x and not x.startswith('#')]
    labels = lines[0].split()
    rows = []
    for x in lines[1:]:
        t, *vals = x.split()
        rows.append((float(t.lstrip('s')), dict(zip(labels, (int(v) for v in vals)))))
    return rows


def _ever(rows, label, n=1):
    return any(r[label] >= n for _, r in rows)


def _at(rows, second):
    return [r for t, r in rows if t <= second][-1]


def test_pairs_differ_in_one_field_only():
    sys.path[:0] = [str(ROOT / 'experimental/cnv'), str(ROOT / 'experimental/campaign')]
    from missions import aiteamfields_bench as b
    xml = {k: f().assets[0][1] for k, f in b.MISSION.items()}
    assert xml['aigathwp'].replace(' GatherWaypoint="CNV AI WP Target"', '') == xml['aigathno']
    assert xml['aigathbad'].replace(' GatherWaypoint="CNV AI WP Nowhere"', '') == xml['aigathno']
    # the personality id ends in the mod name's last letter (aiteamfilter_bench: PID + name[-1])
    assert xml['aimaxty1'].replace('MaxTypesOfUnits="1"', 'MaxTypesOfUnits="3"').replace('CNVTeamF1', 'CNVTeamF3') \
        == xml['aimaxty3']
    assert xml['aihotdef'].replace('Priority="DEFAULT"', 'Priority="HOTSPOT"') == xml['aihotstd']
    assert xml['aihotscr'].replace('Priority="SCRIPTED"', 'Priority="STANDARD"') == xml['aihotstd']


def _gather_effect(rows, gathered):
    assert _ever(rows, '到远厂'), rows
    if gathered:
        first_wp = min(t for t, r in rows if r['到路点'] >= 2)
        first_far = min(t for t, r in rows if r['到远厂'] >= 1)
        assert first_wp < first_far, (first_wp, first_far)
    else:
        assert not _ever(rows, '到路点'), rows


def _types_effect(rows, n):
    home = _at(rows, 40)
    gone = [k for k in ('坦克在家', '步兵在家', '标枪在家') if home[k] == 0]
    assert len(gone) == (1 if n == 1 else 3), home
    assert all(home[k] == 2 for k in home if k not in gone), home


def _release_effect(rows, released):
    assert _ever(rows, '到目标') == released, rows


CASES = [('aigathwp', _gather_effect, True), ('aigathno', _gather_effect, False), ('aigathbad', _gather_effect, False),
         ('aimaxty1', _types_effect, 1), ('aimaxty3', _types_effect, 3),
         ('aihotstd', _release_effect, True), ('aihotdef', _release_effect, False),
         ('aihotscr', _release_effect, True)]


@pytest.mark.parametrize('build,effect,arg', CASES)
def test_bench(build, effect, arg):
    effect(_bench(build), arg)


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.parametrize('build,effect,arg', CASES)
def test_model(build, effect, arg):
    effect(_model(build), arg)
