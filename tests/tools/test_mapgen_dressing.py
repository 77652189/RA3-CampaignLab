import json
from dataclasses import asdict

import numpy as np
import pytest

from experimental.mapgen import build, dressing, paint
from experimental.mapgen.buildings import Building, Foundation, Layout, Shape
from experimental.mapgen.design import Design, DesignError
from experimental.mapgen.roads import Roadbed
from experimental.mapgen.terrain import Piece, TerrainPlan, expand


@pytest.fixture
def slice_inputs(tmp_path):
    sketch = Design({
        'version': 2,
        'seed': 159,
        'blocks': {'south': {'at': [400, 100], 'height': 3, 'use': 'park'},
                   'north': {'at': [400, 450], 'height': 3, 'use': 'oldtown', 'protagonist': 'T_House'}},
        'borders': {'frame': {'line': [[0, 0], [3300, 0], [3300, 500], [0, 500], [0, 0]]}},
        'roads': {'lane': {'line': [[0, 250], [3300, 250]], 'width': 'street'}},
    })
    footprint = Shape('BOX', (400., 350., 0.), 25., 20., 30.)
    house = Building('T_House', 400., 350., 0., 'lane', True, (footprint,), (footprint,),
                     Foundation(210., 210., 210.), True, 'all')
    layout = Layout((('north', (house,)), ('south', ())))
    library = {'kits': {'Town_T': {'buildings': [], 'destructibles': [], 'props': [
        {'template': 'T_' + name, 'geometry': {'shapes': [{'Type': 'CYLINDER', 'MajorRadius': 4}]}}
        for name in ('Tree', 'Bush', 'Wall')
    ]}}, 'blocking': {'t_tree': {'cls': 'topple'}, 't_bush': {'cls': 'none'}, 't_wall': {'cls': 'all'}}}
    ground = expand(TerrainPlan(), library, 331, 51, 0)
    empty = np.zeros_like(ground.blocked)
    roads = Roadbed('Town_T', (), (), empty, empty.copy())
    return sketch, ground, roads, layout, library, dict.fromkeys(sketch.blocks, 'Town_T'), tmp_path, 0


def test_locked_building_and_output_bytes(slice_inputs):
    layout = slice_inputs[3]
    locked = layout.to_bytes()

    def encoded():
        result = dressing.expand(*slice_inputs)
        ground = slice_inputs[1]
        assert result.ground.raw is ground.raw and result.ground.blocked is ground.blocked
        assert result.ground.waterline is ground.waterline and result.ground.hidden is ground.hidden
        assert result.ground.pieces is ground.pieces
        assert result.pieces
        assert all(p.template != 'T_House' for p in result.pieces)
        return json.dumps([asdict(p) for p in result.pieces], sort_keys=True).encode()

    assert encoded() == encoded()
    assert layout.to_bytes() == locked


def test_prop_on_lane_names_prop_and_lane(slice_inputs):
    sketch, _, roads, layout, library, _, sage, _ = slice_inputs
    with pytest.raises(DesignError, match=r'T_Wall.*enters lane lane'):
        dressing.check_lanes(sketch, roads, layout, [Piece('T_Wall', 200, 250, 0)], library, sage)


def test_busy_frontage_stops_at_its_budget(slice_inputs):
    result = dressing.expand(*slice_inputs)
    counts = {(block, facade): (limit, used) for block, facade, limit, used in result.facades}
    assert counts['north', 'lane'] == (12, 12)
    assert counts['south', 'lane'] == (6, 6)
    assert sum(used for _, used in counts.values()) == len(result.pieces)


def test_block_kit_selects_ground_buildings_and_scenery(tmp_path, monkeypatch):
    monkeypatch.setattr(paint, 'ART', tmp_path)
    monkeypatch.setattr(build.labpaths, 'SDK3', str(tmp_path))
    (tmp_path / 'texture').touch()
    sdk = tmp_path / 'SageXML'
    sdk.mkdir()
    shape = {'Type': 'CYLINDER', 'MajorRadius': 4}
    library = {'kits': {}, 'texture_kits': {}, 'blocking': {}}
    for kit, prefix, tile in (('Town', 'T', 'Grass_Heidelberg01'), ('Port', 'P', 'Grass_Port')):
        house, tree = f'{prefix}_House', f'{prefix}_Tree'
        source = f'{house}.xml'
        (sdk / source).write_text(f'<AssetDeclaration><GameObject id="{house}"/></AssetDeclaration>')
        library['texture_kits'][kit] = {'Grass': [{'id': tile, 'Texture': 'texture', 'BumpTexture': 'texture'}]}
        library['kits'][f'{kit}_{prefix}'] = {
            'buildings': [{'template': house, 'source': source, 'geometry': {'shapes': [shape], 'footprint': [shape]}}],
            'props': [{'template': tree, 'geometry': {'shapes': [shape]}}], 'destructibles': [],
        }
        library['blocking'][tree.lower()] = {'cls': 'none'}
    data = {
        'version': 2,
        'blocks': {
            'town': {'height': 3, 'use': 'woodland', 'at': [400, 350], 'protagonist': 'T_House'},
            'port': {'height': 3, 'use': 'woodland', 'at': [1150, 350], 'protagonist': 'P_House', 'kit': 'Port_P'},
        },
        'borders': {
            'frame': {'line': [[0, 0], [1500, 0], [1500, 700], [0, 700], [0, 0]]},
            'blocks': {'line': [[750, 0], [750, 700]]},
        },
    }
    design_file, library_file = tmp_path / 'design.json', tmp_path / 'library.json'
    design_file.write_text(json.dumps(data))
    library_file.write_text(json.dumps(library))
    result = build.build(design_file, library_file, kit='Town_T')
    assert {piece.template for piece in result.scenery if piece.x > 750} == {'p_tree'}
    assert dict(result.layout.blocks)['port'][0].template == 'P_House'
    assert result.ground.textures[65, 145] == 'Grass_Port'


def test_winter_woods_leave_a_building_pad_and_ice_bare(slice_inputs, tmp_path, monkeypatch):
    monkeypatch.setattr(paint, 'ART', tmp_path)
    monkeypatch.setattr(build.labpaths, 'SDK3', str(tmp_path))
    (tmp_path / 'texture').touch()
    library = slice_inputs[4]
    winter_tiles = (
        'Snow_Solvang01', 'Snow_Iceland04', 'Snow_Solvang08', 'Snow_Solvang10',
        'Snow_Solvang02', 'Snow_Solvang09', 'Snow_Solvang03',
    )
    library['texture_kits'] = {'Town': {'Snow': [
        {'id': tile, 'Texture': 'texture', 'BumpTexture': 'texture'} for tile in winter_tiles
    ]}}
    data = {
        'version': 2,
        'blocks': {
            'woods': {'height': 3, 'use': 'snow_woodland', 'at': [300, 250]},
            'frozen': {'height': 3, 'use': 'ice', 'at': [300, 700]},
        },
        'borders': {
            'edge': {'line': [[0, 0], [600, 0], [600, 950], [0, 950], [0, 0]]},
            'bank': {'line': [[0, 500], [600, 500]], 'pass': ['foot', 'vehicle', 'amphibian']},
        },
        'points': {'pad': {'block': 'woods', 'at': [120, 120]}},
        'relations': {'room': {'type': '放得下', 'point': 'pad', 'side': 200}},
    }
    design_file, library_file = tmp_path / 'design.json', tmp_path / 'library.json'
    design_file.write_text(json.dumps(data))
    library_file.write_text(json.dumps(library))
    result = build.build(design_file, library_file, TerrainPlan(ground='Snow_Solvang01'), kit='Town_T')
    assert {p.template for p in result.scenery} == {'t_tree'}
    assert all(p.y < 500 and max(abs(p.x - 120), abs(p.y - 120)) > 100 for p in result.scenery)
    assert 'Snow_Solvang02' in result.ground.textures[95:115, 45:75]
    assert result.check_relations()['room'].status == 'pass'
