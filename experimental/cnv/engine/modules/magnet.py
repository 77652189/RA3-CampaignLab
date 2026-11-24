"""MagneticEffectUpdate (E225, bench checks/engine_magnet_e.readings.toml): the Assault Destroyer's black-hole armor.
While its thing holds the ObjectStatusValidation's RequiredStatus (the toggle's GENERIC_TOGGLE_STATE) it draws each
enemy of its ObjectFilter's kinds within Radius (centre to centre, INFERRED) not MAGNETIZED: the fight
(engine/orders/order.fight) turns such a shooter's attack onto it. Not modelled: a BezierProjectile bent onto it, the
MAGNETIZED bit it sets, the shield's scalable draw (looks only)."""
import math

from engine.kernel import factory, interfaces, module
from engine.ports import templates


class MagnetData(module.ModuleData):
    def __init__(self, radius=0.0, need=frozenset(), kinds=frozenset()):
        self.radius, self.need, self.kinds = radius, need, kinds

    @classmethod
    def parse(cls, head, inner):
        need = {s for h, _ in templates.blocks(inner, 'ObjectStatusValidation')
                for s in (templates.attr(h, 'RequiredStatus') or '').split()}
        kinds = {k for h, _ in templates.blocks(inner, 'ObjectFilter') for k in (templates.attr(h, 'Include') or '').split()}
        return cls(templates.num(templates.attr(head, 'Radius'), 0.0), frozenset(need), frozenset(kinds))


@factory.module('MagneticEffectUpdate')
class Magnet(module.Module, interfaces.Magnet):
    DATA = MagnetData
    STATE = ()

    def draws(self, other, enemy):
        t, d = self.thing, self.data
        return bool(enemy and t.alive and d.need <= module.status_now(t) and d.kinds & set(other.kinds)
                    and 'MAGNETIZED' not in other.status and math.hypot(other.x - t.x, other.y - t.y) <= d.radius)
