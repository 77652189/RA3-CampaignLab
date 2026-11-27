from dataclasses import replace
import json
from pathlib import Path
from xml.etree import ElementTree

import pytest

from experimental.campaign.mapscript import Node
from experimental.mapgen import build as builder, paint, terrain
from experimental.mapgen.build import MapBuild
from experimental.mapgen.buildings import Footprint, Layout, Shape
from experimental.mapgen.checks import draw_failures
from experimental.mapgen.campaign_writer import rules
from experimental.mapgen.design import Design
from experimental.mapgen.dressing import Assets, footpath_flanks
from experimental.mapgen.export import export
from experimental.mappage import viewer
from test_mapgen_terrain import _container


def test_sketch_relations_survive_layout_and_native_build(tmp_path, monkeypatch):
    size = (111, 111, 0)
    monkeypatch.setattr(builder, 'CONTAINER', size)
    monkeypatch.setattr(viewer, 'CONTAINER', size)
    monkeypatch.setattr(paint, 'ART', tmp_path)
    monkeypatch.setattr(builder.labpaths, 'SDK3', tmp_path)
    sage = tmp_path / 'SageXML'
    sage.mkdir()
    (sage / 'House.xml').write_text('<AssetDeclaration><GameObject id="T_House"/></AssetDeclaration>')
    (tmp_path / 'surface.tga').touch()
    shape = {'Type': 'BOX', 'MajorRadius': 24, 'MinorRadius': 24, 'Height': 30}

    def material(name):
        return [{'id': name, 'Texture': 'surface.tga', 'BumpTexture': 'surface.tga'}]

    library = tmp_path / 'library.json'
    library.write_text(json.dumps({
        'kits': {'Test_T': {'buildings': [{'template': 'T_House', 'source': 'House.xml',
                                         'geometry': {'footprint': [shape], 'shapes': [shape]}}],
                            'props': [], 'destructibles': []}},
        'blocking': {'t_house': {'cls': 'all'}},
        'texture_kits': {'Test': {'Grass': material('Grass_Heidelberg01'),
                                  'Sand': material('Sand_SantaMonica01')}},
    }))
    source = tmp_path / 'design.json'
    source.write_text(json.dumps({
        'version': 2,
        'borders': {
            'rim': {'line': [[0, 0], [1000, 0], [1000, 800], [0, 800], [0, 0]]},
            'coast': {'line': [[0, 550], [1000, 550]]},
            'mouth': {'line': [[500, 0], [500, 550]], 'pass': ['ship']},
        },
        'blocks': {
            'bay': {'at': [250, 200], 'height': 3, 'use': 'water', 'kind': 'water'},
            'port': {'at': [750, 200], 'height': 3, 'use': 'water', 'kind': 'water'},
            'yard': {'at': [250, 680], 'height': 3, 'use': 'park', 'protagonist': 'T_House'},
        },
        'points': {'muster': {'at': [250, 680], 'block': 'yard'}},
        'relations': {
            'channel': {'type': '通不通', 'from': 'bay', 'to': 'port', 'who': 'ship', 'only_via': 'mouth'},
            'room': {'type': '放得下', 'point': 'muster', 'side': 40},
        },
    }), encoding='utf-8')

    def expand(level):
        return builder.build(source, library, kit='Test_T', level=level)

    sketch = expand('sketch')
    answers = sketch.check_relations()
    assert answers['channel'].status == 'pass'
    assert answers['room'].status == 'pending' and '需要布局' in answers['room'].decision
    assert sketch.roadbed is None and not sketch.layout.blocks and not sketch.scenery
    page = tmp_path / 'preview'
    viewer.write_preview(page, sketch, title='港口')
    assert '需要布局' in (page / 'index.html').read_text(encoding='utf-8')
    assert 'PASS `channel`' in (page / 'summary.md').read_text(encoding='utf-8')
    assert {p.name for p in page.iterdir()} == {'index.html', 'summary.md', 'built.png'}
    with pytest.raises(ValueError, match='requires a full build'):
        export(sketch, None, None)

    layout = expand('layout')
    assert layout.check_relations()['room'].status == 'fail'  # House overlaps the meeting point.
    full = expand('full')
    assert full.check_relations() == layout.check_relations()
    assert full.check_relations()['channel'] == answers['channel']

    container = _container(*size)
    container.name_id('Object')
    container.name_id('ObjectsList')
    container.nodes.append(Node('ObjectsList', 1, b'', []))
    prepared = tmp_path / 'container.map'
    prepared.write_bytes(container.map_file())

    def encoded(built, name):
        stem = tmp_path / name
        built.write(prepared, stem)
        return tuple((tmp_path / f'{name}-{suffix}').read_bytes()
                     for suffix in ('game.map', 'editor.map', 'locked.json'))

    assert encoded(full, 'first') == encoded(expand('full'), 'second')


def test_harbor_order_checks_each_state_on_the_same_continuous_water():
    sketch = Design({
        'version': 2,
        'blocks': {
            'outer': {'height': 3, 'use': 'water', 'kind': 'water', 'at': [250, 250]},
            'inner': {'height': 3, 'use': 'water', 'kind': 'water', 'at': [650, 210]},
            'land': {'height': 3, 'use': 'park', 'at': [250, 650]},
            'island': {'height': 3, 'use': 'park', 'at': [740, 390]},
        },
        'borders': {
            'frame': {'line': [[0, 0], [1000, 0], [1000, 800], [0, 800], [0, 0]]},
            'coast': {'line': [[0, 550], [1000, 550]]},
            'mouth': {'line': [[500, 0], [500, 550]], 'pass': ['ship']},
            'islandCoast': {'line': [[700, 350], [780, 350], [780, 430], [700, 430], [700, 350]]},
        },
        'states': {'radarLive': {'hold': ['fleetEntry']}, 'radarDown': {}},
        'relations': {
            'wait': {'type': '通不通', 'from': 'outer', 'to': 'inner', 'who': 'ship',
                     'state': 'radarLive', 'order': 'fleetEntry', 'reachable': False},
            'enter': {'type': '通不通', 'from': 'outer', 'to': 'inner', 'who': 'ship',
                      'state': 'radarDown', 'order': 'fleetEntry', 'only_via': 'mouth'},
        },
    })
    plan = terrain.from_design(sketch, terrain.TerrainPlan(), 'test')
    ground = terrain.expand(plan, {'kits': {}}, 160, 140, 30)
    frame = terrain.design_frame(sketch, ground, 0, 30)
    result = MapBuild(plan, frame.close(ground), None, Layout(()), sketch, frame, ())
    assert sketch.check_relations() == {'enter': 'pass', 'wait': 'pass'}
    assert {name: a.status for name, a in result.check_relations().items()} == {'enter': 'pass', 'wait': 'pass'}
    assert ground.waterline[55, 80] - ground.raw[55, 80] >= terrain.SUB_DEPTH * rules.RAW_PER_WORLD
    assert ground.raw[69, 104] > ground.waterline[69, 104]
    ground.raw[51, 95] = 180 * rules.RAW_PER_WORLD
    answers = result.check_relations()
    assert answers['enter'].status == 'fail' and answers['enter'].witness.place == 'inner'
    assert answers['wait'].status == 'pass'


def test_only_way_up_is_checked_on_the_built_grid():
    sketch = Design({
        'version': 2,
        'blocks': {
            'valley': {'height': 3, 'use': 'canyon', 'at': [150, 80]},
            'rim': {'height': 4, 'use': 'canyon', 'at': [150, 330]},
        },
        'borders': {
            'frame': {'line': [[0, 0], [300, 0], [300, 400], [0, 400], [0, 0]]},
            'wall': {'line': [[0, 200], [300, 200]], 'segments': {
                'ramp': {'span': [100, 200], 'pass': ['foot', 'vehicle', 'amphibian']},
            }},
        },
        'relations': {'climb': {'type': '通不通', 'from': 'valley', 'to': 'rim',
                                'who': 'vehicle', 'only_via': 'wall.ramp'}},
    })
    backdrop = terrain.Block(((0, 0), (350, 0), (350, 450), (0, 450)), 3)
    plan = terrain.from_design(sketch, terrain.TerrainPlan(blocks=(backdrop,)), 'test')
    assert plan.blocks[0] is backdrop

    def answers(p):
        ground = terrain.expand(p, {'kits': {}}, 95, 105, 30)
        frame = terrain.design_frame(sketch, ground, 1, 30)
        assert frame.bounds == (0, 0, 30, 40)
        assert not frame.mask[38, 62] and ground.owners[38, 62] == 0
        return MapBuild(p, frame.close(ground), None, Layout(()), sketch, frame, ()).check_relations()

    opened = answers(plan)
    assert opened['climb'].status == 'pass'
    assert opened == answers(plan)
    cut = answers(replace(plan, ramps=()))['climb']
    assert cut.status == 'fail'
    assert 'wall.ramp' in cut.place and 'wall.ramp' in cut.decision
    bypass = terrain.Ramp((40, 110), (0, 1), 1, 40)
    assert answers(replace(plan, ramps=(*plan.ramps, bypass)))['climb'].status == 'fail'

def test_named_footpath_lays_real_flanks_at_its_crossing(tmp_path):
    sketch = Design({
        'version': 2,
        'blocks': {
            'valley': {'height': 3, 'use': 'canyon', 'at': [150, 80]},
            'rim': {'height': 4, 'use': 'canyon', 'at': [150, 330]},
        },
        'borders': {
            'frame': {'line': [[0, 0], [360, 0], [360, 400], [0, 400], [0, 0]]},
            'wall': {'line': [[0, 200], [360, 200]], 'segments': {
                'path': {'from': 'houses', 'to': 'hillPath', 'footpath': 'T_Rock'},
            }},
        },
        'points': {'houses': {'block': 'valley', 'at': [160, 80]},
                   'hillPath': {'block': 'rim', 'at': [220, 320]}},
        'relations': {
            'foot': {'type': '通不通', 'from': 'houses', 'to': 'hillPath',
                     'who': 'foot', 'only_via': 'wall.path'},
            'tank': {'type': '通不通', 'from': 'houses', 'to': 'hillPath',
                     'who': 'vehicle', 'reachable': False},
        },
    })
    plan = terrain.from_design(sketch, terrain.TerrainPlan(), 'test')
    # Halfway between the named sites in Y gives the cut at X=190.
    assert sketch.check_relations() == {'foot': 'pass', 'tank': 'pass'}
    assert plan.ramps[0].low == (190, 110)
    shape = {'Type': 'BOX', 'MajorRadius': 18.75, 'MinorRadius': 9.}
    library = {'kits': {'test': {'props': [{'template': 'T_Rock', 'geometry': {'shapes': [shape]}}],
                                 'buildings': [], 'destructibles': []}},
               'blocking': {'t_rock': {'cls': 'rockbig'}}}
    assets = Assets(library, tmp_path)
    flanks = tuple(p for _, p in footpath_flanks(sketch, assets))
    # The inner edges bound [180, 200]; both props extend into the shoulders of the cut.
    assert [(p.template, p.x, p.y) for p in flanks] == [('T_Rock', 161.25, 200.), ('T_Rock', 218.75, 200.)]
    assert [assets.posed(p).collision[0].point_gap((190., 200.)) for p in flanks] == [10., 10.]
    ground = terrain.expand(plan, library, 97, 101, 30)
    frame = terrain.design_frame(sketch, ground, 0, 30)
    built = MapBuild(plan, frame.close(ground), None, Layout(()), sketch, frame, flanks,
                     footprints=assets.occupied(flanks))
    # The two flanks leave only the x=190 terrain sample free. The adjacent
    # routing columns at x=180 and x=200 are occupied by the measured boxes.
    assert {name: a.status for name, a in built.check_relations().items()} == {'foot': 'fail', 'tank': 'pass'}


def test_failed_channel_draws_its_best_route_bottleneck(tmp_path):
    sketch = Design({
        'version': 2,
        'blocks': {'bay': {'height': 3, 'use': 'water', 'kind': 'water', 'at': [200, 250]},
                   'port': {'height': 3, 'use': 'water', 'kind': 'water', 'at': [800, 250]}},
        'borders': {
            'frame': {'line': [[0, 0], [1000, 0], [1000, 500], [0, 500], [0, 0]]},
            'mouth': {'line': [[500, 0], [500, 500]], 'pass': ['ship']},
        },
        'relations': {'enter': {'type': '通不通', 'from': 'bay', 'to': 'port',
                                'who': 'ship', 'only_via': 'mouth'}},
    })
    plan = terrain.from_design(sketch, terrain.TerrainPlan(), 'test')
    ground = terrain.expand(plan, {'kits': {}}, 161, 111, 30)
    frame = terrain.design_frame(sketch, ground, 0, 30)
    # A shoal cuts the channel. The one deeper cell is the best crossing,
    # even though it lies off the straight line from anchorage to berth.
    ground.raw[30:81, 80] = 190 * rules.RAW_PER_WORLD
    ground.raw[60, 80] = 175 * rules.RAW_PER_WORLD
    result = MapBuild(plan, frame.close(ground), None, Layout(()), sketch, frame, ())
    answers = result.check_relations()
    assert answers['enter'].witness.at == (500, 300)
    assert 'mouth（500, 300）航道水深 25' in answers['enter'].decision
    svg = tmp_path / 'relations.svg'
    draw_failures(sketch, answers, svg)
    root = ElementTree.parse(svg)
    witness = root.find(".//{http://www.w3.org/2000/svg}circle[@data-world-x='500'][@data-world-y='300']")
    assert witness is not None and float(witness.attrib['cx']) > 30


def test_level_boundary_keeps_one_opening():
    sketch = Design({
        'version': 2,
        'blocks': {
            'woods': {'height': 3, 'use': 'woodland', 'at': [150, 120]},
            'clearing': {'height': 3, 'use': 'wildland', 'at': [150, 390]},
        },
        'borders': {
            'edge': {'line': [[0, 0], [450, 0], [450, 500], [0, 500], [0, 0]]},
            'trees': {'line': [[0, 200], [270, 290], [450, 290]], 'pass': [],
                      'segments': {'gap': {'span': [310, 390], 'pass': ['foot']}}},
        },
        'relations': {
            'through': {'type': '通不通', 'from': 'woods', 'to': 'clearing',
                        'who': 'foot', 'only_via': 'trees.gap'},
        },
    })
    plan = terrain.from_design(sketch, terrain.TerrainPlan(), 'test')
    ground = terrain.expand(plan, {'kits': {}}, 106, 111, 30)
    frame = terrain.design_frame(sketch, ground, 0, 30)
    result = MapBuild(plan, frame.close(ground), None, Layout(()), sketch, frame, ())
    assert result.check_relations()['through'].status == 'pass'
    assert ground.raw[53, 40] == ground.raw[59, 63]
    assert ground.blocked[53, 40] and not ground.blocked[59, 63]


def _split_design(*, height=4, coast=False, passage=None):
    wall = {'line': [[0, 400], [1000, 400]]}
    if passage is not None:
        wall.update(passage)
    return {
        'version': 2,
        'blocks': {'south': {'height': 0 if coast else 3, 'use': 'park', 'at': [500, 200]},
                   'north': {'height': height, 'use': 'park', 'at': [500, 600]}},
        'borders': {'frame': {'line': [[0, 0], [1000, 0], [1000, 800], [0, 800], [0, 0]]}, 'wall': wall},
    }


def _expanded(sketch, plan=None, **options):
    plan = plan or terrain.from_design(sketch, terrain.TerrainPlan(), 'test')
    ground = terrain.expand(plan, {'kits': {}}, 160, 140, 30)
    frame = terrain.design_frame(sketch, ground, 0, 30)
    return MapBuild(plan, frame.close(ground), None, Layout(()), sketch, frame, (), **options)


def test_implicit_street_crossing_has_a_ramp():
    data = _split_design()
    data['blocks']['south']['at'] = [400, 200]
    data['blocks']['north']['at'] = [600, 600]
    data['roads'] = {'street': {'line': [[500, 0], [500, 800]], 'width': 'street'}}
    data['relations'] = {'cross': {'type': '通不通', 'from': 'south', 'to': 'north', 'who': 'vehicle'}}
    sketch = Design(data)
    assert sketch.check_relations()['cross'] == 'pass'
    assert _expanded(sketch).plan.ramps == (terrain.Ramp((500, 310), (0, 1), 1, 180),)


def test_sealed_shore_blocks_amphibians():
    data = _split_design(height=3, coast=True, passage={'pass': [], 'closed_reason': 'sealed'})
    data['blocks']['south']['kind'] = 'water'
    data['relations'] = {'cross': {'type': '通不通', 'from': 'south', 'to': 'north',
                                   'who': 'amphibian', 'reachable': False}}
    sketch = Design(data)
    assert sketch.check_relations()['cross'] == 'pass'
    built = _expanded(sketch)
    assert built.check_relations()['cross'].status == 'pass'
    # The closed bank drops one full basin depth, rather than only 4 units per sample.
    assert (terrain.STEP_WORLD * 3 - built.ground.raw[69, 80] / rules.RAW_PER_WORLD) == 80


def test_flank_order_ignores_json_key_order(tmp_path):
    data = _split_design()
    data['points'] = {f'{side}{x}': {'block': side, 'at': [x, y]}
                      for side, y in [('south', 200), ('north', 600)] for x in (210, 710)}
    segments = {str_name: {'from': f'south{x}', 'to': f'north{x}', 'footpath': 'T_Rock'}
                for str_name, x in [('west', 210), ('east', 710)]}
    library = {'kits': {'test': {'buildings': [], 'destructibles': [], 'props': [
        {'template': 'T_Rock', 'geometry': {'shapes': [
            {'Type': 'BOX', 'MajorRadius': 20, 'MinorRadius': 9}]}}]}},
        'blocking': {'t_rock': {'cls': 'rockbig'}}}
    outputs = []
    for order in (segments, dict(reversed(tuple(segments.items())))):
        data['borders']['wall']['segments'] = order
        outputs.append([p.x for _, p in footpath_flanks(Design(data), Assets(library, tmp_path))])
    assert outputs == [[180, 240, 680, 740]] * 2


def test_handwritten_ramp_keeps_other_design_opening():
    data = _split_design(passage={'segments': {
        name: {'span': [x-50, x+50], 'pass': ['foot', 'vehicle', 'amphibian']}
        for name, x in [('west', 250), ('east', 750)]}})
    sketch = Design(data)
    west, east = terrain.from_design(sketch, terrain.TerrainPlan(), 'test').ramps
    assert terrain.from_design(sketch, terrain.TerrainPlan(ramps=(west,)), 'test').ramps == (west, east)


def test_handwritten_ramp_shoulder_cannot_enter_closed_frame():
    data = _split_design(passage={'pass': [], 'closed_reason': 'sealed'})
    data['borders']['frame']['line'] = [[200, 100], [1000, 100], [1000, 800], [200, 800], [200, 100]]
    data['borders']['wall']['line'][0][0] = 200
    sketch = Design(data)
    scenery = tuple(terrain.Block(((0, y), (200, y), (200, y + 400), (0, y + 400)), h)
                    for y, h in ((0, 3), (400, 4)))
    with pytest.raises(ValueError, match='ramp.*outside the playable frame'):
        terrain.from_design(sketch, terrain.TerrainPlan(
            blocks=scenery, ramps=(terrain.Ramp((160, 310), (0, 1), 1, 180),)), 'test')


def test_closed_water_border_is_rejected():
    data = _split_design(height=3, passage={'pass': []})
    for block in data['blocks'].values():
        block['kind'] = 'water'
    with pytest.raises(ValueError, match='wall.*continuous water'):
        Design(data)


def test_implicit_opening_id_is_documented_and_inherits_the_border_state():
    data = _split_design()
    data['blocks']['south']['at'] = [400, 200]
    data['blocks']['north']['at'] = [600, 600]
    data['roads'] = {'street': {'line': [[500, 0], [500, 800]], 'width': 'street'}}
    data['states'] = {'closed': {'pass': {'street': [], 'wall': []}}}
    sketch = Design(data)
    opening, = sketch.spans['wall']
    assert opening == 'wall.road-street' and opening in sketch.via_ids
    assert sketch.base_pass[opening] and not sketch.state_pass['closed'][opening]
    format_doc = Path(__file__).resolve().parents[2] / 'docs/mapgen/format.md'
    instructions = format_doc.read_text(encoding='utf-8')
    assert 'wall.road-street' in instructions and '显式过口保留自己的通行声明' in instructions


def test_layout_rejects_flank_touching_a_nearby_road(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'CONTAINER', (111, 91, 5))
    data = _split_design(height=3, passage={'pass': [], 'segments': {
        'foot': {'from': 'toe', 'to': 'top', 'footpath': 'T_Rock'}}})
    data['points'] = {'toe': {'block': 'south', 'at': [500, 200]},
                      'top': {'block': 'north', 'at': [500, 600]}}
    for block in data['blocks'].values():
        block['ground_texture'] = 'Grass_Heidelberg01'
    data['roads'] = {'lane': {'line': [[350, 430], [650, 430]], 'width': 'street',
                              'ends': ['start', 'end']}}
    shape = {'Type': 'BOX', 'MajorRadius': 20, 'MinorRadius': 20, 'Height': 30}
    library = {'kits': {'Test_T': {'buildings': [], 'destructibles': [], 'props': [
        {'template': 'T_Rock', 'geometry': {'shapes': [shape]}}]}},
        'blocking': {'t_rock': {'cls': 'rockbig'}}}
    catalogue, source = tmp_path / 'library.json', tmp_path / 'design.json'
    catalogue.write_text(json.dumps(library))
    source.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='T_Rock.*enters lane lane'):
        builder.build(source, catalogue, kit='Test_T', level='layout')


def test_missing_native_footprint_stops_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, 'CONTAINER', (111, 91, 5))
    data = _split_design(passage={'closed_reason': 'sealed'})
    data['points'] = {'room': {'block': 'north', 'at': [55, 440]}}
    data['relations'] = {'space': {'type': '放得下', 'point': 'room', 'side': 10}}
    shape = {'Type': 'BOX', 'MajorRadius': 14, 'MinorRadius': 14, 'Height': 30}
    library = {'kits': {'Test_T': {'buildings': [], 'destructibles': [], 'props': [
        {'template': 'T_Cliff', 'geometry': {'shapes': [shape]}}], 'cliffs': [
        dict(template='T_Cliff', height_steps=1, samples=16, length=100, offset_y=-40)]}},
        'blocking': {}}
    catalogue, source = tmp_path / 'library.json', tmp_path / 'design.json'
    source.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def answer():
        catalogue.write_text(json.dumps(library))
        return builder.build(source, catalogue, kit='Test_T', level='layout').check_relations()['space']

    with pytest.raises(ValueError, match='T_Cliff.*no verified SDK footprint and blocking class'):
        answer()
    library['blocking']['t_cliff'] = {'cls': 'all'}
    assert answer().status == 'fail'


def test_net_room_counts_a_solid_flank():
    data = _split_design(height=3)
    data['points'] = {'pad': {'block': 'north', 'at': [500, 600]}}
    data['relations'] = {'space': {'type': '放得下', 'point': 'pad', 'side': 80}}
    stone = Shape('BOX', (500, 600, 0), 15, 15, 0)
    built = _expanded(Design(data), footprints=(Footprint('rockbig', (stone,), (stone,)),))
    assert built.check_relations()['space'].status == 'fail'


def test_route_cannot_fit_a_single_fine_row():
    data = _split_design(height=3)
    data['points'] = {'a': {'block': 'south', 'at': [100, 200]},
                      'b': {'block': 'south', 'at': [900, 200]}}
    data['relations'] = {'route': {'type': '通不通', 'from': 'a', 'to': 'b', 'who': 'vehicle'}}
    built = _expanded(Design(data))
    built.ground.blocked[:, 79:82] = True
    built.ground.blocked[50, 79:82] = False
    assert built.check_relations()['route'].status == 'fail'


def test_unexpanded_state_is_pending_even_if_base_has_room():
    data = _split_design(height=3)
    data['points'] = {'pad': {'block': 'north', 'at': [500, 600]}}
    data['states'] = {'later': {'playable': ['north']}}
    data['relations'] = {'baseRoom': {'type': '放得下', 'point': 'pad', 'side': 80},
                         'laterRoom': {'type': '放得下', 'point': 'pad', 'side': 80, 'state': 'later'}}
    answers = _expanded(Design(data)).check_relations()
    assert [answer.status for answer in answers.values()] == ['pass', 'pending']
