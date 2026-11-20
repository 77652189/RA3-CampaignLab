"""Characterize LeechHealthDamageNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_a_nonlethal_hit_heals_half_the_damage_taken(monkeypatch):
    """LeechHealthDamageNugget heals from damage after armor on a surviving victim."""
    s = small_world(model=False)
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<LeechHealthDamageNugget Damage="40" DamageType="CANNON" PercentDamageToHeal="50%"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    caster.set_hp(caster.hp - 50)
    target.armor = {'CANNON': 50}
    caster_before, target_before = caster.hp, target.hp
    s.deal(FRAME)
    assert target.hp == target_before - 20  # 40 × 50% armor
    assert caster.hp == caster_before + 10  # 20 actual damage × 50%
