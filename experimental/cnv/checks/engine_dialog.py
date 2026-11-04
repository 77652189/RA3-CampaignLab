"""Engine unit test: when the dialogue subtitle panel clears.

The panel: bottom of the screen, yellow lines on a dark band, the subtitles of played dialogue (not the military
caption box at the top, checks/engine_caption.py). The game data sets it to hold a line 20 s; it was seen to clear
after ~5.4 s.

Bench 2026-11-04: it clears 5.1 - 5.6 game seconds after a line comes up, whatever the line's length (retail lines of
3.3, 4.3 and 4.34 s) and whatever speed the bench runs the mission at (x1, x2.9, x8) -- not the 20 s, not the
audio's end (at x2.9 the 4.34 s line's audio was still playing when the panel cleared), not real seconds (at x8 the
audio had not finished in 33 game seconds, the panel was long gone). At x1, as a player sees it: up at 0.9 s, the
audio done at 5.3 s, the panel gone between 5.7 and 6.0 s. So a dubbed line's subtitle stays ~5.5 s however long it is.

The checks: one retail line (its own subtitle) at PLAY_AT s, or two 20 s apart (pair); real watches at x1 (a frame
every 0.35 s), fast at x2.9 (every 1 s), slow at x8 (every 4 s). 第k句帧数 counts the game frames from the line's start
till HAS_FINISHED_AUDIO -- the game's own clock (15 a second) to time the frames by, since the bench's seconds are its
estimate. The panel is read off the frames: mean brightness and bright text pixels in its box (x 380-820, y 566-632
of the 1280x720 frame), no counter can see it.
"""
from maps import festival
from parts import Mission, Script, Test

PLAY_AT, RUN = 3.0, 33.0
LINE = 'MA01_AlliedIntel24'                     # retail, 4.34 s, with its own subtitle
PAIR = (('MA01_AlliedIntel36', PLAY_AT), ('MA01_AlliedIntel40', PLAY_AT + 20))     # 3.3 s and 4.3 s


def mission():
    m = Mission(name='CampDialog', map=festival, facts={})
    m.put('AlliedAntiVehicleVehicleTech1', 'west field', 250, 30, name='UNIT - CNV Dialog Guardian', role='guardian')
    return m


def _line(t, k, line, at):
    """Play `line` at `at` s; counter k counts the frames till it has finished."""
    frames, played, done = f'CNV_Dialog_Frames{k}', f'CNV Dialog Played {k}', f'CNV Dialog Finished {k}'
    t.counters.append((frames, f'第{k}句帧数'))
    t.scripts += [
        Script(f'Test - play {k} timer', [], [('SET_MILLISECOND_TIMER', f'CNV Dialog Play {k}', at)]),
        Script(f'Test - play {k}', [('TIMER_EXPIRED', f'CNV Dialog Play {k}')],
               [('PLAY_SOUND_EFFECT', line), ('SET_FLAG', played, 1)]),
        Script(f'Test - playing {k}', [('FLAG', played, 1), ('FLAG', done, 0)],
               [('INCREMENT_COUNTER', 1, frames)], once=False),
        Script(f'Test - finished {k}', [('FLAG', played, 1), ('HAS_FINISHED_AUDIO', line)], [('SET_FLAG', done, 1)])]


def _watch(every, lines=((LINE, PLAY_AT),), run=RUN):
    def check(m):
        t = Test()
        for k, (line, at) in enumerate(lines, 1):
            _line(t, k, line, at)
        t.expect += [('第1句帧数', 2, '>', 0)]            # the line played (the panel itself is read off the frames)
        t.bench = [('bench_watch', dict(seconds=run, every=every, sheet=False, lines=len(t.counters)))]
        return t
    return check


# the builds this module makes and their checks (cnv/registry.py); the bench's rate is set by the frame interval
MISSION = {'engine_dialog': mission}
CHECKS = {'engine_dialog': {'real': _watch(0.35, run=14.0), 'fast': _watch(1), 'slow': _watch(4),
                            'pair': _watch(1, PAIR, run=48.0)}}
