"""The game adapter, step 1 (work/re/sim_split/adapter_pack/plan.md 会话 1): a fixed bench map's reading contract and
the replay transport, so a plug-in written against the observation port (experimental/cnv/engine/ports/observe.py)
can read a game the way it reads a simulator run -- the part of the port the bench has a channel for, and nothing
else.

What the bench gives (census.md "台子入口与读数来源"): the counter lines a check declared (DISPLAY_COUNTER, read off an
archived frame by counters.read; a line it could not read is None), the frame's mission second (wall time x the
rate, paused stretches left out: harness.Session.second), its logic frame when ra3ext runs (harness.ext_frame; else
absent) and the frame's archive id (the PNG's number). Nothing else is read here: a thing's position, health, orders
are not published by the bench, and the port's other calls have no channel (census.md lists each).

Pieces:
- `Contract`: what one fixed bench map publishes -- its counter lines in display order (each the script counter's
  name and the label the check gave it), the things bound by name (template, owner: static, from the mission), a
  thing's presence line where the map publishes one (a counter that reads > 0 while it lives; 0 before it first
  reads > 0 is "not here yet", not a death), and the ending rule
  where the map reports its end through a counter;
- `Sample`: one accepted reading, read only: where it came from (source, run, archive id), the mission second, the
  logic frame (or MISSING), the values (MISSING where not read), which lines it covers, and whether it moved the
  clock on (`fresh`; a repeat of the frame before is no new sample: the driver ticks once per fresh one);
- `GameObserve`: the observation port's shape over the latest sample -- `t`, `fps`, `frame()`, `counters()`,
  `thing(name)`, `living()`, `is_thing(v)`, `ending()`, `human`; any other port call raises Unsupported;
- references: `thing(name)` hands a `GameThing` whose `serial` is a `Ref` (run, name, generation). A bound thing's
  generation goes up each time its presence line comes back after reading 0 (a thing made again under its name, the
  map's own respawn); `GameAdapter.resolve(ref)` refuses (StaleRef) a reference of another run, of an earlier
  generation, or of a thing that reads gone: a new thing under an old name never takes an old reference's place;
- the transport: every read the adapter makes goes through one `call(ask) -> answer` (asks and answers are JSON
  data). `Replay(transcript)` answers from a recorded transcript and refuses an ask that is not the next recorded one
  (order and arguments both); `Recorder(call)` wraps a live one and keeps the transcript. The game process and the
  MCP stay behind the transport (bench side); `transcript_from_archive` makes a transcript from an archived run
  (index.json + its PNGs), the readings the bench took then.

A sample is refused (SampleError) when it is a menu frame (the walk's or the pause menu's: no HUD to read), has no
mission second, goes back in time (frame or second), or comes after the ending was read; a frame skipped over is
delivered as it is (`skipped`: logic frames between it and the sample before)."""
import dataclasses
import json
import os

FPS = 15                                # the game's logic rate (engine/modules/aura.py; the bench's speed-up keeps it)
SAMPLE = 'sample'                       # the one ask of step 1: the next reading


class _Missing:
    """A value the bench did not read. It is no number: using it as one raises NotRead (a plug-in that needs it
    must check `is MISSING` first) -- a reading never falls back to a default without saying so."""
    _one = None

    def __new__(cls):
        if cls._one is None:
            cls._one = super().__new__(cls)
        return cls._one

    def __repr__(self):
        return 'MISSING'

    def _refuse(self, *_):
        raise NotRead('the bench did not read this value')

    __bool__ = __int__ = __float__ = __index__ = __lt__ = __le__ = __gt__ = __ge__ = _refuse
    __add__ = __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = __truediv__ = __mod__ = __neg__ = _refuse

    def __eq__(self, other):
        return other is self

    def __hash__(self):
        return id(self)


class NotRead(ValueError):
    """A MISSING value used as a number."""


MISSING = _Missing()


class Unsupported(LookupError):
    """A port call or a field the bench has no channel for (census.md)."""


class StaleRef(LookupError):
    """A thing reference that no longer names what it named (another run, an earlier generation, a thing gone)."""


class SampleError(ValueError):
    """A reading that cannot be a sample (a menu frame, no clock, the clock going back, after the ending)."""


class TranscriptError(AssertionError):
    """A replay asked for something other than the next recorded ask, or past the transcript's end."""


@dataclasses.dataclass(frozen=True)
class Line:
    counter: str                        # the script counter's name (what counters() is keyed by, as in a sim run)
    label: str                          # what the check called it (the HUD line's label; cnv_result's header)


@dataclasses.dataclass(frozen=True)
class Bound:
    name: str                           # the object's name in the map
    template: str
    owner: str                          # the player's name
    presence: str = ''                  # a counter that reads > 0 while it lives ('' : the map publishes none)


@dataclasses.dataclass(frozen=True)
class Ending:
    counter: str                        # the map reports its end by this counter reaching `value`
    value: int
    how: str                            # '赢' / '输'
    why: str


@dataclasses.dataclass(frozen=True)
class Group:
    """A selection route: the player's things the map stands together at the start, and the world box that selects
    exactly them there. The bench reads no positions, so the box holds only till the group is first ordered."""
    name: str
    members: tuple                      # bound names
    box: tuple                          # (x0, y0, x1, y1) world


@dataclasses.dataclass(frozen=True)
class Goal:
    """A receipt route: the map counts a group's members inside a square (`counter` reads `done` when all are in)."""
    group: str
    x: float
    y: float
    half: float
    counter: str
    done: int

    def holds(self, x, y):
        return abs(x - self.x) <= self.half and abs(y - self.y) <= self.half


@dataclasses.dataclass(frozen=True)
class Contract:
    mod: str
    human: str
    lines: tuple                        # Line, in the HUD's order (top to bottom)
    things: tuple = ()                  # Bound
    ending: Ending | None = None        # None: the map does not report its end (ending() is Unsupported)
    view: tuple | None = None           # where the mission puts the camera (bench_view): world clicks need it
    groups: tuple = ()                  # Group
    goals: tuple = ()                   # Goal

    def __post_init__(self):
        names = [ln.counter for ln in self.lines]
        if len(set(names)) != len(names):
            raise ValueError(f'{self.mod}: a counter line twice')
        for b in self.things:
            if b.presence and b.presence not in names:
                raise ValueError(f'{b.name}: presence line {b.presence!r} is not one of the lines')
        if self.ending is not None and self.ending.counter not in names:
            raise ValueError(f'ending counter {self.ending.counter!r} is not one of the lines')
        for g in self.groups:
            for m in g.members:
                if self.bound(m) is None:
                    raise ValueError(f'group {g.name}: {m!r} is not a bound thing')
        for g in self.goals:
            if g.counter not in names or self.group(g.group) is None:
                raise ValueError(f'goal of {g.group}: its counter {g.counter!r} or its group is not the contract one')

    def bound(self, name):
        return next((b for b in self.things if b.name == name), None)

    def group(self, name):
        return next((g for g in self.groups if g.name == name), None)


# The fixed bench map of the first acceptance: CampFormSS (experimental/cnv/checks/engine_formation_player.py,
# engine_formation_sync `s`, bench D 94). Two groups of the player on the probe map's pace lanes, each two Guardian
# tanks (roles 0, 1) and two Peacekeepers (2, 3); the bench box-selects each group and right-clicks its goal (a plain
# move). Its four lines: per lane +1 a tank in the goal square (half 70 round (1000, lane)), +10 a Peacekeeper (22 =
# all four in; set to 0 each frame first, so a level, not a sum), and the frames a tank of the lane is in while
# neither Peacekeeper is. All eight are bound; the map publishes no presence line for them, nor an ending. The boxes
# and goals are the check's own (box X0 - 90 .. X0 + 40, lane +- 55; the click at (X1, lane)), the view the mission's.
_LANES = (('plain', 'Plain', 1230.0), ('formation', 'Formation', 1390.0))
FORMSS = Contract(
    mod='CampFormSS', human='Player_1',
    lines=(Line('CNV_Form_Plain', 'plain'), Line('CNV_Form_Formation', 'formation'),
           Line('CNV_Form_Plain_Ahead', 'plain 坦克先到帧'), Line('CNV_Form_Formation_Ahead', 'formation 坦克先到帧')),
    things=tuple(Bound(f'UNIT - CNV Form {t} {k}', 'CNV_FormTank' if k < 2 else 'CNV_FormMan', 'Player_1')
                 for _, t, _ in _LANES for k in range(4)),
    view=(825.0, 1300.0),
    groups=tuple(Group(g, tuple(f'UNIT - CNV Form {t} {k}' for k in range(4)), (560.0, y - 55, 690.0, y + 55))
                 for g, t, y in _LANES),
    goals=tuple(Goal(g, 1000.0, y, 70.0, f'CNV_Form_{t}', 22) for g, t, y in _LANES))


@dataclasses.dataclass(frozen=True)
class Sample:
    source: str                         # 'archive' (a transcript made from an archived run) or 'live'
    run: str                            # the run's archive folder name
    seq: int                            # this sample's number in the run, from 1
    archive_id: int                     # the archived frame (PNG) it was read off
    second: float                       # estimated mission seconds (the bench's clock: 0.1 s)
    frame: object                       # the logic frame (ra3ext), or MISSING
    values: tuple                       # one per contract line: int, or MISSING
    covers: frozenset                   # the counters this sample read
    fresh: bool                         # the clock moved on since the sample before (a repeat is not fresh)
    skipped: object                     # logic frames between this and the sample before (MISSING without frames)
    note: str = ''


@dataclasses.dataclass(frozen=True)
class Ref:
    run: str
    name: str
    generation: int


@dataclasses.dataclass(frozen=True)
class GameThing:
    """A bound thing as the bench sees it: name, template, owner (static), `serial` its reference. The port's other
    thing fields are not read on the bench: MISSING (any other attribute: AttributeError, as on a sim thing)."""
    name: str
    template: str
    owner: str
    serial: Ref
    alive: object                       # True / False off its presence line, MISSING without one

    UNREAD = ('x', 'y', 'z', 'hp', 'max_hp', 'health', 'angle', 'team', 'speed', 'target', 'goal', 'status')

    def __getattr__(self, field):
        if field in GameThing.UNREAD:
            return MISSING
        raise AttributeError(field)


class Replay:
    """A transport answering from a recorded transcript: each ask must be the next recorded one, exactly."""

    def __init__(self, transcript):
        self.meta = {k: v for k, v in transcript.items() if k != 'calls'}
        self._calls = list(transcript['calls'])
        self._at = 0

    def call(self, ask):
        if self._at >= len(self._calls):
            raise TranscriptError(f'ask {ask!r} after the transcript\'s {len(self._calls)} calls')
        rec = self._calls[self._at]
        if rec['ask'] != ask:
            raise TranscriptError(f'call {self._at + 1}: asked {ask!r}, the transcript has {rec["ask"]!r}')
        self._at += 1
        return rec['answer']

    def left(self):
        return len(self._calls) - self._at


class Recorder:
    """A transport wrapping a live one (`call(ask) -> answer`), keeping every ask and answer as a transcript."""

    def __init__(self, call, **meta):
        self._call = call
        self.transcript = dict(meta, calls=[])

    def call(self, ask):
        answer = self._call(ask)
        self.transcript['calls'].append(dict(ask=ask, answer=answer))
        return answer

    def save(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.transcript, f, ensure_ascii=False, indent=1)


class GameAdapter:
    """One game run read through a transport, sample by sample (`step`), as the observation port (`observe`)."""

    def __init__(self, contract, transport, run, source='archive'):
        self.contract, self.transport, self.run, self.source = contract, transport, run, source
        self.sample = None
        self.ended = None                   # (how, second, why) once the ending reads
        self._gen = {b.name: 1 for b in contract.things}
        self._gone = {b.name: False for b in contract.things}
        self._seen = set()                  # the bound things whose presence line has read > 0
        self.observe = GameObserve(self)
        self.commands = GameCommands(self)

    def step(self):
        """The next sample (None: the transport has no more). SampleError for a reading that cannot be one."""
        answer = self.transport.call(sample_ask(self.contract))
        if answer is None:
            self.commands.close()
            return None
        return self.take(answer)

    def take(self, answer):
        """An archived frame's record (a sample's, or an input's pause record) as the next sample."""
        if self.ended is not None:
            raise SampleError(f'archive frame {answer.get("id")}: a sample after the ending ({self.ended[1]} s)')
        if answer.get('menu'):
            raise SampleError(f'archive frame {answer.get("id")}: a menu frame ({answer.get("note", "")}), no HUD')
        second = answer.get('second')
        if second is None:
            raise SampleError(f'archive frame {answer.get("id")}: no mission second')
        values = answer['values']
        if len(values) != len(self.contract.lines):
            raise SampleError(f'archive frame {answer["id"]}: {len(values)} values for {len(self.contract.lines)} lines')
        frame = answer.get('frame')
        frame = MISSING if frame is None else frame
        before = self.sample
        fresh, skipped = True, MISSING
        if before is not None:
            if second < before.second:
                raise SampleError(f'archive frame {answer["id"]}: second {second} before {before.second}')
            if frame is not MISSING and before.frame is not MISSING:
                if frame < before.frame:
                    raise SampleError(f'archive frame {answer["id"]}: logic frame {frame} before {before.frame}')
                fresh, skipped = frame > before.frame, max(0, frame - before.frame - 1)
            else:
                fresh = second > before.second
        vals = tuple(MISSING if v is None else v for v in values)
        covers = frozenset(ln.counter for ln, v in zip(self.contract.lines, vals) if v is not MISSING)
        self.sample = Sample(self.source, self.run, 1 if before is None else before.seq + 1, answer['id'], second,
                             frame, vals, covers, fresh, skipped, answer.get('note', ''))
        self._births()
        e = self.contract.ending
        if e is not None and self.observe.counters()[e.counter] is not MISSING \
                and self.observe.counters()[e.counter] == e.value:
            self.ended = (e.how, second, e.why)
        self.commands.receipts()
        return self.sample

    def _births(self):
        """A bound thing whose presence line reads > 0 again after reading 0 is a new thing under its name."""
        counters = self.observe.counters()
        for b in self.contract.things:
            if not b.presence or counters[b.presence] is MISSING:
                continue
            here = counters[b.presence] > 0
            if here and self._gone[b.name] and b.name in self._seen:
                self._gen[b.name] += 1          # gone after it was here: a new thing (0 before it ever was: not yet)
            if here:
                self._seen.add(b.name)
            self._gone[b.name] = not here

    def resolve(self, ref):
        """The bound thing `ref` names now; StaleRef when it names another run's, an earlier generation's, or one
        that reads gone."""
        if not isinstance(ref, Ref):
            raise TypeError(f'not a thing reference: {ref!r}')
        if ref.run != self.run:
            raise StaleRef(f'{ref.name}: a reference of run {ref.run}, this is {self.run}')
        if self.contract.bound(ref.name) is None:
            raise StaleRef(f'{ref.name}: not a thing this map binds')
        if ref.generation != self._gen[ref.name]:
            raise StaleRef(f'{ref.name}: generation {ref.generation}, made again since (now {self._gen[ref.name]})')
        if self._gone[ref.name]:
            raise StaleRef(f'{ref.name}: gone')
        return self.observe.thing(ref.name)


class GameObserve:
    """The observation port's shape over a GameAdapter's latest sample. Calls the bench has no channel for raise
    Unsupported (census.md names each one's gap)."""
    SUPPORTED = ('t', 'fps', 'frame', 'counters', 'things', 'thing', 'living', 'is_thing', 'ending', 'human')

    def __init__(self, adapter):
        self._a = adapter

    def _now(self):
        if self._a.sample is None:
            raise SampleError('no sample yet')
        return self._a.sample

    @property
    def t(self):
        return self._now().second

    @property
    def fps(self):
        return FPS

    def frame(self):
        return self._now().frame

    def counters(self):
        s = self._now()
        return {ln.counter: v for ln, v in zip(self._a.contract.lines, s.values)}

    def thing(self, name):
        b = self._a.contract.bound(name)
        if b is None:
            return None
        if b.presence:
            v = self.counters()[b.presence]
            alive = MISSING if v is MISSING else v > 0
        else:
            alive = MISSING
        return GameThing(b.name, b.template, b.owner, Ref(self._a.run, b.name, self._a._gen[b.name]), alive)

    def things(self):
        """The bound things only (the bench lists no others)."""
        return [self.thing(b.name) for b in self._a.contract.things]

    def living(self):
        if any(not b.presence for b in self._a.contract.things):
            raise Unsupported('living: the map publishes no presence line for '
                              + ', '.join(b.name for b in self._a.contract.things if not b.presence))
        out = []
        for g in self.things():
            if g.alive is MISSING:
                raise Unsupported(f'living: {g.name} not read in archive frame {self._now().archive_id}')
            if g.alive:
                out.append(g)
        return out

    @staticmethod
    def is_thing(v):
        return isinstance(v, GameThing)

    def ending(self):
        if self._a.contract.ending is None:
            raise Unsupported(f'ending: {self._a.contract.mod} does not report its end')
        self._now()
        return self._a.ended

    @property
    def human(self):
        return self._a.contract.human

    def __getattr__(self, name):
        raise Unsupported(f'{name}: no bench channel (work/re/sim_split/adapter_pack/census.md)')


# What the bench's pause record of each input says (bench_mcp.after's note), to check it is the input asked for.
NOTE = {'bench_view': 'camera set by the mission', 'bench_box': 'box select ', 'bench_click': 'right click at screen'}


class GameCommands:
    """The command port's shape for a game (step 2, plan.md 会话 2): the human player's plain group move, given as the
    bench's inputs -- the mission's camera once (bench_view, so world clicks land), the group's box (bench_box), a
    right click at the point (bench_click right) -- each answered by its pause record (an archived frame: it becomes
    the next sample). Only `move` of a whole group the contract publishes, by 'player', to a world point (`pos`, or
    `place` '@x,y' as a sim line writes one), from the group's start: the bench reads no positions, so after a group's
    move no box selects it again (a second move is refused). The box and the click are two pause records (the game
    runs between: the recorded run's 101 frames), not one resume.

    `do` keeps (ok, why): False refused (nothing sent, or nothing that orders a unit), None issued with no receipt yet
    -- never True at once. The receipt is the map's own count: a goal of the group holding the point whose counter
    reads below `done` at the click and `done` at a later sample (`sent()` then shows True). A point no goal holds,
    or a goal already reading `done`, has no receipt route: the move stays None, and the run's end says so. Attack has
    no route: no archived run right-clicks an enemy (handoff-r3 gap; recording one passes the stage gate first)."""
    KINDS = frozenset({'move'})

    def __init__(self, adapter):
        self._a = adapter
        self._sent = []                   # dict(frame, cmd, ok, why, goal)
        self._spent = {}                    # group -> its move's entry
        self._viewed = False

    @staticmethod
    def kinds():
        return GameCommands.KINDS

    @staticmethod
    def _point(cmd):
        if cmd.pos is not None:
            return float(cmd.pos[0]), float(cmd.pos[1])
        if cmd.place.startswith('@'):
            x, _, y = cmd.place[1:].partition(',')
            return float(x), float(y)
        return None

    def _group(self, cmd):
        return next((g for g in self._a.contract.groups
                     if sorted(cmd.units) == sorted(g.members)), None)

    def check(self, cmd):
        """(ok, why) before anything is sent."""
        a, c = self._a, self._a.contract
        if cmd.kind not in self.KINDS:
            if cmd.kind == 'attack':
                return False, 'attack: no route yet -- no archived bench run right-clicks an enemy'
            return False, f'{cmd.kind}: no bench route'
        if cmd.by != 'player':
            return False, f'by {cmd.by!r}: the bench plays the human player only'
        if a.sample is None:
            return False, 'no sample yet'
        if a.ended is not None:
            return False, f'after the ending ({a.ended[1]} s)'
        if c.view is None:
            return False, f'{c.mod}: the mission sets no camera for world clicks'
        if self._point(cmd) is None:
            return False, f'move to {cmd.place!r}: a world point (pos, or @x,y); the bench clicks no named place'
        g = self._group(cmd)
        if g is None:
            return False, 'move: the units are not one group the map publishes (a box selects a whole group only)'
        for m in g.members:
            b = c.bound(m)
            if b.owner != c.human:
                return False, f'{m}: not the player\'s ({b.owner})'
            if b.presence:
                v = a.observe.counters()[b.presence]
                if v is MISSING or v <= 0:
                    return False, f'{m}: not here (its presence line reads {v})'
        if g.name in self._spent:
            e = self._spent[g.name]
            if e['ok'] is None:
                return False, f'{g.name}: no blind retry -- its move at frame {e["frame"]} has no receipt'
            return False, f'{g.name}: moved at frame {e["frame"]}; the bench reads no positions, no box selects it now'
        return True, ''

    def _send(self, ask):
        """The pause record of one input, taken as the next sample; or why it is not the one asked for."""
        ans = self._a.transport.call(ask)
        if not isinstance(ans, dict) or 'id' not in ans:
            return f'{ask["tool"]}: no pause record ({ans!r})'
        if not str(ans.get('note', '')).startswith(NOTE[ask['tool']]) or ans.get('paused') is not True:
            return f'{ask["tool"]}: archive frame {ans["id"]} records {ans.get("note")!r}, paused {ans.get("paused")}'
        self._a.take(ans)
        return ''

    def do(self, cmd):
        ok, why = self.check(cmd)
        if not ok:
            frame = self._a.sample.frame if self._a.sample is not None else MISSING
            self._sent.append(dict(frame=frame, cmd=cmd, ok=False, why=why, goal=None))
            return False, why
        c, g, (x, y) = self._a.contract, self._group(cmd), self._point(cmd)
        if not self._viewed:
            off = self._send(dict(tool='bench_view', x=c.view[0], y=c.view[1]))
            if off:
                return self._refused(cmd, off)
            self._viewed = True
        x0, y0, x1, y1 = g.box
        off = self._send(dict(tool='bench_box', x0=x0, y0=y0, x1=x1, y1=y1))
        if off:
            return self._refused(cmd, off)      # no unit ordered (a selection may be left: the next box replaces it)
        boxed = self._a.sample
        off = self._send(dict(tool='bench_click', x=x, y=y, right=True))
        s = self._a.sample
        e = dict(frame=s.frame, cmd=cmd, ok=None, goal=None,
                 why=f'issued: box archive frame {boxed.archive_id} (frame {boxed.frame}), ' + (
                     f'click unsure: {off}' if off else f'click archive frame {s.archive_id} (frame {s.frame})'))
        goal = next((q for q in c.goals if q.group == g.name and q.holds(x, y)), None)
        if goal is None:
            e['why'] += '; no receipt route (the map counts no goal of the group there)'
        elif not off:
            v = self._a.observe.counters()[goal.counter]
            if v is MISSING or v >= goal.done:
                e['why'] += f'; no receipt route ({goal.counter} reads {v} at the click, not below {goal.done})'
            else:
                e['goal'] = goal
        self._sent.append(e)
        self._spent[g.name] = e
        return None, e['why']

    def _refused(self, cmd, why):
        self._sent.append(dict(frame=self._a.sample.frame, cmd=cmd, ok=False, why=why, goal=None))
        return False, why

    def receipts(self):
        """A pending move whose goal counter reads `done` in this sample is confirmed (the adapter calls it per sample)."""
        s = self._a.sample
        for e in self._sent:
            if e['ok'] is None and e['goal'] is not None:
                v = self._a.observe.counters()[e['goal'].counter]
                if v is not MISSING and v == e['goal'].done:
                    e['ok'] = True
                    e['why'] += (f'; receipt: {e["goal"].counter} reads {v} at archive frame {s.archive_id} '
                                 f'(frame {s.frame})')

    def close(self):
        """The run is over: a move still without its receipt says so (it stays None: not known, not refused)."""
        for e in self._sent:
            if e['ok'] is None and not e['why'].endswith('no receipt by the run\'s end'):
                e['why'] += '; no receipt by the run\'s end'

    def sent(self):
        """(frame, Command, ok, why) for every command given, in order (ok: True receipt, None not known, False
        refused); the frame is the click's pause record's (a refusal's: the sample's)."""
        return tuple((e['frame'], e['cmd'], e['ok'], e['why']) for e in self._sent)

    def __getattr__(self, name):
        raise Unsupported(f'{name}: no bench channel (work/re/sim_split/adapter_pack/census.md)')


def transcript_with_inputs(run_dir, contract, steps, read=None):
    """The transcript of an archived run with its inputs: `steps` the check's bench steps ([tool, args], world
    units, as build.steps hands them to the bench). A bench_watch's frames are `sample` asks; each other step is its
    own ask (args less `look`: the adapter always takes the pause record), answered by its archived frame with
    `paused` as cnv_result.txt recorded it. Each frame's note must be its step's (NOTE), every frame used once."""
    if read is None:
        read = _read_png
    with open(os.path.join(run_dir, 'index.json'), encoding='utf-8') as f:
        index = json.load(f)
    with open(os.path.join(run_dir, 'cnv_result.txt'), encoding='utf-8') as f:
        log = f.read().splitlines()
    if index['mod'] != contract.mod:
        raise ValueError(f'{run_dir}: a run of {index["mod"]}, the contract is {contract.mod}')
    n, frames, calls = len(contract.lines), list(index['frames']), []
    sample = sample_ask(contract)

    def answer(fr):
        return dict(id=fr['id'], second=fr.get('second'), frame=fr.get('frame'), note=fr.get('note', ''), menu=False,
                    values=list(read(os.path.join(run_dir, f'{fr["id"]:04d}.png'), n)))
    for tool, args in steps:
        if tool == 'bench_watch':
            while frames and str(frames[0].get('note', '')).startswith('watch'):
                calls.append(dict(ask=sample, answer=answer(frames.pop(0))))
            continue
        fr = frames.pop(0)
        if not str(fr.get('note', '')).startswith(NOTE[tool]):
            raise ValueError(f'archive frame {fr["id"]}: {fr.get("note")!r} is not a {tool}')
        line = next((x for x in log if x.startswith(f'{tool}: ') and f' frame {fr["id"]} at ' in x), '')
        ask = dict(tool=tool, **{k: v for k, v in args.items() if k != 'look'})
        calls.append(dict(ask=ask, answer=dict(answer(fr), paused=line.endswith('; paused'))))
    if frames:
        raise ValueError(f'archive frames {[fr["id"] for fr in frames]} are no step\'s')
    calls.append(dict(ask=sample, answer=None))
    return dict(mod=contract.mod, run=os.path.basename(os.path.normpath(run_dir)), source='archive', steps=steps,
                calls=calls)


def transcript_from_archive(run_dir, contract, read=None):
    """The transcript of the samples an archived run took: one `sample` ask per archived frame, in order, answered
    with that frame's id, mission second, logic frame (where ra3ext ran), note, whether it is a menu frame, and its
    counter values off the PNG (`read(path, n)`: counters.read on the image; None where a line is not read). The
    transcript ends with a `sample` answered None (no more)."""
    if read is None:
        read = _read_png
    with open(os.path.join(run_dir, 'index.json'), encoding='utf-8') as f:
        index = json.load(f)
    if index['mod'] != contract.mod:
        raise ValueError(f'{run_dir}: a run of {index["mod"]}, the contract is {contract.mod}')
    n = len(contract.lines)
    ask = sample_ask(contract)
    calls = []
    for fr in index['frames']:
        menu = fr.get('second') is None or str(fr.get('note', '')).startswith('menu:')
        values = [None] * n if menu else read(os.path.join(run_dir, f'{fr["id"]:04d}.png'), n)
        calls.append(dict(ask=ask, answer=dict(id=fr['id'], second=fr.get('second'), frame=fr.get('frame'),
                                               note=fr.get('note', ''), menu=menu, values=list(values))))
    calls.append(dict(ask=ask, answer=None))
    return dict(mod=contract.mod, run=os.path.basename(os.path.normpath(run_dir)), source='archive', calls=calls)


_COUNTERS = []


def _read_png(path, n):
    import importlib.util
    from PIL import Image
    if not _COUNTERS:
        spec = importlib.util.spec_from_file_location('counters', os.path.join(os.path.dirname(__file__), 'counters.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _COUNTERS.append(mod)
    return _COUNTERS[0].read(Image.open(path).convert('RGB'), n)


def sample_ask(contract):
    """The `sample` ask: the contract's counter lines by name, in the HUD's order -- a reading is the values of these
    lines, so a transcript answers only the contract it was read with (review 1120aa P2: an ask of the line count let
    another contract with as many lines replay the run, its readings filed under the wrong counters)."""
    return dict(tool=SAMPLE, lines=[ln.counter for ln in contract.lines])


def replay(contract, transcript):
    """A GameAdapter on a recorded transcript of a run of the contract's map (its sample asks name the lines)."""
    if transcript.get('mod') != contract.mod:
        raise TranscriptError(f'a transcript of {transcript.get("mod")!r}, the contract is {contract.mod!r}')
    return GameAdapter(contract, Replay(transcript), transcript['run'], transcript.get('source', 'archive'))


def main(argv=None):
    """record <run_dir> <out.json> [--steps steps.json]: the transcript of an archived CampFormSS run (with --steps,
    the check's bench steps as JSON [[tool, args], ...]: its inputs too)."""
    import argparse
    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument('cmd', choices=['record'])
    ap.add_argument('run_dir')
    ap.add_argument('out')
    ap.add_argument('--steps')
    a = ap.parse_args(argv)
    if a.steps:
        with open(a.steps, encoding='utf-8') as f:
            tr = transcript_with_inputs(a.run_dir, FORMSS, [tuple(s) for s in json.load(f)])
    else:
        tr = transcript_from_archive(a.run_dir, FORMSS)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(tr, f, ensure_ascii=False, indent=1)
    got = [c['answer'] for c in tr['calls'] if c['answer']]
    print(f'{len(got)} samples, {sum(None in c["values"] for c in got)} with a line not read -> {a.out}')


if __name__ == '__main__':
    main()
