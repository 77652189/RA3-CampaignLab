"""TEAM_SET_HEALTH native named HP counters; work/re/c_teamhp_report.md."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('teamhp_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('variant', ['a', 'b'])
def test_teamhp_current_mixed_members_and_controls_match_bench(variant):
    import build
    import sim
    rows = json.loads((ROOT / 'tests/fixtures/c_teamhp.json').read_text(encoding='utf-8'))[variant]
    expected = {row[-1]: row for row in rows}
    m, t, _ = build.resolve('engine_teamhp', variant)
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.produce_due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.produce_due = observe
    e.advance(max(expected)+8)
    assert not e.unknown.get('TEAM_SET_HEALTH', 0)
    assert got == expected
