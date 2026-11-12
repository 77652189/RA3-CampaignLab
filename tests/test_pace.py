"""齐步 (units/pace.py, plan.py `进攻 ... 齐步: 是`, contract.pace_released): a force of mixed speeds goes to its goal together.
The faster units are copies carrying an upgrade whose SPEED modifier brings them to the slowest member's speed; the
upgrade is taken away when one of them gets inside the arrival area (docs/engine/pathing.md 5)."""
import pytest
from test_plans import named, small  # (puts experimental/cnv on the path)  # noqa: F401, I001
import contract  # noqa: E402
import parts  # noqa: E402
import sim  # noqa: E402
import simunits  # noqa: E402
from maps import festival  # noqa: E402
from parts import Mission, Script, square  # noqa: E402
from plantime import PlanError  # noqa: E402
from units import pace  # noqa: E402

TANK, WALKER = 'JapanAntiVehicleVehicleTech1', 'JapanAntiInfantryInfantry'         # speed 75 and 50


def force(**more):
    wave = {'名字': 'w', '开始': '开局 + 1:00', '兵': {'帝国武士': 2, '海啸坦克': 2}, '从': 'north base', '打': 'west field', '齐步': '是'}
    wave.update(more)
    return small(进攻=[wave])


def test_the_percent_brings_a_unit_down_to_the_slowest_and_never_below_it():
    assert pace.percent(75, 50) == 67 and pace.percent(120, 40) == 34 and pace.percent(80, 50) == 63
    assert 80 * pace.percent(80, 50) / 100 >= 50                       # a hair early, never late
    assert pace.percent(100, 100) == 99                                 # (the caller makes no copy of the slowest)


def test_a_paced_copy_is_the_units_own_file_with_one_upgrade_added():
    u = pace.paced(TANK, 67)
    assert u.id == 'CNV_Pace67_' + TANK and u.names == {'pace': 'Upgrade_CNV_Pace67_' + TANK}
    assert f'id="{u.id}"' in u.xml and f'id="{TANK}"' not in u.xml
    assert f'<TriggeredBy>{u.names["pace"]}</TriggeredBy>' in u.xml and '<Modifier Type="SPEED" Value="67%"/>' in u.xml
    assert pace.is_pace_upgrade(u.names['pace']) and not pace.is_pace_upgrade('Upgrade_CNV_TideGun_High')
    assert simunits.speed_scale(u.xml, {u.names['pace']}) == pytest.approx(0.67)
    assert simunits.speed_scale(u.xml, set()) == 1.0 and simunits.speed_scale(u.xml, {'Upgrade_Other'}) == 1.0


def test_buildings_and_aircraft_do_not_set_the_pace():
    speeds = pace.movers([WALKER, TANK, 'JapanBarracks', 'JapanAntiAirAircraft'])
    assert speeds == {WALKER: 50.0, TANK: 75.0}


def test_the_wave_makes_the_faster_unit_slow_and_releases_it_on_arrival():
    m = force()
    copy = pace.copy_id(TANK, 67)
    assert copy in {u.id for u in m.units} and pace.copy_id(WALKER, 99) not in {u.id for u in m.units}
    send = [s for s in m.scripts if s.name.startswith('CNV ZZ - Wave 1 ') and not s.name.endswith('start')]
    for s in send:                                                      # (a script per difficulty)
        made = {a[1]: a[2] for a in s.do if a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT'}
        assert sorted(made.values()) == sorted([WALKER] * 2 + [copy] * 2)       # the slowest keeps retail's own template
        grants = [a for a in s.do if a[0] == 'NAMED_RECEIVE_UPGRADE']
        assert {a[2] for a in grants} == {n for n, t in made.items() if t == copy} and len(grants) == 2
        assert grants[0][1] == 'Upgrade_' + copy
    free = named(m, 'CNV ZZ - Pace 1 ')
    assert len(free) == 2 * 3                                           # each slowed unit, in each difficulty's script
    for s in free:
        assert s.when[0][0] == 'NAMED_INSIDE_AREA' and s.when[0][2] == 'CNV ZZ Pace west field'
        assert {a[0] for a in s.do} == {'NAMED_REMOVE_UPGRADE'} and len(s.do) == 2
    w = festival.SITES['west field']
    assert m.areas['CNV ZZ Pace west field'] == square(w.x, w.y, max(w.r, 250.0))      # (the site's own radius, if wider)
    assert parts.contract(m) == []
    assert contract.pace_released(m) == []


def test_a_force_of_one_speed_needs_no_copy():
    m = force(兵={'帝国武士': 3})
    assert not any(u.id.startswith('CNV_Pace') for u in m.units) and not named(m, 'CNV ZZ - Pace')


def test_a_grant_nobody_takes_away_is_named():
    m = force()
    m.scripts = [s for s in m.scripts if not s.name.startswith('CNV ZZ - Pace')]
    bad = contract.pace_released(m)
    assert bad and all('is slowed by Upgrade_CNV_Pace67_' in b and '(齐步)' in b for b in bad)
    # an area wait is what releases: a removal behind some other condition does not count
    m2 = force()
    for s in named(m2, 'CNV ZZ - Pace'):
        s.when = [('FLAG', 'x', 1)]
    assert contract.pace_released(m2)


def test_pace_needs_a_place_to_go():
    with pytest.raises(PlanError, match='齐步 needs 打 or 守'):
        force(打='猎杀')
    with pytest.raises(PlanError, match='齐步 needs 打 or 守'):
        small(规则=[{'当': '开局', '做': [{'出动': 'camp', '打': '猎杀', '齐步': '是'}]}])


def test_placed_troops_sent_off_together_are_placed_as_paced_copies_and_released_on_arrival():
    troops = [{'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'},
              {'单位': '帝国武士', '数量': 2, '在': 'north base', '阵营': '敌', '角色': 'foot'},
              {'单位': '海啸坦克', '数量': 2, '在': 'north base', '阵营': '敌', '角色': 'tank'}]
    m = small(开局={'部队': troops},
              规则=[{'当': '开局 + 0:30', '做': [{'出动': ['foot', 'tank'], '打': 'west field', '齐步': '是'}]}])
    copy = pace.copy_id(TANK, 67)
    assert copy in {u.id for u in m.units}
    tanks = [o for o in m.objects if o.name.startswith('UNIT - CNV ZZ tank')]
    foot = [o for o in m.objects if o.name.startswith('UNIT - CNV ZZ foot')]
    assert len(tanks) == 2 and {o.template for o in tanks} == {copy}            # placed as the copy from the start
    assert {o.template for o in foot} == {WALKER} and m.cast['tank 1'].template == copy
    send = [s for s in m.scripts if any(a[0] == 'NAMED_RECEIVE_UPGRADE' for a in s.do)]
    assert len(send) == 1
    grants = [a for a in send[0].do if a[0] == 'NAMED_RECEIVE_UPGRADE']
    assert {a[2] for a in grants} == {o.name for o in tanks} and grants[0][1] == 'Upgrade_' + copy
    free = named(m, 'CNV ZZ - Pace placed')
    assert len(free) == 2 and all(s.when[0] == ('NAMED_INSIDE_AREA', s.do[0][2], 'CNV ZZ Pace west field') for s in free)
    assert contract.pace_released(m) == [] and parts.contract(m) == []


def test_the_simulator_walks_a_slowed_unit_at_the_slowed_speed_and_back_at_full_when_released():
    """A tank (75) and a walker (50) sent together from the start to the west field: unpaced the tank is there well
    ahead; paced both stand in the goal within a couple of seconds, and the tank's speed is its own again after."""
    a, b = festival.SITES['start'], festival.SITES['west field']
    up = pace.paced(TANK, pace.percent(75, 50))
    straight = ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5

    def arrival(slow):
        make = [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'T', up.id if slow else TANK, 'Soviet_1/teamSoviet_1', 'A'),
                ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'W', WALKER, 'Soviet_1/teamSoviet_1', 'A')]
        if slow:
            make.append(('NAMED_RECEIVE_UPGRADE', up.names['pace'], 'T'))
        go = [('MOVE_NAMED_UNIT_TO', 'T', 'B'), ('MOVE_NAMED_UNIT_TO', 'W', 'B')]
        scripts = [Script('make', [], make + go),
                   Script('t', [('NAMED_INSIDE_AREA', 'T', 'Goal')], [('SET_FLAG', 'TT', 1)]),
                   Script('w', [('NAMED_INSIDE_AREA', 'W', 'Goal')], [('SET_FLAG', 'WW', 1)]),
                   Script('free', [('NAMED_INSIDE_AREA', 'T', 'Goal')], [('NAMED_REMOVE_UPGRADE', up.names['pace'], 'T')])]
        m = Mission(name='T', map=festival, scripts=scripts, units=[up])
        m.waypoints = {'A': (a.x, a.y), 'B': (b.x, b.y)}
        m.areas = {'Goal': square(b.x, b.y, 100)}
        s = sim.Sim(m)
        when = {}
        while len(when) < 2 and s.t < 600:
            s.step()
            for k, flag in (('T', 'TT'), ('W', 'WW')):
                if k not in when and s.flags.get(flag):
                    when[k] = s.t
            s.t = round(s.t + sim.DT, 3)
        return when, s
    free, _ = arrival(False)
    slow, s = arrival(True)
    assert free['W'] - free['T'] > 0.2 * straight / 50 * 0.5            # unpaced: the tank is there long before
    assert abs(slow['W'] - slow['T']) <= 3.0                            # paced: together
    assert s.bodies['T'].speed == pytest.approx(75.0)                   # released at the goal
