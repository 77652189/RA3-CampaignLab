"""Characterize LeechPercentMaxHealthDamageNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import pytest  # noqa: E402
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_a_killing_hit_heals_a_fraction_of_maximum_health(monkeypatch):
    """LeechPercentMaxHealthDamageNugget heals from a killed victim's maximum HP."""
    s = small_world(model=False)
    caster = s.add('caster', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<LeechPercentMaxHealthDamageNugget Damage="20" DamageType="UNRESISTABLE" '
           'PercentMaxHealthToTake="10%"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    caster.set_hp(caster.hp - 150)
    target.set_hp(10)
    caster_before = caster.hp
    s.deal(FRAME)
    assert not target.alive
    assert caster.hp == pytest.approx(caster_before + 0.1 * target.max_hp)
