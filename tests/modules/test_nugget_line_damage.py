"""Characterize LineDamageNugget in a small world."""
from math import pi


def test_the_dynamic_line_reaches_past_the_aim_point(weapon_world):
    """LineDamageNugget hits enemies inside the dynamic rectangle, including past the aim point."""
    s, fire = weapon_world
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<LineDamageNugget Damage="20" DamageType="UNRESISTABLE" UseDynamicLineLength="true" '
           'LineWidth="20" OverShootDistance="70"/>'
           '</Nuggets></WeaponTemplate>')
    near = s.add('near', target.template, target.owner, 1400, 2500)
    off = s.add('off', target.template, target.owner, 1350, 2670)
    edge = s.add('edge', target.template, target.owner, 1350, 2500 + target.radius + 15)
    friend = s.add('friend', target.template, caster.owner, 1325, 2500)
    target.angle = near.angle = pi  # Both face the caster, so the flank scalar is 1.
    # The edge vehicle misses by 5: the line reaches half its width plus the body radius.
    bodies = (target, near, off, edge, friend)
    before = {body.name: body.hp for body in bodies}
    fire(xml, target, caster)
    assert {body.name: before[body.name] - body.hp for body in bodies} == {
        'target': 20, 'near': 20, 'off': 0, 'edge': 0, 'friend': 0,
    }
