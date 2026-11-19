"""World (docs/engine/sim-modules.md 5): one game's mutable state, all in the instance -- the schedule, the parse cache
of module data, the audit set and the gap log. Two worlds in one process share nothing (tests/test_kernel.py). Today
the Sim hosts it: Sim.world, and the Sim's `used` / `unmodeled` are the world's own."""
import weakref

from engine.kernel import factory, interfaces, module, schedule, snap  # noqa: F401  (module: Thing, which sim.Body is)


def no_blocks(template, tag):
    return []


class World:
    def __init__(self, blocks=no_blocks, tags=factory.TAGS, kill=None, remove=None, pay=None, toggled=None,
                 modify=None, suppression_at=None, spawn=None, vacate=None, create=None, fire=None):
        """blocks(template, tag) -> [(head, inner)]: the template data port; tags: the factory's registry;
        kill(thing, why, death, cause): the host's death of a thing (World.kill); create(thing, ocl, airborne): the
        host's making of what a thing's death lists (World.create); fire(thing, weapon): the host's firing of a
        weapon where a thing died (World.fire); remove(thing, why): the host's deletion of one,
        no death (World.remove); pay(thing, amount): the host's payment to a thing's holder (World.pay);
        toggled(thing, module): what the host re-sets when a toggle enters its next state (World.toggled);
        modify(thing): the host's re-reading of a thing's attribute modifiers (World.modify);
        suppression_at(thing, frame): the suppression fields covering a thing (World.suppression_at);
        spawn(thing, module, template): the host's making of a thing a Spawn module of `thing` makes (World.spawn);
        vacate(thing, delete): the host's emptying of a Contain module's thing that died or was deleted
        (World.vacate)."""
        self.blocks, self.tags, self._kill, self._remove, self._pay = blocks, tags, kill, remove, pay
        self._toggled, self._modify, self._suppression_at = toggled, modify, suppression_at
        self._spawn, self._vacate, self._create, self._fire = spawn, vacate, create, fire
        self.schedule = schedule.Schedule()
        self.data = {}          # (template, tag, index) -> ModuleData, parsed once a world
        self.block_lists = {}   # (template, tag) -> the port's blocks, asked once a world
        self.used = set()       # the audit set: rules the run leaned on
        self.gaps = {}          # (kind, name) -> {'n' times, 't' first met, 'what' first note} (Sim.gap writes it)
        self.frame = 0          # the frame of the cell now running (simloop sets it), what wake() defaults to
        self.made = 0           # things built so far: the next one's serial (Thing.serial)
        self.late = {}          # serial -> [(tag, head)]: the modules attached after its thing was made (attach)
        self.numbered = weakref.WeakValueDictionary()   # serial -> the thing this world numbered (owns)

    def build(self, thing, frame):
        """Number a new thing (Thing.serial), make its modules (none unless a tag is registered) and hold its update
        modules from `frame`."""
        thing.serial, self.made = self.made, self.made + 1
        self.numbered[thing.serial] = thing
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

    def attach(self, thing, tag, frame=None, head=''):
        """One module of a registered tag made on a thing after it was made -- its data the parse of a block of the
        tag with attributes `head` (default: none), no on_create -- and held from `frame` (default: the frame of the
        cell now running): the skirmish AI's late lifetime (simbody.last_until), a reload for a power no block of the
        thing serves (simpower.start_reload). Noted in `late` by the thing's serial (a thing this world numbered), so
        a snapshot's thing gets it again (remake). -> the module."""
        m = self._attached(thing, tag, head)
        if hasattr(thing, 'serial'):
            if thing.serial not in self.late:
                self._forget_late(thing, self.late)
            self.late.setdefault(thing.serial, []).append((tag, head))
        if isinstance(m, interfaces.Update):
            self.schedule.add(m, self.frame if frame is None else frame)
        return m

    @staticmethod
    def _forget_late(thing, late):
        """A thing's row of `late` goes when the thing is reclaimed (numbered is weak: a thing replaced under its name
        and dropped leaves no row behind, review 1119j #3). Bound to the table it was written in: a restore's new
        table is not touched by the old one's things."""
        weakref.finalize(thing, late.pop, thing.serial, None)

    def _attached(self, thing, tag, head):
        cls = self.tags[tag]
        m = cls(thing, cls.DATA.parse(head, '').seal(), self)
        thing.modules = tuple(thing.modules) + (m,)
        return m

    def remake(self, thing, late, n):
        """A snapshot's thing that the new world made short (World.restore): the modules its template makes, when it
        has none (a thing made in the run, built bare by the host), then the last of `late` ([(tag, head)], the
        snapshot's attached ones) it lacks, up to `n` modules -- made bare: no on_create, not scheduled (the
        schedule and every module's STATE are the snapshot's)."""
        if not thing.modules and self.tags:
            thing.modules = factory.build(thing, self.blocks_of, self.data, self.tags, self)
        lack = n - len(thing.modules)
        if lack > len(late):
            raise ValueError(f'World.restore: thing {thing.serial} ({thing.name!r}) has {len(thing.modules)} modules '
                             f'and {len(late)} attached, the snapshot {n}')
        for tag, head in late[len(late) - lack:] if lack > 0 else ():
            self._attached(thing, tag, head)

    def kill(self, thing, why, death='NORMAL', cause=''):
        """A module kills its thing (LifetimeUpdate): the host's death -- today Sim.destroy -- of type `death`
        (module.Death's death) and `cause` (its cause: 'lifetime' for a death of age). A world with no host kills
        nothing."""
        if self._kill is None:
            raise RuntimeError(f'World.kill({thing.name!r}): this world has no host to kill with')
        self._kill(thing, why, death, cause)

    def create(self, thing, ocl, airborne):
        """A CreateObjectDie module's thing died and its ObjectCreationList `ocl` is to be made (step B5b): the host
        makes it where the thing died -- today a death of age's objects as things (simbody.Life.leave), and with
        `airborne` a death in the air's falling wrecks as their landing's death blasts (simbody.Life.air_crash). A
        world with no host makes nothing."""
        if self._create is None:
            raise RuntimeError(f'World.create({thing.name!r}): this world has no host to make with')
        self._create(thing, ocl, airborne)

    def fire(self, thing, weapon):
        """A FireWeaponWhenDead module's thing died and its DeathWeapon goes off (step B5c): the host fires the
        WeaponTemplate `weapon` where the thing died, as the thing's -- today its DamageNuggets queued as death blasts
        (simbody.Life.fire, simdamage.death_blast_due). A world with no host fires nothing."""
        if self._fire is None:
            raise RuntimeError(f'World.fire({thing.name!r}): this world has no host to fire with')
        self._fire(thing, weapon)

    def remove(self, thing, why):
        """A module takes its thing out, no death (a toppled prop gone: ToppleUpdate): the host's deletion -- today
        Sim.delete. A world with no host removes nothing."""
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

    def spawn(self, thing, module, template):
        """A Spawn module makes a thing of `template` for its thing (SpawnBehavior's replacement): the host makes it
        -- today Sim.spawn_child (Sim.add at the parent's spot; the child's SlavedUpdate enslaved, the module told
        adopt). -> the thing made. A world with no host makes nothing."""
        if self._spawn is None:
            raise RuntimeError(f'World.spawn({thing.name!r}): this world has no host to make with')
        return self._spawn(thing, module, template)

    def vacate(self, thing, delete):
        """A Contain module's thing died (delete False: its passengers out alive, or killed with it by
        KillPassengersOnDeath) or was deleted (True: they go with it) -- step B4c: the host empties it, today
        simgarrison.Garrisons.died (it keeps the walk out, the kill and the owner given back). A thing already
        emptied: nothing. A world with no host empties nothing."""
        if self._vacate is None:
            raise RuntimeError(f'World.vacate({thing.name!r}): this world has no host to empty with')
        self._vacate(thing, delete)

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

    def snapshot(self, things, extra=None):
        """The world's part of a snapshot (docs/engine/sim-modules.md 9.2, step S), in values engine/kernel/snap.py
        keeps: the count of things made, the frame, the audit set, the gaps, the schedule (each cell's modules in the
        cell's order with wake frame and seq, and the running count) and every module's STATE. `things`: all the
        host's things, the dead it still holds too; a held module whose thing is not among them is an error.
        `extra`: the host's own marks (snap.encode). Wiring, the parse caches and the template port are the new
        world's own (World.restore writes onto a world made for the same mission)."""
        things = list(things)
        serials = [t.serial for t in things]
        if len(set(serials)) != len(serials):
            raise ValueError('World.snapshot: two things of one serial')
        held = set(serials)
        cells = []
        for phase, cell in self.schedule.cells.items():
            rows = []
            for m, at in cell.items():
                if m.thing.serial not in held or not any(x is m for x in m.thing.modules):
                    raise ValueError(f'World.snapshot: {type(m).__name__} of {m.thing.name!r} is held by the schedule '
                                     'but its thing is not among the things given')
                rows.append([snap.encode(m), at, self.schedule.seq[m]])
            cells.append([phase, rows])
        return {'made': self.made, 'frame': self.frame,
                'used': snap.encode(self.used, extra, 'used'), 'gaps': snap.encode(self.gaps, extra, 'gaps'),
                'schedule': {'cells': cells, 'added': self.schedule.added},
                'things': [[t.serial, [type(m).__name__ for m in t.modules],
                            [snap.module_state(m, extra) for m in t.modules]] for t in things],
                'late': [[k, [list(x) for x in v]] for k, v in sorted(self.late.items()) if k in held]}

    def restore(self, snap_, things, extra=None):
        """Write a World.snapshot onto this world, made anew for the same mission: `things` serial -> Thing, the
        host's things for the snapshot's, each thing's serial set here: made with their modules, or bare (a thing
        made in the run: no modules yet) -- the modules its template makes and the snapshot's attached ones a thing
        lacks are made here (remake). The things and their modules must then be the snapshot's (same serials, same
        module classes in order), else nothing more is written past the check. The audit set and the gaps are
        written in place (the host holds them under other names)."""
        want = {row[0]: row[1] for row in snap_['things']}
        if set(want) != set(things):
            raise ValueError(f'World.restore: things {sorted(set(want) ^ set(things))[:10]} are on one side only')
        late = {k: [tuple(x) for x in v] for k, v in snap_['late']}
        self.numbered = weakref.WeakValueDictionary()
        for serial, t in things.items():
            t.serial = serial
            self.numbered[serial] = t
            if len(t.modules) < len(want[serial]) and (not t.modules or late.get(serial)):
                self.remake(t, late.get(serial, []), len(want[serial]))
        for serial, names in want.items():
            have = [type(m).__name__ for m in things[serial].modules]
            if have != names:
                raise ValueError(f'World.restore: thing {serial} ({things[serial].name!r}) has modules {have}, '
                                 f'the snapshot {names}')
        self.late = late
        for serial in late:
            self._forget_late(things[serial], late)
        for serial, _names, states in snap_['things']:
            for m, state in zip(things[serial].modules, states):
                snap.set_module_state(m, state, things, extra)
        self.made, self.frame = snap_['made'], snap_['frame']
        self.used.clear()
        self.used.update(snap.decode(snap_['used'], things, extra))
        self.gaps.clear()
        self.gaps.update(snap.decode(snap_['gaps'], things, extra))
        s = self.schedule
        s.cells, s.seq = {}, {}
        for phase, rows in snap_['schedule']['cells']:
            cell = s.cells[phase] = {}
            for ref, at, seq in rows:
                m = snap.decode(ref, things)
                cell[m] = at
                s.seq[m] = seq
        s.added = snap_['schedule']['added']

    def wake(self, module, frame=None):
        """Run an update module at `frame`, by default the frame of the cell now running (`frame`, which the frame
        loop sets before each cell): a module woken by a cell before its own runs this frame, by one after it the
        next (step K2)."""
        self.schedule.wake(module, self.frame if frame is None else frame)
