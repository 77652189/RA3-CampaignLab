"""Named unpack-placement replays; original evidence: work/re/c_placement_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


@pytest.mark.parametrize('build, expected', [
    ('aiplace1', (1, 0, 0, 1)),
    ('aiplace200', (1, 0, 0, 1)),
    ('aiplacej200', (1, 0, 0, 1)),
])
def test_placement_named_bench_replay(build, expected):
    # Both Allied-side bench runs kept the core. This does not establish the
    # distance rule: neither run established an eligible unpacking team.
    w = simai.run(build, 'a', until=41)
    rows = [tuple(values) for second, values in w.sim.series if 35 <= second <= 40]
    assert rows
    assert all(row == expected for row in rows), rows[-3:]


@pytest.mark.parametrize('build', ['aiplace1', 'aiplace200', 'aiplacej200'])
def test_placement_original_readings(build):
    path = Path(simai.labpaths.WORK) / 're/c_placement_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[build]
    rows = [values for second, frame, values in evidence['rows'] if 35 <= second <= 40]
    assert rows and all(row == [1, 0, 0, 1] for row in rows)
    assert evidence['states']
    assert all(not s['mem'] and s['mstate'] == 8 and s['tgt'] == -1
               for s in evidence['states'])
