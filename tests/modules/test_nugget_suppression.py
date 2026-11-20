"""Characterize SuppressionNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_a_two_hit_volley_keeps_two_fields_at_the_hit_site(monkeypatch):
    """SuppressionNugget writes one stationary field per hit, with a frame deadline."""
    s = small_world(model=False)
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<SuppressionNugget Radius="30" Suppression="60" DurationSeconds="0.5s"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 2)
    before = target.hp
    now = s.frame_now()
    s.deal(FRAME)
    assert target.hp == before
    row = (now + 8, 60, 1350, 2500, 30)  # ceil(0.5 × 15)
    assert s.suppression_fields == [row, row]
    target.x += 100
    s.clock.frame = now + 7
    s.suppression_tick()
    assert s.suppression_fields == [row, row]
    s.clock.frame = now + 8
    s.suppression_tick()
    assert not s.suppression_fields
