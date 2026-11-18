"""Thing, Module and ModuleData (docs/engine/sim-modules.md 1).

A thing is an object on the map: who, whose, where, plus its modules. A module is the running instance of one XML
module tag on one thing; it keeps only its own state (STATE names it, for the snapshot) and reaches other modules
only through their interfaces (Thing.find), the thing's blackboard, or the kernel's broadcasts. A module's data is
the parse of that tag's block, shared by every thing of the template, read only once made."""
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
    world: the World it lives in -- for the kernel's services (the audit set), not to reach other things."""
    DATA = ModuleData
    TAGS = ()
    STATE = ()

    def __init__(self, thing, data, world=None):
        self.thing, self.data, self.world = thing, data, world
