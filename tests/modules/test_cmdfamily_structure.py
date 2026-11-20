"""An explicit order and AI auto-acquire lift the ordinary structure filter."""
import simsmall
from engine.ports.command import Command

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


def test_nearer_power_plant_needs_an_order_or_ai_autoacquire():
    s = simsmall.small_world([('tank', GUARDIAN, 'Player_1', 1400.0, 2400.0),
                              ('plant', 'SovietPowerPlant', 'Soviet_1', 1530.0, 2400.0),
                              ('foe', GUARDIAN, 'Soviet_1', 1400.0, 2570.0)], model=False)
    tank = s.bodies['tank']
    s.bodies['foe'].status.add('NO_ATTACK')

    def pick():
        s.fight()
        return [target.name for target, _, a in s.firing if a is tank]

    assert pick() == ['foe']  # plant is STRUCTURE, with no base-defense exception
    assert s.commands.do(Command('auto_acquire', units=('tank',), args=(('on', True),))) == (True, '')
    assert pick() == ['plant']  # closest centre now eligible
    assert s.commands.do(Command('auto_acquire', units=('tank',), args=(('on', False),))) == (True, '')
    assert pick() == ['foe']
    assert s.commands.do(Command('attack', units=('tank',), target='plant')) == (True, '')
    assert pick() == ['plant']
