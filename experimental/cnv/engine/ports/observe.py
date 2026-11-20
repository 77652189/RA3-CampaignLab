"""The observation port (docs/engine/sim-modules.md 6; module_plan P "观测端口"): what readers of a running world --
the frame record (simrecord), the show and the UI, the player-style runs, reports -- read it through, read only.

Why one port: the object fields move into kernel modules family by family (hp / max_hp / health_floor into the Body
module, then weapons, movement, orders); a reader that reads them here is not touched by a move, only this file is.
Names are the ones the object and the world carry today, so a reader never renames.

Three groups and an internal door:
- the clock: `t`, `fps`, `frame()`;
- things (objects): `things()`, `living()`, `thing(name)`, `is_thing(v)`; a thing's public fields are read off it by
  their names (name template owner x y hp max_hp health ...: the readers' census, R3 12a);
- scripts and players: `flags()`, `counters()`, `timers()` (name -> the mission second it runs out at), `objectives()`,
  `ending()`, `money()`, `income()`, `markers()`, `countdowns()`, `waypoints()`, `banned()`;
- a run's outcome (what a report reads once the run is over: simbench, simchecks, playcheck, mappage): `ending()`,
  `log()`, `series()`, `unknown()`, `ending_line()`;
- players and sight: `human`, `foe`, `enemy(a, b)`, `sees(x, y)`, `side_sees(side, thing)`, `looks(viewer, x, y)`,
  `can_hit(weapon, thing)`, `ground_z(x, y)`;
- internal (the simulator's own bookkeeping, which a game adapter does not have): `state(thing)` (every field a
  thing records, its modules' RECORDED and Body.FORWARDS by their old names), `report(name)` (log, used, unknown, ...),
  `log_since(n)`, `gaps()`, `pending()`, `fresh_sight()`, `specimen(...)` (a dead body made to read a template's
  numbers), combat this tick (`firing()`, `volleys()`, `attachments()`, `expected_damage(...)`: the skirmish AI's,
  R3 13f-2b), the mission's data (`mission()`, `model()`), the run's names and presentation (`point`,
  `text`, `label`, `who`, `input`, `late_captions`, `ending_line`); and the taps a recorder hangs on the loop
  (`on_frame`, `on_tick`, `on_act`, `on_sample`, `on_happen`, `scripts`).

Values are the world's own objects, not copies (a record reads every frame): a reader must not change them."""
from engine.kernel import module as kernel_module


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

    # --- scripts and players
    def flags(self):
        return self._w.flags

    def counters(self):
        return self._w.counters

    def timers(self):
        """Timer name -> the mission second it runs out at (either executor's)."""
        return self._w.timers

    def objectives(self):
        return self._w.objectives

    def ending(self):
        """(how '赢' / '输', mission second, why) once the run ended, else None."""
        return self._w.ending

    # --- a run's outcome
    def log(self):
        """The timeline: (mission second, kind, text) each."""
        return self._w.log

    def series(self):
        """The counter readings: (second, [one value per counter of the check]) each."""
        return self._w.series

    def unknown(self):
        """Action name -> how many times the run met an action the simulator does not know."""
        return self._w.unknown

    def money(self):
        return self._w.money

    def income(self):
        return self._w.income

    def markers(self):
        """Objective -> the names (objects, waypoints) its arrows on the map point at."""
        return self._w.markers

    def countdowns(self):
        """The timers shown on screen as countdowns (their names)."""
        return self._w.countdowns

    def waypoints(self):
        """The map's waypoints: name -> (x, y)."""
        return self._w.waypoints

    def banned(self):
        """(player, template in lower case) the scripts took off a player's build menu."""
        return self._w.banned

    def players(self):
        """The map's players: name -> its entry (the map's PLAYERS)."""
        return self._w.players

    def areas(self):
        """The map's trigger areas: name -> their points (.items())."""
        return self._w.areas

    # --- players and sight
    @property
    def human(self):
        return self._w.human

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
        return g.grids['ground'], g.grids['water'], g.zgrid, (x0, y0), g.world((0, 1))[0] - x0

    # --- internal
    @staticmethod
    def state(thing):
        """A thing's fields as the record shows them: its own (not `modules`), and beside them the RECORDED fields its
        kernel modules have set (their STATE less what never recorded: Module.RECORDED) -- a field moved off the
        thing into a module records as it did on the thing (step K1 on) -- and Body.FORWARDS (a moved dataclass field
        every body had: None where no module sets it)."""
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
        return d

    def report(self, name):
        """One of the run's report fields (log, used, unknown, series, events, ...) by name; None where the world has
        none of that name (a field since removed reads None, as the record always wrote it)."""
        return getattr(self._w, name, None)

    def log_since(self, n):
        """The timeline's lines from the n-th on, and how many there are now."""
        log = self._w.log
        return log[n:], len(log)

    def gaps(self):
        """(kind, name) -> how many times the run met what the simulator does not model."""
        return {k: v.get('n') for k, v in self._w.unmodeled.items()}

    def unmodeled(self):
        """(kind, name) -> {'n', 't' first met, 'what'}: what the run met and the simulator does not model."""
        return self._w.unmodeled

    def blocks(self, thing):
        """What of the way a thing takes up: None, (x, y, radius), or a wall's bar (x, y, angle, length, width)."""
        return self._w.blocks(thing)

    # --- internal: combat this tick (the skirmish AI's reads, R3 13f-2b)
    def firing(self):
        """This tick's aimed fire: [(target, damage per second, shooter)] (a new list each tick)."""
        return self._w.firing

    def volleys(self):
        """This tick's volleys: [(pick, weapon, shooter)] (a new list each tick)."""
        return self._w.volleys

    def attachments(self):
        """Child serial -> (child, parent, module rule): what rides on what."""
        return self._w.attachments

    def expected_damage(self, thing, behind, ahead, now=None):
        """The damage a thing expects in the next `ahead` seconds from the fire told it is coming (InformTarget:
        simdamage.Damage's table; the AI micro's incoming-damage callback). Asking drops the rows past their expiry
        and notes the history it lacks (`behind`) as a gap -- the table's own upkeep, not a change of the fight."""
        return self._w.expected_damage(thing, behind, ahead, now=now)

    # --- internal: the production menu (a command port's, once there is one: what an order to build may ask for)
    def own(self):
        """Template id -> its unit data as compiled (what simunits reads a menu and a price off)."""
        return self._w.own

    def factories(self, player):
        """A player's living structures that build units."""
        return self._w.factories(player)

    def offers(self, player):
        """[(template or upgrade, cost, seconds)] a player can build or buy now."""
        return self._w.offers(player)

    def queues(self):
        """Factory serial (Thing.serial) -> its jobs ({'template', 'progress', ...})."""
        return self._w.queues

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
