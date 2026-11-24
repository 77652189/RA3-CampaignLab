"""MagneticEffectUpdate (E225, checks/engine_magnet_e.readings.toml): the destroyer's black hole on turns a shooter
within its Radius onto it; off, or the shooter beyond the Radius, the shooter keeps its order."""
import pytest

import engine.objects.toggle as simtoggle
import engine.testing.small as simsmall
from engine.ports.command import Command


@pytest.mark.parametrize('on, gap, drawn', [(True, 150.0, True), (False, 150.0, False), (True, 260.0, False)])
def test_the_black_hole_draws_a_shooter_within_its_radius_while_on(on, gap, drawn):
    s = simsmall.small_world([('vip', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 1400.0, 2400.0),
                              ('ship', 'AlliedAntiNavyShipTech1', 'Player_1', 1400.0 + gap, 2250.0),
                              ('hammer', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1400.0, 2250.0)],
                             model=False)
    for name in ('vip', 'ship'):
        s.bodies[name].status.add('NO_ATTACK')
    if on:
        assert simtoggle.press(s, s.bodies['ship'], 'Command_ToggleMagneticArmor', lambda owner: False)
    assert s.commands.do(Command('attack', units=('hammer',), target='vip')) == (True, '')
    s.advance(1)
    assert (s.bodies['hammer'].goal is s.bodies['ship']) is drawn
