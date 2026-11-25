"""MetaImpactNugget of an instant DamageDealtAtSelfPosition weapon (the retail shotgun's spelling): the shock is
centred on the shooter's feet and its arc runs about the shooter's line to the target (bench engine_knock_self)."""
from types import SimpleNamespace

import numpy as np
import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.data.units as simunits  # noqa: E402
from sim import Ground  # noqa: E402
from engine.combat.host import impact_ground_z  # noqa: E402
from engine.world.handle import GAP_WEAPON  # noqa: E402

SPOTS = {'man': (25, 0), 'behind': (38, 0), 'side': (25, 20), 'far': (60, 0)}
# the bench's shocks (the shooter faced +y there; here +x): per frame, forward / sideways / up
BENCH_V = {'man': (3.2261, 0, 0.8388), 'behind': (3.2856, 0, 0.5620), 'side': (2.5509, 2.0407, 0.6632)}


def _xml(arc):
    return ('<WeaponTemplate id="SampleHit" DamageDealtAtSelfPosition="true"><Nuggets>'
            '<MetaImpactNugget ShockWaveAmount="50" ShockWaveRadius="40.0" ShockWaveTaperOff="1.0" '
            f'ShockWaveZMult="1.0"{arc} ForbiddenTargetModelCondition="STUNNED_FLAILING"/>'
            '</Nuggets></WeaponTemplate>')


@pytest.mark.parametrize('arc,shocked', [(' ShockWaveArc="5d"', {'man', 'behind'}),
                                         ('', {'man', 'behind', 'side'})])
def test_the_shotgun_shocks_from_its_feet_along_its_line(weapon_world, monkeypatch, arc, shocked):
    """Retail: 25 and 38 ahead fly, 39 deg off does not, 60 is out of the 40 radius, the shooter at the centre
    never; without the arc the side man flies too. The speeds are the bench's (velocity unchanged)."""
    s, fire = weapon_world
    elevation = np.full((40, 48), 400.0)
    s.ground = Ground(SimpleNamespace(DIMS=(48, 40, 0), WATERLINE=320, ground=lambda: SimpleNamespace(e=elevation)))
    gun = s.add('gun', 'AlliedAntiInfantryInfantry', 'Player_1', 200, 200)
    men = {k: s.add(k, 'AlliedAntiInfantryInfantry', 'Soviet_1', 200 + dx, 200 + dy) for k, (dx, dy) in SPOTS.items()}
    got, velocity = {}, simunits.meta_impact_velocity

    def seen(effect, position, centre, height, **kw):
        v = velocity(effect, position, centre, height, **kw)
        got[(position[0] - centre[0], position[1] - centre[1])] = v
        return v
    monkeypatch.setattr(simunits, 'meta_impact_velocity', seen)
    fire(_xml(arc), men['man'], gun)
    assert {k for k, b in men.items() if b.serial in s.impact_flights} == shocked
    assert gun.serial not in s.impact_flights
    for k in shocked:
        assert got[SPOTS[k]] == pytest.approx(BENCH_V[k], abs=1e-4)


def test_an_arc_shock_at_a_projectiles_detonation_is_a_gap(weapon_world):
    """The arc's axis at a projectile's detonation is unmeasured (engine_knock_arc b): no flight, a gap."""
    s, _ = weapon_world
    gun = s.add('gun', 'AlliedAntiInfantryInfantry', 'Player_1', 200, 200)
    man = s.add('man', 'AlliedAntiInfantryInfantry', 'Soviet_1', 225, 200)
    weapons = simunits._weapons([_xml(' ShockWaveArc="5d"').replace(' DamageDealtAtSelfPosition="true"', '')])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = []
    s.queue_projectile_hit(s.frame_now(), man, 0, gun, weapon, (man.x, man.y, impact_ground_z(s, man.x, man.y)))
    s.deal(1 / 15)
    assert not s.impact_flights
    assert 'Arc' in s.unmodeled[(GAP_WEAPON, 'MetaImpactNugget')]['what']
