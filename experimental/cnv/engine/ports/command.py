"""The command port (module_plan P "命令端口"; R3 13, draft and census in the private notes): how whoever gives orders --
the player-style runs, the UI, the plays, the script actions, the AI and the proxy -- tells a world's units what to
do, so that when the order family (AIUpdate) moves into kernel modules only this file's routes change.

A command is data: `Command(kind, by, ...)`, names and numbers only (an object, a template, a place by its name; no
object, no function), so it can be logged, compared, queued and saved with a snapshot as it is.

Two routes, as in the game (a player's click is a message carried into the logic frame; the AI and the scripts call
a unit's AI command interface there and then):
- `post(cmd, at)`: queued, run at `at` (mission seconds, or `('@', flag, secs)`: that long after the flag first reads
  1) by the frame loop's events cell -- today's `Sim.events` / `anchored`, so a queued command runs exactly when the
  script line it reads as would (`text(cmd)`: its line). What is queued is the command itself (`queued(cmd, at)`:
  `(at, ORDER, cmd)`, its fields as given -- never its line written and read back, so a name that appears later cannot
  turn it into another: review 11-19 i #1); `Sim.happen` gives it through `do` and notes it as its line's event
  (`event(cmd, at)`). A command no line could carry (a `pos`, an `args` entry, a `player` or `force` on a kind whose
  line has none) is refused, as before (the queue holds the commands the script verbs give). A name a line cannot hold
  (an unnamed object's `#0`: '#' starts a comment) still reaches its unit (simui replays events). A giver that records
  its run as lines and replays them (autoplay) posts those lines (`post_line`), so its run gives what its replay will
  even where a name splits another way (`a` told to use `x y` reads as `a x` told to use `y`: review 11-19 d #4);
- `do(cmd)`: now (the AI command interface route).
`post_line(line)` queues a whole script line as it is (a play replayed by a test player may hold the god's-hand
verbs too -- 造, 删除, 血量 ...: those are not commands and go in as the script events they are, unlogged).

The port holds no rules: `do` routes each kind to the world's own order call (`Sim.happen` gives a script line's
order through `do` too: one port per run, `Sim.commands`). Kinds with no route yet (`check` says so) get theirs when
their giver moves to the port. The skirmish AI (simai, simpullback; R3 13f-1) gives its members' orders through `do`
by serial: a member re-sent drops its target first (`drop_target` on each unit's move too), a form-up slot's `face`,
a pursuit's threat taken as the unit's goal alone (`attack` with `goal_only`), a SimpleExpansion miner armed to unpack
at `pos` (`stand` / `here` / `send`), `enter` a garrison, `place` a structure. The proxy player (simproxy, R3 13e) gives the player's own clicks
through `do`: a selection's move (`('drop_target', True)`: the click drops the units' attack target first), a sidebar
build (no `target`: the owner's factory with the shortest queue), a ground power or a transform answering the world's
refusals (`via` 'click' / 'transform').

Two kinds of address. A script line's (the player's, the plays'): `units` / `target` are what `Sim.pick` reads (a
role, `名字含 ...`, `队 ...`; one not there is noted). A map script's (`('objects', True)`, the script actions since
R3 13d): `units` are objects' names as the script action found them (`Sim.body`: a reference reads as what it points
at), each given its order even when not there -- the order call takes a missing one as it always did -- and `target`
goes to the order call as it is (it looks the name up itself); `('objects', 'serial')`: `units` are the serials of the
objects the action picked itself (a team's members: found as picked, a reference of the same name cannot take one's
place -- review 11-19 f #1). A line verb's command may pin what its names picked: `('unit_serials', (n, ...))` the
serials of the objects `units` names (one each, as picked) and `('target_serial', n)` the target's -- the route is the
line's own, the names stay for the record (its noted line), and a name a role or another object also answers to
cannot take the order (the page's click, review 1119z P2 #1; `Commands.line` writes no such command); a pin of an
object by another name, or with none of its objects left, is refused (`do`, review 1120bb P2 #1). A serial stands for
a living object, the giver's own where the giver has units (the player's, the proxy's, an AI's) and of the name it
was given with: a dead one (its body stays in the table), one given to another player since, is not ordered; a
target pin of another name or dead refuses the command (review 1120cc P2). A route that cannot go on without its object (a factory, the unit to unpack) refuses a
missing one; a press the world turns down (a target gone, out of range) is refused (review 11-19 f #4 #5).

A line's tails `强制` / `由 P` (in a line a player or a play wrote, or `text` wrote for a command that has them) read as
part of the name when the whole, exactly as written, is a name in the world (`Commands.command`: a role or an object
called `enemy 强制`, or `enemy  强制` with its two spaces: review 11-19 g #2, i #4) -- sim.parse_script keeps the word
group whole and `split` decides -- so a line reads as its own name; a command whose line would read as another here (a
forced attack on `enemy` beside an `enemy 强制`) is not written (`Commands.line`; autoplay checks its lines with it). A
posted command has no line to read: it is queued as itself.
`issued()` is the record of what was posted and done -- written, never read in a run (nothing in a game decides by
it; so a snapshot does not hold it: R2 13a)."""
import dataclasses
import math
import sys
import types

# The commands a player or the AI can give in the game (the port's whole vocabulary; module_plan §2 order family and
# the modules they go to). The line verbs below are the ones a script line, so `post`, carries today.
KINDS = frozenset({
    'move', 'attack_move', 'attack', 'attack_ground', 'stop', 'idle', 'guard', 'follow_path', 'capture', 'enter',
    'exit', 'power', 'toggle', 'stance', 'build', 'place', 'unpack', 'sell', 'buy_science', 'hunt', 'flee',
    'auto_acquire', 'face', 'set_lifetime', 'fill_body'})
VERB = {'attack_move': '派', 'move': '走', 'attack': '攻击', 'power': '放', 'capture': '占领', 'build': '生产',
        'buy_science': '买'}
KIND = {v: k for k, v in VERB.items()}
# the kinds `do` has a route for (the rest: R3 13e-13f, with their givers): the line verbs', and the script actions'
# (13d-1 the orders; 13d-2 the buttons: unpack, toggle); face (Generals' AI command list has AICMD_FACE_POSITION;
# INFERRED for RA3) joined with them.
# The skirmish AI's (13f-1): enter (a garrison / its own base defense), place (a structure set down: INFERRED, below).
ROUTED = frozenset(VERB) | {'guard', 'stop', 'idle', 'follow_path', 'attack_ground', 'face', 'hunt', 'flee', 'stance',
                            'auto_acquire', 'unpack', 'toggle', 'enter', 'place', 'set_lifetime',
                            'fill_body'}
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


# What a line adds for the two fields only some lines carry: a forced attack (`攻击 X 打 Y 强制`: whatever the
# relation, the game's force-attack) and an explicit player for a build or a science (`生产 T 在 F 由 P`, `买 S 由 P`;
# without it, the human player). sim.parse_script reads them back (the event's last item).
FORCE = '强制'
BY_PLAYER = ' 由 '
# The verb of a queued command's event (`queued`): no script line has it (parse_script refuses `0 命令 ...`).
ORDER = '命令'
# The args a line verb's command may carry beside its line: what its names picked, by serial (its line, for the
# record, names them; the command goes by the serials). A line written for a replay to read cannot hold them.
PINS = ('unit_serials', 'target_serial')
POINTED = frozenset({'move', 'attack_move', 'face', 'attack_ground', 'unpack'})     # the routes `_pointed` checks
TARGETED = frozenset({'attack', 'capture', 'build', 'enter'})     # the routes that read `target` / `target_serial`


def takes_target(cmd):
    """Whether cmd's route reads a target: TARGETED's, and a script's power pressed at one (`via` 'wfire' with
    `objects`; without, it goes by place: review ff P3); the rest go to a place or nowhere, so a `target_serial`
    given them would be checked by `_pinned` and then never used."""
    return cmd.kind in TARGETED or (cmd.kind == 'power' and cmd.arg('via') == 'wfire' and bool(cmd.arg('objects')))


def by_player(s):
    """(the rest, player) of a line's tail `... 由 P`, or (s, '')."""
    head, mark, player = s.rpartition(BY_PLAYER)
    return (head.strip(), player.strip()) if mark and head.strip() else (s, '')


def split(verb, whole, named=None):
    """A line's last word group as parse_script keeps it whole (`攻击`'s target, `生产`'s factory, `买`'s science) ->
    (name, force) for 攻击, (name, player) for 生产 / 买. `named(s)`: s is a name in the world -- then the whole, exactly
    as written (its spaces too), is that name and no tail (review 11-19 g #2, i #4). A science is no object: 买 always
    splits."""
    if verb != '买' and named and named(whole):
        return whole, (False if verb == '攻击' else '')
    if verb == '攻击':
        head = whole[:-len(FORCE)]
        if whole.endswith(FORCE) and head[-1:].isspace() and head.strip():
            return head.strip(), True
        return whole, False
    return by_player(whole)


def text(cmd):
    """The script line's text of a command (no time): what a run records and a replay reads back. ValueError when no
    line carries the kind, or the command holds more than its line can say."""
    if cmd.kind not in VERB:
        raise ValueError(f'{cmd.kind}: no script line carries it')
    if cmd.player and cmd.kind not in ('build', 'buy_science'):
        raise ValueError(f"{cmd.kind}: its script line carries no player (a unit command goes as its owner's)")
    if cmd.force and cmd.kind != 'attack':
        raise ValueError(f'{cmd.kind}: its script line carries no force')
    if cmd.pos is not None or cmd.attacking:
        raise ValueError(f'{cmd.kind}: a script line carries a place by its name, and no path-follow fighting')
    extra = [k for k, _ in cmd.args if not (cmd.kind == 'buy_science' and k == 'science') and k not in PINS]
    if extra:
        raise ValueError(f'{cmd.kind}: its script line carries no {", ".join(extra)}')
    by = f'{BY_PLAYER}{cmd.player}' if cmd.player else ''
    if cmd.kind == 'buy_science':
        return f"买 {cmd.arg('science')}{by}"
    if cmd.kind == 'build':
        if not cmd.target:
            raise ValueError("build: its script line names the factory (a sidebar build is do's only)")
        return f'生产 {cmd.template} 在 {cmd.target}{by}'
    if len(cmd.units) != 1:
        raise ValueError(f'{cmd.kind}: a script line names one address (it may name several units)')
    who = cmd.units[0]
    return {'attack_move': f'派 {who} 去 {cmd.place}', 'move': f'走 {who} 去 {cmd.place}',
            'attack': f'攻击 {who} 打 {cmd.target}' + (f' {FORCE}' if cmd.force else ''),
            'power': f'放 {who} {cmd.power} 在 {cmd.place}',
            'capture': f'占领 {who} 进 {cmd.target}'}[cmd.kind]


def event(cmd, at):
    """The script event (at, verb, ...) parse_script makes of `at text(cmd)` (for names a line can hold): a tail stays
    in its word group, as the line has it (`enemy 强制`, `f 由 P`: `split` reads it)."""
    text(cmd)                       # the same checks
    verb, by = VERB[cmd.kind], f'{BY_PLAYER}{cmd.player}' if cmd.player else ''
    if cmd.kind == 'buy_science':
        return (at, verb, cmd.arg('science') + by)
    if cmd.kind == 'build':
        return (at, verb, cmd.template, cmd.target + by)
    who = cmd.units[0]
    tail = {'attack_move': (cmd.place,), 'move': (cmd.place,),
            'attack': (cmd.target + (f' {FORCE}' if cmd.force else ''),),
            'power': (cmd.power, cmd.place), 'capture': (cmd.target,)}[cmd.kind]
    return (at, verb, who) + tail


def queued(cmd, at):
    """The event `post` queues: the command itself, run at `at` (`Sim.happen` gives it through `do`)."""
    return (at, ORDER, cmd)


def command(e, by='script', named=None):
    """The command a script event gives, or None (a god's-hand verb: 造 血量 旗标 摧毁 删除 打, one-name 占领). A
    queued command's event (`queued`) gives the command as posted (its own `by`). `named(s)`: s is a name in the
    world -- then a word group's whole is that name, no tail read off it (`split`)."""
    _, verb, *rest = e
    if verb == ORDER:
        return rest[0]
    kind = KIND.get(verb)
    if kind is None or (verb == '占领' and len(rest) != 2):
        return None
    if kind == 'buy_science':
        science, player = split(verb, rest[0])
        return Command(kind, by, player=player, args=(('science', science),))
    if kind == 'build':
        factory, player = split(verb, rest[1], named)
        return Command(kind, by, player=player, template=rest[0], target=factory)
    if kind in ('attack_move', 'move'):
        return Command(kind, by, units=(rest[0],), place=rest[1])
    if kind == 'power':
        return Command(kind, by, units=(rest[0],), power=rest[1], place=rest[2])
    if kind == 'attack':
        target, force = split(verb, rest[1], named)
        return Command(kind, by, units=(rest[0],), target=target, force=force)
    return Command(kind, by, units=(rest[0],), target=rest[1])


def _where(cmd):
    """A move's goal: `pos`, else `place` (the player's and the AI's moves read `place` alone: a `pos` move was answered
    ok and nobody moved -- gameport step 3, one plug-in's move on the simulator)."""
    return cmd.place if cmd.pos is None else cmd.pos


class Commands:
    """The command port of one world (today a sim.Sim). `rules`: the unit orders' rule modules its routes call --
    order, ability, hunt, micro (engine.orders, L5), toggle (engine.objects.toggle) and body (the AI's lifetime, fill) --
    handed in by the world's maker (sim.ORDER_RULES) with `refresh_modifiers`, the world's re-read of a body's
    attribute modifiers (the micro's charge): this port imports none of them, so a giver of any layer may use it (ADR
    0037 S1, B3)."""

    def __init__(self, world, **rules):
        self._w = world
        self._r = types.SimpleNamespace(**rules, peers=rules['order'].Peers(world))
        self._issued = []
        self._libs = {}                     # player -> his AI's template library getter, which `fill_body` reads

    def library(self, player, get):
        """Wire `player`'s AI template library (`get()`, read when used) for `fill_body`: the Brain does when made (a
        snapshot keeps none; the Brain made again on restore wires it again)."""
        self._libs[player] = get

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

    def _read(self, line):
        return sys.modules[type(self._w).__module__].parse_script(line)

    def _named(self, who):
        """`who` is a role or an object's name here (what pick finds by name; no note)."""
        w = self._w
        return who in w.m.cast or who in w.bodies or any(k.startswith(who + ' ') and k[len(who) + 1:].isdigit()
                                                         for k in w.m.cast)

    def command(self, e, by='script'):
        """`command(e, by)` with this world's names: a line's tail is a name's own end when the whole is a name."""
        return command(e, by, self._named)

    def line(self, cmd):
        """text(cmd), checked to read back here as cmd (ValueError: no line carries it, or its line reads as another
        command in this world -- a tail taken for a name's end)."""
        s = text(cmd)
        pinned = [k for k, _ in cmd.args if k in PINS]
        if pinned:
            raise ValueError(f'{s!r}: the command picks by serial ({", ".join(pinned)}), its line by name')
        if self.command(event(cmd, 0), cmd.by) != cmd:
            raise ValueError(f'{s!r} reads as another command here (a name ends in its tail)')
        return s

    def post(self, cmd, at):
        """Queue it for `at` (seconds, or ('@', flag, secs)): run by the events cell when its script line would be, as
        itself (`queued`: no line written and read back, review 11-19 i #1). A command no line carries whole is
        refused (ok False, nothing queued)."""
        ok, why = self.check(cmd)
        if ok and cmd.kind not in VERB:     # the queue holds the script verbs' commands: a kind no line carries is do's
            ok, why = False, f'{cmd.kind}: not queued (no script line carries it; do gives it now)'
        if ok:
            try:
                event(cmd, at)              # the checks (it is noted as this event when it runs)
            except ValueError as err:
                ok, why = False, str(err)
        if ok:
            self._queue(queued(cmd, at))
        self._issued.append((self._w.frame_now(), cmd, ok, why or 'posted'))
        return ok, why

    def post_line(self, line, one=False):
        """Queue a script line as it is (`<time> <verb> ...`; a time may be `<flag>+<secs>`): the events queued. A line
        that does not read raises parse_script's ValueError, a run switch RunSwitch (it is given at the start only),
        and with `one` a line that is not exactly one event ValueError -- each before anything is queued."""
        events = self._read(line)
        if any(e[0] is None for e in events):
            raise RunSwitch(f'{line!r}: a run switch, not a line to queue')
        if one and len(events) != 1:
            raise ValueError(f'{line!r}: {len(events)} events, not one')
        for e in events:
            self._queue(e)
            cmd = self.command(e, 'player')
            if cmd is not None:
                self._issued.append((self._w.frame_now(), cmd, True, 'posted'))
        return tuple(events)

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
            ok, why = self._pinned(cmd)
        if ok:
            ok, why = self._pointed(cmd)
        if ok:
            ok, why = getattr(self, '_' + cmd.kind)(cmd)
        self._issued.append((self._w.frame_now(), cmd, ok, why or 'done'))
        return ok, why

    def _pointed(self, cmd):
        """(ok, why) of a route that goes to or turns to a point (POINTED): `pos` two finite numbers, else `place` one
        this world finds -- checked before any unit is touched (review 1122tt closure P2: a bad place surfaced only
        after the old order was dropped or the unpack written, the run stuck)."""
        if cmd.kind not in POINTED:
            return True, ''
        p = self._spot(cmd)
        if isinstance(p, (tuple, list)) and len(p) >= 2 and all(
                isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in p[:2]):
            return True, ''
        return False, f'{cmd.kind}: 找不到地点 {cmd.place if cmd.pos is None else cmd.pos}'

    def _spot(self, cmd):                    # a pointed route's point: `pos`, else where `place` is (None: not found)
        return cmd.pos if cmd.pos is not None else self._w.point(cmd.place) if isinstance(cmd.place, str) else None

    def _pinned(self, cmd):
        """(ok, why) of a command's pins: a serial stands for the living object its name picked (review 1120cc P2).
        `unit_serials`: one for each name in `units`, each the object of that name when it was picked; a pin whose
        object here goes by another name (a foe's serial beside `bob`) refuses the whole command, nothing ordered; one
        whose object is gone -- out of the table, dead (a body stays in it, name and serial), or no longer the giver's
        (`_giver`: given to another player since the click) -- is not ordered, and when none is left the command is
        refused: a name made again since does not take the order (review 1120bb P2 #1). `target_serial`: the object
        `target` names (when it names one), living -- one of another name, or gone, refuses the command (the target is the object picked,
        its name the record; whether the route may take it -- an enemy to attack, a factory of his -- is the route's)."""
        pins = cmd.arg('unit_serials')
        if pins is not None:
            if len(pins) != len(cmd.units):
                return False, f'{len(pins)} 个编号对 {len(cmd.units)} 个名字'
            found = self._serials(pins)
            for name, s in zip(cmd.units, pins):
                if s in found and found[s].name != name:
                    return False, f'编号 {s} 是 {found[s].name}，不是 {name}'
            if not self._held(cmd, found.values()):
                return False, f'找不到 {"、".join(cmd.units)}（编号 {"、".join(map(str, pins))} 已不在）'
        s = cmd.arg('target_serial')
        if s is not None and not takes_target(cmd):    # a route that reads no target would drop the pin unread
            return False, f'{cmd.kind}: 不带目标，编号 {s} 无处可用'     # (review 1120ee P2 #4's class)
        if s is not None:
            t = self._serials((s,)).get(s)
            if t is not None and cmd.target and t.name != cmd.target:     # no name: a pin alone (11-19 m)
                return False, f'编号 {s} 是 {t.name}，不是 {cmd.target}'
            if t is None or not t.alive:
                return False, f'找不到 {cmd.target}（编号 {s} 已不在）'
        return True, ''

    def _serials(self, serials):
        """{serial: the object in the world's table that has it} for those of `serials` there."""
        want = set(serials)
        return {b.serial: b for b in self._w.bodies.values() if b.serial in want}

    def _giver(self, cmd):
        """Whose units a pinned command may order: the AI's (`ai:P`) P's, the player's and the proxy's (a click on his
        own: SimUI and simproxy pick only those) the human's; a script's or a test's anyone's (None)."""
        who, _, player = cmd.by.partition(':')
        if who == 'ai':
            return player
        return self._w.human if who in ('player', 'proxy') else None

    def _held(self, cmd, bodies):
        """The ones of `bodies` a pin still stands for: living, and the giver's (`_giver`)."""
        owner = self._giver(cmd)
        return [b for b in bodies if b.alive and (owner is None or b.owner == owner)]

    def issued(self):
        """(frame, Command, ok, why) for every command posted or done, in order. A record: nothing in a run reads it."""
        return tuple(self._issued)

    def pending(self):
        """The queued script events not run yet, in the order they will run (the timed ones by time, then the ones
        waiting on a flag): what a snapshot holds of the queue."""
        return tuple(self._w.events) + tuple(self._w.anchored)

    # --- the routes (the script verbs' order calls; Sim.happen runs its order verbs through `do` since R3 13c-2)
    def _units(self, cmd):
        # by serial -- a line verb's pins, or the objects an action or the AI picked: each object as picked; one gone
        # (out of the world's table: a name taken over since; dead; no longer the giver's -- `_pinned`) is not
        # ordered: no None to the routes
        pins = cmd.arg('unit_serials')
        if pins is None and cmd.arg('objects') == 'serial':
            pins = cmd.units
        if pins is not None:
            found = self._serials(pins)
            return self._held(cmd, [found[s] for s in pins if s in found])
        if cmd.arg('objects'):              # a map script's: each name as Sim.body finds it, a missing one None
            named = [self._w.body(n) for n in cmd.units]
        else:
            named = [b for who in cmd.units for b in self._w.pick(who)]
        # the AI's by name too: only its own living (review tt #1)
        return self._held(cmd, [b for b in named if b is not None]) if cmd.by.startswith('ai:') else named

    def _target(self, cmd, lookup):
        """The target: `('target_serial', n)` the object the giver picked (`target` its name, for the record; one no
        longer in the world's table is None -- a name taken over since does not take its place: the 11-19 same-name
        sweep), else `lookup(cmd.target)`."""
        s = cmd.arg('target_serial')
        if s is None:
            return lookup(cmd.target)
        return self._serials((s,)).get(s)     # `_pinned` checked it: living, of that name

    def _attack_move(self, cmd):
        r = self._r
        if cmd.arg('objects'):
            return self._script_move(cmd, True)
        for b in self._units(cmd):          # each unit's own attack-move (ATTACK_MOVE_NAMED_UNIT_TO)
            r.order.order_move(self._w, r.peers, b, _where(cmd), True, on_grid=True)
        return True, ''

    def _move(self, cmd):                    # several at once: a group move (MOVE_NAMED_UNIT_TO)
        r = self._r
        if cmd.arg('objects'):
            return self._script_move(cmd, False)
        r.order.order_group(self._w, r.peers, self._units(cmd), _where(cmd), False, on_grid=True)
        return True, ''

    def _script_move(self, cmd, attacking):
        """A map script's move: a team's (`group`: one group move, MOVE_TEAM_TO) or each unit's own; to `pos` or the
        place; `on_grid`: snapped (engine_drop)."""
        w, r, where, grid = self._w, self._r, _where(cmd), cmd.arg('on_grid', False)
        if cmd.arg('group'):
            units = self._units(cmd)
            if cmd.arg('drop_target'):      # the player's click on a selection: his move replaces their attack
                for b in units:
                    b.goal = None
            r.order.order_group(w, r.peers, units, where, attacking, on_grid=grid)
        else:                               # each unit's own (the AI re-sends a member: `drop_target` first; a
            face = cmd.arg('face')          # form-up slot's `face`, radians, turned to once there)
            for b in self._units(cmd):
                if cmd.arg('drop_target'):
                    b.goal = None
                r.order.order_move(w, r.peers, b, where, attacking, face=face, on_grid=grid)
        return True, ''

    def _attack(self, cmd):
        w, r = self._w, self._r
        if cmd.arg('goal_only'):            # the AI's pursuit takes a threat as the unit's goal alone: no fresh attack
            aimed = bool(cmd.target) or cmd.arg('target_serial') is not None    # order, its mode / path / follow
            t = self._target(cmd, w.bodies.get) if aimed else None  # untouched (INFERRED, e135); no target (no name,
            if aimed and (t is None or not t.alive):    # no serial: review 11-19 m): the goal dropped (a charge
                return False, f'找不到 {cmd.target or cmd.arg("target_serial")}'  # ended); a dead one: none (cc P2 #2)
            for b in self._units(cmd):
                b.aiupdate.command('goal', t)
            return True, ''
        if cmd.arg('objects'):
            t = cmd.target if cmd.arg('target_serial') is None else self._target(cmd, None)
            if t is None:
                return False, f'找不到 {cmd.target}'
            sent = []                       # a unit not there is ordered all the same and refuses nothing (as before)
            for b in self._units(cmd):
                ok = r.order.order_attack(w, r.peers, b, t, cmd.force)
                if b is not None:
                    sent.append(ok)
                if ok and b is not None and cmd.arg('team') is not None:    # TEAM_ATTACK_TEAM ('' the default
                    # team's, f #2): the fight takes the team's next one when this dies; a refused one none (o #2)
                    w.team_targets[b.serial] = cmd.arg('team')
            return self._attacked(cmd, sent)
        t = self._target(cmd, lambda n: next(iter(w.pick(n)), None))  # the one picked is given as it is: read
        if t is None:                       # again by its name, a script reference of that name took its place
            return False, f'找不到 {cmd.target}'   # (11-19 same-name sweep S3); pinned, by its serial (z #1)
        return self._attacked(cmd, [r.order.order_attack(w, r.peers, b, t, cmd.force) for b in self._units(cmd)])

    @staticmethod
    def _attacked(cmd, sent):
        """The world's answers (order_attack's): one turned down (its own side without force, a dead one) refuses
        the command (review 11-19 m); no unit, as before, is no refusal."""
        return (True, '') if all(sent) else (False, f'不能攻击 {cmd.target}')

    def _power(self, cmd):
        w, r = self._w, self._r
        if cmd.arg('via') == 'micro':       # the AI micro manager's self-power (micro.fire): refused when none fires;
            # a script's press heeds no reload (engine_aimicro d)
            fired = [r.micro.fire(w, b, cmd.power, r.refresh_modifiers, cmd.by != 'script') for b in self._units(cmd)]
            return (True, '') if fired and all(fired) else (False, f'{cmd.power}: not fired')
        if cmd.arg('objects'):
            return self._script_press(cmd)
        p = w.point(cmd.place)
        refused = []                        # the world's refusals (order_power's (False, why)): the first is the answer
        for b in self._units(cmd):
            u = next((u for u in w.mm.units if u.id == b.template), None)
            if p is None:
                w.note('剧本', f'找不到地点 {cmd.place}')
            else:
                ok, why = r.ability.order_power(w, r.peers, b, (u.abilities.get(cmd.power) if u else None) or cmd.power, p)
                if not ok:
                    refused.append(why)
        if p is None:
            return False, f'找不到地点 {cmd.place}'
        return (False, refused[0]) if refused else (True, '')

    def _capture(self, cmd):
        w, r = self._w, self._r
        if cmd.arg('objects'):              # refused when no unit goes (none there, or none may enter it: f #4)
            t = cmd.target if cmd.arg('target_serial') is None else self._target(cmd, None)
            sent = [r.order.order_capture(w, r.peers, b, t) for b in self._units(cmd)] if t is not None else []
            return (True, '') if sent and all(sent) else (False, f'没有能去占 {cmd.target} 的工兵')
        t = self._target(cmd, lambda n: next(iter(w.pick(n)), None))  # the one picked, as it is (S3, as _attack)
        if t is None:
            return False, f'找不到 {cmd.target}'
        sent = [r.order.order_capture(w, r.peers, b, t) for b in self._units(cmd)]     # each one's answer (i #3)
        return (True, '') if sent and all(sent) else (False, f'没有能去占 {cmd.target} 的工兵')

    def _build(self, cmd):
        w = self._w
        if cmd.arg('objects'):              # a map script's press of that factory's build button (press: queued while
            f = self._target(cmd, w.body)   # banned, bench engine_production g); the action names the template
            if f is None:                   # no factory: refused, not another's queue (review 11-19 f #5; by serial,
                                            # one gone since: same-name sweep 11-19b O07)
                return False, f'找不到工厂 {cmd.target}'
            if w.order_build(cmd.player, cmd.template, factory=f, press=cmd.arg('press', False)):
                return True, ''
            return False, f'{w.label(f)} 现在造不了 {cmd.template}'
        if not cmd.target and cmd.arg('target_serial') is None:     # the player's sidebar click (simproxy): the
            # shortest queue that builds it; a serial alone is that factory's (review 1120ee P2 #4), not the sidebar's
            if w.order_build(cmd.player or w.human, cmd.template):
                return True, ''
            return False, f'没有工厂现在造得了 {cmd.template}'
        if cmd.arg('target_serial') is not None:    # the AI's / the SimUI menu's: the template off that factory's
            tmpl = cmd.template                     # menu, never a role of that name (review 1120aa P2, N03's)
        else:                                       # a text order: a unit ID or a mission role
            tmpl = next((u.id for u in w.mm.units if u.id == cmd.template), None) or \
                next((r.template for k, r in w.m.cast.items() if k == cmd.template), cmd.template)
        f = self._target(cmd, lambda n: next(iter(w.pick(n)), None))   # the AI's: by serial (11-19b N03)
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

    # --- the map scripts' orders (simact_order's actions give them through `do` since R3 13d-1; the actions keep what
    # decides who is ordered -- a team's members, the living ones, the movers -- the routes are the order calls)
    def _guard(self, cmd):
        r = self._r
        for b in self._units(cmd):
            r.order.order_guard(self._w, r.peers, b, cmd.place)
        return True, ''

    def _stop(self, cmd):
        r = self._r
        for b in self._units(cmd):
            r.order.order_stop(b)
        return True, ''

    def _idle(self, cmd):                    # its order dropped, nothing new (the AI's command 5)
        r = self._r
        for b in self._units(cmd):
            r.order.stand(b)
        return True, ''

    def _follow_path(self, cmd):
        r = self._r
        r.order.order_follow(self._w, r.peers, self._units(cmd), cmd.place, cmd.attacking, exact=cmd.arg('exact', False),
                             start=cmd.arg('start'), as_team=cmd.arg('as_team', False))
        return True, ''

    def _attack_ground(self, cmd):           # fire at the spot till another order replaces it (fight: ground_fire)
        r = self._r
        p = self._spot(cmd)
        for b in self._units(cmd):
            r.order.stand(b)
            b.aiupdate.command('ground', p)
        return True, ''

    def _face(self, cmd):                    # stand and turn to the point
        r = self._r
        p = self._spot(cmd)
        for b in self._units(cmd):
            r.order.stand(b)
            b.face = math.atan2(p[1] - b.y, p[0] - b.x)
        return True, ''

    def _hunt(self, cmd):                    # the crew attack-moves to the nearest hostile, again after each dies
        r = self._r
        r.hunt.hunt_due(self._w, r.peers, self._w.frame_now(), self._units(cmd))
        return True, ''

    def _flee(self, cmd):                    # RunOffMapBehavior's run
        r = self._r
        for b in self._units(cmd):
            r.ability.flee_start(self._w, r.peers, b)
        return True, ''

    def _stance(self, cmd):                  # an AI setting, no order dropped: the unit's AIUpdate's (aiupdate.py)
        for b in self._units(cmd):
            b.aiupdate.set_stance(cmd.arg('stance'), isinstance(b.goal, type(b)))
        return True, ''

    def _set_lifetime(self, cmd):            # the AI's late read of a retail fixed lifetime: dies at `die_frame`
        # its dodge's beacon, a foe's (no `_held`): only a living dodge beacon with no lifetime yet, at a whole frame;
        # everything checked before anything is written (review tt #2 / #3)
        die = cmd.arg('die_frame')
        if type(die) is not int or die < 0:
            return False, f'set_lifetime: die_frame {die!r} is not a frame'
        live = [b for b in self._serials(cmd.units).values() if b.alive and 'SKIRMISH_AI_ATTEMPT_TO_DODGE' in b.kinds
                and getattr(b, 'life_end', None) is None]
        for b in live:
            self._r.body.last_until(self._w, b, die)
        return (True, '') if live else (False, 'set_lifetime: no living dodge beacon without a lifetime')

    def _fill_body(self, cmd):               # a factory's unit the template reader knows nothing of: his AI's library
        get, own = self._libs.get(self._giver(cmd)), self._units(cmd)
        lib = get() if get is not None else None
        own = [b for b in own if 'all' in (b.guessed or []) and lib.template(b.template) is not None] if lib else []
        if not own:                         # review tt #6: one the library misses is refused, not "filled"
            return False, 'fill_body: no library, or none of his living it knows and the reader did not'
        for b in own:
            self._r.body.fill(self._w, b, lib)
        return True, ''

    def _auto_acquire(self, cmd):            # an AI setting: takes what only a computer's units take by themselves
        for b in self._units(cmd):
            b.aiupdate.set_auto_acquire(cmd.arg('on'))
        return True, ''

    # --- the map scripts' button presses (simact_ability's since R3 13d-2): the button's module entry with no refusal (a
    # script's press heeds no reload); the action picks the entry by what the unit's template has (`via`)
    def _script_press(self, cmd):
        """power by `button`, `via`: 'wfire' (WeaponFireSpecialAbilityUpdate, at `target` or none), 'leap' (a
        ProjectileSelf leap to the place), 'movement' (MovementSpecialPower to the place), 'self'
        (ActivateModuleSpecialPower) -- a script's press, no refusal; or the player's own (simproxy, R3 13e), which
        answer the world's refusals: 'click' (`power` at `pos`: reload, ground, ForbiddenObjectRange, reach -- then
        the scripts' way at a waypoint), 'transform' (`power` untargeted)."""
        w, r, button, via = self._w, self._r, cmd.arg('button'), cmd.arg('via')
        if via in ('click', 'transform'):
            return r.ability.player_power(w, r.peers, self._units(cmd), cmd.power, cmd.pos, via)
        if via not in ('wfire', 'leap', 'movement', 'self'):
            return False, f'power: no press route {via!r}'
        pressed = []                        # each press's answer: False where the world turned it down (f #4)
        aim = (cmd.target or None) if cmd.arg('target_serial') is None else self._target(cmd, None)   # the object
        for b in self._units(cmd):          # picked by serial, not one of its name (review 1120ee P2 #4's class)
            if via == 'wfire':
                pressed.append(w.wfire_press(b, button, aim))
            elif via == 'leap':
                pressed.append(w.leap_press(b, button, w.point(cmd.place)))
            elif via == 'movement':
                pressed.append(w.movement_power_press(b, button, w.point(cmd.place)))
            else:
                pressed.append(w.self_power_press(b, button))
        return (True, '') if all(pressed) else (False, f'{button}: not pressed (a target gone, out of range)')

    def _unpack(self, cmd):                  # drive to the place, turn into the button's replacement there (M10)
        """At the place, or at `pos` (the AI's SimpleExpansion: armed, `stand` its Distance, `here` where it stands
        then, `send` False -- its team's move walks it)."""
        w, r = self._w, self._r
        p, where = (w.point(cmd.place), cmd.place) if cmd.pos is None else (cmd.pos, None)
        units = self._units(cmd)
        if not units or None in units:      # no unit to unpack: refused before the order call (f #5)
            return False, 'no unit to unpack'
        ok = all([r.ability.order_unpack(w, r.peers, b, p, cmd.arg('button'), where, stand=cmd.arg('stand'), here=cmd.arg('here', False),
                                 send=cmd.arg('send', True)) for b in units])
        return (True, '') if ok else (False, 'no unpack button of his')

    def _toggle(self, cmd):                  # the toggle module (M5) steps to its next ToggleState
        r = self._r
        if all([r.toggle.press(self._w, b, cmd.arg('button'), self._w.short_of_power) for b in self._units(cmd)]):
            return True, ''
        return False, 'not a toggle of his'

    def _enter(self, cmd):                   # into a building (`via` 'garrison': GarrisonContain, the AI's own defense)
        w = self._w
        if cmd.arg('via') != 'garrison':
            return False, f"enter: no route {cmd.arg('via')!r}"
        g = self._target(cmd, w.bodies.get)
        if g is None:
            return False, f'找不到 {cmd.target}'
        sent = [w.garrison.send(b, g) for b in self._units(cmd)]   # each one's answer (review 11-19 k #4: a dead
        return (True, '') if sent and all(sent) else (False, f'进不去 {cmd.target}')    # building was a success)

    def _place(self, cmd):
        """A structure set down at `pos` (`('name', n)`, `('team', t)`): INFERRED -- in the game a dozer / the yard
        builds it there; the skirmish AI's yard job sets it down whole the frame it is done, as before (AI line / step
        G to measure). The giver keeps its own books (made, trace, its note, the free unit)."""
        w = self._w
        b = w.add(cmd.arg('name'), cmd.template, cmd.player, cmd.pos[0], cmd.pos[1],
                  by='skirmish AI' if cmd.by.startswith('ai') else cmd.by, at=w.t, team=cmd.arg('team', ''))
        if w.blocks(b):
            w.reblock()
        w.change()
        return True, ''
