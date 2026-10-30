r"""The numbers behind docs/story/graybox-cards.md (ADR 0011): what the simulator's data can say about each question card
(docs/design/cards/), by cheap arithmetic on its unit numbers. Everything a card leans on that the simulator has no model for
(economy, the skirmish AI, queueing in a street, the new rules each card adds) is NOT here: the write-up says "留给实机".

  python -I -X utf8 experimental/cnv/graybox_cards.py            one line a fact (the full text: work/logs/graybox_cards.log)
  python -I -X utf8 experimental/cnv/graybox_cards.py --verbose  the same on screen, with the working
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]
import glossary  # noqa: E402
import graybox  # noqa: E402
import offline  # noqa: E402
import plan  # noqa: E402
import sim  # noqa: E402

T = glossary.template


def world():
    """A4's sim for the bodies' numbers, and the fight-numbers reader."""
    s = sim.Sim(plan.Compiler(plan.load('a4')).compile())
    return s, graybox.Bodies(s)


def cost_of(side):
    return sum((offline.cost(t) or 500) * n for t, n in side.items())


def in_sequence(body, mine, groups):
    """`groups` met one after another (a column in a narrow street): what is left of `mine` (a share of its
    numbers) after each, None once it is wiped out or cannot finish one."""
    left, share = dict(mine), []
    start = sum(mine.values())
    for g in groups:
        left, rest, _ = graybox.fluid(body, left, g)
        if sum(rest.values()) >= 0.05:
            return None
        share.append(sum(left.values()) / start)
    return share


def biggest(ok, lo=0.05, hi=64.0):
    """The largest scale m in [lo, hi] for which ok(m) holds (ok is true for small m); None when not even lo."""
    if not ok(lo):
        return None
    for _ in range(14):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return lo


def a4_streets(s, body):
    """A4 甲 (three streets, two engineers): the escort and one street's group (2 Knights : 1 Tank Killer, the plan's
    plaza mix), at the scale where the escort still wins with half left. Merged is the three groups at once; a column
    is the three in a narrow street one after another. The truck's life under one street's fire is the price of letting
    a street through."""
    escort = {T('守护者坦克', '盟军'): 3, T('维和步兵', '盟军'): 4, T('标枪兵', '盟军'): 2}
    unit = {T('帝国武士', '帝国'): 2.0, T('坦克杀手', '帝国'): 1.0}

    def scaled(m):
        return {t: n * m for t, n in unit.items()}

    def merged(m):
        a, b, _ = graybox.fluid(body, escort, {t: n * 3 * m for t, n in unit.items()})
        return sum(b.values()) < 0.05 and sum(a.values()) / sum(escort.values()) >= graybox.HALF

    def column(m):
        share = in_sequence(body, escort, [scaled(m)] * 3)
        return share is not None and share[-1] >= graybox.HALF

    def single(m):
        a, b, _ = graybox.fluid(body, escort, scaled(m))
        return sum(b.values()) < 0.05 and sum(a.values()) / sum(escort.values()) >= graybox.HALF
    truck = body('CNV_ConvoyTruck')
    street = scaled(1.0)
    _, _, clear = graybox.fluid(body, escort, street)
    fire = sum(offline.dps(body.s, body(t), truck) * n for t, n in street.items())
    return dict(escort_cost=cost_of(escort), street_cost=cost_of(street),
                single=biggest(single), column=biggest(column), merged=biggest(merged),
                truck_hp=truck.max_hp, truck_guessed=bool(truck.guessed), street_dps_on_truck=fire,
                truck_seconds=truck.max_hp / fire if fire else math.inf, clear_seconds=clear)


def a4_street_types(s, body):
    """A4 甲 says the three streets send different troops (infantry, tank killers, tsunami tanks) so the escort's mix
    must change street by street. k* of each escort type against each street, and the cheapest type that answers
    all three."""
    streets = {'武士街': {T('帝国武士', '帝国'): 5}, '坦克杀手街': {T('坦克杀手', '帝国'): 4}, '海啸街': {T('海啸坦克', '帝国'): 3}}
    mine = {n: T(n, '盟军') for n in ('守护者坦克', '维和步兵', '标枪兵')}
    table = {n: {st: graybox.kstar(body, t, e) for st, e in streets.items()} for n, t in mine.items()}
    easy = [n for n, row in table.items() if all(k is not None and k <= graybox.EASY for k in row.values())]
    return dict(table=table, one_type_answers_all=easy)


def wall_cover(builders, life=30.0, cooldown=40.0, window=40.0):
    """Seconds of a window (the convoy crossing a plaza) the gate is shut: `builders` ice engineers, the first
    putting a wall up as the window opens and the next each `life` later (the relay), each again when its cooldown
    is over; a wall lives `life`. Returns (shut seconds, the window)."""
    shut = []
    for i in range(builders):
        t = i * life
        while t < window:
            shut.append((t, t + life))
            t += cooldown
    covered, end = 0.0, 0.0
    for a, b in sorted(shut):
        a = max(a, end)
        b = min(b, window)
        if b > a:
            covered += b - a
        end = max(end, b)
    return covered, window


def a4_plaza(s, body):
    """A4 乙: the convoy needs ~40 s for a plaza; a wall lives 30 s, cools down 40 s."""
    one, two = wall_cover(1), wall_cover(2)
    return dict(one_engineer=one[0] / one[1], two_relay=two[0] / two[1])


def a4_cold(s, body):
    """A4 丙: what the 拆源 route costs the convoy -- the north camp's building health over what the player's army
    does to buildings per second (the convoy waits at the bridge head meanwhile)."""
    hp = sum(b.max_hp for b in s.living() if b.owner != s.human and 'STRUCTURE' in b.kinds and not b.scenery)
    escort = {T('守护者坦克', '盟军'): 3, T('维和步兵', '盟军'): 4, T('标枪兵', '盟军'): 2}
    wall = s.add('#wall', 'JapanBarracks', s.foe, 0.0, 0.0)
    wall.alive = False
    wall.kinds = frozenset({'STRUCTURE'})
    dps = sum(offline.dps(s, body(t), wall) * n for t, n in escort.items())
    return dict(camp_hp=hp, escort_dps=dps, seconds=hp / dps if dps else math.inf)


def s1_lake(s, body):
    """S1: ranges (the card's hook range 300 is a confirmed number), the roster the flow gives the player and the
    enemy's, and the lake against the ice window of card 丙 (60 s) at the roster's speeds."""
    mine = ['防空步兵', '镰刀机甲']
    theirs = ['守护者坦克', '维和步兵']
    ranges = {n: max((w['range'] for w in body(T(n, f)).weapons), default=0.0)
              for n, f in [(x, '苏联') for x in mine] + [(x, '盟军') for x in theirs]}
    vision = body(T('守护者坦克', '盟军')).vision
    heavy = {n: body(T(n, '苏联')).speed for n in ['镰刀机甲']}
    return dict(hook=300.0, ranges=ranges, escort_vision=vision,
                window_reach={n: v * 60.0 for n, v in heavy.items()}, window_half={n: v * 30.0 for n, v in heavy.items()},
                map_width=4740.0)


def j7_valleys(s, body):
    """J7: the jammer's 250 aura at 40 % speed, and the ranges of the high-ground card."""
    out = {}
    for who, f in [('动员兵', '苏联'), ('铁锤坦克', '苏联'), ('天启坦克', '苏联')]:
        v = body(T(who, f)).speed
        out[who] = dict(speed=v, extra=2 * 250.0 / v * (1 / 0.4 - 1))   # a full pass through the circle
    far = {n: max((w['range'] for w in body(T(n, '帝国')).weapons), default=0.0)
           for n in ['帝国武士', '坦克杀手', '天狗机甲', '海啸坦克', '鬼王']}
    v4 = max(w['range'] for w in body(T('V4火箭车', '苏联')).weapons)
    h = 1.0                                              # a tower's health, in towers: arithmetic of the shields
    seq = h + 2 * h + 4 * h                              # one by one, each next doubled (the card's numbers)
    par = 3 * h                                          # all three worn down together, felled together
    return dict(aura_extra=out, ranges=far, v4_range=v4, shield_sequential=seq, shield_together=par)


def facts():
    s, body = world()
    return dict(a4_streets=a4_streets(s, body), a4_types=a4_street_types(s, body), a4_plaza=a4_plaza(s, body), a4_cold=a4_cold(s, body),
                s1=s1_lake(s, body), j7=j7_valleys(s, body))


def lines(f):
    a, p, c, l, j = f['a4_streets'], f['a4_plaza'], f['a4_cold'], f['s1'], f['j7']
    ratio = lambda x: f'{x:.1f}' if x else '打不赢'
    return [
        f'A4甲 护卫造价 {a["escort_cost"]}；一条街一组造价 {a["street_cost"]}（2 武士 : 1 坦克杀手）；护卫赢（剩一半）的最大组数 '
        f'单街 {ratio(a["single"])}，三条街排成纵队 {ratio(a["column"])}，三条街并成一团 {ratio(a["merged"])}',
        f'A4甲 车 {a["truck_hp"]:g} 血{"（猜的）" if a["truck_guessed"] else ""}，一条街的火力打车 {a["street_dps_on_truck"]:.0f}/秒，'
        f'{a["truck_seconds"]:.1f} 秒一辆；护卫清一条街要 {a["clear_seconds"]:.1f} 秒',
        'A4甲 三条街各种兵的 k*（<=1.5 轻松）：' + '；'.join(
            f'{n} ' + '、'.join(f'{st} {graybox.fmt(k)}' for st, k in row.items()) for n, row in f['a4_types']['table'].items()) +
        f'；一种兵就能答三条街：{"、".join(f["a4_types"]["one_type_answers_all"]) or "没有"}',
        f'A4乙 一个工兵封门占车过广场 40 秒的 {p["one_engineer"]:.0%}，两个接力 {p["two_relay"]:.0%}',
        f'A4丙 北营建筑总血 {c["camp_hp"]:g}，护卫对建筑每秒 {c["escort_dps"]:.0f}，拆光要 {c["seconds"]:.0f} 秒',
        f'S1 磁钩 {l["hook"]:g} 对 己方最大射程 {max(l["ranges"][n] for n in ("防空步兵", "镰刀机甲")):g}、敌方最大射程 '
        f'{max(l["ranges"][n] for n in ("守护者坦克", "维和步兵")):g}；车队视野 {l["escort_vision"]:g}；镰刀机甲 60 秒走 '
        f'{l["window_reach"]["镰刀机甲"]:g}，对地图宽 {l["map_width"]:g}',
        'J7 干扰车光环（半径 250）整个穿过多花：' + '，'.join(f'{k} {v["extra"]:.1f} 秒（速度 {v["speed"]:g}）' for k, v in j['aura_extra'].items()),
        'J7 帝国直射武器最大射程：' + '，'.join(f'{k} {v:g}' for k, v in j['ranges'].items()) + f'；V4 火箭车 {j["v4_range"]:g}',
        f'J7丙 护盾：一座座拆要 {j["shield_sequential"]:g} 座的血，一起拆 {j["shield_together"]:g}，比 {j["shield_sequential"] / j["shield_together"]:.2f}',
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()
    f = facts()
    text = '\n'.join(lines(f))
    path = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'logs', 'graybox_cards.log')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(text + '\n\n' + repr(f) + '\n')
    print(text if a.verbose else text.splitlines()[0] + f'\n（全文 {os.path.relpath(path, os.path.dirname(os.path.dirname(HERE)))}）')


if __name__ == '__main__':
    main()
