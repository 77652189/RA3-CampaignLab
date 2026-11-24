"""ChargeWeaponUpdate (E213, bench engine_charge_e a-c): the next attack's first shot skips the part of its pre-attack
the weapon has charged (idle / ChargeTime, at most all of it); idle ChargeTime + OverChargeTime, that shot also deals
OverChargePercent more damage, none short of it. Retail's one block is the Wave-Force tower's (5 s, 2 s, 40 %,
ForbiddenStatus IS_FIRING_WEAPON IS_RELOADING_WEAPON). Bench: idle 16 s 10 frames / x 1.4, 6 s 3 frames / x 1.0 (the
simulator's both: 3), 4 s 21 frames (the simulator 12: the cut in proportion is INFERRED -- a's and b's 7-9 frames
over may be the turret's idle scan, MaxIdleScanAngle 90 at 180 deg/s, not modelled).
The host asks it when a weapon's clip clock starts anew (WeaponSet.start_clip): idle = from the old cycle's end (none:
the thing's making) to the attack. INFERRED: the forbidden status is the clip clock's busy span (the simulator sets
neither bit), a charge the thing's only weapon's, power and other statuses not read."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates


class ChargeWeaponData(module.ModuleData):
    def __init__(self, charge=0.0, over=0.0, percent=0.0):
        self.charge = charge        # ChargeTime, seconds
        self.over = over            # OverChargeTime, seconds after the charge
        self.percent = percent      # OverChargePercent, a fraction (40% -> 0.4)

    @classmethod
    def parse(cls, head, inner):
        a = lambda name: templates.attr(head, name)
        return cls(templates.secs(a('ChargeTime')), templates.secs(a('OverChargeTime')),
                   templates.num((a('OverChargePercent') or '').rstrip('%')) / 100.0)


@factory.module('ChargeWeaponUpdate')
class ChargeWeapon(module.Module, interfaces.Create, interfaces.Charge):
    """made: the second its thing was made (the idle start of its first attack)."""
    DATA = ChargeWeaponData
    STATE = ('made',)
    made = 0.0

    def on_create(self, frame):
        self.made = frame / 15.0

    def on_build_complete(self):
        pass

    def spend(self, t, idle_since):
        idle = t - (self.made if idle_since is None else idle_since)
        d = self.data
        cut = min(1.0, idle / d.charge) if d.charge > 0 else 1.0
        return cut, 1.0 + d.percent if idle >= d.charge + d.over - 1e-6 else 1.0
