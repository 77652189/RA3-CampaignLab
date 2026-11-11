"""Engine unit test: pausing and shifting the script timers -- STOP_TIMER, RESTART_TIMER, SUB_FROM_MSEC_TIMER --
nothing on the map but scripts (as engine_script.py: festival, no facts).

A timer shares the counters' table (engine_script out: a 2 s timer read as a counter shows 30, its frames left), so
the counter lines show a timer's own frames left; the expired lines are live (cleared at the top of every frame by a
repeating script, set again below it while TIMER_EXPIRED holds).

  stop   P (10 s at 0) stopped at 2 s, restarted at 5 s; E (2 s at 0) stopped at 4 s, after it ran out.
         Lines: 停表帧 P's frames left; 停表到 P expired (live); 过期停 E expired (live).
         [model (RA3-EngineModel scripts.py, Generals TCounter isCountdownTimer): P 150 -> ~120 at 2 s, holds there
         to 5 s, runs on, out ~3 s late (~13 s); a stopped timer is no countdown: TIMER_EXPIRED false even at 0 --
         过期停 1 from 2 s to 4 s, then 0; RESTART_TIMER only when frames are left]
  shift  S (10 s at 0) SUB_FROM_MSEC_TIMER 5 s at 2 s. Lines: 减帧 S's frames left; 减到 S expired (live).
         [model: S 150 -> ~120 at 2 s -> ~45, out at ~5 s; frames = ceil(seconds x 15)]. The ADD_TO_ twin is not
         in the catalog (mapscript.catalog: no retail map has it, so no ctype to write): not probed (named so here
         that inventory.benched does not take it for measured).

读数 (bench 2026-11-10; the bench's seconds ~1 s ahead of the mission's)
  stop   CampTimerStop_mcp_1110_211657: 停表帧 120 s1-s3, 109 94 80 64 48 34 17 3 s4-s11, -1 from s12; 停表到 1 from
         s12; 过期停 1 s1-s2, 0 from s3. As the model: STOP_TIMER holds the frames, RESTART_TIMER runs them on, a
         stopped timer is not expired at -1. The simulator's readout had hidden running timers (0 while P ran): its
         lines now read the table (sim.py series, eng.value).
  shift  CampTimerShift_mcp_1110_211936: 减帧 32 17 3 s1-s3, -1 from s4; 减到 1 from s4 -- 75 frames off.
Simulator after the fix: each reading 1-2 s later (tests/test_simbench.py test_timer_*).
"""
from maps import festival
from parts import Mission, Script, Test

STEP = 'CNV_Tmr_'


def mission():
    return Mission(name='CampTimer', map=festival, facts={})


def _at(t, key, secs, actions):
    timer = f'{STEP}At_{key}'
    t.scripts += [Script(f'Tmr - {key} timer', [], [('SET_MILLISECOND_TIMER', timer, secs)]),
                  Script(f'Tmr - {key}', [('TIMER_EXPIRED', timer)], actions)]


def _live(t, timer, counter, label):
    """counter 1 while TIMER_EXPIRED timer holds, 0 else (read at the frame's end)."""
    t.scripts += [Script(f'Tmr - {counter} clear', [], [('SET_COUNTER', counter, 0)], once=False),
                  Script(f'Tmr - {counter} set', [('TIMER_EXPIRED', timer)], [('SET_COUNTER', counter, 1)],
                         once=False)]
    t.counters.append((counter, label))


def stop(m):
    t = Test()
    p, e = f'{STEP}P', f'{STEP}E'
    t.scripts.append(Script('Tmr - start', [], [('SET_MILLISECOND_TIMER', p, 10.0), ('SET_MILLISECOND_TIMER', e, 2.0)]))
    _at(t, 'stop p', 2.0, [('STOP_TIMER', p)])
    _at(t, 'stop e', 4.0, [('STOP_TIMER', e)])
    _at(t, 'restart p', 5.0, [('RESTART_TIMER', p)])
    t.counters.append((p, '停表帧'))
    _live(t, p, f'{STEP}POut', '停表到')
    _live(t, e, f'{STEP}EOut', '过期停')
    t.bench = [('bench_watch', dict(seconds=18, every=1, sheet=False, lines=len(t.counters)))]
    return t


def shift(m):
    t = Test()
    s = f'{STEP}S'
    t.scripts.append(Script('Tmr - start', [], [('SET_MILLISECOND_TIMER', s, 10.0)]))
    _at(t, 'sub s', 2.0, [('SUB_FROM_MSEC_TIMER', 5.0, s)])
    t.counters.append((s, '减帧'))
    _live(t, s, f'{STEP}SOut', '减到')
    t.bench = [('bench_watch', dict(seconds=12, every=1, sheet=False, lines=len(t.counters)))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_timer': mission}
CHECKS = {'engine_timer': {'stop': stop, 'shift': shift}}
