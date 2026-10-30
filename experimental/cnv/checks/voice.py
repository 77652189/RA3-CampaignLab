"""Voice probe checks (missions/voice_bench.py), read off the counters:

play: the line played at `play at` s; 播放帧数 counts the frames from then till HAS_FINISHED_AUDIO holds, 播完 is 1
  from then on. A line the game plays runs ~4.8 s (~70 frames at 15 a second); one it cannot find is finished at
  once (a frame or two). The frame a second after the start is looked at for the subtitle.

Bench 2026-10-29: the audio is read from data\\static.12\\cdata -- voice_bench_s (static only) finished in 4 frames,
voice_bench_12 and voice_bench (both) played; the subtitle came up by itself (CampVoice12Play frame 5); but the
4.8 s line took ~212 frames (~14 s) to finish: the FAIL of 播完 stands till that is understood (a sample rate the
encoder wrote wrong, or the event's own settings).
"""
from parts import Script, Test

RUN = 16.0
MIN_FRAMES = 45                                 # 3 s of the 4.8 s line at ~15 frames a second


def play(m):
    t = Test()
    line, at = next(iter(m.voice.events)), m.facts['play at']
    t.counters += [('CNV_Voice_Frames', '播放帧数'), ('CNV_Voice_Done', '播完')]
    t.scripts += [
        Script('Test - play timer', [], [('SET_MILLISECOND_TIMER', 'CNV Voice Play', at)]),
        Script('Test - play', [('TIMER_EXPIRED', 'CNV Voice Play')],
               [('PLAY_SOUND_EFFECT', line), ('SET_FLAG', 'CNV Voice Played', 1)]),
        Script('Test - playing', [('FLAG', 'CNV Voice Played', 1), ('FLAG', 'CNV Voice Finished', 0)],
               [('INCREMENT_COUNTER', 1, 'CNV_Voice_Frames')], once=False),
        Script('Test - finished', [('FLAG', 'CNV Voice Played', 1), ('HAS_FINISHED_AUDIO', line)],
               [('SET_FLAG', 'CNV Voice Finished', 1), ('SET_COUNTER', 'CNV_Voice_Done', 1)])]
    t.expect += [('播完', RUN - 3, '==', 1), ('播放帧数', RUN - 3, '>=', MIN_FRAMES)]
    t.bench = [('bench_watch', dict(seconds=at + 1, every=1, sheet=False, lines=len(t.counters))),
               ('bench_look', dict(note='the subtitle of CNV_TEST_001 at the bottom?')),
               ('bench_watch', dict(seconds=RUN - at - 1, every=1, sheet=False, lines=len(t.counters)))]
    return t
