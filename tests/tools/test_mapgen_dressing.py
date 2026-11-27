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
