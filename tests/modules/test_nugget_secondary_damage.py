"""Characterize SecondaryDamageNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.data.units as simunits  # noqa: E402
from engine.testing.small import small_world  # noqa: E402

FRAME = 1 / 15


def test_a_two_hit_volley_adds_cold_without_health_damage(monkeypatch):
    """SecondaryDamageNugget gives cold to the tracker without taking health."""
    s = small_world(model=False)
    s.own['SampleColdBody'] = (
        '<GameObject id="SampleColdBody" KindOf="VEHICLE"><Body>'
        '<ActiveBody id="Body" MaxHealth="100"/></Body><Behaviors>'
        '<SecondaryDamageTracker id="Cold" DissipateAmount="0"/>'
        '</Behaviors></GameObject>'
    )
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SampleColdBody', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<SecondaryDamageNugget Amount="12"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 2)
    before = target.hp
    s.deal(FRAME)
    assert target.hp == before
    assert target.cold == 24  # two hits at 12 each, with no configured dissipation

    shielded = s.add('shielded', target.template, target.owner, 1350, 2540)
    shielded.shielded = True
    s.volleys = [(shielded, weapon, caster)]
    s.deal(FRAME)
    assert shielded.cold == 0  # the same two hits cannot add cold through the shield
