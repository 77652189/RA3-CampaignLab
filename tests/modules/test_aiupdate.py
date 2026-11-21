"""engine.modules.aiupdate (cmd_pack C2): AIOrderState, HOLD_FIRE's kept attack (stance.md a / b / f), an order's writes."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.ports.observe import Observe  # noqa: E402


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


def test_an_orders_writes_and_what_attaches_one():    # C2b
    s = simsmall.small_world([('a', 'SovietAntiVehicleVehicleTech3', 'Player_1', 0.0, 0.0),
                              ('p', 'AlliedPowerPlant', 'Player_2', 300.0, 0.0)], model=False)
    a, p = s.bodies['a'], s.bodies['p']
    p.goal, p.mode = None, 'idle'                       # unarmed, defaults written: none attached, no words
    assert p.acquire == frozenset() and 'YES' in a.acquire and p.find(interfaces.AIUpdate) is None
    p.ground_fire = None                                # but a ground fire records once set
    assert Observe.state(p)['ground_fire'] is None
    a.mode = 'move'
    for order, target, want in (('ground', (1, 2), (None, 'idle', (1, 2))), ('goal', p, (p, 'idle', (1, 2))),
                                ('attack', p, (p, 'attack', None)), ('stop', None, (None, 'attack', None)),
                                ('idle', None, (None, 'idle', None))):
        a.aiupdate.command(order, target)
        assert (a.goal, a.mode, a.ground_fire) == want, order


def test_aim_engages_an_attack_mover_only_and_a_teleport_forgets_the_chase_not_home():    # C3
    s = simsmall.small_world([('a', 'SovietAntiVehicleVehicleTech3', 'Player_1', 0.0, 0.0)], model=False)
    a = s.bodies['a']
    m, m.mode, m.chase, m.resume, m.auto_to, m.home = a.aiupdate, 'move', a, (1, 2), (3, 4), (5, 6)
    m.engage()                                          # a plain mover fires on its way
    assert not a.engaged
    m.mode = 'attack'
    m.engage()
    m.forget()
    assert a.engaged and (a.chase, a.resume, a.auto_to, a.home) == (None, None, None, (5, 6))
