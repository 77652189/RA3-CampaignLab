"""Retail-campaign actions, batch 13 (round 226): the dolphin's jump (water), the bear's roar _ON_NAMED once more, and
whether the campaign bomber drop's press counts as cast at all -- one run. Mission on maps/probe_air.py: the dolphins in
its sea trench (x 2160..2440 full depth, y 3050..3550), the rest on the flat east of 'air B'; everyone but the stores
holding fire (NO_ATTACK). PRESS (3 s); what the data predicts in brackets (15 logic frames a second).
  DJ  AlliedAntiNavalScout (dolphin) NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT Command_ActivateJumpSpecialPower 250
      north (a04's intro, 8 uses): WeaponFireSpecialAbilityUpdate, UnpackTime 0, StartAbilityRange 300, weapon
      AlliedAntiNavalScoutJumpWeapon ProjectileSelf at 160 a second -- the Sickle's leap's shape (Sim.leap_press);
      DQ another dolphin told to MOVE 250 north. [DJ there ~1.6 s after the press]
  RN  SovietScoutInfantry (bear) the roar _ON_NAMED its conscript C2 60 north (round 224: held nobody, but C2 was sent
      away 0.3 s after the press); RF another bear, the same _ON_NAMED C4 300 north (does the bear walk over?); RB a
      third, the roar pressed plainly, C1 60 north (the control). The conscripts (s4) stand till PRESS + 5 s, then are
      sent 300 further north. [C1 held to ~13 s; C2 / C4 walk at 8 s if the object order is refused]
  DP  CAMP_PowerStore_AlliedBomberDrop (the player's) and DS (s4's): the button Command_CAMPAlliedBomberDrop2 at a spot
      400 north at PRESS, NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT SpecialPowerCAMPAlliedBomberDrop2 at LATE (12 s).
      Hypothesis E (round 225's table): does PLAYER_TRIGGERED_SPECIAL_POWER see the press? [engine_super: it sees a
      building's cast for a frame or so]
Counters:
  跳 = DJ in its jump square + 10 x DQ in its square
  吼 = C1 in its start square + 10 x C2 + 100 x C4 + 1000 x RF within 120 of C4's start
  放 = frames PLAYER_TRIGGERED_SPECIAL_POWER(p1, the drop) + 100 x (s4, the drop) + 10 000 x (p1, SpecialPower_Roar)
  机 = the player's bombers anywhere (0-2) + 10 x s4's + 100 x the player's GIs round DP's spot >= 1 + 1000 x s4's
  BENCH 11-14 (round 226, run_queue; CampActsWetAll_mcp_1114_091622; tests/test_simbench.py
    test_acts_wet_all_as_the_bench; bench row s_k = simulator k + 1): s1-s2 0 111 0 0 | s3 0 111 10101 0 |
    s4 11 111 20101 0 | s5-s6 11 1111 20101 0 | s7-s11 11 1111 30101 0 | s12 11 1111 30202 0 | s13 11 1110 30202 0 |
    s14-s16 11 1100 30202 0 | s17-s27 11 1000 30202 0.
    DJ / DQ: both in their squares by s4 (the jump as Sim.leap_press; the swimmer as fast: not telling). The roar
    _ON_NAMED does go off: RF walked up to C4 (1000 at s5), cast s7; RN cast s4, a reading after RB's s3; C2 / C4 held
    10 s like C1 (round 224's "nobody held" was C2 sent away at 3.3 s: held outside its square). Each cast seen once by
    PLAYER_TRIGGERED_SPECIAL_POWER (10 000). The drop: both stores' button seen cast at the press (1 / 100), the
    by-name casts at 12 s once more (s12) -- the press counts, and still no bomber, no GI (机 0): what fails is the
    OCL's creation (CREATE_AT_EDGE_NEAR_SOURCE), not the press; left inferred (inventory NOTES).
"""
from maps import probe_air
from parts import Mission, Script, Test, square, status
import checks.engine_scripts8 as s8

MAN = 'SovietAntiInfantryInfantry'
BEAR = 'SovietScoutInfantry'
DOLPHIN = 'AlliedAntiNavalScout'
STORE = 'CAMP_PowerStore_AlliedBomberDrop'
BOMBER = 'CAMP_AlliedBomberAircraft_Infantry_1'
GI = 'AlliedAntiInfantryInfantry'
DROP_POWER = 'SpecialPowerCAMPAlliedBomberDrop2'
ROAR = 'Command_ActivateRoarSpecialPower'
ROAR_POWER = 'SpecialPower_Roar'
JUMP = 'Command_ActivateJumpSpecialPower'
LAND, SEA = 'air B', 'air sea S'
# row -> (template, x, y, side, site)
ROWS = {'DJ': (DOLPHIN, 2400.0, 3120.0, 'p1', SEA), 'DQ': (DOLPHIN, 2200.0, 3120.0, 'p1', SEA),
        'RB': (BEAR, 4400.0, 2000.0, 'p1', LAND), 'C1': (MAN, 4400.0, 2060.0, 's4', LAND),
        'RN': (BEAR, 3400.0, 2000.0, 'p1', LAND), 'C2': (MAN, 3400.0, 2060.0, 's4', LAND),
        'RF': (BEAR, 3900.0, 2000.0, 'p1', LAND), 'C4': (MAN, 3900.0, 2300.0, 's4', LAND),
        'DP': (STORE, 3400.0, 2700.0, 'p1', LAND), 'DS': (STORE, 4400.0, 2700.0, 's4', LAND)}
JUMPS = {'DJ': 250.0, 'DQ': 250.0}                 # north
SPOT = 400.0                                       # a store's spot, north of it
PRESS, LATE, RUN = 3.0, 12.0, 26.0
AWAY = PRESS + 5.0


def _n(part):
    return f'UNIT - CNV A13 {part}'


def mission():
    m = Mission(name='CampActsWet', map=probe_air, units=[], facts={})
    m.spawns |= {r[0] for r in ROWS.values()} | {BOMBER, GI, 'AlliedAntiVehicleInfantry'}
    for row, (tmpl, x, y, side, site) in ROWS.items():
        o = probe_air.SITES[site]
        m.put(tmpl, site, x - o.x, y - o.y, side=side, angle=0.0, name=_n(row), role=row.lower())
        if row in JUMPS:
            m.waypoint(f'jump {row}', f'CNV A13 Jump {row}', site, x - o.x, y + JUMPS[row] - o.y)
        if row.startswith('C'):
            m.waypoint(f'away {row}', f'CNV A13 Away {row}', site, x - o.x, y + 300.0 - o.y)
        if row in ('DP', 'DS'):
            m.waypoint(f'spot {row}', f'CNV A13 Spot {row}', site, x - o.x, y + SPOT - o.y)
    return m


def all_(m):
    t = Test()
    hold = [('UNIT_CHANGE_OBJECT_STATUS', _n(r), status('NO_ATTACK'), 1) for r in ROWS if r not in ('DP', 'DS')]
    s8.at(t, 'hold', 0.1, hold + [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'press', PRESS, [
        ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n('DJ'), JUMP, m.mark('jump DJ')),
        ('MOVE_NAMED_UNIT_TO', _n('DQ'), m.mark('jump DQ')),
        ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('RB'), ROAR),
        ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', _n('RN'), ROAR, _n('C2')),
        ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', _n('RF'), ROAR, _n('C4')),
        ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n('DP'), 'Command_CAMPAlliedBomberDrop2', m.mark('spot DP')),
        ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n('DS'), 'Command_CAMPAlliedBomberDrop2', m.mark('spot DS'))])
    s8.at(t, 'away', AWAY, [('MOVE_NAMED_UNIT_TO', _n(c), m.mark(f'away {c}')) for c in ('C1', 'C2', 'C4')])
    s8.at(t, 'late', LATE, [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', _n(r), DROP_POWER, m.mark(f'spot {r}'))
                            for r in ('DP', 'DS')])
    area = {}
    for row in JUMPS:
        area[row] = f'Test A13 Jump {row}'
        t.areas[area[row]] = square(*m.point(f'jump {row}'), 60.0)
    for row in ('C1', 'C2', 'C4'):
        area[row] = f'Test A13 Start {row}'
        t.areas[area[row]] = square(ROWS[row][1], ROWS[row][2], 30.0)
    area['RF'] = 'Test A13 Near C4'
    t.areas[area['RF']] = square(ROWS['C4'][1], ROWS['C4'][2], 120.0)
    t.areas['Test A13 Whole'] = square(2500.0, 2500.0, 2500.0)
    for r in ('DP', 'DS'):
        t.areas[f'Test A13 Spot {r}'] = square(*m.point(f'spot {r}'), 400.0)
    inside = lambda row: ('NAMED_INSIDE_AREA', _n(row), area[row])  # noqa: E731
    s8.total(t, 'CNV_A13_Jump', '跳', [(1, inside('DJ')), (10, inside('DQ'))])
    s8.total(t, 'CNV_A13_Roar', '吼', [(1, inside('C1')), (10, inside('C2')), (100, inside('C4')),
                                       (1000, inside('RF'))])
    p1, s4 = m.player('p1'), m.player('s4')
    t.counters.append(('CNV_A13_Cast', '放'))       # only added to: a cast is seen for a frame or so
    for who, power, w in ((p1, DROP_POWER, 1), (s4, DROP_POWER, 100), (p1, ROAR_POWER, 10000)):
        t.scripts.append(Script(f'Test - A13 cast {w}', [('PLAYER_TRIGGERED_SPECIAL_POWER', who, power)],
                                [('INCREMENT_COUNTER', w, 'CNV_A13_Cast')], once=False))
    has = lambda who, tmpl, k, a: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', who, 3, k, tmpl, a)  # noqa
    s8.total(t, 'CNV_A13_Bomb', '机', [(1, has(p1, BOMBER, 1, 'Test A13 Whole')),
                                       (1, has(p1, BOMBER, 2, 'Test A13 Whole')),
                                       (10, has(s4, BOMBER, 1, 'Test A13 Whole')),
                                       (10, has(s4, BOMBER, 2, 'Test A13 Whole')),
                                       (100, has(p1, GI, 1, 'Test A13 Spot DP')),
                                       (1000, has(s4, GI, 1, 'Test A13 Spot DS'))])
    s8.watch(t, RUN)
    return t


WING = 'JapanAntiAirShip'                          # the Sea-Wing: on the water, Command_JAAS_Transform takes it up
WINGS = {'WT': 2200.0, 'WB': 2300.0, 'WP': 2400.0}  # x in the trench, all at y 3200
SHORE = 650.0                                      # each one's land point, north of it (y 3850: past the bank)
BACK = PRESS + 3.0


def wing_mission():
    """Round 278 (j05's AAS -> AVA, 7 uses): WT pressed at PRESS, WB at PRESS and again at BACK, WP never; all three
    MOVEd to their land point a second after BACK. [the second ToggleState: TRANSFORMATION_TOGGLE_STATE, LocomotorSet
    SUPERSONIC 150, the JetAIUpdate: WT flies over the bank (~650 at 150); WB / WP on the water locomotor stay put]"""
    m = Mission(name='CampActsWing', map=probe_air, units=[], facts={})
    m.spawns |= {WING}
    o = probe_air.SITES[SEA]
    for row, x in WINGS.items():
        m.put(WING, SEA, x - o.x, 3200.0 - o.y, angle=1.5708, name=_n(row), role=row.lower())
        m.waypoint(f'shore {row}', f'CNV A13 Shore {row}', SEA, x - o.x, 3200.0 + SHORE - o.y)
    return m


def wing(m):
    """态 = WT TRANSFORMATION_TOGGLE_STATE + 10 x WB's + 100 x WT AIRBORNE_TARGET + 1000 x WB's;
    岸 = WT in its land square (100) + 10 x WB + 100 x WP."""
    t = Test()
    s8.at(t, 'hold', 0.1, [('UNIT_CHANGE_OBJECT_STATUS', _n(r), status('NO_ATTACK'), 1) for r in WINGS] +
          [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'press', PRESS, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n(r), 'Command_JAAS_Transform') for r in ('WT', 'WB')])
    s8.at(t, 'back', BACK, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('WB'), 'Command_JAAS_Transform')])
    s8.at(t, 'move', BACK + 1.0, [('MOVE_NAMED_UNIT_TO', _n(r), m.mark(f'shore {r}')) for r in WINGS])
    for r in WINGS:
        t.areas[f'Test A13 Shore {r}'] = square(*m.point(f'shore {r}'), 100.0)
    has = lambda r, bit: ('UNIT_HAS_OBJECT_STATUS', _n(r), status(bit))  # noqa: E731
    s8.total(t, 'CNV_A13_Wing', '态', [(1, has('WT', 'TRANSFORMATION_TOGGLE_STATE')),
                                       (10, has('WB', 'TRANSFORMATION_TOGGLE_STATE')),
                                       (100, has('WT', 'AIRBORNE_TARGET')), (1000, has('WB', 'AIRBORNE_TARGET'))])
    s8.total(t, 'CNV_A13_Shore', '岸', [(w, ('NAMED_INSIDE_AREA', _n(r), f'Test A13 Shore {r}'))
                                        for r, w in (('WT', 1), ('WB', 10), ('WP', 100))])
    s8.watch(t, 18.0)
    return t


MISSION = {'engine_acts_wet': mission, 'engine_acts_wing': wing_mission}
CHECKS = {'engine_acts_wet': {'all': all_}, 'engine_acts_wing': {'all': wing}}
