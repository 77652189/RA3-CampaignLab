"""Named native-status filter replay; work/re/c_vital_report.md.

Only the script-controlled ATTACHED slice matched. Ground samples did not keep
AIRBORNE_TARGET on the engine, and lane zero has overlapping count areas.
"""
from functools import lru_cache
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)


@lru_cache(maxsize=2)
def replay(build):
    if not simai.available():
        pytest.skip('no private AI model')
    w = simai.run(build, 'a', 61, lib=simai.model()['xmldata'].Library())
    rows = [(second, values) for second, values in w.sim.series if 55 <= second <= 60]
    assert len(rows) == 6
    return rows


AIR_GAP = pytest.mark.xfail(strict=True, reason=
    'Engine ground samples never retain AIRBORNE_TARGET; model retains it and '
    'recruits teams. No native flying/landing control; see work/re/c_vital_report.md '
    'and handoff-c.md. This does not establish target-filter behavior.')
AREA_GAP = pytest.mark.xfail(strict=True, reason=
    'Native lane zero reads two at goal and four at home in overlapping regions, '
    'model zero/four; exact same-frame positions unavailable. '
    'See work/re/c_vital_report.md and handoff-c.md.')


@pytest.mark.parametrize('build,lane,expected', [
    pytest.param('aivitalon', 0, 24, marks=AIR_GAP),
    pytest.param('aivitalon', 1, 4, marks=AIR_GAP),
    pytest.param('aivitalon', 2, 4, marks=AIR_GAP),
    ('aivitalon', 3, 140),
    pytest.param('aivitaloff', 0, 24, marks=AREA_GAP),
    ('aivitaloff', 1, 4), ('aivitaloff', 2, 4), ('aivitaloff', 3, 4),
])
def test_vital_named_bench_replay(build, lane, expected):
    rows = replay(build)
    assert all(values[lane] == expected for _, values in rows), rows


@pytest.mark.parametrize('build,expected', [('aivitalon', [24, 4, 4, 140]),
                                          ('aivitaloff', [24, 4, 4, 4])])
def test_vital_original_readings(build, expected):
    path = Path(simai.labpaths.WORK) / 're/c_vital_measured.json'
    if not path.exists():
        pytest.skip('private original readings unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[build]
    assert evidence['build'] == build
    rows = evidence['rows']
    late = [v for second, _, v in rows if 55 <= second <= 60]
    assert len(late) >= 5 and all(v == expected for v in late), late
    assert all(v[:3] == [24, 4, 4] for _, _, v in rows)
    # Native ATTACHED set/clear/set sequence, not a model target or recruitment guess.
    transitions = []
    for _, _, values in rows:
        bit = values[3] // 100
        if not transitions or transitions[-1] != bit:
            transitions.append(bit)
    assert transitions == ([1, 0, 1] if build == 'aivitalon' else [1, 0])
