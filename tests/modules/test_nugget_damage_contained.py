"""Characterize DamageContainedNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_the_first_eligible_passenger_takes_the_hit(monkeypatch):
    """DamageContainedNugget filters garrison occupants and caps the eligible list in entry order."""
    s = small_world(model=False)
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'AM_Apartments_01', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<DamageContainedNugget Damage="20" DamageType="UNRESISTABLE" '
           'MaxUnitsToDamage="1"><DamageObjectFilter Rule="NONE" '
           'Include="INFANTRY"/></DamageContainedNugget>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    first = s.add('first', 'AlliedAntiInfantryInfantry', 'Soviet_1', 1350, 2530)
    second = s.add('second', first.template, first.owner, 1350, 2560)
    assert s.garrison.put(first, target, script=True)
    assert s.garrison.put(second, target, script=True)
    before = (first.hp, second.hp, target.hp)
    s.deal(FRAME)
    assert (first.hp, second.hp, target.hp) == (before[0] - 20, before[1], before[2])
