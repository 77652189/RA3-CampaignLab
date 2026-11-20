"""Characterize ProjectileNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_the_straight_shell_arrives_after_full_distance_steps(monkeypatch):
    """ProjectileNugget resolves the warhead and snapshots damage until a straight shell arrives."""
    s = small_world(model=False)
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
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
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    start = s.frame_now()
    before = target.hp
    target.armor = {'CANNON': 50}
    s.deal(FRAME)
    assert target.hp == before
    assert [(hit[0], hit[1], hit[2]) for hit in s._harm().projectile_hits] == [
        (start + 4, target, 20),  # floor(100 / 25); 40 warhead × 50% armor
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
