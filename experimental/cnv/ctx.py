"""The compile context a plan device (devices/) or a hand-written level (missions/a8, j4) is given: what it may ask of
the compiler and the mission, and the three outlets everything a player sees or a unit is told goes through.

  say(key, secs)                 the one way to show a line: the action that puts `key` on the caption strip
  camera(a, secs, in, out)       the camera moves a plan's 镜头 step compiles to (needs the compiler)
  order(kind, names, target)     the one way to tell named units what to do: whole-team orders (attack, guard, hunt,
                                 move, attack_move, stop), the group made a team of the map's own (K6, G6)

`say` is the one queue (class Talk): a line only raises its flag, and the `CNV <tag> - Say k` script plays it when nobody
is talking, then holds the floor. The strip stacks lines and clears them all ~5.4 s after the last one came up
(2026-11-03, measured in CampShell), so two lines closer than that show together; a line in a 过场 takes the same floor
(scene_steps), and the floor is reserved for a whole scene, so no line from outside lands in it. The rest is the small
set of things a device used to take from `self.c` (the compiler) and `self.m` (the mission) by reaching in: each is one
line that forwards, so a device can no longer touch what is not listed. A Ctx made without a compiler (a hand-written
level has none) answers say / order / tag and the mission's own; a compiler's questions raise PlanError.
"""
from model import TEAM_ORDERS, Script
from plantime import PlanError

CAPTION = 'SHOW_MILITARY_CAPTION'        # the caption action is spelled here and nowhere else (tests/test_architecture G3a)
FUNC, CHAT = '功能', '闲话'              # a line's tier (Talk): the plan marks a 功能 line, an unmarked one is 闲话
NAME = {FUNC: 'func', CHAT: 'chat'}       # a tier in a script's or counter's name (those are Latin-1)
CHAT_LIFE = 10.0                       # a 闲话 line that waited this long (s) in the queue is dropped
STRIP_CLEAR = 6.5                       # the caption strip stacks lines and clears all at once ~5.4 s after the last one was
                                        # added; a line takes the floor this long at least (with a margin)


def caption(key, secs):
    """The action that shows the strip text `key` for `secs` seconds."""
    return (CAPTION, key, secs)


class Talk:
    """The one queue of everything said (a caption, a voice line, an announcer line). Outside a 过场 a line asks to be
    said (flag `Want k`); the script `Enq k` puts it at the back of its tier's queue (counter `Q`, the line's place in
    counter `Pos k`), and `Say k` plays it when it is first in its tier and nobody is talking (flag `Talking`), then
    holds the floor for the line's turn (at least STRIP_CLEAR): first come, first played. Three tiers, 2026-11-04
    (总控): the ending's own line is said by the ending script itself, ahead of everything, once the floor is free
    (ending_gate); a 功能 line (a goal, an attack coming, the convoy leaving, a horn) is never dropped and goes ahead of
    the rest; a 闲话 line that has waited CHAT_LIFE seconds is dropped (a line said ten seconds late is not about what
    the player sees: K2). Both queues only ever lose their first line (played, or the oldest 闲话 line dropped), so a
    place is kept by one decrement of the lines behind (`Shift`). In a 过场 (scene) the line is handed back as its own
    actions: the scene's timeline places it, and scene_steps puts it through floor() so it takes the same floor."""

    def __init__(self, tag):
        self.tag = tag
        self.busy, self.timer = f'CNV_{tag}_Talking', f'CNV {tag} Talk Timer'
        self.scening = f'CNV_{tag}_InScene'     # raised for the length of a scene: no queued line starts in it
        self.dropped = f'CNV_{tag}_Dropped'     # counts the 闲话 lines that waited too long (the sim reads it)
        self.lines = []                         # (tier, actions, seconds) of the queued lines
        self.scene = False                      # compiling a 过场
        self.scened = False                     # the level has a 过场 (its queued lines wait for it)
        self.floored = False                    # a scene line took the floor (Say done must free it)
        self.turn = 0.0                         # seconds the last line handed back in a scene takes to say
        self.anchored = True                    # the rule being compiled hangs on an event or a camera (K2)

    # names: one place for each (the flags and counters a line's scripts share)
    def want(self, k):
        return f'CNV_{self.tag}_Want_{k}'

    def pending(self, k):
        return f'CNV_{self.tag}_Say_{k}'

    def place(self, k):
        return f'CNV_{self.tag}_Pos_{k}'

    def length(self, tier):
        return f'CNV_{self.tag}_Q_{NAME[tier]}'

    def left(self, tier):
        return f'CNV_{self.tag}_Left_{NAME[tier]}'

    def put(self, before, key, secs, after, turn, tier=FUNC):
        acts = list(before) + ([caption(key, secs)] if key is not None else []) + list(after)
        if self.scene:
            self.turn = turn
            return acts
        if tier not in (FUNC, CHAT):
            raise PlanError(f'a line {key!r}: tier {tier!r}: {FUNC} or {CHAT}')
        if not self.anchored:
            raise PlanError(f'a line {key!r} that hangs on nothing but the clock: a rule that says something needs an '
                            f'event in its 当 (not just 开局 + a time), or a 镜头 or other act before the line, so what '
                            f'the player sees is what is said')
        self.lines.append((tier, acts, max(turn, STRIP_CLEAR)))
        return [('SET_FLAG', self.want(len(self.lines) - 1), 1)]

    def floor(self, acts, turn):
        """`acts` (one line of a scene) as a line that holds the floor for its turn."""
        self.floored = True
        return [('SET_FLAG', self.busy, 1),
                ('SET_MILLISECOND_TIMER', self.timer, float(max(turn, STRIP_CLEAR)))] + list(acts)

    def ending_gate(self):
        """The condition an ending script adds: it waits for the line being said to end, then says its own and ends the
        mission in the same frame (the ending line is never lost, and is before every queued line)."""
        return [('FLAG', self.busy, 0)]

    def ending_begin(self):
        """What an ending script does first: take the floor, so no queued line starts in the frame the mission ends."""
        return [('SET_FLAG', self.busy, 1)]

    def scripts(self):
        """The scripts that play the queued lines. The order is the engine's: Shift sees what the last frame's leaver
        raised, Enq sees the queue Shift left, and the leavers (Say, Drop) come after both."""
        out, tiers = [], [t for t in (FUNC, CHAT) if any(x[0] == t for x in self.lines)]
        for tier in tiers:
            ks = [k for k, x in enumerate(self.lines) if x[0] == tier]
            out += [Script(f'CNV {self.tag} - Shift {k}', [('FLAG', self.left(tier), 1), ('FLAG', self.pending(k), 1),
                                                           ('COUNTER', self.place(k), 4, 0)],
                           [('DECREMENT_COUNTER', 1, self.place(k))], once=False) for k in ks]
            out.append(Script(f'CNV {self.tag} - Shift done {NAME[tier]}', [('FLAG', self.left(tier), 1)],
                              [('SET_FLAG', self.left(tier), 0)], once=False))
        for k, (tier, acts, secs) in enumerate(self.lines):
            out.append(Script(f'CNV {self.tag} - Enq {k}', [('FLAG', self.want(k), 1), ('FLAG', self.pending(k), 0)],
                              [('SET_FLAG', self.want(k), 0), ('SET_FLAG', self.pending(k), 1),
                               ('SET_COUNTER_TO_COUNTER', self.place(k), self.length(tier)),
                               ('INCREMENT_COUNTER', 1, self.length(tier))] +
                              ([('SET_MILLISECOND_TIMER', f'CNV {self.tag} Age {k}', CHAT_LIFE)] if tier == CHAT else []),
                              once=False))
        gate = [('FLAG', self.scening, 0)] if self.scened else []
        for k, (tier, acts, secs) in enumerate(self.lines):
            first = [('FLAG', self.pending(k), 1), ('COUNTER', self.place(k), 2, 0)]
            leave = [('SET_FLAG', self.pending(k), 0), ('SET_FLAG', self.want(k), 0),
                     ('DECREMENT_COUNTER', 1, self.length(tier)), ('SET_FLAG', self.left(tier), 1)]
            # the 闲话 wait for the 功能 queue to be empty
            ahead = [('COUNTER', self.length(FUNC), 2, 0)] if tier == CHAT and FUNC in tiers else []
            out.append(Script(f'CNV {self.tag} - Say {k}' + (' chat' if tier == CHAT else ''),
                              first + [('FLAG', self.busy, 0)] + ahead + gate,
                              leave + [('SET_FLAG', self.busy, 1), ('SET_MILLISECOND_TIMER', self.timer, float(secs))]
                              + acts, once=False))
        for k, (tier, acts, secs) in enumerate(self.lines):
            if tier == CHAT:
                out.append(Script(f'CNV {self.tag} - Drop {k}',
                                  [('FLAG', self.pending(k), 1), ('TIMER_EXPIRED', f'CNV {self.tag} Age {k}'),
                                   ('COUNTER', self.place(k), 2, 0)],
                                  [('SET_FLAG', self.pending(k), 0), ('SET_FLAG', self.want(k), 0),
                                   ('DECREMENT_COUNTER', 1, self.length(tier)), ('SET_FLAG', self.left(tier), 1),
                                   ('INCREMENT_COUNTER', 1, self.dropped)], once=False))
        if self.lines or self.floored:
            out.append(Script(f'CNV {self.tag} - Say done', [('FLAG', self.busy, 1), ('TIMER_EXPIRED', self.timer)],
                              [('SET_FLAG', self.busy, 0)], once=False))
        return out


class Ctx:
    def __init__(self, compiler=None, mission=None, tag=None):
        if compiler is None and mission is None:
            raise PlanError('Ctx: needs a compiler or a mission')
        self._c = compiler
        self._m = mission if mission is not None else compiler.m
        self.tag = tag if tag is not None else compiler.tag
        self.talk = Talk(self.tag)

    # ---- the three outlets
    def say(self, key, secs, tier=FUNC):
        """One line of caption: the action that queues it (the caption itself inside a scene). A device's or a
        hand-written level's line is a 功能 line unless told."""
        return self.line((), key, secs, tier=tier)[0]

    def line(self, before, key, secs, after=(), turn=None, tier=FUNC):
        """A line said: `before` (a voice event), the caption `key` (None: no caption, as retail's announcer), `after`
        (a talking head); `secs` the caption stays, `turn` how long the line takes the floor (default `secs`); `tier`
        FUNC or CHAT (Talk). The actions that queue it."""
        return self.talk.put(before, key, secs, after, secs if turn is None else turn, tier)

    def final(self, key, secs):
        """The ending's own line: the caption an ending script shows in the frame it ends the mission (its script
        takes ending_gate: it is said after the line being said, ahead of every queued one)."""
        return caption(key, secs)

    def ending_gate(self):
        return self.talk.ending_gate()

    def ending_begin(self):
        return self.talk.ending_begin()

    def talk_scripts(self):
        """What a level written by hand adds to its scripts at the end: the scripts that play its queued lines."""
        return self.talk.scripts()

    def camera(self, a, secs, ease_in, ease_out):
        return self._compiler('camera').camera(a, secs, ease_in, ease_out)

    def order(self, kind, names, target=None, side='p1', crew=None):
        """The one way to tell named units what to do (K6, G6): the actions that give the group `names`, of `side`, a
        whole-team order (Mission.order: the units join the group's team first, so one made or let go later takes it
        too). kind: attack (target: a named unit), guard (an area), hunt, move / attack_move (a waypoint), stop (the
        team's members, no joining). `crew` keys the group's team when several calls must order the same group (a
        convoy's trucks); else it is named after the set of names."""
        if kind not in TEAM_ORDERS:
            raise PlanError(f'order: no kind {kind!r}: {", ".join(TEAM_ORDERS)}')
        if kind not in ('hunt', 'stop') and target is None:
            raise PlanError(f'order {kind}: needs a target')
        return self._m.order(kind, names, target, side, crew)

    # ---- the compiler's
    def _compiler(self, what):
        if self._c is None:
            raise PlanError(f'{what}: this level is written by hand, there is no plan compiler behind it')
        return self._c

    def unit(self, name, side='p1'):
        return self._compiler('unit').unit(name, side)

    def when(self, label, c, actions, **kw):
        return self._compiler('when').when(label, c, actions, **kw)

    def area(self, site):
        return self._compiler('area').area(site)

    def mark(self, site):
        """A waypoint at a site (published as a mark under the site's name), its name."""
        return self._compiler('mark').mark(site)

    def text(self, kind, s):
        return self._compiler('text').text(kind, s)

    def part_names(self, part):
        return self._compiler('part_names').part_names(part)

    def side(self, who):
        return self._compiler('side').side[who]

    def side_names(self):
        """The plan's side words (我, 敌 ...), sorted."""
        return sorted(self._compiler('side_names').side)

    def device(self, name):
        return self._compiler('device').devices[name]

    def plan_start(self, value):
        """The plan's own start phase times of `value` (what carrier.facts asks of the compiler's data)."""
        import plancheck
        c = self._compiler('plan_start')
        return plancheck.times_of(value, plancheck.phase_starts(c.d))

    # ---- the mission's
    def put(self, *a, **kw):
        return self._m.put(*a, **kw)

    def player(self, who):
        return self._m.player(who)

    def team(self, who):
        return self._m.team(who)

    def waypoint(self, *a, **kw):
        return self._m.waypoint(*a, **kw)

    def point(self, key):
        return self._m.point(key)

    def site(self, name, dx=0.0, dy=0.0):
        return self._m.site(name, dx, dy)

    def site_names(self):
        """The names of the sites the map publishes."""
        return list(self._m.map.SITES)

    def where(self, site):
        return self._m.where(site)

    def mark_of(self, key):
        """The waypoint a mark key (`ice 3`, `sea`) names."""
        return self._m.mark(key)

    def has_mark(self, key):
        return key in self._m.marks

    def add_area(self, name, area):
        self._m.areas[name] = area

    def add_point(self, name, xy):
        self._m.waypoints[name] = xy

    def spawns_add(self, *templates):
        """Templates the scripts create (the contract: they must be published)."""
        self._m.spawns.update(templates)

    def string(self, key, text, keep=False):
        """A string of the mission's table; `keep` leaves one already there."""
        if keep:
            self._m.strings.setdefault(key, text)
        else:
            self._m.strings[key] = text

    def countdown(self, timer):
        self._m.countdowns.append(timer)

    def add_unit(self, unit):
        self._m.units.append(unit)

    def add_role(self, key, role, later=False):
        self._m.cast[key] = role
        if later:
            self._m.later.add(key)

    def made(self, keys):
        return self._m.made(keys)

    def role(self, key):
        return self._m.cast[key]

    def roles(self):
        return list(self._m.cast.values())

    def compiled_scripts(self):
        return list(self._m.scripts)

    def fact(self, key, default=None):
        return self._m.facts.get(key, default)

    def has_fact(self, key):
        return key in self._m.facts

    def voice_has(self, group):
        """Whether the mission's voice pack has the voice group (True when there is no pack: nothing to be missing)."""
        voice = self._m.voice
        return voice is None or group in getattr(voice, 'groups', {group})
