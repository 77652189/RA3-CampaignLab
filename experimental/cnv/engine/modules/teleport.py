"""TeleportStoredObjectsUpdate (E227, checks/engine_teleport.readings.toml): the Chronosphere's carry. The second step's
cast (TeleportStoredObjectsSpecialPower of its power, act_ability) begins it at a point with the store whose
TeleportLinkID is that power's StoreObjectsLinkID (StoreObjectsSpecialPower, specialpower.py):
- InitialDelayTime frames on (15 x seconds, cut down: 1.7 s is 25): with GetObjectsCurrentlyAtStorePosition the store
  takes its things again at its point; each stored thing of InstaKillObjectFilter dies (every Telefrag);
- DelayTime frames later (at least one): each one left moves by the landing point less the store's point (the
  formation kept); the things of CollidesWithOnTeleport within the store's Radius of the landing point, taken before
  anyone moves, that it overlaps (the two bounding circles, INFERRED): HEALTH_SUBTRACTION both lose the other's health
  as it was; INSTANT_DEATH_TELEPORTER_ONLY the one moved dies. The store is cleared. Each one moved stands still
  FadeInTime frames from the landing (World.hold: no move, and no new fire as EMP'd -- the fire INFERRED).
The bench (a-e): 1.7 s + 2 s kills the infantry seen from frame 26 of the second cast, the tank in B from 56;
0 s + 0 s seen in frames 1 and 2; INSTANT_DEATH_TELEPORTER_ONLY onto a parked tank kills only the one moved,
HEALTH_SUBTRACTION both; FadeInTime 2 s keeps the landed tank in B 29 frames longer (c against a). Not modelled: the
freeze between the steps, Telefrag SWAP (a gap), the ground height, the drawing (TargetFX)."""
import math

from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15
LAG = 1     # the cast's frame: the script executor moves the frame on, so InitialDelayTime counts from the next one
            # (the bench: the insta-kill seen from frame 26 of 1.7 s, from 1 of 0 s -- a wake now runs next frame too)


def _frames(head, name):
    return int(FPS * templates.secs(templates.attr(head, name) or '0s'))


def _filter(inner, tag):
    """(Include kinds, Exclude kinds, ExcludeThing templates) of the filter block `tag`; None: no such block."""
    h, i = next(iter(templates.blocks(inner, tag)), (None, ''))
    return None if h is None else (templates.words(h, 'Include'), templates.words(h, 'Exclude'),
                                   templates.names(h, i, 'ExcludeThing'))


def _takes(f, t):
    return f is not None and bool(t.kinds & f[0]) and not t.kinds & f[1] and t.template not in f[2]


class TeleportData(module.ModuleData):
    def __init__(self, power=None, first=0, delay=0, telefrag='NONE', at_store=False, kill=None, collide=None, fade=0):
        self.power, self.first, self.delay, self.fade = power, first, delay, fade   # Initial/Delay/FadeInTime: frames
        self.telefrag, self.at_store = telefrag, at_store           # Telefrag, GetObjectsCurrentlyAtStorePosition
        self.kill, self.collide = kill, collide                     # InstaKillObjectFilter, CollidesWithOnTeleport

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'SpecialPowerTemplate'), _frames(head, 'InitialDelayTime'),
                   _frames(head, 'DelayTime'), (templates.attr(head, 'Telefrag') or 'NONE').upper(),
                   (templates.attr(head, 'GetObjectsCurrentlyAtStorePosition') or '').lower() == 'true',
                   _filter(inner, 'InstaKillObjectFilter'), _filter(inner, 'CollidesWithOnTeleport'),
                   _frames(head, 'FadeInTime'))


@factory.module('TeleportStoredObjectsUpdate')
class Teleport(module.Module, interfaces.Update, interfaces.Teleport):
    """In the frame order's seq cell (right after the scripts'), asleep until a cast: step 0 (the insta-kill), then step 1 (the move)."""
    DATA = TeleportData
    PHASE = 'seq'
    STATE = ('store', 'end', 'step', 'due')
    RECORDED = ()
    store = None        # the store module of the cast
    end = None          # the landing point
    step = None         # 0: the insta-kill next, 1: the move next; None: idle
    due = 0             # the frame step 0 runs: a cast again starts the delays over (review 1125 T, INFERRED)

    def power(self):
        return self.data.power

    def begin(self, point):
        b, d = self.thing, self.data
        link = next((m.data.link for m in b.find(interfaces.SpecialPower) if m.power() == d.power and m.data.link),
                    None)
        self.store = next((m for m in b.find(interfaces.Store) if m.link() == link), None)
        self.end, self.step, self.due = point, 0, self.world.frame + d.first + LAG
        self.world.wake(self, self.due)

    def update(self, frame):
        d, s = self.data, self.store
        if self.step is None or s is None:
            self.step = None
            return interfaces.SLEEP
        if frame < self.due:            # an earlier cast's wake
            return self.due - frame
        if self.step == 0:
            if d.at_store and s.stored_at is not None:
                s.store(s.stored_at)
            for t in s.stored():
                if _takes(d.kill, t):
                    self.world.kill(t, 'teleport insta-kill')
            self.step = 1
            return max(1, d.delay)
        self._move(s, frame)
        self.step = self.store = None
        return interfaces.SLEEP

    def _move(self, s, frame):
        d, (ex, ey) = self.data, self.end
        sx, sy = s.stored_at if s.stored_at is not None else self.end
        r = s.data.radius
        near = [t for t in self.world.living() if math.hypot(t.x - ex, t.y - ey) <= r and _takes(d.collide, t)]
        if d.telefrag == 'SWAP':
            self.world.gap('TeleportStoredObjectsUpdate', 'SWAP', '时空互换没模拟：没传')
            near = None
        for m in (s.stored() if near is not None else ()):
            m.x, m.y = m.x - sx + ex, m.y - sy + ey
            if d.fade:
                self.world.hold(m, frame + d.fade)
            for t in near:
                if t is m or 'INERT' in t.kinds or math.hypot(t.x - m.x, t.y - m.y) >= t.radius + m.radius:
                    continue
                if d.telefrag == 'HEALTH_SUBTRACTION':
                    hm, ht = m.hp, t.hp
                    m.damage(ht)
                    t.damage(hm)
                    for x in (m, t):
                        if x.alive and x.hp <= 0:
                            self.world.kill(x, 'telefrag')
                elif d.telefrag == 'INSTANT_DEATH_TELEPORTER_ONLY' and m.alive:
                    self.world.kill(m, 'telefrag')
        s.clear()
