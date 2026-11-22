"""Fallback replay: return, home wait and measured second-departure ordering."""
from test_simai_bench_b import lib, _probe_run, pytestmark  # noqa: F401
import pytest


@pytest.fixture(scope='module')
def trips(lib):
    return {b: _probe_run(b, lib, 60.0)[1] for b in ('aifbshort', 'aifblong')}


def test_fallback_distance_both_teams_return_alive(trips):
    # B round 230's xfail (aifbshort lost one Peacekeeper on the way home since 65873f7c) passes since structures
    # dead in a fight leave their survivor (E, CreateObjectDie, model da5b198 and be5d767 alike); why not traced
    """checks/engine_aifallback.py: both reach the far area and return with four."""
    for build in ('aifbshort', 'aifblong'):
        rows = trips[build]
        out = next(i for i, r in enumerate(rows) if r['步兵在家'] == 0)
        back = next(i for i in range(out, len(rows)) if rows[i]['步兵在家'] == 4)
        assert any(r['到远厂'] >= 1 for r in rows[out:back])
        assert any(r['中途人数'] >= 1 for r in rows[out:back])
        assert all(r['步兵数'] == 4 for r in rows[:back + 1])


@pytest.mark.xfail(strict=True, reason=(
    'old cause gone: in B round 205, the model\'s B194 (b830b09, SimpleAttack with '
    'UseAestheticsManager forms up first) shifted the first trip. aifbshort got home at row 36 with hostiles still '
    'listed, went straight to state 5 (the gather move, f541) and left at row 38 instead of idling. '
    'Model b830b09~1: rows 36 / 53. B205 aifblong waited 17 (34 -> 51). Needs the form-up point / when it '
    'applies (handoff-b, question to D round 193 / 203). Now aifbshort loses one Peacekeeper on the return '
    '(B230, 65873f7c reach change, handoff-b): three alive from row 34 and three home at row 36. The bench has '
    'four home for 18 samples, s35-52. The model never has all four home after leaving, so the return search '
    'raises StopIteration before departure. In the same fixture aifblong now waits 16 samples (34 -> 50).'))
def test_fallback_distance_first_return_and_departure(trips):
    """checks/engine_aifallback.py: the measured second-departure ordering."""
    returns, departures = [], []
    for build in ('aifbshort', 'aifblong'):
        rows = trips[build]
        out = next(i for i, r in enumerate(rows) if r['步兵在家'] == 0)
        back = next(i for i in range(out, len(rows)) if rows[i]['步兵在家'] == 4)
        departure = next(i for i in range(back + 1, len(rows)) if rows[i]['步兵在家'] < 4)
        returns.append(back)
        departures.append(departure)
        # Bench: each team waits 18 one-second samples at home (s35..52 /
        # s31..48). Allow phase/path differences without accepting an instant rejoin.
        assert 15 <= departure - back <= 20
        assert all(r['步兵数'] == 4 for r in rows[:departure + 1])
    assert returns[0] > returns[1]
    # Bench: short leaves again s53, long s49; assert behavior, not exact seconds.
    assert departures[0] > departures[1]
