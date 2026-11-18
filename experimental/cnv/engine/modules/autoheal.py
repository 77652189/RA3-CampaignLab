"""AutoHealBehavior (engine line C round 7, docs/engine/heal.md 1; bench engine_heal a-g): a hurt object is mended
HealingAmount every HealingDelay, the first StartHealingDelay after the latest hurt; full health stops it. The
intervals are trunc(15 x seconds) frames, the seconds a float32 (0.5 s is 7). Moved from simheal.Heal.autoheal in
step K1; asleep at full health, woken by the Damage broadcast since step K2; the gated blocks modelled since step K3
(ADR 0029, docs/engine/sim-modules.md 4):
  - InitiallyActive="false": idle (hurts ignored) until its upgrade trigger holds (TriggeredBy, the Upgrade
    interface: the heroic heal of infantry and vehicles), then it mends two frames on (bench f); the upgrade taken
    back puts it to sleep again (bench g);
  - ObjectStatusValidation: asleep while its thing's status fails it (one RequiredStatus bit, no ForbiddenStatus
    bit); the status coming good later does not wake it, a hurt does (bench c, d: the Tsunami's armour);
  - StartHealingDelay 0: a hurt mends the next frame, but only once the last mend's HealingDelay has run out;
  - Radius > 0, AffectsWholePlayer, AffectsContained (healing others; no retail or mod block has one) and
    HealOnlyIfNotInCombat / UnderAttack true are noted as gaps, the module asleep -- not guessed.
Not taken from the frozen private model (step K3 compared): its first wake of a block active at creation at a random
1..HealingDelay frames (only an object made hurt and never hit sees it; the simulator: HealingDelay)."""
import math
import struct

from engine.kernel import factory, interfaces, module
from engine.ports import templates

GAP = '物体模块'


def frames(v):
    """The program's conversion: trunc(15 x seconds), the seconds a float32 (0.5 s -> 7, 0.25 s -> 3, 1 s -> 15)."""
    s = struct.unpack('<f', struct.pack('<f', round(templates.secs(v) * 1000) / 1000.0))[0]
    return max(0, math.floor(s * 15))


class AutoHealData(module.ModuleData):
    def __init__(self, rule=None, active=True, trigger=module.Trigger(), required=frozenset(), forbidden=frozenset(),
                 unmodelled=''):
        self.rule = rule            # (amount, every, wait) frames; None: heals nothing
        self.active = active        # InitiallyActive (absent: active, INFERRED -- every retail block names it)
        self.trigger = trigger      # what makes an inactive one active (TriggeredBy ...)
        self.required, self.forbidden = required, forbidden     # ObjectStatusValidation
        self.unmodelled = unmodelled    # a branch not modelled (its gap note); the module sleeps

    @classmethod
    def parse(cls, head, inner):
        a = lambda name: templates.attr(head, name)
        check = templates.child(inner, 'ObjectStatusValidation')
        wide = [n for n in ('AffectsWholePlayer', 'AffectsContained', 'HealOnlyIfNotInCombat', 'HealOnlyIfNotUnderAttack')
                if (a(n) or '').lower() == 'true']
        if templates.num(a('Radius'), 0.0) > 0:
            wide.insert(0, 'Radius')
        return cls((int(templates.num(a('HealingAmount'), 0.0)), frames(a('HealingDelay') or '1s'),
                    frames(a('StartHealingDelay') or '0s')),
                   (a('InitiallyActive') or 'true').lower() != 'false',
                   module.Trigger(templates.names(head, inner, 'TriggeredBy'), templates.names(head, inner, 'ConflictsWith'),
                                  (a('RequiresAllTriggers') or '').lower() == 'true'),
                   frozenset((templates.attr(check, 'RequiredStatus') or '').split()),
                   frozenset((templates.attr(check, 'ForbiddenStatus') or '').split()),
                   ' '.join(wide))


@factory.module('AutoHealBehavior')
class AutoHeal(module.Module, interfaces.Update, interfaces.Damage, interfaces.Upgrade):
    """In the frame order's autoheal cell: runs when made, then at its next mend; asleep at full health, dead,
    inactive or with its status check failing. A hurt (on_damaged) wakes it to restart the wait; health back to full,
    or below a moved maximum (on_healed), wakes an idle one; its upgrade (on_upgrade) wakes it to mend the next frame.
    heal_at: the frame of the next mend (None at full health); hurt: told of a hurt since its last run; upgraded: its
    trigger holds (the kernel keeps it); next_ok: the frame the last mend's HealingDelay runs out (kept by a block with
    no StartHealingDelay, the only one that reads it)."""
    DATA = AutoHealData
    PHASE = 'autoheal'
    STATE = ('heal_at', 'hurt', 'upgraded', 'next_ok')
    heal_at = None
    hurt = False
    upgraded = False
    next_ok = 0

    def _live(self):
        rule = self.data.rule
        return bool(rule and rule[0]) and not self.data.unmodelled and (self.data.active or self.upgraded)

    def _valid(self):
        status = self.thing.status
        d = self.data
        return not (d.forbidden & status) and (not d.required or bool(d.required & status))

    def update(self, frame):
        if self.data.unmodelled:
            self.world.gap(GAP, 'AutoHealBehavior/' + self.data.unmodelled.split()[0],
                           f'{self.thing.template}: {self.data.unmodelled} 未模拟')
            return interfaces.SLEEP
        if not self._live() or not self.thing.alive or not self._valid():
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
            if not wait:
                self.next_ok = self.heal_at
            if b.hp >= b.max_hp - 1e-9:
                return 1                # mended to full: next frame clears heal_at, as the every-frame module did
        return self.heal_at - frame

    def on_damaged(self, info):
        if not self._live():
            return
        if not self.data.rule[2] and self.world.frame <= self.next_ok:
            return                      # no StartHealingDelay: the mend already due stands (heal.md 1)
        self.hurt = True
        self.world.wake(self)

    def on_healed(self, info):
        b = self.thing
        if self._live() and (self.heal_at is None or b.hp >= b.max_hp - 1e-9):
            self.world.wake(self)

    def on_damage_state(self, old, new):
        pass

    def on_upgrade(self):
        """Bench f (11-17): granted by a script at a frame, the first mend comes two frames on -- one later than a
        hurt's next-frame mend (bench c); the private model's reading (wake the next frame) is a frame early here."""
        self.hurt = False
        self.heal_at = self.world.frame + 2
        self.world.wake(self, self.heal_at)

    def on_remove(self):
        self.hurt = False
        self.heal_at = None
