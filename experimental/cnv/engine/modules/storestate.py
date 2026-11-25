"""StoreCurrentStateUpdate (E223, benches/body_death/state/readings.toml#engine_storestate_e): its thing's place and health every
SleepTime, kept for MaxTime and SPAN frames more; Tanya's time belt (ReconstituteStateSpecialAbility, act_ability)
takes her back to the oldest kept, whatever its TimeStepsBack (the bench: 10 s asked, a 5 s store went 85-88 frames
back, a 2 s one 40-43, a 12 s one past the 187 frames there were). INFERRED: SPAN fitted on those two; her owner and
her command are not put back (D's engine_rewind reads the owner rewound too)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

SPAN = 12           # frames kept past MaxTime (the bench's two stores, 12 +- 2)


class StoreStateData(module.ModuleData):
    def __init__(self, every=3, keep=75):
        self.every, self.keep = every, keep     # SleepTime, MaxTime: frames (15 x seconds, cut down)

    @classmethod
    def parse(cls, head, inner):
        f = lambda name, v: int(15 * templates.secs(templates.attr(head, name) or v))    # noqa: E731
        return cls(max(1, f('SleepTime', '0.25s')), f('MaxTime', '5s'))


@factory.module('StoreCurrentStateUpdate')
class StoreState(module.Module, interfaces.Update, interfaces.Rewind):
    """In the frame order's expire cell, every SleepTime: (frame, x, y, health) kept while no older than MaxTime +
    SPAN frames. kept: those states, the oldest first."""
    DATA = StoreStateData
    PHASE = 'expire'
    STATE = ('kept',)
    RECORDED = ()
    kept = ()

    def oldest(self):
        return self.kept[0][1:] if self.kept else None

    def update(self, frame):
        b, d = self.thing, self.data
        if not b.alive:
            return interfaces.SLEEP
        self.kept = tuple(k for k in self.kept if k[0] >= frame - d.keep - SPAN) + ((frame, b.x, b.y, b.hp),)
        return d.every
