"""World (docs/engine/sim-modules.md 5): one game's mutable state, all in the instance -- the schedule, the parse cache
of module data, the audit set and the gap log. Two worlds in one process share nothing (tests/test_kernel.py). Today
the Sim hosts it: Sim.world, and the Sim's `used` / `unmodeled` are the world's own."""
from engine.kernel import factory, interfaces, module, schedule  # noqa: F401  (module: Thing, which sim.Body is)


def no_blocks(template, tag):
    return []


class World:
    def __init__(self, blocks=no_blocks, tags=factory.TAGS):
        """blocks(template, tag) -> [(head, inner)]: the template data port; tags: the factory's registry."""
        self.blocks, self.tags = blocks, tags
        self.schedule = schedule.Schedule()
        self.data = {}          # (template, tag, index) -> ModuleData, parsed once a world
        self.block_lists = {}   # (template, tag) -> the port's blocks, asked once a world
        self.used = set()       # the audit set: rules the run leaned on
        self.gaps = {}          # (kind, name) -> {'n' times, 't' first met, 'what' first note} (Sim.gap writes it)

    def build(self, thing, frame):
        """Make a thing's modules (none unless a tag is registered) and hold its update modules from `frame`."""
        if not self.tags:
            return ()
        mods = factory.build(thing, self.blocks_of, self.data, self.tags, self)
        for m in mods:
            if isinstance(m, interfaces.Update):
                self.schedule.add(m, frame)
        return mods

    def blocks_of(self, template, tag):
        """The template data port's blocks of a tag, asked once a world (the port reads the XML files)."""
        key = (template, tag)
        if key not in self.block_lists:
            self.block_lists[key] = tuple(self.blocks(template, tag))
        return self.block_lists[key]

    def drop(self, thing):
        """A thing leaves the world (taken out of its registry): its update modules leave the schedule. None: none."""
        for m in getattr(thing, 'modules', ()):
            if isinstance(m, interfaces.Update):
                self.schedule.remove(m)

    def wake(self, module, frame):
        self.schedule.wake(module, frame)
