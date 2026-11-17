"""PLAYER_KILL named bench replay; see work/re/c_playerkill_report.md."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('playerkill_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_playerkill_owned_units_and_buildings_match_bench():
    import build
    import sim
    # CampPlayerKillA_mcp_1116_062916: before/after empty call, target kill, repeat, final.
    expected = {45: [7, 7, 0, 45], 61: [7, 7, 0, 61], 75: [7, 7, 0, 75],
                83: [5, 5, 0, 83], 152: [5, 5, 0, 152], 287: [5, 5, 0, 287]}
    m, t, _ = build.resolve('engine_playerkill', 'a')
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.produce_due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.produce_due = observe
    e.advance(max(expected)+8)
    assert not e.unknown.get('PLAYER_KILL', 0)
    assert got == expected
