"""Retail-campaign conditions, batch 6 (round 245): four of the last seven gaps on one map.
TEAM_ENTERED_AREA_PARTIALLY (a03 ('TEAM - Hammer Patrol', area, 0); ep01 ('TEAM - Naval Attackers', area, 1)),
TEAM_OUTSIDE_AREA_ENTIRELY (j04 ('<This Team>', 'AREA - Major Gameplay', 0) twice),
BUILDING_GARRISONNED_BY_OBJECT_TYPE (a02 ('UNIT - Port Authority', 'alliedcommandotech1', 'Player_1')) and
PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_COMPLETELY_BUILT (a05 ('Player_2', >=, 1, 'sovietoutpost', area)).
Mission on maps/probe_border.py (level ground), every place absolute; areas apart (a unit in many overlapping areas
freezes their counts, round 236).

  all  team: the player's crew Go (Guardians go 1 (1000, 1000), go 2 (1000, 1150)), the area Home round them, F 700
       east (squares of half-side 150), as engine_conds team. go 1 -> F at 1 s, go 2 -> F at 6 s, go 1 back home at
       12 s and -> F again at 18 s; TEAM_KILL(Go) at 24 s. Spawn: a reinforcement team never made.
       进入 (only added) = 1 x frames TEAM_ENTERED_AREA_PARTIALLY(Go, F, 0) + 100 x (Go, F, 1) + 10000 x (Go, Home, 0)
       区外 (every frame) = 1 TEAM_OUTSIDE_AREA_ENTIRELY(Go, F, 0) 2 (Go, F, 1) 4 (Go, Home, 0) 8 (Spawn, F, 0)
         16 TEAM_INSIDE_AREA_PARTIALLY(Go, F, 0) (benched, the reference)
       garrisons: retail's AM_Apartments_01 h1 / h2 / h3 at (2400 / 3000 / 3600, 2800) (the civilians'); the player's
       conscript man a 200 south of h1, Soviet_4's man d 200 south of h2 (both NO_ATTACK). At 2 s
       NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY man a -> h1, man d -> h2; NAMED_EXIT_BUILDING man a at 10 s.
       驻类 (every frame) = 1 BUILDING_GARRISONNED_BY_OBJECT_TYPE(h1, conscript, Player_1) 2 (h1, conscript, Soviet_4)
         4 (h2, conscript, Soviet_4) 8 (h1, conscript in lower case, Player_1) 16 (h1, AlliedCommandoTech1, Player_1)
         32 (h3, conscript, Player_1)
       building: the area B (x 2100-3900, y 4000-4600); the player's power plant 'plant p' at (2400, 4300), Soviet_4's
       'plant s' at (3000, 4300); at 3 s CREATE_NAMED_ON_TEAM_AT_WAYPOINT the player's 'plant n' at (3600, 4300)
       (made by script it unpacks, UnpackTime 3 s: engine_build b).
       建成 (every frame) = 1 ..._COMPLETELY_BUILT(Player_1, >=, 1, AlliedPowerPlant, B) 2 (Player_1, >=, 2, ...)
         4 (Soviet_4, >=, 1, ...) 8 PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA(Player_1, >=, 2, ..., B) (benched,
         the reference) 16 _COMPLETELY_BUILT(Player_1, >=, 1, alliedpowerplant, B)
  [prediction (Generals' ScriptConditions / Team.cpp as the guide, INFERRED until the bench):
   ENTERED = Team::didPartialEnter, a member's didEnter(area): one frame as it comes in. 进入 +1 ~s2 (go 1 in F),
   +1 ~s7 (go 2), +10000 ~s13 (go 1 home again), +1 ~s19 (go 1 in F again): 10003 at the end; k 1 never (a
   Guardian has no WATER).
   OUTSIDE = !(INSIDE_ENTIRELY || INSIDE_PARTIALLY), so an absent team is outside: 区外 11 to ~s2 (1 + 2 + 8), 26
   (2 + 8 + 16) with go 1 in F, 30 with go 2 in F too (Home emptied: + 4), 26 while go 1 is home (~s13-s19), 30
   again, 15 from s24 (Go killed: outside everything).
   GARRISONNED = the building holds one of that type and is that player's (a civilian building is its occupant's):
   驻类 0 to s2, 13 (1 + 4 + 8: the type's case ignored, as retail writes it lower case) to ~s10 (+3.5: the garrison
   count dropped him late, engine_razed), 4 after.
   COMPLETELY_BUILT = the _IN_TRIGGER_AREA count of the player's own, unpacked ones only: 建成 21 (1 + 4 + 16), 29
   once plant n is made (the reference counts it at once), 31 once it has unpacked (~s6)]
  BENCH 11-15 (round 245, CampAreaAll_mcp_1115_093807 -- built then as engine_area, since renamed; run_queue at
    bddb0af4; the bench's seconds ~1.5 behind the
    timers): 进入 / 区外 / 驻类 / 建成 s1 10000 11 13 21 | s2-s6 20000 11 13 31 | s7-s8 30001 30 13 31 | s9-s10 30001 30 4
    31 | s11-s20 30002 30 4 31 | s21 30003 30 4 31 | s22-s31 30003 15 4 31. Against the prediction: ENTERED counts
    the first frame (both placed inside Home) and AGAIN the frame each Guardian leaves Home (s2 go 1, s7 go 2) -- but
    not go 1 leaving F (~s12); F: go 1 s7, go 2 s11, go 1 again s21 (go 1, sent home at 12 s, never got there before
    it was sent back: no Home entry). k 1 never. OUTSIDE as Generals (Home stays empty while go 1 is away: 30, not
    26). GARRISONNED drops the man the moment he is ordered out (not ~3.5 s late as the garrison count). COMPLETELY_
    BUILT counts the script's plant at once, unpacking (31 at s2). Simulator: simcond / team_entered
    (INFERRED: an entry seen on the first frame stays marked until the member leaves); tests/test_simbench.py
    test_area_all_as_the_bench.
"""
from maps import probe_border
from parts import Mission, Script, Test, square, status
import checks.engine_scripts8 as s8

TANK, MAN, TANYA, HOUSE, POWER = ('AlliedAntiVehicleVehicleTech1', 'SovietAntiInfantryInfantry', 'AlliedCommandoTech1',
                                  'AM_Apartments_01', 'AlliedPowerPlant')
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
GO = {'go 1': (1000.0, 1000.0), 'go 2': (1000.0, 1150.0)}
HOME, F = (1000.0, 1075.0), (1700.0, 1075.0)
HOUSES = {'h1': (2400.0, 2800.0), 'h2': (3000.0, 2800.0), 'h3': (3600.0, 2800.0)}
MEN = {'man a': ('p1', 'h1'), 'man d': ('s4', 'h2')}
PLANTS = {'plant p': ('p1', (2400.0, 4300.0)), 'plant s': ('s4', (3000.0, 4300.0))}
BUILD = (3600.0, 4300.0)
B = [(2100.0, 4000.0), (3900.0, 4000.0), (3900.0, 4600.0), (2100.0, 4600.0)]
GE, KILL_AT, RUN = 3, 24.0, 30.0                # sim.CMP 3 is >=


def _n(part):
    return f'UNIT - CNV Area {part.title()}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def _mark(m, part, x, y):
    m.waypoint(part, f'Test Area {part.title()}', 'stop row', x - O[0], y - O[1])


def mission():
    m = Mission(name='CampEnter', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, MAN, POWER, TANYA}       # TANYA only named by a condition
    go = m.crew('Go')
    for role, (x, y) in GO.items():
        _put(m, TANK, x, y, angle=0.0, name=_n(role), role=role, props={'originalOwner': go})
        _mark(m, f'to {role}', x + F[0] - HOME[0], y)
        _mark(m, f'home {role}', x, y)
    m.reinforcement('Spawn', [(TANK, 1)], 'p1')
    for role, (x, y) in HOUSES.items():
        _put(m, HOUSE, x, y, side='civ', angle=0.0, name=_n(role), role=role)
    for role, (side, house) in MEN.items():
        x, y = HOUSES[house]
        _put(m, MAN, x, y - 200.0, side=side, angle=0.0, name=_n(role), role=role)
    for role, (side, (x, y)) in PLANTS.items():
        _put(m, POWER, x, y, side=side, angle=0.0, name=_n(role), role=role)
    _mark(m, 'build', *BUILD)
    return m


def all_(m):
    t = Test()
    p1, s4 = m.player(), m.player('s4')
    go, spawn = m.teams['Go'], m.teams['RSpawn']
    n = {r: m.role(r).name for r in list(GO) + list(HOUSES) + list(MEN) + list(PLANTS)}
    t.areas['Test Area Home'] = square(*HOME, 150.0)
    t.areas['Test Area F'] = square(*F, 150.0)
    t.areas['Test Area B'] = B
    t.scripts.append(Script('Test - Area hold', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', n[r], status('NO_ATTACK'), 1) for r in MEN]))
    s8.at(t, 'go1', 1.0, [('MOVE_NAMED_UNIT_TO', n['go 1'], m.mark('to go 1'))])
    s8.at(t, 'in', 2.0, [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man a'], n['h1']),
                         ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man d'], n['h2'])])
    s8.at(t, 'make', 3.0, [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', _n('plant n'), POWER, m.team('p1'), m.mark('build'))])
    s8.at(t, 'go2', 6.0, [('MOVE_NAMED_UNIT_TO', n['go 2'], m.mark('to go 2'))])
    s8.at(t, 'out', 10.0, [('NAMED_EXIT_BUILDING', n['man a'])])
    s8.at(t, 'back', 12.0, [('MOVE_NAMED_UNIT_TO', n['go 1'], m.mark('home go 1'))])
    s8.at(t, 'again', 18.0, [('MOVE_NAMED_UNIT_TO', n['go 1'], m.mark('to go 1'))])
    s8.at(t, 'kill', KILL_AT, [('TEAM_KILL', go)])
    t.counters.append(('CNV_Area_Enter', '进入'))
    t.scripts += [Script(f'Test - CNV_Area_Enter {w}', [('TEAM_ENTERED_AREA_PARTIALLY', go, area, k)],
                         [('INCREMENT_COUNTER', w, 'CNV_Area_Enter')], once=False)
                  for w, area, k in ((1, 'Test Area F', 0), (100, 'Test Area F', 1), (10000, 'Test Area Home', 0))]
    o = 'TEAM_OUTSIDE_AREA_ENTIRELY'
    s8.total(t, 'CNV_Area_Out', '区外', [
        (1, (o, go, 'Test Area F', 0)), (2, (o, go, 'Test Area F', 1)), (4, (o, go, 'Test Area Home', 0)),
        (8, (o, spawn, 'Test Area F', 0)), (16, ('TEAM_INSIDE_AREA_PARTIALLY', go, 'Test Area F', 0))])
    g = 'BUILDING_GARRISONNED_BY_OBJECT_TYPE'
    s8.total(t, 'CNV_Area_Held', '驻类', [
        (1, (g, n['h1'], MAN, p1)), (2, (g, n['h1'], MAN, s4)), (4, (g, n['h2'], MAN, s4)),
        (8, (g, n['h1'], MAN.lower(), p1)), (16, (g, n['h1'], TANYA, p1)), (32, (g, n['h3'], MAN, p1))])
    c = 'PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA_COMPLETELY_BUILT'
    s8.total(t, 'CNV_Area_Built', '建成', [
        (1, (c, p1, GE, 1, POWER, 'Test Area B')), (2, (c, p1, GE, 2, POWER, 'Test Area B')),
        (4, (c, s4, GE, 1, POWER, 'Test Area B')),
        (8, ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', p1, GE, 2, POWER, 'Test Area B')),
        (16, (c, p1, GE, 1, POWER.lower(), 'Test Area B'))])
    s8.watch(t, RUN)
    return t


MISSION = {'engine_enter': mission}
CHECKS = {'engine_enter': {'all': all_}}
