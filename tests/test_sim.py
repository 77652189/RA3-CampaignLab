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


def test_the_engines_semantics_for_the_dead_and_the_gone():
    """docs/engine/script-semantics.md 4.2 / 7: a killed unit reads 0 % health while it dies and is counted; once
    gone it is outside every area; a script's kill clears who hit it last."""
    m = mission([Script('hurt', [('UNIT_HEALTH', 'UNIT - T Tank', 0, 10)], [('SET_FLAG', 'Low', 1)]),
                 Script('out', [('NAMED_OUTSIDE_AREA', 'UNIT - T Tank', 'Here')], [('SET_FLAG', 'Out', 1)]),
                 Script('hit', [('NAMED_ATTACKED_BY_PLAYER', 'UNIT - T Tank', 'Player_1')], [('SET_FLAG', 'Hit', 1)]),
                 Script('kill', [('FLAG', 'Hit', 1)], [('NAMED_KILL', 'UNIT - T Tank')]),
                 Script('win', [('FLAG', 'Out', 1)], [WON])], ['win'])
    m.put('AlliedAntiVehicleVehicleTech1', 'start', role='tank', name='UNIT - T Tank')
    s0 = festival.SITES['start']
    m.areas = {'Here': square(s0.x, s0.y, 200)}
    s = sim.Sim(m, script='20 打 tank').run(120)
    assert s.flags.get('Low') == 1 and s.flags.get('Hit') == 1
    tank = s.bodies['UNIT - T Tank']
    assert tank.last_hit is None                                      # the script's kill came from nobody
    assert s.ending[0] == '赢' and s.ending[1] > 20 + sim.LINGER       # outside only once it is gone


def test_won_and_lost_in_one_frame_is_a_warning_and_enable_rearms():
    m = mission([Script('again', [('FLAG', 'Go', 1)], [('INCREMENT_COUNTER', 1, 'N'), ('SET_FLAG', 'Go', 0)]),
                 Script('arm', [('COUNTER', 'N', 0, 3)], [('ENABLE_SCRIPT', 'again'), ('SET_FLAG', 'Go', 1)],
                        once=False),
                 Script('start', [], [('SET_FLAG', 'Go', 1)]),
                 Script('win', [('COUNTER', 'N', 3, 3)], [WON]),
                 Script('lose', [('COUNTER', 'N', 3, 3)], [LOST])], ['win', 'lose'])
    s = sim.Sim(m).run(60)
    assert s.counters['N'] == 3                                       # the once-script armed again, three times
    assert s.ending[0] == '赢' and s.both and any('同一帧' in x for _, k, x in s.log if k == '警告')


def test_no_level_has_a_static_problem():
    """Every level as built: it can be won, each phase can be reached, each main objective gets its tick (a hold-out
    objective with no 完成 of its own is ticked by the win: plan.py compile_endings)."""
    import build
    bad = []
    for lv in build.LEVELS:
        m, t, _ = build.resolve(lv, '')
        bad += [f'{lv}: {x.strip()}' for x in simstatic.report(m) if '问题' in x]
    assert not bad, '\n'.join(bad)


def test_the_win_ticks_a_hold_out_objective():
    s = sim.simulate('j5', script='不打', until=700)       # the wiring: held to the end (the fight loses it)
    held =[g.name for g in s.m.objectives if not g.bonus and not g.spec.get('完成')]
    assert held and s.ending[0] == '赢' and all(s.objectives.get(g) == 2 for g in held)


def test_a_fight_by_the_games_numbers():
    """The fight model: a guardian (480 hp, cannon 30/s) against an imperial warrior (160 hp, gun 14.3/s; a tank
    takes GUN at 50 %, infantry CANNON at 20 %): side by side, the warrior falls at 160 / (30 x 0.2) ~ 27 s, the
    guardian loses 27 x 14.3 x 0.5 ~ 190 hp."""
    m = mission([Script('lose', [('NAMED_DESTROYED', 'UNIT - T W')], [WON])], ['lose'])
    m.put('AlliedAntiVehicleVehicleTech1', 'start', role='tank', name='UNIT - T G')
    m.put('JapanAntiInfantryInfantry', 'start', 100, 0, role='w', side='s1', name='UNIT - T W')
    s = sim.Sim(m).run(120)
    g = s.bodies['UNIT - T G']
    assert s.ending[0] == '赢' and 24 <= s.ending[1] <= 30 and 270 <= g.hp <= 310
    assert s.first_death[1].name == 'UNIT - T W'


def test_a_defence_left_alone_is_lost():
    """J5 done nothing: the head-hunters reach Yuriko and the level is lost (before the fight model it held to a
    win); 不打 turns the fight off again."""
    assert sim.simulate('j5', until=600).ending[0] == '输'
    assert sim.simulate('j5', script='不打', until=600).ending[0] == '赢'
