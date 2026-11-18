"""The public script executor (ADR 0033 item 2: the real implementation; the private model's script core is an
optional plug-in to the same port, engine/ports/scripts.py). It asks the world every condition (World.condition) and
every action (World.action) but its own -- the timers', the script switches', CALL_SUBROUTINE's -- which it does
itself and tells the world of (World.core), as the plug-in does.

What it runs, once a frame (script-semantics.md 1): the script lists (engine/script/lists.py) in side order; per
list its loose scripts in file order, then its active groups that are not subroutines (a group's items the same
way, one level down: INFERRED for RA3's nested groups); a subroutine only when CALL_SUBROUTINE calls it. A script runs
when it is active, on at the difficulty (World.difficulty of its list's side, else the run's) and its evaluation
frame is due (one with an interval first 0..2 s into the game, at random, then every interval); then its actions if
one of its OR groups holds (ANDed; an empty OR group skipped; a disabled condition holds), else its else actions --
a once script then off, either branch (Generals executeScript). An inverted condition is the world's answer negated
(World.assumed('inverted') for ours, the compiler's NOT mark: `assume_inverted`). It keeps no clock but a count of
its steps (the intervals' frames): it runs on the world's (Executor).

The counters and the timers are one table (docs/engine/script-semantics.md 3): a name's `[value, is_countdown_timer]`,
made at 0 the first time it is used; a running timer's value is the frames it has left, taken down by one at the start
of each frame, before the scripts, until it is -1; TIMER_EXPIRED is a running timer at 0 or below (bench
engine_script frames, engine_timer). The counter actions are still the world's (simact_world), on the same table
through simexec.Counters. ENABLE_SCRIPT / DISABLE_SCRIPT switch a group and a script of that name both (the first
of a name: Generals findScript / findGroup); a once script that fired is armed again (script-semantics.md 8 item 10).
CALL_SUBROUTINE runs a subroutine group's scripts (the group active) or a subroutine script (Generals
callSubroutine; not measured in RA3: INFERRED)."""
import math
import random

from engine.ports import scripts as port
from engine.script import lists as script_lists

# the timer actions the executor does itself (script-semantics.md 3) ...
TIMER_ACTIONS = frozenset({'SET_MILLISECOND_TIMER', 'SET_RANDOM_MSEC_TIMER', 'SET_TIMER', 'SET_RANDOM_TIMER',
                           'STOP_TIMER', 'RESTART_TIMER', 'SUB_FROM_MSEC_TIMER', 'ADD_TO_MSEC_TIMER'})
# ... and the script switches and calls (script-semantics.md 1, 5); the world hears of each through World.core
SCRIPT_ACTIONS = frozenset({'ENABLE_SCRIPT', 'DISABLE_SCRIPT', 'CALL_SUBROUTINE', 'NO_OP'})
OWN_ACTIONS = TIMER_ACTIONS | SCRIPT_ACTIONS


class PublicExecutor(port.Executor):
    """`lists`: the map's script lists (engine/script/lists.ScriptList, in side order); `level`: the run's difficulty
    index into a script's levels; `fps`: logic frames a second (a timer's seconds as frames, an interval's);
    `clock`: an object whose `frame` it moves on before each frame's scripts (the model's engine as the world's
    clock, simexec.attach's executor 'public'), None: the world's clock; `assume_inverted`: an inverted condition is
    the compiler's NOT mark (ours), an assumption the run lists; `seed`: the intervals' first frames."""

    def __init__(self, world, lists, level, fps, clock=None, assume_inverted=False, seed=0):
        self.world, self.lists, self.level = world, lists, level
        self.fps, self.script, self.clock = fps, None, clock
        self.assume_inverted = assume_inverted
        self.counters = {}              # name -> [value, is_countdown_timer]: the counters and timers, one table
        self.steps = 0                  # frames run (the intervals' clock)
        self._side = ''
        self._scripts, self._groups = {}, {}
        for lst in lists:
            self._index(lst.items)
        rng = random.Random(seed)       # Generals: a script with a delay first runs 0..2 s into the game
        self._next = {id(s): rng.randint(0, 2 * fps) if s.interval > 0 else 0 for s in self._scripts.values()}

    def _index(self, items):
        for it in items:
            if isinstance(it, script_lists.Group):
                self._groups.setdefault(it.name, it)
                self._index(it.items)
            else:
                self._scripts.setdefault(it.name, it)

    def script_named(self, name):
        """The script of that name (the first of it), None where none (UNIT_EXECUTE_SEQUENTIAL_SCRIPT)."""
        return self._scripts.get(name)

    def counter(self, name):
        """The table's entry for `name`, made (a plain counter at 0) the first time it is used."""
        return self.counters.setdefault(name, [0, False])

    def frames(self, secs):
        """A timer's seconds as frames: ceil(seconds x frame rate) (script-semantics.md 3)."""
        return int(math.ceil(round(float(secs) * self.fps, 6)))

    # ----------------------------------------------------------------------------------------- the frame
    def step(self):
        if self.clock is not None:
            self.clock.frame += 1
        self.steps += 1
        for c in self.counters.values():
            if c[1] and c[0] >= 0:
                c[0] -= 1
        for lst in self.lists:
            self._side = lst.side
            self._run_items(lst.items)

    def _run_items(self, items):
        for s in items:                         # loose scripts first, then groups (Generals executeScripts)
            if isinstance(s, script_lists.Script) and not s.subroutine:
                self.execute(s)
        for g in items:
            if isinstance(g, script_lists.Group) and g.active and not g.subroutine:
                self._run_items(g.items)

    def execute(self, s):
        if not s.active:
            return
        level = self.world.difficulty(self._side)
        if not s.levels[self.level if level is None else level]:
            return
        if s.interval > 0:
            if self.steps < self._next.get(id(s), 0):
                return
            self._next[id(s)] = self.steps + s.interval * self.fps
        if any(o and all(self.holds(c) for c in o) for o in s.ors):
            self.do(s.actions, s)
        elif s.else_actions:
            self.do(s.else_actions, s)
        else:
            return
        if s.once:
            s.active = False

    def do(self, actions, s):
        for a in actions:
            if a.enabled:
                self.action(a.name, list(a.args), s)

    def holds(self, c):
        if not c.enabled:                       # INFERRED
            return True
        if c.inverted and self.assume_inverted:
            self.world.assumed('inverted')
        if c.name == 'CONDITION_TRUE':
            v = True
        elif c.name == 'CONDITION_FALSE':
            v = False
        elif c.name == 'TIMER_EXPIRED':
            v = self.timer_expired(c.args[0])
        else:
            v = self.world.condition(self, c.name, list(c.args))
        return (not v) if c.inverted else v

    def timer_expired(self, name):
        c = self.counters.get(name)
        if c is None:
            self.world.assumed('timer unset')
            return False
        return c[1] and c[0] < 1

    # ------------------------------------------------------------------------------------------ actions
    def action(self, name, a, s=None):
        """Do one action of the script `s` (UNIT_EXECUTE_SEQUENTIAL_SCRIPT's steps come in here too)."""
        if s is not None:
            self.script = s
        if name not in OWN_ACTIONS:
            self.world.action(self, name, a)
            return
        self.world.core(self, name, a, self.script)
        if name == 'SET_MILLISECOND_TIMER':         # (timer, seconds): from the top
            self.counter(a[0])[:] = [self.frames(a[1]), True]
        elif name == 'SET_RANDOM_MSEC_TIMER':       # (timer, lo, hi) at random: the latest, as the beat sheet counts
            self.counter(a[0])[:] = [self.frames(a[2]), True]
        elif name == 'SET_TIMER':                   # (timer, frames)
            self.counter(a[0])[:] = [int(a[1]), True]
        elif name == 'SET_RANDOM_TIMER':            # (timer, lo, hi) frames: the latest
            self.counter(a[0])[:] = [int(a[2]), True]
        elif name == 'STOP_TIMER':                  # frames left kept; no longer expired (bench engine_timer)
            self.counter(a[0])[1] = False
        elif name == 'RESTART_TIMER':               # runs on only with frames left
            c = self.counter(a[0])
            if c[0] > 0:
                c[1] = True
        elif name in ('SUB_FROM_MSEC_TIMER', 'ADD_TO_MSEC_TIMER'):     # (seconds, timer)
            d = self.frames(a[0])
            self.counter(a[1])[0] += d if name == 'ADD_TO_MSEC_TIMER' else -d
        elif name in ('ENABLE_SCRIPT', 'DISABLE_SCRIPT'):
            for x in (self._groups.get(a[0]), self._scripts.get(a[0])):
                if x is not None:
                    x.active = name == 'ENABLE_SCRIPT'
        elif name == 'CALL_SUBROUTINE':
            g, sc = self._groups.get(a[0]), self._scripts.get(a[0])
            caller = self.script
            if g is not None:
                if g.subroutine and g.active:
                    for x in g.items:
                        if isinstance(x, script_lists.Script):
                            self.execute(x)
            elif sc is not None and sc.subroutine:
                self.execute(sc)
            self.script = caller
