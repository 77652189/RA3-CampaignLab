"""Standalone mission factories for the UI presentation benches."""
import sys

from parts import Mission
import labpaths


def _enable_media_imports():
    # The media packages import experimental.campaign even in isolated build.py.
    if labpaths.ROOT not in sys.path:
        sys.path.insert(0, labpaths.ROOT)


def movie():
    """Movie probe (experimental/video/pack.py): can a mission play a movie of ours? CNVTEST01 (288x288, 4 s, no audio) in the
    radar window with MOVIE_PLAY_RADAR at RADAR_AT s, CNVTEST02 (1280x720, 2 s) full screen with MOVIE_PLAY_FULLSCREEN at
    FULL_AT s; HAS_FINISHED_VIDEO is read for both. The clips are made by work/video_test/make_test.py and encoded with
    NihAV's nihav-encoder (see docs/story/handoff.md 1g); read back by movie in checks.py.
    """
    import os

    from maps import festival

    RADAR_AT = 4.0
    FULL_AT = 14.0
    CLIPS = {'CNVTEST01': os.path.join(labpaths.WORK, 'video_test', 'CNVTEST01.vp6'),
             'CNVTEST02': os.path.join(labpaths.WORK, 'video_test', 'CNVTEST02.vp6')}


    class LazyPack:
        """The clips read only when a build takes the pack's include, files or check."""

        def __init__(self, clips):
            self.clips, self.made, self.events, self.strings = clips, None, set(clips), {}

        def _make(self):
            if self.made is None:
                _enable_media_imports()
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


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'movie': lambda: mission(),
    }
    return dict(MISSION=MISSION)


def scene():
    """The plan words for what the player sees, on the bench (docs/design/teardowns/layout.md 3; plan.py scene /
    compile_shown): a tiny plan on the festival map, two phases.

      - 看: opens with a 过场 -- the camera to the harbour (the far east end) and back. The bench gets into the mission
        only some seconds after it began (bench 2026-10-27: the first frame was past this one), so the second phase's
        is the one the frames show.
      - 北营 (from AT): a 过场 -- the camera to the north base, the whole map for a look, back to the west field -- and
        two goals: one on the clock after the hand-back, a bonus shown only once the player's dog gets to the convoy
        start (亮出).

    Published (the cast): dog (the player's), camp (the enemy's); facts 过场 看, 过场 北营, 段 北营; goals
    'Objective01 - CNV SC' and 'Bonus01 - CNV SC' (their shown flags CNV_SC_Objective01_Shown, CNV_SC_Bonus01_Shown);
    the scenes' flags CNV_SC_Scene_1 / _2.
    """
    import plan

    AT = 30.0                                       # the second phase begins, seconds from the start
    PLAN = {
        '关卡': 'sc', '名字': '过场试验', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'},
        '开局': {'资金': 0, '部队': [{'单位': '警犬', '在': 'west field', '角色': 'dog'},
                                 {'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
        '段': [{'名字': '看', '过场': [{'镜头': 'harbour', '秒': 3}, {'镜头': 'west field', '秒': 2}],
               '结束': f'开局 + {AT:g}'},
              {'名字': '北营', '目标': ['看过了', '找到车队'],
               '过场': [{'镜头': 'camp', '秒': 3}, {'揭全图': '看一眼'}, {'停': 4}, {'镜头': 'west field', '秒': 2},
                       {'闪烁': 'dog'}]}],
        '目标': {'看过了': {'说明': '交还控制以后亮出', '标记': ['camp']},
               '找到车队': {'奖励': True, '说明': '警犬走到车队出发点才亮出', '标记': ['convoy start'],
                        '亮出': 'dog 进入 convoy start'}},
    }


    def mission(name='CampScene'):
        return plan.Compiler(PLAN, name).compile()


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'scene': lambda: mission(),
    }
    return dict(MISSION=MISSION)


def voice():
    """Voice probe (the voice line's pack, experimental/voice/pack.py, make(test=True)): one dubbed line, CNV_TEST_001
    (~4.8 s), played with PLAY_SOUND_EFFECT at PLAY_AT s as retail plays its mission dialogue -- read back by
    voice in checks.py: whether HAS_FINISHED_AUDIO waits for the line's length (a sound the game cannot find is finished at
    once), whether the subtitle DIALOGEVENT:CNV_TEST_001 comes up by itself (looked at), and, with `cdata` naming one of
    the pack's two candidate folders, which one the game reads a new AudioFile's audio from.
    """
    from maps import festival

    PLAY_AT = 4.0


    class LazyPack:
        """The test pack, compiled (pack.make: ~25 s under the SDK build lock) only when a build takes its include, files
        or check; its events and strings are known without: listing the builds and the contract check stay quick."""

        def __init__(self, cdata=None):
            _enable_media_imports()
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


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'voice_bench': lambda: mission(),
        'voice_bench_s': lambda: mission(name='CampVoiceS', cdata='data\\static\\cdata'),
        'voice_bench_12': lambda: mission(name='CampVoice12', cdata='data\\static.12\\cdata'),
    }
    return dict(MISSION=MISSION)


BENCHES = (movie, scene, voice)
