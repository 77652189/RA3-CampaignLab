"""Named facing against native hull headings; work/re/c_facewp_report.md."""
import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('facewp_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('variant', ['b'])
def test_facewp_named_heading_and_untouched_control_match_bench(variant):
    import build
    import sim
    measured = json.loads((ROOT / 'tests/fixtures/c_facewp.json').read_text(encoding='utf-8'))[variant]
    m, t, _ = build.resolve('engine_facewpai', variant)
    e = sim.Sim(m, t, script='不打')
    expected = {row['frame']: row for row in measured}
    got = {}
    tick = e.production.due

    def observe(frame):
        tick(frame)
        if frame in expected:
            bodies = [e.body(m.role(r).name) for r in ('alpha', 'beta', 'control')]
            got[frame] = [math.degrees(b.angle) for b in bodies]
            assert e.counters['CNV_FW_Alive'] == 7

    e.production.due = observe
    e.advance(max(expected)+8)
    assert not e.unknown.get('NAMED_FACE_WAYPOINT', 0)
    assert got.keys() == expected.keys()
    for frame, headings in got.items():
        # Native hd is rounded to whole degrees; compare circular angles.
        for actual, native in zip(headings, expected[frame]['headings']):
            assert abs((actual-native+180.) % 360.-180.) <= 1., (frame, actual, native)
