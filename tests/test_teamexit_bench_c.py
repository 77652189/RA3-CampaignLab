"""TEAM_EXIT_ALL_BUILDINGS named replay; see work/re/c_teamexit_report.md."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('teamexit_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_teamexit_mixed_building_and_transport_match_bench():
    import build
    import sim
    # CampTeamExitA_mcp_1116_064136: all 33 displayed samples, keyed by logical frame.
    before = (44, 51, 60, 67, 74)
    after = (82, 89, 97, 104, 113, 120, 128, 135, 143, 150, 158, 165, 173,
             180, 189, 195, 203, 211, 218, 226, 233, 242, 248, 257, 264, 272, 279, 287)
    expected = {f: [3, 3, 127, f] for f in before}
    expected.update({f: [0, 3, 127, f] for f in after})
    m, t, _ = build.resolve('engine_teamexit', 'a')
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.produce_due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.produce_due = observe
    e.advance(max(expected)+8)
    assert not e.unknown.get('TEAM_EXIT_ALL_BUILDINGS', 0)
    assert got == expected
