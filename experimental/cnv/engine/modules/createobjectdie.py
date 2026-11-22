"""CreateObjectDie (step B5b, ADR 0029, docs/engine/sim-modules.md 4; moved from simunits.life_leaves -- the body's
`leaves` -- and the module pick of simunits.air_wrecks): one module a CreateObjectDie block. Told of its thing's death,
it makes its ObjectCreationList when its DieMuxData takes the death (the private model's DieMux.applies, Generals
isDieApplicable): the death type in DeathTypes ('ALL' less its '-X's, or the types it names) and not in
DeathTypesForbidden, the thing's status holding every RequiredStatus bit and no ExemptStatus bit.

What the simulator keeps of it (INFERRED, the first two kept from the readers it replaced):
  * a death of age (module.Death's cause LIFETIME, from a LifetimeUpdate read off the template -- a mission's own,
    the port's LifetimeUpdate rule; the skirmish AI's late one leaves nothing) makes the list's objects where it
    stood that frame (World.create: the ice core's wall; bench 2026-11-07 engine_life);
  * a death in the air (the thing's surface 'air') makes the first module's wrecks fall whose RequiredStatus names
    AIRBORNE_TARGET or nothing and whose RequiredStatus / ExemptStatus hold for the thing's status as it is
    (module.status_now: its status bits, AIRBORNE_TARGET in the air; B5 review e #6) (World.create airborne:
    Life.air_crash, checks/engine_crash_fall.py) -- the one list simunits.air_wrecks read; the death type is not
    read there (it read none);
  * any other death on the ground its block takes (death type, status as the death began) makes the list's infantry
    only, at the middle of the nugget's MinHealth..MaxHealth (World.create fight: Life.leave, simunits.ocl_objects;
    bench 11-22 aigarrbld 054620: the player's power plant dies in a fight and leaves the player a Peacekeeper of
    150 at ~0.55 health that fires the next frame). In retail only the structures' Generic / ConYard
    BuildingDestruction and BuildingSuicide lists make infantry; the hulks, rubble and debris the others make are
    not made. Not read: UpgradeForbidden (Upgrade_NoSpawnUponDestruction, a PLAYER upgrade nothing in retail grants)
    and REQUIRES_LIVE_PLAYER (the simulator has no defeated player); INFERRED.
VeterancyLevels and the list's other nuggets (FX, debris, weapons) are not read.

Kept from step B5b (B5 review e #5, the coordinator's ruling 11-19): the list is found by its name over every
ObjectCreationList the mission and the retail data have (in the SDK a global named asset; the old reader looked in
the thing's own XML only) -- kept; an immortal body that lives out its lifetime makes nothing (it does not die, so no
Die module is told; the old reader made the list all the same) -- a behaviour change, INFERRED. Known order: the
objects it leaves are in the world while the later Die modules and the Destroy modules are told (they came after
every Destroy module before)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

LIFETIME = module.LIFETIME      # module.Death's cause for a LifetimeUpdate's death of age
AIRBORNE = module.AIRBORNE      # the status bit of a thing in the air


class CreateObjectDieData(module.ModuleData, module.DieMux):
    def __init__(self, ocl='', types=frozenset({'ALL'}), forbidden=frozenset(), required=frozenset(),
                 exempt=frozenset()):
        self.ocl = ocl              # CreationList: the ObjectCreationList it makes
        self.types = types          # DieMuxData DeathTypes (ALL, -X, +X, X)
        self.forbidden = forbidden  # DeathTypesForbidden
        self.required = required    # RequiredStatus: every bit
        self.exempt = exempt        # ExemptStatus: none of them

    @classmethod
    def parse(cls, head, inner):
        mux = templates.child(inner, 'DieMuxData')
        w = templates.words
        return cls(templates.attr(head, 'CreationList', ''), w(mux, 'DeathTypes', 'ALL'),
                   w(mux, 'DeathTypesForbidden'), w(mux, 'RequiredStatus'), w(mux, 'ExemptStatus'))


@factory.module('CreateObjectDie')
class CreateObjectDie(module.Module, interfaces.Die, interfaces.CreateOnDeath):
    """No update, no state of its own: told of its thing's death (on_die), it asks the host to make its list."""
    DATA = CreateObjectDieData
    STATE = ()

    def on_die(self, info):
        d, thing = self.data, self.thing
        if info.cause == LIFETIME and d.takes(info.death):
            self.world.create(thing, d.ocl, False)
        elif thing.surface != 'air' and d.takes(info.death) and d.holds(
                module.status_now(thing) if info.status is None else info.status):
            self.world.create(thing, d.ocl, False, fight=True)
        if thing.surface == 'air' and self._first_airborne(info.status):
            self.world.create(thing, d.ocl, True)

    def _first_airborne(self, status=None):
        """Is it the first module whose block takes a death in the air, by the status the death began with (review
        i #5: one list a death, as the parent picked it; None: the status now)?"""
        if status is None:
            status = module.status_now(self.thing)
        return next((m for m in self.thing.find(interfaces.CreateOnDeath) if m.takes_airborne(status)), None) is self

    def creation_list(self):
        return self.data.ocl

    def takes(self, death):
        return self.data.takes(death)

    def takes_airborne(self, status=None):
        """Its block is one for a death in the air -- its RequiredStatus names AIRBORNE_TARGET or nothing (the pick
        of the old simunits.air_wrecks) -- and its RequiredStatus / ExemptStatus hold for the thing's status
        (module.status_now; None: its status now, as if in the air): B5 review e #6, the parent's pick by the status
        the thing has, never a status of the one bit."""
        d = self.data
        if status is None:
            status = module.status_now(self.thing) | {AIRBORNE}
        return (not d.required or AIRBORNE in d.required) and d.holds(status)
