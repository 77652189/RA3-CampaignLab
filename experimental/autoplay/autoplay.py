r"""The auto player's frame (ADR 0026 item 4): a level played start to end in the plan simulator by a player who sees only
what a human sees and acts only through the script verbs, so every run is also a script.

  View     what the player has in front of them, read once a decision: its own units, the enemies its units see
           (Sim.side_sees: vision, the high-ground rule, a bombarder that just fired), the ones it saw lately and has
           not looked at since (ghosts), the objectives' markers (Sim.markers: the arrows on the map), the countdowns
           on screen. It never reads a script's flag, a hidden objective, an enemy out of sight.
  Orders   the player's hands: 派 / 走 / 攻击 / 放 lines at the simulator's clock, pushed into Sim.events as parse_script
           reads them, so what the run did IS the script (`Run.lines`): the same text through Sim(script=...) plays
           the same game (`replay`), and the testbench replays it by playcheck as any plays/*.txt.
  play     one run: the simulator ticked as Sim.run does (step, a sample each whole second, the quiet check), the
           player asked for decisions every `interval()` seconds while it has the controls (Sim.input).

The players are in players.py (idle, rush, counter, card), what the briefing says in levels.py, the batch and its
statistics in batch.py. The simulator's conclusions are only as good as its rules: until the engine inventory is met
(ADR 0026) a number from here is a reference, not a verdict.

  python -I -X utf8 experimental/autoplay/autoplay.py a3 rush 1 [--script out.txt]     one run, its ending and script
"""
import argparse
import dataclasses
import importlib.util
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CNV = os.path.join(os.path.dirname(HERE), 'cnv')


def load(name, path):
    """A module by file (no sys.path edit of ours: guard G4's ceiling): the simulator's own import puts the cnv folders
    on the path, and this folder's modules are loaded here, after it, under their plain names."""
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


sim = load('sim', os.path.join(CNV, 'sim.py'))
levels = load('levels', os.path.join(HERE, 'levels.py'))
players = load('players', os.path.join(HERE, 'players.py'))
num, where = players.num, players.where

GHOST_SECS = 25.0           # an enemy last seen this long ago is no longer where the player thinks it is
GHOST_LOOKED = 120.0        # ... or a unit of the player's is this close to the spot and sees nothing there
ENDINGS = {'赢': 'win', '输': 'lose'}
NAME_BAD = ('#', ';', ' 去 ', ' 打 ', ' 在 ', ' 进 ')        # a name the script's line cannot carry


@dataclasses.dataclass
class Foe:
    """An enemy (or a thing the level calls enemy) as the player has it: where it was seen, and what a click on it shows."""
    name: str
    addr: str                   # how a script names it, '' when it has no name a line can carry
    template: str
    x: float
    y: float
    hp: float
    kinds: frozenset
    body: object                # read for what the UI shows (weapons, armour, health); never for where it is now
    live: bool                  # seen this decision (else a ghost)
    seen_at: float

    @property
    def structure(self):
        return 'STRUCTURE' in self.kinds


def attackable(b):
    """A thing the player can pick as a target: not a marker (a zone's sculpture, a signal's smoke: UNATTACKABLE or
    INERT in its KindOf), not one held out of the fight (frozen in stasis)."""
    return 'UNATTACKABLE' not in b.status and 'UNATTACKABLE' not in b.kinds and not any(k.startswith('INERT') for k in b.kinds)


class View:
    """What the player has in front of them at one moment (Sim.side_sees, markers, countdowns)."""

    def __init__(self, s, brief):
        self.s, self.brief = s, brief
        self.ghosts = {}                    # name -> Foe, last seen
        self._addr = {}
        self.t = 0.0
        self.refresh()

    def address(self, b):
        """The name a script line uses for body b ('guardian 1', or its own name), '' when none carries."""
        if b.name not in self._addr:
            s = self.s
            role = next((k for k, r in s.m.cast.items() if r.name == b.name and b.name), '')
            got = ''
            for c in (role, b.name):
                if c and not any(x in c for x in NAME_BAD) and not c.startswith(('名字含 ', '敌人 在 ')) \
                        and ((c in s.m.cast and s.m.cast[c].name == b.name) or s.bodies.get(c) is b):
                    got = c
                    break
            self._addr[b.name] = got
        return self._addr[b.name]

    def control(self):
        """The player has the controls: no scene holds the input, and the first tick has run (a scene's lock comes
        in the first tick, simproxy.SimWorld.control)."""
        return self.s.input and self.s.t > 0

    def refresh(self):
        s = self.s
        s.seen = {}                         # this moment's sight (Sim.fight clears it each tick too)
        self.t = s.t
        me = s.human
        self.mine = [b for b in s.living() if b.owner == me and not b.scenery]
        self.units = [b for b in self.mine if b.speed > 0 and 'STRUCTURE' not in b.kinds]
        self.army = [b for b in self.units if b.weapons]
        escort = {s.m.cast[r].name for r in self.brief.escort if r in s.m.cast}
        self.convoy = [b for b in s.living() if b.name in escort]       # the level drives these (an ally's, A4's trucks)
        self.foes = []
        for b in s.living():
            if b.scenery or b.owner in (me, sim.CIV) or not s.enemy(me, b.owner) or not attackable(b):
                continue
            if s.side_sees(me, b):
                f = Foe(b.name, self.address(b), b.template, b.x, b.y, b.hp, b.kinds, b, True, s.t)
                self.foes.append(f)
                self.ghosts[b.name] = f
        live = {f.name for f in self.foes}
        for name, g in list(self.ghosts.items()):
            if name in live:
                continue
            # a death out of sight is not known: a ghost stays until it is stale, or the player looked at its spot
            looked = any(math.hypot(u.x - g.x, u.y - g.y) < GHOST_LOOKED and s.sees(g.x, g.y) for u in self.units)
            if s.t - g.seen_at > GHOST_SECS or looked:
                del self.ghosts[name]
        self.old = [g for n, g in self.ghosts.items() if n not in live]       # seen lately, not in sight now

    # ---- the objectives' markers (the arrows and flags on the map)
    def markers(self):
        """[(objective, [own bodies], [(x, y) places], [enemy Foe-like (name, addr, x, y, template)])] of the objectives
        shown now: what the arrows point at. An enemy object an arrow points at is shown even in the fog."""
        s = self.s
        out = []
        for obj, names in s.markers.items():
            if s.objectives.get(obj) != 1:
                continue
            own, places, foes = [], [], []
            for n in sorted(names):
                b = s.bodies.get(n)
                if b is not None:
                    if not b.alive:
                        continue
                    if b.owner == s.human:
                        own.append(b)
                    elif s.enemy(s.human, b.owner):
                        foes.append(b)
                    continue
                p = s.waypoints.get(n)
                if p is not None:
                    places.append((float(p[0]), float(p[1])))
            out.append((obj, own, places, foes))
        return out

    def countdowns(self):
        """[(label, seconds left)] of the countdown timers on screen."""
        s = self.s
        return [(n, max(0.0, s.timers[n] - s.t)) for n in s.countdowns if n in s.timers]

    def centre(self, bodies):
        bodies = list(bodies)
        if not bodies:
            return None
        return (sum(b.x for b in bodies) / len(bodies), sum(b.y for b in bodies) / len(bodies))


class Orders:
    """The player's hands. Each order is a script line stamped with the simulator's clock and pushed into its event
    list; `lines` is the run as a script."""

    def __init__(self, s, view):
        self.s, self.view = s, view
        self.lines = []
        self.memo = {}                      # unit name -> (verb, target): the last order, not repeated while it stands
        self.skipped = 0                    # orders to a unit no script line can name

    def push(self, time, text):
        """One event at `time` (seconds, or `<flag>+<secs>`): into the simulator, as parse_script reads the line."""
        line = f'{time} {text}'
        (e,) = sim.parse_script(line)
        s = self.s
        if isinstance(e[0], tuple):
            s.anchored.append(e)
        else:
            s.events.append(e)
            s.events.sort(key=lambda x: x[0])
        self.lines.append(line)

    def now(self, text):
        self.push(num(self.s.t), text)

    def _fresh(self, b, verb, target):
        """False when b is already on this very order (a unit still under way is not told again: that resets its path)."""
        key = (verb, target)
        if self.memo.get(b.name) == key and (b.path or b.goal is not None or b.engaged):
            return False
        self.memo[b.name] = key
        return True

    def go(self, units, p, attack=True):
        """Attack-move (派) or plain move (走) each unit to the ground point p."""
        verb = '派' if attack else '走'
        for b in units:
            who = self.view.address(b)
            if not who:
                self.skipped += 1
            elif b.alive and self._fresh(b, verb, where(p)):
                self.now(f'{verb} {who} 去 {where(p)}')

    def hit(self, units, foe):
        """Each unit attacks that thing (攻击), or attack-moves to where it was seen when no line can name it."""
        for b in units:
            who = self.view.address(b)
            if not who:
                self.skipped += 1
            elif not foe.addr:
                if b.alive and self._fresh(b, '派', where((foe.x, foe.y))):
                    self.now(f'派 {who} 去 {where((foe.x, foe.y))}')
            elif b.alive and self._fresh(b, '攻击', foe.addr):
                self.now(f'攻击 {who} 打 {foe.addr}')

    def power(self, b, ability, p):
        who = self.view.address(b)
        if who:
            self.now(f'放 {who} {ability} 在 {where(p)}')


@dataclasses.dataclass
class Run:
    level: str
    personality: str
    seed: int
    outcome: str                # win / lose / timeout / stuck
    t: float                    # the mission second the run ended at
    lines: list
    lost: int                   # units of the player's that died (ice walls and scenery aside)
    left: int                   # ... and that were alive at the end
    skipped: int
    ending: str = ''            # the script that ended it
    escort_lost: int = 0        # of the units the level asks to keep alive (Brief.escort), how many died


def losses(s):
    """The player's units that died in the run (sim.Sim's death notes: a body with a lifetime of its own, scenery and
    a deletion are not losses)."""
    return sum(1 for b in s.bodies.values() if b.owner == s.human and not b.alive and not b.deleted and not b.scenery
               and b.life_end is None and b.died_at is not None)


def finish(s, level, name, seed, lines, skipped, brief=None):
    if s.ending:
        outcome, t, by = ENDINGS.get(s.ending[0], 'lose'), s.ending[1], s.ending[2]
    else:
        outcome, t, by = ('stuck' if not s.pending() else 'timeout'), s.t, ''
    escort = [s.bodies.get(s.m.cast[r].name) for r in (brief.escort if brief else ()) if r in s.m.cast]
    return Run(level, name, seed, outcome, t, lines, losses(s),
               sum(1 for b in s.bodies.values() if b.owner == s.human and b.alive and not b.scenery and b.speed > 0),
               skipped, by, sum(1 for b in escort if b is not None and not b.alive))


def tick(s):
    """One step of sim.Sim.run's loop: step, the whole second's sample, the quiet check, the clock. False: stop."""
    s.step()
    if abs(s.t - round(s.t)) < 1e-6:
        s.sample()
    if not s.pending() and s.t - s.last_change >= sim.QUIET:
        s.note('卡住', f'{sim.QUIET:g} 秒没有任何变化，也没有在等的计时、移动和剧本事件')
        return False
    s.t = round(s.t + sim.DT, 3)
    return True


def play(level, personality, seed, difficulty="normal", until=None, style=None):
    """One run of `personality` on `level`, seeded: a Run (its script in .lines)."""
    import build
    brief = levels.brief(level)
    until = brief.until if until is None else until
    m, t, _ = build.resolve(level, '')
    s = sim.Sim(m, t, difficulty, '')
    view = View(s, brief)
    out = Orders(s, view)
    rng = random.Random(f'{level}/{personality}/{seed}')
    me = players.make(personality, rng, brief, style)
    me.start(s, out)
    s.used |= {'engine model' if s.eng else 'frame rate', 'difficulty side'}
    next_at = 0.0
    while s.t <= until and s.ending is None:
        if s.t >= next_at and view.control():
            view.refresh()
            me.decide(view, out)
            next_at = s.t + me.interval()
        if not tick(s):
            break
    return finish(s, level, personality, seed, out.lines, out.skipped, brief), s


def replay(level, lines, difficulty='normal', until=None):
    """The same game from the exported script alone: (outcome, t) as the simulator's own run ends it."""
    import build
    brief = levels.brief(level)
    m, t, _ = build.resolve(level, '')
    s = sim.Sim(m, t, difficulty, '\n'.join(lines)).run(brief.until if until is None else until)
    return (ENDINGS.get(s.ending[0], 'lose'), s.ending[1]) if s.ending else ('none', s.t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('level')
    ap.add_argument('personality')
    ap.add_argument('seed', type=int, nargs='?', default=1)
    ap.add_argument('--level-difficulty', default='normal', dest='diff', choices=list(sim.LEVELS))
    ap.add_argument('--script', default='', help='write the run as a script (the testbench plays it back) here')
    ap.add_argument('--replay', action='store_true', help='play the exported script again and compare')
    a = ap.parse_args()
    run, s = play(a.level, a.personality, a.seed, a.diff)
    print(f'{a.level} {a.personality} #{a.seed}: {run.outcome} {sim.mmss(run.t)} ({run.ending}); '
          f'lost {run.lost}, alive {run.left}, {len(run.lines)} orders, {run.skipped} not nameable')
    if a.script:
        os.makedirs(os.path.dirname(os.path.abspath(a.script)), exist_ok=True)
        with open(a.script, 'w', encoding='utf-8') as f:
            f.write(f'# autoplay {a.level} {a.personality} #{a.seed}: {run.outcome} {sim.mmss(run.t)}\n')
            f.write('\n'.join(run.lines) + '\n')
    if a.replay:
        again = replay(a.level, run.lines, a.diff)
        same = again[0] == run.outcome and abs(again[1] - run.t) < 1e-6 or run.outcome in ('timeout', 'stuck')
        print(f'replay: {again[0]} {sim.mmss(again[1])} -> {"same" if same else "DIFFERENT"}')


if __name__ == '__main__':
    main()
