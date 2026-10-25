"""The skirmish AI probe (missions/ai_bench.py), read off the counters (all the enemy's: Soviet_1):

wake: asleep it neither builds nor spends; woken it spends and builds (a power plant); told to attack, its army
  comes over to the player's base.
asleep: the control, never woken: no power plant, no money spent, nobody at the player's base the whole run.

Bench 2026-10-25, first run (counted by kind, every player's): asleep it spent nothing; woken it spent the 10000 in
~80 s and its vehicles went from 3 to 5; nothing reached the player's base by 296 s.
"""
from parts import Script, Test, counted, square

LAG = 4.0                                       # the bench's clock runs ~3 s behind the mission's
HOME = 700.0                                    # half-side of the area counted around the player's start
RUN_AFTER_ATTACK = 240.0


def readout(m):
    """Not kind-in-area counts: the engine counts every player's with those (probe/count, 2026-10-25). By template
    (the player's own count) and the has-units test instead."""
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    s1 = m.player('s1')
    t.counters.append(('CNV_AI_Money', '敌方资金'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AI_Money')], once=False))
    counted('CNV_AI_Power', '敌方电厂', t, template='AlliedPowerPlant', player=s1)
    counted('CNV_AI_Barracks', '敌方兵营', t, template='AlliedBarracks', player=s1)
    t.areas['Test home'] = square(*m.site('start'), HOME)
    t.counters.append(('CNV_AI_Home', '在我方'))
    t.scripts += [Script('Test - home zero', [], [('SET_COUNTER', 'CNV_AI_Home', 0)], once=False),
                  Script('Test - home', [('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', s1, 'Test home')],
                         [('SET_COUNTER', 'CNV_AI_Home', 1)], once=False)]
    return t


def wake(m):
    t, f = readout(m), m.facts
    w, a = f['wake at'], f['attack at']
    t.expect += [('敌方电厂', 1, '==', 0, w - LAG), ('敌方资金', 1, '==', 0, w - LAG),
                 ('在我方', 1, '==', 0, w - LAG),
                 ('敌方资金', w + LAG, 'ever>', 0, w + 30),                   # given its money
                 ('敌方电厂', w + LAG, 'ever>=', 1, a),                       # and builds with it
                 ('在我方', a, 'ever==', 1, a + RUN_AFTER_ATTACK)]             # sent over once told to
    t.bench = [('bench_watch', dict(seconds=a + RUN_AFTER_ATTACK, every=5, sheet=False, lines=len(t.counters)))]
    return t


def capped(m):
    """The plan's 敌方AI (missions/ai_plan_bench.py): the generated personality in use -- it builds, never past its
    caps -- and once told to attack, its army hurts the player's base: a guardian lost or the yard damaged (bench
    2026-10-25: "enemy units by the player's start" was its miner at the player's ore, not an attack)."""
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    f, s1 = m.facts, m.player('s1')
    counted('CNV_AI_Power', '敌方电厂', t, template='AlliedPowerPlant', player=s1)
    counted('CNV_AI_Barracks', '敌方兵营', t, template='AlliedBarracks', player=s1)
    counted('CNV_AI_Yard', '我方建造厂血量', t, health=m.role('player yard').name)
    counted('CNV_AI_Guards', '我方守护者', t, template='AlliedAntiVehicleVehicleTech1')
    w, a, run = f['wake at'], f['attack at'], f['watch after attack']
    t.expect += [('敌方电厂', 1, '==', 0, w - LAG), ('敌方电厂', w + LAG, 'ever>=', 1, a),
                 ('敌方电厂', 1, '<=', f['power cap']), ('敌方兵营', 1, '<=', f['barracks cap']),
                 ('我方守护者', 1, '==', 3, a), ('我方守护者', a, 'ever<', 3, a + run)]
    x, y = m.site('base edge')                  # the frames show the attack coming
    t.bench = [('bench_camera', dict(x=x, y=y, look=False)),
               ('bench_watch', dict(seconds=a + run, every=6, sheet=False, lines=len(t.counters)))]
    return t


def asleep(m):
    t, f = readout(m), m.facts
    t.expect += [('敌方电厂', 1, '==', 0), ('敌方资金', 1, '==', 0), ('在我方', 1, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=f['attack at'] + 30, every=5, sheet=False, lines=len(t.counters)))]
    return t
