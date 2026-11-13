"""Named CountModifier bench replay; original evidence: work/re/c_countmodifier_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)


def measured():
    path = Path(simai.labpaths.WORK) / 're/c_countmodifier_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.mark.parametrize('build, expected', [('aicmhalf', [4, 5]), ('aicmfour', [7, 2])])
def test_count_modifier_original_readings(build, expected):
    rows = measured()[build]['rows']
    # Independent raw samples, without manufacturing an exact game frame.
    samples = [values for second, _, values in rows if 39 <= second <= 41]
    assert len(samples) >= 2
    assert all(values == expected for values in samples), samples


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build', ['aicmhalf', 'aicmfour'])
def test_count_modifier_named_bench_replay(build):
    rows = measured()[build]['rows']
    before = max((row for row in rows if row[0] <= 40), key=lambda row: row[0])
    after = min((row for row in rows if row[0] >= 40), key=lambda row: row[0])
    assert before[2] == after[2], (before, after)
    w = simai.run(build, 'a', until=41)
    samples = [values for second, values in w.sim.series if 40 <= second <= 41]
    assert samples and all(values == before[2] for values in samples), (samples, before, after)
