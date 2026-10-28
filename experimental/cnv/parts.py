"""The decoupled build: units, maps, missions and tests declared apart, assembled into a mod by one call.

A unit is a function of its options returning Unit parts (the XML text and what the map compile must know about
it); a map gives the terrain and the start; a mission places objects and writes scripts; a test adds its own
objects, scripts, on-screen counters, the bench steps that run it and the readings it expects. assemble() feeds
them through the CampNew7 pipeline (experimental/campaign: mission slot, map cache, linked map stream, lint) --
the old make_camp*.py chain stays as it was (user 2026-10-21: only new work is written this way).

Each layer talks to the next only through what that one publishes (user 2026-10-22: interface to interface, no
reaching in): a map its SITES (named places) and PLAYERS / TEAMS; a unit its abilities; a mission its cast (who
plays which part, on which sites), its endings, its marks (waypoints by part) and facts (timings). A check asks the
mission (m.site, m.role, m.ability, m.point, m.player), never a mission module's constants or a coordinate of its own; contract() says, before any build, which
script argument names something nobody published.

  python -I -X utf8 experimental/cnv/build.py a8 [--test liberty_jump] [--name CampX]
"""
import collections
import dataclasses
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAMPAIGN = os.path.join(os.path.dirname(HERE), 'campaign')
sys.path.insert(0, CAMPAIGN)


MAX_NAME = 15                           # mod folder names longer than this crash the game at start (see assemble)
COUNTER_LINES = 4                       # counter / countdown lines that fit on the bench's screen (counters.MAX_LINES)


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


NOT = 'NOT'                             # a condition's last item: it is written inverted ('...', NOT)


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
    spawns: set = dataclasses.field(default_factory=set)        # templates its scripts name that nobody casts (a
                                                                # plan's waves and reinforcements, what it counts)
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
        o = Obj(template, *self.site(site, dx, dy), side=side, name=name, site=site, **kw)
        self.objects.append(o)
        if role:
            r = self.cast.setdefault(role, Role(template, name, side))
            assert (r.template, r.name, r.side) == (template, name, side), f'cast {role} is already {r}'
            if site not in r.sites:
                r.sites.append(site)
        return o

    def waypoint(self, part, name, site, dx=0.0, dy=0.0):
        """A waypoint by a map site, published as a mark (scripts aim at it; checks ask m.mark / m.point)."""
        self.waypoints[name] = self.site(site, dx, dy)
        self.marks[part] = name

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
    if m.countdowns and len(test.counters) + len(m.countdowns) > COUNTER_LINES:
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


AREA_ARG = 9                            # script argument type of a trigger area name (script_catalog.json)
# the other argument types contract() holds against what was published
TEAM_ARG, WAYPOINT_ARG, PLAYER_ARG, OBJECT_ARG, STRING_ARG, POWER_ARG, TEMPLATE_ARG = 3, 7, 11, 14, 25, 31, 61
COMMAND_ARG = 34                        # a command button (NAMED_USE_COMMANDBUTTON_ABILITY)
OBJECTIVE_ARG = 91                      # a mission objective's name (SET_MISSION_OBJECTIVE_STATUS ...)
MUSIC_EVENT_ARG = 96                    # a Pathfinder event's name (PATH_MUSIC_PLAY_EVENT): held to Mission.music
CREATES_NAMED = ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION',
                 'UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION')


def missing_areas(mission):
    """Trigger areas the scripts name but nobody declared (the map's own areas are replaced by the mission's)."""
    return [p for p in contract(mission) if ' area ' in p]


def contract(mission):
    """What the mission (merged with its check) uses that nobody published -- checked before any build:
    objects placed by raw coordinates or on a site the map lacks; cast parts naming no object; script arguments
    naming an object, waypoint, trigger area, team, player, string or special power nobody declared, a template
    that is neither cast nor one of the mission's units; a named object fired with a power its unit does not
    publish."""
    import mapscript
    m, cat, out = mission, mapscript.catalog(), []
    sites = getattr(m.map, 'SITES', {})
    named = {o.name: o for o in m.objects if o.name}
    named.update({o.name: o for o in getattr(m.map, 'STRONGPOINTS', {}).values()})     # the map's, published
    out += [f'object {o.template} at ({o.x:g}, {o.y:g}): placed by raw coordinates, not by a map site'
            for o in m.objects if not o.site]
    out += [f'object {o.template}: map has no site {o.site!r}' for o in m.objects if o.site and o.site not in sites]
    # an object a script creates by name is declared by that script (the first argument of the CREATE_NAMED_* ones)
    created = {args[0] for s in m.scripts for name, *args in s.do if name in CREATES_NAMED}
    out += [f'cast {k}: no object named {r.name!r}' for k, r in m.cast.items()
            if r.name and r.name not in named and r.name not in created]
    out += [f'mark {k}: no waypoint {w!r}' for k, w in m.marks.items() if w not in m.waypoints]
    powers = {p: u for u in m.units for p in u.abilities.values()}
    known = {AREA_ARG: ('area', m.areas), TEAM_ARG: ('team', set(getattr(m.map, 'TEAMS', {}).values())),
             WAYPOINT_ARG: ('waypoint', m.waypoints), PLAYER_ARG: ('player', set(getattr(m.map, 'PLAYERS', {}).values())),
             OBJECT_ARG: ('object', set(named) | created), STRING_ARG: ('string', m.strings), POWER_ARG: ('power', powers),
             COMMAND_ARG: ('command button', powers), OBJECTIVE_ARG: ('objective', {g.name for g in m.objectives}),
             TEMPLATE_ARG: ('template', {r.template for r in m.cast.values()} | {u.id for u in m.units} | m.spawns)}
    if m.music:
        known[MUSIC_EVENT_ARG] = ('music event', m.music.events)

    def latin(v):
        try:
            v.encode('latin-1')
            return True
        except UnicodeEncodeError:
            return False
    # the map stores names and script arguments as Latin-1 (only the string table's texts are Unicode): a plan's
    # Chinese in a script name would crash the build (2026-10-24)
    out += [f'script name {s.name!r}: not Latin-1' for s in m.scripts if not latin(s.name)]
    seen = collections.Counter(s.name for s in m.scripts)
    out += [f'script name {k!r}: {n} scripts have it' for k, n in seen.items() if n > 1]
    out += [f'{kind} {v!r}: not Latin-1' for kind, vs in (('object', named), ('waypoint', m.waypoints),
                                                          ('area', m.areas)) for v in vs if not latin(v)]
    out += [f'{s.name}: {name} argument {v!r}: not Latin-1' for s in m.scripts for name, *args in s.when + s.do
            for v in args if isinstance(v, str) and not latin(v)]
    for s in m.scripts:
        for name, *args in s.when + s.do:
            types = cat[name]['args']
            for t, v in zip(types, args):
                if t in known and v not in known[t][1]:
                    out.append(f'{s.name}: {name} {known[t][0]} {v!r} not published')
            own = POWER_ARG if POWER_ARG in types else COMMAND_ARG
            if OBJECT_ARG in types and own in types:                # NAMED_FIRE_SPECIAL_POWER_* / _USE_COMMANDBUTTON_*
                who, power = args[types.index(OBJECT_ARG)], args[types.index(own)]
                if who in named and power in powers and powers[power].id != named[who].template:
                    out.append(f'{s.name}: {who} ({named[who].template}) fired {power}, an ability of {powers[power].id}')
    return out


def write_map(m, mm):
    """The mission (merged) written into the container map: the map's terrain and its own objects (ore, tech,
    bridges: map.OBJECTS), then the mission's waypoints, objects, scripts, trigger areas and objectives."""
    import mapxml
    import newmap
    mm.map.terrain(m)
    for side, props in mm.sides.items():
        mapxml.set_player(m, mm.player(side), **props)
    borders = getattr(mm.map, 'BORDERS', None)
    if borders:                             # MAP_SWITCH_BORDER(k) switches to the k-th; the first is the whole map
        import mapterrain
        hm = mapterrain.HeightMap(m)
        hm.set_borders([tuple(round(v / mapterrain.CELL) for v in r) for r in borders.values()])
        hm.store()
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    tmpl = lambda k: k.head[22:22 + int.from_bytes(k.head[20:22], 'little')].decode('latin-1')   # noqa: E731
    like = mm.map.like(m, objs, tmpl)
    objs.kids = [k for k in objs.kids if tmpl(k) == '*Waypoints/Waypoint']        # the map's starts stay
    wid = 1 + max(newmap.typed_props_of(m, k)[0].get('waypointID', (1, 0))[1] for k in objs.kids)
    for k, (wname, (x, y)) in enumerate(mm.waypoints.items()):
        objs.kids.append(newmap.object_node(m, *like['wp'], '*Waypoints/Waypoint', x, y, waypointName=wname,
                                            waypointID=wid + k, uniqueID=f'Waypoint {wid + k}'))
    # the map's own objects (a bridge's two ends stay next to each other), its scenery (civilian props), the mission's
    for o in list(getattr(mm.map, 'OBJECTS', [])) + list(getattr(mm.map, 'SCENERY', [])) + mm.objects:
        angle = o.angle if o.angle is not None else (1.5708 if o.side == 'p1' else -1.5708)
        extra = dict(o.props, **({'objectName': o.name} if o.name else {}))
        props, flags = like[o.side]
        objs.kids.append(newmap.object_node(m, props, flags if o.flags is None else o.flags, o.template, o.x, o.y,
                                            angle=angle, uniqueID=o.name or f'{o.template} {len(objs.kids)}', **extra))
    ours = [m.new_script(s.name, [m.new_content('Condition', *c[:-1], inverted=True) if c[-1] == NOT else
                                  m.new_content('Condition', *c) for c in s.when]
                         or [m.new_content('Condition', 'CONDITION_TRUE')],
                         [m.new_content('ScriptAction', *a) for a in s.do], one_shot=s.once,
                         difficulties=tuple(s.levels))
            for s in mm.scripts]            # before clearing: chunk versions are read off existing nodes
    newmap.clear_scripts(m)[2].kids += ours
    m.set_trigger_areas(mm.areas)           # the base map's areas went with its scripts
    m.set_objectives([dict(name=g.name, title=g.title, desc=g.desc, bonus=int(g.bonus), flags=1)
                      for g in mm.objectives])


def preview(mission, test=None, out=None):
    """The map a build would make, without compiling or the game (seconds, not the 70 s build): write_map on the
    container map, saved as a .map (default work/maps/<name>.map) for maprender / mapstudy. Returns the path."""
    import make_campnew18 as c18
    from mapscript import MapFile
    mm = merged(mission, test)
    broken = contract(mm)
    assert not broken, 'uses what nobody published:\n  ' + '\n  '.join(broken)
    path, data = next((p, d) for p, d in c18.c6._map_files() if p.lower().endswith('.map'))
    m = MapFile(data)
    write_map(m, mm)
    out = out or os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'maps', mm.name + '.map')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as f:
        f.write(m.map_file())
    return out


def assemble(mission, test=None, name=None):
    """Write the units, set the pipeline up for this mission (+ test) and build the mod; returns the mod folder."""
    import make_campnew18 as c18                # the pipeline (c7 ... c2) and the generated island's start
    c7, c6, c4, c2 = c18.c7, c18.c6, c18.c4, c18.c2
    import newmap
    mm = merged(mission, test)
    name = name or mm.name
    # bench 2026-10-21: the same build as CampLibRidersJump (17) and CampBisjcdXXXXXXX (17) crashed before the main
    # menu (exit 0xC000000D), as CampBisjcd (10) / CampBisjcdXXXX (14) / CampLibertyJump (15) it ran
    assert len(name) <= MAX_NAME, f'mod name {name!r} is {len(name)} characters: the game crashes above {MAX_NAME}'
    assert '_' not in name, f'mod name {name!r}: with an underscore the game crashes at start (CampA7East_What)'
    broken = contract(mm)
    assert not broken, 'uses what nobody published:\n  ' + '\n  '.join(broken)
    c4.NAME = c2.NAME = name
    c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', name, 'data')
    c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', name.lower(), 'data')
    c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', name)
    c7.MAP_MOD = name + 'Map'
    why = mod_busy(name)
    if why:
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', name)
        print(f'{why} -> staging at', c4.OUT)

    import atexit
    release = sdk_build_lock(name)              # one build at a time: the SDK's CNVUnits folder is shared
    atexit.register(release)
    data = os.path.join(c2.SDK, 'Mods', 'CNVUnits', 'Data')
    os.makedirs(data, exist_ok=True)
    seen = set()
    for u in mm.units:
        if u.id in seen:
            continue
        seen.add(u.id)
        for fname, text in {u.id + '.xml': u.xml, **u.files}.items():
            with open(os.path.join(data, fname), 'w', encoding='utf-8', newline='\r\n') as f:
                f.write(text.replace('\r\n', '\n'))
        c7.EXTRA_TEMPLATES[u.id] = {'file': f'DATA:CNVUnits/Data/{u.id}.xml', 'EditorSorting': 'UNIT'}
        # every unit compiled and linked, placed or not: map.xml includes only the object files the map places, and an
        # object creation list or a builder names its template at run time, which the reference walk from the map
        # never reaches (bench 2026-10-22: an OCL made retail's Guardian but nothing of ours the map did not place;
        # the Soviet engineer building one of ours crashed the game)
        if u.id not in {o.template for o in mm.objects}:
            c7.EXTRA_ALL.append(f'DATA:CNVUnits/Data/{u.id}.xml')
        c7.EXTRA_OWN += [f'GameObject:{u.id}'.encode()]
        c7.EXTRA_OWN += [n if isinstance(n, bytes) else n.encode() for n in u.link]
        c7.EXTRA_ALL += [f'DATA:CNVUnits/Data/{f}' for f in u.also]
        c4.c3.STRINGS.update(u.strings)
    for fname, text, link in mm.assets:         # nothing in the map refers to them by file: included and linked
        with open(os.path.join(data, fname), 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(text.replace('\r\n', '\n'))
        c7.EXTRA_ALL.append(f'DATA:CNVUnits/Data/{fname}')
        c7.EXTRA_OWN.append(link.encode())
    c4.c3.STRINGS.update(mm.strings)
    # our music: its map into the static stream, its .mus files into the big, then checked in the spliced stream
    c2.EXTRA_STATIC = [mm.music.include] if mm.music else []
    c4.EXTRA_FILES = list(mm.music.files) if mm.music else []
    c4.CHECKS = [mm.music.check] if mm.music else []

    borders = []

    def edit(m):
        write_map(m, mm)
        import mapterrain
        names = list(getattr(mm.map, 'BORDERS', {}))
        borders[:] = [(names[k] if k < len(names) else str(k), [v * mapterrain.CELL for v in r])
                      for k, r in enumerate(mapterrain.HeightMap(m).borders())]
        print(f'{name}: {len(mm.objects)} objects, {len(mm.waypoints)} waypoints, {len(mm.areas)} areas, '
              f'{len(mm.scripts)} scripts, units {sorted(seen)}')

    c6.edit = edit
    c4.main()
    release()
    write_sidecar(c4.OUT, mm.map.__name__.split('.')[-1], borders)
    return c4.OUT


SIDECAR = 'cnv_map.json'


def write_sidecar(out, map_name, borders):
    """What the bench needs of the built map, next to the mod (testbench/harness.py reads it): the map's borders in
    world units, in MAP_SWITCH_BORDER order -- the minimap draws only the playable one (calib.world_to_minimap)."""
    import json
    with open(os.path.join(out, SIDECAR), 'w', encoding='utf-8') as f:
        json.dump(dict(map=map_name, borders=borders), f, ensure_ascii=False, indent=1)


def mod_busy(name):
    """Why the mod must not be written into Mods now ('' if it may): the user's game is up, or a bench game has this
    mod open. Bench games with other mods do not stop it (several run at once: testbench/slots.py)."""
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'testbench'))
    import slots
    return slots.busy(name)


def sdk_build_lock(name):
    """Wait for the SDK, hold it for this build; returns the release (testbench/slots.build_lock)."""
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'testbench'))
    import slots
    return slots.build_lock(name)


def game_running():
    import subprocess
    out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
    return 'ra3_1.' in out or 'ra3.exe' in out or 'ra3ep1' in out
