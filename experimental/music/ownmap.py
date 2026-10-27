"""Our own Pathfinder maps, built node by node (no retail nodes left), on top of the retail map's header, variables,
track entries and event heads: the game looks events up by name hash, so every retail event stays, with our actions.

A section here is: entry node -> segment nodes (one stream each) -> exit node, the exit going on to another
section's entry (or its own: a loop; or nowhere: stop). Events jump with the retail pair PREP + GOTO <section entry>,
or a GOTO alone. timeline(m, node, fires, seconds) says offline what the game plays when events fire.

  spy(m): every event jumps to a looping section of its own whose stream is the event's index, so a tracer
  recording says which event fired when. The section MenuTrack goes to also carries a router to every other
  section: through transition A if the node's router value v names routers[v - 1], through transition B if it names
  routers[v] (MusSpy 2026-10-25: A, v - 1; B sat in the last router, which maps then lost: pfdx docstring, routers).
  See SPY_* for the streams.
"""
import copy
from dataclasses import dataclass

from experimental.music import pfdx

TRACK = 0x11000001          # action word 0: the handle of PathMusicTrack:Track (pfdx docstring)
PREP, GOTO = 0x000F0400, 0x00030400
SET, IF, ELIF, ELSE, ENDIF = 0x000E0800, 0x009E0100, 0x00AE0100, 0x00300100, 0x00400100
ALWAYS = (0, 127)


def goto(sec, prep=False):
    """Actions: jump to `sec` (prep: PREP first, a cut at once)."""
    return [(TRACK, PREP, 0x01FFFFFF)] * prep + [(TRACK, GOTO, 0x00FF0000 | sec.entry)]


def set_var(var, value):
    """Actions: map variable `var` = value (retail: SetPlayerAllied sets variable 0, 'player', to 1)."""
    return [(TRACK, SET, value | var << 16)]


def switch(var, cases, default):
    """Actions: the first of cases {value: actions} whose value variable `var` holds, else `default` (retail's
    IF / ELIF / ELSE / ENDIF, as Combat picks the player's side)."""
    out = []
    for k, (value, acts) in enumerate(cases.items()):
        out += [(TRACK, ELIF if k else IF, var | value << 16)] + list(acts)
    return out + [(TRACK, ELSE, 0)] + list(default) + [(0xFFFFFFFF, ENDIF, 0)]


def run(actions, variables):
    """What an event's actions do (only == comparisons): sets `variables` in place, -> (jump target node or None,
    PREP or not)."""
    target, prep, stack = None, False, []           # stack: [this branch taken, one branch already taken]
    for _, op, arg in actions:
        holds = variables.get(arg & 0xFFFF, 0) == arg >> 16
        if op == IF:
            stack.append([holds, holds])
        elif op == ELIF:
            taken = not stack[-1][1] and holds
            stack[-1] = [taken, stack[-1][1] or taken]
        elif op == ELSE:
            stack[-1] = [not stack[-1][1], True]
        elif op == ENDIF:
            stack.pop()
        elif not all(s[0] for s in stack):
            continue
        elif op == SET:
            variables[arg >> 16] = arg & 0xFFFF
        elif op == PREP:
            prep = True
        elif op == GOTO:
            target = arg & 0xFFFF
    return target, prep


@dataclass
class Section:
    entry: int
    exit: int
    segments: list


class Builder:
    def __init__(self, base):
        """base: a parsed retail map; its nodes, routers, samples and event actions are dropped."""
        self.m = copy.deepcopy(base)
        self.m.nodes, self.m.routers, self.m.samples = [], [], []
        for e in self.m.events:
            e.actions = []
        self.sections = []

    def _node(self, **kw):
        self.m.nodes.append(pfdx.Node(**{**dict(w0=0, track=0, b3=0, router=0, low=0, kind=0x10, b7=1, ref=0,
                                                ref_kind=0, w12=0, branches=[]), **kw}))
        return len(self.m.nodes) - 1

    def section(self, streams, router=0):
        """A section playing `streams` (indexes into the sample table, track 0) in order; its exit leads nowhere
        until link() / loop()."""
        k = len(self.sections)
        entry = self._node(w0=0, ref=2 * k)
        segs = [self._node(w0=s + 1, kind=0x40, ref=entry, ref_kind=4, router=router) for s in streams]
        exit_ = self._node(w0=0xFFFF, ref=2 * k + 1)
        chain = [entry] + segs + [exit_]
        for a, b in zip(chain, chain[1:]):
            self.m.nodes[a].branches = [(*ALWAYS, b)]
        self.sections.append(Section(entry, exit_, segs))
        return self.sections[-1]

    def link(self, sec, to):
        self.m.nodes[sec.exit].branches = [(*ALWAYS, to.entry)]

    def loop(self, sec):
        self.link(sec, sec)

    def stop(self, sec):
        """The music stops when `sec` ends."""
        self.m.nodes[sec.exit].branches = [(*ALWAYS, 0xFFFF)]

    def on(self, event, sec, prep=True):
        """The event (retail name, or index for the few whose name is not known) jumps to `sec`; prep: with the
        retail PREP before the GOTO, a cut at once without the routers' transition; without it the jump waits for
        the playing segment's end and goes through the transition (CampMusic 2026-10-25, pfdx docstring)."""
        self.act(event, goto(sec, prep))

    def act(self, event, actions):
        """The event's actions, as written (goto / set_var / switch)."""
        e = self.m.events[event] if isinstance(event, int) else next(e for e in self.m.events if e.name == event)
        e.actions = list(actions)

    def build(self, samples):
        """samples: [(SNS offset / 0x80, ms)] for every stream, track 0's first (mus.pack tables)."""
        self.m.samples = list(samples)
        return self.m


def timeline(m, node, fires, seconds):
    """What the game plays from `node` on when events fire, by the rules measured in game (pfdx docstring, PREP):
    PREP + GOTO cuts over at once; a GOTO alone waits for the playing segment's end, then goes through the
    segment's router pair for its target if there is one. Branches: the last one (as pfdx.walk).
      fires: [(seconds, event name)]  ->  [(start s, end s, stream)], a cut segment ending early."""
    events = {e.name: e for e in m.events if e.name}
    fires = sorted(fires)
    variables = {}

    def jump(name):                     # the event's actions run when it fires (its SETs too)
        return run(events[name].actions, variables)

    def segment(i):                     # the first segment from node i on, or None (stop)
        while i != 0xFFFF:
            n = m.nodes[i]
            if n.is_segment:
                return i
            if not n.branches:
                return None
            i = n.branches[-1][2]
        return None

    out, t, k, pending = [], 0.0, 0, None
    seg = segment(node)
    while seg is not None and t < seconds:
        n = m.nodes[seg]
        end = t + m.samples[n.stream][1] / 1000
        cut = None
        while k < len(fires) and fires[k][0] < end:
            target, prep = jump(fires[k][1])
            k += 1
            if target is None:
                continue
            if prep:
                cut = (max(fires[k - 1][0], t), target)
                break
            pending = target
        if cut:
            out.append((t, cut[0], n.stream))
            t, seg, pending = cut[0], segment(cut[1]), None
            continue
        out.append((t, end, n.stream))
        t = end
        if pending is not None:
            pairs = m.routers[n.router - 1] if n.router else []
            seg = segment(next((a for a, b in pairs if b == pending), pending))
            pending = None
        else:
            seg = segment(n.branches[-1][2]) if n.branches else None
    return out


SPY_SECONDS = 4.0          # each event's section: one stream this long, looping
SPY_MENU_SECONDS = 6.0      # MenuTrack's: longer, so a jump that waits for its end is told from one at once
SPY_TRANSITION_SECONDS = 1.0


def spy(base, plain=('BriefingTrack',), seconds=None, routed=('MenuTrack',)):
    """-> (Builder, [stream lengths in ms] for track 0). Streams: event i -> i; E = len(events) is transition A,
    E + 1 transition B. Event i's section loops on stream i (SPY_SECONDS long, or seconds[name]); the sections of
    the events in `routed` have router value 2 on their segment, routers[1] (A, the one the engine reads for 2) and
    routers[2] (B) each hold one pair per section that is not routed. Events in `plain` jump without PREP (the shell
    fires BriefingTrack on entering the campaign menus, MenuTrack on coming back)."""
    b = Builder(base)
    E = len(b.m.events)
    seconds = seconds or {'MenuTrack': SPY_MENU_SECONDS}
    names = [e.name for e in b.m.events]
    secs = []
    for i in range(E):
        s = b.section([i], router=2 if names[i] in routed else 0)
        b.loop(s)
        secs.append(s)
    pairs = {'A': [], 'B': []}
    for which, stream in (('A', E), ('B', E + 1)):
        for i, target in enumerate(secs):
            if names[i] in routed:
                continue
            t = b.section([stream])
            b.link(t, target)
            pairs[which].append((t.entry, target.entry))
    b.m.routers = [[(secs[0].entry, secs[0].entry)], pairs['A'], pairs['B']]     # routers[0]: unused filler
    for i, e in enumerate(b.m.events):
        b.on(i, secs[i], prep=e.name not in plain)
    lengths = [int(seconds.get(n, SPY_SECONDS) * 1000) for n in names] + [int(SPY_TRANSITION_SECONDS * 1000)] * 2
    return b, lengths


# the jump timing probe (missions/music_bench.py fires these from the mission's scripts at known moments)
TIMING_CUT = 'S_A01BrightonThreat'          # PREP + GOTO
TIMING_PLAIN = 'S_A01BrightonCombat'        # GOTO alone, its section routed: leaving it plays transition A
TIMING_INTO = 'S_A01BrightonExplore'        # GOTO alone, reached from TIMING_PLAIN's section through A
TIMING = {'cut': TIMING_CUT, 'plain': TIMING_PLAIN, 'into': TIMING_INTO}
TIMING_SECONDS = 8.0


def timing(base):
    """spy() with the three timing events on long segments (a jump that waits for a segment's end shows), two of
    them without PREP and TIMING_PLAIN's section routed."""
    events = (TIMING_CUT, TIMING_PLAIN, TIMING_INTO)
    return spy(base, plain=('BriefingTrack', TIMING_PLAIN, TIMING_INTO),
               seconds={'MenuTrack': SPY_MENU_SECONDS, **{e: TIMING_SECONDS for e in events}},
               routed=('MenuTrack', TIMING_PLAIN))
