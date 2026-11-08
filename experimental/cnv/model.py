"""Layer L2, the mission data: what a unit, a map site, a mission and a check publish, and how a check merges into its
mission -- plain data and the functions that shape it, nothing that writes a map or builds a mod.

Each layer talks to the next only through what that one publishes (user 2026-10-22: interface to interface, no
reaching in): a map its SITES (named places) and PLAYERS / TEAMS; a unit its abilities; a mission its cast (who
plays which part, on which sites), its endings, its marks (waypoints by part) and facts (timings). A check asks the
mission (m.site, m.role, m.ability, m.point, m.player), never a mission module's constants or a coordinate of its own.

Imports neither contract.py nor package.py (tests/test_architecture.py, G-layers). The campaign folder must already
be on sys.path (package.py / parts.py put it there) for _enum's labpaths. Split out of parts.py (ADR 0016).
"""
import dataclasses
import os


MAX_NAME = 15                           # mod folder names longer than this crash the game at start (see assemble)
TEAM_ORDERS = {'attack': 'TEAM_ATTACK_NAMED', 'guard': 'TEAM_GUARD_AREA', 'hunt': 'TEAM_HUNT', 'move': 'MOVE_TEAM_TO',
               'attack_move': 'ATTACK_MOVE_TEAM_TO', 'stop': 'TEAM_STOP'}      # Mission.order: kind -> whole-team action
COUNTER_LINES = 4                      # counter / countdown lines that fit on the bench's screen (counters.MAX_LINES)
# K8 (I4): the ground a camera shows while a scene runs (letterbox on: the picture is a band 2.4 : 1, not the 16 : 9 of
# play). Measured in CampShell 2026-11-05 on A4's demo (work/acceptance/2026-11-05/zh_a4_demo_*.png): 0.39 px a map unit
# in a 320 px wide picture whose band is 135 px tall -> ~820 units wide. Height remeasured 2026-11-07 on the bench
# (A4's demonstration camera, two marks of known world position in one letterbox frame: runs/CampA4_mcp_1107_195947
# frame 38): ~1.42 px a map unit up the screen (the ground is seen at an angle), the band 540 of 720 px -> ~380 units
# tall, not the 345 of taking the sideways scale for both. bench_where (the play camera's fit) is ~50 px off here and
# says 525: do not use it for this. Half of that:
LETTERBOX_HALF = (410.0, 190.0)
LETTERBOX_UNDER = (410.0, 254.0)      # ... and what the camera renders under the bars (16 : 9 at the same zoom): the ground the
                                       # border must cover for the picture to show no black (play's is plan.VIEW_HALF)
STAGE_MARGIN = 40.0                    # what a staged piece shows stands this far inside that band, what it hides this far out
VIEW_HALF = (950.0, 540.0)             # half the ground the screen shows at the default zoom (~1900 x 1080 map units, sapporo
                                       # 'view start', user 2026-11-03): a camera centre nearer the playable border than this
                                       # shows the black beyond it (K5)


def view_rect(borders, half=None):
    """Where a camera centre may be while the playable area is the intersection of `borders` ((x0, y0, x1, y1) each):
    inside it, `half` (VIEW_HALF) from its edges, the middle where it is narrower than the screen. Returned as
    (x0, y0, x1, y1), the rect of centres."""
    x0, y0 = max(b[0] for b in borders), max(b[1] for b in borders)
    x1, y1 = min(b[2] for b in borders), min(b[3] for b in borders)
    out = []
    for lo, hi, h in ((x0, x1, (half or VIEW_HALF)[0]), (y0, y1, (half or VIEW_HALF)[1])):
        lo, hi = (lo + h, hi - h) if hi - lo > 2 * h else ((lo + hi) / 2,) * 2
        out += [lo, hi]
    return out[0], out[2], out[1], out[3]


@dataclasses.dataclass
class Unit:
    """One GameObject of ours: its XML file (in the shared CNVUnits/Data folder) and what the compile needs."""
    id: str
    xml: str
    files: dict = dataclasses.field(default_factory=dict)       # more files of this unit: {name: text}
    also: list = dataclasses.field(default_factory=list)        # of those, included type="all" (UI nothing refers to)
    link: list = dataclasses.field(default_factory=list)        # instance names to link though nothing refers to them
    strings: dict = dataclasses.field(default_factory=dict)
    names: dict = dataclasses.field(default_factory=dict)       # the unit's own ids (its XML's insides)
    abilities: dict = dataclasses.field(default_factory=dict)   # published: {what: special power id} ('jump': ...)
    what: str = ''                                              # published: one line on what it is for
    params: dict = dataclasses.field(default_factory=dict)      # published: the options it was made with


@dataclasses.dataclass
class Site:
    """A place a map publishes: where, how far it reaches, what it is good for. Missions place by site name."""
    x: float
    y: float
    r: float = 0.0
    what: str = ''
    build: float = 0.0                  # > 0: a square this wide here must be flat enough to build on (platmap.lint)
    facing: float = None                # radians: a refinery pad's front, the way its ore lies (resources.py, K4)
    cast: float = 0.0                   # > 0: a spell is cast here (an ice block): this radius stays clear (K3, resources.py)

    def at(self, dx=0.0, dy=0.0):
        return (self.x + dx, self.y + dy)


@dataclasses.dataclass
class Role:
    """A part a mission publishes: who plays it (template), the placed object's name if scripts refer to it, the
    side, the sites it stands on (an unnamed part placed on several: every one)."""
    template: str
    name: str = ''
    side: str = 'p1'
    sites: list = dataclasses.field(default_factory=list)

    @property
    def site(self):
        return self.sites[0]


@dataclasses.dataclass
class Obj:
    template: str
    x: float
    y: float
    side: str = 'p1'                    # p1 (the player) / s1 (the Soviet enemy)
    name: str = ''                      # objectName, for scripts
    angle: float = None                 # default: p1 faces north, s1 south
    props: dict = dataclasses.field(default_factory=dict)       # more object properties (objectInitialHealth ...)
    site: str = ''                      # the map site it was placed by (Mission.put); '' = raw coordinates
    flags: int = None                   # object flags (a bridge's start 16 / end 32); None: those of its side's template


NOT = 'NOT'                             # a condition's last item: it holds when its test does not (unnot)


def unnot(scripts):
    """The scripts with every NOT condition read off a flag instead: the game ignores a condition's inverted bit in
    a map's own scripts (bench 2026-10-29, probe align: an inverted FLAG and an inverted TIMER_EXPIRED both counted
    only once their test held -- our bytes are retail's, which compiles its scripts into the stream, ours are read
    off the .map). Per distinct test two scripts first in the list, every frame: one sets the flag, the next clears
    it while the test holds; the NOT condition becomes FLAG(flag, 1), the same frame."""
    tests = list(dict.fromkeys(tuple(c[:-1]) for s in scripts for c in s.when if c[-1] == NOT))
    flag = {c: f'CNV Not {k}' for k, c in enumerate(tests)}
    first = [x for k, c in enumerate(tests) for x in (
        Script(f'CNV Not {k} - set', [], [('SET_FLAG', flag[c], 1)], once=False),
        Script(f'CNV Not {k} - holds', [c], [('SET_FLAG', flag[c], 0)], once=False))]
    return first + [dataclasses.replace(s, when=[('FLAG', flag[tuple(c[:-1])], 1) if c[-1] == NOT else c
                                                 for c in s.when]) for s in scripts]


@dataclasses.dataclass
class Script:
    name: str
    when: list                          # conditions, ANDed: ('TIMER_EXPIRED', 'x') ...; [] = every frame; one
                                        # ending in NOT holds when its test does not
    do: list                            # actions: ('SHOW_MILITARY_CAPTION', 'SCRIPT:X', 5.0) ...
    once: bool = True
    levels: tuple = (True, True, True)  # the difficulties it runs on (easy, normal, hard): the script header's bits,
                                        # retail's only difficulty switch (no map uses a difficulty condition)


@dataclasses.dataclass
class Goal:
    """A mission objective as the player sees it (the retail way, experimental/campaign/mapstudy.py): announced on
    screen and listed in the pause menu once revealed (status 1; 0 is hidden, 2 done, 3 failed), a green marker on
    each cast part / mark it is about; bonus goals are the yellow optional ones. Revealed `at` seconds into the
    mission, one after another like retail; at=None: the mission reveals it itself (m.reveal)."""
    name: str
    title: str                          # string keys
    desc: str
    bonus: bool = False
    show: tuple = ()                    # cast parts and marks the marker points at ('truck 1', 'exit' ...)
    at: float = 2.0


@dataclasses.dataclass
class Part:
    """What a mission or a test adds: units, objects, waypoints {name: (x, y)}, trigger areas {name: [(x, y) ...]}
    (polygons; square() for the usual one), scripts, strings."""
    units: list = dataclasses.field(default_factory=list)
    objects: list = dataclasses.field(default_factory=list)
    waypoints: dict = dataclasses.field(default_factory=dict)
    areas: dict = dataclasses.field(default_factory=dict)
    scripts: list = dataclasses.field(default_factory=list)
    strings: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class Mission(Part):
    name: str = ''                      # the mod folder (Documents/Red Alert 3/Mods/<name>)
    map: object = None                  # a maps.* module: terrain(m), like(...), SITES, PLAYERS, TEAMS
    objectives: list = dataclasses.field(default_factory=list)  # [Goal]
    cast: dict = dataclasses.field(default_factory=dict)        # published: {part: Role}; a group as 'platform 1' ...
    endings: list = dataclasses.field(default_factory=list)     # published: the names of its win / lose scripts
    marks: dict = dataclasses.field(default_factory=dict)       # published: {part: waypoint name} ('strike' ...)
    facts: dict = dataclasses.field(default_factory=dict)       # published: numbers a check may hold it to (seconds)
    later: set = dataclasses.field(default_factory=set)         # cast parts a script creates in play: their objective
                                                                # markers wait for made(), not the reveal
    countdowns: list = dataclasses.field(default_factory=list)  # published: the timers it shows on screen (countdowns
                                                                # stand above the counters, in the same 4 lines)
    views: dict = dataclasses.field(default_factory=dict)       # {camera waypoint: the rect (x0 y0 x1 y1) its centre may
                                                                # be in}: what a plan's camera moves aim at (K5)
    spells: dict = dataclasses.field(default_factory=dict)      # {waypoint name: site}: where the PLAYER casts a spell
                                                                # (an ice block); the site must keep its cast circle
    stages: list = dataclasses.field(default_factory=list)      # K8: what a staged piece of a scene shows and hides:
                                                                # {label, camera (a view point), see [(what, (x, y))],
                                                                # hide [(what, (x, y))], scripts [names], smoke [names]}
                                                                # clear (Site.cast, contract.cast_points_clear, K3)
    spawns: set = dataclasses.field(default_factory=set)       # templates its scripts name that nobody casts (a
                                                                # plan's waves and reinforcements, what it counts)
    lines: list = dataclasses.field(default_factory=list)       # the plan's spoken captions, in compile order: {说话人,
                                                                # 原文 (the flow script's words, what a dubbed line
                                                                # is looked up by), 通报 (what the caption shows),
                                                                # 字串 (its string key)}
    subtitles: dict = dataclasses.field(default_factory=dict)   # {voice event: string key} the recordings that carry their
                                                                # own subtitle (the dialogue panel shows it); a line is
                                                                # shown there or as a caption, never both (E6)
    teams: dict = dataclasses.field(default_factory=dict)       # {crew key: 'Owner/teamName'} the mission's own teams,
                                                                # written into the map's Teams (Mission.crew, K6)
    sides: dict = dataclasses.field(default_factory=dict)       # {side: {player property: value}} changed in the
                                                                # map's player list (a skirmish AI's faction, its
                                                                # personality: mapxml.set_player)
    assets: list = dataclasses.field(default_factory=list)      # more XML compiled in: [(file name, text, instance
                                                                # to link, 'AIPersonalityDefinition:X')]
    ai_wake: list = dataclasses.field(default_factory=list)     # the scripts that wake its skirmish AI (plan.py
                                                                # 敌方AI): keep_ai_asleep() drops them
    music: object = None                # our Pathfinder map and tracks (experimental/music/pack.Pack: include,
                                        # files, events, check), compiled into the static stream; published: the
                                        # events it plays (PATH_MUSIC_PLAY_EVENT may name only those). None: retail's
    video: object = None                # our movies (experimental/video/pack.Pack: include, files, events, check), the same way
    voice: object = None                # our dubbed lines (experimental/voice/pack.Pack: include, files, events,
                                        # strings, check), compiled into the static stream the same way; a sound
                                        # named CNV_* (PLAY_SOUND_EFFECT, HAS_FINISHED_AUDIO) must be one of its events

    def find(self, name):
        return next(o for o in self.objects if o.name == name)

    def where(self, name):
        """One of the map's sites (a Site: x, y, r, what)."""
        sites = self.map.SITES
        assert name in sites, f'map {self.map.__name__} has no site {name!r}: {sorted(sites)}'
        return sites[name]

    def site(self, name, dx=0.0, dy=0.0):
        """A point by one of the map's sites (offset dx, dy)."""
        return self.where(name).at(dx, dy)

    def strongpoint(self, name):
        """One of the map's strongpoints (its STRONGPOINTS: a building a squad can garrison, placed with the map's
        OBJECTS, platmap.strongpoint): the object's name, for scripts."""
        sp = getattr(self.map, 'STRONGPOINTS', {})
        assert name in sp, f'map {self.map.__name__} has no strongpoint {name!r}: {sorted(sp)}'
        return sp[name].name

    def put(self, template, site, dx=0.0, dy=0.0, role='', side='p1', name='', **kw):
        """Place an object by a map site; with role, publish it in the cast (a named object: scripts refer to it)."""
        pad = getattr(self.map, 'SITES', {}).get(site)
        if pad is not None and pad.facing is not None and template.endswith('Refinery') and kw.get('angle') is None:
            kw['angle'] = pad.facing                        # a refinery stands facing its ore (K4, resources.py)
        o = Obj(template, *self.site(site, dx, dy), side=side, name=name, site=site, **kw)
        self.objects.append(o)
        if role:
            r = self.cast.setdefault(role, Role(template, name, side))
            assert (r.template, r.name, r.side) == (template, name, side), f'cast {role} is already {r}'
            if site not in r.sites:
                r.sites.append(site)
        return o

    def waypoint(self, part, name, site, dx=0.0, dy=0.0, cast=False):
        """A waypoint by a map site, published as a mark (scripts aim at it; checks ask m.mark / m.point). cast: the
        player casts a spell here (an ice block): the waypoint is the site itself, and the site must be a cast point."""
        self.waypoints[name] = self.site(site, dx, dy)
        self.marks[part] = name
        if cast:
            self.spells[name] = site

    def mark(self, part):
        assert part in self.marks, f'mission {self.name} marks no {part!r}: {sorted(self.marks)}'
        return self.marks[part]

    def point(self, part):
        return self.waypoints[self.mark(part)]

    def role(self, part):
        assert part in self.cast, f'mission {self.name} casts no {part!r}: {sorted(self.cast)}'
        return self.cast[part]

    def roles(self, group):
        """A group's parts in order: roles('platform') -> cast 'platform 1', 'platform 2', ..."""
        out, k = [], 1
        while f'{group} {k}' in self.cast:
            out.append(self.cast[f'{group} {k}'])
            k += 1
        return out

    def ability(self, part, what):
        """The special power behind a cast part's published ability ('carrier', 'jump')."""
        t = self.role(part).template
        u = next((u for u in self.units if u.id == t), None)
        assert u and what in u.abilities, f'{part} ({t}) publishes no ability {what!r}: {u and sorted(u.abilities)}'
        return u.abilities[what]

    def param(self, part, what):
        """One of the options a cast part's unit publishes it was made with ('wall', 'lifetime')."""
        t = self.role(part).template
        u = next((u for u in self.units if u.id == t), None)
        assert u and what in u.params, f'{part} ({t}) publishes no param {what!r}: {u and sorted(u.params)}'
        return u.params[what]

    def player(self, side='p1'):
        return self.map.PLAYERS[side]

    def ai_player(self):
        """The player a skirmish AI runs (the side given an aiPersonality: plan.py 敌方AI), or None."""
        side = next((s for s, p in self.sides.items() if 'aiPersonality' in p), None)
        return side and self.player(side)

    def team(self, side='p1'):
        """A side's team to create units on: the map's, else the player's default team (Soviet_2/teamSoviet_2)."""
        if side in self.map.TEAMS:
            return self.map.TEAMS[side]
        p = self.player(side)
        return f'{p}/team{p}'

    def crew(self, key, side='p1'):
        """The team of a group that is ordered as one (a convoy: K6), made on first use, as `side`'s: written into the
        map's Teams, a singleton named after the key. Returns what a script calls it ('Player_1/teamCNVConvoy')."""
        if key not in self.teams:
            owner = self.player(side)
            assert key.isalnum(), f'crew {key!r}: letters and digits only (a team name goes through Latin-1 as a script argument)'
            self.teams[key] = f'{owner}/teamCNV{key}'
        return self.teams[key]

    def order(self, kind, names, target=None, side='p1', crew=None):
        """K6, the one way to tell units what to do (Ctx.order forwards here; ADR 0016): the actions that give the
        group `names` (of `side`) a whole-team order. The group is a team of the map's own (`crew` names it, else it is
        named after the set of names), made on first use. Every order first puts each name on the team
        (UNIT_SET_TEAM), so a member made or released since the last order takes this one as well, and the order is
        to the team: never one command to one unit (contract.single_orders). kind: attack (target a named unit),
        guard (target an area), hunt, move / attack_move (target a waypoint), stop (the team's own members: it adds
        nobody)."""
        verb = TEAM_ORDERS.get(kind)
        assert verb, f'order: no kind {kind!r}: {sorted(TEAM_ORDERS)}'
        names = list(names)
        if not names:
            return []
        team = self.crew(crew or crew_key(names), side)
        if kind == 'stop':
            return [(verb, team)]
        return [('UNIT_SET_TEAM', n, team) for n in names] + [(verb, team) + (() if target is None else (target,))]

    def drop_endings(self):
        """The mission without its win / lose scripts (a check that keeps the counters up)."""
        self.scripts = [s for s in self.scripts if s.name not in self.endings]

    def keep_ai_asleep(self):
        """The mission with its skirmish AI never woken (a check about something else: bench 2026-10-26, a7/pick --
        woken, its army over the river drew the player's tanks off the carrier's landing point)."""
        self.scripts = [s for s in self.scripts if s.name not in self.ai_wake]

    # ---- objectives: actions for the mission's scripts, and the reveal scripts assemble() adds
    def goal(self, name):
        hit = [g for g in self.objectives if g.name == name]
        assert hit, f'no objective {name!r}: {[g.name for g in self.objectives]}'
        return hit[0]

    def markers(self, name, on=True, only=None):
        """Green markers of objective `name` on its cast parts (named objects) and marks (waypoints); only: just
        these parts."""
        out = []
        for part in self.goal(name).show:
            if only is not None and part not in only:
                continue
            if part in self.marks:
                out.append(('LINK_MISSION_OBJECTIVE_TO_WAYPOINT', name, self.marks[part], int(on)))
            else:
                r = self.role(part)
                assert r.name, f'objective {name}: cast part {part!r} is unnamed, a marker needs a named object'
                out.append(('LINK_MISSION_OBJECTIVE_TO_OBJECT', name, r.name, int(on)))
        return out

    def reveal(self, name):
        now = [p for p in self.goal(name).show if p not in self.later]
        return self.markers(name, only=now) + [('SET_MISSION_OBJECTIVE_STATUS', name, 1)]

    def made(self, parts):
        """The markers every objective shows on `parts` (in later), for the script that creates them."""
        return [a for g in self.objectives for a in self.markers(g.name, only=parts)]

    def done(self, name):
        return [('SET_MISSION_OBJECTIVE_STATUS', name, 2)] + self.markers(name, on=False)

    def failed(self, name):
        return [('SET_MISSION_OBJECTIVE_STATUS', name, 3)] + self.markers(name, on=False)

    def goal_scripts(self, gap=4.0):
        """At the start every objective hidden (status 0: written in the map they are listed from the start --
        bench 2026-10-24: stages not yet reached already showed in the mission menu), then one timer; each objective
        with an `at` revealed then, retail-like a few seconds apart so each gets its own announcement. The others
        are revealed by the mission's own scripts (m.reveal)."""
        timed = sorted((g for g in self.objectives if g.at is not None), key=lambda g: g.at)
        timers, reveals, last = [], [], None
        for k, g in enumerate(timed, 1):
            last = g.at if last is None else max(g.at, last + gap)
            timers.append(('SET_MILLISECOND_TIMER', f'CNV Goal Timer {k}', last))
            reveals.append(Script(f'CNV Goals - Reveal {k}', [('TIMER_EXPIRED', f'CNV Goal Timer {k}')],
                                  self.reveal(g.name)))
        hidden = [('SET_MISSION_OBJECTIVE_STATUS', g.name, 0) for g in self.objectives]
        return [Script('CNV Goals - Start', [], hidden + timers)] + reveals if self.objectives else []


@dataclasses.dataclass
class Test(Part):
    counters: list = dataclasses.field(default_factory=list)    # [(counter, label text)] shown bottom left, in order
    bench: list = dataclasses.field(default_factory=list)       # ra3bench calls after bench_start
    expect: list = dataclasses.field(default_factory=list)      # [(label text, from second, op, value)]

def crew_key(names):
    """The key of the team of a group of named units: 'G' and a digest of the sorted names (letters and digits only)."""
    import hashlib
    return 'G' + hashlib.sha1('|'.join(sorted(names)).encode('utf-8')).hexdigest()[:10]


def square(x, y, r):
    """A trigger area: the square of half-side r around (x, y), corners counter-clockwise."""
    return [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]


def counted(counter, label, test, template=None, status=None, area=None, kind=None, player='Player_1', most=8,
            named=None, health=None, owner=None):
    """A test readout: how many `template`s the player owns (with `area`: how many of them stand in that trigger
    area; with `kind` instead of a template -- kindof('VEHICLE') -- how many of that KindOf, but every player's: the
    engine ignores the player in that one, bench 2026-10-25 probe/count), or how many of their
    objects carry `status` ((index, 0.0, name) as in ObjectStatus.xsd's order), shown as a game counter -- read as a
    number by bench_counters instead of counting units in a frame. Counted per value 0 .. most - 1: at `most` or
    more the counter shows `most`. named + area: 1 while that named object is inside the area, else 0 -- for a
    unit that teleports (bench 2026-10-22: after the A7 carrier's jump the type-in-area count of the area it left
    stayed 1 for 35 s; the area it landed in counted it at once). health: that named object's health in percent.
    owner: 1 while that named object belongs to `player`, else 0 -- for a unit that changes hands (bench 2026-10-22:
    a unit the spy's bribe took was counted by its new owner's type count only once the spy died)."""
    test.counters.append((counter, label))
    if owner:                                   # 0 every frame, then 1 if ours (scripts run in order)
        test.scripts += [Script(f'Test - count {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False),
                         Script(f'Test - count {counter} ours', [('NAMED_OWNED_BY_PLAYER', player, owner)],
                                [('SET_COUNTER', counter, 1)], once=False)]
    elif health:
        test.scripts.append(Script(f'Test - count {counter}', [],
                                   [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', health, counter)], once=False))
    elif named:
        test.scripts += [Script(f'Test - count {counter} in', [('NAMED_INSIDE_AREA', named, area)],
                                [('SET_COUNTER', counter, 1)], once=False),
                         Script(f'Test - count {counter} out', [('NAMED_OUTSIDE_AREA', named, area)],
                                [('SET_COUNTER', counter, 0)], once=False)]
    elif area:
        cond = (('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', kind) if kind else
                ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', template))
        test.scripts += [Script(f'Test - count {counter} {n}', [(cond[0], player, 2, n, cond[1], area)],
                                [('SET_COUNTER', counter, n)], once=False) for n in range(most)]
        test.scripts.append(Script(f'Test - count {counter} {most}+', [(cond[0], player, 3, most, cond[1], area)],
                                   [('SET_COUNTER', counter, most)], once=False))
    elif template:
        test.scripts.append(Script(f'Test - count {counter}', [],
                                   [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', template, player, counter)], once=False))
    else:
        test.scripts += [Script(f'Test - count {counter} {n}',
                                [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', player, 2, n, status)],
                                [('SET_COUNTER', counter, n)], once=False) for n in range(most)]


def _enum(xsd, type_name):
    import re
    import labpaths
    p = os.path.join(labpaths.WORK, 'downloads', 'ra3sdk_v3', 'sdk3', 'Schemas', 'xsd', 'Includes', xsd)
    x = open(p, encoding='utf-8').read()
    x = x[x.index(f'name="{type_name}"'):]
    return re.findall(r'value="([A-Z_0-9]+)"', x[:x.index('</xs:simpleType>')])


def status(name):
    """An ObjectStatus as a script argument: (its index in ObjectStatus.xsd's order, 0.0, name) -- retail's
    UNPACKING is 162, its place in that list."""
    names = _enum('ObjectStatus.xsd', 'ObjectStatusType')
    assert names.index('UNPACKING') == 162
    return (names.index(name), 0.0, name)


def kindof(name):
    """A KindOf as a script argument, the same way (retail: STRUCTURE 9, OUTPOST 246)."""
    names = _enum('KindOf.xsd', 'KindOfType')
    assert names.index('STRUCTURE') == 9 and names.index('OUTPOST') == 246
    return (names.index(name), 0.0, name)


def side_by_side(a, b, dx, suffix=''):
    """Mission b's objects and waypoints moved dx east and added to a (an A/B pair on one map: give the two
    variants different unit tags so their ids differ). suffix: appended to b's object names and cast parts, so
    both carriers can be named ('carrier' and 'carrier B')."""
    out = dataclasses.replace(a)
    out.units = a.units + b.units
    out.objects = a.objects + [dataclasses.replace(o, x=o.x + dx, name=o.name and o.name + suffix) for o in b.objects]
    out.cast = {**a.cast, **{k + suffix: dataclasses.replace(r, name=r.name and r.name + suffix)
                             for k, r in b.cast.items()}}
    out.waypoints = {**a.waypoints, **{k: (x + dx, y) for k, (x, y) in b.waypoints.items()}}
    out.areas = {**a.areas, **{k: [(x + dx, y) for x, y in pts] for k, pts in b.areas.items()}}
    out.scripts, out.strings = a.scripts + b.scripts, {**a.strings, **b.strings}
    return out


def merged(mission, test=None):
    """The mission as built: its objectives' reveal scripts first, then (with a test) the test's parts added."""
    m = dataclasses.replace(mission, scripts=mission.goal_scripts() + mission.scripts)
    if test is None:
        return m
    for f in ('units', 'objects', 'scripts'):
        setattr(m, f, getattr(m, f) + getattr(test, f))
    if test.counters and m.countdowns and len(test.counters) + len(m.countdowns) > COUNTER_LINES:     # as contract.observes
        # the counters must stay readable: a countdown would push the last one off the screen (bench 2026-10-24)
        m.scripts = m.scripts + [Script('Test - countdowns off', [], [('HIDE_COUNTDOWN_TIMER', c) for c in m.countdowns],
                                        once=False)]
    m.waypoints = {**mission.waypoints, **test.waypoints}
    m.areas = {**mission.areas, **test.areas}
    m.strings = {**mission.strings, **test.strings}
    assert len(test.counters) <= 4, 'only four counter lines fit above the bottom bar (counters.MAX_LINES)'
    keys = [f'SCRIPT:CNVTEST_COUNTER{k}' for k in range(len(test.counters))]
    m.strings.update({k: label for k, (_, label) in zip(keys, test.counters)})
    if test.counters:
        m.scripts = m.scripts + [Script('Test - counters', [], [('DISPLAY_COUNTER', c, k)
                                                                for k, (c, _) in zip(keys, test.counters)])]
    return m
