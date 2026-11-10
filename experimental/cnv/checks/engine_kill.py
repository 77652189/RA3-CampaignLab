"""Engine unit test: the kill chain (ADR 0019 layer 3; docs/engine/weapons.md; engine line C round 6) -- what a shooter
does between a kill and its next shot. engine_clip read the weapon's own rhythm (the coil: a shot every 48 frames, so
a 480-health tank dies to two shots in 96 frames); the powerdef bench shows one tank per ~125 frames, ~29 frames more
per KILL. This probe measures them: one shooter (engine_clip's V4 copy, instant, damage KILL = more than any target's
health) and four 10 000-health Hammers in a row, NO_ATTACK so they only stand; each shot kills one.

Variants (ca coil+auto, co coil+ordered, ba bare+auto, bo bare+ordered, c3 clip3+auto, pa pre-only+auto; id suffix: timers (pre-attack s, firing s, reload s, clip, ReAcquireDetailType), how the next target comes):
  auto   the order names target 1 only; targets 2-4 are taken by the shooter itself (auto-acquire)
  order  every target is ordered by script the frame the one before is destroyed
  clip3  the 3-shot clip (no pre-attack, firing 0.3, reload 2.0), auto: does the clip go on across a kill?
  bare   no pre-attack, firing 0, reload 0.1, auto: the shortest cycle, the kill gap with nothing to hide behind
(each in a 'coil' (pre 2.5, firing 0.5, reload 0.1) and a 'bare' timer set where it makes sense; see VARIANTS).

Counters (one line a target): the frames in which that target is still alive and the one before is gone (target 1:
from the order). A kill shows as the counter standing still; the spans are the shooter's frames to the kill, and
span(k) - first-shot-frames is the kill chain's extra. The reading is the frame count the script saw, one more than the
frame the damage landed (docs/engine/weapons.md 1).

Bench 11-09 (round 6; work/bench_results/engine_kill__<variant>.json; pa not run). Counter per target = frames between
the kill before and this one (target 1: from the order); one kill = one shot:
  co (coil, ordered each kill)  40 / 48 / 48 / 48   -> the weapon's own cycle, NO extra between kills
  ca (coil, auto-acquire)       40 / 96 (then 4th 96; 3rd read 0 = it died out of order) -> auto adds one more
                                full cycle (+48) before the next shot
  bo (bare, ordered)            2 / 2 / 2 / 2
  ba (bare, auto)               2 / 5 / - / 4      -> auto adds +3 (about the gap + 1)
  c3 (clip3 0 / 0.3 / 2.0, auto)  2 / 10 / - / 8   (gap inside the clip is 5; ordered not run)
So the ~29 frames a kill the powerdef coil loses are the AUTO-acquire's: a shooter that picks its next target itself
waits (coil: +48 after a one-shot kill; in powerdef the kill is the 2nd shot and the loss is ~29, so it is not simply
one cycle -- not fitted). An ORDERED next target costs nothing. Next: ordered vs auto with a 2-shot kill (the
powerdef case), 3 / 4 shot kills, and the 3rd-target order (which of the idle targets the shooter takes).
"""
from maps import probe_range
from parts import Mission, Script, Test
from checks.engine_clip import clip_v4
from checks.engine_missile import FAR, TARGET_ID, target

ORDER = 6.0
KILL = 50000.0                          # more than the target's 10 000 whatever its armour
N = 4
SPOTS = [(0, FAR), (90, FAR), (-90, FAR), (180, FAR)]

# id suffix: (timers = (pre, firing, reload, clip, ReAcquireDetailType, spans, run, label), ordered by script?)
VARIANTS = {
    'ca':    ((2.5, 0.5, 0.1, 1, 'PRE_FIRE', (), 0, '线圈时序'), False, 45, '线圈时序，自动索敌'),
    'co':   ((2.5, 0.5, 0.1, 1, 'PRE_FIRE', (), 0, '线圈时序'), True, 45, '线圈时序，脚本逐个下令'),
    'ba':    ((0.0, 0.0, 0.1, 1, 'PRE_FIRE', (), 0, '无前摇'), False, 25, '无前摇，自动索敌'),
    'bo':   ((0.0, 0.0, 0.1, 1, 'PRE_FIRE', (), 0, '无前摇'), True, 25, '无前摇，脚本逐个下令'),
    'c3':   ((0.0, 0.3, 2.0, 3, 'PRE_FIRE', (), 0, '三发夹'), False, 45, '三发夹，自动索敌'),
    'pa':     ((2.5, 0.0, 0.1, 1, 'PRE_FIRE', (), 0, '只有前摇'), False, 45, '只有前摇，自动索敌'),
}


def _uid(k):
    return 'CNV_Kill' + k.title()


def _tid(i):
    return f'{TARGET_ID}K{i}'


def mission():
    units = [clip_v4(k, hit=KILL, spec=v[0], uid=_uid(k)) for k, v in VARIANTS.items()]
    units += [target(id=_tid(i)) for i in range(N)]
    m = Mission(name='CampKill', map=probe_range, units=units, facts={})
    for k in VARIANTS:
        m.put(_uid(k), 'base gun', side='p1', role=f'kill {k}', name=f'UNIT - CNV Kill {k.title()}')
    for i, (dx, dy) in enumerate(SPOTS):
        m.put(_tid(i), 'base gun', dx, dy, side='s1', role=f'kill target {i}', name=f'UNIT - CNV Kill Target {i}')
    return m


def kill_test(m, k):
    timers, by_script, run, label = VARIANTS[k]
    t = Test()
    shooter = m.role(f'kill {k}').name
    tg = [m.role(f'kill target {i}').name for i in range(N)]
    idle = [m.role(f'kill {i}').name for i in VARIANTS if i != k]
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('NAMED_DELETE', x) for x in idle]
    start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in [shooter] + tg]
    start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('UNIT_CHANGE_OBJECT_STATUS', shooter, 'NO_ATTACK', 0),
                             ('NAMED_ATTACK_NAMED', shooter, tg[0]), ('SET_FLAG', 'Test Ordered', 1)]))
    for i in range(N):
        c = f'CNV_Kill_T{i}'
        t.counters.append((c, f'靶{i + 1}'))
        cond = [('FLAG', 'Test Ordered', 1), ('NAMED_NOT_DESTROYED', tg[i])] + \
               ([('NAMED_DESTROYED', tg[i - 1])] if i else [])
        t.scripts.append(Script(f'Test - {c}', cond, [('INCREMENT_COUNTER', 1, c)], once=False))
        if by_script and i:
            t.scripts.append(Script(f'Test - next {i}', [('NAMED_DESTROYED', tg[i - 1]), ('NAMED_NOT_DESTROYED', tg[i])],
                                    [('NAMED_ATTACK_NAMED', shooter, tg[i])], once=False))
    t.expect = [(f'靶{N}', 0, 'ever>=', 1, run - 1)]
    t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_kill': mission}
CHECKS = {'engine_kill': {k: (lambda m, k=k: kill_test(m, k)) for k in VARIANTS}}
