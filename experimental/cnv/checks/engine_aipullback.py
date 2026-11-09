"""Engine probe: the skirmish AI team's PullbackInjured / ReverseMove (missions/aipullback_bench.py; docs/engine/aiteamstate.md).

  aipull1 / aipull0   a  守军数 (the player's Peacekeepers), 坦克数 (s1 Hammers), 到远厂 (Hammers within 300 of the far
                         plant), 回家 (Hammers within 300 of the AI's war factory)
  airev1 / airev0     a  守军数, 坦克数, 近厂 (Hammers within 150 of the far plant), 到远厂 (within 300)
     once a second, AFTER seconds after the wake

Expectations are the model's; a FAIL is a reading too.
  aipull1   回家 is 1 or more at some time after the wake
  aipull0   回家 stays 0 from the wake + 25 s on (the tanks are at the far plant by then)
  airev*    only that the counters exist (守军数 12 at the wake) -- the per-second readings are the result

Readings (11-09; 4 Hammers vs 12 Peacekeepers, Crush false; tanks reach the plant s15):
  aipull1  FAIL (no retreat): 回家 1 at s1-2 (a tank near the factory at the start), 0 from s3 to the end; 4 tanks s3-24
           (到远厂 1..3 at s12-14, 4 from s15) | 3 @ s25-26 | 2 @ s27-35 | 1 @ s36-37 | 0 @ s38-85; guards 12 all along
  aipull0  PASS, second for second the same as aipull1 (no tank ever goes home)
  airev1   守军 12 -> 11 at s31; 4 tanks s1-22 (近厂 2 @ s19-22) | 3 @ s23-30 (近厂 1 @ s25-29, 0 @ s30) | 2 @ s31-37
           (近厂 1 @ s34-37) | 0 @ s38-85
  airev0   守军 12 all along; 4 tanks to s22 (近厂 1 @ s18, 2 @ s19-22) | 3 @ s23-30 | 2 @ s31-33 (近厂 1) | 1 @ s34-36 |
           0 @ s37-85
  (the first airev1 run's expectation was written as '>=' and so failed at 11 guards; changed to ever>=, same readings)
  aipullh1 FAIL: the 4 tanks set to 30 % at s12 on the road -- they drive on, 到远厂 4 by s15-16, 3 @ s17-20, 2 @ s21,
           1 @ s22-24, 0 from s25; 回家 0 from s4 to the end. Not the shot-down-too-fast window.
  aipullga FAIL: the same with Allied Guardian tanks (the AI's own faction): 4 at the plant s12, 0 by s20, 回家 0. Not the
           faction either. Not settled: the member KindOf filter 0x808990 (masks 0xc000 / 0x1000, not read), the
           template +0xdc bit 13 test, the path test 0x6d9130, or 0x8df430 never reached in these states.
  aipullh0 not run (aipull0 already shows no-one goes home).
  (11-09, round 69; 血量 = tank 1's health %, read 30 from the set on: UNIT_SET_HEALTH does take)
  aipulli1 FAIL: hurt 0.5 s after the wake, ~1000 from any enemy (no AlphaStrike) -- 血量 30 s9-12, the 4 drive on,
           到远厂 1 @ s13 .. 3 @ s15-16, all dead by s23; 回家 0 from s3
  aipullr1 FAIL, second for second as aipulli1, with SKIRMISH_AI_USE_REPAIRS s1 1 at the hurt: not the repair switch
  aipullp1 FAIL: hurt before the wake (idle, ~400 from the factory): they join the team at 30 % and leave steadily,
           近家 (600) 4 @ s1-5, 3 @ s6-7, 2 @ s8, 1 @ s9-10, 0 from s11 -- no lingering (not sent home and re-recruited)
  aipullbig FAIL, the same as aipullp1 with PullbackInjuredHealthPct 100000: not the health ratio's scale
  So 0x8df430 is reached (EnterGarrisons, in the same state functions, worked) and the member gates pass; left: the
  facility search -- the ArmyDef map lookup (key at team / brain + 0x24), template +8 against ArmyDef +0x28, or the
  path test 0x6d9130.
  (11-09, round 70) The ArmyDefinition is found by the player's faction (its Side), so s1 Allied -> AlliedWarFactory
  as the probe has it. aipulli1 with the faction changed:
  aipullsov PASS (Soviet AI, a SovietCrane): 血量 30 from s9, 回家 1 @ s19 .. 4 @ s23, then 坦克数 4 -> 0 by s29 with
           血量 frozen at 39 -- the 4 hurt tanks drive home and into the Crane (SlaughterHordeContain: ground up for
           75 % cash back). Before this run's window moved to wake + 5 s it read FAIL (the window began at s35).
  aipulljp  FAIL (Japan AI, a JapanWarFactory): as aipulli1 -- they drive on, all dead by s25, 回家 0.
  So the pull-back works, but only to a repair place the vehicle can enter: retail's Allied / Japan war factories
  (no vehicle Contain) are never found (the facility search's reach test, or the template match -- not told apart);
  the Soviet AI recycles its hurt vehicles in the Crane.
  ReverseMove: airev1 / airev0 differ too little to read a back-up (近厂 2 in both at s19-22).
"""
from checks import engine_aitarget as at
from parts import Script, Test, counted, square

AFTER = 70.0
LATE = 25.0
HURT_AT = 12.0                           # aipullh*: the tanks are on the road (at the far plant s15)
IDLE = ('aipulli1', 'aipullr1', 'aipullp1', 'aipullbig', 'aipullsov', 'aipulljp')   # hurt at the wake, ~1000 from any enemy (p1: before it)
IDLE_HURT = {'aipulli1': 0.5, 'aipullr1': 0.5, 'aipullp1': -9.0, 'aipullbig': -9.0, 'aipullsov': 0.5, 'aipulljp': 0.5}   # s after the wake
HURT = 30.0                              # % -- under PullbackInjuredHealthPct 0.35


def a(m, build):
    t = Test()
    s1, p1 = m.player('s1'), m.player('p1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1)]))
    o = m.find(m.role('far plant').name)
    t.areas[at.FAR] = square(o.x, o.y, 300.0)
    inf, tank = m.cnv_units
    wake = m.facts['wake at']
    end = wake + AFTER
    tanks = [o.name for o in m.objects if o.template == tank and o.side == 's1']
    if build in IDLE:                    # four counters at most: 血量 (tank 1's health %) for 守军数
        t.counters.append(('CNV_PB_Health', '血量'))
        t.scripts.append(Script('Test - health', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', tanks[0],
                                                       'CNV_PB_Health')], once=False))
    else:
        counted('CNV_PB_Guards', '守军数', t, template=inf, player=p1, most=13)
    counted('CNV_PB_Tanks', '坦克数', t, template=tank, player=s1)
    if build.startswith('aipull'):
        f = m.find(m.role('ai factory').name)
        t.areas[at.HOME] = square(f.x, f.y, 300.0)
        if build in ('aipullp1', 'aipullbig'):
            t.areas['CNV_PB_NearHome'] = square(f.x, f.y, 600.0)
            counted('CNV_PB_NearH', '近家', t, template=tank, area='CNV_PB_NearHome', player=s1)
        else:
            counted('CNV_PB_Far', '到远厂', t, template=tank, area=at.FAR, player=s1)
        counted('CNV_PB_Home', '回家', t, template=tank, area=at.HOME, player=s1)
        if build.startswith('aipullh') or build == 'aipullga' or build in IDLE:
            timer = 'Test - hurt timer'
            t.scripts += [Script('Test - hurt set', [], [('SET_MILLISECOND_TIMER', timer,
                                                          wake + IDLE_HURT[build] if build in IDLE else HURT_AT)]),
                          Script('Test - hurt tanks', [('TIMER_EXPIRED', timer)],
                                 [('UNIT_SET_HEALTH', n, HURT) for n in tanks])]
        if build == 'aipullr1':          # after the wake's SKIRMISH_AI_USE_REPAIRS 0
            t.scripts.append(Script('Test - repairs on', [('TIMER_EXPIRED', timer)],
                                    [('SKIRMISH_AI_USE_REPAIRS', s1, 1)]))
        if build in ('aipull1', 'aipullh1', 'aipullga') or build in IDLE:
            # IDLE: from 5 s after the wake (aipullsov's Soviet tanks were home s19-28, wake ~s9, then ground up)
            t.expect += [('回家', wake + (5.0 if build in IDLE else LATE), 'ever>=', 1, end)]
        else:
            t.expect += [('回家', wake + LATE, '==', 0, end)]
    else:
        t.areas['CNV_PB_Near'] = square(o.x, o.y, 150.0)
        counted('CNV_PB_NearC', '近厂', t, template=tank, area='CNV_PB_Near', player=s1)
        counted('CNV_PB_Far', '到远厂', t, template=tank, area=at.FAR, player=s1)
        t.expect += [('守军数', wake, 'ever>=', 12, end)]
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('aipull1', 'aipull0', 'aipullh1', 'aipullh0', 'aipullga', 'aipulli1', 'aipullr1', 'aipullp1', 'aipullbig', 'aipullsov', 'aipulljp',
                                                           'airev1', 'airev0')}
