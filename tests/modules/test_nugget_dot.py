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
           'DamageDuration="0.4s" RemoveIfHealed="true"/>'
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

    target.set_hp(target.max_hp - 20)
    before = target.hp
    s.volleys = [(target, weapon, caster)]
    s.deal(FRAME)
    assert target.hp == before - 7
    s.volleys.clear()

    # The current healing check compares with HP saved before the first tick.
    target.set_hp(before + 1)
    s.clock.frame += 3  # 0.2 seconds at 15 Hz, when the next tick would land
    s.deal(FRAME)
    assert target.hp == before + 1
    assert not s._harm().dots


def test_only_a_direct_single_first_hit_books_a_dot(monkeypatch):
    """Step N2b: a volley of two, or a second hit on a target already on the book, books nothing and is a gap."""
    s = small_world(model=False)
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<DOTNugget Damage="7" DamageType="UNRESISTABLE" DamageInterval="0.2s" DamageDuration="2s"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    shots = [2]
    monkeypatch.setattr(s, 'shots_due', lambda *_: shots[0])
    s.volleys = [(target, weapon, caster)]
    s.deal(FRAME)
    assert not s._harm().dots and any(name == 'DOTNugget' for _, name in s.unmodeled)
    s.unmodeled.clear()
    shots[0] = 1
    s.deal(FRAME)
    assert len(s._harm().dots) == 1 and not any(name == 'DOTNugget' for _, name in s.unmodeled)
    s.clock.frame += 1
    s.deal(FRAME)
    assert len(s._harm().dots) == 1 and any(name == 'DOTNugget' for _, name in s.unmodeled)
