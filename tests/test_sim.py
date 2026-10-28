"""The plan simulator (experimental/cnv/sim.py, simstatic.py): the game's script semantics on small missions of our
own (timers, flags, NOT, moving along the map, the player's script of events, stuck), the known traps it carries
(the S5 fleet past the open lock loses at once), every level running with nothing it does not know, and the static
half finding what can never happen."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import parts  # noqa: E402
import sim  # noqa: E402
import simstatic  # noqa: E402
from maps import festival  # noqa: E402
from parts import NOT, Mission, Script, square  # noqa: E402

WON = ('SET_FLAG', sim.WON, 1)
LOST = ('SET_FLAG', sim.LOST, 1)


def mission(scripts, endings=()):
    m = Mission(name='T', map=festival, scripts=list(scripts))
    m.endings = list(endings)
    return m


def test_a_timer_then_a_flag_then_the_win():
    m = mission([Script('go', [], [('SET_MILLISECOND_TIMER', 'T go', 10.0)]),
                 Script('half', [('TIMER_EXPIRED', 'T go')], [('SET_FLAG', 'F', 1)]),
                 Script('win', [('FLAG', 'F', 1)], [WON])], ['win'])
    s = sim.Sim(m).run()
    assert s.ending[0] == '赢' and abs(s.ending[1] - 10.0) <= sim.DT


def test_not_and_a_once_script_fire_once():
    m = mission([Script('count', [('FLAG', 'F', 1, NOT)], [('INCREMENT_COUNTER', 1, 'C')]),
                 Script('again', [('COUNTER', 'C', 3, 1)], [('INCREMENT_COUNTER', 1, 'D')], once=False),
                 Script('win', [('COUNTER', 'D', 3, 4)], [WON])], ['win'])
    s = sim.Sim(m).run()
    assert s.counters['C'] == 1 and s.ending[0] == '赢'            # the once-script one time, the other each tick


def test_a_unit_walks_the_map_at_its_speed():
    """A warrior (speed 50) from the start to the west field along the ground; the area there sees it come."""
    m = mission([Script('make', [], [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'W', 'JapanAntiInfantryInfantry',
                                      'Soviet_1/teamSoviet_1', 'A'), ('MOVE_NAMED_UNIT_TO', 'W', 'B')]),
                 Script('win', [('NAMED_INSIDE_AREA', 'W', 'Goal')], [WON])], ['win'])
    a, b = festival.SITES['start'], festival.SITES['west field']
    m.waypoints = {'A': (a.x, a.y), 'B': (b.x, b.y)}
    m.areas = {'Goal': square(b.x, b.y, 100)}
    s = sim.Sim(m).run()
    straight = ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5
    assert s.ending[0] == '赢' and straight / 50 - 3 <= s.ending[1] <= 1.6 * straight / 50


def test_the_players_script_destroys_and_the_level_is_lost():
    m = mission([Script('lose', [('NAMED_DESTROYED', 'UNIT - T Truck')], [LOST])], ['lose'])
    m.put('AlliedAntiVehicleVehicleTech1', 'start', role='truck', name='UNIT - T Truck')
    s = sim.Sim(m, script='45 摧毁 truck').run()
    assert s.ending[:2] == ('输', 45.0)


def test_nothing_pending_is_stuck():
    m = mission([Script('win', [('FLAG', 'Never', 1)], [WON])], ['win'])
    s = sim.Sim(m).run()
    assert s.ending is None and '卡住' in s.ending_line() and 'FLAG(Never, 1)' in s.ending_line()


def test_the_fleet_through_the_open_lock_loses_at_once():
    """S5's known trap: nothing done, the fleet sails off and the lock is not shut -- lost the moment it passes."""
    s = sim.simulate('s5', until=600)
    assert s.ending and s.ending[0] == '输' and s.ending[1] < 300


def test_every_level_runs_with_nothing_unknown():
    import build
    for lv in build.LEVELS:
        s = sim.simulate(lv, until=120)
        assert not s.unknown, f'{lv}: {s.unknown}'


def test_static_finds_a_phase_never_reached_and_a_flag_nobody_sets():
    m = mission([Script('CNV T - Phase 1', [], [('SET_FLAG', 'CNV_T_Phase_1', 1)]),
                 Script('CNV T - Phase 2', [('FLAG', 'CNV_T_Ready', 1)], [('SET_FLAG', 'CNV_T_Phase_2', 1)]),
                 Script('CNV T - Win', [('FLAG', 'CNV_T_Phase_2', 1)], [WON])], ['CNV T - Win'])
    out = '\n'.join(simstatic.report(m))
    assert '赢不了' in out and 'CNV_T_Phase_2' in out and 'CNV_T_Ready' in out


def test_static_takes_what_the_player_makes_as_possible():
    """The player's engineer makes ice no script makes: a count of it in an area could still be met."""
    m = mission([Script('CNV T - Win', [('PLAYER_HAS_OBJECT_COMPARISON', 'Player_1', 3, 1, 'CNV_IceWall')], [WON])],
                ['CNV T - Win'])
    assert '能赢' in simstatic.report(m)[0]


def test_the_wiring_checks_in_the_simulator():
    """experimental/cnv/simchecks.py: each bench check that is wiring only, run in the simulator -- its ending
    and, where they are wiring, its counters."""
    import simchecks
    bad = []
    for level, check in simchecks.CHECKS:
        ok, lines = simchecks.run(level, check)
        if not ok:
            bad.append(f'{level} {check}: ' + ' | '.join(x for x in lines if x.startswith('FAIL'))[:300])
    assert not bad, '\n'.join(bad)
