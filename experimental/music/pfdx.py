"""EA Pathfinder interactive music map ('PFDx' v5.3, RA3's PathMusicMap): read and write, worked out from the
retail file (no format documentation exists beyond the sample table, which vgmstream reads).

Layout, little endian, offsets from the magic. A "word offset" is stored divided by 4.
  0x00 'PFDx'  0x04 u8 version 5  0x05 u8 sub version 3  0x06 u16 h06  0x08 u32 h08
  0x0c u8 h0c  0x0d u8 tracks  0x0e u8 h0e  0x0f u8 events  0x10 u16 h10  0x12 u16 nodes
  0x14 u32 x 10: node table, node data, event table, event data, variables, routers, track table, track entries,
                 sample table, end            (then 12 bytes of padding words: header is 0x48 bytes)
  node table   u16 word offset per node, then a 0 terminator
  node         u16 w0, u8 track, u8 b3, u8 router (0 = none, v = routers[v - 1]: in game, MusSpy 2026-10-25),
               u8 branches << 4 | low,
               u8 kind, u8 b7 (1), u24 ref, u8 ref kind, u32 w12 (0), then per branch: u8 lo, u8 hi, u16 node
               (node 0xFFFF = stop). Two kinds:
               kind 0x40 segment: plays stream w0 - 1 (numbered across tracks: track 0 first, then track 1;
                        all 732 streams are used, some by several nodes); ref = its section's entry node
                        (ref kind 4); router: applied when an event is pending at this segment's end
               kind 0x10 section boundary, in pairs: entry (w0 0) and exit (w0 0xFFFF); track = which .mus;
                        ref = serial number (entry 2k, exit 2k + 1, ref kind 0); b3 0xF8 / 0x08 with branches
                        (0,0) and (1,127) on exits: a loop (seen as "repeat unless 0")
               Branch (lo, hi): taken when the selector value is in lo..hi; (0, 127) = always,
               (255, 56) + (56, 127) = a random pick between two.
  event table  u16 word offset per event
  event        5 x u32 head (all 0 but head[3] = name hash (low 24 bits = PathMusicEventRuntime.EventNameHash &
               0xFFFFFF) | action count << 24); then 12 bytes per action: u32 w0, u32 op (bytes 00, class, code,
               00), u32 argument. w0 is 0x11000001 or 0x11000002 (0xFFFFFFFF on endif): the same numbers sit in the
               PathMusicTrack instances as their handles (Track 0x11000001, Track_Mem 0x11000002), so most likely
               the track an action is meant for (not checked in game yet). Seen in retail:
                 GOTO  0x00030400  arg u16 section entry node, u8 0xFF, u8 0      (295)
                 PREP  0x000F0400  arg 0x01FFFFFF, before a lone GOTO              (188; in game, CampMusic
                       2026-10-25: PREP + GOTO cuts over at once (within 0.4 s of the script) and skips the routers;
                       a GOTO alone waits for the end of the playing segment, then plays the router's transition if
                       there is one, then its target: 2.4 to 6.8 s on 8 s segments, each on a segment's end)
                 SET   0x000E0800  arg u16 value, u16 variable                     (player: Soviet 0, Allied 1, Empire 2)
                 IF    0x009E0100  arg u16 variable, u16 value  (== ; 0x019E0100 / 0x029E0100 other comparisons)
                 ELIF  0x00AE0100  arg as IF       ELSE 0x00300100       ENDIF 0x00400100 (w0 0xFFFFFFFF)
                 and a few rare ones (0x000C0500 / 0x000C0200 carry milliseconds: fades)
  variables    20 bytes each: name (12 bytes, NUL terminated, rest left as found), u32, u32
  routers      u32 word offset per router, then per router a list of (u16 a, u16 b) pairs: when an event jumps
               (GOTO without PREP) to section entry b from a segment that uses the router, section a plays
               instead at that segment's end (a transition written for that pair); it goes on by a's own exit
               branches (in retail those do not lead to b; ours do: in game a then b, MusSpy / CampMusic
               2026-10-25)
  track table  u32 word offset per track; track entry 20 bytes (vgmstream: u32 first stream, u16 subbanks,
               u16, u32 BE checksum = first word of the .mus, u32, u32)
  sample table per stream: u32 SNS offset / 0x80 in its .mus, u32 duration in ms
"""
import struct
from dataclasses import dataclass, field

HEADER_SIZE = 0x48


@dataclass
class Node:
    w0: int
    track: int
    b3: int
    router: int
    low: int
    kind: int
    b7: int
    ref: int
    ref_kind: int
    w12: int
    branches: list            # [(lo, hi, node)]

    @property
    def is_segment(self):
        return self.kind == 0x40

    @property
    def stream(self):
        """Index into PathMap.samples (and the .mus streams, track 0 first) of the audio a segment plays."""
        return self.w0 - 1 if self.is_segment else None


@dataclass
class Event:
    head: list                # 5 x u32, head[3] high byte rewritten from len(actions)
    actions: list             # [(u32, u32, u32)]
    name: str = ''

    @property
    def hash24(self):
        return self.head[3] & 0xFFFFFF


@dataclass
class PathMap:
    h06: int
    h08: int
    h0c: int
    h0e: int
    h10: int
    pad: bytes
    nodes: list = field(default_factory=list)
    events: list = field(default_factory=list)
    variables: list = field(default_factory=list)    # raw 20-byte entries
    routers: list = field(default_factory=list)      # [[(a, b)]]
    tracks: list = field(default_factory=list)       # raw 20-byte entries
    samples: list = field(default_factory=list)      # [(sns offset / 0x80, ms)]
    version: tuple = (5, 3)

    def variable_names(self):
        return [v[:12].split(b'\0')[0].decode('latin-1') for v in self.variables]


def walk(m, node, segments=8):
    """Streams played from `node` on, taking the last branch at every node (loops repeat), for expectations."""
    out, seen = [], 0
    while node != 0xFFFF and len(out) < segments and seen < 10000:
        n = m.nodes[node]
        if n.is_segment:
            out.append(n.stream)
        if not n.branches:
            break
        node = n.branches[-1][2]
        seen += 1
    return out


def strip_asset_header(blob):
    """A compiled PathMusicMap instance has 12 bytes before the magic; a bare .mpf starts with it."""
    i = blob.find(b'xDFP')
    if i < 0:
        raise ValueError('no PFDx magic')
    return blob[i:]


def parse(blob, names=None):
    """blob: the PathMusicMap instance or a bare .mpf. names: {event name: EventNameHash}, to label events."""
    d = strip_asset_header(blob)
    u16 = lambda o: struct.unpack_from('<H', d, o)[0]
    u32 = lambda o: struct.unpack_from('<I', d, o)[0]
    sec = [u32(0x14 + 4 * i) for i in range(10)]
    m = PathMap(u16(6), u32(8), d[0x0c], d[0x0e], u16(0x10), d[0x3c:HEADER_SIZE], version=(d[4], d[5]))
    num_tracks, num_events, num_nodes = d[0x0d], d[0x0f], u16(0x12)

    for i in range(num_nodes):
        o = u16(sec[0] + 2 * i) * 4
        n = d[o + 5] >> 4
        m.nodes.append(Node(u16(o), d[o + 2], d[o + 3], d[o + 4], d[o + 5] & 0xF, d[o + 6], d[o + 7],
                            u32(o + 8) & 0xFFFFFF, d[o + 11], u32(o + 12),
                            [(d[o + 16 + 4 * k], d[o + 17 + 4 * k], u16(o + 18 + 4 * k)) for k in range(n)]))

    by_hash = {h & 0xFFFFFF: k for k, h in (names or {}).items()}
    for i in range(num_events):
        o = u16(sec[2] + 2 * i) * 4
        head = list(struct.unpack_from('<5I', d, o))
        acts = [struct.unpack_from('<3I', d, o + 20 + 12 * k) for k in range(head[3] >> 24)]
        m.events.append(Event(head, acts, by_hash.get(head[3] & 0xFFFFFF, '')))

    m.variables = [d[o:o + 20] for o in range(sec[4], sec[5], 20)]

    first = u32(sec[5]) * 4
    starts = [u32(sec[5] + 4 * i) * 4 for i in range((first - sec[5]) // 4)]
    for i, o in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else sec[6]
        m.routers.append([struct.unpack_from('<2H', d, p) for p in range(o, end, 4)])

    m.tracks = [d[u32(sec[6] + 4 * i) * 4:u32(sec[6] + 4 * i) * 4 + 20] for i in range(num_tracks)]
    m.samples = [struct.unpack_from('<2I', d, o) for o in range(sec[8], sec[9], 8)]
    return m


def build(m):
    """PathMap -> bare .mpf bytes (what BinaryAssetBuilder's PathMusicMap File= reads)."""
    body = bytearray(HEADER_SIZE)
    sec = []

    def here():
        return len(body)

    def word(o):
        assert o % 4 == 0 and o // 4 < 0x10000, o
        return o // 4

    # node table, then nodes
    sec.append(here())
    body += bytes(2 * (len(m.nodes) + 1))
    body += bytes(-len(body) % 4)
    sec.append(here())
    for i, n in enumerate(m.nodes):
        struct.pack_into('<H', body, sec[0] + 2 * i, word(here()))
        body += struct.pack('<HBBBBBBI I', n.w0, n.track, n.b3, n.router, len(n.branches) << 4 | n.low, n.kind, n.b7,
                            n.ref | n.ref_kind << 24, n.w12)
        for lo, hi, to in n.branches:
            body += struct.pack('<BBH', lo, hi, to)

    sec.append(here())
    body += bytes(2 * len(m.events))
    body += bytes(-len(body) % 4)
    sec.append(here())
    for i, e in enumerate(m.events):
        struct.pack_into('<H', body, sec[2] + 2 * i, word(here()))
        head = list(e.head)
        head[3] = (head[3] & 0xFFFFFF) | len(e.actions) << 24
        body += struct.pack('<5I', *head)
        for a in e.actions:
            body += struct.pack('<3I', *a)

    sec.append(here())
    for v in m.variables:
        body += v

    sec.append(here())
    table = here()
    body += bytes(4 * len(m.routers))
    for i, r in enumerate(m.routers):
        struct.pack_into('<I', body, table + 4 * i, word(here()))
        for a, b in r:
            body += struct.pack('<2H', a, b)

    sec.append(here())
    body += bytes(4 * len(m.tracks))
    sec.append(here())
    for i, t in enumerate(m.tracks):
        struct.pack_into('<I', body, sec[6] + 4 * i, word(here()))
        body += t

    sec.append(here())
    for s in m.samples:
        body += struct.pack('<2I', *s)
    sec.append(here())

    struct.pack_into('<4sBBHIBBBBHH', body, 0, b'xDFP', m.version[0], m.version[1], m.h06, m.h08, m.h0c,
                     len(m.tracks), m.h0e, len(m.events), m.h10, len(m.nodes))
    struct.pack_into('<10I', body, 0x14, *sec)
    body[0x3c:HEADER_SIZE] = m.pad
    return bytes(body)
