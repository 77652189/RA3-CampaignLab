"""Characterize SecondaryDamageNugget in a small world."""

FRAME = 1 / 15


def test_a_two_hit_volley_adds_cold_without_health_damage(weapon_world):
    """SecondaryDamageNugget gives cold to the tracker without taking health."""
    s, fire = weapon_world
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
    before = target.hp
    weapon = fire(xml, target, caster, shots_due=lambda *_: 2)
    assert target.hp == before
    assert target.cold == 24  # two hits at 12 each, with no configured dissipation

    shielded = s.add('shielded', target.template, target.owner, 1350, 2540)
    shielded.shielded = True
    s.volleys = [(shielded, weapon, caster)]
    s.deal(FRAME)
    assert shielded.cold == 0  # the same two hits cannot add cold through the shield
