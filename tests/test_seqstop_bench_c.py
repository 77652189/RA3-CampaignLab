"""Sequential stop real counters; evidence work/re/c_seqstop_report.md."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('seqstop_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _read(expected):
    import build
    import sim
    m, t, _ = build.resolve('engine_seqstop', 'a')
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


def test_seqstop_clears_pending_scripts_keeps_move_and_accepts_fresh_script():
    # Actual four-counter snapshots, not screenshot seconds or model predictions.
    expected = {43: [1, 1, 0, 43], 282: [111, 1, 3, 282],
                308: [111, 1001, 3, 308], 360: [111, 1001, 3, 360]}
    assert _read(expected) == expected


def test_seqstop_both_arrived_before_control_advances():
    expected = {252: [1, 1, 3, 252]}
    assert _read(expected) == expected
