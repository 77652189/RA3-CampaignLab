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

    target.set_hp(10)  # less than the same hit's 20 damage after armor
    caster_before = caster.hp
    s.deal(FRAME)
    assert not target.alive
    assert caster.hp == caster_before


def test_the_payout_is_what_the_victim_lost_at_most_and_one_claim_only():
    """engine/combat/leech.refund (step N2): a damage claim on a survivor pays by the smaller of its hit and what the
    victim lost (a floor kept the rest); a maximum claim on a survivor and two claims at once pay nothing (gaps)."""
    import types
    from engine.combat import leech
    mended, gaps = [], []

    def gap(tag, why):
        gaps.append(tag)
    healer = types.SimpleNamespace(alive=True, mend=mended.append)
    victim = types.SimpleNamespace(hp=95.0, max_hp=100.0)
    leech.refund([(healer, 'damage', 0.5, 20.0)], victim, 100.0, gap)
    assert mended == [2.5] and gaps == []           # lost 5 of the hit's 20
    leech.refund([(healer, 'maximum', 0.5, 0.0)], victim, 100.0, gap)
    assert mended == [2.5, 0.0] and gaps == ['LeechPercentMaxHealthDamageNugget']
    leech.refund([(healer, 'damage', 0.5, 20.0)] * 2, victim, 100.0, gap)
    leech.refund([], victim, 100.0, gap)
    assert mended == [2.5, 0.0] and gaps == ['LeechPercentMaxHealthDamageNugget', 'leech']
