"""Retail-campaign conditions, batch 5 (round 240): PLAYER_DESTROYED_N_BUILDINGS_PLAYER (8 uses, j03 / j07: always
N = 1 -- (Player_1, 1, Soviet02), (Allies01, 1, Player_1), ...; ep01 j03 N = 2) and
SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED (8, j02 (Player_1, <=, 0) seven times, j07 (Player_2, >=, 1)). Mission on
maps/probe_border.py (level ground), every place absolute. Clear of probe_range's lanes (y 400, 1200-1900,
3300-3750) and the start (1250, 2500). No trigger areas.

  all  razing: the player's guns (Guardians) 600 north of their marks, out of sight: gun 0 at (1000, 4000) for
       Soviet_4's 'foe' (a Guardian, NO_ATTACK) at (1000, 4600); gun a / gun b at (2200 / 3400, 4000) for Soviet_4's
       power plants A / B at (2200 / 3400, 4600). Soviet_5's plant C at (4400, 4600); the player's plant M at
       (4500, 2400) and Soviet_4's 'raider' (a Guardian) 600 south of it at (4500, 3000). At 0 s foe, A, B, M set to
       5 % health. NAMED_ATTACK_NAMED gun 0 -> foe at 1 s, gun a -> A at 4 s, gun b -> B at 10 s, raider -> M at 16 s;
       NAMED_KILL(C) at 13 s (no killer).
       摧毁 (every frame) = 1 PLAYER_DESTROYED_N_BUILDINGS_PLAYER(Player_1, 1, Soviet_4) 2 (Player_1, 2, Soviet_4)
         4 (Player_1, 1, Soviet_5: a script's kill) 8 (Soviet_4, 1, Player_1) 16 (Player_1, 0, Soviet_4)
       死 (every frame) = 1 NAMED_DESTROYED(foe) 2 (A) 4 (B) 8 (C) 16 (M)
       garrisons: three of retail's AM_Apartments_01 (the civilians') at (2400 / 3000 / 3600, 2800), H1 H2 H3; the
       player's conscripts man a / man b / man c and Soviet_4's man d 200 south of them (every man NO_ATTACK). At 2 s
       NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY man a, man b -> H1, man d -> H3; at 6 s man c -> H2;
       NAMED_EXIT_BUILDING man a at 10 s, man b at 14 s, man c at 18 s.
       驻军 (every frame) = 1 SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED(Player_1, <=, 0) 2 (Player_1, >=, 1)
         4 (Player_1, ==, 1) 8 (Player_1, ==, 2) 16 (Player_1, >=, 3) 32 (Soviet_4, >=, 1)
  [prediction from the data (the simulator before this round knew neither; Generals' ScriptConditions read as a
   guide, INFERRED). Generals' evaluatePlayerDestroyedNOrMoreBuildings is a stub (`@todo implement me`, FALSE);
   RA3's retail scripts use it as a live trigger (j07's AI turns on once the player razes one of its buildings), so
   predicted: the player's count of the opponent's structures it killed by weapon, at least N; a unit and a script's
   kill not counted: 摧毁 16 from the start (N 0), 17 once A falls (~s5), 19 once B falls (~s11), 27 once M falls
   (~s17); &4 never; the foe's death (~s2) changes nothing. The stub would read 0 all run.
   SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED = the number of the player's garrisonable objects holding anyone (a
   building, not its men; a civilian building is the occupant's while held): 驻军 1 to s2, 6 + 32 = 38 s2-s6 (H1),
   42 s6-s14 (H1 + H2; the men counted would read 2 + 16 + 32 = 50 s6-s10), 38 s14-s18 (H2), 33 after]
  BENCH 11-15 (round 240, CampRazedAll_mcp_1115_030516 PASS; the bench's seconds ~1.5 behind the timers): 摧毁 /
    死 / 驻军 s1-s4 0 0 42 | s5-s6 0 1 50 | s7-s11 0 3 50 | s12 0 11 42 | s13-s16 0 15 42 | s17-s18 0 15 38 |
    s20-s37 0 31 33. So: PLAYER_DESTROYED_N_BUILDINGS_PLAYER false all run, N 0 too -- the stub, as Generals';
    SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED counts the MEN inside (2 -> == 2, 3 -> >= 3, then 2 / 1 / 0), not the
    buildings; a man counts at once on NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY but is dropped ~3.5 s after
    NAMED_EXIT_BUILDING (NAMED_BUILDING_IS_EMPTY flipped at once, engine_sighted: INFERRED he counts while climbing
    out; the simulator drops him at once, not modelled). The kills came 2-4 s earlier than the simulator's (死).
    Simulator: simcond (tests/test_simbench.py test_razed_all_as_the_bench).
"""
from maps import probe_border
from parts import Mission, Script, Test, status
import checks.engine_scripts8 as s8

TANK, MAN, HOUSE, POWER = ('AlliedAntiVehicleVehicleTech1', 'SovietAntiInfantryInfantry', 'AM_Apartments_01',
                           'AlliedPowerPlant')
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
UNITS = {'gun 0': ('p1', TANK, (1000.0, 4000.0)), 'gun a': ('p1', TANK, (2200.0, 4000.0)),
         'gun b': ('p1', TANK, (3400.0, 4000.0)), 'foe': ('s4', TANK, (1000.0, 4600.0)),
         'raider': ('s4', TANK, (4500.0, 3000.0))}
PLANTS = {'a': ('s4', (2200.0, 4600.0)), 'b': ('s4', (3400.0, 4600.0)), 'c': ('s5', (4400.0, 4600.0)),
          'm': ('p1', (4500.0, 2400.0))}
HOUSES = {'h1': (2400.0, 2800.0), 'h2': (3000.0, 2800.0), 'h3': (3600.0, 2800.0)}
MEN = {'man a': ('p1', 'h1', -60.0), 'man b': ('p1', 'h1', 60.0), 'man c': ('p1', 'h2', 0.0),
       'man d': ('s4', 'h3', 0.0)}
RUN = 30.0


def _n(part):
    return f'UNIT - CNV Razed {part.title()}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def mission():
    m = Mission(name='CampRazed', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, MAN}
    for role, (side, template, (x, y)) in UNITS.items():
        _put(m, template, x, y, side=side, angle=1.5708 if side == 'p1' else -1.5708, name=_n(role), role=role)
    for k, (side, (x, y)) in PLANTS.items():
        _put(m, POWER, x, y, side=side, angle=0.0, name=_n(f'plant {k}'), role=f'plant {k}')
    for role, (x, y) in HOUSES.items():
        _put(m, HOUSE, x, y, side='civ', angle=0.0, name=_n(role), role=role)
    for role, (side, house, dx) in MEN.items():
        x, y = HOUSES[house]
        _put(m, MAN, x + dx, y - 200.0, side=side, angle=0.0, name=_n(role), role=role)
    return m


def all_(m):
    t = Test()
    p1, s4, s5 = m.player(), m.player('s4'), m.player('s5')
    n = {r: m.role(r).name for r in list(UNITS) + list(HOUSES) + list(MEN) + [f'plant {k}' for k in PLANTS]}
    t.scripts.append(Script('Test - Razed start', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', n[r], status('NO_ATTACK'), 1) for r in ['foe'] + list(MEN)] + [
        ('UNIT_SET_HEALTH', n[r], 5.0) for r in ('foe', 'plant a', 'plant b', 'plant m')]))
    s8.at(t, 'foe', 1.0, [('NAMED_ATTACK_NAMED', n['gun 0'], n['foe'])])
    s8.at(t, 'in', 2.0, [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man a'], n['h1']),
                         ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man b'], n['h1']),
                         ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man d'], n['h3'])])
    s8.at(t, 'a', 4.0, [('NAMED_ATTACK_NAMED', n['gun a'], n['plant a'])])
    s8.at(t, 'in c', 6.0, [('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', n['man c'], n['h2'])])
    s8.at(t, 'b', 10.0, [('NAMED_ATTACK_NAMED', n['gun b'], n['plant b'])])
    s8.at(t, 'out a', 10.0, [('NAMED_EXIT_BUILDING', n['man a'])])
    s8.at(t, 'c', 13.0, [('NAMED_KILL', n['plant c'])])
    s8.at(t, 'out b', 14.0, [('NAMED_EXIT_BUILDING', n['man b'])])
    s8.at(t, 'm', 16.0, [('NAMED_ATTACK_NAMED', n['raider'], n['plant m'])])
    s8.at(t, 'out c', 18.0, [('NAMED_EXIT_BUILDING', n['man c'])])
    d = 'PLAYER_DESTROYED_N_BUILDINGS_PLAYER'
    s8.total(t, 'CNV_Razed_Razed', '摧毁', [
        (1, (d, p1, 1, s4)), (2, (d, p1, 2, s4)), (4, (d, p1, 1, s5)), (8, (d, s4, 1, p1)), (16, (d, p1, 0, s4))])
    s8.total(t, 'CNV_Razed_Dead', '死', [(w, ('NAMED_DESTROYED', n[r])) for w, r in (
        (1, 'foe'), (2, 'plant a'), (4, 'plant b'), (8, 'plant c'), (16, 'plant m'))])
    g = 'SKIRMISH_PLAYER_HAS_COMPARISON_GARRISONED'
    s8.total(t, 'CNV_Razed_Held', '驻军', [
        (1, (g, p1, 1, 0)), (2, (g, p1, 3, 1)), (4, (g, p1, 2, 1)), (8, (g, p1, 2, 2)), (16, (g, p1, 3, 3)),
        (32, (g, s4, 3, 1))])
    t.expect = [('死', 0, 'ever>=', 1, RUN)]
    s8.watch(t, RUN)
    return t


MISSION = {'engine_razed': mission}
CHECKS = {'engine_razed': {'all': all_}}
