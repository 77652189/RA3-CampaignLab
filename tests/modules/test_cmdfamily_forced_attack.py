"""A force order's behavior after dispatch, including the allied-only edge."""
import engine.testing.small as simsmall
from engine.ports.command import Command

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


def test_forced_ally_is_picked_only_when_aim_has_a_hostile_candidate():
    s = simsmall.small_world([('tank', GUARDIAN, 'Player_1', 1400.0, 2400.0),
                              ('ally', GUARDIAN, 'Player_1', 1550.0, 2400.0)],
                             model=False)
    tank, ally = s.bodies['tank'], s.bodies['ally']
    assert s.commands.do(Command('attack', units=('tank',), target='ally', force=True)) == (True, '')
    s.fight()
    assert tank.goal is ally and not s.firing  # aim returns early with no hostile candidate

    # This hostile is beyond cannon reach. It admits the weapon's aim pass,
    # where the explicit (allied) goal takes precedence over the hostile list.
    foe = s.add('foe', GUARDIAN, 'Soviet_1', 1400.0, 2700.0)
    foe.status.add('NO_ATTACK')
    s.fight()
    assert [target.name for target, _, a in s.firing if a is tank] == ['ally']


def test_force_attack_ground_suppresses_object_aim_until_stop():
    s = simsmall.small_world([('tank', GUARDIAN, 'Player_1', 1400.0, 2400.0),
                              ('foe', GUARDIAN, 'Soviet_1', 1550.0, 2400.0)], model=False)
    tank = s.bodies['tank']
    s.bodies['foe'].status.add('NO_ATTACK')
    spot = (1400.0, 2600.0)
    s.waypoints['ground'] = spot
    assert s.commands.do(Command('attack_ground', units=('tank',), place='ground')) == (True, '')
    s.fight()
    assert tank.ground_fire == spot and not s.firing

    assert s.commands.do(Command('stop', units=('tank',))) == (True, '')
    s.fight()
    assert tank.ground_fire is None
    assert [target.name for target, _, a in s.firing if a is tank] == ['foe']
