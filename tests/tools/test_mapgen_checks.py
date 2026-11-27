from dataclasses import replace

from experimental.mapgen import terrain
from experimental.mapgen.build import MapBuild
from experimental.mapgen.buildings import Layout
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
