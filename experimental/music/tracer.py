"""Tracer audio: every music stream replaced by two steady sine tones that spell its index, so a recording of the
game tells exactly which stream played when (no person listening, no fingerprints of real music needed).

  index k -> tone A = 300 + 20 * (k // 27) Hz, tone B = 1000 + 25 * (k % 27) Hz   (k < 27 * 28 = 756)
  plus a short 2500 Hz blip in the first 60 ms of every stream, marking where a stream (re)starts.
"""
import numpy as np

RATE = 22050
A0, A_STEP, B0, B_STEP, PER = 300.0, 20.0, 1000.0, 25.0, 27
BLIP_HZ, BLIP_SEC = 2500.0, 0.06


def tones(k):
    return A0 + A_STEP * (k // PER), B0 + B_STEP * (k % PER)


def stream(k, ms, rate=RATE):
    n = max(128, int(round(ms * rate / 1000)))
    t = np.arange(n) / rate
    fa, fb = tones(k)
    x = 0.22 * np.sin(2 * np.pi * fa * t) + 0.22 * np.sin(2 * np.pi * fb * t)
    blip = t < BLIP_SEC
    x[blip] += 0.3 * np.sin(2 * np.pi * BLIP_HZ * t[blip])
    edge = min(64, n // 4)                       # no click at the ends
    ramp = np.linspace(0, 1, edge)
    x[:edge] *= ramp
    x[-edge:] *= ramp[::-1]
    return (x * 32767 * 0.9).astype(np.int16)


def _two_peaks(s, guard=3):
    k = int(s.argmax())
    rest = np.concatenate([s[:max(0, k - guard)], s[k + guard + 1:]])
    return len(rest) and rest.max() > 0.35 * s[k]


def decode(x, sr, win=0.25, hop=0.125):
    """recording (any rate, mono or stereo) -> [(start s, end s, stream index)] runs, plus blip times [s]."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    n, h = int(win * sr), int(hop * sr)
    w = np.hanning(n)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    band = lambda lo, hi: (freqs >= lo) & (freqs <= hi)
    ba, bb, bblip = band(280, A0 + A_STEP * 28), band(980, B0 + B_STEP * PER), band(2400, 2600)
    rows, blips = [], []
    for s in range(0, len(x) - n, h):
        spec = np.abs(np.fft.rfft(x[s:s + n] * w))
        floor = np.median(spec) + 1e-9
        pa, pb = spec[ba].max(), spec[bb].max()
        t = s / sr
        if spec[bblip].max() > 20 * floor:
            blips.append(t)
        if pa < 20 * floor or pb < 20 * floor:
            rows.append((t, None))
            continue
        if _two_peaks(spec[ba]) or _two_peaks(spec[bb]):        # straddles two streams
            rows.append((t, None))
            continue
        fa, fb = freqs[ba][spec[ba].argmax()], freqs[bb][spec[bb].argmax()]
        i, j = int(round((fa - A0) / A_STEP)), int(round((fb - B0) / B_STEP))
        rows.append((t, i * PER + j if 0 <= i < 28 and 0 <= j < PER else None))
    runs = []
    for t, k in rows:
        if runs and runs[-1][2] == k:
            runs[-1][1] = t + win
        else:
            runs.append([t, t + win, k])
    merged = []
    for b in blips:
        if not merged or b - merged[-1] > 0.3:
            merged.append(b)
    return [tuple(r) for r in runs if r[2] is not None and r[1] - r[0] >= win], merged
