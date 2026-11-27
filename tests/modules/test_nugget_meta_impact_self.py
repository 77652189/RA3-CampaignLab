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


@pytest.mark.parametrize('self_flag', [' DamageDealtAtSelfPosition="true"', ''])
def test_king_onis_instant_arc_shock_goes_off_at_its_feet(weapon_world, monkeypatch, self_flag):
    """engine_knock_oni a: an instant arc shock is centred on the shooter's feet with or without
    DamageDealtAtSelfPosition, and 135d reaches 82 deg off its line (half-angle = the arc); the bench's speed."""
    s, fire = weapon_world
    elevation = np.full((40, 48), 400.0)
    s.ground = Ground(SimpleNamespace(DIMS=(48, 40, 0), WATERLINE=320, ground=lambda: SimpleNamespace(e=elevation)))
    gun = s.add('gun', 'AlliedAntiInfantryInfantry', 'Player_1', 200, 200)
    man = s.add('man', 'AlliedAntiInfantryInfantry', 'Soviet_1', 225, 200)
    out = s.add('out', 'AlliedAntiInfantryInfantry', 'Soviet_1', 205, 165)      # bench (35, 5) facing +y
    got, velocity = [], simunits.meta_impact_velocity
    monkeypatch.setattr(simunits, 'meta_impact_velocity',
                        lambda *a, **kw: got.append(velocity(*a, **kw)) or got[-1])
    fire(f'<WeaponTemplate id="SampleHit"{self_flag} WeaponSpeed="999999.0"><Nuggets>'
         '<MetaImpactNugget ShockWaveAmount="89" ShockWaveRadius="75.0" ShockWaveZMult="1.0" ShockWaveArc="135d" '
         'ForbiddenTargetObjectStatus="LEECHED_TARGET_ACTIVE" '
         'ForbiddenTargetModelCondition="STUNNED STUNNED_STANDING_UP STUNNED_FLAILING">'
         '<SpecialObjectFilter Rule="ANY" Include="INFANTRY"></SpecialObjectFilter></MetaImpactNugget>'
         '</Nuggets></WeaponTemplate>', man, gun)
    assert {man.serial, out.serial} <= set(s.impact_flights) and gun.serial not in s.impact_flights
    assert (0.4362, -3.0536, 0.5671) in [pytest.approx(v, abs=1e-3) for v in got]


def test_an_arc_shock_at_a_projectiles_detonation_reaches_no_one(weapon_world):
    """engine_knock_arc b / engine_knock_kami a: a V4's arc shock at its detonation shocks no one (INFERRED axis)."""
    s, _ = weapon_world
    gun = s.add('gun', 'AlliedAntiInfantryInfantry', 'Player_1', 200, 200)
    man = s.add('man', 'AlliedAntiInfantryInfantry', 'Soviet_1', 225, 200)
    weapons = simunits._weapons([_xml(' ShockWaveArc="5d"').replace(' DamageDealtAtSelfPosition="true"', '')])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = []
    s.queue_projectile_hit(s.frame_now(), man, 0, gun, weapon, (man.x, man.y, impact_ground_z(s, man.x, man.y)))
    s.deal(1 / 15)
    assert not s.impact_flights and (GAP_WEAPON, 'MetaImpactNugget') not in s.unmodeled
