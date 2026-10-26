"""A4 冰雕里的兵 (docs/story/plans/a4.md): its music, written here as a score and played by our own synthesizer
(synth.py), and the Pathfinder map that plays it (ownmap.Builder).

D minor, 96 BPM, a bar is 2.5 s, a segment 2 bars (5 s: the longest a jump without PREP waits). The cold colour is
the celesta, the music box and the wind. The sides, as Red Alert 3 does it (rock and electronics over the orchestra):
the Empire hidden in the ice is the koto, the shamisen and the shakuhachi in the in-scale (D Eb G A Bb) over taiko;
the Allies are the horns' march theme, then, when they win, rock drums, distorted guitars and synth arpeggios.

  prep     布防          loop  pads, celesta, the koto heard only in passing, a muffled heartbeat of taiko
  escort   第一程        loop  the march: bass and strings ostinato, snare, the horns' theme, a synth pulse
  tense    交战·劣势      loop  the Empire on top: palm-muted chugs on a D pedal, shamisen riff, shakuhachi
                               wails, the Allied theme in fragments; half-time drums
  fierce   交战·激烈      loop  the Allies on top: double-time rock drums, guitar riff, the march theme on
                               trumpets, synth arpeggios, choir
  final    最后一程      loop  the march theme in full, trumpets, choir and the band
  ambush   冰雕碎了      cut   the ice cracks, taiko and a brass cluster, into tense
  harbour  港口生变      cut   a brass alarm call, into tense
  victory / defeat      cut   then the music stops
  prep>escort, tense>fierce, fierce>tense, battle>escort, battle>final: router transitions, one bar each

EVENTS: what the mission's scripts fire (retail names: the game looks events up by name). In combat the mission
turns on a dynamic system (PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM, sdk SageXML/PathMusic): the game then fires
SetAdvantageEnemy when the enemy kills twice what we kill over 20 s (-> tense), ResetAdvantage when it evens out and
SetAdvantagePlayer when we destroy 5 important buildings in 2 minutes (both -> fierce).

  python -I -X utf8 experimental/music/a4.py   -> work/music/a4/: each section (loops twice), a playthrough of the
                                                  mission (PLAYTHROUGH, by ownmap.timeline), index.html to listen
  python -I -X utf8 experimental/music/a4.py heard <recording.wav>    which section the game played when (after
                                                  a build has made STREAMS: pack())
"""
import html
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from experimental.music import ownmap, synth  # noqa: E402
from experimental.music.synth import Mix, hz  # noqa: E402

BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
SEG_BARS = 2

# name: (bars, loop, RMS dB)
SECTIONS = {
    'prep': (8, True, -23.0), 'escort': (8, True, -19.0), 'tense': (8, True, -18.0), 'fierce': (8, True, -16.0),
    'final': (8, True, -16.5),
    'ambush': (1, False, -16.0), 'harbour': (1, False, -16.5), 'victory': (3, False, -17.5), 'defeat': (3, False, -22.0),
    'prep>escort': (1, False, -20.0), 'tense>fierce': (1, False, -16.5), 'fierce>tense': (1, False, -17.0),
    'battle>escort': (1, False, -19.0), 'battle>final': (1, False, -17.0),
}
# what the mission fires: (retail event, section, PREP = cut at once)
EVENTS = {
    'start': ('S_A04GibraltarIntro', 'prep', True),
    'escort': ('S_A04GibraltarExplore', 'escort', False),
    'ambush': ('S_A04Threat1', 'ambush', True),
    'harbour': ('BigReveal', 'harbour', True),
    'final': ('S_A04Threat1_1', 'final', False),
    'win': ('S_EndMissionWin', 'victory', True),
    'lose': ('S_EndMissionLose', 'defeat', True),
    # fired by the game's dynamic system while it is on (Standard_NoLeadIn): fighting is fierce, losing is tense
    'combat': ('Combat', 'fierce', False),
    'losing': ('SetAdvantageEnemy', 'tense', False),
    'even': ('ResetAdvantage', 'fierce', False),
    'winning': ('SetAdvantagePlayer', 'fierce', False),
    # the fighting is over: back to the convoy's leg (PHASES). Our maps all carry the Heidelberg container's own
    # ThreatLevel1 / ThreatLevel1_1 states (their map streams), so the game fires Heidelberg's events, not
    # Threat1 / Threat1_1 (bench 2026-10-26, CampMusDynS); the plain one gets the same actions (CALM_TOO)
    'calm': ('S_A03HeidelbergThreat1_1', None, False),
}
CALM_TOO = ('Threat1_1',)
DYNAMIC_SYSTEM = 'Standard_NoLeadIn'
# the level plan's words (docs/story/plans: 音乐 <提示词>; 胜利 / 失败 are played by the plan's endings)
CUES = {'布防': 'start', '行进': 'escort', '伏击': 'ambush', '港口': 'harbour', '最后一程': 'final',
        '胜利': 'win', '失败': 'lose'}
# the convoy's legs: the map remembers which one it is on in a variable of its own (the retail map's
# 'a05incoming', only retail A05 sets it), so that calm knows where to go back to
PHASES = {'escort': 0, 'final': 1}
PHASE_VAR = 3
SHELL = {'MenuTrack': True, 'BriefingTrack': False}     # the shell's own events, both to prep (PREP or not)
LINKS = {'prep>escort': 'escort', 'tense>fierce': 'fierce', 'fierce>tense': 'tense', 'battle>escort': 'escort',
         'battle>final': 'final', 'ambush': 'fierce', 'harbour': 'fierce'}
ROUTES = {'prep': ['prep>escort'], 'tense': ['battle>escort', 'battle>final', 'tense>fierce'],
          'fierce': ['battle>escort', 'battle>final', 'fierce>tense']}

# a mission compressed to 4 minutes: (seconds, event key, what happened)
PLAYTHROUGH = [
    (0.0, 'start', '任务开始：布防，冰雕里藏着兵'),
    (45.0, 'escort', '车队出发'),
    (70.0, 'ambush', '1 号广场的冰雕碎了，伏兵冲出来'),
    (88.0, 'losing', '伏兵人多，我方吃亏（游戏判定：劣势）'),
    (106.0, 'even', '稳住阵脚，扳回来了（均势）'),
    (122.0, 'calm', '伏兵清光，战斗平息，车队接着走（游戏判定）'),
    (140.0, 'harbour', '港口桥头有埋伏，车队停下'),
    (162.0, 'losing', '北营小队从背后打停着的车队（劣势）'),
    (180.0, 'even', '分兵回防，又稳住了（均势）'),
    (197.0, 'final', '港口清空，最后一程'),
    (232.0, 'win', '车队到达港口，胜利'),
]
PLAYTHROUGH_SECONDS = 245.0


# --- notation ----------------------------------------------------------------------------------------------------

_STEP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def p(name):
    """'C#4' -> 61."""
    return 12 * (int(name[-1]) + 1) + _STEP[name[0]] + name[1:-1].count('#') - name[1:-1].count('b')


def seq(text):
    """'D4:0:.75 A4:1:2' -> [(beat in bar, beats, midi)]; one bar."""
    out = []
    for item in text.split():
        name, at, dur = item.split(':')
        out.append((float(at), float(dur), p(name)))
    return out


def chord(names):
    return [p(n) for n in names.split()]


class Writer:
    """Places notes on a section's Mix by bar and beat, a little loose (as players are)."""

    def __init__(self, mix, name):
        self.mix = mix
        self.rng = np.random.default_rng(sum(map(ord, name)))

    def at(self, bar, beat, loose=0.006):
        return max(0.0, bar * BAR + beat * BEAT + self.rng.uniform(-loose, loose))

    def note(self, inst, bar, beat, pitch, beats, vel=0.7, gain=0.0, pan=0.0, verb=0.3, **kw):
        vel = float(np.clip(vel * self.rng.uniform(0.94, 1.06), 0.05, 1.0))
        self.mix.add(self.at(bar, beat), inst(float(hz(pitch)), beats * BEAT, vel, **kw), gain, pan, verb)

    def chord(self, inst, bar, beat, pitches, beats, **kw):
        for k, q in enumerate(pitches):
            self.note(inst, bar, beat, q, beats, seed=k, **kw)

    def line(self, inst, bar, notes, **kw):
        for beat, beats, q in notes:
            self.note(inst, bar, beat, q, beats, **kw)

    def hit(self, inst, bar, beat, vel=0.8, gain=0.0, pan=0.0, verb=0.3, **kw):
        vel = float(np.clip(vel * self.rng.uniform(0.92, 1.08), 0.05, 1.0))
        self.mix.add(self.at(bar, beat, 0.003), inst(vel, seed=int(self.rng.integers(1 << 16)), **kw), gain, pan, verb)

    def drums(self, inst, bar, pattern, gain=0.0, pan=0.0, verb=0.3, scale=1.0, **kw):
        """16 steps a bar: X loud, x medium, o soft, . rest."""
        for k, c in enumerate(pattern.replace(' ', '')):
            if c != '.':
                self.hit(inst, bar, k / 4, {'X': 1.0, 'x': 0.62, 'o': 0.35}[c] * scale, gain, pan, verb, **kw)


# --- the sections --------------------------------------------------------------------------------------------------

PREP_CHORDS = [('D2', 'D3 A3 C4 E4 F4'), ('Bb1', 'F3 A3 D4 E4'), ('G1', 'F3 Bb3 D4 A4'), ('A1', 'G3 D4 E4 A4'),
               ('D2', 'D3 A3 C4 E4 F4'), ('Bb1', 'F3 A3 D4 E4'), ('Eb2', 'G3 Bb3 D4 F4'), ('A1', 'E3 A3 C#4 E4')]
PREP_CELESTA = ['A5:0:1.5 F5:1.5:.5 E5:2:2', 'D5:0:1 E5:1:.5 F5:1.5:.5 A5:2:2', 'Bb5:0:1.5 A5:1.5:.5 G5:2:1 D5:3:1',
                'E5:0:3', 'A5:0:1.5 F5:1.5:.5 E5:2:2', 'D5:0:1 E5:1:.5 F5:1.5:.5 C6:2:2',
                'Bb5:0:1 G5:1:1 Eb5:2:2', 'D5:0:1 C#5:1:1 E5:2:2']


def prep(w):
    for bar, (root, voicing) in enumerate(PREP_CHORDS):
        w.chord(synth.pad, bar, 0, chord(voicing), 4.4, vel=0.32, gain=-5, verb=0.55)
        w.note(synth.strings, bar, 0, p(root) + 12, 4.2, vel=0.45, gain=-9, verb=0.45, bright=0.2, attack=0.9)
        w.note(synth.strings, bar, 0, p(root), 4.2, vel=0.4, gain=-11, verb=0.4, bright=0.12, attack=1.0)
        w.line(synth.celesta, bar, seq(PREP_CELESTA[bar]), vel=0.55, gain=-3, pan=0.2, verb=0.5)
        if bar >= 4:
            w.line(synth.musicbox, bar, [(b, d, q + 12) for b, d, q in seq(PREP_CELESTA[bar])], vel=0.4, gain=-15,
                   pan=-0.35, verb=0.6)
        w.hit(synth.taiko, bar, 0, vel=0.32, gain=-13, verb=0.6)
        w.hit(synth.taiko, bar, 0.45, vel=0.2, gain=-15, verb=0.6)
    # the hidden enemy, heard in passing
    w.line(synth.koto, 3, seq('D4:3:.25 Eb4:3.25:.25 G4:3.5:.25 A4:3.75:1'), vel=0.45, gain=-9, pan=-0.5, verb=0.6)
    w.note(synth.koto, 6, 2, p('D4'), 1.5, vel=0.5, gain=-8, pan=-0.5, verb=0.6, bend=1.0)
    w.line(synth.koto, 6, seq('G3:3.5:.25 A3:3.75:.25'), vel=0.4, gain=-10, pan=-0.5, verb=0.6)
    w.hit(synth.timpani, 0, 0, vel=0.5, gain=-11, verb=0.5, f=hz(p('D2')))
    w.hit(synth.timpani, 4, 0, vel=0.45, gain=-12, verb=0.5, f=hz(p('D2')))
    seconds = w.mix.n / synth.RATE
    w.mix.add(0, synth.wind(seconds, 0.3), -16, verb=0.1)
    w.mix.add(0, synth.sparkle(seconds, 2.0, 0.25), -15, verb=0.6)


MARCH_CHORDS = [('D2', 'D4 F4 A4'), ('Bb1', 'D4 F4 Bb4'), ('F2', 'C4 F4 A4'), ('C2', 'C4 E4 G4'),
                ('D2', 'D4 F4 A4'), ('Bb1', 'D4 F4 Bb4'), ('G1', 'D4 G4 Bb4'), ('A1', 'C#4 E4 A4')]
MARCH_THEME = ['D4:0:.75 D4:.75:.25 A4:1:2 G4:3:.5 F4:3.5:.5', 'F4:0:2 G4:2:1 A4:3:1', 'C5:0:2 A4:2:1 F4:3:1',
               'G4:0:3', 'D4:0:.75 D4:.75:.25 A4:1:2 G4:3:.5 A4:3.5:.5', 'Bb4:0:2 A4:2:1 G4:3:1',
               'G4:0:1 A4:1:1 Bb4:2:1 D5:3:1', 'C#5:0:2 A4:2:2']
SNARE_MARCH = 'X..x .xx. X..x .x.x'
SNARE_FILL = 'X.x. X.x. xxxx XXXX'


def _ostinato(w, bar, root, gain_bass=-6, gain_low=-11):
    for k, step in enumerate([0, 0, 12, 0, 0, 0, 12, 7]):
        q = p(root) + 12 + step
        accent = 0.9 if k in (0, 4) else 0.65
        w.note(synth.bass, bar, k / 2, q - 12, 0.4, vel=accent, gain=gain_bass, verb=0.15)
        w.note(synth.strings, bar, k / 2, q, 0.3, vel=accent, gain=gain_low, verb=0.25, bright=0.45, attack=0.01,
               release=0.12, voices=4)


def _arpeggio(w, bar, voicing, gain=-13, octave=12):
    tones = chord(voicing)
    for k in range(16):
        q = tones[[0, 1, 2, 1][k % 4]] + (octave if k >= 8 else 0)
        w.note(synth.strings, bar, k / 4, q, 0.2, vel=0.55 if k % 4 else 0.75, gain=gain, pan=0.35 if k % 2 else
               -0.35, verb=0.3, bright=0.55, attack=0.008, release=0.1, voices=3)


def escort(w):
    for bar, (root, voicing) in enumerate(MARCH_CHORDS):
        _ostinato(w, bar, root)
        _arpeggio(w, bar, voicing)
        w.chord(synth.strings, bar, 0, chord(voicing), 4.1, vel=0.4, gain=-15, verb=0.45, bright=0.3, attack=0.3)
        w.drums(synth.snare, bar, SNARE_FILL if bar in (3, 7) else SNARE_MARCH, gain=-11, pan=0.1, verb=0.25,
                scale=0.8)
        w.drums(synth.taiko, bar, 'X... .... x... ....', gain=-9, verb=0.35, scale=0.75)
        w.drums(synth.kick, bar, 'X... .... X... ....', gain=-9, verb=0.05, scale=0.8)
        w.drums(synth.hat, bar, 'x.o. x.o. x.o. x.o.', gain=-19, pan=0.3, verb=0.05)
        _pulse(w, bar, [p(root) + 24, p(root) + 31], every=0.5, gain=-19, decay=0.1)
        w.line(synth.brass, bar, seq(MARCH_THEME[bar]), vel=0.72, gain=-5, pan=-0.15, verb=0.35, bright=0.45)
        if bar >= 4:
            w.line(synth.brass, bar, [(b, d, q - 12) for b, d, q in seq(MARCH_THEME[bar])], vel=0.6, gain=-13,
                   pan=0.2, verb=0.35, bright=0.3)
            tones = chord(voicing)
            for k in range(8):
                w.note(synth.celesta, bar, k / 2, tones[k % 3] + 12 + 12 * (k // 3 % 2), 0.5, vel=0.45, gain=-13,
                       pan=0.45, verb=0.45)
    w.hit(synth.cymbal, 0, 0, vel=0.5, gain=-16, verb=0.4)


def _riff(w, bar, root, pattern, gain=-9.0, shape=(0, 7, 12)):
    """Distorted guitars, 16 steps a bar: O an open chord ringing to the next hit, m palm-muted, . rest;
    double-tracked (two takes, hard left and right)."""
    steps = pattern.replace(' ', '')
    hits = [k for k, c in enumerate(steps) if c != '.']
    for take, pan in ((0, -0.7), (1, 0.7)):
        for i, k in enumerate(hits):
            beats = ((hits[i + 1] if i + 1 < len(hits) else 16) - k) / 4 * 0.95
            w.note(synth.guitar, bar, k / 4, p(root), beats, vel=0.85 if k % 4 == 0 else 0.72, gain=gain, pan=pan,
                   verb=0.06, mute=steps[k] == 'm', shape=shape, seed=take)


def _kit(w, bar, kick, snare, hats, gain=0.0, open_hats=''):
    w.drums(synth.kick, bar, kick, gain=gain - 5, verb=0.05)
    w.drums(synth.rock_snare, bar, snare, gain=gain - 7, verb=0.18)
    w.drums(synth.hat, bar, hats, gain=gain - 18, pan=0.3, verb=0.05)
    if open_hats:
        w.drums(synth.hat, bar, open_hats, gain=gain - 16, pan=0.3, verb=0.1, open_=True)


def _pulse(w, bar, pitches, every=0.25, gain=-18.0, decay=0.08):
    """The synth pulse ticking under it all, cycling through `pitches`."""
    for k in range(int(4 / every)):
        w.note(synth.synth_pluck, bar, k * every, pitches[k % len(pitches)], every * 0.8,
               vel=0.75 if k % 4 == 0 else 0.55, gain=gain, pan=0.4 if k % 2 else -0.4, verb=0.2, decay=decay)


TENSE_CHORDS = ['D2', 'Eb2', 'D2', 'C2', 'D2', 'Eb2', 'Bb1', 'A1']
TENSE_RIFF = {'D2': 'm.mm m.mm m.m. mmmm', 'Eb2': 'O... ...m m.mm m.mm', 'C2': 'O... ...m m.mm mmmm',
              'Bb1': 'O... .... O... ..mm', 'A1': 'O... .... m.mm mmmm'}
SHAMISEN = ['D5:0:.25 Eb5:.5:.25 D5:.75:.25 A4:1.25:.25 G4:1.75:.25 A4:2:.5 Bb4:2.75:.25 A4:3:.5 G4:3.5:.5',
            'Eb5:0:.25 D5:.5:.25 Bb4:.75:.25 G4:1.25:.25 Eb4:1.75:.25 G4:2:.5 A4:2.75:.25 Bb4:3:.5 A4:3.5:.5',
            'D5:0:.25 Eb5:.5:.25 D5:.75:.25 A4:1.25:.25 G4:1.75:.25 A4:2:.5 Bb4:2.75:.25 D5:3:.5 Eb5:3.5:.5',
            'C5:0:.5 Bb4:.5:.25 A4:.75:.25 G4:1:.5 A4:1.75:.25 D4:2:1 Eb4:3:.5 D4:3.5:.5']
SHAKUHACHI = [('A4:0:3', 1.0, 0.0), ('Bb4:0:2 A4:2:1.8', 0.5, 0.0), ('D5:0:1.5 C5:1.5:.5 Bb4:2:1.8', 1.0, 0.0),
              ('A4:0:3.5', 0.5, 2.0)]
ALLIED_FRAGMENT = {4: 'D4:0:.75 D4:.75:.25 A4:1:1', 6: 'D4:0:.75 D4:.75:.25 Bb4:1:1.5'}


def tense(w):
    """Losing: the Empire's music has the upper hand; the Allied theme only gets out its first notes."""
    for bar, root in enumerate(TENSE_CHORDS):
        _riff(w, bar, root, TENSE_RIFF[root], gain=-10)
        _kit(w, bar, 'X..x ..x. .... ..x.', '.... .... X... ....', 'x.x. x.x. x.x. x.x.', gain=-2)
        w.drums(synth.taiko, bar, 'X... .... .... x..x', gain=-6, verb=0.35, scale=0.9)
        _pulse(w, bar, [p('D5')], gain=-21, decay=0.05)
        for k in range(8):
            w.note(synth.bass, bar, k / 2, p(root), 0.42, vel=0.9 if k % 4 == 0 else 0.7, gain=-7, verb=0.1)
        w.note(synth.strings, bar, 0, p(root) + 12, 4.0, vel=0.55, gain=-13, verb=0.3, bright=0.45, attack=0.3,
               tremolo=12.8)
        w.note(synth.strings, bar, 0, p(root) + 13, 4.0, vel=0.45, gain=-16, verb=0.3, bright=0.45, attack=1.2,
               tremolo=12.8)
        if bar < 4:
            w.line(synth.shamisen, bar, seq(SHAMISEN[bar]), vel=0.8, gain=-7, pan=-0.3, verb=0.25)
        else:
            notes, scoop, fall = SHAKUHACHI[bar - 4]
            seq_ = seq(notes)
            for i, (b, d, q) in enumerate(seq_):
                w.note(synth.shakuhachi, bar, b, q, d, vel=0.75, gain=-6, pan=-0.2, verb=0.5, scoop=scoop,
                       fall=fall if i == len(seq_) - 1 else 0.0)
            if bar in ALLIED_FRAGMENT:
                w.line(synth.brass, bar, seq(ALLIED_FRAGMENT[bar]), vel=0.55, gain=-12, pan=0.35, verb=0.4,
                       bright=0.3)
    w.hit(synth.cymbal, 0, 0, vel=0.6, gain=-15, verb=0.35)


FIERCE_CHORDS = [('D2', 'D4 F4 A4'), ('Bb1', 'D4 F4 Bb4'), ('C2', 'C4 E4 G4'), ('D2', 'D4 F4 A4'),
                 ('F2', 'C4 F4 A4'), ('C2', 'C4 E4 G4'), ('Bb1', 'D4 F4 Bb4'), ('A1', 'C#4 E4 A4')]
FIERCE_THEME = ['D4:0:.75 D4:.75:.25 A4:1:2 G4:3:.5 F4:3.5:.5', 'F4:0:2 G4:2:1 A4:3:1', 'E4:0:1 G4:1:1 C5:2:2',
                'D5:0:2 A4:2:2', 'C5:0:2 A4:2:1 F4:3:1', 'G4:0:2 E4:2:1 G4:3:1', 'Bb4:0:2 D5:2:2', 'C#5:0:2 E5:2:2']


def fierce(w):
    """Winning: the Allies' march theme on trumpets over the band at full tilt."""
    for bar, (root, voicing) in enumerate(FIERCE_CHORDS):
        fill = bar in (3, 7)
        _riff(w, bar, root, 'Om.m Om.m O.mm O.O.' if not fill else 'Om.m Om.m OOOO OOOO', gain=-9)
        _kit(w, bar, 'X..x X.x. X..x X.x.', '.... X... .... X..x' if not fill else '.... X... XxXx XXXX',
             'xoxo xoxo xoxo xoxo', gain=0)
        if fill:
            for k, f in enumerate((180, 150, 120, 95)):
                w.hit(synth.tom, bar, 2 + k * 0.5, vel=0.85, gain=-7, verb=0.2, f=f)
        for k in range(8):
            w.note(synth.bass, bar, k / 2, p(root) + (12 if k % 2 else 0), 0.42, vel=0.85, gain=-6, verb=0.1)
        tones = chord(voicing)
        _pulse(w, bar, [q + 12 for q in tones + tones[1:2]], gain=-15, decay=0.12)
        theme = seq(FIERCE_THEME[bar])
        w.line(synth.brass, bar, [(b, d, q + 12) for b, d, q in theme], vel=0.85, gain=-5, pan=0.1, verb=0.3,
               bright=0.75)
        w.line(synth.brass, bar, theme, vel=0.8, gain=-8, pan=-0.15, verb=0.3, bright=0.5)
        w.chord(synth.choir, bar, 0, [q - 12 for q in tones], 4.0, vel=0.5, gain=-16, verb=0.45, vowel='ah')
        w.chord(synth.strings, bar, 0, tones, 4.1, vel=0.5, gain=-16, verb=0.4, bright=0.45, attack=0.2)
        w.hit(synth.taiko, bar, 0, vel=0.8, gain=-9, verb=0.35)
    w.hit(synth.cymbal, 0, 0, vel=0.8, gain=-11, verb=0.3)
    w.hit(synth.cymbal, 4, 0, vel=0.7, gain=-12, verb=0.3)


FINAL_CHORDS = [('D2', 'D4 F4 A4'), ('Bb1', 'D4 F4 Bb4'), ('F2', 'C4 F4 A4'), ('C2', 'C4 E4 G4'),
                ('G1', 'D4 G4 Bb4'), ('Bb1', 'D4 F4 Bb4'), ('A1', 'C#4 E4 A4'), ('A1', 'C#4 E4 A4')]
FINAL_THEME = ['D4:0:.75 D4:.75:.25 A4:1:2 G4:3:.5 F4:3.5:.5', 'F4:0:2 G4:2:1 A4:3:1', 'C5:0:2 A4:2:1 F4:3:1',
               'G4:0:2 E4:2:1 G4:3:1', 'Bb4:0:2 A4:2:1 G4:3:1', 'D5:0:2 C5:2:1 Bb4:3:1', 'C#5:0:2 D5:2:1 E5:3:1',
               'A4:0:4']


def final(w):
    for bar, (root, voicing) in enumerate(FINAL_CHORDS):
        _ostinato(w, bar, root, -6, -12)
        _arpeggio(w, bar, voicing, gain=-15)
        theme = seq(FINAL_THEME[bar])
        w.line(synth.brass, bar, [(b, d, q + 12) for b, d, q in theme], vel=0.8, gain=-6, pan=0.1, verb=0.35,
               bright=0.7)
        w.line(synth.brass, bar, theme, vel=0.75, gain=-8, pan=-0.2, verb=0.35, bright=0.45)
        w.line(synth.glock, bar, [(b, d, q + 24) for b, d, q in theme], vel=0.35, gain=-17, pan=0.4, verb=0.5)
        w.chord(synth.choir, bar, 0, [q - 12 for q in chord(voicing)], 4.0, vel=0.5, gain=-14, verb=0.5, vowel='ah')
        w.chord(synth.strings, bar, 0, chord(voicing), 4.1, vel=0.5, gain=-14, verb=0.45, bright=0.4, attack=0.25)
        _riff(w, bar, root, 'O.mm O.mm O.mm O.O.', gain=-12)
        _kit(w, bar, 'X... X..x X... X.x.', '.... X... .... X...', 'x.x. x.x. x.x. x.x.', gain=-2)
        w.drums(synth.taiko, bar, 'X... .... X... ....', gain=-9, verb=0.35, scale=0.85)
        w.drums(synth.snare, bar, SNARE_FILL if bar in (3, 7) else SNARE_MARCH, gain=-14, pan=0.1, verb=0.25,
                scale=0.85)
        w.hit(synth.timpani, bar, 0, vel=0.6, gain=-11, verb=0.4, f=hz(p(root) + 12))
    w.hit(synth.cymbal, 0, 0, vel=0.7, gain=-13, verb=0.35)
    w.hit(synth.cymbal, 4, 0, vel=0.6, gain=-14, verb=0.35)


def ambush(w):
    w.mix.add(0, synth.ice_crack(1.0), -2, verb=0.4)
    w.hit(synth.taiko, 0, 0, vel=1.0, gain=-2, verb=0.45)
    w.hit(synth.taiko, 0, 0.5, vel=0.7, gain=-6, verb=0.45)
    w.chord(synth.brass, 0, 0, chord('D3 Eb3 A3 D4 Eb4'), 1.0, vel=1.0, gain=-9, verb=0.4, bright=0.9)
    # then it gathers into combat's downbeat: a tremolo cluster and low brass swelling, the small drums rolling
    for q in chord('D3 Eb3 A3 D4'):
        w.note(synth.strings, 0, 0.75, q, 3.25, vel=0.75, gain=-8, verb=0.35, bright=0.55, attack=0.8, tremolo=12.8)
    w.chord(synth.brass, 0, 1, chord('D2 A2 Eb3'), 3.0, vel=0.6, gain=-10, verb=0.35, bright=0.4)
    w.drums(synth.taiko, 0, '.... oooo xxxx xxXX', gain=-9, pan=0.35, verb=0.3, size=0.45)
    w.mix.add(BEAT, synth.cymbal(0.6, 3 * BEAT, swell=True), -13, verb=0.3)
    w.hit(synth.taiko, 0, 3.5, vel=0.85, gain=-5, verb=0.4)


def harbour(w):
    w.hit(synth.cymbal, 0, 0, vel=0.8, gain=-11, verb=0.4)
    w.hit(synth.timpani, 0, 0, vel=0.9, gain=-6, verb=0.4, f=hz(p('D2')))
    for beat, voicing in ((0, 'A3 D4'), (1, 'A4 D5'), (2, 'A3 D4'), (3, 'Bb4 Eb5')):
        w.chord(synth.brass, 0, beat, chord(voicing), 0.8, vel=0.95, gain=-7, verb=0.35, bright=0.85)
    w.drums(synth.taiko, 0, 'X... X... X... XxXx', gain=-4, verb=0.35)
    w.note(synth.strings, 0, 0, p('D3'), 4.0, vel=0.7, gain=-10, verb=0.3, bright=0.5, tremolo=12.8)


def victory(w):
    w.hit(synth.cymbal, 0, 0, vel=0.8, gain=-10, verb=0.5)
    w.hit(synth.taiko, 0, 0, vel=0.95, gain=-4, verb=0.5)
    w.hit(synth.timpani, 0, 0, vel=0.9, gain=-6, verb=0.5, f=hz(p('D2')))
    w.chord(synth.brass, 0, 0, chord('D4 F#4 A4 D5'), 7.0, vel=0.85, gain=-9, verb=0.5, bright=0.65, release=1.2)
    w.note(synth.brass, 0, 0, p('A5'), 7.0, vel=0.7, gain=-12, verb=0.5, bright=0.7, release=1.2)
    w.chord(synth.strings, 0, 0, chord('D3 A3 D4 F#4 A4'), 7.5, vel=0.6, gain=-12, verb=0.5, bright=0.45, attack=0.1,
            release=1.5)
    w.chord(synth.choir, 0, 0, chord('D4 F#4 A4'), 7.0, vel=0.55, gain=-13, verb=0.55, attack=0.3)
    w.line(synth.glock, 0, seq('D6:0:1 F#6:.5:1 A6:1:1 D7:1.5:2'), vel=0.5, gain=-12, pan=0.3, verb=0.6)
    w.note(synth.bass, 0, 0, p('D2'), 7.0, vel=0.7, gain=-10, verb=0.3, release=1.0)


def defeat(w):
    w.hit(synth.taiko, 0, 0, vel=0.8, gain=-6, verb=0.6)
    w.note(synth.strings, 0, 0, p('D2'), 9.0, vel=0.6, gain=-9, verb=0.5, bright=0.2, attack=0.6, release=2.0)
    w.note(synth.strings, 0, 0, p('A2'), 9.0, vel=0.5, gain=-11, verb=0.5, bright=0.2, attack=0.6, release=2.0)
    w.note(synth.strings, 0, 1, p('Eb3'), 8.0, vel=0.5, gain=-12, verb=0.5, bright=0.25, attack=2.0, release=2.0)
    w.line(synth.celesta, 0, seq('D5:1:1 C5:2:1 Bb4:3:1'), vel=0.5, gain=-6, pan=0.2, verb=0.6)
    w.line(synth.celesta, 1, seq('A4:0:2 Eb4:2:2'), vel=0.45, gain=-7, pan=0.2, verb=0.6)
    w.mix.add(0, synth.wind(3 * BAR, 0.3), -14, verb=0.1)


def prep_escort(w):
    # starts as loud as prep ends (its pad goes on), then the snare and the timpani roll the march in
    w.chord(synth.pad, 0, 0, chord('E3 A3 C#4 E4'), 3.9, vel=0.32, gain=-5, verb=0.55, attack=0.05, release=0.3)
    for k in range(32):
        w.hit(synth.snare, 0, k / 8, vel=0.2 + 0.65 * (k / 31) ** 1.5, gain=-11, pan=0.1, verb=0.25)
    for k in range(16):
        w.hit(synth.timpani, 0, k / 4, vel=0.25 + 0.55 * k / 15, gain=-13, verb=0.4, f=hz(p('A1')))
    w.chord(synth.strings, 0, 0, chord('A2 E3 A3 C#4 E4'), 3.9, vel=0.55, gain=-12, verb=0.4, bright=0.35,
            attack=0.4, release=0.1)
    w.mix.add(0, synth.cymbal(0.6, BAR, swell=True), -14, verb=0.3)
    w.hit(synth.taiko, 0, 3.5, vel=0.6, gain=-8, verb=0.35)


def tense_fierce(w):
    """The tide turns: a tom fill and the guitars and brass climbing into the Allies' theme."""
    w.hit(synth.kick, 0, 0, vel=0.9, gain=-3, verb=0.05)
    _riff(w, 0, 'A1', 'O... .... .... mmmm', gain=-9)
    for k in range(12):
        w.hit(synth.tom, 0, k / 4, vel=0.45 + 0.5 * k / 11, gain=-8, verb=0.2, f=200 - 9 * k)
    _kit(w, 0, '.... .... .... X.X.', '.... .... .... XXXX', 'x.x. x.x. x.x. ....', gain=-1)
    w.line(synth.brass, 0, seq('A3:0:1 C#4:1:1 E4:2:1 A4:3:1'), vel=0.9, gain=-6, verb=0.3, bright=0.75)
    w.line(synth.brass, 0, seq('A4:0:1 C#5:1:1 E5:2:1 A5:3:1'), vel=0.8, gain=-11, verb=0.3, bright=0.8)
    w.mix.add(0, synth.cymbal(0.7, BAR, swell=True), -12, verb=0.3)
    w.note(synth.bass, 0, 0, p('A1'), 4.0, vel=0.8, gain=-7, verb=0.1)


def fierce_tense(w):
    """The enemy strikes back: a crash, the guitars left ringing, the shakuhachi rising over them."""
    w.hit(synth.cymbal, 0, 0, vel=0.8, gain=-11, verb=0.35)
    w.hit(synth.taiko, 0, 0, vel=1.0, gain=-3, verb=0.45)
    w.hit(synth.kick, 0, 0, vel=0.9, gain=-4, verb=0.05)
    _riff(w, 0, 'D2', 'O... .... .... ..mm', gain=-9)
    w.hit(synth.timpani, 0, 0, vel=0.8, gain=-8, verb=0.4, f=hz(p('D2')))
    w.note(synth.shakuhachi, 0, 1, p('Bb4'), 2.5, vel=0.8, gain=-5, pan=-0.2, verb=0.5, scoop=2.0, fall=1.0)
    for q in chord('D3 Eb3'):
        w.note(synth.strings, 0, 1, q, 3.0, vel=0.6, gain=-12, verb=0.35, bright=0.5, attack=1.5, tremolo=12.8)
    w.drums(synth.taiko, 0, '.... .... x..x X.XX', gain=-8, verb=0.3, scale=0.8)


def combat_escort(w):
    w.drums(synth.taiko, 0, 'X... x... o... ....', gain=-5, verb=0.4)
    w.chord(synth.strings, 0, 0, chord('A2 E3 G3 C#4 A4'), 3.6, vel=0.55, gain=-11, verb=0.45, bright=0.35,
            release=0.3)
    w.line(synth.celesta, 0, seq('A5:2:.5 G5:2.5:.5 E5:3:.5 C#5:3.5:.5'), vel=0.55, gain=-6, pan=0.25, verb=0.5)
    w.note(synth.bass, 0, 0, p('A1'), 2.0, vel=0.7, gain=-8, verb=0.2)


def combat_final(w):
    for k in range(16):
        w.hit(synth.taiko, 0, k / 4, vel=0.35 + 0.65 * k / 15, gain=-6, verb=0.35, size=0.8 if k % 4 else 1.0)
    for k in range(32):
        w.hit(synth.snare, 0, k / 8, vel=0.2 + 0.6 * k / 31, gain=-13, pan=0.1, verb=0.25)
    w.line(synth.brass, 0, seq('A3:0:1 C#4:1:1 E4:2:1 A4:3:1'), vel=0.85, gain=-6, verb=0.35, bright=0.7)
    w.mix.add(0, synth.cymbal(0.7, BAR, swell=True), -12, verb=0.3)
    w.note(synth.bass, 0, 0, p('A1'), 4.0, vel=0.8, gain=-7, verb=0.2)
    _riff(w, 0, 'A1', 'O... O... O... OOOO', gain=-12)


WRITERS = {'prep': prep, 'escort': escort, 'tense': tense, 'fierce': fierce, 'final': final, 'ambush': ambush,
           'harbour': harbour, 'victory': victory, 'defeat': defeat, 'prep>escort': prep_escort,
           'tense>fierce': tense_fierce, 'fierce>tense': fierce_tense, 'battle>escort': combat_escort,
           'battle>final': combat_final}


def render(name):
    """-> (n, 2) float, the whole section."""
    bars, loop, rms = SECTIONS[name]
    mix = Mix(bars * BAR, loop=loop)
    WRITERS[name](Writer(mix, name))
    x = mix.render(rms)
    if not loop and name not in LINKS:          # the music stops after it: ring out, not cut off
        fade = int(1.5 * synth.RATE)
        x[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
    return x


def segments(name):
    """The section's streams: a loop is cut into segments of SEG_BARS, a one-shot is one stream."""
    bars, loop, _ = SECTIONS[name]
    return [SEG_BARS] * (bars // SEG_BARS) if loop else [bars]


def stream_ms():
    """[(section, ms)] for every stream, in stream order."""
    return [(name, int(round(b * BAR * 1000))) for name in SECTIONS for b in segments(name)]


# --- the map -------------------------------------------------------------------------------------------------------

def music_map(base):
    """-> (Builder, {section: ownmap.Section}, [ms] per stream)."""
    b = ownmap.Builder(base)
    streams = stream_ms()
    secs, k = {}, 0
    route_of = {name: i + 1 for i, name in enumerate(ROUTES)}
    for name in SECTIONS:
        n = len(segments(name))
        secs[name] = b.section(list(range(k, k + n)), router=route_of.get(name, 0))
        k += n
    for name, (bars, loop, _) in SECTIONS.items():
        if loop:
            b.loop(secs[name])
        elif name in LINKS:
            b.link(secs[name], secs[LINKS[name]])
        else:
            b.stop(secs[name])
    b.m.routers = [[(secs[t].entry, secs[LINKS[t]].entry) for t in ts] for ts in ROUTES.values()]
    for event, section, prep_ in EVENTS.values():
        if section is None:                     # calm: back to the leg the convoy is on
            for name in (event,) + CALM_TOO:
                b.act(name, ownmap.switch(PHASE_VAR, {v: ownmap.goto(secs[s]) for s, v in PHASES.items() if v},
                                          ownmap.goto(secs[next(s for s, v in PHASES.items() if not v)])))
        elif section in PHASES:
            b.act(event, ownmap.set_var(PHASE_VAR, PHASES[section]) + ownmap.goto(secs[section], prep_))
        else:
            b.on(event, secs[section], prep=prep_)
    for event, prep_ in SHELL.items():
        b.on(event, secs['prep'], prep=prep_)
    return b, secs, [ms for _, ms in streams]


# --- listening -----------------------------------------------------------------------------------------------------

OUT = os.path.join(ROOT, 'work', 'music', 'a4')


def _write(path, x):
    from scipy.io import wavfile
    wavfile.write(path, synth.RATE, (np.clip(x, -1, 1) * 32767).astype(np.int16))


def playthrough(m, start, audio, owner):
    """The mission's music as the game would play it (ownmap.timeline): -> (audio, [(start, end, section)])."""
    fires = [(t, EVENTS[key][0]) for t, key, _ in PLAYTHROUGH if key != 'start']
    parts, rows = [], []
    for t0, t1, s in ownmap.timeline(m, start, fires, PLAYTHROUGH_SECONDS):
        x = audio[s][:int(round((t1 - t0) * synth.RATE))].copy()
        if len(x) < len(audio[s]):                      # a PREP cut: a short fade (what the game does is not measured)
            fade = min(len(x), int(0.03 * synth.RATE))
            x[-fade:] *= np.linspace(1, 0, fade)[:, None]
        parts.append(x)
        if rows and rows[-1][2] == owner[s] and abs(rows[-1][1] - t0) < 1e-6:
            rows[-1] = (rows[-1][0], t1, owner[s])
        else:
            rows.append((t0, t1, owner[s]))
    return np.concatenate(parts), rows


NAMES_ZH = {'prep': '布防', 'escort': '第一程（行进）', 'tense': '交战·劣势（紧张）', 'fierce': '交战·均势/优势（激烈）',
            'final': '最后一程', 'ambush': '冰雕碎了', 'harbour': '港口生变', 'victory': '胜利', 'defeat': '失败',
            'prep>escort': '过渡：布防→行进', 'tense>fierce': '过渡：劣势→激烈', 'fierce>tense': '过渡：激烈→劣势',
            'battle>escort': '过渡：交战→行进', 'battle>final': '过渡：交战→最后一程'}


def page(rows):
    fmt = lambda s: f'{int(s // 60)}:{s % 60:04.1f}'
    story = ''.join(f'<tr><td>{fmt(t)}</td><td>{html.escape(what)}</td><td>{EVENTS[key][0]}'
                    f'{"（立刻切）" if EVENTS[key][2] else "（等小段放完）"}</td></tr>'
                    for t, key, what in PLAYTHROUGH)
    heard = ''.join(f'<tr><td>{fmt(a)}–{fmt(b)}</td><td>{NAMES_ZH[s]}</td></tr>' for a, b, s in rows)
    clips = ''.join(f'<li>{NAMES_ZH[n]}{"（循环两遍）" if SECTIONS[n][1] else ""}<br>'
                    f'<audio controls preload="none" src="sections/{n.replace(">", "_")}.wav"></audio></li>'
                    for n in SECTIONS)
    return f'''<!doctype html><meta charset="utf-8"><title>A4 配乐样品</title>
<style>body{{font:15px/1.6 system-ui,sans-serif;max-width:760px;margin:24px auto;padding:0 16px;background:#fff;color:#222}}
table{{border-collapse:collapse;width:100%}}td{{border-bottom:1px solid #ddd;padding:3px 8px}}audio{{width:100%}}
li{{margin:8px 0}}</style>
<h1>A4 冰雕里的兵 · 配乐样品</h1>
<p>代码写谱，我们自己的合成器渲染（不用采样、不用下载的模型）。D 小调，96 拍每分，每小段 5 秒。</p>
<h2>按关卡流程放一遍（{fmt(PLAYTHROUGH_SECONDS)}，压缩过的时间线）</h2>
<audio controls src="playthrough.wav"></audio>
<table><tr><th>时间</th><th>关卡里发生了什么</th><th>脚本发的事件</th></tr>{story}</table>
<h3>实际播出的段落（按游戏里量到的跳转规律推算）</h3>
<table>{heard}</table>
<h2>各段单听</h2><ul>{clips}</ul>'''


STREAMS = os.path.join(OUT, 'streams')          # every stream as a wav (NNN.wav) and their fingerprints (index.npz)


def streams(sections_too=False):
    """-> (audio per stream, its section), rendered on all cores; sections_too: also each section's wav."""
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor() as ex:
        whole = dict(zip(SECTIONS, ex.map(render, SECTIONS)))
    audio, owner = [], []
    for name, x in whole.items():
        if sections_too:
            os.makedirs(os.path.join(OUT, 'sections'), exist_ok=True)
            _write(os.path.join(OUT, 'sections', name.replace('>', '_') + '.wav'),
                   np.concatenate([x, x]) if SECTIONS[name][1] else x)
        n = int(round(SEG_BARS * BAR * synth.RATE)) if SECTIONS[name][1] else len(x)
        for k in range(0, len(x), n):
            audio.append(x[k:k + n])
            owner.append(name)
    return audio, owner


def pack(folder=None):
    """Our music as a mod build takes it (experimental/music/pack.py): the map, the streams in .mus (44.1 kHz
    stereo EA-XAS); also writes STREAMS, so a recording of the game can be told apart stream by stream
    (listen.identify)."""
    from experimental.music import extract, listen
    from experimental.music import pack as pk
    audio, owner = streams()
    b, secs, lengths = music_map(extract.retail_map())
    assert [len(a) * 1000 // synth.RATE for a in audio] == lengths, 'streams and the map disagree'
    pcm = [(np.clip(a, -1, 1) * 32767).astype(np.int16) for a in audio]
    os.makedirs(STREAMS, exist_ok=True)
    for k, x in enumerate(pcm):
        from scipy.io import wavfile
        wavfile.write(os.path.join(STREAMS, f'{k:03d}.wav'), synth.RATE, x)
    listen.build_index(STREAMS, os.path.join(STREAMS, 'index.npz'))
    tracks = pk.music_tracks(b.m, pcm, synth.RATE)
    return pk.make(b.m, tracks, *([folder] if folder else []))


def heard(wav, min_votes=40):
    """A recording of the game -> [(start s, end s, section)]: each 2 s of it matched to our streams (STREAMS'
    fingerprints), runs of one section joined; chunks matched too weakly (silence, other sound) are left out."""
    from scipy.io import wavfile
    from experimental.music import listen
    sr, x = wavfile.read(wav)
    owner = [name for name, _ in stream_ms()]
    rows = []
    for a, b, stream, off, votes in listen.identify(x, sr, os.path.join(STREAMS, 'index.npz')):
        if votes < min_votes:
            continue
        s = owner[stream]
        if rows and rows[-1][2] == s and a - rows[-1][1] < 4.1:
            rows[-1] = (rows[-1][0], b, s)
        else:
            rows.append((a, b, s))
    return rows


def main():
    if sys.argv[1:2] == ['heard']:
        for a, b, s in heard(sys.argv[2]):
            print(f'{a:6.1f}-{b:6.1f}  {s}')
        return
    import json
    from experimental.music import pfdx
    audio, owner = streams(sections_too=True)
    retail = os.path.join(ROOT, 'work', 'music', 'retail')
    names = json.load(open(os.path.join(retail, 'event_hashes.json')))
    base = pfdx.parse(open(os.path.join(retail, 'map.bin'), 'rb').read(), names)
    b, secs, lengths = music_map(base)
    assert [len(a) * 1000 // synth.RATE for a in audio] == [ms for ms in lengths], 'streams and the map disagree'
    m = b.build([(k, ms) for k, ms in enumerate(lengths)])
    x, rows = playthrough(m, secs['prep'].entry, audio, owner)
    _write(os.path.join(OUT, 'playthrough.wav'), x)
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page(rows))
    for a, b_, s in rows:
        print(f'{a:6.1f}-{b_:6.1f}  {s}')
    print(OUT)


if __name__ == '__main__':
    main()
