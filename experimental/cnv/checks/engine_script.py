"""Engine unit test: the script engine's own clock and bookkeeping, nothing on the map but scripts (ADR 0019 layer 1,
the side-by-side of the Python script-engine model against the game).

All four readings freeze within ~2 s; read at s6. Scripts in this order, all on the first frame F:
  early count  [repeat] FLAG run -> +1 early         (before start: does not see run at F)
  start        [once]   run on; timer T 1.1 s; timer Shared 2.0 s; Out = 7; Out := Shared (SET_COUNTER_TO_COUNTER)
  count        [repeat] FLAG run -> +1 frames        (after start: sees run at F)
  stop         [once]   TIMER_EXPIRED T -> run off
  once         [once]   FLAG run -> +1 rearm
  rearm        [once]   COUNTER rearm >= 1 -> ENABLE_SCRIPT once

  计时帧数 frames: 1 + the frames T takes. Model (15 frames/s, ceil, timers tick before the scripts): ceil(16.5) =
    17 -> 18. 30 frames/s would read 35; floor or round 17; ticking after the scripts (OpenSAGE) 19.
  先看帧数 early: one fewer than frames (17) when a change is seen by later scripts the same frame and by earlier
    ones the next frame.
  一次性重开 rearm: 2 when ENABLE_SCRIPT re-arms a one-shot script that has fired (Generals: one-shot = inactive),
    1 when it does not (the old simulator's guess).
  计时器当计数器 out: 30 when counters and timers share one table (a 2 s timer holds 30 frames), 0 when they do
    not, 7 when SET_COUNTER_TO_COUNTER is (source, destination).
"""
from maps import festival
from parts import Mission, Script, Test

RUN, T, EARLY, FRAMES, REARM = 'CNV_Scr_Run', 'CNV_Scr_T', 'CNV_Scr_Early', 'CNV_Scr_Frames', 'CNV_Scr_Rearm'
SHARED, OUT = 'CNV_Scr_Shared', 'CNV_Scr_Out'


def mission():
    return Mission(name='CampScr', map=festival, facts={})


def frames(m):
    t = Test()
    t.scripts += [
        Script('Scr - early count', [('FLAG', RUN, 1)], [('INCREMENT_COUNTER', 1, EARLY)], once=False),
        Script('Scr - start', [], [('SET_FLAG', RUN, 1), ('SET_MILLISECOND_TIMER', T, 1.1),
                                   ('SET_MILLISECOND_TIMER', SHARED, 2.0), ('SET_COUNTER', OUT, 7),
                                   ('SET_COUNTER_TO_COUNTER', OUT, SHARED)]),
        Script('Scr - count', [('FLAG', RUN, 1)], [('INCREMENT_COUNTER', 1, FRAMES)], once=False),
        Script('Scr - stop', [('TIMER_EXPIRED', T)], [('SET_FLAG', RUN, 0)]),
        Script('Scr - once', [('FLAG', RUN, 1)], [('INCREMENT_COUNTER', 1, REARM)]),
        Script('Scr - rearm', [('COUNTER', REARM, 3, 1)], [('ENABLE_SCRIPT', 'Scr - once')])]
    t.counters += [(FRAMES, '计时帧数'), (EARLY, '先看帧数'), (REARM, '一次性重开'), (OUT, '计时器当计数器')]
    t.expect += [('计时帧数', 6, '==', 18), ('先看帧数', 6, '==', 17), ('一次性重开', 6, '==', 2),
                 ('计时器当计数器', 6, '==', 30)]
    t.bench = [('bench_watch', dict(seconds=9, every=3, sheet=False, lines=4))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_script': mission}
CHECKS = {'engine_script': {'frames': frames}}
