"""The decoupled build: units, maps, missions and tests declared apart, assembled into a mod by one call.

A unit is a function of its options returning Unit parts (the XML text and what the map compile must know about
it); a map gives the terrain and the start; a mission places objects and writes scripts; a test adds its own
objects, scripts, on-screen counters, the bench steps that run it and the readings it expects. assemble() feeds
them through the CampNew7 pipeline (experimental/campaign: mission slot, map cache, linked map stream, lint) --
the old make_camp*.py chain stays as it was (user 2026-10-21: only new work is written this way).

  python -I -X utf8 experimental/cnv/build.py a8 [--test liberty_jump] [--name CampX]
"""
import dataclasses
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAMPAIGN = os.path.join(os.path.dirname(HERE), 'campaign')
sys.path.insert(0, CAMPAIGN)


MAX_NAME = 15                           # mod folder names longer than this crash the game at start (see assemble)


@dataclasses.dataclass
class Unit:
    """One GameObject of ours: its XML file (in the shared CNVUnits/Data folder) and what the compile needs."""
    id: str
    xml: str
    files: dict = dataclasses.field(default_factory=dict)       # more files of this unit: {name: text}
    also: list = dataclasses.field(default_factory=list)        # of those, included type="all" (UI nothing refers to)
    link: list = dataclasses.field(default_factory=list)        # instance names to link though nothing refers to them
    strings: dict = dataclasses.field(default_factory=dict)
    names: dict = dataclasses.field(default_factory=dict)       # ids a mission or test refers to (power, ...)


@dataclasses.dataclass
class Obj:
    template: str
    x: float
    y: float
    side: str = 'p1'                    # p1 (the player) / s1 (the Soviet enemy)
    name: str = ''                      # objectName, for scripts
    angle: float = None                 # default: p1 faces north, s1 south
    props: dict = dataclasses.field(default_factory=dict)       # more object properties (objectInitialHealth ...)


@dataclasses.dataclass
class Script:
    name: str
    when: list                          # conditions, ANDed: ('TIMER_EXPIRED', 'x') ...; [] = every frame
    do: list                            # actions: ('SHOW_MILITARY_CAPTION', 'SCRIPT:X', 5.0) ...
    once: bool = True


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
    map: object = None                  # a maps.* module: terrain(m), START
    objectives: list = dataclasses.field(default_factory=list)  # [(name, title key, description key)]
    names: dict = dataclasses.field(default_factory=dict)       # ids tests refer to (the carrier's power ...)

    def find(self, name):
        return next(o for o in self.objects if o.name == name)


@dataclasses.dataclass
class Test(Part):
    counters: list = dataclasses.field(default_factory=list)    # [(counter, label text)] shown bottom left, in order
    bench: list = dataclasses.field(default_factory=list)       # ra3bench calls after bench_start
    expect: list = dataclasses.field(default_factory=list)      # [(label text, from second, op, value)]


def square(x, y, r):
    """A trigger area: the square of half-side r around (x, y), corners counter-clockwise."""
    return [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]


def counted(counter, label, test, template=None, status=None, area=None, player='Player_1', most=8):
    """A test readout: how many `template`s the player owns (with `area`: how many of them stand in that trigger
    area), or how many of their objects carry `status` ((index, 0.0, name) as in ObjectStatus.xsd's order), shown as
    a game counter -- read as a number by bench_counters instead of counting units in a frame."""
    test.counters.append((counter, label))
    if area:
        test.scripts += [Script(f'Test - count {counter} {n}',
                                [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', player, 2, n, template, area)],
                                [('SET_COUNTER', counter, n)], once=False) for n in range(most)]
    elif template:
        test.scripts.append(Script(f'Test - count {counter}', [],
                                   [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', template, player, counter)], once=False))
    else:
        test.scripts += [Script(f'Test - count {counter} {n}',
                                [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', player, 2, n, status)],
                                [('SET_COUNTER', counter, n)], once=False) for n in range(most)]


def status(name):
    """An ObjectStatus as a script argument: (its index in ObjectStatus.xsd's order, 0.0, name) -- retail's
    UNPACKING is 162, its place in that list."""
    import re
    import labpaths
    p = os.path.join(labpaths.WORK, 'downloads', 'ra3sdk_v3', 'sdk3', 'Schemas', 'xsd', 'Includes', 'ObjectStatus.xsd')
    x = open(p, encoding='utf-8').read()
    x = x[x.index('name="ObjectStatusType"'):]
    names = re.findall(r'value="([A-Z_0-9]+)"', x[:x.index('</xs:simpleType>')])
    assert names.index('UNPACKING') == 162
    return (names.index(name), 0.0, name)


def side_by_side(a, b, dx):
    """Mission b's objects and waypoints moved dx east and added to a (an A/B pair on one map: give the two
    variants different unit tags so their ids differ)."""
    out = dataclasses.replace(a)
    out.units = a.units + b.units
    out.objects = a.objects + [dataclasses.replace(o, x=o.x + dx) for o in b.objects]
    out.waypoints = {**a.waypoints, **{k: (x + dx, y) for k, (x, y) in b.waypoints.items()}}
    out.areas = {**a.areas, **{k: [(x + dx, y) for x, y in pts] for k, pts in b.areas.items()}}
    out.scripts, out.strings = a.scripts + b.scripts, {**a.strings, **b.strings}
    return out


def merged(mission, test=None):
    if test is None:
        return mission
    m = dataclasses.replace(mission)
    for f in ('units', 'objects', 'scripts'):
        setattr(m, f, getattr(mission, f) + getattr(test, f))
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


def missing_areas(mission):
    """Trigger areas the scripts name but nobody declared (the map's own areas are replaced by the mission's)."""
    import mapscript
    cat, out = mapscript.catalog(), []
    for s in mission.scripts:
        for name, *args in s.when + s.do:
            out += [f'{s.name}: {name} -> {v!r}' for t, v in zip(cat[name]['args'], args)
                    if t == AREA_ARG and v not in mission.areas]
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
    assert not missing_areas(mm), f'scripts name undeclared trigger areas: {missing_areas(mm)}'
    c4.NAME = c2.NAME = name
    c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', name, 'data')
    c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', name.lower(), 'data')
    c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', name)
    c7.MAP_MOD = name + 'Map'
    if game_running():
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', name)
        print('RA3 is running -> staging at', c4.OUT)

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
        c7.EXTRA_OWN += [n if isinstance(n, bytes) else n.encode() for n in u.link]
        c7.EXTRA_ALL += [f'DATA:CNVUnits/Data/{f}' for f in u.also]
        c4.c3.STRINGS.update(u.strings)
    c4.c3.STRINGS.update(mm.strings)

    def edit(m):
        mm.map.terrain(m)
        objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
        tmpl = lambda k: k.head[22:22 + int.from_bytes(k.head[20:22], 'little')].decode('latin-1')   # noqa: E731
        like = mm.map.like(m, objs, tmpl)
        objs.kids = [k for k in objs.kids if tmpl(k) == '*Waypoints/Waypoint']        # the map's starts stay
        wid = 1 + max(newmap.typed_props_of(m, k)[0].get('waypointID', (1, 0))[1] for k in objs.kids)
        for k, (wname, (x, y)) in enumerate(mm.waypoints.items()):
            objs.kids.append(newmap.object_node(m, *like['wp'], '*Waypoints/Waypoint', x, y, waypointName=wname,
                                                waypointID=wid + k, uniqueID=f'Waypoint {wid + k}'))
        for o in mm.objects:
            angle = o.angle if o.angle is not None else (1.5708 if o.side == 'p1' else -1.5708)
            extra = dict(o.props, **({'objectName': o.name} if o.name else {}))
            objs.kids.append(newmap.object_node(m, *like[o.side], o.template, o.x, o.y, angle=angle,
                                                uniqueID=o.name or f'{o.template} {len(objs.kids)}', **extra))
        ours = [m.new_script(s.name, [m.new_content('Condition', *c) for c in s.when]
                             or [m.new_content('Condition', 'CONDITION_TRUE')],
                             [m.new_content('ScriptAction', *a) for a in s.do], one_shot=s.once)
                for s in mm.scripts]            # before clearing: chunk versions are read off existing nodes
        newmap.clear_scripts(m)[2].kids += ours
        m.set_trigger_areas(mm.areas)           # the base map's areas went with its scripts
        m.set_objectives([dict(name=n, title=t, desc=d, bonus=0, flags=1) for n, t, d in mm.objectives])
        print(f'{name}: {len(mm.objects)} objects, {len(mm.waypoints)} waypoints, {len(mm.areas)} areas, '
              f'{len(mm.scripts)} scripts, units {sorted(seen)}')

    c6.edit = edit
    c4.main()
    return c4.OUT


def game_running():
    import subprocess
    out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
    return 'ra3_1.' in out or 'ra3.exe' in out or 'ra3ep1' in out
