"""Japanese MCV waypoint replay; evidence work/re/c_jpndeploy_report.md."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('jpndeploy_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_jpndeploy_waypoint_and_untouched_control_match_bench():
    import build
    import sim
    # Real pre-action and settled samples; travel/unfold timing stays a gap.
    pre = (44, 52, 59, 67, 74)
    settled = (306, 315, 323, 331, 340, 348, 356, 365, 372, 381, 389, 398,
               405, 415, 423, 432, 440, 448, 455, 464, 472, 482, 495, 501)
    expected = {f: [0, 7, 7, f] for f in pre}
    expected.update({f: [3, 7, 4, f] for f in settled})
    m, t, _ = build.resolve('engine_jpndeploy', 'a')
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.produce_due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.produce_due = observe
    e.advance(max(expected)+8)
    assert not e.unknown.get('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', 0)
    assert got == expected
