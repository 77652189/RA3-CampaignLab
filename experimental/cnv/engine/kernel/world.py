"""World (docs/engine/sim-modules.md 5): one game's mutable state, all in the instance -- the schedule, the parse cache
of module data, the audit set and the gap log. Two worlds in one process share nothing (tests/test_kernel.py). Today
the Sim hosts it: Sim.world, and the Sim's `used` / `unmodeled` are the world's own."""
from engine.kernel import factory, interfaces, module, schedule  # noqa: F401  (module: Thing, which sim.Body is)


def no_blocks(template, tag):
    return []


class World:
    def __init__(self, blocks=no_blocks, tags=factory.TAGS, kill=None, remove=None, pay=None, toggled=None,
                 modify=None, suppression_at=None):
        """blocks(template, tag) -> [(head, inner)]: the template data port; tags: the factory's registry;
        kill(thing, why): the host's death of a thing (World.kill); remove(thing, why): the host's deletion of one,
        no death (World.remove); pay(thing, amount): the host's payment to a thing's holder (World.pay);
        toggled(thing, module): what the host re-sets when a toggle enters its next state (World.toggled);
        modify(thing): the host's re-reading of a thing's attribute modifiers (World.modify);
        suppression_at(thing, frame): the suppression fields covering a thing (World.suppression_at)."""
        self.blocks, self.tags, self._kill, self._remove, self._pay = blocks, tags, kill, remove, pay
        self._toggled, self._modify, self._suppression_at = toggled, modify, suppression_at
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

    def remove(self, thing, why):
        """A module takes its thing out, no death (a toppled prop gone: ToppleUpdate): the host's deletion -- today
        Sim.destroy(delete=True). A world with no host removes nothing."""
        if self._remove is None:
            raise RuntimeError(f'World.remove({thing.name!r}): this world has no host to remove with')
        self._remove(thing, why)

    def pay(self, thing, amount):
        """A module pays its thing's holder (AutoDepositUpdate): the host's money -- today simmoney.Money.deposit
        (the neutral side paid nothing). A world with no host pays nobody."""
        if self._pay is None:
            raise RuntimeError(f'World.pay({thing.name!r}): this world has no host to pay with')
        self._pay(thing, amount)

    def toggled(self, thing, module):
        """A toggle module entered its next ToggleState (ToggleStatusSpecialAbilityUpdate): the host re-sets what the
        state switches -- today simtoggle.entered (Sim.modify for its ObjectStatus / AttributeModifier, the
        LocomotorSet's speed), until the modifier and movement families read the Toggle interface themselves."""
        if self._toggled is None:
            raise RuntimeError(f'World.toggled({thing.name!r}): this world has no host to tell')
        self._toggled(thing, module)

    def modify(self, thing):
        """A module's state moved what a thing's attribute modifiers are (SuppressionUpdate entering or leaving): the
        host re-reads them -- today Sim.modify, until the modifier family is a module of its own."""
        if self._modify is None:
            raise RuntimeError(f'World.modify({thing.name!r}): this world has no host to tell')
        self._modify(thing)

    def suppression_at(self, thing, frame):
        """The suppression fields covering a thing in `frame`: [(end frame, value)], in the order the hits left them,
        those still alive (end after `frame`) within their radius of it, centre to centre in 2D. The host keeps the
        fields (today Sim.suppression_fields, which the combat family's SuppressionNugget fills); none: []."""
        return [] if self._suppression_at is None else self._suppression_at(thing, frame)

    def data_of(self, template, tag):
        """The data of a registered tag's blocks of a template, in order: the parse its things' modules get
        (World.data), for a reader that needs it before or without the modules (Sim.toggles_of: a first
        ToggleState's status is set before a body's modules are made)."""
        cls = self.tags[tag]
        out = []
        for k, (head, inner) in enumerate(self.blocks_of(template, tag)):
            key = (template, tag, k)
            if key not in self.data:
                self.data[key] = cls.DATA.parse(head, inner).seal()
            out.append(self.data[key])
        return tuple(out)

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
