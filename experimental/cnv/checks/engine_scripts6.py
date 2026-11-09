"""Engine probe, the script machinery (docs/engine/inventory.md, the heaviest inferred script items with no unit in
them): CONDITION_TRUE, DISABLE_SCRIPT / ENABLE_SCRIPT, NO_OP, CALL_SUBROUTINE, a script's ELSE actions, SET_TIMER,
SET_RANDOM_COUNTER, SET_RANDOM_MSEC_TIMER, COUNTER_SECONDS, COUNTER_COUNTER. Mission here (build engine_scripts6) on
maps/probe_border.py, no units: every reading is a counter (checks `switch`: 帧 开关 自关 子程序; `timers`: 否则 随机 计时 -- four lines fit;
both run every script). What the Generals source / the
engine model (RA3-EngineModel ra3model/scripts.py, 15 frames a second) predicts is in brackets.

  帧    a repeating script, CONDITION_TRUE only, adds 1 a frame; DISABLE_SCRIPT on it at OFF_AT, ENABLE_SCRIPT at
        ON_AT. [15 a second, flat from OFF_AT to ON_AT, then on again]
  开关  sum of: 1 a script off at the start ([off]), never enabled [never]; 2 one off at the start, ENABLE_SCRIPT at
        ARM_AT [2 from ARM_AT]; 4 a once-script switched off by a script before it in the list, the same frame [never];
        8 a once-script switched off by a script after it, the same frame [8: it already ran]; 16 a once-script that
        adds 16 and is ENABLE_SCRIPTed again at REARM_AT [16, then 32: a fired once-script is only switched off]
        -- [24 at the start, 26 from ARM_AT, 42 from REARM_AT]
  自关  a repeating script: add 1, NO_OP, DISABLE_SCRIPT itself, add 10 [11 and stays: the actions after the switch
        still run in that pass, NO_OP changes nothing]
  子程序 a caller runs CALL_SUBROUTINE at CALL1 and CALL2 on: S1 a once-sub adding 1 [1: closed after the first call];
        S2 a repeating sub adding 10 [20; never run by the frame pass itself]; S4 a repeating sub off at the start
        adding 100 [0: an inactive sub is not run] -- [11 from CALL1, 21 from CALL2]
  否则  1 a once-script whose condition never holds, ELSE adds 1 [1 and stays: Generals closes a once-script after its
        ELSE too]; S3 a repeating sub whose condition never holds, ELSE adds 10, called at CALL1 and CALL2 [10, 20]
        -- [1, 11 from CALL1, 21 from CALL2]
  随机  SET_RANDOM_COUNTER(R, 1, 3) every 0.5 s (a timer re-armed); a value v seen adds 2^v once [14: 1..3 inclusive,
        0 and 4 never]
  计时  sum of: 1 SET_TIMER 45 expired [at 3 s: frames]; 2 SET_RANDOM_MSEC_TIMER(T, 6, 6) expired [6 s: (timer, lo,
        hi) in seconds]; 4 SET_RANDOM_MSEC_TIMER(T, 8, 10) expired [8..10 s]; 8 COUNTER_SECONDS(a 20 s timer, <=, 15)
        [5 s: the seconds left]; 16 COUNTER_SECONDS(the same, <, 12) [8 s]; 32 COUNTER_COUNTER(帧, >=, K = 60)
        [4 s] -- [1 at 3, 33 at 4, 41 at 5, 43 at 6, 59 at 8, 63 by 10]

读数 (bench 2026-11-09, run_queue engine_scripts6:switch / :timers, both PASS; the bench's seconds run ~2 ahead of
mission time here: 帧 45 at s1 = 3 s; sim pair tests/test_simbench.py test_scripts6_*). Every bracket held:
  switch  帧 45 60 75 90 105 ... 150 at s8, 151 s9-s12, 167 at s13 and on 15 a second (287 at s21): CONDITION_TRUE
          holds every frame, 15 frames a second; DISABLE_SCRIPT stops a repeating script (151 = frame 151, the timer's
          10 s), ENABLE_SCRIPT starts it again. 开关 24 at s1, 26 from s2, 42 from s4: an [off] script never runs
          till enabled; DISABLE_SCRIPT from an earlier script in the same frame stops a once-script before its turn,
          from a later one too late; ENABLE_SCRIPT re-arms a fired once-script (16 -> 32). 自关 11 from s1: the
          actions after a script's own DISABLE_SCRIPT still run in that pass, NO_OP is nothing, the script stays
          off. 子程序 11 from s1 (CALL1), 21 from s3 (CALL2): a once-sub runs on its first call only, a repeating sub
          on each call and never in the frame pass, an [off] sub not at all.
  timers  否则 11 at s1, 21 from s3: a once-script's ELSE ran once and closed it; a called sub's ELSE runs when its
          condition fails. 随机 6 at s1, 14 from s3: SET_RANDOM_COUNTER(c, 1, 3) gives 1, 2 and 3, never 0 or 4
          (inclusive). 计时 1 at s2 (SET_TIMER 45 = 45 frames, 3 s), 33 at s3 (COUNTER_COUNTER 帧 >= 60 at 4 s), 41 at
          s4 (COUNTER_SECONDS <= 15 of a 20 s timer at 5 s: the seconds left), 43 s5-s6 (SET_RANDOM_MSEC_TIMER(t, 6, 6)
          at 6 s: (timer, lo, hi) in seconds), 63 from s7 (COUNTER_SECONDS < 12 at 8 s, the (8, 10) one by 9 s).
"""
from maps import probe_border
from parts import Mission, Script, Test

OFF_AT, ON_AT, ARM_AT, REARM_AT, CALL1, CALL2 = 10.0, 14.0, 3.0, 5.0, 2.0, 4.0
RUN = 20.0
LT, LE, EQ, GE = 0, 1, 2, 3


def mission():
    return Mission(name='CampScr6', map=probe_border, facts={})


def _at(t, key, secs, actions):
    timer = f'Test S6 {key} Timer'
    t.scripts += [Script(f'Test - S6 {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Test - S6 {key}', [('TIMER_EXPIRED', timer)], actions)]


def _add(n, counter):
    return ('INCREMENT_COUNTER', n, counter)


SHOW = {'switch': ('帧', '开关', '自关', '子程序'), 'timers': ('否则', '随机', '计时')}


def core(m, show):
    t = Test()
    F, SW, SELF, SUB, ELSE, RND, CLK = (f'CNV_S6_{k}' for k in ('Frames', 'Switch', 'Self', 'Sub', 'Else', 'Rnd',
                                                                  'Clock'))
    t.counters += [(F, '帧'), (SW, '开关'), (SELF, '自关'), (SUB, '子程序'), (ELSE, '否则'), (RND, '随机'),
                   (CLK, '计时')]
    never = ('FLAG', 'CNV S6 Never', 1)
    s = t.scripts
    s.append(Script('Test - S6 init', [], [('SET_COUNTER', c, 0) for c, _ in t.counters]
                    + [('SET_COUNTER', 'CNV_S6_R', 9), ('SET_COUNTER', 'CNV_S6_K', 60)]))
    # 帧
    s.append(Script('Test - S6 frames', [('CONDITION_TRUE',)], [_add(1, F)], once=False))
    _at(t, 'off', OFF_AT, [('DISABLE_SCRIPT', 'Test - S6 frames')])
    _at(t, 'on', ON_AT, [('ENABLE_SCRIPT', 'Test - S6 frames')])
    # 开关
    s.append(Script('Test - S6 never on', [], [_add(1, SW)], active=False))
    s.append(Script('Test - S6 armed later', [], [_add(2, SW)], active=False))
    _at(t, 'arm', ARM_AT, [('ENABLE_SCRIPT', 'Test - S6 armed later')])
    s.append(Script('Test - S6 cut before', [], [('DISABLE_SCRIPT', 'Test - S6 victim before')]))
    s.append(Script('Test - S6 victim before', [], [_add(4, SW)]))
    s.append(Script('Test - S6 victim after', [], [_add(8, SW)]))
    s.append(Script('Test - S6 cut after', [], [('DISABLE_SCRIPT', 'Test - S6 victim after')]))
    s.append(Script('Test - S6 rearmed', [], [_add(16, SW)]))
    _at(t, 'rearm', REARM_AT, [('ENABLE_SCRIPT', 'Test - S6 rearmed')])
    # 自关
    s.append(Script('Test - S6 self', [], [_add(1, SELF), ('NO_OP',), ('DISABLE_SCRIPT', 'Test - S6 self'),
                                           _add(10, SELF)], once=False))
    # 子程序, 否则
    s.append(Script('Test - S6 S1', [], [_add(1, SUB)], sub=True))
    s.append(Script('Test - S6 S2', [], [_add(10, SUB)], once=False, sub=True))
    s.append(Script('Test - S6 S3', [never], [_add(1000, ELSE)], orelse=[_add(10, ELSE)], once=False, sub=True))
    s.append(Script('Test - S6 S4', [], [_add(100, SUB)], once=False, sub=True, active=False))
    calls = [('CALL_SUBROUTINE', f'Test - S6 {k}') for k in ('S1', 'S2', 'S3', 'S4')]
    _at(t, 'call1', CALL1, calls)
    _at(t, 'call2', CALL2, calls)
    s.append(Script('Test - S6 else once', [never], [_add(1000, ELSE)], orelse=[_add(1, ELSE)]))
    # 随机
    s.append(Script('Test - S6 roll', [], [('SET_MILLISECOND_TIMER', 'Test S6 Roll', 0.5)]))
    s.append(Script('Test - S6 reroll', [('TIMER_EXPIRED', 'Test S6 Roll')],
                    [('SET_RANDOM_COUNTER', 'CNV_S6_R', 1, 3), ('SET_MILLISECOND_TIMER', 'Test S6 Roll', 0.5)],
                    once=False))
    s += [Script(f'Test - S6 seen {v}', [('COUNTER', 'CNV_S6_R', EQ, v)], [_add(2 ** v, RND)]) for v in range(5)]
    # 计时
    s.append(Script('Test - S6 clocks', [], [('SET_TIMER', 'Test S6 Frames45', 45),
                                             ('SET_RANDOM_MSEC_TIMER', 'Test S6 Six', 6.0, 6.0),
                                             ('SET_RANDOM_MSEC_TIMER', 'Test S6 Eight', 8.0, 10.0),
                                             ('SET_MILLISECOND_TIMER', 'Test S6 Twenty', 20.0)]))
    s += [Script('Test - S6 t45', [('TIMER_EXPIRED', 'Test S6 Frames45')], [_add(1, CLK)]),
          Script('Test - S6 t6', [('TIMER_EXPIRED', 'Test S6 Six')], [_add(2, CLK)]),
          Script('Test - S6 t8', [('TIMER_EXPIRED', 'Test S6 Eight')], [_add(4, CLK)]),
          Script('Test - S6 le15', [('COUNTER_SECONDS', 'Test S6 Twenty', LE, 15.0)], [_add(8, CLK)]),
          Script('Test - S6 lt12', [('COUNTER_SECONDS', 'Test S6 Twenty', LT, 12.0)], [_add(16, CLK)]),
          Script('Test - S6 k60', [('COUNTER_COUNTER', F, GE, 'CNV_S6_K')], [_add(32, CLK)])]
    t.expect += [('帧', 6, '>', 50), ('自关', 2, '==', 11), ('开关', RUN - 2, '==', 42), ('子程序', RUN - 2, '==', 21),
                 ('否则', RUN - 2, '==', 21), ('随机', RUN - 2, '==', 14), ('计时', RUN - 2, '==', 63)]
    t.counters = [(c, label) for c, label in t.counters if label in SHOW[show]]     # four lines fit; all scripts run
    t.expect = [e for e in t.expect if e[0] in SHOW[show]]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1.0, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_scripts6': mission}
CHECKS = {'engine_scripts6': {k: (lambda m, k=k: core(m, k)) for k in SHOW}}
