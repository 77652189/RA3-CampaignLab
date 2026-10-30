r"""Enemy composition and counters in the campaign maps, retail and ours, one ruler (read only: retail archives, built
mods): what the enemy fields in each stage, what each of its units is good against, and what the player has that
answers it.

  python -I -X utf8 docs/design/teardowns/data/units_measure.py            -> units.json + units.md here
  python -I -X utf8 docs/design/teardowns/data/units_measure.py j02 A4     (only these; the md is rebuilt from the json)

Why: the user's playtest (2026-10-28) of Iga and Stalingrad -- "我会根据敌人选择最合适的兵种应对" -- the choice
that carried both levels was reading what the next wave is and answering it with the right unit and the right
micro, not the timers. A level whose enemy is one kind of thing, or whose player has one unit that answers all of
it, is flattened by that unit ("A4 基本上可以平推过去").

Roles: RA3 names its units by what they are built to kill (<Faction>Anti{Infantry,Vehicle,Air,Structure,Navy}...);
ROLES below is that, by hand, with the few names that lie corrected (the IFV is AntiAirVehicle and changes with its
passenger; the Flak Trooper is AntiVehicleInfantry and shoots aircraft; the transforming Japanese units do two
things). Body = what the unit is: 步 infantry, 车 vehicle (amphibious too), 空 air, 船 ship. A unit answers an enemy
if the enemy's body is in what the unit kills. sim_combat.json's weapons were not used: a third of the retail units
come out with none there (Conscript, Apollo, Vindicator, Tesla Trooper ...).

Per map, at normal difficulty:
  enemy      placed units of the players hostile to the human (minus teams / names a start script deletes at normal)
             and scripted spawns of theirs (CREATE_REINFORCEMENT_TEAM: the team's unit types x max counts;
             CREATE_*_ON_TEAM_*: one of the template), each weighted by its build cost (SDK SageXML BuildCost);
             a script that may repeat counts once. Skirmish AIs switched on are listed with their faction, not counted
             (what they build is up to them).
  stages     the first showing of each main objective (timeline_measure's clock; objectives shown together are one
             stage). A spawn belongs to the last stage begun before it; a placed unit to the stage whose border
             first contains it (no border switches: stage 1, '开局摆好').
  player     placed units of the human, units given (reinforcements, transfers to the human), and -- with a base --
             the faction's buildable roster (STANDARD) minus what a start script disallows (units, or the building
             that makes them) plus what a later script allows
  answers    per stage: the enemy's cost by body; for each body with >= 10% of it, the player's units that kill it;
             'one answer' = the best single player unit and the share of the stage's enemy cost it answers;
             'shift' = the bodies' mix differs from the stage before by >= 0.3 (total variation)
  enemy vs enemy  pairs of non-human players who are each other's enemies and both have units
"""
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout_measure as LM  # noqa: E402
import timeline_measure as TM  # noqa: E402
from layout_measure import mapstudy, mapxml  # noqa: E402

sys.path.insert(0, os.path.join(LM.ROOT, 'experimental', 'cnv'))
import simunits  # noqa: E402

OUT_JSON = os.path.join(HERE, 'units.json')
OUT_MD = os.path.join(HERE, 'units.md')
SHARE = 0.10        # a body with less of the stage's enemy cost does not need an answer
SHIFT = 0.30        # total variation between two stages' body mixes that counts as a change
BODIES = ('步', '车', '空', '船')

# template: (name, body, kills). kills: bodies (and 楼 buildings) it is built to kill
ROLES = {
    # Allies
    'alliedantiinfantryinfantry': ('维和步兵', '步', '步'), 'alliedantivehicleinfantry': ('标枪兵', '步', '车空'),
    'alliedscoutinfantry': ('警犬', '步', '步'), 'alliedengineer': ('工程师', '步', ''),
    'alliedinfiltrationinfantry': ('间谍', '步', ''), 'alliedcommandotech1': ('谭雅', '步', '步楼'),
    'alliedlegionnaireinfantry': ('冷冻军团兵', '步', '步车'),
    'alliedantiinfantryvehicle': ('激流气垫船', '车', '步船'), 'alliedantiinfantryvehicle_ground': ('激流气垫船', '车', '步船'),
    'alliedantiairvehicletech1': ('多功能步兵车', '车', '空'), 'alliedantivehiclevehicletech1': ('守护者坦克', '车', '车'),
    'alliedantistructurevehicle': ('雅典娜炮', '车', '楼'), 'alliedantivehiclevehicletech3': ('幻影坦克', '车', '车步'),
    'alliedfuturetank': ('未来坦克', '车', '车步'), 'alliedartilleryvehicle': ('平定者', '车', '步楼'),
    'alliedfighteraircraft': ('阿波罗战机', '空', '空'), 'alliedantigroundaircraft': ('先锋战机', '空', '车楼'),
    'alliedbomberaircraft': ('世纪轰炸机', '空', '楼车步'), 'alliedsupportaircraft': ('冷冻直升机', '空', ''),
    'alliedgunshipaircraft': ('先兆炮艇', '空', '步车'),
    'alliedantinavalscout': ('海豚', '船', '船'), 'alliedantiairship': ('水翼船', '船', '空'),
    'alliedantinavyshiptech1': ('突击驱逐舰', '船', '船车'), 'alliedantistructureship': ('航空母舰', '船', '楼车'),
    # Soviets
    'sovietantiinfantryinfantry': ('动员兵', '步', '步'), 'sovietantivehicleinfantry': ('防空步兵', '步', '空步'),
    'sovietheavyantivehicleinfantry': ('磁暴步兵', '步', '车'), 'sovietscoutinfantry': ('战熊', '步', '步'),
    'sovietengineer': ('战斗工兵', '步', ''), 'sovietcommandotech1': ('娜塔莎', '步', '步车楼'),
    'sovietscoutvehicle': ('恐怖机器人', '车', '车'), 'sovietantiinfantryvehicle': ('镰刀', '车', '步'),
    'sovietantivehiclevehicletech1': ('锤式坦克', '车', '车'), 'sovietantivehiclevehicletech2': ('磁能坦克', '车', '车'),
    'sovietantivehiclevehicletech3': ('天启坦克', '车', '车'), 'sovietantistructurevehicle': ('V4 火箭车', '车', '楼'),
    'sovietheavywalkervehicle': ('收割者', '车', '步空'), 'sovietgrindervehicle': ('绞肉机', '车', '步车'),
    'sovietantigroundaircraft': ('双刃直升机', '空', '车步'), 'sovietfighteraircraft': ('米格战机', '空', '空'),
    'sovietbomberaircraft': ('基洛夫飞艇', '空', '楼车步'),
    'sovietantinavyshiptech1': ('海蝎', '车', '船车'), 'sovietantinavyshiptech2': ('阿库拉潜艇', '船', '船'),
    'sovietantiairship': ('牛蛙', '车', '空'), 'sovietantiairship_ground': ('牛蛙', '车', '空'),
    'sovietantistructureship': ('无畏舰', '船', '楼'),
    # Empire
    'japanantiinfantryinfantry': ('帝国武士', '步', '步'), 'japanantivehicleinfantry': ('坦克杀手', '步', '车'),
    'japanantivehicleinfantrytech3': ('火箭天使', '空', '车'), 'japaninfiltrationinfantry': ('忍者', '步', '步'),
    'japancommandotech1': ('百合子', '步', '步车'), 'japanarcherinfantry': ('弓箭少女', '步', '步空'),
    'japanscoutinfantry': ('爆裂机器人', '车', '车'), 'japanlighttransportvehicle': ('疾行者', '车', ''),
    'japanantiinfantryvehicle': ('机甲天狗', '车', '步空'), 'japanantiairvehicletech1': ('打击者-VX', '车', '空车'),
    'japanantivehiclevehicletech1': ('海啸坦克', '车', '车'), 'japanantivehiclevehicletech3': ('鬼王', '车', '车'),
    'japanantistructurevehicle': ('波能炮', '车', '楼车'), 'japansentinelvehicle': ('钢铁浪人', '车', '车'),
    'japanmechaking': ('将军处刑者', '车', '车步楼'),
    'japannavyscoutship': ('夜叉潜艇', '船', '船'), 'japanantiairship': ('天翼', '船', '空船'),
    'japanantivehicleship': ('薙刀巡洋舰', '船', '船'), 'japanantistructureship': ('将军战舰', '船', '楼'),
    'a04_explodingtengu': ('自爆天狗', '空', '车步'),
}
# what the faction builds with a full base (Uprising's own units come in by script)
STANDARD = {
    'allied': ['alliedantiinfantryinfantry', 'alliedantivehicleinfantry', 'alliedscoutinfantry', 'alliedcommandotech1',
               'alliedantiinfantryvehicle', 'alliedantiairvehicletech1', 'alliedantivehiclevehicletech1',
               'alliedantistructurevehicle', 'alliedantivehiclevehicletech3', 'alliedfighteraircraft',
               'alliedantigroundaircraft', 'alliedbomberaircraft', 'alliedsupportaircraft', 'alliedantinavalscout',
               'alliedantiairship', 'alliedantinavyshiptech1', 'alliedantistructureship'],
    'soviet': ['sovietantiinfantryinfantry', 'sovietantivehicleinfantry', 'sovietheavyantivehicleinfantry',
               'sovietscoutinfantry', 'sovietcommandotech1', 'sovietscoutvehicle', 'sovietantiinfantryvehicle',
               'sovietantivehiclevehicletech1', 'sovietantivehiclevehicletech3', 'sovietantistructurevehicle',
               'sovietantigroundaircraft', 'sovietfighteraircraft', 'sovietbomberaircraft', 'sovietantinavyshiptech1',
               'sovietantinavyshiptech2', 'sovietantiairship', 'sovietantistructureship'],
    'japan': ['japanantiinfantryinfantry', 'japanantivehicleinfantry', 'japanantivehicleinfantrytech3',
              'japaninfiltrationinfantry', 'japancommandotech1', 'japanscoutinfantry', 'japanantiinfantryvehicle',
              'japanantiairvehicletech1', 'japanantivehiclevehicletech1', 'japanantivehiclevehicletech3',
              'japanantistructurevehicle', 'japannavyscoutship', 'japanantiairship', 'japanantivehicleship',
              'japanantistructureship'],
}
MAKER = {'barracks': '步', 'warfactory': '车', 'airfield': '空', 'navalyard': '船'}
FACTION = {'PlayerTemplate:Allies': 'allied', 'PlayerTemplate:Soviet': 'soviet', 'PlayerTemplate:Japan': 'japan'}
BASE = re.compile(r'constructionyard|mcv', re.I)
# punishments for exploits, debug skips, cutscene extras: not the level's enemy
SKIP = re.compile(r'cheese|debug|cheat|cine|intro', re.I)
# action: (template, team, where) argument indices
SPAWN_TEMPLATE = {'CREATE_NAMED_ON_TEAM_AT_WAYPOINT': (1, 2, 3), 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION': (1, 2, 3),
                  'CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT': (0, 1, 2),
                  'CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION': (0, 1, 2),
                  'CREATE_UNNAMED_ON_TEAM_AT_NAMED_OBJECT_LOCATION': (0, 1, 2)}

_cost = None


def cost(t):
    """Build cost from the SDK's SageXML (a campaign override: its parent's); 500 when nothing says."""
    global _cost
    if _cost is None:
        _cost = {}
        for tpl, _, path in simunits.units():
            try:
                c = re.search(r'<BuildCost\b[^>]*\bAmount="(\d+)"', open(path, encoding='utf-8', errors='replace').read())
            except OSError:
                continue
            if c:
                _cost[tpl] = int(c.group(1))
    t = t.lower()
    if t in _cost:
        return _cost[t]
    parent = str((mapstudy._index or {}).get(t, {}).get('inheritFrom', '')).lower()
    return _cost.get(parent, 500)


def role(t):
    """(name, body, kills) or None for what is not a fighting unit."""
    t = t.lower()
    if t in ROLES:
        return ROLES[t]
    mapstudy.kind(t, '')                                   # loads the index
    parent = str((mapstudy._index or {}).get(t, {}).get('inheritFrom', '')).lower()
    if parent in ROLES:
        return ROLES[parent]
    return None


def read_teams(m):
    node = next((n for _, n in m.walk() if n.name == 'Teams'), None)
    out = {}
    if node is None:
        return out
    d = node.head
    for p in range(len(d) - 6):
        try:
            pr = mapxml._props(m, d, p)
        except Exception:
            continue
        if 'teamName' in pr and len(pr) > len(out.get(pr['teamName'], {})):
            out[pr['teamName']] = pr
    return out


def team_units(pr):
    out = []
    for i in range(1, 8):
        u = str(pr.get(f'teamUnitType{i}', '')).replace('GameObject:', '')
        n = int(pr.get(f'teamUnitMaxCount{i}', 0) or 0)
        if u and n:
            out += [u] * n
    return out


def mix(units):
    """{body: cost share} of a list of templates (fighting units only)."""
    tot, by = 0, {}
    for u in units:
        r = role(u)
        if not r:
            continue
        c = cost(u)
        by[r[1]] = by.get(r[1], 0) + c
        tot += c
    return {b: round(v / tot, 3) for b, v in by.items()} if tot else {}


def measure(name, m):
    lv = TM.Level(name, m)
    # PlayerScriptsList holds one list per SidesList player and a first one for the unnamed neutral player:
    # timeline_measure gives list i to player i, one off (air_measure.owned_scripts checks this on Brighton)
    psl = next((x for _, x in m.walk() if x.name == 'PlayerScriptsList'), None)
    n_lists = len([k for k in psl.kids if k.name == 'ScriptList']) if psl else 0
    names = list(lv.players)
    if n_lists == len(names) + 1:
        shift = {p: ([''] + names)[i] for i, p in enumerate(names)}
        for s in lv.scripts:
            s.owner = shift.get(s.owner, s.owner)
    sides = lv.players
    human = lv.human
    faction = FACTION.get(str(sides.get(human, {}).get('playerFaction', '')))
    if name.startswith('ours_'):            # our builds say Allies for every player: the level's line says
        faction = {'A': 'allied', 'S': 'soviet', 'J': 'japan'}.get(name.split('_')[1][:1], faction)
    teams = read_teams(m)
    ck, T = lv.propagate(1)
    used = set()
    for t in T.values():
        if t is not None:
            used.update(ck.chain(t[0]))
    ck.name_anchors(used)
    goals, links = mapstudy.objectives(m)
    bonus = {g['name'] for g in goals if g['bonus']}
    titles = {g['name']: g['title'] for g in goals}

    # deleted at normal by a start script; stage starts; spawns; gains; allows
    # (a spawn whose script's time cannot be worked out -- a subroutine called at random, say -- has when None and
    # goes by its place)
    deleted, starts, spawns, gains, ai_on, given = set(), [], [], [], set(), set()
    disallow, allow_later, allow_start, base_at = set(), set(), set(), []
    if any(o['side'] == human and BASE.search(o['template']) for o in lv.objs):
        base_at.append((0, 0.0, 0, False))
    yards = {o['side'] for o in lv.objs if BASE.search(o['template'])}
    for s in lv.scripts:
        if not s.diff[1]:                                  # not built at normal
            continue
        t = T.get(s.idx)
        at_start = t is not None and t[0] == 0 and t[1] <= 1 and \
            all(all(c[0] == 'CONDITION_TRUE' for c in g) for g in s.ors)
        for (an, v, raw), off in zip(s.acts, s.offs):
            when = None if t is None else (t[0], t[1] + off, t[2], t[3])
            if an == 'TEAM_TRANSFER_TO_PLAYER' and len(v) >= 2 and lv.is_human(v[1], s.owner):
                given.add(lv.team_key(v[0]))
            if an in ('SKIRMISH_AI_MAKE_BASE', 'SKIRMISH_AI_START') and v:      # an AI that builds, timed or not
                p = s.owner if v[0] == '<This Player>' else v[0]
                if p in lv.enemies:
                    ai_on.add(p)
            if when is None and an not in SPAWN_TEMPLATE and not an.startswith('CREATE_REINFORCEMENT_TEAM'):
                continue
            if an in ('TEAM_DELETE', 'NAMED_DELETE') and at_start and v:
                deleted.add(lv.team_key(v[0]) if an == 'TEAM_DELETE' else str(v[0]))
            elif an == 'SET_MISSION_OBJECTIVE_STATUS' and len(v) >= 2 and int(TM.num(raw[1])) == 1 \
                    or an == 'SHOW_MISSION_OBJECTIVE' and v:
                if v[0] not in bonus:
                    starts.append((when, v[0]))
            elif an in ('CREATE_REINFORCEMENT_TEAM', 'CREATE_REINFORCEMENT_TEAM_AT_UNIT_POSITION') and v:
                if SKIP.search(str(v[0])) or SKIP.search(s.name):
                    continue
                us = team_units(teams.get(lv.team_key(v[0]), {}))
                spawns.append((when, lv.team_owner(v[0]), us, s.once, lv.team_key(v[0]),
                               lv.pos_of(v[1]) if len(v) > 1 else None))
            elif an in SPAWN_TEMPLATE and len(v) > max(SPAWN_TEMPLATE[an]):
                if SKIP.search(s.name):
                    continue
                i, j, k = SPAWN_TEMPLATE[an]
                spawns.append((when, lv.team_owner(v[j]), [str(v[i])], s.once, lv.team_key(v[j]),
                               lv.pos_of(v[k]) if len(v) > k else None))
            elif an == 'TEAM_TRANSFER_TO_PLAYER' and len(v) >= 2 and lv.is_human(v[1], s.owner):
                k = lv.team_key(v[0])
                gains += [(when, o['template']) for o in lv.objs if o['team'] == k]
            elif an == 'NAMED_TRANSFER_OWNERSHIP_PLAYER' and len(v) >= 2 and lv.is_human(v[1], s.owner):
                o = next((o for o in lv.objs if o['name'] == str(v[0])), None)
                if o:
                    gains.append((when, o['template']))
                    if BASE.search(o['template']):
                        base_at.append(when)
            elif an == 'PLAYER_TRANSFER_OWNERSHIP_PLAYER' and len(v) >= 2 and lv.is_human(v[1], s.owner):
                gains += [(when, o['template']) for o in lv.objs if o['side'] == v[0]]
                if v[0] in yards:
                    base_at.append(when)
            elif an == 'ALLOW_DISALLOW_ONE_BUILDING' and len(v) >= 3:
                who = str(v[0])
                mine = lv.is_human(who, s.owner) or who == '<All Players>'
                if not mine:
                    continue
                what, flag = str(v[1]).lower(), int(TM.num(raw[2]))
                if at_start:
                    (allow_start if flag else disallow).add(what)
                elif flag:
                    allow_later.add(what)
                if flag and BASE.search(what):
                    base_at.append(when)
    for when, owner, us, _, _, _ in spawns:
        if owner == human or owner in TM.GENERIC:
            gains += [(when, u) for u in us]
            if any(BASE.search(u) for u in us):
                base_at.append(when)
    disallow -= allow_start
    base = any(w is not None for w in base_at)

    # stages: objectives first shown together are one stage
    starts.sort(key=lambda q: ck.key(q[0]))
    stages = []
    for when, g in starts:
        if any(g in st['goals'] for st in stages):
            continue
        if stages and abs(ck.est(when) - ck.est(stages[-1]['t'])) < 5 and when[0] == stages[-1]['t'][0]:
            stages[-1]['goals'].append(g)
        else:
            stages.append(dict(t=when, goals=[g]))
    if not stages:
        stages = [dict(t=(0, 0.0, 0, False), goals=[])]

    def stage_of(when):
        k, i = ck.key(when), 0
        for j, st in enumerate(stages):
            if ck.key(st['t']) <= k or j == 0:
                i = j
        return i

    # border of a placed unit -> the stage of that border's first switch
    border_t = {}
    for s in lv.scripts:
        t = T.get(s.idx)
        if t is None:
            continue
        for (an, v, raw), off in zip(s.acts, s.offs):
            if an == 'MAP_SWITCH_BORDER':
                k = int(TM.num(raw[0]))
                w = (t[0], t[1] + off, t[2], t[3])
                if k not in border_t or ck.key(w) < ck.key(border_t[k]):
                    border_t[k] = w
    order = sorted(border_t, key=lambda k: ck.key(border_t[k]))

    # each stage's objective markers: a placed unit goes to the nearest one's stage, not before its border opens
    marks = {}
    for g, _, target in links:
        p = lv.pos_of(target)
        for i, st in enumerate(stages):
            if g in st['goals'] and p:
                marks.setdefault(i, []).append(p)

    def placed_stage(p):
        first = 0
        for k in order:
            if 0 <= k < len(lv.rects) and LM.inside(p, lv.rects[k]):
                first = stage_of(border_t[k])
                break
        near = [(min(TM.dist(p, q) for q in qs), i) for i, qs in marks.items() if i >= first]
        return min(near)[1] if near else first

    enemy = [[] for _ in stages]
    owners = {}
    for o in lv.objs:
        if o['side'] in lv.enemies and role(o['template']) and o['team'] not in deleted and \
                o['name'] not in deleted and not SKIP.search(o['team']):
            enemy[placed_stage(o['p'])].append(o['template'])
            owners.setdefault(o['side'], 0)
            owners[o['side']] += 1
    repeats = 0
    for when, owner, us, once, team, pos in spawns:
        if owner in lv.enemies and team not in given:
            us = [u for u in us if role(u)]
            enemy[stage_of(when) if when is not None else placed_stage(pos) if pos else 0] += us
            if us:
                owners[owner] = owners.get(owner, 0) + len(us)
                repeats += not once

    # the player's units
    # by stage: what was placed, what was given by then, and the build list once there is a base
    have = [set() for _ in stages]
    have[0] = {o['template'].lower() for o in lv.objs if o['side'] == human and role(o['template'])}
    for when, g in gains:
        if role(g):
            have[stage_of(when) if when is not None else 0].add(g.lower())
    build = set()
    if base and faction:
        gone = {b for k, b in MAKER.items() if any(d.endswith(k) and d.startswith(faction) for d in disallow)}
        build = {u for u in STANDARD[faction] if u not in disallow and ROLES[u][1] not in gone}
    build |= {a for a in allow_later if role(a)}
    base_stage = min((stage_of(w) for w in base_at if w is not None), default=None)
    rosters, acc = [], set()
    for i in range(len(stages)):
        acc |= have[i]
        rosters.append(sorted(acc | (build if base_stage is not None and base_stage <= i else set())))
    roster = rosters[-1]

    out_stages, prev = [], None
    for i, (st, us) in enumerate(zip(stages, enemy)):
        roster_i = rosters[i]
        mx = mix(us)
        kinds = {}
        for u in us:
            r = role(u)
            kinds.setdefault(r[0], [0, 0, r[2]])
            kinds[r[0]][0] += 1
            kinds[r[0]][1] += cost(u)
        need = [b for b in BODIES if mx.get(b, 0) >= SHARE]
        answers = {b: sorted({role(u)[0] for u in roster_i if b in role(u)[2]}) for b in need}
        best, best_share = None, 0.0
        for u in roster_i:
            sh = sum(mx.get(b, 0) for b in role(u)[2] if b in BODIES)
            if sh > best_share:
                best, best_share = role(u)[0], sh
        shift = None
        if prev is not None and mx:
            shift = round(sum(abs(mx.get(b, 0) - prev.get(b, 0)) for b in BODIES) / 2, 2)
        if mx:
            prev = mx
        out_stages.append(dict(
            goals=[titles.get(g, g) for g in st['goals']], t=ck.fmt(st['t']), mix=mx,
            cost=sum(cost(u) for u in us), kinds=sorted(([k, v[0], v[1], v[2]] for k, v in kinds.items()),
                                                        key=lambda q: -q[2]),
            roster=[role(u)[0] for u in roster_i], answers=answers, unanswered=[b for b in need if not answers[b]], best=best,
            best_share=round(best_share, 2), shift=shift))
    hostile = [p for p in lv.enemies if owners.get(p) or p in ai_on]
    feud = []
    for i, p in enumerate(sorted(hostile)):
        for q in sorted(hostile)[i + 1:]:
            if q in str(sides.get(p, {}).get('playerEnemies', '')).split():
                feud.append([p, q])
    # a third party: not the human's ally, has fighting units, and is at war with one of the human's enemies
    armed = {o['side'] for o in lv.objs if role(o['template'])} | {w[1] for w in spawns if any(role(u) for u in w[2])}
    third = [p for p, pr in sides.items() if p != human and p not in lv.enemies and p not in lv.allies and
             p in armed and any(e in str(pr.get('playerEnemies', '')).split() for e in hostile)]
    every = [u for us in enemy for u in us]
    return dict(map=name, faction=faction, base=base, roster=[role(u)[0] for u in roster],
                enemy_ai=sorted(ai_on), stages=out_stages, mix=mix(every),
                enemy_kinds=len({role(u)[0] for u in every}), repeats=repeats, feud=feud, third=third)


def short(name):
    if name.startswith('ours_'):
        return name.split('_')[1]
    s = name.replace('camp_', '').replace('ep01_', 'up-')
    return '_'.join(s.split('_')[:2])


def fmt_mix(mx):
    return ' '.join(f'{b}{round(mx[b] * 100)}' for b in BODIES if mx.get(b)) or '—'


def write_md(data):
    lines = ['# 敌军构成和克制：每关每段的敌人、玩家拿什么打（每关一行，再分段）', '',
             '由 [units_measure.py](units_measure.py) 生成，口径见脚本开头。普通难度。"构成"是敌方兵力按造价的份额：'
             '步＝步兵，车＝战车（含两栖），空＝飞机，船＝船。"答案"是玩家手里专打这类的兵种；"一招鲜"是玩家最好的'
             '单个兵种能对付这一段多少敌方兵力（造价份额）。"换"是这一段的构成和上一段差多少（0～1，≥0.3 算换了）。'
             '遭遇战 AI 自己造的兵不算，只列出有没有。', '',
             '| 关 | 阵营 | 敌方种类 | 全关构成 | 段数 | 构成换了的段 | 一招鲜（最高的一段） | 有没有缺答案 | 敌方 AI | 敌人之间互打 |',
             '|---|---|---|---|---|---|---|---|---|---|']
    agg = {}
    detail = ['', '## 分段', '']
    for name in sorted(data, key=lambda n: (n.startswith('ours'), n)):
        v = data[name]
        if 'error' in v:
            lines.append(f'| {short(name)} | 读不出：{v["error"]} | | | | | | | | |')
            continue
        side = 'ours' if name.startswith('ours') else 'retail'
        a = agg.setdefault(side, dict(n=0, kinds=[], bodies=[], shifts=[], one=[], gaps=0, feud=0, ai=0, six=0,
                                      stages=0, three=0, one_stage=0, all_one=0, air=0))
        sts = [s for s in v['stages'] if s['mix']]
        a['six'] += v['enemy_kinds'] >= 6
        a['stages'] += len(sts)
        a['three'] += sum(1 for s in sts if sum(1 for b in BODIES if s['mix'].get(b, 0) >= SHARE) >= 3)
        a['one_stage'] += sum(1 for s in sts if s['best_share'] >= 0.999)
        a['all_one'] += bool(sts) and all(s['best_share'] >= 0.999 for s in sts)
        a['air'] += v['mix'].get('空', 0) >= SHARE
        shifts = sum(1 for s in sts if s['shift'] is not None and s['shift'] >= SHIFT)
        one = max((s['best_share'] for s in sts), default=0)
        gaps = sorted({b for s in sts for b in s['unanswered']})
        a['n'] += 1
        a['kinds'].append(v['enemy_kinds'])
        a['bodies'].append(sum(1 for b in BODIES if v['mix'].get(b, 0) >= SHARE))
        a['shifts'].append(shifts / max(1, len(sts) - 1) if len(sts) > 1 else 0)
        a['one'].append(one)
        a['gaps'] += bool(gaps)
        a['feud'] += bool(v['feud'] or v['third'])
        a['ai'] += bool(v['enemy_ai'])
        feud = '、'.join('/'.join(p) for p in v['feud']) or ('第三方' if v['third'] else '—')
        lines.append(f"| {short(name)} | {v['faction']} | {v['enemy_kinds']} | {fmt_mix(v['mix'])} | {len(sts)} | "
                     f"{shifts} | {round(one * 100)}% | {'、'.join(gaps) or '—'} | {'、'.join(v['enemy_ai']) or '—'} | "
                     f"{feud} |")
        detail.append(f"### {short(name)}（玩家能用：{'、'.join(v['roster']) or '—'}）")
        detail.append('')
        detail.append('| 段 | 开始 | 构成 | 主要敌人（个数，专打） | 答案 | 一招鲜 | 换 |')
        detail.append('|---|---|---|---|---|---|---|')
        for i, s in enumerate(v['stages'], 1):
            ks = '、'.join(f'{k}×{n}（{kill or "—"}）' for k, n, _, kill in s['kinds'][:5]) or '—'
            ans = '；'.join(f"{b}：{'、'.join(x) or '**没有**'}" for b, x in s['answers'].items()) or '—'
            goal = '、'.join(s['goals'])[:40] or '（开局）'
            detail.append(f"| {i} {goal} | {s['t']} | {fmt_mix(s['mix'])} | {ks} | {ans} | "
                          f"{s['best'] or '—'} {round(s['best_share'] * 100)}% | "
                          f"{'' if s['shift'] is None else s['shift']} |")
        detail.append('')
    med = lambda xs: round(statistics.median(xs), 2) if xs else None  # noqa: E731
    r, o = agg.get('retail', {}), agg.get('ours', {})
    lines += ['', '## 汇总', '', '| | 原版 | 我们 |', '|---|---|---|',
              f"| 关数 | {r.get('n', 0)} | {o.get('n', 0)} |",
              f"| 敌方兵种数（中位数） | {med(r.get('kinds', []))} | {med(o.get('kinds', []))} |",
              f"| 敌方兵种 ≥ 6 种的关 | {r.get('six', 0)} | {o.get('six', 0)} |",
              f"| 占 ≥10% 的敌方体型数（中位数，最多 4） | {med(r.get('bodies', []))} | {med(o.get('bodies', []))} |",
              f"| 敌方飞机占 ≥10% 的关 | {r.get('air', 0)} | {o.get('air', 0)} |",
              f"| 一段里有 ≥ 3 种体型的段 / 有敌人的段 | {r.get('three', 0)} / {r.get('stages', 0)} | "
              f"{o.get('three', 0)} / {o.get('stages', 0)} |",
              f"| 构成换了的段占比（中位数） | {med(r.get('shifts', []))} | {med(o.get('shifts', []))} |",
              f"| 玩家一个兵种就能对付整段敌人的段 | {r.get('one_stage', 0)} / {r.get('stages', 0)} | "
              f"{o.get('one_stage', 0)} / {o.get('stages', 0)} |",
              f"| 每段都是这样的关 | {r.get('all_one', 0)} | {o.get('all_one', 0)} |",
              f"| 有一段缺答案的关（多是玩家没有船、或只有突击队的关） | {r.get('gaps', 0)} | {o.get('gaps', 0)} |",
              f"| 有遭遇战 AI 的关 | {r.get('ai', 0)} | {o.get('ai', 0)} |",
              f"| 敌人之间互打或有第三方的关 | {r.get('feud', 0)} | {o.get('feud', 0)} |"]
    open(OUT_MD, 'w', encoding='utf-8').write('\n'.join(lines + detail) + '\n')


def main():
    parts = sys.argv[1:]
    old = json.load(open(OUT_JSON, encoding='utf-8')) if os.path.exists(OUT_JSON) else {}
    for name, load in LM.jobs(parts):
        try:
            old[name] = measure(name, load())
            v = old[name]
            print(name, v['faction'], 'kinds', v['enemy_kinds'], fmt_mix(v['mix']), 'stages',
                  [(fmt_mix(s['mix']), s['best'], s['best_share']) for s in v['stages']], flush=True)
        except Exception as ex:
            import traceback
            traceback.print_exc()
            old[name] = dict(map=name, error=repr(ex))
            print('FAIL', name, repr(ex), flush=True)
        with open(OUT_JSON, 'w', encoding='utf-8') as fh:
            json.dump(old, fh, ensure_ascii=False, indent=1)
    write_md(old)


if __name__ == '__main__':
    main()
