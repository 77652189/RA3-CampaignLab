"""Characterize StripMaxHealthPercentNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import pytest  # noqa: E402
import engine.data.units as simunits  # noqa: E402
from engine.testing.small import small_world  # noqa: E402

FRAME = 1 / 15


def test_stripping_deals_a_fraction_of_the_unchanged_maximum(monkeypatch):
    """StripMaxHealthPercentNugget computes damage from maximum HP at partial health."""
    s = small_world(model=False)
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<StripMaxHealthPercentNugget AmountToStrip="10%" DamageType="CANNON"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    caster.dealt = 2
    maximum = target.max_hp
    target.set_hp(maximum / 2)
    target.armor = {'CANNON': 50}
    s.deal(FRAME)
    assert target.max_hp == maximum
    assert target.hp == pytest.approx(maximum * .4)  # .5 − .1 × .5 armor × 2 dealt
