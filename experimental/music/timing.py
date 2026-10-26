"""Jump timing from a recording of the music bench mission (experimental/cnv/missions/music_bench.py, built with
the ownmap.timing map): when each scripted event was heard, against when the script fired it.

  python -I -X utf8 experimental/music/timing.py <recording.wav>

The recording's clock and the mission's are not the same: the mission's 0 is taken as when SetPlayerAllied was
heard (the game fires it as the mission starts, a cut). Each jump is then shown with its latency and, for the
section it left, how far into that section's segment it came (0 = on a segment's end: the jump waited for it).
"""
import os
import sys

import numpy as np
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experimental.music import extract, ownmap, tracer  # noqa: E402


def schedule():
    """[(mission seconds, kind)] from the mission's published facts ('<kind> <n>' = seconds)."""
    sys.path.insert(0, os.path.join(ROOT, 'experimental', 'cnv'))
    import parts  # noqa: F401  (puts experimental/campaign on the path, which the maps import from)
    from missions import music_bench
    return sorted((t, k.split()[0]) for k, t in music_bench.mission().facts.items())


def onsets(x, sr):
    """[(start s, stream)] of every tracer run, its start moved to the stream-start blip just before it if any."""
    runs, blips = tracer.decode(x, sr, win=0.12, hop=0.03)
    out = []
    for a, _, k in runs:
        if out and out[-1][1] == k:
            continue
        near = [b for b in blips if a - 0.35 <= b <= a + 0.05]
        out.append((near[-1] if near else a, k))
    return out


def main():
    sr, x = wavfile.read(sys.argv[1])
    x = x.astype(np.float64)
    x = x.mean(axis=1) if x.ndim > 1 else x
    x *= 8000 / max(np.abs(x).max(), 1)
    base = extract.retail_map()
    names = [e.name for e in base.events]
    _, lengths = ownmap.timing(base)
    stream = {kind: names.index(e) for kind, e in ownmap.TIMING.items()}
    A = len(names)
    heard = onsets(x, sr)
    print('heard:', ', '.join(f'{t:.2f}s k{k}' for t, k in heard))
    start0 = next(t for t, k in heard if k == names.index('SetPlayerAllied'))
    print(f"mission 0 = SetPlayerAllied heard at {start0:.2f} s")
    rows, at = [], 0
    for fired, kind in schedule():
        hit = next((i for i, (t, k) in enumerate(heard) if i >= at and k == stream[kind]), None)
        if hit is None:
            print(f'  {fired:5.1f}s {kind:5s}: not heard')
            continue
        at = hit
        via = at > 0 and heard[at - 1][1] == A and heard[at][0] - heard[at - 1][0] < 2.0
        j = at - 1 if via else at                              # a transition first: the jump began with it
        start = heard[j][0]
        left_at, left = heard[j - 1] if j else (None, None)    # the section the jump left, and when it began
        seg = lengths[left] / 1000 if left is not None and left < len(lengths) else None
        phase = (start - left_at) % seg if seg else None
        phase = min(phase, seg - phase) if seg else None       # distance from the nearest segment end
        latency = start - start0 - fired
        rows.append((kind, latency))
        print(f'  {fired:5.1f}s {kind:5s}: heard {start:6.2f}s, latency {latency:+.2f} s'
              + (f', {phase:.2f} s from a segment end of k{left} ({seg:g} s)' if seg else '')
              + (', through transition A' if via else ''))
        at += 1
    for kind in ownmap.TIMING:
        d = [lat for k, lat in rows if k == kind]
        if d:
            print(f'{kind}: {len(d)} jumps, latency {min(d):+.2f} .. {max(d):+.2f} s')


if __name__ == '__main__':
    main()
