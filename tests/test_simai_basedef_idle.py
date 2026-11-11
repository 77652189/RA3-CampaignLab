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
               'Consumer is called but eligible turrets remain beyond 150 until lost; '
               'arrival/combat interface gap: work/re/handoff-c.md (Base defense idle).')),
    ('aibd0', 0),
    ('aibdidle', 0),
])
def test_recorded_base_defense_counter_replay(lib, build, expected):
    """engine_aibasedef 11-09: on 1 to s75, off / idle-only 0 throughout."""
    world, rows = _probe_run(build, lib, 75.0)
    assert rows
    enclosed = [r['进炮塔'] for r in rows]
    entries = [e for e in world.garrison.log if not e[3]]
    print(build, 'max/final enclosed', max(enclosed), enclosed[-1], 'entries', entries)
    assert max(enclosed) == expected, (build, enclosed, entries)
    assert enclosed[-1] == expected
    if expected:
        assert [e[2] for e in entries] == ['UNIT - CNV AI Turret 1']
    else:
        assert entries == []
