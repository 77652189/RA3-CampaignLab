"""Thing, Module and ModuleData (docs/engine/sim-modules.md 1).

A thing is an object on the map: who, whose, where, plus its modules. A module is the running instance of one XML
module tag on one thing; it keeps only its own state (STATE names it, for the snapshot) and reaches other modules
only through their interfaces (Thing.find), the thing's blackboard, or the kernel's broadcasts. A module's data is
the parse of that tag's block, shared by every thing of the template, read only once made."""
import types

from engine.kernel import interfaces


class Thing:
    """The kernel's side of an object (sim.Body inherits it). A thing without modules uses the empty class default
    and carries neither a modules field nor a find cache. `serial`: the thing's number in its world, World.build's
    running count from 0 -- the key every table about a thing uses (never id(): it differs run to run and a new
    object may reuse a dead one's; never the name: a thing made under a dead one's name is another thing), so a
    snapshot (docs/engine/sim-modules.md 9.2) can write the tables back as they were."""
    # The frame recorder reads instance fields. Keep the cache and the number outside that state.
    __slots__ = ('__dict__', '__weakref__', '_find_cache', 'serial')

    @property
    def modules(self):
        return self.__dict__.get('modules', ())

    @modules.setter
    def modules(self, modules):
        modules = tuple(modules)
        if hasattr(self, '_find_cache'):
            del self._find_cache
        if modules:
            self.__dict__['modules'] = modules
        else:
            self.__dict__.pop('modules', None)

    def find(self, interface):
        """The modules implementing `interface`, in the order made; for one of interfaces.ONE the one (or None)."""
        try:
            return self._find_cache[interface]
        except (AttributeError, KeyError):
            pass

        modules = self.modules
        one = interface in interfaces.ONE
        if not modules:
            return None if one else ()

        matches = [m for m in modules if isinstance(m, interface)]
        if one:
            if len(matches) > 1:
                raise ValueError(f'{interface.__name__}: {len(matches)} modules on one thing')
            found = matches[0] if matches else None
        else:
            found = tuple(matches)
        if not hasattr(self, '_find_cache'):
            self._find_cache = {}
        self._find_cache[interface] = found
        return found

    def health_moved(self, was, now):
        """Its health went from `was` to `now` (step K2): the Damage modules are told -- on_damaged(was) when it fell,
        else on_healed(was) (it rose, stayed, or the maximum moved). The Body's damage / mend / health call it; whoever
        writes the health or its maximum past them calls it too."""
        if not self.modules:
            return
        for m in self.find(interfaces.Damage):
            if now < was:
                m.on_damaged(was)
            else:
                m.on_healed(was)

    def upgrades_moved(self, have):
        """The upgrades it holds are now `have` (step K3, the Generals UpgradeMux): each Upgrade module whose trigger
        they come to satisfy is told on_upgrade, each whose trigger they no longer satisfy on_remove (RA3 takes an
        upgrade back: NAMED_REMOVE_UPGRADE). Told whenever the held upgrades may have moved (simmodifier.modify); a
        module already as the upgrades say hears nothing."""
        if not self.modules:
            return
        for m in self.find(interfaces.Upgrade):
            want = m.data.trigger.wants(have)
            if want != m.upgraded:
                m.upgraded = want
                if want:
                    m.on_upgrade()
                else:
                    m.on_remove()


def forward(interface, read, default=None):
    """A read-only attribute of a thing for a field moved into a module that outside code still reads (sim.Body
    FORWARDS; docs/engine/sim-modules.md 10): read(the thing's `interface` module, one of interfaces.ONE; else the
    tuple of its modules of that interface), `default` (the field's old default) when it has none."""
    def get(thing):
        # The modules setter clears this lookup; the reader still sees the module's current state.
        try:
            m = thing._find_cache[interface]
        except (AttributeError, KeyError):
            m = thing.find(interface) if thing.modules else None
        return default if m is None or m == () else read(m)
    return property(get)


class Trigger:
    """An upgrade module's trigger (Generals UpgradeMux): TriggeredBy -- any one, or all with RequiresAllTriggers --
    and none of ConflictsWith. No TriggeredBy: never. Read only."""
    __slots__ = ('by', 'conflicts', 'all')

    def __init__(self, by=(), conflicts=(), all=False):
        object.__setattr__(self, 'by', frozenset(by))
        object.__setattr__(self, 'conflicts', frozenset(conflicts))
        object.__setattr__(self, 'all', bool(all))

    def __setattr__(self, name, value):
        raise AttributeError('a Trigger is read only')

    def wants(self, have):
        have = set(have)
        if not self.by or self.conflicts & have:
            return False
        return self.by <= have if self.all else bool(self.by & have)


LIFETIME = 'lifetime'           # Death.cause of a LifetimeUpdate's death of age (step B5b)


class Death:
    """What a Die module is told (interfaces.Die.on_die, step B4c): the frame its thing died in, why (the host's
    words), its death type (step B5a: NORMAL, CRUSHED for a crush; step B5b: a lifetime's DeathType) and its cause
    (step B5b: 'lifetime' for a LifetimeUpdate's death of age, else '') and the thing's status as the broadcast
    began (status_now; review i #5: the airborne wreck list is picked once a death, not again as each module's turn
    comes; None: each module reads the status now). Read only; the killer and the damage come with the death modules
    that need them (step B5)."""
    __slots__ = ('frame', 'why', 'death', 'cause', 'status')

    def __init__(self, frame, why='', death='NORMAL', cause='', status=None):
        object.__setattr__(self, 'frame', frame)
        object.__setattr__(self, 'why', why)
        object.__setattr__(self, 'death', death)
        object.__setattr__(self, 'cause', cause)
        object.__setattr__(self, 'status', None if status is None else frozenset(status))

    def __setattr__(self, name, value):
        raise AttributeError('a Death is read only')


class DieMux:
    """What every Die module's data shares (Generals DieMuxData, the private model's DieMux.applies): a data class
    that sets `types` (DeathTypes: ALL, -X, +X, X), `forbidden` (DeathTypesForbidden), `required` (RequiredStatus:
    every bit) and `exempt` (ExemptStatus: none of them) gets takes / holds (step B5c: CreateObjectDie,
    FireWeaponWhenDead)."""

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


AIRBORNE = 'AIRBORNE_TARGET'    # the status bit of a thing in the air


def status_now(thing):
    """The status a Die module's RequiredStatus / ExemptStatus is matched against (DieMux.holds): the thing's object
    status bits as they are, AIRBORNE_TARGET added while it is in the air (surface 'air': the simulator sets no such
    bit) -- shared by CreateObjectDie and FireWeaponWhenDead (B5 review e #6: never a status made up of the one bit)."""
    status = set(getattr(thing, 'status', ()))
    if getattr(thing, 'surface', '') == 'air':
        status.add(AIRBORNE)
    return status


class ModuleData:
    """The parse of one module block: parse(head, inner) -> an instance, sealed by the factory -- read only after."""

    @classmethod
    def parse(cls, head, inner):
        """head: the tag's attributes text; inner: its inner XML (a block of the template data port)."""
        return cls()

    def __setattr__(self, name, value):
        if getattr(self, '_sealed', False):
            raise AttributeError(f'{type(self).__name__} is read only once parsed')
        object.__setattr__(self, name, value)

    def seal(self):
        object.__setattr__(self, '_sealed', True)
        return self


class Module:
    """One module instance. DATA: its data class; TAGS: the XML tags it is registered under (factory.module);
    STATE: every field it sets on itself after it is made and may change -- the snapshot takes these (World.snapshot,
    step S; tests/guards/test_module_state.py holds it to what the class assigns).
    RECORDED: the ones of STATE the frame record shows among its thing's fields (Observe.state, the set ones only); a
    class that names STATE but not RECORDED records all of its STATE, one that names neither keeps its base's two.
    world: the World it lives in -- for the kernel's services (the audit set), not to reach other things.
    ALIGN: what its family assumes of the engine, {key it puts in world.used: the line the report prints as 待对齐}
    (factory.align gathers them into sim.ALIGN; tests/guards/test_align.py)."""
    DATA = ModuleData
    TAGS = ()
    STATE = ()
    RECORDED = ()
    ALIGN = types.MappingProxyType({})

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if 'STATE' in vars(cls) and 'RECORDED' not in vars(cls):
            cls.RECORDED = cls.STATE

    def __init__(self, thing, data, world=None):
        self.thing, self.data, self.world = thing, data, world
