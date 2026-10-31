r"""Graybox by the simulator (ADR 0011): qualitative, never exact. What it can say: how big an army of ONE unit type
has to be, as a multiple of the enemy's cost, to beat what a stage throws at it -- k*. What it cannot say is written
out ("留给实机"): the economy, the skirmish AI, ranges and micro, every new rule a question card adds.

  python -I -X utf8 experimental/cnv/graybox.py a4              summary (the full text goes to work/logs/graybox_a4.log)
  python -I -X utf8 experimental/cnv/graybox.py a4 --verbose    all of it

k*(P, stage)  P's army costs k x the stage's enemy (everything the walkthrough met in it), both sides fight at once
              as one mass (heterogeneous Lanchester, fluid: each side's fire is split over the targets it can hit in
              proportion to their numbers; range, speed, splash and micro are out, as in offline.ratio). k* is the
              least k where P wins with at least half of its numbers left. inf: P cannot kill some enemy type that
              hurts it (it needs a second unit type), or loses even at KMAX.
平推 (push)   the best single type per stage. k* under EASY (1.5): "不动脑也轻松"; a type that needs more than TOUGH
              (3): the stage asks for more than one unit type or for a plan.
All of it assumes the enemy arrives all at once: the worst case for the player (waves that come apart are easier),
so a stage that is easy here is easy in the game.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]
import offline  # noqa: E402
import simunits  # noqa: E402

EASY = 1.5                                      # k* under this: a push with no thought
TOUGH = 3.0                                     # k* over this: the stage wants more than a push
KMAX = 20.0
HALF = 0.5                                      # a win keeps at least this share of the player's numbers
STEP, HORIZON = 0.25, 900.0                     # seconds
ROOT = os.path.dirname(os.path.dirname(HERE))


class Bodies:
    """Fight numbers of templates, read once: the owners do not matter to Lanchester, only the numbers."""

    def __init__(self, s):
        self.s, self._b = s, {}

    def __call__(self, template):
        if template not in self._b:
            b = self.s.add(f'#graybox {len(self._b)}', template, self.s.foe, 0.0, 0.0)
            b.alive = False
            self._b[template] = b
        return self._b[template]

    def armed(self, template):
        return any(w['dps'] for w in self(template).weapons)


def fluid(body, mine, theirs, later=()):
    """Fluid heterogeneous Lanchester, `mine` {template: n} against `theirs`; returns (what is left of each,
    seconds). A side's fire goes to the enemy types it can hit, in proportion to their numbers. `later`:
    [(second, {template: n})] more of the enemy that join at those seconds (waves coming apart in time)."""
    a, b = dict(mine), dict(theirs)
    pending = sorted(((float(at), dict(g)) for at, g in later), key=lambda p: p[0])
    t = 0.0
    while t < HORIZON:
        while pending and pending[0][0] <= t:
            for e, n in pending.pop(0)[1].items():
                b[e] = b.get(e, 0.0) + n
        if sum(a.values()) < 0.05:
            break
        if sum(b.values()) < 0.05:
            if not pending:
                break
            t = pending[0][0]                   # nobody left to fight until the next wave arrives
            continue
        hurt_a = dict.fromkeys(a, 0.0)
        hurt_b = dict.fromkeys(b, 0.0)
        for fire, foe, hurt in ((a, b, hurt_b), (b, a, hurt_a)):
            for p, n in fire.items():
                if n <= 0:
                    continue
                rate = {e: offline.dps(body.s, body(p), body(e)) for e, m in foe.items() if m > 0}
                rate = {e: r for e, r in rate.items() if r > 0}
                mass = sum(foe[e] for e in rate)
                for e, r in rate.items():
                    hurt[e] += n * r * foe[e] / mass * STEP / body(e).max_hp
        moved = sum(hurt_a.values()) + sum(hurt_b.values())
        for side, hurt in ((a, hurt_a), (b, hurt_b)):
            for e, d in hurt.items():
                side[e] = max(0.0, side[e] - d)
        t += STEP
        if not moved:
            if not pending:
                break
            t = max(t, pending[0][0])
    return a, b, t


def wins(body, mix, enemy, k, cost):
    """An army of cost k x the enemy's, split by `mix` {template: share of the cost}, against `enemy`: (does it win
    with HALF of its numbers left, its share left, seconds)."""
    total = k * sum(cost(t) * m for t, m in enemy.items())
    n = {p: total * f / cost(p) for p, f in mix.items()}
    a, b, t = fluid(body, n, enemy)
    left = sum(a.values()) / sum(n.values())
    return sum(b.values()) < 0.05 and left >= HALF, left, t


def kstar(body, mix, enemy, cost=None):
    """The least k at which an army `mix` ({template: share}, or one template) beats `enemy` {template: n};
    math.inf when it never does; None when the data gives some body no weapon."""
    cost = cost or (lambda t: offline.cost(t) or 500)
    if isinstance(mix, str):
        mix = {mix: 1.0}
    if not all(body.armed(t) for t in list(mix) + list(enemy)):
        return None                             # the data does not give a weapon: unknown, not a win or a loss
    if not wins(body, mix, enemy, KMAX, cost)[0]:
        return math.inf
    lo, hi = 0.0, KMAX
    for _ in range(18):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if wins(body, mix, enemy, mid, cost)[0] else (mid, hi)
    return hi


SHARES = (0.2, 0.35, 0.5)                       # a helper's share of the cost: a push with a little of something else


def best_mix(body, have, enemy):
    """The best army of one main type, or one main plus one helper (SHARES of the cost): (k*, mix)."""
    best = (math.inf, None)
    for p in have:
        for helper in [None] + [q for q in have if q != p]:
            for f in ((0.0,) if helper is None else SHARES):
                mix = {p: 1.0} if helper is None else {p: 1.0 - f, helper: f}
                k = kstar(body, mix, enemy)
                if k is not None and k < best[0]:
                    best = (k, mix)
    return best


def verdict(ks):
    """One word for a stage from its best single-type k* (None: nothing known)."""
    best = min((k for k in ks if k is not None), default=None)
    if best is None:
        return '数据不足'
    return '平推轻松' if best <= EASY else '平推可过但费兵' if best <= TOUGH else '平推不行'


def stages(level):
    """[(stage, {enemy template: n}, {player template: k*}, best k*)] for the plan's walkthrough."""
    s, starts, enemy, have = offline.walk(level)
    body = Bodies(s)
    out = []
    for n, _ in starts:
        e = enemy.get(n, {})
        if not e:
            out.append((n, {}, {}, None, None))
            continue
        ks = {p: kstar(body, p, e) for p in sorted(have.get(n, ()))}
        known = [k for k in ks.values() if k is not None]
        k2, mix = best_mix(body, sorted(have.get(n, ())), e)
        out.append((n, e, ks, min(known + [k2]) if known or mix else None, mix))
    return s, out


def fmt(k):
    return '?' if k is None else '打不动' if k == math.inf else f'{k:.2f}'


def report(level, verbose=False):
    s, rows = stages(level)
    lines = [f'{level}（灰盒，旧版走查敌人的并发形态；EASY={EASY}，TOUGH={TOUGH}）']
    summary = []
    for n, e, ks, best, mix in rows:
        if not e:
            lines.append(f'- {n}：没碰上带武器的敌人')
            continue
        total = sum((offline.cost(t) or 500) * m for t, m in e.items())
        v = verdict([best])
        army = '+'.join(f'{offline.label(p)}{f:.0%}' for p, f in mix.items()) if mix else '?'
        summary.append(f'{n} {v}（{army} k*={fmt(best)}）')
        lines.append(f'- {n}：敌人 ' + '，'.join(f'{offline.label(t)}{m}' for t, m in e.items()) +
                     f'（造价 {total}）→ {v}；最好的编成 {army}，k*={fmt(best)}')
        for p, k in sorted(ks.items(), key=lambda q: (q[1] is None, q[1] if q[1] is not None else 0)):
            lines.append(f'    {offline.label(p)}（{offline.cost(p) or "?"}）k*={fmt(k)}')
    lines.append('')
    lines.append('说明：k* = 全押一种兵、总造价是敌军的 k 倍时刚好打赢（剩一半）；射程、速度、溅射、技能、微操、'
                 '经济、遭遇战 AI 都不算，敌人按全部同时到齐算（对玩家最不利）。')
    return '\n'.join(lines), summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('level')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()
    text, summary = report(a.level, a.verbose)
    path = os.path.join(ROOT, 'work', 'logs', f'graybox_{a.level}.log')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(text + '\n')
    print(text if a.verbose else '；'.join(summary) + f'\n（全文 {os.path.relpath(path, ROOT)}）')


if __name__ == '__main__':
    main()
