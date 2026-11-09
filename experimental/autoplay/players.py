r"""The auto players' personalities (ADR 0026 item 4). Each is a seeded random stream deciding from a View only; every
command goes out through Orders, so it is a script line. Randomness is the human's: a reaction that is not the same
second twice, an aim that is a little off, a target picked among the good ones, a mistake now and then.

  idle     does nothing: what the level does by itself (a floor: a level that a player who sits still wins is broken)
  rush     平推: the whole army attack-moves at the nearest enemy it knows of, else goes where the objectives' arrows
           point (escorting the units the arrow marks), else scouts the briefing's sites; no retreat, no kinds
  counter  按兵种克制: each unit picks the enemy it hurts most per second against that enemy's health and armour (what
           the unit's info card says), kills the dangerous first, pulls the wounded back; moves up as a group
  card     照题卡巧解: the level's own plan (plays/<level>.txt, the intended solution) played by someone who is a little
           off: each order's time shifted, now and then forgotten, a destination clicked beside the mark. `sloppy`
           is the same hand with a wide spread

A personality's knobs are in Style; a run gets them from `make(name, rng, brief)`.
"""
import dataclasses
import math
import os
import re

import sim      # autoplay.py loads this file after the simulator, whose import puts the cnv folders on the path
import simunits


def num(t):
    """A time in a script line: seconds, no float noise."""
    return f'{t:.3f}'.rstrip('0').rstrip('.')


def where(p):
    """A ground click as the script writes it."""
    return f'@{p[0]:.0f},{p[1]:.0f}'


@dataclasses.dataclass
class Style:
    think: tuple = (2.0, 5.0)          # seconds between two decisions (uniform)
    aim: float = 40.0                  # a destination is clicked this far (sigma, map units) off the spot
    chase: float = 1500.0              # an enemy this far from the army is not gone after (the army's middle)
    defend: float = 700.0              # counter, with a convoy to keep: enemies this far from the convoy are answered
    near: float = 900.0                # counter: a unit looks at enemies this close
    pullback: float = 0.35             # counter: a unit under this health pulls back when enemies are near
    noise: float = 0.35                # counter: log-normal sigma on a target's score (not a perfect player)
    keep: float = 1.5                  # counter: a unit keeps its target while its score is within this factor of the best
    group: float = 350.0               # counter: the army moves on only when this share (below) is within this of its middle
    share: float = 0.7
    # card
    shift: float = 5.0                 # card: an order's time moves by this much (sigma, seconds)
    slip: float = 0.03                 # card: the share of orders forgotten
    click: float = 50.0                # card: a named destination is clicked this far (sigma) off its mark
    off: float = 0.15                  # card: the share of destinations clicked off the mark at all


class Player:
    name = ''

    def __init__(self, rng, brief, style=None):
        self.rng, self.brief, self.style = rng, brief, style or Style()

    def start(self, s, out):
        """Before the first tick: a personality that plays a plan puts it in here."""

    def interval(self):
        return self.rng.uniform(*self.style.think)

    def decide(self, view, out):
        raise NotImplementedError

    def aim(self, p):
        """A click near the point (the hand's spread)."""
        return (p[0] + self.rng.gauss(0, self.style.aim), p[1] + self.rng.gauss(0, self.style.aim))


class Idle(Player):
    name = 'idle'

    def interval(self):
        return 60.0

    def decide(self, view, out):
        pass


class Moving(Player):
    """What rush and counter share: where the army goes when no enemy is in sight, and the units the arrows mark."""
    escort = False                      # True: the units the level drives (a convoy) come before the arrows

    def start(self, s, out):
        self.lead = 0
        self.looked = set()             # leads looked at

    def goal(self, view):
        """The place the army should be heading for now (None: stay), from the objectives' arrows, the units the level
        moves, the briefing's sites -- in that order, as a human reads the screen."""
        s = view.s
        marks = view.markers()
        for obj, own, places, foes in marks:
            if foes:                    # an arrow on an enemy thing: go there
                near = min(foes, key=lambda b: self.dist(view, b))
                return (near.x, near.y)
        if view.convoy and self.escort:
            return view.centre(view.convoy)
        for obj, own, places, foes in marks:
            if own and places:          # units to take somewhere: go with them
                c = view.centre(own)
                far = max(math.hypot(b.x - c[0], b.y - c[1]) for b in own)
                if far > 500:           # strung out: gather at the middle of them first
                    return c
                return min(places, key=lambda p: math.hypot(p[0] - c[0], p[1] - c[1]))
            if places and not own:
                c = view.centre(view.army) or places[0]
                return min(places, key=lambda p: math.hypot(p[0] - c[0], p[1] - c[1]))
        sites = [q for q in (s.point(n) for n in self.brief.leads) if q]
        if sites:
            c = view.centre(view.army) or sites[0]
            for q in sites[self.lead:]:
                if math.hypot(q[0] - c[0], q[1] - c[1]) < 250.0:
                    self.lead = max(self.lead, sites.index(q) + 1)
            return tuple(sites[self.lead % len(sites)])
        return None

    @staticmethod
    def dist(view, b):
        c = view.centre(view.army) or (b.x, b.y)
        return math.hypot(b.x - c[0], b.y - c[1])

    def wards(self, view, out):
        """The units an arrow marks that are the player's to move (not the level's own convoy) go to the arrow's place."""
        for obj, own, places, foes in view.markers():
            mine = [b for b in own if b.speed > 0 and b not in view.convoy and not b.weapons]
            if mine and places:
                c = view.centre(mine)
                p = min(places, key=lambda q: math.hypot(q[0] - c[0], q[1] - c[1]))
                out.go(mine, p, attack=False)


class Rush(Moving):
    name = 'rush'

    def decide(self, view, out):
        self.wards(view, out)
        army = view.army
        if not army:
            return
        c = view.centre(army)
        foes = sorted(view.foes + view.old, key=lambda f: math.hypot(f.x - c[0], f.y - c[1]))
        foes = [f for f in foes if math.hypot(f.x - c[0], f.y - c[1]) <= self.style.chase]
        units = [f for f in foes if not f.structure or f.body.weapons]
        if units:
            out.go(army, self.aim((units[0].x, units[0].y)))
        elif foes:                       # only buildings: they take no unit by themselves
            out.hit(army, foes[0])
        else:
            g = self.goal(view)
            if g:
                out.go(army, self.aim(g))


class Counter(Moving):
    name = 'counter'
    escort = True                       # a convoy the level asks to keep alive is what this player stays by

    def start(self, s, out):
        super().start(s, out)
        self.pick = {}                  # unit name -> the Foe it was told to attack

    def eff(self, s, u, f):
        """Damage a second the unit does to that enemy: its weapons that can hit it, by the enemy's armour."""
        return sum(w['dps'] * f.body.armor.get(w['type'], simunits.ARMOR_DEFAULT) / 100.0
                   for w in u.weapons if s.can_hit(w, f.body))

    def score(self, view, u, f):
        s = view.s
        e = self.eff(s, u, f)
        if e <= 0:
            return 0.0
        threat = sum(w['dps'] for w in f.body.weapons)
        d = math.hypot(f.x - u.x, f.y - u.y)
        kill = e / max(f.hp, 1.0)                              # how fast the unit takes it down
        weight = (30.0 + threat) * (0.05 if f.structure and not f.body.weapons else 1.0)
        return kill * weight / (1.0 + d / 600.0)

    def decide(self, view, out):
        s = view.s
        st = self.style
        self.wards(view, out)
        army = view.army
        if not army:
            return
        c = view.centre(army)
        a = view.centre(view.convoy) or c                      # the army answers what comes near what it keeps
        reach = st.defend if view.convoy else st.chase

        def close(f):                                          # near what it keeps, or near the army itself
            return min(math.hypot(f.x - a[0], f.y - a[1]), math.hypot(f.x - c[0], f.y - c[1])) <= reach
        foes = [f for f in view.foes if close(f)]
        if not foes:
            ghosts = [f for f in view.old if close(f)]
            self.pick.clear()
            if ghosts:
                g = min(ghosts, key=lambda f: math.hypot(f.x - c[0], f.y - c[1]))
                out.go(army, self.aim((g.x, g.y)))
                return
            g = self.goal(view)
            if g:
                near = [b for b in army if math.hypot(b.x - c[0], b.y - c[1]) <= st.group]
                if view.convoy or len(near) >= st.share * len(army):     # on once gathered (a convoy does not wait)
                    out.go(army, self.aim(g))
                else:
                    out.go(army, self.aim(c))
            return
        rear = view.centre(view.convoy) or tuple(s.point('start') or c)
        for u in army:
            near = [f for f in foes if math.hypot(f.x - u.x, f.y - u.y) <= st.near]
            if u.health < st.pullback * 100.0 and near:
                out.go([u], self.aim(rear), attack=False)
                self.pick.pop(u.name, None)
                continue
            scored = [(self.score(view, u, f) * math.exp(self.rng.gauss(0, st.noise)), f) for f in (near or foes)]
            scored = [x for x in scored if x[0] > 0]
            if not scored:
                out.go([u], self.aim((foes[0].x, foes[0].y)))
                continue
            best, f = max(scored, key=lambda x: x[0])
            held = self.pick.get(u.name)
            keep = next((v for v, g in scored if held is not None and g.name == held.name), None)
            if keep is not None and keep * st.keep >= best:
                continue                                       # it stays on its target
            self.pick[u.name] = f
            out.hit([u], f)


class Card(Player):
    name = 'card'

    def start(self, s, out):
        """The plan's own lines, each a little off, in the run's script from the first second."""
        path = self.brief.plan
        if not path or not os.path.exists(path):
            return
        st = self.style
        for raw in re.split(r'[;\n]', open(path, encoding='utf-8').read()):
            line = raw.split('#')[0].strip()
            if not line or line in ('不动', '不打', '高地不挡') or line.startswith('自动打掉'):
                continue                # the run's own switches (Sim reads them at its start): not a player's order
            time, rest = line.split(None, 1)
            if self.rng.random() < st.slip:
                continue
            if '+' in time and not re.fullmatch(r'[\d:.]+', time):          # <flag>+<time>: the flag's own time shifted
                flag, _, delta = time.rpartition('+')
                at = f'{flag}+{num(max(0.0, sim.seconds(delta) + self.rng.gauss(0, st.shift)))}'
            else:
                at = num(max(1.0, sim.seconds(time) + self.rng.gauss(0, st.shift)))
            out.push(at, self.click_off(s, rest))

    def click_off(self, s, rest):
        """A named destination clicked beside its mark now and then (派 / 走 who 去 place)."""
        st = self.style
        m = re.match(r'(派|走) (.+) 去 (.+)$', rest)
        if m and self.rng.random() < st.off:
            p = s.point(m.group(3).strip())
            if p is not None and not m.group(3).strip().startswith('@'):
                q = (p[0] + self.rng.gauss(0, st.click), p[1] + self.rng.gauss(0, st.click))
                return f'{m.group(1)} {m.group(2)} 去 {where(q)}'
        return rest

    def interval(self):
        return 1e9

    def decide(self, view, out):
        pass


class Sloppy(Card):
    name = 'card_sloppy'

    def __init__(self, rng, brief, style=None):
        super().__init__(rng, brief, style or Style(shift=12.0, slip=0.12, click=120.0, off=0.5))


class Tight(Card):
    name = 'card_tight'

    def __init__(self, rng, brief, style=None):
        super().__init__(rng, brief, style or Style(shift=2.0, slip=0.0, click=30.0, off=0.05))


PERSONALITIES = {'idle': Idle, 'rush': Rush, 'counter': Counter, 'card_tight': Tight, 'card': Card,
                 'card_sloppy': Sloppy}


def make(name, rng, brief, style=None):
    return PERSONALITIES[name](rng, brief, style)
