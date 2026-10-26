"""The .mus writer (experimental/music/mus.py): its constant header matches retail, the directory it writes reads
back, and every stream decodes (through our XAS decoder) to what went in."""
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from experimental.music import mus, pfdx  # noqa: E402
from ra3voice import xas  # noqa: E402

RETAIL = ROOT / 'work' / 'music' / 'retail' / 'track_mem.cdata'


def test_constant_matches_retail():
    if not RETAIL.exists():
        pytest.skip('run experimental/music/extract.py first (needs the game)')
    assert RETAIL.read_bytes()[8:0x28] == mus.CONSTANT


@pytest.mark.parametrize('name', ['track_mem.cdata', 'track.cdata'])
def test_repack_with_retail_ids_is_retail(name):
    """Our container is retail's byte for byte: the retail streams repacked with their own ids and checksum; the
    header end and sample table we return are the ones in the retail map."""
    path = RETAIL.parent / name
    if not path.exists():
        pytest.skip('run experimental/music/extract.py first (needs the game)')
    data = path.read_bytes()
    ids = [r['id'] for r in mus.read_directory(data)]
    got, header_end, table = mus.pack(mus.raw_streams(data), data[:4], ids)
    assert got == data
    m = pfdx.parse((RETAIL.parent / 'map.bin').read_bytes())
    t = next(i for i, e in enumerate(m.tracks) if e[8:12] == data[:4])
    assert struct.unpack_from('<I', m.tracks[t], 12)[0] == header_end
    first = struct.unpack_from('<I', m.tracks[t], 0)[0]
    assert m.samples[first:first + len(table)] == table


def test_build_reads_back():
    t = np.arange(5000)
    a = (np.sin(t / 7) * 9000).astype(np.int16)
    b = np.stack([a, -a], axis=1)
    data, header_end, table = mus.build([a, b], 22050, b'TEST')
    assert data[:4] == b'TEST' and struct.unpack_from('<I', data, 4)[0] == 2
    d = mus.read_directory(data)
    assert [r['index'] for r in d] == [0, 1] and all(r['sns'] % 0x80 == 0 for r in d)
    assert header_end == d[1]['snr'] + 0x10
    assert table == [(r['sns'] // 0x80, 5000 * 1000 // 22050) for r in d]
    for r, pcm in zip(d, [a[:, None], b]):
        h0, h1 = struct.unpack_from('>II', data, r['snr'])
        ch = ((h0 >> 18) & 0x3F) + 1
        assert (h0 >> 24) & 0xF == mus.CODEC_XAS and h0 & 0x3FFFF == 22050 and h1 & 0x3FFFFFFF == 5000
        assert ch == pcm.shape[1]
        p, frames = r['sns'], []
        while True:
            bh, _ = struct.unpack_from('>II', data, p)
            frames.append(data[p + 8:p + (bh & 0xFFFFFF)])
            p += bh & 0xFFFFFF
            if bh >> 24 == 0x80:
                break
        payload = b''.join(frames)
        fb = xas.FRAME_BYTES
        for c in range(ch):
            mono = b''.join(payload[(f * ch + c) * fb:(f * ch + c + 1) * fb] for f in range(len(payload) // fb // ch))
            got = xas.decode(mono, 5000).astype(int)
            assert np.abs(got - pcm[:, c]).max() < 600
