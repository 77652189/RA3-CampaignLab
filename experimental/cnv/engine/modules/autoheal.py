"""AutoHealBehavior (engine line C round 7, bench engine_heal a / b, docs/engine/heal.md 1): a hurt object (health
below what it was last frame) is mended HealingAmount every HealingDelay, the first StartHealingDelay after the
latest hurt; full health stops it. The intervals are floor(15 x seconds) frames (0.5 s is 7). The state- and
rank-gated blocks (InitiallyActive false, an ObjectStatusValidation) and the area ones (Radius) are not modelled:
their module never runs. Moved from simheal.Heal.autoheal in step K1 (ADR 0029, docs/engine/sim-modules.md)."""
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
class AutoHeal(module.Module, interfaces.Update):
    """Wakes every frame in the frame order's autoheal cell. heal_at: the frame of the next mend (None at full
    health); heal_seen: the health it saw last frame."""
    DATA = AutoHealData
    PHASE = 'autoheal'
    STATE = ('heal_at', 'heal_seen')
    heal_at = None
    heal_seen = None

    def update(self, frame):
        rule = self.data.rule
        if not rule or not rule[0]:
            return interfaces.SLEEP
        b = self.thing
        if not b.alive:
            return 1
        amount, every, wait = rule
        if self.heal_seen is not None and b.hp < self.heal_seen - 1e-9:
            self.heal_at = frame + max(wait, 1)
        if b.hp < b.max_hp - 1e-9:
            if self.heal_at is None:
                self.heal_at = frame + every
            if frame >= self.heal_at:
                b.mend(amount)
                self.heal_at = frame + every
        else:
            self.heal_at = None
        self.heal_seen = b.hp
        self.world.used.add('autoheal')
        return 1
