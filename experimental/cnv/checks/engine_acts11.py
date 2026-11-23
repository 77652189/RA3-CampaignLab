"""Retail-campaign actions, batch 11 (round 223): toggle and evacuate buttons pressed by a script, all in one run.
Mission on maps/probe_border.py ('stop row' offsets as checks/engine_acts10.py), everyone the player's, holding fire
(NO_ATTACK). LOAD (1 s): the crews put in by TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY. PRESS (3 s): every button
below, the two Kirovs told to MOVE 450 east; BACK (15 s): the toggles pressed again. What the data predicts is in
brackets.
  DE  JapanLightTransportVehicle (Sudden transport; TransportContain 5 INFANTRY) + crew TDE of 3 conscripts.
      NAMED_USE_COMMANDBUTTON_ABILITY Command_DisguisedEvacuate (LogicCommand Type EVACUATE; j01 / y01, 33 uses).
      [all out where it is, as the Twinblade's EVACUATE: 1-2 s]
  CV  ST_building05 (ContestableGarrisonContain 8) + crew TCV of 3. Command_CivilianStructureEvacuate (EVACUATE; a09's
      Leningrad blocks, 8 uses). [all out]
  JB  JapanBaseDefense pressed Command_JapanBaseDefenseToggleBinaryWeapon (a04 / j-levels, 25 uses: its CommandSet's
      one button; ToggleStatusSpecialAbilityUpdate PackTime 2 s, the second ToggleState GENERIC_TOGGLE_STATE);
  JW  another pressed Command_ToggleBinaryWeapon (a04, 6 uses: the Sickle's button, no module for it here).
      [JB GENERIC_TOGGLE_STATE 3 s - 15 s; JW never. Placed, not built: StructureUnpackUpdate (15 s; the campaign
      override 30 s) may hold the first press -- not known]
  AP  SovietAntiVehicleVehicleTech3 (Apocalypse) Command_ToggleHarpoonSpecialPower (a08, 9 uses). [GENERIC 3-15 s]
  MA  A08_SpecialMirageTank / MT AlliedAntiVehicleVehicleTech3, Command_ToggleMirageField (a08, 7 uses).
      [MA NON_AUTOACQUIRABLE, MT BROADCASTING_INVISIBILITY, 3 s - 15 s]
  KV  SovietBomberAircraft (Kirov) Command_ToggleAfterburners (a09, 12 uses); KP the same, not pressed. [KV GENERIC_
      TOGGLE_STATE + SHROUD_REVEAL_TO_ALL 3-15 s; SwitchLocomotorUpdate NORMAL_UPGRADED 55 against 30 -> KV there
      ~11 s, KP ~18 s; LoseHealthUpdate 200 / s of 6000 while GENERIC: 100 % -> 60 % at 15 s]
Counters:
  门 = DE men in (ENCLOSED) + 10 x DE men out (alive, not ENCLOSED) + 100 x CV in + 1000 x CV out
  态 = JB GENERIC_TOGGLE_STATE + 10 x JW's + 100 x AP's + 1000 x KV's
  幻 = MA NON_AUTOACQUIRABLE + 10 x MT BROADCASTING_INVISIBILITY + 100 x KV SHROUD_REVEAL_TO_ALL
       + 1000 x KV inside its far square + 2000 x KP inside its
  血 = KV's health %
  [predicted: 门 3030 -> 303 (LOAD) -> 3030 by ~5 s; 态 0 -> 1101 (3 s) -> 0 (15 s); 幻 0 -> 111 (3 s) -> 1111
   (~11 s) -> 1000 (15 s) -> 3000 (~18 s); 血 100 -> 60 (3-15 s)]
  The simulator before round 223: EVACUATE out 1.5 s after the press everywhere, JB toggled, no health lost.
  BENCH 11-14 (round 223, run_queue; CampActsTglAll_mcp_1114_065941; tests/test_simbench.py
    test_acts_tgl_all_as_the_bench; bench row s_k = mission k + 2): s1 303 0 0 100 | s2 3030 1100 111 97 |
    s3 .. 93 | s4 90 | s5 87 | s6 83 | s7 80 | s8 77 | s9 73 | s10 70 | s11 67 | s12 63 | s13 3030 1100 111 60 |
    s14-s24 3030 0 3000 60 | s25 3030 0 3000 61.
    DE / CV: all out within a second of the press (simgarrison.evacuate: only an aircraft waits to land). AP, KV, MA, MT
    as predicted, off by the second press. KV: 200 a second while GENERIC_TOGGLE_STATE (simunits.lose_health), but no
    faster: both Kirovs in their squares s13-s14 (SwitchLocomotorUpdate not seen working; not modelled). JB: no press
    taken -- the player has no power plant (tower below). s25 61: the Kirov's own heal starting (not tested).
  tower (engine_acts_twr:t, CampActsTwrT): the player has a SovietPowerPlant. BENCH 11-14 塔 s1-s33 1 | s34-s46 11:
    J1's press at 3 s toggles it (a placed tower is not held by its StructureUnpackUpdate), J2's at 35 s too, J3's
    Command_ToggleBinaryWeapon never (no module for that power). So all's JB was short of power (Sim.toggle_press:
    a POWERED structure short of power takes no toggle).
"""
from maps import probe_border
from parts import Mission, Script, Test, square, status
import checks.engine_scripts8 as s8

MAN = 'SovietAntiInfantryInfantry'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
# row -> (template, x, y, crew size)
ROWS = {'DE': ('JapanLightTransportVehicle', 700.0, 3900.0, 3), 'CV': ('ST_building05', 3300.0, 4100.0, 3),
        'JB': ('JapanBaseDefense', 700.0, 4300.0, 0), 'JW': ('JapanBaseDefense', 1100.0, 4300.0, 0),
        'AP': ('SovietAntiVehicleVehicleTech3', 1500.0, 3900.0, 0),
        'MA': ('A08_SpecialMirageTank', 1500.0, 4300.0, 0), 'MT': ('AlliedAntiVehicleVehicleTech3', 1500.0, 4600.0, 0),
        'KV': ('SovietBomberAircraft', 2200.0, 3900.0, 0), 'KP': ('SovietBomberAircraft', 2200.0, 4400.0, 0)}
CREW_DY = {'DE': -90.0, 'CV': 250.0}
FAR, FAR_R = 450.0, 100.0
PRESSES = {'DE': 'Command_DisguisedEvacuate', 'CV': 'Command_CivilianStructureEvacuate',
           'JB': 'Command_JapanBaseDefenseToggleBinaryWeapon', 'JW': 'Command_ToggleBinaryWeapon',
           'AP': 'Command_ToggleHarpoonSpecialPower', 'MA': 'Command_ToggleMirageField',
           'MT': 'Command_ToggleMirageField', 'KV': 'Command_ToggleAfterburners'}
BACK = ('JB', 'AP', 'MA', 'MT', 'KV')
LOAD, PRESS, AGAIN, RUN = 1.0, 3.0, 15.0, 24.0


def _n(part):
    return f'UNIT - CNV A11 {part}'


def mission():
    m = Mission(name='CampActsTgl', map=probe_border, units=[], facts={})
    m.spawns |= {MAN} | {r[0] for r in ROWS.values()}
    for row, (tmpl, x, y, n) in ROWS.items():
        m.put(tmpl, 'stop row', x - O[0], y - O[1], angle=0.0, name=_n(row), role=row.lower())
        if n:
            c = m.crew(f'T{row}')
            for k in range(n):
                m.put(MAN, 'stop row', x - 100.0 + 40.0 * k - O[0], y + CREW_DY[row] - O[1], angle=0.0,
                      name=_n(f'{row} {k}'), role=f'{row.lower()} {k}', props={'originalOwner': c})
        if row in ('KV', 'KP'):
            m.waypoint(f'far {row}', f'CNV A11 Far {row}', 'stop row', x + FAR - O[0], y - O[1])
    return m


def _men(row):
    return [_n(f'{row} {k}') for k in range(ROWS[row][3])]


def _bit(row, bit):
    return ('UNIT_HAS_OBJECT_STATUS', _n(row), status(bit))


def all_(m):
    t = Test()
    hold = [('UNIT_CHANGE_OBJECT_STATUS', u, status('NO_ATTACK'), 1) for row in ROWS for u in [_n(row)] + _men(row)]
    s8.at(t, 'hold', 0.1, hold + [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'load', LOAD, [('TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY', m.teams[f'T{row}'], _n(row))
                            for row in ('DE', 'CV')])
    s8.at(t, 'press', PRESS, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n(r), b) for r, b in PRESSES.items()] +
          [('MOVE_NAMED_UNIT_TO', _n(r), m.mark(f'far {r}')) for r in ('KV', 'KP')])
    s8.at(t, 'back', AGAIN, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n(r), PRESSES[r]) for r in BACK])
    area = {}
    for row in ('KV', 'KP'):
        area[row] = f'Test A11 Far {row}'
        t.areas[area[row]] = square(*m.point(f'far {row}'), FAR_R)
    inn = lambda row, w: [(w, ('UNIT_HAS_OBJECT_STATUS', u, status('ENCLOSED'))) for u in _men(row)]  # noqa
    out = lambda row, w: [(w, ('UNIT_HAS_OBJECT_STATUS', u, status('ENCLOSED'), 'NOT')) for u in _men(row)]  # noqa
    s8.total(t, 'CNV_A11_Out', '门', inn('DE', 1) + out('DE', 10) + inn('CV', 100) + out('CV', 1000))
    s8.total(t, 'CNV_A11_State', '态', [(1, _bit('JB', 'GENERIC_TOGGLE_STATE')), (10, _bit('JW', 'GENERIC_TOGGLE_STATE')),
                                        (100, _bit('AP', 'GENERIC_TOGGLE_STATE')),
                                        (1000, _bit('KV', 'GENERIC_TOGGLE_STATE'))])
    s8.total(t, 'CNV_A11_More', '幻', [(1, _bit('MA', 'NON_AUTOACQUIRABLE')), (10, _bit('MT', 'BROADCASTING_INVISIBILITY')),
                                       (100, _bit('KV', 'SHROUD_REVEAL_TO_ALL')),
                                       (1000, ('NAMED_INSIDE_AREA', _n('KV'), area['KV'])),
                                       (2000, ('NAMED_INSIDE_AREA', _n('KP'), area['KP']))])
    t.counters.append(('CNV_A11_HP', '血'))
    t.scripts.append(Script('Test - A11 hp', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', _n('KV'), 'CNV_A11_HP')],
                            once=False))
    s8.watch(t, RUN)
    return t


TOWERS = {'J1': 700.0, 'J2': 1100.0, 'J3': 1500.0}


def tower_mission():
    """tower: the player has a SovietPowerPlant (no unpack) this time; three JapanBaseDefense, J1 pressed its button at
    3 s, J2 at 35 s, J3 pressed Command_ToggleBinaryWeapon at 35 s."""
    m = Mission(name='CampActsTwr', map=probe_border, units=[], facts={})
    m.spawns |= {'JapanBaseDefense', 'SovietPowerPlant'}
    m.put('SovietPowerPlant', 'stop row', 2600.0 - O[0], 4300.0 - O[1], angle=0.0, name=_n('PP'), role='pp')
    for row, x in TOWERS.items():
        m.put('JapanBaseDefense', 'stop row', x - O[0], 4300.0 - O[1], angle=0.0, name=_n(row), role=row.lower())
    return m


def tower(m):
    t = Test()
    s8.at(t, 'hold', 0.1, [('UNIT_CHANGE_OBJECT_STATUS', _n(r), status('NO_ATTACK'), 1) for r in TOWERS] +
          [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'early', PRESS, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('J1'), PRESSES['JB'])])
    s8.at(t, 'late', 35.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('J2'), PRESSES['JB']),
                            ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('J3'), PRESSES['JW'])])
    s8.total(t, 'CNV_A11_Tower', '塔', [(w, _bit(r, 'GENERIC_TOGGLE_STATE'))
                                       for r, w in (('J1', 1), ('J2', 10), ('J3', 100))])
    s8.watch(t, 40.0)
    return t


# Round 284: Command_ToggleDeployWeapon (s03, 5 uses): the Ore Collector's gun (ToggleStatusSpecialAbilityUpdate, the
# second state GENERIC_TOGGLE_STATE + WEAPONSTATE_ONE = JapanMinerGun). Two empty miners of the player, an s4 conscript
# (NO_ATTACK) 150 east of each; JM pressed at 3 s and again at 12 s, JC never.
MINERS = {'JM': (700.0, 4900.0), 'JC': (2200.0, 4900.0)}


def miner_mission():
    m = Mission(name='CampActsJmn', map=probe_border, units=[], facts={})
    m.spawns |= {'JapanMiner', MAN}
    for row, (x, y) in MINERS.items():
        m.put('JapanMiner', 'stop row', x - O[0], y - O[1], angle=0.0, name=_n(row), role=row.lower())
        m.put(MAN, 'stop row', x + 150.0 - O[0], y - O[1], side='s4', angle=3.1416, name=_n(f'{row} man'),
              role=f'{row.lower()} man')
    return m


def miner(m):
    """态 = JM GENERIC_TOGGLE_STATE 1 + JC 10; 血M / 血C = the conscript beside JM / JC, health %."""
    t = Test()
    s8.at(t, 'hold', 0.1, [('UNIT_CHANGE_OBJECT_STATUS', _n(f'{r} man'), status('NO_ATTACK'), 1) for r in MINERS])
    s8.at(t, 'on', PRESS, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('JM'), 'Command_ToggleDeployWeapon')])
    s8.at(t, 'off', 12.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('JM'), 'Command_ToggleDeployWeapon')])
    s8.total(t, 'CNV_A11_Gun', '态', [(1, _bit('JM', 'GENERIC_TOGGLE_STATE')), (10, _bit('JC', 'GENERIC_TOGGLE_STATE'))])
    for r, lab in (('JM', '血M'), ('JC', '血C')):
        t.counters.append((f'CNV_A11_{r}', lab))
        t.scripts.append(Script(f'Test - A11 {r} man', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', _n(f'{r} man'),
                                                              f'CNV_A11_{r}')], once=False))
    s8.watch(t, 20.0)
    return t


# Round 312: Command_ActivateDisguiseSpecialPower on the Sudden transport (j01 'Transports-Disguise', 2 uses: pressed, then
# NAMED_ATTACK_NAMED an enemy Bullfrog). The button's power is SpecialPower_InfantryDisguise (the spy's); the transport's
# SpecialPower module is SpecialPower_JapanLightTransportVehicleDisguise, fired by its Disguiser weapon. Three transports,
# an s4 Bullfrog (NO_ATTACK) 300 east of each; at 3 s DP is pressed, DA pressed + told to attack its boat, DC only told to
# attack. 装 = DISGUISED: DP 1 + DA 10 + DC 100. [DP never; DA as DC, ~1 s (UnpackTime) after the order]
# BENCH 11-22 (CampActsDsgD_mcp_1122_181357; bench row s_k = mission k + 2): 装 0 s1-s2, 110 s3-s13, as predicted.
DISGUISERS = {'DP': 3900.0, 'DA': 4300.0, 'DC': 4700.0}
DISGUISE = 'Command_ActivateDisguiseSpecialPower'


def disguise_mission():
    m = Mission(name='CampActsDsg', map=probe_border, units=[], facts={})
    m.spawns |= {'JapanLightTransportVehicle', 'SovietAntiAirShip'}
    for row, y in DISGUISERS.items():
        m.put('JapanLightTransportVehicle', 'stop row', 700.0 - O[0], y - O[1], angle=0.0, name=_n(row), role=row.lower())
        m.put('SovietAntiAirShip', 'stop row', 1000.0 - O[0], y - O[1], side='s4', angle=3.1416, name=_n(f'{row} boat'),
              role=f'{row.lower()} boat')
    return m


def disguise(m):
    t = Test()
    s8.at(t, 'hold', 0.1, [('UNIT_CHANGE_OBJECT_STATUS', _n(f'{r} boat'), status('NO_ATTACK'), 1) for r in DISGUISERS] +
          [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'press', PRESS, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n(r), DISGUISE) for r in ('DP', 'DA')] +
          [('NAMED_ATTACK_NAMED', _n(r), _n(f'{r} boat')) for r in ('DA', 'DC')])
    s8.total(t, 'CNV_A11_Dsg', '装', [(w, ('UNIT_HAS_MODELCONDITION', _n(r), 'DISGUISED'))
                                     for r, w in (('DP', 1), ('DA', 10), ('DC', 100))])
    s8.watch(t, 12.0)
    return t


# Round 313: NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT Command_SovietAntiGroundAircraftEvacuate (a05 'HotSpot04-
# ExitAtReactor', 2 uses: the Twinblade with its engineer, moved to the spot, pressed at it on arrival). Two Twinblades,
# each loaded (1 s) with three conscripts; at 3 s WF is pressed at a point 600 east, WH at its own spot.
# 门 = WF in 1 + WF out 10 + WH in 100 + WH out 1000; 到 = WF in its far square 1 + 10 x each WF man in it.
# [WF flies there, lands, all out there; WH out where it is, 1-2 s] BENCH 11-22 (CampActsEvaW_mcp_1122_182849; bench
# row s_k = mission k + 2): 门 303 s1-s2, 3030 s3-s21, 到 0: both out where they stood, the waypoint ignored.
EVAC = {'WF': 600.0, 'WH': 0.0}


def evac_mission():
    m = Mission(name='CampActsEva', map=probe_border, units=[], facts={})
    m.spawns |= {'SovietAntiGroundAircraft', MAN}
    for row, y in (('WF', 3900.0), ('WH', 4500.0)):
        m.put('SovietAntiGroundAircraft', 'stop row', 700.0 - O[0], y - O[1], angle=0.0, name=_n(row), role=row.lower())
        c = m.crew(f'T{row}')
        for k in range(3):
            m.put(MAN, 'stop row', 600.0 + 40.0 * k - O[0], y - 90.0 - O[1], angle=0.0, name=_n(f'{row} {k}'),
                  role=f'{row.lower()} {k}', props={'originalOwner': c})
        m.waypoint(f'to {row}', f'CNV A11 To {row}', 'stop row', 700.0 + EVAC[row] - O[0], y - O[1])
    return m


def evac(m):
    t = Test()
    men = {r: [_n(f'{r} {k}') for k in range(3)] for r in EVAC}
    s8.at(t, 'hold', 0.1, [('UNIT_CHANGE_OBJECT_STATUS', u, status('NO_ATTACK'), 1) for r in EVAC
                           for u in [_n(r)] + men[r]] + [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'load', LOAD, [('TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY', m.teams[f'T{r}'], _n(r)) for r in EVAC])
    s8.at(t, 'press', PRESS, [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', _n(r),
                               'Command_SovietAntiGroundAircraftEvacuate', m.mark(f'to {r}')) for r in EVAC])
    t.areas['Test A11 To WF'] = square(*m.point('to WF'), 100.0)
    enc = lambda u, w, *no: (w, ('UNIT_HAS_OBJECT_STATUS', u, status('ENCLOSED'), *no))  # noqa
    s8.total(t, 'CNV_A11_Eva', '门', [enc(u, w * k, *no) for r, k in (('WF', 1), ('WH', 100)) for u in men[r]
                                     for w, no in ((1, ()), (10, ('NOT',)))])
    s8.total(t, 'CNV_A11_EvaTo', '到', [(w, ('NAMED_INSIDE_AREA', u, 'Test A11 To WF'))
                                       for u, w in [(_n('WF'), 1)] + [(u, 10) for u in men['WF']]])
    s8.watch(t, 20.0)
    return t


MISSION = {'engine_acts_tgl': mission, 'engine_acts_twr': tower_mission, 'engine_acts_jmn': miner_mission,
           'engine_acts_dsg': disguise_mission, 'engine_acts_eva': evac_mission}
CHECKS = {'engine_acts_tgl': {'all': all_}, 'engine_acts_twr': {'t': tower}, 'engine_acts_jmn': {'g': miner},
          'engine_acts_dsg': {'d': disguise}, 'engine_acts_eva': {'w': evac}}
