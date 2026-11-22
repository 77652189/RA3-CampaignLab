"""Air target eligibility and line of fire at the normal fight entry."""
import engine.testing.small as simsmall
import engine.orders.order as simorder
from engine.ports.command import Command

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


def test_ground_cannon_rejects_ordered_aircraft_but_antiair_can_aim_past_a_building():
    s = simsmall.small_world([('tank', GUARDIAN, 'Player_1', 1400.0, 2400.0),
                              ('ifv', 'AlliedAntiAirVehicleTech1', 'Player_1', 1400.0, 2440.0),
                              ('wall', 'AlliedPowerPlant', 'Player_1', 1490.0, 2420.0),
                              ('air', 'SovietAntiGroundAircraft', 'Soviet_1', 1580.0, 2440.0),
                              ('ground', GUARDIAN, 'Soviet_1', 1400.0, 2220.0)], model=False)
    tank, ifv, air, ground = (s.bodies[n] for n in ('tank', 'ifv', 'air', 'ground'))
    air.status.add('NO_ATTACK')
    ground.status.add('NO_ATTACK')
    assert air.surface == 'air'
    assert ifv.weapons[0]['los']  # missiles normally require a clear line
    assert s.line_blocked(ifv.x, ifv.y, air, ifv)  # plant intersects even this sight line in 2D
    for attacker in (tank, ifv):
        assert s.commands.do(Command('attack', units=(attacker.name,), target='air')) == (True, '')
    simorder.fight(s, simorder.Peers(s))
    # The cannon falls back to a ground foe. The IFV has ANTI_AIRBORNE,
    # and the line-of-fire obstacle check exempts air.
    assert [(a.name, target.name) for target, _, a in s.firing] == [('tank', 'ground'), ('ifv', 'air')]
