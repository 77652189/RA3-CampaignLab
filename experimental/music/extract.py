"""Copy the retail dynamic music (EA Pathfinder) out of the game into work/music/retail/ for study.

  PathMusicMap:PC_RA3PathMusicMap   -> map.bin    (instance data in data\\static.bin; the Pathfinder map, 'PFDx')
  PathMusicTrack:Track              -> track.bin  (instance data) + track.cdata (the streamed .mus, ~230 MB)
  PathMusicTrack:Track_Mem          -> track_mem.bin + track_mem.cdata (the small in-memory .mus)
  every PathMusicEvent (global stream) -> event_hashes.json {name: EventNameHash}, to name the map's events

Read only: the game folder is never written. Run: python -I experimental/music/extract.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from experimental.campaign import labpaths  # noqa: E402
from ra3voice import big, manifest, refpack  # noqa: E402

OUT = os.path.join(labpaths.WORK, 'music', 'retail')
STATIC_BIG = os.path.join(labpaths.GAME, 'Data', 'StaticStream.big')
GLOBAL_BIG = os.path.join(labpaths.GAME, 'Data', 'GlobalStream.big')
WANT = {'PathMusicMap:PC_RA3PathMusicMap': 'map',
        'PathMusicTrack:Track': 'track',
        'PathMusicTrack:Track_Mem': 'track_mem'}


def _unpack(raw):
    return refpack.decompress(raw) if refpack.is_refpack(raw) else raw


def music_assets(files=None):
    """{asset name: manifest.Asset} of the three music assets in the retail static stream (cdata_path usable)."""
    files = files or big.read_files(STATIC_BIG, ['data\\static.manifest'])
    assets = manifest.parse(_unpack(files['data\\static.manifest']))
    found = {a.name: a for a in assets if a.name in WANT}
    missing = set(WANT) - set(found)
    if missing:
        sys.exit(f'not in static.manifest: {sorted(missing)}')
    for a in found.values():
        a.stream = 'static'
    return found


def retail_map():
    """The retail map as extracted (main), its events named."""
    import json
    from experimental.music import pfdx
    names = json.load(open(os.path.join(OUT, 'event_hashes.json')))
    return pfdx.parse(open(os.path.join(OUT, 'map.bin'), 'rb').read(), names)


def retail_streams(indices):
    """Retail track 0's streams `indices` as stored, [(SNR header, SNS data)] (mus.pack's input), from the
    extracted track.cdata (main)."""
    from experimental.music import mus
    with open(os.path.join(OUT, 'track.cdata'), 'rb') as f:
        data = f.read()
    rows = mus.read_directory(data)
    return [(data[r['snr']:r['snr'] + r['snr_size']], data[r['sns']:r['sns'] + r['sns_size']])
            for r in (rows[i] for i in indices)]


def event_hashes():
    """{event name: EventNameHash} of every PathMusicEvent in the retail global stream (the instance's u32 at +4;
    the map keeps its low 24 bits). Instances carrying an XferAlternateEvent are bigger than the plain 16 bytes,
    the hash sits at the same place (S_A01BrightonIntro, the first event retail mission 1 plays)."""
    import struct
    files = big.read_files(GLOBAL_BIG, ['data\\global.manifest', 'data\\global.bin'])
    binary = _unpack(files['data\\global.bin'])
    return {a.name.split(':', 1)[1]: struct.unpack_from('<I', binary, a.bin_offset + 4)[0]
            for a in manifest.parse(_unpack(files['data\\global.manifest'])) if a.name.startswith('PathMusicEvent:')}


def main():
    os.makedirs(OUT, exist_ok=True)
    import json
    names = event_hashes()
    json.dump(names, open(os.path.join(OUT, 'event_hashes.json'), 'w'), indent=0)
    print(f'event_hashes.json: {len(names)} event names')
    files = big.read_files(STATIC_BIG, ['data\\static.manifest', 'data\\static.bin'])
    binary = _unpack(files['data\\static.bin'])
    found = music_assets(files)
    cdata = {name: a.cdata_path for name, a in found.items()}
    blobs = big.read_files(STATIC_BIG, list(cdata.values()))
    for name, a in found.items():
        stem = WANT[name]
        with open(os.path.join(OUT, stem + '.bin'), 'wb') as f:
            f.write(binary[a.bin_offset:a.bin_offset + a.inst_size])
        blob = blobs.get(cdata[name])
        if blob is not None:
            with open(os.path.join(OUT, stem + '.cdata'), 'wb') as f:
                f.write(_unpack(blob))
        print(f'{name}: instance {a.inst_size} B, cdata {len(blob) if blob else 0} B')


if __name__ == '__main__':
    main()
