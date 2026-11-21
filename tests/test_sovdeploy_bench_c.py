"""Soviet MCV waypoint replay; evidence work/re/c_sovdeploy_report.md."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('sovdeploy_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_sovdeploy_waypoint_and_untouched_control_match_bench():
    import build
    import sim
    # Real pre-action and settled samples; travel/unfold timing stays a gap.
    pre = (45, 52, 61, 67)
    settled = (250, 257, 265, 272, 280, 288, 295, 302, 311, 318,
               325, 333, 340, 347, 356, 363, 371, 378, 386, 394,
               400, 409, 416, 423, 432, 439, 447, 454, 461, 468)
    expected = {f: [0, 7, 7, f] for f in pre}
    expected.update({f: [3, 7, 4, f] for f in settled})
    m, t, _ = build.resolve('engine_sovdeploy', 'a')
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.production.due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.production.due = observe
    e.advance(max(expected)+8)
    assert not e.unknown.get('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', 0)
    assert got == expected
