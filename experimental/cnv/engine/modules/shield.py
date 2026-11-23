"""ShieldSphereUpdate (E, bench checks/engine_shield.readings.toml): the Athena's shield. Its ActivateModuleSpecialPower
starts it (engine/objects/special.py self_power_press, which also sets and later drops its ObjectStatus); while up it
takes every shell landing on its thing (engine/combat/projectile.arrive) whose damage type it absorbs, fired from
beyond RadiusMax, and its thing loses nothing.

It is up while  elapsed / Duration + taken / (2 x MaxDamage) < 1  -- the hit that reaches 1 is still taken, and the
shield goes down then even with no hit (engine_shieldn: 1, 2, 3 V4s, 500 a rocket, ended it after 227, 220, 189
frames; engine_shield a: 189 with three rockets, the fourth hurt). The 2 is fitted on those three (INFERRED).
Not modelled: its allies inside the sphere (ObjectFilter), RadiusMin / the sphere shrinking, instant (non-shell)
hits, IgnoreInsideToInsideCheck; the shooter's distance is taken at landing (INFERRED)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates


class ShieldData(module.ModuleData):
    def __init__(self, frames=0, most=0.0, radius=0.0, spared=frozenset()):
        self.frames, self.most, self.radius, self.spared = frames, most, radius, spared

    @classmethod
    def parse(cls, head, inner):
        a = lambda name: templates.attr(head, name)
        return cls(int(templates.secs(a('Duration') or '0s') * 15), templates.num(a('MaxDamage'), 0.0),
                   templates.num(a('RadiusMax'), 0.0), frozenset((a('DamageTypesNotToAbsorb') or '').split()))


@factory.module('ShieldSphereUpdate')
class Shield(module.Module, interfaces.Shield):
    DATA = ShieldData
    STATE = ('up_from', 'soaked')

    def __init__(self, thing, data, world=None):
        super().__init__(thing, data, world)
        self.up_from, self.soaked = None, 0.0

    def start(self, now):
        self.up_from, self.soaked = now, 0.0

    def used(self, now):
        d = self.data
        return (now - self.up_from) / max(d.frames, 1) + (self.soaked / (2 * d.most) if d.most > 0 else 0.0)

    def over(self, now):
        return self.up_from is not None and self.used(now) >= 1

    def absorb(self, now, damage, kind, distance):
        if self.up_from is None or self.over(now) or kind in self.data.spared or distance <= self.data.radius:
            return False
        self.soaked += damage
        return True

    def stop(self):
        self.up_from = None
