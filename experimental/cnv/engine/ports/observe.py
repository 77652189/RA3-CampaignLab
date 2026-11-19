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
  `ending()`, `money()`, `income()`;
- internal (the simulator's own bookkeeping, which a game adapter does not have): `state(thing)` (every field a
  thing records, its modules' STATE and Body.FORWARDS by their old names), `report(name)` (log, used, unknown, ...),
  `log_since(n)`, `gaps()`; and the taps a recorder hangs on the loop (`on_frame`, `on_tick`, `scripts`).

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
        return self._w.ending

    def money(self):
        return self._w.money

    def income(self):
        return self._w.income

    # --- internal
    @staticmethod
    def state(thing):
        """A thing's fields as the record shows them: its own (not `modules`), and beside them the STATE fields its
        kernel modules have set -- a field moved off the thing into a module records as it did on the thing (step K1
        on) -- and Body.FORWARDS (a moved dataclass field every body had: None where no module sets it)."""
        d = {k: v for k, v in vars(thing).items() if k != 'modules'}
        for m in thing.modules:
            own = vars(m)
            for k in m.STATE:
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
