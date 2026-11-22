"""SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER of the dead (engine.script.act_world): 0 while it lies its SlowDeath out
(E161 the dish, engine_acts_jmn g the conscript), the last value once gone (a Guardian has no SlowDeath; NAMED_DELETE)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.script.act_world as simact_world  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402


def test_the_dead_read_0_while_lying_and_keep_the_last_value_once_gone():
    s = simsmall.small_world([('man', 'SovietAntiInfantryInfantry', 'Player_2', 0.0, 0.0),
                              ('tank', 'AlliedAntiVehicleVehicleTech1', 'Player_2', 300.0, 0.0),
                              ('gone', 'SovietAntiInfantryInfantry', 'Player_2', 600.0, 0.0)], model=False)
    for n in s.bodies:
        s.counters[n] = 12
    s.destroy(s.bodies['man'], 'test'), s.destroy(s.bodies['tank'], 'test'), s.destroy(s.bodies['gone'], 'test')
    s.bodies['gone'].deleted = True
    s.advance(30)                                       # a second on: the tank is gone, the man still lies (8.5 s)
    for n in s.bodies:
        simact_world.set_unit_health_percentage_to_counter(s, '', [n, n], None)
    assert (s.counters['man'], s.counters['tank'], s.counters['gone']) == (0, 12, 12)
