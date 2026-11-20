"""Characterize ActivateLiftObjectNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.data.units as simunits  # noqa: E402
from engine.testing.small import small_world  # noqa: E402

FRAME = 1 / 15


def test_ground_lift_releases_the_timer_and_keeps_the_status(monkeypatch):
    """ActivateLiftObjectNugget adds a caster-owned countdown and a target lift bit."""
    s = small_world(model=False)
    s.own['SampleCaster'] = (
        '<GameObject id="SampleCaster" KindOf="INFANTRY"><Behaviors>'
        '<LiftObjectUpdate id="Lift" TimeIncrement="0.2s" MaxTimeLifted="1s"/>'
        '</Behaviors></GameObject>'
    )
    caster = s.add('caster', 'SampleCaster', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<ActivateLiftObjectNugget><SpecialObjectFilter Rule="ANY" '
           'Include="VEHICLE"/></ActivateLiftObjectNugget>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    s.deal(FRAME)
    timer = (caster.name, target.name)
    assert s.lift_timers.remaining == {timer: 3}  # trunc(.2 × 15)
    assert 'LIFTED_INTO_AIR' in target.status
    s.volleys.clear()
    for remaining in (2, 1, 0):
        s.deal(FRAME)
        assert s.lift_timers.remaining[timer] == remaining
    s.deal(FRAME)
    assert not s.lift_timers.remaining
    assert 'LIFTED_INTO_AIR' in target.status

    amphibian = s.add('amphibian', 'SovietAntiAirShip', 'Soviet_1', 1350, 2540)
    assert amphibian.surface == 'both' and 'VEHICLE' in amphibian.kinds
    s.volleys = [(amphibian, weapon, caster)]
    s.deal(FRAME)
    assert (caster.name, amphibian.name) not in s.lift_timers.remaining
    assert 'LIFTED_INTO_AIR' not in amphibian.status
