"""A1 (11-25, coord_1125_a1_bench.md items 1, 2, 4b): the retail tesla coil (SovietBaseDefenseAdvanced, its gun
SovietBaseDefenseAdvancedTeslaGun AttackRange 350, PreAttackDelay 2.5 s, 450 a shot; VisionRange 360; Geometry BOX
10 x 10, then 15 x 15) against a retail SovietPowerPlant (BOX 30 x 30, 1000 health). On the range probe map.

  a range: six lanes, s1's coil on '<lane> gun' and the player's plant at a centre distance east of it:
     base 370 (box edge 340), removed 385, high 393 (edge 363), switch 400, order 410 (edge 380), and low at a1mc's
     own P4 offset from its north coil (+194, +354: centre 404, box edge 363, diagonal). 射程甲 = base 1, removed 10,
     high 100, switch 1000; 射程乙 = order 1, low 10 (a flag once the lane's plant is hurt; healed back each time).
  b captured: s1's coil on 'base gun', s1's plant 300 east of it (in reach on every model), the player's engineer 120
     east of that, ordered in at 10 s; two more s1 plants on the power pads keep the coil powered (+300 -75).
     占打 = plant hits after the capture (healed back) + 1000 while the player owns the plant.
  c design power: s1 = two coils, AlliedSuperWeapon, AlliedConstructionYard and two plants: load 2 x 75 + 75 - 50 =
     175 against 200; the player's engineer takes one plant at 10 s (100 left). 电 = excess 25 +1, excess -75 +2,
     excess < 0 +4, no power +10, has power +100.

Simulator (engine/combat/range.in_range, bounding circles: coil 14.1, plant 42.4, reach 345): fires at centre
distance <= 401.6 -- base, removed, high, switch yes; order, low no. A box-edge reading (coil centre to the plant's
box <= 350) says base, removed yes; high, switch, order, low no.
"""
from maps import probe_range
from parts import Mission, Script, Test

COIL, PLANT, ENG = 'SovietBaseDefenseAdvanced', 'SovietPowerPlant', 'AlliedEngineer'
A_LANES = {'base': (370, 0), 'removed': (385, 0), 'high': (393, 0), 'switch': (400, 0), 'order': (410, 0),
           'low': (194, 354)}
A_FLAGS = (('Coil A', '射程甲', ('base', 'removed', 'high', 'switch')), ('Coil B', '射程乙', ('order', 'low')))
RUN = {'a': 45, 'b': 45, 'c': 35}


# near (11-25, a read 0 0 throughout: nothing fired even at 370): base 300, removed 320, high 340, switch 355
# picked by the coil; order 370 and low the P4 offset ordered (NAMED_ATTACK_NAMED at 10 s: reach without vision)
NEAR = {'base': (300, 0), 'removed': (320, 0), 'high': (340, 0), 'switch': (355, 0), 'order': (370, 0),
        'low': (194, 354)}
FORCED = ('order', 'low')


def mission(lanes=A_LANES, name='CampA1Coil'):
    m = Mission(name=name, map=probe_range, units=[])
    for lane, (dx, dy) in lanes.items():
        m.put(COIL, lane + ' gun', side='s1', role='coil ' + lane, name='Coil ' + lane)
        m.put(PLANT, lane + ' gun', dx, dy, role='plant ' + lane, name='Plant ' + lane)
    for k, (pad, dy) in enumerate((('power 1', 0), ('power 2', 0), ('power 3', 0), ('power 1', 200), ('power 2', 200))):
        m.put(PLANT, pad, 0, dy, side='s1', role=f's1 plant {k}', name=f'Coil s1 plant {k}')
    return m


def captured_mission():
    m = Mission(name='CampA1Cap', map=probe_range, units=[])
    m.put(COIL, 'base gun', side='s1', role='coil', name='Coil base')
    m.put(PLANT, 'base gun', 300, 0, side='s1', role='taken', name='Plant taken')
    m.put(ENG, 'base gun', 420, 0, role='man', name='Man taken')
    for k, pad in enumerate(('power 1', 'power 2')):
        m.put(PLANT, pad, side='s1', role=f's1 plant {k}', name=f'Coil s1 plant {k}')
    return m


def power_mission():
    m = Mission(name='CampA1Pow', map=probe_range, units=[])
    m.put(COIL, 'base gun', side='s1', role='coil', name='Coil base')
    m.put(COIL, 'high gun', side='s1', role='coil 2', name='Coil high')
    m.put('AlliedSuperWeapon', 'order gun', side='s1', role='chrono', name='Coil chrono')
    m.put('AlliedConstructionYard', 'removed gun', side='s1', role='yard', name='Coil yard')
    m.put(PLANT, 'power 1', side='s1', role='kept', name='Plant kept')
    m.put(PLANT, 'switch gun', side='s1', role='taken', name='Plant taken')
    m.put(ENG, 'switch gun', 0, -180, role='man', name='Man taken')
    return m


def _start(m, t, *more):
    t.scripts = [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')), *more]),
                 Script('Test - no budget', [], [('PLAYER_SET_MONEY', m.player('s1'), 0)], once=False)]


def _hurt(name, counter, value, once):
    """+value to counter when `name` is hurt (once: a flag), then heal it back."""
    return [Script(f'Test - hurt {name}', [('UNIT_HEALTH', name, 0, 100)], [('INCREMENT_COUNTER', value, counter)],
                   once=once),
            Script(f'Test - heal {name}', [('UNIT_HEALTH', name, 0, 100)], [('UNIT_SET_HEALTH', name, 100.0)],
                   once=False)]


def range_check(m, forced=()):
    t = Test()
    _start(m, t, ('SET_MILLISECOND_TIMER', 'Coil order', 10.0))
    if forced:
        t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Coil order')],
                                [('NAMED_ATTACK_NAMED', 'Coil ' + lane, 'Plant ' + lane) for lane in forced]))
    for counter, label, lanes in A_FLAGS:
        t.counters.append((counter, label))
        for k, lane in enumerate(lanes):
            t.scripts += _hurt('Plant ' + lane, counter, 10 ** k, once=True)
    t.bench = [('bench_watch', dict(seconds=RUN['a'], every=1, sheet=False, lines=2))]
    return t


def captured_check(m):
    t = Test()
    _start(m, t, ('SET_MILLISECOND_TIMER', 'Coil enter', 10.0))
    t.scripts.append(Script('Test - enter', [('TIMER_EXPIRED', 'Coil enter')],
                            [('NAMED_GARRISON_SPECIFIC_BUILDING', 'Man taken', 'Plant taken')]))
    t.counters.append(('Coil taken', '占打'))
    # hits only once the player owns it (s1's coil never shoots its own plant)
    t.scripts += [Script('Test - hurt taken', [('UNIT_HEALTH', 'Plant taken', 0, 100),
                                               ('NAMED_OWNED_BY_PLAYER', m.player('p1'), 'Plant taken')],
                         [('INCREMENT_COUNTER', 1, 'Coil taken')], once=False),
                  Script('Test - heal taken', [('UNIT_HEALTH', 'Plant taken', 0, 100)],
                         [('UNIT_SET_HEALTH', 'Plant taken', 100.0)], once=False)]
    t.counters.append(('Coil owner', '归属'))
    t.scripts += [Script('Test - owner 0', [], [('SET_COUNTER', 'Coil owner', 0)], once=False),
                  Script('Test - owner 1', [('NAMED_OWNED_BY_PLAYER', m.player('p1'), 'Plant taken')],
                         [('SET_COUNTER', 'Coil owner', 1000)], once=False)]
    t.bench = [('bench_watch', dict(seconds=RUN['b'], every=1, sheet=False, lines=2))]
    return t


def power_check(m):
    t = Test()
    s1 = m.player('s1')
    _start(m, t, ('SET_MILLISECOND_TIMER', 'Coil enter', 10.0))
    t.scripts.append(Script('Test - enter', [('TIMER_EXPIRED', 'Coil enter')],
                            [('NAMED_GARRISON_SPECIFIC_BUILDING', 'Man taken', 'Plant taken')]))
    t.counters.append(('Coil power', '电'))
    t.scripts.append(Script('Test - reset power', [], [('SET_COUNTER', 'Coil power', 0)], once=False))
    for k, (cond, value) in enumerate(((('PLAYER_EXCESS_POWER_COMPARE_VALUE', s1, 2, 25), 1),
                                       (('PLAYER_EXCESS_POWER_COMPARE_VALUE', s1, 2, -75), 2),
                                       (('PLAYER_EXCESS_POWER_COMPARE_VALUE', s1, 0, 0), 4),
                                       (('PLAYER_HAS_NO_POWER', s1), 10), (('PLAYER_HAS_POWER', s1), 100))):
        t.scripts.append(Script(f'Test - power {k}', [cond], [('INCREMENT_COUNTER', value, 'Coil power')], once=False))
    t.counters.append(('Coil owner', '归属'))
    t.scripts += [Script('Test - owner 0', [], [('SET_COUNTER', 'Coil owner', 0)], once=False),
                  Script('Test - owner 1', [('NAMED_OWNED_BY_PLAYER', m.player('p1'), 'Plant taken')],
                         [('SET_COUNTER', 'Coil owner', 1000)], once=False)]
    t.bench = [('bench_watch', dict(seconds=RUN['c'], every=1, sheet=False, lines=2))]
    return t


MISSION = {'engine_a1coil': mission, 'engine_a1near': lambda: mission(NEAR, 'CampA1Near'), 'engine_a1cap': captured_mission, 'engine_a1pow': power_mission}
CHECKS = {'engine_a1coil': {'a': range_check}, 'engine_a1near': {'d': lambda m: range_check(m, FORCED)}, 'engine_a1cap': {'b': captured_check},
          'engine_a1pow': {'c': power_check}}
