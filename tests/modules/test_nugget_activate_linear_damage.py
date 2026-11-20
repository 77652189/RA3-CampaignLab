"""Characterize ActivateLinearDamageNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.data.units as simunits  # noqa: E402
from engine.testing.small import small_world  # noqa: E402

FRAME = 1 / 15


def test_one_line_node_hits_on_the_next_frame(monkeypatch):
    """ActivateLinearDamageNugget starts a SweepWeapon line that deals damage at its node."""
    s = small_world(model=False)
    s.own['SampleCaster'] = (
        '<GameObject id="SampleCaster" KindOf="INFANTRY"><Behaviors>'
        '<LinearDamageUpdate id="Sweep" Speed="500" Length="100" Radius="50" SweepWeapon="SampleNode"/>'
        '</Behaviors></GameObject>'
        '<WeaponTemplate id="SampleNode" RadiusDamageAffects="ENEMIES"><Nuggets>'
        '<DamageNugget Damage="17" DamageType="UNRESISTABLE" Radius="5"/>'
        '</Nuggets></WeaponTemplate>'
    )
    caster = s.add('caster', 'SampleCaster', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<ActivateLinearDamageNugget Lifetime="1s"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    now = s.frame_now()
    before = target.hp
    s.deal(FRAME)
    assert target.hp == before
    (line,) = s.sweeps.lines
    assert (line['frame'], line['nodes'], line['total']) == (now, 1, 1)
    # Node spacing 2 × 50, length 100, speed 500 / 5. Node 1 is at the target.
    s.sweeps.due(now)
    assert target.hp == before
    s.sweeps.due(now + 1)
    assert target.hp == before - 17
    assert not s.sweeps.lines
