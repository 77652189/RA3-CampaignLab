"""Characterize ParalyzeNugget in a small world."""


def test_emp_expires_at_the_longest_deadline(weapon_world):
    """ParalyzeNugget applies an EMP deadline; a shorter hit cannot shorten it."""
    s, fire = weapon_world
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<ParalyzeNugget ParalyzeType="EMP" DurationSeconds="1s"/><ParalyzeNugget '
           'ParalyzeType="EMP" DurationSeconds="0.2s"/>'
           '</Nuggets></WeaponTemplate>')
    now = s.frame_now()
    fire(xml, target, caster)
    assert s.emp_until == {target.serial: now + 15}  # max(1 × 15, .2 × 15)
    s.clock.frame = now + 14
    assert s.emp_disabled(target)
    s.clock.frame = now + 15
    assert not s.emp_disabled(target)
