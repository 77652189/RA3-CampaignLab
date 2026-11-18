"""The public script executor (ADR 0033 item 2: the real implementation; the private model's script core is an
optional plug-in to the same port, engine/ports/scripts.py). It asks the world everything through the port's
`World`: each condition (World.condition) and each action (World.action), so the core actions too (flags,
counters, timers: the world's own in a run without the plug-in).

What it runs today is the simulator's older loop, as the frame loop ran it before the port (step P1, a pure move):
once a frame, each script of the map in file order -- not done (a once script that fired), not disabled, on at the
run's difficulty -- whose conditions all hold has its actions done in order; a condition ending in the NOT mark is
negated (World.assumed('inverted')). It keeps no frame of its own: it runs on the world's clock (Executor). Timers
in seconds, no groups, no subroutines, no per-side lists: docs/engine/script-semantics.md is what it is to grow
into (step Z)."""
from engine.ports import scripts as port


class PublicExecutor(port.Executor):
    """`scripts`: the map's scripts (each with name, levels, when, do, once); `level`: the run's difficulty index into
    a script's levels; `done` / `disabled`: the run's sets of script names (the world's, shared: actions change them);
    `not_mark`: the last item of a negated condition; `clock`: an object whose `frame` it moves on before each frame's
    scripts (the model's engine as the world's clock, simexec.attach's executor 'public'), None: the world's clock."""

    def __init__(self, world, scripts, level, done, disabled, not_mark, clock=None):
        self.world, self.scripts, self.level = world, scripts, level
        self.done, self.disabled, self.not_mark = done, disabled, not_mark
        self.script, self.clock = None, clock

    def step(self):
        if self.clock is not None:
            self.clock.frame += 1
        for sc in self.scripts:
            if sc.name in self.done or sc.name in self.disabled or not sc.levels[self.level]:
                continue
            if all(self.holds(c) for c in sc.when):
                for name, *a in sc.do:
                    self.script = sc
                    self.world.action(self, name, a)
                if sc.once:
                    self.done.add(sc.name)

    def holds(self, c):
        c = list(c)
        neg = c and c[-1] == self.not_mark
        if neg:
            c = c[:-1]
            self.world.assumed('inverted')
        v = self.world.condition(self, c[0], c[1:])
        return (not v) if neg else v
