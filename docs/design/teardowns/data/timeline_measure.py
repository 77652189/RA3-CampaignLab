r"""What the player sees, and when: a timeline per campaign map, retail and ours, and the map re-measured at the key
moments from what the player knows by then (read only: retail archives, built mods in the Mods folder).

  python -I -X utf8 docs/design/teardowns/data/timeline_measure.py            -> timeline.json + timeline.md here
  python -I -X utf8 docs/design/teardowns/data/timeline_measure.py j02 S6     (only these; the md is rebuilt from
                                                                               the whole json)

1. Events, from the scripts' (enabled) actions: border switches; reveals (radius, permanent or not, undo); camera
   moves / follows / setups; flashes and radar events; objective status (0 hidden, 1 shown, 2 done, 3 failed) and
   marker links (third argument 1 on, 0 off); enemy spawns and dispatches (reinforcements, created units, hunt /
   attack / follow orders, skirmish-AI starts and AI transfers) and the human side's gains (reinforcements,
   ownership transfers).
2. Times: a script fires at the latest of its conditions (the earliest of its OR groups), after it is active
   (initially active, or an ENABLE_SCRIPT / its group's, or a CALL_SUBROUTINE). Condition times:
     CONDITION_TRUE, FLAG(x, 0), an inverted condition (export suffix +0100000001000000: the second u32 of the
     content's trailing bytes), NAMED_NOT_DESTROYED, a named object the player already owns -> the start ('开局');
     FLAG(x, 1) -> the earliest script setting it; TIMER_EXPIRED -> the earliest setter + its seconds
     (SET_MILLISECOND_TIMER: seconds; SET_TIMER: frames / 15; random timers: the middle, marked '≈');
     COUNTER_SECONDS(t, <, s) -> setter + seconds - s; COUNTER -> 0 already satisfies it: the start, a SET_COUNTER
     to a satisfying value: that script, increments: a new anchor 'counter reaches v';
     HAS_FINISHED_VIDEO / _AUDIO -> the script playing it + L (unknown length, never a number);
     PLAYER_IS_HUMAN_OR_AI_PERSONALITY -> single player: Player_1 human, everybody else AI;
     anything else (units in areas, objects destroyed or captured, health, sightings...) -> a new player-progress
     anchor 'P<n> <what>', whose earliest moment is the time the script began to look for it.
   Times are 'anchor + seconds (+ L ...)'. Ordering across anchors: the start < any player anchor; an anchor is
   later than its parent's anchor; unrelated anchors are not ordered (an event counts as 'already happened' at a
   moment only when its anchor is that moment's anchor or one of its ancestors).
   Difficulty: script headers [E--] / [-N-] / [--H]: the normal line is built; easy and hard only for differences.
3. Key moments (control handed back, each border switch, each objective shown, each large reveal), measured from
   the player's knowledge then:
     known      current playable rectangle ∩ (live permanent reveals ∪ one-shot reveals ∪ a 500-unit vision circle
                around the human and allied objects placed at the start, every human gain (reinforcement, transfer)
                so far, and every player-progress anchor with a place (an area entered, an object destroyed)) --
                the 500 vision radius and 'where the player has been' are approximations; whole-map or point
                reveals that are undone again by then count only as 'glimpsed'
     anchor     the player's reference point (start; later the latest gain: a handed-over base, a reinforcement):
                corner / edge / centre of the known area's bounding box (layout_measure's 0.25 rule)
     threats    enemy clusters (layout_measure.clusters of the placed enemy objects) inside the known area, and the
                origins of enemy forces already dispatched, as octants from the anchor
     goals      shown objectives, their markers: inside the known area or not (to be found); how they were pointed
                out within ±10 s of being shown (camera move, reveal, flash, radar event near a marker)
"""
import json
import math
import os
import re
import statistics
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout_measure as LM  # noqa: E402
from layout_measure import big, mapscript, mapstudy, mapterrain, mapxml, octant, OURS  # noqa: E402

OUT_JSON = os.path.join(HERE, 'timeline.json')
OUT_MD = os.path.join(HERE, 'timeline.md')
CELL = mapterrain.CELL
FPS = 15                        # RA3 logic frames per second (SET_TIMER counts frames)
L_GUESS = 15                    # seconds, only to order times that wait on an unknown video / audio length
PLAYER_GUESS = 60               # seconds, only to order times: a player-progress anchor after it is looked for
MAX_RANK = 14                   # anchors on anchors deeper than this are not followed
VISION = 500                    # approximate sight radius of the player's units
GRID = 50                       # world units per cell of the knowledge mask
POINT = 10                      # seconds: a camera / reveal / flash this close to an objective pointed at it
NEAR = 700                      # world units: a camera target / flash / radar event this close to a marker
BIG_REVEAL = 0.05               # a reveal covering this share of the playable area is a key moment
COORD3D = mapscript.COORD3D
GENERIC = ('<All Players>', '<All Human Players>', '<Local Player>')

PLAY = re.compile(r'MOVIE|SOUND|AUDIO|SPEECH|DIALOG|MUSIC')
CAMERA = {'MOVE_CAMERA_TO': 0, 'MOVE_CAMERA_TO_NAMED': 0, 'PLAYER_CAMERA_MOVE_TO': 1, 'PLAYER_CAMERA_MOVE_TO_NAMED': 1,
          'CAMERA_FOLLOW_NAMED': 0, 'PLAYER_CAMERA_TETHER_NAMED': 1, 'SETUP_CAMERA': 0, 'RESET_CAMERA': 0}
FLASH = ('NAMED_FLASH', 'NAMED_FLASH_WHITE', 'TEAM_FLASH')
RADAR = ('RADAR_CREATE_EVENT', 'OBJECT_CREATE_RADAR_EVENT', 'TEAM_CREATE_RADAR_EVENT')
TEAM_ORDERS = ('TEAM_HUNT', 'TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS', 'TEAM_FOLLOW_WAYPOINTS', 'TEAM_FOLLOW_WAYPOINTS_EXACT',
               'TEAM_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT', 'ATTACK_MOVE_TEAM_TO', 'ATTACK_MOVE_TEAM_TO_NAMED_OBJECT',
               'ATTACK_MOVE_TEAM_TO_NEAREST_OBJECT_OF_TYPE_OF_PLAYER', 'MOVE_TEAM_TO', 'TEAM_ATTACK_NAMED',
               'TEAM_ATTACK_TEAM', 'TEAM_ATTACK_MOVE_TOWARDS_NEAREST_OBJECT_TYPE', 'TEAM_MOVE_TO_NEAREST_OBJECT_OF_TYPE',
               'TEAM_CONTEXT_SENSITIVE_ATTACK', 'TEAM_AI_TRANSFER')
NAMED_ORDERS = ('NAMED_HUNT', 'NAMED_ATTACK_AREA', 'NAMED_ATTACK_FOLLOW_WAYPOINTS', 'NAMED_ATTACK_NAMED',
                'NAMED_ATTACK_TEAM', 'NAMED_FOLLOW_WAYPOINTS', 'NAMED_FOLLOW_WAYPOINTS_EXACT',
                'NAMED_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT', 'NAMED_FORCE_ATTACK_NAMED', 'NAMED_FORCE_ATTACK_WAYPOINT',
                'ATTACK_MOVE_NAMED_UNIT_TO', 'MOVE_NAMED_UNIT_TO', 'UNIT_AI_TRANSFER', 'UNIT_CONTEXT_SENSITIVE_ATTACK')
PLAYER_AI = ('SKIRMISH_AI_START', 'PLAYER_TOGGLE_SKIRMISH_AI', 'SKIRMISH_AI_TRANSFER_ALL', 'UNIT_AI_TRANSFER_ALL')
NOT_UNITS = re.compile(r'fx|prop|marker|dummy|reveal|waypoint|effect|flare|beacon|smoke|invisible', re.I)
DISCOVER = ('NAMED_DISCOVERED', 'TEAM_DISCOVERED', 'ENEMY_SIGHTED', 'ENEMY_SIGHTED_BY_TEAM', 'TYPE_SIGHTED',
            'CAMERA_ENTERED_AREA')
CN = {  # player-progress conditions in words
    'NAMED_INSIDE_AREA': '{0} 进入 {1}', 'NAMED_EXITED_AREA': '{0} 离开 {1}', 'NAMED_OUTSIDE_AREA': '{0} 在 {1} 外',
    'PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA': '{0} 的单位在 {4}', 'SKIRMISH_PLAYER_HAS_UNITS_IN_AREA': '{0} 的单位在 {1}',
    'PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA': '{0} 的单位在 {4}', 'TEAM_INSIDE_AREA_PARTIALLY': '{0} 进入 {1}',
    'TEAM_INSIDE_AREA_ENTIRELY': '{0} 全进 {1}', 'TEAM_ENTERED_AREA_PARTIALLY': '{0} 进入 {1}',
    'NAMED_DESTROYED': '{0} 被毁', 'NAMED_DYING': '{0} 将毁', 'TEAM_DESTROYED': '{0} 全灭', 'NAMED_OWNED_BY_PLAYER': '{1} 拿到 {0}',
    'NAMED_DISCOVERED': '{0} 发现 {1}', 'TEAM_DISCOVERED': '{0} 发现 {1}', 'CAMERA_ENTERED_AREA': '镜头进入 {0}',
    'NAMED_ATTACKED_BY_PLAYER': '{0} 被 {1} 攻击', 'TEAM_ATTACKED_BY_PLAYER': '{0} 被 {1} 攻击', 'UNIT_HEALTH': '{0} 血量',
    'ENEMY_SIGHTED': '{0} 看见敌人', 'BUILT_BY_PLAYER': '{1} 造出 {0}', 'NAMED_SELECTED': '选中 {0}',
    'PLAYER_HAS_OBJECT_COMPARISON': '{0} 的 {3} 数量', 'MISSION_HOT_SPOT_ACTIVE': '热点 {0}',
    'PLAYER_DESTROYED_N_BUILDINGS_PLAYER': '{0} 拆了 {2} 的建筑'}


# ---------------------------------------------------------------- reading the map
def sval(v):
    if isinstance(v, tuple) and len(v) == 3:
        return v[2] if v[2] else v[0]
    return v


def num(v):
    if isinstance(v, tuple) and len(v) == 3:
        return v[0] if v[0] else v[1]
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return 0
    return v


class Script:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def read_scripts(m, players):
    """Scripts with their OR groups kept apart, group chain and owning player."""
    order = list(players)
    psl = next((n for _, n in m.walk() if n.name == 'PlayerScriptsList'), None)
    lists = [k for k in psl.kids if k.name == 'ScriptList'] if psl else []
    out, groups = [], {}

    def visit(kids, chain, owner):
        for k in kids:
            if k.name == 'ScriptGroup':
                title, p = m.string(k.head, 0)
                active = k.head[p] if len(k.head) > p else 1
                groups[title] = bool(active)
                visit(k.kids, chain + [title], owner)
            elif k.name == 'Script':
                title, p = m.string(k.head, 0)
                for _ in range(3):
                    _, p = m.string(k.head, p)
                h = k.head[p:p + 6] if len(k.head) >= p + 6 else bytes([1, 1, 1, 1, 1, 0])
                ors, acts, offs, off = [], [], [], 0.0
                for x in k.kids:
                    if x.name == 'OrCondition':
                        g = []
                        for c in x.kids:
                            if c.name != 'Condition':
                                continue
                            name, args, rest = m.content(c)
                            if len(rest) >= 1 and rest[0] == 0:
                                continue            # a disabled condition
                            inv = len(rest) >= 8 and rest[4] == 1
                            g.append((name, [a[1] if a[0] == COORD3D else sval(a[1]) for a in args],
                                      [a[1] for a in args], inv))
                        ors.append(g)
                    elif x.name == 'ScriptAction':
                        name, args, rest = m.content(x)
                        if len(rest) >= 1 and rest[0] == 0:
                            continue                # a disabled action
                        acts.append((name, [a[1] if a[0] == COORD3D else sval(a[1]) for a in args],
                                     [a[1] for a in args]))
                        offs.append(off)
                        # waits inside a script (sequential scripts run by an object): later actions are later
                        if name in ('UNIT_IDLE_FOR_SECONDS', 'TEAM_IDLE_FOR_SECONDS') and len(args) > 1:
                            off += float(num(args[1][1]) or 0)
                        elif name in ('UNIT_IDLE_FOR_FRAMECOUNT', 'TEAM_IDLE_FOR_FRAMECOUNT') and len(args) > 1:
                            off += float(num(args[1][1]) or 0) / FPS
                out.append(Script(name=title, chain=chain, owner=owner, active=bool(h[0]), once=bool(h[1]),
                                  diff=(bool(h[2]), bool(h[3]), bool(h[4])), sub=bool(h[5]), ors=ors, acts=acts,
                                  offs=offs, idx=len(out)))
    for i, sl in enumerate(lists):
        visit(sl.kids, [], order[i] if i < len(order) else None)
    return out, groups


def read_teams(m):
    node = next((n for _, n in m.walk() if n.name == 'Teams'), None)
    teams = {}
    if node is None:
        return teams
    d = node.head
    for p in range(len(d) - 6):
        try:
            pr = mapxml._props(m, d, p)
        except Exception:
            continue
        if 'teamName' in pr and len(pr) > len(teams.get(pr['teamName'], {})):
            teams[pr['teamName']] = pr
    return {k: str(v.get('teamOwner', '')) for k, v in teams.items()}


# ---------------------------------------------------------------- times
class Clock:
    """Times are (anchor id, seconds, unknown lengths L, approximate). Anchor 0 is the start."""

    def __init__(self):
        self.anchors = [dict(label='开局', parent=None, pos=None, cond=None)]
        self.by_key = {}
        self.alias = {0: '开局'}
        self.control = 0.0          # player-progress anchors cannot happen before control is handed back

    def parent_anchor(self, a):
        p = self.anchors[a]['parent']
        return None if p is None else p[0]

    def chain(self, a):
        out, seen = [], set()
        while a is not None and a not in seen:
            seen.add(a)
            out.append(a)
            a = self.parent_anchor(a)
        return out

    def rank(self, a):
        return len(self.chain(a)) - 1

    def est(self, t):
        """A guessed absolute time, only for ordering: each player-progress anchor is taken as PLAYER_GUESS seconds
        after the moment it began to be looked for."""
        s, a, seen = t[1] + L_GUESS * t[2], t[0], set()
        while a and a not in seen:
            seen.add(a)
            p = self.anchors[a]['parent']
            s += PLAYER_GUESS
            if p is None:
                break
            s += p[1] + L_GUESS * p[2]
            a = p[0]
        return s

    def key(self, t):
        return (round(self.est(t), 3), self.rank(t[0]), t[0])

    def tmax(self, *ts):
        if any(t is None for t in ts):
            return None
        best = ts[0]
        for t in ts[1:]:
            if self.key(t) > self.key(best):
                best = t
            if t[3] and not best[3] and self.key(t) == self.key(best):
                best = t
        # mixing anchors that are not on one chain: mark approximate
        anc = {t[0] for t in ts}
        if len(anc) > 1 and not all(a in self.chain(best[0]) for a in anc):
            best = (best[0], best[1], best[2], True)
        return best

    def tmin(self, *ts):
        ts = [t for t in ts if t is not None]
        if not ts:
            return None
        return min(ts, key=self.key)

    def anchor(self, label, gate, pos=None, cond=None):
        """The player-progress anchor 'label', looked for from `gate` on (one per label and gate). A label already
        on the gate's own chain is the same event seen again (a repeating script): that anchor is reused."""
        for a in self.chain(gate[0]):
            if self.anchors[a]['label'] == label:
                return (a, 0.0, 0, False)
        if self.rank(gate[0]) >= MAX_RANK:
            return None
        k = (label, gate[0], round(gate[1], 3), gate[2])
        a = self.by_key.get(k)
        if a is None:
            a = len(self.anchors)
            self.anchors.append(dict(label=label, parent=gate, pos=pos, cond=cond))
            self.by_key[k] = a
        return (a, 0.0, 0, False)

    def before(self, e, M):
        """Has event time e certainly happened by moment M?"""
        if e is None or M is None:
            return False
        ce = (e[1] + L_GUESS * e[2])
        if e[0] == M[0]:
            return ce <= M[1] + L_GUESS * M[2] + 1e-6
        ch = self.chain(M[0])
        if e[0] not in ch:
            return False
        child = ch[ch.index(e[0]) - 1]
        p = self.anchors[child]['parent']
        bound = p[1] + L_GUESS * p[2]
        if e[0] == 0:
            bound = max(bound, self.control)
        return ce <= bound + 1e-6

    def name_anchors(self, used):
        order = sorted((a for a in used if a), key=lambda a: self.est((a, 0.0, 0, False)))
        self.alias = {0: '开局', **{a: f'P{i}' for i, a in enumerate(order, 1)}}

    def fmt(self, t):
        if t is None:
            return '未确定'
        a, s, n, ap = t
        lab = self.alias.get(a, f'P?{a}')
        s = round(s, 1)
        txt = lab + (f' + {s:g} 秒' if s or not n else '') + ' + L' * n
        return ('≈' if ap else '') + txt


def area_center(pts):
    a = np.array(pts, float)
    return (float(a[:, 0].mean()), float(a[:, 1].mean()))


class Level:
    def __init__(self, name, m):
        self.name, self.m = name, m
        self.players = mapstudy.players(m)
        self.human = next((n for n, p in self.players.items() if p.get('playerIsHuman')), 'Player_1')
        hp = self.players.get(self.human, {})
        self.enemies = set(str(hp.get('playerEnemies', '')).split())
        self.allies = set(str(hp.get('playerAllies', '')).split()) - {self.human}
        self.teams = read_teams(m)
        self.scripts, self.groups = read_scripts(m, self.players)
        if name.startswith('ours_'):            # our builds are check builds: drop the check's own scripts
            self.scripts = [s for s in self.scripts if not s.name.startswith('Test')]   # ('Test - reveal' ...)
            for i, s in enumerate(self.scripts):
                s.idx = i
        self.areas = {k: area_center(v) for k, v in m.trigger_areas().items() if v}
        self.area_poly = {k: v for k, v in m.trigger_areas().items() if v}
        hm = mapterrain.HeightMap(m)
        self.size = ((hm.width - 2 * hm.border) * CELL, (hm.height - 2 * hm.border) * CELL)
        self.rects = [tuple(v * CELL for v in r) for r in hm.borders()]
        self.wps, self.named, self.named_owner, self.objs = {}, {}, {}, []
        for o in mapxml.objects(m):
            owner = str(o['props'].get('originalOwner', ''))
            side, _, team = owner.partition('/')
            p = (o['x'], o['y'])
            nm = str(o['props'].get('objectName', ''))
            if o['template'] == '*Waypoints/Waypoint':
                self.wps[str(o['props'].get('waypointName', ''))] = p
                continue
            if nm:
                self.named[nm] = p
                self.named_owner[nm] = side
            k = mapstudy.kind(o['template'], owner)
            e = (mapstudy._index or {}).get(o['template'].lower(), {})
            self.objs.append(dict(p=p, side=side, team=team, name=nm, kind=k, template=o['template'],
                                  structure=e.get('EditorSorting', '') == 'STRUCTURE'))
        # created named objects: name -> (owner, spawn point)
        for s in self.scripts:
            for an, v, _ in s.acts:
                if an.startswith('CREATE_NAMED_ON_TEAM_AT_WAYPOINT') and len(v) >= 4:
                    own = self.team_owner(v[2])
                    if v[0] not in self.named_owner:
                        self.named_owner[v[0]] = own
                    if v[0] not in self.named and v[3] in self.wps:
                        self.named[v[0]] = self.wps[v[3]]
        self.team_spawn = {}
        for s in self.scripts:
            for an, v, _ in s.acts:
                if an == 'CREATE_REINFORCEMENT_TEAM' and len(v) >= 2 and v[1] in self.wps:
                    self.team_spawn.setdefault(self.team_key(v[0]), self.wps[v[1]])

    # ---- names to owners and places
    def team_key(self, t):
        return str(t).split('/', 1)[1] if '/' in str(t) else str(t)

    def team_owner(self, t):
        t = str(t)
        if '/' in t:
            return t.split('/')[0]
        return self.teams.get(t, '')

    def team_pos(self, t):
        k = self.team_key(t)
        ps = [o['p'] for o in self.objs if o['team'] == k]
        if ps:
            return area_center(ps)
        return self.team_spawn.get(k)

    def pos_of(self, x):
        x = str(x)
        if x in self.wps:
            return self.wps[x]
        if x in self.named:
            return self.named[x]
        if x in self.areas:
            return self.areas[x]
        return None

    def player_pos(self, p):
        ps = [o['p'] for o in self.objs if o['side'] == p and o['structure']] or \
             [o['p'] for o in self.objs if o['side'] == p]
        return tuple(float(v) for v in np.median(np.array(ps), axis=0)) if ps else None

    def is_human(self, p, owner=None):
        p = str(p)
        if p == '<This Player>':
            p = owner or ''
        return p == self.human or p in GENERIC

    # ---- propagation
    def propagate(self, d):
        """Earliest firing time of every script at difficulty d (0 easy, 1 normal, 2 hard)."""
        ck = Clock()
        live = [s for s in self.scripts if s.diff[d]]
        flag_set, timer_set, enable, call, play, cset, cinc = {}, {}, {}, {}, {}, {}, {}
        for s in live:
            for (an, v, raw), off in zip(s.acts, s.offs):
                me = (s.idx, off)
                if an == 'SET_FLAG' and len(v) >= 2 and num(raw[1]):
                    flag_set.setdefault(v[0], []).append(me)
                elif an == 'SET_MILLISECOND_TIMER' and len(v) >= 2:
                    timer_set.setdefault(v[0], []).append((s.idx, off + float(num(raw[1]) or 0), False))
                elif an == 'SET_TIMER' and len(v) >= 2:
                    timer_set.setdefault(v[0], []).append((s.idx, off + float(num(raw[1]) or 0) / FPS, False))
                elif an == 'SET_RANDOM_TIMER' and len(v) >= 3:
                    timer_set.setdefault(v[0], []).append((s.idx, off + (num(raw[1]) + num(raw[2])) / 2 / FPS, True))
                elif an == 'SET_RANDOM_MSEC_TIMER' and len(v) >= 3:
                    timer_set.setdefault(v[0], []).append((s.idx, off + (num(raw[1]) + num(raw[2])) / 2, True))
                elif an == 'ENABLE_SCRIPT' and v:
                    enable.setdefault(v[0], []).append(me)
                elif an == 'CALL_SUBROUTINE' and v:
                    call.setdefault(v[0], []).append(me)
                elif an == 'SET_COUNTER' and len(v) >= 2:
                    cset.setdefault(v[0], []).append((me, num(raw[1])))
                elif an in ('INCREMENT_COUNTER', 'DECREMENT_COUNTER') and len(v) >= 2:
                    cinc.setdefault(v[1], []).append(me)
                if PLAY.search(an):
                    for x in v:
                        if isinstance(x, str) and x:
                            play.setdefault(x, []).append(me)
        T = {s.idx: None for s in live}
        start = (0, 0.0, 0, False)

        def earliest(ids):
            return ck.tmin(*[None if T.get(i) is None else (T[i][0], T[i][1] + o, T[i][2], T[i][3])
                             for i, o in ids])

        def ok(op, a, b):
            return [a < b, a <= b, a == b, a >= b, a > b, a != b][int(op)] if 0 <= int(op) <= 5 else False

        def cond(c, s, gate):
            name, v, raw, inv = c
            if name == 'CONDITION_TRUE':
                return None if inv else start
            if inv:
                return start
            if name == 'FLAG':
                want = num(raw[1]) if len(raw) > 1 else 1
                return earliest(flag_set.get(v[0], [])) if want else start
            if name == 'TIMER_EXPIRED':
                return ck.tmin(*[None if T.get(i) is None else
                                 (T[i][0], T[i][1] + dur, T[i][2], T[i][3] or ap)
                                 for i, dur, ap in timer_set.get(v[0], [])])
            if name == 'COUNTER_SECONDS' and len(raw) >= 3:
                op, sec = int(num(raw[1])), float(num(raw[2]))
                outs = []
                for i, dur, ap in timer_set.get(v[0], []):
                    if T.get(i) is None:
                        continue
                    off = max(0.0, dur - sec) if op in (0, 1, 2) else 0.0
                    outs.append((T[i][0], T[i][1] + off, T[i][2], T[i][3] or ap))
                return ck.tmin(*outs)
            if name in ('COUNTER', 'COUNTER_COUNTER') and len(raw) >= 3 and name == 'COUNTER':
                op, val = int(num(raw[1])), num(raw[2])
                if ok(op, 0, val):
                    return start
                sets = [i for i, x in cset.get(v[0], []) if ok(op, x, val)]
                t = earliest(sets)
                if t is not None:
                    return t
                first = earliest(cinc.get(v[0], []))
                if first is not None:
                    return ('P', f'计数 {v[0]} 到 {val:g}', None, name, first)
                return None
            if name in ('HAS_FINISHED_VIDEO', 'HAS_FINISHED_AUDIO', 'HAS_FINISHED_SPEECH'):
                t = earliest(play.get(v[0], [])) if v else None
                return None if t is None else (t[0], t[1], t[2] + 1, t[3])
            if name == 'PLAYER_IS_HUMAN_OR_AI_PERSONALITY':
                p = v[0] if v[0] != '<This Player>' else (s.owner or '')
                human = p == self.human or (p == 'Player_1' and self.human not in self.players)
                return start if (v[1] == 'Human') == human else None
            if name == 'NAMED_NOT_DESTROYED' or name == 'TEAM_HAS_UNITS':
                return start
            if name == 'NAMED_OWNED_BY_PLAYER' and len(v) >= 2 and self.named_owner.get(v[0]) == v[1]:
                return start
            # player progress: a new anchor
            words = [str(x) for x in v if not isinstance(x, tuple)]
            tpl = CN.get(name)
            try:
                lab = tpl.format(*words) if tpl else f'{name}({", ".join(words)[:60]})'
            except IndexError:
                lab = f'{name}({", ".join(words)[:60]})'
            pos = None
            for x in v:
                if isinstance(x, str) and x in self.area_poly:
                    pos = self.areas[x]
                    break
            if pos is None:
                for x in v:
                    if isinstance(x, str) and (x in self.named or x in self.wps):
                        pos = self.pos_of(x)
                        break
            return ('P', lab, pos, name, None)

        def gate_of(s):
            parts = []
            own = start if s.active else earliest(enable.get(s.name, []))
            parts.append(own)
            for g in s.chain:
                parts.append(start if self.groups.get(g, True) else earliest(enable.get(g, [])))
            if s.sub:
                parts.append(earliest(call.get(s.name, [])))
            return ck.tmax(*parts)

        def group_time(g, s, gate):
            det, prog = [gate], []
            for c in g:
                r = cond(c, s, gate)
                if r is None:
                    return None
                if r[0] == 'P':
                    prog.append(r)
                    if r[4] is not None:
                        det.append(r[4])
                else:
                    det.append(r)
            t = ck.tmax(*det)
            if t is None or not prog:
                return t
            lab = ' 且 '.join(sorted({p[1] for p in prog}))
            pos = next((p[2] for p in prog if p[2]), None)
            return ck.anchor(lab, t, pos=pos, cond=prog[0][3])

        for _ in range(60):
            changed = False
            for s in live:
                gate = gate_of(s)
                t = None
                if gate is not None:
                    t = gate if not s.ors else ck.tmin(*[group_time(g, s, gate) for g in s.ors])
                if t != T[s.idx]:
                    T[s.idx] = t
                    changed = True
            if not changed:
                break
        return ck, T

    # ---- events
    def events(self, ck, T):
        ev = []
        for s in self.scripts:
            t = T.get(s.idx)
            if t is None:
                continue
            for (an, v, raw), off in zip(s.acts, s.offs):
                for e in self.classify(an, v, raw, s):
                    e.update(t=(t[0], t[1] + off, t[2], t[3]), script=s.name)
                    ev.append(e)
        ev.sort(key=lambda e: ck.key(e['t']))
        return ev

    def classify(self, an, v, raw, s):
        P = lambda x: self.pos_of(x)
        if an == 'MAP_SWITCH_BORDER':
            return [dict(kind='border', k=int(num(raw[0])))]
        if an in ('DISABLE_INPUT', 'ENABLE_INPUT'):
            return [dict(kind='input_off' if an == 'DISABLE_INPUT' else 'input_on')]
        if an == 'MAP_REVEAL_AT_WAYPOINT' and len(v) >= 3 and self.is_human(v[2], s.owner):
            return [dict(kind='reveal', perm=False, pos=P(v[0]), r=float(num(raw[1])), what=v[0])]
        if an == 'MAP_REVEAL_PERMANENTLY_AT_WAYPOINT' and len(v) >= 4 and self.is_human(v[2], s.owner):
            return [dict(kind='reveal', perm=True, pos=P(v[0]), r=float(num(raw[1])), id=v[3], what=v[0])]
        if an == 'MAP_REVEAL_PERMANENTLY_IN_TRIGGER' and len(v) >= 3 and self.is_human(v[1], s.owner):
            return [dict(kind='reveal', perm=True, area=v[0], pos=self.areas.get(v[0]), id=v[2], what=v[0])]
        if an in ('MAP_REVEAL_ALL', 'MAP_REVEAL_ALL_PERM') and v and self.is_human(v[0], s.owner):
            return [dict(kind='reveal', perm=an.endswith('PERM'), all=True, id='<all>', what='全图')]
        if an == 'MAP_REVEAL_ALL_UNDO_PERM' and v and self.is_human(v[0], s.owner):
            return [dict(kind='unreveal', id='<all>')]
        if an in ('MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT', 'MAP_UNDO_REVEAL_PERMANENTLY_IN_TRIGGER') and v:
            return [dict(kind='unreveal', id=v[0])]
        if an in CAMERA:
            i = CAMERA[an]
            if i and v and not self.is_human(v[0], s.owner):
                return []
            tgt = v[i] if len(v) > i else None
            face = v[3] if an == 'SETUP_CAMERA' and len(v) > 3 else None
            p = P(tgt) or (P(face) if face else None)
            return [dict(kind='camera', what=tgt, pos=p, how=an)] if tgt else []
        if an in FLASH and v:
            p = self.team_pos(v[0]) if an == 'TEAM_FLASH' else P(v[0])
            return [dict(kind='flash', what=v[0], pos=p)]
        if an in RADAR and v:
            if an == 'RADAR_CREATE_EVENT':
                c = v[0] if isinstance(v[0], tuple) else None
                p = (c[0], c[1]) if c else None
            elif an == 'TEAM_CREATE_RADAR_EVENT':
                p = self.team_pos(v[0])
            else:
                p = P(v[0])
            return [dict(kind='radar', what=str(v[0]), pos=p)]
        if an == 'SET_MISSION_OBJECTIVE_STATUS' and len(v) >= 2:
            return [dict(kind='objective', name=v[0], status=int(num(raw[1])))]
        if an == 'SHOW_MISSION_OBJECTIVE' and v:
            return [dict(kind='objective', name=v[0], status=1)]
        if an.startswith('LINK_MISSION_OBJECTIVE_TO_') and len(v) >= 3:
            return [dict(kind='link', name=v[0], target=v[1], on=bool(num(raw[2])), pos=P(v[1]))]
        # forces
        out = []
        if an in ('CREATE_REINFORCEMENT_TEAM',) and len(v) >= 2:
            out.append(self.force(self.team_owner(v[0]), P(v[1]), f'刷出 {v[0]}', 'spawn', v[0]))
        elif an.startswith('CREATE_NAMED_ON_TEAM_AT_WAYPOINT') and len(v) >= 4 and not NOT_UNITS.search(v[1]):
            out.append(self.force(self.team_owner(v[2]), P(v[3]), f'刷出 {v[1]}', 'spawn', v[0]))
        elif an.startswith('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT') and len(v) >= 3 and not NOT_UNITS.search(v[0]):
            out.append(self.force(self.team_owner(v[1]), P(v[2]), f'刷出 {v[0]}', 'spawn', None))
        elif an in TEAM_ORDERS and v:
            if an == 'TEAM_AI_TRANSFER' and len(raw) > 1 and not num(raw[1]):
                return []
            out.append(self.force(self.team_owner(v[0]), self.team_pos(v[0]), f'{an} {v[0]}', 'order', v[0]))
        elif an in NAMED_ORDERS and v:
            if an == 'UNIT_AI_TRANSFER' and len(raw) > 1 and not num(raw[1]):
                return []
            out.append(self.force(self.named_owner.get(v[0], ''), P(v[0]), f'{an} {v[0]}', 'order', v[0]))
        elif an in PLAYER_AI and v:
            p = v[0] if v[0] != '<This Player>' else (s.owner or '')
            if an == 'PLAYER_TOGGLE_SKIRMISH_AI' and len(raw) > 1 and not num(raw[1]):
                return []
            out.append(self.force(p, self.player_pos(p), f'{an} {p}', 'ai', p))
        elif an == 'NAMED_TRANSFER_OWNERSHIP_PLAYER' and len(v) >= 2:
            if self.is_human(v[1], s.owner):
                out.append(dict(kind='gain', pos=P(v[0]), what=v[0]))
            elif v[1] in self.enemies:
                out.append(self.force(v[1], P(v[0]), f'交给 {v[1]}: {v[0]}', 'ai', v[0]))
        elif an == 'TEAM_TRANSFER_TO_PLAYER' and len(v) >= 2:
            if self.is_human(v[1], s.owner):
                out.append(dict(kind='gain', pos=self.team_pos(v[0]), what=v[0]))
            elif v[1] in self.enemies:
                out.append(self.force(v[1], self.team_pos(v[0]), f'交给 {v[1]}: {v[0]}', 'ai', v[0]))
        elif an == 'PLAYER_TRANSFER_OWNERSHIP_PLAYER' and len(v) >= 2 and self.is_human(v[1], s.owner):
            out.append(dict(kind='gain', pos=self.player_pos(v[0]), what=v[0]))
        return [e for e in out if e]

    def force(self, owner, pos, what, how, ref):
        if owner in self.enemies:
            return dict(kind='enemy', how=how, pos=pos, what=what, ref=ref, owner=owner)
        if owner == self.human:
            return dict(kind='gain', pos=pos, what=what) if how == 'spawn' else None
        return None


# ---------------------------------------------------------------- the player's knowledge at a moment
class Knowledge:
    def __init__(self, lv):
        self.lv = lv
        self.nx = int(math.ceil(lv.size[0] / GRID)) + 1
        self.ny = int(math.ceil(lv.size[1] / GRID)) + 1
        xs = (np.arange(self.nx) + 0.5) * GRID
        ys = (np.arange(self.ny) + 0.5) * GRID
        self.X, self.Y = np.meshgrid(xs, ys)

    def disk(self, mask, p, r):
        if p is None:
            return
        i0, i1 = max(0, int((p[0] - r) / GRID)), min(self.nx, int((p[0] + r) / GRID) + 2)
        j0, j1 = max(0, int((p[1] - r) / GRID)), min(self.ny, int((p[1] + r) / GRID) + 2)
        if i0 >= i1 or j0 >= j1:
            return
        sub = (self.X[j0:j1, i0:i1] - p[0]) ** 2 + (self.Y[j0:j1, i0:i1] - p[1]) ** 2 <= r * r
        mask[j0:j1, i0:i1] |= sub

    def poly(self, mask, pts):
        from matplotlib.path import Path
        path = Path(np.array(pts))
        inside = path.contains_points(np.c_[self.X.ravel(), self.Y.ravel()]).reshape(self.X.shape)
        mask |= inside

    def rect(self, r):
        m = np.zeros((self.ny, self.nx), bool)
        m[(self.X >= r[0]) & (self.X <= r[2]) & (self.Y >= r[1]) & (self.Y <= r[3])] = True
        return m


# ---------------------------------------------------------------- one map
def measure(name, m):
    lv = Level(name, m)
    out = dict(map=name, human=lv.human, size=[round(v) for v in lv.size])
    ck, T = lv.propagate(1)
    ev = lv.events(ck, T)
    K = Knowledge(lv)
    whole = (0, 0, lv.size[0], lv.size[1])
    rect_of = lambda k: lv.rects[k] if 0 <= k < len(lv.rects) else whole

    # start point: layout_measure's (median of the human objects inside the first border)
    mine = [o['p'] for o in lv.objs if o['side'] == lv.human]
    friends = [o['p'] for o in lv.objs if o['side'] == lv.human or o['side'] in lv.allies]
    first_border = next((e['k'] for e in ev if e['kind'] == 'border' and e['t'][0] == 0), None)
    r0 = rect_of(first_border) if first_border is not None else whole
    mine_in = [p for p in mine if LM.inside(p, r0, LM.ENTER)] or mine
    start = tuple(float(v) for v in np.median(np.array(mine_in), axis=0)) if mine_in else None
    if start is None:
        for key in ('Player_1_Start', 'Player_1 Start', 'wp_player_1_start'):
            if key in lv.wps:
                start = lv.wps[key]
                break
    out['start'] = [round(v) for v in start] if start else None
    foes = [o for o in lv.objs if o['side'] in lv.enemies]
    cl = LM.clusters([o['p'] for o in foes])

    # control handed back
    offs = [e for e in ev if e['kind'] == 'input_off' and e['t'][0] == 0 and e['t'][1] <= 5]
    ons = [e for e in ev if e['kind'] == 'input_on' and offs and ck.key(e['t']) > ck.key(offs[0]['t'])]
    # the first ENABLE_INPUT after the opening DISABLE_INPUT (an opening whose end waits on a scripted unit
    # reaching an area gives a player-progress anchor here, though no player acts)
    on0 = [e for e in ons if e['t'][0] == 0 and e['t'][1] <= 180]
    control = (on0 or ons)[0]['t'] if offs and ons else (0, 0.0, 0, False)
    if offs and not ons:
        control = None
    ck.control = control[1] + L_GUESS * control[2] if control and control[0] == 0 else 0.0
    every = set()
    for e in ev:
        every.update(ck.chain(e['t'][0]))
    ck.name_anchors(every)

    # key moments
    moments = [('交还控制', control)] if control else []
    seen_b, seen_o = set(), set()
    for e in ev:
        if e['kind'] == 'border' and e['k'] not in seen_b:
            seen_b.add(e['k'])
            if not (e['t'][0] == 0 and control and ck.key(e['t']) <= ck.key(control)):
                moments.append((f'换边界 {e["k"]}', e['t']))
        elif e['kind'] == 'objective' and e['status'] == 1 and e['name'] not in seen_o:
            seen_o.add(e['name'])
            moments.append((f'亮目标 {e["name"]}', e['t']))
    playable_area = lambda r: (r[2] - r[0]) * (r[3] - r[1])
    for e in ev:
        if e['kind'] == 'reveal' and not (e['t'][0] == 0 and control and ck.key(e['t']) <= ck.key(control)):
            cur = rect_of(current_border(ck, ev, e['t'], first_border))
            a = playable_area(whole) if e.get('all') else math.pi * e.get('r', 0) ** 2 if 'r' in e else \
                poly_area(lv.area_poly.get(e.get('area'), []))
            if a >= BIG_REVEAL * playable_area(cur):
                moments.append((f'大块揭图 {e["what"]}', e['t']))
    moments.sort(key=lambda q: ck.key(q[1]))

    goals = {g['name']: g for g in mapstudy.objectives(m)[0]}

    def state(M):
        """The player's knowledge at moment M."""
        b = current_border(ck, ev, M, first_border)
        play = K.rect(rect_of(b))
        seen = np.zeros_like(play)
        glimpsed = np.zeros_like(play)
        for p in friends:
            K.disk(seen, p, VISION)
        anchor_pt, anchor_what = start, '出生点'
        reveals, undone, gains = {}, set(), []
        for e in ev:
            if not ck.before(e['t'], M):
                continue
            if e['kind'] == 'reveal':
                if e.get('perm'):
                    reveals[e['id']] = e
                    undone.discard(e['id'])
                else:
                    if e.get('all'):
                        glimpsed[:] = True
                    else:
                        K.disk(seen, e['pos'], e['r'])
            elif e['kind'] == 'unreveal':
                if e['id'] in reveals:
                    undone.add(e['id'])
            elif e['kind'] == 'gain' and e.get('pos'):
                K.disk(seen, e['pos'], VISION)
                if LM.inside(e['pos'], whole):
                    gains.append(e)
        if gains:                               # the latest batch of gains (one script, one anchor): its median
            last = gains[-1]
            batch = [g['pos'] for g in gains if g['script'] == last['script'] and g['t'][0] == last['t'][0]]
            anchor_pt = tuple(float(v) for v in np.median(np.array(batch), axis=0))
            anchor_what = f'{last["script"]}（{len(batch)} 处）'
        for rid, e in reveals.items():
            tgt = glimpsed if rid in undone else seen
            if e.get('all'):
                tgt[:] = True
            elif e.get('area') and e['area'] in lv.area_poly:
                K.poly(tgt, lv.area_poly[e['area']])
            elif e.get('pos'):
                K.disk(tgt, e['pos'], e.get('r', 0))
        for a in ck.chain(M[0])[:-1]:            # player-progress anchors that have happened: the player was there
            pos = ck.anchors[a]['pos']
            if pos:
                K.disk(seen, pos, VISION)
        known = seen & play
        frac = known.sum() / max(1, play.sum())
        res = dict(border=b, known=round(float(frac), 2),
                   glimpsed=round(float(((seen | glimpsed) & play).sum() / max(1, play.sum())), 2),
                   anchor=anchor_what, anchor_at=[round(v) for v in anchor_pt] if anchor_pt else None)
        ys, xs = np.nonzero(known)
        if len(xs) and anchor_pt:
            bx = (xs.min() * GRID, ys.min() * GRID, (xs.max() + 1) * GRID, (ys.max() + 1) * GRID)
            res['known_box'] = [round(v) for v in bx]
            w, h = bx[2] - bx[0], bx[3] - bx[1]
            nx, ny = (anchor_pt[0] - bx[0]) / max(1, w), (anchor_pt[1] - bx[1]) / max(1, h)
            u, v = min(nx, 1 - nx), min(ny, 1 - ny)
            res['anchor_place'] = 'outside' if not (0 <= nx <= 1 and 0 <= ny <= 1) else \
                'corner' if u < 0.25 and v < 0.25 else 'edge' if min(u, v) < 0.25 else 'centre'
        isknown = lambda p: p is not None and 0 <= int(p[1] / GRID) < K.ny and 0 <= int(p[0] / GRID) < K.nx and \
            bool(known[int(p[1] / GRID), int(p[0] / GRID)])
        res['_isknown'] = isknown
        # threats
        th = []
        for c, n in cl:
            if n >= 8 and isknown(c) and anchor_pt:
                th.append(dict(src='据点', n=int(n), dir=octant(c[0] - anchor_pt[0], c[1] - anchor_pt[1]),
                               dist=round(math.hypot(c[0] - anchor_pt[0], c[1] - anchor_pt[1]))))
        for e in ev:
            if e['kind'] == 'enemy' and ck.before(e['t'], M) and e.get('pos') and anchor_pt:
                p = e['pos']
                th.append(dict(src='已出动', what=e['what'], dir=octant(p[0] - anchor_pt[0], p[1] - anchor_pt[1]),
                               dist=round(math.hypot(p[0] - anchor_pt[0], p[1] - anchor_pt[1]))))
        res['threat_dirs'] = sorted({x['dir'] for x in th}, key=LM.OCT.index)
        res['threat_clusters'] = sum(1 for x in th if x['src'] == '据点')
        res['threat_dispatched'] = len({x['what'] for x in th if x['src'] == '已出动'})
        # goals
        status, links = {}, {}
        for e in ev:
            if ck.before(e['t'], M):
                if e['kind'] == 'objective':
                    status[e['name']] = e['status']
                elif e['kind'] == 'link':
                    links.setdefault(e['name'], {})[e['target']] = (e['on'], e.get('pos'))
        gl = []
        for g, st in status.items():
            if st != 1:
                continue
            ms = [p for on, p in links.get(g, {}).values() if on and p]
            item = dict(name=g, bonus=bool(goals.get(g, {}).get('bonus')), markers=len(ms),
                        known_markers=sum(1 for p in ms if isknown(p)))
            if ms and anchor_pt:
                c = area_center(ms)
                item.update(dir=octant(c[0] - anchor_pt[0], c[1] - anchor_pt[1]),
                            dist=round(math.hypot(c[0] - anchor_pt[0], c[1] - anchor_pt[1])))
            gl.append(item)
        res['goals'] = gl
        return res

    # objectives: how each was pointed out
    pointing = {}
    for e in ev:
        if e['kind'] != 'objective' or e['status'] != 1 or e['name'] in pointing:
            continue
        S = e['t']
        win = [x for x in ev if x['t'][0] == S[0] and abs(x['t'][1] - S[1]) <= POINT]   # video lengths L not counted
        marks = [(x['target'], x.get('pos')) for x in ev if x['kind'] == 'link' and x['name'] == e['name'] and x['on']
                 and (ck.before(x['t'], (S[0], S[1] + POINT, S[2], False)))]
        mp = [p for _, p in marks if p]
        names = {t for t, _ in marks}
        how = []
        for x in win:
            if x['kind'] == 'camera' and x.get('pos') and any(dist(x['pos'], p) <= NEAR for p in mp):
                how.append('镜头')
            elif x['kind'] == 'reveal' and mp and (x.get('all') or any(
                    (x.get('pos') and dist(x['pos'], p) <= x.get('r', 600) + 200) for p in mp)):
                how.append('揭图')
            elif x['kind'] == 'flash' and (x['what'] in names or (x.get('pos') and any(dist(x['pos'], p) <= NEAR for p in mp))):
                how.append('闪烁')
            elif x['kind'] == 'radar' and x.get('pos') and any(dist(x['pos'], p) <= NEAR for p in mp):
                how.append('雷达')
        an = ck.anchors[S[0]]
        near = S[0] != 0 and (an['cond'] in DISCOVER or (an['pos'] and any(dist(an['pos'], p) <= 1000 for p in mp)))
        pointing[e['name']] = dict(t=S, how=sorted(set(how)), markers=len(mp), walk_up=bool(near),
                                   bonus=bool(goals.get(e['name'], {}).get('bonus')))

    used = set()
    out['moments'] = []
    for lab, M in moments:
        s = state(M)
        isknown = s.pop('_isknown')
        for g in s['goals']:
            p = pointing.get(g['name'])
            g['pointed'] = p['how'] if p else []
        s.update(label=lab, t=ck.fmt(M))
        out['moments'].append(s)
        used.update(ck.chain(M[0]))
    for name_, p in pointing.items():
        st = state((p['t'][0], p['t'][1] + POINT, p['t'][2], False))
        isknown = st.pop('_isknown')
        g = next((x for x in st['goals'] if x['name'] == name_), None)
        if p['how']:
            cat = '领着看（' + '、'.join(p['how']) + '）'
        elif p['walk_up']:
            cat = '走近才触发'
        elif not p['markers']:
            cat = '没有标记'
        elif g and g['known_markers']:
            cat = '只有标记（在已知区域）'
        else:
            cat = '标记在未知区域'
        p.update(cat=cat, t=ck.fmt(p['t']), known_frac=st['known'])
    out['goals'] = [dict(name=k, title=goals.get(k, {}).get('title', ''), **v) for k, v in pointing.items()]
    # opening camera tour: camera events before control
    cams = [e for e in ev if e['kind'] == 'camera' and e['t'][0] == 0 and control and ck.key(e['t']) <= ck.key(control)]
    spots = []
    for e in cams:
        if e.get('pos') and all(dist(e['pos'], q) > 400 for q in spots):
            spots.append(e['pos'])
    out['opening_camera'] = dict(moves=len(cams), spots=len(spots), control=ck.fmt(control))
    # enemies: first appearance and the sleepers
    first = next((e for e in ev if e['kind'] == 'enemy' and not (
        control and e['t'][0] == 0 and ck.key(e['t']) < ck.key(control))), None)     # not the opening cutscene's
    vis0 = out['moments'][0]['threat_clusters'] if out['moments'] else 0
    fa = None
    if vis0:
        fa = dict(t=ck.fmt(control), how='开局就在视野里', trigger='开局', dir=out['moments'][0]['threat_dirs'])
    if first:
        p = first.get('pos')
        d1 = dict(t=ck.fmt(first['t']), how=first['what'], trigger='计时' if first['t'][0] == 0 else '玩家推进',
                  dir=[octant(p[0] - start[0], p[1] - start[1])] if p and start else [])
        out['first_dispatch'] = d1
        if fa is None:
            fa = d1
    out['first_seen'] = fa
    disp_team, disp_name, disp_player = {}, {}, {}
    for e in ev:
        if e['kind'] != 'enemy':
            continue
        if e['how'] == 'ai':
            if e['ref'] in lv.players:
                disp_player.setdefault(e['ref'], e['t'])
            else:
                disp_name.setdefault(e['ref'], e['t'])
                disp_team.setdefault(lv.team_key(e['ref']), e['t'])
        elif e['how'] == 'order':
            disp_team.setdefault(lv.team_key(e['ref']), e['t'])
            disp_name.setdefault(e['ref'], e['t'])
    sleep = dict(timed=0, triggered=0, never=0)
    for o in foes:
        if o['structure'] or o['kind'] != 'player':
            continue
        ts = [disp_name.get(o['name']) if o['name'] else None, disp_team.get(o['team']), disp_player.get(o['side'])]
        t = ck.tmin(*ts)
        sleep['never' if t is None else 'timed' if t[0] == 0 else 'triggered'] += 1
    out['enemy_units'] = sleep
    # timeline (compact)
    tl = []
    for e in ev:
        if e['kind'] in ('border', 'objective', 'reveal', 'unreveal', 'camera', 'flash', 'radar', 'input_on',
                         'input_off', 'gain', 'enemy', 'link'):
            row = dict(t=ck.fmt(e['t']), kind=e['kind'], script=e['script'])
            for k in ('k', 'name', 'status', 'what', 'r', 'perm', 'target', 'on', 'how'):
                if k in e:
                    row[k] = e[k]
            if e.get('pos'):
                row['at'] = [round(e['pos'][0]), round(e['pos'][1])]
            tl.append(row)
            used.update(ck.chain(e['t'][0]))
    out['timeline'] = tl
    out['anchors'] = [dict(id=ck.alias.get(i), label=ck.anchors[i]['label'],
                           after=ck.fmt(ck.anchors[i]['parent']) if ck.anchors[i]['parent'] else None)
                      for i in sorted(used, key=lambda a: ck.est((a, 0.0, 0, False))) if i]
    # other difficulties: objective show and border times that differ (start-anchored ones)
    diffs = []
    for d, dn in ((0, '简单'), (2, '困难')):
        ck2, T2 = lv.propagate(d)
        ev2 = lv.events(ck2, T2)
        for kind in ('objective', 'border', 'enemy'):
            a = first_times(ck, ev, kind)
            b = first_times(ck2, ev2, kind)
            for k in a:
                if k in b and a[k][0] == 0 and b[k][0] == 0 and ck.fmt(a[k]) != ck2.fmt(b[k]):
                    diffs.append(dict(diff=dn, what=k, normal=ck.fmt(a[k]), other=ck2.fmt(b[k])))
    out['difficulty_diffs'] = diffs
    return out


def first_times(ck, ev, kind):
    out = {}
    for e in ev:
        if e['kind'] == kind and (kind != 'objective' or e['status'] == 1):
            k = f'{kind} {e.get("name", e.get("k", e.get("what")))}'
            out.setdefault(k, e['t'])
    return out


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def poly_area(pts):
    if len(pts) < 3:
        return 0
    a = np.array(pts, float)
    return 0.5 * abs(np.dot(a[:, 0], np.roll(a[:, 1], 1)) - np.dot(a[:, 1], np.roll(a[:, 0], 1)))


def current_border(ck, ev, M, first):
    b = first
    for e in ev:
        if e['kind'] == 'border' and ck.before(e['t'], M):
            b = e['k']
    return b if b is not None else (0 if ck else None)


# ---------------------------------------------------------------- the md
# acceptance: (map key part, hand-timed event, hand time, finder, regex my time must match, note)
#   finder: ('goal', objective name) | ('control',) | ('moment', label part) | ('tl', kind, field, value part)
G, TL, C = 'goal', 'tl', ('control',)
ACCEPT = [
    ('ep01_a01', '交还控制', '约 14', C, r'^开局 \+ 1[3-5]', ''),
    ('ep01_a01', '开局第 1 块边界（开场镜头里切）', '开场镜头中（约 9）', (TL, 'border', 'k', '1'), r'^开局 \+ 9', ''),
    ('ep01_a01', '目标"护送基地车"亮', '约 16', (G, 'EP01_A01_Objective_1'), r'^开局 \+ 1[5-7]', ''),
    ('ep01_a01', '目标"基地车必须存活"亮', '约 28（目标 1 + 12 秒计时，且 45 号语音播完）', (G, 'EP01_A01_Objective_2'),
     r'^开局 \+ 19\.1 秒 \+ L$', '两个条件取晚：计时到 16.1 + 12 = 28.1，语音到 16.1 + 3 + L；排序时 L 按 15 秒估，所以写成了后者。'
     'L ≥ 9 秒时两者相同'),
    ('ep01_a01', '扩到蓝边界', '山顶清空 + 6 + 6', (TL, 'border', 'k', '2'), r'^P\d+ \+ 1[12]',
     '排出来挂在"基地车进 Bridge Problems 区"那条兜底路径上（桥全炸了直接扩图），它是"最早可能"的那条，不是正常路线；'
     '算法取所有路径里最早的，分不出哪条是主线'),
    ('ep01_a01', '目标"打败慎三的效忠派"亮', 'T2 + 30（T2 = 蓝边界）', (G, 'EP01_A01_Objective_2p5'), r'\+ 30 秒$',
     '秒数对上，锚点是"山顶清空"而不是蓝边界（同上一条）'),
    ('j03_odessa', '交还控制', '6', C, r'^开局 \+ 6 秒$', ''),
    ('j03_odessa', '目标 1 亮', '8.5 + L₂', (G, 'Objective_1_Escort_Parts'), r'^开局 \+ 8\.5 秒 \+ L$', ''),
    ('j03_odessa', '切到 0 号边界（巨人登场）', '目标 1 完成后的过场里', (TL, 'border', 'k', '0'), r'^P\d+ \+ 8\.1 秒$', ''),
    ('j03_odessa', '目标 2 亮', 'D + 28.6', (G, 'Objective_2_Destroy_Artillery'), r'^P\d+ \+ 28\.6 秒$', ''),
    ('j03_odessa', '奖励目标亮', 'D + 34.6', (G, 'Bonus_Culture_Killer'), r'^P\d+ \+ 34\.6 秒$', ''),
    ('j03_odessa', '目标 3 亮', 'E + 2（E = TH04、TH11 播完）', (G, 'Objective_3_Destroy_Krukov'), r'^P\d+ \+ [\d.]+ 秒 \+ L \+ L$', ''),
    ('j02_stalingrad', '开场全图揭开、交还控制时收回', '0～7', C, r'^开局 \+ 7 秒$', ''),
    ('j02_stalingrad', '交还控制时已知区域（全图揭开已收回）', '只剩出生点附近', ('known0',), r'^已知 [0-9]%', ''),
    ('j02_stalingrad', '目标 1 亮', '10.5 + L₇ + 1 + L₁ + 1', (G, 'Objective_1_Beachhead'), r'^开局 \+ 1[12]\.5 秒 \+ L \+ L$',
     '差 1 秒（12.5 vs 11.5），没查出是哪一段的 1 秒缓冲'),
    ('j02_stalingrad', '母亲像过场：揭开半径 200', 'D₁ + 5～6', (TL, 'reveal', 'what', 'wp_statue_reveal'), r'^P\d+ \+ [56] 秒$', ''),
    ('j02_stalingrad', '目标 2 亮', 'D₁ + 14 + L₂ + 1', (G, 'Objective_2_Statue'), r'^P\d+ \+ 15 秒 \+ L$', ''),
    ('j02_stalingrad', '奖励目标亮', '目标 2 + 6', (G, 'Bonus_Kill_Monuments'), r'^P\d+ \+ 21 秒 \+ L$', ''),
    ('j02_stalingrad', '目标 3 亮 + 河道永久揭开', 'D₂ + 7', (G, 'Objective_3_Transports'), r'^P\d+ \+ 7 秒$', ''),
    ('j02_stalingrad', '揭开整条河道', 'D₂ + 7', (TL, 'reveal', 'what', 'area_reveal_river'), r'^P\d+ \+ 7 秒$', ''),
    ('ep01_a03', '开场过场结束', '约 32（含两段视频）', C, r'^开局 \+ 2\d(\.\d)? 秒 \+ L$', '22 + L，L≈10 时对上'),
    ('ep01_a03', '目标 1 亮', '过场结束 + 2', (G, 'MO_Build_Base'), r'^开局 \+ 24 秒 \+ L$', ''),
    ('ep01_a03', '目标 2 亮', '目标 1 完成 + 1 + 台词 + 2', (G, 'MO_Defeat_Naomi'), r'^P\d+ \+ 3 秒 \+ L$',
     '排出"P + 2"：亮目标 2 的脚本只等一个旗标，等台词的那个旗标在另一条路上，没跟上'),
    ('ep01_a03', '奖励目标亮', '目标 2 + 1', (G, 'MO_Garrison_Structure'), r'^P\d+ \+ 3 秒', '相对目标 2 晚 1 秒，对上'),
    ('ep01_a03', '目标 3 亮', '高良认输 + 约 49 + L（扩图 +1、存档 +1、过场约 42、EVA 台词）', (G, 'MO_Defeat_Tatsu'),
     r'^P\d+ \+ (4[7-9]|5[0-2]) 秒 \+ L$', ''),
    ('a08_havana', '目标 1 亮', '12', (G, 'A08_Objective_1'), r'^开局 \+ 12 秒$', ''),
    ('a08_havana', '目标 2 亮', '目标 1 完成 + 5.5', (G, 'A08_Objective_2'), r'^P\d+ \+ 5\.5 秒$', ''),
    ('a08_havana', '目标 3 亮', '目标 2 完成 + 5', (G, 'A08_Objective_3'), r'^P\d+ \+ 5 秒$', ''),
    ('a08_havana', '目标 4 亮', 'P + 12（P = 第二段，目标 3 完成 + 3 + 过场 20～40）', (G, 'A08_Objective_4'),
     r'^≈?P\d+ \+ 30\.2 秒 \+ L \+ L$', '目标 3 完成 + 30.2 + 两段影片：和"+3 + 过场 + 12"一致'),
    ('a08_havana', '目标 5 亮', 'P + 17（目标 4 + 5）', (G, 'A08_Objective_5'), r'^≈?P\d+ \+ 35\.2 秒 \+ L \+ L$', ''),
    ('j07_yokohama', '开场过场结束', 'T26～27', C, r'^开局 \+ 2[67]', ''),
    ('j07_yokohama', '目标 1 亮', 'T28 + L₄', (G, 'J07_Objective_Capture_Outposts'), r'^开局 \+ 28 秒 \+ L$', ''),
    ('j07_yokohama', '目标 3 亮', '目标 2 完成 + 约 21', (G, 'J07_Objective_Destroy_Relay_Stations'), r'^P\d+ \+ 21 秒$', ''),
    ('j07_yokohama', '奖励目标 2 亮', '库可夫到场 + 约 44 + 8', (G, 'J07_Bonus_Destroy_Soviets'), r'^P\d+ \+ 5[0-3] 秒$',
     '秒数对上；锚点取了"盟军快被打光，苏军提前到场"那条路，而不是 G3 + 180 的计时（同伊贺：算法取最早可能）'),
    ('ep01_y01', '开场两段视频加运镜结束', '约 78', C, r'^开局 \+ 7[6-9]', ''),
    ('ep01_y01', '目标 1 亮', 'C + 1', (G, 'Y01_Powers'), r'^开局 \+ 7[7-9]', ''),
    ('ep01_y01', '武士 B 冲锋', '进 Warrior 01 区', (TL, 'enemy', 'script', 'Warriors - B'), r'^P\d+', ''),
    ('ep01_y01', '目标 2 亮', '读升级文件 F4 + 8 + IZ03 + 3', (G, 'Y01_GetFree'), r'^P\d+ \+ 38\.7 秒$',
     '脚本在播 IZ03 时用 400 帧（26.7 秒）等视频放完，手排把这段写成了未知长度；8 + 1 + 26.7 + 3 = 38.7'),
    ('ours_A4', '第 1 段主目标亮', '段开始 2 秒', (G, 'Objective01 - CNV A4'), r'^开局 \+ 2 秒$', ''),
    ('ours_A4', '第 1 段第 2 个奖励目标亮', '段开始 2 + 4 + 4 秒', (G, 'Bonus02 - CNV A4'), r'^开局 \+ 10 秒$', ''),
    ('ours_A4', '第 2 段主目标亮', '最晚 1:00 + 2 秒', (G, 'Objective02 - CNV A4'), r'^开局 \+ 62 秒$',
     '排的是"计时到"那条；广场封过 + 10 秒那条更早时会提前'),
    ('ours_A4', '港口生变：扩到全图', '车队到达 halt（玩家推进）', (TL, 'border', 'k', '0'), r'^P\d+', ''),
    ('ours_S6', '第 1 段主目标亮', '段开始 2 秒', (G, 'Objective01 - CNV S6'), r'^开局 \+ 2 秒$', ''),
    ('ours_S6', '倒计时段主目标亮', '1:30 + 2 秒', (G, 'Objective02 - CNV S6'), r'^开局 \+ 92 秒$', ''),
    ('ours_S6', '倒计时段两个奖励目标亮', '1:30 + 6 / + 10 秒', (G, 'Bonus01 - CNV S6'), r'^开局 \+ 100 秒$', ''),
    ('ours_S6', '开场试探（第一股敌人）', '0:30', ('first',), r'^开局 \+ 30 秒$', ''),
]


def find(r, f):
    if f[0] == 'control':
        return r['opening_camera']['control']
    if f[0] == 'known0':
        m0 = r['moments'][0] if r['moments'] else None
        return f'已知 {m0["known"]:.0%}，看过 {m0["glimpsed"]:.0%}' if m0 else '没有'
    if f[0] == 'first':
        return (r.get('first_dispatch') or {}).get('t', '没有')
    if f[0] == 'goal':
        g = next((g for g in r['goals'] if g['name'] == f[1]), None)
        return g['t'] if g else '没找到'
    if f[0] == 'moment':
        mo = next((x for x in r['moments'] if f[1] in x['label']), None)
        return mo['t'] if mo else '没找到'
    if f[0] == 'tl':
        e = next((e for e in r['timeline'] if e['kind'] == f[1] and f[3] in str(e.get(f[2], ''))), None)
        return e['t'] if e else '没找到'
    return '?'


def write_md(data):
    import layout_table as LT
    keys = sorted(data, key=lambda k: (k.startswith('ours_'), k))
    retail = [k for k in keys if not k.startswith('ours_') and 'error' not in data[k]]
    ours = [k for k in keys if k.startswith('ours_') and 'error' not in data[k]]
    W = []
    w = W.append
    w('# 玩家视角的动态布局：时间线测量\n')
    w('由 [timeline_measure.py](timeline_measure.py) 生成（只读原版存档和 Mods 里我们编好的地图）；原始数据 '
      '[timeline.json](timeline.json)。算法、近似和每一项怎么量的，见 timeline_measure.py 开头。读数时记住：\n')
    w('- 时刻写成"锚点 + 秒"。"开局"是任务开始；P1、P2……是玩家推进（进区域、拆掉某物、目标完成……）才会发生的事，'
      '每关末尾列出它们是什么、最早从什么时候起才可能发生。"+ L"是一段长度未知的视频或语音；"≈"表示这个时刻混了'
      '几条互不相干的链，或者用了随机计时器的中值。')
    w('- "已知区域"= 当前可玩区 ∩（还没收回的永久揭图 ∪ 一次性揭图 ∪ 玩家和盟友开局单位、后来到手的单位、玩家推进'
      '到过的地方周围 500 的视野）。500 是视野的近似，"推进到过的地方"只取那个锚点条件里的区域或物体位置，玩家路上看见的'
      '不算——所以玩家推进以后的已知区域**偏小**。揭开又收回的（过场里揭全图）只算"看过一眼"。')
    w('- 排的是普通难度；只在别的难度生效的脚本不进这条线，开局计时上的差别记在 json 的 difficulty_diffs。')
    w('- "被领着看"：目标亮出前后 10 秒内（不计视频长度 L），同一条锚点链上有镜头移到标记 700 以内、揭开标记那里、'
      '闪烁标记物体或雷达事件。\n')
    # ---- acceptance
    w('## 验收表（对照手排时间线）\n')
    if ACCEPT:
        w('| 关 | 手排事件 | 手排时刻 | 排出来的 | 对上了吗 |')
        w('|---|---|---|---|---|')
        for part, ev, hand, f, rx, note in ACCEPT:
            k = next((k for k in keys if part in k), None)
            mine = find(data[k], f) if k and 'error' not in data[k] else '没跑'
            okay = bool(re.search(rx, mine)) if rx else False
            w(f'| {LT.ident(k)[0] if k else part} | {ev} | {hand} | {mine} | {"对上" if okay else "**对不上**"}'
              f'{"：" + note if note else ""} |')
        w('')
    # ---- summary
    w('## 汇总：原版 40 关 vs 我们 11 关\n')
    w(summary(data, retail, ours))
    # ---- per map
    w('## 每关\n')
    for k in keys:
        r = data[k]
        name = LT.ident(k)[0]
        w(f'### {name}（{k}）\n')
        if 'error' in r:
            w(f'测量失败：`{r["error"]}`\n')
            continue
        oc = r['opening_camera']
        fs = r.get('first_seen') or {}
        eu = r['enemy_units']
        w(f'- 交还控制：{oc["control"]}；开场镜头 {oc["moves"]} 次、指过 {oc["spots"]} 处。'
          f'敌人第一次露面：{fs.get("t", "未确定")}（{fs.get("how", "")}，{fs.get("trigger", "")}，'
          f'{"、".join(fs.get("dir", [])) or "方向未知"}）。开局预摆的敌方机动单位：定时出动 {eu["timed"]}、'
          f'等玩家触发 {eu["triggered"]}、脚本从不调动 {eu["never"]}。')
        w('')
        w('| 时刻 | 关键时刻 | 可玩区 | 已知 / 看过 | 锚点在已知区域的 | 威胁方向 | 进行中的目标（标记在已知区里 / 要自己找） |')
        w('|---|---|---|---|---|---|---|')
        for mo in r['moments']:
            gs = []
            for g in mo['goals']:
                tag = ('奖' if g['bonus'] else '主') + ' ' + g['name']
                if not g['markers']:
                    gs.append(f'{tag}（无标记）')
                else:
                    where = f'{g.get("dir", "")} {g.get("dist", "")}'
                    gs.append(f'{tag} {where}（{g["known_markers"]}/{g["markers"]} 已知'
                              f'{"，" + "、".join(g["pointed"]) if g["pointed"] else ""}）')
            w(f'| {mo["t"]} | {mo["label"]} | {mo["border"]} | {mo["known"]:.0%} / {mo["glimpsed"]:.0%} | '
              f'{LT.PLACE.get(mo.get("anchor_place"), "?")}（{str(mo["anchor"])[:30]}） | '
              f'{"、".join(mo["threat_dirs"]) or "—"} | {"；".join(gs) or "—"} |')
        w('')
        if r['goals']:
            w('| 目标 | 亮出 | 怎么被发现 |')
            w('|---|---|---|')
            for g in r['goals']:
                w(f'| {"奖励" if g["bonus"] else "主"} {g["name"]} | {g["t"]} | {g["cat"]} |')
            w('')
        need = set()
        for txt in [mo['t'] for mo in r['moments']] + [g['t'] for g in r['goals']] + [fs.get('t', '')]:
            need.update(re.findall(r'P\d+', txt))
        an = [a for a in r['anchors'] if a['id'] in need]
        if an:
            w('锚点：' + '；'.join(f'{a["id"]} = {a["label"][:90]}（{a["after"]} 起）' for a in an) + '\n')
    with open(OUT_MD, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(W) + '\n')


def summary(data, retail, ours):
    def stats(keys):
        s = {}
        k0 = [data[k]['moments'][0] for k in keys if data[k]['moments']]
        s['n'] = len(keys)
        s['known0'] = statistics.median([m['known'] for m in k0]) if k0 else None
        s['glimpse0'] = sum(1 for m in k0 if m['glimpsed'] > m['known'] + 0.2)
        cam = [data[k]['opening_camera'] for k in keys]
        s['cam_maps'] = sum(1 for c in cam if c['spots'])
        s['cam_spots'] = statistics.median([c['spots'] for c in cam if c['spots']]) if s['cam_maps'] else 0
        s['place0'] = {}
        for m in k0:
            p = m.get('anchor_place', '?')
            s['place0'][p] = s['place0'].get(p, 0) + 1
        mains = [g for k in keys for g in data[k]['goals'] if not g['bonus']]
        bon = [g for k in keys for g in data[k]['goals'] if g['bonus']]

        def cats(gs):
            out = {}
            for g in gs:
                c = g['cat'].split('（')[0] if g['cat'].startswith('领着看') else g['cat']
                out[c] = out.get(c, 0) + 1
            return out
        s['main'], s['bonus'] = cats(mains), cats(bon)
        s['main_n'], s['bonus_n'] = len(mains), len(bon)
        s['main_known'] = statistics.median([g['known_frac'] for g in mains]) if mains else None
        fs = [data[k].get('first_seen') for k in keys]
        s['fs_open'] = sum(1 for f in fs if f and f['trigger'] == '开局')
        s['fs_timed'] = sum(1 for f in fs if f and f['trigger'] == '计时')
        s['fs_player'] = sum(1 for f in fs if f and f['trigger'] == '玩家推进')
        s['fs_none'] = sum(1 for f in fs if not f)
        secs = []
        for f in fs:
            if f and f['trigger'] in ('计时', '开局'):
                mt = re.match(r'≈?开局(?: \+ ([\d.]+) 秒)?', f['t'])
                if mt and '+ L' not in f['t']:
                    secs.append(float(mt.group(1) or 0))
        s['fs_sec'] = statistics.median(secs) if secs else None
        eu = [data[k]['enemy_units'] for k in keys]
        tot = [sum(e.values()) for e in eu]
        s['sleep'] = statistics.median([(e['triggered'] + e['never']) / t for e, t in zip(eu, tot) if t]) \
            if any(tot) else None
        s['trig'] = statistics.median([e['triggered'] / t for e, t in zip(eu, tot) if t]) if any(tot) else None
        s['timed'] = statistics.median([e['timed'] / t for e, t in zip(eu, tot) if t]) if any(tot) else None
        s['moments'] = statistics.median([len(data[k]['moments']) for k in keys])
        grow = []
        for k in keys:
            ms = data[k]['moments']
            if len(ms) > 1:
                grow.append(max(m['known'] for m in ms) - ms[0]['known'])
        s['grow'] = statistics.median(grow) if grow else None
        return s
    a, b = stats(retail), stats(ours)
    pct = lambda x: '—' if x is None else f'{x:.0%}'
    num_ = lambda x: '—' if x is None else f'{x:g}'
    dic = lambda d: '、'.join(f'{k} {v}' for k, v in sorted(d.items(), key=lambda q: -q[1])) or '—'
    P = {'corner': '角落', 'edge': '边上', 'centre': '中间', 'outside': '框外', '?': '?'}
    rows = [
        ('测到的关', a['n'], b['n']),
        ('交还控制时已知区域占可玩区（中位数）', pct(a['known0']), pct(b['known0'])),
        ('交还控制前在过场里"看过一眼"更大范围的关（看过的比已知多 20% 以上）', a['glimpse0'], b['glimpse0']),
        ('交还控制时出生点在已知区域的', dic({P.get(k, k): v for k, v in a['place0'].items()}),
         dic({P.get(k, k): v for k, v in b['place0'].items()})),
        ('开场有镜头领着看的关', f'{a["cam_maps"]}/{a["n"]}', f'{b["cam_maps"]}/{b["n"]}'),
        ('其中领着看了几处（中位数）', num_(a['cam_spots']), num_(b['cam_spots'])),
        ('主目标总数', a['main_n'], b['main_n']),
        ('主目标怎么被发现', dic(a['main']), dic(b['main'])),
        ('主目标亮出时已知区域占比（中位数）', pct(a['main_known']), pct(b['main_known'])),
        ('奖励目标总数', a['bonus_n'], b['bonus_n']),
        ('奖励目标怎么被发现', dic(a['bonus']), dic(b['bonus'])),
        ('敌人第一次露面：开局就在视野里 / 计时出动 / 玩家推进才出动 / 排不出',
         f'{a["fs_open"]} / {a["fs_timed"]} / {a["fs_player"]} / {a["fs_none"]}',
         f'{b["fs_open"]} / {b["fs_timed"]} / {b["fs_player"]} / {b["fs_none"]}'),
        ('其中开局或计时的，露面时刻（中位数，秒）', num_(a['fs_sec']), num_(b['fs_sec'])),
        ('预摆的敌方机动单位：定时出动的比例（每关中位数）', pct(a['timed']), pct(b['timed'])),
        ('　　等玩家触发的比例', pct(a['trig']), pct(b['trig'])),
        ('　　睡着（等触发 + 脚本从不调动）的比例', pct(a['sleep']), pct(b['sleep'])),
        ('关键时刻个数（中位数）', num_(a['moments']), num_(b['moments'])),
        ('已知区域从交还控制到最后一个关键时刻涨了多少（中位数，按上面的近似算）', pct(a['grow']), pct(b['grow'])),
    ]
    out = ['| | 原版 | 我们 |', '|---|---|---|'] + [f'| {r[0]} | {r[1]} | {r[2]} |' for r in rows]
    return '\n'.join(out) + '\n' + SUMMARY_NOTES + '\n'


SUMMARY_NOTES = '''
读这张表：

- **原版几乎每关开场都领着看（36/40），我们 2/11。** 原版的开场过场平均指两处（出生点、第一个目标或敌人），17 关还在过场里把更大的范围（常常是全图）揭开给玩家看一眼、交还控制时再收回（斯大林格勒、直布罗陀是典型）。我们没有开场过场：交还控制就是开局 0 秒，玩家只看得见自己单位周围。
- **交还控制时的已知区域**：原版中位数 24%，我们 11%。原版大的那部分来自开局就永久揭开的出生区（`RevealerWP_MissionStart` 一类）和第一块小边界；我们没有揭图，已知区域只是单位周围一圈。注意：我们的检查构建本来带一条 `Test - reveal`（全图揭开，给测试台用），这里已经剔掉，否则我们每关都是 100%。
- **主目标被领着看过**：原版 48/133（36%），我们 4/30（13%）。原版另有 40 个主目标亮出时标记在玩家还不知道的地方（要自己去找），我们 12 个；我们更多是"标记就在已知区域里"——因为我们的目标多半就在出生点旁边（布局卡第 3 条）。
- **奖励目标**：原版 43 个里 13 个"走近才触发"（发现某物或进某区才亮），15 个亮出时在未知区域，只有 2 个亮出时就看得见；我们 16 个里 8 个在未知区域、3 个走近才触发。差别不在比例，而在原版奖励目标会随推进"冒出来"。
- **敌人第一次露面**：原版 22/40 是玩家推进才出动、15/40 开局就在视野里（预摆的敌方据点）、只有 3/40 靠计时；我们 8/11 靠计时（"开场试探 0:30"一类）。原版预摆的敌方机动单位每关中位数 92% 是"睡着"的（等触发或脚本从不调动，靠自身警戒），我们是 100%——但我们的敌人几乎都是脚本刷出来的，预摆的很少，这一项对我们意义不大。
- **已知区域随推进涨了多少**（原版 +11%，我们 +1%）：这是最粗的一项，玩家推进后的视野只按锚点条件里的区域或物体算，**偏小**；只用来比较"关卡有没有主动揭图"，不要当成玩家真实看到的。
- "交还控制时出生点在已知区域的中间"在已知区域只是出生点周围一圈时是必然的；这一行只在有揭图、有小边界的关才有意义（原版边上 13、角落 10）。

已知的不准确处：

1. **多条路取最早**：一个旗标或计时器有几个来源（主线和兜底路径）时，算法取最早可能的那个，分不出哪条是主线。伊贺"扩蓝边界"挂到了"桥全炸了"的兜底路径上，横滨"奖励目标 2"挂到了"盟军快被打光、苏军提前到场"上（秒数仍对得上）。
2. **"忙碌"旗标当成一直为真**：`FLAG(f_is_audio_playing, 0)` 这类"没在播别的"的门，开局为 0，算法当它一直成立，所以等台词、等别的过场的脚本会排早（宫古岛目标 2 少了一段台词）。
3. **视频和语音长度未知**写成 L；比较"计时器 vs 播完"谁晚时 L 按 15 秒估（伊贺目标 2：手排 28，排出 19.1 + L）。脚本自己用帧数等视频的（研究所 400 帧）会算成具体秒数。
4. **玩家推进的锚点不排先后**：两个互不相干的玩家推进锚点（P3、P7）谁先发生算不出；只有在同一条链上（P7 是在 P3 之后才开始等的）才算"已经发生"。所以某个关键时刻的"已知区域"只包括同一条链上已经发生的揭图和到手的单位。
5. 视野半径 500 是近似；玩家单位会走动，路上看到的不算；揭开又收回的只算"看过一眼"。
6. 开场过场里由脚本单位走进某区域才结束的（直布罗陀、库页岛、隐岐群岛），"交还控制"是个 P 锚点，不是具体秒数。
7. 只排普通难度；简单、困难只在 json 的 difficulty_diffs 里记开局计时上的差别。
'''


# ---------------------------------------------------------------- run
def main():
    parts = sys.argv[1:]
    old = json.load(open(OUT_JSON, encoding='utf-8')) if os.path.exists(OUT_JSON) else {}
    for name, load in LM.jobs(parts):
        try:
            old[name] = measure(name, load())
            r = old[name]
            m0 = r['moments'][0] if r['moments'] else {}
            print(name, 'control', r['opening_camera']['control'], 'known', m0.get('known'), len(r['moments']),
                  'moments', flush=True)
        except Exception as ex:                 # one broken map must not stop the table
            import traceback
            traceback.print_exc()
            print('FAIL', name, repr(ex), flush=True)
            old[name] = dict(map=name, error=repr(ex))
        with open(OUT_JSON, 'w', encoding='utf-8') as fh:
            json.dump(old, fh, ensure_ascii=False, indent=1)
    if 'write_md' in globals():
        write_md(old)


if __name__ == '__main__':
    main()
