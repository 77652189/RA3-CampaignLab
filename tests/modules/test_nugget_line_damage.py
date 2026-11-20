"""Characterize LineDamageNugget in a small world."""
from math import pi

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_the_dynamic_line_reaches_past_the_aim_point(monkeypatch):
    """LineDamageNugget hits enemies inside the dynamic rectangle, including past the aim point."""
    s = small_world(model=False)
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<LineDamageNugget Damage="20" DamageType="UNRESISTABLE" UseDynamicLineLength="true" '
           'LineWidth="20" OverShootDistance="70"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    near = s.add('near', target.template, target.owner, 1400, 2500)
    off = s.add('off', target.template, target.owner, 1350, 2670)
    friend = s.add('friend', target.template, caster.owner, 1325, 2500)
    target.angle = near.angle = pi  # Both face the caster, so the flank scalar is 1.
    before = {body.name: body.hp for body in (target, near, off, friend)}
    s.deal(FRAME)
    assert {body.name: before[body.name] - body.hp for body in (target, near, off, friend)} == {
        'target': 20, 'near': 20, 'off': 0, 'friend': 0,
    }
