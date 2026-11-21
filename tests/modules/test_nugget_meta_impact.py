"""Characterize MetaImpactNugget in a small world."""
from types import SimpleNamespace

import numpy as np

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.data.units as simunits  # noqa: E402
from sim import Ground  # noqa: E402
from engine.testing.small import small_world  # noqa: E402
from engine.combat.host import impact_ground_z  # noqa: E402
from engine.world.handle import GAP_WEAPON  # noqa: E402

FRAME = 1 / 15


def _shot():
    """A shock at a man on level ground (and one 30 off its centre), its arrival queued: (world, target, outside,
    centre, the frame)."""
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
    s.volleys = []
    s.queue_projectile_hit(s.frame_now(), target, 0, caster, weapon, centre)
    return s, target, outside, centre, s.frame_now()


def test_the_collision_launches_a_neighbour_and_landing_starts_the_hold():
    """MetaImpactNugget moves a grounded body and starts a 38-frame hold at landing."""
    s, target, outside, centre, now = _shot()
    before = target.hp
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


def test_a_curve_dipping_under_the_smoothed_ground_is_a_gap_and_no_flight(monkeypatch):
    """One sample 50 under the smoothed terrain, the end on its landing's ground: the engine's height queries the
    simulator lacks -- a gap, the body stays."""
    s, target, _, _, _ = _shot()
    curve = simunits.meta_impact_trajectory

    def dipping(*args):
        points = curve(*args)
        x, y, z = points[1]
        return [points[0], (x, y, z - 50), *points[2:]]
    monkeypatch.setattr(simunits, 'meta_impact_trajectory', dipping)
    s.deal(FRAME)
    assert target.serial not in s.impact_flights and target.z is None
    assert s.unmodeled[(GAP_WEAPON, 'MetaImpactNugget')]['what'] == '坡地轨迹和地形查询未建模'
