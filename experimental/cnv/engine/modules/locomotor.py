"""The Locomotor family's data (move_pack M2 step 1, ADR 0029): a GameObject's <LocomotorSet>s and the
<LocomotorTemplate>s of GlobalData/Locomotor.xml they name -- a named resource, not a module, like a WeaponTemplate.
simunits' readers (stats' speed and surface, turning, locomotor_speed) walk the chain and read each text here.
Step 2: a thing's locomotion state (LocomotorState), the four Body fields speed / surface / turn_rate / turn_first;
step 3: path / dest / face; M3 step 1: go_to's set_off / stood_for / frame_move / jet_motion."""
from engine.kernel import factory, interfaces, module
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


@factory.module('LocomotorState')
class LocomotorState(module.Module, interfaces.Locomotor):
    """The Body fields it was, by the same names (the frame record, Body's forwards): speed from Sim.add (the NORMAL
    set's), the modifier pass, a toggle state and the AI's fill; surface (surface_of) and turning (turns). The host
    attaches it (write): no block makes it, no update of its own (engine/objects/locomotion.py drives by it)."""
    STATE = ('speed', 'surface', 'turn_rate', 'turn_first', 'path', 'dest', 'face', 'set_off', 'stood_for',
             'frame_move', 'jet_motion', 'rolling', 'carry', 'stops_at')
    speed, surface, turn_rate, turn_first = 0.0, 'ground', None, False
    path, dest, face = [], None, None   # step 3: the way still to go, where it was sent, the facing once there (the
    # defaults write compares; each module its own path list)
    rolling, carry, stops_at = False, 0.0, -1.0     # M3 3, drive's: it drove the last tick (a new way: no turn in
    # place), seconds of the last tick left at a waypoint leg's end (driven on next tick), when its way ended
    set_off, stood_for, frame_move, jet_motion = -1, None, False, None  # M3 1, go_to's: the frame it was sent from
    # standing, the goal it stands short of, frame-sized steps (topple contact / Jet startup), simjet's startup

    def __init__(self, *args):
        super().__init__(*args)
        self.path = []

    def set(self, **values):
        assert set(values) <= set(self.STATE), values
        for k, v in values.items():
            setattr(self, k, v)


def write(world, thing, **values):
    """Write `thing`'s locomotion (LocomotorState.set): its module, one attached (World.attach) unless it has none and
    every value is the default (a building made, a speed of 0 kept) -- a thing with none reads the defaults. `world`
    None: its Body module's (writer)."""
    m = thing.find(interfaces.Locomotor)
    if m is None and all(getattr(LocomotorState, k) == v for k, v in values.items()):
        return
    (m or (world or thing.find(interfaces.Body).world).attach(thing, 'LocomotorState')).set(**values)


def writer(field):
    """Body's setter of step 3's `field` (path / dest / face): only hands the value on to write. The writes of those
    go through the setter for now, each moved to call write when its own family moves (R 11-20; guard: WRITTEN)."""
    return lambda thing, value: write(None, thing, **{field: value})
