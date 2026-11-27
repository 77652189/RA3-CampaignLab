import json
from runpy import run_path
from struct import unpack_from
from types import SimpleNamespace

import numpy as np

from experimental.mapgen import build as builder, paint
from experimental.mapgen.build import MapBuild
from experimental.mapgen.buildings import Layout
from experimental.mapgen.campaign_writer import MapFile, mapterrain
from experimental.mapgen.design import Design
from experimental.mapgen.export import CampaignMap, _interface, module_bytes
from experimental.mapgen.terrain import DesignFrame, TerrainPlan, expand
from test_mapgen_terrain import _container


def test_exported_mission_interface(tmp_path):
    from experimental.cnv import build as cnv
    from model import Script

    data = {
        'version': 2,
        'borders': {
            'rim': {'line': [[0, 0], [4000, 0], [4000, 4000], [0, 4000], [0, 0]]},
            'divide': {'line': [[1800, 0], [1800, 4000]]},
        },
        'blocks': {
            'west': {'at': [900, 2000], 'height': 3, 'use': 'park'},
            'east': {'at': [2700, 2000], 'height': 3, 'use': 'park'},
        },
        'points': {
            'spawn': {'block': 'west', 'at': [1200, 1800]},
            'lookout': {'block': 'east', 'at': [2700, 2200], 'use': 'watch the road'},
        },
        'states': {'eastOnly': {'playable': ['east']}, 'reopened': {}},
        'mission': {
            'starts': {'Player_1_Start': 'spawn'},
            'paths': {'patrol': ['spawn', 'lookout']},
            'regions': {'watchZone': {'point': 'lookout', 'radius': 40}},
        },
    }

    def generate(data):
        frame = DesignFrame(np.empty((500, 500), dtype=bool), (0, 0, 400, 400))
        built = MapBuild(TerrainPlan(), SimpleNamespace(pieces=()), None, Layout(()), Design(data), frame, ())
        return module_bytes(_interface(built, 0))

    source = generate(data)
    reordered = dict(reversed(tuple(data.items())))
    reordered['points'] = dict(reversed(tuple(data['points'].items())))
    reordered['states'] = dict(reversed(tuple(data['states'].items())))
    assert generate(reordered) == source

    path = tmp_path / 'generated.py'
    path.write_bytes(source)
    published = run_path(str(path))
    assert published['SITES']['lookout'].at() == (2700, 2200)
    assert published['STARTS']['Player_1_Start'] == 'spawn'
    borders = list(published['BORDERS'].values())
    assert {name: borders[index] for name, index in published['STATE_BORDERS'].items()} == {
        'base': (0, 0, 4400, 4400),
        'eastOnly': (1400, 0, 4400, 4400),
        'reopened': (0, 0, 4400, 4400),
    }

    mission = published['mission']('GeneratedMap')
    mission.put('AlliedAntiInfantryInfantry', 'spawn', name='Scout')
    mission.scripts.append(Script('Patrol', [('NAMED_INSIDE_AREA', 'Scout', 'watchZone')],
                                  [('NAMED_FOLLOW_WAYPOINTS', 'Scout', 'patrol')]))
    contract = cnv.parts.contract
    assert contract(mission) == []
    mission.scripts.append(Script('Test - missing mark', [], [('MOVE_NAMED_UNIT_TO', 'Scout', 'missing')]))
    assert contract(mission) == ["Test - missing mark: MOVE_NAMED_UNIT_TO waypoint 'missing' not published"]


def test_full_export_replaces_template_texture_table():
    size = (11, 11, 0)
    container = _container(*size)
    tiles = mapterrain.Tiles(container, size[0])
    tiles.blend(0, 0, 'Grass_Heidelberg01', (0, 1, 0, 0))
    tiles.store()

    plan = TerrainPlan(ground='Snow_Iceland03')
    ground = expand(plan, {}, *size)
    ground.textures[:, :5] = 'Snow_Solvang01'
    ground.rank = ('Snow_Iceland03', 'Snow_Solvang01')
    built = MapBuild(plan, ground, None, Layout(()), None, None, ())
    built.apply_terrain(container)
    game, editor, _ = built.outputs(container)

    for raw in (game, editor):
        tiles = mapterrain.Tiles(MapFile(raw), size[0])
        assert set(tiles.textures) == {'Snow_Iceland03', 'Snow_Solvang01'}
        assert (tiles.texture_at(4, 5), tiles.texture_at(5, 5)) == ('Snow_Solvang01', 'Snow_Iceland03')
        used_blends = set(tiles.arrays[1]) - {0}
        assert used_blends == set(range(1, len(tiles.descs) + 1))
        start, cells, _ = tiles.textures['Snow_Iceland03']
        assert used_blends and all(start <= unpack_from('<I', d)[0] // 4 < start + cells for d in tiles.descs)


def test_declared_ore_occupies_the_ground_that_the_module_writes(tmp_path, monkeypatch):
    from experimental.cnv import build as cnv

    monkeypatch.setattr(builder, 'CONTAINER', (111, 91, 5))
    monkeypatch.setattr(paint, 'ART', tmp_path)
    (tmp_path / 'tile').touch()
    data = {'version': 2,
            'borders': {'rim': {'line': [[0, 0], [1000, 0], [1000, 800], [0, 800], [0, 0]]}},
            'blocks': {'yard': {'at': [500, 400], 'height': 3, 'use': 'park'}},
            'points': {'pad': {'block': 'yard', 'at': [350, 350]}, 'clear': {'block': 'yard', 'at': [477, 477]}},
            'mission': {'ore': {'field': {'pad': 'pad', 'node': 'deposit', 'facing': 45}}},
            'relations': {'room': {'type': '放得下', 'point': 'clear', 'side': 40}}}
    shape = {'Type': 'BOX', 'MajorRadius': 30, 'MinorRadius': 30}
    catalogue = {'kits': {'Test_T': {'buildings': [], 'destructibles': [], 'props': [
        {'template': 'OreNode', 'geometry': {'shapes': [shape]}}]}},
        'blocking': {'orenode': {'cls': 'all'}},
        'texture_kits': {'Test': {'Grass': [
            {'id': 'Grass_Heidelberg01', 'Texture': 'tile', 'BumpTexture': 'tile'}]}}}
    source, library = tmp_path / 'design.json', tmp_path / 'library.json'
    source.write_text(json.dumps(data))
    library.write_text(json.dumps(catalogue))
    for level in ('sketch', 'layout', 'full'):
        built = builder.build(source, library, kit='Test_T', level=level)
        assert built.check_relations()['room'].status == 'fail'
    native = CampaignMap('Generated.py', **_interface(built, 5))
    ore, = native.OBJECTS
    assert (ore.template, ore.x, ore.y) == ('OreNode', 477.3, 477.3)
    assert native.SITES['deposit'].at() == (ore.x, ore.y)
    placed, = built.placements()
    assert (placed.template, placed.x, placed.y, placed.angle) == (ore.template, ore.x, ore.y, ore.angle)


def test_moodless_campaign_export_preserves_container_lighting(monkeypatch):
    from experimental.cnv import build as cnv
    from mapscript import Node
    import make_campnew18 as c18
    import mapxml
    import newmap

    m = _container(11, 11, 0)
    for name in newmap.ATMOSPHERE_CHUNKS:
        m.nodes.append(Node(name, 1, b'\x03' if name == 'GlobalLighting' else b'', []))
    m.nodes.append(Node('WorldInfo', 1, mapxml.encode_props(m, {'weather': (1, 0)}), []))
    theme = newmap.read_atmosphere(m)
    lighting = next(n for n in m.nodes if n.name == 'GlobalLighting')
    monkeypatch.setattr(c18, 'generate', lambda m: setattr(lighting, 'head', b'\x01'))
    monkeypatch.setattr(c18, 'PREVIEWS', {})
    monkeypatch.setattr(c18.c7, 'OWN_ATLAS', False)
    native = CampaignMap('Generated.py', {}, [], {}, {}, {}, {}, {}, {}, render=lambda m: {})
    native.terrain(m)
    assert newmap.read_atmosphere(m) == theme
