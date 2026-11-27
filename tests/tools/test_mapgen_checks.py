from dataclasses import replace

from experimental.mapgen import terrain
from experimental.mapgen.build import MapBuild
from experimental.mapgen.buildings import Layout
from experimental.mapgen.design import Design


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
