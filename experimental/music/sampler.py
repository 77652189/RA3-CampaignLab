"""Recorded orchestra for our scores: the VSCO-2 Community Edition samples (Versilian Studios, CC0,
github.com/sgossner/VSCO-2-CE at 4403009), a subset in work/music/vsco2, played as synth.py's instruments are
(the same calls, the same arguments), so a score switches by name and renders with synth.py alone where the
library is missing (available()).

A note takes the sample nearest in pitch at the velocity layer nearest `vel`, resampled to the pitch, its lead-in
silence cut so the attack lands on the beat; a held note is cut at its length with a release, a short one plays its
staccato / spiccato. The strings and brass split by register into their sections. The file names' octaves are one
below scientific pitch (OCTAVE, measured from the audio: test_sampler).

  python -I -X utf8 experimental/music/sampler.py      the library's index: notes and layers per folder
"""
import functools
import os
import re
import sys

import numpy as np
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from experimental.music import sf2, synth  # noqa: E402

LIB = os.path.join(ROOT, 'work', 'music', 'vsco2')
RATE = synth.RATE
LEVEL = 10 ** (-12 / 20)          # a file's loudest 0.3 s, RMS: about synth.py's instruments at vel 0.7
VEL = 0.7                         # the velocity a file plays at LEVEL; louder or softer in proportion

# (instrument, articulation): folder
FOLDERS = {
    ('violins', 'sus'): 'Strings/Violin Section/susVib', ('violins', 'short'): 'Strings/Violin Section/Spic',
    ('violins', 'trem'): 'Strings/Violin Section/Trem',
    ('violas', 'sus'): 'Strings/Viola Section/susvib', ('violas', 'short'): 'Strings/Viola Section/spic',
    ('celli', 'sus'): 'Strings/Cello Section/susvib', ('celli', 'short'): 'Strings/Cello Section/spic',
    ('celli', 'trem'): 'Strings/Cello Section/trem',
    ('horns', 'sus'): 'Brass/F Horn/sus', ('horns', 'short'): 'Brass/F Horn/stac',
    ('trumpets', 'sus'): 'Brass/Trumpet/sus', ('trumpets', 'short'): 'Brass/Trumpet/stac',
    ('trombones', 'sus'): 'Brass/Tenor Trombone/sus', ('trombones', 'short'): 'Brass/Tenor Trombone/stac',
    ('tuba', 'sus'): 'Brass/Tuba/sus', ('tuba', 'short'): 'Brass/Tuba/stac',
    ('flute', 'sus'): 'Woodwinds/Flute/susvib', ('flute', 'short'): 'Woodwinds/Flute/stac',
    ('oboe', 'sus'): 'Woodwinds/Oboe/Vib', ('oboe', 'short'): 'Woodwinds/Oboe/Stacc',
    ('clarinet', 'sus'): 'Woodwinds/Clarinet/susLong', ('clarinet', 'short'): 'Woodwinds/Clarinet/stac',
    ('bassoon', 'sus'): 'Woodwinds/Bassoon/sus', ('bassoon', 'short'): 'Woodwinds/Bassoon/stac',
    ('harp', 'pluck'): 'Strings/Harp', ('glock', 'hit'): 'Percussion/Glock',
}
# the file names count octaves from C3 = middle C: one octave to add for scientific pitch (A4 = 440 Hz), measured on
# every folder's audio (test_sampler)
OCTAVE = 1
SOUNDS = {'Strings/Harp': -1}     # folders named in scientific pitch after all (measured)
_STEP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
_NOTE = re.compile(r'_([A-G])(#?)(-?\d)(?=[_.])')
_VEL = re.compile(r'_v(\d+)')


def available():
    return os.path.isdir(LIB) and sf2.available()


@functools.lru_cache(maxsize=None)
def index(folder):
    """-> {layer: [(midi, path)]}, layers in order of loudness (the files' v numbers; one layer where they have
    none)."""
    d = os.path.join(LIB, *folder.split('/'))
    out = {}
    for name in sorted(os.listdir(d)):
        m, v = _NOTE.search(name), _VEL.search(name)
        if not (m and name.endswith('.wav')):
            continue
        midi = 12 * (int(m.group(3)) + 1 + OCTAVE + SOUNDS.get(folder, 0)) + _STEP[m.group(1)] + (m.group(2) == '#')
        out.setdefault(int(v.group(1)) if v else 1, []).append((midi, os.path.join(d, name)))
    return {k: sorted(out[k]) for k in sorted(out)}


@functools.lru_cache(maxsize=None)
def load(path):
    """-> (n, 2) float at RATE, the lead-in silence cut (3 ms kept before the attack)."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', wavfile.WavFileWarning)        # the files' sampler chunks
        sr, x = wavfile.read(path)
    x = x.astype(np.float64) / (32768.0 if x.dtype == np.int16 else 2.0 ** 31 if x.dtype == np.int32 else 1.0)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    x = x[:, :2]
    if sr != RATE:
        t = np.arange(int(len(x) * RATE / sr)) * sr / RATE
        x = np.stack([np.interp(t, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)
    env = np.abs(x).max(axis=1)
    start = int(np.argmax(env > env.max() * 10 ** (-40 / 20)))
    x = x[max(0, start - int(0.003 * RATE)):]
    w = int(0.3 * RATE)                          # every file as loud as the next at its loudest 0.3 s: the level is
    mono = x.mean(axis=1)                        # the score's (vel, gain), the layer only the timbre
    loud = max(np.sqrt((mono[i:i + w] ** 2).mean()) for i in range(0, max(1, len(mono) - w + 1), w // 3))
    x = x * (LEVEL / max(loud, 1e-9))
    x.setflags(write=False)
    return x


def _repitch(x, ratio):
    if abs(ratio - 1) < 1e-4:
        return x
    t = np.arange(0, len(x) - 1, ratio)
    return np.stack([np.interp(t, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)


def note(folder, midi, dur, vel=0.7, attack=0.0, release=0.25, layer=None):
    """One note from a folder: -> (n, 2). dur None: the whole sample."""
    layers = index(folder)
    keys = list(layers)
    k = keys[int(round(np.clip(vel, 0, 1) * (len(keys) - 1)))] if layer is None else layer
    near_midi, path = min(layers[k], key=lambda e: abs(e[0] - midi))
    x = _repitch(load(path), 2 ** ((midi - near_midi) / 12)) * (vel / VEL)
    if dur is not None:
        n, r = int(dur * RATE), int(release * RATE)
        x = x[:n + r].copy()
        if len(x) > n:
            x[n:] *= np.linspace(1, 0, len(x) - n)[:, None] ** 2
    else:
        x = x.copy()
    if attack > 0.02:                                       # a swell: the bow's start under a fade in
        a = min(len(x), int(attack * RATE))
        x[:a] *= np.linspace(0, 1, a)[:, None] ** 1.5
    return x


def range_of(folder):
    notes = [m for v in index(folder).values() for m, _ in v]
    return min(notes), max(notes)


def _section(kind, midi, art):
    """The section that plays `midi`, by register, among those with that articulation."""
    order = {'strings': (('celli', 55), ('violas', 65), ('violins', 200)),
             'brass': (('tuba', 41), ('trombones', 53), ('horns', 67), ('trumpets', 200))}[kind]
    names = [n for n, _ in order if (n, art) in FOLDERS]
    first = next((n for n, top in order if midi < top and (n, art) in FOLDERS), names[-1])
    for name in [first] + [n for n in names if n != first]:
        lo, hi = range_of(FOLDERS[name, art])
        if lo - 2 <= midi <= hi + 2:
            return FOLDERS[name, art]
    return FOLDERS[first, art]


def _db(g):
    """A trim (the score's gains were set by ear on synth.py's instruments; test_sampler measures these)."""
    return 10 ** (g / 20)


def _midi(f):
    return 69 + 12 * np.log2(f / 440.0)


# --- synth.py's instruments, recorded --------------------------------------------------------------------------

def strings(f, dur, vel=0.7, bright=0.5, attack=0.25, release=0.6, voices=6, tremolo=0.0, seed=0):
    midi = float(_midi(f))
    if tremolo:
        art = 'trem'
    elif dur < 0.5 and attack < 0.05:
        art = 'short'
    else:
        art = 'sus'
    folder = _section('strings', midi, art)
    if art == 'short':
        return note(folder, midi, None, vel) * _db(3)
    return note(folder, midi, dur, vel, attack=attack, release=max(0.15, release)) * _db(2)


def brass(f, dur, vel=0.8, bright=0.6, release=0.3, voices=3, seed=0):
    midi = float(_midi(f))
    art = 'short' if dur < 0.4 else 'sus'
    folder = _section('brass', midi, art)
    if art == 'short':
        return note(folder, midi, None, vel) * _db(-5)
    return note(folder, midi, dur, vel, release=max(0.15, release))


def _hit(names, vel, seed):
    """One of a set of one-shots ordered soft to loud, by velocity."""
    paths = [os.path.join(LIB, *n.split('/')) for n in names]
    return load(paths[int(round(np.clip(vel, 0, 1) * (len(paths) - 1)))]) * (vel / VEL)


# the five drums' principal (the pitch heard; the fifth and the octave above it ring too), measured
TIMPANI = {1: 41.4, 2: 46.8, 3: 49.5, 4: 52.4, 5: 54.6}


def timpani(vel=0.8, f=73.4, seed=0):
    """The drum nearest the pitch (folded by octaves into the drums' range), retuned to it."""
    want = float(_midi(f))
    while want < 40:
        want += 12
    while want > 57:
        want -= 12
    k = min(TIMPANI, key=lambda d: abs(TIMPANI[d] - want))
    layers = sorted(n for n in os.listdir(os.path.join(LIB, 'Percussion', 'Timpani'))
                    if n.startswith(f'Timpani{k}_Hit'))
    return _repitch(_hit([f'Percussion/Timpani/{n}' for n in layers], vel, seed), 2 ** ((want - TIMPANI[k]) / 12)) * _db(6)


def bass_drum(vel=0.9, seed=0):
    """The concert bass drum."""
    return _hit([f'Percussion/BDrumNewhit_v{k}_rr1_Sum.wav' for k in range(1, 8)], vel, seed)


def snare(vel=0.7, seed=0):
    return _hit([f'Percussion/Snare2-HitSN_v{k}_rr1_Sum.wav' for k in (1, 3, 5, 7, 9)], vel, seed) * _db(-4)


def cymbal(vel=0.7, length=2.5, swell=False, seed=0):
    if swell:
        x = load(os.path.join(LIB, 'Percussion', 'susCymb1-cresc-Short_v1.wav')).copy()
        n = int(length * RATE)                    # the swell's peak lands at `length`
        peak = int(np.argmax(np.abs(x).max(axis=1)))
        x = x[max(0, peak - n):peak + int(0.05 * RATE)]
        return x * (vel / VEL) * _db(-7)
    return _hit([f'Percussion/cymbal-crash1_{d}_rr1.wav' for d in ('pp', 'mp', 'mf', 'ff')], vel, seed) * _db(-7)


def gong(vel=0.8, seed=0):
    return _hit([f'Percussion/gongHit_{d}.wav' for d in ('p', 'mf', 'f', 'fff')], vel, seed)


def woodwind(name, f, dur, vel=0.7, attack=0.0, release=0.3, seed=0):
    """flute, oboe, clarinet or bassoon: held, or (under 0.4 s) staccato."""
    midi = float(_midi(f))
    if dur < 0.4:
        return note(FOLDERS[name, 'short'], midi, None, vel)
    return note(FOLDERS[name, 'sus'], midi, dur, vel, attack=attack, release=release)


def harp(f, dur=1.0, vel=0.7, seed=0):
    return note(FOLDERS['harp', 'pluck'], float(_midi(f)), dur + 1.5, vel, release=0.8)


def glock(f, dur=1.0, vel=0.7, seed=0):
    return note(FOLDERS['glock', 'hit'], float(_midi(f)), None, vel) * _db(6)


# --- from the SoundFont (sf2.py): what VSCO-2 has not --------------------------------------------------------------

GM = {'choir ah': 52, 'choir oo': 53, 'koto': 107, 'shamisen': 106, 'shakuhachi': 77, 'taiko': 116, 'celesta': 8,
      'musicbox': 10, 'guitar': 30}


@functools.lru_cache(maxsize=None)
def _gm_level(program):
    """The preset's middle C at VEL brought to LEVEL, as every VSCO file is."""
    x = sf2.font().note(0, program, 60, 1.0, VEL).mean(axis=1)
    w = int(0.3 * RATE)
    loud = max(np.sqrt((x[i:i + w] ** 2).mean()) for i in range(0, max(1, len(x) - w + 1), w // 3))
    return LEVEL / max(loud, 1e-9)


def _gm(name, midi, dur, vel, release=None):
    return sf2.font().note(0, GM[name], midi, dur, vel, release) * (_gm_level(GM[name]) * vel / VEL)


def _bend(x, semis):
    """x re-read at a pitch that moves: semis(t seconds) -> semitones, per output sample."""
    t = np.arange(len(x)) / RATE
    pos = np.concatenate([[0.0], np.cumsum(2 ** (semis(t) / 12))[:-1]])
    pos = pos[pos < len(x) - 1]
    return np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)


def choir(f, dur, vel=0.6, vowel='ah', attack=0.6, release=1.0, seed=0):
    x = _gm('choir oo' if vowel == 'oo' else 'choir ah', float(_midi(f)), dur, vel, release)
    if attack > 0.02:
        a = min(len(x), int(attack * RATE))
        x[:a] *= np.linspace(0, 1, a)[:, None] ** 1.5
    return x * _db(-8.5)


def koto(f, dur=1.0, vel=0.7, bend=0.0, seed=0):
    """bend: semitones pressed up (oshi) over the note's first half."""
    x = _gm('koto', float(_midi(f)), dur, vel, 1.2)
    if bend:
        x = _bend(x, lambda t: bend * np.clip(t / max(dur * 0.5, 0.05), 0, 1))
    return x


def shamisen(f, dur=0.5, vel=0.8, seed=0):
    return _gm('shamisen', float(_midi(f)), dur, vel, 0.15) * _db(-6)


def shakuhachi(f, dur, vel=0.6, scoop=1.0, fall=0.0, seed=0):
    """Slides up into the note from `scoop` semitones below, falls `fall` at the end."""
    x = _gm('shakuhachi', float(_midi(f)), dur, vel, 0.35)
    return _bend(x, lambda t: -scoop * np.exp(-t / 0.12)
                 - fall * np.clip((t - dur * 0.75) / max(dur * 0.25, 0.05), 0, 1) ** 2)


def taiko(vel=0.9, size=1.0, seed=0):
    """The taiko: larger is lower."""
    return _gm('taiko', 52 - 8 * min(size, 1.2), 0.8, vel, 0.6) * _db(-2 if size < 0.8 else 0)


def celesta(f, dur=1.0, vel=0.7, seed=0):
    return _gm('celesta', float(_midi(f)), dur, vel, 1.5) * _db(6)


def musicbox(f, dur=1.0, vel=0.6, seed=0):
    return _gm('musicbox', float(_midi(f)), dur, vel, 1.5) * _db(6.5)


def guitar(f, dur, vel=0.8, mute=False, shape=(0, 7, 12), seed=0):
    """A power chord (`shape`: semitones over f) on the distorted guitar; mute: palm-muted, a short dark chug."""
    midi = float(_midi(f))
    x = sum(_gm('guitar', midi + s, 0.12 if mute else dur, vel, 0.03 if mute else 0.1) for s in shape)
    if mute:
        x = synth.lp(x, 900)
    return x * _db(-6)


def main():
    for (inst, art), folder in FOLDERS.items():
        layers = index(folder)
        lo, hi = range_of(folder)
        print(f'{inst:10s} {art:6s} layers {list(layers)} notes {sum(map(len, layers.values()))} midi {lo}-{hi}')


if __name__ == '__main__':
    main()
