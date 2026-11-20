"""Characterize DamageNugget in a small world."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import simunits  # noqa: E402
from simsmall import small_world  # noqa: E402

FRAME = 1 / 15


def test_the_hit_uses_type_armor_and_rear_scalar(monkeypatch):
    """DamageNugget applies armor, flank and caster damage scaling on a discrete hit."""
    s = small_world(model=False)
    caster = s.add('caster', 'AlliedAntiInfantryInfantry', 'Player_1', 1250, 2500)
    target = s.add('target', 'SovietAntiVehicleVehicleTech1', 'Soviet_1', 1350, 2500)
    xml = ('<WeaponTemplate id="SampleHit" RequiredAntiMask="ANTI_GROUND"><Nuggets>'
           '<DamageNugget Damage="40" DamageType="CANNON"/>'
           '</Nuggets></WeaponTemplate>')
    weapons = simunits._weapons([xml])
    weapon = simunits._resolve(weapons['SampleHit'], weapons)
    s.volleys = [(target, weapon, caster)]
    monkeypatch.setattr(s, 'shots_due', lambda *_: 1)
    caster.dealt = 2.0
    target.angle = 0.0  # caster is due west of a target facing east
    target.armor = {'CANNON': 50.0, '<rear': 150.0}
    target.taken = 0.5
    before = target.hp
    s.deal(FRAME)
    assert before - target.hp == 30  # 40 × 2 × .5 armor × .5 taken × 1.5 rear
    assert target.last_by == caster.name
