"""Hear what the game plays, without a person listening: record the speakers (WASAPI loopback) and name the music
streams in the recording by matching band-energy fingerprints against known audio (Shazam-style offset voting).

  python -I experimental/music/listen.py index             fingerprint work/music/retail/wav/*.wav -> index.npz
  python -I experimental/music/listen.py record-game <sec> <out.wav>   only the game process (start the bench too)
  python -I experimental/music/listen.py record <sec> <out.wav>        the whole speaker mix
  python -I experimental/music/listen.py identify <in.wav> [index.npz]   -> one line per matched stretch
"""
import os
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from experimental.campaign import labpaths  # noqa: E402

RATE = 11025
N_FFT, HOP = 1024, 512                      # 46 ms hop
BANDS = np.unique(np.geomspace(4, N_FFT // 2, 33).astype(int))
RETAIL_INDEX = os.path.join(labpaths.WORK, 'music', 'retail', 'index.npz')


def to_mono_rate(x, sr):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr == 44100:
        return resample_poly(x, 1, 4)
    return resample_poly(x, RATE, sr)


def fingerprint(x):
    """mono RATE audio -> frames x bands, each frame zero mean / unit norm over bands (loudness-free)."""
    if len(x) < N_FFT:
        x = np.pad(x, (0, N_FFT - len(x)))
    n = 1 + (len(x) - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n)[:, None]
    spec = np.abs(np.fft.rfft(x[idx] * np.hanning(N_FFT), axis=1)) ** 2
    e = np.log1p(np.add.reduceat(spec, BANDS[:-1], axis=1))
    e -= e.mean(axis=1, keepdims=True)
    e /= np.linalg.norm(e, axis=1, keepdims=True) + 1e-6
    return e.astype(np.float32)


def build_index(wav_dir, out):
    frames, owner, pos = [], [], []
    files = sorted(f for f in os.listdir(wav_dir) if f.endswith('.wav'))
    for f in files:
        sr, x = wavfile.read(os.path.join(wav_dir, f))
        fp = fingerprint(to_mono_rate(x, sr))
        frames.append(fp)
        owner.append(np.full(len(fp), int(f[:-4]), np.int32))
        pos.append(np.arange(len(fp), dtype=np.int32))
    np.savez(out, frames=np.concatenate(frames), owner=np.concatenate(owner), pos=np.concatenate(pos))
    print(len(files), 'streams,', sum(len(a) for a in frames), 'frames ->', out)


def identify(x, sr, index=RETAIL_INDEX, chunk_sec=2.0):
    """-> [(start sec, end sec, stream, offset sec into the stream, votes)] for each chunk of the recording."""
    z = np.load(index)
    frames, owner, pos = z['frames'], z['owner'], z['pos']
    fp = fingerprint(to_mono_rate(x, sr))
    step = int(chunk_sec * RATE / HOP)
    out = []
    for s in range(0, len(fp) - step + 1, step):
        q = fp[s:s + step]
        if np.abs(q).sum() == 0:
            continue
        sims = q @ frames.T                                   # step x all frames
        best = np.argsort(sims, axis=1)[:, -5:]               # 5 nearest frames per query frame
        votes = {}
        for k in range(step):
            for j in best[k]:
                key = (int(owner[j]), int(pos[j]) - k)
                votes[key] = votes.get(key, 0) + 1
        (stream, off), v = max(votes.items(), key=lambda kv: kv[1])
        out.append((s * HOP / RATE, (s + step) * HOP / RATE, stream, off * HOP / RATE, v))
    return out


CAPTURE_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'proc_capture.cs')
CAPTURE_EXE = os.path.join(labpaths.WORK, 'music', 'tools', 'proc_capture.exe')
SESSIONS_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio_sessions.cs')
SESSIONS_EXE = os.path.join(labpaths.WORK, 'music', 'tools', 'audio_sessions.exe')
CSC = r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'


def _tool(src, exe):
    import subprocess
    if not os.path.exists(exe) or os.path.getmtime(exe) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(exe), exist_ok=True)
        subprocess.run([CSC, '-nologo', '-optimize', '-out:' + exe, src], check=True)


def _foreground_pid():
    import ctypes
    from ctypes import wintypes
    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(ctypes.windll.user32.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value


def _tell_active(pid):
    """Post 'you are active' to the game's windows (messages only, nothing is raised): out of focus the game plays
    no music at all (the bench's keys have the same trouble, see run_bench.ps1 Key)."""
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(h, _):
        p = wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(h):
            found.append(h)
        return True
    u.EnumWindows(each, 0)
    for h in found:
        u.PostMessageW(h, 0x001C, 1, 0)       # WM_ACTIVATEAPP
        u.PostMessageW(h, 0x0006, 1, 0)       # WM_ACTIVATE, WA_ACTIVE
        u.PostMessageW(h, 0x0007, 0, 0)       # WM_SETFOCUS
    return len(found)


def record_game(seconds, out, wait=90, volume=0.03):
    """Wait for the game process (RA3_*.game, as run_bench.ps1 starts it), then record only what it plays, its
    sessions at `volume` (a whisper on the user's speakers; the tracer tones survive it)."""
    import subprocess
    import time
    _tool(CAPTURE_SRC, CAPTURE_EXE)
    _tool(SESSIONS_SRC, SESSIONS_EXE)
    t0 = time.time()
    while True:
        rows = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], capture_output=True, text=True, errors='replace').stdout
        pids = [int(r.split('","')[1]) for r in rows.splitlines() if r.lower().startswith('"ra3_') and '.game"' in r.lower()]
        if pids:
            break
        if time.time() - t0 > wait:
            sys.exit('no game process appeared')
        time.sleep(0.5)
    print('game pid', pids[0], 'after', round(time.time() - t0, 1), 's')
    cap = subprocess.Popen([CAPTURE_EXE, str(pids[0]), str(seconds), out])
    # the loopback hears the game only through its sessions' mute and volume (and Windows keeps those per program:
    # the bench mutes them): unmute at a whisper while recording, then leave them as the bench does (muted)
    # every 2 s the peak meter of each of its sessions (one per output device): shows where the game sends sound,
    # which the process loopback may not hear (a game controller is a speaker too)
    shown, meters, t_cap = False, [], time.time()
    while cap.poll() is None:
        r = subprocess.run([SESSIONS_EXE, str(pids[0]), 'set', str(volume), '0'], capture_output=True, text=True,
                           errors='replace')
        active = [l for l in r.stdout.splitlines() if 'state 1' in l]
        _tell_active(pids[0])
        if not shown and time.time() - t0 > 15:
            print('game sessions playing:', active or 'none')
            shown = True
        meters.append((time.time() - t_cap, _foreground_pid() == pids[0],
                       [(l.split('|')[0].strip()[:24], l.rsplit('peak', 1)[-1].strip()) for l in active]))
        time.sleep(2)
    for t, front, m in meters[::5]:
        print(f'  sessions at {t:4.0f} s:', ', '.join(f'{d} peak {p}' for d, p in m) or 'none')
    back = [round(t) for t, front, _ in meters if not front]
    print('  game window in front the whole time' if not back else f'  game window NOT in front at {back} s')
    subprocess.run([SESSIONS_EXE, str(pids[0]), 'set', '1', '1'], capture_output=True)
    if cap.returncode:
        sys.exit(f'capture failed ({cap.returncode})')


def record(seconds, out):
    """Everything the speakers play (other programs too); record_game is the clean one."""
    import soundcard as sc
    spk = sc.default_speaker()
    mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
    data = mic.record(samplerate=44100, numframes=int(44100 * seconds))
    wavfile.write(out, 44100, (np.clip(data, -1, 1) * 32767).astype(np.int16))
    print('recorded', seconds, 's from', spk.name, '->', out, 'peak', float(np.abs(data).max()))


def main():
    cmd = sys.argv[1]
    if cmd == 'index':
        build_index(os.path.join(labpaths.WORK, 'music', 'retail', 'wav'), RETAIL_INDEX)
    elif cmd == 'record':
        record(float(sys.argv[2]), sys.argv[3])
    elif cmd == 'record-game':
        record_game(float(sys.argv[2]), sys.argv[3])
    elif cmd == 'identify':
        sr, x = wavfile.read(sys.argv[2])
        for a, b, stream, off, v in identify(x, sr, *(sys.argv[3:4] or [RETAIL_INDEX])):
            print(f'{a:6.1f}-{b:6.1f}s  stream {stream:3d} at {off:7.1f}s  votes {v}')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
