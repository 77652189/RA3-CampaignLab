"""Whole-team moves that go round too far (simstatic.long_detours; docs/engine/pathing.md 1: a way round of about 1 400 is
taken, 1 800 is not -- the units stop partway, no error). One finding class, one list that only shrinks (ADR 0016)."""
import pytest
from test_plans import small  # (puts experimental/cnv on the path)  # noqa: F401, I001
import build  # noqa: E402
import parts  # noqa: E402
import simstatic  # noqa: E402

# what the levels do today, by the script that does it (a name prefix): delete a line when it is fixed, never add one.
# (A4's Ghost King transports, 2 420 round for 630 straight, are gone from it: the bench, 2026-11-07 engine_land, read
# the boat go straight at the quay; the simulator's way round was a bridge deck it drove onto from the water, R7)
LEFT = ()


def found(level):
    m, t, _ = build.resolve(level, '')
    return simstatic.long_detours(parts.merged(m, t))


@pytest.mark.parametrize('level', build.LEVELS)
def test_every_level_moves_its_teams_by_ways_the_game_takes_or_is_listed(level):
    bad = [x for x in found(level) if not x.startswith(LEFT)]
    assert not bad, bad[:3]


def test_the_list_is_still_true():
    """A name left in LEFT that no level trips any more is stale."""
    tripped = found('a4')
    assert all(any(x.startswith(n) for x in tripped) for n in LEFT)


def test_a_stricter_limit_names_more_and_a_looser_names_none(monkeypatch):
    tight = found('s2')
    assert tight == []                                        # (long and nearly straight: not a detour)
    monkeypatch.setattr(simstatic, 'BENT', 1.1)
    assert found('s2')                                        # the same moves are named once a long way counts
    monkeypatch.setattr(simstatic, 'DETOUR_LIMIT', 1e9)
    assert found('a4') == []
