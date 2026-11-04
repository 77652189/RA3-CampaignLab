"""The timeline of a retail APT movie, read and edited in place (the shell's world map, ADR 0014).

A stream's `AptAptData` chunk is a 12-byte head (0, 12, length) and then the .apt file, whose pointers are offsets into
that file; its `AptConstData` chunk is the same head and the .apt's constant file, whose word at 20 points at the movie
(checked on the 27 retail *_global_briefing and *_objective_briefing screens, 2026-11-03). The layout is the one of
OpenSAGE's reader (OpenSage.Data.Apt): a movie is (type 9, signature, frame count, frames, -, character count, characters,
width, height, ms per frame, import count, imports, export count, exports, -); a frame is (item count, item pointers); an
item starts with its type (1 action, 2 frame label, 3 place object, 4 remove object); a place object is
(type, flags, depth, character, 2x2 matrix, translation, colour, -, ratio, name, clip depth, clip actions), 64 bytes.

Only the main timeline is read (no sprites' own frames). Edits keep every size: a placement's floats are rewritten where
they are, so the stream's relocation and import tables stay valid.

  m = movie(apt, const);  for it in placements(m): ...;  move(buf, it, (x, y))
"""
import struct
from dataclasses import dataclass

HEAD = 12
MOVE, HAS_CHARACTER, HAS_MATRIX = 1, 2, 4


@dataclass
class Place:
    frame: int
    at: int                 # the item's offset in the .apt
    flags: int
    depth: int
    char: int               # the character at that depth (carried over from the frame that placed it)
    matrix: tuple           # (a, b, c, d): x' = a x + c y + tx, y' = b x + d y + ty
    translate: tuple


def apt_of(chunk):
    """The .apt file inside an AptAptData / AptConstData chunk: (offset in the chunk, length)."""
    zero, at, length = struct.unpack_from('<3I', chunk, 0)
    assert zero == 0 and at == HEAD and at + length <= len(chunk), 'not an APT chunk'
    return at, length


def _u(b, o, n=1):
    v = struct.unpack_from(f'<{n}I', b, o)
    return v if n > 1 else v[0]


def _cstr(b, o):
    return b[o:b.index(b'\0', o)].decode('latin1') if o else None


def movie(apt, const):
    """{'frames': [[(kind, offset)]], 'imports': {name: character}, 'libraries': {name: the library it is imported from, e.g.
    '..\\\\common\\\\shell\\\\missionBriefings\\\\fe_missionBriefingAssets'}, 'size': (w, h), 'ms': ms per frame} of the .apt bytes
    `apt` with its constant file `const`."""
    off = _u(const, 20)
    kind, _sig = _u(apt, off, 2)
    assert kind == 9, f'no movie at {off}'
    fc, fp, _, cc, cp, w, h, ms, ic, ip = _u(apt, off + 8, 10)
    imports, libraries = {}, {}
    for k in range(ic):
        lib, name, char, _p = _u(apt, ip + 16 * k, 4)
        imports[_cstr(apt, name)] = char
        libraries[_cstr(apt, name)] = _cstr(apt, lib)
    frames = []
    for f in range(fc):
        n, items = _u(apt, fp + 8 * f, 2)
        frames.append([(_u(apt, p), p) for p in (_u(apt, items + 4 * i) for i in range(n))])
    return dict(frames=frames, imports=imports, libraries=libraries, size=(w, h), ms=ms)


def placements(m, apt):
    """Every place-object item of the main timeline, in order, with the character standing at its depth."""
    at = {}
    for f, items in enumerate(m['frames']):
        for kind, p in items:
            if kind == 3:
                flags, depth, char = struct.unpack_from('<Iii', apt, p + 4)
                if flags & HAS_CHARACTER:
                    at[depth] = char
                yield Place(f, p, flags, depth, at.get(depth), struct.unpack_from('<4f', apt, p + 16),
                            struct.unpack_from('<2f', apt, p + 32))
            elif kind == 4:
                at.pop(struct.unpack_from('<i', apt, p + 4)[0], None)


def move(buf, it, translate):
    """Rewrite placement `it`'s translation in `buf` (a bytearray of the .apt)."""
    assert it.flags & HAS_MATRIX, f'frame {it.frame} depth {it.depth}: no matrix to move'
    struct.pack_into('<2f', buf, it.at + 32, *translate)


def place(buf, it, matrix, translate):
    """Rewrite placement `it`'s 2x2 matrix (a, b, c, d) and translation in `buf`."""
    assert it.flags & HAS_MATRIX, f'frame {it.frame} depth {it.depth}: no matrix to rewrite'
    struct.pack_into('<6f', buf, it.at + 16, *matrix, *translate)
