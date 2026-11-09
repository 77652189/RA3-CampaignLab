"""Engine probe, protocol points (simtech.py; the program read in the engine line's notes): mission
missions/protocol_bench.py. What the notes predict is in brackets; the readings go below.

  pts     点数 = Player_1's protocol points (PLAYER_HAS_COMPARISON_POWER_POINTS ==, 0 .. 8, 9 = more), every frame.
          From the start [1: InitialTechPoints], then a step every 2 s:
            2 s  SET_MAX 2, SET_POINTS 2   [2: 1 + 2 > cap 2 -> the cap]
            4 s  SET_POINTS 1              [2: 2 + 1 > 2 -> the cap, not 1 -- the program's own rule]
            6 s  SET_POINTS 0              [0]
            8 s  SET_MAX 0, SET_POINTS 5   [5: a cap below 1 does not limit it]
           10 s  SET_MAX 3, SET_POINTS 0   [3: 5 + 0 > 3 -> the cap, not 0]
           12 s  SET_MAX -1, SET_POINTS 7  [7]
          我方科技 = 1 PLAYER_HAS_PLAYER_TECH(Player_1, PlayerTech_Generic_Rank_1) + 2 (.., PlayerTech_Allied) + 4 (..,
          PlayerTech_Soviet) + 8 (.., PlayerTech_Generic_Rank_2) [3: an Allied player at rank 1]; 敌方点数 = Soviet_1's
          points [1, untouched]; 敌方科技 = the same four of Soviet_1 [5: rank 1 + the Soviet default]
  rank    no setting for Player_1; SET_MAX(Soviet_1, 0), SET_MAX(Soviet_2, 2) at the start. 我方 / 敌二 = their
          points; 二级 = 1 Player_1 + 2 Soviet_1 + 4 Soviet_2 holding PlayerTech_Generic_Rank_2; 升级帧 = the frames run
          when Player_1 first holds rank 2's [1 . 0 until rank experience reaches 360 at 1 a second, frame 5400;
          then 2 . 5: Soviet_1's cap 0 stops its experience, Soviet_2's cap 2 lets the rank's point in]
  ailock  every protocol locked for Soviet_1 in the first frame, none for Soviet_2: 锁了的 / 没锁的 = their points

读数
Bench 2026-11-08 (one run each; the bench's seconds run ~2 s behind the game's; sim pairs in tests/test_simbench.py
test_protocol_*). The game's own rank badge is drawn over the counters' left edge: the OCR reads '?' where a chevron
covers a digit -- read off the frames by eye (pts: work/testbench/runs/CampProtPts_mcp_1108_204243).
  pts     点数 2 2 2 2 2 2 2 (s0.7-3.7: the 4 s SET_POINTS 1 never shows 1) 0 0 0 0, 5 5 5 5, 3 3 3 (SET_POINTS 0 under
          cap 3 gives 3), then 7 -- the program's rule exactly. 我方科技 3. 敌方科技 5. 敌方点数 **0 from the first
          reading**, not 1: see ailock.
  ailock  锁了的 1, 没锁的 0, s1-s21: a campaign computer player (AI not woken) spends its starting point on a
          protocol at once; one with everything locked cannot (simtech.Book.ai_buy).
  rank    (first run, 敌一 in place of 升级帧) 我方 1 to s342, 2 from s362; 敌二 0 throughout (its points spent at
          once, the rank's too); 二级 5 from s352 (Soviet_1 never). Second run: 升级帧 5400 = 360 s x 15 exactly,
          我方 2, 敌二 0, 二级 5.
"""
from parts import Script, Test

RUN = {'pts': 16.0, 'rank': 380.0, 'ailock': 20.0}
LADDER = 9                                      # 0 .. 8 exactly, LADDER = more
STEPS = [(2.0, [('MAX', 2), ('SET', 2)]), (4.0, [('SET', 1)]), (6.0, [('SET', 0)]), (8.0, [('MAX', 0), ('SET', 5)]),
         (10.0, [('MAX', 3), ('SET', 0)]), (12.0, [('MAX', -1), ('SET', 7)])]
NAMES = {'MAX': 'PLAYER_SET_MAX_PLAYER_POWER_POINTS', 'SET': 'PLAYER_SET_PLAYER_POWER_POINTS'}
TECHS = ('PlayerTech_Generic_Rank_1', 'PlayerTech_Allied', 'PlayerTech_Soviet', 'PlayerTech_Generic_Rank_2')


def _at(t, key, secs, actions):
    """actions at `secs` s from the start (a timer of its own)."""
    timer = f'Test {key} Timer'
    t.scripts += [Script(f'Test - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - {key}', [('TIMER_EXPIRED', timer)], actions)]


def _points(t, counter, label, player):
    """counter = the player's protocol points, every frame (LADDER for more than LADDER - 1)."""
    t.counters.append((counter, label))
    t.scripts += [Script(f'Test - {counter} {k}', [('PLAYER_HAS_COMPARISON_POWER_POINTS', player, 2, k)],
                         [('SET_COUNTER', counter, k)], once=False) for k in range(LADDER)]
    t.scripts.append(Script(f'Test - {counter} more', [('PLAYER_HAS_COMPARISON_POWER_POINTS', player, 3, LADDER)],
                            [('SET_COUNTER', counter, LADDER)], once=False))


def _sum(t, counter, label, parts):
    """counter = the sum of the weights whose condition holds, recounted every frame. parts: [(weight, condition)]."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
    t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', w, counter)], once=False)
                  for k, (w, c) in enumerate(parts)]


def _techs(t, counter, label, player):
    _sum(t, counter, label, [(1 << k, ('PLAYER_HAS_PLAYER_TECH', player, n)) for k, n in enumerate(TECHS)])


def _watch(t, run, every=1.0):
    t.bench = [('bench_watch', dict(seconds=run, every=every, sheet=False, lines=len(t.counters)))]


def pts(m):
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    for k, (secs, steps) in enumerate(STEPS):
        _at(t, f'step {k}', secs, [(NAMES[what], p1, n) for what, n in steps])
    _points(t, 'CNV_PT_Points', '点数', p1)
    _techs(t, 'CNV_PT_Techs', '我方科技', p1)
    _points(t, 'CNV_PT_SPoints', '敌方点数', s1)
    _techs(t, 'CNV_PT_STechs', '敌方科技', s1)
    _watch(t, RUN['pts'], 0.5)
    return t


def rank(m):
    t = Test()
    p1, s1, s2 = m.player('p1'), m.player('s1'), m.player('s2')
    t.scripts.append(Script('Test - caps', [], [(NAMES['MAX'], s1, 0), (NAMES['MAX'], s2, 2)]))
    for counter, label, p in (('CNV_PT_P1', '我方', p1), ('CNV_PT_S2', '敌二', s2)):
        _points(t, counter, label, p)
    _sum(t, 'CNV_PT_Rank2', '二级', [(w, ('PLAYER_HAS_PLAYER_TECH', p, TECHS[3])) for w, p in ((1, p1), (2, s1), (4, s2))])
    # 升级帧: the frames the scripts have run (one a frame) when Player_1 first holds rank 2's protocol
    t.counters.append(('CNV_PT_RankAt', '升级帧'))
    t.scripts += [Script('Test - frames', [], [('INCREMENT_COUNTER', 1, 'CNV_PT_Frames')], once=False),
                  Script('Test - rank at', [('PLAYER_HAS_PLAYER_TECH', p1, TECHS[3])],
                         [('SET_COUNTER_TO_COUNTER', 'CNV_PT_RankAt', 'CNV_PT_Frames')])]
    _watch(t, RUN['rank'], 10.0)
    return t


def ailock(m):
    """Every protocol locked for Soviet_1 in the first frame (PLAYER_LOCK_PLAYER_TECH on: the AI's choice skips a
    locked one), none for Soviet_2."""
    import simtech
    t = Test()
    s1, s2 = m.player('s1'), m.player('s2')
    t.scripts.append(Script('Test - lock all', [], [('PLAYER_LOCK_PLAYER_TECH', s1, pid, 1)
                                                    for pid, _, _ in sorted(simtech.protocols().values())]))
    _points(t, 'CNV_PT_L1', '锁了的', s1)
    _points(t, 'CNV_PT_L2', '没锁的', s2)
    _watch(t, RUN['ailock'], 1.0)
    return t


CHECKS = {'engine_protocol': {'pts': pts, 'rank': rank, 'ailock': ailock}}
