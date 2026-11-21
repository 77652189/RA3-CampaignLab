"""Characterize ProjectileNugget in a small world."""

FRAME = 1 / 15


def test_the_straight_shell_arrives_after_full_distance_steps(weapon_world):
    """ProjectileNugget resolves the warhead and snapshots damage until a straight shell arrives."""
    s, fire = weapon_world
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1360, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<ProjectileNugget ProjectileTemplate="SampleShell" WarheadTemplate="SampleWarhead"/>'
           '</Nuggets></WeaponTemplate>')
    s.own['SampleShell'] = (
        '<GameObject id="SampleShell"><Behaviors>'
        '<ProjectileUpdate id="Flight" StateMachine="StraightLineProjectile">'
        '<MoveInStraightLine MuzzleVelocity="25"/>'
        '</ProjectileUpdate></Behaviors></GameObject>'
    )
    xml += ('<WeaponTemplate id="SampleWarhead"><Nuggets>'
            '<DamageNugget Damage="40" DamageType="CANNON"/>'
            '</Nuggets></WeaponTemplate>')
    start = s.frame_now()
    before = target.hp
    target.armor = {'CANNON': 50}
    fire(xml, target, caster)
    assert target.hp == before
    assert [(hit[0], hit[1], hit[2]) for hit in s._harm().projectile_hits] == [
        (start + 4, target, 20),  # floor(110 / 25); 40 warhead × 50% armor
    ]

    target.armor = {'CANNON': 0}
    s.volleys.clear()
    s.clock.frame = start + 3
    s.deal(FRAME)
    assert target.hp == before
    s.clock.frame = start + 4
    s.deal(FRAME)
    assert before - target.hp == 20
    assert not s._harm().projectile_hits


def _rocket(s, fire, behaviors):
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1700, 2500)
    s.own['SampleRocket'] = f'<GameObject id="SampleRocket"><Behaviors>{behaviors}</Behaviors></GameObject>'
    start, before = s.frame_now(), target.hp
    fire('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
         '<ProjectileNugget ProjectileTemplate="SampleRocket" WarheadTemplate="SampleWarhead"/></Nuggets></WeaponTemplate>'
         '<WeaponTemplate id="SampleWarhead"><Nuggets><DamageNugget Damage="40" DamageType="UNRESISTABLE"/>'
         '</Nuggets></WeaponTemplate>', target, caster)
    return start, before, target


def test_a_bezier_rocket_lands_a_fixed_time_after_launch(weapon_world):
    """BezierProjectile: the hit is queued BEZIER_FRAMES after launch whatever the distance (bench E168)."""
    s, fire = weapon_world
    start, before, target = _rocket(s, fire, '<BezierProjectile id="Flight"/>')
    assert target.hp == before
    assert [(hit[0], hit[2] > 0) for hit in s._harm().projectile_hits] == [(start + 70, True)]


def test_a_shell_with_no_flight_module_never_lands(weapon_world):
    """No BezierProjectile / ProjectileUpdate (and no parent to bring one): nothing lands (bench E168 removal lane)."""
    s, fire = weapon_world
    _, before, target = _rocket(s, fire, '')
    assert target.hp == before and not s._harm().projectile_hits
