"""Crate effects on a human player's pickup: heal (engine_healcrate_r b), attribute modifier
(engine_secretfile_e b, hung by the order layer), cash (engine_moneycrate_e a) and
veterancy (engine_vetcrate_e a).

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
class HealCrate(module.Module, interfaces.CrateCollect):
    DATA = HealCrateData

    def collect(self, collector, allied):
        # The active order represents the crate's collector registration.
        if not _collecting(self, collector):
            return False
        self.heal(allied)
        return True

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


def _collecting(crate_module, collector):
    return collector.mode == 'collect_crate' and collector.goal is crate_module.thing


class AttributeCrateData(module.ModuleData):
    def __init__(self, modifier):
        self.modifier = modifier

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'AttributeModifier'))


@factory.module('AttributeCrateCollide')
class AttributeCrate(module.Module, interfaces.CrateCollect):
    DATA = AttributeCrateData

    def collect(self, collector, allied):
        return _collecting(self, collector)

    def worn(self):
        return self.data.modifier


class MoneyCrateData(module.ModuleData):
    def __init__(self, amount):
        self.amount = amount

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.num(templates.attr(head, 'MoneyProvided')))


@factory.module('MoneyCrateCollide')
class MoneyCrate(module.Module, interfaces.CrateCollect):
    DATA = MoneyCrateData

    def collect(self, collector, allied):
        if not _collecting(self, collector):
            return False
        # INFERRED: a pickup pays directly, bypassing income sharing and the money cap.
        self.world.pay(collector, self.data.amount)
        return True


class VeterancyCrateData(module.ModuleData):
    def __init__(self, radius, cap, special):
        self.radius, self.cap, self.special = radius, cap, special

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.num(templates.attr(head, 'RangeOfEffect')),
                   int(templates.num(templates.attr(head, 'AffectsUpToLevel'))),
                   any(templates.attr(head, field) in ('true', '1') for field in ('AddsOwnerVeterancy', 'IsPilot')))


@factory.module('VeterancyCrateCollide')
class VeterancyCrate(module.Module, interfaces.CrateCollect):
    DATA = VeterancyCrateData

    def collect(self, collector, allied):
        if not _collecting(self, collector):
            return False
        if self.data.special or self.data.cap <= 0:
            self.world.gap('物体模块', 'VeterancyCrateCollide/variant', '全局、驾驶员或默认等级上限未对拍')
            return False
        return True

    def promotions(self, collector):
        crate, d = self.thing, self.data
        yield collector, d.cap
        # INFERRED: same owner only, centre-to-centre from the crate; other owners and the exact boundary are gaps.
        for unit in self.world.living():
            if (unit is not collector and unit.owner == collector.owner
                    and math.hypot(unit.x - crate.x, unit.y - crate.y) <= d.radius):
                yield unit, d.cap
