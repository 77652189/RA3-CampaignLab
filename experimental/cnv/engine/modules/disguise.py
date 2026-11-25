"""SpecialDisguiseUpdate (A369; the SpecialPowerNugget disguise consumer, engine/combat/special_power.py): the hit
puts the disguise on, as the hit thing's owner; DISGUISED shows UnpackTime later (engine_spntrans a: the native
transport's hit latched at s5 without the bit, s6 both; the spy, no UnpackTime, at once -- engine_spndisguise a).
While worn its owner passes for that player: a foe of its own owner that is not that player's enemy does not take it
by itself (engine/orders/target.takes_by_itself; engine_spncancel a: the observer of the hit's owner leaves the
native lanes alone, shoots the removed-SPN and script-bit lanes). A script's DISGUISED is no disguise.
Not modelled: the look (OpacityTarget, the hit's template), an order naming it, detectors, what takes it off
(engine_spncargo: a loaded EVACUATE does -- a mismatch reading; an empty one does not), FaceTarget."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15


class DisguiseData(module.ModuleData):
    def __init__(self, frames=0):
        self.frames = frames        # UnpackTime x 15, rounded

    @classmethod
    def parse(cls, head, inner):
        v = templates.attr(head, 'UnpackTime')
        return cls(int(round(templates.secs(v) * FPS)) if v else 0)


@factory.module('SpecialDisguiseUpdate')
class Disguise(module.Module, interfaces.Disguise):
    DATA = DisguiseData
    STATE = ('owner', 'since')
    owner = since = None

    def wear(self, owner):
        self.owner, self.since = owner, self.world.frame + self.data.frames

    def seen_as(self, frame=None):
        frame = self.world.frame if frame is None else frame
        return self.owner if self.since is not None and frame >= self.since and self.thing.alive else None

    def shows(self, condition, frame):
        return condition == 'DISGUISED' and self.seen_as(frame) is not None
