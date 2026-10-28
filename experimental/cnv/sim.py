r"""The plan simulator: a level's timeline and ending in seconds, without the game (user 2026-10-27: "把策划案模拟器做
完整，先把开发效率提升上去，最后再把游戏实际和策划案模拟器对齐").

It runs the mission as built -- parts.merged(mission, check): the scripts the compiler wrote (plan.py and the
devices), the objectives' reveal scripts, a check's own -- the way the game runs a map's scripts: every tick each
active script in order, all its conditions true, its actions at once (later scripts see them in the same tick), a
once-script then off. The world is what those scripts ask about: named objects and their owners, health, positions;
flags, counters, timers; objectives; the border, reveals, the camera. Units move along the map's walkable ground
(water for ships, both for amphibians, a straight line for aircraft) at their game speed (simunits.py), routed on the
map's own height field. Combat is not simulated: the player's side of it is a script of events (SCRIPT below) --
"60 派 tank 去 north camp", "120 摧毁 north barracks", "90 血量 yuriko 1". Whatever the engine does that the
simulator only guesses at is listed (ALIGN, and each run's 'guessed' lines): the bench settles those last.

  python -I -X utf8 experimental/cnv/sim.py <level> [--check <check>] [--script <file or "t 动作 ...; ...">]
                                             [--level easy|normal|hard] [--until <seconds>]

A script (剧本), one event a line (or ';' between them), times in seconds or m:ss:
  <t> 派 <谁> 去 <地点>     move (a map site, a mark, a trigger area, a named object)
  <t> 摧毁 <谁>             destroyed (killed by the player)
  <t> 删除 <谁>             gone without dying
  <t> 血量 <谁> <百分比>     health set
  <t> 打 <谁>               attacked by the player (NAMED_ATTACKED_BY_PLAYER)
  <t> 占领 <谁>             now the player's
  <t> 旗标 <名字> <值>       a flag set outright (a check's or a device's)
  <t> 造 <单位> 在 <地点> [角度]  the player makes one (a unit id of the mission's, a cast part's template, a retail
                            template): an engineer's ice -- '40 造 CNV_IceWall 在 inside 1 1.57'
  自动打掉 <秒>             every enemy that has been that long within REACH (300) of something of the player's is
                            destroyed (the player fights back where the enemy comes to them)
  <谁>: a cast part ('yuriko'), a group of them ('tank' = tank 1, tank 2 ...), an object's name, 名字含 <text>
  (every object whose name holds it: '名字含 W1-' a plan's first wave), 敌人 在 <地点> (the enemy's there).
"""
import argparse
import dataclasses
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import parts  # noqa: E402
import simunits  # noqa: E402

DT = 0.5                        # seconds a tick
UNTIL = 1800.0                  # a run stops here at the latest (30 minutes)
QUIET = 120.0                   # nothing pending this long and no ending: stuck
CIV = 'PlyrCivilian'
CMP = {0: lambda a, b: a < b, 1: lambda a, b: a <= b, 2: lambda a, b: a == b, 3: lambda a, b: a >= b,
       4: lambda a, b: a > b, 5: lambda a, b: a != b}
WON, LOST = 'Mission Won', 'Mission Lost'
LEVELS = {'easy': 0, 'normal': 1, 'hard': 2}
NEAR = 800.0                    # an enemy this close to something of the player's is a threat (the tension curve)
REACH = 300.0                   # 自动打掉: an enemy this close to something of the player's is being fought
GRID = 20.0                     # routing cells (world units)
LAG = 0.0                       # the readings' clock: mission seconds. A check's own expectations count the bench's
                                # seconds, which run behind by no fixed lag (~8 s after the menus, more where the game
                                # runs slow: j7 win ends at mission 10 and was read at bench 10) -- so the simulator's
                                # versions of the checks carry their own expectations (simchecks.py)

# what the simulator assumes of the engine and the bench has not settled ("待对齐清单"): printed with every run that
# leans on one of them
ALIGN = {
    'timer unset': 'TIMER_EXPIRED of a timer never set: taken as false',
    'destroyed unborn': 'NAMED_DESTROYED / NAMED_NOT_DESTROYED of a named object not (yet) made: both false',
    'deleted': 'NAMED_DELETE: counted as destroyed by NAMED_DESTROYED (not by the player: no NAMED_ATTACKED)',
    'kind all players': 'PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA counts every player\'s objects, the '
                        'scenery\'s buildings and fences too (bench 2026-10-25 probe/count; "清空某地也算建筑")',
    'units in area': 'SKIRMISH_PLAYER_HAS_UNITS_IN_AREA: any object of that player, buildings too',
    'discovered': 'NAMED_DISCOVERED: inside the player\'s sight (vision / shroud range) or a reveal; on the bench '
                  '2026-10-27 (sight look) it read 1 for every target, 400 off too -- unsettled',
    'special power': 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT / NAMED_USE_COMMANDBUTTON_ABILITY: logged, no effect '
                     '(a jump, a carrier\'s drop: the device\'s own scripts say what follows)',
    'ai': 'a skirmish AI (UNIT_AI_TRANSFER_ALL, SKIRMISH_AI_*): woken and logged; what it builds and when it '
          'attacks is not simulated (bench 2026-10-27 aistep: it may never build a kind it is let to)',
    'attack': 'NAMED_ATTACK_NAMED: the attacker goes to its target; the fight is the script\'s (摧毁)',
    'guard': 'UNIT_GUARD_AREA: goes to the area\'s middle and stays',
    'bridge deck': 'a bridge is walkable deck from its start to its end object (BRIDGE_DECK wide); bench '
                   '2026-10-27 (reroute): a wall on a deck stops nobody',
    'health of the dead': 'SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER of a dead object: 0',
    'no combat': 'nobody fights: an enemy that reaches the player hurts nothing; a level that is won by holding out '
                 'is won by doing nothing -- its losses come only from the script (摧毁 / 血量)',
}

# actions that change nothing the scripts ask about: logged on the timeline (the player sees or hears them)
SHOWN = {'SHOW_MILITARY_CAPTION': '通报', 'CAMPAIGN_CREATE_AUTO_SAVE': '存档', 'PATH_MUSIC_PLAY_EVENT': '音乐',
         'PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM': '战况音乐', 'NAMED_FLASH': '闪烁'}
IGNORED = {'PLAYER_SET_MAX_PLAYER_POWER_POINTS', 'PLAYER_SET_PLAYER_POWER_POINTS', 'DISPLAY_COUNTER', 'HIDE_COUNTER',
           'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES',
           'SKIRMISH_AI_USE_REPAIRS', 'SKIRMISH_AI_USE_REBUILD_SYSTEM', 'CAMERA_LETTERBOX_BEGIN', 'CAMERA_LETTERBOX_END',
           'NAMED_SET_MAX_HEALTH'}


@dataclasses.dataclass
class Body:
    """An object in the simulated world."""
    name: str
    template: str
    owner: str
    x: float
    y: float
    speed: float = 0.0
    surface: str = 'ground'
    vision: float = 0.0
    kinds: frozenset = frozenset()
    health: float = 100.0
    alive: bool = True
    deleted: bool = False
    path: list = dataclasses.field(default_factory=list)       # world points still to go
    goal: object = None                                         # what it is after: a point, or a Body (attack)
    close_since: float = None                                   # an enemy: since when it is within REACH of the
                                                                # player's (自动打掉)
    made_by: str = ''                                           # the script that created it
    made_at: float = 0.0
    attacked: set = dataclasses.field(default_factory=set)     # players that attacked it
    scenery: bool = False
    team: str = ''
    guessed: list = dataclasses.field(default_factory=list)    # what of its numbers simunits only guessed
    angle: float = 0.0
    dest: object = None                                         # where it was sent (rerouted when the way changes)
    status: set = dataclasses.field(default_factory=set)       # IMMOBILE (stays put), UNATTACKABLE (the player
                                                                # cannot destroy it) ...


def inside(pts, x, y):
    """Point in polygon (even-odd)."""
    c, n = False, len(pts)
    for k in range(n):
        (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def mmss(t):
    return f'{int(t // 60)}:{int(t % 60):02d}'


def seconds(s):
    s = str(s).strip()
    if ':' in s:
        m, sec = s.split(':')
        return 60 * float(m) + float(sec)
    return float(s)


class Ground:
    """The map's routing grids (GRID cells): ground (dry, not too steep, bridges over), water, both; paths by
    least cost, cached per surface and goal cell."""

    def __init__(self, mapmod):
        import platmap
        dims = platmap.CONTAINER
        w, h, b = dims
        if hasattr(mapmod, 'LAYOUT'):
            e, _ = platmap.heights(mapmod.LAYOUT, w, h, b)
            walk = platmap.walkable(mapmod.LAYOUT, getattr(mapmod, 'OBJECTS', []), dims, e)
        else:
            e = mapmod.ground().e
            import newmap
            walk = (e > newmap.WATERLINE + 10) & (platmap.slope_of(e) <= platmap.STEEP)
        import newmap
        water = e < newmap.WATERLINE - 5
        d = int(GRID // platmap.CELL)
        hh, ww = h // d, w // d
        fold = lambda a: a[:hh * d, :ww * d].reshape(hh, d, ww, d)            # noqa: E731
        self.b, self.d = b, d
        self.grids = {'ground': fold(walk).all(axis=(1, 3)), 'water': fold(water).all(axis=(1, 3))}
        self.grids['both'] = self.grids['ground'] | self.grids['water'] | fold(walk | water).all(axis=(1, 3))
        self.cache = {}
        self.blocked = np.zeros(self.grids['ground'].shape, bool)
        self.version = 0
        # a bridge's deck: what stands on it blocks nobody (bench 2026-10-27, reroute: the warriors walked through an
        # ice wall on the deck)
        self.deck = np.zeros_like(self.blocked)
        objs = list(getattr(mapmod, 'OBJECTS', []))
        jj, ii = np.mgrid[0:self.blocked.shape[0], 0:self.blocked.shape[1]]
        self.xy = self.world((jj, ii))
        for o, q in zip(objs, objs[1:]):
            if getattr(o, 'flags', None) == platmap.BRIDGE_START and getattr(q, 'flags', None) == platmap.BRIDGE_END:
                self.deck |= self.strip((o.x, o.y), (q.x, q.y), platmap.BRIDGE_DECK, 0.0)

    def strip(self, p, q, width, over):
        """Cells within width / 2 of segment p-q, the segment `over` longer at both ends."""
        x, y = self.xy
        dx, dy = q[0] - p[0], q[1] - p[1]
        n = max(math.hypot(dx, dy), 1e-6)
        ux, uy = dx / n, dy / n
        u = (x - p[0]) * ux + (y - p[1]) * uy
        v = -(x - p[0]) * uy + (y - p[1]) * ux
        return (u >= -over) & (u <= n + over) & (abs(v) <= width / 2)

    def set_blocks(self, shapes):
        """What stands in the way now: [(x, y, angle, length, thick) a bar, or (x, y, r) a round building]; off a
        bridge's deck. Routes are worked out anew."""
        x, y = self.xy
        m = np.zeros_like(self.blocked)
        for s in shapes:
            if len(s) == 3:
                m |= (x - s[0]) ** 2 + (y - s[1]) ** 2 <= s[2] ** 2
            else:
                cx, cy, a, length, thick = s
                u = (x - cx) * math.cos(a) + (y - cy) * math.sin(a)
                v = -(x - cx) * math.sin(a) + (y - cy) * math.cos(a)
                m |= (abs(u) <= length / 2) & (abs(v) <= thick / 2)
        m &= ~self.deck
        if (m != self.blocked).any():
            self.blocked, self.version, self.cache = m, self.version + 1, {}
            return True
        return False

    def cell(self, x, y):
        import platmap
        return (int(round((y / platmap.CELL + self.b) / self.d)), int(round((x / platmap.CELL + self.b) / self.d)))

    def world(self, c):
        import platmap
        return ((c[1] * self.d - self.b) * platmap.CELL, (c[0] * self.d - self.b) * platmap.CELL)


    def snap(self, g, c):
        if 0 <= c[0] < g.shape[0] and 0 <= c[1] < g.shape[1] and g[c]:
            return c
        jj, ii = np.nonzero(g[max(0, c[0] - 15):c[0] + 16, max(0, c[1] - 15):c[1] + 16])
        if not len(jj):
            return None
        k = int(np.argmin((jj + max(0, c[0] - 15) - c[0]) ** 2 + (ii + max(0, c[1] - 15) - c[1]) ** 2))
        return (int(jj[k] + max(0, c[0] - 15)), int(ii[k] + max(0, c[1] - 15)))

    def route(self, surface, p, q):
        """World points from p to q (None: no way); aircraft fly straight."""
        if surface == 'air':
            return [q]
        from skimage import graph
        g = self.grids[surface] & ~self.blocked
        a, z = self.snap(g, self.cell(*p)), self.snap(g, self.cell(*q))
        if a is None or z is None:
            return None
        key = (surface, z)
        if key not in self.cache:
            m = graph.MCP_Geometric(np.where(g, 1.0, np.inf))
            cost, _ = m.find_costs([z])
            self.cache[key] = (m, cost)
        m, cost = self.cache[key]
        if not np.isfinite(cost[a]):
            return None
        cells = m.traceback(a)[::-1]
        pts = [self.world(c) for c in cells[::-1]]
        return pts[1::3] + [q] if len(pts) > 3 else [q]


class Sim:
    def __init__(self, mission, test=None, level='normal', script=''):
        self.m = mission
        self.mm = parts.merged(mission, test)
        self.test = test
        self.level = LEVELS[level]
        self.t = 0.0
        self.log = []                       # (t, kind, text)
        self.used = set()                   # ALIGN keys the run leaned on
        self.unknown = {}                   # condition / action names the simulator does not know: count
        self.flags, self.counters, self.timers = {}, {}, {}
        self.objectives = {}                # name -> status (0 hidden, 1 shown, 2 done, 3 failed)
        self.markers = {}                   # objective -> {object / waypoint}
        self.done, self.disabled = set(), set()
        self.border = 0
        self.reveal_all = False
        self.reveals = {}                   # name -> (x, y, r)
        self.peeks = []                     # (x, y, r): a reveal that is not permanent (taken as for this tick on)
        self.camera = None
        self.input = True
        self.countdowns = set()
        self.ending = None
        self.last_change = 0.0
        self.ai = {}                        # player -> woken at
        self.money = {}
        self.relations = {}
        self.players = dict(mission.map.PLAYERS)
        self.human = self.players['p1']
        self.foe = self.players.get('s1')
        self.ground = Ground(mission.map)
        self.own = {u.id: u.xml for u in self.mm.units}
        self.bodies = {}                    # name -> Body (named ones), plus unnamed under '#k'
        self.series = []                    # (t, counter values) for a check's counters
        self.threat = []                    # (t, enemies near, countdowns) every 10 s
        self.first_threat = None
        self.known = None                   # cells ever seen (GRID)
        self.known_at = []                  # (t, km2 known)
        self.guessed = set()
        self.walls = {u.id: u.params for u in self.mm.units if 'length' in u.params}   # our bars of ice, gates
        teams = getattr(mission.map, 'TEAMS', {})
        for k, o in enumerate(list(getattr(mission.map, 'OBJECTS', [])) + self.mm.objects):
            b = self.add(o.name or f'#{k}', o.template, self.owner_of(o.side), o.x, o.y)
            b.team = teams.get(o.side, '')
            b.angle = o.angle or 0.0
        import platprops
        for k, o in enumerate(getattr(mission.map, 'SCENERY', [])):
            if o.template in platprops.STRUCTURE:
                b = self.add(f'#scenery {k}', o.template, CIV, o.x, o.y)
                b.scenery = True
                b.kinds = frozenset(b.kinds | {'STRUCTURE'})
        self.script = parse_script(script)
        self.auto_kill = next((e[2] for e in self.script if e[1] == '自动打掉'), None)
        self.events = sorted((e for e in self.script if e[0] is not None), key=lambda e: e[0])
        self.areas = self.mm.areas
        self.waypoints = self.mm.waypoints
        self.reblock()

    def blocks(self, b):
        """What of the way a body takes up: a wall of ours its bar (or disc, square), a building its round."""
        if b.template in self.walls:
            p = self.walls[b.template]
            if p.get('shape') == 'disc':
                return (b.x, b.y, p['length'] / 2)
            return (b.x, b.y, b.angle, p['length'], p['length'] if p.get('shape') == 'square' else p['thick'])
        if 'STRUCTURE' in b.kinds and 'bridge' not in b.template.lower():
            import platprops
            return (b.x, b.y, platprops.radius(b.template) if b.template in platprops.CATALOG else 40.0)
        return None

    def reblock(self):
        """The way as it stands now; whoever is on the move takes it anew."""
        shapes = [s for s in (self.blocks(b) for b in self.living()) if s]
        if self.ground.set_blocks(shapes):
            for b in self.living():
                if b.path and b.dest is not None:
                    self.send(b, b.dest)

    # ---- the world
    def owner_of(self, side):
        return self.players.get(side, CIV)

    def add(self, name, template, owner, x, y, by='', at=0.0):
        st = simunits.stats(template, self.own)
        b = Body(name, template, owner, float(x), float(y), st['speed'], st['surface'],
                 max(st['vision'] or 0.0, st['shroud'] or 0.0), frozenset(st['kinds']), made_by=by, made_at=at)
        b.guessed = st['guessed']
        self.bodies[name] = b
        return b

    def living(self):
        return [b for b in self.bodies.values() if b.alive]

    def enemy(self, a, b):
        """Player a takes player b as an enemy."""
        if (a, b) in self.relations:
            return self.relations[(a, b)] == 'Enemy'
        return {a, b} == {self.human, self.foe} or (a != b and CIV not in (a, b) and self.human in (a, b)
                                                   and (a in self.ai or b in self.ai))

    def point(self, name):
        """A waypoint, a trigger area's middle, a site, a mark, a named object."""
        if name in self.waypoints:
            return self.waypoints[name]
        if name in self.areas:
            pts = self.areas[name]
            return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        if name in self.m.marks:
            return self.waypoints[self.m.marks[name]]
        sites = getattr(self.m.map, 'SITES', {})
        if name in sites:
            return (sites[name].x, sites[name].y)
        if name in self.bodies:
            return (self.bodies[name].x, self.bodies[name].y)
        return None

    def note(self, kind, text):
        self.log.append((self.t, kind, text))

    def change(self):
        self.last_change = self.t

    def send(self, b, target, by=''):
        if b.guessed:                               # its speed matters now: say when it is only a guess
            self.guessed.add(f'{b.template}: {", ".join(b.guessed)}')
        if not b.alive or b.speed <= 0:
            return
        p = self.point(target) if isinstance(target, str) else target
        if p is None:
            return
        path = self.ground.route(b.surface, (b.x, b.y), p)
        b.dest = p
        if path is None:
            self.note('卡住', f'{self.label(b)} 到不了 {target if isinstance(target, str) else "目标"}'
                              f'（{b.surface} 没有路）')
            b.path = []
            return
        b.path = path
        self.change()

    def label(self, b):
        role = next((k for k, r in self.m.cast.items() if r.name == b.name and b.name), '')
        return role or b.name or b.template

    def destroy(self, b, why, delete=False):
        if not b.alive:
            return
        b.alive, b.deleted, b.path = False, delete, []
        b.health = 0.0 if not delete else b.health
        self.note('删除' if delete else '摧毁', f'{self.label(b)}（{why}）')
        self.change()
        if self.blocks(b):
            self.reblock()

    # ---- conditions
    def holds(self, c):
        c = list(c)
        neg = c and c[-1] == parts.NOT
        if neg:
            c = c[:-1]
        v = self.cond(c[0], c[1:])
        return (not v) if neg else v

    def body(self, name):
        return self.bodies.get(name)

    def cond(self, name, a):
        if name == 'FLAG':
            return int(self.flags.get(a[0], 0)) == int(a[1])
        if name == 'TIMER_EXPIRED':
            if a[0] not in self.timers:
                self.used.add('timer unset')
                return False
            return self.t >= self.timers[a[0]]
        if name == 'COUNTER':
            return CMP[a[1]](self.counters.get(a[0], 0), a[2])
        if name in ('NAMED_DESTROYED', 'NAMED_NOT_DESTROYED'):
            b = self.body(a[0])
            if b is None:
                self.used.add('destroyed unborn')
                return False
            if b.deleted:
                self.used.add('deleted')
            return (not b.alive) if name == 'NAMED_DESTROYED' else b.alive
        if name in ('NAMED_INSIDE_AREA', 'NAMED_OUTSIDE_AREA'):
            b = self.body(a[0])
            return bool(b and b.alive and inside(self.areas[a[1]], b.x, b.y) == (name == 'NAMED_INSIDE_AREA'))
        if name == 'PLAYER_HAS_OBJECT_COMPARISON':
            n = sum(1 for b in self.living() if b.owner == a[0] and b.template.lower() == a[3].lower())
            return CMP[a[1]](n, a[2])
        if name == 'PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA':
            n = sum(1 for b in self.living() if b.owner == a[0] and b.template.lower() == a[3].lower()
                    and inside(self.areas[a[4]], b.x, b.y))
            return CMP[a[1]](n, a[2])
        if name == 'PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA':
            self.used.add('kind all players')
            kind = a[3][2] if isinstance(a[3], tuple) else a[3]
            n = sum(1 for b in self.living() if kind in b.kinds and inside(self.areas[a[4]], b.x, b.y))
            return CMP[a[1]](n, a[2])
        if name == 'SKIRMISH_PLAYER_HAS_UNITS_IN_AREA':
            self.used.add('units in area')
            return any(b.owner == a[0] and not b.scenery and inside(self.areas[a[1]], b.x, b.y) for b in self.living())
        if name == 'NAMED_OWNED_BY_PLAYER':
            b = self.body(a[1])
            return bool(b and b.alive and b.owner == a[0])
        if name == 'NAMED_ATTACKED_BY_PLAYER':
            b = self.body(a[0])
            return bool(b and a[1] in b.attacked)
        if name == 'UNIT_HEALTH':
            b = self.body(a[0])
            return bool(b and b.alive and CMP[a[1]](b.health, a[2]))
        if name == 'NAMED_DISCOVERED':
            self.used.add('discovered')
            b = self.body(a[1])
            return bool(b and self.sees(b.x, b.y))
        if name == 'CAMERA_ENTERED_AREA':
            return bool(self.camera and inside(self.areas[a[0]], *self.camera))
        self.unknown[name] = self.unknown.get(name, 0) + 1
        return False

    def sees(self, x, y):
        if self.reveal_all:
            return True
        if any(math.hypot(x - rx, y - ry) <= r for rx, ry, r in list(self.reveals.values()) + self.peeks):
            return True
        return any(b.owner == self.human and math.hypot(b.x - x, b.y - y) <= b.vision for b in self.living())

    # ---- actions
    def act(self, name, a, script):
        if name == 'SET_FLAG':
            if int(self.flags.get(a[0], 0)) != int(a[1]):
                self.flags[a[0]] = int(a[1])
                self.change()
                if a[0] == WON and a[1]:
                    self.end('赢', script)
                elif a[0] == LOST and a[1]:
                    self.end('输', script)
        elif name == 'SET_COUNTER':
            self.counters[a[0]] = a[1]
        elif name in ('INCREMENT_COUNTER', 'DECREMENT_COUNTER'):
            self.counters[a[1]] = self.counters.get(a[1], 0) + (a[0] if name == 'INCREMENT_COUNTER' else -a[0])
            self.change()
        elif name == 'SET_MILLISECOND_TIMER':
            self.timers[a[0]] = self.t + float(a[1])
            self.change()
        elif name in ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION'):
            p = self.point(a[3])
            if p is None:
                return
            old = self.bodies.get(a[0])
            if old and old.alive:
                return                                  # one object to a name (the game makes no second)
            b = self.add(a[0], a[1], a[2].split('/')[0], *p, by=script.name, at=self.t)
            b.team = a[2]
            b.angle = float(a[4]) if len(a) > 4 else 0.0
            if self.blocks(b):
                self.reblock()
            self.note('出现', f'{self.label(b)}（{a[1]}，{self.who(b.owner)}）在 {a[3]}'
                      + ('' if b.owner == self.human or self.sees(b.x, b.y) else '，玩家看不见'))
            self.change()
        elif name in ('MOVE_NAMED_UNIT_TO', 'ATTACK_MOVE_NAMED_UNIT_TO'):
            b = self.body(a[0])
            if b:
                self.send(b, a[1])
        elif name == 'NAMED_ATTACK_NAMED':
            self.used.add('attack')
            b, target = self.body(a[0]), self.body(a[1])
            if b and target and target.alive and b.alive and b.goal is not target:
                b.goal = target
                self.send(b, (target.x, target.y))
        elif name == 'UNIT_GUARD_AREA':
            self.used.add('guard')
            b = self.body(a[0])
            if b and not inside(self.areas[a[1]], b.x, b.y):
                self.send(b, a[1])
        elif name == 'NAMED_STOP':
            b = self.body(a[0])
            if b:
                b.path, b.goal = [], None
        elif name == 'UNIT_TELEPORT_TO_WAYPOINT':
            b, p = self.body(a[0]), self.point(a[1])
            if b and p:
                b.x, b.y, b.path = p[0], p[1], []
                self.change()
        elif name == 'NAMED_TRANSFER_OWNERSHIP_PLAYER':
            b = self.body(a[0])
            if b and b.owner != a[1]:
                b.owner = a[1]
                self.note('易主', f'{self.label(b)} 归 {self.who(a[1])}')
                self.change()
        elif name in ('NAMED_KILL', 'NAMED_DELETE'):
            b = self.body(a[0])
            if b:
                self.destroy(b, '脚本' if name == 'NAMED_KILL' else '脚本删掉', delete=name == 'NAMED_DELETE')
        elif name == 'UNIT_SET_HEALTH':
            b = self.body(a[0])
            if b:
                b.health = float(a[1])
        elif name == 'UNIT_CHANGE_OBJECT_STATUS':
            b = self.body(a[0])
            st = a[1][2] if isinstance(a[1], tuple) else a[1]
            if b:
                (b.status.add if a[2] else b.status.discard)(st)
        elif name == 'SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER':
            b = self.body(a[0])
            if b:
                self.used.add('health of the dead')
                self.counters[a[1]] = int(round(b.health)) if b.alive else 0
        elif name == 'SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER':
            self.counters[a[2]] = sum(1 for b in self.living() if b.owner == a[1] and
                                      b.template.lower() == a[0].lower())
        elif name == 'SET_PLAYER_MONEY_TO_COUNTER':
            self.counters[a[1]] = int(self.money.get(a[0], 0))
        elif name == 'PLAYER_SET_MONEY':
            self.money[a[0]] = a[1]
        elif name == 'PLAYER_GIVE_MONEY':
            self.money[a[0]] = self.money.get(a[0], 0) + a[1]
        elif name == 'NAMED_GARRISON_SPECIFIC_BUILDING':
            b = self.body(a[0])
            if b and self.body(a[1]):
                self.send(b, a[1])
        elif name == 'ATTACK_MOVE_TEAM_TO':
            for b in self.living():
                if b.team == a[0]:
                    self.send(b, a[1])
        elif name == 'SET_MISSION_OBJECTIVE_STATUS':
            old = self.objectives.get(a[0], 0)
            self.objectives[a[0]] = a[1]
            if a[1] != old and a[1]:
                g = next((g for g in self.m.objectives if g.name == a[0]), None)
                title = self.text(g.title) if g else a[0]
                self.note('目标', f'{"奖励" if g and g.bonus else ""}目标{["", "亮出", "完成", "失败"][a[1]]}：{title}')
                self.change()
        elif name in ('LINK_MISSION_OBJECTIVE_TO_OBJECT', 'LINK_MISSION_OBJECTIVE_TO_WAYPOINT'):
            s = self.markers.setdefault(a[0], set())
            (s.add if a[2] else s.discard)(a[1])
        elif name == 'ALLOW_DISALLOW_ONE_BUILDING':
            pass                                        # production: the AI's and the player's, not simulated
        elif name == 'PLAYER_RELATES_PLAYER':
            self.relations[(a[0], a[1])] = a[2]
        elif name in ('UNIT_AI_TRANSFER_ALL', 'SKIRMISH_AI_MAKE_BASE'):
            self.used.add('ai')
            if a[0] not in self.ai:
                self.ai[a[0]] = self.t
                self.note('AI', f'{self.who(a[0])} 交给遭遇战 AI（造兵、进攻不模拟）')
        elif name == 'MAP_SWITCH_BORDER':
            self.border = int(a[0])
            names = list(getattr(self.m.map, 'BORDERS', {}))
            self.note('边界', f'可玩区换成 {names[self.border] if self.border < len(names) else self.border}')
            self.change()
        elif name in ('MAP_REVEAL_ALL', 'MAP_REVEAL_ALL_PERM'):
            self.reveal_all = True
            self.note('揭图', '全图')
        elif name == 'MAP_REVEAL_ALL_UNDO_PERM':
            self.reveal_all = False
            self.note('揭图', '全图收回')
        elif name in ('MAP_REVEAL_PERMANENTLY_AT_WAYPOINT', 'MAP_REVEAL_AT_WAYPOINT'):
            p = self.point(a[0])
            if p:
                if name == 'MAP_REVEAL_AT_WAYPOINT':
                    self.peeks.append((p[0], p[1], float(a[1])))
                else:
                    self.reveals[a[3]] = (p[0], p[1], float(a[1]))
                self.note('揭图', f'{a[0]} 半径 {a[1]:g}')
        elif name == 'MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT':
            self.reveals.pop(a[0], None)
        elif name in ('MOVE_CAMERA_TO', 'MOVE_CAMERA_TO_NAMED', 'CAMERA_FOLLOW_NAMED'):
            p = self.point(a[0])
            if p:
                self.camera = p
                self.note('镜头', f'到 {a[0]}')
        elif name in ('DISABLE_INPUT', 'ENABLE_INPUT'):
            self.input = name == 'ENABLE_INPUT'
            self.note('过场', '交还控制' if self.input else '锁住操作')
        elif name == 'DISPLAY_COUNTDOWN_TIMER':
            if a[0] not in self.countdowns:
                self.countdowns.add(a[0])
                left = self.timers.get(a[0], self.t) - self.t
                self.note('倒计时', f'{self.text(a[1])} {mmss(max(0.0, left))}')
        elif name == 'HIDE_COUNTDOWN_TIMER':
            self.countdowns.discard(a[0])
        elif name in ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'NAMED_USE_COMMANDBUTTON_ABILITY'):
            self.used.add('special power')
            self.note('技能', f'{a[0]} 用 {a[1]}' + (f' 打 {a[2]}' if len(a) > 2 else ''))
        elif name in ('ENABLE_SCRIPT', 'DISABLE_SCRIPT'):
            (self.disabled.discard if name == 'ENABLE_SCRIPT' else self.disabled.add)(a[0])
        elif name in SHOWN:
            text = self.text(a[0]) if isinstance(a[0], str) else str(a[0])
            self.note(SHOWN[name], text)
        elif name in IGNORED or name == 'CAMERA_STOP_FOLLOW':
            pass
        else:
            self.unknown[name] = self.unknown.get(name, 0) + 1

    def text(self, key):
        return self.mm.strings.get(key, key)

    def who(self, player):
        if player == self.human:
            return '玩家'
        side = next((s for s, p in self.players.items() if p == player), player)
        return {'s1': '敌人'}.get(side, side)

    def end(self, how, script):
        if self.ending is None:
            self.ending = (how, self.t, script.name)
            self.note('结局', f'{how}（{script.name}）')

    # ---- the player's script
    def pick(self, who):
        """The bodies a script event names."""
        who = who.strip()
        if who.startswith('名字含 '):
            part = who[4:].strip()
            return [b for b in self.living() if part in b.name]
        if who.startswith('敌人 在 '):
            p = self.point(who[5:].strip())
            sites = getattr(self.m.map, 'SITES', {})
            r = sites[who[5:].strip()].r if who[5:].strip() in sites and sites[who[5:].strip()].r else 400.0
            return [b for b in self.living() if p and self.enemy(self.human, b.owner) and not b.scenery
                    and math.hypot(b.x - p[0], b.y - p[1]) <= r]
        names = [self.m.cast[who].name] if who in self.m.cast else \
            [r.name for k, r in self.m.cast.items() if re.fullmatch(re.escape(who) + r' \d+', k)]
        if not names and who in self.bodies:
            names = [who]
        out = [self.bodies[n] for n in names if n in self.bodies]
        if not out:
            self.note('剧本', f'找不到 {who}（还没出现，或者不是角色、物体名）')
        return out

    def happen(self, e):
        t, verb, *rest = e
        self.note('剧本', ' '.join([verb] + [str(x) for x in rest]))
        if verb == '派':
            who, where = rest
            for b in self.pick(who):
                self.send(b, where)
        elif verb in ('摧毁', '删除'):
            for b in self.pick(rest[0]):
                if verb == '摧毁' and 'UNATTACKABLE' in b.status:
                    self.note('剧本', f'{self.label(b)} 打不动（UNATTACKABLE），没摧毁')
                    continue
                b.attacked.add(self.human)
                self.destroy(b, '剧本', delete=verb == '删除')
        elif verb == '血量':
            for b in self.pick(rest[0]):
                b.health = float(rest[1])
                b.attacked.add(self.human)
        elif verb == '打':
            for b in self.pick(rest[0]):
                b.attacked.add(self.human)
        elif verb == '占领':
            for b in self.pick(rest[0]):
                b.owner = self.human
        elif verb == '旗标':
            self.flags[rest[0]] = int(rest[1])
        elif verb == '造':
            what, where, angle = rest
            tmpl = next((u.id for u in self.mm.units if u.id == what), None) or \
                next((r.template for k, r in self.m.cast.items() if k == what), what)
            p = self.point(where)
            if p is None:
                self.note('剧本', f'找不到地点 {where}')
            else:
                b = self.add(f'UNIT - SIM Made {len(self.bodies)}', tmpl, self.human, *p, by='剧本', at=self.t)
                b.angle = angle
                if self.blocks(b):
                    self.reblock()
        self.change()

    # ---- running
    def step(self):
        while self.events and self.events[0][0] <= self.t:
            self.happen(self.events.pop(0))
        for s in self.mm.scripts:
            if s.name in self.done or s.name in self.disabled or not s.levels[self.level]:
                continue
            if all(self.holds(c) for c in s.when):
                for name, *a in s.do:
                    self.act(name, a, s)
                if s.once:
                    self.done.add(s.name)
            if self.ending:
                return
        self.move()

    def move(self):
        for b in self.living():
            if isinstance(b.goal, Body):
                g = b.goal
                if not g.alive:
                    b.goal, b.path = None, []
                elif not b.path or math.hypot(b.path[-1][0] - g.x, b.path[-1][1] - g.y) > 150:
                    if int(self.t / DT) % 8 == 0:                    # re-aimed every 4 s
                        self.send(b, (g.x, g.y))
            if not b.path or 'IMMOBILE' in b.status:
                continue
            left = b.speed * DT
            while left > 0 and b.path:
                tx, ty = b.path[0]
                d = math.hypot(tx - b.x, ty - b.y)
                if d <= left:
                    b.x, b.y, left = tx, ty, left - d
                    b.path.pop(0)
                else:
                    b.x += (tx - b.x) * left / d
                    b.y += (ty - b.y) * left / d
                    left = 0
            self.change()
        if self.auto_kill is not None:
            mine = [b for b in self.living() if b.owner == self.human]
            for b in self.living():
                if not self.enemy(self.human, b.owner) or b.scenery or b.speed <= 0 or 'UNATTACKABLE' in b.status:
                    continue
                close = any(math.hypot(b.x - o.x, b.y - o.y) <= REACH for o in mine)
                b.close_since = (b.close_since if b.close_since is not None else self.t) if close else None
                if close and self.t - b.close_since >= self.auto_kill:
                    b.attacked.add(self.human)
                    self.destroy(b, f'自动打掉：在玩家 {REACH:g} 以内 {self.auto_kill:g} 秒')

    def sample(self):
        """Every second: a check's counters; every 10: the threat; every 30: what the player has seen."""
        if self.test and self.test.counters and self.t >= LAG:
            self.series.append((int(round(self.t - LAG)), [self.counters.get(c, 0) for c, _ in self.test.counters]))
        if int(round(self.t)) % 10 == 0:
            mine = [b for b in self.living() if b.owner == self.human]
            near = [b for b in self.living() if self.enemy(self.human, b.owner) and not b.scenery and b.speed > 0
                    and any(math.hypot(b.x - o.x, b.y - o.y) <= NEAR for o in mine)]
            self.threat.append((self.t, len(near), len(self.countdowns)))
            if near and self.first_threat is None:
                b = min(near, key=lambda b: b.made_at)
                self.first_threat = (self.t, b)
                self.used.add('no combat')
        if int(round(self.t)) % 30 == 0:
            self.see()

    def see(self):
        g = self.ground.grids['both'] | self.ground.grids['ground'] | ~self.ground.grids['both']
        if self.known is None:
            self.known = np.zeros(g.shape, bool)
            jj, ii = np.mgrid[0:g.shape[0], 0:g.shape[1]]
            self._xy = self.ground.world((jj, ii))
        x, y = self._xy
        if self.reveal_all:
            self.known[:] = True
        for rx, ry, r in list(self.reveals.values()) + self.peeks:
            self.known |= (x - rx) ** 2 + (y - ry) ** 2 <= r * r
        for b in self.living():
            if b.owner == self.human and b.vision:
                self.known |= (x - b.x) ** 2 + (y - b.y) ** 2 <= b.vision ** 2
        self.peeks = []
        rect = list(getattr(self.m.map, 'BORDERS', {'': (0, 0, 1e9, 1e9)}).values())
        x0, y0, x1, y1 = rect[self.border] if self.border < len(rect) else rect[0]
        inb = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
        self.known_at.append((self.t, round(float((self.known & inb).sum()) * GRID * GRID / 1e6, 2)))

    def pending(self):
        """Something still to come: a timer running, a unit moving, a script event."""
        return bool(self.events) or any(v > self.t for v in self.timers.values()) or \
            any(b.path for b in self.living())

    def run(self, until=UNTIL):
        while self.t <= until and self.ending is None:
            self.step()
            if abs(self.t - round(self.t)) < 1e-6:
                self.sample()
            if not self.pending() and self.t - self.last_change >= QUIET:
                self.note('卡住', f'{QUIET:g} 秒没有任何变化，也没有在等的计时、移动和剧本事件')
                break
            self.t = round(self.t + DT, 3)
        if self.ending and self.test and self.test.counters:   # the counters go with the mission
            self.series += [(int(self.t - LAG) + k, [None] * len(self.test.counters)) for k in range(1, 4)]
        return self

    # ---- the report
    def ending_line(self):
        if self.ending:
            how, t, by = self.ending
            return f'结局：{how}，{mmss(t)}（{by}）'
        head = f'结局：{mmss(self.t)} 内没有结束' if self.pending() else \
            f'结局：卡住，{mmss(self.t)} 以后什么都不会再发生'
        return head + '；还差：' + '；'.join(self.missing())

    def missing(self):
        """What each ending (win / lose script) still waits for: its conditions false now."""
        out = []
        for s in self.mm.scripts:
            if s.name in self.m.endings and s.levels[self.level]:
                false = [c for c in s.when if not self.holds(c)]
                out.append(f'{s.name} ← ' + ', '.join(describe(c) for c in false))
        return out or ['（这一关没有写输赢）']

    def report(self, every=False):
        """The ending, the timeline (units made in one tick folded into one line, a line said again and again
        given once with how often), the measures, what the run assumed."""
        out = [self.ending_line()]
        if every:
            out += [f'{mmss(t)} [{k}] {x}' for t, k, x in self.log]
        else:
            rows, made, again = [], {}, {}
            for t, k, x in self.log:
                if k == '出现':
                    if t not in made:
                        made[t] = []
                        rows.append([t, k, made[t]])
                    made[t].append(x)
                elif (k, x) in again:
                    again[(k, x)].append(t)
                else:
                    again[(k, x)] = [t]
                    rows.append([t, k, x])
            for t, k, x in rows:
                if k == '出现':
                    out.append(f'{mmss(t)} [出现] {len(x)} 个：{x[0]}' + ('……' if len(x) > 1 else ''))
                    continue
                ts = again[(k, x)]
                more = f'（又 {len(ts) - 1} 次，到 {mmss(ts[-1])}）' if len(ts) > 1 else ''
                out.append(f'{mmss(t)} [{k}] {x}{more}')
        out.append(self.metrics())
        if self.used:
            out.append('待对齐（这次推演用到的假设）：' + '；'.join(ALIGN[k] for k in sorted(self.used)))
        if self.unknown:
            out.append('不认识的条件 / 动作（当成不成立 / 没效果）：' + ', '.join(f'{k}×{v}' for k, v in self.unknown.items()))
        if self.guessed:
            out.append('数据里没有、用了默认值：' + '；'.join(sorted(self.guessed)))
        return out

    def metrics(self):
        peak = max(self.threat, key=lambda x: x[1], default=(0, 0, 0))
        curve = ' '.join(f'{mmss(t)}:{n}' for t, n, _ in self.threat if int(t) % 60 == 0)
        known = ' '.join(f'{mmss(t)}:{v:g}' for t, v in self.known_at if int(t) % 120 == 0)
        if self.first_threat:
            t, b = self.first_threat
            s = next((s for s in self.mm.scripts if s.name == b.made_by), None)
            why = f'由 {b.made_by} 造出（条件 {s.when}）' if s else '开局就在图上'
            first = f'第一股敌人 {mmss(t)} 到玩家 {NEAR:g} 以内：{self.label(b)}，{why}'
        else:
            first = '没有敌人走到玩家附近'
        return (f'张力（每分钟，玩家 {NEAR:g} 以内的敌人数）：{curve or "—"}；最高 {peak[1]} 个，{mmss(peak[0])}\n'
                f'已知区域（km²，每 2 分钟）：{known or "—"}\n{first}')


def describe(c):
    """A condition as one short line: FLAG(CNV_A4_Phase_2=1), NOT NAMED_DESTROYED(x)."""
    c = list(c)
    neg = c and c[-1] == parts.NOT
    args = [a[2] if isinstance(a, tuple) and len(a) == 3 else a for a in (c[1:-1] if neg else c[1:])]
    return ('NOT ' if neg else '') + f'{c[0]}(' + ', '.join(str(a) for a in args) + ')'


def parse_script(text):
    """Events (t, verb, args...) from a script's text; 自动打掉 as (None, '自动打掉', seconds)."""
    if text and os.path.exists(text):
        text = open(text, encoding='utf-8').read()
    out = []
    for line in re.split(r'[;\n]', text or ''):
        line = line.split('#')[0].strip()
        if not line or line == '不动':
            continue
        if line.startswith('自动打掉'):
            out.append((None, '自动打掉', seconds(line.split()[1])))
            continue
        t, rest = line.split(None, 1)
        if rest.startswith('派 '):
            who, _, where = rest[2:].rpartition(' 去 ')
            out.append((seconds(t), '派', who.strip(), where.strip()))
        elif rest.startswith('血量 '):
            who, pct = rest[3:].rsplit(None, 1)
            out.append((seconds(t), '血量', who.strip(), float(pct.rstrip('%'))))
        elif rest.startswith('旗标 '):
            name, v = rest[3:].rsplit(None, 1)
            out.append((seconds(t), '旗标', name.strip(), int(v)))
        elif rest.startswith('造 '):
            what, _, where = rest[2:].partition(' 在 ')
            angle = 0.0
            if re.fullmatch(r'-?[\d.]+', where.split()[-1]) and len(where.split()) > 1:
                where, angle = where.rsplit(None, 1)[0], float(where.split()[-1])
            out.append((seconds(t), '造', what.strip(), where.strip(), angle))
        else:
            verb, _, who = rest.partition(' ')
            if verb not in ('摧毁', '删除', '打', '占领'):
                raise ValueError(f'剧本 {line!r}: 动作是 派 / 摧毁 / 删除 / 血量 / 打 / 占领 / 旗标 / 造 之一')
            out.append((seconds(t), verb, who.strip()))
    return out


def simulate(name, check='', script='', level='normal', until=UNTIL):
    import build
    m, t, _ = build.resolve(name, check)
    return Sim(m, t, level, script).run(until)


def main():
    if sys.argv[1:] == ['--align']:             # the list of what the bench must still settle
        print('\n'.join(f'- {k}: {v}' for k, v in ALIGN.items()))
        return
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--check', default='')
    ap.add_argument('--script', default='')
    ap.add_argument('--level', default='normal', choices=list(LEVELS))
    ap.add_argument('--until', type=float, default=UNTIL)
    ap.add_argument('--all', action='store_true', help='every line of the timeline (units made one by one)')
    a = ap.parse_args()
    import simchecks
    own = simchecks.CHECKS.get((a.name, a.check)) if a.check else None
    s = simulate(a.name, a.check, a.script or (own or {}).get('script', ''), a.level, a.until)
    print('\n'.join(s.report(a.all)))
    if own and not a.script:                    # the check's simulator version: its ending, its wiring counters
        ok, lines = simchecks.run(a.name, a.check)
        print('\n'.join(['模拟器版检查：' + ('PASS' if ok else 'FAIL')] + [x for x in lines[1:]]))
        sys.exit(0 if ok else 1)
    if s.test and s.test.expect:
        import build
        lines, _ = build.report(s.test, s.series)
        print('测试台版的期望（秒数按测试台，和任务秒数差几秒，只作参考；这个检查没有模拟器版）：')
        print('\n'.join(lines))


if __name__ == '__main__':
    main()
