"""Movement's swept segment, using the CrusherInfo modules on the bodies."""
import engine.objects.locomotion as simlocomotion  # noqa: E402
import engine.testing.small as simsmall
from engine.modules import locomotor  # noqa: E402


def test_swept_crush_kills_only_the_lower_level_enemy_inside_its_own_radius():
    s = simsmall.small_world(model=False)
    hammer = s.add('hammer', 'SovietAntiVehicleVehicleTech1', 'Player_1', 1200, 2500)
    template = 'SovietAntiInfantryInfantry'
    victim = s.add('victim', template, 'Soviet_1', 1230, 2500)
    equal = s.add('equal', 'AlliedAntiVehicleVehicleTech1', 'Soviet_1', 1240, 2500)
    friendly = s.add('friendly', template, 'Player_1', 1250, 2500)
    outside = s.add('outside', template, 'Soviet_1', 1260, 2500)
    outside.y += outside.radius + 1
    hammer.angle = 0
    locomotor.write(s.world, hammer, speed=160)
    simlocomotion.go_to(s, hammer, (1280, 2500))
    s.move()

    # The half-second sweep is 80 units. The victim's centre lies on that
    # segment with both endpoints outside its radius. Equal 20 and allies live.
    assert (hammer.x, hammer.y) == (1280, 2500)
    assert not victim.alive and s.kills == [('Player_1', 'hammer', template, 'victim')]
    assert equal.alive and friendly.alive and outside.alive
