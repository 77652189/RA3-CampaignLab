"""AutoDepositUpdate (Generals' AutoDepositUpdate, R4; bench 2026-11-07 a4 derrick, E146 / E147 engine_bankcapture;
moved from simunits.deposit and simmoney.Money.deposit_due in step M4, ADR 0029, docs/engine/sim-modules.md 4): a
building that pays its holder. Taken (an engineer's capture): the InitialCaptureBonus now and the clock set a
DepositInterval on; then the Deposit Amount every DepositInterval -- seconds x 15 frames, cut down -- while a player
holds it. The clock runs for the neutral side too (the first deposit an interval after it is made), it just pays
nobody (the host's World.pay leaves the neutral out). The derrick: 500 when taken, 15 every 2 s (s7 515 -> s46 800).

Who captures stays outside (simorder.capture_due asks capture(frame) for the bonus and pays it)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15                        # the game's logic frames a second (bench 2026-10-28, probe align)


def _amount(inner, tag):
    return templates.num(templates.attr(templates.child(inner, tag), 'Amount'))


class DepositData(module.ModuleData):
    def __init__(self, bonus=0.0, amount=0.0, frames=0):
        self.bonus = bonus          # InitialCaptureBonus Amount: paid to whoever takes it
        self.amount = amount        # Deposit Amount: paid to its holder each interval
        self.frames = frames        # DepositInterval in frames

    @classmethod
    def parse(cls, head, inner):
        return cls(_amount(inner, 'InitialCaptureBonus'), _amount(inner, 'Deposit'),
                   int(templates.secs(templates.attr(head, 'DepositInterval', '0s')) * FPS + 1e-6))


@factory.module('AutoDepositUpdate')
class Deposit(module.Module, interfaces.Update, interfaces.Create, interfaces.Deposit):
    """In the frame order's deposit cell: asleep until its next deposit frame, then pays its thing's owner the amount
    (World.pay) and sets the next. deposit_at: that frame (the name the body's field had, so the frame record is
    unchanged)."""
    DATA = DepositData
    PHASE = 'deposit'
    STATE = ('deposit_at',)
    deposit_at = None

    def on_create(self, frame):
        self.deposit_at = frame + self.data.frames      # Generals: the first deposit an interval after it is made

    def on_build_complete(self):
        pass

    def rules(self):
        d = self.data
        return d.bonus, d.amount, d.frames

    def next_frame(self):
        return self.deposit_at

    def capture(self, frame):
        """Taken in `frame`: the clock set an interval on; -> the bonus its taker is paid."""
        self.deposit_at = frame + self.data.frames
        self.world.wake(self, self.deposit_at)
        return self.data.bonus

    def update(self, frame):
        if self.deposit_at is None or not self.thing.alive:
            return interfaces.SLEEP
        if frame < self.deposit_at:
            return self.deposit_at - frame
        self.deposit_at = frame + self.data.frames
        if self.data.amount > 0:
            self.world.pay(self.thing, self.data.amount)
        return max(1, self.deposit_at - frame)
