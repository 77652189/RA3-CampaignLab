"""GrapplingHookUpdate (E226, checks/engine_grapple.readings.toml): with the harpoon toggled on the Apocalypse's hook
pulls the Hammer in about 40 a second and stops it within the Apocalypse's radius; off, the cannon shoots, no pull."""
import math

import pytest

import engine.objects.toggle as simtoggle
import engine.testing.small as simsmall
from engine.ports.command import Command


@pytest.mark.parametrize('on, clock', [(True, True), (False, True), (True, False)])   # the default clock: the aim hooks
def test_the_harpoon_pulls_the_hooked_vehicle_in(on, clock):
    s = simsmall.small_world([('apoc', 'SovietAntiVehicleVehicleTech3', 'Player_1', 1400.0, 2400.0),
                              ('hammer', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1400.0, 2560.0)], model=False)
    s.shot_clock = clock
    a, h = s.bodies['apoc'], s.bodies['hammer']
    h.status.add('NO_ATTACK')
    if on:
        assert simtoggle.press(s, a, 'Command_ToggleHarpoonSpecialPower', lambda owner: False)
    assert s.commands.do(Command('attack', units=('apoc',), target='hammer')) == (True, '')
    s.advance(30)                   # 2 s
    near = math.hypot(h.x - a.x, h.y - a.y)
    assert (60 < near < 120) if on else near > 150
    if on:
        s.advance(30)
        assert math.hypot(h.x - a.x, h.y - a.y) <= a.radius + 1e-6 and (a.x, a.y) == (1400.0, 2400.0)


def test_the_crush_leeches_half_the_hammer_only_with_the_crush_puppies():
    """SovietHarpoonCrushWeapon (review 1125 G): its plain kill is ForbiddenUpgrade Upgrade_SovietCrushPuppiesPower,
    its LeechPercentMaxHealthDamageNugget (50 %) RequiredUpgrade it -- a dead Hammer of 550 gives 275 back or none."""
    def crush(upgrade):
        s = simsmall.small_world([('apoc', 'SovietAntiVehicleVehicleTech3', 'Player_1', 1400.0, 2400.0),
                                  ('hammer', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1400.0, 2560.0)], model=False)
        a, h = s.bodies['apoc'], s.bodies['hammer']
        h.status.add('NO_ATTACK')
        a.damage(a.max_hp / 2)
        if upgrade:
            s.act('NAMED_RECEIVE_UPGRADE', ['Upgrade_SovietCrushPuppiesPower', 'apoc'], None)
        simtoggle.press(s, a, 'Command_ToggleHarpoonSpecialPower', lambda owner: False)
        s.commands.do(Command('attack', units=('apoc',), target='hammer'))
        s.advance(75)
        assert not h.alive
        return a.hp
    assert crush(True) - crush(False) == 550 * 0.5
