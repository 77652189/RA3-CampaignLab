"""HealCrateCollide heals eligible units within range of the crate."""

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.testing.small as simsmall  # noqa: E402
from engine.modules.healcrate import AttributeCrate, HealCrate, MoneyCrate, VeterancyCrate  # noqa: E402


def test_heal_crate_collide_respects_range_and_owner():
    infantry = 'AlliedAntiInfantryInfantry'
    s = simsmall.small_world([('crate', 'HealCrate', 'PlyrCivilian', 1360.0, 1450.0),
                              ('ally', infantry, 'Player_1', 1365.0, 1450.0),
                              ('enemy', infantry, 'Player_2', 1355.0, 1450.0),
                              ('far', infantry, 'Player_1', 1600.0, 1450.0)], model=False)
    ally, enemy, far = (s.bodies[name] for name in ('ally', 'enemy', 'far'))
    for unit in (ally, enemy, far):
        unit.set_hp(unit.max_hp / 2)

    effect, = s.bodies['crate'].find(HealCrate)
    effect.heal(lambda unit: unit.owner == ally.owner)

    assert ally.hp == ally.max_hp
    assert enemy.hp == enemy.max_hp / 2
    assert far.hp == far.max_hp / 2


def test_attribute_crate_collide_takes_only_the_unit_collecting_it():   # AttributeCrateCollide
    s = simsmall.small_world([('crate', 'AttributeCrate', 'PlyrCivilian', 1360.0, 1450.0),
                              ('man', 'AlliedAntiInfantryInfantry', 'Player_1', 1365.0, 1450.0)], model=False)
    crate, man = s.bodies['crate'], s.bodies['man']
    effect, = crate.find(AttributeCrate)
    man.mode, man.goal = 'collect_crate', None
    assert not effect.collect(man, None)
    man.goal = crate
    assert effect.collect(man, None)
    assert effect.worn() is None        # retail's AttributeCrate names no modifier


def test_money_crate_collide_pays_the_registered_collector():   # MoneyCrateCollide
    s = simsmall.small_world([('crate', 'MoneyCrate', 'PlyrCivilian', 1360.0, 1450.0),
                              ('man', 'AlliedAntiInfantryInfantry', 'Player_1', 1365.0, 1450.0)], model=False)
    crate, man = s.bodies['crate'], s.bodies['man']
    effect, = crate.find(MoneyCrate)
    before = s.wallet.money.copy()

    assert not effect.collect(man, None)
    assert s.wallet.money == before

    man.mode, man.goal = 'collect_crate', crate
    assert effect.collect(man, None)
    before[man.owner] += 1000
    assert s.wallet.money == before


def test_veterancy_crate_collide_selects_pickup_and_nearby_recipients():   # VeterancyCrateCollide
    infantry = 'AlliedAntiInfantryInfantry'
    s = simsmall.small_world([('crate', 'VeterancyCrate', 'PlyrCivilian', 1360.0, 1450.0),
                              ('man', infantry, 'Player_1', 1370.0, 1450.0),
                              ('near', infantry, 'Player_1', 1360.0, 1490.0),
                              ('far', infantry, 'Player_1', 1510.0, 1450.0)], model=False)
    crate, man, near = (s.bodies[name] for name in ('crate', 'man', 'near'))
    effect, = crate.find(VeterancyCrate)
    assert not effect.collect(man, None)

    man.mode, man.goal = 'collect_crate', crate
    assert effect.collect(man, None)
    assert list(effect.promotions(man)) == [(man, 9), (near, 9)]
