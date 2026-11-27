import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

from experimental.mapgen import build, dressing, paint, terrain
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
    roads = Roadbed('Town_T', (), (), empty, empty.copy(), empty.copy())
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
    sketch, *args = slice_inputs
    slot, prop = next(iter(dressing.expand(sketch, *args).slots.items()))
    data = sketch.data | {'patches': {'shift': {'op': 'move', 'slot': slot, 'at': [200, 250]}}}
    with pytest.raises(DesignError, match=rf'{prop.template}.*enters lane lane'):
        dressing.expand(Design(data), *args)


def test_busy_frontage_stops_at_its_budget(slice_inputs):
    result = dressing.expand(*slice_inputs)
    counts = {(block, facade): (limit, used) for block, facade, limit, used in result.facades}
    assert counts['north', 'lane'] == (12, 12)
    assert counts['south', 'lane'] == (6, 6)
    assert sum(used for _, used in counts.values()) == len(result.pieces)


def test_quay_dressing_respects_continuous_authored_paving(slice_inputs, monkeypatch):
    _, _, _, _, library, _, sage, _ = slice_inputs
    kit = 'Town_T'
    monkeypatch.setattr(paint, 'ART', sage)
    (sage / 'tile').touch()

    def tiles(*names):
        return [dict(id=name, Texture='tile', BumpTexture='tile') for name in names]

    library['texture_kits'] = {'Town': {'Road': tiles('CargoApron', 'ContinuousPaving'),
                                        'Grass': tiles('Field'), 'Cliff': tiles('RockFace'),
                                        'Sand': tiles('Sand')}}
    data = {'version': 2, 'blocks': {
        'quay': {'at': [300, 370], 'height': 3, 'use': 'dock'},
        'field': {'at': [300, 480], 'height': 3, 'use': 'wildland'},
        'sea': {'at': [300, 160], 'height': 3, 'use': 'water', 'kind': 'water'},
    }, 'borders': {
        'frame': {'line': [[0, 0], [600, 0], [600, 500], [0, 500], [0, 0]]},
        'shore': {'line': [[0, 300], [600, 300]], 'pass': []},
        'yard': {'line': [[0, 440], [600, 440]], 'pass': ['foot', 'vehicle', 'amphibian']},
    }}

    def finish():
        sketch = Design(data)
        plan = terrain.from_design(sketch, TerrainPlan(ground='Field'), kit)
        ground = paint.paint(plan, library, expand(plan, library, 61, 51, 0))
        return dressing.expand(sketch, ground, None, Layout(()), library,
                               dict.fromkeys(sketch.blocks, kit), sage, 0).ground

    assert finish().textures[37, 30] == 'CargoApron'
    data['blocks']['quay']['ground_texture'] = 'ContinuousPaving'
    ground = finish()
    assert ground.textures[37, 30] == 'ContinuousPaving'
    assert ground.owners[43, 30] != ground.owners[45, 30]
    assert ground.edge_texture(30, 45, 30, 44, 'ContinuousPaving') == 'ContinuousPaving'


def test_bluff_corners_and_camera_margin_get_kit_planting(slice_inputs):
    _, _, _, _, library, _, sage, _ = slice_inputs
    sketch = Design({
        'version': 2,
        'blocks': {'foot': {'at': [250, 250], 'height': 3, 'use': 'woodland'},
                   'top': {'at': [450, 450], 'height': 4, 'use': 'woodland'}},
        'borders': {
            'frame': {'line': [[200, 200], [900, 200], [900, 900], [200, 900], [200, 200]]},
            'rim': {'line': [[300, 300], [600, 300], [600, 600], [300, 600], [300, 300]],
                    'closed_reason': 'bluff'},
        },
    })
    kit = 'Town_T'
    plan = terrain.from_design(sketch, TerrainPlan(), kit)
    ground = expand(plan, library, 111, 111, 0)
    frame = terrain.design_frame(sketch, ground, 0, 0)
    result = dressing.expand(sketch, frame.close(ground), None, Layout(()), library,
                             dict.fromkeys(sketch.blocks, kit), sage, 0, frame)
    # The high face makes four bends, and each puts plants within the face.
    corners = [count for block, name, _, count in result.facades
               if block == 'top' and name.startswith('cliff corner')]
    assert len(corners) == 4 and all(corners)
    assert any(block is None and count for block, _, _, count in result.facades)
    assert result.ground.blocked[50, 18]  # dressing does not open the visible backdrop


def test_woodland_places_stands_beyond_the_open_lot(slice_inputs):
    _, _, _, _, library, _, sage, _ = slice_inputs
    sketch = Design({
        'version': 2,
        'blocks': {'grove': {'at': [450, 450], 'height': 3, 'use': 'woodland'}},
        'borders': {'frame': {'line': [[0, 0], [900, 0], [900, 900], [0, 900], [0, 0]]}},
        'points': {'clearing': {'block': 'grove', 'at': [450, 450]}},
    })
    ground = expand(TerrainPlan(), library, 91, 91, 0)
    result = dressing.expand(sketch, ground, None, Layout(()), library, {'grove': 'Town_T'}, sage, 0)
    # Trees follow the woodland outline, including its far edge beyond any centre clump.
    assert any(p.template == 't_tree' and p.x < 150 for p in result.pieces)


def test_ramp_scrub_follows_steep_shoulders_outside_opening(slice_inputs):
    _, _, _, _, library, _, sage, _ = slice_inputs
    sketch = Design({
        'version': 2,
        'blocks': {'low': {'at': [450, 200], 'height': 3, 'use': 'park'},
                   'high': {'at': [450, 600], 'height': 4, 'use': 'park'}},
        'borders': {
            'frame': {'line': [[0, 0], [900, 0], [900, 800], [0, 800], [0, 0]]},
            'cliff': {'line': [[0, 400], [900, 400]], 'closed_reason': 'scarp',
                      'segments': {'ramp': {'from': 'foot', 'to': 'crest',
                                            'pass': ['foot', 'vehicle', 'amphibian']}}},
        },
        'points': {'foot': {'block': 'low', 'at': [450, 270]},
                   'crest': {'block': 'high', 'at': [450, 530]}},
    })
    kit = 'Town_T'
    ground = expand(terrain.from_design(sketch, TerrainPlan(), kit), library, 91, 81, 0)
    result = dressing.expand(sketch, ground, None, Layout(()), library,
                             dict.fromkeys(sketch.blocks, kit), sage, 0)
    cells = [(round(p.y / 10), round(p.x / 10)) for p in result.pieces if p.template == 't_bush']
    steep_sides = {i * 10 for j, i in cells if ground.ramp_edges[j, i] and ground.blocked[j, i]}
    assert min(steep_sides) < 360 and max(steep_sides) > 540


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


def test_snow_ramp_keeps_its_snow_and_exposed_rock_after_dressing(slice_inputs, monkeypatch):
    _, _, _, _, library, _, sage, _ = slice_inputs
    monkeypatch.setattr(paint, 'ART', sage)
    (sage / 'tile').touch()

    def tiles(*names):
        return [dict(id=name, Texture='tile', BumpTexture='tile') for name in names]

    library['texture_kits'] = {
        'Town': {'Snow': tiles('Snow_Solvang01', 'Snow_Solvang08'),
                 'Dirt': tiles('BareDirt'), 'Grass': tiles('GreenGrass'), 'Cliff': tiles('ExposedRock')},
        'Iceland': {'Snow': tiles('Snow_Iceland04')},  # Outside the local palette.
    }
    sketch = Design({'version': 2, 'blocks': {
        'low': {'at': [450, 200], 'height': 3, 'use': 'snow'},
        'high': {'at': [450, 600], 'height': 4, 'use': 'snow', 'ground_texture': 'Snow_Solvang01'},
    }, 'borders': {
        'frame': {'line': [[0, 0], [900, 0], [900, 800], [0, 800], [0, 0]]},
        'cliff': {'line': [[0, 400], [900, 400]], 'segments': {
            'ramp': {'span': [360, 540], 'pass': ['foot', 'vehicle', 'amphibian']},
        }},
    }})
    plan = terrain.from_design(sketch, TerrainPlan(ground='Snow_Solvang01'), 'Town_T')
    native = expand(plan, library, 91, 81, 0)
    surface = paint.paint(plan, library, native)
    ground = dressing.expand(sketch, surface, None, Layout(()), library,
                             dict.fromkeys(sketch.blocks, 'Town_T'), sage, 0).ground
    assert native.ramp[37, 45] and not native.blocked[37, 45] and ground.textures[37, 45] == 'Snow_Iceland04'
    assert native.ramp[42, 45] and not native.blocked[42, 45] and ground.textures[42, 45] == 'Snow_Solvang01'
    assert native.blocked[37, 35] and ground.textures[37, 35] == 'ExposedRock'
    assert not {'BareDirt', 'GreenGrass'} & set(ground.textures.flat)
    assert ground.raw is native.raw and ground.blocked is native.blocked


def test_patches_apply_to_the_written_scenery_slots(slice_inputs):
    data = slice_inputs[0].data
    args = slice_inputs[1:]
    bad = Design(data | {'patches': {'missing': {'op': 'delete', 'slot': 'south.trees.noSuchSlot'}}})
    with pytest.raises(DesignError, match=r'missing.*south.trees.noSuchSlot'):
        dressing.expand(bad, *args)

    before = dressing.expand(Design(data), *args)
    delete, move, swap = list(before.slots)[:3]
    a, b, c = [before.slots[key] for key in (delete, move, swap)]
    modified = Design(data | {'patches': {
        'drop': {'op': 'delete', 'slot': delete},
        'shift': {'op': 'move', 'slot': move, 'at': [1500, 100]},
        'swap': {'op': 'replace', 'slot': swap, 'with': 'T_Bush'},
    }})
    after = dressing.expand(modified, *args)
    assert a in before.pieces and delete not in after.slots and a not in after.pieces
    assert (after.slots[move].x, after.slots[move].y) == (1500, 100)
    assert after.slots[move].angle == b.angle and after.slots[swap].template == 'T_Bush'
    assert (after.slots[swap].x, after.slots[swap].y) == (c.x, c.y)
    assert tuple(after.slots.values()) == after.pieces
    format_doc = Path(__file__).resolve().parents[2] / 'docs/mapgen/format.md'
    assert '带补丁的全量构建中，`built.scenery_slots` 反映补丁执行后的摆放' in format_doc.read_text(encoding='utf-8')


def test_dressing_cannot_change_weighted_race_distance(tmp_path, monkeypatch):
    monkeypatch.setattr(build, 'CONTAINER', (111, 91, 5))
    monkeypatch.setattr(paint, 'ART', tmp_path)
    (tmp_path / 'tile').touch()
    shape = {'Type': 'BOX', 'MajorRadius': 4, 'MinorRadius': 4, 'Height': 30}
    library = {'kits': {'Test_T': {'buildings': [], 'destructibles': [], 'props': [
        {'template': 'T_Tree', 'geometry': {'shapes': [shape]}},
        {'template': 'T_Block', 'geometry': {'shapes': [shape | {'MajorRadius': 40, 'MinorRadius': 40}]}},
    ]}}, 'blocking': {'t_tree': {'cls': 'none'}, 't_block': {'cls': 'all'}},
        'texture_kits': {'Test': {'Grass': [
            {'id': 'Grass_Heidelberg01', 'Texture': 'tile', 'BumpTexture': 'tile'}]}}}
    data = {'version': 2, 'blocks': {'yard': {'at': [510, 410], 'height': 3, 'use': 'wildland'}},
            'borders': {'rim': {'line': [[0, 0], [1000, 0], [1000, 800], [0, 800], [0, 0]]}}}
    catalogue, source = tmp_path / 'library.json', tmp_path / 'design.json'
    catalogue.write_text(json.dumps(library))

    def make(level='full'):
        source.write_text(json.dumps(data), encoding='utf-8')
        return build.build(source, catalogue, kit='Test_T', level=level)

    slot = next(iter(make().scenery_slots))
    data['points'] = {name: {'at': at, 'block': 'yard'}
                      for name, at in [('a', [500, 220]), ('b', [500, 120]), ('goal', [820, 540])]}
    data['relations'] = {'race': {'type': '谁先到', 'a': 'a', 'b': 'b', 'to': 'goal',
                                  'who': 'vehicle', 'min_lead': 90}}
    data['patches'] = {'block': {'op': 'replace', 'slot': slot, 'with': 'T_Block'}}
    assert make('layout').check_relations()['race'].status == 'pass'
    with pytest.raises(DesignError, match='race.*changes lane race'):
        make()
