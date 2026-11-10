"""Inventory batch 3, the part NOT yet on the bench (it crashed at start, DirectX box, 11-09 x5): written, contract ok,
the simulator's predictions in brackets. Not an engine_ file on purpose: inventory.bench_sources reads only
checks/engine_*.py, so nothing here counts as measured. Once run (run_queue pend_scripts8:status pend_scripts8:power
pend_scripts8s:pfire pend_scripts8s:pdis), write the readings in and move it to checks/engine_scripts8b.py (the build
names to engine_scripts8b / engine_scripts8bs).

  status  (engine_scripts8's map) crew Hold (two Guardians) ~140 from an enemy Guardian (NO_ATTACK, so it does not
          shoot back); a lone Guardian 'free' 120 from another (the control), 1200 south (a first run had them 250
          apart: nobody fired, the control neither). The team status action, NO_ATTACK on at the start, off at OFF_AT.
          甲敌 / 乙敌 = the held crew's / the control's enemy's health % [甲敌 100 until OFF_AT, 88 at 11 s; 乙敌 94 at
          1 s, down ~6 a second]
  power   the base power action (player, 1000) at 2 s, (player, 300) at 6 s. 电级 = how many of 0 / 1 / 300 / 1000 /
          1001 / 1300 the excess power is at least [1 -> 4 at 2 s -> 3 at 6 s: a supply set, not added]
  pfire   (missions/super_bench.py's Niagara: the player's proton collider, enemy base defenses at 0 / 150 / 240 / 300
          from 'Test Proton Spot'; the rest deleted at the start) the player-level superweapon cast at frame CAST of the
          tick; 帧数 = frames since; 满血帧 = frames target 0 is at 100 after the cast; 血0 = its health %; 施放数 =
          frames the player's power is seen triggered [as engine_super q's named cast: 满血帧 56, 血0 44]
  pdis    the same with the availability action ('Disabled') at the start, and the named cast (the collider) at
          CAST + LATER [a script's cast goes all the same: 满血帧 56; a player's click would be refused]
"""
from missions import super_bench
from parts import Script, Test, status
import checks.engine_scripts8 as s8

OFF_AT, CAST, LATER = 10.0, 75, 300
RUN = {'status': 20.0, 'power': 10.0, 'pfire': 20.0, 'pdis': 40.0}
GE = 3
LEVELS = (0, 1, 300, 1000, 1001, 1300)
TEAM_STATUS, BASE_POWER = 'TEAM_CHANGE_OBJECT_' + 'STATUS', 'PLAYER_SET_' + 'BASE_POWER'
P_FIRE, P_AVAIL = 'PLAYER_FIRE_SPECIAL_' + 'POWER_AT_WAYPOINT', 'PLAYER_SPECIAL_POWER_' + 'AVAILABILITY'


def mission():
    return s8.mission('CampPend8')


def super_mission():
    return super_bench.mission('CampPend8S')


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
    t.expect += [('甲敌', OFF_AT - 1, '==', 100), ('乙敌', OFF_AT - 1, '<', 100)]
    s8.watch(t, RUN['status'])
    return t


def power(m):
    t = Test()
    p1 = m.player()
    s8.at(t, 'set', 2.0, [(BASE_POWER, p1, 1000)])
    s8.at(t, 'reset', 6.0, [(BASE_POWER, p1, 300)])
    s8.total(t, 'CNV_S8_Power', '电级', [(1, ('PLAYER_EXCESS_POWER_' + 'COMPARE_VALUE', p1, GE, n)) for n in LEVELS])
    t.expect += [('电级', 4, '==', 4)]
    s8.watch(t, RUN['power'], 0.5)
    return t


def _super(m, which):
    t = Test()
    p1 = m.player('p1')
    power, spot = super_bench.POWER_P, m.mark('proton spot')
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


MISSION = {'pend_scripts8': mission, 'pend_scripts8s': super_mission}
CHECKS = {'pend_scripts8': {'status': status_, 'power': power},
          'pend_scripts8s': {'pfire': lambda m: _super(m, 'pfire'), 'pdis': lambda m: _super(m, 'pdis')}}
