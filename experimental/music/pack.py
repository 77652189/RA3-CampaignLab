"""A music pack: our Pathfinder map and its .mus tracks, in the shape a mod build takes them (the interface with the
mission builds, experimental/cnv/parts.Mission.music).

The map must be in the static stream (the shell plays music before any map loads), so a pack is an XML for the
static mod.xml (`include`, type="all": BinaryAssetBuilder then compiles our PathMusicMap and splice_assets puts it
over retail's by id) plus the .mus files at the retail cdata paths (`files`, added to the mod's big as they are).

  pack = make(m, tracks)        m: a pfdx.PathMap, tracks: {'PathMusicTrack:Track' / ':Track_Mem': .mus bytes}
  pack.include                  'DATA:CNVMusic/Data/music.xml'   (written under the SDK's Mods folder)
  pack.files                    [(big path, bytes)]
  pack.events                   the event names it plays (what a mission's PATH_MUSIC_PLAY_EVENT may name)
  pack.check(files)             the spliced static stream holds our map (BinaryAssetBuilder keeps a cache)
  Later(lambda: make(...), events)   the same, made on first use (what a mission puts in Mission.music)
"""
import os
import struct
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import numpy as np

from experimental.campaign import labpaths
from experimental.music import extract, mus, pfdx, tracer

FOLDER = 'CNVMusic'
MAP_ASSET = 'PathMusicMap:PC_RA3PathMusicMap'
# (asset, retail .mus) per map track, in the map's track order
TRACKS = [('PathMusicTrack:Track', 'track.cdata'), ('PathMusicTrack:Track_Mem', 'track_mem.cdata')]


def tracer_stream(args):
    """(k, ms, rate, channels) -> (SNR, SNS) of tracer k, EA-XAS (a process pool's worker)."""
    k, ms, rate, channels = args
    x = tracer.stream(k, ms, rate)
    return mus.encode(np.stack([x] * channels, axis=1) if channels > 1 else x, rate)


def tracer_tracks(m, lengths, kept=()):
    """Tracer streams of the given lengths (ms) for track 0 (stream k plays tracer k) and one 1 s stream for
    Track_Mem (unused, the game may expect the track), 22.05 kHz mono EA-XAS, our ids; then on track 0 the retail
    streams the map keeps (ownmap.Builder.keep: extract.retail_streams), as stored. The map's track entries follow
    them and its sample table is replaced. Returns {asset name: .mus bytes}."""
    per_track = [list(enumerate(lengths)), [(len(lengths) + len(kept), 1000)]]
    encoded = []
    for streams in per_track:
        with ProcessPoolExecutor() as ex:
            encoded.append(list(ex.map(tracer_stream, [(k, ms, tracer.RATE, 1) for k, ms in streams])))
    encoded[0] += list(kept)
    return _tracks(m, encoded)


def _encode(args):
    pcm, rate = args
    return mus.encode(pcm, rate)


def music_tracks(m, streams, rate, kept=()):
    """Our music for track 0: streams [(n,) or (n, 2) int16] at `rate`, EA-XAS (stream k of the map plays
    streams[k]), then the retail streams the map keeps (as tracer_tracks); Track_Mem gets one second of silence.
    The map's track entries and sample table follow them."""
    with ProcessPoolExecutor() as ex:
        main = list(ex.map(_encode, [(x, rate) for x in streams]))
    silence = np.zeros((rate, 2) if streams[0].ndim == 2 else rate, np.int16)
    return _tracks(m, [main + list(kept), [mus.encode(silence, rate)]])


def _tracks(m, encoded):
    """encoded: per map track, [(SNR, SNS)]; -> {asset name: .mus bytes}, the map patched to them."""
    out, table = {}, []
    for t, ((name, _), raw) in enumerate(zip(TRACKS, encoded)):
        checksum = b'CNV' + bytes([t])
        data, header_end, tab = mus.pack(raw, checksum)
        entry = bytearray(m.tracks[t])
        struct.pack_into('<I', entry, 0, len(table))
        entry[8:12] = checksum
        struct.pack_into('<I', entry, 12, header_end)
        m.tracks[t] = bytes(entry)
        table += tab
        out[name] = data
        print(f'{name}: {len(raw)} streams, {len(data) / 1e6:.1f} MB')
    m.samples = table
    return out


@dataclass
class Pack:
    mpf: bytes
    include: str
    files: list = field(default_factory=list)
    events: set = field(default_factory=set)        # the event names our map does something on

    def check(self, files):
        """files: the mod's [(big path, bytes)] after splice_assets; exits unless its map instance is ours."""
        from ra3voice import manifest, refpack
        got = dict(files)
        unpack = lambda b: refpack.decompress(b) if refpack.is_refpack(b) else b
        for a in manifest.parse(unpack(got['data\\static.manifest'])):
            if a.name == MAP_ASSET:
                inst = unpack(got['data\\static.bin'])[a.bin_offset:a.bin_offset + a.inst_size]
                if pfdx.strip_asset_header(inst) != self.mpf:
                    sys.exit('the spliced music map is not ours (stale BinaryAssetBuilder cache?)')
                print('music: spliced map == our .mpf')
                return
        sys.exit('music: no map in the spliced static stream')


class Later:
    """A pack made only when a build first asks for it (include / files / check): a mission names its events up
    front, which is all the offline contract reads, without encoding audio or needing the game's data."""

    def __init__(self, make_pack, events):
        self._make, self._pack, self.events = make_pack, None, set(events)

    def _get(self):
        if self._pack is None:
            self._pack = self._make()
            missing = self.events - self._pack.events
            assert not missing, f'music: the map plays none of {sorted(missing)}'
        return self._pack

    include = property(lambda self: self._get().include)
    files = property(lambda self: self._get().files)

    def check(self, files):
        self._get().check(files)


def make(m, tracks, folder=FOLDER):
    """Write <SDK>/Mods/<folder>/Data/music.xml + music.mpf and return the Pack."""
    data = os.path.join(labpaths.SDK3, 'Mods', folder, 'Data')
    os.makedirs(data, exist_ok=True)
    mpf = pfdx.build(m)
    with open(os.path.join(data, 'music.mpf'), 'wb') as f:
        f.write(mpf)
    with open(os.path.join(data, 'music.xml'), 'w', encoding='ascii', newline='\r\n') as f:
        f.write('<?xml version="1.0" encoding="us-ascii"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset">\n'
                f'\t<PathMusicMap id="{MAP_ASSET.split(":")[1]}" File="music.mpf" />\n</AssetDeclaration>\n')
    assets = extract.music_assets()
    return Pack(mpf, f'DATA:{folder}/Data/music.xml', [(assets[name].cdata_path, data) for name, data in tracks.items()],
                {e.name for e in m.events if e.name and e.actions})
