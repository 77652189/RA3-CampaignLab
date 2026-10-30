"""Voice probe checks (missions/voice_bench.py), read off the counters:

play: the line played at `play at` s; 播放帧数 counts the frames from then till HAS_FINISHED_AUDIO holds, 播完 is 1
  from then on. A line the game plays runs ~4.8 s (~70 frames at 15 a second); one it cannot find is finished at
  once (a frame or two). The frame a second after the start is looked at for the subtitle.

Bench 2026-10-29: the audio is read from data\\static.12\\cdata -- voice_bench_s (static only) finished in 4 frames,
voice_bench_12 and voice_bench (both) played; the subtitle came up by itself (CampVoice12Play frame 5). The 4.8 s
line took 212 frames to finish, at 24 kHz and again at 48 kHz (75c5c90): not the sample rate. The control (`ref`,
retail's MA01_AlliedIntel24, 4.34 s) took 190: 44 frames per second of audio for both (44.2 and 43.8), so a line
plays at its own length and the pack is right. Why an audio second is 44 script frames when a 10 s timer is 150
(15 a second) is not known (the bench holds the game between calls: the audio may run on in real time); so the
audio's frames are never converted to mission seconds, only compared with the control's. Expected: frames within
15% of 44 x the line's length (bench 2026-10-30: play 213, ref 190, both PASS).
"""
from parts import Script, Test

RUN = 20.0
FRAMES_PER_S = 44.0                             # per second of audio (bench 2026-10-30: 212 / 4.8, 190 / 4.34)
TOLERANCE = 0.15
LINE_SECONDS = 4.8                              # CNV_TEST_001 (the pack's 115200 samples at 24 kHz)
REFERENCE_SECONDS = 4.34
REFERENCE = 'MA01_AlliedIntel24'                # a retail mission line: the control for the same check


def play(m):
    return _play(m, next(iter(m.voice.events)), LINE_SECONDS)


def ref(m):
    """The same check on a retail line: the frames a line of that length takes with nothing of ours in it."""
    return _play(m, REFERENCE, REFERENCE_SECONDS)


def _play(m, line, seconds):
    t = Test()
    frames = FRAMES_PER_S * seconds
    at = m.facts['play at']
    t.counters += [('CNV_Voice_Frames', '播放帧数'), ('CNV_Voice_Done', '播完')]
    t.scripts += [
        Script('Test - play timer', [], [('SET_MILLISECOND_TIMER', 'CNV Voice Play', at)]),
        Script('Test - play', [('TIMER_EXPIRED', 'CNV Voice Play')],
               [('PLAY_SOUND_EFFECT', line), ('SET_FLAG', 'CNV Voice Played', 1)]),
        Script('Test - playing', [('FLAG', 'CNV Voice Played', 1), ('FLAG', 'CNV Voice Finished', 0)],
               [('INCREMENT_COUNTER', 1, 'CNV_Voice_Frames')], once=False),
        Script('Test - finished', [('FLAG', 'CNV Voice Played', 1), ('HAS_FINISHED_AUDIO', line)],
               [('SET_FLAG', 'CNV Voice Finished', 1), ('SET_COUNTER', 'CNV_Voice_Done', 1)])]
    t.expect += [('播完', RUN - 3, '==', 1),
                 ('播放帧数', RUN - 3, '>=', frames * (1 - TOLERANCE)),
                 ('播放帧数', RUN - 3, '<=', frames * (1 + TOLERANCE))]
    t.bench = [('bench_watch', dict(seconds=at + 1, every=1, sheet=False, lines=len(t.counters))),
               ('bench_look', dict(note='the subtitle of CNV_TEST_001 at the bottom?')),
               ('bench_watch', dict(seconds=RUN - at - 1, every=1, sheet=False, lines=len(t.counters)))]
    return t
