"""EA Pathfinder .mus (v5.3, RA3's PathMusicTrack cdata): read the directory, write a new one from PCM (EA-XAS).

Layout, worked out from the retail track.mus / track-mem.mus (vgmstream reads the directory the same way):
  0x00 4 bytes  checksum: must equal the track entry's checksum bytes in the map (pfdx track entry +8)
  0x04 u32      stream count
  0x08 32 bytes constant (identical in both retail files)
  0x28 per stream 28 bytes: u32 id, u16 index, u16 sub index (0), u32 SNR offset / 0x10, u32 SNS offset / 0x80,
       u32 SNR size (8), u32 SNS size, u32 0
  SNR headers (8 bytes each, at 0x10 steps), then SNS block data (each stream at a 0x80 boundary)
The map's track entry +12 is the end of the SNR headers (what the game preloads); the map's sample table holds
(SNS offset / 0x80, duration ms) per stream, track 0's streams first.
"""
import struct
import zlib

import numpy as np

from ra3voice import xas

CONSTANT = bytes.fromhex('403f3400' '19250037' '403f3400' '00000000' '00000000' 'af220037' 'e0f11200' '00000000')
CODEC_XAS = 4
BLOCK_SAMPLES = 1024          # samples per SNS block (multiple of 128)


def read_directory(data):
    n = struct.unpack_from('<I', data, 4)[0]
    rows = [struct.unpack_from('<IHHIIIII', data, 0x28 + 0x1c * i) for i in range(n)]
    return [dict(id=r[0], index=r[1], sub=r[2], snr=r[3] * 0x10, sns=r[4] * 0x80, snr_size=r[5], sns_size=r[6])
            for r in rows]


def _sns(pcm, channels):
    """int16 [n, channels] -> SNS blocks: whole 76-byte XAS frames interleaved per channel, last block flag 0x80."""
    n = len(pcm)
    per = [xas.encode(pcm[:, c]) for c in range(channels)]
    fb = xas.FRAME_BYTES
    frames = len(per[0]) // fb
    step = BLOCK_SAMPLES // xas.FRAME_SAMPLES
    out = bytearray()
    for f0 in range(0, frames, step):
        f1 = min(frames, f0 + step)
        chunk = b''.join(per[c][f * fb:(f + 1) * fb] for f in range(f0, f1) for c in range(channels))
        last = f1 == frames
        ns = n - f0 * xas.FRAME_SAMPLES if last else (f1 - f0) * xas.FRAME_SAMPLES
        out += struct.pack('>II', (0x80 << 24 if last else 0) | (8 + len(chunk)), ns) + chunk
    return bytes(out)


def raw_streams(data):
    """A .mus -> [(8-byte SNR header, SNS data)] per stream, as stored (any codec), for pack()."""
    return [(data[r['snr']:r['snr'] + r['snr_size']], data[r['sns']:r['sns'] + r['sns_size']])
            for r in read_directory(data)]


def encode(pcm, rate):
    """int16 [n] or [n, channels] -> (SNR header, SNS data) in EA-XAS, for pack()."""
    s = np.asarray(pcm, dtype=np.int16)
    s = s[:, None] if s.ndim == 1 else s
    n, ch = s.shape
    return struct.pack('>II', (CODEC_XAS << 24) | ((ch - 1) << 18) | rate, (1 << 30) | n), _sns(s, ch)


def duration_ms(snr):
    """Rounded down, as in the retail map's sample table."""
    h0, h1 = struct.unpack('>II', snr[:8])
    return (h1 & 0x1FFFFFFF) * 1000 // (h0 & 0x3FFFF)


def pack(streams, checksum, ids=None):
    """streams: [(SNR header, SNS data)]. ids: the directory's u32 per stream (retail ones look like hashes of
    names we do not know; default crc32 of b'cnv<i>'). SNR headers start at a 0x100 boundary, as in retail.
    Returns (mus bytes, header end, [(SNS offset / 0x80, duration ms)]) -- the last two go into the map's track
    entry and sample table."""
    count = len(streams)
    ids = ids or [zlib.crc32(b'cnv%d' % i) for i in range(count)]
    snr_at = (0x28 + 0x1c * count + 0xFF) & ~0xFF
    header_end = snr_at + 0x10 * count
    sns_at = (header_end + 0x7F) & ~0x7F
    body = bytearray()
    rows, snrs, table = [], bytearray(), []
    for i, (snr, sns) in enumerate(streams):
        snrs += snr.ljust(0x10, b'\0')
        off = sns_at + len(body)
        rows.append(struct.pack('<IHHIIIII', ids[i], i, 0, (snr_at + 0x10 * i) // 0x10, off // 0x80, len(snr),
                                len(sns), 0))
        table.append((off // 0x80, duration_ms(snr)))
        body += sns
        body += bytes(-len(body) % 0x80)
    head = checksum + struct.pack('<I', count) + CONSTANT + b''.join(rows)
    head = head.ljust(snr_at, b'\0') + bytes(snrs)
    head = head.ljust(sns_at, b'\0')
    return head + bytes(body), header_end, table


def build(streams, rate, checksum=b'CNVm'):
    """streams: list of int16 arrays [n] or [n, channels], all EA-XAS at `rate`. Returns what pack() does."""
    return pack([encode(s, rate) for s in streams], checksum)
