"""Original Joypad diagnostic readings, without claiming native input acceptance.

The script phase is not an enabled-state readout. Native controller acceptance
and full action replay remain gaps; see work/re/c_joypad_report.md.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('joypad_labpaths', ROOT / 'experimental/campaign/labpaths.py')
_paths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_paths)


def test_joypad_original_phase_and_untouched_control_readings():
    """Anchor the actual named run, not a fabricated enabled/accepted flag."""
    path = Path(_paths.WORK) / 're/c_joypad_measured.json'
    if not path.exists():
        pytest.skip('private original Joypad archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))
    assert evidence['run'].startswith('CampJoypadA_mcp_')
    assert evidence['verdict'] == 'NOEXPECT'
    rows = [row['values'] for row in evidence['rows']]
    assert rows
    assert {values[0] for values in rows} == {0, 1, 2, 3}
    assert all(len(values) == 3 and values[1] == 1 for values in rows)
    assert all(a[0] <= b[0] and a[2] < b[2] for a, b in zip(rows, rows[1:]))
    assert rows[-1][0] == 3
    assert '逻辑帧' in evidence['output']
