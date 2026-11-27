from dataclasses import replace
from xml.etree import ElementTree

from experimental.mapgen import terrain
from experimental.mapgen.build import MapBuild
from experimental.mapgen.buildings import Layout
from experimental.mapgen.checks import draw_failures
from experimental.mapgen.campaign_writer import rules
from experimental.mapgen.design import Design


def test_harbor_mouth_does_not_create_a_bank_in_continuous_water():
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
        'relations': {'enter': {'type': '通不通', 'from': 'outer', 'to': 'inner',
                                'who': 'ship', 'only_via': 'mouth'}},
    })
    plan = terrain.from_design(sketch, terrain.TerrainPlan(), 'test')
    ground = terrain.expand(plan, {'kits': {}}, 160, 140, 30)
    frame = terrain.design_frame(sketch, ground, 0, 30)
    result = MapBuild(plan, frame.close(ground), None, Layout(()), sketch, frame, ())
    assert result.check_relations()['enter'].status == 'pass'
    assert ground.waterline[55, 80] - ground.raw[55, 80] >= terrain.SUB_DEPTH * rules.RAW_PER_WORLD
    assert ground.raw[69, 104] > ground.waterline[69, 104]


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

def test_named_foot_ramp_locates_the_narrow_cut_and_checks_real_passage():
    sketch = Design({
        'version': 2,
        'blocks': {
            'valley': {'height': 3, 'use': 'canyon', 'at': [150, 80]},
            'rim': {'height': 4, 'use': 'canyon', 'at': [150, 330]},
        },
        'borders': {
            'frame': {'line': [[0, 0], [360, 0], [360, 400], [0, 400], [0, 0]]},
            'wall': {'line': [[0, 200], [360, 200]], 'segments': {
                'path': {'from': 'houses', 'to': 'hillPath', 'pass': ['foot']},
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
    assert plan.ramps[0].width == 20 and plan.ramps[0].narrow
    ground = terrain.expand(plan, {'kits': {}}, 97, 101, 30)
    frame = terrain.design_frame(sketch, ground, 0, 30)
    built = MapBuild(plan, frame.close(ground), None, Layout(()), sketch, frame, ())
    assert {name: a.status for name, a in built.check_relations().items()} == {'foot': 'pass', 'tank': 'fail'}


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
