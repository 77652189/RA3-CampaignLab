"""HealCrateCollide for the retail human-player pickup (engine_healcrate_r a/b).

ObjectFilter selects recipients. The bench backs fully healing nearby units of the collector's owner and
excluding a nearby enemy. INFERRED: centre-to-centre healing range, the exact collision shape/timing and
healing allied players' units. Other pickup gates and crate effects, AI collection and custom ObjectFilter rules
remain gaps.
"""
import math

from engine.kernel import factory, interfaces, module
from engine.ports import templates


class HealCrateData(module.ModuleData):
    def __init__(self, radius, include, exclude):
        self.radius, self.include, self.exclude = radius, include, exclude

    @classmethod
    def parse(cls, head, inner):
        f = templates.child(inner, 'ObjectFilter')
        return cls(templates.num(templates.attr(head, 'Range')),
                   templates.words(f, 'Include'), templates.words(f, 'Exclude'))


@factory.module('HealCrateCollide')
class HealCrate(module.Module):
    DATA = HealCrateData

    def heal(self, allied):
        crate, d = self.thing, self.data
        for b in self.world.living():
            if ((d.include and not d.include & b.kinds) or d.exclude & b.kinds
                    or not allied(b)
                    or math.hypot(crate.x - b.x, crate.y - b.y) > d.radius):
                continue
            body = b.find(interfaces.Body)
            if body is not None:
                body.attempt_healing(math.inf)
