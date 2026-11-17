"""Named native magnetic-mine replay; evidence: work/re/c_attachmine_report.md."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location('simbench_attachmine', Path(__file__).resolve().parents[1] /
                                             'experimental/cnv/simbench.py')
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)


@pytest.fixture(scope='module', params=['a', 'b'])
def mine_readings(request):
    import build
    import sim
    m, t, _ = build.resolve('engine_attachmine', request.param)
    e = sim.Sim(m, t)
    e.shot_clock = True
    rows = e.run(14).series
    return request.param, tuple(rows[-1][1])


def test_native_mine_deleted_nugget_matches_bench(mine_readings):
    check, readings = mine_readings
    assert (readings[1], readings[3]) == (110, 110 if check == 'a' else 7110)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason='Native magnetic-mine creation/AttachUpdate consumer remains a gap; '
                          'see work/re/c_attachmine_report.md and handoff-c.md')
def test_native_mine_attachment_and_target_status_match_bench(mine_readings):
    check, readings = mine_readings
    assert readings == ((111, 110, 111, 110) if check == 'a' else (111, 110, 7111, 7110))
