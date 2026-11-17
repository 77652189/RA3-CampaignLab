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


def _same_length(old, new):
    assert len(new) == len(old), f'{old!r} -> {new!r}: not the same length'
    return new


def hollow(archive, prefix, renames=None):
    """The stream with nothing to draw: [(big path, bytes)] for its four files. Every AptGeometryData chunk is a 16-byte head
    (0, text offset, text length, ...) and the shape as text ('c' clear, 's' style, 't' triangle); the text is cut to a bare
    'c' and the chunk keeps its size (zero padded), and every texture's pixels are made transparent. The movie, its scripts
    and its sizes stay, so the engine finds every clip it calls and finds nothing on screen. renames: as in `patch` (the
    names a script calls renamed, e.g. the engine-drawn picture's `RenderImage` into a call nobody answers)."""
    (h, E, chunks, bufs), raw = mapxml.read_stream(prefix, mapxml._archive_get(archive))
    chunks = [list(c) for c in chunks]
    for k, e in enumerate(E):
        name = mapxml.sa.cstr(bufs[2], e[6]).decode()
        data = chunks[k][0]
        if renames and name.startswith('AptConstData:'):            # the scripts' constants only: the movie's own names (AptAptData) stay
            pattern, rename = renames
            chunks[k][0] = pattern.sub(lambda m: _same_length(m.group(0), rename(m.group(0))), data)
        if name.startswith('AptGeometryData:'):
            zero, at, length, extra = struct.unpack_from('<4I', data, 0)
            assert zero == 0 and at == 16 and at + length <= len(data), f'{name}: not a shape text chunk'
            text = b'c\r\n'
            chunks[k][0] = struct.pack('<4I', zero, at, len(text), extra) + text + bytes(len(data) - at - len(text))
        elif name.startswith('Texture:'):
            _size(data)
            chunks[k][0] = data[:HEAD + DDS_HEAD] + bytes(len(data) - HEAD - DDS_HEAD)
    files = mapxml.write_stream(h, E, chunks, bufs, (raw[1][:4], raw[2][:4], raw[3][:4]))
    return [(prefix + x, v) for x, v in zip(('manifest', 'bin', 'relo', 'imp'), files)]


SCRIPT = (b'AptAptData', b'AptConstData', b'AptDatData')     # a screen's movie, its constants, its image -> texture table


def patch(archive, prefix, images, renames=None, movie=None, donor=None):
    """images: {texture id: PIL image of the texture's exact size}. The stream's four files with those pictures in.
    renames: (compiled regex over bytes, f(match bytes) -> bytes of the same length): the names in the stream's constants (a
    script's string table: event names it plays, labels it shows) rewritten, every occurrence the same way.
    movie: f(.apt bytes, constant file bytes) -> .apt bytes of the same length (apt_movie: the timeline edited in place).
    donor: another stream's prefix whose movie, constants and image table (SCRIPT) take the place of this one's -- its
    timeline played over this stream's own shapes and pictures (the same character numbers: the retail objective
    briefings all draw their map as shape 3 filled with texture 1); the entries' sizes and content hashes follow."""
    (h, E, chunks, bufs), raw = mapxml.read_stream(prefix, mapxml._archive_get(archive))
    chunks = [list(c) for c in chunks]
    E = [list(e) for e in E]
    if donor:
        (_, dE, dC, dB), _ = mapxml.read_stream(donor, mapxml._archive_get(archive))
        theirs = {mapxml.sa.cstr(dB[2], e[6]).split(b':')[0]: (e, c) for e, c in zip(dE, dC)}
        for k, e in enumerate(E):
            kind = mapxml.sa.cstr(bufs[2], e[6]).split(b':')[0]
            if kind in SCRIPT:
                de, dc = theirs[kind]
                assert e[5] == de[5] == 0, f'{kind}: references other assets'
                chunks[k] = list(dc)
                e[3] = de[3]
    if movie:
        import apt_movie
        kinds = {mapxml.sa.cstr(bufs[2], e[6]).split(b':')[0]: k for k, e in enumerate(E)}
        a, c = chunks[kinds[b'AptAptData']][0], chunks[kinds[b'AptConstData']][0]
        (ao, al), (co, cl) = apt_movie.apt_of(a), apt_movie.apt_of(c)
        new = movie(a[ao:ao + al], c[co:co + cl])
        chunks[kinds[b'AptAptData']][0] = a[:ao] + _same_length(a[ao:ao + al], new) + a[ao + al:]
    if renames:
        pattern, rename = renames
        for k, e in enumerate(E):
            if mapxml.sa.cstr(bufs[2], e[6]).startswith((b'AptConstData:', b'AptAptData:')):
                chunks[k][0] = pattern.sub(lambda m: _same_length(m.group(0), rename(m.group(0))), chunks[k][0])
    for tex, img in images.items():
        k = _find(E, bufs, tex)
        w, hh = _size(chunks[k][0])
        assert img.size == (w, hh), f'{tex} is {w}x{hh}, the picture {img.size}'
        r, g, b, a = img.convert('RGBA').split()
        from PIL import Image
        pixels = Image.merge('RGBA', (b, g, r, a)).tobytes()          # A8R8G8B8 little endian = B, G, R, A in memory
        chunks[k][0] = chunks[k][0][:HEAD + DDS_HEAD] + pixels
    for e, c in zip(E, chunks):
        e[8:11] = [len(x) for x in c]
    files = mapxml.write_stream(h, E, chunks, bufs, (raw[1][:4], raw[2][:4], raw[3][:4]))
    return [(prefix + x, v) for x, v in zip(('manifest', 'bin', 'relo', 'imp'), files)]
