"""The command port (module_plan P "命令端口"; R3 13, draft and census in the private notes): how whoever gives orders --
the player-style runs, the UI, the plays, the script actions, the AI and the proxy -- tells a world's units what to
do, so that when the order family (AIUpdate) moves into kernel modules only this file's routes change.

A command is data: `Command(kind, by, ...)`, names and numbers only (an object, a template, a place by its name; no
object, no function), so it can be logged, compared, queued and saved with a snapshot as it is.

Two routes, as in the game (a player's click is a message carried into the logic frame; the AI and the scripts call
a unit's AI command interface there and then):
- `post(cmd, at)`: queued, run at `at` (mission seconds, or `('@', flag, secs)`: that long after the flag first reads
  1) by the frame loop's events cell -- today's `Sim.events` / `anchored`, so a queued command runs exactly when the
  script line it reads as would (`text(cmd)`: its line; `event(cmd, at)`: the event, the command as given). A command
  its line cannot carry whole (a `pos`, an `args` entry, a `player` or `force` on a kind whose line has none) is
  refused, not queued short. The event is the command's, not its line read back: a name a line cannot hold (an
  unnamed object's `#0`: '#' starts a comment) still reaches its unit (simui replays events). A giver that records
  its run as lines and replays them (autoplay) posts those lines (`post_line`), so its run gives what its replay will
  even where a name splits another way (`a` told to use `x y` reads as `a x` told to use `y`: review 11-19 d #4);
- `do(cmd)`: now (the AI command interface route).
`post_line(line)` queues a whole script line as it is (a play replayed by a test player may hold the god's-hand
verbs too -- 造, 删除, 血量 ...: those are not commands and go in as the script events they are, unlogged).

The port holds no rules: `do` routes each kind to the world's own order call (`Sim.happen` gives a script line's
order through `do` too: one port per run, `Sim.commands`). Kinds with no route yet (`check` says so) get theirs when
their giver moves to the port (R3 13f: the AI). The proxy player (simproxy, R3 13e) gives the player's own clicks
through `do`: a selection's move (`('drop_target', True)`: the click drops the units' attack target first), a sidebar
build (no `target`: the owner's factory with the shortest queue), a ground power or a transform answering the world's
refusals (`via` 'click' / 'transform').

Two kinds of address. A script line's (the player's, the plays'): `units` / `target` are what `Sim.pick` reads (a
role, `名字含 ...`, `队 ...`; one not there is noted). A map script's (`('objects', True)`, the script actions since
R3 13d): `units` are objects' names as the script action found them (`Sim.body`: a reference reads as what it points
at), each given its order even when not there -- the order call takes a missing one as it always did -- and `target`
goes to the order call as it is (it looks the name up itself); `('objects', 'serial')`: `units` are the serials of the
objects the action picked itself (a team's members: found as picked, a reference of the same name cannot take one's
place -- review 11-19 f #1). A route that cannot go on without its object (a factory, the unit to unpack) refuses a
missing one; a press the world turns down (a target gone, out of range) is refused (review 11-19 f #4 #5).

A line's tails `强制` / `由 P` (written only by `text` for a command that has them) read as part of the name when the
whole is a name in the world (`Commands.command`: a role or an object called `enemy 强制`), so a run's line reads as its
own name; a command whose line would read as another here (a forced attack on `enemy` beside an `enemy 强制`) is not
written (`Commands.line`) nor posted (review 11-19 g #2).
`issued()` is the record of what was posted and done -- written, never read in a run (nothing in a game decides by
it; so a snapshot does not hold it: R2 13a)."""
import dataclasses
import math
import sys

# The commands a player or the AI can give in the game (the port's whole vocabulary; module_plan §2 order family and
# the modules they go to). The line verbs below are the ones a script line, so `post`, carries today.
KINDS = frozenset({
    'move', 'attack_move', 'attack', 'attack_ground', 'stop', 'idle', 'guard', 'follow_path', 'capture', 'enter',
    'exit', 'power', 'toggle', 'stance', 'build', 'place', 'unpack', 'sell', 'buy_science', 'hunt', 'flee',
    'auto_acquire', 'face'})
VERB = {'attack_move': '派', 'move': '走', 'attack': '攻击', 'power': '放', 'capture': '占领', 'build': '生产',
        'buy_science': '买'}
KIND = {v: k for k, v in VERB.items()}
# the kinds `do` has a route for (the rest: R3 13e-13f, with their givers): the line verbs', and the script actions'
# (13d-1 the orders; 13d-2 the buttons: unpack, toggle); face (Generals' AI command list has AICMD_FACE_POSITION;
# INFERRED for RA3) joined with them.
ROUTED = frozenset(VERB) | {'guard', 'stop', 'idle', 'follow_path', 'attack_ground', 'face', 'hunt', 'flee', 'stance',
                            'auto_acquire', 'unpack', 'toggle'}
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


def by_player(s):
    """(the rest, (player,)) of a line's tail `... 由 P`, or (s, ()) (sim.parse_script reads 生产 / 买 with it)."""
    head, mark, player = s.rpartition(BY_PLAYER)
    return (head, (player.strip(),)) if mark else (s, ())


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
    extra = [k for k, _ in cmd.args if not (cmd.kind == 'buy_science' and k == 'science')]
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
    """The script event (at, verb, ...) parse_script makes of `at text(cmd)` (for names a line can hold)."""
    text(cmd)                       # the same checks
    verb, by = VERB[cmd.kind], (cmd.player,) if cmd.player else ()
    if cmd.kind == 'buy_science':
        return (at, verb, cmd.arg('science')) + by
    if cmd.kind == 'build':
        return (at, verb, cmd.template, cmd.target) + by
    who = cmd.units[0]
    tail = {'attack_move': (cmd.place,), 'move': (cmd.place,), 'attack': (cmd.target,) + ((FORCE,) if cmd.force else ()),
            'power': (cmd.power, cmd.place), 'capture': (cmd.target,)}[cmd.kind]
    return (at, verb, who) + tail


def command(e, by='script', named=None):
    """The command a script event gives, or None (a god's-hand verb: 造 血量 旗标 摧毁 删除 打, one-name 占领).
    `named(s)`: s is a name in the world -- then a tail `强制` / `由 P` read off a line is the name's own end (g #2)."""
    _, verb, *rest = e
    kind = KIND.get(verb)
    if kind is None or (verb == '占领' and len(rest) != 2):
        return None
    if named and kind == 'attack' and rest[2:] == [FORCE] and named(f'{rest[1]} {FORCE}'):
        rest = [rest[0], f'{rest[1]} {FORCE}']
    if named and kind == 'build' and len(rest) > 2 and named(f'{rest[1]}{BY_PLAYER}{rest[2]}'):
        rest = [rest[0], f'{rest[1]}{BY_PLAYER}{rest[2]}']
    if kind == 'buy_science':
        return Command(kind, by, player=rest[1] if len(rest) > 1 else '', args=(('science', rest[0]),))
    if kind == 'build':
        return Command(kind, by, player=rest[2] if len(rest) > 2 else '', template=rest[0], target=rest[1])
    if kind in ('attack_move', 'move'):
        return Command(kind, by, units=(rest[0],), place=rest[1])
    if kind == 'power':
        return Command(kind, by, units=(rest[0],), power=rest[1], place=rest[2])
    if kind == 'attack':
        return Command(kind, by, units=(rest[0],), target=rest[1], force=rest[2:] == [FORCE])
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
        if self.command(event(cmd, 0), cmd.by) != cmd:
            raise ValueError(f'{s!r} reads as another command here (a name ends in its tail)')
        return s

    def post(self, cmd, at):
        """Queue it for `at` (seconds, or ('@', flag, secs)): run by the events cell as its script line would be. A
        command its line cannot carry whole is refused (ok False, nothing queued)."""
        ok, why = self.check(cmd)
        if ok and cmd.kind not in VERB:     # the queue is today's script events: a kind no line carries is do's only
            ok, why = False, f'{cmd.kind}: not queued (no script line carries it; do gives it now)'
        if ok:
            try:
                e = event(cmd, at)
                self.line(cmd)
            except ValueError as err:
                ok, why = False, str(err)
        if ok:
            self._queue(e)
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
        if cmd.arg('objects') == 'serial':  # the objects an action picked, each as picked (one no longer in the world's
            want = set(cmd.units)           # table -- a name taken over since -- is not ordered: no None to the routes)
            found = {b.serial: b for b in self._w.bodies.values() if b.serial in want}
            return [found[s] for s in cmd.units if s in found]
        if cmd.arg('objects'):              # a map script's: each name as Sim.body finds it, a missing one None
            return [self._w.body(n) for n in cmd.units]
        return [b for who in cmd.units for b in self._w.pick(who)]

    def _attack_move(self, cmd):
        if cmd.arg('objects'):
            return self._script_move(cmd, True)
        for b in self._units(cmd):          # each unit's own attack-move (ATTACK_MOVE_NAMED_UNIT_TO)
            self._w.order_move(b, cmd.place, True, on_grid=True)
        return True, ''

    def _move(self, cmd):                    # several at once: a group move (MOVE_NAMED_UNIT_TO)
        if cmd.arg('objects'):
            return self._script_move(cmd, False)
        self._w.order_group(self._units(cmd), cmd.place, False, on_grid=True)
        return True, ''

    def _script_move(self, cmd, attacking):
        """A map script's move: a team's (`group`: one group move, MOVE_TEAM_TO) or each unit's own; to `pos` or the
        place; `on_grid`: snapped (engine_drop)."""
        w, where, grid = self._w, cmd.place if cmd.pos is None else cmd.pos, cmd.arg('on_grid', False)
        if cmd.arg('group'):
            units = self._units(cmd)
            if cmd.arg('drop_target'):      # the player's click on a selection: his move replaces their attack
                for b in units:
                    b.goal = None
            w.order_group(units, where, attacking, on_grid=grid)
        else:
            for b in self._units(cmd):
                w.order_move(b, where, attacking, on_grid=grid)
        return True, ''

    def _attack(self, cmd):
        w = self._w
        if cmd.arg('objects'):
            for b in self._units(cmd):
                w.order_attack(b, cmd.target, cmd.force)
                if cmd.arg('team') is not None:     # TEAM_ATTACK_TEAM ('' the default team's, f #2): the fight
                    # takes the team's next one when this dies
                    w.team_targets[b.serial] = cmd.arg('team')
            return True, ''
        targets = w.pick(cmd.target)
        if not targets:
            return False, f'找不到 {cmd.target}'
        for b in self._units(cmd):
            w.order_attack(b, targets[0].name, cmd.force)
        return True, ''

    def _power(self, cmd):
        w = self._w
        if cmd.arg('objects'):
            return self._script_press(cmd)
        p = w.point(cmd.place)
        refused = []                        # the world's refusals (order_power's (False, why)): the first is the answer
        for b in self._units(cmd):
            u = next((u for u in w.mm.units if u.id == b.template), None)
            if p is None:
                w.note('剧本', f'找不到地点 {cmd.place}')
            else:
                ok, why = w.order_power(b, (u.abilities.get(cmd.power) if u else None) or cmd.power, p)
                if not ok:
                    refused.append(why)
        if p is None:
            return False, f'找不到地点 {cmd.place}'
        return (False, refused[0]) if refused else (True, '')

    def _capture(self, cmd):
        w = self._w
        if cmd.arg('objects'):              # refused when no unit goes (none there, or none may enter it: f #4)
            sent = [w.order_capture(b, cmd.target) for b in self._units(cmd)]
            return (True, '') if sent and all(sent) else (False, f'没有能去占 {cmd.target} 的工兵')
        targets = w.pick(cmd.target)
        if not targets:
            return False, f'找不到 {cmd.target}'
        for b in self._units(cmd):
            w.order_capture(b, targets[0].name)
        return True, ''

    def _build(self, cmd):
        w = self._w
        if cmd.arg('objects'):              # a map script's press of that factory's build button (press: queued while
            f = w.body(cmd.target)          # banned, bench engine_production g); the action names the template
            if f is None:                   # no factory: refused, not another's queue (review 11-19 f #5)
                return False, f'找不到工厂 {cmd.target}'
            if w.order_build(cmd.player, cmd.template, factory=f, press=cmd.arg('press', False)):
                return True, ''
            return False, f'{w.label(f)} 现在造不了 {cmd.template}'
        if not cmd.target:                  # the player's sidebar click (simproxy): the shortest queue that builds it
            if w.order_build(cmd.player or w.human, cmd.template):
                return True, ''
            return False, f'没有工厂现在造得了 {cmd.template}'
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

    # --- the map scripts' orders (simact_order's actions give them through `do` since R3 13d-1; the actions keep what
    # decides who is ordered -- a team's members, the living ones, the movers -- the routes are the order calls)
    def _guard(self, cmd):
        for b in self._units(cmd):
            self._w.order_guard(b, cmd.place)
        return True, ''

    def _stop(self, cmd):
        for b in self._units(cmd):
            self._w.order_stop(b)
        return True, ''

    def _idle(self, cmd):                    # its order dropped, nothing new (the AI's command 5)
        for b in self._units(cmd):
            self._w.stand(b)
        return True, ''

    def _follow_path(self, cmd):
        self._w.order_follow(self._units(cmd), cmd.place, cmd.attacking, exact=cmd.arg('exact', False),
                             start=cmd.arg('start'), as_team=cmd.arg('as_team', False))
        return True, ''

    def _attack_ground(self, cmd):           # fire at the spot till another order replaces it (fight: ground_fire)
        p = self._w.point(cmd.place)
        for b in self._units(cmd):
            self._w.stand(b)
            b.ground_fire = p
        return True, ''

    def _face(self, cmd):                    # stand and turn to the point
        p = self._w.point(cmd.place)
        for b in self._units(cmd):
            self._w.stand(b)
            b.face = math.atan2(p[1] - b.y, p[0] - b.x)
        return True, ''

    def _hunt(self, cmd):                    # the crew attack-moves to the nearest hostile, again after each dies
        w = self._w
        movers = self._units(cmd)
        w.hunts = [h for h in w.hunts if not any(b in movers for b in h[0])]
        w.hunts.append([movers, None, w.frame_now()])
        w.hunt_due(w.frame_now())
        return True, ''

    def _flee(self, cmd):                    # RunOffMapBehavior's run
        for b in self._units(cmd):
            self._w.flee_start(b)
        return True, ''

    def _stance(self, cmd):                  # an AI setting, no order dropped: GUARD 0 AGGRESSIVE 1 HOLD_POSITION 2 HOLD_FIRE 3
        stance = cmd.arg('stance')
        for b in self._units(cmd):
            hold = stance == 3               # going HOLD_FIRE stops a standing attack without dropping it (stance.md)
            if hold != b.hold_fire:
                b.hold_paused = hold and isinstance(b.goal, type(b))
            b.hold_fire, b.stance = hold, stance
        return True, ''

    # --- the map scripts' button presses (simact_ability's since R3 13d-2): the button's module entry with no refusal (a
    # script's press heeds no reload); the action picks the entry by what the unit's template has (`via`)
    def _script_press(self, cmd):
        """power by `button`, `via`: 'wfire' (WeaponFireSpecialAbilityUpdate, at `target` or none), 'leap' (a
        ProjectileSelf leap to the place), 'movement' (MovementSpecialPower to the place), 'self'
        (ActivateModuleSpecialPower) -- a script's press, no refusal; or the player's own (simproxy, R3 13e), which
        answer the world's refusals: 'click' (`power` at `pos`: reload, ground, ForbiddenObjectRange, reach -- then
        the scripts' way at a waypoint), 'transform' (`power` untargeted)."""
        w, button, via = self._w, cmd.arg('button'), cmd.arg('via')
        if via in ('click', 'transform'):
            return self._player_power(cmd, via)
        if via not in ('wfire', 'leap', 'movement', 'self'):
            return False, f'power: no press route {via!r}'
        pressed = []                        # each press's answer: False where the world turned it down (f #4)
        for b in self._units(cmd):
            if via == 'wfire':
                pressed.append(w.wfire_press(b, button, cmd.target or None))
            elif via == 'leap':
                pressed.append(w.leap_press(b, button, w.point(cmd.place)))
            elif via == 'movement':
                pressed.append(w.movement_power_press(b, button, w.point(cmd.place)))
            else:
                pressed.append(w.self_power_press(b, button))
        return (True, '') if all(pressed) else (False, f'{button}: not pressed (a target gone, out of range)')

    def _player_power(self, cmd, via):
        """Each unit's own click; refused only when every unit's is (why: their refusals, sorted, once each)."""
        w, units, refused = self._w, self._units(cmd), []
        for b in units:
            ok, why = w.order_power(b, cmd.power, cmd.pos) if via == 'click' else w.order_transform(b, cmd.power)
            if not ok:
                refused.append(why)
        if units and len(refused) == len(units):
            return False, ', '.join(sorted(set(refused)))
        return True, ''

    def _unpack(self, cmd):                  # drive to the place, turn into the button's replacement there (M10)
        w = self._w
        p = w.point(cmd.place)
        if None in self._units(cmd):        # no unit to unpack: refused before the order call (f #5)
            return False, 'no unit to unpack'
        if all([w.order_unpack(b, p, cmd.arg('button'), cmd.place) for b in self._units(cmd)]):
            return True, ''
        return False, 'no unpack button of his'

    def _toggle(self, cmd):                  # the toggle module (M5) steps to its next ToggleState
        if all([self._w.toggle_press(b, cmd.arg('button')) for b in self._units(cmd)]):
            return True, ''
        return False, 'not a toggle of his'

    def _auto_acquire(self, cmd):            # an AI setting: takes what only a computer's units take by themselves
        for b in self._units(cmd):
            b.ai_acquire = cmd.arg('on')
        return True, ''
