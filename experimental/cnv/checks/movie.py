"""Movie probe checks (missions/movie_bench.py), read off the counters:

play: CNVTEST01 starts in the radar window at `radar at` s, CNVTEST02 full screen at `full at` s. 雷达帧数 / 全屏帧数 count
  the frames from the start till HAS_FINISHED_VIDEO holds, 雷达播完 / 全屏播完 are 1 from then on (radar only: see below).
  A radar clip the game plays runs its own length (4 s); one it cannot find is finished at once. The frame a second into
  each clip is looked at (the picture: the colour bar, the square, CNV TEST nnn). The mission is still running at the
  end (the counters can be read): the game did not crash.
"""
from parts import Script, Test

RUN = 30.0


def play(m):
    t = Test()
    r, f = m.facts['radar at'], m.facts['full at']
    t.counters += [('CNV_Movie_RFrames', '雷达帧数'), ('CNV_Movie_RDone', '雷达播完'),
                   ('CNV_Movie_FFrames', '全屏帧数'), ('CNV_Movie_FDone', '全屏播完')]
    t.scripts += [
        Script('Test - radar timer', [], [('SET_MILLISECOND_TIMER', 'CNV Movie Radar', r)]),
        Script('Test - radar', [('TIMER_EXPIRED', 'CNV Movie Radar')],
               [('MOVIE_PLAY_RADAR', 'CNVTEST01'), ('SET_FLAG', 'CNV Movie RPlayed', 1)]),
        Script('Test - radar playing', [('FLAG', 'CNV Movie RPlayed', 1), ('FLAG', 'CNV Movie RFinished', 0)],
               [('INCREMENT_COUNTER', 1, 'CNV_Movie_RFrames')], once=False),
        Script('Test - radar finished', [('FLAG', 'CNV Movie RPlayed', 1), ('HAS_FINISHED_VIDEO', 'CNVTEST01')],
               [('SET_FLAG', 'CNV Movie RFinished', 1), ('SET_COUNTER', 'CNV_Movie_RDone', 1)]),
        Script('Test - full timer', [], [('SET_MILLISECOND_TIMER', 'CNV Movie Full', f)]),
        Script('Test - full', [('TIMER_EXPIRED', 'CNV Movie Full')],
               [('MOVIE_PLAY_FULLSCREEN', 'CNVTEST02', 0), ('SET_FLAG', 'CNV Movie FPlayed', 1)]),
        Script('Test - full playing', [('FLAG', 'CNV Movie FPlayed', 1), ('FLAG', 'CNV Movie FFinished', 0)],
               [('INCREMENT_COUNTER', 1, 'CNV_Movie_FFrames')], once=False),
        Script('Test - full finished', [('FLAG', 'CNV Movie FPlayed', 1), ('HAS_FINISHED_VIDEO', 'CNVTEST02')],
               [('SET_FLAG', 'CNV Movie FFinished', 1), ('SET_COUNTER', 'CNV_Movie_FDone', 1)])]
    # bench 2026-11-01: the radar clip counts 63 frames (4 s at 15 a second) and HAS_FINISHED_VIDEO holds; the full-screen
    # clip is on screen (the picture, counters hidden meanwhile) but HAS_FINISHED_VIDEO never holds for it -- retail
    # uses that condition for its radar clips only and waits for the full-screen ones with a timer -- so full screen is
    # judged by the picture and by the mission running on after it (the counter goes on counting)
    t.expect += [('雷达播完', RUN - 3, '==', 1), ('雷达帧数', RUN - 3, '>=', 50), ('雷达帧数', RUN - 3, '<=', 75),
                 ('全屏帧数', RUN - 3, '>=', 100)]
    t.bench = [('bench_watch', dict(seconds=r + 1.5, every=1, sheet=False, lines=len(t.counters))),
               ('bench_look', dict(note='the radar window: CNV TEST movie (colour bar, square, frame number)?')),
               ('bench_watch', dict(seconds=f - r - 2.8, every=1, sheet=False, lines=len(t.counters))),
               ('bench_look', dict(note='full screen: CNV TEST movie over the whole screen? (the mission runs ~2 s ahead)')),
               ('bench_watch', dict(seconds=RUN - f + 1.3, every=1, sheet=False, lines=len(t.counters)))]
    return t
