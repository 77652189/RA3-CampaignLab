r"""What the plan simulator does not understand, per level -- so that "meets something it does not know and says nothing"
shows up by itself (user 2026-11-08: the player-style runs of A3 A6 A7 A9 J7 found five gaps -- a ball's INVULNERABLE bit,
an OCL weapon read as no weapon, the time-stop zone, a unit firing for ever at what it cannot hurt, no capture order --
that the quick `win` check had hidden).

For every level as built (build.LEVELS, the level as played: no check's scripts) it lists what the level makes and the
simulator (sim.py, simunits.py, simproxy.py: read here, never changed) does not model. Nothing is run -- only the levels
are compiled and a probe Sim is poked (about 10 s for all of them). Six kinds of item:

  武器          a template in the level whose XML declares a weapon, and simunits.fight() reads it as none (an OCL
                nugget -- orbital strike, spawn -- no damage block, a weapon template not found, a unit the table lacks)
  升级          AttributeModifier effects other than SPEED-through-an-upgrade (INVULNERABLE, RANGE ... and the status bits
                a modifier sets), upgrade modules the simulator does not read, and retail upgrades a script gives whose
                effect it does not apply
  脚本动作      an action name no part of the run handles -- not the engine model's core, not a Sim.act branch (found by
                calling Sim.act with the script's own arguments: an unknown name lands in Sim.unknown), not shown on the
                timeline; also an action refined by what it is told (a status bit, a special power, a command button)
  脚本动作(忽略)  names sim.IGNORED drops on purpose: may hide play
  脚本条件      a condition name Sim.cond does not know (it reads false)
  设备          a device's mechanism (MECHANISMS below: the table is the register, each with its source) whose probe
                finds no code in sim.py / simunits.py / simproxy.py
  命令          orders the player gives that simproxy cannot issue (capture, stop, guard, stance), and the abilities of the
                player's units that order_power / simproxy only log
  对打不动      a pair (shooter, target) where the shooter's every weapon that may fire at the target does nothing to it:
                the fight model fires at it for ever (found by putting the two in a bare Sim and running Sim.fight)

KNOWN (below) is the register of gaps already known: key (category, name) for every level, or (level, category, name) for
one; each with owner, repro and note. tests/test_simcoverage.py: the items must all be KNOWN, and a KNOWN entry no item
matches is stale (delete it) -- so a new unmodelled thing turns the test red.

  python -I -X utf8 experimental/cnv/simcoverage.py [<level> ...] [--verbose]
"""
import argparse
import ast
import dataclasses
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import parts  # noqa: E402
import sim  # noqa: E402
import simunits  # noqa: E402

WEAPON, UPGRADE, ACTION, IGNORED_ACTION, CONDITION, DEVICE, COMMAND, STUCK = (
    '武器', '升级', '脚本动作', '脚本动作(忽略)', '脚本条件', '设备', '命令', '对打不动')
CATEGORIES = (WEAPON, UPGRADE, ACTION, IGNORED_ACTION, CONDITION, DEVICE, COMMAND, STUCK)
PROBE_LEVEL = 'a1'                      # the level the probe Sim is made of (any one does)
PLAYS = os.path.join(HERE, 'plays')
CREATES = ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION')


@dataclasses.dataclass(frozen=True)
class Item:
    level: str
    category: str
    name: str
    text: str = dataclasses.field(default='', compare=False)

    def line(self):
        return f'{self.category} | {self.name} | {self.text}'


# ---- what the simulator's code contains, read off its source (never imported strings: docstrings and comments do not count)
def code_strings(path):
    """Every string constant of a module's code, docstrings left out (a comment is not in the tree at all)."""
    tree = ast.parse(open(path, encoding='utf-8').read())
    docs = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
    return {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docs}


_code = {}


def sim_code():
    """The string constants of sim.py, simunits.py, simproxy.py -- the three files the player-style run is made of."""
    if not _code:
        _code['all'] = set().union(*(code_strings(os.path.join(HERE, f)) for f in ('sim.py', 'simunits.py',
                                                                                   'simproxy.py')))
    return _code['all']


def status_modelled():
    """The object statuses sim.py acts on (a `'X' in b.status` test)."""
    src = open(os.path.join(HERE, 'sim.py'), encoding='utf-8').read()
    return set(re.findall(r"'([A-Z_]+)' (?:not )?in \w+\.status", src))


def issuable_kinds():
    """The order kinds simproxy's SimWorld.issue gives (`o.kind == 'x'` / `o.kind in (...)`): what a player proxy can do."""
    tree = ast.parse(open(os.path.join(HERE, 'simproxy.py'), encoding='utf-8').read())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'issue')
    kinds = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Compare) and isinstance(n.left, ast.Attribute) and n.left.attr == 'kind':
            for c in n.comparators:
                kinds |= {x.value for x in ast.walk(c) if isinstance(x, ast.Constant) and isinstance(x.value, str)}
    return kinds


# ---- what a level makes
@dataclasses.dataclass
class Info:
    name: str
    m: object
    mm: object
    own: dict                           # unit id -> XML (the mission's own units)
    human: str
    places: list                        # (template, owner, how) of everything the level puts in or makes
    templates: set
    human_templates: set
    actions: dict                       # action name -> [args of each use]
    conds: dict
    plan: dict


def strings_of(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, (tuple, list)):
        for y in x:
            yield from strings_of(y)


def template_exists(name, own):
    if name in own:
        return True
    if not re.fullmatch(r'\w+', name):
        return False
    simunits.retail_xml('x')            # builds the file index
    return name.lower() in simunits._retail_files and '<GameObject' in simunits.retail_xml(name)


def canon(name, own):
    """A template's name in the case of its file (a script may write it in lower case)."""
    if name in own or not re.fullmatch(r'\w+', name or ''):
        return name
    simunits.retail_xml('x')
    p = simunits._retail_files.get(name.lower())
    return os.path.basename(p)[:-4] if p else name


_infos = {}


def info(name):
    if name in _infos:
        return _infos[name]
    import build
    m, t, _ = build.resolve(name, '')
    mm = parts.merged(m, t)
    own = {u.id: u.xml for u in mm.units}
    players = dict(m.map.PLAYERS)
    human = players['p1']
    civ = sim.CIV
    places = []
    for o in list(getattr(m.map, 'OBJECTS', [])) + list(mm.objects):
        places.append((o.template, players.get(o.side, civ), 'placed'))
    for k, r in m.cast.items():
        places.append((r.template, players.get(r.side, civ), 'cast'))
    actions, conds = {}, {}
    for s in mm.scripts:
        for c in s.when:
            c = list(c)
            if c and c[-1] == parts.NOT:
                c = c[:-1]
            conds.setdefault(c[0], []).append(c[1:])
        for a in s.do:
            actions.setdefault(a[0], []).append(list(a[1:]))
            if a[0] in CREATES:
                places.append((a[2], a[3].split('/')[0], 'made by a script'))
    plan_file = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'docs', 'story', 'plans', f'{name}.md')
    plan = {}
    if os.path.exists(plan_file):
        import plan as planmod
        plan = planmod.load(name)
    play = os.path.join(PLAYS, f'{name}.txt')
    if os.path.exists(play):
        for e in sim.parse_script(play):
            if len(e) > 2 and e[1] == '造':
                what = e[2]
                tmpl = next((u.id for u in mm.units if u.id == what), None) or \
                    next((r.template for k, r in m.cast.items() if k == what), what)
                places.append((tmpl, human, 'the player makes it (plays/)'))
    places = [(canon(t, own), o, how) for t, o, how in places]
    templates = {p[0] for p in places} | set(own) | {canon(r.template, own) for r in m.cast.values()}
    for n in list(actions) + list(conds):
        for args in (actions.get(n, []) + conds.get(n, [])):
            for s in strings_of(args):
                if canon(s, own) not in templates and template_exists(s, own):
                    templates.add(canon(s, own))
    # a template's owner by where it came from; the player's own
    human_templates = {t for t, owner, _ in places if owner == human}
    _infos[name] = Info(name, m, mm, own, human, places, templates, human_templates, actions, conds, plan)
    return _infos[name]


# ---- 1. weapons
_weapon_bodies = {}


def weapon_body(wid):
    """(attributes, body) of a retail WeaponTemplate, and what it inherits from, as nugget tags over the chain."""
    if not _weapon_bodies:
        for text in simunits._weapon_files():
            for head, body in simunits._blocks(text, 'WeaponTemplate'):
                w = simunits._attr(head, 'id')
                if w:
                    _weapon_bodies[w] = (head, re.sub(r'<!--.*?-->', '', body, flags=re.S))
    return _weapon_bodies.get(wid)


def nuggets_of(wid, own=None):
    """The nugget tags of a weapon over its inheritFrom chain: a retail template, or one the mission's own units'
    XML declare."""
    mine = {}
    for text in (own or {}).values():
        for head, body in simunits._blocks(text, 'WeaponTemplate'):
            if simunits._attr(head, 'id'):
                mine[simunits._attr(head, 'id')] = (head, re.sub(r'<!--.*?-->', '', body, flags=re.S))
    out, seen = set(), set()
    while wid in mine or wid in _weapon_bodies or weapon_body(wid):
        if wid in seen:
            break
        seen.add(wid)
        head, body = mine.get(wid) or _weapon_bodies[wid]
        out |= set(re.findall(r'<(\w*Nugget)\b', body))
        wid = simunits._attr(head, 'inheritFrom')
    return sorted(out)


def declared_picks(template, own):
    """The weapon template of each slot as simunits.read_fight takes it (the PRIMARY one), from the unit's XML or what it
    inherits from; None when the XML names no weapon."""
    xml = simunits._xml(template, own)
    for _ in range(5):
        picks = []
        for head, body in simunits._blocks(xml, 'WeaponSetUpdate'):
            for slot in re.finditer(r'<WeaponSlot\w*\b.*?</WeaponSlot\w*>', body, re.S):
                ws = [(simunits._attr(h, 'Ordering'), simunits._attr(h, 'Template'))
                      for h, _ in simunits._blocks(slot.group(0), 'Weapon')]
                pick = next((t for o, t in ws if o == 'PRIMARY_WEAPON'), ws[0][1] if ws else None)
                if pick:
                    picks.append(pick)
        if picks:
            return picks
        m = re.search(r'\binheritFrom="([^"]+)"', xml[:2000])
        if not m or m.group(1).lower() == template.lower():
            break
        xml = simunits._xml(m.group(1), own)
    return None


def weapon_items(inf):
    out = []
    data = simunits._fight_data()
    table = simunits.weapon_table(inf.own)              # the retail weapons and the mission's own units' ones
    for t in sorted(inf.templates):
        picks = declared_picks(t, inf.own)
        if not picks:
            continue
        read = simunits.fight(t, inf.own)['weapons']
        lost = []
        for p in picks:
            w = table.get(p)
            if w is None:
                lost.append(f'{p}: 武器模板找不到')
                continue
            r = simunits._resolve(w, table)               # its warhead's or its OCL's damage too, as the fight reads it
            if r['dps'] > 0 and r['range'] > 0:
                continue
            why = ', '.join(nuggets_of(p, inf.own)) or '没有伤害块'
            lost.append(f'{p}: 伤害读成 0（{why}）' if r['range'] > 0 else f'{p}: 射程读成 0（{why}）')
        if lost:
            out.append(Item(inf.name, WEAPON, t, ('读空 ' if not read else '少读了 ') + '; '.join(lost)))
        elif not read and t not in inf.own and t.lower() not in data['units']:
            out.append(Item(inf.name, WEAPON, t, f'单位表里没有这个模板，武器读成空（XML 有 {", ".join(picks)}）'))
    return out


# ---- 2. upgrades and modifiers
# XML tags ending in Upgrade that are not an unread gameplay module: AttributeModifierUpgrade (read below, with its
# modifier), CommandSetUpgrade (simunits.command_set), NeededUpgrade (a data tag: simunits.needs), TechUpgrade (the
# tiers: simunits.upgrade_needs / tech_receivers, bench engine_tech), ModelConditionUpgrade and SubObjectsUpgrade (what
# the unit looks like: nothing a script or the fight asks about)
READ_OR_VISUAL = {'AttributeModifierUpgrade', 'CommandSetUpgrade', 'NeededUpgrade', 'TechUpgrade',
                  'ModelConditionUpgrade', 'SubObjectsUpgrade'}
def upgrade_items(inf):
    out = []
    for uid, xml in sorted(inf.own.items()):
        mods = {}
        for head, body in simunits._blocks(xml, 'AttributeModifier'):
            if simunits._attr(head, 'id'):
                mods[simunits._attr(head, 'id')] = (re.findall(r'<Modifier\s+Type="(\w+)"', body),
                                                    simunits._attr(head, 'ObjectStatusToSet'))
        by_upgrade = {simunits._attr(h, 'AttributeModifier'): ' '.join(re.findall(r'<TriggeredBy>([^<]*)</TriggeredBy>', b))
                      for h, b in simunits._blocks(xml, 'AttributeModifierUpgrade')}
        for mid, (types, status) in sorted(mods.items()):
            via = f'升级 {by_upgrade[mid].strip()}' if mid in by_upgrade else '不是升级给的（光环等）'
            for ty in dict.fromkeys(types):
                if ty == 'SPEED' and mid in by_upgrade:
                    continue                               # simunits.speed_scale reads exactly this
                out.append(Item(inf.name, UPGRADE, f'{uid}:{ty}', f'属性修改器 {mid} 的 {ty}（{via}）模拟器不读'
                                + ('（只读升级给的 SPEED）' if ty != 'SPEED' else '')))
            for st in (status or '').split():
                out.append(Item(inf.name, UPGRADE, f'{uid}:状态 {st}', f'属性修改器 {mid} 设状态位 {st}（{via}），模拟器的状态只由脚本动作改'))
        for tag in dict.fromkeys(re.findall(r'<(\w+Upgrade)\b', xml)):
            if tag in READ_OR_VISUAL:
                continue
            out.append(Item(inf.name, UPGRADE, f'{uid}:{tag}', f'升级模块 {tag}：模拟器不读'))
    # retail upgrades a script gives (the mission's own are above)
    declared = {m_ for xml in inf.own.values() for m_ in re.findall(r'<UpgradeTemplate\s+id="([^"]+)"', xml)}
    objs = {o.name: o.template for o in list(getattr(inf.m.map, 'OBJECTS', [])) + list(inf.mm.objects) if o.name}
    for name, idx in (('NAMED_RECEIVE_UPGRADE', 1), ('NAMED_REMOVE_UPGRADE', 1)):
        seen = set()
        for a in inf.actions.get(name, []):
            up, who = a[0], a[idx]
            if up in declared or up in seen:
                continue
            seen.add(up)
            tmpl = objs.get(who)
            xml = simunits._xml(tmpl, inf.own) if tmpl else ''
            if xml and simunits.speed_scale(xml, {up}) != 1.0:
                continue
            out.append(Item(inf.name, UPGRADE, up, f'原版升级 {up}（{name}）：效果不模拟（只认 SPEED 修改器）'))
    seen = set()
    for a in inf.actions.get('GIVE_PLAYER_UPGRADE', []):
        up = a[1]
        if up in declared or up in seen or simunits.upgrade_type(up) in ('PLAYER', 'OBJECT'):
            continue                                       # a tier / tech gate: the simulator keeps it (player_ups)
        seen.add(up)
        out.append(Item(inf.name, UPGRADE, up, f'GIVE_PLAYER_UPGRADE {up}：upgrade.xml 里没有，不知道它做什么'))
    return out


# ---- 3. script actions and conditions
_probe = {}


class Dummy:
    name = 'probe'


def probe_sim():
    if 'sim' not in _probe:
        import build
        m, t, _ = build.resolve(PROBE_LEVEL, '')
        _probe['sim'] = sim.Sim(m, t)
    return _probe['sim']


def refined(name, args):
    """The name an action is told apart by: what it is told to do matters for these (a status bit, a power, a button)."""
    if name == 'UNIT_CHANGE_OBJECT_STATUS' and len(args) > 1:
        st = args[1][2] if isinstance(args[1], tuple) else args[1]
        return f'{name}:{st}'
    if name in ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'NAMED_USE_COMMANDBUTTON_ABILITY',
                'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED') and len(args) > 1:
        return f'{name}:{args[1]}'
    return name


def power_modelled(power, inf):
    """A script's special power the simulator acts on: a superweapon's blast, the Iron Curtain / Nanoswarm, a unit's
    assemble-a-structure power."""
    return power in sim.SUPERWEAPON_HITS or power in sim.CURTAIN or \
        any(simunits.assemble(u, power, inf.own) for u in inf.own)


def name_state(kind, name, args, inf):
    """'core' (the engine model's own), 'ignored', 'shown', 'handled' (a branch of Sim.act / Sim.cond), or 'unknown'."""
    got = sim.engine_model()
    core = (got[0].CORE_ACTIONS if kind == 'act' else got[0].CORE_CONDITIONS) if got else frozenset()
    if name in core and name not in sim.SEEN_CORE:
        return 'core'
    if kind == 'act':
        if name in sim.IGNORED or name == 'CAMERA_STOP_FOLLOW':
            return 'ignored'
        if name in sim.SHOWN:
            return 'shown'
    ps = probe_sim()
    before = ps.unknown.get(name, 0)
    try:
        (ps.act(name, list(args), Dummy) if kind == 'act' else ps.cond(name, list(args)))
    except Exception:
        return 'handled'                                   # it got into a branch (and fell over on our empty world)
    return 'unknown' if ps.unknown.get(name, 0) > before else 'handled'


_state = {}


def script_items(inf):
    out = []
    modelled = status_modelled()
    for kind, table in (('act', inf.actions), ('cond', inf.conds)):
        reported = set()
        for name, uses in sorted(table.items()):
            for args in uses:
                key = refined(name, args) if kind == 'act' else name
                if key in reported:
                    continue
                reported.add(key)
                if (kind, key) not in _state:
                    _state[(kind, key)] = name_state(kind, name, args, inf)
                st = _state[(kind, key)]
                if kind == 'cond':
                    if st == 'unknown':
                        out.append(Item(inf.name, CONDITION, name, 'Sim.cond 不认识：当成不成立（false）'))
                    continue
                if st == 'ignored':
                    out.append(Item(inf.name, IGNORED_ACTION, name, 'sim.IGNORED 明确忽略（不做任何事）'))
                elif st == 'unknown':
                    out.append(Item(inf.name, ACTION, key, 'Sim.act 不认识：没效果，记进 Sim.unknown'))
                elif name == 'UNIT_CHANGE_OBJECT_STATUS' and args[1:2] and key.split(':', 1)[1] not in modelled:
                    out.append(Item(inf.name, ACTION, key, f'状态位 {key.split(":", 1)[1]} 只记下来；模拟器只认 {sorted(modelled)}'))
                elif name in ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'NAMED_USE_COMMANDBUTTON_ABILITY') and \
                        len(args) > 1 and not (name == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT' and power_modelled(args[1], inf)):
                    out.append(Item(inf.name, ACTION, key, f'{args[1]} 只记进时间线（special power），没有效果'))
    return out


# ---- 4. devices: device -> the mechanism it leans on -> is there code for it
# (device, mechanism) -> dict(what, source, probe): a probe is a list of strings; the mechanism is modelled when sim.py /
# simunits.py / simproxy.py holds a string constant containing any of them (None: it is plain scripts, modelled by the
# script actions above). The table is the register; add a row when a device gains a mechanism.
MECHANISMS = {
    ('时停区', '冻结+无敌'): dict(
        what='圈里所有单位（敌我中立）停住、打不到也不开火；走进来的也停（光环给 IN_STASIS / UNATTACKABLE / SPEED 0%）',
        source='devices/stasis.py docstring; units/stasis_zone.py docstring (checks/engine_stasis.py)',
        probe=['IN_STASIS', 'OUT_OF_TIME', 'StasisZone']),
    ('自由号', '跳跃'): dict(
        what='自由号用 SpecialPower_CNV_ChronoDeck 跳到落点 / 跳回家 / 跳回救电站（NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT）',
        source='devices/carrier.py:137-160; units/liberty.py', probe=['ChronoDeck']),
    ('列车', '刹车'): dict(
        what='玩家用 Command_*_brake 让列车停下（列车路线靠脚本每秒下命令）',
        source='devices/train.py docstring ("玩家只能瞄准和刹车"); model Unit.abilities brake', probe=['brake']),
    ('节律', '状态靠升级一开一关'): dict(
        what='NAMED_RECEIVE_UPGRADE / NAMED_REMOVE_UPGRADE 按节拍换两个升级（升级的效果另算，在"升级"一类）',
        source='devices/rhythm.py:91', probe=None),
    ('号角', '冰墙挡路 + 脚本造波'): dict(
        what='冰墙（寿命、挡路）封出口；每响一声脚本造一波；冰幕工兵走过去造冰',
        source='devices/horn.py docstring; sim.py lifetime / assemble / reblock', probe=None),
    ('冰雕广场', '冰雕藏兵 + 遇伏停车'): dict(
        what='冰雕被车队靠近而碎、放出兵（脚本）；冰雕 UNATTACKABLE；冰幕工兵冻出口',
        source='devices/ice_plazas.py docstring; sim.py UNATTACKABLE, assemble', probe=None),
    ('车队', '玩家指挥不了的车队'): dict(
        what='三辆车由脚本每几秒下一次移动命令；车属盟友，玩家点不了',
        source='devices/convoy.py docstring', probe=None),
}


def device_items(inf):
    out = []
    code = sim_code()
    for dname, spec in (inf.plan.get('机关') or {}).items():
        kind = spec.get('类型')
        for (dev, mech), row in MECHANISMS.items():
            if dev != kind or row['probe'] is None:
                continue
            if not any(tok in c for tok in row['probe'] for c in code):
                out.append(Item(inf.name, DEVICE, f'{dev}:{mech}', f'机关 {dname}（{dev}）：{row["what"]}；模拟器没有对应规则（出处 {row["source"]}）'))
    return out


# ---- 5. the player's orders
# what a player does -> the order kinds simproxy.issue would have to give for it (derived: issuable_kinds())
PLAYER_ORDERS = {
    'capture': ('占领', {'capture'}), 'stop': ('停止', {'stop'}), 'guard': ('守卫', {'guard'}),
    'stance': ('停火/站位', {'stance', 'hold_fire'}), 'garrison': ('驻扎进建筑', {'garrison'}),
}


def inherited_text(template, own):
    xml, out = simunits._xml(template, own), []
    for _ in range(5):
        out.append(xml)
        m = re.search(r'\binheritFrom="([^"]+)"', xml[:2000])
        if not m or m.group(1).lower() == template.lower():
            break
        xml = simunits._xml(m.group(1), own)
    return '\n'.join(out)


def needs_capture(inf):
    if any(n.startswith('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED') and
           any('CaptureBuilding' in str(a) for a in inf.actions.get(n, [])) for n in inf.actions):
        return True
    return any('CaptureBuilding' in inherited_text(t, inf.own) for t in inf.human_templates if template_exists(t, inf.own))


def command_items(inf):
    out = []
    can = issuable_kinds()
    armed = [t for t in sorted(inf.human_templates) if declared_picks(t, inf.own)]
    need = {'capture': needs_capture(inf), 'stop': bool(armed), 'guard': bool(armed), 'stance': bool(armed),
            'garrison': any('GARRISON' in n for n in inf.actions)}
    for k, (label, kinds) in PLAYER_ORDERS.items():
        if need[k] and not (kinds & can):
            why = {'capture': '工程师占领只有脚本动作（NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED）和剧本动词"占领"（瞬间易主）',
                   'stop': 'Sim.order_stop 有，simproxy 没有 stop 命令', 'guard': 'Sim.order_guard 只给脚本用，simproxy 没有 guard 命令',
                   'stance': '模拟器有 NO_ATTACK 状态但玩家没有停火 / 站位命令：单位一律自由开火',
                   'garrison': '脚本能驻扎，玩家下不了'}[k]
            who = '（玩家的兵：' + ', '.join(armed[:4]) + ('…' if len(armed) > 4 else '') + '）' if armed and k != 'capture' else ''
            out.append(Item(inf.name, COMMAND, label, f'玩家下不了{label}命令：{why}{who}'))
    # abilities the player's units publish: simproxy issues a ground power (order_power) or only notes it
    mine = {u.id: u for u in inf.mm.units if u.id in inf.human_templates or
            not any(t == u.id for t, _, _ in inf.places)}
    for uid, u in sorted(mine.items()):
        for what, ab in sorted(u.abilities.items()):
            if ab.startswith('SpecialPower') and 'power' in can and power_modelled(ab, inf) and \
                    simunits.power_rules(uid, ab, inf.own):
                continue
            out.append(Item(inf.name, COMMAND, f'技能 {ab}',
                            f'{uid} 的"{what}"：玩家能点，但模拟器只记日志、没有效果（order_power 只对造结构 / 超武有效）'))
    for t in sorted(inf.human_templates - set(inf.own)):
        if not template_exists(t, inf.own):
            continue
        for ab in dict.fromkeys(re.findall(r'SpecialPowerTemplate="(\w+)"', inherited_text(t, inf.own))):
            if not power_modelled(ab, inf):
                out.append(Item(inf.name, COMMAND, f'技能 {ab}', f'{t} 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'))
    return out


# ---- 6. firing at what it cannot hurt
_stuck = {}


def fires_for_nothing(shooter, target, shooter_is_human, own):
    """Whether Sim.fight, with just the two bodies side by side, has `shooter` fire at `target` with damage 0."""
    key = (shooter, target, shooter_is_human, own.get(shooter), own.get(target))
    if key not in _stuck:
        ps = probe_sim()
        ps.bodies.clear()
        ps.own = own
        try:
            a = ps.add('probe shooter', shooter, ps.human if shooter_is_human else ps.foe, 1000.0, 1000.0)
            ps.add('probe target', target, ps.foe if shooter_is_human else ps.human, 1005.0, 1000.0)
            ps.seen, ps.firing = {}, []
            ps.fight()
            mine = [dmg for _, dmg, s in ps.firing if s is a]
            _stuck[key] = bool(mine) and not any(mine)
        except Exception:
            _stuck[key] = False
        ps.bodies.clear()
    return _stuck[key]


def stuck_items(inf):
    out = []
    civ = sim.CIV
    mine = {t for t in inf.human_templates if declared_picks(t, inf.own)}
    foes = {t for t, owner, _ in inf.places if owner not in (inf.human, civ)}
    foe_armed = {t for t in foes if declared_picks(t, inf.own)}
    for shooters, targets, human in ((mine, foes, True), (foe_armed, inf.human_templates, False)):
        for s in sorted(shooters):
            hit = [t for t in sorted(targets) if fires_for_nothing(s, t, human, inf.own)]
            if hit:
                out.append(Item(inf.name, STUCK, s, ('玩家的' if human else '敌人的') + f' {s} 对 {", ".join(hit[:5])}'
                                + ('…' if len(hit) > 5 else '') + ' 一直开火但伤害为 0：Sim.fight 会一直打（攻击移动在交战中不放行）'))
    return out


# ---- the whole
def census(levels=None):
    import build
    got = []
    for lv in levels or build.LEVELS:
        inf = info(lv)
        for fn in (weapon_items, upgrade_items, script_items, device_items, command_items, stuck_items):
            got += fn(inf)
    return list(dict.fromkeys(got))             # one per (level, category, name): the first text


# ---- the register of what is known. key: (category, name) -- for every level -- or (level, category, name); value:
# dict(owner, repro, note). Owner '总控分派': the controller assigns the line.
def gap(repro, note, owner='总控分派'):
    return dict(owner=owner, repro=repro, note=note)


def first(level, name, text):
    """A first-census entry (2026-11-08): nobody has looked at it yet, the controller assigns it. The repro lists the
    item again; `text` is what the census said then."""
    return gap(f'python -I -X utf8 experimental/cnv/simcoverage.py {level} --verbose | grep -F "{name}"',
               f'首次普查登记，待分派：{text}')


SIMPY = 'python -I -X utf8 experimental/cnv/sim.py'
A9 = gap(rf'{SIMPY} a9 --script experimental/cnv/plays/a9.txt --until 900 | grep "摧毁\] ball"',
         'a9 球的暗护盾：升级给球的 INVULNERABLE 状态位没模拟（只有超武铁幕有无敌），暗球被打掉，6 个球 1 分钟拆完')
A3 = gap(f'{SIMPY} a3 --script experimental/cnv/plays/a3.txt | grep Beatc5bb8',
         'a3 时停区没模拟：圈里单位不冻、圈不挡追兵（光环给的 IN_STASIS / UNATTACKABLE / NO_ATTACK / SPEED 0%）')
A6_ATHENA = gap(f'{SIMPY} a6 --script experimental/cnv/plays/a6.txt --until 400 --all',
                'a6 雅典娜炮的自动开火已模拟（11-08 引擎线 B：OCL 武器按生成物体的 FireWeaponUpdate 算，台上 engine_ocl a），'
                '玩家用 SpecialPower_AthenaCannonTrigger 点炮仍没效果')
A7 = gap(f'{SIMPY} a7 --script experimental/cnv/plays/a7.txt | grep "奖励目标失败"',
         'a7 玩家没法下占领命令：order_capture 只由脚本动作触发，"完好占领电站"奖励目标在剧本里必然失败')
J7 = gap(f'{SIMPY} j7 --script experimental/cnv/plays/j7.txt --all | grep -i jam',
         'j7 干扰没模拟：干扰车只是一辆敌车，干扰光环（SPEED 减速、IMMOBILE、StatusBitsUpgrade）和 jam 按钮都没规则')

KNOWN = {
    # ---- the gaps the player-style runs found (docs/story/handoff-phase4.md, 39th session). One gap can be several items
    ('a9', '升级', 'CNV_TowerBall:INVULNERABLE'): A9,
    ('a9', '升级', 'CNV_TowerBall:状态 NO_BRIBE'): A9,
    ('a9', '升级', 'CNV_TowerBall:状态 UNDER_IRON_CURTAIN'): A9,
    ('a3', '设备', '时停区:冻结+无敌'): A3,
    ('a3', '升级', 'CNV_A3StasisZone:SPEED'): A3,
    ('a3', '升级', 'CNV_A3StasisZone:状态 UNATTACKABLE'): A3,
    ('a3', '升级', 'CNV_A3StasisZone:状态 NO_ATTACK'): A3,
    ('a3', '升级', 'CNV_A3StasisZone:状态 NON_AUTOACQUIRABLE'): A3,
    ('a3', '升级', 'CNV_A3StasisZone:状态 IN_STASIS'): A3,
    ('a6', '命令', '技能 SpecialPower_AthenaCannonTrigger'): A6_ATHENA,
    ('a7', '命令', '占领'): A7,
    ('j7', '升级', 'CNV_Jammer:状态 IMMOBILE'): J7,
    ('j7', '升级', 'CNV_Jammer:SPEED'): J7,
    ('j7', '升级', 'CNV_Jammer:StatusBitsUpgrade'): J7,
    ('j7', '脚本动作', 'NAMED_USE_COMMANDBUTTON_ABILITY:Command_CNV_Jammer_jam'): J7,
    # ---- the first census (2026-11-08): everything else it found, not looked at yet, to be assigned
    ('武器', 'AlliedAntiStructureShip'): first('a5', 'AlliedAntiStructureShip', '读空 AlliedAntiStructureAttackDrones: 伤害读成 0（WeaponOCLNugget）'),
    ('武器', 'AlliedAntiVehicleVehicleTech1'): first('a1', 'AlliedAntiVehicleVehicleTech1', '少读了 AlliedAntiVehicleVehicleTech1TargetPainter: 伤害读成 0（Activ'),
    ('武器', 'AlliedSupportAircraft'): first('a7', 'AlliedSupportAircraft', '读空 AlliedSupportAircraftCryobeam: 伤害读成 0（ActivateLaserNugget'),
    ('武器', 'CNV_ChronoLag'): first('a3', 'CNV_ChronoLag', '读空 CNV_ChronoLag_Shell: 武器模板找不到; AlliedAntiVehicleVehicleTec'),
    ('武器', 'CNV_Liberty'): first('a7', 'CNV_Liberty', '读空 CNV_LibertyDrones: 武器模板找不到'),
    ('武器', 'CNV_Pace63_AlliedAntiVehicleVehicleTech1'): first('s5', 'CNV_Pace63_AlliedAntiVehicleVehicleTech1', '少读了 AlliedAntiVehicleVehicleTech1TargetPainter: 伤害读成 0（Activ'),
    ('武器', 'JapanCommandoTech1'): first('j3', 'JapanCommandoTech1', '读空 JapanCommandoTech1PsyonicCrush: 伤害读成 0（ActivateLiftObject'),
    ('武器', 'JapanLightTransportVehicle'): first('a4', 'JapanLightTransportVehicle', '读空 JapanLightTransportVehicleDisguiser: 伤害读成 0（SpecialPowerN'),
    ('武器', 'SovietAntiVehicleVehicleTech3'): first('a3', 'SovietAntiVehicleVehicleTech3', '少读了 SovietAntiVehicleVehicleTech3Harpoon: 伤害读成 0（GrapplingHo'),
    ('升级', 'CNV_Burrower:SPEED'): first('a5', 'CNV_Burrower:SPEED', '属性修改器 AttributeModifier_CNV_Burrower_Under 的 SPEED（不是升级给的（光环'),
    ('升级', 'CNV_Burrower:StatusBitsUpgrade'): first('a5', 'CNV_Burrower:StatusBitsUpgrade', '升级模块 StatusBitsUpgrade：模拟器不读'),
    ('升级', 'CNV_Burrower:状态 NO_ATTACK'): first('a5', 'CNV_Burrower:状态 NO_ATTACK', '属性修改器 AttributeModifier_CNV_Burrower_Under 设状态位 NO_ATTACK（不是'),
    ('升级', 'CNV_Burrower:状态 UNATTACKABLE'): first('a5', 'CNV_Burrower:状态 UNATTACKABLE', '属性修改器 AttributeModifier_CNV_Burrower_Under 设状态位 UNATTACKABLE'),
    ('升级', 'CNV_ChronoLag:SPEED'): first('a3', 'CNV_ChronoLag:SPEED', '属性修改器 AttributeModifier_CNV_ChronoLag_Unit 的 SPEED（不是升级给的（光环'),
    ('升级', 'CNV_ChronoLag:StatusBitsUpgrade'): first('a3', 'CNV_ChronoLag:StatusBitsUpgrade', '升级模块 StatusBitsUpgrade：模拟器不读'),
    ('升级', 'CNV_ChronoLag:VISION'): first('a3', 'CNV_ChronoLag:VISION', '属性修改器 AttributeModifier_CNV_ChronoLag_Deploy 的 VISION（不是升级给的'),
    ('升级', 'CNV_ChronoLag:状态 DOES_CONTAIN_TIBERIUM'): first('a3', 'CNV_ChronoLag:状态 DOES_CONTAIN_TIBERIUM', '属性修改器 AttributeModifier_CNV_ChronoLag_Cooldown 设状态位 DOES_CON'),
    ('升级', 'CNV_ChronoLag:状态 IMMOBILE'): first('a3', 'CNV_ChronoLag:状态 IMMOBILE', '属性修改器 AttributeModifier_CNV_ChronoLag_Deploy 设状态位 IMMOBILE（不'),
    ('升级', 'CNV_ChronoLag:状态 IN_STASIS'): first('a3', 'CNV_ChronoLag:状态 IN_STASIS', '属性修改器 AttributeModifier_CNV_ChronoLag_Structure 设状态位 IN_STAS'),
    ('升级', 'CNV_ChronoLag:状态 NON_AUTOACQUIRABLE'): first('a3', 'CNV_ChronoLag:状态 NON_AUTOACQUIRABLE', '属性修改器 AttributeModifier_CNV_ChronoLag_Structure 设状态位 NON_AUT'),
    ('升级', 'CNV_ChronoLag:状态 NO_ATTACK'): first('a3', 'CNV_ChronoLag:状态 NO_ATTACK', '属性修改器 AttributeModifier_CNV_ChronoLag_Structure 设状态位 NO_ATTA'),
    ('升级', 'CNV_ChronoLag:状态 UNATTACKABLE'): first('a3', 'CNV_ChronoLag:状态 UNATTACKABLE', '属性修改器 AttributeModifier_CNV_ChronoLag_Structure 设状态位 UNATTAC'),
    ('升级', 'CNV_ComboParent:StatusBitsUpgrade'): first('j4', 'CNV_ComboParent:StatusBitsUpgrade', '升级模块 StatusBitsUpgrade：模拟器不读'),
    ('s6', '升级', 'CNV_Jammer:SPEED'): first('s6', 'CNV_Jammer:SPEED', '属性修改器 AttributeModifier_CNV_Jammer_Slow 的 SPEED（不是升级给的（光环等））'),
    ('s6', '升级', 'CNV_Jammer:StatusBitsUpgrade'): first('s6', 'CNV_Jammer:StatusBitsUpgrade', '升级模块 StatusBitsUpgrade：模拟器不读'),
    ('s6', '升级', 'CNV_Jammer:状态 IMMOBILE'): first('s6', 'CNV_Jammer:状态 IMMOBILE', '属性修改器 AttributeModifier_CNV_Jammer_On 设状态位 IMMOBILE（不是升级给的（光'),
    ('升级', 'CNV_Pace63_AlliedAntiVehicleVehicleTech1:StatusBitsUpgrade'): first('s5', 'CNV_Pace63_AlliedAntiVehicleVehicleTech1:StatusBitsUpgrade', '升级模块 StatusBitsUpgrade：模拟器不读'),
    ('升级', 'CNV_S2ArmouredTrain:状态 IMMOBILE'): first('s2', 'CNV_S2ArmouredTrain:状态 IMMOBILE', '属性修改器 AttributeModifier_CNV_S2ArmouredTrain_Brake 设状态位 IMMOB'),
    ('升级', 'CNV_S2CryoTrain:状态 IMMOBILE'): first('s2', 'CNV_S2CryoTrain:状态 IMMOBILE', '属性修改器 AttributeModifier_CNV_S2CryoTrain_Brake 设状态位 IMMOBILE（'),
    ('升级', 'CNV_Shikigami:ARMOR'): first('j5', 'CNV_Shikigami:ARMOR', '属性修改器 AttributeModifier_CNV_Shikigami_Guard 的 ARMOR（不是升级给的（光'),
    ('升级', 'CNV_Shikigami:StatusBitsUpgrade'): first('j5', 'CNV_Shikigami:StatusBitsUpgrade', '升级模块 StatusBitsUpgrade：模拟器不读'),
    ('升级', 'CNV_TideGun:RANGE'): first('a8', 'CNV_TideGun:RANGE', '属性修改器 AttributeModifier_CNV_TideGun_High 的 RANGE（升级 Upgrade_'),
    ('升级', 'CNV_TideGun:VISION'): first('a8', 'CNV_TideGun:VISION', '属性修改器 AttributeModifier_CNV_TideGun_High 的 VISION（升级 Upgrade'),
    ('脚本动作', 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:SpecialPower_CNV_ChronoDeck'): first('a7', 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:SpecialPower_CNV_ChronoDeck', 'SpecialPower_CNV_ChronoDeck 只记进时间线（special power），没有效果'),
    ('脚本动作', 'UNIT_SET_MODELCONDITION_GENERIC'): first('a7', 'UNIT_SET_MODELCONDITION_GENERIC', 'Sim.act 不认识：没效果，记进 Sim.unknown'),
    ('脚本动作(忽略)', 'CAMERA_LETTERBOX_BEGIN'): first('a4', 'CAMERA_LETTERBOX_BEGIN', 'sim.IGNORED 明确忽略（不做任何事）'),
    ('脚本动作(忽略)', 'CAMERA_LETTERBOX_END'): first('a4', 'CAMERA_LETTERBOX_END', 'sim.IGNORED 明确忽略（不做任何事）'),
    ('脚本动作(忽略)', 'CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT'): first('a4', 'CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', 'sim.IGNORED 明确忽略（不做任何事）'),
    ('脚本动作(忽略)', 'PLAYER_SET_MAX_PLAYER_POWER_POINTS'): first('a4', 'PLAYER_SET_MAX_PLAYER_POWER_POINTS', 'sim.IGNORED 明确忽略（不做任何事）'),
    ('脚本动作(忽略)', 'PLAYER_SET_PLAYER_POWER_POINTS'): first('a4', 'PLAYER_SET_PLAYER_POWER_POINTS', 'sim.IGNORED 明确忽略（不做任何事）'),
    ('脚本动作(忽略)', 'SET_COOP_AI_COMMAND_UI_ENABLED'): first('a4', 'SET_COOP_AI_COMMAND_UI_ENABLED', 'sim.IGNORED 明确忽略（不做任何事）'),
    ('脚本动作(忽略)', 'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES'): first('a4', 'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', 'sim.IGNORED 明确忽略（不做任何事）'),
    ('脚本动作(忽略)', 'SKIRMISH_AI_USE_REBUILD_SYSTEM'): first('a4', 'SKIRMISH_AI_USE_REBUILD_SYSTEM', 'sim.IGNORED 明确忽略（不做任何事）'),
    ('脚本动作(忽略)', 'SKIRMISH_AI_USE_REPAIRS'): first('a4', 'SKIRMISH_AI_USE_REPAIRS', 'sim.IGNORED 明确忽略（不做任何事）'),
    ('设备', '列车:刹车'): first('s2', '列车:刹车', '机关 装甲列车（列车）：玩家用 Command_*_brake 让列车停下（列车路线靠脚本每秒下命令）；模拟器没有对应规'),
    ('设备', '自由号:跳跃'): first('a7', '自由号:跳跃', '机关 自由号（自由号）：自由号用 SpecialPower_CNV_ChronoDeck 跳到落点 / 跳回家 / 跳回'),
    ('命令', '停止'): first('a1', '停止', '玩家下不了停止命令：Sim.order_stop 有，simproxy 没有 stop 命令（玩家的兵：AlliedAn'),
    ('命令', '停火/站位'): first('a1', '停火/站位', '玩家下不了停火/站位命令：模拟器有 NO_ATTACK 状态但玩家没有停火 / 站位命令：单位一律自由开火（玩家的兵：A'),
    ('a3', '命令', '占领'): first('a3', '占领', '玩家下不了占领命令：工程师占领只有脚本动作（NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAM'),
    ('a4', '命令', '占领'): first('a4', '占领', '玩家下不了占领命令：工程师占领只有脚本动作（NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAM'),
    ('命令', '守卫'): first('a1', '守卫', '玩家下不了守卫命令：Sim.order_guard 只给脚本用，simproxy 没有 guard 命令（玩家的兵：Al'),
    ('命令', '技能 Command_CNV_Burrower_burrow'): first('s5', '技能 Command_CNV_Burrower_burrow', 'CNV_Burrower 的"burrow"：玩家能点，但模拟器只记日志、没有效果（order_power 只对造结构 '),
    ('命令', '技能 Command_CNV_ChronoLag_deploy'): first('a3', '技能 Command_CNV_ChronoLag_deploy', 'CNV_ChronoLag 的"deploy"：玩家能点，但模拟器只记日志、没有效果（order_power 只对造结构'),
    ('命令', '技能 Command_CNV_ComboParent_part'): first('j4', '技能 Command_CNV_ComboParent_part', 'CNV_ComboParent 的"part"：玩家能点，但模拟器只记日志、没有效果（order_power 只对造结构'),
    ('命令', '技能 Command_CNV_Jammer_jam'): first('s6', '技能 Command_CNV_Jammer_jam', 'CNV_Jammer 的"jam"：玩家能点，但模拟器只记日志、没有效果（order_power 只对造结构 / 超武有'),
    ('命令', '技能 Command_CNV_S2ArmouredTrain_brake'): first('s2', '技能 Command_CNV_S2ArmouredTrain_brake', 'CNV_S2ArmouredTrain 的"brake"：玩家能点，但模拟器只记日志、没有效果（order_power '),
    ('命令', '技能 Command_CNV_Shikigami_guard'): first('j5', '技能 Command_CNV_Shikigami_guard', 'CNV_Shikigami 的"guard"：玩家能点，但模拟器只记日志、没有效果（order_power 只对造结构 '),
    ('命令', '技能 Command_Evacuate'): first('s5', '技能 Command_Evacuate', 'CNV_Burrower 的"unload"：玩家能点，但模拟器只记日志、没有效果（order_power 只对造结构 '),
    ('命令', '技能 SpecialPowerReturnToProducer'): first('a7', '技能 SpecialPowerReturnToProducer', 'AlliedFighterAircraft 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('a2', '命令', '技能 SpecialPower_AthenaCannonTrigger'): first('a2', '技能 SpecialPower_AthenaCannonTrigger', 'AlliedAntiStructureVehicle 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_Bark'): first('a2', '技能 SpecialPower_Bark', 'AlliedScoutInfantry 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_CNV_Beacon_Pull'): first('a5', '技能 SpecialPower_CNV_Beacon_Pull', 'CNV_Beacon 的"pull"：玩家能点，但模拟器只记日志、没有效果（order_power 只对造结构 / 超武'),
    ('命令', '技能 SpecialPower_CNV_ChronoDeck'): first('a8', '技能 SpecialPower_CNV_ChronoDeck', 'CNV_Liberty 的"jump"：玩家能点，但模拟器只记日志、没有效果（order_power 只对造结构 / 超'),
    ('命令', '技能 SpecialPower_JapanAntiInfantryInfantryBonzai'): first('j4', '技能 SpecialPower_JapanAntiInfantryInfantryBonzai', 'JapanAntiInfantryInfantry 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_MolotovCocktail'): first('s2', '技能 SpecialPower_MolotovCocktail', 'SovietAntiInfantryInfantry 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_PackReplaceSelf'): first('a1', '技能 SpecialPower_PackReplaceSelf', 'AlliedConstructionYard 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_PaintTargetTrigger'): first('a1', '技能 SpecialPower_PaintTargetTrigger', 'AlliedAntiVehicleVehicleTech1 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_PaintTargetTrigger_HighTechnology'): first('a1', '技能 SpecialPower_PaintTargetTrigger_HighTechnology', 'AlliedAntiVehicleVehicleTech1 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_PsyonicBlast'): first('j3', '技能 SpecialPower_PsyonicBlast', 'JapanCommandoTech1 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_RadarLock'): first('a4', '技能 SpecialPower_RadarLock', 'AlliedAntiVehicleInfantry 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_SmokeBomb'): first('j3', '技能 SpecialPower_SmokeBomb', 'JapanInfiltrationInfantry 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_TargetedRepairVehicle'): first('a2', '技能 SpecialPower_TargetedRepairVehicle', 'AlliedWarFactory 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_TimeBelt'): first('a1', '技能 SpecialPower_TimeBelt', 'AlliedCommandoTech1 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_ToggleAlliedEngineerHeal'): first('a3', '技能 SpecialPower_ToggleAlliedEngineerHeal', 'AlliedEngineer 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_ToggleEnergizedArmor'): first('j7', '技能 SpecialPower_ToggleEnergizedArmor', 'JapanAntiVehicleVehicleTech1 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_ToggleMagneticArmor'): first('a5', '技能 SpecialPower_ToggleMagneticArmor', 'AlliedAntiNavyShipTech1 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_ToggleRiotShield'): first('a1', '技能 SpecialPower_ToggleRiotShield', 'AlliedAntiInfantryInfantry 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_ToggleShieldSphere'): first('a2', '技能 SpecialPower_ToggleShieldSphere', 'AlliedAntiStructureVehicle 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_ToggleSpiderHole'): first('j4', '技能 SpecialPower_ToggleSpiderHole', 'JapanAntiVehicleInfantry 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_ToggleTargetPainter'): first('a1', '技能 SpecialPower_ToggleTargetPainter', 'AlliedAntiVehicleVehicleTech1 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_TriggerEMPCruiseMissle'): first('a5', '技能 SpecialPower_TriggerEMPCruiseMissle', 'AlliedAntiStructureShip 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_TriggerJump'): first('a2', '技能 SpecialPower_TriggerJump', 'AlliedAntiNavalScout 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_TriggerLeap'): first('s2', '技能 SpecialPower_TriggerLeap', 'SovietAntiInfantryVehicle 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
    ('命令', '技能 SpecialPower_UnpackReplaceSelf'): first('a1', '技能 SpecialPower_UnpackReplaceSelf', 'AlliedMCV 的原版特殊能力：玩家能点，模拟器只记日志、没有效果'),
}


def build_levels():
    import build
    return tuple(build.LEVELS)


def match(item, known=None):
    """The KNOWN key that covers an item, else None."""
    known = KNOWN if known is None else known
    for k in ((item.level, item.category, item.name), (item.category, item.name)):
        if k in known:
            return k
    return None


def verdict(items, known=None):
    """(new, stale): items no KNOWN key covers, KNOWN keys no item matches."""
    known = KNOWN if known is None else known
    new = [i for i in items if match(i, known) is None]
    hit = {match(i, known) for i in items}
    return new, sorted((k for k in known if k not in hit), key=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('levels', nargs='*')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()
    import build
    t0 = time.time()
    levels = a.levels or list(build.LEVELS)
    items = census(levels)
    by = {lv: [i for i in items if i.level == lv] for lv in levels}
    for lv in levels:
        mine = by[lv]
        known = [i for i in mine if match(i)]
        print(f'== {lv}: {len(mine)} 项未模拟（已登记 {len(known)}）')
        for i in mine:
            k = match(i)
            print(f'  {i.category} | {i.name} | ' + (i.text if a.verbose else i.text[:60]) +
                  (f'  [已登记: {KNOWN[k]["owner"]}]' if k else ''))
            if a.verbose and k:
                print(f'      复现 {KNOWN[k]["repro"]}  说明 {KNOWN[k]["note"]}')
    new, stale = verdict(items)
    print(f'共 {len(items)} 项（{len({(i.category, i.name) for i in items})} 种），未登记 {len(new)}，'
          + ('登记过期 ' + str(len(stale)) if not a.levels else '') + f'；{time.time() - t0:.1f} 秒')
    if not a.levels:
        for k in stale:
            print('  登记过期（删掉）:', k)
    sys.exit(1 if new or (stale and not a.levels) else 0)


if __name__ == '__main__':
    main()
