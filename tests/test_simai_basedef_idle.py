"""Direct counter replays for the recorded engine_aibasedef fighting team.

These probes do not put a team in idle with both garrison flags enabled.
They cannot establish EnterBaseDefensesWhenIdle's positive idle behavior.
"""
import pytest

from test_simai_bench_b import lib, _probe_run, pytestmark  # noqa: F401


@pytest.mark.parametrize('build, expected', [
    pytest.param('aibd1', 1, marks=pytest.mark.xfail(
        strict=True, raises=AssertionError,
        reason='engine_aibasedef aibd1 has one enclosed from s21; model has none. '
               'At each dispatch living turrets remain beyond 150; all are dead by frame 451. '
               'arrival/combat interface gap: work/re/handoff-c.md (Base defense idle).')),
    ('aibd0', 0),
    ('aibdidle', 0),
])
def test_recorded_base_defense_counter_replay(lib, build, expected):
    """engine_aibasedef 11-09: on 1 to s75, off / idle-only 0 throughout."""
    world, rows = _probe_run(build, lib, 76.0)
    assert rows
    enclosed = [r['进炮塔'] for r in rows]
    entries = [e for e in world.garrison.log if not e[3]]
    print(build, 'max/final enclosed', max(enclosed), enclosed[-1], 'entries', entries)
    # Sim.series uses mission seconds starting at t=0; do not infer time from row index.
    window = [(t, r['进炮塔']) for (t, _), r in zip(world.sim.series, rows) if 21 <= t <= 75]
    assert [t for t, _ in window] == list(range(21, 76))
    assert max(enclosed) == expected, (build, enclosed, entries)
    assert enclosed[-1] == expected
    if expected:
        # The recorded positive lasts from s21 through s75, not just at the end.
        assert all(value == expected for _, value in window), window
        # The counter identifies no particular turret; aibdwho's choice was inferred.
        assert entries
        assert all(e[2] in {f'UNIT - CNV AI Turret {k}' for k in range(1, 5)} for e in entries)
    else:
        assert entries == []
