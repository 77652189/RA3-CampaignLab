"""World (docs/engine/sim-modules.md 5): one game's mutable state, all in the instance -- the schedule, the parse cache
of module data, the audit set and the gap log. Two worlds in one process share nothing (tests/test_kernel.py). Today
the Sim hosts it: Sim.world, and the Sim's `used` / `unmodeled` are the world's own."""
from engine.kernel import factory, interfaces, module, schedule  # noqa: F401  (module: Thing, which sim.Body is)


def no_blocks(template, tag):
    return []


class World:
    def __init__(self, blocks=no_blocks, tags=factory.TAGS, kill=None):
        """blocks(template, tag) -> [(head, inner)]: the template data port; tags: the factory's registry;
        kill(thing, why): the host's death of a thing (World.kill)."""
        self.blocks, self.tags, self._kill = blocks, tags, kill
        self.schedule = schedule.Schedule()
        self.data = {}          # (template, tag, index) -> ModuleData, parsed once a world
        self.block_lists = {}   # (template, tag) -> the port's blocks, asked once a world
        self.used = set()       # the audit set: rules the run leaned on
        self.gaps = {}          # (kind, name) -> {'n' times, 't' first met, 'what' first note} (Sim.gap writes it)
        self.frame = 0          # the frame of the cell now running (simloop sets it), what wake() defaults to

    def build(self, thing, frame):
        """Make a thing's modules (none unless a tag is registered) and hold its update modules from `frame`."""
        if not self.tags:
            return ()
        mods = factory.build(thing, self.blocks_of, self.data, self.tags, self)
        for m in mods:
            if isinstance(m, interfaces.Update):
                self.schedule.add(m, frame)
        for m in mods:
            if isinstance(m, interfaces.Create):
                m.on_create(frame)
        return mods

    def attach(self, thing, tag, frame=None):
        """One module of a registered tag made on a thing after it was made -- its data the tag's empty block, no
        on_create -- and held from `frame` (default: the frame of the cell now running): the skirmish AI's late
        lifetime (simbody.last_until). -> the module."""
        cls = self.tags[tag]
        m = cls(thing, cls.DATA.parse('', '').seal(), self)
        thing.modules = tuple(thing.modules) + (m,)
        if isinstance(m, interfaces.Update):
            self.schedule.add(m, self.frame if frame is None else frame)
        return m

    def kill(self, thing, why):
        """A module kills its thing (LifetimeUpdate): the host's death -- today Sim.destroy plus what the thing's
        death leaves (the death family's, until step M Body + death family). A world with no host kills nothing."""
        if self._kill is None:
            raise RuntimeError(f'World.kill({thing.name!r}): this world has no host to kill with')
        self._kill(thing, why)

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

    def gap(self, kind, name, what=''):
        """A module met what it does not act on: noted as Sim.gap does (t: seconds, 15 logic frames a second)."""
        g = self.gaps.get((kind, name))
        if g is None:
            self.gaps[(kind, name)] = {'n': 1, 't': self.frame / 15.0, 'what': what}
        else:
            g['n'] += 1

    def wake(self, module, frame=None):
        """Run an update module at `frame`, by default the frame of the cell now running (`frame`, which the frame
        loop sets before each cell): a module woken by a cell before its own runs this frame, by one after it the
        next (step K2)."""
        self.schedule.wake(module, self.frame if frame is None else frame)
