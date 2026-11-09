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


def test_each_computer_player_draws_from_its_own_personality(mission):
    """A player's protocol lottery is its map personality's PowerChoice lines (simtech.Book): DefaultPersonality has
    none (never buys); the map's own AIP_... ones are not in the SDK and take their faction's solo base lines."""
    books = sim.Sim(mission).books
    assert not books['Soviet_2'].choices and not books['Allied_1'].choices     # DefaultPersonality
    assert books['Soviet_1'].choices                                           # AIP_A01_SovietHuntMarshall


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
    # bench 11-09 (retail_q1_spots.py): the blobs' middle at its final spot <=2.9 s after the order; the simulator was
    # 3.9 s on grid-row ways, in time since they are pulled straight (Ground.pull, Generals' Path::optimize)
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
    # 3.6, not the bench's 2.9: the bench's middle is the team-blue pixels' (the dogs' figures, bigger and twice as
    # fast, weigh more); the simulator's is the six units' own, the last Peacekeeper (185 off) walking to a spot 22-39
    # short of the point since the units stop apart (group move, 11-09: 3.4 s)
    assert arrived is not None and 2.0 <= arrived <= 3.6, arrived


def test_question_1_the_squad_stands_round_the_point(mission):
    """The squad stops apart, its middle short of the point: a column march's ends (Sim.column_ends). Bench 11-09
    (testbench/retail_q1_spots.py, units as blobs): 3 columns x 2 rows, the front row on the point, ~44-50 across
    and ~48 back, the middle ~22 short; the farthest ~76 off (pixel centres sit above the feet: ~10 off)."""
    s = sim.Sim(mission, script='22.6 走 队 Player_1/teamPlayer_1 去 @505.2,1576.7')
    s.advance(int(32 * 15))
    crew = [b for b in s.living() if b.owner == 'Player_1']
    cx, cy = sum(b.x for b in crew) / len(crew), sum(b.y for b in crew) / len(crew)
    assert 10 <= math.hypot(cx - 505.2, cy - 1576.7) <= 35
    apart = min(math.hypot(a.x - b.x, a.y - b.y) for i, a in enumerate(crew) for b in crew[i + 1:])
    assert apart >= 38, apart                                       # bench: the closest pair ~42
    assert max(math.hypot(b.x - 505.2, b.y - 1576.7) for b in crew) <= 75


def test_two_units_sent_alone_to_one_point_stand_apart(mission):
    """Two separate move orders to one point (MOVE_NAMED_UNIT_TO each): the second's goal is moved off the first's
    (Generals' AIInternalMoveToState adjusts every move's goal off the spots other units hold). Bench 11-09
    retail_q1_spots.py: a dog and a Peacekeeper sent alone to one point stood ~22 apart (sim.HOLD_SPOTS)."""
    s = sim.Sim(mission, script='22.6 走 UNIT - P1 - Peacekeeper 01 去 @505.2,1576.7; '
                                '22.6 走 UNIT - P1 - Peacekeeper 02 去 @505.2,1576.7')
    s.advance(int(35 * 15))
    a, b = s.bodies['UNIT - P1 - Peacekeeper 01'], s.bodies['UNIT - P1 - Peacekeeper 02']
    assert math.hypot(a.x - b.x, a.y - b.y) >= 14
    assert min(math.hypot(u.x - 505.2, u.y - 1576.7) for u in (a, b)) <= 1


def test_a_players_names_are_its_own():
    """A name in a player's script list is that player's (retail.scoped): 'Player/name' another's, a bare one the
    list's own; our maps' unnamed list keeps names as they are."""
    players = {'Soviet_2', 'Player_1'}
    assert retail.scoped('Soviet_2', 'FLAG - X', players) == 'Soviet_2/FLAG - X'
    assert retail.scoped('Player_1', 'Soviet_2/FLAG - X', players) == 'Soviet_2/FLAG - X'
    assert retail.scoped('Player_1', 'A/B', players) == 'Player_1/A/B'
    assert retail.scoped('', 'FLAG - X', players) == 'FLAG - X'


def test_objective_1_completes_when_the_soviets_are_gone(mission):
    """A01_OBJECTIVE_1 ('Objective 01 - Completed'): the buffer timer, Soviet_2's flag set when its 'TEAM - Intro
    Patrol 01' is destroyed (TEAM_DESTROYED, read from the other list as 'Soviet_2/FLAG - ...'), and no Soviet_1
    object of the list 'objective 01 - soviet infantry' (OBJECTLIST_ADDOBJECTTYPE: conscripts and war bears) left.
    The Soviets killed by hand at 31 s: the objective is done in the next second."""
    s = sim.Sim(mission, script='30 摧毁 队 Soviet_2/TEAM - Intro Patrol 01')
    s.advance(31 * 15)
    assert not any('目标完成' in text for _, kind, text in s.log if kind == '目标')
    for b in s.living():
        if b.owner == 'Soviet_1' and b.template.lower() in s.of_types('objective 01 - soviet infantry'):
            s.destroy(b, 'test')
    s.advance(5 * 15)
    done = [t for t, kind, text in s.log if kind == '目标' and text == '目标完成：MISSIONOBJ:A01_OBJECTIVE_1']
    assert done and 31 <= done[0] <= 32, s.log[-20:]


A02, A03 = 'camp_a02_cannes_smith', 'camp_a03_heidelberg_smith'


def _objectives(s):
    return [(t, text) for t, kind, text in s.log if kind == '目标']


def test_a_side_carries_its_library_maps():
    """LibraryMaps: one entry per script list, SidesList order (a02: the neutral side the restrictions, the object
    lists and the victory relevance; Player_1 the end of the mission); the library's scripts join that side's list,
    the map's own script of the same name overriding the library's ('Victory Condition (OVERRIDE ME)')."""
    m = retail.RetailMission(A02)
    assert m.libraries[''] == ('lib_camp_restrictions', 'lib_object_lists', 'lib_power_restrictions',
                               'lib_victory_relevance')
    assert m.libraries['Player_1'] == ('lib_end_mission',)
    s = sim.Sim(m)
    s.advance(2)
    got = set(s.of_types('_object list_soviet loss condition'))       # Lib_Victory_Relevance's, on the neutral side
    assert {'sovietconstructionyard', 'sovietwarfactory', 'sovietbarracks', 'sovietmcv'} <= got, got
    assert not any(kind == '结局' for _, kind, _ in s.log)              # the library's OVERRIDE ME win is the map's


def test_a02_no_objective_is_done_at_the_start():
    """Question 2 (docs/story/retail-q2-q3.md): objective 5's '0 Soviet05 objects of the loss-condition list' reads
    the list Lib_Victory_Relevance defines (it read an empty list: done at 0:01), objective 1's 'NOT Soviet05 units in
    the convention center' keeps its inverted bit (ignored: done at 0:04). Neither is done in the first minute; both
    the spy and the convention-center objectives show."""
    s = sim.Sim(retail.RetailMission(A02)).run(60.0)
    got = _objectives(s)
    assert not any('完成' in text for _, text in got), got
    assert {'目标亮出：MISSIONOBJ:A02_Objective_1', '目标亮出：MISSIONOBJ:A02_Objective_2'} <= {x for _, x in got}


def test_a03_the_escort_objective_shows_after_the_intro():
    """Question 3: the only way to 'Objective01 - Escort MCVs' is the intro chain, the map's own timers 12 + 5 + 1 s;
    Player_2's 'With AI' branch reads its personality 'AIPersonalityDefinition:AIP_A03_Coop_AlliedSpecialForces' by
    the bare name the script gives. (The bench saw it at its 3.2 s: its clock starts after the menus, >= 15 s into
    the mission -- the bench's to measure.)"""
    s = sim.Sim(retail.RetailMission(A03)).run(25.0)
    shown = [t for t, text in _objectives(s) if text == '目标亮出：MISSIONOBJ:A03_OBJECTIVE_1']
    assert shown and 17 <= shown[0] <= 19, _objectives(s)


J01, S01 = 'camp_j01_russianvillage_white', 'camp_s01_leningradcanals_rao'


def test_j01_reads_the_neutral_sides_object_list_in_any_case():
    """Question 4 (docs/story/retail-q4-q5.md): j01's unnamed list asks '_object list_japan all units', which
    Lib_Object_Lists defines on PlyrNeutral as '_OBJECT LIST_Japan All Units'. Object lists are one table, any case
    (retail.SCOPED_ARGS): read per side or by case the list was empty, 'AllP1DeadP2IsAI' fired and the mission was
    lost at 0:42; the game plays on past 63 s."""
    s = sim.Sim(retail.RetailMission(J01)).run(70.0)
    assert len(s.of_types('_object list_japan all units')) > 1          # the list's types, not the name itself
    assert not any(kind == '结局' or text == 'S_EndMissionLose' for _, kind, text in s.log), s.log[-10:]


def test_s01_runs_without_its_missing_area_and_keeps_natasha():
    """Question 5: s01 names 'AREA - P2 Delete Aircraft', which the map lacks -- an empty area (it raised KeyError);
    'Emergency - Natasha Indestructible' sets the Indestructible panel flag below 10 % health, and an indestructible
    body takes no damage (it was killed at 0:09 and the mission lost at 0:17); the game plays on past 63 s."""
    s = sim.Sim(retail.RetailMission(S01)).run(70.0)
    assert 'AREA - P2 Delete Aircraft' in s.areas.missing
    assert s.body('UNIT - Commando').alive
    assert not any(kind == '结局' for _, kind, _ in s.log), s.log[-10:]
