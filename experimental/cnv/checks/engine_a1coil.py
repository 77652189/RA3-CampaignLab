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
from model import status
from parts import Mission, Script, Test, counted, square

COIL, PLANT, ENG = 'SovietBaseDefenseAdvanced', 'SovietPowerPlant', 'AlliedEngineer'
A_LANES = {'base': (370, 0), 'removed': (385, 0), 'high': (393, 0), 'switch': (400, 0), 'order': (410, 0),
           'low': (194, 354)}
A_FLAGS = (('Coil A', '射程甲', ('base', 'removed', 'high', 'switch')), ('Coil B', '射程乙', ('order', 'low')))
RUN = {'a': 45, 'b': 45, 'c': 35, 'e': 30, 'f': 45, 'g': 290, 'h': 30, 'i': 60}
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


# j where a passenger sits (11-26, review 135 ①): e's run (255 east missed, 310 hit; same house, same entry in every
# lane) is no one shape from the house. e again, plus 位甲 (base removed high) / 位乙 (switch order low): two digits a
# lane, con 0's then con 1's (lane k of the three at 10 ** 2k), every frame; digit = 3 x (1 east / 2 west of the
# house's centre by > 3) + (1 north / 2 south). A conscript kept at the centre reads 0 (the simulator's); one at a
# garrison bone its side. Same digits in every lane: the bone is the entry order's; different ones that match e's
# hits: a bone each house rolls, the reach (262.5) from it.
J_SIDES = (('east', 3, (3, 90, -70, 70)), ('west', 6, (-90, -3, -70, 70)), ('north', 1, (-90, 90, 3, 70)),
           ('south', 2, (-90, 90, -70, -3)))


def seat_check(m):
    t = garrison_check(m)
    for (_, label, lanes), counter in zip(G_FLAGS, ('Seat A', 'Seat B')):
        t.counters.append((counter, label.replace('驻', '位')))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        for i, lane in enumerate(lanes):
            x, y = m.site(lane + ' gun', 0, 0)
            for side, v, (x0, x1, y0, y1) in J_SIDES:
                area = f'Seat {lane} {side}'
                t.areas[area] = [(x + x0, y + y0), (x + x1, y + y0), (x + x1, y + y1), (x + x0, y + y1)]
                t.scripts += [Script(f'Test - {area} {k}', [('NAMED_INSIDE_AREA', f'Con {lane} {k}', area)],
                                     [('INCREMENT_COUNTER', v * 10 ** (2 * i + k), counter)], once=False)
                              for k in (0, 1)]
    t.bench = [('bench_watch', dict(seconds=RUN['e'], every=1, sheet=False, lines=4))]
    return t


# k j with every engineer deleted in the start script (no target): the seats a passenger takes by itself (11-26:
# 258788 / 788428, each house its own; l / m: drawn from the logic random stream in entry order).
def bare_seat_check(m):
    t = seat_check(m)
    t.scripts[0].do +=[('NAMED_DELETE', 'Man ' + lane) for lane in G_LANES]
    return t


# l k with the twelve put in in the reverse order (low con 1 first, base con 0 last; the same objects, the same ids):
# k's 258788 / 788428 again = by id; the n-th put in seated as k's n-th (位甲 824887, 位乙 887852) = drawn in entry
# order (seeded random).
def reversed_seat_check(m):
    t = bare_seat_check(m)
    do = t.scripts[0].do
    put = [a for a in do if a[0] == 'NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY']
    t.scripts[0].do = do[:2] + put[::-1] + do[2 + len(put):]
    return t


# m k with three SET_RANDOM_COUNTER draws (into 驻甲, no engineer to flag it: 1..1000) before the twelve go in: other seats than k's = the seats are
# the game's logic random stream's (l: in entry order); k's again = a count of their own.
def drawn_seat_check(m):
    t = bare_seat_check(m)
    t.scripts[0].do[2:2] = [('SET_RANDOM_COUNTER', 'Gar A', 1, 1000)] * 3
    return t


# n j with the base / removed / high / switch engineers moved 150 east / west / north / south of their house first
# (every bone reaches): a passenger aiming moves to the free bone nearest its target (j: high's con 0 to 08) -> each
# pair on the two bones nearest, whatever it drew: base 08 05 (digits 3 5), removed 04 12 (8 7), high 01 03 (4 4),
# switch 09 07 (2 8); order / low as j. No move: k's draws (88 87 25 28).
N_NEAR = {'base': (150, 0), 'removed': (-150, 0), 'high': (0, 150), 'switch': (0, -150)}


def near_seat_check(m):
    t = seat_check(m)
    for lane, (dx, dy) in N_NEAR.items():
        t.waypoints['Test Near ' + lane] = m.site(lane + ' gun', dx, dy)
    t.scripts[0].do[2:2] = [('UNIT_TELEPORT_TO_WAYPOINT', 'Man ' + lane, 'Test Near ' + lane) for lane in N_NEAR]
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
# but not WALL_PIECE. Per lane a target 150 north of the player's Tanya, ordered to attack it at 3 s: base
# MJ_PalaceWall01 (a1mc's fort wall, STRUCTURE, 3000), high SV_PCampWallGate01 (a small civilian building), order
# RM_CastleGate01 (BaseRockBig: UNATTACKABLE), removed MJ_PalaceWall01 owned by s1; controls switch s1's
# SovietPowerPlant, low s1's Hammer tank (NO_ATTACK; 11-15 kind: her charge killed a King Oni). 11-25 first run
# (CampA1GateH_mcp_1125_232153, health % only): every wall 100 to s31, nothing told whether she went. So now a digit a
# lane, every frame: +1 the target stands, +2 Tanya inside a 70 square round it, +4 Tanya out of a 30 square round
# her start. 甲 = base high order, 乙 = removed switch low; 宫墙 / 敌墙 their health %.
# Predicted: all but order blown (6 while she is on it, 4 once she has let go); order 1 (no attack) or 5 / 7.
# 11-25 second run (run_queue, 756e44ab): 甲 111 to s31 -- she never leaves home for a neutral target, wall, gate or
# rock alike (the script's attack is dropped); 乙 s1 711, s2 655, s3 677, s4 477, s5-s31 066: the s1 wall, the plant
# and the tank she goes for by herself before the order (enemies), each blown ~1 s after she is on it (the wall s5);
# back home after the tank. A dead target's health % counter stays at its last value (敌墙 100).
GATES = {'base': ('MJ_PalaceWall01', 'civ'), 'high': ('SV_PCampWallGate01', 'civ'), 'order': ('RM_CastleGate01', 'civ'),
         'removed': ('MJ_PalaceWall01', 's1'), 'switch': (PLANT, 's1'), 'low': ('SovietAntiVehicleVehicleTech1', 's1')}
GATE_LINES = (('Gate A', '甲', ('base', 'high', 'order')), ('Gate B', '乙', ('removed', 'switch', 'low')))


def gate_mission():
    m = Mission(name='CampA1Gate', map=probe_range, units=[])
    for lane, (gate, side) in GATES.items():
        m.put(gate, lane + ' gun', 0, 150, side=side, role='gate ' + lane, name='Gate ' + lane, angle=0.0)
        m.put('AlliedCommandoTech1', lane + ' gun', role='tanya ' + lane, name='Tanya ' + lane)
    return m


def gate_check(m):
    t = Test()
    _start(m, t, ('SET_MILLISECOND_TIMER', 'Gate go', 3.0), ('UNIT_CHANGE_OBJECT_STATUS', 'Gate low', 'NO_ATTACK', 1))
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Gate go')],
                            [('NAMED_ATTACK_NAMED', 'Tanya ' + lane, 'Gate ' + lane) for lane in GATES]))
    for lane in GATES:
        t.areas['Gate near ' + lane] = square(*m.site(lane + ' gun', 0, 150), 70.0)
        t.areas['Gate home ' + lane] = square(*m.site(lane + ' gun', 0, 0), 30.0)
    for counter, label, lanes in GATE_LINES:
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        for k, lane in enumerate(lanes):
            rows = ((('NAMED_NOT_DESTROYED', 'Gate ' + lane), 1),
                    (('NAMED_INSIDE_AREA', 'Tanya ' + lane, 'Gate near ' + lane), 2),
                    (('NAMED_OUTSIDE_AREA', 'Tanya ' + lane, 'Gate home ' + lane), 4))
            t.scripts += [Script(f'Test - {counter} {lane} {v}', [cond], [('INCREMENT_COUNTER', v * 10 ** k, counter)],
                                 once=False) for cond, v in rows]
    for lane, label in (('base', '宫墙'), ('removed', '敌墙')):
        counted('Gate hp ' + lane, label, t, health='Gate ' + lane)
    m.ext = True           # ra3ext's clock, a logic frame for each archived frame (11-25's sN ran ~2 s behind, E265)
    t.bench = [('bench_watch', dict(seconds=RUN['h'], every=0.5, sheet=False, lines=4))]
    return t


C4_LANES = (('base', '正常', None), ('high', '击杀', 'NAMED_KILL'), ('order', '删除', 'NAMED_DELETE'))


def c4_interrupt_mission():
    m = Mission(name='CampC4Break', map=probe_range, units=[])
    for lane, _, _ in C4_LANES:
        m.put('AlliedCommandoTech1', lane + ' gun', name=f'C4 Tanya {lane}')
        for charge, distance in (('first', 150), ('second', 205)):
            m.put(GATES['low'][0], lane + ' gun', 0, distance, side='s1', angle=0.0, name=f'C4 {charge} {lane}')
    return m


def c4_interrupt_check(m):
    """Kill or delete the first tank as soon as Tanya attaches, with one uninterrupted control.

    Predict that the second attachment has its own fuse, like the uninterrupted control.
    Pack first attached frames + 100 * second attached frames + 10000 once the second dies.
    Count only while Tanya is attached and the corresponding live tank is marked.
    """
    t = Test()
    start = []
    for lane, label, interruption in C4_LANES:
        tanya, first, second = (f'C4 {role} {lane}' for role in ('Tanya', 'first', 'second'))
        counter = f'C4 Fuse {lane}'
        t.counters.append((counter, label))
        start.extend(('UNIT_CHANGE_OBJECT_STATUS', target, 'NO_ATTACK', 1) for target in (first, second))
        start.append(('NAMED_ATTACK_NAMED', tanya, first))
        attached = ('UNIT_HAS_OBJECT_STATUS', tanya, status('ATTACHED'))
        for target, place in ((first, 1), (second, 100)):
            t.scripts.append(Script(f'Test - count {target}', [attached, ('NAMED_NOT_DESTROYED', target),
                                    ('UNIT_HAS_OBJECT_STATUS', target, status('MARCH_OF_DEATH'))],
                                    [('INCREMENT_COUNTER', place, counter)], once=False))
        if interruption:
            t.scripts.append(Script(f'Test - interrupt {lane}', [attached], [(interruption, first)]))
        t.scripts.extend((Script(f'Test - retarget {lane}', [('NAMED_DESTROYED', first)],
                                 [('NAMED_ATTACK_NAMED', tanya, second)]),
                          Script(f'Test - finish {lane}', [('NAMED_DESTROYED', second)],
                                 [('INCREMENT_COUNTER', 10000, counter)])))
    t.scripts.insert(0, Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')), *start]))
    m.ext = True
    t.bench = [('bench_watch', dict(seconds=14., every=.5, sheet=False, lines=len(t.counters)))]
    return t


# i landing craft (item 7): a1mc's city is a level-1 plateau over the bay; its one ramp is the Aquatic Park beach
# (Ramp (2880, 3110) -> (2880, 2860), 300 wide). Read on a1mc's own terrain (work/mappage/a1mc/a1mc.py, the draft;
# its objects are neutral walls and one empty Soviet house). The player's Bullfrog (SovietAntiAirShip, AMPHIBIOUS)
# per lane in the water, ordered at 1 s to a point ~250 inside the shore: beach in front of the ramp (the control),
# west 230 west of it, pier between two Soviet piers 700 east. 登陆 a digit a lane (beach 1, west 10, pier 100),
# latched: +1 at the goal, +2 once in the beach's box. Climbing the cliff straight = 1, round by the beach = 3,
# never up = 0. Predicted (the ramp is the only way up): 3 3 3, or pier 0 if the way round is past the run.
# 11-26 (run_queue): s1 22, s3 32, s5 33, s11 233, s19-s61 333. Pier: out past the pier tips, into the beach box at
# s11, at its goal s19 (~1200 round at ~120 a second) -- not the 250 straight up: the cliff is not climbed. West
# (80 off the ramp's edge) is in the box by s1 and at its goal by s3: either way is as long, it tells nothing.
LAND = {'beach': ((2880, 3200), (2880, 2700)), 'west': ((2650, 3100), (2680, 2720)),
        'pier': ((3580, 3300), (3580, 2950))}
BEACH_BOX = (2880, 2985, 150)


def land_mission():
    import importlib.util
    import os
    import labpaths
    path = os.path.join(labpaths.WORK, 'mappage', 'a1mc', 'a1mc.py')
    spec = importlib.util.spec_from_file_location('engine_a1land_map', path)
    a1mc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a1mc)
    m = Mission(name='CampA1Land', map=a1mc, units=[])
    bx, by = a1mc.SITES['beach'].x, a1mc.SITES['beach'].y
    for lane, ((x, y), _) in LAND.items():
        m.put('SovietAntiAirShip', 'beach', x - bx, y - by, role='frog ' + lane, name='Frog ' + lane)
    from checks.probe_view import open_in_view
    return open_in_view(m, 'A1Land')    # a1mc's start is in the city corner, past the screen's reach


def land_check(m):
    t = Test()
    _start(m, t, ('MAP_REVEAL_ALL_PERM', m.player('p1')))
    order = []
    t.areas['Land beach'] = square(*BEACH_BOX)
    t.counters.append(('Land', '登陆'))
    for k, (lane, (_, goal)) in enumerate(LAND.items()):
        t.waypoints['Land ' + lane] = goal
        t.areas['Land at ' + lane] = square(*goal, 80.0)
        order += m.order('move', ['Frog ' + lane], 'Land ' + lane, crew='Land' + lane.title())
        t.scripts += [Script(f'Test - land {lane} {v}', [('NAMED_INSIDE_AREA', 'Frog ' + lane, area)],
                             [('INCREMENT_COUNTER', v * 10 ** k, 'Land')])
                      for area, v in (('Land at ' + lane, 1), ('Land beach', 2))]
    t.scripts.append(Script('Test - land go', [], order))
    t.bench = [('bench_watch', dict(seconds=RUN['i'], every=2, sheet=False, lines=2))]
    return t


MISSION = {'engine_a1land': land_mission, 'engine_a1gate': gate_mission, 'engine_a1cd': countdown_mission, 'engine_a1gar': garrison_mission, 'engine_a1jav': javelin_mission,
           'engine_a1coil': mission, 'engine_a1near': lambda: mission(NEAR, 'CampA1Near'), 'engine_a1cap': captured_mission, 'engine_a1pow': power_mission}
CHECKS = {'engine_a1land': {'i': land_check}, 'engine_a1gate': {'h': gate_check}, 'engine_a1cd': {'g': countdown_check}, 'engine_a1gar': {'e': garrison_check, 'j': seat_check, 'k': bare_seat_check, 'l': reversed_seat_check, 'm': drawn_seat_check, 'n': near_seat_check}, 'engine_a1jav': {'f': javelin_check},
          'engine_a1coil': {'a': range_check}, 'engine_a1near': {'d': lambda m: range_check(m, FORCED)}, 'engine_a1cap': {'b': captured_check},
          'engine_a1pow': {'c': power_check}}

MISSION['engine_c4break'] = c4_interrupt_mission
CHECKS['engine_c4break'] = {'a': c4_interrupt_check}
