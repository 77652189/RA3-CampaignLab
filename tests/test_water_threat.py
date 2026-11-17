"""Named ThreatToWater replay and original counters; work/re/c_water_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)

CASES = [('aiwaterdist', (4, 0, 0)), ('aiwaterthreat', (4, 0, 0)),
         ('aiwaternear', (4, 0, 0)), ('aiwaterfar', (0, 4, 0))]


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build, expected', [
    pytest.param(build, expected, marks=pytest.mark.xfail(strict=True, reason=
        'Bench ThreatToWater went near (4/0/0); model goes far. Actual water threat '
        'and sample/candidate eligibility missing; see work/re/c_water_report.md and handoff-c.md.'))
    if build == 'aiwaterthreat' else (build, expected) for build, expected in CASES
])
def test_water_threat_named_bench_replay(build, expected):
    w = simai.run(build, 'a', until=41)
    rows = [tuple(v) for second, v in w.sim.series if 40 <= second <= 41]
    assert rows and all(row == expected for row in rows), rows


@pytest.mark.parametrize('build, expected', CASES)
def test_water_threat_original_readings(build, expected):
    path = Path(simai.labpaths.WORK) / 're/c_water_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[build]
    rows = evidence['rows']
    before = max((r for r in rows if r[0] <= 40), key=lambda r: r[0])
    after = min((r for r in rows if r[0] >= 40), key=lambda r: r[0])
    assert all(tuple(r[2]) == expected for r in (before, after))


@pytest.mark.parametrize('build', [
    'aiwaterdist',
    pytest.param('aiwaterthreat', marks=pytest.mark.xfail(strict=True, reason=
        'Original prediction far was contradicted by near counters; water threat baseline missing. '
        'See work/re/c_water_report.md and handoff-c.md; original verdict retained.')),
    pytest.param('aiwaternear', marks=pytest.mark.xfail(strict=True, reason=
        'Original sampler missed s40..41; raw verdict is FAIL despite stable 4/0/0. '
        'See work/re/c_water_report.md and handoff-c.md; do not relabel raw verdict.')),
    'aiwaterfar',
])
def test_water_threat_original_verdict(build):
    path = Path(simai.labpaths.WORK) / 're/c_water_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[build]
    assert evidence['verdict'] == 'PASS', evidence['result']['expectations']
