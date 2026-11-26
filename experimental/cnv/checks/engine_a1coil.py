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
from parts import Mission, Script, Test, counted, square

COIL, PLANT, ENG = 'SovietBaseDefenseAdvanced', 'SovietPowerPlant', 'AlliedEngineer'
A_LANES = {'base': (370, 0), 'removed': (385, 0), 'high': (393, 0), 'switch': (400, 0), 'order': (410, 0),
           'low': (194, 354)}
A_FLAGS = (('Coil A', '射程甲', ('base', 'removed', 'high', 'switch')), ('Coil B', '射程乙', ('order', 'low')))
RUN = {'a': 45, 'b': 45, 'c': 35, 'e': 30, 'f': 45, 'g': 290, 'h': 30}
SELECT, SPAWN = 'SpecialPowerChronosphereObjectSelect', 'SpecialPowerChronosphereObjectSpawn'


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


# e garrison reach (item 3): per lane a retail GE_TownHouse01 (BOX 56.4 x 36.3 half, angle 0: long side east-west)
# held by two of s1's conscripts (AK47 150), the player's engineer at (dx, dy) from its centre; both sides see all.
# 驻甲 = base 1, removed 10, high 100; 驻乙 = switch 1, order 10, low 100 (flags once the lane's engineer is hurt).
# 11-25 first run (x 140 / 180 / 200 / 225, y 175 / 200): 111 111 from s1 -- the house's AttributeModifier_Garrisoned
# aura (AffectContainedOnly) gives RANGE 175 %: 262.5. So now: box edge + 262.5: x <= 319, y <= 299 -> 111 / 10;
# centre + 262.5 -> 1 / 0. The simulator has no garrison aura (garrison.py): reach 150 from the house's spot -> 0 / 0.
G_LANES = {'base': (255, 0), 'removed': (280, 0), 'high': (310, 0), 'switch': (335, 0), 'order': (0, 280),
           'low': (0, 310)}
G_FLAGS = (('Gar A', '驻甲', ('base', 'removed', 'high')), ('Gar B', '驻乙', ('switch', 'order', 'low')))


def garrison_mission():
    m = Mission(name='CampA1Gar', map=probe_range, units=[])
    for lane, (dx, dy) in G_LANES.items():
        m.put('GE_TownHouse01', lane + ' gun', side='civ', role='house ' + lane, name='House ' + lane, angle=0.0)
        for k in (0, 1):
            m.put('SovietAntiInfantryInfantry', lane + ' gun', -40 + 80 * k, -160, side='s1', role=f'con {lane} {k}',
                  name=f'Con {lane} {k}')
        m.put(ENG, lane + ' gun', dx, dy, role='man ' + lane, name='Man ' + lane)
    return m


def garrison_check(m):
    t = Test()
    _start(m, t, ('MAP_REVEAL_ALL_PERM', m.player('s1')),
           *[('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', f'Con {lane} {k}', 'House ' + lane)
             for lane in G_LANES for k in (0, 1)])
    for counter, label, lanes in G_FLAGS:
        t.counters.append((counter, label))
        for k, lane in enumerate(lanes):
            t.scripts += _hurt('Man ' + lane, counter, 10 ** k, once=True)
    t.bench = [('bench_watch', dict(seconds=RUN['e'], every=1, sheet=False, lines=2))]
    return t


# f javelin (item 4 of 3): the player's javelin 'south' of s1's plant in each lane, ordered to attack it at 4 s;
# lock lanes toggle SpecialPower_RadarLock at 1 s. 锁远 = base plant's health % (lock, 240 off: past the plain 175),
# 锁近 = high (lock, 150 off), 平射 = order (no toggle, 150 off). Lock: 3.5 s on, then 40 a shot every 0.2-0.3 s
# (no reload): 25 shots, the plant (1000) down ~10 s after the order; plain: 25 a shot every ~0.6 s, 40 shots.
J_LANES = {'base': (240, True), 'high': (150, True), 'order': (150, False)}
J_COUNTERS = {'base': '锁远', 'high': '锁近', 'order': '平射'}


def javelin_mission():
    m = Mission(name='CampA1Jav', map=probe_range, units=[])
    for lane, (d, _) in J_LANES.items():
        m.put(PLANT, lane + ' gun', 0, d, side='s1', role='plant ' + lane, name='Plant ' + lane)
        m.put('AlliedAntiVehicleInfantry', lane + ' gun', role='jav ' + lane, name='Jav ' + lane)
    return m


def javelin_check(m):
    t = Test()
    _start(m, t, ('SET_MILLISECOND_TIMER', 'Jav lock', 1.0), ('SET_MILLISECOND_TIMER', 'Jav go', 4.0))
    t.scripts += [Script('Test - lock', [('TIMER_EXPIRED', 'Jav lock')],
                         [('NAMED_USE_COMMANDBUTTON_ABILITY', 'Jav ' + lane, 'Command_ToggleRadarLockSpecialPower')
                          for lane, (_, lock) in J_LANES.items() if lock]),
                  Script('Test - go', [('TIMER_EXPIRED', 'Jav go')],
                         [('NAMED_ATTACK_NAMED', 'Jav ' + lane, 'Plant ' + lane) for lane in J_LANES])]
    for lane, label in J_COUNTERS.items():
        counted('Jav ' + lane, label, t, health='Plant ' + lane)
    t.bench = [('bench_watch', dict(seconds=RUN['f'], every=1, sheet=False, lines=3))]
    return t


# g countdown and a Soviet cast (items 4, 5): three AI sides each own a retail AlliedSuperWeapon (Chronosphere,
# ReloadTime 180 s, POWERED, -75) and a plant (+100). s1 keeps its power (the control); s2's plant goes to the player
# at 60 s (s2 under-powered) and back at 90 s; at 20 s a script has s3's fire Select at 'Cd A' (its tank and
# conscript, NO_ATTACK) and Spawn at 'Cd B' 450 east. 就绪 = s1 ready (1) + s2 ready (10); 电 = s2 powered (1) +
# s2 under-powered (10); 传送 = s3's tank in B (1) + its conscript in B (10) + conscript alive (100) + tank alive (1000).
# Ready: s1 ~180 s; s2 paused 210, reset 270, unaffected 180. Cast: 1101 (the retail filter kills the infantry).
CD = {'s1': ('base gun', 'power 1'), 's2': ('high gun', 'power 2'), 's3': ('order gun', 'power 3')}
CD_A, CD_B = ('switch gun', 0, 300), ('switch gun', 450, 300)
CHRONO, TANK = 'AlliedSuperWeapon', 'AlliedAntiVehicleVehicleTech1'


def countdown_mission():
    m = Mission(name='CampA1Cd', map=probe_range, units=[])
    for side, (pad, plant) in CD.items():
        m.put(CHRONO, pad, side=side, role='chrono ' + side, name='Chrono ' + side)
        m.put(PLANT, plant, side=side, role='plant ' + side, name='Plant ' + side)
    m.put(TANK, CD_A[0], CD_A[1] - 30, CD_A[2], side='s3', role='tank', name='Cd tank')
    m.put('SovietAntiInfantryInfantry', CD_A[0], CD_A[1] + 30, CD_A[2], side='s3', role='con', name='Cd con')
    return m


def countdown_check(m):
    t = Test()
    s2 = m.player('s2')
    for w, (site, dx, dy) in (('Cd A', CD_A), ('Cd B', CD_B)):
        t.waypoints[w] = m.site(site, dx, dy)
    t.areas['Cd B'] = square(*m.site(*CD_B), 80.0)
    _start(m, t, *[('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in ('Cd tank', 'Cd con')],
           *[('SET_MILLISECOND_TIMER', f'Cd {k}', float(k)) for k in (20, 60, 90)])
    t.scripts += [Script('Test - cast', [('TIMER_EXPIRED', 'Cd 20')],
                         [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'Chrono s3', SELECT, 'Cd A'),
                          ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'Chrono s3', SPAWN, 'Cd B')]),
                  Script('Test - dark', [('TIMER_EXPIRED', 'Cd 60')],
                         [('NAMED_TRANSFER_OWNERSHIP_PLAYER', 'Plant s2', m.player('p1'))]),
                  Script('Test - light', [('TIMER_EXPIRED', 'Cd 90')], [('NAMED_TRANSFER_OWNERSHIP_PLAYER', 'Plant s2', s2)])]
    lines = (('Cd ready', '就绪', [(('SKIRMISH_SPECIAL_POWER_READY', m.player(s), SELECT), v) for s, v in (('s1', 1), ('s2', 10))]),
             ('Cd power', '电', [(('PLAYER_HAS_POWER', s2), 1), (('PLAYER_HAS_NO_POWER', s2), 10)]),
             ('Cd cast', '传送', [(('NAMED_INSIDE_AREA', 'Cd tank', 'Cd B'), 1), (('NAMED_INSIDE_AREA', 'Cd con', 'Cd B'), 10),
                                 (('NAMED_NOT_DESTROYED', 'Cd con'), 100), (('NAMED_NOT_DESTROYED', 'Cd tank'), 1000)]))
    for counter, label, rows in lines:
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts += [Script(f'Test - {counter} {k}', [cond], [('INCREMENT_COUNTER', v, counter)], once=False)
                      for k, (cond, v) in enumerate(rows)]
    t.bench = [('bench_watch', dict(seconds=RUN['g'], every=2, sheet=False, lines=3))]
    return t


# h Tanya's C4 on a gate (item 7): her C4 (AlliedCommandoAttachWeapon) takes STRUCTURE VEHICLE VALID_TARGET_FOR_C4
# but not WALL_PIECE. Per lane a gate piece 150 north of the player's Tanya, ordered to attack it at 3 s; the lane's
# counter is its health %: base MJ_PalaceWall01 (a1mc's fort wall, STRUCTURE, 3000), high SV_PCampWallGate01 (a small
# civilian building), order RM_CastleGate01 (BaseRockBig: UNATTACKABLE), removed MJ_PalaceWall01 owned by s1.
# Predicted: base, high, removed blown (0); order untouched (100).
GATES = {'base': ('MJ_PalaceWall01', 'civ', '宫墙'), 'high': ('SV_PCampWallGate01', 'civ', '营门'),
         'order': ('RM_CastleGate01', 'civ', '城门'), 'removed': ('MJ_PalaceWall01', 's1', '敌墙')}


def gate_mission():
    m = Mission(name='CampA1Gate', map=probe_range, units=[])
    for lane, (gate, side, _) in GATES.items():
        m.put(gate, lane + ' gun', 0, 150, side=side, role='gate ' + lane, name='Gate ' + lane, angle=0.0)
        m.put('AlliedCommandoTech1', lane + ' gun', role='tanya ' + lane, name='Tanya ' + lane)
    return m


def gate_check(m):
    t = Test()
    _start(m, t, ('SET_MILLISECOND_TIMER', 'Gate go', 3.0))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Gate go')],
                            [('NAMED_ATTACK_NAMED', 'Tanya ' + lane, 'Gate ' + lane) for lane in GATES]))
    for lane, (_, _, label) in GATES.items():
        counted('Gate ' + lane, label, t, health='Gate ' + lane)
    t.bench = [('bench_watch', dict(seconds=RUN['h'], every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_a1gate': gate_mission, 'engine_a1cd': countdown_mission, 'engine_a1gar': garrison_mission, 'engine_a1jav': javelin_mission,
           'engine_a1coil': mission, 'engine_a1near': lambda: mission(NEAR, 'CampA1Near'), 'engine_a1cap': captured_mission, 'engine_a1pow': power_mission}
CHECKS = {'engine_a1gate': {'h': gate_check}, 'engine_a1cd': {'g': countdown_check}, 'engine_a1gar': {'e': garrison_check}, 'engine_a1jav': {'f': javelin_check},
          'engine_a1coil': {'a': range_check}, 'engine_a1near': {'d': lambda m: range_check(m, FORCED)}, 'engine_a1cap': {'b': captured_check},
          'engine_a1pow': {'c': power_check}}
