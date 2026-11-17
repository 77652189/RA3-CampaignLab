"""The simulator's upgrade shield (simunits.shielded, sim.Sim._upgrade): an upgrade whose AttributeModifier is
INVULNERABLE and sets the Iron Curtain status bit stops all damage while the unit holds it (bench: docs/engine/
upgrades.md 4; units/tower_ball.py, A9's dark balls). INVULNERABLE alone does not (the same bench)."""
from test_plans import named, small  # (puts experimental/cnv on the path)  # noqa: F401, I001
import simunits  # noqa: E402
from units import tower_ball  # noqa: E402


def test_the_dark_upgrade_shields_and_the_lit_one_does_not():
    u = tower_ball.tower_ball()
    assert simunits.shielded(u.xml, {u.names['off']})
    assert not simunits.shielded(u.xml, {u.names['on']}) and not simunits.shielded(u.xml, set())


def test_invulnerable_without_the_iron_curtain_bit_does_not_shield():
    u = tower_ball.tower_ball()
    bare = u.xml.replace('ObjectStatusToSet="NO_BRIBE UNDER_IRON_CURTAIN"', 'ObjectStatusToSet="NO_BRIBE"')
    assert bare != u.xml and not simunits.shielded(bare, {u.names['off']})
