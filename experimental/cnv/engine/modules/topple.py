"""ToppleUpdate (bench 2026-11-09 engine_topple, 11-10 engine_propbody; moved from simtopple.rules, the expire cell's
topple part of simbody.Life.expire and the knock-over in Sim.move / simbody.Life.destroy in step M2, ADR 0029,
docs/engine/sim-modules.md 4): a prop a crusher drives into falls -- the angular fall and its damped bounces (the
reference ToppleUpdate.cpp under work/downloads/cnc_generals_src; SDK defaults for the angular velocity, acceleration
and bounce) -- and, with KillWhenStartToppled or KillWhenToppled, is gone that many frames plus its SlowDeath's
DestructionDelay later, deleted, never dying (no script-visible DYING); a killed one falls where it stands, gone its
delay later. DynamicsDraw.Lifetime only controls the visual debris.

Who knocks it over stays outside (the movement: Sim.move's swept boxes, simtopple.crosses); the module takes the
knock (`knock`) and the kill (`fall_where_it_stands`) and removes its thing in the expire cell (World.remove).
Known and kept from the code it replaced, unlike the frame order before (the expire cell's per-object loop): in one
frame every toppled prop goes before any sold structure (the cell's modules run first), and the props in the order
they were made (a prop made again under a name in use: the new one's place)."""
import math

from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15                        # the game's logic frames a second (bench 2026-10-28, probe align)


def _percent(head, name, default):
    return float(templates.attr(head, name, default).rstrip('%')) / 100


class ToppleData(module.ModuleData):
    def __init__(self, start=False, finish=False, velocity=0.2, accel=0.01, bounce=0.2, minimum=0.5):
        self.start = start          # KillWhenStartToppled: gone its delay after the knock, no fall time
        self.finish = finish        # KillWhenToppled: gone once it has settled, plus its delay
        self.velocity = velocity    # InitialVelocityPercent of the knocker's speed (a frame), the fall's first step
        self.accel = accel          # InitialAccelPercent: added to the angular velocity every frame of the fall
        self.bounce = bounce        # BounceVelocityPercent: the velocity kept, reversed, at each bounce
        self.minimum = minimum      # MinimumToppleSpeed: the least knocker speed the fall is worked from

    @classmethod
    def parse(cls, head, inner):
        return cls(start=templates.attr(head, 'KillWhenStartToppled', 'false') == 'true',
                   finish=templates.attr(head, 'KillWhenToppled', 'false') == 'true',
                   velocity=_percent(head, 'InitialVelocityPercent', '20%'),
                   accel=_percent(head, 'InitialAccelPercent', '1%'),
                   bounce=_percent(head, 'BounceVelocityPercent', '20%'),
                   minimum=float(templates.attr(head, 'MinimumToppleSpeed', '0.5')))


def fall_frames(speed, data):
    """Frames from the knock until it rests: the angular fall, then damped bounces until resting (the reference
    source's 0.01 rad/frame stop threshold); 0 with KillWhenStartToppled, None when nothing brings it down or it never
    settles. speed: the knocker's, a frame."""
    if data.start:
        return 0
    speed = max(speed, data.minimum)
    velocity, accel = speed * data.velocity, speed * data.accel
    if velocity <= 0 and accel <= 0:
        return None                                 # no force to bring it down
    angle, limit = 0.0, math.pi / 2 - math.pi / 64
    for frame in range(1, 10001):
        angle += min(velocity, limit - angle)
        if angle >= limit and velocity > 0:
            velocity *= -data.bounce
            if abs(velocity) < 0.01:
                return frame
        else:
            velocity += accel
    return None                                     # no settling, no removal


@factory.module('ToppleUpdate')
class Topple(module.Module, interfaces.Update, interfaces.Create, interfaces.Topple):
    """In the frame order's expire cell: asleep until its gone frame, then removes its thing (World.remove:
    '倒伏后消失'). toppled: knocked over (or killed); topple_end: the frame it is gone in (None: it stays); delay: its
    SlowDeath's DestructionDelay in frames (the body's `lies`, read by the death family's reader when it was made).
    The names the body's fields had, so the frame record is unchanged; delay, set at on_create, is state too (a
    snapshot's restore makes things without on_create) but never recorded."""
    DATA = ToppleData
    PHASE = 'expire'
    STATE = ('toppled', 'topple_end', 'delay')
    RECORDED = ('toppled', 'topple_end')
    toppled = False
    topple_end = None
    delay = 0

    def on_create(self, frame):
        self.delay = int(round(self.thing.lies * FPS))

    def on_build_complete(self):
        pass

    def rules(self):
        """The rules as the body's `topple` field held them (simtopple.rules before step M2)."""
        d = self.data
        return dict(start=d.start, finish=d.finish, velocity=d.velocity, accel=d.accel, bounce=d.bounce,
                    minimum=d.minimum, delay=self.delay)

    def is_toppled(self):
        return self.toppled

    def gone_frame(self):
        return self.topple_end

    def knock(self, frame, speed):
        """A crusher drove into it at `speed` (a frame) in `frame`: it is toppled; it is gone its fall plus its delay
        later when it kills on starting or ending the fall (engine_topple)."""
        self.toppled = True
        fall = fall_frames(speed, self.data)
        if fall is not None and (self.data.start or self.data.finish):
            self._gone_at(frame + fall + self.delay)

    def fall_where_it_stands(self, frame):
        """Killed in `frame` (engine_propbody b): it falls where it stands, no fall time, gone its delay later
        (61 / 121 frames counted with the kill's); once only."""
        if self.topple_end is None:
            self.toppled = True
            self._gone_at(frame + self.delay)

    def _gone_at(self, frame):
        self.topple_end = frame
        self.world.wake(self, frame)

    def update(self, frame):
        if self.topple_end is None or not self.thing.alive:
            return interfaces.SLEEP
        if frame < self.topple_end:
            return self.topple_end - frame
        self.world.remove(self.thing, '倒伏后消失')     # PropBody never exposes NAMED_DYING, even for one frame
        return interfaces.SLEEP
