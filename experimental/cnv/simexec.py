"""L6 the world's side of the script executor port (engine/ports/scripts.py, step P1): what the simulator answers an
executor -- the public one (engine/script/executor.py) or the private model's plug-in (scriptplugin.py) -- through
the port's `World`. Moved off Sim (its condition / action / this_player / update / difficulty, and the core actions
the model's SimEngine reported) as a pure move; the rules stay where they were (simcond / simact by name)."""
import collections.abc

from engine.ports import scripts as port
from engine.script import executor as script_executor
from engine.script import lists as script_lists
import simcond
import simworld
import simunits
from simscript import RA3_ONLY

# core actions the plug-in runs itself that the world still watches (World.core): the timeline's notes on them ...
SEEN_CORE = {'SET_FLAG', 'SET_MISSION_OBJECTIVE_STATUS', 'DISPLAY_COUNTDOWN_TIMER',
             'MARK_MISSION_OBJECTIVE_COMPLETED', 'MARK_MISSION_OBJECTIVE_NOT_COMPLETED'}
# ... and the ones that only change something (the quiet clock: Sim.change)
CHANGES = {'INCREMENT_COUNTER', 'DECREMENT_COUNTER', 'SET_MILLISECOND_TIMER', 'SET_RANDOM_MSEC_TIMER'}


def attach(sim, got, executor, skirmish_setup, parts):
    """The Sim's script executor (moved off Sim.__init__): `got` the model's (module, plug-in class) where it is on
    this computer, else None; `parts` (the compiler's NOT mark, unnot) handed in by sim.py, which layered modules do
    not import. Either executor's counter-and-timer table is the Sim's counters and timers (Counters / Timers). With it the scripts as the game runs them: the compiler's NOT flags (package.py writes
    unnot's), one list, the run's difficulty, the Sim the engine's World; the model's FPS is the frame rate. Without it
    the public executor, on our maps the same unnot'd list. Either way, on our maps the container's Lib_Skirmish_Setup is handed the published players.

    executor 'public' with the model there (simrecord --executor public@model, a diagnostic): the model's engine
    holding no scripts, only its frame clock (Sim.frame_now, the model's FPS), and the public executor on it -- the
    simulator's model-or-not branches as with the model, so a cross against the plug-in is the executor alone."""
    sim.eng = None
    sim.clock = sim.__dict__.get('clock') or simworld.FrameClock()   # the world's frame clock without the model
    sim.fps = simunits.LIFE_FPS                     # the frame loop's rate, the model's FPS when there is one
    if not sim.retail:      # the container's start-up, ours with or without the model (a world's, not an executor's)
        sim.handed = skirmish_setup(sim.m.map, set(sim.players.values()))
        sim.library_ai = frozenset(sim.handed)      # kept: their MAKE_BASE stands in for the library's wake
    if got:
        mod, cls = got
        sim.fps = mod.FPS
    if got and executor == 'public':
        sim.eng = cls([], world=SimWorld(sim), difficulty=sim.level, end_library=False)
        sim.clock = sim.eng
    elif got:
        lists = sim.m.script_lists(mod) if sim.retail else mod.from_cnv(parts.unnot(sim.mm.scripts))
        # a retail map's own scripts keep their inverted bit (the engine model: honored for retail's compiled
        # scripts; a02's 'NOT units in the convention center' completed objective 1 at 0:04 with it ignored)
        sim.eng = cls(lists, world=SimWorld(sim), difficulty=sim.level, honor_inverted=sim.retail)
        sim.clock = sim.eng                         # its step moves the frame on
        sim.flags = sim.eng.flags
        sim.model_scripts = True
    if not sim.retail and any(c and c[-1] == parts.NOT for s in sim.mm.scripts for c in s.when):
        sim.used.add('inverted')                    # either executor reads them off unnot's flags
    if not sim.model_scripts:
        # the public executor's lists: a retail map's own per side with its libraries (retail.script_lists), ours
        # one unnamed list as the package writes it, the compiler's NOT read off unnot's flags (set at the frame's
        # top, before the scripts that change the test: bench engine_toggle 第四行 1001), as the model runs them
        lists = (sim.m.script_lists(script_lists) if sim.retail
                 else script_lists.from_cnv(parts.unnot(sim.mm.scripts), parts.NOT))
        sim.executor = script_executor.PublicExecutor(SimWorld(sim), lists, sim.level, sim.fps, clock=sim.clock)
    else:
        sim.executor = sim.eng
    sim.counters, sim.timers = Counters(sim.executor), Timers(sim.executor, sim)   # the executor's one table


class Counters(collections.abc.MutableMapping):
    """An executor's one counter / timer table (`counters`: name -> [value, is_countdown_timer]; `counter(name)` its
    entry, made at 0) as the simulator's counters: a plain counter's value by name (a running timer is not one)."""

    def __init__(self, owner):
        self.owner = owner

    def __getitem__(self, k):
        c = self.owner.counters[k]
        if c[1]:
            raise KeyError(k)
        return c[0]

    def __setitem__(self, k, v):
        self.owner.counter(k)[0] = v

    def __delitem__(self, k):
        del self.owner.counters[k]

    def __iter__(self):
        return (k for k, c in self.owner.counters.items() if not c[1])

    def __len__(self):
        return sum(1 for _ in self)


class Timers(collections.abc.Mapping):
    """... and as its timers: a running countdown's mission second it runs out at (at or before now once out), its
    frames left at the Sim's frame rate."""

    def __init__(self, owner, sim):
        self.owner, self.sim = owner, sim

    def __getitem__(self, k):
        c = self.owner.counters[k]
        if not c[1]:
            raise KeyError(k)
        return self.sim.t + c[0] / self.sim.fps

    def __iter__(self):
        return (k for k, c in self.owner.counters.items() if c[1])

    def __len__(self):
        return sum(1 for _ in self)


class SimWorld(port.World):
    """The port's World over a Sim: conditions by name (simcond.cond), actions by name (Sim.act: simshow and simui
    override it)."""

    def __init__(self, sim):
        self.sim = sim

    def condition(self, eng, name, args):
        if name in RA3_ONLY:
            self.sim.ra3_only.add(name)
        return simcond.cond(self.sim, name, port.this_player(eng, args))

    def action(self, eng, name, args):
        self.sim.act(name, port.this_player(eng, args), eng.script)

    def update(self, eng):
        """Units move and fight in step(), once a DT tick."""

    def difficulty(self, side):
        return None                             # the run's level ('difficulty side')

    def core(self, eng, name, args, script):
        if name in SEEN_CORE:
            self.sim.act(name, list(args), script)
        elif name in CHANGES:
            self.sim.change()

    def assumed(self, what):
        self.sim.used.add(what)
