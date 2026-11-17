"""SpawnBehavior third slice: Allied factory drone loss and recovery across a power outage.

Retail energy: AlliedWarFactory -50, AlliedPowerPlant +100. Delete the sole plant
at 12s (excess -50), create its replacement at 30s. The latter must finish unpacking
before supply returns; use PLAYER_HAS_POWER, not the creation timer, as the reference.
Initial prediction from KillSpawnsOnDisabled=true was drone removal. The bench
refuted it: a player's power shortage does not remove this factory's drones.
Four counters: all drones, drones near factory, power (100 powered / 10 dark plus
1 excess=50 / 2 excess=-50), frames since actual power recovery after creation.
No damaged vehicles: autonomous repair/slaving is outside this probe.

Bench 2026-11-11 CampSpPowPower_mcp_1111_071538: s1-s10 3/3/101/0,
s11-s33 3/3/12/0, s34 3/3/101/15, s61 3/3/101/425. No count
transition through the outage or recovery. True module disabling, drone identity
and replacement after a death during an outage remain unmeasured.
"""
from maps import probe_range
from parts import Mission, Script, Test, counted, kindof, square
from checks.engine_spawn import FACTORY, DRONE, POWER, AROUND

CUT, RESTORE, RUN = 12.0, 30.0, 60.0


def mission():
    m = Mission(name='CampSpPow', map=probe_range, units=[], facts={})
    m.put(FACTORY, 'order gun', side='p1', role='factory', name='UNIT - CNV SpPow Factory')
    m.put(POWER, 'power 1', side='p1', role='plant', name='UNIT - CNV SpPow Plant')
    m.waypoint('restore', 'Test SpPow Restore', 'power 1')
    m.spawns |= {DRONE, POWER}
    return m


def check(m):
    t = Test()
    p1 = m.player('p1')
    t.scripts += [
        Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1),
               ('SET_MILLISECOND_TIMER', 'Test Cut', CUT),
               ('SET_MILLISECOND_TIMER', 'Test Restore', RESTORE)]),
        Script('Test - cut', [('TIMER_EXPIRED', 'Test Cut')], [('NAMED_DELETE', m.role('plant').name)]),
        Script('Test - restore', [('TIMER_EXPIRED', 'Test Restore')], [
               ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'UNIT - CNV SpPow New Plant', POWER,
                m.team('p1'), 'Test SpPow Restore'), ('SET_FLAG', 'Test Restoring', 1)])]
    t.areas['Test All'] = square(2500, 2500, 2700)
    t.areas['Test Factory'] = square(*m.site('order gun'), AROUND)
    for suffix, label, area in (('All', '无人机总数', 'Test All'), ('By', '厂旁', 'Test Factory')):
        counted('CNV_SpPow_' + suffix, label, t, kind=kindof('DRONE'), area=area, player=p1, most=6)
    t.counters += [('CNV_SpPow_Power', '电力'), ('CNV_SpPow_Frames', '复电帧')]
    t.scripts.append(Script('Test - power zero', [], [('SET_COUNTER', 'CNV_SpPow_Power', 0)], once=False))
    for label, condition, value in (
            ('on', ('PLAYER_HAS_POWER', p1), 100), ('off', ('PLAYER_HAS_NO_POWER', p1), 10),
            ('surplus', ('PLAYER_EXCESS_POWER_COMPARE_VALUE', p1, 2, 50), 1),
            ('deficit', ('PLAYER_EXCESS_POWER_COMPARE_VALUE', p1, 2, -50), 2)):
        t.scripts.append(Script('Test - power ' + label, [condition],
                               [('INCREMENT_COUNTER', value, 'CNV_SpPow_Power')], once=False))
    t.scripts.append(Script('Test - recovered frames', [('FLAG', 'Test Restoring', 1), ('PLAYER_HAS_POWER', p1)],
                           [('INCREMENT_COUNTER', 1, 'CNV_SpPow_Frames')], once=False))
    t.expect = [('无人机总数', 2, '==', 3), ('厂旁', 2, '==', 3),
                ('电力', 2, '==', 101, 8), ('电力', 16, '==', 12, 28),
                ('电力', 42, '==', 101), ('复电帧', 2, '==', 0, 28),
                ('复电帧', 42, '>=', 100)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_spawn_power': mission}
CHECKS = {'engine_spawn_power': {'power': check}}
