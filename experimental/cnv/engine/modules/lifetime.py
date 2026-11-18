"""LifetimeUpdate (bench 2026-11-07 engine_life; moved from simbody.Life.expire and simunits.lifetime in step M1,
ADR 0029, docs/engine/sim-modules.md 4): an object is killed -- its DeathType, not deleted; what its death leaves made
that frame (the ice core's wall) -- the seconds x 15 frames after the frame it was made, cut down (a 30 s wall 450
frames, a 5.5 s core 82); MinLifetime and MaxLifetime apart: their middle (the game draws one between, a guess).

Read only from a mission's own template XML, as the reader it replaced (simunits.module_blocks OWN_ONLY: none of our
scripts makes a retail object with a lifetime); the skirmish AI sets one it reads itself (simbody.last_until, through
the Lifetime interface on a module attached late).
Known and kept from the code it replaced, unlike the frame order before (the expire cell's per-object loop): in one
frame every lifetime runs out before any toppled prop or sold structure goes (the cell's modules run first)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15                        # the game's logic frames a second (bench 2026-10-28, probe align)


class LifetimeData(module.ModuleData):
    def __init__(self, frames=0, death='NORMAL'):
        self.frames = frames        # frames from the one it is made in to the one it dies in
        self.death = death          # its DeathType (what its CreateObjectDie answers: simunits.life_leaves)

    @classmethod
    def parse(cls, head, inner):
        lo, hi = templates.secs(templates.attr(head, 'MinLifetime')), templates.secs(templates.attr(head, 'MaxLifetime'))
        return cls(int((lo + hi) / 2 * FPS + 1e-6), templates.attr(head, 'DeathType', 'NORMAL'))


@factory.module('LifetimeUpdate')
class Lifetime(module.Module, interfaces.Update, interfaces.Create, interfaces.Lifetime):
    """In the frame order's expire cell: asleep until its die frame, then kills its thing (World.kill: '寿命到了').
    life_end: the frame it dies in (None until set; the name the body's field had, so the frame record is unchanged)."""
    DATA = LifetimeData
    PHASE = 'expire'
    STATE = ('life_end',)
    life_end = None

    def on_create(self, frame):
        self.life_end = frame + self.data.frames

    def on_build_complete(self):
        pass

    def die_frame(self):
        return self.life_end

    def set_die_frame(self, frame):
        self.life_end = frame
        self.world.wake(self, frame)

    def update(self, frame):
        if self.life_end is None or not self.thing.alive:
            return interfaces.SLEEP
        if frame < self.life_end:
            return self.life_end - frame
        self.world.used.add('lifetime')
        self.world.kill(self.thing, '寿命到了')
        return interfaces.SLEEP
