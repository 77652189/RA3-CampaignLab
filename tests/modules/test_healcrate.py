"""HealCrateCollide heals eligible units within range of the crate."""

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.testing.small as simsmall  # noqa: E402
from engine.modules.healcrate import HealCrate  # noqa: E402


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
