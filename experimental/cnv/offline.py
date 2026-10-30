r"""Offline checks of a plan, no game (ADR 0009: layer 3 opens for A4 first): who beats whom, whether one unit type
answers a whole stage (P29: under ONE of its cost), and the high-ground sight lines the plan leans on.

  python -I -X utf8 experimental/cnv/offline.py a4

matchups  each player unit -- what it starts with or is given, and from the stage its base comes what a base builds
          (ROSTER: the faction's ground units, the plan's 禁造 taken off) -- against each enemy template met, cost for
          cost: Lanchester's square law on the fight model's numbers (simunits.fight: health, damage per second x
          the target's armour, the weapon's anti mask as sim.can_hit has it). With n = 1 / cost a side, the ratio
          (hp_P dps(P->E) / cost_P^2) / (hp_E dps(E->P) / cost_E^2): over 1 P wins. Range, speed, splash, micro and
          abilities are out (the fight model's own limits, sim.ALIGN 'combat'): a ratio near 1 is a coin toss.
stages    the enemy met per stage in the plan's walkthrough (sim.py with WALK: the fight model off, what comes near
          the player's beaten after a while -- an enemy's stage is the one running when it first came within REACH
          of the player's), by build cost; per player unit the share of that cost it beats; the best share must be
          under ONE. The skirmish AI's builds are not simulated (sim.ALIGN 'ai'): what it was let build is not in
          the count.
sight     the plan's high-ground claims (SIGHT) on the map's ground: a viewer of a template at a point, a target
          point, what the plan says; sim.looks decides (its vision, HIGH_STEP: 'high ground' in sim.ALIGN).
"""
import argparse
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]
import glossary  # noqa: E402
import plan  # noqa: E402
import sim  # noqa: E402
import simunits  # noqa: E402

ONE = 0.9                                       # P29 (a4-redesign.md): one unit type answers under 90 % of a stage
# the walkthrough that wins (a4.md 返工: the player's escort with the trucks, plazas 2 and 3 frozen, the north
# command down at 2:40; 5:53)
WALK = {'a4': '不打; 自动打掉 5; 0 派 guardian 去 plaza 1; 0 派 peacekeeper 去 plaza 1; 0 派 javelin 去 plaza 1; '
              '40 造 CNV_A4IceWall 在 inside 2; 100 派 guardian 去 halt; 100 派 peacekeeper 去 halt; '
              '100 派 javelin 去 halt; 120 派 peacekeeper 去 north base; 120 派 javelin 去 north base; '
              '160 摧毁 north command; 200 造 CNV_A4IceWall 在 inside 3; '
              '210 派 guardian 去 north mouth'}
# what a base builds that fights on the ground (air and ships: A4 bans the airfield, the fight is ashore)
ROSTER = {'盟军': ['维和步兵', '标枪兵', '警犬', '谭雅', '守护者坦克', '幻影坦克', '多功能步兵车', '激流 ZX', '雅典娜炮'],
          '苏联': ['动员兵', '防空步兵', '磁暴步兵', '战熊', '娜塔莎', '镰刀', '铁锤坦克', '天启坦克', 'V4 火箭车'],
          '帝国': ['帝国武士', '坦克杀手', '火箭天使', '爆裂无人机', '百合子', '天狗', '打击者', '海啸坦克', '鬼王',
                 '波能炮']}
BASE = re.compile(r'constructionyard|mcv', re.I)


def a4_sight(m, s):
    """A4's high-ground claims (a4-redesign.md P27, a4.md 规则 and 目标说明)."""
    mp = m.map
    x = mp.P1[1] + 40.0                         # the lane's middle stretch, over the avenue
    lane, avenue = (x, mp.LANE[0] + 30.0), (x, mp.ROAD_Y + mp.AVENUE / 2 - 20.0)
    tower = s.point('ramp tower 1')
    return [('后巷高处看得见大街（占了后巷就能看清大街）', '守护者坦克', lane, avenue, True),
            ('后巷高处看得见大街（步兵上去）', '维和步兵', lane, avenue, True),
            ('大街看不见后巷高处（大街上的敌人看不见你）', '帝国武士', avenue, lane, False),
            ('坡脚看不见坡顶的波能塔（要先派兵上坡）', '守护者坦克', s.point('front ramp west'), tower, False),
            ('北营低地看不见坡顶的波能塔', '守护者坦克', s.point('north camp'), tower, False),
            ('波能塔看得见坡脚', '波能塔', tower, s.point('front ramp west'), True)]


SIGHT = {'a4': a4_sight}

_cost = None


def cost(template):
    """Build cost from the SDK's SageXML; None when nothing says."""
    global _cost
    if _cost is None:
        _cost = {}
        for t, _, path in simunits.units():
            try:
                c = re.search(r'<BuildCost\b[^>]*\bAmount="(\d+)"', open(path, encoding='utf-8', errors='replace').read())
            except OSError:
                continue
            if c:
                _cost[t] = int(c.group(1))
    return _cost.get(template.lower())


def dps(s, a, t):
    """Damage per second body a does to body t: each weapon that can hit t, x t's armour for its type."""
    return sum(w['dps'] * t.armor.get(w['type'], simunits.ARMOR_DEFAULT) / 100.0 for w in a.weapons
               if s.can_hit(w, t))


def ratio(s, p, e):
    """Cost for cost, p's strength over e's (Lanchester's square law); inf: e cannot hurt p; None: neither."""
    cp, ce = cost(p.template) or 500, cost(e.template) or 500
    mine, theirs = p.max_hp * dps(s, p, e) / cp ** 2, e.max_hp * dps(s, e, p) / ce ** 2
    if not theirs:
        return math.inf if mine else None
    return mine / theirs


def walk(level):
    """Run the plan's walkthrough: (sim, compiler, [(stage, start s)], {enemy template: (stage, cost met)},
    {stage: player templates})."""
    c = plan.Compiler(plan.load(level))
    m = c.compile()
    s = sim.Sim(m, script=WALK.get(level, ''))
    starts, met, have = [], {}, {}
    base = None
    while s.t <= sim.UNTIL and s.ending is None:
        s.step()
        for ph in c.phases:
            if s.flags.get(ph.flag) == 1 and ph.name not in dict(starts):
                starts.append((ph.name, s.t))
        stage = starts[-1][0] if starts else (c.phases[0].name if c.phases else '')
        for b in s.living():
            if b.owner == s.human and b.speed > 0 and b.weapons:
                have.setdefault(stage, set()).add(b.template)
            if base is None and b.owner == s.human and BASE.search(b.template):
                base = stage
            if b.owner != s.human and s.enemy(s.human, b.owner) and b.close_since is not None and \
                    (b.weapons or 'CAN_ATTACK' in b.kinds) and id(b) not in met:
                met[id(b)] = (b.template, stage)
        if not s.pending() and s.t - s.last_change >= sim.QUIET:
            break
        s.t = round(s.t + sim.DT, 3)
    enemy = {}
    for t, stage in met.values():
        enemy.setdefault(stage, {}).setdefault(t, 0)
        enemy[stage][t] += 1
    names = [n for n, _ in starts]
    if base is not None:                        # from the stage the base comes: what it builds, less the bans
        faction = c.faction['p1']
        banned = {t for p, t in s.banned if p == s.human}
        build = {glossary.template(n, faction) for n in ROSTER.get(faction, [])}
        build = {t for t in build if t.lower() not in banned}
        for n in names[names.index(base):]:
            have[n] = have.get(n, set()) | build
    acc = set()
    for n in names:                             # what was had stays (the roster grows)
        acc |= have.get(n, set())
        have[n] = set(acc)
    return s, starts, enemy, have


def label(template):
    inv = {v.lower(): k for k, v in glossary.OWN.items()}
    return inv.get(template.lower(), template)


def report(level):
    s, starts, enemy, have = walk(level)
    lines = [f'{level}: walkthrough {WALK.get(level, "")!r} -- {s.ending_line()}',
             '段：' + '，'.join(f'{n} {sim.mmss(t)}' for n, t in starts)]
    proto = {}

    def body(t, owner):
        if (t, owner) not in proto:
            proto[(t, owner)] = s.add(f'#offline {len(proto)}', t, owner, 0.0, 0.0)
            proto[(t, owner)].alive = False             # out of the world: only its numbers are read
        return proto[(t, owner)]

    foes = sorted({t for e in enemy.values() for t in e}, key=label)
    mine = sorted({t for h in have.values() for t in h}, key=label)
    lines.append('\n对阵（同造价，>1 我方赢；inf = 对方打不动我；- = 谁也打不动谁；? = 数据里读不出它的武器）：')
    lines.append('我方 \\ 敌方 | ' + ' | '.join(label(t) for t in foes))
    table = {}
    for p in mine:
        row = []
        for e in foes:
            bp, be = body(p, s.human), body(e, s.foe)
            if not any(w['dps'] for w in bp.weapons) or not any(w['dps'] for w in be.weapons):
                row.append('?')                         # unknown: neither a win nor a loss in the counts
                continue
            r = ratio(s, bp, be)
            table[(p, e)] = r
            row.append('-' if r is None else 'inf' if r == math.inf else f'{r:.2g}')
        lines.append(f'{label(p)} ({cost(p) or "?"}) | ' + ' | '.join(row))
    lines.append('（战斗模型只算血量、伤害、护甲和能不能打到：碾压、溅射、射程差、技能和微操都不算，坦克打步兵会偏弱）')
    problems = []
    lines.append(f'\n每段的敌人和"一个兵种能对付多少"（按造价，要低于 {ONE:.0%}）：')
    for n, _ in starts:
        e = enemy.get(n, {})
        total = sum((cost(t) or 500) * k for t, k in e.items())
        if not total:
            lines.append(f'- {n}：没碰上带武器的敌人')
            continue
        shares = {p: sum((cost(t) or 500) * k for t, k in e.items() if (table.get((p, t)) or 0) > 1) / total
                  for p in have.get(n, [])}
        best = max(shares, key=shares.get) if shares else None
        nobody = [label(t) for t in e if not any((table.get((p, t)) or 0) > 1 for p in have.get(n, []))]
        lines.append(f'- {n}：' + '，'.join(f'{label(t)} {k}' for t, k in sorted(e.items(), key=lambda q: -q[1])) +
                     f'（共 {total}）；最好的一种 {label(best)} {shares[best]:.0%}' if best else '' +
                     (f'；谁也打不过：{"、".join(nobody)}' if nobody else ''))
        if best and shares[best] >= ONE:
            problems.append(f'{n}: one unit type answers {shares[best]:.0%} of the stage ({label(best)}), P29 wants '
                            f'under {ONE:.0%}')
    claims = SIGHT.get(level)
    if claims:
        lines.append('\n高地视野（低处看不见高出 %g 的地方）：' % sim.HIGH_STEP)
        for text, who, (vx, vy), (tx, ty), want in claims(s.m, s):
            v = s.add(f'#offline {len(proto) + 100}', glossary.template(who, '盟军'), s.human, vx, vy)
            v.alive = False
            got = s.looks(v, tx, ty)
            sight = v.vision or max((w['range'] for w in v.weapons), default=0.0)
            d = math.hypot(tx - vx, ty - vy)
            lines.append(f'- {"过" if got == want else "不对"} {text}：{who} 站在 {s.ground.z(vx, vy):.0f} 高，'
                         f'目标 {s.ground.z(tx, ty):.0f} 高，相距 {d:.0f}，视野 {sight:.0f} -> '
                         f'{"看得见" if got else "看不见"}')
            if got != want:
                problems.append(f'sight: {text}: {"sees" if got else "does not see"}')
    lines.append('\n' + ('PROBLEMS\n  ' + '\n  '.join(problems) if problems else 'OK'))
    return '\n'.join(lines), problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('level')
    text, problems = report(ap.parse_args().level)
    print(text)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
