"""The Locomotor family's data (move_pack M2 step 1, ADR 0029): a GameObject's <LocomotorSet>s and the
<LocomotorTemplate>s of GlobalData/Locomotor.xml they name -- a named resource, not a module, like a WeaponTemplate.
simunits' readers (stats' speed and surface, turning, locomotor_speed) walk the chain and read each text here."""
from engine.kernel import module
from engine.ports import templates


class LocomotorSet(module.ModuleData):
    """One <LocomotorSet>: the Locomotor a Condition (NORMAL when not written) moves by at its Speed (None: a macro)."""

    def __init__(self, condition, locomotor, speed):
        self.condition, self.locomotor, self.speed = condition, locomotor, speed

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'Condition', 'NORMAL'), templates.attr(head, 'Locomotor'),
                   templates.num(templates.attr(head, 'Speed'), None))


class Locomotor(module.ModuleData):
    """One <LocomotorTemplate>: its Surfaces (GROUND, WATER, AIR ...), 360 / TurnTimeSeconds degrees a second (None:
    none written) and its TurnThresholdHS in degrees (None: it drives off turning)."""

    def __init__(self, surfaces, turn_rate, limit):
        self.surfaces, self.turn_rate, self.limit = surfaces, turn_rate, limit

    @classmethod
    def parse(cls, head, inner):
        secs, limit = templates.secs(templates.attr(head, 'TurnTimeSeconds')), templates.attr(head, 'TurnThresholdHS')
        return cls((templates.attr(head, 'Surfaces') or '').split(), 360.0 / secs if secs > 0 else None,
                   templates.num(limit.rstrip('d')) if limit else None)


def sets(text):
    """[LocomotorSet] of every <LocomotorSet> in a template's text, in order."""
    return [LocomotorSet.parse(h, i) for h, i in templates.blocks(text or '', 'LocomotorSet')]


def speed_of(found, condition):
    """The first set of that Condition with a speed, None when none (a toggle's state switches to it: the Tengu's jet
    200 against 100 on the ground); NORMAL's is the template's own speed, its Locomotor its surfaces and turning."""
    return next((s for s in found if s.condition == condition and s.speed is not None), None)


def library(text):
    """{id: Locomotor} of a Locomotor.xml text."""
    return {templates.attr(h, 'id'): Locomotor.parse(h, i) for h, i in templates.blocks(text, 'LocomotorTemplate')}


def surface_of(surf, kinds):
    """A locomotor's Surfaces as a routing grid. DEEP_WATER is water: the ships' and the dolphin's locomotors write
    DEEP_WATER alone (round 252, engine_dam: read as 'ground' before, the dolphin was routed over the bank and a dry
    dam). The routing's water grid does not tell deep from shallow (INFERRED)."""
    s = set(surf)
    wet = bool(s & {'WATER', 'DEEP_WATER'})
    if 'AIRCRAFT' in kinds or 'AIR' in s:
        return 'air'
    if 'AMPHIBIOUS' in kinds or ('GROUND' in s and wet):
        return 'both'
    if wet:
        return 'water'
    return 'ground'


def turns(loco, speed, surface):
    """(turn_rate, turn_first) of a thing on `loco` (None: none): a TurnThresholdHS turns it in place before it drives
    off (tests/test_turn_rate.py). Aircraft bank as they fly (not benched): they and a standing thing turn at once."""
    return (loco.turn_rate, loco.limit is not None) if speed > 0 and surface != 'air' and loco else (None, False)
