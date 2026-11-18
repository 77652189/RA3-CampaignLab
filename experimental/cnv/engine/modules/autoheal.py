"""AutoHealBehavior (engine line C round 7, bench engine_heal a / b, docs/engine/heal.md 1): a hurt object is mended
HealingAmount every HealingDelay, the first StartHealingDelay after the latest hurt; full health stops it. The
intervals are floor(15 x seconds) frames (0.5 s is 7). The state- and rank-gated blocks (InitiallyActive false, an
ObjectStatusValidation) and the area ones (Radius) are not modelled: their module never runs. Moved from
simheal.Heal.autoheal in step K1; asleep at full health, woken by the Damage broadcast since step K2 (ADR 0029,
docs/engine/sim-modules.md 4)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates


class AutoHealData(module.ModuleData):
    def __init__(self, rule=None):
        self.rule = rule    # (amount, every, wait) frames; None: a block not modelled

    @classmethod
    def parse(cls, head, inner):
        if templates.attr(head, 'InitiallyActive') == 'false' or templates.attr(head, 'ObjectStatusValidation') or \
                '<ObjectStatusValidation' in inner or templates.num(templates.attr(head, 'Radius'), 0.0) > 0:
            return cls()
        return cls((int(templates.num(templates.attr(head, 'HealingAmount'), 0.0)),
                    int(15 * templates.secs(templates.attr(head, 'HealingDelay') or '1s')),
                    int(15 * templates.secs(templates.attr(head, 'StartHealingDelay') or '0s'))))


@factory.module('AutoHealBehavior')
class AutoHeal(module.Module, interfaces.Update, interfaces.Damage):
    """In the frame order's autoheal cell: runs when made, then at its next mend; asleep at full health or dead.
    A hurt (on_damaged) wakes it to restart the wait; health back to full, or below a moved maximum (on_healed),
    wakes an idle one. heal_at: the frame of the next mend (None at full health); hurt: told of a hurt since its
    last run. Woken at the frame of the cell that told it, it runs this frame if the autoheal cell is still to
    come, else the next -- as the every-frame module of step K1 saw the health fall."""
    DATA = AutoHealData
    PHASE = 'autoheal'
    STATE = ('heal_at', 'hurt')
    heal_at = None
    hurt = False

    def _live(self):
        rule = self.data.rule
        return bool(rule and rule[0])

    def update(self, frame):
        if not self._live() or not self.thing.alive:
            return interfaces.SLEEP
        b = self.thing
        amount, every, wait = self.data.rule
        self.world.used.add('autoheal')
        if self.hurt:
            self.hurt = False
            self.heal_at = frame + max(wait, 1)
        if b.hp >= b.max_hp - 1e-9:
            self.heal_at = None
            return interfaces.SLEEP
        if self.heal_at is None:
            self.heal_at = frame + every
        if frame >= self.heal_at:
            b.mend(amount)
            self.heal_at = frame + every
            if b.hp >= b.max_hp - 1e-9:
                return 1                # mended to full: next frame clears heal_at, as the every-frame module did
        return self.heal_at - frame

    def on_damaged(self, info):
        if self._live():
            self.hurt = True
            self.world.wake(self)

    def on_healed(self, info):
        b = self.thing
        if self._live() and (self.heal_at is None or b.hp >= b.max_hp - 1e-9):
            self.world.wake(self)

    def on_damage_state(self, old, new):
        pass
