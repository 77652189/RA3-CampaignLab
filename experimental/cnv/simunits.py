r"""What the plan simulator (sim.py) needs of a unit, from the game's own data: how fast it goes, on what (ground,
water, both, air), how far it sees, its KindOf. Retail templates from the SDK's SageXML (the index mapstudy keeps:
work\sagexml_gameobjects.json gives each template's file and KindOf; the file its LocomotorSet's NORMAL Speed and its
VisionRange / ShroudClearingRange, defines resolved; each field from the nearest template up the inheritFrom chain that
writes it, resolve()), cached in work\sim_units_v6.json. Our own units (a mission's Unit: its XML) are read the same
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'campaign'))
import labpaths  # noqa: E402

CACHE = os.path.join(labpaths.WORK, 'sim_units_v6.json')     # v2: defines resolved (2026-10-29); v3: + ShroudClearingHeight;
                                                            # v4: + radius (R8); v5: radius read through 'Type= "BOX"'
                                                            # v6: inherited fields resolved up inheritFrom (eggs, 11-10)
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
    """Locomotor template id -> its Surfaces (GROUND, WATER, AIR ...)."""
    global _surf_memo
    if _surf_memo is None:
        _surf_memo = _read_surfaces()
    return _surf_memo


def _read_surfaces():
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


def _own_fields(text, surfaces):
    """What one GameObject block writes itself (None: left to what it inherits): speed and its locomotor's surfaces
    (the NORMAL LocomotorSet), vision, shroud, clear height, radius."""
    speed, surf = None, None
    for m in re.finditer(r'<LocomotorSet\b(.*?)/?>', text, re.S):
        a = m.group(1)
        cond = re.search(r'\bCondition="([^"]+)"', a)
        if cond and cond.group(1) != 'NORMAL':
            continue
        sp, lo = re.search(r'\bSpeed="([\d.]+)"', a), re.search(r'\bLocomotor="([^"]+)"', a)
        if sp and speed is None:
            speed = float(sp.group(1))
            surf = surfaces.get(lo.group(1), []) if lo else []
    return dict(speed=speed, surf=surf, vision=number(text, 'VisionRange'), shroud=number(text, 'ShroudClearingRange'),
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
    r = resolve(template, own, surfaces)
    kinds = set(r['kinds']) | ({'STRUCTURE'} if r['sorting'] == 'STRUCTURE' else set())
    return dict(speed=r['speed'], surface=surface_of(r['surf'] or [], kinds), vision=r['vision'],
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
    """(template lower case, its index entry with EditorSorting resolved up the chain, its XML file) for every unit
    and building: the index's file, or -- where the index points at a campaign override (Includes/CampaignOverrides:
    an edit, not the unit) -- the SageXML file of the template's own name. A template that does not write its
    EditorSorting takes its base's (the Nanocore eggs: BaseEgg's UNIT)."""
    idx = json.load(open(INDEX, encoding='utf-8')) if os.path.exists(INDEX) else {}
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


def _build():
    surfaces = _surfaces()
    return {t: read_xml(t, surfaces=surfaces) for t, _, _ in units()}


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
COMBAT_CACHE = os.path.join(labpaths.WORK, 'sim_combat_v34.json')    # v34: ai_parts (a weapon's nuggets + warhead for the AI's rate); v33: lift dispatch
                                                                    # (Flags ATTACK_NEEDS_LINE_OF_SIGHT)
WEAPONS_GLOB = ('GlobalData', 'Weapon.xml')
ARMOR = os.path.join(SAGEXML, 'GlobalData', 'Armor.xml')
ARMOR_DEFAULT = 100.0           # a damage type an armour does not name: taken in full (a guess)


def percent(armor, dtype):
    """The percent of `dtype` damage an armour ({type: percent}, '*': its ArmorTemplate Default) takes: the type's own
    line, else the Default (CryoBeamFrozenArmor 90000: a frozen unit breaks at a touch; InvulnerableArmor 0), else
    ARMOR_DEFAULT."""
    return armor.get(dtype, armor.get('*', ARMOR_DEFAULT))


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
                if (rest.strip() or fi.strip() or len(filters) > 1
                        or (filters and _attr(f, 'Rule', 'ANY') != 'ANY')
                        or set(re.findall(r'(\w+)\s*=', f)) - {'Rule', 'Include', 'Exclude'}
                        or set(re.findall(r'(\w+)\s*=', h)) - {'id', 'Lifetime'}):
                    unsupported.append('ActivateLiftObjectNugget')
                else:
                    lifts.append(dict(include=_attr(f, 'Include', '').split(), exclude=_attr(f, 'Exclude', '').split()))
            if lifts:
                got['lift'] = lifts
            # Grappling still needs its unresolved caster update.
            for effect in ('GrapplingHookNugget',):
                if list(_blocks(bare, effect)):
                    unsupported.append(effect)
            impacts, delayed_impacts = [], []
            for h, inner in _blocks(bare, 'MetaImpactNugget'):
                # Retail Omega writes Amount/Radius/Z with spaces around '='.
                h = re.sub(r'(\w+)\s*=\s*"', r'\1="', h)
                # Delayed payloads feed only the isolated expiry interface.
                # Never send them through immediate Physics: observation and
                # landing phases remain unresolved, as do other variants.
                unsupported.append('MetaImpactNugget')
                fields = set(re.findall(r'(\w+)\s*=', h))
                if not (inner or '').strip() and fields <= {
                        'id', 'ShockWaveAmount', 'ShockWaveRadius', 'ShockWaveZMult', 'ShockWaveTaperOff',
                        'ShockwaveDelaySeconds'} and all(
                        _attr(h, field) is not None for field in
                        ('ShockWaveAmount', 'ShockWaveRadius')):
                    seconds = _secs(_attr(h, 'ShockwaveDelaySeconds', '0s'))
                    if not math.isfinite(seconds) or seconds < 0:
                        continue
                    effect = dict(amount=_num(_attr(h, 'ShockWaveAmount')),
                                  radius=_num(_attr(h, 'ShockWaveRadius')),
                                  zmult=_num(_attr(h, 'ShockWaveZMult', '1')),
                                  taper=_num(_attr(h, 'ShockWaveTaperOff', '0')))
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
                # Ordinary target-only launch notification. Radius/filter variants
                # and the whole AI response remain explicitly incomplete.
                if not (inner or '').strip() and set(re.findall(r'(\w+)\s*=', h)) <= {
                        'id', 'MinTimeToImpactFudgeFactor', 'MaxTimeToImpactFudgeFactor'}:
                    informs.append(dict(min=_num(_attr(h, 'MinTimeToImpactFudgeFactor', '0.85')),
                                        max=_num(_attr(h, 'MaxTimeToImpactFudgeFactor', '1.15'))))
            if informs:
                got['inform'] = informs
            if any(_blocks(bare, 'InformTargetNugget')):
                # engine_inform_ai: an AI miner can react before the slow shell hits.
                # Partial launch/table/armor execution is modeled; full replay,
                # history and radius/filter variants remain gaps.
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
                inform=w.get('inform', []), weapon_speed=w.get('weapon_speed', 999999.0),
                weapon_key=w.get('weapon_key'),
                meta_impacts=w.get('meta_impacts', weapons.get(w.get('warhead'), {}).get('meta_impacts', [])),
                delayed_meta_impacts=w.get('delayed_meta_impacts',
                    weapons.get(w.get('warhead'), {}).get('delayed_meta_impacts', [])),
                unmodeled_effects=list(dict.fromkeys(w.get('unmodeled_effects', []) +
                    weapons.get(w.get('warhead'), {}).get('unmodeled_effects', []))))


def lift_module(template, own=None):
    """D50 timing interface, see work/re/d50_lift_release.md.

    Only explicit timer fields are supported; no guessed XSD defaults.
    Falling/landing, aircraft and vertical motion remain gaps.
    """
    def read(xml):
        modules = list(_blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'LiftObjectUpdate'))
        if not modules:
            return None
        h, inner = modules[0]
        if len(modules) != 1 or inner.strip() or any(_attr(h, k) is None for k in ('TimeIncrement', 'MaxTimeLifted')):
            return False
        return dict(increment=int(_secs(_attr(h, 'TimeIncrement')) * FPS),
                    maximum=int(_secs(_attr(h, 'MaxTimeLifted')) * FPS))
    return _chain(template, own, read)


class LiftTimers:
    """Caster-owned target ledger, D50. Release does not clear object status.

    A positive counter is decremented; a zero counter releases on its next
    update. New entries use increment directly, only renewal clamps to max.
    """
    def __init__(self):
        self.remaining = {}

    def hit(self, caster, target, increment, maximum):
        key = (caster, target)
        self.remaining[key] = (min(maximum, self.remaining[key] + increment)
                               if key in self.remaining else increment)

    def tick(self):
        released = []
        for key, left in list(self.remaining.items()):
            if left > 0:
                self.remaining[key] -= 1
            else:
                released.append(key)
                del self.remaining[key]
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
        return _num(_attr(shape[0], 'Height')) if shape and _attr(shape[0], 'Height') is not None else None
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
                weapons=[g for g in guns if (g['dps'] > 0 or g.get('sdps', 0) > 0 or g.get('dot') or g.get('lift')) and g['range'] > 0])


def freeze(template, own=None):
    """(tracker(), the armour {type: percent} of its ArmorSet with Conditions SECONDARY_DAMAGE) of a template, each
    from its own XML else what it inherits from (the retail units inherit both from BaseVehicle / BaseInfantry /
    BaseStructure; INFERRED that a unit's own ArmorSet does not drop the base's frozen one: frozen units break at a
    touch in the game); (None, None) where neither is found."""
    def frozen(xml):
        m = re.search(r'<ArmorSet\b[^>]*\bArmor="([^"]+)"[^>]*\bConditions="[^"]*SECONDARY_DAMAGE', xml or '')
        return m.group(1) if m else None
    try:
        t = _inherited(template, own, lambda x: tracker(x or ''), None)
        a = _inherited(template, own, frozen, None)
    except (OSError, ValueError):
        return None, None
    return t, (_fight_data()['armors'].get(a) if a else None)


def immortal_body(template, own=None):
    """(immortal, MaxHealth) from the nearest Body in the XML inheritance chain.
    A different body overrides an inherited immortal body. Retail props may be
    absent from the combat cache, so read their MaxHealth here too.
    """
    def read(xml):
        xml = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        body = next(_blocks(xml, 'Body'), None)
        if body is None:
            return None
        immortal = bool(list(_blocks(body[1], 'ImmortalBody')))
        return immortal, number(xml, 'MaxHealth') if immortal else None
    return _chain(template, own, read) or (False, None)


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


def manager_body(template, own=None):
    """Whether the nearest explicit Body is ManagerBody, respecting body overrides."""
    def read(xml):
        xml = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        body = next(_blocks(xml, 'Body'), None)
        return bool(list(_blocks(body[1], 'ManagerBody'))) if body is not None else None
    return bool(_chain(template, own, read))


def manager_proxy_health(template, own=None):
    """Whole-proxy effective HP; INFERRED from engine_managerbody a / b.

    HB_Bridge_02 at lengths 270 / 700 loses 20 percent to 200 script damage,
    independent of length, and lethal damage leaves a live 1-percent proxy.
    Use the retail center body's MaxHealth (1000), not ManagerBody's XML 1.
    Mapping that observable floor to exactly 1% HP is INFERRED (a counter-side
    minimum of 1 could hide lower internal HP); internal HP,
    other bridge configurations, segment damage/sharing and repairs are unbenched.
    This creates no bridge pieces and does not sum their health.
    """
    if not manager_body(template, own):
        return None
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


def suppression(template, own=None):
    """Nearest infantry suppression rule; an explicit Remove stops inheritance.

    RA3 data only. engine_suppress_probe 2026-11-10 confirms individual hit
    lifetimes and birth-phased samples; no invented linear decay.
    """
    def read(xml):
        for h, _ in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'SuppressionUpdate'):
            if _attr(h, 'xai:joinAction') == 'Remove':
                return False
            return dict(threshold=_num(_attr(h, 'Suppressability')),
                        every=max(1, _frames(_secs(_attr(h, 'UpdateDelay', '1s')))),
                        duration=_frames(_secs(_attr(h, 'SuppressionDuration', '0s'))),
                        modifier=_attr(h, 'AttributeModifierSuppressed'))
        return None
    return _chain(template, own, read) or None


def repair_update(template, own=None):
    """RepairUpdate fields (schema defaults); player repair, distinct from AutoHeal.

    Includes and inheritance are resolved. Rebuild/dead and non-toggleable paths
    are read so the caller can report them as unmeasured rather than heal them.
    """
    def read(xml):
        clean = re.sub(r'<!--.*?-->', '', _with_includes(xml), flags=re.S)
        head, inner = next(_blocks(clean, 'RepairUpdate'), (None, ''))
        if head is None:
            return None
        cost, _ = next(_blocks(inner, 'PercentOfBuildCostToRebuildInfo'), ('', ''))
        return {'rate': _num(_attr(head, 'HealAmountPerSecond'), 10),
                'toggleable': _attr(head, 'Toggleable', 'true').lower() == 'true',
                'dead': _attr(head, 'RepairableWhenDead', 'false').lower() == 'true',
                'cost': tuple(_num(_attr(cost, state), 50) / 100
                              for state in ('Pristine', 'Damaged', 'ReallyDamaged', 'Rubble'))}
    return _inherited(template, own, read, None)


def repair_measured_config(template, own=None):
    """Reject unmeasured RepairUpdate fields, including fields outside repair_update's summary."""
    def read(xml):
        clean = re.sub(r'<!--.*?-->', '', _with_includes(xml), flags=re.S)
        blocks = list(_blocks(clean, 'RepairUpdate'))
        if not blocks:
            return None
        if len(blocks) != 1:
            return False
        head, inner = blocks[0]
        attrs = set(re.findall(r'([\w:]+)\s*=', head)) - {'xmlns', 'id'}
        if attrs - {'HealAmountPerSecond', 'Toggleable', 'RepairableWhenDead'}:
            return False
        tags = set(re.findall(r'<(?!/)(\w+)', inner))
        if tags - {'PercentOfBuildCostToRebuildInfo', 'SelfAudio'}:
            return False
        for h, _ in _blocks(inner, 'PercentOfBuildCostToRebuildInfo'):
            if set(re.findall(r'([\w:]+)\s*=', h)) - {'Pristine', 'Damaged', 'ReallyDamaged', 'Rubble'}:
                return False
        return True
    return bool(_inherited(template, own, read, None))


def autoheal(template, own=None):
    """(amount, every, wait): AutoHealBehavior of a template that mends from the start, with no state or rank in the
    way -- HealingAmount points every `every` frames, the first `wait` frames after a hurt (engine_heal a / b, bench
    11-06, docs/engine/heal.md 1: the intervals are floor(15 x seconds) frames, 0.5 s is 7). None without one (the
    state-gated and rank-gated ones are not modelled: InitiallyActive false or an ObjectStatusValidation)."""
    def read(xml):
        for head, inner in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'AutoHealBehavior'):
            if _attr(head, 'InitiallyActive') == 'false' or _attr(head, 'ObjectStatusValidation') or \
                    '<ObjectStatusValidation' in inner or \
                    _num(_attr(head, 'Radius'), 0.0) > 0:
                continue
            return (int(_num(_attr(head, 'HealingAmount'), 0.0)),
                    int(15 * _secs(_attr(head, 'HealingDelay') or '1s')),
                    int(15 * _secs(_attr(head, 'StartHealingDelay') or '0s')))
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


def tracker(text):
    """A SecondaryDamageTracker (the freeze): {'every': UpdateDuration s, 'melt': DissipateAmount taken off each
    UpdateDuration, 'cap': MaxDamageClampScaler (the most it holds, x max health), 'steps': [[Fraction of max health,
    AttributeModifier id, OnEnterDisable, SetUpgradedArmor, DIE_ON_ENTER], ...] lowest first}; None without one. Retail BaseVehicle /
    BaseInfantry / BaseStructure: 25 a second, 200 %, 0.2 .. 0.8 slow speed and rate of fire to 80 .. 20 %, 1.0 frozen
    (UNDER_FROZEN, CryoBeamFrozenArmor). A $ define as the cap: MAX_SECONDARY_DAMAGE_SCALER, 200 % (the only one)."""
    blocks = list(_blocks(re.sub(r'<!--.*?-->', '', text, flags=re.S), 'SecondaryDamageTracker'))
    if not blocks:
        return None
    head, inner = blocks[-1]                            # an override after the base's (xai:joinAction Replace)
    cap = _attr(head, 'MaxDamageClampScaler') or '125%'
    cap = 2.0 if cap.startswith('=') else _num(cap.rstrip('%'), 125.0) / 100.0
    steps = sorted((_num(_attr(h, 'Fraction')), _attr(h, 'AttributeModifier'),
                    _attr(h, 'OnEnterDisable') == 'true', _attr(h, 'SetUpgradedArmor') == 'true',
                    'DIE_ON_ENTER' in (_attr(h, 'Options') or '').split())
                   for h, _ in _blocks(inner or '', 'EffectInfo'))
    return dict(every=_secs(_attr(head, 'UpdateDuration') or '1s'), melt=_num(_attr(head, 'DissipateAmount'), 0.0),
                cap=cap, steps=[list(x) for x in steps])


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
    """The weapon template of each WeaponSlot as read_fight takes it (the PRIMARY one), from the unit's XML or what it
    inherits from (5 steps); [] when the XML names none. Sim.add asks it when fight() reads no weapon (a gap, not a
    unit without guns); simcoverage.declared_picks reads the same."""
    try:
        xml = _xml(template, own)
    except (OSError, ValueError):
        return []
    for _ in range(5):
        picks = []
        for head, body in _blocks(xml or '', 'WeaponSetUpdate'):
            for slot in re.finditer(r'<WeaponSlot\w*\b.*?</WeaponSlot\w*>', body, re.S):
                ws = [(_attr(h, 'Ordering'), _attr(h, 'Template')) for h, _ in _blocks(slot.group(0), 'Weapon')]
                pick = next((t for o, t in ws if o == 'PRIMARY_WEAPON'), ws[0][1] if ws else None)
                if pick:
                    picks.append(pick)
        if picks:
            return picks
        up = parent(xml, template)
        if not up or up.lower() == template.lower():
            break
        try:
            xml = _xml(up, own)
        except (OSError, ValueError):
            break
    return []


def weapon_sets(template, own=None):
    """The weapon choice a unit makes by its ObjectStatus (engine line C round 11, engine_weaponset a / b, bench 11-09,
    docs/engine/weaponset.md): per WeaponSlot the list of [need, forbid, weapon] of its <Weapon> lines in XML order
    (need = ObjectStatus bits all present, forbid = ForbiddenObjectStatus bits none present, weapon = the resolved
    template, PRIMARY_WEAPON flagged). A line's Upgrade="X" is one more need, the bit UPGRADE_BIT + X lowercased: the
    line is held only while the object (or its player) has X (pick_weapons' upgrades) -- the IFV's passenger guns
    (Uprade_IFV_*, granted by who rides in, not modelled) are not an empty IFV's; before, its slots 3-7 (one
    upgrade line each) gave it a 750-dps pistol and the AI's expected efficiency 7.6 for it vs conscripts (B round
    132). None where no weapon line carries a status or upgrade condition (the unit's weapons are read_fight's,
    whatever its status). Walks the inheritance like declared_weapons."""
    try:
        xml, table = _xml(template, own), weapon_table(own)
    except (OSError, ValueError):
        return None
    for _ in range(5):
        slots = []
        for head, body in _blocks(xml or '', 'WeaponSetUpdate'):
            for slot in re.finditer(r'<WeaponSlot\w*\b.*?</WeaponSlot\w*>', body, re.S):
                slots.append([(set((_attr(h, 'ObjectStatus') or '').split())
                               | {UPGRADE_BIT + u.lower() for u in (_attr(h, 'Upgrade') or '').split()},
                               set((_attr(h, 'ForbiddenObjectStatus') or '').split()),
                               _attr(h, 'Ordering') == 'PRIMARY_WEAPON', _attr(h, 'Template'))
                              for h, _ in _blocks(slot.group(0), 'Weapon')])
        if slots:
            if not any(need or forbid for s in slots for need, forbid, _, _ in s):
                return None
            return [[(need, forbid, prim, _resolve(table[t], table) if t in table else None)
                     for need, forbid, prim, t in s] for s in slots]
        up = parent(xml, template)
        if not up or up.lower() == template.lower():
            break
        try:
            xml = _xml(up, own)
        except (OSError, ValueError):
            break
    return None


UPGRADE_BIT = 'UPGRADE:'            # weapon_sets: a <Weapon Upgrade="X"> line's need


def pick_weapons(slots, status, upgrades=()):
    """The weapons a unit holds under `status` with `upgrades` (the object's and its player's upgrade names): per
    slot the first line (a PRIMARY_WEAPON one before the rest) whose need bits are all set and forbid bits none set;
    one that cannot hurt or reach (the target painter) is no gun."""
    if upgrades:
        status = set(status) | {UPGRADE_BIT + u.lower() for u in upgrades}
    guns = []
    for s in slots:
        for need, forbid, prim, w in sorted(s, key=lambda e: not e[2]):
            if need <= status and not (forbid & status):
                if w and (w['dps'] > 0 or w.get('sdps', 0) > 0 or w.get('dot') or w.get('lift')) and w['range'] > 0:
                    guns.append(w)
                break
    return guns


def fight(template, own=None):
    """{hp, armor {damage type: percent}, weapons [{range, dps, type, anti}]} for a template (own: the mission's
    units' XML, read with the retail weapons and armours and their own weapons); hp None when the data has none."""
    d = _fight_data()
    if own and template in own:
        return read_fight(own[template], weapon_table(own), d['armors'])
    return d['units'].get(template.lower(), dict(hp=None, armor={}, weapons=[]))


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


def lifetime(template, own=None):
    """(frames, leaves) of a mission unit with a LifetimeUpdate, else (None, []): it is killed (its DeathType, not
    deleted) `frames` after the frame it was made -- the seconds x 15, cut down (bench 2026-11-07 engine_life: a 30 s
    wall 450 frames, a 5.5 s core 82); Min and Max apart: their middle (the game draws one between, a guess). leaves:
    what its CreateObjectDie lists for that death type make where it stood (the ice core's wall, born the frame the
    core dies). Retail templates are not read (none of our scripts makes one with a lifetime)."""
    xml = (own or {}).get(template)
    life = next(_blocks(xml, 'LifetimeUpdate'), None) if xml else None
    if life is None:
        return None, []
    lo, hi = _secs(_attr(life[0], 'MinLifetime')), _secs(_attr(life[0], 'MaxLifetime'))
    death = _attr(life[0], 'DeathType', 'NORMAL')
    frames = int((lo + hi) / 2 * LIFE_FPS + 1e-6)
    leaves = []
    for head, inner in _blocks(xml, 'CreateObjectDie'):
        if not _dies_of(next((h for h, _ in _blocks(inner, 'DieMuxData')), ''), death):
            continue
        ocl = _attr(head, 'CreationList')
        for h, body in _blocks(xml, 'ObjectCreationList'):
            if _attr(h, 'id') == ocl:
                leaves += re.findall(r'<CreateObject>\s*([^<\s]+)\s*</CreateObject>', body)
    return frames, leaves


_crush_memo = {}


def _chain(template, own, first):
    """Walk the template's XML up its inheritFrom chain (5 steps, as _inherited) calling first(xml) on each; the first
    non-None answer, else None."""
    xml = _xml(template, own)
    for _ in range(5):
        got = first(xml)
        if got is not None:
            return got
        up = parent(xml, template)
        if not up:
            break
        xml = retail_xml(template) if up.lower() == template.lower() else _xml(up, own)
        template = up
    return None


def crush(template, own=None):
    """(crusher, crushable): its CrusherInfo's CrusherLevel (0: crushes nothing) and CrushableLevel (None: cannot be
    crushed), each from the nearest template up the chain that writes it (a child's own number beats its base's:
    the Hammer's 20 over BaseVehicle's 10 -- docs/engine/crush.md, bench 11-06). Crushed when crusher > crushable,
    strictly (crush.md: 30 against 30 and 20 against 20 live)."""
    key = (template, (own or {}).get(template))
    if key not in _crush_memo:
        def level(attr):
            def read(xml):
                for head, _ in _blocks(xml or '', 'CrusherInfo'):
                    v = _attr(head, attr)
                    if v is not None:
                        return int(_num(v))
                return None
            return _chain(template, own, read)
        _crush_memo[key] = (level('CrusherLevel') or 0, level('CrushableLevel'))
    return _crush_memo[key]


_slow_memo = {}


def slow_death(template, own=None):
    """Seconds a body lies as a dying one after it is killed: the DestructionDelay of its plain SlowDeath (the module
    without DeathFlags -- the others are for named death types), 0 without one (a vehicle or building's DestroyDie
    takes it out at once). Bench 11-06 engine_crush: a crushed conscript (8.5 s) lay 127 frames, dying and in its
    spot; a plant killed by script was gone the next frame."""
    key = (template, (own or {}).get(template))
    if key not in _slow_memo:
        def read(xml):
            mods = list(_blocks(xml or '', 'SlowDeath'))
            if not mods:
                return None
            plain = [h for h, _ in mods if 'DeathFlags' not in h and 'DeathTypes' not in h]
            return _secs(_attr(plain[0], 'DestructionDelay')) if plain else 0.0
        _slow_memo[key] = _chain(template, own, read) or 0.0
    return _slow_memo[key]


_prop_memo = {}


def prop_body(template, own=None):
    """None unless its Body (nearest up the chain) is a PropBody; then 'dies' when a DestroyDie / SlowDeath up the
    chain takes a NORMAL death (a script kill), else 'stays'. Bench 11-10 engine_propbody a / b / c: a PropBody has no
    health (the percent reads 0, NAMED_DAMAGE 10 changes nothing), a Hammer told to attack never fires (UNATTACKABLE),
    and NAMED_KILL leaves a street segment (PropBody only) standing for good; a tree / lantern (SlowDeath only for
    TOPPLED) topples where it stands and is gone its ToppleUpdate delay + 1 frames later (61 / 121), never dying."""
    key = (template, (own or {}).get(template))
    if key not in _prop_memo:
        def body(xml):
            got = list(_blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'Body'))
            return ('<PropBody' in got[0][1]) if got else None

        def destroyer(xml):
            text = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
            for tag in ('DestroyDie', 'SlowDeath'):
                for _, inner in _blocks(text, tag):
                    if _dies_of(next((h for h, _ in _blocks(inner, 'DieMuxData')), ''), 'NORMAL'):
                        return True
            return None
        _prop_memo[key] = None if not _chain(template, own, body) else \
            ('dies' if _chain(template, own, destroyer) else 'stays')
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


_death_memo, _weapon_blocks = {}, None


def death_weapons(template, own=None, death='NORMAL', scalars=False):
    """[(damage, damage type, radius, delay s, affects)] -- each DamageNugget of each FireWeaponWhenDead's DeathWeapon
    (InitiallyActive, its DieMuxData taking the death type) from the nearest template up the chain that has the module:
    the weapon goes off where the body died, `delay` after (the nugget's DelayTimeSeconds), hurting what of `affects`
    (RadiusDamageAffects: ALLIES ENEMIES NEUTRALS, relative to the dead one's owner) lies within the radius, centre to
    centre. Bench 11-05 engine_spawn_refill: S02_ExplodingMig (1000 GRENADE, 100, .3 s) killed by script takes the
    Guardian 40 + 69 off its centre with it. INFERRED: no falloff inside the radius (the game's DamageNugget has none
    without DamageArc / a ScalarFalloff), SpecialObjectFilter not read, an upgrade-activated module (InitiallyActive
    false) never fires."""
    global _weapon_blocks
    key = (template, (own or {}).get(template), death)
    if key in _death_memo:
        return _death_memo[key] if scalars else [d[:5] for d in _death_memo[key]]
    if _weapon_blocks is None:
        _weapon_blocks = {}
        for text in _weapon_files():
            for head, body in _blocks(re.sub(r'<!--.*?-->', '', text, flags=re.S), 'WeaponTemplate'):
                _weapon_blocks.setdefault(_attr(head, 'id'), (head, body))
    mine = {}
    for text in (own or {}).values():
        for head, body in _blocks(text or '', 'WeaponTemplate'):
            mine[_attr(head, 'id')] = (head, body)

    def read(xml):
        mods = list(_blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'FireWeaponWhenDead'))
        return mods or None
    out = []
    for head, inner in _chain(template, own, read) or []:
        if (_attr(head, 'InitiallyActive') or 'false').lower() != 'true':
            continue
        if not _dies_of(next((h for h, _ in _blocks(inner, 'DieMuxData')), ''), death):
            continue
        whead, wbody = mine.get(_attr(head, 'DeathWeapon')) or _weapon_blocks.get(_attr(head, 'DeathWeapon'), ('', ''))
        affects = frozenset((_attr(whead, 'RadiusDamageAffects') or 'ENEMIES NEUTRALS').split())
        for nh, nb in _blocks(wbody, 'DamageNugget'):
            out.append((_num(_attr(nh, 'Damage'), 0.0), _attr(nh, 'DamageType') or '', _num(_attr(nh, 'Radius'), 0.0),
                        _secs(_attr(nh, 'DelayTimeSeconds') or '0s'), affects, _ally_scalar(nb)))
    _death_memo[key] = out
    return [d[:5] for d in out] if not scalars else out


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


def air_wrecks(template, own=None):
    """What an aircraft killed in the air leaves (Physics P5, checks/engine_crash_fall.py): (choose_one, [wreck]) from
    the CreateObjectDie that takes an airborne death (RequiredStatus AIRBORNE_TARGET, or ExemptStatus
    PARKED_AT_AIRFIELD, or no status at all), None without one. A wreck: dict(template, scale = the OCL's VelocityScale
    of the plane's velocity (INHERIT_VELOCITY), gravity = its own Physics GravityMultiplier (default 1), falls =
    KillWhenRestingOnGround, weapons = its FireWeaponWhenDead (death_weapons with scalars)). The Apollo's: CHOOSE_ONE of
    AlliedFighterAircraft_Collapse (debris, no weapon) and AlliedFighterAircraft_Dying (x 0.5, falls, 150 EXPLOSIVE
    radius 20, allies 50 %)."""
    key = (template, (own or {}).get(template))
    if key in _wreck_memo:
        return _wreck_memo[key]

    def read(xml):
        text = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)
        mods = list(_blocks(text, 'CreateObjectDie'))
        if not mods:
            return None
        for head, inner in mods:
            req = re.search(r'RequiredStatus="([^"]*)"', inner)
            exempt = re.search(r'ExemptStatus="([^"]*)"', inner)
            if req and 'AIRBORNE_TARGET' not in req.group(1).split():
                continue
            if exempt and 'AIRBORNE_TARGET' in exempt.group(1).split():
                continue
            return _attr(head, 'CreationList')
        return ''
    name = _chain(template, own, read)
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
                               weapons=death_weapons(w, own, scalars=True)))
    _wreck_memo[key] = ('CHOOSE_ONE' in (_attr(head, 'Flags') or ''), wrecks)
    return _wreck_memo[key]


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
    return open(p, encoding='utf-8', errors='replace').read() if p else ''


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
                     and not _attr(head, 'ReplaceWith')
                     and _attr(head, 'id') != 'ModuleTag_EngineerContainBridge')
        return dict(enabled=_attr(head, 'ImmediatelyEnabled', 'false').lower() == 'true',
                    allowed=allowed, relations=relations, supported=supported,
                    status=frozenset(_attr(head, 'ObjectStatusToSet', 'NO_REFUND').split()))
    return _chain(template, own, read)


def deposit(template, own=None):
    """(bonus, amount, frames) of an AutoDepositUpdate (the oil derrick: 500 when taken, 15 every 2 s), else None.
    When it pays (Generals' AutoDepositUpdate, R4): the capture pays the bonus and sets the next deposit `frames` on;
    then `amount` every `frames` while a player (not the neutral side) holds it; frames = seconds x 15, cut down."""
    if own and template in own:
        return _deposit_of(own[template])
    if template.lower() not in _deposits:
        _deposits[template.lower()] = _deposit_of(retail_xml(template))
    return _deposits[template.lower()]


_deposits = {}


def _deposit_of(xml):
    head, inner = next(_blocks(xml, 'AutoDepositUpdate'), (None, ''))
    if head is None:
        return None
    bonus = re.search(r'<InitialCaptureBonus[^>]*Amount="([\d.]+)"', inner)
    amount = re.search(r'<Deposit\b[^>]*Amount="([\d.]+)"', inner)
    return (float(bonus.group(1)) if bonus else 0.0, float(amount.group(1)) if amount else 0.0,
            int(_secs(_attr(head, 'DepositInterval', '0s')) * LIFE_FPS + 1e-6))


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
    return next((module for module in modules if module['SpecialPowerTemplate'] == power), None)


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
        body = xml or retail_xml(template)
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


def assigned_repair_rate(template, command, own=None):
    """E67 explicit dispatch only; retail drone configuration, no allocation model.

    Custom drone XML/dispatch flags remain unmeasured. The rate comes from the
    retail passive healing module, rather than the observed final percentage.
    """
    power = command_power(command, own)
    if power != 'SpecialPower_TargetedRepairVehicle':
        return None
    def read(xml):
        blocks = list(_blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S),
                              'AssignSlavesTargetObjectSpecialPower'))
        if not blocks:
            return None
        return any(not inner.strip() and _attr(head, 'SpecialPowerTemplate') == power
                   and set(re.findall(r'(\w+)\s*=', head)) == {'id', 'SpecialPowerTemplate'}
                   for head, inner in blocks)
    if not _chain(template, own, read) or not spawn_modules(template, own):
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

    Return (radius, fraction/second) only for the measured complete module shape.
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
        return (value, .1) if value == 100 else False

    return _chain(template, own, read)


def spawn_modules(template, own=None):
    """Nearest SpawnBehavior group; only the engine_spawn repair-drone configuration is supported.

    Compare the complete subtree so new flags or child variants remain explicit gaps.
    Even the supported configuration only implements initial burst, death refill and parent removal.
    """
    import xml.etree.ElementTree as ET

    expected = dict(SpawnNumberData='3', InitialBurst='3', SpawnReplaceDelayData='10s',
                    SpawnedRequireSpawner='true', KillSpawnsOnCaptured='true',
                    SpawnInsideBuilding='true', KillSpawnsOnDisabled='true')

    def read(xml):
        out = {}
        for head, inner in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'SpawnBehavior'):
            try:
                node = ET.fromstring('<SpawnBehavior ' + head + '>' + inner + '</SpawnBehavior>')
            except ET.ParseError:
                out[_attr(head, 'id', '')] = None
                continue
            attrs = dict(node.attrib)
            mid = attrs.pop('id', '')
            children = [(c.tag, dict(c.attrib), (c.text or '').strip(), len(c)) for c in node]
            valid = attrs == expected and children == [
                ('Die', {'DeathTypes': 'ALL'}, '', 0),
                ('SpawnTemplate', {}, 'AlliedWarFactoryRepairDrone', 0)]
            out[mid] = 'AlliedWarFactoryRepairDrone' if valid else None
        return out or None

    return _chain(template, own, read) or {}


UNPACK_SPAWN = dict(SpawnNumberData='1', SpawnReplaceDelayData='9999s', IsOneShotData='true', FadeInTime='1.0s',
                    SpawnOnUnpack='true', CanReclaimOrphans='false', SetPurchasePrice='true')


def unpack_spawn(template, own=None):
    """{module id: the one unit it makes} for the nearest SpawnBehavior group's refinery configuration (all three
    nations' refineries: one collector on unpacking, one-shot, never replaced -- UNPACK_SPAWN, exactly, one
    SpawnTemplate). Anything else (more attributes, more children) is not this and stays spawn_modules' gap.
    Bench 2026-11-12 checks/engine_mining.py mineturn<k> / mineniag p: a refinery the map places pays without a
    collector placed (the placed one deleted at the start) -- it gives its own."""
    import xml.etree.ElementTree as ET

    def read(xml):                          # the nearest level with SpawnBehavior answers, as spawn_modules
        out, seen = {}, False
        for head, inner in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'SpawnBehavior'):
            seen = True
            try:
                node = ET.fromstring('<SpawnBehavior ' + head + '>' + inner + '</SpawnBehavior>')
            except ET.ParseError:
                continue
            attrs = dict(node.attrib)
            mid = attrs.pop('id', '')
            kids = [(c.tag, dict(c.attrib), (c.text or '').strip(), len(c)) for c in node]
            if attrs == UNPACK_SPAWN and len(kids) == 1 and kids[0][:2] == ('SpawnTemplate', {}) \
                    and kids[0][2] and not kids[0][3]:
                out[mid] = kids[0][2]
        return out if seen else None

    return _chain(template, own, read) or {}


def attach_modules(template, own=None):
    """Nearest AttachUpdate group: direct teleport/stick/status subset (engine_attach a).

    Unsupported modules stay False, so recognizing an id cannot silently
    implement leech, death, repair, idle-detach or autonomous scanning.
    Multiple inherited module groups and distance boundaries are unbenched.
    """
    def read(xml):
        out = {}
        for h, inner in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'AttachUpdate'):
            flags = set(_attr(h, 'Flags', 'STICK_TO_PARENT TELEPORT USE_GEOMETRY').split())
            mid = _attr(h, 'id')
            if (inner.strip() or not {'STICK_TO_PARENT', 'TELEPORT'} <= flags
                    or flags - {'STICK_TO_PARENT', 'TELEPORT', 'ONE_ATTACH_PER_PARENT'}
                    or set(re.findall(r'(\w+)\s*=', h)) - {'id', 'Flags', 'Range', 'CloseEnoughRange', 'ParentStatus', 'AttachedObjectStatus'}):
                out[mid] = False
            else:
                out[mid] = dict(flags=flags, range=_num(_attr(h, 'Range')),
                                child=set(_attr(h, 'AttachedObjectStatus', '').split()) | {'ATTACHED'},
                                parent=set(_attr(h, 'ParentStatus', '').split()))
        return out or None
    return _chain(template, own, read) or {}


def nugget_disguise_power(template, power, own=None):
    """engine_spndisguise: retail direct-hit DISGUISED bit only.

    Identity, rendering, enemy acquisition, retargeting and cancellation remain
    gaps. Reject unmeasured handler/power shapes rather than treating them as buffs.
    """
    def handler(xml):
        for h, inner in _blocks(re.sub(r'<!--.*?-->', '', xml or '', flags=re.S), 'SpecialDisguiseUpdate'):
            if _attr(h, 'SpecialPowerTemplate') == power:
                node = ET.fromstring('<SpecialDisguiseUpdate ' + h + '/>')
                attrs = dict(node.attrib)
                attrs.pop('id', None)
                return not inner.strip() and attrs == dict(
                    SpecialPowerTemplate=power, TriggerInstantlyOnCreate='false',
                    OpacityTarget='0.5', DisguiseFX='FX_None')
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
        if (set(node.attrib) - {'id', 'TargetType', 'InitiateSound', 'Flags', 'WaypointModeTerminal'}
                or node.get('TargetType') != 'OBJECT'
                or set(node.get('Flags', '').split()) != {
                    'NEEDS_OBJECT_FILTER', 'DO_NOT_REACQUIRE_TARGET', 'CAN_NOT_BE_SCRAMBLED'}
                or node.get('WaypointModeTerminal') != 'false' or len(node) != 1):
            return False
        f = node[0]
        if (f.tag != 'ObjectFilter' or dict(f.attrib) != dict(
                Rule='ANY', Relationship='ALLIES ENEMIES NEUTRAL', Include='INFANTRY')
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
                if power == 'SpecialPower_InfantryDisguise':
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


def toggle_modules(xml):
    """The template's ToggleStatusSpecialAbilityUpdate modules, in order: [{power, pack, unpack (seconds), states:
    [{status: set, modifier: id or None}]}]. A press moves a module to its next state, modulo the count (work/re
    l2_ability.md 3: the old state's ObjectStatus / AttributeModifier off, the new one's on); the first state holds
    from the start; disabled: the state's DisabledType (engine_toggle d / f: a script press then does nothing).
    ModelConditions / ArmorSet / LocomotorSet are not read here."""
    out = []
    xml = re.sub(r'<!--.*?-->', '', xml or '', flags=re.S)        # retail keeps old ToggleStates in comments
    for head, inner in _blocks(xml, 'ToggleStatusSpecialAbilityUpdate'):
        states = [dict(status=set((_attr(h, 'ObjectStatus') or '').split()), modifier=_attr(h, 'AttributeModifier'),
                       disabled=_attr(h, 'DisabledType'))
                  for h, _ in _blocks(inner, 'ToggleState')]
        if states:
            out.append(dict(power=_attr(head, 'SpecialPowerTemplate'), pack=_secs(_attr(head, 'PackTime') or '0s'),
                            unpack=_secs(_attr(head, 'UnpackTime') or '0s'), states=states))
    return out


def template_toggles(template, own=None, depth=0):
    """toggle_modules of the template, else of what it inherits from (retail's CampaignOverrides.xml redefines the
    Hammer as inheriting from itself: its parent is then the retail file)."""
    xml = _xml(template, own)
    found = toggle_modules(xml)
    parent = _attr(re.match(r'<GameObject\b[^>]*>', xml).group(0), 'inheritFrom') if xml.startswith('<GameObject') else None
    if found or not parent or depth > 4:
        return found
    if parent.lower() == template.lower():
        return toggle_modules(retail_xml(template))
    return template_toggles(parent, own, depth + 1)


def status_bits(xml, upgrades):
    """(set, clear): the bits the held upgrades' StatusBitsUpgrade modules set and clear (Generals StatusBitsUpgrade:
    on upgrade sets StatusToSet, clears StatusToClear; INFERRED for RA3, not on the bench)."""
    on, off = set(), set()
    for head, inner in _blocks(xml or '', 'StatusBitsUpgrade'):
        if _triggers(inner) & set(upgrades):
            on |= set((_attr(head, 'StatusToSet') or '').split())
            off |= set((_attr(head, 'StatusToClear') or '').split())
    return on, off


def auras(xml):
    """The object's AttributeModifierAuraUpdate modules: [{'mod', 'range', 'refresh' (frames), 'relation' (set of
    ALLIES / ENEMIES / NEUTRAL, against the aura's owner), 'include' / 'exclude' (KindOf sets; include empty = any),
    'active' (InitiallyActive), 'needs' (RequiredObjectStatusFlags the aura object must have: the jammer's toggle),
    'self' (AllowSelf)}]. Bench upgrades.md 5 (the stasis zone): Range 200, refresh 0.25 s, the modifier's Duration 1 s
    -- whoever is within stops, and is free within 1 s of the object's going or of leaving the circle."""
    out = []
    for head, inner in _blocks(xml or '', 'AttributeModifierAuraUpdate'):
        f, _ = next(_blocks(inner, 'ObjectFilter'), ('', ''))
        out.append({'mod': _attr(head, 'AttributeModifierName'), 'range': _num(_attr(head, 'Range'), 0.0),
                    'refresh': max(1, int(round(_secs(_attr(head, 'RefreshDelay', '1s')) * LIFE_FPS))),
                    'relation': set((_attr(f, 'Relationship') or 'ALLIES ENEMIES NEUTRAL').split()),
                    'include': set((_attr(f, 'Include') or '').split()),
                    'exclude': set((_attr(f, 'Exclude') or '').split()),
                    'active': (_attr(head, 'InitiallyActive', 'true') or 'true').lower() != 'false',
                    'needs': set((_attr(head, 'RequiredObjectStatusFlags') or '').split()),
                    'self': (_attr(head, 'AllowSelf', 'false') or '').lower() == 'true'})
    return [a for a in out if a['mod']]


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


def _xml(template, own=None):
    """The template's own XML: a mission's, else its GameObject in the file the SageXML index names (a file may hold
    several, AlliedAntiInfantryVehicle.xml the Riptide's two), else the file of its own name. A mission file may also
    hold another GameObject (engine_dynamics: a copy of BaseVehicle the unit inherits): the unit's text leaves the
    others out, and a template defined only inside a mission file is that GameObject."""
    global _index
    if (own or {}).get(template):
        return _own_only(own[template], template)
    for text in (own or {}).values():
        for m in re.finditer(r'<GameObject\b.*?</GameObject>', text or '', re.S):
            if re.search(rf'\bid="{re.escape(template)}"', re.match(r'<GameObject\b[^>]*>', m.group(0)).group(0), re.I):
                return m.group(0)
    if _index is None:
        _index = {k.lower(): v for k, v in json.load(open(INDEX, encoding='utf-8')).items()} \
            if os.path.exists(INDEX) else {}
    f = (_index.get(template.lower()) or {}).get('file', '')
    path = os.path.join(SAGEXML, *f[5:].split('/')) if f.startswith('DATA:') else ''
    if path and os.path.exists(path):
        text = open(path, encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'<GameObject\b.*?</GameObject>', text, re.S):
            if re.search(rf'\bid="{re.escape(template)}"', m.group(0)[:2000], re.I):
                return m.group(0)
    return retail_xml(template)


def _own_only(text, template):
    """A mission unit's file without the GameObjects that are not `template` (its includes, weapons and the rest kept)."""
    def keep(m):
        head = re.match(r'<GameObject\b[^>]*>', m.group(0)).group(0)
        return m.group(0) if re.search(rf'\bid="{re.escape(template)}"', head, re.I) else ''
    return re.sub(r'<GameObject\b.*?</GameObject>', keep, text, flags=re.S) if text.count('<GameObject') > 1 else text


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
    """read(xml) of the template, else of what it inherits from (inheritFrom), up to 5 steps. A campaign override
    (CampaignOverrides.xml: the same id inheriting itself) is read first, then the file of the template's own name."""
    xml = _xml(template, own)
    for _ in range(5):
        got = read(xml)
        if got != empty:
            return got
        up = parent(xml, template)
        if not up:
            break
        xml = retail_xml(template) if up.lower() == template.lower() else _xml(up, own)
        template = up
    return empty


def command_set(structure, upgrades=(), own=None):
    """The structure's CommandSet: its own, or the last CommandSetUpgrade's whose TriggeredBy it holds (AlliedConstruction
    Yard: ...Level2 once it holds Upgrade_AlliedTech2, its button then buys Tech3)."""
    def read(xml):
        bare = re.sub(r'<CommandSetUpgrade\b.*?(/>|</CommandSetUpgrade>)', '', xml, flags=re.S)
        base = (re.findall(r'\bCommandSet="([^"]+)"', bare) or [None])[0]
        swaps = [(_attr(h, 'CommandSet'), set(re.findall(r'<TriggeredBy>\s*([^<\s]+)', i)))
                 for h, i in _blocks(xml, 'CommandSetUpgrade')]
        return (base, swaps) if base or swaps else None
    base, swaps = _inherited(structure, own, read, None) or ('', [])
    held = {u.lower() for u in upgrades}
    for cs, trig in swaps:
        if cs and trig and {t.lower() for t in trig} <= held:
            base = cs
    return base or ''


def menu(factory, own=None, upgrades=()):
    """The units a structure builds: its CommandSet's UNIT_BUILD commands' objects, in the sidebar's order."""
    sets, cmds = _commands(own)
    return [cmds[c][1] for c in sets.get(command_set(factory, upgrades, own), [])
            if cmds.get(c, ('', None))[0] == 'UNIT_BUILD' and cmds[c][1]]


def build_button(factory, template, own=None, upgrades=()):
    """The factory's UNIT_BUILD command that builds `template` (Command_ConstructAlliedEngineer), None when its
    CommandSet has none (the other way: built)."""
    sets, cmds = _commands(own)
    return next((c for c in sets.get(command_set(factory, upgrades, own), [])
                 if cmds.get(c, ('', None)) == ('UNIT_BUILD', template)), None)


def built(factory, button, own=None, upgrades=()):
    """The template the factory's `button` builds (a UNIT_BUILD command of its CommandSet), else None."""
    sets, cmds = _commands(own)
    if button not in sets.get(command_set(factory, upgrades, own), []):
        return None
    kind, obj = cmds.get(button, ('', None))
    return obj if kind == 'UNIT_BUILD' else None


def upgrade_menu(structure, own=None, upgrades=()):
    """The upgrades a structure's buttons buy (OBJECT_UPGRADE: the structure's own; PLAYER_UPGRADE: the player's), as
    [(upgrade, 'OBJECT' | 'PLAYER')] in the sidebar's order."""
    sets, cmds = _commands(own)
    out = []
    for c in sets.get(command_set(structure, upgrades, own), []):
        kind, up = cmds.get(c, ('', None))
        if kind in ('OBJECT_UPGRADE', 'PLAYER_UPGRADE') and up:
            out.append((up, kind.split('_')[0]))
    return out


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
        if os.path.exists(p):
            out.append(open(p, encoding='utf-8', errors='replace').read())
    return '\n'.join(out)


def tech_receivers(structure, own=None):
    """The structure's TechUpgradeReceiver modules: [(upgrades in lower case, radius, rectangular?, {source templates
    in lower case})] -- an Allied factory takes Upgrade_AlliedTech2 / 3 from a yard or outpost holding it within 600
    (RECTANGULAR; AlliedTechUpgradeReceiverLevel2/3.xml)."""
    def read(xml):
        out = []
        for h, i in _blocks(_with_includes(xml), 'TechUpgradeReceiver'):
            out.append(({t.lower() for t in re.findall(r'<TriggeredBy>\s*([^<\s]+)', i)}, _num(_attr(h, 'Radius'), 0.0),
                        (_attr(h, 'DistanceType', '') or '').upper() == 'RECTANGULAR',
                        {t.lower() for t in re.findall(r'<IncludeThing>\s*([^<\s]+)', i)}))
        return out or None
    return _inherited(structure, own, read, None) or []


def production(template, own=None):
    """(cost, seconds): BuildCost Amount and BuildTime of the template's XML ((0, 0.0) where it writes none)."""
    def read(xml):
        cost = re.search(r'<BuildCost\b[^>]*\bAmount="([\d.]+)"', xml)
        secs = re.search(r'\bBuildTime="([\d.]+)"', xml)
        return int(float(cost.group(1))) if cost else 0, float(secs.group(1)) if secs else 0.0
    return _inherited(template, own, read, (0, 0.0))


def energy(template, own=None):
    """EnergyProduction of the template (0 where it writes none): > 0 supplies the owner's power, < 0 is its demand."""
    def read(xml):
        m = re.search(r'\bEnergyProduction="(-?[\d.]+)"', xml)
        return int(float(m.group(1))) if m else None
    return _inherited(template, own, read, None) or 0


def unpack_frames(template, own=None):
    """StructureUnpackUpdate's UnpackTime x 15 rounded (RA3 1.13, work/re/l2_construction.md: F = round(UnpackTime x 15)); 0 where it
    has none. A '=$NAME' value is the define of the template's file (SovietPowerPlant: 10 s) or GlobalDefines."""
    def read(xml):
        head, _ = next(_blocks(xml, 'StructureUnpackUpdate'), (None, ''))
        return _attr(head, 'UnpackTime') if head else None
    v = _inherited(template, own, read, None)
    if not v:
        return 0
    if v.startswith('=$'):
        _xml(template, own)                     # loads the index
        f = (_index.get(template.lower()) or {}).get('file', '')
        path = os.path.join(SAGEXML, *f[5:].split('/')) if f.startswith('DATA:') else ''
        text = open(path, encoding='utf-8', errors='replace').read() if path and os.path.exists(path) else ''
        g = dict(DEFINE.findall(open(GLOBAL_DEFINES, encoding='utf-8', errors='replace').read())) \
            if os.path.exists(GLOBAL_DEFINES) else {}
        v = {**g, **dict(DEFINE.findall(text))}.get(v[2:], '')
    return int(round(_secs(v.lstrip('=')) * LIFE_FPS))


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


def special_weapon(weapon, own=None):
    """What a special ability's weapon does where it goes off (weapon_fire_ability): dict(affects (RadiusDamageAffects),
    damage [(damage, type, radius, delay s)] from its DamageNuggets, paralyze [dict(kind (ParalyzeType), radius,
    seconds, include (KindOf), relation, exclude (templates, lower), forbidden_upgrade)] from its ParalyzeNuggets, the
    one SpecialObjectFilter each). Not read: MetaImpactNugget (the blast's shockwave: a push, gap)."""
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
               paralyze=[])
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
            forbidden_upgrade=forbidden[0] if forbidden else ''))
    return out


def needs(template, own=None):
    """(objects, upgrades) its GameDependency asks for: every RequiredObject the player must own, every NeededUpgrade
    the player must hold (all of them: inference, the sidebar's lit buttons not measured)."""
    def read(xml):
        head, inner = next(_blocks(xml, 'GameDependency'), (None, ''))
        return (re.findall(r'<RequiredObject>\s*([^<\s]+)', inner or ''),
                re.findall(r'<NeededUpgrade>\s*([^<\s]+)', inner or ''))
    return _inherited(template, own, read, ([], []))


def exit_of(factory, own=None):
    """(create, rally, door frames) of a factory: UnitCreatePoint and NaturalRallyPoint (x, y) in its own frame (rally
    None where it writes none), and ProductionUpdate's DoorOpeningTime in frames, rounded up (0.66 s -> 10: bench
    2026-11-05 engine_production, every unit appeared 10 frames after its build was full)."""
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
    return _inherited(factory, own, read, None) or ((0.0, 0.0), None, 0)
