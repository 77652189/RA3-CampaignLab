"""Legacy Japan egg command versus concrete command; work/re/c_eggcmd_report.md."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('eggcmd_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _read(expected, mission='engine_eggcmd'):
    import build
    import sim
    m, t, _ = build.resolve(mission, 'a')
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.production.due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.production.due = observe
    e.advance(max(expected) + 8)
    assert not e.unknown.get('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', 0)
    return got


def test_eggcmd_legacy_and_concrete_buttons_match_display_counters():
    expected = {59: [0, 15, 15, 59], 249: [4, 15, 11, 249],
                393: [4, 15, 11, 393], 560: [4, 15, 11, 560]}
    assert _read(expected) == expected


def test_eggcmd_naval_legacy_and_concrete_buttons_match_display_counters():
    # engine_eggnav:a, CampEggNavA_mcp_1116_061650: real water deployment positive.
    expected = {57: [0, 7, 7, 57], 247: [2, 7, 5, 247],
                390: [2, 7, 5, 390], 496: [2, 7, 5, 496]}
    assert _read(expected, 'engine_eggnav') == expected
