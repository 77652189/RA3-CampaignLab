"""The command port (module_plan P "命令端口"; R3 13, draft and census in the private notes): how whoever gives orders --
the player-style runs, the UI, the plays, the script actions, the AI and the proxy -- tells a world's units what to
do, so that when the order family (AIUpdate) moves into kernel modules only this file's routes change.

A command is data: `Command(kind, by, ...)`, names and numbers only (an object, a template, a place by its name; no
object, no function), so it can be logged, compared, queued and saved with a snapshot as it is.

Two routes, as in the game (a player's click is a message carried into the logic frame; the AI and the scripts call
a unit's AI command interface there and then):
- `post(cmd, at)`: queued, run at `at` (mission seconds, or `('@', flag, secs)`: that long after the flag first reads
  1) by the frame loop's events cell -- today's `Sim.events` / `anchored`, so a queued command runs exactly when the
  script line it reads as would (`text(cmd)`: its line; `event(cmd, at)`: the event parse_script makes of it);
- `do(cmd)`: now (the AI command interface route).
`post_line(line)` queues a whole script line as it is (a play replayed by a test player may hold the god's-hand
verbs too -- 造, 删除, 血量 ...: those are not commands and go in as the script events they are, unlogged).

The port holds no rules: `do` routes each kind to the world's own order call (`Sim.happen` gives a script line's
order through `do` too: one port per run, `Sim.commands`). Kinds with no route yet (`check` says so) get theirs when their giver moves to the port (R3 13d-13f).
`issued()` is the record of what was posted and done -- written, never read in a run (nothing in a game decides by
it; so a snapshot does not hold it: R2 13a)."""
import dataclasses
import sys

# The commands a player or the AI can give in the game (the port's whole vocabulary; module_plan §2 order family and
# the modules they go to). The line verbs below are the ones a script line, so `post`, carries today.
KINDS = frozenset({
    'move', 'attack_move', 'attack', 'attack_ground', 'stop', 'idle', 'guard', 'follow_path', 'capture', 'enter',
    'exit', 'power', 'toggle', 'stance', 'build', 'place', 'unpack', 'sell', 'buy_science', 'hunt', 'flee',
    'auto_acquire'})
VERB = {'attack_move': '派', 'move': '走', 'attack': '攻击', 'power': '放', 'capture': '占领', 'build': '生产',
        'buy_science': '买'}
KIND = {v: k for k, v in VERB.items()}
ROUTED = frozenset(VERB)            # the kinds `do` has a route for (the rest: R3 13d-13f, with their givers)
GIVERS = ('player', 'ai', 'script', 'proxy', 'test')     # `by`: 'player', 'ai:<player>', ...
DATA = (str, int, float, bool, type(None))


class RunSwitch(ValueError):
    """A script line that is a run switch (自动打掉 / 不打 / 高地不挡): it sets a run up, it is not queued."""


def _data(v):
    return isinstance(v, DATA) or (isinstance(v, tuple) and all(_data(x) for x in v))


@dataclasses.dataclass(frozen=True)
class Command:
    """One order. `units` / `target` are names a script line can carry (an object's name, a role, `名字含 ...`, ...);
    `place` a place's name or `@x,y`, `pos` a point; `args` the rest as (name, value) pairs."""
    kind: str
    by: str = 'player'
    player: str = ''                # in whose name (build / place / buy_science; a unit command goes as its owner's)
    units: tuple = ()
    pos: tuple | None = None
    place: str = ''
    target: str = ''
    template: str = ''
    power: str = ''
    attacking: bool = False         # a path followed fighting (follow_path); move / attack_move are two kinds
    force: bool = False             # attack whatever the relation
    args: tuple = ()

    def __post_init__(self):
        for f in dataclasses.fields(self):
            v = getattr(self, f.name)
            if not _data(v):
                raise TypeError(f'Command.{f.name}: names and numbers only, not {type(v).__name__}')
        if self.by.split(':')[0] not in GIVERS:
            raise ValueError(f'Command.by {self.by!r}: one of {GIVERS} (ai:<player>)')
        if any(not (isinstance(a, tuple) and len(a) == 2 and isinstance(a[0], str)) for a in self.args):
            raise ValueError('Command.args: (name, value) pairs')

    def arg(self, name, default=None):
        return next((v for k, v in self.args if k == name), default)


def text(cmd):
    """The script line's text of a command (no time): what a run records and a replay reads back."""
    if cmd.kind not in VERB:
        raise ValueError(f'{cmd.kind}: no script line carries it')
    if cmd.kind == 'buy_science':
        return f"买 {cmd.arg('science')}"
    if cmd.kind == 'build':
        return f'生产 {cmd.template} 在 {cmd.target}'
    if len(cmd.units) != 1:
        raise ValueError(f'{cmd.kind}: a script line names one address (it may name several units)')
    who = cmd.units[0]
    return {'attack_move': f'派 {who} 去 {cmd.place}', 'move': f'走 {who} 去 {cmd.place}',
            'attack': f'攻击 {who} 打 {cmd.target}', 'power': f'放 {who} {cmd.power} 在 {cmd.place}',
            'capture': f'占领 {who} 进 {cmd.target}'}[cmd.kind]


def event(cmd, at):
    """The script event (at, verb, ...) parse_script makes of `at text(cmd)`."""
    text(cmd)                       # the same checks
    verb = VERB[cmd.kind]
    if cmd.kind == 'buy_science':
        return (at, verb, cmd.arg('science'))
    if cmd.kind == 'build':
        return (at, verb, cmd.template, cmd.target)
    who = cmd.units[0]
    tail = {'attack_move': (cmd.place,), 'move': (cmd.place,), 'attack': (cmd.target,),
            'power': (cmd.power, cmd.place), 'capture': (cmd.target,)}[cmd.kind]
    return (at, verb, who) + tail


def command(e, by='script'):
    """The command a script event gives, or None (a god's-hand verb: 造 血量 旗标 摧毁 删除 打, one-name 占领)."""
    _, verb, *rest = e
    kind = KIND.get(verb)
    if kind is None or (verb == '占领' and len(rest) != 2):
        return None
    if kind == 'buy_science':
        return Command(kind, by, args=(('science', rest[0]),))
    if kind == 'build':
        return Command(kind, by, template=rest[0], target=rest[1])
    if kind in ('attack_move', 'move'):
        return Command(kind, by, units=(rest[0],), place=rest[1])
    if kind == 'power':
        return Command(kind, by, units=(rest[0],), power=rest[1], place=rest[2])
    return Command(kind, by, units=(rest[0],), target=rest[1])


class Commands:
    """The command port of one world (today a sim.Sim)."""

    def __init__(self, world):
        self._w = world
        self._issued = []

    @staticmethod
    def kinds():
        return KINDS

    def check(self, cmd):
        """(ok, why) before the world is asked: a kind the port knows and has a route for. (The refusals that need the
        world -- dead, not mine, no factory, money, cooldown -- are still the order calls' own: `do` returns them.)"""
        if cmd.kind not in KINDS:
            return False, f'unknown command {cmd.kind!r}'
        if cmd.kind not in ROUTED:
            return False, f'{cmd.kind}: no route yet (its giver moves to the port later)'
        return True, ''

    def post(self, cmd, at):
        """Queue it for `at` (seconds, or ('@', flag, secs)): run by the events cell as its script line would be."""
        ok, why = self.check(cmd)
        if ok:
            self._queue(event(cmd, at))
        self._issued.append((self._w.frame_now(), cmd, ok, why or 'posted'))
        return ok, why

    def post_line(self, line):
        """Queue a script line as it is (`<time> <verb> ...`; a time may be `<flag>+<secs>`): the events queued. A line
        that does not read raises parse_script's ValueError; a run switch RunSwitch (it is given at the start only)."""
        out = []
        for e in sys.modules[type(self._w).__module__].parse_script(line):
            if e[0] is None:
                raise RunSwitch(f'{line!r}: a run switch, not a line to queue')
            self._queue(e)
            out.append(e)
            cmd = command(e, 'player')
            if cmd is not None:
                self._issued.append((self._w.frame_now(), cmd, True, 'posted'))
        return tuple(out)

    def drop_pending(self):
        """Drop every queued command still to come (a play script handing the run over to the player)."""
        self._w.events.clear()
        self._w.anchored.clear()

    def _queue(self, e):
        w = self._w
        if isinstance(e[0], tuple):
            w.anchored.append(e)
        else:
            w.events.append(e)
            w.events.sort(key=lambda x: x[0])

    def do(self, cmd):
        """Now: the kind's order call (a script line's order, run by `Sim.happen`, comes here). (ok, why)."""
        ok, why = self.check(cmd)
        if ok:
            ok, why = getattr(self, '_' + cmd.kind)(cmd)
        self._issued.append((self._w.frame_now(), cmd, ok, why or 'done'))
        return ok, why

    def issued(self):
        """(frame, Command, ok, why) for every command posted or done, in order. A record: nothing in a run reads it."""
        return tuple(self._issued)

    def pending(self):
        """The queued script events not run yet, in the order they will run (the timed ones by time, then the ones
        waiting on a flag): what a snapshot holds of the queue."""
        return tuple(self._w.events) + tuple(self._w.anchored)

    # --- the routes (the script verbs' order calls; Sim.happen runs its order verbs through `do` since R3 13c-2)
    def _units(self, cmd):
        return [b for who in cmd.units for b in self._w.pick(who)]

    def _attack_move(self, cmd):
        for b in self._units(cmd):          # each unit's own attack-move (ATTACK_MOVE_NAMED_UNIT_TO)
            self._w.order_move(b, cmd.place, True, on_grid=True)
        return True, ''

    def _move(self, cmd):                    # several at once: a group move (MOVE_NAMED_UNIT_TO)
        self._w.order_group(self._units(cmd), cmd.place, False, on_grid=True)
        return True, ''

    def _attack(self, cmd):
        w = self._w
        targets = w.pick(cmd.target)
        if not targets:
            return False, f'找不到 {cmd.target}'
        for b in self._units(cmd):
            w.order_attack(b, targets[0].name, cmd.force)
        return True, ''

    def _power(self, cmd):
        w = self._w
        p = w.point(cmd.place)
        for b in self._units(cmd):
            u = next((u for u in w.mm.units if u.id == b.template), None)
            if p is None:
                w.note('剧本', f'找不到地点 {cmd.place}')
            else:
                w.order_power(b, (u.abilities.get(cmd.power) if u else None) or cmd.power, p)
        return (False, f'找不到地点 {cmd.place}') if p is None else (True, '')

    def _capture(self, cmd):
        w = self._w
        targets = w.pick(cmd.target)
        if not targets:
            return False, f'找不到 {cmd.target}'
        for b in self._units(cmd):
            w.order_capture(b, targets[0].name)
        return True, ''

    def _build(self, cmd):
        w = self._w
        tmpl = next((u.id for u in w.mm.units if u.id == cmd.template), None) or \
            next((r.template for k, r in w.m.cast.items() if k == cmd.template), cmd.template)
        f = next(iter(w.pick(cmd.target)), None)
        if f is None:
            why = f'找不到工厂 {cmd.target}'
        elif not w.order_build(cmd.player or w.human, tmpl, factory=f):
            why = f'{w.label(f)} 现在造不了 {tmpl}（不是玩家的、不造它、科技或禁造）'
        else:
            return True, ''
        w.note('剧本', why)
        return False, why

    def _buy_science(self, cmd):
        w, science = self._w, cmd.arg('science')
        player = cmd.player or w.human
        book = w.books.get(player)
        if book and book.buy(science, w.frame_now()):
            w.note('协议', f'玩家买了 {science}（剩 {book.points} 点）')
            w.change()
            return True, ''
        why = f'买不了 {science}' + (f'（{book.points} 点）' if book else '（玩家没有协议）')
        w.note('剧本', why)
        return False, why
