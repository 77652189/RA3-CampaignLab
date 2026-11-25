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

full=True (the engine model's copy, retailref ai_states_sdk.xml) writes every field, defaults too, and the strings'
text (a compiled string is {length, pointer}, the pointer in the instance's relocations); to_sdk() then turns the raw
values into the SDK's spelling by the SDK xsd's attribute types (floats, times, percentages, enums by their xsd order,
flag lists, KindOf masks, references by name). INFERRED: an enum's compiled value is its index in the xsd -- the 175
strategic states the SDK and retail both have come back equal under it (engine line B, E238).
"""
import functools
import glob
import json
import os
import re
import struct
import xml.etree.ElementTree as ET

import labpaths

LAYOUT = os.path.join(labpaths.WORK, 're', 'b169_layout.json')
# personalities, build and budget states (engine line B round 171, work/re/scripts/b171_layout.py), merged over LAYOUT
LAYOUT_MORE = os.path.join(labpaths.WORK, 're', 'b171_layout.json')
TYPE = 'AIStrategicStateDefinition'
ORDER = {TYPE: ['Heuristic', 'TargetHeuristic', 'Tactic']}


def layout():
    for path in (LAYOUT, LAYOUT_MORE):
        if not os.path.exists(path):
            raise SystemExit(f'ai_compiled: the compiled AI layout is not here: {path} (private work/re; engine line B '
                             'measures it with work/re/scripts/b169_layout.py / b171_layout.py)')
    lay = json.load(open(LAYOUT, encoding='utf-8'))
    lay['roots'] = {TYPE: TYPE}
    for key, more in json.load(open(LAYOUT_MORE, encoding='utf-8')).items():
        if key == 'bits_by_type':
            continue
        cur = lay.setdefault(key, {})
        for k, v in more.items():
            if isinstance(v, dict) and isinstance(cur.get(k), dict):
                cur[k] = {**cur[k], **v}
            else:
                cur.setdefault(k, v)
    lay.setdefault('imports_opt', {})
    return lay


def _u32(data, o):
    return struct.unpack_from('<I', data, o)[0]


def _i32(data, o):
    return struct.unpack_from('<i', data, o)[0]


class _Reader:
    def __init__(self, lay, data, imports, refname, relocs=(), full=False):
        self.L, self.d, self.imp, self.ref = lay, data, imports, refname
        self.rel, self.full = set(relocs), full
        self.hashes = {v['hash']: k for k, v in lay['heuristics'].items()}
        self.sname = {}

    def string(self, attr, o, taken=(), end=None):
        """The text of the compiled string {length, pointer} at o (full mode only, attr an xs:string somewhere in the
        xsd), None where o + 4 holds no pointer of its own (taken: the struct's other fields / children; end: the
        struct's end) or the text is not ASCII."""
        if not self.full or attr not in _string_attrs() or o + 4 not in self.rel or o + 4 in taken \
                or (end is not None and o + 8 > end):
            return None
        n, p = _u32(self.d, o), _u32(self.d, o + 4)
        s = self.d[p:p + n]
        return s.decode('ascii') if len(s) == n and all(32 <= c < 127 for c in s) else None

    def fields(self, el, tag, spec, base):
        """Write the attributes of the struct at base whose bytes differ from the default (full: all of them)."""
        default = bytes.fromhex(spec['default'])
        req = set(self.L['required'].get(tag, ()))
        taken = {base + f[0] for f in spec['fields'].values()}
        for t in {tag, self.sname.get(tag, tag)}:
            taken |= {base + v[0] for v in self.L['pointers'].get(t, {}).values()}
            taken |= {base + v[1] for v in self.L['lists'].get(t, {}).values()}
        for attr, (o, w, kind) in spec['fields'].items():
            got = self.d[base + o:base + o + w]
            if kind == 'ptr':
                p = _u32(self.d, base + o)
                if not p:
                    continue
                s = self.string(attr, p)
                if s is not None:
                    el.set(attr, s)
                    continue
                key = f'{tag}.{attr}'
                names = self.L['pointed_enums'].get(key)
                el.set(attr, names[_i32(self.d, p)] if names and 0 <= _i32(self.d, p) < len(names)
                       else str(_i32(self.d, p)))
                continue
            s = self.string(attr, base + o, taken, base + spec["size"]) if w == 4 else None
            if s is not None:
                el.set(attr, s)
                continue
            if got == default[o:o + w] and attr not in req and not self.full:
                continue
            el.set(attr, self.value(tag, attr, got))
        for attr, o in self.L['imports_opt'].get(tag, {}).items():
            if base + o in self.imp:
                el.set(attr, self.ref(base + o))
        for attr in self.L['required'].get(tag, ()):        # in order: the file comes out the same every run
            if attr not in el.attrib:
                o = self.L['imports'].get(tag, {}).get(attr)
                el.set(attr, self.ref(base + o) if o is not None else '?')

    def value(self, tag, attr, got):
        key = f'{tag}.{attr}'
        if key not in self.L['enums'] and key not in self.L['bits']:    # a shared struct under another tag
            key = f'{self.sname.get(tag, tag)}.{attr}'
        if len(got) == 1:
            return 'true' if got[0] else 'false'
        n = struct.unpack_from('<i', got)[0] if len(got) == 4 else None
        if key in self.L['enums'] and n is not None:
            name = self.L['enums'][key].get(str(n), str(n))
            if name == '(default)':     # full: the number, for to_sdk's xsd enum (SovietCrane's CONSTANT is 0)
                return self.L['enum_defaults'].get(key, str(n) if self.full else name)
            return name
        if key in self.L['bits'] and n is not None:
            return ' '.join(b for k, b in enumerate(self.L['bits'][key]) if n >> k & 1)
        return str(n) if n is not None else got.hex()

    def struct(self, parent, tag, sname, base):
        el = ET.SubElement(parent, tag) if parent is not None else ET.Element(tag)
        self.sname[tag] = 'ObjectFilter' if sname == 'ObjectFilter' else 'TargetBaseCriteria' if sname == 'BaseCriteria' \
            else sname                          # b169 keys BaseCriteria enums by TargetBaseCriteria
        self.fields(el, tag, self.L['structs'][sname], base)
        self.children(el, tag, base)
        return el

    def children(self, el, tag, base):
        if not any(tag in self.L[k] for k in ('inline', 'pointers', 'lists')):
            tag = self.sname.get(tag, tag)          # a shared struct under another tag (an ObjectFilter)
        for child, (o, sname) in self.L['inline'].get(tag, {}).items():
            self.struct(el, child, sname, base + o)
        for child, (o, sname) in self.L['pointers'].get(tag, {}).items():
            p = _u32(self.d, base + o)
            if p and sname == 'heuristic':          # OpeningMove: a pointer to {count, pointer array} of heuristics
                h = ET.SubElement(el, child)
                for k in range(_u32(self.d, p)):
                    self.heuristic(h, _u32(self.d, _u32(self.d, p + 4) + 4 * k))
            elif p:
                self.struct(el, child, sname, p)
        for child, (co, po, sname) in self.L['lists'].get(tag, {}).items():
            n, p = _u32(self.d, base + co), _u32(self.d, base + po)
            if sname == 'heuristic':
                h = ET.SubElement(el, 'Heuristic')
                for k in range(n):
                    self.heuristic(h, _u32(self.d, p + 4 * k))
            elif sname == 'thing':          # a name hash, or a reference (a personality's Side) in full mode
                for k in range(n):
                    ET.SubElement(el, child).text = self.ref(p + 4 * k) if self.full and p + 4 * k in self.imp \
                        else f'{_u32(self.d, p + 4 * k):08x}'
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


def decode(name, data, imports, refnames, lay=None, typ=TYPE, relocs=(), full=False):
    """The <typ id=name> element of one compiled instance (typ: a layout root, AIStrategicStateDefinition /
    AIPersonalityDefinition / AIBuildStateDefinition / AIBudgetStateDefinition): data (its bytes), imports (its
    import offsets, in order) and refnames (the names of its references, same order); relocs (its pointer offsets)
    and full: the module doc."""
    lay = lay or layout()
    imp = list(imports)

    def ref(o):
        return refnames[imp.index(o)].split(':')[-1] if o in imp and imp.index(o) < len(refnames) else '?'
    r = _Reader(lay, data, imp, ref, relocs, full)
    el = r.struct(None, typ, lay['roots'][typ], 0)
    el.set('id', name)
    order = ORDER.get(typ)
    if order:
        el[:] = sorted(el, key=lambda c: order.index(c.tag) if c.tag in order else 9)
    return el


def _offsets(chunk):
    return [x for x in struct.unpack('<%dI' % (len(chunk) // 4), chunk) if x != 0xffffffff]


def asset_names(inst):
    """{(type id, instance id): 'Type:Name'} of a mapxml.layered() result."""
    return {k: (i.name.decode('latin-1') if isinstance(i.name, bytes) else i.name) for k, i in inst.items()}


def decode_stream(inst, full=False, more=None):
    """{asset name: element} of every compiled instance of a layout root type over a mapxml.layered() result; full:
    every field, in the SDK's spelling (to_sdk, the hashes named by the asset ids of this stream and of `more`, another
    layered() result: the GameObjects are in the static stream)."""
    lay = layout()
    names = asset_names(inst)
    hashed = {k[1]: n.split(':', 1)[-1] for k, n in {**asset_names(more or {}), **names}.items()}   # instance id =
    #                                                                                   FastHash(lower-case name)
    out = {}
    for k, i in inst.items():
        typ, _, name = names[k].partition(':')
        if typ not in lay['roots']:
            continue
        data, rel, imp = (bytes(c) for c in i.chunks)
        refnames = [names.get(tuple(r), '?') for r in i.refs]
        out[name] = decode(name, data, _offsets(imp), refnames, lay, typ, _offsets(rel), full)
        if full:
            to_sdk(out[name], hashed)
    return out


# ---- raw compiled values -> the SDK's spelling, by the SDK xsd's attribute types (full mode)
XSD = os.path.join(labpaths.SDK3, 'Schemas', 'xsd')
_XS = '{http://www.w3.org/2001/XMLSchema}'
FLOATS = {'xs:float', 'SageReal', 'Time', 'Percentage', 'Angle', 'Velocity', 'SageDuration'}
STRINGS = {'xs:string'}
_INT = re.compile(r'-?\d+$')


def _numbered(enumerations):
    """{compiled value: name} of an xsd enumeration: xas:forceValue where given, else one past the previous (from 0).
    INFERRED: an INVALID opening without a forceValue is -1 too -- PathToTargetHeuristic's default
    LocomotorConditionToUseForTest (LocomotorSetType: INVALID, NORMAL, ...) compiles NORMAL as 0."""
    out, n = {}, -1
    for k, e in enumerate(enumerations):
        force = next((v for a, v in e.attrib.items() if a.endswith('forceValue')), None)
        if force is not None and not _INT.match(force):         # an alias: forceValue="CAPTURED"
            n = next((m for m, name in out.items() if name == force), n + 1)
            continue
        n = int(force) if force is not None else -1 if k == 0 and e.get('value') == 'INVALID' else n + 1
        out[n] = e.get('value')
    return out


@functools.lru_cache(maxsize=1)
def _xsd():
    """(simple types {name: ('enum', values) / ('list', item) / ('restrict', base)}, complex types {name: (attrs
    {name: type}, children {name: type}, base type)}) of every SDK xsd."""
    simple, complex_ = {}, {}
    for f in glob.glob(os.path.join(XSD, '**', '*.xsd'), recursive=True):
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        for st in root.iter(_XS + 'simpleType'):
            if st.get('name'):
                en = _numbered([e for e in st.iter(_XS + 'enumeration')])
                li, rs = st.find(_XS + 'list'), st.find(_XS + 'restriction')
                simple[st.get('name')] = ('enum', en) if en else ('list', li.get('itemType')) if li is not None \
                    else ('restrict', rs.get('base') if rs is not None else '?')
        for ct in root.iter(_XS + 'complexType'):
            if ct.get('name'):
                ext = ct.find('.//' + _XS + 'extension')
                complex_[ct.get('name')] = ({a.get('name'): a.get('type') for a in ct.iter(_XS + 'attribute')},
                                            {e.get('name'): e.get('type') for e in ct.iter(_XS + 'element')},
                                            ext.get('base') if ext is not None else None)
    return simple, complex_


@functools.lru_cache(maxsize=1)
def _string_attrs():
    """The attribute names some xsd complex type declares xs:string (where full mode reads a compiled string)."""
    return frozenset(a for attrs, _, _ in _xsd()[1].values() for a, t in attrs.items() if t in STRINGS)


def _lookup(t, k, which):
    """The type of attribute (which 0) / child (which 1) k of complex type t, up its extension chain."""
    seen, cx = set(), _xsd()[1]
    while t in cx and t not in seen:
        seen.add(t)
        if k in cx[t][which]:
            return cx[t][which][k]
        t = cx[t][2]
    return None


def _base(t):
    simple = _xsd()[0]
    for _ in range(8):
        if t in FLOATS or t not in simple or simple[t][0] != 'restrict':
            break
        t = simple[t][1]
    return t


def _num(x):
    return f'{x:.6g}'


def _value(t, v, names):
    """The SDK spelling of raw value v of xsd type t (None: drop the attribute)."""
    b, simple = _base(t), _xsd()[0]
    if v in ('?', '(default)') or (t in STRINGS and v == '0'):   # an unread reference / enum, an empty string
        return None
    hexmask = b in simple and simple[b][0] == 'list' and re.fullmatch(r'[0-9a-f]{16,}', v)
    if not _INT.match(v) and not hexmask:
        return v
    if b in FLOATS:
        x = struct.unpack('<f', struct.pack('<i', int(v)))[0]
        return _num(x) + 's' if b == 'Time' else _num(x * 100) + '%' if b == 'Percentage' else _num(x)
    if b in simple and simple[b][0] == 'enum':
        return simple[b][1].get(int(v), v)
    if b in simple and simple[b][0] == 'list':
        en = simple.get(_base(simple[b][1]), ('', {}))[1]
        if hexmask:                                     # a KindOf-like byte mask
            bits = [k * 8 + j for k, byte in enumerate(bytes.fromhex(v)) for j in range(8) if byte >> j & 1]
        else:
            bits = [k for k in range(32) if (int(v) & 0xffffffff) >> k & 1]
        return ' '.join(en.get(k, f'#{k}') for k in bits)
    if t and ('WeakRef' in t or t.endswith('Ref')):
        return None if int(v) == 0 else names.get(int(v) & 0xffffffff, v)       # 0: no reference
    return v


def to_sdk(el, names, t=None):
    """el (a full-mode decode) rewritten in place in the SDK's spelling: names {FastHash: asset name}. A personality's
    choice lines (StrategicState / BudgetState / BuildState: the compiled form keeps no id) get their State as id,
    numbered when one repeats (the engine model merges choices by id)."""
    t = t or el.tag
    for a, v in list(el.attrib.items()):
        if a == 'id':
            continue
        got = _value(_lookup(t, a, 0), v, names)
        if got is None:
            del el.attrib[a]
        else:
            el.set(a, got)
    seen = {}
    for c in el:
        kt = _lookup(t, c.tag, 1)
        if c.text and re.fullmatch(r'[0-9a-f]{8}', c.text) and kt and ('Ref' in kt or 'Thing' in c.tag):
            c.text = names.get(int(c.text, 16), c.text)
        to_sdk(c, names, kt)
        if t == 'AIPersonalityDefinition' and c.tag in ('StrategicState', 'BudgetState', 'BuildState'):
            key = c.get('State', '')
            seen[key] = seen.get(key, 0) + 1
            c.set('id', key if seen[key] == 1 else f'{key}#{seen[key]}')
    return el
