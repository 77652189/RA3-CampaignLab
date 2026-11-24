"""A toy world for the proxy player's unit tests: implements proxy/world.py's World with nothing from the game.

Flat ground, straight-line moves, damage per frame = dps / 15 x (2 when the target's kind is one the shooter is
made for, else 0.5). Enemy spawners (kindof SPAWNER) make a unit every `every` frames up to `cap` alive; enemy units
walk at the player's home and shoot whatever they see on the way. The player's units shoot what they were told to,
or the nearest enemy in range when idle; they heal at home. One production queue, paid on order. None of these
numbers is the game's -- they only make the decision loop observable. The real world is CampaignLab's simulator
(an adapter there, after engine line A's rules R1-R7).
"""
import dataclasses
import math

from proxy import world as pw

FPS = 15


@dataclasses.dataclass
class Spec:
    kindof: frozenset
    hp: float
    cost: int = 0
    speed: float = 0.0               # per frame
    sight: float = 300.0
    range: float = 150.0
    dps: float = 0.0
    good_against: frozenset = frozenset()
    seconds: float = 5.0
    powers: tuple = ()
    spawn: tuple = None              # (template, every frames, cap alive)


@dataclasses.dataclass
class Ent:
    id: int
    owner: str
    template: str
    spec: Spec
    x: float
    y: float
    hp: float
    order: tuple = None              # ('move', (x, y)) | ('attack', id)
    timer: int = 0


def _d(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


class FakeWorld:
    def __init__(self, specs, home=(0.0, 0.0), money=0, income=0.0, offers=(), leads=(), heal=0.02,
                 base_sight=400.0, me='Player', enemy='Enemy'):
        self.specs, self.home, self.money, self.income = specs, home, float(money), income
        self.offer_names, self.leads, self.heal = list(offers), list(leads), heal
        self.base_sight, self.me, self.enemy = base_sight, me, enemy
        self.ents = {}
        self.frame = 0
        self.next_id = 1
        self.queue = []                  # [(template, ready frame)]
        self.powers = []                 # (frame, unit id, power) the world took
        self.dead = []                   # (frame, template, owner)

    def add(self, template, owner, x, y):
        s = self.specs[template]
        e = Ent(self.next_id, owner, template, s, x, y, s.hp)
        self.ents[e.id] = e
        self.next_id += 1
        return e

    # --- World ---------------------------------------------------------------------------------------------------
    def observe(self):
        mine = [e for e in self.ents.values() if e.owner == self.me]
        units = [e for e in mine if 'STRUCTURE' not in e.spec.kindof]

        def visible(e):
            if math.hypot(e.x - self.home[0], e.y - self.home[1]) <= self.base_sight:
                return True
            return any(_d(e, u) <= u.spec.sight for u in units)

        seen = [pw.Thing(e.id, e.owner, e.template, kindof=e.spec.kindof, x=e.x, y=e.y, value=e.spec.cost,
                         hits=frozenset({'ground'}) if e.spec.dps else frozenset())
                for e in self.ents.values() if e.owner != self.me and visible(e)]
        return pw.Observation(
            frame=self.frame, me=self.me, money=int(self.money), home=self.home,
            mine=[pw.Mine(e.id, e.template, e.spec.kindof, e.x, e.y, e.hp, e.spec.hp, e.spec.cost, e.spec.range,
                          e.spec.sight, e.spec.good_against, e.spec.powers, busy=e.order[0] if e.order else '')
                  for e in units],
            seen=seen, enemies=frozenset({self.enemy}), leads=list(self.leads),
            offers=[pw.Offer(t, self.specs[t].kindof, self.specs[t].cost, self.specs[t].good_against,
                             self.specs[t].seconds) for t in self.offer_names])

    def issue(self, order):
        if order.kind == 'build':
            s = self.specs.get(order.template)
            if order.template not in self.offer_names or self.money < s.cost:
                return False
            self.money -= s.cost
            start = max([self.frame] + [r for _, r in self.queue[-1:]])
            self.queue.append((order.template, start + round(s.seconds * FPS)))
            return True
        units = [self.ents.get(i) for i in order.units]
        if not units or any(u is None or u.owner != self.me for u in units):
            return False
        if order.kind in ('move', 'attack_move'):     # attack_move: fight what is in range, else walk on
            for u in units:
                u.order = (order.kind, order.pos)
        elif order.kind == 'attack':
            if order.target not in self.ents:
                return False
            for u in units:
                u.order = ('attack', order.target)
        elif order.kind == 'power':
            self.powers.append((self.frame, order.units[0], order.power))
        else:
            return False
        return True

    def step(self, frames):
        for _ in range(frames):
            self._frame()

    def losses(self):
        return [pw.Loss(f, owner, t, pw.kind_of(self.specs[t]), self.specs[t].cost) for f, t, owner in self.dead]

    # --- one frame -------------------------------------------------------------------------------------------------
    def _frame(self):
        self.frame += 1
        self.money += self.income
        while self.queue and self.queue[0][1] <= self.frame:
            t, _ = self.queue.pop(0)
            self.add(t, self.me, self.home[0] + 30 * (self.next_id % 5), self.home[1] + 30)
        for e in list(self.ents.values()):
            if e.spec.spawn and e.owner != self.me:
                t, every, cap = e.spec.spawn
                e.timer += 1
                alive = sum(1 for o in self.ents.values() if o.template == t and o.owner == e.owner)
                if e.timer >= every and alive < cap:
                    e.timer = 0
                    self.add(t, e.owner, e.x + 40, e.y + 40)
        hits = []
        for e in list(self.ents.values()):
            if 'STRUCTURE' in e.spec.kindof and not e.spec.dps:
                continue
            tgt = self._aim(e)
            if tgt is not None and _d(e, tgt) <= e.spec.range:
                k = pw.kind_of(tgt.spec)
                hits.append((tgt, e.spec.dps / FPS * (2.0 if k in e.spec.good_against else 0.5)))
                continue
            goal = (tgt.x, tgt.y) if tgt is not None else self._goal(e)
            if goal is not None:
                self._walk(e, goal)
        for tgt, dmg in hits:
            tgt.hp -= dmg
        for e in list(self.ents.values()):
            if e.hp <= 0:
                del self.ents[e.id]
                self.dead.append((self.frame, e.template, e.owner))
            elif e.owner == self.me and math.hypot(e.x - self.home[0], e.y - self.home[1]) < 100:
                e.hp = min(e.spec.hp, e.hp + e.spec.hp * self.heal / FPS)
        for e in self.ents.values():
            if e.order and e.order[0] == 'attack' and e.order[1] not in self.ents:
                e.order = None
            elif e.order and e.order[0] in ('move', 'attack_move') and math.hypot(e.x - e.order[1][0], e.y - e.order[1][1]) < 5:
                e.order = None

    def _foes(self, e):
        return [o for o in self.ents.values() if (o.owner == self.me) != (e.owner == self.me)]

    def _aim(self, e):
        if e.order and e.order[0] == 'attack':
            return self.ents.get(e.order[1])
        if e.order and e.order[0] == 'move':
            return None                      # a moving player unit does not stop to shoot
        reach = e.spec.range if e.owner == self.me else e.spec.sight
        near = [o for o in self._foes(e) if _d(e, o) <= reach]
        return min(near, key=lambda o: (_d(e, o), o.id)) if near else None

    def _goal(self, e):
        if e.order and e.order[0] in ('move', 'attack_move'):
            return e.order[1]
        if e.owner != self.me:
            return self.home
        return None

    def _walk(self, e, goal):
        dx, dy = goal[0] - e.x, goal[1] - e.y
        d = math.hypot(dx, dy)
        if d < 1e-9 or not e.spec.speed:
            return
        s = min(e.spec.speed, d)
        e.x += dx / d * s
        e.y += dy / d * s
