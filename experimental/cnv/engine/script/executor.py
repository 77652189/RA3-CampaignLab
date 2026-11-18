"""The public script executor (ADR 0033 item 2: the real implementation; the private model's script core is an
optional plug-in to the same port, engine/ports/scripts.py). It asks the world every condition (World.condition) and
every action (World.action) but the timers', which it does itself on its own table and tells the world of
(World.core), as the plug-in does.

What it runs: once a frame, each script of the map in file order -- not done (a once script that fired), not disabled,
on at the run's difficulty -- whose conditions all hold has its actions done in order; a condition ending in the NOT
mark is negated (World.assumed('inverted')). It keeps no frame of its own: it runs on the world's clock (Executor).

The counters and the timers are one table (docs/engine/script-semantics.md 3): a name's `[value, is_countdown_timer]`,
made at 0 the first time it is used; a running timer's value is the frames it has left, taken down by one at the start
of each frame, before the scripts, until it is -1; TIMER_EXPIRED is a running timer at 0 or below (bench
engine_script frames, engine_timer). The counter actions are still the world's (simact_world), on the same table
through simexec.Counters. No groups, no subroutines, no per-side lists yet: script-semantics.md is what it is to grow
into (step Z)."""
import math

from engine.ports import scripts as port

# the timer actions and the condition the executor does itself (script-semantics.md 3); the world hears of each
# action through World.core
TIMER_ACTIONS = frozenset({'SET_MILLISECOND_TIMER', 'SET_RANDOM_MSEC_TIMER', 'SET_TIMER', 'SET_RANDOM_TIMER',
                           'STOP_TIMER', 'RESTART_TIMER', 'SUB_FROM_MSEC_TIMER', 'ADD_TO_MSEC_TIMER'})


class PublicExecutor(port.Executor):
    """`scripts`: the map's scripts (each with name, levels, when, do, once); `level`: the run's difficulty index into
    a script's levels; `done` / `disabled`: the run's sets of script names (the world's, shared: actions change them);
    `not_mark`: the last item of a negated condition; `fps`: logic frames a second (a timer's seconds as frames);
    `clock`: an object whose `frame` it moves on before each frame's scripts (the model's engine as the world's clock,
    simexec.attach's executor 'public'), None: the world's clock."""

    def __init__(self, world, scripts, level, done, disabled, not_mark, fps, clock=None):
        self.world, self.scripts, self.level = world, scripts, level
        self.done, self.disabled, self.not_mark = done, disabled, not_mark
        self.fps, self.script, self.clock = fps, None, clock
        self.counters = {}              # name -> [value, is_countdown_timer]: the counters and timers, one table

    def counter(self, name):
        """The table's entry for `name`, made (a plain counter at 0) the first time it is used."""
        return self.counters.setdefault(name, [0, False])

    def frames(self, secs):
        """A timer's seconds as frames: ceil(seconds x frame rate) (script-semantics.md 3)."""
        return int(math.ceil(round(float(secs) * self.fps, 6)))

    def step(self):
        if self.clock is not None:
            self.clock.frame += 1
        for c in self.counters.values():
            if c[1] and c[0] >= 0:
                c[0] -= 1
        for sc in self.scripts:
            if sc.name in self.done or sc.name in self.disabled or not sc.levels[self.level]:
                continue
            if all(self.holds(c) for c in sc.when):
                for name, *a in sc.do:
                    self.script = sc
                    self.action(name, a)
                if sc.once:
                    self.done.add(sc.name)

    def holds(self, c):
        c = list(c)
        neg = c and c[-1] == self.not_mark
        if neg:
            c = c[:-1]
            self.world.assumed('inverted')
        if c[0] == 'TIMER_EXPIRED':
            v = self.timer_expired(c[1])
        else:
            v = self.world.condition(self, c[0], c[1:])
        return (not v) if neg else v

    def timer_expired(self, name):
        c = self.counters.get(name)
        if c is None:
            self.world.assumed('timer unset')
            return False
        return c[1] and c[0] < 1

    def action(self, name, a):
        if name not in TIMER_ACTIONS:
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
        else:                                       # SUB_FROM / ADD_TO_MSEC_TIMER (seconds, timer)
            d = self.frames(a[0])
            self.counter(a[1])[0] += d if name == 'ADD_TO_MSEC_TIMER' else -d
