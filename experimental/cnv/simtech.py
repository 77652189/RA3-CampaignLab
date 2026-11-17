r"""Protocols (PlayerTech) and protocol points, per player: what the scripts PLAYER_SET_MAX_PLAYER_POWER_POINTS /
PLAYER_SET_PLAYER_POWER_POINTS / PLAYER_LOCK_PLAYER_TECH change and PLAYER_HAS_COMPARISON_POWER_POINTS /
PLAYER_HAS_PLAYER_TECH ask, as the game keeps them (read from the program; the engine line's notes, not public).

A player of a playable faction (Allies, Soviet, Japan) has a protocol book; a civilian or neutral one has none (the
scripts' actions skip it, its conditions read false). The book:
  owned    protocols held: the faction's DefaultTech and rank 1's from the start, a rank's own on reaching it, the
           ones bought (buy)
  locked   PLAYER_LOCK_PLAYER_TECH's set (on: in, off: out). The game's buy itself does not look at it; what does
           is the AI's choice and the purchase screen -- so a locked protocol cannot be bought by a player
  points   to spend; starts at the faction's InitialTechPoints (1), before any script
  earned   every point a rank gave (the cap counts these, not points: spending or setting points does not move it)
  cap      PLAYER_SET_MAX_PLAYER_POWER_POINTS's value; none at first (-1). 0: no rank gives a point and no rank
           experience comes in any more (the campaign's usual "no protocols this mission")
  xp, rank rank experience: TechRankPointsPerSecond (1) a mission second, while there is a next rank and
           earned < cap; at the rank's ExperiencePointsToNextRank (360) the next rank is reached (the rest kept),
           its protocols given and its TechPointsGranted (1) added -- clipped to the cap, the protocols given anyway
PLAYER_SET_PLAYER_POWER_POINTS(n) is the game's own odd rule: points = n, except where a cap of 1 or more is set
and points + n (the old points) would pass it: then points = cap. A cap of 0 does not limit it.
A computer player spends its points as soon as it can (ai_buy; a campaign one too, its AI not woken: bench 11-08),
by its personality's lottery (read from the program): from frame 10, while it has points, every frame, the
personality's <PowerChoice PlayerPower Weight> lines it may buy now (cost, not held, dependencies held, not locked) in
file order; a draw uniform in [0, their weights' sum) is walked down the lines, the one it falls in bought -- one a
frame; a sum of 0 buys nothing (DefaultPersonality and HuntPersonality have no PowerChoice: they never buy). The
lines add up through inheritFrom, parents first (INFERRED, as the AI model's lists); Weight's default 20% (the XSD).
A retail mission's own personality (AIP_..., its map's assets, not in the SDK) cannot be read: its faction's
<Faction>SoloBasePersonality stands in (INFERRED; the bench's AIP_A03_Soviet02BaseMarshall did spend its point).
Where the draw falls (DRAW): the program takes it from the logic random stream, and a single-player game seeds that
stream with 0 (Generals InitRandom(0); RA3 INFERRED), so a mission draws the same every run. The simulator cannot
replay the stream, so it walks a fixed fraction DRAW of the sum. Bench 11-09 (checks/engine_aipower.py e, a Soviet
computer player, two 1-point lines): 50/50 either order -> the first listed, 7 runs of 7; X 30% first / Y 70% -> X;
X 10% / Y 90% -> Y. So there draw / sum lies in [0.1, 0.3), not "the heaviest line"; DRAW = 0.2 is that bracket's
middle (INFERRED for other missions: the stream's position at frame 10 is their own).
Not modelled: experience from kills (not found in the program), the red alert's multiplier (1.0 / 1.5 / 2.0 at
yellow / orange / red; the simulator has no red alert), what a protocol does once held.
"""
import functools
import os
import re

import simunits

INITIAL_CAP = -1
AI_FROM = 10                    # the first frame a computer player buys in
DRAW = 0.2                      # where the protocol draw falls, a fraction of the weights' sum (bench: [0.1, 0.3))
PLAYABLE = ('Allies', 'Soviet', 'Japan')


@functools.lru_cache(maxsize=None)
def _xml(*rel):
    with open(os.path.join(simunits.SAGEXML, *rel), encoding='utf-8', errors='replace') as f:
        return f.read()


def _texts(inner, tag):
    return [x.strip() for x in re.findall(rf'<{tag}>([^<]*)</{tag}>', inner)]


@functools.lru_cache(maxsize=None)
def ranks():
    """rank id -> (experience to the next, points it gives, protocols it gives)."""
    out = {}
    for head, inner in simunits._blocks(_xml('System', 'PlayerTechRanks.xml'), 'PlayerTechRank'):
        out[simunits._attr(head, 'id')] = (simunits._num(simunits._attr(head, 'ExperiencePointsToNextRank'), 0.0),
                                           int(simunits._num(simunits._attr(head, 'TechPointsGranted'), 0)),
                                           tuple(_texts(inner, 'TechGranted')))
    return out


@functools.lru_cache(maxsize=None)
def factions():
    """faction -> {'default', 'pps', 'initial', 'ranks': [rank id ...]} for the playable ones."""
    out = {}
    for head, inner in simunits._blocks(_xml('System', 'PlayerTemplates.xml'), 'PlayerTemplate'):
        fid = simunits._attr(head, 'id')
        if fid in PLAYABLE:
            out[fid] = dict(default=simunits._attr(head, 'DefaultTech'),
                            pps=simunits._num(simunits._attr(head, 'TechRankPointsPerSecond'), 0.0),
                            initial=int(simunits._num(simunits._attr(head, 'InitialTechPoints'), 0)),
                            ranks=_texts(inner, 'TechRank'))
    return out


@functools.lru_cache(maxsize=None)
def protocols():
    """protocol (lower case) -> (id, cost, dependencies): the campaign's (Includes/CampaignOverrides
    PlayerTechs_CAMP.xml replaces 48 of them: cost 1, a chain of dependencies) over the multiplayer ones."""
    out = {}
    for rel in (('System', 'PlayerTechs.xml'), ('Includes', 'CampaignOverrides', 'PlayerTechs_CAMP.xml')):
        for head, inner in simunits._blocks(_xml(*rel), 'PlayerTech'):
            pid = simunits._attr(head, 'id')
            old = out.get(pid.lower())
            cost = simunits._attr(head, 'TechPointsRequired')
            out[pid.lower()] = (pid, int(simunits._num(cost, 0)) if cost is not None else (old[1] if old else 0),
                                tuple(_texts(inner, 'TechDependency')))
    return out


@functools.lru_cache(maxsize=None)
def _personalities():
    """personality id (lower case) -> (inheritFrom, [(protocol, weight)]) from the SDK's SkirmishAI/Personalities."""
    out = {}
    root = os.path.join(simunits.SAGEXML, 'SkirmishAI', 'Personalities')
    for fn in sorted(os.listdir(root)):
        if not fn.lower().endswith('.xml'):
            continue
        text = _xml('SkirmishAI', 'Personalities', fn)       # (_blocks would stop the head at a child's '/>')
        for head, inner in re.findall(r'<AIPersonalityDefinition\b([^>]*)>(.*?)</AIPersonalityDefinition>', text, re.S):
            pid = simunits._attr(head, 'id')
            if pid:
                lines = [(simunits._attr(h, 'PlayerPower'), _weight(simunits._attr(h, 'Weight')))
                         for h, _ in simunits._blocks(inner, 'PowerChoice')]
                out[pid.lower()] = (simunits._attr(head, 'inheritFrom'), lines)
    return out


def _weight(v):
    """A PowerChoice Weight ('200%' -> 2.0); none: the XSD's default 20%."""
    v = (v or '20%').strip()
    return simunits._num(v[:-1], 20.0) / 100.0 if v.endswith('%') else simunits._num(v, 0.2)


SOLO_BASE = {'Allies': 'alliedsolobasepersonality', 'Soviet': 'sovietsolobasepersonality',
             'Japan': 'japansolobasepersonality'}


def power_choices(personality, faction=None):
    """A personality's PowerChoice lines [(protocol, weight)] through its inheritFrom chain, parents first. One the
    SDK does not have (a retail map's own AIP_...), or none given: its faction's SoloBasePersonality's (INFERRED)."""
    table = _personalities()
    key = str(personality or '').split(':')[-1].lower()
    if key not in table:
        key = SOLO_BASE.get(faction, '')
    chain = []
    while key and key in table and key not in chain:
        chain.append(key)
        key = (table[key][0] or '').lower()
    return [line for k in reversed(chain) for line in table[k][1]]


@functools.lru_cache(maxsize=None)
def power_needs(power):
    """(its RequiredPlayerTech lower or None, [its GameDependency RequiredObject lower]) of a SpecialPowerTemplate
    (GlobalData/SpecialPowerTemplates.xml; inheritFrom followed); None for a name that is no template."""
    blocks = _power_blocks()
    tech, objs, key, seen = None, [], power.lower(), set()
    if key not in blocks:
        return None
    while key in blocks and key not in seen:
        seen.add(key)
        b = blocks[key]
        head = b.split('>', 1)[0]
        t = re.search(r'RequiredPlayerTech="([^"]+)"', head)
        tech = tech or (t.group(1).lower() if t else None)
        objs = objs or [o.lower() for o in _texts(b, 'RequiredObject')]
        parent = re.search(r'inheritFrom="([^"]+)"', head)
        key = parent.group(1).lower() if parent else ''
    return tech, objs


@functools.lru_cache(maxsize=None)
def _power_blocks():
    text = _xml('GlobalData', 'SpecialPowerTemplates.xml')
    out = {}                                # split at each opening tag: some templates close themselves (/>)
    for part in text.split('<SpecialPowerTemplate')[1:]:
        m = re.match(r'\s+id="([^"]+)"', part)
        if m:
            out[m.group(1).lower()] = part
    return out


def faction_of(name, props=None):
    """A player's faction: its SidesList playerFaction where the map gives it (retail), else by its name (ours:
    Player_1 the Allies, Soviet_N, Japan_N / Empire_N); None for a civilian or neutral one (no book)."""
    f = str((props or {}).get('playerFaction', ''))
    if f:
        f = f.split(':', 1)[-1]
        return f if f in PLAYABLE else None
    low = name.lower()
    if low.startswith('soviet'):
        return 'Soviet'
    if low.startswith(('japan', 'empire')):
        return 'Japan'
    if low.startswith(('player', 'allied', 'allies')):
        return 'Allies'
    return None


class Book:
    def __init__(self, faction, fps=15, personality=None):
        f = factions()[faction]
        self.faction, self.fps = faction, fps
        self.choices = power_choices(personality, faction)     # a computer player's lottery (ai_buy)
        self.rank_ids = f['ranks']
        self.pps = f['pps']
        self.points = self.earned = f['initial']
        self.cap = INITIAL_CAP
        self.xp, self.rank = 0.0, 0
        self.owned = {f['default'].lower()} if f['default'] else set()
        self.locked = set()
        self.log = []                       # (frame, what): ranks reached, points given, bought
        self.owned |= {p.lower() for p in ranks()[self.rank_ids[0]][2]} if self.rank_ids else set()

    # ---- the scripts
    def set_cap(self, n):
        self.cap = int(n)

    def set_points(self, n):
        n = int(n)
        self.points = n if self.cap < 1 or self.points + n <= self.cap else self.cap

    def lock(self, name, on):
        key = name.lower()
        if key not in protocols():
            return False                    # not a protocol: the game ignores it
        (self.locked.add if on else self.locked.discard)(key)
        return True

    def has(self, name):
        return name.lower() in self.owned

    # ---- time
    def grows(self):
        return self.rank + 1 < len(self.rank_ids) and (self.cap < 0 or self.earned < self.cap)

    def frame(self, frame, mult=1.0):
        """One logic frame's rank experience (the game adds rate x multiplier a frame); ranks reached at once."""
        if not self.grows():
            return
        self.xp += self.pps * mult / self.fps
        while self.rank + 1 < len(self.rank_ids):
            need = ranks()[self.rank_ids[self.rank]][0]
            if need <= 0 or self.xp + 1e-9 < need:     # 360 x (1 / 15) summed: reached in frame 5400 (bench)
                break
            self.xp -= need
            self.rank += 1
            self.reach(frame)

    def reach(self, frame):
        _, pts, gives = ranks()[self.rank_ids[self.rank]]
        if self.cap >= 0:
            if self.cap <= self.earned:
                pts = 0
            elif self.cap > 0 and self.points + pts > self.cap:
                pts = self.cap - self.points
        self.points += pts
        self.earned += pts
        self.owned |= {p.lower() for p in gives}
        self.log.append((frame, f'军衔 {self.rank + 1}' + (f'，协议点 +{pts}' if pts else '')))

    # ---- the player
    def can_buy(self, name):
        """Whether a player may buy it: known, not held, not locked, its dependencies held, the points there."""
        p = protocols().get(name.lower())
        return bool(p) and p[0].lower() not in self.owned and p[0].lower() not in self.locked and \
            all(d.lower() in self.owned for d in p[2]) and p[1] <= self.points

    def ai_buy(self, frame):
        """A computer player's purchase (the program: from frame 10, while points != 0, one a frame, among the
        personality's PowerChoice lines it can buy -- not held, not locked, dependencies held, affordable): the one
        DRAW x their weights' sum falls in, in file order; nothing when the sum is 0. Bench 11-08 engine_protocol
        ailock: an unlocked campaign computer player's starting point is gone at once, a fully locked one keeps it;
        11-09 engine_aipower: equal weights -> the first listed, 30/70 -> the first, 10/90 -> the second."""
        if frame < AI_FROM or self.points == 0:
            return False
        lines = [(p, w) for p, w in self.choices if p and self.can_buy(p)]
        total = sum(w for _, w in lines)
        if total <= 0:
            return False
        r = DRAW * total                    # the game's draw: the same every run (seed 0); DRAW from the bench
        for p, w in lines:
            r -= w
            if r < 0:
                return self.buy(p, frame)
        return False

    def buy(self, name, frame=0):
        if not self.can_buy(name):
            return False
        pid, cost, _ = protocols()[name.lower()]
        self.points -= cost
        self.owned.add(pid.lower())
        self.log.append((frame, f'买 {pid}（-{cost}）'))
        return True
