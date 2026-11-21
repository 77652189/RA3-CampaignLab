"""engine.modules.locomotor (move_pack M2 step 1): the LocomotorSet / LocomotorTemplate readers and the turn rule
Sim.add takes. The census against the readers it replaced (stats' speed and surface, turning, locomotor_of):
3448 retail + 88 mission-own templates, one difference -- BaseMagneticSatelliteEffect's set writes no Condition and
now counts as NORMAL for locomotor_of too, as stats and turning already read it."""
import pytest
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.data.units as units  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import locomotor as loco  # noqa: E402

SETS = '<LocomotorSet Locomotor="Tank" Speed="30"/><LocomotorSet Condition="SUPERSONIC" Locomotor="Jet" Speed="=$X"/>'
LIBRARY = ('<LocomotorTemplate id="Tank" Surfaces="DEEP_WATER" TurnTimeSeconds="1.25s" TurnThresholdHS="90d"/>'
           '<LocomotorTemplate id="Man" Surfaces="GROUND" TurnTimeSeconds="0.5s"/>')


def test_the_sets_the_library_and_the_turn_rule():
    found, lib = loco.sets(SETS), loco.library(LIBRARY)
    assert loco.speed_of(found, 'NORMAL').locomotor == 'Tank' and loco.speed_of(found, 'SUPERSONIC') is None
    assert (lib['Tank'].turn_rate, lib['Tank'].limit) == (288.0, 90.0) and loco.surface_of(lib['Tank'].surfaces, ()) == 'water'
    assert loco.turns(lib['Tank'], 30.0, 'water') == (288.0, True)          # a threshold: turns in place first
    assert loco.turns(lib['Man'], 30.0, 'ground') == (720.0, False)         # none: walks off turning
    assert loco.turns(lib['Tank'], 30.0, 'air') == loco.turns(lib['Tank'], 0.0, 'water') == \
        loco.turns(None, 30.0, 'ground') == (None, False)                     # aircraft, standing, no locomotor
    own = {'X': '<GameObject id="X" inheritFrom="AlliedAntiVehicleVehicleTech1"><LocomotorSet Speed="=$S" '
                'Locomotor="TestReactiveLocomotorHUMAN"/></GameObject>'}    # review 1120ii #1: a macro speed (the
    assert units.turning('X', own).turn_rate == 720.0       # parent's) still turns by its own NORMAL's Locomotor


def test_the_state_goes_on_a_moving_thing_only_and_the_forwards_read_it():
    """Step 2's LocomotorState (Sim.add, write): a building keeps none, its defaults read; a body's fields are read only."""
    s = simsmall.small_world([('p', 'AlliedPowerPlant', 'Player_1', 0.0, 0.0),
                              ('u', 'AlliedAntiInfantryInfantry', 'Player_1', 300.0, 300.0),
                              ('t', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 600.0, 300.0)], model=False)
    p, u, m = s.bodies['p'], s.bodies['u'], s.bodies['u'].find(interfaces.Locomotor)
    assert (s.bodies['t'].turn_rate, s.bodies['t'].turn_first, u.turn_first) == (360.0, True, False)   # Sim.add's turns
    loco.write(s.world, p, speed=0.0, surface='ground')
    assert p.find(interfaces.Locomotor) is None and (p.speed, p.surface, p.turn_rate, p.turn_first) == (0.0, 'ground', None, False)
    loco.write(s.world, u, speed=7.5)
    assert m.turn_rate > 0 and u.speed == m.speed == 7.5 and u.surface == m.surface == 'ground'
    with pytest.raises(AttributeError):
        u.speed = 1.0
    p.path, p.dest = [], None                       # step 3's setters: a building's cleared way attaches none,
    assert p.find(interfaces.Locomotor) is None and p.path == ()    # a way given one; each module its own list,
    # a thing with none an empty tuple (review 1120ii #2: not one list every such thing shares)
    p.path, u.face = [(5.0, 5.0)], 1.0
    assert p.find(interfaces.Locomotor).path == [(5.0, 5.0)] and u.path == [] and (m.face, m.dest) == (1.0, None)
    assert m.path is not p.path and m.path is not loco.LocomotorState.path
    s.send(u, (400.0, 300.0))                       # M3 1: go_to writes its fields on the module
    assert u.set_off == m.set_off == s.frame_now() and m.dest == (400.0, 300.0)
