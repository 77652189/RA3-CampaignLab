"""The StructureSellUpdate module (engine/modules/sell.py, step M10): SellTime read from the block (BaseStructure's
2 s: 30 frames), a sale (simbody.Life.sell: the refund, SOLD) telling it, the structure deleted in the expire cell at
that frame -- not before, not if killed meanwhile -- and its frame read through the body's `sell_end` forward and in
the frame record. The refund and the refusals: tests/test_simbench.py (engine_sell); a civilian house: engine_garrison."""
import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import sell  # noqa: E402


def test_the_block_is_read_seconds_x_15_and_without_a_selltime_two_seconds():
    assert sell.SellData.parse(' SellTime="2.0s"', '').frames == 30
    assert sell.SellData.parse(' SellTime="3s"', '').frames == 45
    assert sell.SellData.parse('', '').frames == 30


def _world():
    return simsmall.small_world([('plant', 'SovietPowerPlant', 'Player_1', 0.0, 0.0),
                                 ('tank', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 300.0, 0.0)])


def test_a_sold_structure_goes_in_the_expire_cell_30_frames_on_deleted_not_killed():
    s = _world()
    plant = s.bodies['plant']
    m = plant.find(interfaces.Sell)
    assert isinstance(m, sell.Sell) and plant.sell_end is None
    assert s.bodies['tank'].find(interfaces.Sell) is None
    now = s.frame_now()
    s.world.schedule.run('expire', now)         # its first run, unsold: asleep (the sale must wake it)
    s.clock.frame = now = now + 1
    s.sell(plant)
    assert plant.sell_end == now + 30 == m.gone_frame() and 'SOLD' in plant.script_status
    assert simrecord.body_state(plant)['sell_end'] == now + 30
    with pytest.raises(AttributeError):
        plant.sell_end = 0
    for f in range(now, now + 30):
        s.world.schedule.run('expire', f)
    assert plant.alive
    s.world.schedule.run('expire', now + 30)
    assert not plant.alive and plant.deleted


def test_a_second_sale_does_nothing_and_one_killed_meanwhile_stays_dead_not_deleted():
    s = _world()
    plant = s.bodies['plant']
    now = s.frame_now()
    s.sell(plant)
    s.clock.frame = now + 10
    s.sell(plant)
    assert plant.sell_end == now + 30 and [w for _, w, *_ in s.log].count('出售') == 1
    s.destroy(plant, 'test')
    s.world.schedule.run('expire', now + 30)
    assert not plant.alive and not plant.deleted
