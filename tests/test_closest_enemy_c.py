"""Named land ClosestToEnemy replay; work/re/c_closest_report.md.

Only the measured land slice is asserted. Water and refinery filtering are gaps.
"""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)


@pytest.fixture(scope='module')
def replay():
    if not simai.available():
        pytest.skip('no private AI model')
    w = simai.run('aiclosest', 'a', 61, lib=simai.model()['xmldata'].Library())
    rows = [(second, values) for second, values in w.sim.series if 55 <= second <= 60]
    assert len(rows) == 6
    return rows


@pytest.mark.parametrize('lane, expected', [
    (0, 4), (1, 4),
    pytest.param(2, 0, marks=pytest.mark.xfail(strict=True, reason=
        'Native non-defense host reaches enemy anchor, not predicted friendly plant. '
        'Same-frame strategic candidate/slot qualification unavailable; '
        'see work/re/c_closest_report.md and handoff-c.md.')),
    pytest.param(3, 0, marks=pytest.mark.xfail(strict=True, reason=
        'Native A05 host reaches enemy anchor, not predicted friendly plant. '
        'Same-frame strategic candidate/slot qualification unavailable; '
        'see work/re/c_closest_report.md and handoff-c.md.')),
])
def test_closest_enemy_land_named_bench_replay(replay, lane, expected):
    for second, values in replay:
        assert values[lane] == expected, (second, values)


def test_closest_enemy_original_readings():
    import json
    path = Path(simai.labpaths.WORK) / 're/c_closest_measured.json'
    if not path.exists():
        pytest.skip('private original readings unavailable')
    measured = json.loads(path.read_text(encoding='utf-8'))
    assert measured['build'] == 'aiclosest'
    for second in range(55, 61):
        assert measured['rows'][str(second)] == [4, 4, 0, 0]


def test_closest_enemy_teamlog_reads_unpadded_state_hash(monkeypatch):
    import teamlog
    monkeypatch.setattr(teamlog, '_hashed', lambda name: '019dcc78')
    names = teamlog._wants('CNVClosest0')
    assert teamlog._named({'names': ('Soviet_1', '19dcc78_StaticDefense_0_0')}, names)
    assert teamlog._named({'names': ('Soviet_1', '019dcc78_StaticDefense_0_0')}, names)
    assert not teamlog._named({'names': ('Soviet_1', '19dcc789_StaticDefense_0_0')}, names)
