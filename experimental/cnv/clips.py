"""The talking-head clips of a plan's dubbed lines, an optional extra of a line (2026-11-02, the user: "说话头像效果好的话
也放进去"). Next to a recording `<folder>/CNV_A4_090.wav` the voice line may put `<folder>/video/CNV_A4_090.mp4` (288x288,
the speaker's portrait talking); when it is there the plan plays it in the radar window with the line (MOVIE_PLAY_RADAR,
handoff 1g), when it is not the line is the audio alone. The mp4 is converted to a .vp6 beside it (video/to_vp6.py)
when that is older. A clip that cannot be converted is left out and listed in `missing`, never a failed build.

Lazy as the voice pack is: the movie pack (experimental/video/pack.py) is made only when a build takes its include,
files or check. `bool(clips)` is whether any line has one (the mission then carries the movie pack).
"""
import os
import subprocess
import sys

TO_VP6 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'video', 'to_vp6.py')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Clips:
    def __init__(self, wavs, missing):
        """wavs: {event: path of the recording}; missing: the list the build prints."""
        self.wavs, self.missing, self.clips, self.made = wavs, missing, {}, None

    def __bool__(self):
        return bool(self.clips)

    def find(self, ev):
        """The movie id (= the line's event) of the line's clip, or None."""
        if ev in self.clips:
            return ev
        wav = self.wavs.get(ev)
        if not wav:
            return None
        mp4 = os.path.join(os.path.dirname(wav), 'video', os.path.splitext(os.path.basename(wav))[0] + '.mp4')
        if not os.path.exists(mp4):
            return None
        vp6 = mp4[:-4] + '.vp6'
        if not os.path.exists(vp6) or os.path.getmtime(vp6) < os.path.getmtime(mp4):
            r = subprocess.run([sys.executable, '-I', '-X', 'utf8', TO_VP6, mp4, vp6, '--size', 'radar'],
                               capture_output=True, text=True)
            if r.returncode or not os.path.exists(vp6):
                self.missing.append(f'video of {ev}: not converted ({(r.stderr or r.stdout).strip()[-120:]})')
                return None
        self.clips[ev] = vp6
        return ev

    def _make(self):
        if self.made is None:
            if ROOT not in sys.path:
                sys.path.insert(0, ROOT)
            from experimental.video import pack
            self.made = pack.make(self.clips)
        return self.made

    include = property(lambda self: self._make().include)
    files = property(lambda self: self._make().files)
    check = property(lambda self: self._make().check)
