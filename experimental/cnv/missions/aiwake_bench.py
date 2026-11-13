"""Engine probe (line B): does a side with an aiPersonality run its teams before the mission wakes it?

Bench aialobslo (E99 / E101, missions/aialphaclose_bench.py, wake script at 10 s = f150) shows the AI's named team
empty at f17, 4 members at f21 and its first team move at f26 -- long before f150; the simulator only builds the AI
player at the wake. Two readings fit:
  H-a  the wake already ran at f0: its only condition is TIMER_EXPIRED and a never-set timer counts as expired, so if
       it is tested before 'CNV AI - Start' sets the timer, UNIT_AI_TRANSFER_ALL / MAKE_BASE happen at once
  H-b  a side with a personality runs teams / states from frame 0, whatever the wake does
aialobsw is aialobslo with the wake moved to 30 s AND gated by a frame tick >= WAKE_TICK (so it cannot run at f0).
H-a: the team forms and leaves only after ~f450 (步兵在家 4 until ~s30); H-b: 4 members at ~f21 again, out by ~s17.
Counters: 帧 (the tick: one per script pass), 唤醒前 (passes before the wake script ran).
"""
from missions import aialphaclose_bench as ac
from parts import Script

WAKE_AT = 30.0
WAKE_TICK = 450                         # script passes: 30 s at 15 a second
TICK = 'CNV_AW_Tick'
PRE = 'CNV_AW_Pre'
WOKE = 'CNV AW Woke'


def mission():
    m = ac.mission(False, observe=True)
    m.name = 'CampAlObsW'
    start = next(s for s in m.scripts if s.name == 'CNV AI - Start')
    start.do = [a if a[0] != 'SET_MILLISECOND_TIMER' else (a[0], a[1], WAKE_AT) for a in start.do]
    wake = next(s for s in m.scripts if s.name == 'CNV AI - Wake')
    wake.when = list(wake.when) + [('COUNTER', TICK, 3, WAKE_TICK)]
    wake.do = list(wake.do) + [('SET_FLAG', WOKE, 1)]
    m.scripts += [Script('CNV AW - tick', [], [('INCREMENT_COUNTER', 1, TICK)], once=False),
                  Script('CNV AW - before wake', [('FLAG', WOKE, 0)], [('INCREMENT_COUNTER', 1, PRE)], once=False)]
    m.facts.update({'wake at': WAKE_AT, 'wake tick': WAKE_TICK, 'tick counter': TICK, 'pre counter': PRE})
    return m


MISSION = {'aialobsw': mission}
