"""Characterize AttributeModifierNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_the_hit_keeps_its_original_damage_and_sets_the_target_status(monkeypatch):
    """AttributeModifierNugget installs a timed target modifier after accumulating the hit."""
    s = small_world(model=False)
    s.own['SampleCaster'] = (
        '<GameObject id="SampleCaster" KindOf="INFANTRY"></GameObject>'
        '<AttributeModifier id="SampleSlow" Duration="0.4s" ObjectStatusToSet="NO_ATTACK">'
        '<Modifier Type="ARMOR" Value="50%"/></AttributeModifier>'
    )
    caster = s.add('caster', 'SampleCaster', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<DamageNugget Damage="20" DamageType="CANNON"/><AttributeModifierNugget '
           'AttributeModifierName="SampleSlow"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    target.armor = {'CANNON': 100}
    before, now = target.hp, s.frame_now()
    s.deal(FRAME)
    assert before - target.hp == 20  # the hit is calculated before the armor modifier
    assert 'NO_ATTACK' in target.status
    assert target.auras_on['SampleSlow'] == (now + 6, s.own['SampleCaster'])
