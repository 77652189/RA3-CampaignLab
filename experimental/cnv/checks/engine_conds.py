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


MISSION = {'engine_conds': mission}
CHECKS = {'engine_conds': {'team': team, 'fight': fight}}
