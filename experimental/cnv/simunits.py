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

CACHE = os.path.join(labpaths.WORK, 'sim_units_v4.json')     # v2: defines resolved (2026-10-29); v3: + ShroudClearingHeight;
                                                            # v4: + radius (R8)
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
                shroud=number(text, 'ShroudClearingRange'), kinds=sorted(kinds),
                clear_height=number(text, 'ShroudClearingHeight'), radius=radius(text))


def radius(text):
    """R8: the bounding circle radius of a unit's Geometry (its first Shape): a BOX's corner, sqrt(major^2 + minor^2);
    a CYLINDER's or SPHERE's MajorRadius (Generals GeometryInfo::calcBoundingStuff). The weapon reach is measured
    between these circles (sim.Sim.in_range). None when the XML has no Shape."""
    g = re.search(r'<Geometry\b.*?</Geometry>', text, re.S)
    m = re.search(r'<Shape\b(.*?)/?>', g.group(0) if g else '', re.S)
    if not m:
        return None
    a = m.group(1)
    kind = re.search(r'\bType="([^"]+)"', a)
    major, minor = (re.search(rf'\b{n}="([\d.]+)"', a) for n in ('MajorRadius', 'MinorRadius'))
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


def power_rules(template, power, own=None):
    """The SpecialPowerTemplate for `power` of unit `template`: {'reload': frames (ReloadTime x 15, rounded twice --
    RA3 1.13 0x863050, docs/engine/specialpower.md 1 -- at least 1), 'forbidden': ForbiddenObjectRange, 'flags': set of
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


def kind_of(kinds):
    for k in ('STRUCTURE', 'AIRCRAFT', 'SHIP', 'INFANTRY', 'VEHICLE'):
        if k in kinds:
            return k
    return ''


def speed_scale(xml, upgrades):
    """The factor the SPEED modifiers of the upgrades a unit holds multiply its speed by, read from its own XML
    (AttributeModifierUpgrade ... TriggeredBy -> AttributeModifier -> Modifier Type="SPEED" Value="N%"): units/pace.py's."""
    scale = 1.0
    if not xml or not upgrades:
        return scale
    for head, inner in _blocks(xml, 'AttributeModifierUpgrade'):
        triggers = set(re.findall(r'<TriggeredBy>([^<]*)</TriggeredBy>', inner or ''))
        triggers = {t for x in triggers for t in x.split()}
        mod = _attr(head, 'AttributeModifier')
        if not triggers & set(upgrades) or not mod:
            continue
        for mh, mi in _blocks(xml, 'AttributeModifier'):
            if _attr(mh, 'id') == mod:
                for v in re.findall(r'<Modifier\s+Type="SPEED"\s+Value="([\d.]+)%"', mi or ''):
                    scale *= float(v) / 100.0
    return scale


def stats(template, own=None):
    """{speed, surface, vision, shroud, kinds, radius, guessed} for a template; own: {id: xml text} of the mission's units."""
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
    if e.get('clear_height') is None:
        e['clear_height'] = CLEAR_HEIGHT
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
    several, AlliedAntiInfantryVehicle.xml the Riptide's two), else the file of its own name."""
    global _index
    if (own or {}).get(template):
        return own[template]
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


def _inherited(template, own, read, empty):
    """read(xml) of the template, else of what it inherits from (inheritFrom), up to 5 steps. A campaign override
    (CampaignOverrides.xml: the same id inheriting itself) is read first, then the file of the template's own name."""
    xml = _xml(template, own)
    for _ in range(5):
        got = read(xml)
        if got != empty:
            return got
        m = re.search(r'\binheritFrom="([^"]+)"', xml[:2000])
        if not m:
            break
        xml = retail_xml(template) if m.group(1).lower() == template.lower() else _xml(m.group(1), own)
        template = m.group(1)
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


def upgrade_type(upgrade):
    """'OBJECT' (an object holds it: the tiers), 'PLAYER' (the player holds it) or '' (not in upgrade.xml)."""
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
    """StructureUnpackUpdate's UnpackTime x 15 rounded (RA3 1.13 0x720100: F = round(UnpackTime x 15)); 0 where it
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
