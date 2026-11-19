"""CreateObjectDie (step B5b, ADR 0029, docs/engine/sim-modules.md 4; moved from simunits.life_leaves -- the body's
`leaves` -- and the module pick of simunits.air_wrecks): one module a CreateObjectDie block. Told of its thing's death,
it makes its ObjectCreationList when its DieMuxData takes the death (the private model's DieMux.applies, Generals
isDieApplicable): the death type in DeathTypes ('ALL' less its '-X's, or the types it names) and not in
DeathTypesForbidden, the thing's status holding every RequiredStatus bit and no ExemptStatus bit.

What the simulator keeps of it (INFERRED, kept from the readers it replaced; making every death's list -- the hulks,
debris and rubble nearly every retail template has -- is a behaviour change for later, on the bench):
  * a death of age (module.Death's cause LIFETIME, from a LifetimeUpdate read off the template -- a mission's own,
    the port's LifetimeUpdate rule; the skirmish AI's late one leaves nothing) makes the list's objects where it
    stood that frame (World.create: the ice core's wall; bench 2026-11-07 engine_life);
  * a death in the air (the thing's surface 'air': its status AIRBORNE_TARGET, the only bit read) makes the first
    such module's wrecks fall (World.create airborne: Life.air_crash, checks/engine_crash_fall.py) -- the one list
    simunits.air_wrecks read; the death type is not read there (it read none);
  * any other death makes nothing.
VeterancyLevels and the list's other nuggets (FX, debris, weapons) are not read."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

LIFETIME = module.LIFETIME      # module.Death's cause for a LifetimeUpdate's death of age
AIRBORNE = 'AIRBORNE_TARGET'    # the status bit of a thing in the air


def _words(head, name, default=''):
    return frozenset((templates.attr(head, name) or default).split())


class CreateObjectDieData(module.ModuleData):
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
        return cls(templates.attr(head, 'CreationList', ''), _words(mux, 'DeathTypes', 'ALL'),
                   _words(mux, 'DeathTypesForbidden'), _words(mux, 'RequiredStatus'), _words(mux, 'ExemptStatus'))

    def takes(self, death):
        """Its DeathTypes take this death type, and DeathTypesForbidden does not name it."""
        if death in self.forbidden:
            return False
        if 'ALL' in self.types:
            return f'-{death}' not in self.types
        return death in self.types or f'+{death}' in self.types

    def holds(self, status):
        """The status has every RequiredStatus bit and no ExemptStatus bit."""
        return self.required <= status and not self.exempt & status


@factory.module('CreateObjectDie')
class CreateObjectDie(module.Module, interfaces.Die, interfaces.CreateOnDeath):
    """No update, no state of its own: told of its thing's death (on_die), it asks the host to make its list."""
    DATA = CreateObjectDieData
    STATE = ()

    def on_die(self, info):
        d, thing = self.data, self.thing
        if info.cause == LIFETIME and d.takes(info.death):
            self.world.create(thing, d.ocl, False)
        if thing.surface == 'air' and d.holds({AIRBORNE}) and self._first_airborne():
            self.world.create(thing, d.ocl, True)

    def _first_airborne(self):
        return next(m for m in self.thing.find(interfaces.CreateOnDeath) if m.takes_airborne()) is self

    def creation_list(self):
        return self.data.ocl

    def takes(self, death):
        return self.data.takes(death)

    def takes_airborne(self):
        return self.data.holds({AIRBORNE})
