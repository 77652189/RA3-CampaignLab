"""The observation port (docs/engine/sim-modules.md 6; module_plan P "观测端口"): what readers of a running world --
the frame record (simrecord), the show and the UI, the player-style runs, reports -- read it through, read only.

Why one port: the object fields move into kernel modules family by family (hp / max_hp / health_floor into the Body
module, then weapons, movement, orders); a reader that reads them here is not touched by a move, only this file is.
Names are the ones the object and the world carry today, so a reader never renames.

Three groups and an internal door:
- the clock: `t`, `fps`, `frame()`;
- things (objects): `things()`, `living()`, `thing(name)`, `is_thing(v)`, `contents(thing)` (who is inside),
  `home(thing)` (the owner an emptied garrison goes back to), `queue(thing)` (what it builds), `jobs(thing)` (the same whole: paid, filled, held), `clocks(thing)` (its timed modules' frames); a thing's public fields are
  read off it by their names (name template owner x y hp max_hp health ...: the readers' census, R3 12a);
- scripts and players: `flags()`, `counters()`, `timers()` (name -> the mission second it runs out at), `objectives()`,
  `ending()`, `money()`, `income()`, `sciences(player)`, `player_upgrades(player)`, `power(player)`, `markers()`,
  `countdowns()`, `waypoints()`, `banned()`;
- a run's outcome (what a report reads once the run is over: simbench, simchecks, playcheck, mappage): `ending()`,
  `log()`, `series()`, `unknown()`, `ending_line()`;
- players and sight: `human`, `foe`, `relations()`, `enemy(a, b)`, `sees(x, y)`, `side_sees(side, thing)`,
  `looks(viewer, x, y)`, `can_hit(weapon, thing)`, `ground_z(x, y)`;
- internal (the simulator's own bookkeeping, which a game adapter does not have): `state(thing)` (every field a
  thing records, its modules' RECORDED and Body.FORWARDS by their old names), `report(name)` (log, used, unknown, ...),
  `log_since(n)`, `gaps()`, `pending()`, `fresh_sight()`, `specimen(...)` (a dead body made to read a template's
  numbers), combat this tick (`firing()`, `volleys()`, `attachments()`, `expected_damage(...)`: the skirmish AI's,
  R3 13f-2b), the mission's data (`mission()`, `model()`), the run's names and presentation (`point`,
  `text`, `label`, `who`, `input`, `late_captions`, `ending_line`); and the taps a recorder hangs on the loop
  (`on_frame`, `on_tick`, `on_act`, `on_sample`, `on_happen`, `scripts`).

A table, list or set comes back read only and live (engine/ports/readonly.view: not a copy, a record reads every
frame; its write half raises, to any depth -- review 1119z P2 #2); ground_map's arrays as copies one cannot write. A
thing comes back itself -- `thing`, `living`, and a field that holds one (`state(u)['goal']`) hand the live object,
whose fields can be set through it: the read-only promise covers tables and arrays, not things (review 1120dd P2;
a read-only thing handle is an open question, handoff-r3). The
readers a Battlefield file is read through (contents, home, jobs, clocks, sciences, player_upgrades, power, relations: step S 11d,
experimental/cnv/engine/state/battlefield.py) give names and numbers only, so a game adapter can give the same."""
from engine.kernel import interfaces
from engine.kernel import module as kernel_module
from engine.ports.readonly import view


def _fixed(a):
    """An array as it is now, its own copy with the write flag off: ground_map's grids were the routing grid itself
    (review 1120bb P2 #2), and a view with the flag off could turn it back on (`setflags(write=True)`: the view's
    base writeable, review 1120dd P2) -- a copy turned writeable writes only itself."""
    v = a.copy()
    v.flags.writeable = False
    return v


class Observe:
    """Read-only view of one running world (today a sim.Sim)."""

    def __init__(self, world):
        self._w = world

    # --- the clock
    @property
    def t(self):
        """Mission seconds."""
        return self._w.t

    @property
    def fps(self):
        return self._w.fps

    def frame(self):
        """The logic frame now (the frame clock, Sim.frame_now)."""
        return self._w.frame_now()

    # --- things
    def things(self):
        """Every thing, dead ones too, in the order they were made."""
        return self._w.bodies.values()

    def living(self):
        return self._w.living()

    def thing(self, name):
        return self._w.bodies.get(name)

    @staticmethod
    def is_thing(v):
        return isinstance(v, kernel_module.Thing)

    def contents(self, thing):
        """The names of the things inside a building's garrison or a transport, in the order they came in ([] for
        a thing that holds none or cannot)."""
        return [p.name for p in self._w.garrison.held(thing)]

    def by_serial(self, serial):
        """The thing made with this serial (dead too, None once deleted or never made)."""
        return self._w.world.numbered.get(serial)

    def fighting(self, thing):
        """Whether a unit is busy fighting: engaged, or its order's target is a thing."""
        return thing.engaged or isinstance(thing.goal, kernel_module.Thing)

    def garrisons(self, thing, own_defenses):
        """The buildings a unit could be sent into, in the world's order: its player's base defenses
        (own_defenses), else the other garrisons (Garrisons.places)."""
        return self._w.garrison.places(thing, own_defenses)

    def inside(self, thing):
        """The garrison or transport a unit is inside now, None when it is in none."""
        return self._w.garrison.where.get(thing.serial)

    def heading(self, thing):
        """The building a unit was sent into and is on its way to, None when it is not walking into one."""
        return (self._w.garrison.going.get(thing.serial) or (None, None))[1]

    def boarding(self, thing):
        """Whether a unit is inside a garrison or transport, or sent into one and on its way."""
        return self._w.garrison.busy(thing)

    def room(self, transport, thing):
        """The free slots of a transport if it takes the unit, else 0 (Garrisons.room)."""
        return self._w.garrison.room(transport, thing)

    def home(self, thing):
        """The owner a garrisoned building goes back to when its last passenger is out (the owner it had before its
        first), None for one that holds none or a transport (which keeps its owner)."""
        return self._w.garrison.home(thing)

    def queue(self, thing):
        """A factory's jobs in order: [(template, progress 0..1)] ([] for a thing that builds nothing). The world
        keeps a job's progress in per cent (float32): read here / 100, a job done and waiting to come out at 1."""
        return [(job['template'], min(1.0, job['progress'] / 100)) for job in self._w.production.jobs(thing.serial)]

    def jobs(self, thing):
        """A factory's jobs in order, whole: [(template, progress 0..1, paid so far, the logic frame it filled or None,
        held)] -- held: a job not full that stands for a ban (its unit off the owner's menu, the owner's unit
        construction disabled: the hold Sim.production.due keeps a unit job to, upgrades' never). [] for a thing that
        builds nothing (a Battlefield file's queue, S 11d step 7)."""
        p = self._w.production
        return [(job['template'], min(1.0, job['progress'] / 100), job['paid'], job['full'], p.held(job))
                for job in p.jobs(thing.serial)]

    def clocks(self, thing):
        """Its timed modules' frames in the order made (interfaces.Clocked: autoheal, lifetime, sale, unpacking):
        [(the module's XML tag, {name: logic frame or None; autoheal's hurt a bool})] ([] for a thing with none)."""
        return [(type(m).TAGS[0], dict(m.clocks())) for m in thing.find(interfaces.Clocked)] if thing.modules else []

    # --- scripts and players
    def flags(self):
        return view(self._w.flags)

    def counters(self):
        return view(self._w.counters)

    def timers(self):
        """Timer name -> the mission second it runs out at (either executor's)."""
        return view(self._w.timers)

    def objectives(self):
        return view(self._w.objectives)

    def ending(self):
        """(how '赢' / '输', mission second, why) once the run ended, else None."""
        return self._w.ending

    # --- a run's outcome
    def log(self):
        """The timeline: (mission second, kind, text) each."""
        return view(self._w.log)

    def series(self):
        """The counter readings: (second, [one value per counter of the check]) each."""
        return view(self._w.series)

    def unknown(self):
        """Action name -> how many times the run met an action the simulator does not know."""
        return view(self._w.unknown)

    def money(self):
        return view(self._w.money)

    def income(self):
        return view(self._w.income)

    def sciences(self, player):
        """(the protocols a player holds, sorted; its protocol points), or None for a player with no protocols (not
        a playable faction: the neutral side, a map's civilian slots)."""
        book = self._w.books.get(player)
        return None if book is None else (sorted(book.owned), book.points)

    def player_upgrades(self, player):
        """The upgrades a player was given (GIVE_PLAYER_UPGRADE), sorted."""
        return sorted(self._w.player_ups.get(player, ()))

    def power(self, player):
        """A player's power: (made, used), as its living things make and use it now."""
        return self._w.power(player)

    def markers(self):
        """Objective -> the names (objects, waypoints) its arrows on the map point at."""
        return view(self._w.markers)

    def countdowns(self):
        """The timers shown on screen as countdowns (their names)."""
        return view(self._w.countdowns)

    def waypoints(self):
        """The map's waypoints: name -> (x, y)."""
        return view(self._w.waypoints)

    def banned(self):
        """(player, template in lower case) the scripts took off a player's build menu."""
        return view(self._w.banned)

    def players(self):
        """The map's players: name -> its entry (the map's PLAYERS)."""
        return view(self._w.players)

    def areas(self):
        """The map's trigger areas: name -> their points (.items())."""
        return view(self._w.areas)

    # --- players and sight
    @property
    def human(self):
        return self._w.human

    def relations(self):
        """The run's explicit directed relations: (a, b) -> 'Enemy' / 'Neutral' / 'Friend', how player a takes b (the
        map's own -- a retail map lists every pair -- and what scripts set since). A pair not in it falls back to
        `enemy(a, b)`'s default."""
        return view(self._w.relations)

    @property
    def foe(self):
        return self._w.foe

    def enemy(self, a, b):
        """Whether players a and b are enemies."""
        return self._w.enemy(a, b)

    def sees(self, x, y, air=False):
        """Whether the human player sees a point."""
        return self._w.sees(x, y, air)

    def side_sees(self, side, thing):
        """Whether a side (it or a friend) sees a thing, this tick."""
        return self._w.side_sees(side, thing)

    def looks(self, viewer, x, y, air=False):
        """Whether one thing sees a point (its vision, the high-ground rule)."""
        return self._w.looks(viewer, x, y, air)

    def can_hit(self, weapon, thing):
        """Whether a weapon (one of a thing's `weapons`) can take that thing."""
        return self._w.can_hit(weapon, thing)

    def ground_z(self, x, y):
        """The ground's height at a point."""
        return self._w.ground.z(x, y)

    def ground_map(self):
        """The routing grid as a picture of the ground: (walkable, water, the height at each cell's corner -- arrays
        of the grid's rows and columns; the height's may be a row / column longer --, (x, y) of cell (0, 0), a cell's
        size in map units)."""
        g = self._w.ground
        x0, y0 = g.world((0, 0))
        return _fixed(g.grids['ground']), _fixed(g.grids['water']), _fixed(g.zgrid), (x0, y0), g.world((0, 1))[0] - x0

    # --- internal
    @staticmethod
    def state(thing):
        """A thing's fields as the record shows them: its own (not `modules`), and beside them the RECORDED fields its
        kernel modules have set (their STATE less what never recorded: Module.RECORDED) -- a field moved off the
        thing into a module records as it did on the thing (step K1 on) -- and Body.FORWARDS (a moved dataclass field
        every body had: None where no module sets it). A new dict each call, its values read only (readonly.view: a
        reader that cleared `path` emptied the unit's route, review 1120bb P2 #2)."""
        d = {k: v for k, v in vars(thing).items() if k != 'modules'}
        for m in thing.modules:
            own = vars(m)
            # a base older than RECORDED (the golden layer records it with this port) recorded all of STATE
            for k in getattr(m, 'RECORDED', m.STATE):
                if k in own:
                    if k in d:
                        raise ValueError(f'{thing.name}: {type(m).__name__}.{k} is already a field of the body')
                    d[k] = own[k]
        for k in getattr(type(thing), 'FORWARDS', ()):
            d.setdefault(k, getattr(thing, k))
        return {k: view(v) for k, v in d.items()}

    def report(self, name):
        """One of the run's report fields (log, used, unknown, series, events, ...) by name; None where the world has
        none of that name (a field since removed reads None, as the record always wrote it)."""
        return view(getattr(self._w, name, None))

    def log_since(self, n):
        """The timeline's lines from the n-th on, and how many there are now."""
        log = self._w.log
        return log[n:], len(log)

    def gaps(self):
        """(kind, name) -> how many times the run met what the simulator does not model."""
        return {k: v.get('n') for k, v in self._w.unmodeled.items()}

    def unmodeled(self):
        """(kind, name) -> {'n', 't' first met, 'what'}: what the run met and the simulator does not model."""
        return view(self._w.unmodeled)

    def blocks(self, thing):
        """What of the way a thing takes up: None, (x, y, radius), or a wall's bar (x, y, angle, length, width)."""
        return self._w.blocks(thing)

    # --- internal: combat this tick (the skirmish AI's reads, R3 13f-2b)
    def firing(self):
        """This tick's aimed fire: [(target, damage per second, shooter)] (a new list each tick)."""
        return view(self._w.firing)

    def volleys(self):
        """This tick's volleys: [(pick, weapon, shooter)] (a new list each tick)."""
        return view(self._w.volleys)

    def attachments(self):
        """Child serial -> (child, parent, module rule): what rides on what."""
        return view(self._w.attachments)

    def expected_damage(self, thing, behind, ahead, now=None):
        """The damage a thing expects in the next `ahead` seconds from the fire told it is coming (InformTarget:
        simdamage.Damage's table; the AI micro's incoming-damage callback). Asking changes nothing: the table drops
        expired rows on its own clock."""
        return self._w.expected_damage(thing, behind, ahead, now=now)

    # --- internal: the production menu (a command port's, once there is one: what an order to build may ask for)
    def own(self):
        """Template id -> its unit data as compiled (what simunits reads a menu and a price off)."""
        return view(self._w.own)

    def factories(self, player):
        """A player's living structures that build units."""
        return self._w.factories(player)

    def offers(self, player):
        """[(template or upgrade, cost, seconds)] a player can build or buy now."""
        return self._w.offers(player)

    def mission(self):
        """The mission as written (parts.Mission: its map's SITES / BORDERS, cast, objectives) -- data, not the run."""
        return self._w.m

    def model(self):
        """The mission as compiled (strings, subtitles, scripts, units) -- data, not the run."""
        return self._w.mm

    def input(self):
        """Whether the player's input is on (DISABLE_INPUT / ENABLE_INPUT)."""
        return self._w.input

    def pending(self):
        """Whether the run still waits on something (a timer, a move, a script event): the loop's quiet check."""
        return self._w.pending()

    def fresh_sight(self):
        """Forget this tick's sight (side_sees' cache), so the next side_sees reads where things are now (a player's
        decision between ticks; the loop clears it each tick too)."""
        self._w.seen = {}

    def specimen(self, name, template, owner, x=0.0, y=0.0):
        """A dead thing of a template, out of the fight, made only to read the template's numbers (weapons, armour,
        health, vision) -- the one door that adds to the world: the numbers are built by making a body."""
        b = self._w.add(name, template, owner, x, y)
        b.alive = False
        return b

    # --- internal: the run's names and its presentation records (simshow, the UI)
    def point(self, name):
        """Where a name is: a waypoint, an area's middle, a site, a mark, a named thing, '@x,y'; None if nowhere."""
        return self._w.point(name)

    def text(self, key):
        """A string key's text (the mission's string table; the key itself if it has none)."""
        return self._w.text(key)

    def label(self, thing):
        """A thing's name for a reader: its cast role, else its name, else its template."""
        return self._w.label(thing)

    def who(self, player):
        """A player's name for a reader: 玩家 / 敌人 / its side."""
        return self._w.who(player)

    def box_at(self, t):
        """The caption up at mission second t, or None."""
        return self._w.box_at(t)

    def panel_at(self, t):
        """The subtitles stacked in the dialogue panel at mission second t."""
        return self._w.panel_at(t)

    def late_captions(self):
        return self._w.late_captions()

    def ending_line(self):
        return self._w.ending_line()

    def on_act(self, before=None, after=None):
        """Call before(name, args, script) / after(name, args, script) around each action the world carries out
        (Sim.act: the script executor's and a script event's). A tap hung later runs outside one hung earlier. Sim.act's
        keywords (`unit`, the player's ground power's caster) pass through untouched; the taps see the three."""
        w = self._w
        inner = w.act

        def act(name, a, script, *rest, **kw):     # Sim.act's unit by place too (review 11-19 u P3)
            if before is not None:
                before(name, a, script)
            r = inner(name, a, script, *rest, **kw)
            if after is not None:
                after(name, a, script)
            return r
        w.act = act

    def on_sample(self, fn):
        """Call fn() after each whole second's sample of the loop."""
        w = self._w
        inner = w.sample

        def sample():
            r = inner()
            fn()
            return r
        w.sample = sample

    def on_happen(self, fn):
        """Call fn(event) before each script event (the player's orders, Sim.events) is carried out."""
        w = self._w
        inner = w.happen

        def happen(e):
            fn(e)
            return inner(e)
        w.happen = happen

    def on_frame(self, fn):
        """Call fn(frame) before each of the engine model's script steps (nothing without the model)."""
        eng = self._w.eng
        if eng is None:
            return
        inner = eng.step

        def step():
            fn(eng.frame)
            return inner()
        eng.step = step

    def on_tick(self, fn):
        """Call fn() after each DT tick of the loop."""
        w = self._w
        tick = w.step

        def step_tick():
            r = tick()
            fn()
            return r
        w.step = step_tick

    def scripts(self):
        """(the script executor (engine/ports/scripts.Executor), whether it is the engine model's plug-in)."""
        ex = self._w.executor
        return ex, self._w.eng is not None and ex is self._w.eng
