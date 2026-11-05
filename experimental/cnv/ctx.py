"""The compile context a plan device (devices/) or a hand-written level (missions/a8, j4) is given: what it may ask of
the compiler and the mission, and the three outlets everything a player sees or a unit is told goes through.

  say(key, secs)                 the one way to show a line: the action that puts `key` on the caption strip
  camera(a, secs, in, out)       the camera moves a plan's 镜头 step compiles to (needs the compiler)
  order(kind, names, target)     the one way to tell named units what to do: whole-team orders (attack, guard, hunt,
                                 move, attack_move, stop), the group made a team of the map's own (K6, G6)

`say` is the one queue (class Talk): a line only raises its flag. The screen has two channels (engine line, 2026-11-04,
measured on the bench, E6): the military caption box at the top holds ONE line, a new one replaces it and each leaves
after its own seconds; the dialogue panel at the bottom stacks the subtitles of dubbed lines. A line goes by one channel
only: a 功能 line is a caption, shown the frame its event comes (its recording, if any, goes to the head of the queue);
a dubbed 闲话 line is its recording with its own subtitle in the panel and no caption; a 闲话 line nobody recorded is a
caption that waits for the box. A line in a 过场 takes the floor too (scene_steps), and the floor is reserved for a whole
scene, so no line from outside lands in it. The rest is the small
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
PANEL_CLEAR = 5.4                       # the dialogue panel stacks subtitles and clears them all this long (s) after the last
                                        # came up (measured 2026-11-03); the sim models it, no script waits for it
FUNC_HOLD = 2.0                         # a 功能 caption stays up this long (s) at least before another 功能 one replaces it
STRIP_MAX = 2                           # lines the player sees at once (the strip, below): never more (I1, 2026-11-05)
STRIP_HOLD = 6.0                        # what the scripts assume the strip holds a line (s) after the last one came up: the
                                        # game clears it 5.1~6.0 s after the last (PANEL_CLEAR is the middle of that)
FUNC_LATE = FUNC_HOLD + STRIP_HOLD + 0.5    # a 功能 line's caption is up this soon (s) after its event: the contract rule and
                                        # the sim hold the product to it (K1: "号角响了！" came 14 s after the horn). A 功能
                                        # line waits for room in the strip (STRIP_MAX): three at one moment fit (0, FUNC_HOLD,
                                        # then one clearing, STRIP_HOLD, after the second); a fourth is a plan to fix
# THE STRIP (I1, CampShell acceptance 2026-11-05): in the shipped game (CampShell) the military caption, the dubbed lines'
# subtitles and an announcer event's text all go into ONE box that accumulates -- a new line is added under the old ones
# and nothing leaves one by one; the whole stack clears STRIP_HOLD after the last was added. (The bench's E6 measurement
# found a one-line caption box apart from the panel; the product screenshots do not: 3 and 4 lines, captions with
# subtitles, one box.) So the number of lines at once is the depth of one stack, and it is what the queue keeps down:
# every line that comes up counts into counter `Strip` (re-armed timer, cleared when it runs out), and a queued line or a
# 功能 caption comes up only while the depth is below STRIP_MAX.


def caption(key, secs):
    """The action that shows the strip text `key` for `secs` seconds."""
    return (CAPTION, key, secs)


class Line:
    """One queued line: its tier; `acts` what the queue plays when its turn comes (a recording and its talking head, or
    the caption of a 闲话 line nobody recorded); `turn` seconds it holds the floor; `now` a 功能 line's caption, which is
    not queued but shown the frame its event comes (`secs` it stays); `strip` that `acts` show a caption (so the line
    waits for the caption box to be free and holds it)."""
    __slots__ = ('tier', 'acts', 'turn', 'now', 'secs', 'strip', 'adds')

    def __init__(self, tier, acts, turn, now=None, secs=0.0, strip=False, adds=False):
        self.tier, self.acts, self.turn, self.now, self.secs, self.strip = tier, acts, turn, now, secs, strip
        self.adds = adds        # coming up it adds a line to the strip (and waits for room in it); acts carry the count


class Talk:
    """The one queue of everything said (a caption, a voice line, an announcer line). Two channels (E6, see the module
    doc), so a line is one of three things. A 功能 line (a goal, an attack coming, the convoy leaving, a horn) is a caption
    shown the frame its event comes -- the box takes it at once, replacing what was there (script `Now k`, at most
    FUNC_LATE after the event) -- and its recording, if it has one, goes ahead of the 闲话 in the queue. A dubbed 闲话
    line is its recording with a subtitle of its own, which the panel shows. A 闲话 line nobody recorded is a caption
    that waits its turn, so it does not cut off a caption still being read. The queue: a line asks to be said (flag
    `Want k`); the script `Enq k` puts it at the back of its tier's queue (counter `Q`, the line's place in counter
    `Pos k`), and `Say k` plays it when it is first in its tier and nobody is talking (flag `Talking`), then holds the
    floor for the line's turn (the recording and a short gap, or the caption's own seconds): first come, first played.
    Three tiers, 2026-11-04 (总控): the ending's own line is said by the ending script itself, ahead of everything, once
    the floor is free (ending_gate); a 功能 line is never dropped and goes ahead of the rest; a 闲话 line that has
    waited CHAT_LIFE seconds is dropped (a line said ten seconds late is not about what the player sees: K2). Both
    queues only ever lose their first line (played, or the oldest 闲话 line dropped), so a place is kept by one
    decrement of the lines behind (`Shift`). In a 过场 (scene) the line is handed back as its own actions: the scene's
    timeline places it, and scene_steps puts it through floor() so it takes the same floor."""

    def __init__(self, tag):
        self.tag = tag
        self.busy, self.timer = f'CNV_{tag}_Talking', f'CNV {tag} Talk Timer'
        self.box, self.box_timer = f'CNV_{tag}_Box', f'CNV {tag} Box Timer'       # the caption box is taken (its line is up)
        self.fresh, self.fresh_timer = f'CNV_{tag}_Fresh', f'CNV {tag} Fresh Timer'    # a 功能 caption went up FUNC_HOLD ago
        self.scening = f'CNV_{tag}_InScene'     # raised for the length of a scene: no queued line starts in it
        self.dropped = f'CNV_{tag}_Dropped'     # counts the 闲话 lines that waited too long (the sim reads it)
        self.strip, self.strip_timer = f'CNV_{tag}_Strip', f'CNV {tag} Strip Timer'    # lines in the strip now, its clear-out
        self.lines = []                         # the Lines, in the order they were written
        self.scene = False                      # compiling a 过场
        self.scened = False                     # the level has a 过场 (its queued lines wait for it)
        self.floored = False                    # a scene line took the floor (Say done must free it)
        self.turn = 0.0                         # seconds the last line handed back in a scene takes to say
        self.anchored = True                    # the rule being compiled hangs on an event or a camera (K2)

    # names: one place for each (the flags and counters a line's scripts share)
    def want(self, k):
        return f'CNV_{self.tag}_Want_{k}'

    def show(self, k):
        return f'CNV_{self.tag}_Show_{k}'

    def pending(self, k):
        return f'CNV_{self.tag}_Say_{k}'

    def place(self, k):
        return f'CNV_{self.tag}_Pos_{k}'

    def length(self, tier):
        return f'CNV_{self.tag}_Q_{NAME[tier]}'

    def left(self, tier):
        return f'CNV_{self.tag}_Left_{NAME[tier]}'

    def take_box(self, secs):
        """The actions that mark the caption box taken for `secs`: a 闲话 caption waits for it."""
        return [('SET_FLAG', self.box, 1), ('SET_MILLISECOND_TIMER', self.box_timer, float(secs))]

    def strip_add(self):
        """What a line coming up does to the strip: one more line in it, its clear-out timer started again."""
        return [('INCREMENT_COUNTER', 1, self.strip), ('SET_MILLISECOND_TIMER', self.strip_timer, STRIP_HOLD)]

    def strip_room(self):
        """The condition a line coming up waits for: fewer than STRIP_MAX lines in the strip."""
        return ('COUNTER', self.strip, 0, STRIP_MAX)

    def put(self, before, key, secs, after, turn, tier=FUNC):
        cap = [caption(key, secs)] if key is not None else []
        if self.scene:
            self.turn = turn
            return list(before) + cap + list(after) + self.strip_add()
        if tier not in (FUNC, CHAT):
            raise PlanError(f'a line {key!r}: tier {tier!r}: {FUNC} or {CHAT}')
        if not self.anchored:
            raise PlanError(f'a line {key!r} that hangs on nothing but the clock: a rule that says something needs an '
                            f'event in its 当 (not just 开局 + a time), or a 镜头 or other act before the line, so what '
                            f'the player sees is what is said')
        k, voice = len(self.lines), list(before) + list(after)
        if tier == FUNC and cap:                # the caption now, the recording (if any) in the queue
            self.lines.append(Line(tier, voice, turn, cap + self.take_box(secs) + self.strip_add(), secs, adds=True))
            return [('SET_FLAG', self.show(k), 1)] + ([('SET_FLAG', self.want(k), 1)] if voice else [])
        if cap:
            self.lines.append(Line(tier, list(before) + cap + list(after) + self.take_box(turn) + self.strip_add(), turn,
                                   strip=True, adds=True))
        else:                                   # a subtitled recording or an announcer event: its text is a line too
            self.lines.append(Line(tier, voice + self.strip_add(), turn, adds=True))
        return [('SET_FLAG', self.want(k), 1)]

    def floor(self, acts, turn):
        """`acts` (one line of a scene) as a line that holds the floor for its turn."""
        self.floored = True
        return [('SET_FLAG', self.busy, 1), ('SET_MILLISECOND_TIMER', self.timer, float(turn))] + list(acts)

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
        out = []
        queued = [(k, x) for k, x in enumerate(self.lines) if x.acts]
        tiers = [t for t in (FUNC, CHAT) if any(x.tier == t for _, x in queued)]
        for tier in tiers:
            ks = [k for k, x in queued if x.tier == tier]
            out += [Script(f'CNV {self.tag} - Shift {k}', [('FLAG', self.left(tier), 1), ('FLAG', self.pending(k), 1),
                                                           ('COUNTER', self.place(k), 4, 0)],
                           [('DECREMENT_COUNTER', 1, self.place(k))], once=False) for k in ks]
            out.append(Script(f'CNV {self.tag} - Shift done {NAME[tier]}', [('FLAG', self.left(tier), 1)],
                              [('SET_FLAG', self.left(tier), 0)], once=False))
        gate = [('FLAG', self.scening, 0)] if self.scened else []
        if self.lines or self.floored:          # (first: a line coming up in the frame the strip clears sees it empty)
            out.append(Script(f'CNV {self.tag} - Strip done', [('TIMER_EXPIRED', self.strip_timer)],
                              [('SET_COUNTER', self.strip, 0)], once=False))
        room = [self.strip_room()]
        if any(x.now for x in self.lines):      # (before the captions: the one that waited sees the flag down in its frame)
            out.append(Script(f'CNV {self.tag} - Fresh done', [('FLAG', self.fresh, 1), ('TIMER_EXPIRED', self.fresh_timer)],
                              [('SET_FLAG', self.fresh, 0)], once=False))
        for k, x in enumerate(self.lines):      # a 功能 caption: up in the frame its event came (the scene's end, in one)
            if x.now:
                out.append(Script(f'CNV {self.tag} - Now {k}', [('FLAG', self.show(k), 1), ('FLAG', self.fresh, 0)] + room + gate,
                                  [('SET_FLAG', self.show(k), 0), ('SET_FLAG', self.fresh, 1),
                                   ('SET_MILLISECOND_TIMER', self.fresh_timer, FUNC_HOLD)] + x.now, once=False))
        for k, x in queued:
            out.append(Script(f'CNV {self.tag} - Enq {k}', [('FLAG', self.want(k), 1), ('FLAG', self.pending(k), 0)],
                              [('SET_FLAG', self.want(k), 0), ('SET_FLAG', self.pending(k), 1),
                               ('SET_COUNTER_TO_COUNTER', self.place(k), self.length(x.tier)),
                               ('INCREMENT_COUNTER', 1, self.length(x.tier))] +
                              ([('SET_MILLISECOND_TIMER', f'CNV {self.tag} Age {k}', CHAT_LIFE)] if x.tier == CHAT else []),
                              once=False))
        for k, x in queued:
            first = [('FLAG', self.pending(k), 1), ('COUNTER', self.place(k), 2, 0)]
            leave = [('SET_FLAG', self.pending(k), 0), ('SET_FLAG', self.want(k), 0),
                     ('DECREMENT_COUNTER', 1, self.length(x.tier)), ('SET_FLAG', self.left(x.tier), 1)]
            # the 闲话 wait for the 功能 queue to be empty, a caption for the box to be free
            ahead = [('COUNTER', self.length(FUNC), 2, 0)] if x.tier == CHAT and FUNC in tiers else []
            out.append(Script(f'CNV {self.tag} - Say {k}' + (' chat' if x.tier == CHAT else ''),
                              first + [('FLAG', self.busy, 0)] + ahead + ([('FLAG', self.box, 0)] if x.strip else [])
                              + (room if x.adds and not x.now else []) + gate,
                              leave + [('SET_FLAG', self.busy, 1), ('SET_MILLISECOND_TIMER', self.timer, float(x.turn))]
                              + x.acts, once=False))
        for k, x in queued:
            if x.tier == CHAT:
                out.append(Script(f'CNV {self.tag} - Drop {k}',
                                  [('FLAG', self.pending(k), 1), ('TIMER_EXPIRED', f'CNV {self.tag} Age {k}'),
                                   ('COUNTER', self.place(k), 2, 0)],
                                  [('SET_FLAG', self.pending(k), 0), ('SET_FLAG', self.want(k), 0),
                                   ('DECREMENT_COUNTER', 1, self.length(x.tier)), ('SET_FLAG', self.left(x.tier), 1),
                                   ('INCREMENT_COUNTER', 1, self.dropped)], once=False))
        if queued or self.floored:
            out.append(Script(f'CNV {self.tag} - Say done', [('FLAG', self.busy, 1), ('TIMER_EXPIRED', self.timer)],
                              [('SET_FLAG', self.busy, 0)], once=False))
        if any(x.now or x.strip for x in self.lines):
            out.append(Script(f'CNV {self.tag} - Box done', [('FLAG', self.box, 1), ('TIMER_EXPIRED', self.box_timer)],
                              [('SET_FLAG', self.box, 0)], once=False))
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

    def camera(self, a, secs, ease_in, ease_out, tight=False):
        return self._compiler('camera').camera(a, secs, ease_in, ease_out, tight)

    def stage(self, label, camera, see, hide, scripts, smoke=()):
        """K8 (I4): declare a staged piece of a scene -- its camera (a view point: the waypoint a ctx.camera move
        names), what must be in the picture (`see`: [(what, (x, y))]) and what must stay out of it (`hide`: where a
        unit is made, taken away or sent from unseen), and the scripts that make / delete / move units for it.
        `smoke`: those of the scripts that make or take away units IN the picture: each makes smoke at a place in it.
        contract.demo_unframed checks the geometry and that no such script of a demonstration is left undeclared."""
        self._m.stages.append(dict(label=label, camera=camera, see=list(see), hide=list(hide), scripts=list(scripts),
                                   smoke=list(smoke)))

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
