"""engine.modules.locomotor (move_pack M2 step 1): the LocomotorSet / LocomotorTemplate readers and the turn rule
Sim.add takes. The census against the readers it replaced (stats' speed and surface, turning, locomotor_speed):
3448 retail + 88 mission-own templates, one difference -- BaseMagneticSatelliteEffect's set writes no Condition and
now counts as NORMAL for locomotor_speed too, as stats and turning already read it."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
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
