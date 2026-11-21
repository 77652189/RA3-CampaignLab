"""Nearest-building action named replay; work/re/c_teamgarr_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('teamgarr_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('which,owner,frames', [
    ('a', 1, (44, 52, 60, 69, 245, 252, 259, 267, 275, 283, 291, 298,
               306, 314, 322, 331, 339, 347, 355, 363, 371, 378, 386)),
    ('b', 2, (44, 52, 60, 73, 245, 252, 261, 268, 275, 283, 291, 299,
               306, 313, 321, 329, 337, 345, 353, 361, 369, 377, 385,
               392, 399, 407)),
])
def test_teamgarr_nearest_and_team_scope_match_bench(which, owner, frames):
    import build
    import sim
    # Pre-action samples and the settled window from f245, including repeat.
    # Door crossing/queue timing is not asserted by this selection probe.
    expected = {f: ([0, 0, 31, f] if f < 75 else [3, owner, 31, f]) for f in frames}
    m, t, _ = build.resolve('engine_teamgarr', which)
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.production.due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.production.due = observe
    e.advance(max(expected)+8)
    assert not e.unknown.get('TEAM_GARRISON_NEAREST_BUILDING', 0)
    assert got == expected
