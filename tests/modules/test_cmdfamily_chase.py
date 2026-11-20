"""An attack-mover's detour and abandonment of its own chase."""
import simsmall
from engine.ports.command import Command

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'


def test_attack_move_resumes_its_destination_when_quarry_leaves_sight():
    s = simsmall.small_world([('tank', GUARDIAN, 'Player_1', 1400.0, 2400.0),
                              ('foe', GUARDIAN, 'Soviet_1', 1400.0, 2620.0)], model=False)
    tank, foe = s.bodies['tank'], s.bodies['foe']
    foe.status.add('NO_ATTACK')
    s.reveal_all = True  # isolate personal chase sight from side-wide visibility
    assert s.commands.do(Command('attack_move', units=('tank',), pos=(1850.0, 2400.0),
                                 args=(('objects', True),))) == (True, '')
    destination = tank.dest
    # 220 is outside weapon reach, inside sight plus the quarry's radius.
    # An attack move can take the detour even on the opening scan.
    s.advance(1)
    assert s.frame_now() == 8
    assert (tank.chase, tank.resume, tank.auto_to, tank.goal) == (foe, destination, (foe.x, foe.y), None)

    # Still visible to the side, but its centre minus radius is beyond personal sight.
    foe.y = 2800.0
    assert foe.alive
    s.advance(1)
    assert s.frame_now() == 15  # the scan on frame 8 was the next chance to give up
    assert (tank.chase, tank.resume, tank.auto_to, tank.dest) == (None, None, None, destination)
    assert tank.path
