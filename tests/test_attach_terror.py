"""Native Terror Drone attachment replay; evidence: work/re/c_attachterror_report.md."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location('simbench_attachterror', Path(__file__).resolve().parents[1] /
                                             'experimental/cnv/simbench.py')
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason='Native filtered AttachUpdate and parent-death consumer remain gaps; '
                          'see work/re/c_attachterror_report.md and handoff-c.md')
def test_native_terror_attach_and_script_killed_parent_match_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_attachterror', 'a')
    e = sim.Sim(m, t)
    e.shot_clock = True
    rows = e.run(24).series
    assert any(14 <= sec < 16 and tuple(row) == (127000, 127000, 3000, 3000)
               for sec, row in rows)
    assert tuple(rows[-1][1]) == (127007, 127000, 3006, 3002)
