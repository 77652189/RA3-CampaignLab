r"""A retail campaign mission in the simulator (ADR 0026 stop condition 2): the plain game's own map, read by name
from MapsCampaign.big, run by sim.Sim with its own scripts -- no cnv Mission, no compile.

  python -I -X utf8 experimental/cnv/retail.py camp_a01_brightonbeach_smith [--until 600] [--level normal]

What is read off the map (mapstudy / mapxml / mapscript / mapterrain, the readers map_study and retail_scripts use):
  players   SidesList: name, human or not, allies / enemies -> Sim.players (p1 = the human, s1 = the human's first
            enemy, every player also under its own name) and Sim.relations both ways
  objects   ObjectsList: every object of a player that is not a civilian one, every named object, every structure
            (a civilian building, a tech building, ore) -- props, decals, sounds and waypoints are not bodies. Owner =
            originalOwner's player, team = its team
  waypoints the waypoint objects by waypointName; their paths (labels: waypointPathLabel1..3, two_way:
            waypointPathBiDirectional, links: WaypointsList by name); trigger areas (TriggerAreas); the borders
            (HeightMapData)
  terrain   the height field (elevation / 16, as the cnv maps'), the water height (GlobalWaterSettings), the engine's
            own impassable cells (BlendTileData bit field 0)
  scripts   PlayerScriptsList as the engine model reads a .map (ra3model scripts.from_mapfile), one list per side in
            SidesList order (the unnamed neutral side first), each with the scripts of the library maps that side
            carries (LibraryMaps, read from the game's Libraries.big: library_lists)
What the simulator does not act on is listed by the run (Sim.unmodeled / Sim.unknown), not dropped quietly.
"""
import argparse
import dataclasses
import functools
import os
import struct

import numpy as np

import sim  # first: it puts experimental/campaign on sys.path
import mapstudy  # noqa: E402
import mapterrain  # noqa: E402
import mapxml  # noqa: E402
import maprender  # noqa: E402
from model import Obj  # noqa: E402

WORLD_PER_E = 0.7               # world height per height-field unit (elevation / 16; platmap's header)
WAYPOINT = '*Waypoints/Waypoint'
CIVILIAN = 'PlayerTemplate:Civilian'
KEEP_KINDS = ('tech', 'ore', 'bridge', 'civ_building')       # mapstudy.kind: unowned things that are bodies


@dataclasses.dataclass
class Goal:
    name: str
    title: str
    bonus: bool


class Terrain:
    """What sim.Ground asks of a map: DIMS (cells: width, height, border), WATERLINE (height-field units), ground().e
    (the whole height field, border included) and impassable() (the engine's own blocked cells)."""

    def __init__(self, m):
        hm = mapterrain.HeightMap(m)
        self.DIMS = (hm.width, hm.height, hm.border)
        self.e = np.array(hm.elev, np.float32).reshape(hm.height, hm.width) / mapterrain.SCALE
        water = mapstudy.water_height(m)
        self.WATERLINE = water / WORLD_PER_E if water is not None else -1e9
        try:
            tiles = mapterrain.Tiles(m, hm.width)
            bits = np.unpackbits(np.frombuffer(bytes(tiles.extra[:tiles.row_bytes * tiles.height]), np.uint8),
                                 bitorder='little').reshape(tiles.height, 8 * tiles.row_bytes)[:, :hm.width]
            self._blocked = bits.astype(bool)
        except (AssertionError, ValueError, StopIteration):
            self._blocked = np.zeros_like(self.e, bool)
        self.BORDERS = {str(k): tuple(v * mapterrain.CELL for v in r)
                        for k, r in enumerate(hm.borders()) if r[2] > r[0] and r[3] > r[1]}

    def ground(self):
        return self

    def impassable(self):
        return self._blocked


def waypoint_links(m, ids):
    """The map's waypoint path links [(from name, to name)] in file order: WaypointsList's head is u32 count, then
    (u32 from, u32 to) waypointIDs; `ids` {waypointID: waypointName}. A link naming no waypoint object is dropped
    (none in retail's 27 campaign maps)."""
    node = next((n for _, n in m.walk() if n.name == 'WaypointsList'), None)
    if node is None:
        return []
    count = struct.unpack_from('<I', node.head)[0]
    assert len(node.head) == 4 + 8 * count, f'WaypointsList: {len(node.head)} bytes for {count} links'
    pairs = (struct.unpack_from('<II', node.head, 4 + 8 * k) for k in range(count))
    return [(ids[a], ids[b]) for a, b in pairs if a in ids and b in ids]


class RetailMission:
    """Duck-types what sim.Sim reads of a cnv Mission (RETAIL tells it apart): .map (PLAYERS, TEAMS, OBJECTS,
    SCENERY, BORDERS and the terrain), objectives, cast / marks / endings (none), sides, relations, merged(),
    script_lists()."""
    RETAIL = True

    def __init__(self, name):
        self.name = name
        self.file = m = maprender.load(name)
        props = mapstudy.players(m)
        self.sides = {n: p for n, p in props.items()}
        human = next((n for n, p in props.items() if p.get('playerIsHuman')), 'Player_1')
        enemies = str(props.get(human, {}).get('playerEnemies', '')).split()
        players = {'p1': human, **({'s1': enemies[0]} if enemies else {}), **{n: n for n in props}}
        self.relations = {}
        for a, p in props.items():
            for b in str(p.get('playerEnemies', '')).split():
                self.relations[(a, b)] = 'Enemy'
            for b in str(p.get('playerAllies', '')).split():
                self.relations[(a, b)] = 'Friend'
        for a in props:                                 # unlisted pairs: neutral (the game's default relation)
            for b in props:
                if a != b:
                    self.relations.setdefault((a, b), 'Neutral')
        civilian = {n for n, p in props.items() if p.get('playerFaction') == CIVILIAN or n == 'PlyrNeutral'}
        objs, self.waypoints, self.skipped = [], {}, 0
        self.labels, self.two_way, ids = {}, set(), {}
        for o in mapxml.objects(m):
            pr = o['props']
            if o['template'] == WAYPOINT:
                wname = str(pr.get('waypointName', ''))
                self.waypoints[wname] = (o['x'], o['y'])
                ids[pr.get('waypointID')] = wname
                labels = [str(pr[k]) for k in ('waypointPathLabel1', 'waypointPathLabel2', 'waypointPathLabel3')
                          if pr.get(k)]
                if labels:
                    self.labels[wname] = labels
                if pr.get('waypointPathBiDirectional'):
                    self.two_way.add(wname)
                continue
            owner, _, team = str(pr.get('originalOwner', '')).partition('/')
            name = str(pr.get('objectName', '') or '')
            kind = mapstudy.kind(o['template'], owner)
            keep = name or (owner in props and owner not in civilian) or kind in KEEP_KINDS or \
                (kind == 'player' and mapstudy._index.get(o['template'].lower(), {}).get('EditorSorting') == 'STRUCTURE')
            if not keep:
                self.skipped += 1
                continue
            extra = {k: v for k, v in pr.items() if k in ('objectInitialHealth',)}
            if team:                                    # sim.Sim: a str originalOwner is the body's team
                extra['originalOwner'] = f'{owner}/{team}'
            objs.append(Obj(o['template'], o['x'], o['y'], side=owner if owner in props else '', name=name,
                            angle=o['angle'], props=extra))
        self.links = waypoint_links(m, ids)
        self.areas = m.trigger_areas()
        terrain = Terrain(m)
        self.map = terrain
        terrain.PLAYERS, terrain.TEAMS, terrain.OBJECTS, terrain.SCENERY = players, {}, objs, []
        try:
            self.objectives = [Goal(g['name'], g['title'], bool(g['bonus'])) for g in m.objectives()]
        except StopIteration:
            self.objectives = []
        self.cast, self.marks, self.endings = {}, {}, []
        lists = len([1 for _, n in m.walk() if n.name == 'ScriptList'])
        # SidesList's first side is the unnamed neutral one (mapstudy.players leaves out the nameless)
        self.order = ([''] if lists == len(props) + 1 else []) + list(props)
        self.libraries = dict(zip(self.order, library_names(m)))
        self.templates = team_templates(m)

    def merged(self, test=None):
        """What sim.Sim takes from parts.merged: no units or objects of our own (the map's are .map.OBJECTS), no
        cnv scripts (script_lists runs the map's own), the map's areas and waypoints."""
        assert test is None, 'a retail mission takes no cnv check'
        return dataclasses.make_dataclass('Merged', ['units', 'objects', 'scripts', 'areas', 'waypoints', 'strings',
                                                     'subtitles', 'templates', 'links', 'labels', 'two_way'])(
            [], [], [], self.areas, self.waypoints, {}, {}, self.templates, self.links, self.labels, self.two_way)

    def script_lists(self, scripts):
        """The map's scripts for the engine model (scripts = ra3model.scripts), one list per side, every name a
        player's list keeps for itself written out in full (scope_names)."""
        lists = scripts.from_mapfile(self.file, self.order)
        for lst in lists:
            if self.libraries.get(lst.side):
                lst.items = with_libraries(scripts, lst.items, library_lists(scripts, self.libraries[lst.side]))
        return scope_names(scripts, lists, set(self.sides))


LIBRARIES = 'Libraries.big'


def team_templates(m):
    """The map's team templates as sim.Sim.reinforce reads them (model.Mission.templates): {'Owner/name': {'units':
    [(template, min, max)], 'instances': teamMaxInstances}}, every team with a unit line."""
    import mapxml
    out = {}
    for t in mapxml.teams(m):
        pr = {k: v[1] for k, v in t.items()}
        units = [(str(pr[f'teamUnitType{k}']).replace('GameObject:', ''), int(pr.get(f'teamUnitMinCount{k}', 0)),
                  int(pr.get(f'teamUnitMaxCount{k}', 0)))
                 for k in range(1, mapxml.TEAM_UNIT_SLOTS + 1) if pr.get(f'teamUnitType{k}')]
        if units:
            out[f'{pr["teamOwner"]}/{pr["teamName"]}'] = {'units': units, 'instances': int(pr.get('teamMaxInstances', 1))}
    return out


def library_names(m):
    """LibraryMaps: one chunk per script list (SidesList order, the unnamed neutral side first -- the 81 retail
    campaign maps: always as many as their script lists), each u32 count, then u16-prefixed paths
    ('Libraries\\Lib_End_Mission\\Lib_End_Mission.map'); the library's short name, lower case."""
    out = []
    for _, n in m.walk():
        if n.name == 'LibraryMaps':
            d, names = n.head, []
            p = 4
            for _ in range(struct.unpack_from('<I', d, 0)[0]):
                k = struct.unpack_from('<H', d, p)[0]
                names.append(d[p + 2:p + 2 + k].decode('ascii').replace('/', '\\').split('\\')[-1][:-4].lower())
                p += 2 + k
            out.append(tuple(names))
    return out


@functools.lru_cache(maxsize=None)
def _library_map(name):
    """The library map `name`, or None when the game does not ship it: Libraries.big holds 29 libraries, and some
    retail maps name one it lacks (lib_yurikoautoheal) -- the game plays those maps, so a missing library adds no
    scripts (INFERRED: not read in the program)."""
    import labpaths
    arc = os.path.join(labpaths.GAME, 'Data', LIBRARIES)
    try:
        return maprender.load(f'{arc}::libraries\\{name}\\{name}.map')
    except KeyError:
        return None


def library_lists(scripts, names):
    """The items of the library maps `names`, in order: a library is a map of one player ('Player') and the unnamed
    neutral side; both lists' items, as the side carrying it would own them. A library the game lacks: none."""
    items = []
    for name in names:
        m = _library_map(name)
        if m is None:
            continue
        props = mapstudy.players(m)
        n = len([1 for _, x in m.walk() if x.name == 'ScriptList'])
        for lst in scripts.from_mapfile(m, ([''] if n == len(props) + 1 else []) + list(props)):
            items += lst.items
    return items


def with_libraries(scripts, own, library):
    """A side's list with its libraries' scripts: the libraries' first, then the map's own; a library script or group
    whose name the map's own list also has is left out -- the map overrides it (the libraries name such scripts
    'Victory Condition (OVERRIDE ME)', one OR of no conditions; the maps that carry Lib_End_Mission write their own
    of that name). Not read in the program: INFERRED from the libraries and maps (order included)."""
    def names(items):
        for it in items:
            yield it.name
            if isinstance(it, scripts.Group):
                yield from names(it.items)
    mine = set(names(own))

    def keep(items):
        out = []
        for it in items:
            if it.name in mine:
                continue
            if isinstance(it, scripts.Group):
                it = dataclasses.replace(it, items=keep(it.items))
            out.append(it)
        return out
    return keep(library) + list(own)


# Argument types (script_catalog.json) whose names a player's script list keeps for itself: script, counter (timers
# are counters), flag, subroutine. Object lists (48; 61 = an object type or an object list) are one table for all
# players, names in any case (Sim.of_types): the 40 retail campaign maps (scan 2026-11-08, engine line round 103)
# define no list on two sides, refer 197 times to a list another side defines (Lib_Object_Lists rides on the neutral
# side or 'PlyrNeutral', the maps' lists on whichever side wrote them) and 308 times in another case
# ('_object list_japan all units' for '_OBJECT LIST_Japan All Units'); read so, none is left unresolved. j01's
# 'AllP1DeadP2IsAI' read an empty list and lost the mission at 0:42; the game plays on. Not read in the program.
SCOPED_ARGS = (2, 4, 5, 13)


def scoped(side, name, players):
    """A name as the game files it: 'Player/name' names that player's own; a bare one (or one whose part before '/'
    is no player) is the list's own player's. The retail campaign's 81 maps (scan 2026-11-08): every 'Player/' reference -- 126 flags, 54 timers, 314 scripts -- names one that player's list sets or
    holds, none another's; of the bare ones 4273 flags / 3408 timers / 6765 scripts are the list's own and 4 in all
    only another list's (taken for slips of the maps'). Not read in the program: INFERRED from the maps. The engine
    model keeps one table of each, so a run's names are written out in full before it reads them."""
    if not side:
        return name                             # ours: one unnamed list, no scopes
    head, sep, _ = name.partition('/')
    return name if sep and head in players else f'{side}/{name}'


def scope_names(scripts, lists, players):
    import json
    import os
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'campaign', 'script_catalog.json'),
              encoding='utf-8') as f:
        types = {k: v['args'] for k, v in json.load(f).items()}

    def walk(items):
        for it in items:
            yield it
            if isinstance(it, scripts.Group):
                yield from walk(it.items)

    def fix(side, c):
        args = list(c.args)
        for k, t in enumerate(types.get(c.name, ())[:len(args)]):
            if isinstance(args[k], str) and t in SCOPED_ARGS:
                args[k] = scoped(side, args[k], players)
        return dataclasses.replace(c, args=tuple(args))

    for lst in lists:
        for it in walk(lst.items):
            it.name = scoped(lst.side, it.name, players)
            if isinstance(it, scripts.Script):
                it.ors = [[fix(lst.side, c) for c in o] for o in it.ors]
                it.actions = [fix(lst.side, c) for c in it.actions]
                it.else_actions = [fix(lst.side, c) for c in it.else_actions]
    return lists


def simulate(name, level='normal', until=600.0):
    return sim.Sim(RetailMission(name), level=level).run(until)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--level', default='normal')
    ap.add_argument('--until', type=float, default=600.0)
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    s = simulate(a.name, a.level, a.until)
    print('\n'.join(s.report(a.all)))


if __name__ == '__main__':
    main()
