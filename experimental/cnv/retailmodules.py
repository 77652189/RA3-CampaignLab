"""Which object-module types and weapon-effect (nugget) types the retail RA3 data uses.

module_census()  -> {(group, module_type): {'templates', 'campaign', 'examples'}}
weapon_census()  -> {nugget_type: {'weapons', 'examples'}}
effective_modules(template_id) -> [(group, module_type, module_id)]

Rules: a GameObject's modules are the children of its Behaviors/Body/AI/Draws/ClientBehaviors groups.
An xi:include (href DATA:x.xml or relative) in a group is replaced by the included file's root element (no
xpointer) or by the children of the element the xpointer '/n:Root/child::*' names (nested includes resolve
too). inheritFrom: the parent's effective modules first; a child module with the same id in the same group
replaces the parent's, the others are added. Retail data has no RemoveModule/ChildObject.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (os.path.join(os.path.dirname(HERE), 'campaign'),) if p not in sys.path]
import labpaths  # noqa: E402

SAGEXML = os.path.join(labpaths.SDK3, 'SageXML')
RETAILREF = os.path.join(labpaths.WORK, 'retailref')
GROUPS = ('Behaviors', 'Body', 'AI', 'Draws', 'ClientBehaviors')
XI = 'include'

_state = None
_census = None
_wcensus = None
unresolved = {'include': 0, 'parse': 0}
_incl_cache = {}


def _check_dirs():
    for p in (SAGEXML, RETAILREF):
        assert os.path.isdir(p), 'retailmodules: required directory missing: %s' % p


def _tag(e):
    t = e.tag
    return t.split('}', 1)[1] if isinstance(t, str) and t.startswith('{') else t


def _parse(path):
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError, UnicodeDecodeError):
        try:  # some retail files declare one encoding but hold other bytes
            txt = open(path, encoding='utf-8', errors='replace').read()
            txt = re.sub(r'^<\?xml[^>]*\?>', '', txt.lstrip())
            return ET.fromstring(txt)
        except ET.ParseError:
            return None


def _resolve_href(base_file, href):
    if href.startswith('DATA:'):
        return os.path.join(SAGEXML, *href[5:].split('/'))
    return os.path.normpath(os.path.join(os.path.dirname(base_file), href))


def _include_elements(base_file, inc, depth=0):
    """The module elements an xi:include stands for."""
    href = inc.get('href')
    if not href or depth > 8:
        return []
    path = _resolve_href(base_file, href)
    key = (path, inc.get('xpointer'))
    if key in _incl_cache:
        return _incl_cache[key]
    root = _parse(path) if os.path.isfile(path) else None
    out = []
    if root is None:
        unresolved['include'] += 1
    else:
        xp = inc.get('xpointer')
        m = re.search(r'xpointer\(/n:([\w.]+)/child::\*\)', xp or '')
        kids = []
        if m:
            tgt = root if _tag(root) == m.group(1) else next((e for e in root.iter() if _tag(e) == m.group(1)), None)
            if tgt is None:
                unresolved['include'] += 1
            else:
                kids = list(tgt)
        elif xp:
            unresolved['include'] += 1
        else:
            kids = [root]
        for k in kids:
            if not isinstance(k.tag, str):
                continue
            if _tag(k) == XI:
                out.extend(_include_elements(path, k, depth + 1))
            else:
                out.append(k)
    _incl_cache[key] = out
    return out


def _group_modules(path, grp):
    res = []
    for e in list(grp):
        if not isinstance(e.tag, str):
            continue
        if _tag(e) == XI:
            res.extend(_include_elements(path, e))
        else:
            res.append(e)
    return res


def _load():
    global _state
    if _state is not None:
        return _state
    _check_dirs()
    objs = {}      # lower id -> (id, own modules {group: [(type, id)]}, parent lower or None)
    weapons = {}   # lower id -> (id, nugget types, parent lower or None)
    for root_dir, _, files in sorted(os.walk(SAGEXML)):
        for f in sorted(files):
            if not f.endswith('.xml'):
                continue
            p = os.path.join(root_dir, f)
            txt = open(p, encoding='utf-8', errors='replace').read()
            if '<GameObject' not in txt and '<WeaponTemplate' not in txt:
                continue
            root = _parse(p)
            if root is None:
                unresolved['parse'] += 1
                continue
            override = 'CampaignOverrides' in p
            for e in root.iter():
                t = _tag(e)
                if t == 'GameObject' and e.get('id'):
                    k = e.get('id').lower()
                    if k in objs and override:
                        continue
                    own = {}
                    for g in e:
                        if _tag(g) in GROUPS:
                            own.setdefault(_tag(g), []).extend(
                                (_tag(m), m.get('id') or m.get('ID') or '') for m in _group_modules(p, g))
                    objs[k] = (e.get('id'), own, (e.get('inheritFrom') or '').lower() or None)
                elif t == 'WeaponTemplate' and e.get('id'):
                    k = e.get('id').lower()
                    if k in weapons and override:
                        continue
                    nug = [_tag(n) for n in e.iter() if _tag(n).endswith('Nugget')]
                    weapons[k] = (e.get('id'), nug, (e.get('inheritFrom') or '').lower() or None)
    _state = {'objs': objs, 'weapons': weapons, 'eff': {}}
    return _state


def _effective(k, st, seen=()):
    eff = st['eff']
    if k in eff:
        return eff[k]
    if k not in st['objs'] or k in seen:
        return []
    _, own, parent = st['objs'][k]
    mods = {}
    if parent:
        for g, t, i in _effective(parent, st, seen + (k,)):
            mods.setdefault(g, []).append((t, i))
    for g, lst in own.items():
        cur = mods.setdefault(g, [])
        for typ, mid in lst:
            idx = next((n for n, (_, i2) in enumerate(cur) if mid and i2 == mid), None)
            if idx is None:
                cur.append((typ, mid))
            else:
                cur[idx] = (typ, mid)
    eff[k] = [(g, t, i) for g in GROUPS for (t, i) in mods.get(g, [])]
    return eff[k]


def effective_modules(template_id):
    st = _load()
    return list(_effective(str(template_id).lower(), st))


def _campaign_templates():
    out = set()
    for f in os.listdir(RETAILREF):
        if f.endswith('.json') and f != 'index.json':
            try:
                d = json.load(open(os.path.join(RETAILREF, f), encoding='utf-8'))
            except ValueError:
                continue
            for o in d.get('objects', []):
                if isinstance(o, dict) and o.get('t'):
                    out.add(str(o['t']).lower())
    return out


def module_census():
    global _census
    if _census is not None:
        return _census
    st = _load()
    camp = _campaign_templates()
    res = {}
    for k, (name, _, _) in st['objs'].items():
        for key in sorted({(g, t) for g, t, _ in _effective(k, st)}):
            r = res.setdefault(key, {'templates': 0, 'campaign': 0, 'examples': []})
            r['templates'] += 1
            if k in camp:
                r['campaign'] += 1
            if len(r['examples']) < 3:
                r['examples'].append(name)
    _census = res
    return res


def without_ai(mtype):
    """{'templates': n, 'campaign': n}: the templates carrying module `mtype` but no AI update module (no *AIUpdate:
    nothing orders them, no locomotor) -- inventory.module_items splits Physics on it (engine line E, work/re
    e_na_physics_mcu.md: a still thing's default physics moves nothing the simulator plays; a fling is DynamicsUpdate's,
    a knock MetaImpactNugget's, items of their own)."""
    st = _load()
    camp = _campaign_templates()
    out = {'templates': 0, 'campaign': 0}
    for k in st['objs']:
        names = {t for _, t, _ in _effective(k, st)}
        if mtype in names and not any(t.endswith('AIUpdate') for t in names):
            out['templates'] += 1
            out['campaign'] += k in camp
    return out


def _weapon_nuggets(k, st, seen=()):
    if k not in st['weapons'] or k in seen:
        return []
    _, nug, parent = st['weapons'][k]
    return (_weapon_nuggets(parent, st, seen + (k,)) if parent else []) + nug


def weapon_census():
    global _wcensus
    if _wcensus is not None:
        return _wcensus
    st = _load()
    res = {}
    for k, (name, _, _) in st['weapons'].items():
        for t in sorted(set(_weapon_nuggets(k, st))):
            r = res.setdefault(t, {'weapons': 0, 'examples': []})
            r['weapons'] += 1
            if len(r['examples']) < 3:
                r['examples'].append(name)
    _wcensus = res
    return res


def main(argv):
    import time
    t0 = time.time()
    mc, wc = module_census(), weapon_census()
    st = _load()
    print('templates scanned: %d, weapons scanned: %d, module types: %d, nugget types: %d (%.1f s)'
          % (len(st['objs']), len(st['weapons']), len(mc), len(wc), time.time() - t0))
    print('unresolved includes: %(include)d, unparsable files: %(parse)d' % unresolved)
    top = sorted(mc.items(), key=lambda kv: -kv[1]['templates'])
    print('top module types (group type templates/campaign):')
    for (g, t), r in (top if '--verbose' in argv else top[:25]):
        print('  %-15s %-40s %5d / %d' % (g, t, r['templates'], r['campaign']))
    print('nugget types (weapons):')
    for t, r in sorted(wc.items(), key=lambda kv: -kv[1]['weapons']):
        print('  %-40s %5d' % (t, r['weapons']))


if __name__ == '__main__':
    main(sys.argv[1:])
