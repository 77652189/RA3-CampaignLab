"""Our own synthesizer: the instruments our scores are written for, numpy and scipy only (no samples, nothing to
download), so every sound is ours and comes out the same on every machine.

Audio is float at RATE, mono (n,) or stereo (n, 2). An instrument renders one note on its own, from its start, its
ring-out included; Mix places notes on a timeline. A looping section wraps whatever rings past its end back to its
start and its reverb is circular, so it loops with no seam; a one-shot (stinger, transition) is cut at its length.

  m = Mix(seconds, loop=True)
  m.add(start s, audio, gain dB, pan -1..1, verb 0..1)
  m.render(rms dB) -> (n, 2)        dry + reverb, high-passed, levelled to an RMS, soft peak ceiling
"""
import zlib

import numpy as np
from scipy import signal

RATE = 44100


def hz(midi):
    return 440.0 * 2.0 ** ((np.asarray(midi, dtype=float) - 69) / 12)


def _rng(*key):
    """The same noise for the same note on every render."""
    return np.random.default_rng(zlib.crc32(repr(key).encode()))


def _t(n):
    return np.arange(n) / RATE


def _sos(kind, f, order=2):
    f = np.clip(f, 20, RATE / 2 * 0.95)
    return signal.butter(order, f, btype=kind, fs=RATE, output='sos')


def lp(x, f, order=2):
    return signal.sosfilt(_sos('lowpass', f, order), x, axis=0)


def hp(x, f, order=2):
    return signal.sosfilt(_sos('highpass', f, order), x, axis=0)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(_sos('bandpass', [lo, hi], order), x, axis=0)


def saw(f, n, phase=0.0):
    """Band-limited sawtooth (polyBLEP); f a number or an (n,) array (vibrato, glides)."""
    dt = np.broadcast_to(np.asarray(f, dtype=float) / RATE, (n,))
    ph = (phase + np.cumsum(dt)) % 1.0
    y = 2 * ph - 1
    m = ph < dt
    x = ph[m] / dt[m]
    y[m] -= x + x - x * x - 1
    m = ph > 1 - dt
    x = (ph[m] - 1) / dt[m]
    y[m] -= x * x + x + x + 1
    return y


def sine(f, n, phase=0.0):
    return np.sin(2 * np.pi * (phase + np.cumsum(np.broadcast_to(np.asarray(f, dtype=float) / RATE, (n,)))))


def adsr(n, attack, decay, sustain, hold, release):
    """Envelope over n samples: rises in `attack`, falls to `sustain` in `decay`, held until `hold` s, then an
    exponential release (about -60 dB after `release` s)."""
    t = _t(n)
    e = np.where(t < attack, np.sin(0.5 * np.pi * np.clip(t / max(attack, 1e-4), 0, 1)) ** 2,
                 sustain + (1 - sustain) * np.exp(-(t - attack) / max(decay, 1e-4)))
    at_hold = np.interp(hold, t, e) if hold < t[-1] else e[-1]
    return np.where(t < hold, e, at_hold * np.exp(-6.9 * (t - hold) / max(release, 1e-3)))


def _stereo(mono, pan):
    a = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)], axis=-1)


def _modal(f, partials, n, scale_decay=True):
    """Struck or plucked bodies: [(ratio, amplitude, decay s)] of f; higher notes ring shorter."""
    t = _t(n)
    k = (523.0 / f) ** 0.5 if scale_decay else 1.0
    y = np.zeros(n)
    for ratio, amp, tau in partials:
        if f * ratio < RATE * 0.45:
            y += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t / (tau * k))
    return y


def _click(n, lo, hi, tau, seed):
    t = _t(n)
    return bp(_rng('click', seed).standard_normal(n), lo, hi) * np.exp(-t / tau)


# --- sustained -------------------------------------------------------------------------------------------------

def strings(f, dur, vel=0.7, bright=0.5, attack=0.25, release=0.6, voices=6, tremolo=0.0, seed=0):
    """A string section: detuned sawtooths spread across the stereo field, delayed vibrato, a lowpass that opens
    with `bright` and `vel`. tremolo: bowing repeats per second (0 = legato)."""
    n = int((dur + release + 0.05) * RATE)
    t = _t(n)
    rng = _rng('str', f, dur, seed)
    detune = np.linspace(-14, 14, voices) + rng.uniform(-2, 2, voices)
    vib = 1 + 0.0018 * np.sin(2 * np.pi * rng.uniform(4.8, 5.6) * t) * np.clip((t - 0.25) / 0.4, 0, 1)
    out = np.zeros((n, 2))
    for k, c in enumerate(detune):
        v = saw(f * 2 ** (c / 1200) * vib, n, rng.uniform())
        out += _stereo(v, (k / max(voices - 1, 1)) * 1.4 - 0.7)
    cutoff = f * (2.5 + 9 * bright * (0.5 + 0.5 * vel))
    out = hp(lp(out, min(cutoff, 14000), 2), 60)
    env = adsr(n, attack, 0.4, 0.85, dur, release)
    if tremolo:
        env = env * (0.55 + 0.45 * np.abs(np.sin(np.pi * tremolo * t)) ** 0.6)
    return out * env[:, None] * vel / voices ** 0.5


def brass(f, dur, vel=0.8, bright=0.6, release=0.3, voices=3, seed=0):
    """Horns and trumpets: the tone brightens as the note speaks (a dark and a bright filtering crossfaded by a
    fast envelope), a small scoop up into pitch, a breath of noise."""
    n = int((dur + release + 0.05) * RATE)
    t = _t(n)
    rng = _rng('brass', f, dur, seed)
    scoop = 1 - 0.018 * np.exp(-t / 0.05)
    raw = sum(saw(f * 2 ** (c / 1200) * scoop, n, rng.uniform()) for c in np.linspace(-5, 5, voices)) / voices
    dark, light = lp(raw, f * 2.2), lp(raw, min(f * (3 + 9 * bright * vel), 12000))
    blare = np.exp(-t / 0.35) * 0.6 + 0.4 * vel
    y = dark + (light - dark) * blare
    y += 0.04 * vel * bp(rng.standard_normal(n), f * 2, min(f * 6, 9000)) * np.exp(-t / 0.08)
    return hp(y, 50) * adsr(n, 0.035 + 0.04 * (1 - vel), 0.3, 0.8, dur, release) * vel


def choir(f, dur, vel=0.6, vowel='ah', attack=0.6, release=1.0, seed=0):
    """Voices: detuned sawtooths through a vowel's formants."""
    formants = {'ah': [(800, 1.0), (1150, 0.5), (2900, 0.25)], 'oo': [(350, 1.0), (650, 0.35), (2700, 0.08)],
                'eh': [(500, 1.0), (1700, 0.5), (2500, 0.25)]}[vowel]
    n = int((dur + release + 0.05) * RATE)
    t = _t(n)
    rng = _rng('choir', f, dur, seed)
    out = np.zeros((n, 2))
    for k in range(5):
        vib = 1 + 0.004 * np.sin(2 * np.pi * rng.uniform(4.5, 6) * t + rng.uniform(0, 6))
        v = saw(f * 2 ** (rng.uniform(-12, 12) / 1200) * vib, n, rng.uniform())
        v = sum(a * bp(v, fc / 1.18, fc * 1.18) for fc, a in formants)
        out += _stereo(v, k / 4 * 1.2 - 0.6)
    return out * (adsr(n, attack, 0.5, 0.9, dur, release) * vel / 2)[:, None]


def pad(f, dur, vel=0.5, attack=1.2, release=1.8, seed=0):
    """A cold pad: soft odd harmonics and an octave shimmer that drifts slowly in and out of tune."""
    n = int((dur + release + 0.05) * RATE)
    t = _t(n)
    rng = _rng('pad', f, dur, seed)
    y = sum(sine(f * k, n, rng.uniform()) / k ** 2 for k in (1, 3, 5, 7))
    left = sine(f * 2 * 2 ** (3 / 1200), n, rng.uniform()) * 0.35
    right = sine(f * 2 * 2 ** (-3 / 1200), n, rng.uniform()) * 0.35
    drift = 0.6 + 0.4 * np.sin(2 * np.pi * 0.17 * t + rng.uniform(0, 6))
    out = np.stack([y + left * drift, y + right * (1.6 - drift)], axis=-1)
    return out * (adsr(n, attack, 1.0, 0.9, dur, release) * vel)[:, None]


def bass(f, dur, vel=0.8, release=0.08, seed=0):
    """A short, dark bass for ostinatos: a filtered sawtooth over a sine an octave down."""
    n = int((dur + release + 0.03) * RATE)
    y = lp(saw(f, n), f * (3 + 4 * vel)) * 0.75 + 0.6 * sine(f, n) + 0.2 * sine(f / 2, n)
    return y * adsr(n, 0.004, 0.15, 0.7, dur, release) * vel


# --- struck and plucked ----------------------------------------------------------------------------------------

def celesta(f, dur=1.0, vel=0.7, seed=0):
    n = int(2.5 * RATE)
    y = _modal(f, [(1, 1.0, 1.4), (2, 0.35, 0.45), (3, 0.1, 0.2), (4.16, 0.05, 0.1)], n)
    return (y + 0.08 * _click(n, 2000, 9000, 0.004, ('cel', f, seed))) * vel


def glock(f, dur=1.0, vel=0.7, seed=0):
    n = int(3.5 * RATE)
    y = _modal(f, [(1, 1.0, 2.4), (2.76, 0.4, 0.9), (5.40, 0.2, 0.4), (8.93, 0.08, 0.18)], n)
    return (y + 0.1 * _click(n, 3000, 12000, 0.003, ('glock', f, seed))) * vel


def musicbox(f, dur=1.0, vel=0.6, seed=0):
    n = int(2.5 * RATE)
    y = _modal(f, [(1, 1.0, 1.6), (2.0, 0.12, 0.5), (3.01, 0.22, 0.4), (5.97, 0.07, 0.15)], n)
    return (y + 0.05 * _click(n, 4000, 12000, 0.002, ('box', f, seed))) * vel


def koto(f, dur=1.0, vel=0.7, bend=0.0, seed=0):
    """A plucked silk string: harmonics shaped by where it is plucked, upper ones dying first, a slight
    inharmonicity. bend: semitones pressed up (oshi) over the note's first half."""
    n = int((dur + 1.6) * RATE)
    t = _t(n)
    p, B = 0.22, 0.0003
    ratio = 2 ** (bend * np.clip(t / max(dur * 0.5, 0.05), 0, 1) / 12) if bend else 1.0
    y = np.zeros(n)
    for k in range(1, 25):
        fk = f * k * (1 + B * k * k) ** 0.5
        if fk > RATE * 0.42:
            break
        tau = 1.4 * (220 / f) ** 0.3 / (1 + 0.5 * (k - 1))
        y += np.sin(np.pi * k * p) / k ** 1.1 * np.sin(2 * np.pi * np.cumsum(fk * np.broadcast_to(ratio, (n,))) /
                                                      RATE) * np.exp(-t / tau)
    y += 0.25 * _click(n, 1500, 6000, 0.006, ('koto', f, seed))
    damp = np.where(t < dur + 0.25, 1.0, np.exp(-(t - dur - 0.25) / 0.15))
    return y * damp * vel * 0.6


def taiko(vel=0.9, size=1.0, seed=0):
    """Size 1: a big o-daiko; 0.5: a small high shime-daiko."""
    n = int((0.4 + 1.2 * size) * RATE)
    t = _t(n)
    f0 = 56 / size ** 1.3
    f = f0 * (1 + 0.9 * np.exp(-t / 0.018))
    ph = 2 * np.pi * np.cumsum(f) / RATE
    body = (0.6 * np.sin(ph) * np.exp(-t / (0.45 * size)) + 0.45 * np.sin(1.52 * ph) * np.exp(-t / (0.2 * size)) +
            0.3 * np.sin(2.31 * ph) * np.exp(-t / (0.09 * size)))
    slap = lp(_rng('taiko', vel, seed).standard_normal(n), 2500 / size ** 0.5) * np.exp(-t / 0.015)
    return hp(np.tanh(1.2 * (body + 0.8 * slap)), 32) * vel


def snare(vel=0.7, seed=0):
    n = int(0.45 * RATE)
    t = _t(n)
    tone = 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04) + 0.25 * np.sin(2 * np.pi * 330 * t) * np.exp(-t / 0.025)
    wires = bp(_rng('snare', vel, seed).standard_normal(n), 1500, 5500 + 2000 * vel) * np.exp(-t / (0.09 + 0.06 * vel))
    return (tone + 0.9 * wires) * vel


def timpani(vel=0.8, f=73.4, seed=0):
    n = int(3.0 * RATE)
    y = _modal(f, [(1, 1.0, 1.6), (1.5, 0.45, 0.9), (1.98, 0.25, 0.6), (2.44, 0.12, 0.4)], n, scale_decay=False)
    t = _t(n)
    return (y + 0.4 * lp(_rng('timp', f, vel, seed).standard_normal(n), 500) * np.exp(-t / 0.02)) * vel


def cymbal(vel=0.7, length=2.5, swell=False, seed=0):
    """A crash, or (swell) the same reversed: it rises into the beat it ends on."""
    n = int(length * RATE)
    t = _t(n)
    rng = _rng('cym', vel, length, seed)
    y = bp(rng.standard_normal((n, 2)), 3500, 10000) * np.exp(-t / (length / 4))[:, None]
    y += 0.3 * bp(rng.standard_normal((n, 2)), 600, 3000) * np.exp(-t / 0.15)[:, None]
    return (y[::-1] if swell else y) * vel * 0.5


# --- the band: what makes it Red Alert 3 (rock and electronics over the orchestra) ------------------------------

def kick(vel=0.9, seed=0):
    n = int(0.5 * RATE)
    t = _t(n)
    f = 55 + 120 * np.exp(-t / 0.028)
    body = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t / 0.18)
    beater = hp(_rng('kick', vel, seed).standard_normal(n), 2500) * np.exp(-t / 0.004)
    return hp(np.tanh(1.8 * (body + 0.35 * beater)), 40) * vel


def rock_snare(vel=0.8, seed=0):
    n = int(0.6 * RATE)
    t = _t(n)
    rng = _rng('rsnare', vel, seed)
    body = np.sin(2 * np.pi * 200 * t * (1 + 0.2 * np.exp(-t / 0.01))) * np.exp(-t / 0.07)
    wires = bp(rng.standard_normal(n), 1000, 5500) * np.exp(-t / 0.16)
    crack = bp(rng.standard_normal(n), 2500, 8000) * np.exp(-t / 0.01)
    return np.tanh(1.5 * (1.3 * body + 0.8 * wires + 0.3 * crack)) * vel


_METAL = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)          # six square waves: a cymbal's clangour


def hat(vel=0.5, open_=False, seed=0):
    n = int((0.45 if open_ else 0.09) * RATE)
    t = _t(n)
    metal = sum(np.sign(np.sin(2 * np.pi * f * 2.0 * t + k)) for k, f in enumerate(_METAL))
    noise = _rng('hat', vel, seed).standard_normal(n)
    y = bp(0.6 * metal / 6 + 0.5 * noise, 7000, 15000)
    return y * np.exp(-t / (0.12 if open_ else 0.022)) * vel


def tom(vel=0.8, f=110.0, seed=0):
    n = int(0.6 * RATE)
    t = _t(n)
    fr = f * (1 + 0.5 * np.exp(-t / 0.04))
    body = np.sin(2 * np.pi * np.cumsum(fr) / RATE) * np.exp(-t / 0.25)
    stick = bp(_rng('tom', f, vel, seed).standard_normal(n), 1000, 5000) * np.exp(-t / 0.01)
    return np.tanh(1.3 * (body + 0.3 * stick)) * vel


def guitar(f, dur, vel=0.8, mute=False, shape=(0, 7, 12), seed=0):
    """A distorted electric guitar playing a power chord (`shape`: semitones over f, the low E string's D tuned
    down): the strings are distorted together, as an amp does, then through a speaker cabinet. mute: palm-muted
    (a short, dark chug)."""
    ring = 0.12 if mute else dur + 0.15
    n = int((ring + 0.1) * RATE)
    t = _t(n)
    rng = _rng('gtr', f, dur, mute, seed)
    x = sum(saw(f * 2 ** ((s + rng.uniform(-0.06, 0.06)) / 12), n, rng.uniform()) for s in shape)
    x = lp(x, 700 if mute else 3000) * np.exp(-t / (0.07 if mute else 1.2))
    x = hp(x, 90)
    drive = 9 + 10 * vel
    y = np.tanh(drive * x + 0.25) - np.tanh(0.25)
    cab = lp(hp(y, 85), 6000, 4)
    cab = cab + 1.2 * bp(cab, 1200, 3500)               # the speaker's presence peak
    env = np.where(t < ring, 1.0, np.exp(-(t - ring) / 0.03)) * np.clip(t / 0.002, 0, 1)
    return cab * env * vel * 0.25


def synth_pluck(f, dur, vel=0.7, decay=0.18, seed=0):
    """The electronic pulse under the orchestra: two detuned sawtooths and a square, a filter that snaps shut."""
    n = int((dur + 0.4) * RATE)
    t = _t(n)
    rng = _rng('pluck', f, dur, seed)
    x = 0.5 * (saw(f * 2 ** (7 / 1200), n, rng.uniform()) + saw(f * 2 ** (-7 / 1200), n, rng.uniform()))
    x += 0.4 * np.sign(sine(f, n, rng.uniform()))
    dark, light = lp(x, f * 1.2), lp(x, min(f * 14, 14000))
    y = dark + (light - dark) * np.exp(-t / decay)[:]
    return hp(y, 120) * adsr(n, 0.002, decay * 2, 0.25, dur, 0.15) * vel * 0.6


def shakuhachi(f, dur, vel=0.6, scoop=1.0, fall=0.0, seed=0):
    """The bamboo flute: a breathy tone that slides up into the note (`scoop` semitones below), a delayed
    vibrato, a fall at the end (`fall` semitones)."""
    n = int((dur + 0.5) * RATE)
    t = _t(n)
    rng = _rng('shaku', f, dur, seed)
    bend = -scoop * np.exp(-t / 0.12) - fall * np.clip((t - dur * 0.75) / max(dur * 0.25, 0.05), 0, 1) ** 2
    vib = 0.25 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.4) / 0.5, 0, 1)
    fr = f * 2 ** ((bend + vib) / 12)
    ph = 2 * np.pi * np.cumsum(fr) / RATE
    tone = np.sin(ph) + 0.22 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    breath = bp(rng.standard_normal(n), f * 0.9, min(f * 4, 12000)) * (0.35 + 0.8 * np.exp(-t / 0.06))
    env = adsr(n, 0.12, 0.3, 0.8, dur, 0.35) * (1 + 0.15 * np.sin(2 * np.pi * 0.7 * t))
    return (tone + 0.5 * breath) * env * vel * 0.5


def shamisen(f, dur=0.5, vel=0.8, seed=0):
    """Three strings struck with a plectrum: bright, quick to die, with the buzz of the sawari."""
    n = int((dur + 0.6) * RATE)
    t = _t(n)
    y = np.zeros(n)
    for k in range(1, 30):
        if f * k > RATE * 0.42:
            break
        y += np.sin(np.pi * k * 0.1) / k ** 0.9 * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (3 + 2.2 * k))
    y = np.tanh(2.5 * y + 0.3 * y ** 2)
    y += 0.4 * _click(n, 2000, 8000, 0.003, ('sham', f, seed))
    return y * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.05)) * vel * 0.5


# --- the scenery -----------------------------------------------------------------------------------------------

def _periodic_noise(n, rng, lo, hi, channels=2):
    """Noise whose spectrum is shaped in one FFT: periodic over n samples, so a loop of it has no seam."""
    spec = rng.standard_normal((n // 2 + 1, channels)) + 1j * rng.standard_normal((n // 2 + 1, channels))
    fr = np.fft.rfftfreq(n, 1 / RATE)
    octaves = np.log(np.maximum(fr, 1) / np.sqrt(lo * hi)) / np.log(hi / lo) * 2      # 0 at the band's middle
    shape = (np.exp(-octaves ** 2) / np.sqrt(np.maximum(fr, 20)))[:, None]
    y = np.fft.irfft(spec * shape, n, axis=0)
    return y / (np.abs(y).max() + 1e-9)


def wind(seconds, vel=0.3, seed=0):
    """Snow wind over a whole loop: two bands of noise breathing at speeds that fit the loop a whole number of
    times (so it loops)."""
    n = int(seconds * RATE)
    t = _t(n)
    rng = _rng('wind', seconds, seed)
    low, high = _periodic_noise(n, rng, 250, 900), _periodic_noise(n, rng, 1200, 4000)
    cyc = lambda k, ph: 0.5 + 0.5 * np.sin(2 * np.pi * k * t / seconds + ph)
    return (low * cyc(2, 0)[:, None] ** 2 + 0.4 * high * cyc(3, 1.7)[:, None] ** 3) * vel


def sparkle(seconds, per_second=3.0, vel=0.2, seed=0):
    """Ice glitter: tiny high bell strikes at random times."""
    n = int(seconds * RATE)
    rng = _rng('sparkle', seconds, seed)
    out = np.zeros((n, 2))
    tiny = int(0.25 * RATE)
    for _ in range(int(seconds * per_second)):
        at = rng.integers(0, n)
        f = rng.uniform(3500, 9000)
        y = _modal(f, [(1, 1.0, 0.09), (2.76, 0.3, 0.04)], tiny, scale_decay=False) * rng.uniform(0.3, 1.0)
        y = _stereo(y, rng.uniform(-0.9, 0.9))
        idx = (at + np.arange(tiny)) % n
        out[idx] += y
    return out * vel


def ice_crack(vel=1.0, seed=0):
    """Ice giving way: a run of sharp cracks, a low thud, then shards tinkling down."""
    n = int(2.2 * RATE)
    rng = _rng('crack', vel, seed)
    t = _t(n)
    out = np.zeros((n, 2))
    at = 0
    for k in range(rng.integers(5, 8)):
        m = int(0.03 * RATE)
        c = hp(rng.standard_normal(m), 2500) * np.exp(-_t(m) / rng.uniform(0.002, 0.008)) * rng.uniform(0.5, 1)
        out[at:at + m] += _stereo(c, rng.uniform(-0.6, 0.6))
        at += int(rng.uniform(0.015, 0.07) * RATE)
    thud = np.sin(2 * np.pi * 70 * t * (1 + 0.5 * np.exp(-t / 0.03))) * np.exp(-t / 0.25)
    out += _stereo(thud, 0) * 0.8
    for _ in range(40):
        s = int(rng.uniform(0.05, 1.2) ** 1.5 * RATE)
        m = int(0.2 * RATE)
        if s + m < n:
            y = _modal(rng.uniform(2500, 8000), [(1, 1.0, 0.06), (2.4, 0.4, 0.03)], m, scale_decay=False)
            out[s:s + m] += _stereo(y * rng.uniform(0.1, 0.5), rng.uniform(-1, 1))
    out += hp(rng.standard_normal((n, 2)), 4000) * (np.exp(-t / 0.3) * 0.25)[:, None]
    return out * vel


# --- mixing ----------------------------------------------------------------------------------------------------

def impulse(rt=2.2, seconds=3.0, predelay=0.025, seed=0):
    """A hall: decorrelated stereo noise decaying faster in the highs than the lows, after a few early
    reflections."""
    n = int(seconds * RATE)
    t = _t(n)
    rng = _rng('hall', rt, seconds, seed)
    w = rng.standard_normal((n, 2))
    decay = lambda r: np.exp(-6.9 * t / r)[:, None]
    ir = lp(w, 400) * decay(rt * 1.25) + bp(w, 400, 3500) * decay(rt) + hp(w, 3500) * decay(rt * 0.45)
    ir *= np.clip(t / 0.03, 0, 1)[:, None]
    for d, g in ((0.011, 0.5), (0.019, 0.35), (0.027, 0.3), (0.041, 0.22)):
        ir[int(d * RATE)] += g * rng.choice([-1, 1], 2)
    ir = np.concatenate([np.zeros((int(predelay * RATE), 2)), ir])
    return ir / np.sqrt((ir ** 2).sum(axis=0))


_HALL = {}


class Mix:
    def __init__(self, seconds, loop=False, rt=2.2):
        self.n = int(round(seconds * RATE))
        self.loop, self.rt = loop, rt
        self.dry = np.zeros((self.n, 2))
        self.send = np.zeros((self.n, 2))

    def add(self, start, audio, gain=0.0, pan=0.0, verb=0.25):
        a = audio if audio.ndim == 2 else _stereo(audio, pan)
        if audio.ndim == 2 and pan:
            a = a * np.array([min(1, 1 - pan), min(1, 1 + pan)])
        a = a * 10 ** (gain / 20)
        at = int(round(start * RATE))
        if not self.loop:
            a = a[:max(0, self.n - at)]
        at %= self.n
        while len(a):                           # a loop: what rings past the end goes on from the start
            k = min(len(a), self.n - at)
            self.dry[at:at + k] += a[:k] * (1 - 0.5 * verb)
            self.send[at:at + k] += a[:k] * verb
            a, at = a[k:], 0

    def render(self, rms_db=-18.0, ceiling_db=-1.0):
        ir = _HALL.setdefault(self.rt, impulse(self.rt))
        if self.loop:
            assert len(ir) < self.n, 'a loop shorter than the reverb'
            wet = np.fft.irfft(np.fft.rfft(self.send, axis=0) * np.fft.rfft(ir, self.n, axis=0), self.n, axis=0)
        else:
            wet = signal.fftconvolve(self.send, ir, axes=0)[:self.n]
        x = self.dry + 1.6 * wet
        x = hp(x, 28)                          # (a 2nd-order filter's settling at a loop's start is far below hearing)
        return finish(x, rms_db, ceiling_db)


def finish(x, rms_db=-18.0, ceiling_db=-1.0):
    """Levelled to an RMS, peaks under a soft ceiling."""
    x = x * 10 ** (rms_db / 20) / (np.sqrt((x ** 2).mean()) + 1e-12)
    ceil = 10 ** (ceiling_db / 20)
    knee = 0.6 * ceil
    over = np.abs(x) > knee
    x[over] = np.sign(x[over]) * (knee + (ceil - knee) * np.tanh((np.abs(x[over]) - knee) / (ceil - knee)))
    return x


# --- matching a reference's balance --------------------------------------------------------------------------------

BANDS = 31.5 * 2.0 ** (np.arange(28) / 3)                # third-octave centres, 31.5 Hz .. 16 kHz


def profile(x):
    """-> (dB per BANDS, relative to the whole; side over mid dB): a recording's long-term balance."""
    spec = np.abs(np.fft.rfft(x.mean(axis=1))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    edge = BANDS * 2 ** (1 / 6)
    lo = np.concatenate([[BANDS[0] / 2 ** (1 / 6)], edge[:-1]])
    e = np.array([spec[(f >= a) & (f < b)].sum() for a, b in zip(lo, edge)]) + 1e-20
    mid, side = x.mean(axis=1), (x[:, 0] - x[:, 1]) / 2
    return 10 * np.log10(e / e.sum()), 10 * np.log10(((side ** 2).mean() + 1e-20) / ((mid ** 2).mean() + 1e-20))


def match(x, bands, side_mid, limit=9.0, loop=True):
    """An EQ (and a stereo width) that moves x's balance to a reference's (profile()), at most `limit` dB a band,
    both balances smoothed over five bands first. Applied in one circular FFT over the whole, so a loop stays
    seamless; a one-shot is padded with its ring-out room first."""
    tilt = lambda v: np.convolve(np.pad(v, 2, mode='edge'), np.array([1, 2, 3, 2, 1]) / 9, 'valid')
    gain = np.clip(tilt(np.asarray(bands)) - tilt(profile(x)[0]), -limit, limit)    # the broad balance, not
                                                                                     # the notes either one plays
    n = len(x)
    pad = 0 if loop else int(0.5 * RATE)
    y = np.concatenate([x, np.zeros((pad, 2))]) if pad else x
    f = np.fft.rfftfreq(len(y), 1 / RATE)
    curve = 10 ** (np.interp(np.log2(np.maximum(f, 1)), np.log2(BANDS), gain) / 20)
    y = np.fft.irfft(np.fft.rfft(y, axis=0) * curve[:, None], len(y), axis=0)[:n]
    sm = profile(y)[1]
    mid, side = y.mean(axis=1), (y[:, 0] - y[:, 1]) / 2
    side = side * float(np.clip(10 ** ((side_mid - sm) / 20), 0.4, 1.6))
    return np.stack([mid + side, mid - side], axis=1)
