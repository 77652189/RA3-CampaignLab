"""Retail-campaign actions, batch 10 (round 221): unit ability buttons pressed by a script, all in one run.
Mission on maps/probe_border.py ('stop row' offsets as checks/engine_transport.py), everyone the player's, holding
fire (NO_ATTACK). LOAD (1 s): the crews put in by TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY (round 152: the room,
the relation skipped). PRESS (3 s), MOVE (5 s). What the data predicts is in brackets.
  EJ  SovietSupportBomber_S07 (a01's intro bombers; TransportContain 5 INFANTRY, EjectPassengersSpecialAbilityUpdate
      Height 150, TimePerPassenger 1.25 s, Radius 0) + crew TEJ of 3 conscripts. PRESS:
      NAMED_USE_COMMANDBUTTON_ABILITY Command_ActivateEjectPassengersSpecialPowerUntargeted (75 uses).
      [one out every 1.25 s where the bomber is: in 3 -> 0 by ~7 s]
  EV  SovietAntiGroundAircraft (Twinblade; TransportContain 5) + crew TEV of 3. PRESS: NAMED_USE_COMMANDBUTTON_ABILITY
      Command_SovietAntiGroundAircraftEvacuate (LogicCommand Type EVACUATE, no power; s09's Hinds, 43 uses).
      [lands where it is, all out: timing not in the data]
  SH  JapanAntiVehicleInfantry (Tankbuster). PRESS: Command_ToggleSpiderHole (41 uses; the second ToggleState:
      IMMOBILE_ALLOW_ROTATE NO_ATTACK IMMUNE_TO_BARK IN_SPIDER_HOLE). MOVE 400 east ('far SH'); 9 s: press again;
      10 s: MOVE again. [in the hole 3 s - 9 s, no move while in it; at far SH ~4 s after the second move]
  TB  crew TB = one Bullfrog (SovietAntiAirShip), its passengers crew TBP of 3. PRESS:
      TEAM_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT(TB, Command_ActivateEjectPassengersSpecialPower, far TB 500 east)
      (51 uses: a05's MCVs, j01 / j02's Bullfrogs, j09's leaps). [as round 152's J: 3 in -> 3 at far TB]
  TT / TP  Tengu (JapanAntiInfantryVehicle) pressed Command_JAIV_Transform (38 uses) / not pressed;
  VT / VP  VX (JapanAntiAirVehicleTech1) pressed Command_JAAVT1_Transform (48 uses) / not pressed. MOVE all four
      1200 east. [TRANSFORMATION_TOGGLE_STATE from the press (round 51); LocomotorSet SUPERSONIC: Tengu 200 against
      100 on the ground, VX 120 against 85 -> TT there ~6 s after the move, TP ~12, VT ~10, VP ~14]
Counters:
  弹 = EJ in (ENCLOSED) + 10 x EJ out (alive, not ENCLOSED) + 100 x EV in + 1000 x EV out
  队 = TB passengers in + 10 x at far TB
  到 = first time inside its far square (kept): TT + 10 x TP + 100 x VT + 1000 x VP
  态 = TT TRANSFORMATION_TOGGLE_STATE + 10 x VT's + 100 x SH IN_SPIDER_HOLE + 1000 x SH at far SH
  [predicted: 弹 3030 before LOAD, 303 after, 0 -> 30 (EJ out) by ~8 s, EV out -> 3000 sometime; 队 3 -> 30 by ~8 s;
   到 0 -> 1 (~11 s) -> 101 (~15) -> 111 (~17) -> 1111 (~19); 态 0 -> 111 at 3 s -> 11 at 9 s -> 1011 by ~14 s]
  The simulator before round 221: the Twinblade's men never ENCLOSED and never let out, no untargeted eject, the team
  button unknown (队 3 throughout), the transformed ones no faster (TT = TP 13 s).
  BENCH 11-14 (round 221, run_queue; CampActsBtnAll_mcp_1114_043143; tests/test_simbench.py
    test_acts_btn_all_as_the_bench; bench row s_k = mission k + 2): s1 303 3 0 0 | s2 312 1 0 111 | s3 3021 0 0 111 |
    s4 3030 20 0 111 | s5-s6 3030 30 0 111 | s7-s8 3030 30 0 11 | s9-s10 3030 30 1 11 | s11 3030 30 101 11 |
    s12-s14 3030 30 111 1011 | s15-s25 3030 30 1111 1011.
    EJ as predicted (one out every 1.25 s from the press). EV: the men ENCLOSED inside (the XML's ObjectStatusOfContained
    says UNSELECTABLE NO_ATTACK only), all three out together 1-2 s after the press (simgarrison.EVACUATE_DELAY 1.5,
    INFERRED). TB as round 152's J. SH as predicted: the order given in the hole did not move it. TT s9 / VT s11 /
    TP s12 / VP s15: the SUPERSONIC locomotors (simunits.locomotor_of). The simulator after: 弹 / 队 / 态 the same
    every row from s2, 到 within 1 s.
"""
from maps import probe_border
from parts import Mission, Script, Test, square, status
import checks.engine_scripts8 as s8

MAN, FROG = 'SovietAntiInfantryInfantry', 'SovietAntiAirShip'
BOMBER, BLADE = 'SovietSupportBomber_S07', 'SovietAntiGroundAircraft'
BUSTER, TENGU, VX = 'JapanAntiVehicleInfantry', 'JapanAntiInfantryVehicle', 'JapanAntiAirVehicleTech1'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
# row -> (template, x, y, crew size)
ROWS = {'EJ': (BOMBER, 700.0, 3900.0, 3), 'EV': (BLADE, 700.0, 4100.0, 3), 'SH': (BUSTER, 700.0, 4300.0, 0),
        'TB': (FROG, 700.0, 4500.0, 3), 'TT': (TENGU, 2200.0, 3900.0, 0), 'TP': (TENGU, 2200.0, 4100.0, 0),
        'VT': (VX, 2200.0, 4300.0, 0), 'VP': (VX, 2200.0, 4500.0, 0)}
FAR = {'SH': 400.0, 'TB': 500.0, 'TT': 1200.0, 'TP': 1200.0, 'VT': 1200.0, 'VP': 1200.0}
FAR_R = 200.0
LOAD, PRESS, MOVE, RUN = 1.0, 3.0, 5.0, 24.0


def _n(part):
    return f'UNIT - CNV A10 {part}'


def mission():
    m = Mission(name='CampActsBtn', map=probe_border, units=[], facts={})
    m.spawns |= {MAN, FROG, BOMBER, BLADE, BUSTER, TENGU, VX}
    for row, (tmpl, x, y, n) in ROWS.items():
        props = {'originalOwner': m.crew('TB')} if row == 'TB' else {}
        m.put(tmpl, 'stop row', x - O[0], y - O[1], angle=0.0, name=_n(row), role=row.lower(), props=props)
        if n:
            c = m.crew(('TBP' if row == 'TB' else f'T{row}'))
            for k in range(n):
                m.put(MAN, 'stop row', x - 100.0 + 40.0 * k - O[0], y - 90.0 - O[1], angle=0.0,
                      name=_n(f'{row} {k}'), role=f'{row.lower()} {k}', props={'originalOwner': c})
        if row in FAR:
            m.waypoint(f'far {row}', f'CNV A10 Far {row}', 'stop row', x + FAR[row] - O[0], y - O[1])
    return m


def _men(row):
    return [_n(f'{row} {k}') for k in range(ROWS[row][3])]


def _in(row, w):
    return [(w, ('UNIT_HAS_OBJECT_STATUS', u, status('ENCLOSED'))) for u in _men(row)]


def all_(m):
    t = Test()
    hold = [('UNIT_CHANGE_OBJECT_STATUS', u, status('NO_ATTACK'), 1) for row in ROWS for u in [_n(row)] + _men(row)]
    s8.at(t, 'hold', 0.1, hold + [('MAP_REVEAL_ALL_PERM', m.player('p1'))])
    s8.at(t, 'load', LOAD, [('TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY', m.teams[c], _n(row))
                            for c, row in (('TEJ', 'EJ'), ('TEV', 'EV'), ('TBP', 'TB'))])
    s8.at(t, 'press', PRESS, [
        ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('EJ'), 'Command_ActivateEjectPassengersSpecialPowerUntargeted'),
        ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('EV'), 'Command_SovietAntiGroundAircraftEvacuate'),
        ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('SH'), 'Command_ToggleSpiderHole'),
        ('TEAM_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', m.teams['TB'], 'Command_ActivateEjectPassengersSpecialPower',
         m.mark('far TB')),
        ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('TT'), 'Command_JAIV_Transform'),
        ('NAMED_USE_COMMANDBUTTON_ABILITY', _n('VT'), 'Command_JAAVT1_Transform')])
    s8.at(t, 'move', MOVE, [('MOVE_NAMED_UNIT_TO', _n(r), m.mark(f'far {r}')) for r in ('SH', 'TT', 'TP', 'VT', 'VP')])
    s8.at(t, 'out', 9.0, [('NAMED_USE_COMMANDBUTTON_ABILITY', _n('SH'), 'Command_ToggleSpiderHole')])
    s8.at(t, 'again', 10.0, [('MOVE_NAMED_UNIT_TO', _n('SH'), m.mark('far SH'))])
    area = {}
    for row in FAR:
        area[row] = f'Test A10 Far {row}'
        t.areas[area[row]] = square(*m.point(f'far {row}'), FAR_R)
    out = lambda row, w: [(w, ('UNIT_HAS_OBJECT_STATUS', u, status('ENCLOSED'), 'NOT')) for u in _men(row)]  # noqa
    s8.total(t, 'CNV_A10_Out', '弹', _in('EJ', 1) + out('EJ', 10) + _in('EV', 100) + out('EV', 1000))
    s8.total(t, 'CNV_A10_Team', '队', _in('TB', 1) + [(10, ('NAMED_INSIDE_AREA', u, area['TB'])) for u in _men('TB')])
    t.counters.append(('CNV_A10_There', '到'))
    t.scripts += [Script(f'Test - A10 there {r}', [('NAMED_INSIDE_AREA', _n(r), area[r])],
                         [('INCREMENT_COUNTER', w, 'CNV_A10_There')])
                  for r, w in (('TT', 1), ('TP', 10), ('VT', 100), ('VP', 1000))]
    s8.total(t, 'CNV_A10_State', '态', [
        (1, ('UNIT_HAS_OBJECT_STATUS', _n('TT'), status('TRANSFORMATION_TOGGLE_STATE'))),
        (10, ('UNIT_HAS_OBJECT_STATUS', _n('VT'), status('TRANSFORMATION_TOGGLE_STATE'))),
        (100, ('UNIT_HAS_OBJECT_STATUS', _n('SH'), status('IN_SPIDER_HOLE'))),
        (1000, ('NAMED_INSIDE_AREA', _n('SH'), area['SH']))])
    s8.watch(t, RUN)
    return t


MISSION = {'engine_acts_btn': mission}
CHECKS = {'engine_acts_btn': {'all': all_}}
