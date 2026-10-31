"""The recorded orchestra (experimental/music/sampler.py): notes come out at the pitch asked for (the library's file
names are an octave low: sampler.OCTAVE) and about as loud as synth.py's instrument they stand in for, so a
score's gains hold whichever plays it."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from experimental.music import sampler, synth  # noqa: E402

pytestmark = pytest.mark.skipif(not sampler.available(), reason='needs the VSCO-2 CE subset in work/music/vsco2 '
                                                                 '(fetch_samples.py) and MuseScore_General.sf2')


def _pitch(x):
    """The fundamental (harmonic product spectrum, 0.2-0.7 s in) as a midi number."""
    y = x[int(0.2 * synth.RATE):int(0.7 * synth.RATE)].mean(axis=1)
    s = np.abs(np.fft.rfft(y * np.hanning(len(y)), 1 << 17))
    f = np.fft.rfftfreq(1 << 17, 1 / synth.RATE)
    hps = s.copy()
    for h in (2, 3, 4):
        hps[:len(s[::h])] *= s[::h]
    ok = (f > 25) & (f < 2000)
    return 69 + 12 * np.log2(f[ok][np.argmax(hps[ok])] / 440)


@pytest.mark.parametrize('inst, midi', [(sampler.strings, 57), (sampler.strings, 69), (sampler.strings, 45),
                                        (sampler.brass, 62), (sampler.brass, 70), (sampler.harp, 62),
                                        (sampler.choir, 57), (sampler.koto, 62), (sampler.shakuhachi, 69),
                                        (lambda f, d, v: sampler.woodwind('oboe', f, d, v), 74),
                                        (lambda f, d, v: sampler.woodwind('flute', f, d, v), 76)])
def test_a_note_sounds_at_its_pitch(inst, midi):
    f = float(synth.hz(midi))
    x = inst(f, 2.0, 0.7, attack=0.01) if inst is sampler.strings else inst(f, 2.0, 0.7)
    assert _pitch(x) == pytest.approx(midi, abs=0.3)


def _loudest(x):
    m, w = x.mean(axis=1) if x.ndim == 2 else x, int(0.3 * synth.RATE)
    return 20 * np.log10(max(np.sqrt((m[i:i + w] ** 2).mean()) for i in range(0, max(1, len(m) - w), w // 2)))


@pytest.mark.parametrize('call', [
    lambda m: m.strings(synth.hz(57), 2.0, 0.6, attack=0.1), lambda m: m.strings(synth.hz(50), 0.3, 0.7, attack=0.01),
    lambda m: m.strings(synth.hz(50), 2.0, 0.6, tremolo=12.8), lambda m: m.brass(synth.hz(62), 2.0, 0.75),
    lambda m: m.brass(synth.hz(69), 0.3, 0.8), lambda m: m.timpani(0.8, synth.hz(38)), lambda m: m.taiko(0.8),
    lambda m: m.snare(0.7), lambda m: m.cymbal(0.7), lambda m: m.choir(synth.hz(57), 3.0, 0.5),
    lambda m: m.koto(synth.hz(62), 1.0, 0.6), lambda m: m.shamisen(synth.hz(69), 0.3, 0.8),
    lambda m: m.shakuhachi(synth.hz(69), 2.0, 0.75), lambda m: m.celesta(synth.hz(81), 1.0, 0.55),
    lambda m: m.musicbox(synth.hz(93), 1.0, 0.4), lambda m: m.glock(synth.hz(86), 1.0, 0.4),
    lambda m: m.guitar(synth.hz(38), 0.5, 0.85), lambda m: m.taiko(0.8, size=0.45)])
def test_as_loud_as_the_synth_it_stands_in_for(call):
    assert _loudest(call(sampler)) == pytest.approx(_loudest(call(synth)), abs=2.0)


def test_a_note_starts_on_its_beat():
    """The files' lead-in silence is cut: the attack is within a few ms of the start."""
    x = sampler.brass(float(synth.hz(62)), 1.0, 0.8)
    env = np.abs(x).max(axis=1)
    assert np.argmax(env > env.max() * 0.1) < 0.03 * synth.RATE
