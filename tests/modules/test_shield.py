"""ShieldSphereUpdate (engine/modules/shield.py; bench checks/engine_shield.readings.toml): the Athena's shield takes the
V4 rockets landing on it until elapsed / 20 s + taken / 4000 reaches 1, and the rockets after hurt. Here three V4s
fire at once: their first volley (f83, 525 each from the side) is taken and the shield still up at f150 (with taken /
2000 it would be down at once); the second (f173) uses it up and kills the 400-health Athena."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402

ATHENA, V4 = 'AlliedAntiStructureVehicle', 'SovietAntiStructureVehicle'


def test_a_volley_is_taken_and_the_shield_stays_up_till_time_and_damage_use_it_up():
    s = simsmall.small_world([('a', ATHENA, 'Player_1', 1000.0, 1000.0)]
                             + [(f'v{k}', V4, 'Soviet_1', 900.0 + 100 * k, 1450.0) for k in range(3)])
    s.shot_clock = True                               # rockets fly (the coarse clock deals DPS)
    a = s.bodies['a']
    a.status.add('NO_ATTACK')
    s.self_power_press(a, 'Command_ToggleShieldSphere')
    shield = a.find(interfaces.Shield)[0]
    s.advance(150)
    assert a.health == 100.0 and shield.soaked > 1500 and 'GENERIC_TOGGLE_STATE' in a.status
    s.advance(150)
    assert not a.alive and shield.up_from is None
