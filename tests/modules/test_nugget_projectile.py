"""Characterize ProjectileNugget in a small world."""
import pytest

import parts
import sim
from engine.testing.small import island

FRAME = 1 / 15
BEZIER = '<BezierProjectile id="Flight"/>'


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


def _rocket(s, fire, behaviors, parent=''):
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1700, 2500)
    if parent:                  # the rocket inherits from SampleParent, these its behaviors
        s.own['SampleParent'] = f'<GameObject id="SampleParent"><Behaviors>{parent}</Behaviors></GameObject>'
    up = ' inheritFrom="SampleParent"' if parent else ''
    s.own['SampleRocket'] = f'<GameObject id="SampleRocket"{up}><Behaviors>{behaviors}</Behaviors></GameObject>'
    start, before = s.frame_now(), target.hp
    fire('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
         '<ProjectileNugget ProjectileTemplate="SampleRocket" WarheadTemplate="SampleWarhead"/></Nuggets></WeaponTemplate>'
         '<WeaponTemplate id="SampleWarhead"><Nuggets><DamageNugget Damage="40" DamageType="UNRESISTABLE"/>'
         '</Nuggets></WeaponTemplate>', target, caster)
    return start, before, target


@pytest.mark.parametrize('own, parent', [(BEZIER, ''), ('', BEZIER)], ids=['own', 'inherited'])
def test_a_bezier_rocket_lands_a_fixed_time_after_launch(weapon_world, own, parent):
    """BezierProjectile, its own or its parent's: the hit is queued BEZIER_FRAMES after launch whatever the distance
    (bench E168)."""
    s, fire = weapon_world
    start, before, target = _rocket(s, fire, own, parent)
    assert target.hp == before
    assert [(hit[0], hit[2] > 0) for hit in s._harm().projectile_hits] == [(start + 70, True)]


@pytest.mark.parametrize('behaviors', ['', f'<!-- {BEZIER} -->'], ids=['none', 'commented'])
def test_a_shell_with_no_flight_module_never_lands(weapon_world, behaviors):
    """No BezierProjectile / ProjectileUpdate (and no parent to bring one; one in a comment is none): nothing lands
    (bench E168 removal lane)."""
    s, fire = weapon_world
    _, before, target = _rocket(s, fire, behaviors)
    assert target.hp == before and not s._harm().projectile_hits


def test_only_the_own_files_the_build_compiles_reach_the_simulator():
    """A unit's file nothing includes is written beside it and never compiled: its GameObject (here under the Hammer's
    id) is nobody's; named in `also` or included by the unit it is compiled and the simulator has it (review 1121mm #1)."""
    shadow = '<GameObject id="SovietAntiVehicleVehicleTech1" inheritFrom="AlliedPowerPlant"></GameObject>'
    include = '<Include type="all" source="DATA:CNVUnits/Data/Shadow.xml"/>'
    for also, inc, has in [([], '', False), (['Shadow.xml'], '', True), ([], include, True),
                           ([], f'<!-- {include} -->', False)]:     # a file named in a comment is not included
        unit = parts.Unit('CNV_TestMarker', f'<GameObject id="CNV_TestMarker">{inc}</GameObject>',
                          files={'Shadow.xml': shadow}, also=also)
        s = sim.Sim(parts.Mission(name='T', map=island, scripts=[], units=[unit]), model=False)
        assert ('SovietAntiVehicleVehicleTech1' in s.own) is has
