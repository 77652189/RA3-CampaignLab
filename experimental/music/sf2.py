"""A SoundFont 2 reader and note renderer, numpy only, for the instruments VSCO-2 lacks (sampler.py): the choir,
the Empire's koto, shamisen, shakuhachi and taiko. The font is MuseScore_General.sf2 (MuseScore, MIT; FluidR3 by
Frank Wen, FluidR3Mono by Michael Cowgill, adapted by S. Christian Collins: their notices go with whatever we ship
that carries its sound, MuseScore_General_License.md next to it), fetched into work/music/musescore from
ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/.

What is read of SoundFont 2.01: presets -> instruments -> zones by key and velocity, each zone's sample, root key
and tuning, loop, pan, attenuation and its volume envelope (delay, attack, hold, decay, sustain, release). Not
modulators, filters, LFOs or the modulation envelope.

  python -I -X utf8 experimental/music/sf2.py            the presets
"""
import functools
import os
import struct
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT = os.path.join(ROOT, 'work', 'music', 'musescore', 'MuseScore_General.sf2')
RATE = 44100

# generator numbers (SoundFont 2.01, 8.1.2)
START, END, LOOP_START, LOOP_END = 0, 1, 2, 3
START_COARSE, END_COARSE, LOOP_START_COARSE, LOOP_END_COARSE = 4, 12, 45, 50
PAN, DELAY, ATTACK, HOLD, DECAY, SUSTAIN, RELEASE = 17, 33, 34, 35, 36, 37, 38
INSTRUMENT, KEY_RANGE, VEL_RANGE, ATTENUATION = 41, 43, 44, 48
COARSE_TUNE, FINE_TUNE, SAMPLE_ID, SAMPLE_MODES, SCALE_TUNING, ROOT_KEY = 51, 52, 53, 54, 56, 58
_RANGES = (KEY_RANGE, VEL_RANGE)
_ENV_DEFAULT = {DELAY: -12000, ATTACK: -12000, HOLD: -12000, DECAY: -12000, SUSTAIN: 0, RELEASE: -12000}


def _chunks(data, at, end):
    while at < end:
        cid, size = data[at:at + 4], struct.unpack_from('<I', data, at + 4)[0]
        yield cid, at + 8, size
        at += 8 + size + (size & 1)


class Font:
    def __init__(self, path=FONT):
        self.data = open(path, 'rb').read()
        d = self.data
        assert d[:4] == b'RIFF' and d[8:12] == b'sfbk', path
        parts = {}
        for cid, at, size in _chunks(d, 12, len(d)):
            if cid == b'LIST':
                for sub, a, s in _chunks(d, at + 4, at + size):
                    parts[sub] = (a, s)
        a, s = parts[b'smpl']
        self.smpl = np.frombuffer(d, dtype='<i2', count=s // 2, offset=a)
        rec = lambda name, fmt: [struct.unpack_from(fmt, d, parts[name][0] + k * struct.calcsize(fmt))
                                 for k in range(parts[name][1] // struct.calcsize(fmt))]
        self.phdr = rec(b'phdr', '<20sHHHIII')
        self.pbag, self.ibag = rec(b'pbag', '<HH'), rec(b'ibag', '<HH')
        self.pgen, self.igen = rec(b'pgen', '<Hh'), rec(b'igen', '<Hh')
        self.inst = rec(b'inst', '<20sH')
        self.shdr = rec(b'shdr', '<20sIIIIIBbHH')

    def presets(self):
        """-> {(bank, program): name}"""
        return {(b, p): n.split(b'\0')[0].decode('latin-1') for n, p, b, *_ in self.phdr[:-1]}

    @staticmethod
    def _gens(bags, gens, first, last):
        """The zones of bags first..last-1: [{gen: value}]; ranges as (lo, hi), the rest signed shorts."""
        zones = []
        for k in range(first, last):
            g0, g1 = bags[k][0], bags[k + 1][0]
            z = {}
            for op, amount in gens[g0:g1]:
                z[op] = (amount & 0xFF, (amount >> 8) & 0xFF) if op in _RANGES else amount
            zones.append(z)
        return zones

    @functools.lru_cache(maxsize=None)
    def zones(self, bank, program):
        """The preset's playable zones, preset and instrument levels combined: [{gen: value}] with SAMPLE_ID."""
        k = next(i for i, h in enumerate(self.phdr[:-1]) if h[1] == program and h[2] == bank)
        pz = self._gens(self.pbag, self.pgen, self.phdr[k][3], self.phdr[k + 1][3])
        pglobal = pz[0] if pz and INSTRUMENT not in pz[0] else {}
        out = []
        for p in pz:
            if INSTRUMENT not in p:
                continue
            i = p[INSTRUMENT]
            iz = self._gens(self.ibag, self.igen, self.inst[i][1], self.inst[i + 1][1])
            iglobal = iz[0] if iz and SAMPLE_ID not in iz[0] else {}
            for z in iz:
                if SAMPLE_ID not in z:
                    continue
                zone = dict(iglobal)
                zone.update(z)
                for op, v in list({**pglobal, **p}.items()):           # preset values add to the instrument's
                    if op in _RANGES:
                        lo, hi = zone.get(op, (0, 127))
                        zone[op] = (max(lo, v[0]), min(hi, v[1]))
                    elif op not in (INSTRUMENT, SAMPLE_ID):
                        zone[op] = zone.get(op, _ENV_DEFAULT.get(op, 0)) + v
                out.append(zone)
        return out

    def note(self, bank, program, midi, dur, vel=0.7, release=None):
        """-> (n, 2) float at RATE: every zone that plays this key at this velocity, summed (a stereo pair is two
        zones, panned)."""
        key, v = int(round(midi)), int(np.clip(round(vel * 127), 1, 127))
        hits = [z for z in self.zones(bank, program)
                if z.get(KEY_RANGE, (0, 127))[0] <= key <= z.get(KEY_RANGE, (0, 127))[1]
                and z.get(VEL_RANGE, (0, 127))[0] <= v <= z.get(VEL_RANGE, (0, 127))[1]]
        if not hits:                                   # out of range: the nearest zone's key
            zs = self.zones(bank, program)
            hits = [min(zs, key=lambda z: min(abs(key - z.get(KEY_RANGE, (0, 127))[0]),
                                               abs(key - z.get(KEY_RANGE, (0, 127))[1])))]
        parts = [self._zone(z, midi, dur, release) for z in hits]
        n = max(len(p) for p in parts)
        out = np.zeros((n, 2))
        for p in parts:
            out[:len(p)] += p
        return out

    def _zone(self, z, midi, dur, release):
        name, start, end, ls, le, rate, orig, corr, _, _ = self.shdr[z[SAMPLE_ID]]
        start += z.get(START, 0) + 32768 * z.get(START_COARSE, 0)
        end += z.get(END, 0) + 32768 * z.get(END_COARSE, 0)
        ls += z.get(LOOP_START, 0) + 32768 * z.get(LOOP_START_COARSE, 0)
        le += z.get(LOOP_END, 0) + 32768 * z.get(LOOP_END_COARSE, 0)
        root = z.get(ROOT_KEY, -1)
        root = orig if root < 0 else root
        cents = (midi - root) * z.get(SCALE_TUNING, 100) + 100 * z.get(COARSE_TUNE, 0) + z.get(FINE_TUNE, 0) + corr
        step = 2 ** (cents / 1200) * rate / RATE
        tc = lambda op: 2 ** (z.get(op, _ENV_DEFAULT[op]) / 1200)
        rel = tc(RELEASE) if release is None else release
        n = int((dur + min(rel, 3.0)) * RATE)
        loops = z.get(SAMPLE_MODES, 0) & 1 and le > ls + 8
        pos = np.arange(n) * step
        if loops:
            body = ls - start
            span = le - ls
            pos = np.where(pos < body, pos, body + np.mod(pos - body, span))
        else:
            pos = pos[pos < end - start - 1]
        src = self.smpl[start:end + 2].astype(np.float64) / 32768
        i = pos.astype(np.int64)
        frac = pos - i
        x = src[i] * (1 - frac) + src[np.minimum(i + 1, len(src) - 1)] * frac
        x *= self._envelope(z, len(x), dur, rel)
        x *= 10 ** (-z.get(ATTENUATION, 0) * 0.4 / 200)            # centibels (the 0.4 most players use)
        pan = np.clip(z.get(PAN, 0) / 500, -1, 1)
        return np.stack([x * np.sqrt((1 - pan) / 2), x * np.sqrt((1 + pan) / 2)], axis=1) * np.sqrt(2)

    @staticmethod
    def _envelope(z, n, dur, rel):
        tc = lambda op: 2 ** (z.get(op, _ENV_DEFAULT[op]) / 1200)
        t = np.arange(n) / RATE
        delay, attack, hold, decay = tc(DELAY), tc(ATTACK), tc(HOLD), tc(DECAY)
        sus_db = -min(max(z.get(SUSTAIN, 0), 0), 1440) / 10
        db = np.zeros(n)
        a0, h0, d0 = delay, delay + attack, delay + attack + hold
        lin = np.clip((t - a0) / max(attack, 1e-4), 0, 1)
        in_decay = np.clip((t - d0) / max(decay, 1e-4), 0, 1)       # the full fall (100 dB) takes `decay`
        db = np.maximum(-100 * in_decay, sus_db) * (t >= d0)
        env = 10 ** (db / 20) * np.where(t < h0, lin, 1.0) * (t >= a0)
        off = t >= dur                                              # release: -100 dB over `rel`
        if off.any():
            at_off = env[np.argmax(off)]
            env = np.where(off, at_off * 10 ** (-100 * np.clip((t - dur) / max(rel, 1e-3), 0, 1) / 20), env)
        return env


@functools.lru_cache(maxsize=1)
def font():
    return Font()


def available():
    return os.path.exists(FONT)


def main():
    for (b, p), name in sorted(font().presets().items()):
        print(f'{b:3d} {p:3d}  {name}')


if __name__ == '__main__':
    sys.exit(main())
