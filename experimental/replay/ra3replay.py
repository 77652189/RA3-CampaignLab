r"""Read a Red Alert 3 replay (.RA3Replay): header, timed chunks, commands, footer.

Written from the community's format description (louisdx/cnc-replayreaders, eareplay.html; its RA3 command
table) and checked against our own replays in Documents\Red Alert 3\Replays. No code was copied.

Layout: header | chunks (time_code u32, type u8, size u32, data, u32 0) ... | time_code 0x7FFFFFFF | footer.
One time code = 2 logic frames = 1/15 s. Chunk type 1 = commands, 2 = camera / heartbeat, 3 audio, 4 telestrator.

    python -I -X utf8 experimental/replay/ra3replay.py <file.RA3Replay> [--verbose]
"""
import struct
import sys
from collections import Counter

END = 0x7FFFFFFF

# Command sizes from the community table (whole command: id, player, body, 0xFF). int = fixed size,
# ('std', n) = n header bytes then groups: byte x, (x >> 4) + 1 uint32s, ... until 0xFF. None = layout unknown.
SIZES = {
    0x00: 45, 0x01: None, 0x02: None, 0x03: 17, 0x04: 17, 0x05: 20, 0x06: 20, 0x07: 17, 0x08: 17, 0x09: 35,
    0x0A: ('std', 2), 0x0C: None, 0x0D: ('std', 2), 0x0E: ('std', 2), 0x0F: 16, 0x10: None, 0x12: ('std', 2),
    0x14: 16, 0x15: 16, 0x16: 16, 0x1A: ('std', 2), 0x1B: ('std', 2), 0x21: 20, 0x28: ('std', 2),
    0x29: ('std', 2), 0x2A: ('std', 2), 0x2C: 29, 0x2E: ('std', 2), 0x2F: ('std', 2), 0x32: 53, 0x33: None,
    0x34: 45, 0x35: 1049, 0x36: 16, 0x37: ('std', 2), 0x47: ('std', 2), 0x48: ('std', 2), 0x4B: None,
    0x4C: ('std', 2), 0x4D: None, 0x4E: ('std', 2), 0x52: ('std', 2), 0x5F: 11, 0xF5: ('std', 5),
    0xF6: ('std', 5), 0xF8: ('std', 4), 0xF9: ('std', 2), 0xFA: ('std', 7), 0xFB: ('std', 2), 0xFC: ('std', 2),
    0xFD: ('std', 7), 0xFE: ('std', 15), 0xFF: ('std', 34),
}
NAMES = {
    0x00: 'ability_hard', 0x01: 'creator_info', 0x02: 'rally', 0x03: 'research', 0x04: 'research_stop',
    0x05: 'produce', 0x06: 'produce_stop', 0x07: 'build', 0x08: 'build_stop', 0x09: 'place', 0x0A: 'sell',
    0x0C: 'ungarrison?', 0x0D: 'attack', 0x0E: 'force_fire', 0x10: 'garrison', 0x14: 'move', 0x15: 'attack_move',
    0x16: 'force_move', 0x1A: 'stop', 0x21: 'heartbeat', 0x28: 'repair', 0x29: 'repair_stop', 0x2A: 'q_select',
    0x2C: 'formation_preview', 0x2E: 'stance', 0x2F: 'plan?', 0x32: 'power_target', 0x37: 'tick', 0x4B: 'beacon',
    0x4C: 'beacon_del', 0x4E: 'player_power', 0xF5: 'select', 0xF8: 'click', 0xFA: 'group_make',
    0xFB: 'group_select', 0xFE: 'ability', 0xFF: 'power_select_click',
}


class Reader:
    def __init__(self, data, pos=0):
        self.d, self.p = data, pos

    def take(self, n):
        b = self.d[self.p:self.p + n]
        if len(b) < n:
            raise EOFError(self.p)
        self.p += n
        return b

    def u8(self):
        return self.take(1)[0]

    def u32(self):
        return struct.unpack('<I', self.take(4))[0]

    def wstr(self):
        out = []
        while True:
            c = struct.unpack('<H', self.take(2))[0]
            if not c:
                return ''.join(out)
            out.append(chr(c))


def header(r):
    h = {}
    magic = r.take(17)
    if magic != b'RA3 REPLAY HEADER':
        raise ValueError('not an RA3 replay: %r' % magic)
    h['kind'] = r.u8()                     # 4 skirmish, 5 multiplayer (community guess)
    h['version'] = (r.u32(), r.u32(), r.u32(), r.u32())
    h['commentary'] = r.u8()
    r.u8()
    h['title'], h['description'], h['map_name'], h['map_id'] = r.wstr(), r.wstr(), r.wstr(), r.wstr()
    n = r.u8()
    h['players'] = []
    for _ in range(n + 1):
        pid, name = r.u32(), r.wstr()
        team = r.u8() if h['kind'] == 5 else None
        h['players'].append((pid, name, team))
    r.u32()                                # offset to CNC3RPL
    if r.u32() != 8 or r.take(8) != b'CNC3RPL\0':
        raise ValueError('CNC3RPL marker not found at %d' % r.p)
    h['mod'] = [t.decode('latin1') for t in r.take(22).split(b'\0') if t]
    h['timestamp'] = r.u32()
    r.take(31)
    text = r.take(r.u32()).decode('latin1')
    h['text'] = text
    kv = dict(item.split('=', 1) for item in text.split(';') if '=' in item)
    h['map_path'] = kv.get('M', '')[3:]
    h['seed'] = int(kv['SD']) if 'SD' in kv else None
    h['slots'] = [s.split(',') for s in kv.get('S', '').split(':') if s]
    h['saver'] = r.u8()
    r.u32(), r.u32()
    h['filename'] = r.take(2 * r.u32()).decode('utf-16le')
    h['date'] = struct.unpack('<8H', r.take(16))
    h['vermagic'] = r.take(r.u32()).decode('latin1')
    h['hash'] = r.u32()
    r.u8()
    r.take(4 * 20)
    return h


def commands(data):
    """Split a type-1 chunk's body into (id, player_byte, body bytes). Stops at the first unknown layout."""
    r = Reader(data)
    if r.u8() != 1:
        raise ValueError('command chunk does not start with 1')
    n = r.u32()
    out = []
    for _ in range(n):
        start = r.p
        cid, player = r.u8(), r.u8()
        size = SIZES.get(cid, 'missing')
        if isinstance(size, int):
            r.p = start + size
            if data[r.p - 1] != 0xFF:
                out.append((cid, player, None, 'size %d does not end in FF' % size))
                return out, n
        elif isinstance(size, tuple):
            r.p = start + size[1]
            while True:
                x = r.u8()
                if x == 0xFF:
                    break
                r.take(4 * ((x >> 4) + 1))
        else:
            out.append((cid, player, None, 'layout unknown' if size is None else 'id not in table'))
            return out, n
        out.append((cid, player, data[start + 2:r.p - 1], None))
    return out, n


# Argument groups (seen in our replays, 2026-11-08): byte x = (count - 1) << 4 | type, then count items.
# type 0 int, 1 float, 2 bool (1 byte), 4 object id, 7 position (3 floats); others taken as 4 bytes until seen.
# Object ids are the engine's ObjectIDs (a skirmish start's MCV was 973 / 1876: map objects come first);
# template ints are FastHash(lower-case template name) (experimental/campaign/sagehash.py): 0x89b86e3d =
# alliedpowerplant, 0x509bd329 = alliedbarracks. The heartbeat (0x21) does not follow this layout.
TYPES = {0: 'int', 1: 'float', 2: 'bool', 4: 'obj', 7: 'pos'}
HEADER = {cid: s[1] - 2 for cid, s in SIZES.items() if isinstance(s, tuple)}


def args(cid, body):
    """[(type name, [values])] of one command body (without id, player, 0xFF); None if it does not fit."""
    p, out = HEADER.get(cid, 0), []
    while p < len(body):
        x = body[p]
        n, t = (x >> 4) + 1, x & 15
        p += 1
        if t == 2:
            vals = list(body[p:p + n])
            p += n
        elif t == 7:
            vals = [struct.unpack_from('<3f', body, p + 12 * i) for i in range(n)]
            p += 12 * n
        else:
            vals = list(struct.unpack_from('<%d%s' % (n, 'f' if t == 1 else 'I'), body, p))
            p += 4 * n
        out.append((TYPES.get(t, 't%d' % t), vals))
    return out if p == len(body) else None


def chunks(r):
    while True:
        t = r.u32()
        if t == END:
            return
        kind, size = r.u8(), r.u32()
        data = r.take(size)
        r.u32()
        yield t, kind, data


def read(path):
    data = open(path, 'rb').read()
    r = Reader(data)
    h = header(r)
    h['chunks'] = []
    h['truncated'] = False
    try:
        for c in chunks(r):
            h['chunks'].append(c)
        h['footer'] = r.take(17) == b'RA3 REPLAY FOOTER'
        h['final_time'] = r.u32()
    except EOFError:
        h['truncated'] = True
    return h


def summary(path, verbose=False):
    h = read(path)
    print('%s: %s, map %s, seed %s, version %s, players %s%s' % (
        path, h['title'], h['map_path'], h['seed'], h['version'],
        [p[1] for p in h['players'] if p[1]], ' (TRUNCATED)' if h['truncated'] else ''))
    kinds = Counter(k for _, k, _ in h['chunks'])
    last = h['chunks'][-1][0] if h['chunks'] else 0
    print('  chunks %s, last time code %d (%.0f s)' % (dict(kinds), last, last / 15))
    ids, stuck, total, parsed = Counter(), Counter(), 0, 0
    for t, kind, data in h['chunks']:
        if kind != 1:
            continue
        cmds, n = commands(data)
        total += n
        for cid, player, body, err in cmds:
            if err:
                stuck['0x%02X %s: %s' % (cid, NAMES.get(cid, '?'), err)] += 1
            else:
                parsed += 1
                ids['0x%02X %s' % (cid, NAMES.get(cid, '?'))] += 1
                if verbose and cid not in (0x21, 0x37):
                    print('   t=%d p=%d %s %s' % (t, player, NAMES.get(cid, hex(cid)), body.hex()))
    print('  commands %d, parsed %d (%.0f%%)' % (total, parsed, 100 * parsed / max(total, 1)))
    print('  by id:', dict(ids.most_common()))
    if stuck:
        print('  chunks stopped at:', dict(stuck.most_common()))
    return h


if __name__ == '__main__':
    for a in sys.argv[1:]:
        if not a.startswith('--'):
            summary(a, '--verbose' in sys.argv)
