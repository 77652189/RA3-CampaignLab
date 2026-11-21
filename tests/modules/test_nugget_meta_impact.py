"""Characterize MetaImpactNugget in a small world."""
from types import SimpleNamespace

import numpy as np

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.data.units as simunits  # noqa: E402
from sim import Ground  # noqa: E402
from engine.testing.small import small_world  # noqa: E402
from engine.combat.host import impact_ground_z  # noqa: E402

FRAME = 1 / 15


def test_the_collision_launches_a_neighbour_and_landing_starts_the_hold():
    """MetaImpactNugget moves a grounded body and starts a 38-frame hold at landing."""
    s = small_world(model=False)
    # A level site lets either infantry trajectory land at its launch height.
    elevation = np.full((40, 48), 400.0)
    s.ground = Ground(SimpleNamespace(DIMS=(48, 40, 0), WATERLINE=320,
                                     ground=lambda: SimpleNamespace(e=elevation)))
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 100, 200)
    target = s.add('target', 'SovietAntiInfantryInfantry', 'Soviet_1', 260, 200)
    outside = s.add('outside', target.template, target.owner, 260, 230)
    # A taper of 1 leaves a positive impulse at 30 if selection admits it.
    xml = ('<WeaponTemplate id="SampleShock"><Nuggets>'
           '<MetaImpactNugget ShockWaveAmount="100" ShockWaveRadius="20" ShockWaveZMult="1" ShockWaveTaperOff="1"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleShock'], weapons)
    centre = (target.x, target.y, impact_ground_z(s, target.x, target.y))
    now, before = s.frame_now(), target.hp

    s.volleys = []
    s.queue_projectile_hit(now, target, 0, caster, weapon, centre)
    s.deal(FRAME)
    assert outside.serial not in s.impact_flights  # 30 from the centre, outside radius 20
    (body, start, points) = s.impact_flights[target.serial]
    assert (body, start, points[0]) == (target, now, centre)
    assert target.hp == before  # the shock payload has no damage
    s.clock.frame = now + 1
    s.deal(FRAME)
    assert target.z > centre[2]

    landing = now + len(points) - 1  # one trajectory sample per frame
    s.clock.frame = landing
    s.deal(FRAME)
    assert target.z is None
    assert target.serial not in s.impact_flights
    assert s.knock_hold[target.serial] == landing + 38  # ceil((1 + 1.5) × 15)
