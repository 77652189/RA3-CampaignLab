r"""Every way a level could go, without running it (the plan simulator's static half, sim.py the running one): which
scripts can ever fire, so which phases can be reached, whether the level can be won and lost, which objectives can
be done -- and the wiring: flags, timers and counters waited on that no script sets.

What can happen is grown to a fixed point over the mission as built (parts.merged): a flag's possible values (0 at
the start, and each value a script that can fire sets), the timers some firable script starts, the counters one
changes, the objects that are there or some firable script makes, the objectives' statuses. A script can fire when
each of its conditions could hold, each taken alone (more than can really happen: two conditions that never hold at
once still pass). The world's own conditions -- a named object destroyed, one in an area, a count of a type -- could
hold whenever the object can be there: the player can take it anywhere, kill anything. So a script reported never
firing really never fires; one reported firing might still never fire in play (sim.py shows how it goes).

  python -I -X utf8 experimental/cnv/simstatic.py <level> [--check <check>]
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import parts  # noqa: E402
import sim  # noqa: E402

LEVEL_NAMES = ('easy', 'normal', 'hard')
CREATES = ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION')


class Reach:
    def __init__(self, mm, level):
        self.mm, self.level = mm, level
        self.flags = {}                         # name -> possible values
        self.timers, self.counters, self.set_to = set(), {}, {}   # counters: name -> {'+', '-'}; set_to: values
        self.objects = {o.name for o in list(getattr(mm.map, 'OBJECTS', [])) + mm.objects if o.name}
        self.templates = {o.template.lower() for o in list(getattr(mm.map, 'OBJECTS', [])) + mm.objects}
        self.status = {}                        # objective -> possible statuses
        self.fires = set()
        self.makers = {mm.map.PLAYERS['p1']} | {a[0] for s in mm.scripts for n, *a in s.do
                                                if n in ('UNIT_AI_TRANSFER_ALL', 'SKIRMISH_AI_MAKE_BASE')}
        scripts = [s for s in mm.scripts if s.levels[level]]
        grew = True
        while grew:
            grew = False
            for s in scripts:
                if s.name not in self.fires and all(self.could(c) for c in s.when):
                    self.fires.add(s.name)
                    for name, *a in s.do:
                        self.effect(name, a)
                    grew = True
        self.scripts = scripts

    def values(self, f):
        return self.flags.get(f, {0})

    def counter_could(self, name, op, v):
        ch = self.counters.get(name, set())
        vals = {0} | self.set_to.get(name, set())
        if any(sim.CMP[op](x, v) for x in vals):
            return True
        if '+' in ch and op in (2, 3, 4, 5) and v >= 0:
            return True
        if '-' in ch and op in (0, 1, 2, 5):
            return True
        return False

    def could(self, c):
        c = list(c)
        neg = c and c[-1] == parts.NOT
        name, a = c[0], (c[1:-1] if neg else c[1:])
        if name == 'FLAG':
            vals = self.values(a[0])
            return any(v != int(a[1]) for v in vals) if neg else int(a[1]) in vals
        if neg:
            return True                         # not yet / not there: possible somewhere along the way
        if name == 'TIMER_EXPIRED':
            return a[0] in self.timers
        if name == 'COUNTER':
            return self.counter_could(a[0], a[1], a[2])
        if name in ('NAMED_DESTROYED', 'NAMED_NOT_DESTROYED', 'NAMED_INSIDE_AREA', 'NAMED_OUTSIDE_AREA',
                    'UNIT_HEALTH', 'NAMED_ATTACKED_BY_PLAYER'):
            return a[0] in self.objects
        if name in ('NAMED_OWNED_BY_PLAYER', 'NAMED_DISCOVERED'):
            return a[1] in self.objects
        if name in ('PLAYER_HAS_OBJECT_COMPARISON', 'PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA'):
            needs = sim.CMP[a[1]](0, a[2]) is False
            # the player and a skirmish AI make things in play no script makes (an engineer's ice, a factory's
            # tanks): theirs could be there
            return not needs or a[3].lower() in self.templates or a[0] in self.makers
        return True

    def effect(self, name, a):
        if name == 'SET_FLAG':
            self.flags.setdefault(a[0], {0}).add(int(a[1]))
        elif name == 'SET_MILLISECOND_TIMER':
            self.timers.add(a[0])
        elif name == 'SET_COUNTER':
            self.set_to.setdefault(a[0], set()).add(a[1])
        elif name in ('INCREMENT_COUNTER', 'DECREMENT_COUNTER'):
            self.counters.setdefault(a[1], set()).add('+' if (name == 'INCREMENT_COUNTER') == (a[0] > 0) else '-')
        elif name in ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', 'SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER',
                      'SET_PLAYER_MONEY_TO_COUNTER'):
            k = a[1] if name != 'SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER' else a[2]
            self.counters.setdefault(k, set()).update('+-')
        elif name in CREATES:
            self.objects.add(a[0])
            self.templates.add(a[1].lower())
        elif name == 'SET_MISSION_OBJECTIVE_STATUS':
            self.status.setdefault(a[0], set()).add(a[1])


def wiring(mm):
    """Flags, timers, counters some condition waits on that no script (firable or not) ever sets."""
    set_f, set_t, set_c = set(), set(), set()
    for s in mm.scripts:
        for name, *a in s.do:
            if name == 'SET_FLAG':
                set_f.add(a[0])
            elif name == 'SET_MILLISECOND_TIMER':
                set_t.add(a[0])
            elif name in ('SET_COUNTER',):
                set_c.add(a[0])
            elif name in ('INCREMENT_COUNTER', 'DECREMENT_COUNTER'):
                set_c.add(a[1])
            elif name in ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', 'SET_PLAYER_MONEY_TO_COUNTER'):
                set_c.add(a[1])
            elif name == 'SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER':
                set_c.add(a[2])
    out = []
    for s in mm.scripts:
        for c in s.when:
            c = [x for x in c if x != parts.NOT]
            if c[0] == 'FLAG' and c[1] not in set_f and int(c[2]) != 0:
                out.append(f'{s.name}: 等旗标 {c[1]} = {c[2]}，没有脚本设它')
            elif c[0] == 'TIMER_EXPIRED' and c[1] not in set_t:
                out.append(f'{s.name}: 等计时 {c[1]}，没有脚本开它')
            elif c[0] == 'COUNTER' and c[1] not in set_c and not sim.CMP[c[2]](0, c[3]):
                out.append(f'{s.name}: 等计数 {c[1]}，没有脚本改它')
    return sorted(set(out))


def report(m, t=None):
    """The lines: per difficulty, what can never happen; the wiring once."""
    mm = parts.merged(m, t)
    tag = next((re.match(r'CNV (\w+) - ', s.name).group(1) for s in mm.scripts if re.match(r'CNV (\w+) - ', s.name)),
               None)
    out, seen = [], {}
    for lv in range(3):
        r = Reach(mm, lv)
        # a cap of 0 (plan 上限: none at all) is never lifted: its 'off' script waits for fewer than 0 -- as meant
        never = [s.name for s in r.scripts if s.name not in r.fires and not
                 (s.name.endswith(' off') and any(c[0] == 'PLAYER_HAS_OBJECT_COMPARISON' and c[2] == 0 and c[3] == 0
                                                  for c in s.when))]
        phases = sorted({f for f in {f for s in mm.scripts for n, *a in s.do if n == 'SET_FLAG'
                                      for f in [a[0]]} if tag and re.fullmatch(f'CNV_{tag}_Phase_\\d+', f)})
        lost_phases = [f for f in phases if 1 not in r.values(f)]
        ends = [s for s in r.scripts if s.name in m.endings]
        won = [s.name for s in ends if s.name in r.fires and any(n == 'SET_FLAG' and a[0] == sim.WON
                                                                 for n, *a in s.do)]
        lose = [s.name for s in r.scripts if s.name in r.fires and any(n == 'SET_FLAG' and a[0] == sim.LOST
                                                                       for n, *a in s.do)]
        mains = [g.name for g in m.objectives if not g.bonus]
        ticked = {a[0] for s in mm.scripts for n, *a in s.do if n == 'SET_MISSION_OBJECTIVE_STATUS' and a[1] == 2}
        undone = [g for g in mains if g in ticked and 2 not in r.status.get(g, set())]
        unticked = [g for g in mains if g not in ticked]
        lines = []
        lines.append('能赢' if won else '问题：赢不了，没有一条胜利脚本能触发')
        lines.append('能输' if lose else '注意：输不了，没有一条失败脚本能触发（没有失败条件，或者接不上）')
        if lost_phases:
            lines.append('问题：永远到不了的段：' + '、'.join(lost_phases))
        if undone:
            lines.append('问题：永远完成不了的主目标：' + '、'.join(undone))
        if unticked:
            lines.append('问题：没有脚本给它打勾的主目标（赢的时候也不打）：' + '、'.join(unticked))
        if never:
            lines.append(f'永远触发不了的脚本 {len(never)} 条：' + '；'.join(never[:12]) + ('……' if len(never) > 12 else ''))
        key = tuple(lines)
        if key in seen:
            seen[key].append(LEVEL_NAMES[lv])
            continue
        seen[key] = [LEVEL_NAMES[lv]]
    for lines, lvs in seen.items():
        out.append(f'[{"/".join(lvs)}] ' + lines[0] + '；' + lines[1])
        out += ['  ' + x for x in lines[2:]]
    w = wiring(mm)
    out.append('接线：' + ('没发现等了却没人设的旗标、计时、计数' if not w else f'{len(w)} 处'))
    out += ['  ' + x for x in w[:20]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--check', default='')
    a = ap.parse_args()
    import build
    m, t, _ = build.resolve(a.name, a.check)
    print('\n'.join(report(m, t)))


if __name__ == '__main__':
    main()
