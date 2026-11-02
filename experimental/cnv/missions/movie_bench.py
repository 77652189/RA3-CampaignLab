"""Movie probe (experimental/video/pack.py): can a mission play a movie of ours? CNVTEST01 (288x288, 4 s, no audio) in the
radar window with MOVIE_PLAY_RADAR at RADAR_AT s, CNVTEST02 (1280x720, 2 s) full screen with MOVIE_PLAY_FULLSCREEN at
FULL_AT s; HAS_FINISHED_VIDEO is read for both. The clips are made by work/video_test/make_test.py and encoded with
NihAV's nihav-encoder (see docs/story/handoff.md 1g); read back by checks/movie.py.
"""
import os

from maps import festival
from parts import Mission

RADAR_AT = 4.0
FULL_AT = 14.0
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CLIPS = {'CNVTEST01': os.path.join(ROOT, 'work', 'video_test', 'CNVTEST01.vp6'),
         'CNVTEST02': os.path.join(ROOT, 'work', 'video_test', 'CNVTEST02.vp6')}


class LazyPack:
    """The clips read only when a build takes the pack's include, files or check."""

    def __init__(self, clips):
        self.clips, self.made, self.events, self.strings = clips, None, set(clips), {}

    def _make(self):
        if self.made is None:
            import sys
            if ROOT not in sys.path:
                sys.path.insert(0, ROOT)
            from experimental.video import pack
            self.made = pack.make(self.clips)
        return self.made

    include = property(lambda self: self._make().include)
    files = property(lambda self: self._make().files)
    check = property(lambda self: self._make().check)


def mission(name='CampMovie', clips=None):
    m = Mission(name=name, map=festival, facts={'radar at': RADAR_AT, 'full at': FULL_AT})
    m.video = LazyPack(dict(clips or CLIPS))
    m.put('AlliedAntiVehicleVehicleTech1', 'west field', 250, 30, name='UNIT - CNV Movie Guardian', role='guardian')
    return m
