"""TEAM_UPGRADE real upgrade-query and consumer counters; work/re/c_teamup_report.md."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('teamup_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _read(expected):
    import build
    import sim
    m, t, _ = build.resolve('engine_teamup', 'a')
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


def test_teamup_real_query_and_consumer_apply_only_to_current_team():
    # Archived DISPLAY_COUNTER values at their recorded logic frames.
    expected = {150: [0, 0, 0, 150], 157: [3, 0, 3, 157],
                240: [3, 0, 3, 240], 248: [2, 0, 1, 248],
                323: [2, 0, 1, 323], 332: [3, 0, 3, 332],
                453: [3, 0, 3, 453]}
    assert _read(expected) == expected
