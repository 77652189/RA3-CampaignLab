"""Retail-campaign actions, batch 12 (round 224): the ability buttons left after batch 11, pressed by a script, one run.
Mission on maps/probe_border.py ('stop row' offsets as checks/engine_acts11.py), the player's units and three enemy
conscripts (s4), everyone holding fire (NO_ATTACK). PRESS (3 s): every button below; what the data predicts is in
brackets (15 logic frames a second).
  SB  JapanInfiltrationInfantry (shinobi) Command_SmokeBombSpecialPower (j07's ninjas, 19 uses): ActivateModule-
      SpecialPower, AttributeModifier_SmokeBomb on self (NON_AUTOACQUIRABLE, 10 s); its SpecialAbilityUpdate sets
      UNATTACKABLE while packing (PackTime 0.5 s). [NON_AUTOACQUIRABLE 3 s - 13 s, UNATTACKABLE 3 s - 3.5 s]
  EA  JapanAntiVehicleVehicleTech1 (Tsunami) Command_ToggleEnergizedArmorSpecialPower (a07's fleet, 14 uses):
      AttributeModifier ..EnergizedArmor, 10 s: GENERIC_TOGGLE_STATE, SPEED 125 %, ARMOR 50 %; EP the same, not
      pressed. Both told to MOVE 600 east at the press. [EA GENERIC 3 s - 13 s; speed 75 -> EP there ~8 s after the
      press, EA ~6.4 s]
  RB  SovietScoutInfantry (bear) Command_ActivateRoarSpecialPower (a01, 7 uses); RN another bear, the same button
      _ON_NAMED its conscript (a01's intro, 6 uses; TargetType NONE). Weapon SovietScoutInfantryRoar: ParalyzeNugget
      EMP radius 100, 10 s, enemy INFANTRY -- the dog's bark's shape (engine_wfire bark). Enemy conscripts C1 60 north
      of RB, C2 60 north of RN, C3 200 north of RB; all three sent 300 further north 0.3 s after the press.
      [C1 / C2 held ~150 frames (10 s), C3 walks at once]
  LP  SovietAntiInfantryVehicle (Sickle) NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT Command_ActivateLeapSpecialPower
      (a08 / s02, 8 uses) 250 east: WeaponFireSpecialAbilityUpdate UnpackTime 0.5 s, weapon ProjectileSelf at 300 a
      second; LQ another Sickle told to MOVE 250 east. [LP there ~1.5 s after the press, LQ on its wheels later]
  BD  CAMP_PowerStore_AlliedBomberDrop NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT Command_CAMPAlliedBomberDrop2 (j04,
      28 uses) at a spot 400 north of it: OCLSpecialPower CREATE_AT_EDGE_NEAR_SOURCE, two CAMP_AlliedBomberAircraft_
      Infantry_1 (offset x -70 / +70) fly to the spot and fire SpecialPower_EjectPassengers: each 3 Allied GIs + 2
      Javelins. [some seconds' flight from the north edge, then 6 GIs + 4 Javelins of the player round the spot]
Counters:
  技 = SB NON_AUTOACQUIRABLE + 10 x SB UNATTACKABLE + 100 x EA GENERIC_TOGGLE_STATE + 1000 x EA in its far square
       + 2000 x EP in its
  吼 = C1 in its start square + 10 x C2 + 100 x C3
  跳 = LP in its leap square + 10 x LQ in its square
  兵 = the player's AlliedAntiInfantryInfantry round the spot (0-6) + 10 x AlliedAntiVehicleInfantry (0-4)
  [predicted: 技 0 -> 111 (3 s) -> 101 (3.5 s) -> 3101 (~9.4 s) -> 3101 / 2000 + 1001 (~11 s) -> 3000 (13 s);
   吼 111 -> 011 by 3.5 s, the held ones out ~13 s; 跳 0 -> 1 (~4.5 s) -> 11 (LQ later); 兵 0 -> 46]
  The simulator before round 224: none of SB / EA / LP / BD did anything; both bears held their conscripts.
  BENCH 11-14 (round 224, run_queue; CampActsMixAll_mcp_1114_075347; tests/test_simbench.py
    test_acts_mix_all_as_the_bench; bench row s_k = mission k + 2): s1 0 111 0 0 | s2 101 1 0 0 | s3-s6 101 1 11 0 |
    s7 1101 1 11 0 | s8-s10 3101 1 11 0 | s11 3000 1 11 0 | s12-s25 3000 0 11 0.
    SB / EA: the self modifier on ~10 s (simunits.self_module_power, Sim.self_power_press; the 0.5 s UNATTACKABLE fell
    between readings: INFERRED); EA there a reading before EP (SPEED 125 %). RB held C1 10 s (the bark's shape); RN's
    _ON_NAMED roar held nobody (TargetType NONE: the simulator takes it as refused, INFERRED). LP in its square by s3
    (unpack 0.5 s + 250 at 300 a second: Sim.leap_press), LQ drove there as fast (not telling). BD: nobody round the
    spot in 22 s -- not explained (inventory NOTES), the simulator does nothing either.
"""
from maps import probe_border
from parts import Mission, Test, square, status
import checks.engine_scripts8 as s8

MAN = 'SovietAntiInfantryInfantry'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
# row -> (template, x, y, side)
ROWS = {'SB': ('JapanInfiltrationInfantry', 700.0, 3900.0, 'p1'),
        'EA': ('JapanAntiVehicleVehicleTech1', 700.0, 4300.0, 'p1'),
        'EP': ('JapanAntiVehicleVehicleTech1', 700.0, 4600.0, 'p1'),
        'RB': ('SovietScoutInfantry', 1900.0, 3900.0, 'p1'), 'RN': ('SovietScoutInfantry', 2300.0, 3900.0, 'p1'),
        'C1': (MAN, 1900.0, 3960.0, 's4'), 'C2': (MAN, 2300.0, 3960.0, 's4'), 'C3': (MAN, 1900.0, 4100.0, 's4'),
        'LP': ('SovietAntiInfantryVehicle', 2900.0, 3900.0, 'p1'),
        'LQ': ('SovietAntiInfantryVehicle', 2900.0, 4200.0, 'p1'),
        'BD': ('CAMP_PowerStore_AlliedBomberDrop', 2400.0, 4300.0, 'p1')}
FAR = {'EA': 600.0, 'EP': 600.0, 'LP': 250.0, 'LQ': 250.0}
SPOT = (2400.0, 4700.0)
GI, JAV = 'AlliedAntiInfantryInfantry', 'AlliedAntiVehicleInfantry'
ROAR = 'Command_ActivateRoarSpecialPower'
PRESS, AWAY, RUN = 3.0, 3.3, 24.0


def _n(part):
    return f'UNIT - CNV A12 {part}'


def mission():
    m = Mission(name='CampActsMix', map=probe_border, units=[], facts={})
    m.spawns |= {r[0] for r in ROWS.values()} | {'CAMP_AlliedBomberAircraft_Infantry_1', GI, JAV}
    for row, (tmpl, x, y, side) in ROWS.items():
        m.put(tmpl, 'stop row', x - O[0], y - O[1], side=side, angle=0.0, name=_n(row), role=row.lower())
        if row in FAR:
            m.waypoint(f'far {row}', f'CNV A12 Far {row}', 'stop row', x + FAR[row] - O[0], y - O[1])
        if row.startswith('C'):
            m.waypoint(f'away {row}', f'CNV A12 Away {row}', 'stop row', x - O[0], y + 300.0 - O[1])
    m.waypoint('spot', 'CNV A12 Drop', 'stop row', SPOT[0] - O[0], SPOT[1] - O[1])
    return m


def _bit(row, bit):
    return ('UNIT_HAS_OBJECT_STATUS', _n(row), status(bit))


def all_(m):
    t = Test()
    hold = [('UNIT_CHANGE_OBJECT_STATUS', _n(r), status('NO_ATTACK'), 1) for r in ROWS if r != 'BD']
    s8.at(t, 'hold', 0.1, hold + [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'press', PRESS, [
        ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('SB'), 'Command_SmokeBombSpecialPower'),
        ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('EA'), 'Command_ToggleEnergizedArmorSpecialPower'),
        ('MOVE_NAMED_UNIT_TO', _n('EA'), m.mark('far EA')), ('MOVE_NAMED_UNIT_TO', _n('EP'), m.mark('far EP')),
        ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('RB'), ROAR),
        ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', _n('RN'), ROAR, _n('C2')),
        ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n('LP'), 'Command_ActivateLeapSpecialPower',
         m.mark('far LP')),
        ('MOVE_NAMED_UNIT_TO', _n('LQ'), m.mark('far LQ')),
        ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n('BD'), 'Command_CAMPAlliedBomberDrop2', m.mark('spot'))])
    s8.at(t, 'away', AWAY, [('MOVE_NAMED_UNIT_TO', _n(c), m.mark(f'away {c}')) for c in ('C1', 'C2', 'C3')])
    area = {}
    for row in FAR:
        area[row] = f'Test A12 Far {row}'
        t.areas[area[row]] = square(*m.point(f'far {row}'), 80.0)
    for row in ('C1', 'C2', 'C3'):
        area[row] = f'Test A12 Start {row}'
        t.areas[area[row]] = square(ROWS[row][1], ROWS[row][2], 30.0)
    t.areas['Test A12 Drop'] = square(*SPOT, 400.0)
    inside = lambda row: ('NAMED_INSIDE_AREA', _n(row), area[row])  # noqa: E731
    s8.total(t, 'CNV_A12_Abil', '技', [(1, _bit('SB', 'NON_AUTOACQUIRABLE')), (10, _bit('SB', 'UNATTACKABLE')),
                                       (100, _bit('EA', 'GENERIC_TOGGLE_STATE')), (1000, inside('EA')),
                                       (2000, inside('EP'))])
    s8.total(t, 'CNV_A12_Roar', '吼', [(1, inside('C1')), (10, inside('C2')), (100, inside('C3'))])
    s8.total(t, 'CNV_A12_Leap', '跳', [(1, inside('LP')), (10, inside('LQ'))])
    p1 = m.player('p1')
    s8.total(t, 'CNV_A12_Drop', '兵', [(w, ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, 3, k, tmpl,
                                             'Test A12 Drop'))
                                       for tmpl, w, top in ((GI, 1, 6), (JAV, 10, 4)) for k in range(1, top + 1)])
    s8.watch(t, RUN)
    return t


BOMBER = 'CAMP_AlliedBomberAircraft_Infantry_1'
# the drop (round 225): store -> (x, y, side, its spot); the retail stores are all a computer player's (j04 Allied01,
# j05 Allied04, j07 Allies01, s08 Allies02, s09 Allies01 / 03, ep01 Allied03), round 224's was the human player's
DROPS = {'DP': (2400.0, 4300.0, 'p1', (2400.0, 4700.0)), 'DS': (3600.0, 4000.0, 's4', (3600.0, 4700.0)),
         'DA': (1200.0, 4000.0, 's5', (1200.0, 4700.0))}
LATE = 12.0
# hypothesis D (round 266): the retail stores stand on / past the map's edge (s08 (1338, -157), ep01 (-303, 666));
# probe_range's level ground runs -300 .. 5300, the border 0 .. 5000
EDGE = {'DP': (2400.0, 4950.0, 'p1', (2400.0, 4300.0)), 'DS': (3600.0, -157.0, 's4', (3600.0, 700.0)),
        'DA': (-250.0, 2900.0, 's5', (600.0, 2900.0))}


def drop_mission(allied=False, edge=False, entry=False):
    """engine_acts_drop: s4 / s5 as the map has them (Soviet); engine_acts_ally: both PlayerTemplate:Allies (the
    retail stores' owners are all Allied players); engine_acts_dropx: engine_acts_drop with ra3ext logging the hits of
    the private entry set 'bomberdrop' (D179: the special power's fire and the OCL's create, inject.py kind 'entry')."""
    m = Mission(name='CampActsEdg' if edge else 'CampActsAlly' if allied else 'CampActsDrX' if entry
                else 'CampActsDrop', map=probe_border, units=[], facts={})
    if entry:
        m.ext, m.ext_logs = True, ('entrybomberdrop',)
    if allied:
        for side in ('s4', 's5'):
            m.sides[side] = dict(m.sides.get(side, {}), playerFaction='PlayerTemplate:Allies')
    m.spawns |= {'CAMP_PowerStore_AlliedBomberDrop', BOMBER, GI, JAV}
    for row, (x, y, side, (sx, sy)) in (EDGE if edge else DROPS).items():
        m.put('CAMP_PowerStore_AlliedBomberDrop', 'stop row', x - O[0], y - O[1], side=side, angle=0.0, name=_n(row),
              role=row.lower())
        m.waypoint(f'spot {row}', f'CNV A12 Spot {row}', 'stop row', sx - O[0], sy - O[1])
    return m


def own(m):
    """Three stores, each its own owner and spot (400-700 north), one hypothesis each:
      DP (p1)  Command_CAMPAlliedBomberDrop2 at 3 s and again at 12 s (ReloadTime 0) -- a start-of-game gate?
      DS (s4)  NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT specialpowercampalliedbomberdrop2 at 12 s (j04's other way)
      DA (s5)  UNIT_AI_TRANSFER 1 at 0.1 s (j04's setup), the button at 12 s
    Counters:
      机 = the player's bombers anywhere (0-2) + 10 x s4's + 100 x s5's
      兵 / 敌 / 援 = GIs round DP's / DS's / DA's spot (0-6) + 10 x Javelins (0-4)
    BENCH 11-14 (round 225, run_queue), every counter 0 every second, in all five runs -- nothing came:
      1 engine_acts_mix:all keep (MCP): the camera on the spot and the store at 29-35 s: the store drawn (the player's
        colour), no bomber, no GI, the minimap's units unchanged s3-s12; the store cannot be selected (no hand press)
      2 engine_acts_drop (first form: DP p1 / DS s4, the button at 3 s): 0 0 0
      3 engine_acts_drop:own as here (3 s + 12 s, by name, AI-transferred): 0 0 0 0
      4 engine_acts_ally:own (s4 / s5 PlayerTemplate:Allies): 0 0 0 0
      5 engine_acts_drop:own + DP's NAMED_SET_SPECIAL_POWER_COUNTDOWN 0 at 0.1 s (engine_super's "0 makes it ready"):
        0 0 0 0
    Ruled out: the owner (human / computer, Soviet / Allied), the time (3 s / 12 s), the action (button / by name),
    the AI transfer, the countdown. Not explained (work/re/handoff.md round 225's table).
    Explained 11-16 (D180): the build left CAMP_AlliedBomberAircraft_Infantry_1 out of the mod's stream, the OCL found
    no template and made nothing. BENCH 11-17 (round 272, run_queue; CampActsDropOwn_mcp_1117_*), the build fixed
    (mapxml.map_xml made= includes a spawned retail template's file type="all", make_campnew7.spawn_names links it):
      机 兵 敌 援  s1 0 0 0 0 | s2-s12 0 46 0 0 | s13-s31 0 46 46 46 -- every store drops a full load (6 GIs +
      4 Javelins) at its spot, DP after the first press, DS / DA after 12 s; 机 stays 0 (the bombers not counted
      in Test A12 Whole at any whole second: gone at once, or the comparison does not see them -- open)."""
    return _own(m, DROPS)


def edge(m):
    """Hypothesis D: own's three presses with the stores on the map's edge / past it (EDGE: DP at y 4950 inside the
    border, DS at y -157 as s08's, DA at x -250 as ep01's), each spot 650-850 inside.
    BENCH 11-16 (round 266, run_queue; CampActsEdgEdge_mcp_1116_081513): 机 兵 敌 援 0 0 0 0 every second s1-s39 --
    no bomber, no GI. D ruled out: where the store stands is not the gate either."""
    return _own(m, EDGE)


def when(m):
    """own's presses, counted by the frame (four counters fit): 帧 = frames run; 到 / 满 / 近 = frames with >= 1 of DP's
    GIs in its 400 square / its full load (6 GIs + 4 Javelins) there / >= 1 GI within 150 of the spot. A frame-counted
    difference (帧 - 到) is the first frame the GIs are in, whatever second the screen is read at. [data: the
    bombers start at the edge nearest the store (CREATE_AT_EDGE_NEAR_SOURCE, here y 5000, 300 north of the spot),
    eject 5 each, 0.25 s a passenger, ignoring the target (IgnoreTargetLocation): the first GI ~1 s after the press
    (frame ~60), the load 1.25 s later, near the spot if they fly there first]
    BENCH 11-21 (round 275, engine_acts_drop:at, CampActsDropAt_mcp_1121_062451): 帧 - 到 = 52 at every reading, 到 = 满
    (all ten at once, 7 frames after the press), 帧 - 近 = 83: the square's 400 reaches the edge, so the load is seen
    in its bombers as they are made (INFERRED); within 150 of the spot 38 frames after the press. Readings data."""
    t = _presses(m, DROPS)
    t.areas['Test A12 Near DP'] = square(*DROPS['DP'][3], 150.0)
    s8.frames(t, 'CNV_A12_Frame', '帧', [])
    s8.frames(t, 'CNV_A12_In', '到', [_has(m, 'p1', GI, 1, 'Test A12 Spot DP')])
    s8.frames(t, 'CNV_A12_Full', '满', [_has(m, 'p1', GI, 6, 'Test A12 Spot DP'),
                                        _has(m, 'p1', JAV, 4, 'Test A12 Spot DP')])
    s8.frames(t, 'CNV_A12_Near', '近', [_has(m, 'p1', GI, 1, 'Test A12 Near DP')])
    s8.watch(t, 20.0)
    return t


def _has(m, side, tmpl, k, area):
    return 'PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player(side), 3, k, tmpl, area


def _own(m, drops):
    t = _presses(m, drops)
    s8.total(t, 'CNV_A12_Bomb', '机', [(w, _has(m, side, BOMBER, k, 'Test A12 Whole'))
                                       for side, w in (('p1', 1), ('s4', 10), ('s5', 100)) for k in (1, 2)])
    for r, counter, label in (('DP', 'CNV_A12_DropP', '兵'), ('DS', 'CNV_A12_DropS', '敌'),
                              ('DA', 'CNV_A12_DropA', '援')):
        side = drops[r][2]
        s8.total(t, counter, label, [(w, _has(m, side, tmpl, k, f'Test A12 Spot {r}'))
                                     for tmpl, w, top in ((GI, 1, 6), (JAV, 10, 4)) for k in range(1, top + 1)])
    s8.watch(t, 30.0)
    return t


def _presses(m, drops):
    t = Test()
    s8.at(t, 'reveal', 0.1, [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('UNIT_AI_TRANSFER', _n('DA'), 1),
                             ('NAMED_SET_SPECIAL_POWER_COUNTDOWN', _n('DP'), 'SpecialPowerCAMPAlliedBomberDrop2', 0)])
    button = lambda r: ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n(r), 'Command_CAMPAlliedBomberDrop2',  # noqa
                        m.mark(f'spot {r}'))
    s8.at(t, 'press', PRESS, [button('DP')])
    s8.at(t, 'late', LATE, [button('DP'), button('DA'),
                            ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', _n('DS'), 'SpecialPowerCAMPAlliedBomberDrop2',
                             m.mark('spot DS'))])
    t.areas['Test A12 Whole'] = square(2500.0, 2500.0, 2800.0)
    for r, (_x, _y, _side, spot) in drops.items():
        t.areas[f'Test A12 Spot {r}'] = square(*spot, 400.0)
    return t


MISSION = {'engine_acts_mix': mission, 'engine_acts_drop': drop_mission,
           'engine_acts_ally': lambda: drop_mission(allied=True), 'engine_acts_edge': lambda: drop_mission(edge=True),
           'engine_acts_dropx': lambda: drop_mission(entry=True)}
CHECKS = {'engine_acts_mix': {'all': all_}, 'engine_acts_drop': {'own': own, 'at': when},
          'engine_acts_ally': {'own': own},
          'engine_acts_edge': {'edge': edge}, 'engine_acts_dropx': {'own': own}}
