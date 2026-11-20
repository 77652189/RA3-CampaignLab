"""Characterize ParalyzeNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_emp_expires_at_the_longest_deadline(monkeypatch):
    """ParalyzeNugget applies an EMP deadline; a shorter hit cannot shorten it."""
    s = small_world(model=False)
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<ParalyzeNugget ParalyzeType="EMP" DurationSeconds="1s"/><ParalyzeNugget '
           'ParalyzeType="EMP" DurationSeconds="0.2s"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    now = s.frame_now()
    s.deal(FRAME)
    assert s.emp_until == {target.serial: now + 15}  # max(1 × 15, .2 × 15)
    s.clock.frame = now + 14
    assert s.emp_disabled(target)
    s.clock.frame = now + 15
    assert not s.emp_disabled(target)
