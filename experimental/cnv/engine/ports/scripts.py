"""The script executor port (docs/engine/sim-modules.md 6, ADR 0033 item 2): one interface between the world and
whatever runs the map's scripts, in both directions.

`World` is what an executor asks of the world: a condition's value, an action done, the frame's start and end, a
side's difficulty. `Executor` is what the world asks of an executor: `step()`, one logic frame of scripts. The public
executor (engine/script/executor.py) is the real implementation; the private model's script core is an optional
plug-in to the same two interfaces (its `World` has these five names and arguments), so the two can be run side by
side and compared (simrecord.py `--executor`, `cross`).

The script semantics are docs/engine/script-semantics.md. This file is the interface only: no rule lives here."""


class World:
    """What an executor asks of the world. This base answers nothing (every condition None, every action ignored)."""

    def condition(self, eng, name, args):
        """The value of the condition `name` with `args` (a list), asked by the executor `eng` for a script it runs."""
        return None

    def action(self, eng, name, args):
        """Do the action `name` with `args` (a list) for the executor `eng`; `eng.script` is the script it is in
        (None when the executor has none to give)."""

    def begin(self, eng):
        """The frame has begun (its number already advanced where `eng` keeps one), before its timers and scripts."""

    def update(self, eng):
        """The frame's scripts have run."""

    def difficulty(self, side):
        """The difficulty a side's scripts run at; None: the run's own."""
        return None

    def core(self, eng, name, args, script):
        """`eng` is about to do the core action `name` itself (a flag, an objective, a counter, a timer): the world
        notes what it watches of it. An executor that hands every action to `action` never calls this."""

    def assumed(self, what):
        """The executor leaned on an assumption the run's report lists (`what`, its audit key)."""


class Executor:
    """What the world asks of an executor. An executor that keeps the frame number (`frame`) owns the frame clock and
    moves it on in `step`; one without it runs on the world's clock."""
    script = None                       # the script whose action is being done (World.action reads it)

    def step(self):
        """One logic frame of scripts."""
        raise NotImplementedError

    def snapshot(self):
        """The executor's state between two frames (step S, docs/engine/sim-modules.md 9.2) as a JSON-shaped dict:
        its counters and timers, its clocks, its random draws, which scripts are on. The map's script lists are not
        in it (the executor made for the same mission has them). An executor that cannot says so: the snapshot is
        refused, never taken without it."""
        raise NotImplementedError(f'{type(self).__name__}: this script executor does not take snapshots')

    def restore(self, snap):
        """Write a snapshot of this executor back, onto one made anew for the same mission's lists."""
        raise NotImplementedError(f'{type(self).__name__}: this script executor does not take snapshots')


def this_player(eng, args):
    """'<This Player>' as the game reads it: the player whose script list the script is in (the executor's `_side`;
    retail maps' lists are per player, ours have one unnamed list and never use it)."""
    side = getattr(eng, '_side', '')
    return [side if a == '<This Player>' and side else a for a in args]
