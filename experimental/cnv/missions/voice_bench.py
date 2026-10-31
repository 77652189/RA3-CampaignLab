"""Voice probe (the voice line's pack, experimental/voice/pack.py, make(test=True)): one dubbed line, CNV_TEST_001
(~4.8 s), played with PLAY_SOUND_EFFECT at PLAY_AT s as retail plays its mission dialogue -- read back by
checks/voice.py: whether HAS_FINISHED_AUDIO waits for the line's length (a sound the game cannot find is finished at
once), whether the subtitle DIALOGEVENT:CNV_TEST_001 comes up by itself (looked at), and, with `cdata` naming one of
the pack's two candidate folders, which one the game reads a new AudioFile's audio from.
"""
import os
import sys

from maps import festival
from parts import Mission

PLAY_AT = 4.0
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class LazyPack:
    """The test pack, compiled (pack.make: ~25 s under the SDK build lock) only when a build takes its include, files
    or check; its events and strings are known without: listing the builds and the contract check stay quick."""

    def __init__(self, cdata=None):
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from experimental.voice import pack
        self.pack, self.cdata, self.made = pack, cdata, None
        line, _, text, *_group = pack.TEST             # (event, wav, subtitle, group): the group is for unit voices
        self.events, self.strings = {line}, {f'DIALOGEVENT:{line}': text}

    def _make(self):
        if self.made is None:
            self.made = self.pack.make(test=True)
            if self.cdata:
                self.made.files = [(p, d) for p, d in self.made.files if p.lower().startswith(self.cdata.lower() + '\\')]
        return self.made

    include = property(lambda self: self._make().include)
    files = property(lambda self: self._make().files)
    check = property(lambda self: self._make().check)


def mission(name='CampVoice', cdata=None):
    """cdata: 'data\\static\\cdata' or 'data\\static.12\\cdata' -- the audio in that folder only (None: both)."""
    voice = LazyPack(cdata)
    m = Mission(name=name, map=festival, facts={'play at': PLAY_AT})
    m.voice = voice
    m.put('AlliedAntiVehicleVehicleTech1', 'west field', 250, 30, name='UNIT - CNV Voice Guardian', role='guardian')
    return m
