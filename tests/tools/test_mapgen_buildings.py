import math

import pytest

from experimental.mapgen.buildings import BuildingPlanner
from experimental.mapgen.design import Design, DesignError
from experimental.mapgen.library import _civilian
from experimental.mapgen.roads import ROAD_WIDTH
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
          <GameObject id="T_Shop">
            <Geometry><Shape Type="BOX" MajorRadius="13" MinorRadius="15" /></Geometry>
          </GameObject>
        </AssetDeclaration>''', encoding='utf8')
    library = {'kits': _civilian(tmp_path, set()), 'blocking': {'t_house': {'cls': 'all'}}}

    def make(depth=130, south='T_House', *, junction=False):
        sketch = {
            'version': 2,
            'blocks': {
                'south': {'at': [120, 50], 'height': 3, 'use': 'square', 'protagonist': south},
                'north': {'at': [120, 200], 'height': 3, 'use': 'square', 'protagonist': 'T_Shop'},
            },
            'borders': {'frame': {'line': [[0, 0], [240, 0], [240, 320], [0, 320], [0, 0]]}},
            'roads': {'lane': {'line': [[0, depth], [240, depth]], 'width': 'alley'}},
        }
        if junction:
            sketch['blocks']['south']['at'] = [70, 50]
            sketch['blocks']['north'] = {'at': [120, 200], 'height': 3, 'use': 'oldtown'}
            sketch['roads']['branch'] = {'line': [[120, 0], [120, depth]], 'width': 'alley'}
        design = Design(sketch)
        ground = expand(TerrainPlan(), library, 25, 33, 0)
        return BuildingPlanner(design, ground, library, dict.fromkeys(design.blocks, 'Town_T'),
                               {'T_House': 0., 'T_Shop': 0.}, tmp_path, 0)

    return make


def test_rotated_inherited_footprint_and_door_face_street(planner):
    house, = planner().lock_block('south')
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
        planner(depth=125).lock_block('south')


def test_relock_only_one_block_and_repeat_same_bytes(planner):
    layout = planner().lock()
    assert layout.to_bytes() == planner().lock().to_bytes()
    changed = planner(south='T_Shop')
    relocked = changed.relock(layout, 'south')
    assert dict(relocked.blocks)['north'] is dict(layout.blocks)['north']
    shop, = dict(relocked.blocks)['south']
    assert shop.template == 'T_Shop' and not shop.garrisonable and shop.blocking == 'unknown'
    assert relocked.to_bytes() == changed.lock().to_bytes() != layout.to_bytes()


def test_rowhouses_leave_an_alley_wide_view_across_junction(planner):
    houses = planner(junction=True).lock_block('north')
    assert {h.x > 120 for h in houses} == {False, True}
    assert all(abs(s.center[0] - 120) - s.support(1, 0) >= ROAD_WIDTH['alley'] / 2
               for h in houses for s in h.placement + h.collision)
