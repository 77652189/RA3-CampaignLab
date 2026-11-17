"""Real ModelCondition duration counters; evidence work/re/c_modeldur_report.md."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('modeldur_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _read(variant, expected):
    import build
    import sim
    m, t, _ = build.resolve('engine_modeldur', variant)
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.produce_due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.produce_due = observe
    e.advance(max(expected) + 8)
    return got


def test_modeldur_real_bits_expire_after_measured_frames():
    expected = {44: [11, 14, 14, 44], 75: [11, 45, 45, 75],
                83: [10, 46, 53, 83], 134: [10, 46, 104, 134],
                144: [8, 46, 106, 144], 283: [8, 46, 106, 283]}
    assert _read('a', expected) == expected


def test_modeldur_one_two_seconds_include_duration_boundary():
    expected = {44: [11, 14, 14, 44], 54: [10, 16, 24, 54],
                62: [8, 16, 31, 62], 284: [8, 16, 31, 284]}
    assert _read('b', expected) == expected
