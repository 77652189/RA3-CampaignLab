"""Music probe mod: the retail Pathfinder map with one change, spliced into the retail static stream (SDK mod
overrides by id do not reach the game, see experimental/campaign/splice_assets.py).

  python -I -X utf8 experimental/music/probe_mod.py menu-to <node>
      MenuTrack (the shell's music event) jumps to <node> whatever the shell track variable says.
  python -I -X utf8 experimental/music/probe_mod.py tracer
      the retail map untouched in its logic, every stream replaced by tracer tones of the same length (new .mus
      files written by us, EA-XAS): listen.py + tracer.decode then read off which stream played when.
  python -I -X utf8 experimental/music/probe_mod.py retail
      the retail map spliced back unchanged (control for the splice itself)
  python -I -X utf8 experimental/music/probe_mod.py repack | xas44 | xas22
      why the tracer mod is silent, one cause each (see REMIX): retail audio in .mus files written by us with
      our ids; retail directory with the menu streams as EA-XAS 44.1 kHz stereo; the same at 22.05 kHz mono
  python -I -X utf8 experimental/music/probe_mod.py spy
      our own map (ownmap.spy): every event jumps to a looping tracer of its own index, through a transition
      when it leaves MenuTrack's section
  -> Documents\\Red Alert 3\\Mods\\Mus<Kind>\\Mus<Kind>_1.0.skudef (run_bench.ps1 -Mod <that> -Sound)
"""
import os
import shutil
import struct
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'campaign'))
import splice_assets                                      # noqa: E402
from experimental.campaign import labpaths                # noqa: E402
from experimental.music import extract, mus, ownmap, pack, pfdx, tracer  # noqa: E402
from ra3voice import big                                  # noqa: E402

SDK = labpaths.SDK3
# short names: MusicProbeRetail / MusicProbeTracer (16 letters) crashed the game a second after start, every time
# (MSVCR80.dll, 0xC000000D invalid parameter), the same data as MusicProbeMenu (14) ran; letters and
# digits only to be safe (docs/plan.md, "mod 名最多 15 个字符")
NAMES = {'menu-to': 'MusMenu', 'tracer': 'MusTracer', 'retail': 'MusRetail', 'repack': 'MusRepack',
         'xas44': 'MusXas44', 'xas22': 'MusXas22', 'spy': 'MusSpy'}
# kind: (streams swapped for tracers, None = all; rate; channels; our ids and checksums instead of retail's)
MENU_STREAMS = range(13)            # what the shell plays first (retail: stream 4 from ~22 s)
REMIX = {'tracer': (None, 22050, 1, True),
         'repack': ((), 44100, 2, True),            # retail audio, only our directory ids / checksums
         'xas44': (MENU_STREAMS, 44100, 2, False),  # retail directory, menu streams EA-XAS like retail's rate
         'xas22': (MENU_STREAMS, 22050, 1, False)}


def src_dir(name):
    return os.path.join(SDK, 'Mods', name, 'data')


def built_dir(name):
    return os.path.join(SDK, 'BuiltMods', 'mods', name.lower(), 'data')


def game_running():
    out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
    return 'ra3_1.' in out or 'ra3.exe' in out or 'ra3ep1' in out


def out_dir(name):
    """Documents\\Red Alert 3\\Mods\\<name>, or work\\staging\\<name> while the game runs (nothing is written to
    Mods then; move it over before the bench run)."""
    if game_running():
        return os.path.join(labpaths.WORK, 'staging', name)
    return os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', name)
RETAIL = os.path.join(labpaths.WORK, 'music', 'retail')
GOTO = 0x00030400          # action word 1 of "go to node" (bytes 00 04 03 00)


retail_map = extract.retail_map


def menu_to(m, node):
    """Every go-to action of MenuTrack now goes to `node` (arg word: u16 node, u8 0xFF, u8 0)."""
    ev = next(e for e in m.events if e.name == 'MenuTrack')
    changed = 0
    for k, (w0, w1, w2) in enumerate(ev.actions):
        if w1 == GOTO:
            ev.actions[k] = (w0, w1, (w2 & 0xFFFF0000) | node)
            changed += 1
    return f'MenuTrack: {changed} go-to actions -> node {node}'


_tracer_stream, TRACKS = pack.tracer_stream, pack.TRACKS


def remix_tracks(m, replace, rate, channels, own_ids):
    """The retail streams, those in `replace` (global stream index) swapped for tracer tones of the same length in
    EA-XAS at rate / channels, written as two new .mus files; the map's track entries and sample table follow
    them. own_ids: our directory ids and checksums instead of retail's. Returns {asset name: .mus bytes}."""
    out, table = {}, []
    for t, (name, file) in enumerate(TRACKS):
        data = open(os.path.join(RETAIL, file), 'rb').read()
        raw = mus.raw_streams(data)
        first = struct.unpack_from('<I', m.tracks[t], 0)[0]
        mine = [i for i in range(len(raw)) if first + i in replace]
        with ProcessPoolExecutor() as ex:
            enc = ex.map(_tracer_stream, [(first + i, m.samples[first + i][1], rate, channels) for i in mine])
            for i, e in zip(mine, enc):
                raw[i] = e
        checksum = b'CNV' + bytes([t]) if own_ids else data[:4]
        ids = None if own_ids else [r['id'] for r in mus.read_directory(data)]
        data, header_end, tab = mus.pack(raw, checksum, ids)
        entry = bytearray(m.tracks[t])
        entry[8:12] = checksum
        struct.pack_into('<I', entry, 12, header_end)
        m.tracks[t] = bytes(entry)
        table += tab
        out[name] = data
        print(f'{name}: {len(mine)} of {len(raw)} streams tracer ({rate} Hz x{channels}), '
              f'{"our" if own_ids else "retail"} ids, {len(data) / 1e6:.1f} MB')
    m.samples = table
    return out


def write_sources(name, mpf):
    SRC_DIR = src_dir(name)
    os.makedirs(SRC_DIR, exist_ok=True)
    open(os.path.join(SRC_DIR, 'probe.mpf'), 'wb').write(mpf)
    with open(os.path.join(SRC_DIR, 'music.xml'), 'w', encoding='ascii', newline='\r\n') as f:
        f.write('<?xml version="1.0" encoding="us-ascii"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset">\n'
                '\t<PathMusicMap id="PC_RA3PathMusicMap" File="probe.mpf" />\n</AssetDeclaration>\n')
    with open(os.path.join(SRC_DIR, 'mod.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
                '\t<Tags></Tags>\n\t<Includes>\n'
                '\t\t<Include type="reference" source="DATA:static.xml" />\n'
                '\t\t<Include type="reference" source="DATA:global.xml" />\n'
                '\t\t<Include type="reference" source="DATA:audio.xml" />\n'
                '\t\t<Include type="all" source="music.xml" />\n'
                '\t</Includes>\n</AssetDeclaration>\n')


own_tracks = pack.tracer_tracks


def check_with_vgmstream(mpf, track0, streams, replace):
    """Decode a few streams of our .mpf + .mus with vgmstream; those in `replace` must read back as their tracer."""
    from scipy.io import wavfile
    d = os.path.join(labpaths.WORK, 'music', 'probe', 'vgm_check')
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'check.mpf'), 'wb').write(mpf)
    open(os.path.join(d, 'check.mus'), 'wb').write(track0)
    cli = os.path.join(labpaths.LAB, 'RA3-ChineseVoice', 'third_party', 'vgmstream', 'vgmstream-cli.exe')
    for k in streams:
        out = os.path.join(d, f'{k}.wav')
        r = subprocess.run([cli, '-i', '-s', str(k + 1), '-o', out, os.path.join(d, 'check.mpf')],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'vgmstream cannot read our files (stream {k}): {r.stdout[-300:]}')
        sr, x = wavfile.read(out)
        if k not in replace:
            print(f'vgmstream stream {k}: {len(x) / sr:.2f} s (retail)')
            continue
        runs, _ = tracer.decode(x, sr, win=min(0.25, len(x) / sr * 0.8), hop=0.05)
        heard = {r[2] for r in runs}
        print(f'vgmstream stream {k}: {len(x) / sr:.2f} s at {sr} Hz, tones -> {sorted(heard)}')
        if heard != {k}:
            sys.exit(f'vgmstream stream {k} decodes to tracer {heard}')


def compile_mod(name):
    log = os.path.join(SDK, f'_build_{name}.log')
    for attempt in range(2):         # now and then it exits printing nothing at all; the same run again builds
        r = subprocess.run([os.path.join(SDK, 'tools', 'BinaryAssetBuilder.exe'),
                            os.path.join(src_dir(name), 'mod.xml'), f'/od:{SDK}\\BuiltMods',
                            f'/iod:{SDK}\\BuiltMods', '/ls:true', '/gui:false', '/pc:true', '/vf:false', '/el:0'],
                           cwd=SDK, capture_output=True, text=True, errors='replace')
        open(log, 'w', encoding='utf-8').write(r.stdout + r.stderr)
        if not r.returncode and 'BinaryAssetBuilder complete' in r.stdout:
            return
        if r.stdout.strip() or r.stderr.strip():
            break
    sys.exit('BinaryAssetBuilder failed, see ' + log)


def main():
    kind = sys.argv[1]
    m = retail_map()
    tracks = {}
    if kind == 'menu-to':
        print(menu_to(m, int(sys.argv[2], 0)))
    elif kind in REMIX:
        replace, rate, channels, own_ids = REMIX[kind]
        replace = set(range(len(m.samples)) if replace is None else replace)
        tracks = remix_tracks(m, replace, rate, channels, own_ids)
    elif kind == 'spy':
        b, lengths = ownmap.spy(m)
        m = b.m
        tracks = own_tracks(m, lengths)
        replace = set(range(len(lengths)))
    elif kind != 'retail':
        sys.exit(f'unknown probe {kind}')
    NAME = NAMES[kind]
    OUT = out_dir(NAME)
    mpf = pfdx.build(m)
    if tracks:                      # vgmstream reads .mpf + .mus on its own: an outside check of both files
        check_with_vgmstream(mpf, tracks['PathMusicTrack:Track'], (0, 4, 88), replace)
    write_sources(NAME, mpf)
    compile_mod(NAME)
    files = splice_assets.spliced_files(built_dir(NAME))
    assets = extract.music_assets()
    pack.Pack(mpf, '').check(files)
    files += [(assets[name].cdata_path, data) for name, data in tracks.items()]
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    big.write(os.path.join(OUT, f'{NAME}.big'), files)
    skudef = os.path.join(OUT, f'{NAME}_1.0.skudef')
    with open(skudef, 'w', encoding='ascii', newline='') as f:
        f.write(f'mod-game 1.12\r\nadd-big {NAME}.big\r\n')
    print('->', skudef)


if __name__ == '__main__':
    main()
