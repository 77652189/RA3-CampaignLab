"""Named conyard diagnostic replays; distance semantics remain unverified.

Measured eligibility gate: work/re/c_conyard_report.md. These tests must not
be registered as acceptance for either conyard distance or its time exemption.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)


@pytest.mark.skipif(not simai.available(), reason='no private AI model')
@pytest.mark.parametrize('build', ['aicyard0', 'aicyard300'])
def test_conyard_named_gate_replay(build):
    w = simai.run(build, 'a', until=36)
    rows = [tuple(values) for second, values in w.sim.series if 30 <= second <= 35]
    assert rows and all(row == (1, 0, 0, 1) for row in rows), rows[-3:]


@pytest.mark.parametrize('build', ['aicyard0', 'aicyard300'])
def test_conyard_original_gate_readings(build):
    path = Path(simai.labpaths.WORK) / 're/c_conyard_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))['runs'][build]
    assert evidence['verdict'] == 'NOEXPECT'
    assert evidence['states']
    assert all(not s['mem'] and s['mstate'] == 8 and s['tgt'] == -1 for s in evidence['states'])
    # No row for this state was published. This does not prove no find call;
    # candidate eligibility and the returned placement point remain unknown.
    assert evidence['picks'] == []
    rows = [values for second, frame, values in evidence['counter_rows'] if 30 <= second <= 35]
    assert rows and all(row == [1, 0, 0, 1] for row in rows)
