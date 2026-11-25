r"""What the plan simulator (sim.py) needs of a unit, from the game's own data: how fast it goes, on what (ground,
water, both, air), how far it sees, its KindOf. Retail templates from the SDK's SageXML (the index mapstudy keeps:
work\sagexml_gameobjects.json gives each template's file and KindOf; the file its LocomotorSet's NORMAL Speed and its
VisionRange / ShroudClearingRange, defines resolved; each field from the nearest template up the inheritFrom chain that
writes it, resolve()), cached in work\sim_units_v7.json. Our own units (a mission's Unit: its XML) are read the same
way, over the retail templates they inherit from; a template found nowhere gets its kind's default (DEFAULTS) and is
listed as guessed.
"""
import json
import math
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET

HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
import labpaths  # noqa: E402
from engine.ports.templates import secs as _secs  # noqa: E402,F401  one duration parser, '500ms' too (review ss #5)

CACHE = os.path.join(labpaths.WORK, 'sim_units_v7.json')     # v2: defines resolved (2026-10-29); v3: + ShroudClearingHeight;
                                                            # v4: + radius (R8); v5: radius read through 'Type= "BOX"'
                                                            # v6: inherited fields resolved up inheritFrom (eggs, 11-10)
                                                            # v7: DEEP_WATER is water (round 252)
CLEAR_HEIGHT = 50.0             # ShroudClearingHeight when a unit does not write one (docs/engine/vision.md: retail units
                                # nearly all leave it out)
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
        name = v[2:]
        v = {**_globals, **dict(DEFINE.findall(text))}.get(name)
        v = defines().get(name, '') if v is None else v     # a block cut from its file: the file's defines
    try:
        return float(v.lstrip('='))
    except ValueError:
        return None

# a kind's guess when the data has nothing (world units per second; vision): retail infantry 40-60, vehicles 60-120
DEFAULTS = {'INFANTRY': (50.0, 200.0), 'VEHICLE': (90.0, 250.0), 'AIRCRAFT': (150.0, 300.0), 'SHIP': (70.0, 250.0),
            'STRUCTURE': (0.0, 250.0), '': (0.0, 100.0)}


_surf_memo = None


def _surfaces():
    """Locomotor template id -> its engine.modules.locomotor.Locomotor (Surfaces, turning)."""
    from engine.modules import locomotor
    global _surf_memo
    if _surf_memo is None:
        _surf_memo = locomotor.library(open(LOCOMOTORS, encoding='utf-8', errors='replace').read()
                                       if os.path.exists(LOCOMOTORS) else '')
    return _surf_memo


def _own_fields(text, surfaces):
    """What one GameObject block writes itself (None: left to what it inherits): speed and its locomotor's surfaces
    (the NORMAL LocomotorSet), vision, shroud, clear height, radius."""
    from engine.modules import locomotor
    normal = locomotor.speed_of(locomotor.sets(text), 'NORMAL')
    loco = surfaces.get(normal.locomotor) if normal else None
    return dict(speed=normal and normal.speed, surf=normal and (loco.surfaces if loco else []), vision=number(text, 'VisionRange'), shroud=number(text, 'ShroudClearingRange'),
                clear_height=number(text, 'ShroudClearingHeight'), radius=radius(text))


_all_defines = None


def defines():
    """Every <Define> in SageXML (197 names, none defined twice -- 11-10): an egg's KindOf '=$EGG_KINDOFS' is
    defined in BaseEgg.xml, which the egg's file includes; GameObject blocks cut out of their file lose that."""
    global _all_defines
    if _all_defines is None:
        _all_defines = {}
        for root, _, files in os.walk(SAGEXML):
            for f in files:
                if f.endswith('.xml'):
                    text = open(os.path.join(root, f), encoding='utf-8', errors='replace').read()
                    _all_defines.update(DEFINE.findall(text))
    return _all_defines


def expand(value, depth=0, extra=None):
    """A SageXML attribute value with its defines spelled out: "=$EGG_KINDOFS+' SCORE'" -> the define's text, then
    ' SCORE'; a value not starting with '=' as it is."""
    if not value.startswith('=') or depth > 5:
        return value
    out = []
    for name, lit in re.findall(r"\$([A-Za-z_0-9]+)|'([^']*)'", value[1:]):
        got = (extra or {}).get(name)
        out.append(expand(defines().get(name, '') if got is None else got, depth + 1, extra) if name else lit)
    return ''.join(out)


def edit_kinds(base, value, extra=None):
    """KindOf over the inherited set: '+X -Y' edits it (A04_ExplodingTengu: -VEHICLE +INFANTRY); a plain list
    (BaseStructure's, an egg's =$EGG_KINDOFS) replaces it."""
    toks = expand(value, extra=extra).split()
    if not any(t[0] in '+-' for t in toks):
        return set(toks)
    out = set(base)
    for t in toks:
        (out.discard if t[0] == '-' else out.add)(t.lstrip('+-'))
    return out


def _head(xml, template):
    """The <GameObject ...> tag of `template` in xml (case blind), else the first; '' when none."""
    heads = re.findall(r'<GameObject\b[^>]*>', xml or '')
    mine = [h for h in heads if re.search(rf'\bid="{re.escape(template)}"', h, re.I)]
    return (mine or heads or [''])[0]


def _block_of(text, template):
    """The <GameObject id=template> block of a file's text (case blind), '' when none."""
    for m in re.finditer(r'<GameObject\b.*?</GameObject>', text or '', re.S):
        if re.search(rf'\bid="{re.escape(template)}"', _head(m.group(0), template), re.I):
            return m.group(0)
    return ''


_resolved = {}


def resolve(template, own=None, surfaces=None, xml=None, depth=0):
    """{sorting, kinds, speed, surface, vision, shroud, clear_height, radius} of a template, each from the nearest
    template up its inheritFrom chain that writes it (KindOf edited down the chain, edit_kinds): a Nanocore egg
    writes its LocomotorSet and KindOf define but not EditorSorting (BaseEgg's UNIT). own: {id: xml} of a mission's
    units, read over the retail templates they inherit from. A campaign override (the same id inheriting itself)
    reads over the block of its own name's file."""
    surfaces = surfaces if surfaces is not None else _surfaces()
    key = template.lower()
    mine = xml is not None or bool((own or {}).get(template))
    if not mine and key in _resolved:
        return _resolved[key]
    if xml is None:
        xml = _xml(template, own)
    head = _head(xml, template)
    up = parent(xml, template) if depth < 10 else None
    if not up:
        base = dict(sorting=None, kinds=set(), speed=None, surf=None, vision=None, shroud=None, clear_height=None,
                    radius=None)
    elif up.lower() == key:
        text = retail_xml(up)
        base = resolve(up, None, surfaces, _block_of(text, up) or text, depth + 1)
    else:
        base = resolve(up, own, surfaces, None, depth + 1)
    out = dict(base)
    sort, kind = _attr(head, 'EditorSorting'), _attr(head, 'KindOf')
    if sort:
        out['sorting'] = sort
    if kind is not None:
        out['kinds'] = edit_kinds(base['kinds'], kind, dict(DEFINE.findall(xml)))
    for k, v in _own_fields(xml or '', surfaces).items():
        if v is not None:
            out[k] = v
    if not mine:
        _resolved[key] = out
    return out


def read_xml(template, own=None, surfaces=None):
    """One unit's table entry: speed (the NORMAL LocomotorSet), surface, vision, kinds -- resolve()d up its chain;
    a building (sorted STRUCTURE) counts STRUCTURE among its kinds."""
    from engine.modules import locomotor
    r = resolve(template, own, surfaces)
    kinds = set(r['kinds']) | ({'STRUCTURE'} if r['sorting'] == 'STRUCTURE' else set())
    return dict(speed=r['speed'], surface=locomotor.surface_of(r['surf'] or [], kinds), vision=r['vision'],
                shroud=r['shroud'], kinds=sorted(kinds), clear_height=r['clear_height'], radius=r['radius'])


def radius(text):
    """R8: the bounding circle radius of a unit's Geometry (its first Shape): a BOX's corner, sqrt(major^2 + minor^2);
    a CYLINDER's or SPHERE's MajorRadius (Generals GeometryInfo::calcBoundingStuff). The weapon reach is measured
    between these circles (sim.Sim.in_range). None when the XML has no Shape."""
    g = re.search(r'<Geometry\b.*?</Geometry>', text, re.S)
    m = re.search(r'<Shape\b(.*?)/?>', g.group(0) if g else '', re.S)
    if not m:
        return None
    a = m.group(1)
    # retail writes some with spaces round '=' (OreNode: Type= "BOX", MajorRadius = "33.3968")
    kind = re.search(r'\bType\s*=\s*"([^"]+)"', a)
    major, minor = (re.search(rf'\b{n}\s*=\s*"([\d.]+)"', a) for n in ('MajorRadius', 'MinorRadius'))
    major = float(major.group(1)) if major else 0.0
    if kind and kind.group(1).upper() == 'BOX':
        minor = float(minor.group(1)) if minor else 0.0
        return (major * major + minor * minor) ** 0.5
    return major


def units():
    """(template lower case, its index entry with EditorSorting resolved up the chain, its XML file) for every unit
    and building: the index's file, or -- where the index points at a campaign override (Includes/CampaignOverrides:
    an edit, not the unit) -- the SageXML file of the template's own name. A template that does not write its
    EditorSorting takes its base's (the Nanocore eggs: BaseEgg's UNIT). The index and the SDK missing is an error,
    not no units: the tables built from this are cached, and an empty one hid it (line A, 11-13)."""
    require_data()
    idx = json.load(open(INDEX, encoding='utf-8'))
    by_name = {}
    for root, _, files in os.walk(SAGEXML):
        for f in files:
            if f.endswith('.xml'):
                by_name.setdefault(f[:-4].lower(), os.path.join(root, f))
    surfaces = _surfaces()
    for t, e in idx.items():
        f = e.get('file', '')
        path = os.path.join(SAGEXML, *f[5:].split('/')) if f.startswith('DATA:') else ''
        if 'CampaignOverrides' in f:
            path = by_name.get(t, '')
        sort = e.get('EditorSorting') if 'CampaignOverrides' not in f else None
        e = dict(e, EditorSorting=sort or resolve(t, surfaces=surfaces)['sorting'] or '')
        if e['EditorSorting'] in ('UNIT', 'STRUCTURE') and path and os.path.exists(path):
            yield t, e, path


class MissingData(FileNotFoundError):
    """The retail data the simulator's tables are built from is not where labpaths says (a worktree without work\\,
    a clean clone): say so instead of building, and caching, empty tables."""


def require_data(paths=None):
    paths = paths or (INDEX, SAGEXML, LOCOMOTORS, ARMOR)
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        raise MissingData(f'simulator data missing: {", ".join(missing)} (labpaths.WORK = {labpaths.WORK}, '
                          f'SDK3 = {labpaths.SDK3}); set CNV_WORK / CNV_SDK to the main checkout\'s')


def _cached(path, build, empty):
    """The cache at `path`, else build() written there. A cache that is `empty` (an earlier run without the data
    wrote it) is not trusted: it is built again, which raises MissingData if the data is still missing; and an empty
    build is never written."""
    if os.path.exists(path):
        got = json.load(open(path, encoding='utf-8'))
        if not empty(got):
            return got
    got = build()
    if empty(got):
        raise MissingData(f'simulator data gave an empty table for {path} (labpaths.WORK = {labpaths.WORK})')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(got, open(path, 'w', encoding='utf-8'), indent=0)
    return got


def _build():
    surfaces = _surfaces()
    return {t: read_xml(t, surfaces=surfaces) for t, _, _ in units()}


_table = None


def table():
    global _table
    if _table is None:
        _table = _cached(CACHE, _build, lambda t: not t)
    return _table


# ---- combat: health, armour, weapons (sim.py's fight model; docs/engine: none of it settled on the bench yet)
COMBAT_CACHE = os.path.join(labpaths.WORK, 'sim_combat_v48.json')    # v48: the shotgun's self-centred arc shock (A363); v47: the grapple nugget (E226); v46: the lift's retail filter; v45: the link guns' ally filter; v44: + taper (DamageDealtAtSelfPosition); v43: weapons from the data port (W1), the cache keeps `sets`; v42: the leech nugget's AI-only damage; v41: Rush infantry/status combination; v40: isolated forbidden object-status gate
                                                                    # (Flags ATTACK_NEEDS_LINE_OF_SIGHT)
ARMOR = os.path.join(SAGEXML, 'GlobalData', 'Armor.xml')
ARMOR_DEFAULT = 100.0           # a damage type an armour does not name: taken in full (a guess)


def percent(armor, dtype):
    """The percent of `dtype` damage an armour ({type: percent}, '*': its ArmorTemplate Default) takes: the type's own
    line, else the Default (CryoBeamFrozenArmor 90000: a frozen unit breaks at a touch; InvulnerableArmor 0), else
    ARMOR_DEFAULT."""
    return armor.get(dtype, armor.get('*', ARMOR_DEFAULT))


FLANK_KEYS = {'<side': 'SideDamageScalar', '<rear': 'RearDamageScalar'}    # in an armour dict, beside the types


def flank(armor, facing, dx, dy):
    """The side / rear scalar an armour takes a hit with (docs/engine/weapons.md, bench engine_shot flank 40 / 40 /
    42 / 44 %; read: the angle from the victim's facing to the direction to its attacker): over 135 degrees its
    RearDamageScalar, over 45 its SideDamageScalar, else 1 -- and 1 with the attacker at the victim's own place
    (dx, dy: the attacker less the victim)."""
    if math.hypot(dx, dy) < 1e-9:
        return 1.0
    off = abs((math.atan2(dy, dx) - facing + math.pi) % (2 * math.pi) - math.pi)
    key = '<rear' if off > math.radians(135) else '<side' if off > math.radians(45) else None
    return armor.get(key, 100.0) / 100.0 if key else 1.0


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


HIT_NUGGETS = ('DamageNugget', 'LineDamageNugget')     # nuggets whose Damage takes health off what they hit (a
                                                        # LineDamageNugget: the sniper rifles, the wave-force beams)


def _weapons(texts, base_table=None):
    """Weapon template id -> {range, damage, type, shots, cycle, anti, warhead, los}; a projectile's damage is its
    warhead's (filled in by _resolve). A template with inheritFrom takes what it does not write from its parent
    (the flak trooper's anti-air SovietAntiVehicleFlakLauncher_Aircraft writes only its range and anti mask: without
    this it had no damage and never fired at aircraft; bench 2026-11-08 engine_air flak*). A template that inherits
    from its own id (Includes/CampaignOverrides: the conscript's AK47, the tesla trooper's gun, the Apollo's cannon,
    the Century bomber's bombs) changes what it writes on the earlier template of that id, it does not replace it.
    base_table: resolved templates (the retail ones) a parent not among `texts` is looked up in (a mission's own
    weapon inheriting a retail one)."""
    defs = []                                           # (id, what it writes, parent) in file order
    for text in texts:
        for head, body in _blocks(text, 'WeaponTemplate'):
            wid = _attr(head, 'id')
            if not wid:
                continue
            bare = re.sub(r'<!--.*?-->', '', body, flags=re.S)
            dmg = [(_num(_attr(h, 'Damage')), _attr(h, 'DamageType', '')) for tag in HIT_NUGGETS
                   for h, _ in _blocks(bare, tag) if _attr(h, 'Damage') is not None]
            war = [_attr(h, 'WarheadTemplate') for h, _ in _blocks(bare, 'ProjectileNugget')]
            projectiles = [_attr(h, 'ProjectileTemplate') for h, _ in _blocks(bare, 'ProjectileNugget')]
            fire = re.search(r'<FiringDuration\b[^>]*MinSeconds="([^"]+)"', body)
            reload_ = re.search(r'<ClipReloadTime\b[^>]*MinSeconds="([^"]+)"', body)
            delay = re.search(r'<DelayBetweenShots\b[^>]*MinSeconds="([^"]+)"', body)
            pre = re.search(r'<PreAttackDelay\b[^>]*MinSeconds="([^"]+)"', body)
            ocl = [_attr(h, 'WeaponOCL') for h, _ in _blocks(bare, 'WeaponOCLNugget')]
            # the cryo beam's freeze: a SecondaryDamageNugget's Amount a shot, not one that needs an upgrade (the
            # Allied High Technology one)
            sd = [_num(_attr(h, 'Amount')) for h, i in _blocks(bare, 'SecondaryDamageNugget')
                  if '<RequiredUpgrade' not in (i or '')]
            got = {}                                            # only what this template writes
            if any(projectiles):
                got['projectile'] = next(p for p in projectiles if p)
            supp = [(_num(_attr(h, 'Radius')), _num(_attr(h, 'Suppression')),
                     _secs(_attr(h, 'DurationSeconds', '0s')))
                    for h, _ in _blocks(bare, 'SuppressionNugget')]
            if supp:
                got['suppression'] = supp
            # Only the unfiltered, single-target form is explained by round 1.
            # Retain unsupported forms as gaps instead of applying them to everyone.
            mods, unsupported = [], []
            lifts = []
            for h, inner in _blocks(bare, 'ActivateLiftObjectNugget'):
                filters = list(_blocks(inner, 'SpecialObjectFilter'))
                f, fi = filters[0] if len(filters) == 1 else ('', '')
                rest = re.sub(r'<SpecialObjectFilter\b.*?(?:/>|>.*?</SpecialObjectFilter>)', '', inner, flags=re.S)
                things = re.findall(r'<ExcludeThing>\s*([^<>\s]+)\s*</ExcludeThing>', fi)
                if (rest.strip() or re.sub(r'<ExcludeThing>[^<]*</ExcludeThing>', '', fi).strip() or len(filters) > 1
                        or (filters and _attr(f, 'Rule', 'ANY') != 'ANY')
                        or set(re.findall(r'(\w+)\s*=', f)) - {'Rule', 'Include', 'Exclude', 'StatusBitFlagsExclude'}
                        or set(re.findall(r'(\w+)\s*=', h)) - {'id', 'Lifetime'}):
                    unsupported.append('ActivateLiftObjectNugget')
                else:   # ExcludeThing and StatusBitFlagsExclude: the retail filters (engine_liftground)
                    lifts.append(dict(include=_attr(f, 'Include', '').split(), exclude=_attr(f, 'Exclude', '').split(),
                                      things=[t.lower() for t in things],
                                      status=_attr(f, 'StatusBitFlagsExclude', '').split()))
            if lifts:
                got['lift'] = lifts
            grapples = [dict(forbidden=_attr(h, 'ForbiddenTargetObjectStatus', '').split(),
                             include=_attr(f, 'Include', '').split(), exclude=_attr(f, 'Exclude', '').split())
                        for h, inner in _blocks(bare, 'GrapplingHookNugget')
                        for f in [next((fh for fh, _ in _blocks(inner, 'SpecialObjectFilter')), '')]]
            if grapples:        # the caster's GrapplingHookUpdate pulls (E226)
                got['grapple'] = grapples
            impacts, delayed_impacts = [], []
            for h, inner in _blocks(bare, 'MetaImpactNugget'):
                # Retail Omega writes Amount/Radius/Z with spaces around '='.
                h = re.sub(r'(\w+)\s*=\s*"', r'\1="', h)
                # Delayed payloads feed only the isolated expiry interface.
                # Never send them through immediate Physics: observation and
                # landing phases remain unresolved, as do other variants.
                unsupported.append('MetaImpactNugget')
                fields = set(re.findall(r'(\w+)\s*=', h))
                # Only the measured Sickle / magnetic ground filter spellings are enabled. Other
                # predicates and delayed filtered shocks remain explicit gaps.
                target_filter = None
                forbidden = _attr(h, 'ForbiddenTargetModelCondition', '').split()
                children = list(_blocks(inner or '', 'SpecialObjectFilter'))
                if len(children) == 1:
                    fh, fi = children[0]
                    attrs = dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', fh))
                    relation = attrs.get('Relationship')
                    status_exclude = attrs.get('StatusBitFlagsExclude')
                    sickle_attrs = dict(Rule='ANY', Relationship=relation, Include='INFANTRY')
                    if status_exclude is not None:
                        sickle_attrs['StatusBitFlagsExclude'] = status_exclude
                    if (not fi.strip() and attrs == sickle_attrs
                            and status_exclude in (None, 'NO_COLLISIONS')
                            and relation in ('ENEMIES', 'ALLIES')
                            # CampKSG b removed only the ENEMIES exclusion.
                            and (status_exclude is not None or relation == 'ENEMIES')
                            and set(forbidden) == {'STUNNED', 'STUNNED_STANDING_UP', 'STUNNED_FLAILING'}
                            and not re.sub(r'<SpecialObjectFilter\b[^>]*>.*?</SpecialObjectFilter>',
                                           '', inner, flags=re.S).strip()
                            and 'ShockwaveDelaySeconds' not in fields):
                        target_filter = dict(relation=relation, forbidden=forbidden,
                                             status_exclude=(status_exclude or '').split())
                    things = re.findall(r'<IncludeThing>\s*([^<>\s]+)\s*</IncludeThing>', fi)
                    if (attrs == dict(Rule='ALL', Exclude='AIRCRAFT INFANTRY',
                                      StatusBitFlagsExclude='UNDER_IRON_CURTAIN')
                            and set(things) == {'SovietScoutVehicle', 'SovietHeavyAntiVehicleInfantry'}
                            and len(things) == 2 and not forbidden
                            and not re.sub(r'<IncludeThing>\s*[^<>\s]+\s*</IncludeThing>', '', fi).strip()
                            and len(children) == 1
                            and not re.sub(r'<SpecialObjectFilter\b[^>]*>.*?</SpecialObjectFilter>',
                                           '', inner, flags=re.S).strip()
                            and 'ShockwaveDelaySeconds' not in fields
                            and _num(_attr(h, 'ShockWaveZMult', '1')) == 0):
                        target_filter = dict(magnetic_ground=True, include_templates=things)
                    # CampKKG: exact retail Rush infantry selector with its
                    # scripted status gate; Arc/model conditions remain gaps.
                    if (attrs == dict(Rule='ANY', Include='INFANTRY') and not fi.strip()
                            and not forbidden
                            and not re.sub(r'<SpecialObjectFilter\b[^>]*>.*?</SpecialObjectFilter>',
                                           '', inner, flags=re.S).strip()
                            and _attr(h, 'ForbiddenTargetObjectStatus') == 'LEECHED_TARGET_ACTIVE'
                            and not fields & {'ShockwaveDelaySeconds', 'InvertShockWave'}):
                        target_filter = dict(rush_infantry=True)
                # CampKOG isolates this status, CampKKG adds only infantry.
                # Native leech lifecycle and other combinations remain gaps.
                object_gate = (_attr(h, 'ForbiddenTargetObjectStatus') == 'LEECHED_TARGET_ACTIVE'
                               and not forbidden
                               and ((not target_filter and not (inner or '').strip())
                                    or target_filter == dict(rush_infantry=True))
                               and 'ShockwaveDelaySeconds' not in fields
                               and 'InvertShockWave' not in fields)
                # A363: the retail shotgun (Arc 5d + Forbidden STUNNED_FLAILING, no filter); its arc runs about the
                # shooter's line, so meta_impact.launch takes it only from a DamageDealtAtSelfPosition weapon.
                # engine_knock_arc b: Forbidden STUNNED_FLAILING alone shocks every standing man.
                shotgun = (not (inner or '').strip() and forbidden == ['STUNNED_FLAILING']
                           and re.fullmatch(r'\d+(\.\d+)?d', _attr(h, 'ShockWaveArc', '0d')) is not None
                           and not fields & {'ShockwaveDelaySeconds', 'InvertShockWave'})
                if ((not (inner or '').strip() and not forbidden) or target_filter or shotgun) and fields <= {
                        'id', 'ShockWaveAmount', 'ShockWaveRadius', 'ShockWaveZMult', 'ShockWaveTaperOff',
                        'ShockwaveDelaySeconds', 'InvertShockWave',
                        *(['ShockWaveArc'] if shotgun else []),
                        *(['ForbiddenTargetObjectStatus'] if object_gate else []),
                        *(['ForbiddenTargetModelCondition'] if target_filter or shotgun else [])} and all(
                        _attr(h, field) is not None for field in
                        ('ShockWaveAmount', 'ShockWaveRadius')):
                    seconds = _secs(_attr(h, 'ShockwaveDelaySeconds', '0s'))
                    if not math.isfinite(seconds) or seconds < 0:
                        continue
                    invert = _attr(h, 'InvertShockWave', 'false')
                    if invert not in ('true', 'false') or ('InvertShockWave' in fields and (
                            seconds > 0 or (target_filter and not target_filter.get('magnetic_ground'))
                            or _num(_attr(h, 'ShockWaveZMult', '1')) != 0)):
                        continue  # Only measured immediate horizontal inversion spellings.
                    effect = dict(amount=_num(_attr(h, 'ShockWaveAmount')),
                                  radius=_num(_attr(h, 'ShockWaveRadius')),
                                  zmult=_num(_attr(h, 'ShockWaveZMult', '1')),
                                  taper=_num(_attr(h, 'ShockWaveTaperOff', '0')))
                    if object_gate:
                        effect['forbidden_status'] = ['LEECHED_TARGET_ACTIVE']
                    if shotgun:
                        effect['forbid_flailing'] = True
                    if shotgun and 'ShockWaveArc' in fields:
                        effect['arc'] = float(_attr(h, 'ShockWaveArc')[:-1])
                    if 'InvertShockWave' in fields:
                        effect['invert'] = invert == 'true'
                    if target_filter:
                        effect['target_filter'] = target_filter
                    if seconds > 0:
                        delayed_impacts.append(dict(effect, delay_seconds=seconds))
                    else:
                        impacts.append(effect)
            if impacts:
                got['meta_impacts'] = impacts
            if delayed_impacts:
                got['delayed_meta_impacts'] = delayed_impacts
            informs = []
            for h, inner in _blocks(bare, 'InformTargetNugget'):
                # engine_inform_radius: plain radius broadcasts launch data.
                # Filters and the whole AI response remain incomplete.
                if not (inner or '').strip() and set(re.findall(r'(\w+)\s*=', h)) <= {
                        'id', 'MinTimeToImpactFudgeFactor', 'MaxTimeToImpactFudgeFactor', 'Radius'}:
                    informs.append(dict(min=_num(_attr(h, 'MinTimeToImpactFudgeFactor', '0.85')),
                                        max=_num(_attr(h, 'MaxTimeToImpactFudgeFactor', '1.15'))))
                    if _attr(h, 'Radius') is not None:
                        informs[-1]['radius'] = _num(_attr(h, 'Radius'))
            if informs:
                got['inform'] = informs
            if any(_blocks(bare, 'InformTargetNugget')):
                # engine_inform_ai: an AI miner can react before the slow shell hits.
                # Partial launch/table/armor execution is modeled; full replay,
                # history, radius boundaries and filter variants remain gaps.
                unsupported.append('InformTargetNugget')
            for h, inner in _blocks(bare, 'AttributeModifierNugget'):
                target_filter = None
                filters = list(_blocks(inner, 'SpecialObjectFilter'))
                if len(filters) == 1:
                    fh, fi = filters[0]
                    attrs = dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', fh))
                    excluded = re.findall(r'<ExcludeThing>\s*([^<>\s]+)\s*</ExcludeThing>', fi)
                    leftover = re.sub(r'<ExcludeThing>\s*[^<>\s]+\s*</ExcludeThing>', '', fi).strip()
                    # Only this retail recipe is explained. Do not broaden to
                    # other rules, relationships, nested selectors or gates.
                    if (attrs == dict(Rule='ANY', Exclude='INFANTRY',
                            Include='VEHICLE SHIP AIRCRAFT FS_BASE_DEFENSE',
                            StatusBitFlagsExclude='UNDER_IRON_CURTAIN')
                            and len(excluded) == 3 and set(excluded) == {
                                'JapanRisingBalloon', 'JapanFallingBalloonBomb', 'JapanBalloonBomb'}
                            and not leftover and _attr(h, 'AttributeModifierName') == 'AttributeMod_WeaponScrambler'
                            and not re.sub(r'<SpecialObjectFilter\b.*?</SpecialObjectFilter>', '', inner, flags=re.S).strip()):
                        target_filter = dict(rule='ANY', kinds=attrs['Include'].split(),
                                             unkinds=['INFANTRY'], exclude=[v.lower() for v in excluded],
                                             status_exclude=['UNDER_IRON_CURTAIN'])
                        inner = ''
                    elif attrs == dict(Rule='NONE', Relationship='ALLIES') and len(included := re.findall(
                            r'<IncludeThing>\s*([^<>\s]+)\s*</IncludeThing>', fi)) == 1 and not re.sub(
                            r'<IncludeThing>\s*[^<>\s]+\s*</IncludeThing>', '', fi).strip():
                        # the link guns' (prism, tesla): an ally of the one template (engine/modules/assist.py)
                        target_filter = dict(include=[included[0].lower()], status_exclude=[])
                        inner = re.sub(r'<SpecialObjectFilter\b.*?</SpecialObjectFilter>', '', inner, flags=re.S)
                required = re.findall(r'<RequiredUpgrade>\s*([^<>\s]+)\s*</RequiredUpgrade>', inner)
                forbidden = re.findall(r'<ForbiddenUpgrade>\s*([^<>\s]+)\s*</ForbiddenUpgrade>', inner)
                rest = re.sub(r'<(RequiredUpgrade|ForbiddenUpgrade)>\s*[^<>\s]+\s*</\1>', '', inner).strip()
                if rest or len(required) + len(forbidden) > 1 or any(_attr(h, field) is not None for field in
                        ('AttributeModifierOwnerName', 'ForbiddenTargetObjectStatus', 'RequiredTargetObjectStatus',
                         'AntiCategories', 'DamageArc')) or _num(_attr(h, 'Radius', '0'), float('nan')) != 0:
                    unsupported.append('AttributeModifierNugget')
                elif _attr(h, 'AttributeModifierName'):
                    mid = _attr(h, 'AttributeModifierName')
                    mods.append(dict(modifier=mid, required_upgrade=required[0] if required else '',
                                     forbidden_upgrade=forbidden[0] if forbidden else '')
                                if required or forbidden else
                                dict(modifier=mid, required_upgrade='', forbidden_upgrade='',
                                     target_filter=target_filter) if target_filter else mid)
            if mods:
                got['hit_modifiers'] = mods
            lines = list(_blocks(bare, 'LineDamageNugget'))
            if lines:
                h, inner = lines[0]
                if len(lines) != 1 or len(dmg) != 1 or (inner or '').strip() or _attr(h, 'UseDynamicLineLength') != 'true' or any(
                        _num(_attr(h, field)) for field in ('OffsetAngle', 'LineLengthLeadOut', 'Radius')):
                    unsupported.append('LineDamageNugget')
                else:
                    got['line'] = dict(width=_num(_attr(h, 'LineWidth')), lead=_num(_attr(h, 'LineLengthLeadIn')),
                                       out=_num(_attr(h, 'OverShootDistance')), dynamic=True)
            strips = []
            for h, inner in _blocks(bare, 'StripMaxHealthPercentNugget'):
                if (inner or '').strip() or _num(_attr(h, 'Radius', '0'), float('nan')) != 0:
                    unsupported.append('StripMaxHealthPercentNugget')
                else:
                    strips.append((_num(_attr(h, 'AmountToStrip', '50%').rstrip('%')) / 100,
                                   _attr(h, 'DamageType', 'UNDEFINED')))
            if strips:
                got['strip_max_health'] = strips
            paralysis = []
            for h, inner in _blocks(bare, 'ParalyzeNugget'):
                if (inner or '').strip() or _attr(h, 'ParalyzeType') != 'EMP':
                    unsupported.append('ParalyzeNugget')
                else:
                    paralysis.append(_secs(_attr(h, 'DurationSeconds', '0s')))
            if paralysis:
                got['emp_seconds'] = paralysis
            # a damage line (simsweep): the shooter's LinearDamageUpdate walks one out per shot, Lifetime caps its frames
            sweeps = [_secs(_attr(h, 'Lifetime') or '0s') for h, _ in _blocks(bare, 'ActivateLinearDamageNugget')]
            if sweeps:
                got['sweep'] = sweeps[0]

            for h, inner in _blocks(bare, 'LeechPercentMaxHealthDamageNugget'):
                if ((inner or '').strip() or any(d for d, _ in dmg) or any(war)
                        or _num(_attr(h, 'Radius', '0'), float('nan')) != 0
                        or _secs(_attr(h, 'DelayTimeSeconds', '0s'))):
                    unsupported.append('LeechPercentMaxHealthDamageNugget')
                else:
                    dmg.append((_num(_attr(h, 'Damage')), _attr(h, 'DamageType', 'UNDEFINED')))
                    got['leech_percent'] = _num(_attr(h, 'PercentMaxHealthToTake', '100%').rstrip('%')) / 100
            for h, inner in _blocks(bare, 'LeechHealthDamageNugget'):
                if ((inner or '').strip() or any(d for d, _ in dmg) or any(war)
                        or _num(_attr(h, 'Radius', '0'), float('nan')) != 0
                        or _secs(_attr(h, 'DelayTimeSeconds', '0s'))):
                    unsupported.append('LeechHealthDamageNugget')
                    # the AI's template rate still counts it as a plain damage nugget, its Damage x the target's
                    # armour for its DamageType, filter or not (engine line B round 226, read): the Hammer's beam
                    got.setdefault('ai_damage', []).append((_num(_attr(h, 'Damage')), _attr(h, 'DamageType', 'UNDEFINED')))
                else:
                    dmg.append((_num(_attr(h, 'Damage')), _attr(h, 'DamageType', 'UNDEFINED')))
                    got['leech_health'] = _num(_attr(h, 'PercentDamageToHeal', '100%').rstrip('%')) / 100
            special_powers = []
            for h, inner in _blocks(bare, 'SpecialPowerNugget'):
                filters = list(_blocks(inner, 'SpecialObjectFilter'))
                rest = re.sub(r'<SpecialObjectFilter\b[^>]*/>', '', inner).strip()
                required = re.findall(r'<RequiredUpgrade>\s*([^<>\s]+)\s*</RequiredUpgrade>', rest)
                forbidden = re.findall(r'<ForbiddenUpgrade>\s*([^<>\s]+)\s*</ForbiddenUpgrade>', rest)
                rest = re.sub(r'<(RequiredUpgrade|ForbiddenUpgrade)>\s*[^<>\s]+\s*</\1>', '', rest).strip()
                if (rest or len(required) + len(forbidden) > 1 or len(filters) > 1 or any(war)
                        or set(re.findall(r'(\w+)\s*=', h)) - {'id', 'SpecialPowerTemplate'}
                        or (filters and (filters[0][1].strip() or _attr(filters[0][0], 'Rule', 'ANY') != 'ANY'
                            or set(re.findall(r'(\w+)\s*=', filters[0][0])) - {'Rule', 'Include', 'Exclude'}))):
                    unsupported.append('SpecialPowerNugget')
                else:
                    f = filters[0][0] if filters else ''
                    special_powers.append(dict(power=_attr(h, 'SpecialPowerTemplate'),
                                               include=_attr(f, 'Include', '').split(),
                                               exclude=_attr(f, 'Exclude', '').split(),
                                               required_upgrade=required[0] if required else '',
                                               forbidden_upgrade=forbidden[0] if forbidden else ''))
            if special_powers:
                got['special_powers'] = special_powers
            attachments = []
            for h, inner in _blocks(bare, 'AttachNugget'):
                filters = list(_blocks(inner, 'SpecialObjectFilter'))
                if (re.sub(r'<SpecialObjectFilter\b[^>]*/>', '', inner).strip() or len(filters) > 1
                        or set(re.findall(r'(\w+)\s*=', h)) - {'id', 'AttachModuleId', 'ForbiddenTargetObjectStatus', 'Radius'}
                        or _num(_attr(h, 'Radius', '0'), float('nan')) != 0
                        or (filters and (filters[0][1].strip() or _attr(filters[0][0], 'Rule', 'ANY') != 'ANY'
                            or set(re.findall(r'(\w+)\s*=', filters[0][0])) - {'Rule', 'Include', 'Exclude'}))):
                    unsupported.append('AttachNugget')
                else:
                    f = filters[0][0] if filters else ''
                    attachments.append(dict(module=_attr(h, 'AttachModuleId'),
                                            forbidden=_attr(h, 'ForbiddenTargetObjectStatus', '').split(),
                                            include=_attr(f, 'Include', '').split(), exclude=_attr(f, 'Exclude', '').split()))
            if attachments:
                got['attach'] = attachments
            contained = []
            for h, inner in _blocks(bare, 'DamageContainedNugget'):
                filters = list(_blocks(inner, 'DamageObjectFilter'))
                if (len(filters) != 1 or re.sub(r'<DamageObjectFilter\b[^>]*/>', '', inner).strip()
                        or _attr(filters[0][0], 'Rule', 'NONE') != 'NONE'
                        or set(re.findall(r'(\w+)\s*=', filters[0][0])) - {'Rule', 'Include', 'Exclude'}
                        or set(re.findall(r'(\w+)\s*=', h)) - {'id', 'Damage', 'DamageType', 'DeathType', 'MaxUnitsToDamage', 'Radius', 'DelayTimeSeconds'}
                        or _num(_attr(h, 'Radius', '0'), float('nan')) != 0
                        or any(war) or _secs(_attr(h, 'DelayTimeSeconds', '0s'))):
                    unsupported.append('DamageContainedNugget')
                else:
                    f = filters[0][0]
                    contained.append(dict(damage=_num(_attr(h, 'Damage')), type=_attr(h, 'DamageType', 'UNDEFINED'),
                                          maximum=int(_num(_attr(h, 'MaxUnitsToDamage', '100'))),
                                          include=_attr(f, 'Include', '').split(), exclude=_attr(f, 'Exclude', '').split()))
            if contained:
                got['contained'] = contained
            dots = []
            for h, inner in _blocks(bare, 'DOTNugget'):
                if (inner.strip() or any(war) or _num(_attr(h, 'Radius', '0'), float('nan')) != 0
                        or set(re.findall(r'(\w+)\s*=', h)) - {'id', 'Damage', 'DamageType', 'DamageFXType', 'DeathType', 'DamageInterval', 'DamageDuration', 'RemoveIfHealed', 'Radius'}
                        or _secs(_attr(h, 'DamageInterval')) <= 0 or _secs(_attr(h, 'DamageDuration')) < 0):
                    unsupported.append('DOTNugget')
                else:
                    dots.append(dict(damage=_num(_attr(h, 'Damage')), type=_attr(h, 'DamageType', 'UNDEFINED'),
                                     interval=_frames(_secs(_attr(h, 'DamageInterval'))),
                                     duration=_frames(_secs(_attr(h, 'DamageDuration'))),
                                     remove_healed=_attr(h, 'RemoveIfHealed', 'true') == 'true'))
            if dots:
                got['dot'] = dots
            if unsupported:
                got['unmodeled_effects'] = unsupported
            if sd:
                got['sd'] = sd[0]
            if any(ocl):
                got['ocl'] = next(o for o in ocl if o)          # the first (a _VET one follows the plain one)
            if pre:
                got['pre'] = _secs(pre.group(1))
            if _attr(head, 'PreAttackType'):
                got['pretype'] = _attr(head, 'PreAttackType')
            if _attr(head, 'WeaponSpeed'):
                got['weapon_speed'] = _num(_attr(head, 'WeaponSpeed'))
            got['weapon_key'] = wid
            if _attr(head, 'AttackRange'):
                got['range'] = _num(_attr(head, 'AttackRange'))
            if dmg:
                got['damage'] = sum(d for d, _ in dmg)
                if any(t for _, t in dmg):                  # an override writing only Damage keeps the type
                    got['type'] = next(t for _, t in dmg if t)
            taper = [(_num(_attr(h, 'Radius', '0')), _num(_attr(h, 'MinRadius', '0')), _num(_attr(h, 'DamageTaperOff')))
                     for h, _ in _blocks(bare, 'DamageNugget') if _attr(h, 'DamageTaperOff') is not None]
            if _attr(head, 'DamageDealtAtSelfPosition') == 'true' and len(taper) == 1:
                got['taper'] = taper[0]                     # (Radius, MinRadius, DamageTaperOff): combat/damage.py
            if _attr(head, 'DamageDealtAtSelfPosition') is not None:     # an inheritor keeps its parent's
                got['at_self'] = _attr(head, 'DamageDealtAtSelfPosition') == 'true'
            if any(war):
                got['warhead'] = next(w for w in war if w)
            if _attr(head, 'ClipSize'):
                got['shots'] = int(_num(_attr(head, 'ClipSize'), 0.0))
            for k, mt in (('fire', fire), ('reload', reload_), ('delay', delay)):
                if mt:
                    got[k] = _secs(mt.group(1))
            if _attr(head, 'RequiredAntiMask'):
                got['anti'] = _attr(head, 'RequiredAntiMask').split()
            if _attr(head, 'Flags') is not None:                # a template that writes Flags writes all of them
                got['los'] = 'ATTACK_NEEDS_LINE_OF_SIGHT' in _attr(head, 'Flags').split()
            defs.append((wid, got, _attr(head, 'inheritFrom')))
    own, parent = {}, {}
    for overrides in (False, True):                     # every override after every first definition, whatever the
        for wid, got, p in defs:                        # file order
            if (p == wid) != overrides:
                continue
            if overrides:
                own[wid] = {**own.get(wid, {}), **got}
            else:
                own[wid], parent[wid] = got, p
    base = dict(range=0.0, damage=0.0, type='', shots=1, fire=0.0, reload=0.0, delay=0.0, anti=[], warhead=None, los=False,
                ocl=None, pre=0.0, pretype='PER_SHOT', sd=0.0)
    out = {}

    def get(wid, depth=0):
        if wid not in out:
            p = parent.get(wid)
            if p in own and p != wid and depth < 10:
                up = get(p, depth + 1)
            else:
                up = (base_table or {}).get(p, base)
            out[wid] = {**up, **own[wid]}
        return out[wid]
    for wid in own:
        get(wid)
    return out


def _pre_per_clip(w, shots):
    """The PreAttackDelay seconds one clip of `shots` waits: before every shot (PER_SHOT, the default), before the
    clip's first (PER_CLIP), none in a long fight (PER_TARGET / PER_ATTACK: once per target). The game's weapon goes
    CoolDown -> PreFire -> Fire, the pre-attack after the shot delay, not under it (read 1.13, work/re/fire_state.md;
    Generals Weapon::getPreAttackDelay); bench engine_ocl a 2026-11-08: the Athena's round comes every ~5.3 s =
    pre-attack 2 + firing 2 + reload 1.1."""
    kind = w.get('pretype', 'PER_SHOT')
    if kind == 'PER_CLIP' and w['shots'] > 0:
        return w.get('pre', 0.0)
    if kind in ('PER_SHOT', 'PER_CLIP'):
        return w.get('pre', 0.0) * shots
    return 0.0


def _resolve(w, weapons):
    """A weapon's damage per second: its own damage, else its warhead's, else the round of the objects its OCL makes
    (ocl_round); one clip of `shots` (each after its pre-attack) then the reload."""
    dmg, typ = w['damage'], w['type']
    # the AI's per-weapon damage (CampaignLab work/re l4_efficiency.md 3, read): every damage nugget on the weapon
    # summed, then its child weapon's -- so a weapon with its own small nugget and a warhead counts both (the attack
    # dog's Maul: 1 UNRESISTABLE + its warhead's 200 MELEE). The combat below keeps "own, else the warhead's".
    parts = [(dmg, typ)] if dmg else []
    if w['warhead'] in weapons and weapons[w['warhead']]['damage']:
        h = weapons[w['warhead']]
        parts.append((h['damage'], h['type']))
    parts += [p for p in w.get('ai_damage', []) if p[0]]    # nuggets only the AI's rate counts (the leech beam)
    if not dmg and w['warhead'] in weapons:
        h = weapons[w['warhead']]
        dmg, typ = h['damage'], h['type']
    if not dmg and w.get('ocl'):
        dmg, typ = ocl_round(w['ocl'], weapons)
    shots = max(w['shots'], 1)
    cycle = _clip_frames(w, shots) / FPS        # whole frames, each part rounded up (engine line C round 6, engine_clip)
    sd = w.get('sd', 0.0)
    if not parts and dmg:
        parts = [(dmg, typ)]
    return dict(range=w['range'], dps=round(dmg * shots / cycle, 2) if dmg else 0.0, type=typ, anti=w['anti'],
                ai_parts=[(round(d * shots / cycle, 2), t) for d, t in parts],
                los=w['los'], sd=sd, sdps=round(sd * shots / cycle, 2) if sd > 0 else 0.0,
                dmg=dmg, cycle=cycle, sched=_shot_times(w, shots), projectile=w.get('projectile'),
                suppression=w.get('suppression', weapons.get(w.get('warhead'), {}).get('suppression', [])),
                hit_modifiers=w.get('hit_modifiers', weapons.get(w.get('warhead'), {}).get('hit_modifiers', [])),
                line=w.get('line', weapons.get(w.get('warhead'), {}).get('line')),
                strip_max_health=w.get('strip_max_health', weapons.get(w.get('warhead'), {}).get('strip_max_health', [])),
                emp_seconds=w.get('emp_seconds', weapons.get(w.get('warhead'), {}).get('emp_seconds', [])),
                leech_percent=w.get('leech_percent', 0.0), leech_health=w.get('leech_health', 0.0),
                sweep=w.get('sweep'), contained=w.get('contained', []), dot=w.get('dot', []),
                special_powers=w.get('special_powers', weapons.get(w.get('warhead'), {}).get('special_powers', [])),
                attach=w.get('attach', weapons.get(w.get('warhead'), {}).get('attach', [])),
                lift=w.get('lift', weapons.get(w.get('warhead'), {}).get('lift', [])),
                **({'grapple': w['grapple']} if w.get('grapple') else {}),
                inform=w.get('inform', []), weapon_speed=w.get('weapon_speed', 999999.0),
                weapon_key=w.get('weapon_key'), **({'taper': w['taper']} if w.get('taper') else {}),
                **({'at_self': True} if w.get('at_self') else {}),
                meta_impacts=w.get('meta_impacts', weapons.get(w.get('warhead'), {}).get('meta_impacts', [])),
                delayed_meta_impacts=w.get('delayed_meta_impacts',
                    weapons.get(w.get('warhead'), {}).get('delayed_meta_impacts', [])),
                unmodeled_effects=list(dict.fromkeys(w.get('unmodeled_effects', []) +
                    weapons.get(w.get('warhead'), {}).get('unmodeled_effects', []))))


def queue_dock(template, own=None):
    """Whether the effective template supplies QueueDock (E164, work/re/e164_queuedock.md).

    Only module presence is consumed here; bone positions and waiting places remain gaps.
    """
    def read(xml):
        text = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        return bool(list(_blocks(text, 'QueueDockBehavior')))
    return _inherited(template, own, read, False)


def lift_module(template, own=None):
    """D50 timing interface, see work/re/d50_lift_release.md.

    Only explicit timer fields are supported; no guessed XSD defaults (an absent LiftVelocity /
    MaxElevationFromGround rises 0). soft: a SoftLandingWeapon is set (LiftTimers' landing). crash: the
    AirplaneCrashWeapon an aircraft hit fires on itself (engine/combat/lift.py), None without one.
    """
    def read(xml):
        modules = list(_blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'LiftObjectUpdate'))
        if not modules:
            return None
        h, inner = modules[0]
        if len(modules) != 1 or inner.strip() or any(_attr(h, k) is None for k in ('TimeIncrement', 'MaxTimeLifted')):
            return False
        return dict(increment=int(_secs(_attr(h, 'TimeIncrement')) * FPS),
                    maximum=int(_secs(_attr(h, 'MaxTimeLifted')) * FPS),
                    rise=_num(_attr(h, 'LiftVelocity') or '0', 0.0),
                    top=_num(_attr(h, 'MaxElevationFromGround') or '0', 0.0),
                    soft=_attr(h, 'SoftLandingWeapon') is not None, crash=_attr(h, 'AirplaneCrashWeapon'))
    return _chain(template, own, read)


SOFT_TOP = 28.0   # the highest lift whose soft landing clears LIFTED: 28 clears, 40 / 60 keep it (INFERRED edge)


class LiftTimers:
    """Caster-owned target ledger, D50. Release does not clear object status.

    A positive counter is decremented, the target rising `rise` a frame to `top`; a zero counter releases on its
    next update. New entries use increment directly, only renewal clamps to max. A released lift with a
    SoftLandingWeapon from no higher than SOFT_TOP falls knock-back's curve (meta_impact_fall: 20 frames from 28)
    and its LIFTED_INTO_AIR goes the frame after it lands (`landed`, the host clears): bench 11-11
    engine_lift_probe, 28 up lifted 28 frames from the hit (7 + 20 + 1), 36 for 15 frames capped at 28;
    40 and 60 up never cleared (D52's 0.1 s modifier on landing; why the higher falls keep it is not read).
    """
    def __init__(self):
        self.remaining, self.height, self.landing, self.landed = {}, {}, {}, []

    def hit(self, caster, target, increment, maximum, rise=0.0, top=0.0, soft=False, serial=None):
        key = (caster, target)
        self.remaining[key] = (min(maximum, self.remaining[key] + increment)
                               if key in self.remaining else increment)
        self.height.setdefault(key, [0.0, rise, top, soft, serial])

    def tick(self, fall=lambda serial, z: len(meta_impact_fall((0.0, 0.0, z), (0.0, 0.0, 0.0), 0.0)[0])):
        """fall(target's serial, height): its fall's frames (the host's: the curve from where it is, the 20 grid's
        snap included -- 20 frames from 28 at the probe's spot, 18 at the origin); `landed`: the serials landed."""
        released, self.landed = [], []
        for target, (left, serial) in list(self.landing.items()):
            if left > 1:
                self.landing[target] = (left - 1, serial)
            else:
                self.landed.append(serial)
                del self.landing[target]
        for key, left in list(self.remaining.items()):
            h = self.height[key]
            if left > 0:
                self.remaining[key] -= 1
                h[0] = min(h[2], h[0] + h[1])
            else:
                released.append(key)
                del self.remaining[key], self.height[key]
                if h[3] and h[0] <= SOFT_TOP:
                    self.landing[key[1]] = (fall(h[4], h[0]), h[4])
        return released


def meta_impact_delay_frames(seconds):
    """D39: float32 seconds * 15, rounded to float32 before ceil.

    In particular 1.2s gives 18, not ceil(double(float32(1.2))*15)=19.
    Only ordinary positive delays at normal game speed are supported.
    """
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('MetaImpact delay must be finite and positive')
    def f32(value):
        return struct.unpack('<f', struct.pack('<f', value))[0]
    return math.ceil(f32(f32(seconds) * FPS))


class MetaImpactDelayQueue:
    """Isolated phase-1 expiry output, never a Physics/landing replay.

    Supply collision frame and selected payload explicitly. At c the entry is
    inserted after phase 1; c+1 first decrements D, and strict-negative expiry
    emits at c+D+1. due(frame) consumes ready events once, including skipped
    frames. Returned tuples are (expiry frame, effect, caller payload).
    Filters, Speed, time scaling, victim lifetime and Physics remain gaps.
    """

    def __init__(self):
        self.pending = []

    def enqueue(self, collision_frame, effect, payload):
        when = collision_frame + meta_impact_delay_frames(effect['delay_seconds']) + 1
        self.pending.append((when, dict(effect), payload))

    def due(self, frame):
        ready = sorted((event for event in self.pending if event[0] <= frame), key=lambda event: event[0])
        self.pending[:] = [event for event in self.pending if event[0] > frame]
        return ready


def meta_impact_velocity(effect, position, centre, height, *, detonation, resistance=0.0):
    """Ordinary immediate shock, world units/frame, before grounded lift.

    engine_knock_probe land/late: the direction uses the victim's half-height,
    but radial attenuation uses its feet. Instant hits do not push. This is a
    numerical interface for an already selected victim. Filters, delays and
    cyclonic/clear variants remain outside the ordinary execution slice.
    INFERRED: an exactly centred target uses the engine's vertical fallback;
    actual projectile collision noise can give it a different direction.
    """
    if not detonation or resistance >= 1:
        return (0.0, 0.0, 0.0)
    delta = [position[i] - centre[i] for i in range(3)]
    delta[2] += height / 2
    if effect.get('invert'):
        # engine_knock_invert a/b: inverse direction, same radial attenuation.
        # Only horizontal (ZMult=0), immediate unfiltered XML is enabled.
        delta = [-x for x in delta]
    if all(abs(x) <= 1e-4 for x in delta):
        delta = [0.0, 0.0, 1.0]
    length = math.sqrt(sum(x * x for x in delta))
    radius = effect['radius']
    distance = math.dist(position, centre)
    falloff = min(1.0, 1 - distance / radius + effect['taper']) if radius > 0 else 1.0
    scale = effect['amount'] / FPS * (1 - resistance) * falloff / length
    return (delta[0] * scale, delta[1] * scale, delta[2] * scale * effect['zmult'])


def meta_impact_ground_launch(position, velocity):
    """Grounded launch parameters, not the duration of flight.

    Default Physics gravity multiplier 1; floor-to-20 landing grid INFERRED.
    n is a landing parameter, never the flight duration.
    No airborne relaunch, terrain search, standing time or fall damage here.
    """
    if not any(velocity):
        return dict(steps=0, height=0.0, landing=tuple(position))
    vz = max(velocity[2], math.sqrt(sum(v * v for v in velocity)) / 4)
    n = max(1, int(2 * vz / (64 / FPS ** 2)))
    return dict(steps=n, height=n * vz / 4,
                landing=(math.floor((position[0] + velocity[0] * n) / 20) * 20,
                         math.floor((position[1] + velocity[1] * n) / 20) * 20,
                         position[2]))


def meta_impact_trajectory(position, velocity, landing=None):
    """Default Physics on level ground, sampled once per frame (land/late).

    Ordinary grounded launch only: no bounce, terrain obstruction or relaunch.
    Length is integrated numerically; ceil(L/b)+1, clamped to 3..128 points.
    The indent percentages are 33/66, not exact thirds.
    landing: the end the engine moved the body's own landing to (a cell it can stand on, Physics P3, bench 11-11
    engine_knock_water man / far): the curve is rebuilt to it with the launch's height a and step b unchanged (the
    engine's `build ... a= b=` line) -- man 2060 -> 2080, 5 points, apex 223.0; far 2060 -> 2500, 28 points.
    A landing lower than the launch by d (bench 11-11 engine_knock_water tank / ramp, ra3ext.log probe lines fitted to
    0.005): the first control stays 1.3 a over the launch, the second is 1.3 max(0, a - d) over it -- tank's direct
    hit (a 16.3, d 9.4) 221.47, ramp's and tank's wet ones (a < d) at the launch height. A landing higher than the
    launch (bench 11-11 engine_knock_water climb, the wet Hammer up the table's ramp, 212.5 -> 268.75, a 9.49): both
    controls 1.3 a over the LANDING (281.09; its 18 probe points fitted to 0.005), the curve over the ramp's slope.
    """
    plan = meta_impact_ground_launch(position, velocity)
    if not plan['steps']:
        return [tuple(position)]
    end, a, n = plan['landing'] if landing is None else landing, max(plan['height'], 0.5), plan['steps']
    b = max(64 / FPS**2, (math.hypot(velocity[0]*n, velocity[1]*n) + 2*plan['height']) / n)
    return _knock_curve(position, end, a, b)


def meta_impact_fall(position, velocity, ground, gravity=1.0):
    """A body set falling in the air (Physics P5, bench 11-11 engine_crash_fall: a shot-down Apollo's wreck, made
    LIKE_EXISTING INHERIT_VELOCITY x 0.5 175 over level ground, ra3ext's `shock` / `build` lines and its probe
    points): the same curve as a knock-back, its numbers from the fall. T = the free fall's frames from the drop d
    under g = 64/225 x the body's OWN GravityMultiplier (the wreck's: the live plane's 30 never comes in, it is gone);
    n = ceil(T) + 1 (37 / 8), the landing = start + velocity x n to the nearest 20 (round 180, below), a = n vz / 4,
    the step b = (horizontal speed x n + 2a + d) / n (12.2286 / 29.3680 as logged). Plain lands in 30 points (29
    frames), GM 30 in 8 (7 frames), a hovering plane's (v 0.1) in 38. Returns (points, landing)."""
    d = max(0.0, position[2] - ground)
    g = 64 / FPS**2 * gravity
    vz = velocity[2]
    t = (vz + math.sqrt(vz * vz + 2 * g * d)) / g
    h = math.hypot(velocity[0], velocity[1])
    # Round 180 (bench 11-12 engine_crash_hit, CampCHHit_mcp_1112_111034): a hovering plane's wreck, v (0.1, 0, 0),
    # logged land 3000 and b 4.8297 = (0.1 x 37 + 175) / 37 -- n is not from the landing's distance (0 there) but
    # ceil(T) + 1 (37 / 37 / 8 for hover / plain / GM 30), and the landing is start + v n to the NEAREST 20 (3003.7 ->
    # 3000, 3162.5 -> 3160, 2945 -> 2940): all three logged lines, the old rule (start + v T rounded up) missed hover's
    n = math.ceil(t - 1e-9) + 1
    end = tuple(round((position[i] + velocity[i] * n) / 20) * 20 for i in (0, 1)) + (ground,)
    a = n * vz / 4
    return _knock_curve(position, end, max(a, 0.5), (h * n + 2 * a + d) / n), end   # a's floor 0.5 as a knock's


def _knock_curve(position, end, a, b):
    """The knock curve from `position` to `end`: a cubic, its controls at 33 / 66 of the way, the first 1.3 a over
    the start, the second 1.3 max(0, a - drop) over it (both 1.3 a over a higher end), sampled at ceil(length / b)
    + 1 points (3 .. 128)."""
    drop = max(0.0, position[2] - end[2])
    first, second = position[2] + 1.3 * a, position[2] + 1.3 * max(0.0, a - drop)
    if end[2] > position[2]:
        first = second = end[2] + 1.3 * a
    controls = [position,
                (position[0] + .33 * (end[0] - position[0]),
                 position[1] + .33 * (end[1] - position[1]), first),
                (position[0] + .66 * (end[0] - position[0]),
                 position[1] + .66 * (end[1] - position[1]), second), end]

    def point(t):
        weights = ((1-t)**3, 3*(1-t)**2*t, 3*(1-t)*t*t, t**3)
        return tuple(sum(w*p[i] for w, p in zip(weights, controls)) for i in range(3))

    # Converge the polyline length rather than choosing a duration from bench values.
    count, previous = 16, 0.0
    while True:
        points = [point(i/count) for i in range(count+1)]
        length = sum(math.dist(p, q) for p, q in zip(points, points[1:]))
        if abs(length - previous) < 1e-5 or count >= 16384:
            break
        previous, count = length, count * 2
    size = min(128, max(3, math.ceil(length/b) + 1))
    return [point(i/(size-1)) for i in range(size)]


# PhysicsBehavior.xsd defaults (every campaign template's Physics: work/re/a_physics_plan.md): after a knock-back
# lands the body lies ShockStunnedTimeLow..High, then gets up for ShockStandingTime
SHOCK_STUNNED, SHOCK_STANDING = 1.0, 1.5


def meta_impact_landing_hold():
    """Frames a knocked-back body keeps still from its first frame on the ground (default Physics only, as
    meta_impact_body): bench 11-11 engine_knock_probe stand, a move order given in the air is kept and the first step
    comes 38 frames after the landing = ceil((1 + 1.5) x 15). ceil of the sum and the sum of the ceils (15 + 23) are
    both 38 here: which one RA3 takes is not told apart. Holds moving only; firing while knocked is not measured."""
    return _frames(SHOCK_STUNNED + SHOCK_STANDING)


# An attack order kept through the knock walks later than a move order: first step at landing + 50, not + 38 (bench
# 11-11 engine_knock_water farfire, the Hammer ~158 degrees round from his flight, and farwalk, straight ahead: both
# 249 from a landing at 199 -- not a turn). Which engine wait it is (the attack state's own re-think) is INFERRED.
KNOCK_ATTACK_WAIT = 12


def meta_impact_resistance(template, own=None):
    """The object's ShockwaveResistance (GameObject attribute, inherited; schema default 0): BaseVehicle 90,
    BaseRepairDrone 120, JapanMechaKing 101, infantry 0. A shock whose nugget amount is under it launches nothing
    (Physics P3 gate, bench 11-11 engine_knock_water: 89 and edge's first try at 60 nobody, 90 and 91 all three): the
    raw ShockWaveAmount, before the distance falloff -- the dry Hammer flew at 90 with 0.63 of it (57)."""
    def read(xml):
        head = re.search(r'<GameObject\b[^>]*>', xml)
        value = _attr(head.group(0), 'ShockwaveResistance') if head else None
        return None if value is None else _num(value)
    return _inherited(template, own, read, None) or 0.0


def meta_impact_body(template, own=None):
    """Height for an unmodified Physics module, None for unsupported/no Physics.

    Restrict the first execution slice to the probe's default module. Overrides
    (including resistance, gravity and alternate curve branches) remain gaps.
    """
    physics = _inherited(template, own, lambda xml: next(_blocks(xml, 'Physics'), None), None)
    if physics is None or (physics[1] or '').strip() or set(re.findall(r'(\w+)\s*=', physics[0])) - {'id'}:
        return None
    def height(xml):
        geometry = next(_blocks(xml, 'Geometry'), None)
        shape = next(_blocks(geometry[1] or '', 'Shape'), None) if geometry else None
        # Retail Tesla Trooper spells this as Height = "15.0".
        value = re.search(r'\bHeight\s*=\s*"([^"]*)"', shape[0]) if shape else None
        return _num(value.group(1)) if value else None
    return _inherited(template, own, height, None)


def _shot_times(w, shots):
    """The seconds, from the start of a clip's cycle, at which each of its `shots` lands: shot k after the
    pre-attack delay(s) and k gaps of max(FiringDuration, DelayBetweenShots) before it; the clip's cycle (the reload
    after the last gap) is `_resolve`'s `cycle`. Engine line C round 2: the fight fires by this clock, not a
    continuous damage per second (the mean rate is the same: dmg x shots / cycle)."""
    gap = _frames(max(w['fire'], w['delay'], 0.1))
    kind = w.get('pretype', 'PER_SHOT')
    pre = _frames(w.get('pre', 0.0))
    out, t = [], 0
    for k in range(shots):
        if kind == 'PER_SHOT' or (kind == 'PER_CLIP' and k == 0):
            t += pre
        out.append(round(t / FPS, 4))
        t += gap
    return out


FPS = 15.0


def _frames(seconds):
    """A duration in whole frames, rounded up (engine_clip, bench 2026-11-09: every part of the weapon's rhythm is
    ceil(seconds x 15): pre-attack, firing, reload). The 1e-6 keeps 1.2 x 15 = 18.000000000000004 at 18."""
    return int(math.ceil(seconds * FPS - 1e-6))


def _clip_frames(w, shots):
    """Frames of one cycle of a clip of `shots` shots: each shot = its pre-attack (PER_SHOT; once for a PER_CLIP clip
    -- the bench's coilpc reads as the coil) + max(FiringDuration, DelayBetweenShots, 0.1), then the reload after the
    last. engine_clip: clip3p gap 13 = 8 + 5, the clip's end 43 = 13 + 30; coil 48 = 38 + 8 + 2."""
    gap = _frames(max(w['fire'], w['delay'], 0.1))
    kind = w.get('pretype', 'PER_SHOT')
    pre = _frames(w.get('pre', 0.0))
    if w['shots'] <= 0:                         # an unlimited clip: no reload
        return gap + (pre if kind in ('PER_SHOT', 'PER_CLIP') else 0)
    n = shots * gap + _frames(w['reload'])
    if kind == 'PER_SHOT':
        n += shots * pre
    elif kind == 'PER_CLIP':
        n += pre
    return n


_ocls = None


def _ocl_table():
    """ObjectCreationList id -> [(count, object template)] (every CreateObject of it), from the SageXML."""
    global _ocls
    if _ocls is None:
        _ocls = {}
        for root, _, files in os.walk(SAGEXML):
            for f in files:
                if not f.endswith('.xml'):
                    continue
                text = open(os.path.join(root, f), encoding='utf-8', errors='replace').read()
                if '<ObjectCreationList' not in text:
                    continue
                for head, body in _blocks(re.sub(r'<!--.*?-->', '', text, flags=re.S), 'ObjectCreationList'):
                    made, count = [], 1
                    for m in re.finditer(r'<CreateObject\b([^>]*)>([^<]*)', body):
                        if m.group(1).strip():                  # the outer element: its options and Count
                            count = int(_num(_attr(m.group(1), 'Count'), 1.0))
                        elif m.group(2).strip():                # the inner one: the template's name
                            made.append((count, m.group(2).strip()))
                    if _attr(head, 'id'):
                        _ocls[_attr(head, 'id')] = made
    return _ocls


def _game_object(template):
    """The <GameObject id=template> block of the retail file of that name ('' when none): a file can hold more than
    one (the Athena's effect and its veteran one)."""
    for head, body in _blocks(retail_xml(template), 'GameObject'):
        if _attr(head, 'id') == template:
            return body
    return ''


def ocl_round(ocl, weapons):
    """(damage, damage type) of one firing of a weapon whose WeaponOCLNugget makes `ocl`: each object it makes that
    lives LifetimeUpdate's MinLifetime and fires a FireWeaponUpdate weapon all that time (every frame for a weapon
    with no firing duration or shot delay; its own pre-attack is not waited for) and its FireWeaponWhenDead weapon once.
    Bench engine_oclone a 2026-11-10: FireDelay0.1s rounds to2frames; firing
    frames2..30 gives29x20, plus20 on death=600raw on a1000HP Hammer (40% left). An object with no FireWeaponUpdate (a drone with weapons of its own,
    the carrier's) gives 0: a unit the simulator would have to make (simcoverage lists it)."""
    dmg, typ = 0.0, ''
    for count, template in _ocl_table().get(ocl, []):
        body = re.sub(r'<!--.*?-->', '', _game_object(template), flags=re.S)
        life = re.search(r'<LifetimeUpdate\b[^>]*MinLifetime="([^"]+)"', body)
        fire = [(_attr(h, 'WeaponName'), _secs(_attr(h, 'FireDelay', '0s')))
                for h, _ in _blocks(body, 'FireWeaponNugget')]
        dead = [_attr(h, 'DeathWeapon') for h, _ in _blocks(body, 'FireWeaponWhenDead')]
        if not (life and any(w in weapons for w, _ in fire)):
            continue
        each = 0.0
        for wid, delay in fire:
            if wid in weapons:
                w = weapons[wid]
                every = max(1, _frames(max(w['fire'], w['delay'], 1.0 / LIFE_FPS)))
                first = max(1, _frames(delay))
                end = _frames(_secs(life.group(1)))
                # GUESSED endpoint convention beyond the Athena case: final lifetime
                # frame is included, then death weapon; engine_oclone replays600 total.
                shots = max(0, 1 + (end - first) // every)
                each += shots * w['damage']
                typ = typ or w['type']
        for wid in dead:
            if wid in weapons:
                each += weapons[wid]['damage']
                typ = typ or weapons[wid]['type']
        dmg += count * each
    return dmg, typ


def _armors():
    text = open(ARMOR, encoding='utf-8', errors='replace').read() if os.path.exists(ARMOR) else ''
    raw = {}
    for head, body in _blocks(text, 'ArmorTemplate'):
        own = {_attr(h, 'Damage'): _num(_attr(h, 'Percent'), 100.0) for h, _ in _blocks(body, 'Armor')}
        if _attr(head, 'Default') is not None:          # the types it does not name (percent: '*')
            own['*'] = _num(_attr(head, 'Default'), ARMOR_DEFAULT)
        for key, att in FLANK_KEYS.items():             # the side / rear scalars (flank), inherited as the percents
            if _attr(head, att) is not None:
                own[key] = _num(_attr(head, att), 100.0)
        raw[_attr(head, 'id')] = (_attr(head, 'inheritFrom'), own)
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


def read_fight(text, armors):
    """One unit's max health and armour from its XML, and `sets`: whether that text writes a WeaponSetUpdate of its
    own (comments left out). fight() reads the weapons from the template data port (step W1, ADR 0029) only then,
    as read_fight read them before: from the unit's own file, never inherited -- 25 retail templates inherit theirs
    (the tutorial tanks, A08's dogs, the Emperor mecha, the Rushmore heads ...) and hold no weapon (Sim.add notes the
    gap); reading the inherited ones is a change of behaviour of its own."""
    arm = re.search(r'<ArmorSet\b[^>]*\bArmor="([^"]+)"', text) or re.search(r'\bArmor="([^"]+)"', text)
    return dict(hp=number(text, 'MaxHealth'), armor=armors.get(arm.group(1), {}) if arm else {},
                sets=bool(re.search(r'<WeaponSetUpdate\b', re.sub(r'<!--.*?-->', '', text, flags=re.S))))


def frozen_armor(template, own=None, condition='SECONDARY_DAMAGE'):
    """The armour {type: percent} of a template's ArmorSet with Conditions SECONDARY_DAMAGE, from its own XML else what
    it inherits from (the retail units inherit it from BaseVehicle / BaseInfantry / BaseStructure; INFERRED that a
    unit's own ArmorSet does not drop the base's frozen one: frozen units break at a touch in the game); None where
    none is found. Its SecondaryDamageTracker is a kernel module (engine/modules/freeze.py, step M11). condition: a
    ToggleState's ArmorSet (the shielded Peacekeeper's PLAYER_UPGRADE, bench engine_hitreaction_r)."""
    def frozen(xml):
        m = re.search(r'<ArmorSet\b[^>]*\bArmor="([^"]+)"[^>]*\bConditions="[^"]*' + condition, xml or '')
        return m.group(1) if m else None
    try:
        a = _inherited(template, own, frozen, None)
    except (OSError, ValueError):
        return None
    return _fight_data()['armors'].get(a) if a else None


def bridge_generation_counts(template, length, own=None):
    """Count-only model for the two measured HB_Bridge_02 lengths (270/700).

    No world bodies/positions, pathing, health sharing or repair are generated.
    Other lengths/configurations return None: rounding beyond these samples is
    INFERRED. Read the XML so overrides cannot silently reuse retail results.
    """
    if template != 'HB_Bridge_02' or length not in (270, 700):
        return None
    def read(xml):
        for head, _ in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'BridgeBuilder'):
            return {key: _attr(head, key) for key in (
                'EndCap', 'EndCap2', 'EndCapLen', 'CenterPiece', 'CenterPieceLen',
                'CenterPieceB', 'CenterPieceBLen', 'GateHouse', 'GateHouse2', 'Width')}
        return None
    data = _chain(template, own, read)
    fields = ('EndCap', 'EndCap2', 'CenterPiece', 'CenterPieceB', 'GateHouse')
    suffixes = ('End', 'End2', 'Center', 'Center2', 'GateHouse')
    if not data or any(data[k] != 'HB_Bridge_02_' + v for k, v in zip(fields, suffixes)):
        return None
    if tuple(_num(data[k]) for k in ('EndCapLen', 'CenterPieceLen', 'CenterPieceBLen')) != (75, 150, 150) \
            or data['GateHouse2'] not in (None, data['GateHouse']) or _num(data['Width']) != 190:
        return None
    # Only the measured sample points; no unmeasured rounding law is assumed.
    counts = (1, 1, 1, 0, 2) if length == 270 else (1, 1, 2, 2, 2)
    return {data[k]: n for k, n in zip(fields, counts)}


def bridge_pair_generation_counts(start, end, length, own=None):
    """Count-only retail mixed-pair baseline, HB start / Bridge1a end, 270/700.

    No world creation or geometry. Only the exact measured pair/configuration is
    supported; end-marker template usage does not imply its builder creates parts.
    engine_bridgebuilder_b:b reads 1322/12/1322/33 (2026-11-11); Bridge1 parts zero.
    """
    if (start, end) != ('HB_Bridge_02', 'Bridge1a'):
        return None
    counts = bridge_generation_counts(start, length, own)
    if counts is None:
        return None
    def read(xml):
        for head, _ in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'BridgeBuilder'):
            return {key: _attr(head, key) for key in (
                'EndCap', 'EndCap2', 'EndCapLen', 'CenterPiece', 'CenterPieceLen',
                'CenterPieceB', 'CenterPieceBLen', 'GateHouse', 'GateHouse2', 'Width')}
        return None
    data = _chain(end, own, read)
    expected = dict(EndCap='Bridge1_End', EndCap2='Bridge1_End2',
                    CenterPiece='Bridge1_Center2', CenterPieceB='Bridge1_Center2',
                    GateHouse='Bridge1_GateHouse')
    if not data or any(data[k] != v for k, v in expected.items()):
        return None
    if tuple(_num(data[k]) for k in ('EndCapLen', 'CenterPieceLen', 'CenterPieceBLen', 'Width')) \
            != (25, 50, 50, 180) or data['GateHouse2'] not in (None, data['GateHouse']):
        return None
    return dict(counts, **{'Bridge1_' + suffix: 0 for suffix in
                          ('End', 'End2', 'Center', 'Center2', 'GateHouse')})


def manager_proxy_health(template, own=None):
    """Whole-proxy effective HP of a template whose Body is a ManagerBody (the caller asks for one only: Sim.add, by
    the port's ManagerBody blocks); INFERRED from engine_managerbody a / b.

    HB_Bridge_02 at lengths 270 / 700 loses 20 percent to 200 script damage,
    independent of length, and lethal damage leaves a live 1-percent proxy.
    Use the retail center body's MaxHealth (1000), not ManagerBody's XML 1.
    Mapping that observable floor to exactly 1% HP is INFERRED (a counter-side
    minimum of 1 could hide lower internal HP); internal HP,
    other bridge configurations, segment damage/sharing and repairs are unbenched.
    This creates no bridge pieces and does not sum their health.
    """
    def read(xml):
        for head, _ in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'BridgeBuilder'):
            center = _attr(head, 'CenterPiece')
            return max_health(center, own) if center else None
        return None
    return _chain(template, own, read)


def wall_builder_start(template, own=None):
    """Startup only: engine_wallinit:a measured the default WALL_SEGMENT bit.

    Construction, connections, limits and nondefault status/model flags are gaps.
    Nearest declaration supplies StartInSecondaryModel (retail segments write it).
    INFERRED outside those profiles: defaults on the nearest declaration; arbitrary
    inherited field overrides have not been compared.
    """
    def read(xml):
        clean = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        for head, _ in _blocks(clean, 'WallBuilderBehavior'):
            return {'secondary': _attr(head, 'StartInSecondaryModel', 'false').lower() == 'true',
                    'status': _attr(head, 'SecondaryObjectStatus', 'WALL_SEGMENT')}
        return None
    return _chain(template, own, read)


BODY = frozenset({'ActiveBody', 'ImmortalBody', 'PropBody', 'ManagerBody', 'ManagedActiveBody',
                  'ManagedImmortalBody', 'HighlanderBody'})


class _ModuleTemplates:
    """Read source GameObjects and merge the parts that supply module data."""

    ASSET = 'uri:ea.com:eala:asset'
    XI = 'http://www.w3.org/2001/XInclude'
    XAI = 'uri:ea.com:eala:asset:instance'
    JOIN = f'{{{XAI}}}joinAction'
    POSITION = f'{{{XAI}}}insertPosition'
    XSD = '{http://www.w3.org/2001/XMLSchema}'
    GROUPS = frozenset({'Behaviors', 'Body', 'AI', 'Draws', 'ClientUpdates', 'ClientBehaviors'})
    # The attribute a repeated element is matched by in a container of this type, 'id' elsewhere (xml_merge.md b).
    # Review l P2 (W2b, INFERRED: xml_merge.md measured the lower-case id only): a WeaponSetUpdate's slots by their
    # ID (each slot kind its own schema element, so by (tag, ID)); a child's slot of a new ID is still added after
    # the parent's. A slot's <Weapon> lines have no key (one slot holds several lines of one Ordering, each under its
    # own status: 295 templates, w2b_draft): a child's lines are added after the parent's in the merged slot.
    KEYS = {'WeaponSetUpdateModuleData': 'ID'}

    @classmethod
    def _document(cls, text):
        # Unit XML also accepts bare GameObject fragments with the standard prefixes.
        text = re.sub(r'^\s*\ufeff?\s*<\?xml\s[^?]*\?>', '', text, count=1)
        return ET.fromstring(f'<Source xmlns:xi="{cls.XI}" xmlns:xai="{cls.XAI}">{text}</Source>')

    @classmethod
    def _includes(cls, node, path, active):
        for i, child in reversed(list(enumerate(node))):
            if child.tag != f'{{{cls.XI}}}include':
                cls._includes(child, path, active)
                continue
            href = child.get('href', '').replace('\\', '/')
            source = os.path.normpath(os.path.join(SAGEXML, href[5:]) if href.startswith('DATA:')
                                      else os.path.join(os.path.dirname(path) if path else SAGEXML, href))
            if source in active:
                raise ValueError(f'circular XML include: {source}')
            fragment = cls._document(_text(source))
            cls._includes(fragment, source, active | {source})
            node.remove(child)
            node[i:i] = list(fragment)

    @classmethod
    def _objects(cls, text, path=None):
        key = ('module_objects', text, path)
        if key not in _reads:
            root = cls._document(text)
            cls._includes(root, path, {path} if path else set())
            for node in root.iter():
                node.tag = node.tag.removeprefix(f'{{{cls.ASSET}}}')
            objects = {}
            for asset in (root, *root.findall('AssetDeclaration')):
                local = {d.attrib['name']: d.attrib['value']
                         for d in asset.findall('Defines/Define') if 'name' in d.attrib and 'value' in d.attrib}
                for obj in asset.findall('GameObject'):
                    for node in obj.iter():
                        for attr, value in node.attrib.items():
                            if value.startswith('=') and ('$' in value or "'" in value):
                                node.set(attr, expand(value, extra=local))
                        if node.text and node.text.strip().startswith('=$'):
                            node.text = expand(node.text.strip(), extra=local)
                    name = obj.get('id', '').lower()
                    if name in objects:
                        raise ValueError(f'duplicate GameObject: {name}')
                    objects[name] = obj
            _reads[key] = objects
        return _reads[key]

    @classmethod
    def _lookup(cls, name, own, source=None, original=False):
        if source is not None and name in source:
            return source
        if not original:
            for xml in own:
                objects = cls._objects(xml)
                if name in objects:
                    return objects
        path = None if original else _sdk_source(name)
        if path:
            objects = cls._objects(_text(path), path)
            if name in objects:
                return objects
        text = retail_xml(name)
        return cls._objects(text, _retail_files.get(name)) if text else {}

    @classmethod
    def _types(cls):
        key = ('module_schema_types', labpaths.SDK3)
        if key not in _reads:
            schema = os.path.join(labpaths.SDK3, 'Schemas', 'xsd', 'CnC3Types.xsd')
            types, seen, pending = {}, set(), [schema]
            while pending:
                path = pending.pop()
                if path in seen:
                    continue
                seen.add(path)
                root = ET.parse(path).getroot()
                for node in root:
                    if node.tag == cls.XSD + 'include':
                        pending.append(os.path.normpath(os.path.join(os.path.dirname(path), node.attrib['schemaLocation'])))
                    elif node.tag == cls.XSD + 'complexType':
                        types[node.attrib['name']] = node
            _reads[key] = types
        return _reads[key]

    @classmethod
    def _fields(cls, type_name):
        """Nested element types, order and cardinality from the SDK's XML schema."""
        key = ('module_schema_fields', type_name)
        if key not in _reads:
            slots = []

            def fields(node):
                for part in node:
                    kind = part.tag.removeprefix(cls.XSD)
                    if kind == 'element':
                        slots.append(([part], part.get('maxOccurs', '1') != '1'))
                    elif kind == 'choice':
                        slots.append((part.findall(cls.XSD + 'element'), part.get('maxOccurs', '1') != '1'))
                    elif kind == 'extension':
                        base = cls._types().get(part.get('base'))
                        if base is not None:
                            fields(base)
                        fields(part)
                    elif kind in ('sequence', 'all', 'complexContent'):
                        fields(part)

            node = cls._types().get(type_name)
            if node is not None:
                fields(node)
            _reads[key] = {part.attrib['name']: (part.get('type'), slot, many)
                           for slot, (choices, many) in enumerate(slots) for part in choices}
        return _reads[key]

    @classmethod
    def _join(cls, parent, child, match, *, inherit, position):
        """Overlay the next child in its container. Replace takes the insertion path after removing its match."""
        action = child.get(cls.JOIN)
        if action is not None and not inherit:
            raise ValueError(f'{action} on {child.tag} without inheritFrom')
        if action == 'Remove':
            if match is None:
                raise ValueError(f'Remove has no matching {child.tag} ({child.get("id", "")})')
            parent.remove(match)
            return
        if match is not None and (action == 'Replace' or match.tag != child.tag):
            parent.remove(match)
            match = None
        if match is None:
            match = ET.Element(child.tag)
            parent.insert(position, match)
        match.attrib.update((key, value) for key, value in child.attrib.items() if key not in (cls.JOIN, cls.POSITION))
        if child.text and child.text.strip():
            match.text = child.text
        return match

    @classmethod
    def _merge(cls, parent, child, type_name, inherit):
        layout = cls._fields(type_name)
        default = (None, len(layout), False)
        for node in child:
            if child.tag == 'GameObject' and node.tag not in cls.GROUPS and node.tag != 'CrusherInfo':
                continue
            nested, slot, many = layout.get(node.tag, default)
            match, position = None, len(parent)
            if inherit:
                attr = cls.KEYS.get(type_name, 'id')
                key = node.get(attr)
                top = node.get(cls.POSITION) == 'Top'
                match_index = None
                for i, old in enumerate(parent):
                    old_slot = layout.get(old.tag, default)[1]
                    same = old_slot == slot and (node.tag in layout or old.tag == node.tag)
                    if same and (not many or key is not None and old.get(attr) == key):
                        match, match_index = old, i
                    if old_slot > slot or (same and top):
                        position = min(position, i)
                if match_index is not None and match_index < position and (
                        node.get(cls.JOIN) == 'Replace' or match.tag != node.tag):
                    position -= 1
            merged = cls._join(parent, node, match, inherit=inherit, position=position)
            if merged is not None:
                cls._merge(merged, node, nested, inherit)
        if child.tag == 'Body' and not len(parent):
            raise ValueError('Body has no module')

    @classmethod
    def _effective(cls, name, own, source=None, trail=frozenset(), original=False):
        objects = cls._lookup(name, own, source, original)
        obj = objects.get(name)
        if obj is None:
            return ET.Element('GameObject')
        ident = (name, id(obj))
        if ident in trail:
            raise ValueError(f'circular template inheritance: {name}')
        up = obj.get('inheritFrom', '').lower()
        if up == name:
            merged = cls._effective(name, (), trail=trail | {ident}, original=True)
        elif up:
            merged = cls._effective(up, own, objects, trail | {ident})
        else:
            merged = ET.Element('GameObject')
        cls._merge(merged, obj, 'GameObject', bool(up))
        return merged

    @staticmethod
    def _blocks(obj):
        blocks = {}
        for group in obj:
            for node in group if group.tag in _ModuleTemplates.GROUPS else (group,):
                xml = ET.tostring(node, encoding='unicode', short_empty_elements=False)
                head, _, rest = xml.partition('>')
                inner = rest.rsplit('</', 1)[0]
                blocks.setdefault(node.tag, []).append((head[len(node.tag) + 1:], inner))
        return blocks

    @classmethod
    def blocks(cls, template, tag, own):
        name = template.lower()
        direct = (own or {}).get(template)
        if tag == 'LifetimeUpdate':
            # The simulator arms scripted lifetimes only on mission-owned templates that declare one.
            obj = cls._objects(direct).get(name) if direct else None
            return cls._blocks(obj).get(tag, []) if obj is not None else []
        files = dict.fromkeys((direct, *(own or {}).values()))
        sources = tuple(xml for xml in files if xml)
        key = ('module_blocks', name, sources)
        if key not in _reads:
            _reads[key] = cls._blocks(cls._effective(name, sources))
        return list(_reads[key].get(tag, ()))


def module_blocks(template, tag, own=None):
    """[(attribute text, inner XML)] for this tag in the merged GameObject, in effective module order."""
    return _ModuleTemplates.blocks(template, tag, own)


def lose_health(template, own=None):
    """The template's state-gated LoseHealthUpdate: (DamagePerSecond, the ObjectStatusValidation RequiredStatus set),
    None without one. Bench 11-14 engine_acts_tgl (round 223): the Kirov's afterburners (GENERIC_TOGGLE_STATE) take
    200 a second of its 6000 from the press until the next press, 100 % -> 60 % over 12 s; HealthTrigger 0 % read as
    no floor; engine_drain a: the Dreadnought's 101 % drains from full health. One without a RequiredStatus is not
    modelled. The third item is the ForbiddenStatus set (engine_drain a: UNDER_IRON_CURTAIN holds the drain)."""
    def read(xml):
        for head, inner in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'LoseHealthUpdate'):
            v, _ = next(_blocks(inner, 'ObjectStatusValidation'), ('', ''))
            need = frozenset((_attr(v, 'RequiredStatus') or '').split())
            if need:
                return (_num(_attr(head, 'DamagePerSecond'), 0.0), need,
                        frozenset((_attr(v, 'ForbiddenStatus') or '').split()))
        return None
    try:
        return _inherited(template, own, read, None)
    except (OSError, ValueError):
        return None


def invis_broadcast(template, own=None):
    """The mirage tank's InvisibilityBroadcastUpdate (engine line C round 9, engine_stealth a / b, bench 11-05,
    docs/engine/stealth.md 1-2): {'range': BroadcastRange, 'period': UpdatePeriod frames, 'self': AffectsSelf,
    'relation' / 'include' / 'exclude' (the BroadcastObjectFilter: Relationship, Include KindOf, StatusBitFlagsExclude),
    'needs': ObjectStatusValidation RequiredStatus -- the broadcaster must carry them}; None without the module."""
    def read(xml):
        for head, inner in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'InvisibilityBroadcastUpdate'):
            f, _ = next(_blocks(inner, 'BroadcastObjectFilter'), ('', ''))
            v, _ = next(_blocks(inner, 'ObjectStatusValidation'), ('', ''))
            return {'range': _num(_attr(head, 'BroadcastRange'), 0.0),
                    'period': max(1, int(round(_secs(_attr(head, 'UpdatePeriod') or '1s') * LIFE_FPS))),
                    'self': (_attr(head, 'AffectsSelf', 'false') or '').lower() == 'true',
                    'relation': set((_attr(f, 'Relationship') or 'ALLIES ENEMIES NEUTRAL').split()),
                    'include': set((_attr(f, 'Include') or '').split()),
                    'exclude': set((_attr(f, 'StatusBitFlagsExclude') or '').split()),
                    'needs': set((_attr(v, 'RequiredStatus') or '').split())}
        return None
    try:
        return _inherited(template, own, read, None)
    except (OSError, ValueError):
        return None


_flee_memo = {}


def run_off_map(template, own=None):
    """The waypoint name a template's RunOffMapBehavior runs to (RunOffMapWaypointName), '' for the module with none
    named, None without the module (a structure: it does not run -- docs/engine/runoffmap.md 1, bench 11-06 engine_runoffmap
    c). BaseInfantry and BaseVehicle both carry it with RequiresSpecificTrigger true: PLAYER_SET_ALL_UNITS_TO_FLEE starts
    it (RequiresSpecificTrigger false would start it at birth: nobody writes that, not modelled)."""
    key = (template, (own or {}).get(template))
    if key not in _flee_memo:
        def read(xml):
            for head, _ in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'RunOffMapBehavior'):
                if _attr(head, 'RequiresSpecificTrigger') == 'false':
                    return None
                return _attr(head, 'RunOffMapWaypointName') or ''
            return None
        try:
            _flee_memo[key] = _chain(template, own, read)
        except (OSError, ValueError):
            _flee_memo[key] = None
    return _flee_memo[key]


_fight = None


def _fight_data():
    global _fight
    if _fight is None:
        def build():
            require_data()
            weapons, armors = _weapons(_weapon_files()), _armors()
            got = {t: read_fight(open(path, encoding='utf-8', errors='replace').read(), armors)
                   for t, _, path in units()}
            return dict(units=got, weapons=weapons, armors=armors)
        _fight = _cached(COMBAT_CACHE, build, lambda d: not (d.get('units') and d.get('weapons') and d.get('armors')))
    return _fight


_own_weapons = {}


def weapon_table(own=None):
    """Weapon template id -> its fields (_weapons): the retail ones and the WeaponTemplates the mission's own units'
    XML declare (a unit of ours carries its weapons in its XML: CNV_ChronoLag_Shell, the trains' tesla guns)."""
    d = _fight_data()
    texts = [x for x in (own or {}).values() if '<WeaponTemplate' in x]
    if not texts:
        return d['weapons']
    key = hash(tuple(texts))
    if key not in _own_weapons:
        _own_weapons[key] = {**d['weapons'], **_weapons(texts, d['weapons'])}
    return _own_weapons[key]


def declared_weapons(template, own=None):
    """The weapon template of each WeaponSlot as fight() takes it (the PRIMARY one, else the slot's first: the data
    port's WeaponSetUpdate blocks, engine.modules.weaponset); [] when the XML names none. Sim.add asks it when fight()
    reads no weapon (a gap, not a unit without guns); simcoverage.declared_picks reads the same. Step W1: a slot in
    an XML comment or a block a template Removes is no longer named (the readers before read the text as written:
    the Guardian's commented second turret, the Century bombers' removed set)."""
    from engine.modules import weaponset
    try:
        return [p for d in weaponset.read(module_blocks(template, 'WeaponSetUpdate', own)) for p in d.picks()]
    except (OSError, ValueError, ET.ParseError):        # ParseError: the port's (StructureName's), as fight()
        return []


def weapon_sets(template, own=None):
    """The weapon choice a unit makes by its ObjectStatus (engine line C round 11, engine_weaponset a / b, bench 11-09,
    docs/engine/weaponset.md): per WeaponSlot the list of [need, forbid, weapon] of its <Weapon> lines in XML order
    (need = ObjectStatus bits all present, forbid = ForbiddenObjectStatus bits none present, weapon = the resolved
    template, PRIMARY_WEAPON flagged). A line's Upgrade="X" is one more need, the bit UPGRADE_BIT + X lowercased: the
    line is held only while the object (or its player) has X (pick_weapons' upgrades) -- the IFV's passenger guns
    (Uprade_IFV_*, granted by who rides in: Garrisons.secondary) are not an empty IFV's; before, its slots 3-7 (one
    upgrade line each) gave it a 750-dps pistol and the AI's expected efficiency 7.6 for it vs conscripts (B round
    132). None where no weapon line carries a status or upgrade condition (the unit's weapons are read_fight's,
    whatever its status). The data port's blocks (engine.modules.weaponset, step W1: slots in the SDK's kind order,
    Hardpoint before Turret -- the Apocalypse's two are never held at once)."""
    from engine.modules import weaponset
    try:
        datas, table = weaponset.read(module_blocks(template, 'WeaponSetUpdate', own)), weapon_table(own)
    except (OSError, ValueError, ET.ParseError):
        return None
    if not any(d.conditioned() for d in datas):
        return None
    return [[(set(x.need), set(x.forbidden), x.primary, _resolve(table[x.template], table) if x.template in table
              else None) for x in s.lines] for d in datas for s in d.slots]


def template_weapons(template, own=None):
    """The weapons the skirmish AI's template-against-template rate counts for a unit (the expected efficiency's
    rates; engine line B round 227, read): per WeaponSlot (Hardpoint, Turret, HierarchicalTurret, Contained -- in
    that order) only one, the first <Weapon> line by Ordering (the asset is sorted by it; XML order among equals)
    that names no Upgrade and no ObjectStatus, or one with ConquerMetricsAlwaysCount="true"; ForbiddenObjectStatus
    is not looked at. A line so picked that cannot hurt or reach still ends its slot. So the Hammer counts its
    leech beam and not its gun (the gun needs GENERIC_TOGGLE_STATE). None where the XML (walked up like
    weapon_sets: the data port's blocks, engine.modules.weaponset.WeaponSlot.counted) has no WeaponSetUpdate: the
    caller keeps the unit's own weapons."""
    from engine.modules import weaponset
    try:
        datas, table = weaponset.read(module_blocks(template, 'WeaponSetUpdate', own)), weapon_table(own)
    except (OSError, ValueError, ET.ParseError):
        return None
    if not datas:
        return None
    guns = []
    for x in (x for d in datas for x in d.counted()):
        w = _resolve(table[x.template], table) if x.template in table else None
        if w and (w['dps'] > 0 or w.get('ai_parts') or w.get('sdps', 0) > 0 or w.get('dot') or w.get('lift')
                  or w.get('grapple')) and w['range'] > 0:
            guns.append(w)
    return guns


def pick_weapons(slots, status, upgrades=()):
    """The weapons a unit holds under `status` with `upgrades` (the object's and its player's upgrade names): per
    slot the first line (a PRIMARY_WEAPON one before the rest) whose need bits are all set and forbid bits none set;
    one that cannot hurt or reach (the target painter) is no gun."""
    from engine.modules import weaponset
    if upgrades:
        status = set(status) | {weaponset.UPGRADE_BIT + u.lower() for u in upgrades}
    guns = []
    for s in slots:
        for need, forbid, prim, w in sorted(s, key=lambda e: not e[2]):
            if need <= status and not (forbid & status):
                if weaponset.armed(w):
                    guns.append(w)
                break
    return guns


def fight(template, own=None):
    """{hp, armor {damage type: percent}, weapons [{range, dps, type, anti}]} for a template (own: the mission's
    units' XML, read with the retail weapons and armours and their own weapons); hp None when the data has none. The
    weapons: the PRIMARY one of each WeaponSlot (else its first) of the data port's WeaponSetUpdate blocks that can
    hurt and reach (engine.modules.weaponset), resolved; none when the unit's file writes no WeaponSetUpdate
    (read_fight's `sets`). A retail unit's are read once (_reads), the shape the combat cache gave them (lists, not
    tuples). A block the port cannot parse (retail StructureName's: the port's known parse error) gives none, as the
    reader before read no weapon there."""
    from engine.modules import weaponset
    d = _fight_data()

    def guns(table, own):
        try:
            datas = weaponset.read(module_blocks(template, 'WeaponSetUpdate', own))
        except ET.ParseError:
            return []
        return [w for x in datas for n in x.picks() if n in table for w in (_resolve(table[n], table),)
                if weaponset.armed(w)]
    if own and template in own:
        f = read_fight(own[template], d['armors'])
        return dict(hp=f['hp'], armor=f['armor'], weapons=guns(weapon_table(own), own) if f['sets'] else [])
    name = template.lower()
    u = d['units'].get(name)
    if u is None and ('fight outside', name) not in _reads:     # outside the unit table, as stats(): a campaign unit
        try:                                                    # (EditorSorting CAMPAIGN_UNITS: JapanMechaKing) reads
            text = _xml(template)                               # its own file (A309)
        except (OSError, ValueError):
            text = ''
        _reads['fight outside', name] = read_fight(text, d['armors']) if text else None
    u = u or _reads.get(('fight outside', name))
    if u is None:
        return dict(hp=None, armor={}, weapons=[])
    key = ('fight weapons', name)
    if key not in _reads:
        _reads[key] = json.loads(json.dumps(guns(d['weapons'], None))) if u['sets'] else []
    return dict(hp=u['hp'], armor=u['armor'], weapons=_reads[key])


LIFE_FPS = 15                   # the game's logic frames a second (bench 2026-10-28, probe align)


def _dies_of(head, death):
    """A DieMuxData's DeathTypes takes this death type: 'ALL' less its '-X's, or the types it names; never one of
    its DeathTypesForbidden."""
    no = re.search(r'DeathTypesForbidden="([^"]*)"', head)
    if no and death in no.group(1).split():
        return False
    m = re.search(r'\bDeathTypes="([^"]*)"', head)
    words = (m.group(1) if m else 'ALL').split()
    if 'ALL' in words:
        return f'-{death}' not in words
    return death in words or f'+{death}' in words


def _chain(template, own, first):
    """Walk the template's XML up its inheritFrom chain (xml_chain) calling first(xml) on each; the first non-None
    answer, else None."""
    for _, xml in xml_chain(template, own):
        got = first(xml)
        if got is not None:
            return got
    return None


def xml_chain(template, own=None, steps=5):
    """(template, xml) of the template and of what it inherits from (inheritFrom), up to `steps` texts: the one walk
    up the chain the readers share. A campaign override (CampaignOverrides.xml: the same id inheriting itself, the
    file the index names) is followed by the file of the template's own name, not ended there: the Hammer and seven
    more armed units keep their WeaponSetUpdate only in that file (B round 229: weapon_sets and declared_weapons
    stopped at the override and read no weapons). _xml may raise OSError / ValueError."""
    xml = _xml(template, own)
    for _ in range(steps):
        yield template, xml
        up = parent(xml, template)
        if not up:
            return
        xml = retail_xml(template) if up.lower() == template.lower() else _xml(up, own)
        template = up


_prop_memo = {}


def prop_death(template, own=None):
    """What a script kill does to a PropBody (the caller asks for one only: Sim.add, by its Body module's kind --
    the reader before step B2b, prop_body, also said whether the Body was one): 'dies' when a DestroyDie / SlowDeath
    up the chain takes a NORMAL death, else 'stays'. Bench 11-10 engine_propbody a / b / c: a PropBody has no
    health (the percent reads 0, NAMED_DAMAGE 10 changes nothing), a Hammer told to attack never fires (UNATTACKABLE),
    and NAMED_KILL leaves a street segment (PropBody only) standing for good; a tree / lantern (SlowDeath only for
    TOPPLED) topples where it stands and is gone its ToppleUpdate delay + 1 frames later (61 / 121), never dying."""
    key = (template, (own or {}).get(template))
    if key not in _prop_memo:
        def destroyer(xml):
            text = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
            for tag in ('DestroyDie', 'SlowDeath'):
                for _, inner in _blocks(text, tag):
                    if _dies_of(next((h for h, _ in _blocks(inner, 'DieMuxData')), ''), 'NORMAL'):
                        return True
            return None
        _prop_memo[key] = 'dies' if _chain(template, own, destroyer) else 'stays'
    return _prop_memo[key]


_hp_memo = {}


def max_health(template, own=None):
    """MaxHealth from the nearest template up the inheritFrom chain that writes it (a define spelled out), None when
    none does: a civilian house writes none of its own (AM_Apartments_01 -> BaseCivilianStructureMedium's
    =$CIV_HEALTH_MEDIUM, 3000; bench 11-05 engine_garrison hp: NAMED_DAMAGE 2600 left 13 %)."""
    key = (template, (own or {}).get(template))
    if key not in _hp_memo:
        def read(xml):
            return number(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'MaxHealth')
        try:
            _hp_memo[key] = _chain(template, own, read)
        except (OSError, ValueError):
            _hp_memo[key] = None
    return _hp_memo[key]


_weapon_blocks = None


def weapon_blasts(weapon, own=None):
    """[(damage, damage type, radius, delay s, affects, allies' scalar, (required upgrades, forbidden upgrades, leech))]
    -- each DamageNugget and LeechPercentMaxHealthDamageNugget (leech: its PercentMaxHealthToTake) of the WeaponTemplate
    `weapon` (the mission's own first, else retail; XML comments not read) as a death weapon fires it (step B5c: a
    FireWeaponWhenDead's DeathWeapon, engine/modules/fireweaponwhendead.py; simbody.Life.fire / wreck_blasts): it goes
    off where the body died, `delay` after (the nugget's DelayTimeSeconds), hurting what of `affects`
    (RadiusDamageAffects: ALLIES ENEMIES NEUTRALS, relative to the dead one's owner) lies within the radius, centre to
    centre. INFERRED: no falloff inside the radius (the game's DamageNugget has none without DamageArc / a
    ScalarFalloff), SpecialObjectFilter not read. A weapon no file has: []. Not cached here (the caller keeps it)."""
    global _weapon_blocks
    if _weapon_blocks is None:
        _weapon_blocks = {}
        for text in _weapon_files():
            for head, body in _blocks(re.sub(r'<!--.*?-->', '', text, flags=re.S), 'WeaponTemplate'):
                _weapon_blocks.setdefault(_attr(head, 'id'), (head, body))
    mine = {}
    for text in (own or {}).values():
        for head, body in _blocks(text or '', 'WeaponTemplate'):
            mine[_attr(head, 'id')] = (head, body)
    whead, wbody = mine.get(weapon) or _weapon_blocks.get(weapon, ('', ''))
    affects = frozenset((_attr(whead, 'RadiusDamageAffects') or 'ENEMIES NEUTRALS').split())
    ups = lambda tag, nb: frozenset(u.lower() for u in re.findall(rf'<{tag}>\s*([^<>\s]+)', nb))
    return [(_num(_attr(nh, 'Damage'), 0.0), _attr(nh, 'DamageType') or '', _num(_attr(nh, 'Radius'), 0.0),
             _secs(_attr(nh, 'DelayTimeSeconds') or '0s'), affects, _ally_scalar(nb),
             (ups('RequiredUpgrade', nb), ups('ForbiddenUpgrade', nb), _pct(_attr(nh, 'PercentMaxHealthToTake') or '0')))
            for nh, nb in _blocks(wbody, '(?:LeechPercentMaxHealth)?DamageNugget')]


def _ally_scalar(nugget):
    """A DamageNugget's DamageScalarDetails for its allies (Filter Rule ALL Relationship ALLIES: the plane's crash,
    NormalAircraftDeathWeapon 50 %), 1.0 without one; other filters are not read (INFERRED: own units count as allies,
    as the death blasts' relation does)."""
    for m in re.finditer(r'<DamageScalarDetails\b([^>]*)>(.*?)</DamageScalarDetails>', nugget or '', re.S):
        scalar = re.search(r'Scalar\s*=\s*"([^"]*)"', m.group(1))
        rule, rel = re.search(r'Rule\s*=\s*"([^"]*)"', m.group(2)), re.search(r'Relationship\s*=\s*"([^"]*)"', m.group(2))
        if scalar and rule and rel and rule.group(1) == 'ALL' and rel.group(1).split() == ['ALLIES']:
            return _pct(scalar.group(1))
    return 1.0


def _pct(v):
    return float(v.strip().rstrip('%')) / 100.0 if v.strip().endswith('%') else float(v)


_ocl_text = None


def _ocl(name, own=None):
    """(head, body) of an ObjectCreationList: a mission unit's own first, else retail's ObjectCreationLists.xml."""
    global _ocl_text
    for text in (own or {}).values():
        for h, b in _blocks(text or '', 'ObjectCreationList'):
            if _attr(h, 'id') == name:
                return h, b
    if _ocl_text is None:
        p = os.path.join(SAGEXML, 'GlobalData', 'ObjectCreationLists.xml')
        _ocl_text = re.sub(r'<!--.*?-->', '', open(p, encoding='utf-8', errors='replace').read(), flags=re.S) \
            if os.path.exists(p) else ''
    return next(((h, b) for h, b in _blocks(_ocl_text, 'ObjectCreationList') if _attr(h, 'id') == name), None)


def fly_height(template, own=None):
    """The PreferredHeight of its NORMAL LocomotorSet's locomotor (retail Locomotor.xml), 0.0 without one: the
    Apollo's / MiG's 175 (bench 11-11 engine_crash_fall: both killed 174.94 over the ground)."""
    def read(xml):
        for m in re.finditer(r'<LocomotorSet\b(.*?)/?>', xml or '', re.S):
            cond = re.search(r'\bCondition="([^"]+)"', m.group(1))
            lo = re.search(r'\bLocomotor="([^"]+)"', m.group(1))
            if lo and (not cond or cond.group(1) == 'NORMAL'):
                return lo.group(1)
        return None
    loco = _chain(template, own, read)
    if not loco or not os.path.exists(LOCOMOTORS):
        return 0.0
    text = open(LOCOMOTORS, encoding='utf-8', errors='replace').read()
    m = re.search(r'<LocomotorTemplate\b[^>]*\bid="' + re.escape(loco) + r'"[^>]*>', text, re.S)
    h = m and re.search(r'\bPreferredHeight="([\d.]+)"', m.group(0))
    return float(h.group(1)) if h else 0.0


_wreck_memo = {}


def ocl_wrecks(name, own=None):
    """What an ObjectCreationList makes fall when its CreateObjectDie takes a death in the air (Physics P5,
    checks/engine_crash_fall.py; the module: engine/modules/createobjectdie.py): (choose_one, [wreck]), None without
    the list. A wreck: dict(template, scale = the nugget's VelocityScale of the plane's velocity (INHERIT_VELOCITY
    nuggets only), gravity = its own Physics GravityMultiplier (default 1), falls = KillWhenRestingOnGround; its death weapons:
    simbody.Life.wreck_blasts, step B5c). The Apollo's: CHOOSE_ONE of AlliedFighterAircraft_Collapse
    (debris, no weapon) and AlliedFighterAircraft_Dying (x 0.5, falls, 150 EXPLOSIVE radius 20, allies 50 %)."""
    key = ('ocl', name, tuple((own or {}).values()))
    if key in _wreck_memo:
        return _wreck_memo[key]
    got = _ocl(name, own) if name else None
    if not got:
        _wreck_memo[key] = None
        return None
    head, body = got
    wrecks = []
    for ch, cb in re.findall(r'<CreateObject\b(\s[^>]*)>((?:\s*<CreateObject>[^<]*</CreateObject>)+)', body):
        objs = re.findall(r'<CreateObject>\s*([^<\s]+)\s*</CreateObject>', cb)
        if not objs or 'INHERIT_VELOCITY' not in (_attr(ch, 'Disposition') or ''):
            continue
        scale = _num(expand(_attr(ch, 'VelocityScale') or '1'), 1.0)
        for w in objs:
            def physics(xml):
                p = next(_blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'Physics'), None)
                return p[0] if p else None
            ph = _chain(w, own, physics) or ''
            wrecks.append(dict(template=w, scale=scale, gravity=_num(_attr(ph, 'GravityMultiplier') or '1', 1.0),
                               falls=(_attr(ph, 'KillWhenRestingOnGround') or '').lower() == 'true',
                               live='REQUIRES_LIVE_PLAYER' in (_attr(ch, 'Options') or '').split()))
    _wreck_memo[key] = ('CHOOSE_ONE' in (_attr(head, 'Flags') or ''), wrecks)
    return _wreck_memo[key]


def ocl_objects(name, own=None):
    """[(template, health share, live)] an ObjectCreationList's <CreateObject> nuggets list, in order (each once a
    listing; Count, the disposition and the other nuggets not read): what a death of age or a structure's in a fight
    leaves (CreateObjectDie, Life.leave). The share is the middle of the nugget's MinHealth..MaxHealth (default 1; the
    game rolls it -- bench 11-22 aigarrbld: one Peacekeeper of ~0.55 off 0.3..0.75, INFERRED); live: its Options name
    REQUIRES_LIVE_PLAYER."""
    got, made, share, live = _ocl(name, own) if name else None, [], 1.0, False
    for head, inner in re.findall(r'<CreateObject\b([^>]*)>([^<]*)', got[1] if got else ''):
        if inner.strip():
            made.append((inner.strip(), share, live))
        else:                                               # the outer element: its health share and options
            share = (_num(_attr(head, 'MinHealth'), 1.0) + _num(_attr(head, 'MaxHealth'), 1.0)) / 2
            live = 'REQUIRES_LIVE_PLAYER' in (_attr(head, 'Options') or '').split()
    return made


def crash_frames(position, velocity, ground, gravity=1.0):
    """(frames, landing) of a falling wreck made at `position` with `velocity` (a frame) over level `ground`: frames
    from the kill to its death weapon's hit = its curve's points (meta_impact_fall) - 1. Bench 11-12 engine_crash_hit:
    the flying plane's wreck (30 points) hits its tank 30 counted frames after the kill, the hovering ones' (38
    points) 38 -- the script's count runs one frame past the hit (the sim's count of frames + 1)."""
    points, end = meta_impact_fall(position, velocity, ground, gravity)
    return len(points) - 1, end


_retail_files = None


def retail_xml(template):
    """The SageXML text of a retail template (the file of its own name), '' when there is none."""
    global _retail_files
    if _retail_files is None:
        _retail_files = {}
        for root, _, files in os.walk(SAGEXML):
            for f in files:
                if f.endswith('.xml'):
                    _retail_files.setdefault(f[:-4].lower(), os.path.join(root, f))
    p = _retail_files.get(template.lower())
    return _text(p) if p else ''


def engineer_contain(template, own=None):
    """Nearest EngineerContain, including retail xi:includes, or None.

    Only the three-engineer NONE filter (optionally Relationship=ALLIES) is
    implemented. Other filters/replacements are surfaced as unsupported.
    """
    def read(xml):
        text = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        def include(m):
            path = os.path.join(SAGEXML, *m.group(1).split('/'))
            return open(path, encoding='utf-8').read() if os.path.isfile(path) else m.group(0)
        text = re.sub(r'<xi:include\b[^>]*href="DATA:([^"]+)"[^>]*/>', include, text)
        block = next(_blocks(text, 'EngineerContain'), None)
        if block is None:
            return None
        head, inner = block
        fh, fi = next(_blocks(inner, 'CanEnterFilter'), ('', ''))
        allowed = frozenset(x.strip().lower() for x in re.findall(r'<IncludeThing>([^<]+)</IncludeThing>', fi))
        relations = frozenset((_attr(fh, 'Relationship') or '').split())
        supported = (_attr(fh, 'Rule') == 'NONE' and bool(allowed)
                     and set(re.findall(r'(\w+)\s*=', fh)) <= {'Rule', 'Relationship'}
                     and not re.sub(r'<IncludeThing>[^<]+</IncludeThing>', '', fi).strip()
                     and relations <= {'ALLIES'}
                     and not _attr(head, 'ReplaceWith'))
        return dict(enabled=_attr(head, 'ImmediatelyEnabled', 'false').lower() == 'true',   # bridge: a gatehouse's
                    bridge=_attr(head, 'id') == 'ModuleTag_EngineerContainBridge',      # (engine_bridgefix a)
                    allowed=allowed, relations=relations, supported=supported,
                    status=frozenset(_attr(head, 'ObjectStatusToSet', 'NO_REFUND').split()))
    return _chain(template, own, read)


def assemble(template, power, own=None):
    """(stand, structure) of a mission unit's AssembleStructureSpecialAbilityUpdate for that special power (the ice
    engineer's freeze), else None: he walks to within `stand` (StartAbilityRange) of the target and builds
    `structure` there (bench 2026-11-07 engine_life, R5)."""
    xml = (own or {}).get(template) or ''
    for head, inner in _blocks(xml, 'AssembleStructureSpecialAbilityUpdate'):
        if _attr(head, 'SpecialPowerTemplate') == power:
            m = re.search(r'<StructureTemplate>\s*([^<\s]+)', inner)
            return _num(_attr(head, 'StartAbilityRange'), 0.0), m.group(1) if m else None
    return None


_acquire = {}


def acquire(template, own=None):
    """The words of a template's AIUpdate AutoAcquireEnemiesWhenIdle (YES = takes enemies by itself when idle,
    ATTACK_BUILDINGS = buildings too); [] when it writes none (Generals' default 0: no idle acquiring). Retail
    2026-11-08: of the 56 armed templates 50 YES, 4 NO (tech-building guns), 2 none (Riptide, Bullfrog); one squad
    'YES ATTACK_BUILDINGS'."""
    if own and template in own:
        m = re.search(r'\bAutoAcquireEnemiesWhenIdle="([^"]*)"', own[template])
        return m.group(1).split() if m else []
    key = template.lower()
    if not _acquire:
        _acquire[None] = {t: p for t, _, p in units()}
    if key not in _acquire:
        path = _acquire[None].get(key)
        text = open(path, encoding='utf-8', errors='replace').read() if path else ''
        m = re.search(r'\bAutoAcquireEnemiesWhenIdle="([^"]*)"', text)
        _acquire[key] = m.group(1).split() if m else (['YES'] if not path else [])
    return _acquire[key]


_retail_powers = None


def _retail_power_heads():
    """id -> attributes text of every SpecialPowerTemplate in the SDK's GlobalData/SpecialPowerTemplates.xml."""
    global _retail_powers
    if _retail_powers is None:
        _retail_powers = {}
        p = os.path.join(SAGEXML, 'GlobalData', 'SpecialPowerTemplates.xml')
        text = open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else ''
        for head, _ in _blocks(text, 'SpecialPowerTemplate'):
            m = re.search(r'\bid="([^"]*)"', head)
            if m:
                _retail_powers.setdefault(m.group(1), head)
    return _retail_powers


def ocl_power(template, power, own=None):
    """The matching host OCLSpecialPower attributes, or None (nearest module group).

    Only Iron Curtain's retail payload and a locally declared empty OCL are
    replayed; callers must keep other OCL configurations as explicit gaps.
    """
    def read(xml):
        xml = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        heads = [head for head, _ in _blocks(xml, 'OCLSpecialPower')]
        return [{key: _attr(head, key) for key in
                 ('SpecialPowerTemplate', 'OCL', 'CreateLocation', 'CanAffectObjectFilter')}
                for head in heads] or None
    modules = _inherited(template, own, read, None) or []
    return next((module for module in modules if (module['SpecialPowerTemplate'] or '').lower() == power.lower()),
                None)


def empty_ocl(ocl, own=None):
    """E63: a resolved local OCL with no nuggets and default flags does nothing.

    A missing reference is not an empty list. Nonempty lists remain unmodeled;
    this does not infer behavior from their names or just their object count.
    Explicit NONE flags and equivalent local declarations are INFERRED from
    schema defaults; the bench uses one self-closing list with omitted flags.
    """
    for xml in (own or {}).values():
        xml = re.sub(r'<!--.*?-->', '', xml, flags=re.S)
        for head, inner in _blocks(xml, 'ObjectCreationList'):
            if _attr(head, 'id') == ocl:
                return (not inner.strip() and _attr(head, 'Flags', 'NONE') == 'NONE' and
                        set(re.findall(r'(\w+)\s*=', head)) <= {'id', 'Flags'})
    return False


def iron_curtain_ocl(ocl, own=None, *, zero_count=False):
    """E64: resolve the reference, accepting only the measured retail payload.

    engine_oclcopy replays the same CreateObject/IronCurtainEffect under a
    new local id. This dispatches the existing effect; it does not implement
    general OCL creation. Attribute order/whitespace equivalence is INFERRED.
    E65 zero_count resolves only that same payload with outer Count="0";
    callers dispatch the cast but no protection. Other counts/payloads stay gaps.
    A local declaration takes precedence over the familiar retail name.
    """
    def declarations(xml):
        xml = re.sub(r'<!--.*?-->', '', xml, flags=re.S)
        return list(_blocks(xml, 'ObjectCreationList'))

    def signature(head, inner, expected_zero=False):
        try:
            root = ET.fromstring(f'<ObjectCreationList {head}>{inner}</ObjectCreationList>')
        except ET.ParseError:
            return None
        root.attrib.pop('id', None)
        if expected_zero:
            children = list(root)
            if len(children) != 1 or children[0].tag != 'CreateObject':
                return None
            children[0].set('Count', '0')

        def tree(node):
            return (node.tag, tuple(sorted(node.attrib.items())),
                    (node.text or '').strip(), (node.tail or '').strip(),
                    tuple(tree(child) for child in node))
        return tree(root)

    with open(os.path.join(SAGEXML, 'GlobalData', 'ObjectCreationLists.xml'),
              encoding='utf-8-sig') as f:
        retail = declarations(f.read())
    expected = next((signature(head, inner, zero_count) for head, inner in retail
                     if _attr(head, 'id') == 'OCL_IronCurtain'), None)
    for xml in (own or {}).values():
        for head, inner in declarations(xml):
            if _attr(head, 'id') == ocl:
                return expected is not None and signature(head, inner) == expected
    return not zero_count and ocl == 'OCL_IronCurtain' and expected is not None


def power_rules(template, power, own=None):
    """The SpecialPowerTemplate for `power` of unit `template`: {'reload': frames (ReloadTime x 15, rounded twice --
    RA3 1.13, work/re/l2_specialpower.md; docs/engine/specialpower.md 1 -- at least 1), 'forbidden': ForbiddenObjectRange, 'flags': set of
    Flags, 'reach': MaxCastRange or 0}, else None. A mission unit's own XML first; else a retail power (the SDK's
    GlobalData/SpecialPowerTemplates.xml -- the superweapons: proton collider 360 s ...) when the template's XML (own or
    retail) names it, so a unit without the power still gets None."""
    xml = (own or {}).get(template) or ''
    heads = [h for h, _ in _blocks(xml, 'SpecialPowerTemplate')]
    if not any(re.search(r'\bid="([^"]*)"', h).group(1) == power for h in heads):
        # Campaign self-overrides keep the power on their retail parent (E206).
        body = '\n'.join(body for _, body in xml_chain(template, own))
        if f'"{power}"' in body and power in _retail_power_heads():
            heads = [_retail_power_heads()[power]]
    for head in heads:
        if re.search(r'\bid="([^"]*)"', head).group(1) == power:
            secs = _secs(_attr(head, 'ReloadTime'))
            return {'reload': max(1, int(round(secs * 15))) if secs else 0,
                    'forbidden': _num(_attr(head, 'ForbiddenObjectRange'), 0.0),
                    'flags': set((_attr(head, 'Flags') or '').split()),
                    'reach': _num(_attr(head, 'MaxCastRange'), 0.0)}
    return None


def assigned_repair_rate(template, power, own=None):
    """E67 explicit dispatch only; retail drone configuration, no allocation model.

    Custom drone XML/dispatch flags remain unmeasured. The rate comes from the
    retail passive healing module, rather than the observed final percentage.
    `power`: the SpecialPowerTemplate a plain AssignSlavesTargetObjectSpecialPower module of the template serves
    (simassign asks its modules: step M13).
    """
    if power != 'SpecialPower_TargetedRepairVehicle' or not module_blocks(template, 'SpawnBehavior', own):
        return None
    if any(k in (own or {}) for k in ('AlliedWarFactoryRepairDrone', 'BaseRepairDrone')):
        return None
    def healing(xml):
        for head, _ in _blocks(xml or '', 'PassiveAreaEffectBehavior'):
            if _attr(head, 'AffectAttached') == 'true':
                return _num(_attr(head, 'HealingPointsPerSecond'))
        return None
    return _chain('AlliedWarFactoryRepairDrone', own, healing)


def passive_area(template, own=None):
    """E70 retail engineer aura only; other PassiveAreaEffect configurations are gaps.

    Return (radius, fraction/second, beneficiary cap) for the measured shape.
    E145: explicit default zero and a one-beneficiary cap are measured; larger
    caps and beneficiary selection order remain gaps.
    Nearest group wins, including unsupported overrides. Attachment/drone healing
    is deliberately outside this independent area-healing slice.
    """
    import xml.etree.ElementTree as ET

    def read(xml):
        blocks = list(_blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S),
                              'PassiveAreaEffectBehavior'))
        if not blocks:
            return None
        if len(blocks) != 1:
            return False
        head, inner = blocks[0]
        node = ET.fromstring('<PassiveAreaEffectBehavior ' + head + '>' + inner +
                             '</PassiveAreaEffectBehavior>')
        attrs = dict(node.attrib)
        attrs.pop('id', None)
        radius = attrs.pop('EffectRadius', None)
        cap = attrs.pop('MaxBeneficiaries', '0')
        if cap not in ('0', '1'):
            return False
        if attrs != dict(HealingPercentPerSecond='10%', AffectWoundedOnly='true',
                         AffectUnderAttack='true', DisabledTypesToProcess='HELD'):
            return False
        children = list(node)
        if len(children) != 2:
            return False
        filt, state = children
        if (filt.tag != 'AllowFilter' or dict(filt.attrib) != dict(
                Rule='ANY', Relationship='ALLIES', Include='INFANTRY') or
                [(c.tag, (c.text or '').strip(), dict(c.attrib), len(c)) for c in filt] != [
                    ('ExcludeThing', 'SovietScoutVehicle', {}, 0)] or
                state.tag != 'ObjectStatusValidation' or len(state) or
                dict(state.attrib) != dict(RequiredStatus='GENERIC_TOGGLE_STATE')):
            return False
        value = number('EffectRadius="' + (radius or '') + '"', 'EffectRadius')
        return (value, .1, int(cap)) if value == 100 else False

    return _chain(template, own, read)


def nugget_disguise_power(template, power, own=None):
    """engine_spndisguise / engine_spntrans: retail direct-hit DISGUISED bit only.

    Identity, rendering, enemy acquisition, retargeting and cancellation remain
    gaps. Transport unpack timing is also a gap: immediate bit application is
    INFERRED; engine_spntrans only replays the settled s12-14 state.
    Reject unmeasured handler/power shapes rather than treating them as buffs.
    """
    def handler(xml):
        for h, inner in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'SpecialDisguiseUpdate'):
            if _attr(h, 'SpecialPowerTemplate') == power:
                node = ET.fromstring('<SpecialDisguiseUpdate ' + h + '/>')
                attrs = dict(node.attrib)
                attrs.pop('id', None)
                expected = dict(SpecialPowerTemplate=power, TriggerInstantlyOnCreate='false',
                                OpacityTarget='0.5', DisguiseFX='FX_None')
                if power == 'SpecialPower_JapanLightTransportVehicleDisguise':
                    expected.update(OpacityTarget='0.0', DisguiseFX='FX_JAP_SuddenDisguise',
                                    UnpackTime='1s', UnpackSound='JAP_SuddenTransport_DisguiseOnMS',
                                    FaceTarget='false')
                return not inner.strip() and attrs == expected
        return None

    active = _chain(template, own, handler)
    if active is None:
        return dict(noop=True, reach=0.)  # measured module-deletion control
    if not active:
        return False
    # Resolve the power's filter from data. Local overrides are not the retail
    # configuration measured by this check, so keep them explicit gaps.
    if any(_attr(h, 'id') == power for xml in (own or {}).values()
           for h, _ in _blocks(xml, 'SpecialPowerTemplate')):
        return False
    text = open(os.path.join(SAGEXML, 'GlobalData', 'SpecialPowerTemplates.xml'), encoding='utf-8').read()
    for h, inner in _blocks(text, 'SpecialPowerTemplate'):
        if _attr(h, 'id') != power:
            continue
        node = ET.fromstring('<SpecialPowerTemplate ' + h + '>' + inner + '</SpecialPowerTemplate>')
        if (set(node.attrib) - {'id', 'TargetType', 'InitiateSound', 'Flags', 'WaypointModeTerminal',
                                       'NameOfVoiceNameToUseAsInitiateIntendToDoVoice'}
                or node.get('TargetType') != 'OBJECT'
                or set(node.get('Flags', '').split()) != {
                    'NEEDS_OBJECT_FILTER', 'DO_NOT_REACQUIRE_TARGET', 'CAN_NOT_BE_SCRAMBLED'}
                or node.get('WaypointModeTerminal') != 'false' or len(node) != 1):
            return False
        f = node[0]
        expected_filter = dict(Rule='ANY', Relationship='ALLIES ENEMIES NEUTRAL', Include='INFANTRY')
        if power == 'SpecialPower_JapanLightTransportVehicleDisguise':
            expected_filter = dict(Rule='ANY', Include='VEHICLE')
        if (f.tag != 'ObjectFilter' or dict(f.attrib) != expected_filter
                or any(c.tag != 'ExcludeThing' or c.attrib or len(c) for c in f)):
            return False
        return dict(disguise=True, reach=0., include=f.get('Include').split(),
                    exclude_templates=[(c.text or '').strip().lower() for c in f])
    return False


def nugget_self_power(template, power, own=None):
    """engine_spn/spnret: direct zero-reload self modifier or passive retail module.

    None: no matching module (native no-op). False: present but its handler
    is outside this probe. Only the measured retail disguise bit is consumed;
    other OCL/disguise/beam configurations must not become buffs.
    """
    def companion(xml):
        xml = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        return True if any(other != 'SpecialPower' and _attr(attrs, 'SpecialPowerTemplate') == power
                           for _, behaviors in _blocks(xml, 'Behaviors')
                           for other, attrs in re.findall(r'<(\w+)\b([^<>]*)>', behaviors)) else None

    def read(xml):
        xml = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        for tag in ('SpecialPower', 'ActivateModuleSpecialPower', 'OCLSpecialPower'):
            for h, inner in _blocks(xml, tag):
                if _attr(h, 'SpecialPowerTemplate') != power:
                    continue
                if power in ('SpecialPower_InfantryDisguise', 'SpecialPower_JapanLightTransportVehicleDisguise'):
                    if (tag != 'SpecialPower' or inner.strip()
                            or _attr(h, 'UpdateModuleStartsAttack') != 'true'
                            or set(re.findall(r'(\w+)\s*=', h)) - {
                                'id', 'SpecialPowerTemplate', 'UpdateModuleStartsAttack'}):
                        return False
                    return nugget_disguise_power(template, power, own)
                rules = power_rules(template, power, own)
                # engine_spnret: the retail painter's active module has no effect
                # consumer; its BeamSpecialAbilityUpdate is commented out. Never
                # infer a no-op when an active companion handler names this power.
                if (tag == 'SpecialPower' and not inner.strip() and rules and not rules['reload']
                        and not rules['flags'] and _attr(h, 'UpdateModuleStartsAttack') == 'false'
                        and not (set(re.findall(r'(\w+)\s*=', h)) -
                                 {'id', 'SpecialPowerTemplate', 'UpdateModuleStartsAttack'})
                        and not _chain(template, own, companion)):
                    return dict(noop=True, reach=rules['reach'])
                if (tag != 'SpecialPower' or inner.strip() or not rules or rules['reload'] or rules['flags']
                        or set(re.findall(r'(\w+)\s*=', h)) - {'id', 'SpecialPowerTemplate', 'AttributeModifier', 'AttributeModifierAffectsSelf'}
                        or _attr(h, 'AttributeModifierAffectsSelf', 'false') != 'true'
                        or not _attr(h, 'AttributeModifier')):
                    return False
                return dict(modifier=_attr(h, 'AttributeModifier'), reach=rules['reach'])
        return None
    return _chain(template, own, read)


def kind_of(kinds):
    for k in ('STRUCTURE', 'AIRCRAFT', 'SHIP', 'INFANTRY', 'VEHICLE'):
        if k in kinds:
            return k
    return ''


def speed_scale(xml, upgrades):
    """The factor the SPEED modifiers of the upgrades a unit holds multiply its speed by, read from its own XML
    (AttributeModifierUpgrade ... TriggeredBy -> AttributeModifier -> Modifier Type="SPEED" Value="N%"): units/pace.py's."""
    if not xml or not upgrades:
        return 1.0
    return effect([modifier(xml, m) for _, m in upgrade_mods(xml, upgrades)])['SPEED']


def shielded(xml, upgrades):
    """Whether an upgrade the unit holds gives it retail Iron Curtain's protection: its AttributeModifier has
    Modifier Type="INVULNERABLE" and sets the UNDER_IRON_CURTAIN status bit. Bench (docs/engine/upgrades.md 4,
    engine line 44bb8f5): INVULNERABLE 100% alone does not stop damage, with ObjectStatusToSet="NO_BRIBE
    UNDER_IRON_CURTAIN" it does; taking the upgrade away makes the unit hurt-able again (units/tower_ball.py)."""
    if not xml or not upgrades:
        return False
    return effect([modifier(xml, m) for _, m in upgrade_mods(xml, upgrades)])['shielded']


# ---- attribute modifiers, one interface for their two sources (docs/engine/upgrades.md 1, 2, 4, 5)
# An AttributeModifier (a mission's own XML, else retail GlobalData/AttributeModifier.xml) hangs on a unit either through
# an upgrade it holds (AttributeModifierUpgrade; StatusBitsUpgrade sets / clears bits without a modifier) or through an
# aura object near it (AttributeModifierAuraUpdate: every RefreshDelay the modifier on whatever its ObjectFilter takes
# within Range; the modifier's own Duration lets it fall off once no longer hung). `modifier` reads one, `effect` sums
# what a unit has on it into the factors and bits the simulator acts on.
RETAIL_MODIFIERS = os.path.join(SAGEXML, 'GlobalData', 'AttributeModifier.xml')
_retail_mods = None


def _retail_modifier_blocks():
    global _retail_mods
    if _retail_mods is None:
        text = open(RETAIL_MODIFIERS, encoding='utf-8', errors='replace').read() \
            if os.path.exists(RETAIL_MODIFIERS) else ''
        _retail_mods = {_attr(h, 'id'): (h, i) for h, i in _blocks(text, 'AttributeModifier') if _attr(h, 'id')}
    return _retail_mods


def modifier(xml, mid):
    """AttributeModifier `mid` (in `xml` first, else retail): {'id', 'types': {Type: [fractions]} (SPEED 0% -> [0.0],
    RANGE 200% -> [2.0]), 'status': set of ObjectStatusToSet bits, 'frames': Duration x 15 or None (none written:
    held while its source holds -- bench upgrades.md 4: a Duration hung through an upgrade still runs out)}; None
    where neither has it."""
    found = None
    for h, i in _blocks(xml or '', 'AttributeModifier'):
        if _attr(h, 'id') == mid:
            found = (h, i)
            break
    if found is None:
        found = _retail_modifier_blocks().get(mid)
    if found is None:
        return None
    head, inner = found
    types = {}
    for ty, v in re.findall(r'<Modifier\s+Type="(\w+)"\s+Value="(-?[\d.]+)%?"', inner or ''):
        types.setdefault(ty, []).append(float(v) / 100.0)
    dur = _attr(head, 'Duration')
    return {'id': mid, 'types': types, 'status': set((_attr(head, 'ObjectStatusToSet') or '').split()),
            'conditions': (_attr(head, 'ModelConditionsSet') or '').split(),
            'frames': int(round(_secs(dur) * LIFE_FPS)) if dur else None}


def _triggers(inner):
    return {t for x in re.findall(r'<TriggeredBy>([^<]*)</TriggeredBy>', inner or '') for t in x.split()}


def upgrade_mods(xml, upgrades):
    """[(upgrade, modifier id)] the upgrades held hang on the unit through its AttributeModifierUpgrade modules."""
    out = []
    for head, inner in _blocks(xml or '', 'AttributeModifierUpgrade'):
        mid = _attr(head, 'AttributeModifier')
        for up in sorted(_triggers(inner) & set(upgrades)):
            if mid:
                out.append((up, mid))
                break
    return out


def locomotor_of(template, own, condition):
    """(Speed, its Locomotor's Surfaces) of the template's LocomotorSet for that Condition (NORMAL, SUPERSONIC ...), up
    its chain; (None, []) when it has none (a toggle's state switches it: the Tengu's jet 200 against 100 on the
    ground; the Sea-Wing's SUPERSONIC on AIR, engine_acts_wing)."""
    from engine.modules import locomotor
    try:
        found = _chain(template, own, lambda xml: locomotor.speed_of(locomotor.sets(xml), condition))
    except (OSError, ValueError):
        found = None
    loco = _surfaces().get(found.locomotor) if found else None
    return (found.speed if found else None), (loco.surfaces if loco else [])


_turning_memo = {}


def turning(template, own=None):
    """The engine.modules.locomotor.Locomotor the template's NORMAL LocomotorSet names, up its chain: how fast it
    turns (360 / TurnTimeSeconds) and its TurnThresholdHS. Bench airev1t (B round 195, A round 227,
    tests/test_turn_rate.py): Hammers (1.25 s), Guardians (1.0 s) and Apocalypses (3 s) turn 19 / 24 / 8 deg a frame
    in place from the order frame on, drive on the frame that starts within ~9 deg of their way, and turn to the
    form-up facing the frame after they arrive; a 51 deg turn (under the threshold) in place too. Infantry
    (TestReactiveLocomotorHUMAN, 0.5 s, no threshold) not benched. None when the template has no locomotor (a
    building)."""
    from engine.modules import locomotor
    key = (template, (own or {}).get(template))
    if key not in _turning_memo:
        try:
            normal = _chain(template, own, lambda xml: next((s for s in locomotor.sets(xml) if s.condition ==
                                                             'NORMAL' and s.locomotor), None))   # by name, not speed
        except (OSError, ValueError):
            normal = None
        _turning_memo[key] = _surfaces().get(normal.locomotor) if normal else None
    return _turning_memo[key]


def status_bits(xml, upgrades):
    """(set, clear): the bits the held upgrades' StatusBitsUpgrade modules set and clear (Generals StatusBitsUpgrade:
    on upgrade sets StatusToSet, clears StatusToClear; INFERRED for RA3, not on the bench)."""
    on, off = set(), set()
    for head, inner in _blocks(xml or '', 'StatusBitsUpgrade'):
        if _triggers(inner) & set(upgrades):
            on |= set((_attr(head, 'StatusToSet') or '').split())
            off |= set((_attr(head, 'StatusToClear') or '').split())
    return on, off


def stack(values):
    """One Type's fractions on one unit: those >= 1 add their excess, those < 1 multiply (docs/engine/weapons.md row
    'AttributeModifier 怎么叠': 150% + 200% = 250%; read in the program, not on the bench)."""
    f = 1.0 + sum(v - 1.0 for v in values if v >= 1.0)
    for v in values:
        if v < 1.0:
            f *= v
    return f


# What a status bit does in the simulator. IN_STASIS: the stasis zone's and the chronolag's modifiers set it together
# with UNATTACKABLE NO_ATTACK NON_AUTOACQUIRABLE and SPEED 0% (bench upgrades.md 5 saw the sum: stops, holds its fire,
# untouched); alone it is taken to stop the unit too (INFERRED).
ACTING_BITS = {'IMMOBILE', 'UNATTACKABLE', 'NO_ATTACK', 'NON_AUTOACQUIRABLE', 'IN_STASIS', 'UNDER_IRON_CURTAIN'}
# Types the simulator applies: SPEED (bench upgrades.md 1, units/pace.py), RANGE (the weapons' range only, upgrades.md
# 2), VISION (sight and so idle acquiring, 2), INVULNERABLE with UNDER_IRON_CURTAIN (4); ARMOR (damage taken x),
# DAMAGE_MULT, RATE_OF_FIRE (damage dealt x) read in the program (weapons.md 107), not on the bench: INFERRED.
ACTING_TYPES = {'SPEED', 'RANGE', 'VISION', 'INVULNERABLE', 'ARMOR', 'DAMAGE_MULT', 'RATE_OF_FIRE'}


def effect(mods, bits=(), cleared=()):
    """What the modifiers on a unit add up to: {Type: factor (stack) for ACTING_TYPES, 'status': bits (the modifiers'
    ObjectStatusToSet + `bits` - `cleared`), 'shielded': INVULNERABLE and UNDER_IRON_CURTAIN both (bench
    upgrades.md 4: INVULNERABLE alone does not stop damage)}."""
    types, status = {}, set(bits)
    for m in mods:
        if not m:
            continue
        for ty, vs in m['types'].items():
            types.setdefault(ty, []).extend(vs)
        status |= m['status']
    status -= set(cleared)
    out = {ty: stack(types.get(ty, [])) for ty in ACTING_TYPES}
    out['status'] = status
    out['shielded'] = 'INVULNERABLE' in types and 'UNDER_IRON_CURTAIN' in status
    return out


_radii = {}


def _retail_radius(template):
    """radius() of a retail template the unit table leaves out (props, ore nodes), None without XML or Shape."""
    if template not in _radii:
        try:
            _radii[template] = radius(retail_xml(template) or '')
        except (OSError, ValueError):
            _radii[template] = None
    return _radii[template]


def stats(template, own=None):
    """{speed, surface, vision, shroud, kinds, radius, guessed} for a template; own: {id: xml text} of the mission's units."""
    if own and template in own:
        e = read_xml(template, own)
    else:
        e = dict(table().get(template.lower()) or {})
        if not e:                       # outside the unit table (not sorted UNIT / STRUCTURE: S02_ExplodingMig, a
            try:                        # prop vehicle): its own chain, so its KindOf (NOT_AUTOACQUIRABLE) is read
                e = read_xml(template) if _xml(template) else {}
            except (OSError, ValueError):
                e = {}
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
    if e.get('clear_height') is None:
        e['clear_height'] = CLEAR_HEIGHT
    if e.get('radius') is None and not (own and template in own):
        e['radius'] = _retail_radius(template)      # outside the table (an ore node): its retail Geometry
    if e.get('radius') is None:
        e['radius'] = 0.0               # no Shape: a point (centre to centre)
    e['kinds'] = sorted(kinds)
    e['guessed'] = guessed if e.get('kinds') or own else ['all']
    return e


# ---- production: what a factory builds, for how much, how long (sim.Sim.offers / order_build; docs/engine/production.md)
COMMAND_SETS = os.path.join(SAGEXML, 'GlobalData', 'LogicCommandSet.xml')
COMMANDS = os.path.join(SAGEXML, 'GlobalData', 'LogicCommand.xml')
_retail_commands = None


def _read_commands(text, sets, cmds):
    for head, inner in _blocks(text, 'LogicCommandSet'):
        if _attr(head, 'id'):           # a set inheriting another (JapanBarracksCommandSet): the base's buttons first
            own = re.findall(r'<Cmd>\s*([^<\s]+)', re.sub(r'<!--.*?-->', '', inner, flags=re.S))
            sets[_attr(head, 'id')] = sets.get(_attr(head, 'inheritFrom', ''), []) + own
    for head, inner in _blocks(text, 'LogicCommand'):     # UNIT_BUILD: its <Object>; OBJECT_ / PLAYER_UPGRADE: its <Upgrade>
        m = re.search(r'<Object>\s*([^<\s]+)', inner) or re.search(r'<Upgrade>\s*([^<\s]+)', inner)
        if _attr(head, 'id'):
            cmds[_attr(head, 'id')] = (_attr(head, 'Type', ''), m.group(1) if m else None)


def _commands(own=None):
    """({command set: [command]}, {command: (Type, Object)}): the SDK's GlobalData, then the mission's own XML on top."""
    global _retail_commands
    if _retail_commands is None:
        sets, cmds = {}, {}
        for p in (COMMAND_SETS, COMMANDS):
            if os.path.exists(p):
                _read_commands(open(p, encoding='utf-8', errors='replace').read(), sets, cmds)
        _retail_commands = sets, cmds
    if not own:
        return _retail_commands
    sets, cmds = dict(_retail_commands[0]), dict(_retail_commands[1])
    for xml in own.values():
        _read_commands(xml or '', sets, cmds)
    return sets, cmds


_index = None
_reads = {}         # T9 (11-18), per process -- the SDK does not change while one runs:
                    #   ('text', path) a SageXML file's text; ('sdk', name) _xml's answer from the SDK;
                    #   ('objects', text) {id.lower(): first GameObject} of a mission file, keyed by its text,
                    #   not the dict; ('only', text, name) that file without its other GameObjects;
                    #   ('production_*', name[, own files]) inherited production data and command-set buttons;
                    #   ('module_*', ...) parsed sources, schema fields and effective module blocks


def _text(path):
    """The SageXML file's text, read once a process (the per-frame build queries read the same files: profile_1118)."""
    if ('text', path) not in _reads:
        _reads['text', path] = open(path, encoding='utf-8', errors='replace').read()
    return _reads['text', path]


def _sdk_source(name):
    """Indexed SageXML source path, or None for an unindexed template."""
    global _index
    if _index is None:
        _index = {k.lower(): v for k, v in json.load(open(INDEX, encoding='utf-8')).items()} \
            if os.path.exists(INDEX) else {}
    f = (_index.get(name) or {}).get('file', '')
    path = os.path.join(SAGEXML, *f[5:].split('/')) if f.startswith('DATA:') else ''
    return path if path and os.path.isfile(path) else None


def _xml(template, own=None):
    """The template's own XML: a mission's, else its GameObject in the file the SageXML index names (a file may hold
    several, AlliedAntiInfantryVehicle.xml the Riptide's two), else the file of its own name. A mission file may also
    hold another GameObject (engine_dynamics: a copy of BaseVehicle the unit inherits): the unit's text leaves the
    others out (its includes, weapons and the rest kept), and a template defined only inside a mission file is that
    GameObject (the first of its id, files in order). Kept per process (T9): the SDK's answer by name, a mission's by
    its file's text, not by the dict (two missions overriding one template each get their own)."""
    name = template.lower()
    if (own or {}).get(template):
        text = own[template]
        if ('only', text, name) not in _reads:
            def keep(m):
                head = re.match(r'<GameObject\b[^>]*>', m.group(0)).group(0)
                return m.group(0) if re.search(rf'\bid="{re.escape(template)}"', head, re.I) else ''
            _reads['only', text, name] = re.sub(r'<GameObject\b.*?</GameObject>', keep, text, flags=re.S) \
                if text.count('<GameObject') > 1 else text
        return _reads['only', text, name]
    for text in (own or {}).values():
        text = text or ''
        if ('objects', text) not in _reads:        # {id.lower(): the file's first GameObject of that id}
            found = {}
            for m in re.finditer(r'<GameObject\b.*?</GameObject>', text, re.S):
                for i in re.findall(r'\bid="([^"]*)"', re.match(r'<GameObject\b[^>]*>', m.group(0)).group(0), re.I):
                    found.setdefault(i.lower(), m.group(0))
            # Readers can build the same index concurrently. Publish only the complete index.
            _reads['objects', text] = found
        if name in _reads['objects', text]:
            return _reads['objects', text][name]
    if ('sdk', name) not in _reads:               # the SageXML index's file, else the file of its own name
        path = _sdk_source(name)
        objects = re.finditer(r'<GameObject\b.*?</GameObject>', _text(path), re.S) if path else ()
        got = next((m.group(0) for m in objects
                    if re.search(rf'\bid="{re.escape(template)}"', m.group(0)[:2000], re.I)), None)
        _reads['sdk', name] = retail_xml(template) if got is None else got
    return _reads['sdk', name]


def parent(xml, template=None):
    """The inheritFrom of the template's GameObject in `xml`, else of the first GameObject, else the first inheritFrom
    in its head (a file without one); None. A mission unit's file opens with its includes and defines, so the tag can
    sit far past the first 2000 characters (CNV_IceEngineer: the chain to BaseInfantry was lost there)."""
    heads = re.findall(r'<GameObject\b[^>]*>', xml or '')
    if template:
        mine = [h for h in heads if re.search(rf'\bid="{re.escape(template)}"', h, re.I)]
        heads = mine or heads
    m = re.search(r'\binheritFrom="([^"]+)"', heads[0] if heads else (xml or '')[:2000])
    return m.group(1) if m else None


def _inherited(template, own, read, empty):
    """read(xml) of the template, else of what it inherits from (xml_chain: a campaign override first, then the file
    of the template's own name); empty when none answers."""
    for _, xml in xml_chain(template, own):
        got = read(xml)
        if got != empty:
            return got
    return empty


_equivalent = {}


def equivalent_to(template, own=None):
    """The template's <EquivalentTo> (up its inheritFrom chain), lower case, else None. The engine's ownership count
    of a name counts these too: the opening's Riptide is AlliedAntiInfantryVehicle_Ground (EquivalentTo AlliedAnti-
    InfantryVehicle) and SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER counted it under both names (bench 2026-11-06
    engine_aiopen b; 2026-11-13 aiskuc / aiskuc7 / aiskucn: each opening Riptide +2 to a sum listing both). Whether
    the base name's own units count under the _Ground name was not seen (INFERRED: no)."""
    key = (template.lower(), bool((own or {}).get(template)))
    if key not in _equivalent:
        def read(xml):
            m = re.search(r'<EquivalentTo>\s*([^<\s]+)', xml or '')
            return m.group(1).lower() if m else None
        _equivalent[key] = _inherited(template, own, read, None)
    return _equivalent[key]


class _ProductionTemplates:
    @staticmethod
    def key(query, template, own):
        # Even an ancestor can be overridden, and _xml uses exact keys and searches files in order.
        return (query, template, tuple(own.items())) if own else (query, template.lower())

    @staticmethod
    def buttons(structure, own, upgrades):
        selected = command_set(structure, upgrades, own)
        # For an already selected set, only the ordered LogicCommand(Set) sources matter.
        key = ('production_buttons', selected, tuple(own.values())) if own else ('production_buttons', selected)
        if key not in _reads:
            sets, cmds = _commands(own)
            units, orders, research = [], [], []
            for button in sets.get(selected, ()):
                kind, target = cmds.get(button, ('', None))
                if kind == 'UNIT_BUILD':
                    orders.append((button, target))
                    if target:
                        units.append(target)
                elif kind in ('OBJECT_UPGRADE', 'PLAYER_UPGRADE') and target:
                    research.append((target, kind.split('_')[0]))
            _reads[key] = tuple(units), tuple(orders), tuple(research)
        return _reads[key]


def command_set(structure, upgrades=(), own=None):
    """The structure's CommandSet: its own, or the last CommandSetUpgrade's whose TriggeredBy it holds (AlliedConstruction
    Yard: ...Level2 once it holds Upgrade_AlliedTech2, its button then buys Tech3)."""
    key = _ProductionTemplates.key('production_command_set', structure, own)
    if key not in _reads:
        def read(xml):
            bare = re.sub(r'<CommandSetUpgrade\b.*?(/>|</CommandSetUpgrade>)', '', xml, flags=re.S)
            base = (re.findall(r'\bCommandSet="([^"]+)"', bare) or [None])[0]
            swaps = [(_attr(h, 'CommandSet'), frozenset(t.lower() for t in re.findall(r'<TriggeredBy>\s*([^<\s]+)', i)))
                     for h, i in _blocks(xml, 'CommandSetUpgrade')]
            return (base, tuple(swaps)) if base or swaps else None
        _reads[key] = _inherited(structure, own, read, None) or ('', ())
    base, swaps = _reads[key]
    held = {u.lower() for u in upgrades}
    for cs, trig in swaps:
        if cs and trig and trig <= held:
            base = cs
    return base or ''


def menu(factory, own=None, upgrades=()):
    """The units a structure builds: its CommandSet's UNIT_BUILD commands' objects, in the sidebar's order."""
    units, _, _ = _ProductionTemplates.buttons(factory, own, upgrades)
    return list(units)


def build_button(factory, template, own=None, upgrades=()):
    """The factory's UNIT_BUILD command that builds `template` (Command_ConstructAlliedEngineer), None when its
    CommandSet has none (the other way: built)."""
    _, orders, _ = _ProductionTemplates.buttons(factory, own, upgrades)
    return next((button for button, target in orders if target == template), None)


def built(factory, button, own=None, upgrades=()):
    """The template the factory's `button` builds (a UNIT_BUILD command of its CommandSet), else None."""
    _, orders, _ = _ProductionTemplates.buttons(factory, own, upgrades)
    return next((target for command, target in orders if command == button), None)


def upgrade_menu(structure, own=None, upgrades=()):
    """The upgrades a structure's buttons buy (OBJECT_UPGRADE: the structure's own; PLAYER_UPGRADE: the player's), as
    [(upgrade, 'OBJECT' | 'PLAYER')] in the sidebar's order."""
    _, _, research = _ProductionTemplates.buttons(structure, own, upgrades)
    return list(research)


UPGRADES = os.path.join(SAGEXML, 'GlobalData', 'upgrade.xml')
_upgrades = None


def _upgrade_table():
    global _upgrades
    if _upgrades is None:
        _upgrades = {}
        text = open(UPGRADES, encoding='utf-8', errors='replace').read() if os.path.exists(UPGRADES) else ''
        for head, inner in _blocks(text, 'UpgradeTemplate'):
            if _attr(head, 'id'):
                _upgrades[_attr(head, 'id').lower()] = (
                    int(_num(_attr(head, 'BuildCost'), 0)), _secs(_attr(head, 'BuildTime')),
                    re.findall(r'<RequiredObject>\s*([^<\s]+)', inner), re.findall(r'<NeededUpgrade>\s*([^<\s]+)', inner),
                    (_attr(head, 'Type', '') or '').upper())
    return _upgrades


def upgrade_type(upgrade, own=None):
    """'OBJECT', 'PLAYER' or ''; mission declarations precede retail upgrade.xml."""
    for xml in (own or {}).values():
        for head, _ in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'UpgradeTemplate'):
            if (_attr(head, 'id') or '').lower() == upgrade.lower():
                return (_attr(head, 'Type', '') or '').upper()
    return _upgrade_table().get(upgrade.lower(), (0, 0.0, [], [], ''))[4]


def upgrade_cost(upgrade):
    """(cost, seconds) of an UpgradeTemplate in GlobalData/upgrade.xml (BuildCost, BuildTime; (0, 0.0) where none)."""
    return _upgrade_table().get(upgrade.lower(), (0, 0.0))[:2]


def upgrade_needs(upgrade):
    """(objects, upgrades) the upgrade's GameDependency asks for: Upgrade_AlliedTech2 an AlliedRefinery of the player's
    (bench 2026-11-07 engine_tech: the yard's button is grey without one), Tech3 Upgrade_AlliedTech2 (held by the yard
    that buys it: inference)."""
    return tuple(_upgrade_table().get(upgrade.lower(), (0, 0.0, [], [], ''))[2:4])


def _with_includes(xml):
    """The XML with the text of every DATA:Includes/... file it references (AlliedWarFactory's TechUpgradeReceiver)."""
    out = [xml]
    for href in re.findall(r'href="DATA:([^"]+)"', xml):
        p = os.path.join(SAGEXML, *href.replace('\\', '/').split('/'))
        if ('text', p) in _reads or os.path.exists(p):
            out.append(_text(p))
    return '\n'.join(out)


def tech_receivers(structure, own=None):
    """The structure's TechUpgradeReceiver modules: [(upgrades in lower case, radius, rectangular?, {source templates
    in lower case})] -- an Allied factory takes Upgrade_AlliedTech2 / 3 from a yard or outpost holding it within 600
    (RECTANGULAR; AlliedTechUpgradeReceiverLevel2/3.xml)."""
    key = _ProductionTemplates.key('production_tech_receivers', structure, own)
    if key not in _reads:
        def read(xml):
            return tuple(
                (frozenset(t.lower() for t in re.findall(r'<TriggeredBy>\s*([^<\s]+)', i)), _num(_attr(h, 'Radius'), 0.0),
                 (_attr(h, 'DistanceType', '') or '').upper() == 'RECTANGULAR',
                 frozenset(t.lower() for t in re.findall(r'<IncludeThing>\s*([^<\s]+)', i)))
                for h, i in _blocks(_with_includes(xml), 'TechUpgradeReceiver'))
        _reads[key] = _inherited(structure, own, read, ())
    return [(set(upgrades), radius, rect, set(sources)) for upgrades, radius, rect, sources in _reads[key]]


def production(template, own=None):
    """(cost, seconds): BuildCost Amount and BuildTime of the template's XML ((0, 0.0) where it writes none)."""
    key = _ProductionTemplates.key('production_cost_time', template, own)
    if key not in _reads:
        def read(xml):
            cost = re.search(r'<BuildCost\b[^>]*\bAmount="([\d.]+)"', xml)
            secs = re.search(r'\bBuildTime="([\d.]+)"', xml)
            return int(float(cost.group(1))) if cost else 0, float(secs.group(1)) if secs else 0.0
        _reads[key] = _inherited(template, own, read, (0, 0.0))
    return _reads[key]


def energy(template, own=None):
    """EnergyProduction of the template (0 where it writes none): > 0 supplies the owner's power, < 0 is its demand."""
    def read(xml):
        m = re.search(r'\bEnergyProduction="(-?[\d.]+)"', xml)
        return int(float(m.group(1))) if m else None
    return _inherited(template, own, read, None) or 0


_command_powers = None


def command_power(button, own=None):
    """The special power a SPECIAL_POWER command button fires (LogicCommand's <SpecialPower>), else None."""
    global _command_powers
    if _command_powers is None:
        _command_powers = {}
        text = open(COMMANDS, encoding='utf-8', errors='replace').read() if os.path.exists(COMMANDS) else ''
        for head, inner in _blocks(text, 'LogicCommand'):
            m = re.search(r'<SpecialPower>\s*([^<\s]+)', inner)
            if _attr(head, 'id') and m:
                _command_powers[_attr(head, 'id')] = m.group(1)
    for xml in (own or {}).values():
        for head, inner in _blocks(xml or '', 'LogicCommand'):
            m = re.search(r'<SpecialPower>\s*([^<\s]+)', inner)
            if _attr(head, 'id') == button and m:
                return m.group(1)
    return _command_powers.get(button)


def replace_self(template, button, own=None):
    """(stand, replacement) of the template's ReplaceSelfSpecialAbility the button fires (the MCVs', the Japanese eggs',
    the Allied miner's SpecialPower_UnpackReplaceSelf), else None: at a point it drives there and turns into the
    replacement (bench 2026-11-10 engine_unpack, 2026-11-05 engine_build a)."""
    power = command_power(button, own)
    if not power:
        return None

    def read(xml):
        for head, inner in _blocks(xml, 'ReplaceSelfSpecialAbility'):
            if _attr(head, 'SpecialPowerTemplate') == power:
                m = re.search(r'<ReplacementTemplate>\s*([^<\s]+)', inner)
                if m:
                    return _num(_attr(head, 'StartAbilityRange'), 0.0), m.group(1)
        return None
    return _inherited(template, own, read, None)


PACK_EXTRA_FRAMES = 14         # frames the packed MCV stands beyond NewObjectUnpackTime: INFERRED, fitted to
                               # engine_pack a / s / j (bench 11-11: out of the 40 square at 50 / 51 / 54, sim
                               # with 30 alone 38; arrival 14 frames late alike) -- not read in the code


def replace_unpack_frames(template, button, own=None):
    """Frames the replacement stands still after a ReplaceSelfSpecialAbility with DISABLE_NEW_OBJECT_DURING_UNPACK
    (a yard packing into its MCV): NewObjectUnpackTime x 15 + PACK_EXTRA_FRAMES; 0 without the option."""
    power = command_power(button, own)

    def read(xml):
        for head, _ in _blocks(xml, 'ReplaceSelfSpecialAbility'):
            if _attr(head, 'SpecialPowerTemplate') == power:
                if 'DISABLE_NEW_OBJECT_DURING_UNPACK' not in (_attr(head, 'ReplaceOptions') or ''):
                    return 0
                secs = _secs(expand(_attr(head, 'NewObjectUnpackTime', '0s')))     # the Allied yard's is a define
                return int(round(secs * LIFE_FPS)) + PACK_EXTRA_FRAMES
        return None
    return _inherited(template, own, read, None) or 0


def weapon_fire_ability(template, button, own=None):
    """The template's WeaponFireSpecialAbilityUpdate the button fires (its SpecialPowerTemplate is the button's
    power), else None: dict(weapon, unpack / pack / freeze frames, range (StartAbilityRange), options, busy_pack).
    Yuriko's blast, Natasha's pilot snipe, the dog's bark (bench 11-11 engine_wfire)."""
    power = command_power(button, own)
    if not power:
        return None

    def read(xml):
        for head, _ in _blocks(xml, 'WeaponFireSpecialAbilityUpdate'):
            if _attr(head, 'SpecialPowerTemplate') == power and _attr(head, 'SpecialWeapon'):
                opts = (_attr(head, 'Options') or '').split()
                return dict(weapon=_attr(head, 'SpecialWeapon'), power=power,
                            unpack=_frames(_secs(expand(_attr(head, 'UnpackTime', '0s')))),
                            pack=_frames(_secs(expand(_attr(head, 'PackTime', '0s')))),
                            freeze=_frames(_secs(expand(_attr(head, 'FreezeAfterTriggerDuration', '0s')))),
                            range=_num(_attr(head, 'StartAbilityRange'), 0.0), options=opts,
                            busy_pack='BUSY_DURING_PACK' in opts)
        return None
    return _chain(template, own, read)


def hit_reaction(template, own=None):
    """E172: zero-threshold heavy HIT_REACTION with status validation.

    Only the retail shielded Peacekeeper condition producer is measured.
    Nonzero thresholds, light/medium reactions, death-type gates and GoIdle
    are unsupported. rotate: RotateToSourceWhenDamaged (engine_hitreaction_r).
    """
    def read(xml):
        for head, inner in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'HitReactionBehavior'):
            if (_attr(head, 'xai:joinAction') == 'Remove'
                    or _num(_attr(head, 'HeavyDamageHitReactionThreshold', '0')) != 0
                    or any(_num(_attr(head, k, '0')) != 0 for k in
                           ('LightDamageHitReactionThreshold', 'MediumDamageHitReactionThreshold'))
                    or any(_secs(_attr(head, k, '0s')) != 0 for k in
                           ('LightDamageHitReactionLifeTimer', 'MediumDamageHitReactionLifeTimer'))
                    or _attr(head, 'GoIdleWhenDamaged', 'false') != 'false'
                    or _attr(head, 'RequiredDeathTypes', '')):
                return False
            validation = next(_blocks(inner, 'ObjectStatusValidation'), ('', ''))[0]
            return dict(seconds=_secs(_attr(head, 'HeavyDamageHitReactionLifeTimer', '0s')),
                        rotate=_attr(head, 'RotateToSourceWhenDamaged', 'false') == 'true',
                        required=set(_attr(validation, 'RequiredStatus', '').split()),
                        forbidden=set(_attr(validation, 'ForbiddenStatus', '').split()))
        return None
    return _chain(template, own, read) or None


def movement_power(template, button, own=None):
    """Targeted MovementSpecialPower data for a waypoint press (E171 Oni rush).

    Only the in-range static-point path is measured. Object targeting, approach,
    cooldowns, collision/bounce and exact activation/exit timing remain gaps.
    """
    power = command_power(button, own)
    if not power:
        return None

    def read(xml):
        xml = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        for head, _ in _blocks(xml, 'MovementSpecialPower'):
            if _attr(head, 'SpecialPowerTemplate') != power or _attr(head, 'MovementType') != 'TARGETED':
                continue
            tpl = _retail_power_heads().get(power, '')
            return dict(duration=_frames(_secs(expand(_attr(head, 'Duration', '0s')))),
                        bits=set((_attr(head, 'ObjectStatus') or '').split()),
                        locomotor=_attr(head, 'LocomotorSet'),
                        modifier=_attr(head, 'AttributeModifier') if
                        _attr(head, 'AttributeModifierAffectsSelf', 'false') == 'true' else '',
                        minimum=float(_attr(tpl, 'MinCastRange', '0')),
                        maximum=float(_attr(tpl, 'MaxCastRange', '0')))
        return None
    return _chain(template, own, read)


def self_module_power(template, button, own=None):
    """The template's ActivateModuleSpecialPower the button fires with AttributeModifierAffectsSelf="true": dict(
    modifier (its AttributeModifier id), trigger (the SpecialAbilityUpdate of that power: SetObjectStatusOnTrigger
    bits), pack (its PackTime frames)), else None. The shinobi's smoke bomb (NON_AUTOACQUIRABLE 10 s, UNATTACKABLE
    through the 0.5 s pack), the Tsunami's energized armor (GENERIC_TOGGLE_STATE, SPEED 125 % 10 s): engine_acts_mix.
    E153 engine_activate also reads SELF_POSITION links to an initially inactive
    ShieldSphereUpdate: shields contains its ObjectStatus bits and Duration frames.
    This covers status lifetime only; absorption, caps and early termination are gaps."""
    power = command_power(button, own)
    if not power:
        return None

    def read(xml):
        xml = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        for head, inner in _blocks(xml, 'ActivateModuleSpecialPower'):
            if _attr(head, 'SpecialPowerTemplate') != power:
                continue
            modifier = (_attr(head, 'AttributeModifier') or '') if \
                _attr(head, 'AttributeModifierAffectsSelf', 'false') == 'true' else ''
            shields = []
            for link, _ in _blocks(inner, 'Modules'):
                if _attr(link, 'TriggerType') != 'SELF_POSITION' or \
                        _attr(link, 'TriggerAtTargetPosition', 'false') != 'false':
                    continue
                for shield, _ in _blocks(xml, 'ShieldSphereUpdate'):
                    if _attr(shield, 'id') == _attr(link, 'ModuleId') and \
                            _attr(shield, 'InitiallyActive', 'false') == 'false':
                        shields.append((_attr(shield, 'id'), set((_attr(shield, 'ObjectStatus') or '').split()),
                                        _frames(_secs(expand(_attr(shield, 'Duration', '0s'))))))
            if not modifier and not shields:
                continue
            trig, pack, hold, keep = set(), 0, 0, True
            for h, _ in _blocks(xml, 'SpecialAbilityUpdate'):
                if _attr(h, 'SpecialPowerTemplate') == power:
                    trig = set((_attr(h, 'SetObjectStatusOnTrigger') or '').split())
                    pack = _frames(_secs(expand(_attr(h, 'PackTime', '0s'))))
                    hold = pack + _frames(_secs(expand(_attr(h, 'UnpackTime', '0s'))))
                    keep = 'RECONSTITUTE_STORED_COMMAND' in (_attr(h, 'Options') or '').split()
            return dict(modifier=modifier, power=power, trigger=trig, pack=pack, shields=shields, hold=hold, keep=keep)
        return None
    return _chain(template, own, read)


def press_records(template, button, own=None):
    """(power, n): the PLAYER_TRIGGERED_SPECIAL_POWER entries a script's press of the button records at once, else None.
    engine_cast all (round 242, bench 11-15 CampCastAll_mcp_1115_040813): Tanya's time belt read twice by one reader
    (名 +16 = 8 x 2) -- her SpecialPower module has UpdateModuleStartsAttack="false" (it records at the press) and a
    ReconstituteStateSpecialAbility of the same power records again (INFERRED: at the press too). King Oni's
    shockwave and the bear's roar (UpdateModuleStartsAttack="true") record once, when their weapon fires (wfire)."""
    power = command_power(button, own)
    if not power:
        return None

    def read(xml):
        xml = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        starts = [h for h, _ in _blocks(xml, 'SpecialPower') if _attr(h, 'SpecialPowerTemplate') == power
                  and _attr(h, 'UpdateModuleStartsAttack', 'false') == 'false']
        if not starts:
            return None
        again = [h for h, _ in _blocks(xml, 'ReconstituteStateSpecialAbility')
                 if _attr(h, 'SpecialPowerTemplate') == power]
        return (power, 1 + bool(again))
    return _chain(template, own, read)


def power_target_type(power):
    """The retail SpecialPowerTemplate's TargetType (NONE / LOCATION / OBJECT ...), '' when not found."""
    return _attr(_retail_power_heads().get(power, ''), 'TargetType') or ''


def self_projectile_ground_weapon(template, own=None):
    """Ground-hit payload of the real Sickle's BezierProjectile (knock_sickle).

    Only dispatch after landing is measured here; curved flight and landing
    coordinates are still supplied by the existing INFERRED leap scheduler.
    """
    def read(xml):
        head, _ = next(_blocks(xml, 'BezierProjectile'), ('', ''))
        return _attr(head, 'GroundHitWeapon') or None
    return _inherited(template, own, read, None)


def self_projectile_speed(weapon, own=None):
    """WeaponSpeed of a ProjectileSelf="true" weapon (the unit itself flies: the Sickle's leap 300), else None."""
    special_weapon(weapon, own)                 # fills _weapon_blocks
    head = (_weapon_blocks.get(weapon) or ('', ''))[0]
    if (_attr(head, 'ProjectileSelf') or '').lower() != 'true':
        return None
    return _num(_attr(head, 'WeaponSpeed'), 0.0) or None


def special_weapon(weapon, own=None):
    """What a special ability's weapon does where it goes off (weapon_fire_ability): dict(affects (RadiusDamageAffects),
    damage [(damage, type, radius, delay s)] from its DamageNuggets, paralyze [dict(kind (ParalyzeType), radius,
    seconds, include (KindOf), relation, exclude (templates, lower), forbidden_upgrade, rule, unkinds (Exclude),
    status_exclude, things (IncludeThing, lower))] from its ParalyzeNuggets, the
    one SpecialObjectFilter each), modifiers [dict(modifier, the upgrade gate, include / unkinds, status_exclude)] from
    its AttributeModifierNuggets. Not read: MetaImpactNugget (the blast's shockwave: a push, gap)."""
    global _weapon_blocks
    if _weapon_blocks is None:
        _weapon_blocks = {}
        for text in _weapon_files():
            for head, body in _blocks(re.sub(r'<!--.*?-->', '', text, flags=re.S), 'WeaponTemplate'):
                _weapon_blocks.setdefault(_attr(head, 'id'), (head, body))
    mine = {}
    for text in (own or {}).values():
        for head, body in _blocks(text or '', 'WeaponTemplate'):
            mine[_attr(head, 'id')] = (head, body)
    whead, wbody = mine.get(weapon) or _weapon_blocks.get(weapon, ('', ''))
    wbody = re.sub(r'<!--.*?-->', '', wbody or '', flags=re.S)
    out = dict(affects=frozenset((_attr(whead, 'RadiusDamageAffects') or 'ENEMIES NEUTRALS').split()), damage=[],
               paralyze=[], modifiers=[])
    for nh, _ in _blocks(wbody, 'DamageNugget'):
        out['damage'].append((_num(_attr(nh, 'Damage'), 0.0), _attr(nh, 'DamageType') or '',
                              _num(_attr(nh, 'Radius'), 0.0), _secs(_attr(nh, 'DelayTimeSeconds') or '0s')))
    for nh, inner in _blocks(wbody, 'ParalyzeNugget'):
        fh, fi = next(_blocks(inner or '', 'SpecialObjectFilter'), ('', ''))
        forbidden = re.findall(r'<ForbiddenUpgrade>\s*([^<>\s]+)', inner or '')
        required = re.findall(r'<RequiredUpgrade>\s*([^<>\s]+)', inner or '')
        out['paralyze'].append(dict(
            required_upgrade=required[0] if required else '',
            kind=_attr(nh, 'ParalyzeType') or 'EMP', radius=_num(_attr(nh, 'Radius'), 0.0),
            seconds=_secs(_attr(nh, 'DurationSeconds') or '0s'),
            include=frozenset((_attr(fh, 'Include') or '').split()), relation=_attr(fh, 'Relationship') or '',
            exclude=frozenset(x.lower() for x in re.findall(r'<ExcludeThing>\s*([^<>\s]+)', fi or '')),
            forbidden_upgrade=forbidden[0] if forbidden else '', rule=_attr(fh, 'Rule') or 'ANY',
            unkinds=frozenset((_attr(fh, 'Exclude') or '').split()),
            status_exclude=frozenset((_attr(fh, 'StatusBitFlagsExclude') or '').split()),
            things=frozenset(x.lower() for x in re.findall(r'<IncludeThing>\s*([^<>\s]+)', fi or ''))))
    for nh, inner in _blocks(wbody, 'AttributeModifierNugget'):     # on the target (the shrink ray: engine_acts_shr)
        fh, _ = next(_blocks(inner or '', 'SpecialObjectFilter'), ('', ''))
        gate = [(re.findall(rf'<{g}>\s*([^<>\s]+)', inner or '') or [''])[0]
                for g in ('RequiredUpgrade', 'ForbiddenUpgrade')]
        mid = _attr(nh, 'AttributeModifierName')
        src = next((text for text in (own or {}).values() if text and  # a mission's own, else retail's
                    any(_attr(h, 'id') == mid for h, _ in _blocks(text, 'AttributeModifier'))), '')
        kinds = {k: frozenset((_attr(fh, a) or '').split())
                 for k, a in (('include', 'Include'), ('unkinds', 'Exclude'), ('status_exclude', 'StatusBitFlagsExclude'))}
        out['modifiers'].append(dict(modifier=mid, xml=src, mod=modifier(src, mid), required_upgrade=gate[0],
                                     forbidden_upgrade=gate[1], **kinds))
    return out


def needs(template, own=None):
    """(objects, upgrades) its GameDependency asks for: every RequiredObject the player must own, every NeededUpgrade
    the player must hold (all of them: inference, the sidebar's lit buttons not measured)."""
    key = _ProductionTemplates.key('production_needs', template, own)
    if key not in _reads:
        def read(xml):
            _, inner = next(_blocks(xml, 'GameDependency'), (None, ''))
            return (tuple(re.findall(r'<RequiredObject>\s*([^<\s]+)', inner)),
                    tuple(re.findall(r'<NeededUpgrade>\s*([^<\s]+)', inner)))
        _reads[key] = _inherited(template, own, read, ((), ()))
    objects, upgrades = _reads[key]
    return list(objects), list(upgrades)


def exit_of(factory, own=None):
    """(create, rally, door frames) of a factory: UnitCreatePoint and NaturalRallyPoint (x, y) in its own frame (rally
    None where it writes none), and ProductionUpdate's DoorOpeningTime in frames, rounded up (0.66 s -> 10: bench
    2026-11-05 engine_production, every unit appeared 10 frames after its build was full)."""
    key = _ProductionTemplates.key('production_exit', factory, own)
    if key not in _reads:
        def read(xml):
            if '<ProductionUpdate' not in xml:
                return None

            def point(tag):
                head, _ = next(_blocks(xml, tag), (None, ''))
                return None if head is None else (_num(_attr(head, 'x'), 0.0), _num(_attr(head, 'y'), 0.0))
            head, _ = next(_blocks(xml, 'ProductionUpdate'), ('', ''))
            door = _secs(_attr(head or '', 'DoorOpeningTime', '0s'))
            return point('UnitCreatePoint') or (0.0, 0.0), point('NaturalRallyPoint'), \
                int(-(-round(door * LIFE_FPS, 6) // 1))
        _reads[key] = _inherited(factory, own, read, None) or ((0.0, 0.0), None, 0)
    return _reads[key]
