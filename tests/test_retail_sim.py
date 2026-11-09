"""A retail campaign mission in the simulator (experimental/cnv/retail.py; ADR 0026 stop condition 2): Allied 1 read
from the game's MapsCampaign.big and run with its own scripts. Skipped where the game is not installed."""
import importlib.util
import math
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    """A module of experimental/cnv by file (sim.py, loaded first, puts its folder on sys.path for the rest)."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, 'experimental', 'cnv', f'{name}.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sim = sys.modules.get('sim') or _load('sim')
retail = sys.modules.get('retail') or _load('retail')

A01 = 'camp_a01_brightonbeach_smith'
pytestmark = pytest.mark.skipif(not os.path.exists(retail.mapstudy.ARCHIVES['ra3']), reason='the game is not installed')


@pytest.fixture(scope='module')
def mission():
    return retail.RetailMission(A01)


def test_the_map_reads_as_a_mission(mission):
    """Players (the human p1, its first enemy s1), relations both ways, a script list per side with the nameless
    neutral side first, the bodies that matter (not the 3700 props), waypoints, areas, the map's own size."""
    assert mission.map.PLAYERS['p1'] == 'Player_1' and mission.map.PLAYERS['s1'] == 'Soviet_1'
    assert mission.relations[('Player_1', 'Soviet_1')] == 'Enemy' and mission.relations[('Player_1', 'Allied_1')] == 'Friend'
    assert mission.order[:3] == ['', 'PlyrNeutral', 'Player_1'] and len(mission.order) == 9
    assert 50 <= len(mission.map.OBJECTS) <= 300 and mission.skipped > 5000
    assert len(mission.waypoints) > 250 and mission.areas
    assert mission.map.DIMS == (575, 575, 50)


def test_the_opening_runs_on_its_own_scripts(mission):
    """The intro locks input and gives it back at ~22 s, the first objective shows, the starting team (4 Peacekeepers,
    2 dogs on Allied_1's 'TEAM - Player 1 Starting Team') is handed to Player_1 -- as the game's opening."""
    s = sim.Sim(mission).run(30.0)
    lines = [text for _, kind, text in s.log if kind == '目标']
    assert any('A01_OBJECTIVE_1' in x for x in lines), s.log
    back = next(t for t, kind, text in s.log if kind == '过场' and text == '交还控制')
    assert 20 <= back <= 25
    mine = [b for b in s.living() if b.owner == 'Player_1']
    assert sorted(b.template for b in mine) == ['AlliedAntiInfantryInfantry'] * 4 + ['AlliedScoutInfantry'] * 2


def test_question_1_the_squad_walks_to_the_point(mission):
    """Acceptance question 1 (docs/story/retail-q1-a01.md): the squad ordered to (505, 1577) has its middle within 30 of
    it ~2.5-2.9 s after the order (bench: 2.9 s at most, sampled every 0.8 s)."""
    order = 22.6
    s = sim.Sim(mission, script=f'{order} 走 队 Player_1/teamPlayer_1 去 @505.2,1576.7')
    s.advance(int(order * 15))
    arrived = None
    while s.t < order + 10 and arrived is None:
        s.advance(1)
        crew = [b for b in s.living() if b.owner == 'Player_1']
        cx, cy = sum(b.x for b in crew) / len(crew), sum(b.y for b in crew) / len(crew)
        if math.hypot(cx - 505.2, cy - 1576.7) <= 30:
            arrived = s.t - order
    assert arrived is not None and 2.0 <= arrived <= 3.2, arrived


@pytest.mark.xfail(strict=True, reason='a group move ends with every unit on the point: the game spreads them round '
                                       'it (the squad stood 19-23 from the point, bench 11-08); no formation model')
def test_question_1_the_squad_stands_round_the_point(mission):
    s = sim.Sim(mission, script='22.6 走 队 Player_1/teamPlayer_1 去 @505.2,1576.7')
    s.advance(int(32 * 15))
    crew = [b for b in s.living() if b.owner == 'Player_1']
    spread = max(math.hypot(b.x - 505.2, b.y - 1576.7) for b in crew)
    assert spread >= 15, spread
