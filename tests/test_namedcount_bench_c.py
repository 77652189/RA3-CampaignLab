"""Named countdown readback; evidence: work/re/c_namedcount_report.md."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('namedcount_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _replay(mission, expected):
    import build
    import sim
    m, t, _ = build.resolve(mission, 'a')
    e = sim.Sim(m, t, script='不打')
    got = {}
    tick = e.produce_due

    def observe(frame):
        tick(frame)
        if frame in expected:
            got[frame] = [e.counters.get(k, 0) for k, _ in t.counters]

    e.produce_due = observe
    e.advance(max(expected)+8)
    assert got == expected
    assert not e.unknown.get('NAMED_SET_SPECIAL_POWER_COUNTDOWN', 0)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='Named countdown and building READY world/timing unresolved after two runs; see work/re/c_namedcount_report.md')
def test_namedcount_iron_curtain_matches_display_readings():
    # CampNamedCountA_mcp_1116_065413: every displayed logical-frame sample.
    before = (43, 50, 59, 68, 77, 86, 96, 106, 114, 124, 133, 143)
    after = (153, 161, 169, 179, 188, 197, 207, 215, 223, 234, 244, 253,
             261, 270, 278, 287, 296, 305, 315)
    expected = {f: [0, 7, 0, f] for f in before}
    expected.update({f: [7, 7, 0, f] for f in after})
    _replay('engine_namedcount', expected)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='Named countdown and building READY world/timing unresolved after two runs; see work/re/c_namedcount_report.md')
def test_namedcount_vacuum_bomb_matches_display_readings():
    # CampNamedVacA_mcp_1116_065548: every displayed logical-frame sample.
    before = (41, 48, 59, 69, 79, 87, 98, 106, 117, 123, 130, 138, 148)
    after = (155, 163, 170, 179, 188, 198, 209, 218, 224, 233, 242, 250,
             258, 267, 274, 283, 292, 300)
    expected = {f: [0, 7, 0, f] for f in before}
    expected.update({f: [3, 7, 0, f] for f in after})
    _replay('engine_namedvac', expected)
