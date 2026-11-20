"""Characterize DOTNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_the_first_and_last_ticks_are_both_included(monkeypatch):
    """DOTNugget ticks immediately, then at each interval including exact expiry."""
    s = small_world(model=False)
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<DOTNugget Damage="7" DamageType="UNRESISTABLE" DamageInterval="0.2s" '
           'DamageDuration="0.4s"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    now = s.frame_now()
    before = target.hp
    s.deal(FRAME)
    assert before - target.hp == 7
    s.volleys.clear()
    for elapsed, expected in ((2, 7), (3, 14), (5, 14), (6, 21), (7, 21)):
        s.clock.frame = now + elapsed
        s.deal(FRAME)
        assert before - target.hp == expected  # seven HP at frame offsets 0, 3 and 6
    assert not s._harm().dots
