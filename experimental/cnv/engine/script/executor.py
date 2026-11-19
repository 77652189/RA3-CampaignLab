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
through simexec.Counters, but SET_RANDOM_COUNTER (the executor's seeded draws); COUNTER_COUNTER / COUNTER_SECONDS
read the table itself (a running timer's frames left), as TIMER_EXPIRED. ENABLE_SCRIPT / DISABLE_SCRIPT switch a group and a script of that name both (the first
of a name: Generals findScript / findGroup); a once script that fired is armed again (script-semantics.md 8 item 10).
CALL_SUBROUTINE runs a subroutine group's scripts (the group active) or a subroutine script (Generals
callSubroutine; not measured in RA3: INFERRED)."""
import math
import operator
import random

from engine.kernel import snap
from engine.ports import scripts as port
from engine.script import lists as script_lists

# the timer actions the executor does itself (script-semantics.md 3) ...
TIMER_ACTIONS = frozenset({'SET_MILLISECOND_TIMER', 'SET_RANDOM_MSEC_TIMER', 'SET_TIMER', 'SET_RANDOM_TIMER',
                           'STOP_TIMER', 'RESTART_TIMER', 'SUB_FROM_MSEC_TIMER', 'ADD_TO_MSEC_TIMER'})
# ... and the script switches and calls (script-semantics.md 1, 5); the world hears of each through World.core
SCRIPT_ACTIONS = frozenset({'ENABLE_SCRIPT', 'DISABLE_SCRIPT', 'CALL_SUBROUTINE', 'NO_OP'})
# ... and the shown counters (counter, label): the label's counter kept (`displayed`) and a 'show' row logged, as
# the plug-in does; the screen's readers (simshow, simui) read them off whichever executor runs
SHOW_ACTIONS = frozenset({'DISPLAY_COUNTER', 'DISPLAY_COUNTDOWN_TIMER'})
# ... and the one counter action that draws at random (its own seeded draws, as the plug-in's)
RANDOM_ACTIONS = frozenset({'SET_RANDOM_COUNTER'})
OWN_ACTIONS = TIMER_ACTIONS | SCRIPT_ACTIONS | SHOW_ACTIONS | RANDOM_ACTIONS
# the comparisons' codes (the world's simscript.CMP): <, <=, ==, >=, >, !=
CMP = (operator.lt, operator.le, operator.eq, operator.ge, operator.gt, operator.ne)


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
        self.displayed = {}             # label -> counter name (DISPLAY_COUNTER / DISPLAY_COUNTDOWN_TIMER)
        self.log = []                   # (frame, 'show', script name, action, args): the plug-in's log's shape
        self._side = ''
        self._scripts, self._groups = {}, {}
        self._again = {}                # name -> the later scripts of a name _scripts already holds (place order)
        for lst in lists:
            self._index(lst.items)
        rng = random.Random(seed)       # Generals: a script with a delay first runs 0..2 s into the game
        # a delayed script's next frame by its _key, never id(): a snapshot names its scripts
        self._next = {s.name: rng.randint(0, 2 * fps) if s.interval > 0 else 0 for s in self._scripts.values()}
        self.rng = rng                  # then SET_RANDOM_COUNTER's draws

    def _index(self, items):
        for it in items:
            if isinstance(it, script_lists.Group):
                self._groups.setdefault(it.name, it)
                self._index(it.items)
            elif self._scripts.setdefault(it.name, it) is not it:
                self._again.setdefault(it.name, []).append(it)

    def _key(self, s):
        """A script's key in _next: its name; a later script of a name already taken, (name, its place among them)."""
        if self._scripts.get(s.name) is s:
            return s.name
        return s.name, next(i for i, x in enumerate(self._again[s.name]) if x is s)

    def _walk(self, items=None):
        """Every script and group of the lists, in the order the lists hold them (a group, then its items)."""
        for it in (x for lst in self.lists for x in lst.items) if items is None else items:
            yield it
            if isinstance(it, script_lists.Group):
                yield from self._walk(it.items)

    def _by_key(self, key):
        if isinstance(key, str):
            return self._scripts[key]
        return self._again[key[0]][key[1]]

    def script_key(self, s):
        """The port's: a script by a key a snapshot keeps (its _key: the name; a later script of a taken name,
        (name, its place among them)); script_by_key finds it again on an executor made for the same lists."""
        return self._key(s)

    def script_by_key(self, key):
        return self._by_key(key)

    def snapshot(self):
        """The port's Executor.snapshot: counters, steps, displayed, log, the delayed scripts' next frames, the
        random draws, the script now acting (by its _key) and the side, each script's and group's `active` and
        `subroutine` in list order (a sequential script turns subroutine in the run: simact_world). A `clock` the
        executor moves on is the world's (its holder takes it)."""
        return {'counters': snap.encode(self.counters, at='counters'), 'steps': self.steps,
                'displayed': snap.encode(self.displayed, at='displayed'), 'log': snap.encode(self.log, at='log'),
                'next': snap.encode(self._next, at='next'), 'rng': snap.encode(self.rng.getstate(), at='rng'),
                'script': None if self.script is None else snap.encode(self._key(self.script)),
                'side': self._side,
                'active': [[type(x).__name__, x.name, x.active, x.subroutine] for x in self._walk()]}

    def restore(self, s):
        active = list(self._walk())
        if [[type(x).__name__, x.name] for x in active] != [row[:2] for row in s['active']]:
            raise ValueError('PublicExecutor.restore: the snapshot is of other script lists')
        things = {}
        for table, key in ((self.counters, 'counters'), (self.displayed, 'displayed'), (self._next, 'next')):
            table.clear()               # in place: a reader may hold the table under another name
            table.update(snap.decode(s[key], things))
        self.log[:] = snap.decode(s['log'], things)
        self.steps = s['steps']
        self.rng.setstate(snap.decode(s['rng'], things))
        self.script = None if s['script'] is None else self._by_key(snap.decode(s['script'], things))
        self._side = s['side']
        for x, row in zip(active, s['active']):
            x.active, x.subroutine = row[2], row[3]

    def script_named(self, name):
        """The script of that name (the first of it), None where none (UNIT_EXECUTE_SEQUENTIAL_SCRIPT)."""
        return self._scripts.get(name)

    def counter(self, name):
        """The table's entry for `name`, made (a plain counter at 0) the first time it is used."""
        return self.counters.setdefault(name, [0, False])

    def readings(self):
        """What the bench's counter lines show: label -> the shown counter's value (a running timer's frames left)."""
        return {k: self.counters.get(n, [0, False])[0] for k, n in self.displayed.items()}

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
            key = self._key(s)
            if self.steps < self._next.get(key, 0):
                return
            self._next[key] = self.steps + s.interval * self.fps
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
        elif c.name == 'COUNTER_COUNTER':           # (counter, comparison, counter): the table's values, a running
            v = CMP[int(c.args[1])](self.value(c.args[0]), self.value(c.args[2]))     # timer's its frames left
        elif c.name == 'COUNTER_SECONDS':           # (timer, comparison, seconds): its frames left in seconds (bench
            v = CMP[int(c.args[1])](self.value(c.args[0]) / self.fps, float(c.args[2])) # engine_scripts6 timers)
        else:
            v = self.world.condition(self, c.name, list(c.args))
        return (not v) if c.inverted else v

    def value(self, name):
        """A name's value in the table (a running timer's frames left), 0 where never used."""
        return self.counters.get(name, [0, False])[0]

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
        elif name == 'SET_RANDOM_COUNTER':          # (counter, lo, hi), both ends in (bench engine_scripts6: 1..3
            self.counter(a[0])[0] = self.rng.randint(int(a[1]), int(a[2]))     # gives 1, 2 and 3, never 0 or 4)
        elif name in ('ENABLE_SCRIPT', 'DISABLE_SCRIPT'):
            for x in (self._groups.get(a[0]), self._scripts.get(a[0])):
                if x is not None:
                    x.active = name == 'ENABLE_SCRIPT'
        elif name in SHOW_ACTIONS:
            self.displayed[str(a[1])] = str(a[0])
            frame = self.clock.frame if self.clock is not None else self.steps      # the frame now
            self.log.append((frame, 'show', s.name if s else '', name, a))
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
