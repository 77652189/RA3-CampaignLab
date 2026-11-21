"""Characterize StripMaxHealthPercentNugget in a small world."""
import pytest

def test_stripping_deals_a_fraction_of_the_unchanged_maximum(weapon_world):
    """StripMaxHealthPercentNugget computes damage from maximum HP at partial health."""
    s, fire = weapon_world
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<StripMaxHealthPercentNugget AmountToStrip="10%" DamageType="CANNON"/>'
           '</Nuggets></WeaponTemplate>')
    caster.dealt = 2
    maximum = target.max_hp
    target.set_hp(maximum / 2)
    target.armor = {'CANNON': 50}
    fire(xml, target, caster)
    assert target.max_hp == maximum
    assert target.hp == pytest.approx(maximum * .4)  # .5 − .1 × .5 armor × 2 dealt
