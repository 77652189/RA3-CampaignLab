r"""What the plan simulator (sim.py) needs of a unit, from the game's own data: how fast it goes, on what (ground,
water, both, air), how far it sees, its KindOf. Retail templates from the SDK's SageXML (the index mapstudy keeps:
work\sagexml_gameobjects.json gives each template's file and KindOf; the file its LocomotorSet's NORMAL Speed and its
VisionRange / ShroudClearingRange, defines resolved), cached in work\sim_units_v2.json. Our own units (a mission's Unit: its XML) are read
the same way from their XML; a template found nowhere gets its kind's default (DEFAULTS) and is listed as guessed.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
import labpaths  # noqa: E402

CACHE = os.path.join(labpaths.WORK, 'sim_units_v2.json')     # v2: defines resolved (2026-10-29)
INDEX = os.path.join(labpaths.WORK, 'sagexml_gameobjects.json')
SAGEXML = os.path.join(labpaths.SDK3, 'SageXML')
LOCOMOTORS = os.path.join(SAGEXML, 'GlobalData', 'Locomotor.xml')
GLOBAL_DEFINES = os.path.join(SAGEXML, 'GlobalData', 'GlobalDefines.xml')
DEFINE = re.compile(r'<Define\s+name="([^"]+)"\s+value="([^"]+)"')

_globals = None


def number(text, name):
    """Attribute `name`'s number in an XML text, None when absent: a value written '=$NAME' is the define's (the
    file's own <Define>s, then GlobalData/GlobalDefines.xml: most retail units see with ShroudClearingRange
    '=$STANDARD_SHROUD_CLEAR', 500), '=50000' the number."""
    global _globals
    m = re.search(r'(?<![A-Za-z])' + name + r'="(=?\$?[A-Za-z_0-9.]+)"', text)
    if not m:
        return None
    v = m.group(1)
    if v.startswith('=$'):
        if _globals is None:
            _globals = dict(DEFINE.findall(open(GLOBAL_DEFINES, encoding='utf-8', errors='replace').read())) \
                if os.path.exists(GLOBAL_DEFINES) else {}
        v = {**_globals, **dict(DEFINE.findall(text))}.get(v[2:], '')
    try:
        return float(v.lstrip('='))
    except ValueError:
        return None

# a kind's guess when the data has nothing (world units per second; vision): retail infantry 40-60, vehicles 60-120
DEFAULTS = {'INFANTRY': (50.0, 200.0), 'VEHICLE': (90.0, 250.0), 'AIRCRAFT': (150.0, 300.0), 'SHIP': (70.0, 250.0),
            'STRUCTURE': (0.0, 250.0), '': (0.0, 100.0)}


def _surfaces():
    """Locomotor template id -> its Surfaces (GROUND, WATER, AIR ...)."""
    if not os.path.exists(LOCOMOTORS):
        return {}
    text = open(LOCOMOTORS, encoding='utf-8', errors='replace').read()
    out = {}
    for m in re.finditer(r'<LocomotorTemplate\b(.*?)>', text, re.S):
        head = m.group(1)
        i, s = re.search(r'\bid="([^"]+)"', head), re.search(r'\bSurfaces="([^"]+)"', head)
        if i:
            out[i.group(1)] = s.group(1).split() if s else []
    return out


def read_xml(text, kindof='', surfaces=None):
    """One unit's numbers from its XML text: speed (the NORMAL LocomotorSet), surface, vision, kinds."""
    surfaces = surfaces if surfaces is not None else {}
    speed, surf = None, []
    for m in re.finditer(r'<LocomotorSet\b(.*?)/?>', text, re.S):
        a = m.group(1)
        cond = re.search(r'\bCondition="([^"]+)"', a)
        if cond and cond.group(1) != 'NORMAL':
            continue
        sp, lo = re.search(r'\bSpeed="([\d.]+)"', a), re.search(r'\bLocomotor="([^"]+)"', a)
        if sp and speed is None:
            speed = float(sp.group(1))
            surf = surfaces.get(lo.group(1), []) if lo else []
    kinds = set(kindof.split())
    if not kindof:
        k = re.search(r'\bKindOf="([^"]+)"', text)
        kinds = set(k.group(1).split()) if k else set()
    return dict(speed=speed, surface=surface_of(surf, kinds), vision=number(text, 'VisionRange'),
                shroud=number(text, 'ShroudClearingRange'), kinds=sorted(kinds))


def surface_of(surf, kinds):
    s = set(surf)
    if 'AIRCRAFT' in kinds or 'AIR' in s:
        return 'air'
    if 'AMPHIBIOUS' in kinds or {'GROUND', 'WATER'} <= s:
        return 'both'
    if 'WATER' in s and 'GROUND' not in s:
        return 'water'
    return 'ground'


def units():
    """(template lower case, its index entry, its XML file) for every unit and building: the index's file, or --
    where the index points at a campaign override (Includes/CampaignOverrides: an edit, not the unit) -- the
    SageXML file of the template's own name."""
    idx = json.load(open(INDEX, encoding='utf-8')) if os.path.exists(INDEX) else {}
    by_name = {}
    for root, _, files in os.walk(SAGEXML):
        for f in files:
            if f.endswith('.xml'):
                by_name.setdefault(f[:-4].lower(), os.path.join(root, f))
    for t, e in idx.items():
        f = e.get('file', '')
        path = os.path.join(SAGEXML, *f[5:].split('/')) if f.startswith('DATA:') else ''
        if 'CampaignOverrides' in f or not e.get('EditorSorting'):
            own = by_name.get(t)
            if not own:
                continue
            path = own
            text = open(own, encoding='utf-8', errors='replace').read()
            sort = re.search(r'\bEditorSorting="([^"]+)"', text)
            e = dict(e, EditorSorting=sort.group(1) if sort else '')
        if e.get('EditorSorting') in ('UNIT', 'STRUCTURE') and path and os.path.exists(path):
            yield t, e, path


def _build():
    surfaces = _surfaces()
    out = {}
    for t, e, path in units():
        # the index writes inherited KindOf as +X / -X edits: keep the added ones; a building is sorted STRUCTURE
        kindof = ' '.join([k.lstrip('+') for k in e.get('KindOf', '').split() if not k.startswith('-')]
                          + (['STRUCTURE'] if e.get('EditorSorting') == 'STRUCTURE' else []))
        out[t] = read_xml(open(path, encoding='utf-8', errors='replace').read(), kindof, surfaces)
    return out


_table = None


def table():
    global _table
    if _table is None:
        if os.path.exists(CACHE):
            _table = json.load(open(CACHE, encoding='utf-8'))
        else:
            _table = _build()
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            json.dump(_table, open(CACHE, 'w', encoding='utf-8'), indent=0)
    return _table


# ---- combat: health, armour, weapons (sim.py's fight model; docs/engine: none of it settled on the bench yet)
COMBAT_CACHE = os.path.join(labpaths.WORK, 'sim_combat_v2.json')     # v2: defines resolved (2026-10-29)
WEAPONS_GLOB = ('GlobalData', 'Weapon.xml')
ARMOR = os.path.join(SAGEXML, 'GlobalData', 'Armor.xml')
ARMOR_DEFAULT = 100.0           # a damage type an armour does not name: taken in full (a guess)


def _blocks(text, tag):
    """(attributes text, inner text) of every <tag ...>...</tag> (or self-closed) element."""
    for m in re.finditer(rf'<{tag}\b(.*?)(/>|>(.*?)</{tag}>)', text, re.S):
        yield m.group(1), m.group(3) or ''


def _attr(head, name, default=None):
    m = re.search(rf'\b{name}="([^"]*)"', head)
    return m.group(1) if m else default


def _num(v, default=0.0):
    """A number attribute; a macro (=$UNLIMITED_CLIP_SIZE ...) or nothing: the default."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _secs(v):
    return _num(v.rstrip('s')) if v else 0.0


def _weapon_files():
    out = []
    for root, _, files in os.walk(SAGEXML):
        for f in files:
            if f.endswith('.xml'):
                p = os.path.join(root, f)
                try:
                    text = open(p, encoding='utf-8', errors='replace').read()
                except OSError:
                    continue
                if '<WeaponTemplate' in text:
                    out.append(text)
    return out


def _weapons(texts):
    """Weapon template id -> {range, damage, type, shots, cycle, anti, warhead}; a projectile's damage is its
    warhead's (filled in by _resolve)."""
    out = {}
    for text in texts:
        for head, body in _blocks(text, 'WeaponTemplate'):
            wid = _attr(head, 'id')
            if not wid:
                continue
            dmg = [(_num(_attr(h, 'Damage')), _attr(h, 'DamageType', ''))
                   for h, _ in _blocks(re.sub(r'<!--.*?-->', '', body, flags=re.S), 'DamageNugget')]
            war = [_attr(h, 'WarheadTemplate') for h, _ in _blocks(re.sub(r'<!--.*?-->', '', body, flags=re.S),
                                                                     'ProjectileNugget')]
            fire = re.search(r'<FiringDuration\b[^>]*MinSeconds="([^"]+)"', body)
            reload_ = re.search(r'<ClipReloadTime\b[^>]*MinSeconds="([^"]+)"', body)
            delay = re.search(r'<DelayBetweenShots\b[^>]*MinSeconds="([^"]+)"', body)
            out[wid] = dict(range=_num(_attr(head, 'AttackRange')), damage=sum(d for d, _ in dmg),
                            type=next((t for d, t in dmg if t), ''),
                            shots=int(_num(_attr(head, 'ClipSize'), 1.0 if not _attr(head, 'ClipSize') else 0.0)),
                            fire=_secs(fire.group(1)) if fire else 0.0, reload=_secs(reload_.group(1)) if reload_ else 0.0,
                            delay=_secs(delay.group(1)) if delay else 0.0,
                            anti=(_attr(head, 'RequiredAntiMask') or '').split(), warhead=next((w for w in war if w), None))
    return out


def _resolve(w, weapons):
    """A weapon's damage per second: its own damage, else its warhead's; one clip of `shots` then the reload."""
    dmg, typ = w['damage'], w['type']
    if not dmg and w['warhead'] in weapons:
        h = weapons[w['warhead']]
        dmg, typ = h['damage'], h['type']
    if w['shots'] <= 0:                         # an unlimited clip: no reload
        shots, cycle = 1, max(w['fire'], w['delay'], 0.1)
    else:
        shots = w['shots']
        cycle = shots * max(w['fire'], w['delay'], 0.1) + w['reload']
    return dict(range=w['range'], dps=round(dmg * shots / cycle, 2) if dmg else 0.0, type=typ, anti=w['anti'])


def _armors():
    text = open(ARMOR, encoding='utf-8', errors='replace').read() if os.path.exists(ARMOR) else ''
    raw = {}
    for head, body in _blocks(text, 'ArmorTemplate'):
        raw[_attr(head, 'id')] = (_attr(head, 'inheritFrom'), {_attr(h, 'Damage'): _num(_attr(h, 'Percent'), 100.0)
                                                              for h, _ in _blocks(body, 'Armor')})
    out = {}

    def get(a, depth=0):
        if a in out:
            return out[a]
        if a not in raw or depth > 10:
            return {}
        base, own = raw[a]
        out[a] = {**get(base, depth + 1), **own} if base else dict(own)
        return out[a]
    for a in raw:
        get(a)
    return out


def read_fight(text, weapons, armors):
    """One unit's fight from its XML: max health, its armour's percents, its weapons (the PRIMARY one of each slot,
    resolved)."""
    arm = re.search(r'<ArmorSet\b[^>]*\bArmor="([^"]+)"', text) or re.search(r'\bArmor="([^"]+)"', text)
    guns = []
    for head, body in _blocks(text, 'WeaponSetUpdate'):
        for slot in re.finditer(r'<WeaponSlot\w*\b.*?</WeaponSlot\w*>', body, re.S):
            ws = [(_attr(h, 'Ordering'), _attr(h, 'Template')) for h, _ in _blocks(slot.group(0), 'Weapon')]
            pick = next((t for o, t in ws if o == 'PRIMARY_WEAPON'), ws[0][1] if ws else None)
            if pick in weapons:
                guns.append(_resolve(weapons[pick], weapons))
    return dict(hp=number(text, 'MaxHealth'), armor=armors.get(arm.group(1), {}) if arm else {},
                weapons=[g for g in guns if g['dps'] > 0 and g['range'] > 0])


_fight = None


def _fight_data():
    global _fight
    if _fight is None:
        if os.path.exists(COMBAT_CACHE):
            _fight = json.load(open(COMBAT_CACHE, encoding='utf-8'))
        else:
            weapons, armors = _weapons(_weapon_files()), _armors()
            got = {t: read_fight(open(path, encoding='utf-8', errors='replace').read(), weapons, armors)
                   for t, _, path in units()}
            _fight = dict(units=got, weapons=weapons, armors=armors)
            json.dump(_fight, open(COMBAT_CACHE, 'w', encoding='utf-8'), indent=0)
    return _fight


def fight(template, own=None):
    """{hp, armor {damage type: percent}, weapons [{range, dps, type, anti}]} for a template (own: the mission's
    units' XML, read with the retail weapons and armours); hp None when the data has none."""
    d = _fight_data()
    if own and template in own:
        return read_fight(own[template], d['weapons'], d['armors'])
    return d['units'].get(template.lower(), dict(hp=None, armor={}, weapons=[]))


def kind_of(kinds):
    for k in ('STRUCTURE', 'AIRCRAFT', 'SHIP', 'INFANTRY', 'VEHICLE'):
        if k in kinds:
            return k
    return ''


def stats(template, own=None):
    """{speed, surface, vision, shroud, kinds, guessed} for a template; own: {id: xml text} of the mission's units."""
    if own and template in own:
        e = read_xml(own[template], surfaces=_surfaces())
    else:
        e = dict(table().get(template.lower()) or {})
    guessed = []
    kinds = set(e.get('kinds') or [])
    speed, vision = DEFAULTS[kind_of(kinds)]
    if e.get('speed') is None:
        if 'STRUCTURE' not in kinds:            # a building does not move: nothing guessed
            guessed.append('speed')
        e['speed'] = speed
    if e.get('vision') is None:
        guessed.append('vision')
        e['vision'] = vision
    e.setdefault('surface', 'ground')
    e.setdefault('shroud', None)
    e['kinds'] = sorted(kinds)
    e['guessed'] = guessed if e.get('kinds') or own else ['all']
    return e
