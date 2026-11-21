"""Characterize DamageContainedNugget in a small world."""


def test_the_first_eligible_passenger_takes_the_hit(weapon_world):
    """DamageContainedNugget filters garrison occupants and caps the eligible list in entry order."""
    s, fire = weapon_world
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'AM_Apartments_01', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<DamageContainedNugget Damage="20" DamageType="UNRESISTABLE" '
           'MaxUnitsToDamage="1"><DamageObjectFilter Rule="NONE" '
           'Include="INFANTRY"/></DamageContainedNugget>'
           '</Nuggets></WeaponTemplate>')
    first = s.add('first', 'AlliedAntiInfantryInfantry', 'Soviet_1', 1350, 2530)
    second = s.add('second', first.template, first.owner, 1350, 2560)
    assert s.garrison.put(first, target, script=True)
    assert s.garrison.put(second, target, script=True)
    before = (first.hp, second.hp, target.hp)
    fire(xml, target, caster)
    assert (first.hp, second.hp, target.hp) == (before[0] - 20, before[1], before[2])

    # A vehicle-only hit has no eligible passengers in this apartment.
    before = (first.hp, second.hp, target.hp)
    fire(xml.replace('Include="INFANTRY"', 'Include="VEHICLE"'), target, caster)
    assert (first.hp, second.hp, target.hp) == before


def test_a_passenger_takes_its_own_armor_and_no_flank():
    """Step N2b: the handler hits a passenger through the host's plain scalar (Context.armor), never the flanked
    one (Context.hit), the shots and the shooter's dealt multiplied in."""
    import types
    import engine.combat  # noqa: F401  (registers the handlers)
    from engine.combat import registry
    house, inside = types.SimpleNamespace(), types.SimpleNamespace(alive=True, kinds={'INFANTRY'}, serial=7)
    added = []
    ctx = types.SimpleNamespace(target=house, by=types.SimpleNamespace(dealt=2.0), n=3, held=lambda h: [inside],
                                armor=lambda v, t: 0.5, hit=lambda v, t: 0.25,
                                add=lambda v, amount: added.append((v, amount)))
    effect = dict(damage=10.0, type='CANNON', maximum=1, include=[], exclude=[])
    registry.HANDLERS['DamageContained'].apply(ctx, [effect])
    assert added == [(inside, 3 * 10.0 * 2.0 * 0.5)]
