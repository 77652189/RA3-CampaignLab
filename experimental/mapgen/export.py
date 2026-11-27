"""Write a design's native maps and its generated CNV map module."""

from dataclasses import asdict
from math import ceil, floor
from pathlib import Path
from pprint import pformat
import struct


GROUND_CHUNKS = ('HeightMapData', 'BlendTileData', 'GlobalWaterSettings',
                 'StandingWaterAreas', 'RiverAreas', 'StandingWaveAreas')


class CampaignMap:
    """The same map part used for the initial export and later CNV builds."""

    def __init__(self, module_file, points, objects, regions, borders, state_borders,
                 paths, starts, fields, render=None):
        from maps import island
        from model import Obj, Site, square
        import resources

        self.__name__ = Path(module_file).stem
        self.game_file = Path(module_file).with_name(f'{self.__name__}-game.map')
        self.SITES = {key: Site(*xy, what=what) for key, (xy, what) in points.items()}
        self.OBJECTS = [Obj(template, x, y, side=side, name=name, angle=angle, flags=flags, props={'z': z})
                        for template, x, y, side, name, angle, flags, z in objects]
        self.STRONGPOINTS = {o.name: o for o in self.OBJECTS if o.name}
        self.PLAYERS, self.TEAMS = island.PLAYERS, island.TEAMS
        self.BORDERS, self.STATE_BORDERS = borders, state_borders
        self.PATHS, self.STARTS = paths, starts
        self.FIELDS = []
        for pad, spec in fields.items():
            site = self.SITES[pad]
            field = resources.Field(**spec)
            site.build = field.build
            site.facing = resources.sites([field])[f'{field.name} refinery'].facing
            self.FIELDS.append(field)
        self.REGIONS = {name: tuple(square(*self.SITES[p['point']].at(), p['radius'])) if isinstance(p, dict)
                        else tuple(map(tuple, p)) for name, p in regions.items()}
        self._render = render

    def mission(self, name):
        """Seed the existing mission model with the names already declared by the map."""
        from model import Mission, Script

        m = Mission(name=name, map=self)
        for point in self.SITES:
            m.waypoint(point, point, point)
        m.areas.update({name: list(poly) for name, poly in self.REGIONS.items()})
        for path, points in self.PATHS.items():
            m.path(path, *points)
        if index := self.STATE_BORDERS['base']:
            m.scripts.append(Script('Map design border', [], [('MAP_SWITCH_BORDER', index)]))
        return m

    def terrain(self, m):
        import make_campnew18 as c18
        import mapterrain
        import newmap
        from mapscript import MapFile

        atmosphere = newmap.read_atmosphere(m) if self._render is not None else None
        c18.c7.OWN_ATLAS = True
        c18.generate(m)
        if self._render is not None:
            newmap.apply_atmosphere(m, atmosphere)
            c18.PREVIEWS.update(self._render(m))
        else:
            source = MapFile(self.game_file.read_bytes())
            chunks = {n.name: n for n in source.nodes if n.name in GROUND_CHUNKS}
            m.nodes = [chunks.get(n.name, n) for n in m.nodes]
            newmap.apply_atmosphere(m, newmap.read_atmosphere(source))
            hm = mapterrain.HeightMap(m)
            tiles = mapterrain.Tiles(m, hm.width)
            c18.PREVIEWS.update({key: newmap.preview_tga(hm, tiles, size, depth)
                                 for key, size, depth in (('art', 512, 24), ('small', 128, 32))})

        if self.STARTS:
            starts = {slot: self.SITES[point].at() for slot, point in self.STARTS.items()}
            for _, node in m.walk():
                if node.name == 'Object' and node.head[22:].startswith(b'*Waypoints/Waypoint'):
                    props, _ = newmap.typed_props_of(m, node)
                    slot = props['waypointName'][1]
                    if slot in starts:
                        node.head = struct.pack('<ff', *starts[slot]) + node.head[8:]
            if self._render is None:
                entry = c18.c4.cache_entry

                def cache_entry():
                    data = entry()
                    data['starts'] = [(slot, *starts.get(slot, (x, y)), z) for slot, x, y, z in data['starts']]
                    return data

                c18.c4.cache_entry = cache_entry

    @staticmethod
    def like(m, objs, template):
        from maps import island

        props = island.like(m, objs, template)
        props['road'] = ({'originalOwner': (3, 'PlyrCivilian/teamPlyrCivilian')}, 0)
        return props


def _borders(built, padding, cell, margin):
    """Use the terrain's base frame and enclose each state's selected faces."""
    from experimental.mapgen.design import DesignError

    sketch = built.sketch
    native = built.frame.map_borders(padding)
    whole, base = native[0], native[-1]
    borders = {'<whole map>': whole}
    states = {}
    for state, selected in sketch.playable.items():
        if selected == sketch.playable['base']:
            rect = base
        else:
            if not selected:
                raise DesignError(state, 'playable', 'a native map border needs at least one playable block')
            x, y = zip(*(point for block in selected for point in sketch.rings[block]))
            rect = (max(base[0], floor((min(x) - margin) / cell)),
                    max(base[1], floor((min(y) - margin) / cell)),
                    min(base[2], ceil((max(x) + margin) / cell)),
                    min(base[3], ceil((max(y) + margin) / cell)))
            if rect[0] >= rect[2] or rect[1] >= rect[3]:
                raise DesignError(state, 'playable', 'selected blocks leave no border inside the map')
        if rect not in borders.values():
            borders[state] = rect
        states[state] = list(borders.values()).index(rect)
    return {name: tuple(v * cell for v in rect) for name, rect in borders.items()}, states


def _interface(built, padding):
    from experimental.mapgen.design import DesignError
    from experimental.mapgen.terrain import CELL, FRAME_MARGIN

    sketch = built.sketch
    if sketch is None:
        raise ValueError('map module export requires a design')
    mission = sketch.mission
    points = {name: (tuple(p['at']), p.get('use', name)) for name, p in sketch.points.items()}
    points.update({name: (tuple(xy), name) for name, xy in mission.get('points', {}).items()})
    for node, (_, field, placement) in built.ore.items():
        points[node] = ((float(placement.x), float(placement.y)), f'{field.name} ore')
    starts = dict(mission.get('starts', {}))
    if 'Player_1_Start' in starts:
        for slot in ('InitialCameraPosition', 'Player_2_Start'):
            starts.setdefault(slot, starts['Player_1_Start'])
    borders, states = _borders(built, padding, CELL, FRAME_MARGIN)

    houses = dict(built.layout.blocks)
    named = {}
    for name, block in mission.get('strongpoints', {}).items():
        matches = [p for p in houses.get(block, ()) if p.protagonist and p.garrisonable]
        if len(matches) != 1:
            raise DesignError(name, 'garrison', f'{block} needs exactly one garrisonable protagonist')
        p, = matches
        key = p.template, p.x, p.y
        if key in named:
            raise DesignError(name, 'garrison', f'{block} already exported as {named[key]}')
        named[key] = name
    objects = [(p.template, float(p.x), float(p.y), p.side, named.get((p.template, p.x, p.y), ''),
                float(p.angle), None if p.flags is None else int(p.flags), float(p.z)) for p in built.placements()]
    fields = {pad: asdict(field) for pad, field, _ in built.ore.values()}
    regions = {name: dict(sorted(p.items())) if isinstance(p, dict) else p
               for name, p in mission.get('regions', {}).items()}
    return dict(points=points, objects=objects, regions=regions, borders=borders, state_borders=states,
                paths=mission.get('paths', {}), starts=starts, fields=fields)


def module_bytes(interface):
    """A relocatable module with the ordered border table and literal design data."""
    names = ('SITES', 'OBJECTS', 'STRONGPOINTS', 'PLAYERS', 'TEAMS', 'REGIONS',
             'BORDERS', 'STATE_BORDERS', 'PATHS', 'STARTS', 'FIELDS')
    data = pformat(interface, sort_dicts=False, width=100)
    source = (
        '# Generated by experimental.mapgen.export. Edit the design and regenerate.\n'
        'from pathlib import Path\n'
        'from runpy import run_path\n'
        'from labpaths import ROOT\n\n'
        '_runtime = run_path(str(Path(ROOT) / "experimental/mapgen/export.py"))\n'
        f'MAP = _runtime["CampaignMap"](__file__, **{data})\n\n'
        + ''.join(f'{name} = MAP.{name}\n' for name in names)
        + 'terrain, like, mission = MAP.terrain, MAP.like, MAP.mission\n'
    )
    return source.encode('utf-8')


def export(built, container, stem):
    """Write game/editor maps, a lock and a CNV module next to the game map.

    The input is the normal CNV campaign container, with its player and waypoint
    property templates. The exported maps contain the map part, ready for missions.
    """
    built.require_full()
    from experimental.cnv import build as cnv
    from experimental.mapgen.campaign_writer import MapFile, mapterrain
    from package import write_map

    stem = Path(stem)
    m = MapFile(Path(container).read_bytes())
    interface = _interface(built, mapterrain.HeightMap(m).border)
    module = stem.with_name(f'{stem.name}.py')
    map_part = CampaignMap(module, **interface, render=built.apply_terrain)
    mission = map_part.mission('GeneratedMap')
    errors = cnv.parts.contract(mission)
    if errors:
        raise ValueError('\n'.join(errors))
    write_map(m, mission)
    for suffix, data in zip(('game.map', 'editor.map', 'locked.json'), built.outputs(m), strict=True):
        stem.with_name(f'{stem.name}-{suffix}').write_bytes(data)
    module.write_bytes(module_bytes(interface))
    return module
