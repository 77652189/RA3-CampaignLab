"""Our pictures in a retail APT screen: the Texture instances of a stream replaced, nothing else changed.

An APT screen (data\\aptui\\<name>.{manifest,bin,relo,imp}, Apt.big) carries its pictures as `Texture:apt_<name>_<n>`
instances: a 12-byte head and an uncompressed A8R8G8B8 DDS without mips (checked on a01_objective_briefing, a01_global_briefing,
fes_m_factionmenu, 2026-11-02). A picture of the same size written over the pixels leaves the stream's sizes, offsets and
manifest as they are, so the screen is the retail one with our picture in it. Shipped in a mod's big under the same
path the game takes it from there (make_campnew9 did that with the faction menu's constants).

  patch('Apt.big', 'data\\\\aptui\\\\a01_objective_briefing.', {'apt_A01_Objective_Briefing_1': <PIL image>})
      -> [(big path, bytes)] for the four files of the stream
  textures('Apt.big', prefix) -> {texture id: (width, height)}
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mapxml                                           # noqa: E402

HEAD = 12                       # the instance's own head before the DDS file
DDS_HEAD = 128                  # 'DDS ' + the 124-byte header


def _find(E, bufs, tex):
    for k, e in enumerate(E):
        if mapxml.sa.cstr(bufs[2], e[6]).decode() == 'Texture:' + tex:
            return k
    raise KeyError(f'no Texture:{tex}')


def _size(chunk):
    dds = chunk[HEAD:]
    assert dds[:4] == b'DDS ', 'not a DDS texture'
    h, w = struct.unpack_from('<II', dds, 12)
    pf = struct.unpack_from('<8I', dds, 76)
    assert pf[3] == 32 and pf[4:] == (0xFF0000, 0xFF00, 0xFF, 0xFF000000), f'not A8R8G8B8: {pf}'
    assert len(dds) == DDS_HEAD + w * h * 4, 'mips or padding: not an uncompressed single level'
    return w, h


def textures(archive, prefix):
    (h, E, chunks, bufs), _ = mapxml.read_stream(prefix, mapxml._archive_get(archive))
    return {mapxml.sa.cstr(bufs[2], e[6]).decode()[8:]: _size(chunks[k][0]) for k, e in enumerate(E)
            if mapxml.sa.cstr(bufs[2], e[6]).startswith(b'Texture:')}


def originals(archive, prefix):
    """{texture id: PIL RGBA image} of the stream's retail pictures."""
    from PIL import Image
    (h, E, chunks, bufs), _ = mapxml.read_stream(prefix, mapxml._archive_get(archive))
    out = {}
    for k, e in enumerate(E):
        name = mapxml.sa.cstr(bufs[2], e[6]).decode()
        if name.startswith('Texture:'):
            w, hh = _size(chunks[k][0])
            out[name[8:]] = Image.frombuffer('RGBA', (w, hh), chunks[k][0][HEAD + DDS_HEAD:], 'raw', 'BGRA', 0, 1)
    return out


def patch(archive, prefix, images):
    """images: {texture id: PIL image of the texture's exact size}. The stream's four files with those pictures in."""
    (h, E, chunks, bufs), raw = mapxml.read_stream(prefix, mapxml._archive_get(archive))
    chunks = [list(c) for c in chunks]
    for tex, img in images.items():
        k = _find(E, bufs, tex)
        w, hh = _size(chunks[k][0])
        assert img.size == (w, hh), f'{tex} is {w}x{hh}, the picture {img.size}'
        r, g, b, a = img.convert('RGBA').split()
        from PIL import Image
        pixels = Image.merge('RGBA', (b, g, r, a)).tobytes()          # A8R8G8B8 little endian = B, G, R, A in memory
        chunks[k][0] = chunks[k][0][:HEAD + DDS_HEAD] + pixels
    files = mapxml.write_stream(h, E, chunks, bufs, (raw[1][:4], raw[2][:4], raw[3][:4]))
    return [(prefix + x, v) for x, v in zip(('manifest', 'bin', 'relo', 'imp'), files)]
