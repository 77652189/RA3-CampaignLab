"""engine.modules.aiupdate (cmd_pack C2a): AIOrderState, HOLD_FIRE's kept attack (stance.md a / b / f)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402


def test_hold_fire_keeps_an_attack_unfired_till_another_stance_or_order():
    s = simsmall.small_world([('a', 'SovietAntiVehicleVehicleTech3', 'Player_1', 0.0, 0.0)], model=False)
    a = s.bodies['a']
    a.aiupdate.set_stance(3, True)                      # on an object: kept, not fired
    a.aiupdate.set_stance(3, False)                     # no change of hold: the pause stays
    assert (a.stance, a.hold_fire, a.hold_paused) == (3, True, True)
    a.aiupdate.set_stance(1, True)                      # another stance: it fires again
    assert (a.stance, a.hold_fire, a.hold_paused) == (1, False, False)
    a.aiupdate.set_stance(3, True)
    assert s.order_attack(a, a, True) and not a.hold_paused     # an order under HOLD_FIRE fires
    a.aiupdate.set_auto_acquire(True)
    assert a.ai_acquire
