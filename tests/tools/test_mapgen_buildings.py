import math

import numpy as np
import pytest

from experimental.mapgen import roads, terrain
from experimental.mapgen.build import MapBuild
from experimental.mapgen.buildings import BuildingPlanner, Layout
from experimental.mapgen.design import Design, DesignError
from experimental.mapgen.library import _civilian
from experimental.mapgen.terrain import TerrainPlan, expand


@pytest.fixture
def planner(tmp_path):
    base = tmp_path / 'BaseObjects'
    base.mkdir()
    (base / 'BaseHouse.xml').write_text('''
        <AssetDeclaration><GameObject id="BaseHouse">
          <Behaviors><ContestableGarrisonContain id="ModuleTag_Garrison" /></Behaviors>
          <Geometry>
            <Shape Type="BOX" MajorRadius="30" MinorRadius="10" />
            <Shape Type="BOX" MajorRadius="6" MinorRadius="7"><Offset x="40" y="16" /></Shape>
            <PlacementShape Type="BOX" MajorRadius="35" MinorRadius="10" />
            <PlacementShape Type="BOX" MajorRadius="8" MinorRadius="8"><Offset x="40" y="16" /></PlacementShape>
          </Geometry>
        </GameObject></AssetDeclaration>''', encoding='utf8')
    entries = tmp_path / 'Civilian' / 'Town_T' / 'Buildings'
    entries.mkdir(parents=True)
    (entries / 'Buildings.xml').write_text('''
        <AssetDeclaration>
          <GameObject id="T_House" inheritFrom="BaseHouse" />
          <GameObject id="T_HouseAlt" inheritFrom="BaseHouse" />
          <GameObject id="T_Shop">
            <Geometry><Shape Type="BOX" MajorRadius="13" MinorRadius="15" /></Geometry>
          </GameObject>
        </AssetDeclaration>''', encoding='utf8')
    library = {'kits': _civilian(tmp_path, set()), 'blocking': {'t_house': {'cls': 'all'}}}

    def make(depth=130, south='T_House', *, children=False, seed=0):
        sketch = {
            'version': 2,
            'seed': seed,
            'blocks': {
                'south': {'at': [120, 50], 'height': 3, 'use': 'square', 'protagonist': south},
                'north': {'at': [120, 200], 'height': 3, 'use': 'square', 'protagonist': 'T_Shop'},
            },
            'borders': {'frame': {'line': [[0, 0], [240, 0], [240, 320], [0, 320], [0, 0]]}},
            'roads': {'lane': {'line': [[0, depth], [240, depth]], 'width': 'alley'}},
        }
        if children:
            sketch['blocks']['north'] = {'at': [120, 200], 'height': 3, 'use': 'oldtown'}
            sketch['points'] = {'muster': {'block': 'north', 'at': [60, 295]}}
            sketch['blocks'].update(
                row={'parent': 'north', 'use': 'rowhouse', 'frontage': {'road': 'lane'}, 'depth': 100},
                spare={'parent': 'north', 'use': 'reserved', 'point': 'muster', 'size': 30})
            recipe = {'frontage': (30, 100), 'depth': (40, 85), 'textures': {'Test': 1},
                      'contents': {'buildings': {'T_House': 1, 'T_HouseAlt': 1}}}
            library['styles'] = {'Town_T': {'lots': {
                'types': {'house': recipe, 'yard': recipe, 'garden': recipe},
                'mix_by_use': {'oldtown': {'yard': 1, 'garden': 1}}}}}
        design = Design(sketch)
        plan = terrain.from_design(design, TerrainPlan(), 'Town_T')
        ground = expand(plan, library, 25, 33, 0)
        return BuildingPlanner(design, ground, library, dict.fromkeys(design.blocks, 'Town_T'),
                               {'T_House': 0., 'T_HouseAlt': 0., 'T_Shop': 0.}, tmp_path, 0)

    return make


def test_rotated_inherited_footprint_and_door_face_street(planner):
    house = planner().protagonist('south')
    # The local +X front points north. The offset (+40,+16) rotates to (-16,+40).
    assert house.angle == pytest.approx(math.pi / 2)
    assert house.street == 'lane' and house.y < 130
    assert len(house.placement) == len(house.collision) == 2
    assert house.placement[1].center == pytest.approx((house.x - 16, house.y + 40, 0))
    assert house.placement[1].half_x == 8 and house.collision[1].half_x == 6
    assert house.foundation.low == house.foundation.high == 210
    assert house.garrisonable and house.blocking == 'all'


def test_no_fit_reports_block_and_tightest_miss(planner):
    # Road half-width 33.11, two setbacks of 6, and 83 from the combined rotated
    # shapes need 128.11. Dropping the offset shape would wrongly let it fit.
    with pytest.raises(DesignError, match=r'south.*tightest miss T_House.*face setback.*3\.110'):
        planner(depth=125).protagonist('south')


def _children(make):
    planner = make(children=True)
    sketch, catalogue = planner.design, planner.library
    plan = terrain.from_design(sketch, TerrainPlan(), 'Town_T')
    original = planner.ground
    plan, ground, owners, generated = roads.cut_blocks(
        sketch, original, None, plan, catalogue, planner.kits, 0, np.zeros_like(original.blocked))
    return planner, plan, ground, owners, generated


def test_designed_children_keep_their_rings_before_seeded_cut(planner):
    _, plan, ground, owners, generated = _children(planner)
    row, spare = (owners[name][0] for name in ('row', 'spare'))
    assert len(generated) > 1 and {'row', 'spare'}.isdisjoint(generated)
    assert plan.blocks[row].surface.use == 'rowhouse'
    assert plan.blocks[spare].surface.use == 'reserved'
    assert np.all(ground.owners[17:27, 1:24] == row)
    assert np.all(ground.owners[28:32, 5:8] == spare)
    _, again_plan, again_ground, _, again = _children(planner)
    assert generated == again and plan == again_plan
    assert np.array_equal(ground.owners, again_ground.owners)


def test_missing_rowhouse_contents_fail_the_generic_check(planner, monkeypatch):
    monkeypatch.setattr('experimental.mapgen.build.CONTAINER', (25, 33, 0))
    planner, plan, ground, owners, generated = _children(planner)
    index, fronts = owners['row']
    houses = planner.contents('row', ground.owners == index, fronts)
    assert len(houses) >= 2 and all(h.garrisonable for h in houses)
    for group, expected in ((houses, 'pass'), ((), 'fail')):
        layout = Layout((('row', group),))
        result = MapBuild(plan, ground, None, layout, planner.design, None, (), generated=generated)
        assert result.check_relations()['row.contents'].status == expected
