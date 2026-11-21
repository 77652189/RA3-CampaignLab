"""Named native production replays; scope/evidence: work/re/c_unitban_report.md."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('unitban_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _read(variant, expected):
    import build
    import sim
    m, t, _ = build.resolve('engine_unitban', variant)
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.production.due
    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]
    e.production.due = observe
    e.advance(max(expected) + 8)
    return got


def test_unitban_queued_engineer_waits_for_enable():
    """engine_unitban:a: disabled queue consumes nothing, then resumes and finishes twice."""
    expected = {150: [2000, 1603, 0, 150], 198: [1843, 1500, 10, 198],
                484: [1000, 1000, 33, 484]}
    assert _read('a', expected) == expected


def test_unitban_enable_resumes_partly_paid_engineer():
    """engine_unitban:b retains 200 already paid, resumes, and produces one per side."""
    expected = {101: [1800, 1766, 0, 101], 180: [1800, 1503, 0, 180],
                195: [1753, 1500, 10, 195], 270: [1503, 1500, 10, 270],
                285: [1500, 1500, 11, 285]}
    assert _read('b', expected) == expected


@pytest.mark.xfail(strict=True, reason=(
    'engine_unitban:a f322 p1 money 1466, model 1433: the second queued engineer starts '
    'payment ten frames too early after the first fills. Door/next-job scheduling is a '
    'production gap; see work/re/c_unitban_report.md.'))
def test_unitban_second_job_measured_payment():
    expected = {322: [1466, 1129, 11, 322]}
    assert _read('a', expected) == expected
