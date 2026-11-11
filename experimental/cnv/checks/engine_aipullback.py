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
           faction either. Not settled: the member KindOf filter (masks 0xc000 / 0x1000, not read), the
           template flag bit 13 test, the path test, or the garrison routine never reached in these states.
  aipullh0 not run (aipull0 already shows no-one goes home).
  (11-09, round 69; 血量 = tank 1's health %, read 30 from the set on: UNIT_SET_HEALTH does take)
  aipulli1 FAIL: hurt 0.5 s after the wake, ~1000 from any enemy (no AlphaStrike) -- 血量 30 s9-12, the 4 drive on,
           到远厂 1 @ s13 .. 3 @ s15-16, all dead by s23; 回家 0 from s3
  aipullr1 FAIL, second for second as aipulli1, with SKIRMISH_AI_USE_REPAIRS s1 1 at the hurt: not the repair switch
  aipullp1 FAIL: hurt before the wake (idle, ~400 from the factory): they join the team at 30 % and leave steadily,
           近家 (600) 4 @ s1-5, 3 @ s6-7, 2 @ s8, 1 @ s9-10, 0 from s11 -- no lingering (not sent home and re-recruited)
  aipullbig FAIL, the same as aipullp1 with PullbackInjuredHealthPct 100000: not the health ratio's scale
  So the garrison routine is reached (EnterGarrisons, in the same state functions, worked) and the member gates pass; left: the
  facility search -- the ArmyDef map lookup (key stored on the team / brain), the template's field against the ArmyDef's field, or the
  path test (work/re/l4_micro_engage.md 1.4).
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
  (11-09, round 71; the target beside the tanks, 80-135 off, healed to 100 every frame)
  airevp1 / airevp0 (the far plant): first runs, unhealed, the tanks shot it to 2 % by s8 and both left s19-24 alike
           (target gone). Healed: airevp0 PASS 近厂 4 all 85 s; airevp1 FAIL, the same -- 近厂 4 all along. A plant is a
           tactical target (state 6), and the reverse-move routine runs in states 2 and 4 only.
  airevt1  FAIL (a player's AlliedBaseDefense instead, CleanupPowerAdvantage 1000, UseGatherState off -> state 2):
           no tank moves, 近塔 = 坦克数 = 中圈 all along; the turret kills them one by one 4 @ s1-10, 3 @ s11-22,
           2 @ s23-34, 1 @ s35-46, 0 from s47. airevt0 not run (airevt1 already shows no back-up).
  Left (work/re handoff-b 72): the reverse-move routine's first gate -- a byte flag reached through the member's locomotor data
  (read as a locomotor template flag, not named); the weapon flag check skips too.
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
    elif not build.startswith(('airevp', 'airevt')):  # no guards
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
    elif build.startswith('airevp') or build.startswith('airevt'):
        # airevp: the far plant beside the tanks, no guards (missions CLOSE_AT); airevt: a player's turret there instead
        turret = build.startswith('airevt')
        g = m.find(m.role('rev turret').name) if turret else o
        near, ring = (100.0, 250.0) if turret else (150.0, 300.0)
        t.counters.append(('CNV_PB_PlantHp', '塔血' if turret else '厂血'))
        t.scripts.append(Script('Test - target health', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', g.name,
                                                              'CNV_PB_PlantHp')], once=False))
        # first runs: the tanks shot the plant to 2 % before the wake (s8) and both builds left it s19-24 alike -- the
        # target gone, not a back-up. So the target is healed back every frame: it stays
        t.scripts.append(Script('Test - target keep', [], [('UNIT_SET_HEALTH', g.name, 100.0)], once=False))
        t.areas['CNV_PB_Near'] = square(g.x, g.y, near)
        t.areas['CNV_PB_Ring'] = square(g.x, g.y, ring)
        lab = '近塔' if turret else '近厂'
        counted('CNV_PB_NearC', lab, t, template=tank, area='CNV_PB_Near', player=s1)
        counted('CNV_PB_Far', '中圈', t, template=tank, area='CNV_PB_Ring', player=s1)
        # model: on, every tank backs off to range - 10 (out of the near square) within a micro update or two;
        # off, they stay
        t.expect += ([(lab, wake, 'ever<', 1, wake + 15.0)] if build.endswith('1')
                     else [(lab, wake + 2.0, '>=', 3, wake + 15.0)])
    else:
        t.areas['CNV_PB_Near'] = square(o.x, o.y, 150.0)
        counted('CNV_PB_NearC', '近厂', t, template=tank, area='CNV_PB_Near', player=s1)
        counted('CNV_PB_Far', '到远厂', t, template=tank, area=at.FAR, player=s1)
        t.expect += [('守军数', wake, 'ever>=', 12, end)]
    t.bench = [('bench_watch', dict(seconds=end + at.LAG, every=1, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {k: {'a': (lambda m, k=k: a(m, k))} for k in ('aipull1', 'aipull0', 'aipullh1', 'aipullh0', 'aipullga', 'aipulli1', 'aipullr1', 'aipullp1', 'aipullbig', 'aipullsov', 'aipulljp',
                                                           'airev1', 'airev0', 'airevp1', 'airevp0', 'airevt1', 'airevt0')}
