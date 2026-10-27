"""Run the test bench to the main menu with a mod (or none), record only the game's audio, and say what music
played: retail streams by fingerprint (listen.py) and tracer streams by their tones (tracer.py). Text only.

  python -I -X utf8 experimental/music/bench_listen.py [--nav <mission s>] <seconds> <skudef | retail> [...]
--nav: the bench walks the menus into a mission (run_bench.ps1 -Nav) and stays <mission s> in it; the report then
lists the menu steps with their bench times (seconds from the game's start, as the recording) next to the music.
The bench lock is taken by run_bench.ps1 itself; the game is turned down to -80 dB, nothing anyone hears, and brought back up in the recording (listen.record_game).
"""
import os
import subprocess
import sys
import threading
import time

import numpy as np
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experimental.campaign import labpaths  # noqa: E402
from experimental.music import listen, tracer  # noqa: E402

BENCH = os.path.join(ROOT, 'experimental', 'testbench', 'run_bench.ps1')
OUT = os.path.join(labpaths.WORK, 'music', 'probe')
GAP = 20       # s between runs: a game started right after the last one exited crashed (MSVCR80) twice in a row


def run(mod, seconds, nav=None):
    tag = 'retail' if mod == 'retail' else os.path.splitext(os.path.basename(mod))[0]
    wav = os.path.join(OUT, f'{tag}.wav')
    args = ['pwsh', '-NoProfile', '-File', BENCH, '-Sound', '-Seconds', str(seconds + 8), '-Shots', str(seconds)]
    if nav is not None:
        args = ['pwsh', '-NoProfile', '-File', BENCH, '-Sound', '-Nav', '-Seconds', str(nav), '-Shots', str(nav)]
    if mod != 'retail':
        args += ['-Mod', mod]
    log = []
    bench = threading.Thread(target=lambda: log.append(subprocess.run(args, capture_output=True, text=True,
                                                                     errors='replace').stdout))
    bench.start()
    listen.record_game(seconds, wav)
    bench.join()
    open(os.path.join(OUT, f'{tag}.bench.log'), 'w', encoding='utf-8').write(log[0])
    result = [l for l in log[0].splitlines() if l.startswith(('RESULT', 'ABORT', 'CRASH'))]
    steps = [l for l in log[0].splitlines() if l.startswith('NAV')]
    return tag, wav, result, steps


def report(tag, wav, result, steps):
    sr, x = wavfile.read(wav)
    x = x.astype(np.float64)
    peak = np.abs(x).max()
    print(f'== {tag}: {" ".join(result)}; peak {peak:.0f} of 32767')
    for s in steps:
        print('  ', s)
    if peak < 30:
        print('   silent')
        return
    gain = 8000 / peak
    runs, blips = tracer.decode(x * gain, sr)
    if runs:
        print('   tracer:', ', '.join(f'{a:.1f}-{b:.1f}s stream {k}' for a, b, k in runs[:60]))
        print('   stream starts (blips):', [round(b, 1) for b in blips[:80]])
    hits = [h for h in listen.identify(x * gain, sr) if h[4] >= 15]
    if hits:
        print('   retail:', ', '.join(f'{a:.0f}s stream {k} @{o:.0f}s' for a, b, k, o, v in hits[:30]))
    if not runs and not hits:
        print('   sound, but neither tracer tones nor retail music')


def main():
    argv, nav = sys.argv[1:], None
    if argv[0] == '--nav':
        nav, argv = int(argv[1]), argv[2:]
    seconds = int(argv[0])
    os.makedirs(OUT, exist_ok=True)
    done = []
    for k, m in enumerate(argv[1:]):
        if k:
            time.sleep(GAP)
        done.append(run(m, seconds, nav))
    for d in done:
        report(*d)


if __name__ == '__main__':
    main()
