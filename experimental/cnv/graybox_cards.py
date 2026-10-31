r"""The numbers behind docs/story/graybox-cards.md (ADR 0011): what the simulator's data can say about each question card
(docs/design/cards/), by cheap arithmetic on its unit numbers. Everything a card leans on that the simulator has no model for
(economy, the skirmish AI, queueing in a street, the new rules each card adds) is NOT here: the write-up says "留给实机".

  python -I -X utf8 experimental/cnv/graybox_cards.py            one line a fact (the full text: work/logs/graybox_cards.log)
  python -I -X utf8 experimental/cnv/graybox_cards.py --verbose  the same on screen, with the working
"""
import argparse
import itertools
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]
import glossary  # noqa: E402
import graybox  # noqa: E402
import offline  # noqa: E402
import plan  # noqa: E402
import sim  # noqa: E402
import simunits  # noqa: E402

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


A4_ESCORT = {('守护者坦克', '盟军'): 3, ('维和步兵', '盟军'): 4, ('标枪兵', '盟军'): 2}
A4_GROUP = {('帝国武士', '帝国'): 3.0, ('坦克杀手', '帝国'): 2.0}      # card 甲, third version: one street's wave, 1050


def a4_run(body, per_wave, scale, resupply=(3,), waves=5):
    """A4 甲, section 1: the escort (no base, no repair) eats `per_wave` street groups one after another each horn
    (a column: the walls' detours come >= 10 s apart and a group dies in ~3 s), and is topped up to full strength
    after the waves in `resupply`. Returns (the escort's share left after each wave it survived, the wave that wiped
    it out or None)."""
    escort = {T(*k): n for k, n in A4_ESCORT.items()}
    group = {T(*k): n * scale for k, n in A4_GROUP.items()}
    start, left, shares = sum(escort.values()), dict(escort), []
    for w in range(1, waves + 1):
        for _ in range(per_wave[(w - 1) % len(per_wave)]):
            left, rest, _ = graybox.fluid(body, left, group)
            if sum(rest.values()) >= 0.05 or sum(left.values()) < 0.05:
                return shares, w
        shares.append(sum(left.values()) / start)
        if w in resupply:
            left = dict(escort)
    return shares, None


def a4_waves(s, body):
    """A4 甲: does the card's own trick (walls turn three streets into one, so the escort eats three groups a horn)
    also grind the escort down over the ~5 horns of section 1? Per wave the escort fights 3 groups (both walls
    used: all three streets into one) or 2 (one wall: the frozen street's group joins an open one, the third
    street's group goes for the trucks, see the card's 取舍)."""
    def survives(per_wave, resupply=(3,)):
        return lambda m: a4_run(body, per_wave, m, resupply)[1] is None
    one, third = {T(*k): n for k, n in A4_ESCORT.items()}, {T(*k): n / 3 for k, n in A4_ESCORT.items()}
    group = {T(*k): n for k, n in A4_GROUP.items()}
    whole, _, secs = graybox.fluid(body, one, group)
    part, _, secs3 = graybox.fluid(body, third, group)
    cut = 900 / cost_of(group)
    truck = body('CNV_ConvoyTruck')
    fire = sum(offline.dps(body.s, body(t), truck) * n for t, n in group.items())
    return dict(group_cost=cost_of(group), truck_seconds=truck.max_hp / fire,
                waves_three=a4_run(body, (3,), 1.0), waves_two=a4_run(body, (2,), 1.0),
                waves_three_900=a4_run(body, (3,), cut), waves_two_900=a4_run(body, (2,), cut),
                waves_three_900_twice=a4_run(body, (3,), cut, resupply=(2, 4)),
                max_scale_three=biggest(survives((3,))), max_scale_two=biggest(survives((2,))),
                max_scale_alternating=biggest(survives((3, 2))),
                whole_left=sum(whole.values()) / sum(one.values()), whole_secs=secs,
                third_left=sum(part.values()) / sum(third.values()), third_secs=secs3)


J7_ROUTES = {'步兵多': {('动员兵', '苏联'): 10, ('铁锤坦克', '苏联'): 1, ('天启坦克', '苏联'): 0.5},
             '机甲多': {('动员兵', '苏联'): 4, ('铁锤坦克', '苏联'): 2, ('天启坦克', '苏联'): 1}}
J7_ARMIES = {'武士+杀手': {('帝国武士', '帝国'): 0.5, ('坦克杀手', '帝国'): 0.5}, '杀手': {('坦克杀手', '帝国'): 1.0},
             '海啸': {('海啸坦克', '帝国'): 1.0}, '天狗+海啸': {('天狗机甲', '帝国'): 0.5, ('海啸坦克', '帝国'): 0.5},
             '武士+海啸': {('帝国武士', '帝国'): 0.5, ('海啸坦克', '帝国'): 0.5}}
J7_TIMINGS = {'同时到': (0, 0, 0), '先一路，另两路晚 15 秒': (0, 15, 15), '三路各差 15 秒': (0, 15, 30),
              '先一路，另两路晚 45 秒': (0, 45, 45)}


def j7_counter(s, body, army_cost=10000.0):
    """J7 甲: how big must the last counterattack be (three routes, as the card's jammers leave them) for an army
    waiting under the tower to be unable to eat it? An army of cost `army_cost` of the best Empire mix (the player
    picks) meets three equal routes arriving `timing` seconds apart; the largest counterattack (total cost, as a
    multiple of the army's) it still beats with half left, per route mix and timing, and which army it was."""
    out = {}
    for rname, route in J7_ROUTES.items():
        unit = {T(*k): n for k, n in route.items()}
        for tname, times in J7_TIMINGS.items():
            best = (0.0, None)
            for aname, mix in J7_ARMIES.items():
                army = {T(*k): army_cost * f / (offline.cost(T(*k)) or 500) for k, f in mix.items()}

                def holds(m):
                    g = {t: n * m for t, n in unit.items()}
                    a, b, _ = graybox.fluid(body, army, g, later=[(at, g) for at in times[1:]])
                    return sum(b.values()) < 0.05 and sum(a.values()) / sum(army.values()) >= graybox.HALF
                m = biggest(holds, lo=0.01, hi=64.0)
                if m and m > best[0]:
                    best = (m, aname)
            out[(rname, tname)] = dict(ratio=3 * best[0] * cost_of(unit) / army_cost, army=best[1])
    return out


def leap_range():
    """The Sickle's leap, from the SDK data: its LeapWeapon's AttackRange (the unit's StartAbilityRange says the same)."""
    text = open(os.path.join(simunits.SAGEXML, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    at = text.index('id="SovietAntiInfantryVehicleLeapWeapon"')
    return float(re.search(r'AttackRange="([\d.]+)"', text[at:]).group(1))


S1_ESCORT = {('守护者坦克', '盟军'): 5, ('维和步兵', '盟军'): 4}        # 3 tow Guardians + 2 free ones, 4 Peacekeepers (a stand-in size)
S1_HOOK = 300.0                                                      # the card's number (confirmed)
S1_CONVOY_SPEED = 50.0                                               # the truck's (the tow is slowed to it)


def s1_geometry(s, body):
    """S1 甲, the geometry table. Hook tank d behind the ice edge, thin band w, tow Guardian g past its outer edge.
    Hook reaches: d + w + g <= 300. The escort cannot shoot the hook tank: d + w > its range. Shore fire cannot reach
    a Guardian from the ice edge: w + g > the player's longest range. The Sickle leaps `leap` (its data): a band the
    hook reaches across is never wider than the leap, so w can never block the jump. `window` = seconds a tow
    Guardian passing at its closest g_near = g_max / 2 stays in the hook's reach (a chord of the 300 circle)."""
    guard, peace = body(T('守护者坦克', '盟军')), body(T('维和步兵', '盟军'))
    enemy = max(w['range'] for b in (guard, peace) for w in b.weapons)
    mine = max(w['range'] for n in ('防空步兵', '镰刀机甲') for w in body(T(n, '苏联')).weapons)
    leap, d, rows = leap_range(), 10.0, []
    for w in (160, 180, 200, 220, 250, 280):
        gmax = S1_HOOK - d - w
        near = (d + w + gmax / 2)
        rows.append(dict(w=w, g_max=gmax, hook_safe=d + w > enemy, shore_blocked=w > mine, leap_blocked=w > leap,
                         window=2 * math.sqrt(S1_HOOK ** 2 - near ** 2) / S1_CONVOY_SPEED))
    return dict(rows=rows, d=d, leap=leap, enemy_range=enemy, my_range=mine, hook=S1_HOOK,
                no_w_blocks_leap=all(not r['leap_blocked'] for r in rows if r['g_max'] >= 0))


def s1_natural(s, body):
    """S1 甲 natural plays. Hooking the truck: the cursor says no (no fight at all); with d + w > 150 the escort
    cannot answer it either. The Sickle leaps the band and lands on thick ice: one Sickle against a Guardian.
    Infantry walks the band (thin ice sinks only vehicles) and fights the escort: the k* of the player's best
    types against the whole escort, against what can actually come to the band (the Guardians cannot cross it:
    only the Peacekeepers), against a cape's share, and what a chase on foot costs in time; and the hook tank's
    (stand-in: a Guardian's body, the hook tank has no data) life when Peacekeepers come ashore for it."""
    escort = {T(*k): n for k, n in S1_ESCORT.items()}
    guard, peace = T('守护者坦克', '盟军'), T('维和步兵', '盟军')
    flak, sickle = T('防空步兵', '苏联'), T('镰刀机甲', '苏联')
    cape = {guard: 3, peace: 2}
    ashore = {peace: escort[peace]}
    lone_guard = {guard: 1}
    armies = {'防空步兵': flak, '镰刀机甲': sickle, '防空步兵 65% + 镰刀 35%': {flak: 0.65, sickle: 0.35}}
    k = lambda mix, foe: graybox.kstar(body, mix, foe)
    table = {n: dict(whole=k(m, escort), cape=k(m, cape), ashore=k(m, ashore), lone=k(m, lone_guard))
             for n, m in armies.items()}
    truck = body('CNV_ConvoyTruck')
    hook_tank_hp = body(guard).max_hp
    peace_on_guard = offline.dps(s, body(peace), body(guard))
    best = {col: min(row[col] for row in table.values()) for col in ('whole', 'cape', 'ashore', 'lone')}
    return dict(table=table, best=best, escort_cost=cost_of(escort), ashore_cost=cost_of(ashore),
                whole_need_cost=best['whole'] * cost_of(escort), ashore_need_cost=best['ashore'] * cost_of(ashore),
                sickle_vs_guard=offline.dps(s, body(sickle), body(guard)), guard_vs_sickle=offline.dps(s, body(guard), body(sickle)),
                flak_kills_truck=truck.max_hp / offline.dps(s, body(flak), truck),
                infantry_speed=body(flak).speed, convoy_speed=S1_CONVOY_SPEED, sickle_speed=body(sickle).speed,
                hook_tank_seconds={n: hook_tank_hp / (n * peace_on_guard) for n in (2, 4, 6)},
                walk_to_range={g: (10.0 + 200 + g - body(peace).weapons[0]['range']) / body(peace).speed for g in (0, 50, 100)})


def s1_ablate(s, body):
    """S1 甲, take one thing away. No thin ice: the Guardians come ashore too, so the player fights the whole escort
    (k* of the best mix); with the ice only the Peacekeepers can come, and the sunk Guardian costs nothing. No cable:
    the truck drives alone and the hook takes it from any cape (the puzzle is gone)."""
    n = s1_natural(s, body)
    return dict(with_ice=n['best']['ashore'], without_ice=n['best']['whole'], lone=n['best']['lone'],
                with_ice_cost=n['ashore_need_cost'], without_ice_cost=n['whole_need_cost'])


def s1_capes(s, body):
    """S1 甲, cape ambush against staying put. The lane touches `capes` capes and the player has `tanks` hook tanks
    (the flow gives three). One tank at every cape (static) catches a Guardian wherever the lane goes when
    tanks >= capes; the optimum can only move round to round when capes > tanks, or when a tank cannot follow the
    convoy: a hook tank slower than the convoy never gets from one cape to the next in time, one as fast as the
    Hammer (75) does when the shore way is under 1.5 x the lane. A hook is one at a time: tow Guardians `gap` apart
    in the column are `gap / speed` seconds apart at a cape."""
    return dict(tanks=3, capes={'简单': 4, '普通': 3}, trucks=(2, 3), convoy_speed=S1_CONVOY_SPEED,
                hammer_speed=body(T('铁锤坦克', '苏联')).speed, gap_seconds={g: g / S1_CONVOY_SPEED for g in (150, 300, 450)},
                relocate_ratio=body(T('铁锤坦克', '苏联')).speed / S1_CONVOY_SPEED)


J7_BASE = (0, 15, 30)                                   # near, middle, far valley: seconds more than the near one, jammers aside
J7_PER = 15.0                                           # seconds a jammer's aura adds to a Soviet pass (infantry, speed 50)


def j7_pick(left, base=J7_BASE, per=J7_PER, jam=True):
    """The valley the reinforcement takes (card 甲): the least 'way seconds + jammers left x 15', a tie to the nearer.
    `jam=False`: jammers do not slow the Soviets (the ablation)."""
    score = [base[i] + (per * left[i] if jam else 0.0) for i in range(3)]
    return min(range(3), key=lambda i: (score[i], i))


def j7_table():
    """For each starting count of jammers per valley (near, middle, far), the fewest jammers to pull, and which, so
    that the reinforcement takes each valley: None when no amount of pulling there alone (or anywhere) does."""
    out = {}
    for n0 in [(3, 3, 3), (3, 2, 2), (3, 3, 2), (2, 2, 2), (2, 2, 3), (2, 3, 3)]:
        best = {}
        for r in itertools.product(*[range(x + 1) for x in n0]):
            v = j7_pick(tuple(a - b for a, b in zip(n0, r)))
            if v not in best or sum(r) < sum(best[v]):
                best[v] = r
        out[n0] = dict(start=j7_pick(n0), pull={v: best.get(v) for v in range(3)},
                       all_cleared=j7_pick((0, 0, 0)), early_by=J7_PER * n0[0])
    return out


def j7_pursuit(n0, moves=1, waves=6, follow=False):
    """After each wave the Soviets move `moves` jammers into the valley where your army stands, from the quickest
    other valley that has one. A static ambusher (stays where the first wave came) meets the waves until the first
    one that takes another valley (`static_meets`). With `follow` the army goes where the last wave went (the
    minimap blip shows it) and the picks are what the waves do against that player: the optimum moves whenever the
    picks change."""
    n, picks, stand = list(n0), [], j7_pick(n0)
    for _ in range(waves):
        picks.append(j7_pick(n))
        if follow:
            stand = picks[-1]
        for _ in range(moves):
            donors = [i for i in range(3) if i != stand and n[i] > 0]
            if not donors:
                break
            give = min(donors, key=lambda i: (J7_BASE[i] + J7_PER * n[i], i))
            n[give] -= 1
            n[stand] += 1
    first = j7_pick(n0)
    static = next((i for i, v in enumerate(picks) if v != first), len(picks))
    return dict(stand=first, picks=picks, static_meets=static,
                changes=sum(1 for a, b in zip(picks, picks[1:]) if a != b))


def j7_grind(body, h, waves, resupply=False, column=False, army_cost=10000.0, route='步兵多'):
    """An Empire army (half Samurai, half Tank Killers) of `army_cost` meets `waves` Soviet waves, each `h` x the
    army's cost. Head-on in a cleared valley (no base to top it up): resupply False. At the cleared valley's mouth
    with the base behind it: resupply True (topped up to full after each wave) and column True (the wave comes
    out of the valley in three batches 10 s apart). Returns the shares left after each wave, the wave that
    wiped it out or None."""
    mine = {T('帝国武士', '帝国'): 0.5, T('坦克杀手', '帝国'): 0.5}
    army = {t: army_cost * f / (offline.cost(t) or 500) for t, f in mine.items()}
    unit = {T(*k): n for k, n in J7_ROUTES[route].items()}
    scale = h * army_cost / cost_of(unit)
    left, shares = dict(army), []
    for w in range(1, waves + 1):
        wave = {t: n * scale for t, n in unit.items()}
        if column:
            part = {t: n / 3 for t, n in wave.items()}
            left, rest, _ = graybox.fluid(body, left, part, later=[(10.0, part), (20.0, part)])
        else:
            left, rest, _ = graybox.fluid(body, left, wave)
        if sum(rest.values()) >= 0.05 or sum(left.values()) < 0.05:
            return shares, w
        shares.append(sum(left.values()) / sum(army.values()))
        if resupply:
            left = dict(army)
    return shares, None


def j7_valley_choice(s, body):
    """J7 甲: the route table, the pursuit, the head-on grind against the ambush at the mouth, the ablation."""
    pick, pursuit, follow = j7_table(), {}, {}
    for n0 in [(3, 3, 3), (3, 2, 2), (2, 2, 2)]:
        for moves in (1, 2):
            pursuit[(n0, moves)] = j7_pursuit(n0, moves)
            follow[(n0, moves)] = j7_pursuit(n0, moves, follow=True)

    def holds(waves, **kw):
        def ok(h):
            shares, dead = j7_grind(body, h, waves, **kw)
            return dead is None and shares[-1] >= graybox.HALF
        return ok
    head = {w: biggest(holds(w), lo=0.05, hi=16.0) for w in (1, 3, 5)}
    mouth = {w: biggest(holds(w, resupply=True, column=True), lo=0.05, hi=16.0) for w in (1, 3, 5)}
    mover = body(T('帝国武士', '帝国')).speed
    valley_seconds = {n: 1500.0 / body(T('动员兵', '苏联')).speed + J7_PER * n for n in (0, 1, 2, 3)}
    off = {n0: [j7_pick(n0, jam=False)] for n0 in [(3, 3, 3), (2, 2, 2)]}
    return dict(pick=pick, pursuit=pursuit, follow=follow, head_on=head, at_mouth=mouth, mover_speed=mover,
                reach={n: mover * t for n, t in valley_seconds.items()}, jam_off=off)


def facts():
    s, body = world()
    return dict(a4_streets=a4_streets(s, body), a4_types=a4_street_types(s, body), a4_plaza=a4_plaza(s, body), a4_cold=a4_cold(s, body),
                s1=s1_lake(s, body), j7=j7_valleys(s, body), a4_waves=a4_waves(s, body), j7_counter=j7_counter(s, body),
                s1_geometry=s1_geometry(s, body), s1_natural=s1_natural(s, body), s1_ablate=s1_ablate(s, body),
                s1_capes=s1_capes(s, body), j7_valley=j7_valley_choice(s, body))


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
    ] + recheck_lines(f) + new_card_lines(f)


def new_card_lines(f):
    """The second-round cards (S1 甲 and J7 甲, redrawn 2026-10-30)."""
    g, n, a, c, v = f['s1_geometry'], f['s1_natural'], f['s1_ablate'], f['s1_capes'], f['j7_valley']
    out = [
        f'S1甲几何 钩 {g["hook"]:g}、镰刀跳 {g["leap"]:g}（武器数据）、护卫射程 {g["enemy_range"]:g}、己方最长 {g["my_range"]:g}；'
        f'磁钩站冰边后 {g["d"]:g}，薄冰带宽 w → 守护者离外沿最多 g：' + '；'.join(
            f'w={r["w"]} g≤{r["g_max"]:g} 窗口{r["window"]:.1f}秒{"" if r["shore_blocked"] else "（岸边步兵打得到）"}' for r in g['rows']) +
        f'；w 能不能挡住跳：{"不能（钩得到就跳得过）" if g["no_w_blocks_leap"] else "能"}',
        f'S1甲自然打法 镰刀 vs 守护者 {n["sickle_vs_guard"]:.1f}/秒，守护者 vs 镰刀 {n["guard_vs_sickle"]:.0f}/秒；步兵 {n["infantry_speed"]:g} = 车队 '
        f'{n["convoy_speed"]:g}（镰刀 {n["sickle_speed"]:g}）；防空步兵 {n["flak_kills_truck"]:.0f} 秒打死一辆车',
        'S1甲 k*（整队护卫 5 守护者 + 4 维和 = {0:g}；岬角一组 3+2；只有上得来的 4 个维和；一辆守护者）：'.format(n['escort_cost']) + '；'.join(
            f'{k} ' + '、'.join(f'{lab} {graybox.fmt(row[col])}' for lab, col in (('整队', 'whole'), ('一组', 'cape'), ('维和', 'ashore'), ('一辆', 'lone')))
            for k, row in n['table'].items()),
        f'S1甲 步兵上冰追要 {n["whole_need_cost"]:.0f} 造价的兵（整队，赢了剩一半）；钩守护者拽进薄冰后只要对付上岸的维和约 {n["ashore_need_cost"]:.0f}；'
        f'没有冰则整队 k* {a["without_ice"]:.2f}，有冰 {a["with_ice"]:.2f}',
        f'S1甲 磁钩坦克（拿守护者的血当替身）被 2/4/6 个维和围：' + '、'.join(f'{k}个 {t:.0f}秒' for k, t in n['hook_tank_seconds'].items()) +
        '；维和从守护者那条线走到射程内：' + '、'.join(f'g={k} {t:.1f}秒' for k, t in n['walk_to_range'].items()),
        f'S1甲 岬角：磁钩 {c["tanks"]} 台，岬角 简单 {c["capes"]["简单"]}、普通 {c["capes"]["普通"]}，卡车 {c["trucks"][0]}～{c["trucks"][1]}；'
        f'磁钩要追上车队至少得和车队一样快（{c["convoy_speed"]:g}），像铁锤（{c["hammer_speed"]:g}）快 {c["relocate_ratio"]:.1f} 倍；'
        '两辆拖车守护者相隔 150/300/450 在同一个岬角差 ' + '/'.join(f'{t:.0f}' for t in c['gap_seconds'].values()) + ' 秒',
        'J7甲 援军选谷 拔掉几辆才走某条（初始每谷几辆 → 走近/中/远；None=拔多少都走不到）：' + '；'.join(
            f'{n0} 起点走{"近中远"[r["start"]]}，→中 {r["pull"][1]}，→远 {r["pull"][2]}，全拔后走{"近中远"[r["all_cleared"]]}且早到 {r["early_by"]:g} 秒'
            for n0, r in v['pick'].items()),
        'J7甲 苏联每波往你那条谷挪干扰车：守一处只碰到第 1 波（之后他们走别的谷）；跟着闪点追，援军选谷依次：' + '；'.join(
            f'{n0} 挪{m}辆 {"".join("近中远"[i] for i in r["picks"])}' for (n0, m), r in v['follow'].items()),
        f'J7甲 看到闪点从一条谷口赶到另一条谷口走得起：谷里要 1500/50 + 15×剩余干扰车 秒，我方步兵 {v["mover_speed"]:g} 能走 ' +
        '、'.join(f'{k}辆 {d:.0f}' for k, d in v['reach'].items()) + '（谷口相隔比这小就追得上）',
        'J7甲 一条谷直冲（谷拆通、没有基地补兵）和守在谷口（基地补满、援军三批出谷）各能吃下几倍大军造价的援军：直冲 ' + '、'.join(
            f'连来{w}波 {x:.1f}' for w, x in v['head_on'].items()) + '；谷口 ' + '、'.join(f'连来{w}波 {x:.1f}' for w, x in v['at_mouth'].items()),
        f'J7甲 消融：干扰车不拖慢苏联，援军永远走近谷：{ "、".join("近中远"[x[0]] for x in v["jam_off"].values()) }',
    ]
    return out


def shares(r):
    left, died = r
    return '、'.join(f'{x:.0%}' for x in left) + (f'，第 {died} 波磨光' if died else '，五波都撑住')


def recheck_lines(f):
    w, c = f['a4_waves'], f['j7_counter']
    g = w['group_cost']
    out = [
        f'A4甲复算 每街一组 {g:g}：整队护卫打一条街 {w["whole_secs"]:.1f} 秒、剩 {w["whole_left"]:.0%}；分三份各打一组 '
        f'{w["third_secs"]:.1f} 秒、剩 {w["third_left"]:.0%}（磨光）；一组打死一辆车 {w["truck_seconds"]:.1f} 秒',
        f'A4甲复算 巧解每波吃三组（两墙全并）：护卫每波后剩 {shares(w["waves_three"])}；每波吃两组（一墙）：{shares(w["waves_two"])}',
        f'A4甲复算 每街降到 900：每波三组 {shares(w["waves_three_900"])}；每波两组 {shares(w["waves_two_900"])}；'
        f'每波三组、第 2、4 波后各补一次 {shares(w["waves_three_900_twice"])}',
        f'A4甲复算 第 3 波后补一次时，护卫撑满五波的最大一组：每波三组 {w["max_scale_three"] * g:.0f}，每波两组 '
        f'{w["max_scale_two"] * g:.0f}，三两交替 {w["max_scale_alternating"] * g:.0f}',
    ]
    for rname in J7_ROUTES:
        out.append(f'J7甲复算 反扑（{rname}）总造价是塔下大军造价的几倍时，大军刚好还能赢（剩一半）：' + '；'.join(
            f'{t} {c[(rname, t)]["ratio"]:.1f}（{c[(rname, t)]["army"]}）' for t in J7_TIMINGS))
    return out


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
