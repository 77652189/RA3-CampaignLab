"""Inventory batch 3, the part measured second (it crashed at start, DirectX box, 11-09 x5; run the same evening after
the user closed Red Alert 2): the team status, the base power, the player's superweapon cast and its availability.
Builds engine_scripts8b (engine_scripts8's map) and engine_scripts8bs (missions/super_bench.py's Niagara). What the
simulator predicted is in brackets; the bench's seconds run ~1 s ahead of the timers (engine_scripts8).

  status  (engine_scripts8's map) crew Hold (two Guardians) ~140 from an enemy Guardian (NO_ATTACK, so it does not
          shoot back); a lone Guardian 'free' 120 from another (the control), 1200 south. The team status action,
          NO_ATTACK on at the start, off at OFF_AT. 甲敌 / 乙敌 = the held crew's / the control's enemy's health %
          [甲敌 100 until OFF_AT, 88 at 11 s; 乙敌 94 at 1 s, down ~6 a second]
  power   the base power action (player, 1000) at 2 s, (player, 300) at 6 s. 电级 = how many of 0 / 1 / 300 / 1000 /
          1001 / 1300 the excess power is at least [1 -> 4 at 2 s -> 3 at 6 s: a supply set, not added]
  pfire   (the player's proton collider, enemy base defenses at 0 / 150 / 240 / 300 from 'Test Proton Spot'; the rest
          deleted at the start) the player-level superweapon cast at frame CAST of the tick; 帧数 = frames since;
          满血帧 = frames target 0 is at 100 after the cast; 血0 = its health %; 施放数 = frames the player's power is
          seen triggered [as engine_super q's named cast: 满血帧 56, 血0 44]
  pdis    the same with the availability action ('Disabled') at the start, and the named cast (the collider) at
          CAST + LATER [a script's cast goes all the same: 满血帧 56; a player's click would be refused]

读数 (bench 2026-11-09 evening, run_queue pend_scripts8:* -- the names before this file's move):
  status  甲敌 100 to s8, 75 at s9, 50 s11, 25 s13, 12 from s15; 乙敌 87 at s1, down ~6 a second to 12 at s12:
          TEAM_CHANGE_OBJECT_STATUS NO_ATTACK holds every member's fire and lifting it frees them at once (the timer's
          10 s = the bench's s9). As the simulator. The first run asked 甲敌 100 from s9 (FAIL: the bench's clock).
  power   电级 4 at s1-s4, 3 from s5: PLAYER_SET_BASE_POWER sets the supply (1000, then 300), it does not add. As
          the simulator (the timers' 2 / 6 s = the bench's s1 / s5). The first run asked 4 from s4 to the end (FAIL:
          the expectation's end second missing).
  pfire   满血帧 56, 血0 44, 施放数 1 (from s7): PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT casts the player's collider as
          the named cast does, and PLAYER_TRIGGERED_SPECIAL_POWER sees it for one frame. As the simulator.
  pdis    满血帧 56, 血0 44, 施放数 1 at s7: with PLAYER_SPECIAL_POWER_AVAILABILITY Disabled a script's player-level
          cast goes all the same (as the simulator). The named cast 300 ticks (~20 s) later: 施放数 2 from s26 but
          血0 stays 44 -- seen as triggered, no blast. The simulator had it hit again; now sim.py's rule (INFERRED):
          a cast in the reload its own last cast started brings no blast (a collider never cast fires uncharged,
          engine_super p / q).
"""
from parts import Script, Test, status
import checks.engine_scripts8 as s8

OFF_AT, CAST, LATER = 10.0, 75, 300
RUN = {'status': 20.0, 'power': 10.0, 'pfire': 20.0, 'pdis': 40.0}
GE = 3
LEVELS = (0, 1, 300, 1000, 1001, 1300)
TEAM_STATUS, BASE_POWER = 'TEAM_CHANGE_OBJECT_STATUS', 'PLAYER_SET_BASE_POWER'
P_FIRE, P_AVAIL = 'PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'PLAYER_SPECIAL_POWER_AVAILABILITY'
POWER_P = 'SpecialPowerParticleCannon'      # missions/super_bench.py's collider power (G5: a check asks no mission)


def mission():
    return s8.mission('CampS8b')


def status_(m):
    t = Test()
    foes = [m.role(f'{p} foe').name for p in s8.STATUS]
    t.scripts.append(Script('Test - S8 hold', [], [('UNIT_CHANGE_OBJECT_STATUS', n, status('NO_ATTACK'), 1) for n in foes]
                            + [(TEAM_STATUS, m.teams['Hold'], status('NO_ATTACK'), 1)]))
    s8.at(t, 'off', OFF_AT, [(TEAM_STATUS, m.teams['Hold'], status('NO_ATTACK'), 0)])
    for counter, label, n in (('CNV_S8_E1', '甲敌', foes[0]), ('CNV_S8_E2', '乙敌', foes[1])):
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter}', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', n, counter)],
                                once=False))
    t.expect += [('甲敌', 0, '==', 100, OFF_AT - 2), ('甲敌', OFF_AT + 1, '<', 100), ('乙敌', 2, '<', 100)]
    s8.watch(t, RUN['status'])
    return t


def power(m):
    t = Test()
    p1 = m.player()
    s8.at(t, 'set', 2.0, [(BASE_POWER, p1, 1000)])
    s8.at(t, 'reset', 6.0, [(BASE_POWER, p1, 300)])
    s8.total(t, 'CNV_S8_Power', '电级', [(1, ('PLAYER_EXCESS_POWER_' + 'COMPARE_VALUE', p1, GE, n)) for n in LEVELS])
    t.expect += [('电级', 2, '==', 4, 4), ('电级', 6, '==', 3)]
    s8.watch(t, RUN['power'], 0.5)
    return t


def _super(m, which):
    t = Test()
    p1 = m.player('p1')
    power, spot = POWER_P, m.mark('proton spot')
    keep = {'collider', 'yard', 'power'} | {f'target {d}' for d in (0, 150, 240, 300)}
    start = [('MAP_REVEAL_ALL_PERM', p1)]
    start += [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'target {d}').name, 'NO_ATTACK', 1) for d in (0, 150, 240, 300)]
    start += [('NAMED_DELETE', r.name) for k, r in m.cast.items() if k not in keep and r.name]
    if which == 'pdis':
        start.append((P_AVAIL, p1, power, 'Disabled'))
    t.scripts.append(Script('Test - S8 start', [], start))
    t.scripts.append(Script('Test - S8 tick', [], [('INCREMENT_COUNTER', 1, 'CNV_S8_Tick')], once=False))
    t.scripts.append(Script('Test - S8 cast', [('COUNTER', 'CNV_S8_Tick', 2, CAST)],
                            [(P_FIRE, p1, power, spot), ('SET_FLAG', 'Test S8 Cast', 1)]))
    on = ('FLAG', 'Test S8 Cast', 1)
    if which == 'pdis':
        t.scripts.append(Script('Test - S8 named cast', [('COUNTER', 'CNV_S8_Tick', 2, CAST + LATER)],
                                [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role('collider').name, power, spot)]))
    target = m.role('target 0').name
    if which == 'pfire':
        s8.frames(t, 'CNV_S8_Frames', '帧数', [on])
    s8.frames(t, 'CNV_S8_Full', '满血帧', [on, ('UNIT_HEALTH', target, 3, 100)])
    t.counters.append(('CNV_S8_H0', '血0'))
    t.scripts.append(Script('Test - S8 health', [on], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, 'CNV_S8_H0')],
                            once=False))
    s8.frames(t, 'CNV_S8_Seen', '施放数', [('PLAYER_TRIGGERED_SPECIAL_POWER', p1, power)])
    t.expect = []
    s8.watch(t, RUN[which], 0.5)
    return t


MISSION = {'engine_scripts8b': mission}     # engine_scripts8bs: missions/super_bench.py makes it
CHECKS = {'engine_scripts8b': {'status': status_, 'power': power},
          'engine_scripts8bs': {'pfire': lambda m: _super(m, 'pfire'), 'pdis': lambda m: _super(m, 'pdis')}}
