"""Retail-campaign conditions, batch 1 (round 207; the gaps of `inventory_retail.py --part 脚本条件`, the program read in
work/re/d115_script_semantics.md). Mission on maps/probe_border.py (level ground, every place absolute, as
checks/engine_scripts9.py). The enemy crew is on Soviet_4: placed units on a Soviet_1 / 2 / 3 crew are on no team
(engine_scripts9 rounds 130-136). What the simulator predicts is in brackets.

  team    the player's crew Go (go 1 at (1000, 1000), go 2 at (1000, 1150)), the area Home round them, the area F 700
          east (both squares of half-side 150). go 1 is sent into F at 1 s, go 2 at 6 s; NO_ATTACK set on go 1 at 2 s,
          on go 2 at 4 s; the money set to 5000 at the start and to 4000 at MONEY_AT; a reinforcement team Spawn (one
          Guardian) made at 3 s, TEAM_KILL(Spawn) at 8 s; TEAM_KILL(Go) at GO_KILL_AT.
          队形 (every frame) = 1 TEAM_INSIDE_AREA_PARTIALLY(Go, F, 0) 2 _ENTIRELY(Go, F, 0) 4 TEAM_HAS_UNITS(Go)
            8 TEAM_HAS_UNITS(Spawn) 16 TEAM_CREATED(Spawn) 32 TEAM_CREATED(Go) 64 TEAM_DESTROYED(Spawn)
            128 TEAM_DESTROYED(Go)
          状态 (every frame) = 1 TEAM_SOME_HAVE_OBJECT_STATUS(Go, NO_ATTACK) 2 TEAM_ALL_HAS_OBJECT_STATUS(Go, NO_ATTACK)
            4 PLAYER_HAS_CREDITS(Player_1, >=, 5000) 8 CURRENT_PLATFORM(PC) 16 PARTIALLY(Go, F, 3) 32 PARTIALLY(Go, F, 7)
            64 PLAYER_HAS_CREDITS(Player_1, <, 4500) 128 PARTIALLY(Go, F, 1)
          离开 (only added) = frames NAMED_EXITED_AREA(go 1, Home) held; 建队帧 (only added) = frames TEAM_CREATED(Spawn)
          held (1 = an edge; growing = a state)
          [simulator 11-13 (sim.Sim.cond_retail): 队形 36 to s2 (Go has units 4, Go created 32: a map team is active
          from the start); 60 from s3 (Spawn made: 8 + 16); s8 53 (go 1 in F: +1; Spawn killed, its units gone: -8);
          117 from s9 (TEAM_DESTROYED(Spawn) from the next frame, still created); 119 from s13 (go 2 in F: entirely);
          112 from s24 (Go killed: neither inside nor with units, still created).
          状态 12 to s1 (credits 5000, PC); 13 from s2 (some); 15 from s4 (all); 63 from s8 (go 1 in F: k 3 / 7 read as
          k 0, INFERRED: every Guardian has an AI); 123 from s10 (credits 4000: >= 5000 off, < 4500 on); 74 from s24
          (Go empty: ALL holds on nobody, Generals evaluateTeamHasObjectStatus returns entireTeam). 离开 1 from s1 (an
          edge, INFERRED). 建队帧 +15 a second from s3 (a state, INFERRED)]
  fight   the player's 'shot' (Guardian, (1000, 3000)) and the crew Foe of Soviet_4: foe 1 at (1400, 3000), foe 2 at
          (2900, 3000), both NO_ATTACK. At 1 s NAMED_ATTACK_NAMED(shot, foe 1); NEXT_AFTER s after foe 1 is destroyed,
          NAMED_ATTACK_NAMED(shot, foe 2).
          被打 (every frame) = 1 TEAM_ATTACKED_BY_PLAYER(Foe, Player_1) 2 (Foe, Soviet_5) 4 SKIRMISH_PLAYER_HAS_BEEN_
            ATTACKED_BY_PLAYER(Soviet_4, Player_1) 8 (Soviet_5, Player_1) 16 TEAM_ATTACKED_BY_OBJECTTYPE(Foe, Guardian)
            32 NAMED_ATTACKED_BY_OBJECTTYPE(foe 2, Guardian)
          击杀 (every frame) = 1 PLAYER_HAS_KILLED_NAMED_UNIT(Player_1, foe 1) 2 PLAYER_HAS_KILLED_TYPE_UNITS(Player_1,
            1, Guardian) 4 (Player_1, 2, Guardian) 8 NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE(shot, >=, 1, Guardian)
            16 TEAM_DESTROYED(Foe) 32 NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE(shot, ==, 1, Guardian)
          甲 / 乙 = foe 1's / foe 2's health % (a dead one's counter keeps its last value)
          [simulator 11-13: 被打 0, 21 from s5 (the first hit: 1 + 4 + 16) while foe 1 lives; 4 from s20 (foe 1
          dead: the team version reads its living members' last damage, D 115; the player-level flag stays); 53 from
          s44 (foe 2 hit: + 1 + 16 + 32); 4 from s59 (both dead). 击杀 0, 43 from s20 (foe 1: 1 + 2 + 8 + 32), 31 from
          s59 (foe 2: + 4 + 16, == 1 off). 甲 93 at s5 -> 0 at s20; 乙 100 to s43, 0 at s59]
  sight   (round 210; batch 2, d115_script_semantics.md 4-6, 15) every unit NO_ATTACK. The player's crew Watch (watch,
          (1000, 4500)); Soviet_4's crews Near (near, 230 east of watch: inside the sight 200 + the two radii 23 only),
          Spy (spy, 1200 east, sent to 400 east at 1 s) and Navy (a Dreadnought on dry land, (2300, 4850): Surfaces
          DEEP_WATER only) in the area N. near to 300 east at 4 s, back to 180 at 9 s, NAMED_KILLed at 14 s. Hot spots
          H1 / H2 (the map's MissionHotSpots): SET_ACTIVENESS(H1, 1) at 2 s, (Nope, 1) at 3 s (not on the map),
          VISIBILITY(H2, 1) at 4 s, LINK(H2, near, 0) at 5 s, SET(H1, 0) at 6 s, SET(H2, 1) at 16 s (its linked unit dead).
          视野 = 1 ENEMY_SIGHTED_BY_TEAM(Watch, Enemy, Soviet_4) 2 (Watch, Friend, Soviet_4) 4 (Watch, Friend, Player_1)
            8 (Near, Enemy, Player_1) 16 (Watch, Neutral, Soviet_4) 32 (Spy, Enemy, Player_1)
          发现 = 1 TEAM_DISCOVERED(Player_1, Near) 2 (Player_1, Spy) 4 (Soviet_4, Watch) 8 (Player_1, Watch)
            16 (Soviet_5, Watch)
          海军 = 1 PARTIALLY(Navy, N, 0) 2 (Navy, N, 1) 4 (Navy, N, 3) 8 (Navy, N, 7) 16 TEAM_HAS_UNITS(Navy)
            32 PARTIALLY(Watch, W, 1) 64 PARTIALLY(Watch, W, 0)
          热点 = 1 MISSION_HOT_SPOT_ACTIVE(H1) 2 (H2) 4 (Nope) 8 (h1, lower case)
          [simulator 11-13 (sim.Sim.cond_retail2): 视野 13 (1 near inside the circles' reach, 4 watch itself, 8 near sees
          watch; INFERRED the member itself counts) / 4 from s5 (near at 300) / 13 from s10 / 4 from s14 (near dead).
          发现 13 (Near seen, Soviet_4 sees Watch, the player's own) / 15 from s10 (spy within the player's sight 500) /
          14 from s14. 海军 88 all along (k 7 + alive + watch k 0: the ship never for k 0, D 119's prediction).
          热点 0 / 9 s2-s5 (case ignored, INFERRED) / 0 / 2 from s16; Nope, VISIBILITY and LINK never]
  BENCH 11-13 (round 210, run_queue; tests/test_simbench.py test_conds_sight_as_the_bench): 视野 / 发现 / 海军 / 热点
    s1-s2 4 13 88 1 | s3 4 12 88 1 | s4 4 13 88 1 | s5-s7 4 13 88 0 | s8 4 12 88 0 | s9 13 12 88 0 | s10-s12 13 15 88 0 |
    s13 5 14 88 0 | s14-s24 5 14 88 2 | s25 4 14 88 2. Against the prediction: near at 230 unseen (视野&1, &8 off until
    it stands at 180: centre to centre, not + both radii); its wreck seen ~11 s after the kill (&1 s13-s24); near off
    for 发现&1 while it moves (s3, s8-s9); the lower-case hot spot name never on (&8). The rest as predicted -- D 119's
    ship never for k 0. The simulator fixed to the first, third and fourth (sim.Sim.cond_retail2); the wreck's time
    is the Guardian's SlowDeath (0 s in the simulator), left to the module lines.

BENCH 11-13 (round 208, run_queue; tests/test_simbench.py test_conds_team_as_the_bench / _fight_):
  team (with the 128 bits): 队形 / 状态 s1 4 13 | s2 12 13 | s3-s6 12 15 | s7-s8 5 15 | s9-s10 5 75 | s11-s21 7 75 |
    s22-s31 128 74; 离开 1, 建队帧 1. Against the prediction: TEAM_CREATED holds one frame after the making (建队帧
    1) and never for the map team Go (32 never); TEAM_DESTROYED(Spawn) never after its TEAM_KILL while
    TEAM_DESTROYED(Go) holds after Go's (128); PARTIALLY with k 3 / 7 / 1 never for the Guardians (16 / 32 / 128).
    The rest as predicted (ALL_HAS on the emptied Go: 74). The simulator fixed to all three (sim.Sim.cond_retail,
    TEAM_DESTROYED); the bench's seconds run a second or two before the simulator's.
  fight: 被打 / 击杀 s1-s2 0 0 | s3-s15 21 0 | s16-s38 4 43 | s39-s52 53 43 | s53-s71 4 31; 甲 87 at s3 .. 12 at s14,
    kept 12; 乙 87 at s39 .. 12 at s52, kept. Every bit as predicted (the fire sooner than the simulator's).
"""
from maps import probe_border
from parts import Mission, Script, Test, square, status
import checks.engine_scripts8 as s8

TANK = 'AlliedAntiVehicleVehicleTech1'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
MONEY_AT, GO_KILL_AT, NEXT_AFTER = 10.0, 24.0, 4.0
RUN = {'team': 30.0, 'fight': 70.0}
GO = {'go 1': (1000.0, 1000.0), 'go 2': (1000.0, 1150.0)}
HOME, F = (1000.0, 1075.0), (1700.0, 1075.0)
SPAWN = (1000.0, 2000.0)
SHOT, FOE = (1000.0, 3000.0), {'foe 1': (1400.0, 3000.0), 'foe 2': (2900.0, 3000.0)}
GE, LT, EQ = 3, 0, 2                            # sim.CMP: 0 <, 1 <=, 2 ==, 3 >=, 4 >, 5 !=
SHIP = 'SovietAntiStructureShip'                # the Dreadnought: Locomotor Surfaces DEEP_WATER only
WATCH, NEAR, NEAR_OUT, NEAR_IN = (1000.0, 4500.0), (1230.0, 4500.0), (1300.0, 4500.0), (1180.0, 4500.0)
SPY, SPY_TO, NAVY = (2200.0, 4500.0), (1400.0, 4500.0), (2300.0, 4850.0)
RUN['sight'] = 24.0
H1, H2 = 'Test Cond H1', 'Test Cond H2'


def _n(part):
    return f'UNIT - CNV Cond {part.title()}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def _mark(m, part, x, y):
    m.waypoint(part, f'Test Cond {part.title()}', 'stop row', x - O[0], y - O[1])


def mission():
    m = Mission(name='CampConds', map=probe_border, units=[], facts={})
    m.spawns |= {TANK}
    go = m.crew('Go')
    for role, (x, y) in GO.items():
        _put(m, TANK, x, y, angle=0.0, name=_n(role), role=role, props={'originalOwner': go})
        _mark(m, f'to {role}', x + F[0] - HOME[0], y)
    m.reinforcement('Spawn', [(TANK, 1)], 'p1')
    _mark(m, 'spawn', *SPAWN)
    _put(m, TANK, *SHOT, angle=0.0, name=_n('shot'), role='shot')
    foe = m.crew('Foe', side='s4')
    for role, (x, y) in FOE.items():
        _put(m, TANK, x, y, side='s4', angle=3.1416, name=_n(role), role=role, props={'originalOwner': foe})
    # sight (round 210): the player's Watch, Soviet_4's Near / Spy / Navy (a Dreadnought on dry land)
    for key, role, side, template, (x, y) in (('Watch', 'watch', 'p1', TANK, WATCH), ('Near', 'near', 's4', TANK, NEAR),
                                              ('Spy', 'spy', 's4', TANK, SPY), ('Navy', 'navy', 's4', SHIP, NAVY)):
        m.spawns |= {template}
        _put(m, template, x, y, side=side, angle=0.0 if side == 'p1' else 3.1416,
             name=_n(role), role=role, props={'originalOwner': m.crew(key, side=side)})
    for part, (x, y) in (('near out', NEAR_OUT), ('near in', NEAR_IN), ('spy to', SPY_TO)):
        _mark(m, part, x, y)
    return m


def _frames(t, counter, label, cond):
    s8.frames(t, counter, label, [cond])


def team(m):
    t = Test()
    p1, go, spawn = m.player(), m.teams['Go'], m.teams['RSpawn']
    na = status('NO_ATTACK')
    t.areas['Test Cond Home'] = square(*HOME, 150.0)
    t.areas['Test Cond F'] = square(*F, 150.0)
    t.scripts.append(Script('Test - Cond start', [], [('PLAYER_SET_MONEY', p1, 5000)]))
    s8.at(t, 'go1', 1.0, [('MOVE_NAMED_UNIT_TO', m.role('go 1').name, m.mark('to go 1'))])
    s8.at(t, 'na1', 2.0, [('UNIT_CHANGE_OBJECT_STATUS', m.role('go 1').name, na, 1)])
    s8.at(t, 'make', 3.0, [('CREATE_REINFORCEMENT_TEAM', spawn, m.mark('spawn'))])
    s8.at(t, 'na2', 4.0, [('UNIT_CHANGE_OBJECT_STATUS', m.role('go 2').name, na, 1)])
    s8.at(t, 'go2', 6.0, [('MOVE_NAMED_UNIT_TO', m.role('go 2').name, m.mark('to go 2'))])
    s8.at(t, 'kills', 8.0, [('TEAM_KILL', spawn)])
    s8.at(t, 'money', MONEY_AT, [('PLAYER_SET_MONEY', p1, 4000)])
    s8.at(t, 'killgo', GO_KILL_AT, [('TEAM_KILL', go)])
    s8.total(t, 'CNV_Cond_Team', '队形', [
        (1, ('TEAM_INSIDE_AREA_PARTIALLY', go, 'Test Cond F', 0)),
        (2, ('TEAM_INSIDE_AREA_ENTIRELY', go, 'Test Cond F', 0)),
        (4, ('TEAM_HAS_UNITS', go)), (8, ('TEAM_HAS_UNITS', spawn)),
        (16, ('TEAM_CREATED', spawn)), (32, ('TEAM_CREATED', go)), (64, ('TEAM_DESTROYED', spawn)),
        (128, ('TEAM_DESTROYED', go))])
    s8.total(t, 'CNV_Cond_State', '状态', [
        (1, ('TEAM_SOME_HAVE_OBJECT_STATUS', go, na)), (2, ('TEAM_ALL_HAS_OBJECT_STATUS', go, na)),
        (4, ('PLAYER_HAS_CREDITS', p1, GE, 5000)), (8, ('CURRENT_PLATFORM', 'PC')),
        (16, ('TEAM_INSIDE_AREA_PARTIALLY', go, 'Test Cond F', 3)),
        (32, ('TEAM_INSIDE_AREA_PARTIALLY', go, 'Test Cond F', 7)),
        (64, ('PLAYER_HAS_CREDITS', p1, LT, 4500)),
        (128, ('TEAM_INSIDE_AREA_PARTIALLY', go, 'Test Cond F', 1))])
    _frames(t, 'CNV_Cond_Exit', '离开', ('NAMED_EXITED_AREA', m.role('go 1').name, 'Test Cond Home'))
    _frames(t, 'CNV_Cond_Made', '建队帧', ('TEAM_CREATED', spawn))
    s8.watch(t, RUN['team'])
    return t


def fight(m):
    t = Test()
    p1, s4, s5, foe = m.player(), m.player('s4'), m.player('s5'), m.teams['Foe']
    shot, f1, f2 = (m.role(r).name for r in ('shot', 'foe 1', 'foe 2'))
    t.scripts.append(Script('Test - Cond hold', [], [('UNIT_CHANGE_OBJECT_STATUS', n, status('NO_ATTACK'), 1)
                                                      for n in (f1, f2)]))
    s8.at(t, 'attack', 1.0, [('NAMED_ATTACK_NAMED', shot, f1)])
    t.scripts += [Script('Test - Cond foe 1 down', [('NAMED_DESTROYED', f1)],
                         [('SET_MILLISECOND_TIMER', 'Test Cond Next', NEXT_AFTER)]),
                  Script('Test - Cond next', [('TIMER_EXPIRED', 'Test Cond Next')], [('NAMED_ATTACK_NAMED', shot, f2)])]
    s8.total(t, 'CNV_Cond_Hit', '被打', [
        (1, ('TEAM_ATTACKED_BY_PLAYER', foe, p1)), (2, ('TEAM_ATTACKED_BY_PLAYER', foe, s5)),
        (4, ('SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER', s4, p1)),
        (8, ('SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER', s5, p1)),
        (16, ('TEAM_ATTACKED_BY_OBJECTTYPE', foe, TANK)), (32, ('NAMED_ATTACKED_BY_OBJECTTYPE', f2, TANK))])
    s8.total(t, 'CNV_Cond_Kill', '击杀', [
        (1, ('PLAYER_HAS_KILLED_NAMED_UNIT', p1, f1)), (2, ('PLAYER_HAS_KILLED_TYPE_UNITS', p1, 1, TANK)),
        (4, ('PLAYER_HAS_KILLED_TYPE_UNITS', p1, 2, TANK)),
        (8, ('NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE', shot, GE, 1, TANK)), (16, ('TEAM_DESTROYED', foe)),
        (32, ('NAMED_HAS_KILLED_COMPARISON_UNIT_TYPE', shot, EQ, 1, TANK))])
    for role, counter, label in (('foe 1', 'CNV_Cond_H1', '甲'), ('foe 2', 'CNV_Cond_H2', '乙')):
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',
                                                           m.role(role).name, counter)], once=False))
    s8.watch(t, RUN['fight'])
    return t


def sight(m):
    t = Test()
    p1, s4, s5 = m.player(), m.player('s4'), m.player('s5')
    watch, near, spy, navy = (m.teams[k] for k in ('Watch', 'Near', 'Spy', 'Navy'))
    t.hotspots = {H1: ('', ''), H2: ('', '')}
    t.areas['Test Cond N'] = square(*NAVY, 150.0)
    t.areas['Test Cond W'] = square(*WATCH, 100.0)
    t.scripts.append(Script('Test - Cond sight hold', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, status('NO_ATTACK'), 1) for r in ('watch', 'near', 'spy', 'navy')]))
    s8.at(t, 'spy', 1.0, [('MOVE_NAMED_UNIT_TO', m.role('spy').name, m.mark('spy to'))])
    s8.at(t, 'h1on', 2.0, [('SET_MISSION_HOT_SPOT_ACTIVENESS', H1, 1)])
    s8.at(t, 'nope', 3.0, [('SET_MISSION_HOT_SPOT_ACTIVENESS', 'Test Cond Nope', 1)])
    s8.at(t, 'out', 4.0, [('SET_MISSION_HOT_SPOT_VISIBILITY', H2, 1),
                          ('MOVE_NAMED_UNIT_TO', m.role('near').name, m.mark('near out'))])
    s8.at(t, 'link', 5.0, [('LINK_MISSION_HOT_SPOT_TO_OBJECT', H2, m.role('near').name, 0)])
    s8.at(t, 'h1off', 6.0, [('SET_MISSION_HOT_SPOT_ACTIVENESS', H1, 0)])
    s8.at(t, 'in', 9.0, [('MOVE_NAMED_UNIT_TO', m.role('near').name, m.mark('near in'))])
    s8.at(t, 'kill', 14.0, [('NAMED_KILL', m.role('near').name)])
    s8.at(t, 'h2on', 16.0, [('SET_MISSION_HOT_SPOT_ACTIVENESS', H2, 1)])
    s8.total(t, 'CNV_Cond_Sight', '视野', [
        (1, ('ENEMY_SIGHTED_BY_TEAM', watch, 'Enemy', s4)), (2, ('ENEMY_SIGHTED_BY_TEAM', watch, 'Friend', s4)),
        (4, ('ENEMY_SIGHTED_BY_TEAM', watch, 'Friend', p1)), (8, ('ENEMY_SIGHTED_BY_TEAM', near, 'Enemy', p1)),
        (16, ('ENEMY_SIGHTED_BY_TEAM', watch, 'Neutral', s4)), (32, ('ENEMY_SIGHTED_BY_TEAM', spy, 'Enemy', p1))])
    s8.total(t, 'CNV_Cond_Found', '发现', [
        (1, ('TEAM_DISCOVERED', p1, near)), (2, ('TEAM_DISCOVERED', p1, spy)), (4, ('TEAM_DISCOVERED', s4, watch)),
        (8, ('TEAM_DISCOVERED', p1, watch)), (16, ('TEAM_DISCOVERED', s5, watch))])
    s8.total(t, 'CNV_Cond_Navy', '海军', [
        (1, ('TEAM_INSIDE_AREA_PARTIALLY', navy, 'Test Cond N', 0)),
        (2, ('TEAM_INSIDE_AREA_PARTIALLY', navy, 'Test Cond N', 1)),
        (4, ('TEAM_INSIDE_AREA_PARTIALLY', navy, 'Test Cond N', 3)),
        (8, ('TEAM_INSIDE_AREA_PARTIALLY', navy, 'Test Cond N', 7)), (16, ('TEAM_HAS_UNITS', navy)),
        (32, ('TEAM_INSIDE_AREA_PARTIALLY', watch, 'Test Cond W', 1)),
        (64, ('TEAM_INSIDE_AREA_PARTIALLY', watch, 'Test Cond W', 0))])
    s8.total(t, 'CNV_Cond_Spot', '热点', [
        (1, ('MISSION_HOT_SPOT_ACTIVE', H1)), (2, ('MISSION_HOT_SPOT_ACTIVE', H2)),
        (4, ('MISSION_HOT_SPOT_ACTIVE', 'Test Cond Nope')), (8, ('MISSION_HOT_SPOT_ACTIVE', H1.lower()))])
    s8.watch(t, RUN['sight'])
    return t


MISSION = {'engine_conds': mission}
CHECKS = {'engine_conds': {'team': team, 'fight': fight, 'sight': sight}}
