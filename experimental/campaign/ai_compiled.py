r"""The compiled AIStrategicStateDefinition instances of the game's global stream, read back into SDK-shaped xml.

The retail campaign maps' own strategic states (and the SDK's) exist in the game only compiled; their xml was not
shipped. decode() turns one compiled instance into the element the SDK xml would have been, flattened (inheritance is
resolved at compile time), so inventory_ai.reached / element_names can count what it writes.

Where every field sits in the compiled struct is not in this repository (public; tests/test_no_program_addresses):
it is measured by compiling a base state and one-attribute variants with the SDK's BinaryAssetBuilder and diffing them
(engine line B round 169), kept in the private work/re as LAYOUT; without it this module stops with a SystemExit.

What comes back: an attribute is written when its compiled bytes differ from the base state's (the xsd default), an
optional attribute when its pointer is set, a list / child element when present. INFERRED: an attribute written with
its default value is indistinguishable from one not written, so the count is a lower bound. Values are the enum or flag
names for the selector attributes and Difficulty, asset names for references; other values are the raw integer.
"""
import json
import os
import struct
import xml.etree.ElementTree as ET

import labpaths

LAYOUT = os.path.join(labpaths.WORK, 're', 'b169_layout.json')
TYPE = 'AIStrategicStateDefinition'


def layout():
    if not os.path.exists(LAYOUT):
        raise SystemExit(f'ai_compiled: the compiled AI layout is not here: {LAYOUT} (private work/re; engine line B '
                         'measures it with work/re/scripts/b169_layout.py)')
    return json.load(open(LAYOUT, encoding='utf-8'))


def _u32(data, o):
    return struct.unpack_from('<I', data, o)[0]


def _i32(data, o):
    return struct.unpack_from('<i', data, o)[0]


class _Reader:
    def __init__(self, lay, data, imports, refname):
        self.L, self.d, self.imp, self.ref = lay, data, imports, refname
        self.hashes = {v['hash']: k for k, v in lay['heuristics'].items()}

    def fields(self, el, tag, spec, base):
        """Write the attributes of the struct at base whose bytes differ from the default."""
        default = bytes.fromhex(spec['default'])
        req = set(self.L['required'].get(tag, ()))
        for attr, (o, w, kind) in spec['fields'].items():
            got = self.d[base + o:base + o + w]
            if kind == 'ptr':
                p = _u32(self.d, base + o)
                if not p:
                    continue
                key = f'{tag}.{attr}'
                names = self.L['pointed_enums'].get(key)
                el.set(attr, names[_i32(self.d, p)] if names and 0 <= _i32(self.d, p) < len(names)
                       else str(_i32(self.d, p)))
                continue
            if got == default[o:o + w] and attr not in req:
                continue
            el.set(attr, self.value(tag, attr, got))
        for attr in req:
            if attr not in el.attrib:
                o = self.L['imports'].get(tag, {}).get(attr)
                el.set(attr, self.ref(base + o) if o is not None else '?')

    def value(self, tag, attr, got):
        key = f'{tag}.{attr}'
        if len(got) == 1:
            return 'true' if got[0] else 'false'
        n = struct.unpack_from('<i', got)[0] if len(got) == 4 else None
        if key in self.L['enums'] and n is not None:
            name = self.L['enums'][key].get(str(n), str(n))
            return self.L['enum_defaults'].get(key, name) if name == '(default)' else name
        if key in self.L['bits'] and n is not None:
            return ' '.join(b for k, b in enumerate(self.L['bits'][key]) if n >> k & 1)
        return str(n) if n is not None else got.hex()

    def struct(self, parent, tag, sname, base):
        el = ET.SubElement(parent, tag) if parent is not None else ET.Element(tag)
        self.fields(el, tag, self.L['structs'][sname], base)
        self.children(el, tag, base)
        return el

    def children(self, el, tag, base):
        for child, (o, sname) in self.L['inline'].get(tag, {}).items():
            self.struct(el, child, sname, base + o)
        for child, (o, sname) in self.L['pointers'].get(tag, {}).items():
            p = _u32(self.d, base + o)
            if p:
                self.struct(el, child, sname, p)
        for child, (co, po, sname) in self.L['lists'].get(tag, {}).items():
            n, p = _u32(self.d, base + co), _u32(self.d, base + po)
            if sname == 'heuristic':
                h = ET.SubElement(el, 'Heuristic')
                for k in range(n):
                    self.heuristic(h, _u32(self.d, p + 4 * k))
            elif sname == 'thing':
                for k in range(n):
                    ET.SubElement(el, child).text = f'{_u32(self.d, p + 4 * k):08x}'
            else:
                size = self.L['structs'][sname]['size']
                for k in range(n):
                    self.struct(el, child, sname, p + size * k)

    def heuristic(self, parent, base):
        name = self.hashes.get(_u32(self.d, base))
        if name is None:
            ET.SubElement(parent, 'UnknownHeuristic', Type=f'{_u32(self.d, base):08x}')
            return
        el = ET.SubElement(parent, name)
        self.fields(el, name, self.L['heuristics'][name], base)
        self.children(el, name, base)


def decode(name, data, imports, refnames, lay=None):
    """The <AIStrategicStateDefinition id=name> element of one compiled instance: data (its bytes), imports (its
    import offsets, in order) and refnames (the names of its references, same order)."""
    lay = lay or layout()
    imp = list(imports)

    def ref(o):
        return refnames[imp.index(o)].split(':')[-1] if o in imp and imp.index(o) < len(refnames) else '?'
    r = _Reader(lay, data, imp, ref)
    el = r.struct(None, TYPE, TYPE, 0)
    el.set('id', name)
    order = ['Heuristic', 'TargetHeuristic', 'Tactic']
    el[:] = sorted(el, key=lambda c: order.index(c.tag) if c.tag in order else 9)
    return el


def decode_stream(inst):
    """{state name: element} over a mapxml.layered() result."""
    lay = layout()
    names = {k: (i.name.decode('latin-1') if isinstance(i.name, bytes) else i.name) for k, i in inst.items()}
    out = {}
    for k, i in inst.items():
        if not names[k].startswith(TYPE + ':'):
            continue
        data, _, imp = (bytes(c) for c in i.chunks)
        imports = [x for x in struct.unpack('<%dI' % (len(imp) // 4), imp) if x != 0xffffffff]
        refnames = [names.get(tuple(r), '?') for r in i.refs]
        out[names[k].split(':', 1)[1]] = decode(names[k].split(':', 1)[1], data, imports, refnames, lay)
    return out
