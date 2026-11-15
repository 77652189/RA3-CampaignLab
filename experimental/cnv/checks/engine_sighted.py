"""Retail-campaign conditions, batch 4 (round 238): TYPE_SIGHTED (17 uses: a02's spies sighted by a Soviet
anti-infantry type written in lower case, ep01's '_object list_allied all units'), NAMED_BUILDING_IS_EMPTY (13: a04's
garrisons, always NOT) and BUILT_BY_PLAYER (8: a01's war factory reveals a bonus objective). Mission on
maps/probe_border.py (level ground), every place absolute; every unit NO_ATTACK. Clear of probe_range's lanes (y 400,
1200-1900, 3300-3750) and the start (1250, 2500). Trigger areas do not overlap.

  all  sight: the player's 'watch' (Guardian, sight 200) at (1000, 4500), 'lone' alone at (2200, 4100); Soviet_4's
       'near' (Guardian) 150 east of watch, its 'scout' (Peacekeeper) 600 east, sent at 5 s to 150 west of watch;
       Soviet_5's 'far' (Guardian) 350 north of watch, never moves. OBJECTLIST_ADDOBJECTTYPE(peacekeeper, L) at 1 s.
       看见 (every frame) = 1 TYPE_SIGHTED(watch, Guardian, Soviet_4) 2 (watch, Peacekeeper, Soviet_4)
         4 (lone, Guardian, Player_1) 8 (watch, Guardian, Soviet_5) 16 (watch, L, Soviet_4)
         32 (watch, guardian -- lower case, Soviet_4)
       garrisons: three of retail's AM_Apartments_01 (the civilians') at (2400 / 3000 / 3600, 2800), H1 H2 H3; the
       player's conscripts 'man 2' / 'man 3' 200 south of H2 / H3. At 2 s NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY
       man 2 -> H2, man 3 -> H3; at 8 s NAMED_EXIT_BUILDING(man 2); at 10 s NAMED_KILL(H3).
       驻军 (every frame) = 1 NAMED_BUILDING_IS_EMPTY(H1) 2 (H2) 4 (H3) 8 (the barracks: no garrison) 16 (watch: a
         tank, no transport)
       building: the player's AlliedBarracks (3400, 4400, facing west) and AlliedPowerPlant (4200, 4400), money
       2000; at 2 s NAMED_USE_COMMANDBUTTON_ABILITY(barracks, Command_ConstructAlliedEngineer) (engine_production e:
       out ~160 frames after the press); at 22 s UNIT_KILL_ALL_IN_AREA(Player_1, X): X west of the barracks
       (x 2900-3380, y 4150-4650; the barracks' own centre outside).
       建造 (every frame) = 1 BUILT_BY_PLAYER(AlliedEngineer, Player_1) 2 (Guardian, Player_1: placed on the map)
         4 (AlliedBarracks, Player_1: placed) 8 (AlliedEngineer, Soviet_4) 16 (alliedengineer, lower case, Player_1)
       帧 (only added) = 1 a frame BUILT_BY_PLAYER(AlliedEngineer, Player_1) holds (an edge or a state)
  [prediction from the data (the simulator before this round knew none of the three; Generals' ScriptConditions
   read as a guide, INFERRED): TYPE_SIGHTED as ENEMY_SIGHTED's range query (round 237) with a type filter in place of
   the relation, the viewer counting itself (lone, as ENEMY_SIGHTED's Friend): 看见 1 + 4 + 32 = 37 to ~s6, then
   + 2 + 16 = 55 once scout is within 200 of watch; 8 never (far is 350 off). NAMED_BUILDING_IS_EMPTY = the
   object's container holds nobody, false for an object with no container or a dead one: 驻军 7 to s2, 1 s2-s8, 3
   from ~s8 (man 2 out), 3 after H3's death (H3 false: gone). BUILT_BY_PLAYER = the player owns a finished one
   (Player::countObjectsByThingTemplate, not "built by production"): 建造 6 from the start, 23 once the engineer
   is out (~s13), 6 again after the kill at 22 s; 帧 grows ~15 a second from ~s13 to s22]
  BENCH 11-15 (round 238, CampSightedAll_mcp_1115_001541 PASS; the bench's seconds ~1.5 behind the timers): 看见 /
    驻军 / 建造 / 帧 s1-s5 37 1 6 0 | s6-s10 37 3 6 0 | s11 37 3 23 5 | s12-s27 39 3 23 20..248 | s31 39 3 6 252.
    So: TYPE_SIGHTED as predicted except &16 -- a list made by OBJECTLIST_ADDOBJECTTYPE never matched (the same
    list PLAYER_HAS_OBJECT_COMPARISON reads, engine_scripts7); NAMED_BUILDING_IS_EMPTY as predicted; BUILT_BY_PLAYER
    as predicted (placed ones count, a state), but the killed engineer still counted until ~s27 (~7 s after the
    kill: while it lies; the simulator's LINGER 0 drops it at once). Simulator: sim.Sim.cond_retail4
    (tests/test_simbench.py test_sighted_all_as_the_bench).
"""
from maps import probe_border
from parts import Mission, Script, Test, square, status
import checks.engine_scripts8 as s8

TANK, PK, MAN = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry', 'SovietAntiInfantryInfantry'
HOUSE, BARRACKS, POWER, ENGINEER = 'AM_Apartments_01', 'AlliedBarracks', 'AlliedPowerPlant', 'AlliedEngineer'
BUTTON = 'Command_ConstructAlliedEngineer'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
WATCH, LONE, NEAR, SCOUT, SCOUT_TO, FAR = ((1000.0, 4500.0), (2200.0, 4100.0), (1150.0, 4500.0), (1600.0, 4500.0),
                                           (850.0, 4500.0), (1000.0, 4850.0))
HOUSES = {'h1': (2400.0, 2800.0), 'h2': (3000.0, 2800.0), 'h3': (3600.0, 2800.0)}
YARD = {'barracks': (BARRACKS, (3400.0, 4400.0)), 'power': (POWER, (4200.0, 4400.0))}
KILL = (2900.0, 4150.0, 3380.0, 4650.0)
RUN = 30.0


def _n(part):
    return f'UNIT - CNV Sighted {part.title()}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def mission():
    m = Mission(name='CampSighted', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, PK, MAN, ENGINEER}
    for role, side, template, (x, y) in (('watch', 'p1', TANK, WATCH), ('lone', 'p1', TANK, LONE),
                                         ('near', 's4', TANK, NEAR), ('scout', 's4', PK, SCOUT),
                                         ('far', 's5', TANK, FAR)):
        _put(m, template, x, y, side=side, angle=0.0 if side == 'p1' else 3.1416, name=_n(role), role=role)
    for role, (x, y) in HOUSES.items():
        _put(m, HOUSE, x, y, side='civ', angle=0.0, name=_n(role), role=role)
    for k in ('2', '3'):
        x, y = HOUSES[f'h{k}']
        _put(m, MAN, x, y - 200.0, side='p1', angle=0.0, name=_n(f'man {k}'), role=f'man {k}')
    for role, (template, (x, y)) in YARD.items():
        _put(m, template, x, y, side='p1', angle=3.1416, name=_n(role), role=role)
    m.waypoint('scout to', 'Test Sighted Scout To', 'stop row', SCOUT_TO[0] - O[0], SCOUT_TO[1] - O[1])
    return m


def all_(m):
    t = Test()
    p1, s4, s5 = m.player(), m.player('s4'), m.player('s5')
    n = {r: m.role(r).name for r in ('watch', 'lone', 'near', 'scout', 'far', 'h1', 'h2', 'h3', 'man 2', 'man 3',
                                     'barracks', 'power')}
    t.areas['Test Sighted X'] = _rect(*KILL)
    t.scripts.append(Script('Test - Sighted start', [], [('PLAYER_SET_MONEY', p1, 2000)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', n[r], status('NO_ATTACK'), 1)
        for r in ('watch', 'lone', 'near', 'scout', 'far', 'man 2', 'man 3')]))
    s8.at(t, 'list', 1.0, [('OBJECTLIST_ADDOBJECTTYPE', PK.lower(), 'L')])
    s8.at(t, 'in', 2.0, [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man 2'], n['h2']),
                         ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man 3'], n['h3']),
                         ('NAMED_USE_COMMANDBUTTON_ABILITY', n['barracks'], BUTTON)])
    s8.at(t, 'scout', 5.0, [('MOVE_NAMED_UNIT_TO', n['scout'], m.mark('scout to'))])
    s8.at(t, 'out', 8.0, [('NAMED_EXIT_BUILDING', n['man 2'])])
    s8.at(t, 'kill', 10.0, [('NAMED_KILL', n['h3'])])
    s8.at(t, 'gone', 22.0, [('UNIT_KILL_ALL_IN_AREA', p1, 'Test Sighted X')])
    s8.total(t, 'CNV_Sighted_Sight', '看见', [
        (1, ('TYPE_SIGHTED', n['watch'], TANK, s4)), (2, ('TYPE_SIGHTED', n['watch'], PK, s4)),
        (4, ('TYPE_SIGHTED', n['lone'], TANK, p1)), (8, ('TYPE_SIGHTED', n['watch'], TANK, s5)),
        (16, ('TYPE_SIGHTED', n['watch'], 'L', s4)), (32, ('TYPE_SIGHTED', n['watch'], TANK.lower(), s4))])
    s8.total(t, 'CNV_Sighted_Empty', '驻军', [(w, ('NAMED_BUILDING_IS_EMPTY', n[r])) for w, r in (
        (1, 'h1'), (2, 'h2'), (4, 'h3'), (8, 'barracks'), (16, 'watch'))])
    s8.total(t, 'CNV_Sighted_Built', '建造', [
        (1, ('BUILT_BY_PLAYER', ENGINEER, p1)), (2, ('BUILT_BY_PLAYER', TANK, p1)),
        (4, ('BUILT_BY_PLAYER', BARRACKS, p1)), (8, ('BUILT_BY_PLAYER', ENGINEER, s4)),
        (16, ('BUILT_BY_PLAYER', ENGINEER.lower(), p1))])
    s8.frames(t, 'CNV_Sighted_Frames', '帧', [('BUILT_BY_PLAYER', ENGINEER, p1)])
    t.expect = [('看见', 0, 'ever>=', 1, RUN)]
    s8.watch(t, RUN)
    return t


MISSION = {'engine_sighted': mission}
CHECKS = {'engine_sighted': {'all': all_}}
