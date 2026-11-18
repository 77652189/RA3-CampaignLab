"""Thing, Module and ModuleData (docs/engine/sim-modules.md 1).

A thing is an object on the map: who, whose, where, plus its modules. A module is the running instance of one XML
module tag on one thing; it keeps only its own state (STATE names it, for the snapshot) and reaches other modules
only through their interfaces (Thing.find), the thing's blackboard, or the kernel's broadcasts. A module's data is
the parse of that tag's block, shared by every thing of the template, read only once made."""
import types

from engine.kernel import interfaces


class Thing:
    """The kernel's side of an object (sim.Body inherits it). `modules` stays the empty class default until the
    factory makes one, so a thing with none carries no field for it."""
    modules = ()

    def find(self, interface):
        """The modules implementing `interface`, in the order made; for one of interfaces.ONE the one (or None)."""
        found = tuple(m for m in self.modules if isinstance(m, interface))
        if interface in interfaces.ONE:
            if len(found) > 1:
                raise ValueError(f'{interface.__name__}: {len(found)} modules on one thing')
            return found[0] if found else None
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
    FORWARDS; docs/engine/sim-modules.md 10): read(the thing's `interface` module, one of interfaces.ONE), `default`
    (the field's old default) when it has none."""
    def get(thing):
        m = thing.find(interface) if thing.modules else None
        return default if m is None else read(m)
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
    STATE: its state fields (World.snapshot, step S; the frame record shows the set ones among its thing's fields).
    world: the World it lives in -- for the kernel's services (the audit set), not to reach other things.
    ALIGN: what its family assumes of the engine, {key it puts in world.used: the line the report prints as 待对齐}
    (factory.align gathers them into sim.ALIGN; tests/guards/test_align.py)."""
    DATA = ModuleData
    TAGS = ()
    STATE = ()
    ALIGN = types.MappingProxyType({})

    def __init__(self, thing, data, world=None):
        self.thing, self.data, self.world = thing, data, world
