"""StructureSellUpdate (bench 2026-11-06 engine_sell, docs/engine/sell.md; moved from the body's `sell_end` field and
simbody.Life.expire in step M10, ADR 0029, docs/engine/sim-modules.md 4): a structure that has one can be sold
(SELL_OBJECT: simbody.Life.sell pays the refund, sets SOLD and tells this module); its SellTime x 15 frames later
(BaseStructure's 2 s: 30) it is deleted -- no death, no ruin (World.remove: '卖掉了'). Killed meanwhile, it stays dead
and the sale does nothing more.

Only BaseStructure.xml has one in the SDK; a civilian house has none and is never sold (bench 11-17 engine_garrison
del). A missing SellTime reads as 2 s (INFERRED: no template lacks it).
Known and kept from the code it replaced, unlike the frame order before (the expire cell's per-object loop after its
modules): in one frame the expire cell's modules -- lifetimes, toppled props, sales -- go in the order made."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15                        # the game's logic frames a second
SELL_SECS = 2.0                 # BaseStructure's SellTime


class SellData(module.ModuleData):
    def __init__(self, frames=int(SELL_SECS * FPS)):
        self.frames = frames        # from the frame it is sold in to the one it is deleted in

    @classmethod
    def parse(cls, head, inner):
        v = templates.attr(head, 'SellTime')
        return cls(int(round((templates.secs(v) if v else SELL_SECS) * FPS)))


@factory.module('StructureSellUpdate')
class Sell(module.Module, interfaces.Update, interfaces.Sell, interfaces.Clocked):
    """In the frame order's expire cell: asleep until sold, then until its delete frame, then deletes its thing.
    sell_end: that frame (None: not sold; the name the body's field had, so the frame record is unchanged)."""
    DATA = SellData
    PHASE = 'expire'
    STATE = ('sell_end',)
    sell_end = None

    def gone_frame(self):
        return self.sell_end

    def start_sale(self, frame):
        self.sell_end = frame + self.data.frames
        self.world.wake(self, self.sell_end)
        return self.sell_end

    def clocks(self):
        return {'gone': self.sell_end}

    def set_clocks(self, values):
        self.sell_end = values['gone']
        if self.sell_end is not None:
            self.world.wake(self, self.sell_end)

    def update(self, frame):
        if self.sell_end is None or not self.thing.alive:
            return interfaces.SLEEP
        if frame < self.sell_end:
            return self.sell_end - frame
        self.world.remove(self.thing, '卖掉了')
        return interfaces.SLEEP
