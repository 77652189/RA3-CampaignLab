"""Trial (2026-11-08): can MiniMax Music 3, a local text-to-music model, stand in for our score + synth.py?

Generates A4's 布防 (prep) and 交战·激烈 (fierce) from text through the voice line's ComfyUI (headless, API only:
nothing is previewed or played), then measures the takes the way a4.py measures its own sections: the tempo against
a4's 96 BPM grid, whether a loop of whole 2-bar segments (5 s) can be cut with no seam, and the long-term spectrum
against retail's (a4.REFERENCE), next to a4.render() of the same section.

  ComfyUI first (its own venv, a port of our own, 6 GB left to the others = the 10 GB of shared/gpu_limit.json):
    third_party/comfyui/.venv/Scripts/python.exe main.py --listen 127.0.0.1 --port 8189 --reserve-vram 6
                                                          --disable-auto-launch
  python -I -X utf8 experimental/music/music3_probe.py gen [tag ...]   -> work/music/music3/gen/<tag>.wav, runs.json
  python -I -X utf8 experimental/music/music3_probe.py measure         -> work/music/music3/report.txt, loops/,
                                                                          compare/ (a take and a4's, same loudness)
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LAB = os.path.dirname(ROOT)
COMFY = os.path.join(LAB, 'RA3-ChineseVoice', 'third_party', 'comfyui')
FFMPEG = os.path.join(LAB, 'RA3-ChineseVoice', 'third_party', 'ffmpeg', 'ffmpeg.exe')
OUT = os.path.join(ROOT, 'work', 'music', 'music3')
URL = 'http://127.0.0.1:8189'
GPU_LIMIT = os.path.join(LAB, 'shared', 'gpu_limit.json')

BPM, SEG = 96, 5.0                     # a4.py: 96 BPM, a segment is 2 bars = 5 s

_NO_VOX = 'Vocal Details: No vocals at all, no choir, no humming. Purely instrumental.'
CAPTIONS = {
    'fierce': (
        'Global Metadata: Orchestral rock battle music for a real-time strategy video game, instrumental only. '
        '96 BPM, D minor, strict steady tempo, four-four time. Triumphant, driving and relentless: the Allied '
        'forces are winning the battle. Loopable game score: the same high energy from the first second to the '
        'last, no intro, no build-up, no breakdown, no ending. Big modern film-score production, punchy and wide.\n'
        + _NO_VOX + '\n'
        'Arrangement: Double-time rock drum kit with a hard snare backbeat and driving eighth-note hi-hats, '
        'distorted electric guitar palm-muted riff on a low D, electric bass locked to the kick, a heroic march '
        'melody on trumpets and French horns, pulsing sixteenth-note synth arpeggios, a fast string ostinato, '
        'brass chord stabs. The same full band throughout.'),
    'prep': (
        'Global Metadata: Tense, cold ambient underscore for a real-time strategy video game, instrumental only. '
        '96 BPM, D minor, slow and steady, four-four time. Quiet suspense while troops dig in at a frozen harbour '
        'before an ambush: icy, still, watchful. Loopable game score: the same low energy from the first second to '
        'the last, no intro, no climax, no ending. Cinematic, soft and spacious.\n'
        + _NO_VOX + '\n'
        'Arrangement: Sustained dark synth pads and soft low strings on a D drone, sparse celesta and music-box '
        'notes like falling ice, a Japanese koto plucking a short phrase in the in scale (D, E flat, G, A, B flat) '
        'heard only in passing, a muffled taiko heartbeat on beats one and three, a cold wind texture. Very sparse, '
        'lots of space.'),
}
LYRICS = '[Instrumental]\n[Instrumental]\n[Instrumental]\n[Instrumental]'
# tag: (section, seed, seconds)
TAKES = {f'{s}_{i}': (s, seed, 40.0) for s in CAPTIONS for i, seed in enumerate((11, 22, 33), 1)}


def _by_file(name, path, package=False):
    """A module (or a package, whose submodules then import normally) loaded by file: this script adds nothing to
    sys.path (tests/test_architecture.py G4 only lets the count of files that edit it go down)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        name, path, submodule_search_locations=[os.path.dirname(path)] if package else None)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _repo():
    """`from experimental.music import ...` needs the repo root on sys.path; a4.py puts it there itself when it is
    loaded, so load it by file once instead of editing the path here."""
    if 'a4_boot' not in sys.modules:
        _by_file('a4_boot', os.path.join(HERE, 'a4.py'))


# --- generating ------------------------------------------------------------------------------------------------
def _post(path, obj):
    req = urllib.request.Request(URL + path, json.dumps(obj).encode(), {'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def _get(path):
    return json.loads(urllib.request.urlopen(URL + path, timeout=60).read())


def _vram_mib():
    out = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                         capture_output=True, text=True).stdout
    return int(out.split()[0])


def _limit():
    try:
        with open(GPU_LIMIT, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def prompt(tag):
    """The official template (Comfy-Org workflow_templates audio_minimax_music_3), as an API prompt, saving flac."""
    section, seed, seconds = TAKES[tag]
    return {
        '3': {'class_type': 'CLIPLoader', 'inputs': {
            'clip_name': 'minimax_music3_text_encoder_pruned_int8_convrot.safetensors', 'type': 'minimax',
            'device': 'default'}},
        '6': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'minimax_music3_dit_fp16.safetensors',
                                                     'weight_dtype': 'default'}},
        '7': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'minimax_music3_dav.safetensors'}},
        '13': {'class_type': 'MiniMaxMusic3TextEncode', 'inputs': {
            'clip': ['3', 0], 'caption': CAPTIONS[section], 'lyrics': LYRICS, 'seed': seed,
            'max_duration': seconds, 'cfg_scale': 1.7, 'top_k': 50}},
        '10': {'class_type': 'ConditioningZeroOut', 'inputs': {'conditioning': ['13', 0]}},
        '15': {'class_type': 'EmptyMiniMaxMusic3LatentAudio', 'inputs': {'seconds': ['13', 1], 'batch_size': 1}},
        '9': {'class_type': 'KSampler', 'inputs': {
            'model': ['6', 0], 'positive': ['13', 0], 'negative': ['10', 0], 'latent_image': ['15', 0],
            'seed': seed, 'steps': 30, 'cfg': 1.7, 'sampler_name': 'euler', 'scheduler': 'simple', 'denoise': 1.0}},
        '12': {'class_type': 'VAEDecodeAudioTiled', 'inputs': {'samples': ['9', 0], 'vae': ['7', 0],
                                                               'tile_size': 1536, 'overlap': 64}},
        '35': {'class_type': 'SaveAudio', 'inputs': {'audio': ['12', 0], 'filename_prefix': f'music3/{tag}'}},
    }


def generate(tag):
    """-> {seconds, vram_peak_mib, vram_base_mib, wav}: one take, timed, the GPU's memory polled meanwhile."""
    base = _vram_mib()
    peak, done = [base], threading.Event()

    def poll():
        while not done.is_set():
            peak.append(_vram_mib())
            time.sleep(0.5)
    threading.Thread(target=poll, daemon=True).start()
    t0 = time.time()
    pid = _post('/prompt', {'prompt': prompt(tag)})['prompt_id']
    while True:
        h = _get('/history/' + pid)
        if pid in h and h[pid].get('status', {}).get('completed') is not None:
            break
        time.sleep(1)
    secs = time.time() - t0
    done.set()
    entry = h[pid]
    if entry['status'].get('status_str') != 'success':
        msgs = [m for m in entry['status'].get('messages', []) if m[0] == 'execution_error']
        raise RuntimeError(f'{tag}: {msgs[-1][1].get("exception_message") if msgs else entry["status"]}')
    a = next(a for o in entry['outputs'].values() for a in o.get('audio', []))
    src = os.path.join(COMFY, 'output', a.get('subfolder', ''), a['filename'])
    os.makedirs(os.path.join(OUT, 'gen'), exist_ok=True)
    shutil.copy(src, os.path.join(OUT, 'gen', tag + '.flac'))
    wav = os.path.join(OUT, 'gen', tag + '.wav')
    subprocess.run([FFMPEG, '-y', '-v', 'error', '-i', src, '-ar', '44100', '-ac', '2', '-c:a', 'pcm_s16le', wav],
                   check=True)
    return {'seconds': round(secs, 1), 'vram_peak_mib': max(peak), 'vram_base_mib': base, 'wav': wav}


def main_gen(tags):
    path = os.path.join(OUT, 'runs.json')
    runs = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    for tag in tags or list(TAKES):
        try:
            r = generate(tag)
        except Exception as e:          # noqa: BLE001 -- note it and go on with the next take
            r = {'error': str(e)[:500]}
        runs[tag] = r
        os.makedirs(OUT, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(runs, f, indent=1, ensure_ascii=False)
        print(tag, r, flush=True)
        duty = float(_limit().get('duty', 1.0))           # shared/gpu_limit.json: rest (1/duty - 1) x the work
        if 'seconds' in r and 0 < duty < 1:
            time.sleep(r['seconds'] * (1 / duty - 1))


# --- measuring -------------------------------------------------------------------------------------------------
RATE = 44100
HOP = 512
FPS = RATE / HOP


def load(path):
    from scipy.io import wavfile
    sr, x = wavfile.read(path)
    assert sr == RATE, (path, sr)
    x = x.astype(float) / 32768 if x.dtype == np.int16 else x.astype(float)
    return x if x.ndim == 2 else np.stack([x, x], axis=1)


def _frames(x, n=2048):
    m = x.mean(axis=1)
    idx = np.arange(0, len(m) - n, HOP)
    win = np.hanning(n)
    return np.abs(np.fft.rfft(np.stack([m[i:i + n] * win for i in idx]), axis=1))


def onsets(x):
    """Spectral flux: the rise of log magnitude summed over frequency, per frame (FPS)."""
    s = np.log1p(100 * _frames(x))
    o = np.maximum(np.diff(s, axis=0), 0).sum(axis=1)
    o = o - np.convolve(o, np.ones(16) / 16, 'same')
    return np.maximum(o, 0)


def tempo(o, lo=60, hi=200):
    """-> (BPM, strength): the autocorrelation peak of an onset envelope, beats folded into 72..144."""
    o = o - o.mean()
    ac = np.correlate(o, o, 'full')[len(o) - 1:]
    ac /= ac[0] + 1e-12
    bpms = np.arange(lo, hi, 0.1)
    lag = 60 / bpms * FPS
    v = np.interp(lag, np.arange(len(ac)), ac) + 0.5 * np.interp(2 * lag, np.arange(len(ac)), ac)
    b = bpms[np.argmax(v)]
    while b >= 144:
        b /= 2
    while b < 72:
        b *= 2
    return float(b), float(v.max())


def grid_phase(o, bpm=BPM, window=SEG):
    """The phase (ms, within a beat) of the onsets against a fixed `bpm` grid, per `window` of seconds: if the take
    keeps that tempo the phase stays put; a slope is a different tempo, scatter is a wandering one."""
    beat = 60 / bpm * FPS
    w = int(window * FPS)
    out = []
    for i in range(0, len(o) - w + 1, w // 2):
        seg = o[i:i + w]
        ang = 2 * np.pi * (np.arange(i, i + w) % beat) / beat
        z = (seg * np.exp(1j * ang)).sum() / (seg.sum() + 1e-12)
        out.append((i / FPS, float(np.angle(z) % (2 * np.pi) / (2 * np.pi) * 60 / bpm * 1000), float(abs(z))))
    return out


def _unwrap_ms(ph, beat_ms):
    return np.unwrap(np.array(ph) / beat_ms * 2 * np.pi) / (2 * np.pi) * beat_ms


def bands_db(x, n=2048):
    """Third-octave band energy (synth.BANDS), dB, per frame."""
    _repo()
    from experimental.music import synth
    spec = _frames(x, n) ** 2
    f = np.fft.rfftfreq(n, 1 / RATE)
    edge = synth.BANDS * 2 ** (1 / 6)
    lo = np.concatenate([[synth.BANDS[0] / 2 ** (1 / 6)], edge[:-1]])
    return 10 * np.log10(np.stack([spec[:, (f >= a) & (f < b)].sum(axis=1) for a, b in zip(lo, edge)], axis=1)
                         + 1e-10)


def seam(feat, start, period, probe=0.5):
    """How different the music is `period` frames on, over `probe` s from `start` (mean |dB|, bands 50 Hz..8 kHz):
    a loop [start, start + period) plays its head where the take would have gone on; 0 = the same."""
    p = int(probe * FPS)
    a, b = feat[start:start + p, 3:25], feat[start + period:start + period + p, 3:25]
    return float(np.abs(a - b).mean())


def best_loop(x, segs, skip=2.0):
    """The cut of `segs` whole segments (5 s each) whose seam is smallest, starts on a 96 BPM beat of the take's own
    grid: -> (start s, seam dB, median seam dB of all starts)."""
    feat = bands_db(x)
    o = onsets(x)
    beat = 60 / BPM * FPS
    period = int(round(segs * SEG * FPS))
    ph = np.median([p for _, p, _ in grid_phase(o)]) / 1000 * FPS
    starts = np.arange(int(skip * FPS) + ph, len(feat) - period - int(0.5 * FPS) - int(skip * FPS), beat)
    if len(starts) == 0:
        return None
    scores = [seam(feat, int(round(s)), period) for s in starts]
    i = int(np.argmin(scores))
    return float(starts[i] / FPS), float(scores[i]), float(np.median(scores))


def cut_loop(x, start, segs, xfade=0.01):
    """x[start : start + segs x 5 s], its last 10 ms blended with what came just before the start, so the end runs
    into the head with no click."""
    a, n, f = int(round(start * RATE)), int(round(segs * SEG * RATE)), int(xfade * RATE)
    y = x[a:a + n].copy()
    r = np.linspace(0, 1, f)[:, None]
    y[-f:] = y[-f:] * np.cos(r * np.pi / 2) + x[a - f:a] * np.sin(r * np.pi / 2)
    return y


def click(y):
    """The step across a loop's end over the 99.9th percentile of steps inside it (test_a4music's measure): <= 1."""
    steps = np.abs(np.diff(y, axis=0)).max(axis=1)
    return float(np.abs(y[0] - y[-1]).max() / (np.percentile(steps, 99.9) + 1e-12))


def spectrum_gap(x, kind):
    """test_a4music's balance test: max |dB| of the smoothed third-octave balance against retail's kind, 50 Hz..8 kHz;
    and side over mid dB against retail's. a4's own sections pass at < 4 dB."""
    _repo()
    from experimental.music import a4, synth
    tilt = lambda v: np.convolve(np.pad(v, 2, mode='edge'), np.array([1, 2, 3, 2, 1]) / 9, 'valid')
    bands, side_mid = a4.REFERENCE[kind]
    got, sm = synth.profile(x)
    d = tilt(got)[3:25] - tilt(np.array(bands))[3:25]
    return float(np.abs(d).max()), float(sm - side_mid), [round(float(v), 1) for v in d]


def rms_db(x):
    return float(10 * np.log10((x ** 2).mean() + 1e-20))


def _write(path, x):
    from scipy.io import wavfile
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wavfile.write(path, RATE, (np.clip(x, -1, 1) * 32767).astype(np.int16))


def measure_one(x, label, kind):
    """-> lines, best (segs, start, seam) for a take or a4's section."""
    o = onsets(x)
    bpm, strength = tempo(o)
    gp = grid_phase(o)
    beat_ms = 60 / BPM * 1000
    ph = _unwrap_ms([p for _, p, _ in gp], beat_ms)
    t = np.array([s for s, _, _ in gp])
    slope = np.polyfit(t, ph, 1)[0] if len(t) > 2 else 0.0          # ms of drift per s against 96 BPM
    resid = float(np.std(ph - np.polyval(np.polyfit(t, ph, 1), t))) if len(t) > 2 else 0.0
    drift_bpm = BPM * (1 - slope / 1000) if slope else BPM          # phase slipping later = slower
    lines = [f'{label}: {len(x) / RATE:.1f} s, RMS {rms_db(x):.1f} dB',
             f'  tempo  {bpm:.1f} BPM (autocorrelation, strength {strength:.2f}); against a 96 grid the beat drifts '
             f'{slope:+.1f} ms/s (= {drift_bpm:.1f} BPM), wanders {resid:.0f} ms (a beat is {beat_ms:.0f} ms)']
    best = None
    for segs in (1, 2, 4):
        if len(x) / RATE < segs * SEG + 5:
            continue
        r = best_loop(x, segs)
        if r is None:
            continue
        start, sc, med = r
        y = cut_loop(x, start, segs)
        lines.append(f'  loop {segs}x5 s  from {start:5.2f} s  seam {sc:4.1f} dB (median of all beat starts '
                     f'{med:4.1f}), click {click(y):.2f}')
        if best is None or sc < best[2]:
            best = (segs, start, sc)
    gap, wide, _ = spectrum_gap(x, kind)
    lines.append(f'  spectrum vs retail {kind!r}: max {gap:.1f} dB off (a4 passes < 4), side/mid {wide:+.1f} dB '
                 f'against retail')
    return lines, best


def main_measure():
    _repo()
    from experimental.music import a4, synth
    kinds = {s: a4.REFERENCE_OF[s] for s in CAPTIONS}
    runs = json.load(open(os.path.join(OUT, 'runs.json'), encoding='utf-8'))
    report = ['MiniMax Music 3 vs a4.py + synth.py, ' + time.strftime('%Y-%m-%d %H:%M'), '']
    report.append('take            gen s   VRAM peak MiB (base)')
    for tag, r in runs.items():
        report.append(f'{tag:14s}  {r.get("seconds", "-"):>6}   {r.get("vram_peak_mib", "-")} '
                      f'({r.get("vram_base_mib", "-")})' + (f'  ERROR {r["error"][:120]}' if 'error' in r else ''))
    report.append('')
    seam_note = ('seam: mean |dB| between the loop head and what the take plays a loop length on, third-octave bands '
                 '50 Hz..8 kHz over 0.5 s; small = the head is where the music would have gone')
    report += [seam_note, '']
    for section in CAPTIONS:
        ref = a4.render(section)                                # a4's own section, as it ships (one pass)
        x2 = np.concatenate([ref, ref])                         # the loop twice: its seam is measured like a take's
        lines, _ = measure_one(x2, f'a4 {section} (RECORDED={a4.RECORDED}, played twice)', kinds[section])
        report += lines + ['']
        _write(os.path.join(OUT, 'compare', f'{section}_a4.wav'), ref)
        picks = []
        for tag in sorted(t for t in runs if t.startswith(section + '_') and 'wav' in runs[t]):
            x = load(runs[tag]['wav'])
            lines, best = measure_one(x, tag, kinds[section])
            report += lines + ['']
            if best:
                segs, start, sc = best
                y = cut_loop(x, start, segs)
                _write(os.path.join(OUT, 'loops', f'{tag}_{segs}x5s.wav'), np.concatenate([y, y, y]))
                picks.append((sc, tag, y))
        if picks:
            sc, tag, y = min(picks)
            rms = a4.SECTIONS[section][2]
            _write(os.path.join(OUT, 'compare', f'{section}_music3.wav'), synth.finish(np.concatenate([y] * 3), rms))
            report.append(f'=> {section}: best take {tag} (seam {sc:.1f} dB); compare/{section}_music3.wav (loop x3) '
                          f'vs compare/{section}_a4.wav, both at {rms} dB RMS')
            report.append('')
    with open(os.path.join(OUT, 'report.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(report) + '\n')
    print('\n'.join(report))


def main_vocals():
    """Is anyone singing? The voice line's Demucs (RA3-ChineseVoice ra3voice.separate, htdemucs) splits each take; the
    vocal stem's level under the mix, and its loudest 2 s. a4's sections are the control: no voice, but a choir (and
    the shakuhachi) leak into the stem too. -> work/music/music3/vocals.txt"""
    _repo()
    _by_file('ra3voice', os.path.join(LAB, 'RA3-ChineseVoice', 'ra3voice', '__init__.py'), package=True)
    from ra3voice import separate
    from experimental.music import a4
    runs = json.load(open(os.path.join(OUT, 'runs.json'), encoding='utf-8'))
    items = [(f'a4 {s}', a4.render(s)) for s in CAPTIONS]
    items += [(t, load(r['wav'])) for t, r in sorted(runs.items()) if 'wav' in r]
    lines = ['vocal stem (htdemucs) under the mix: whole dB, loudest 2 s dB']
    for name, x in items:
        v = separate.vocals(x * 32768, RATE).astype(float) / 32768          # [n, 2] in int16 scale, both ways
        w = 2 * RATE
        loud = max(rms_db(v[i:i + w]) - rms_db(x[i:i + w]) for i in range(0, len(x) - w, w // 2))
        lines.append(f'{name:24s} {rms_db(v) - rms_db(x):6.1f}   {loud:6.1f}')
        print(lines[-1], flush=True)
    with open(os.path.join(OUT, 'vocals.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'measure'
    if cmd == 'gen':
        main_gen(sys.argv[2:])
    elif cmd == 'measure':
        main_measure()
    elif cmd == 'vocals':
        main_vocals()
    else:
        sys.exit(__doc__)
