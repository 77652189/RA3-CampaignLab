"""NotifyWhenAttackingBehavior + AttackAssistResponseBehavior (engine/modules/assist.py, engine.orders.order.assist; bench
checks/engine_attackassist.readings.toml b): a firing prism tower calls the one 250 behind it, whose link boosts it
x1.5; a friend without the response module, or past NotifyRadius 350, gives nothing."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402

TOWER, HAMMER = 'AlliedBaseDefenseAdvanced', 'SovietAntiVehicleVehicleTech1'


def _dealt(mate_at, mate=TOWER):
    s = simsmall.small_world([('src', TOWER, 'Player_1', 1000.0, 1000.0), ('mate', mate, 'Player_1', 1000.0, mate_at),
                              ('foe', HAMMER, 'Soviet_1', 1000.0, 1300.0)])
    s.base_power['Player_1'] = 1000
    s.advance(60)
    return s.bodies['src'].dealt, s.bodies['foe'].health


def test_a_linked_tower_deals_half_again_and_only_a_response_module_within_reach_links():
    on, hurt = _dealt(750.0)
    assert hurt < 100.0 and on == 1.5
    assert _dealt(600.0)[0] == 1.0                                  # 400 off: beyond NotifyRadius 350
    assert _dealt(750.0, 'AlliedBaseDefense')[0] == 1.0             # a friend without the modules
