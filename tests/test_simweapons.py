"""simunits weapon reading: a campaign override (inheritFrom its own id) changes the earlier template instead of
replacing it; a LineDamageNugget's damage counts; a mission's own WeaponTemplate is read, inheriting a retail one."""
import importlib.util
from pathlib import Path

# loaded by file (no new sys.path edit: guard G4's ceiling); simunits puts what it needs on the path itself
_spec = importlib.util.spec_from_file_location(
    'simunits', Path(__file__).resolve().parent.parent / 'experimental' / 'cnv' / 'simunits.py')
simunits = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simunits)

BASE = '''<WeaponTemplate id="Gun" AttackRange="150.0" ClipSize="3">
  <FiringDuration MinSeconds="0.2s" MaxSeconds="0.2s"/>
  <Nuggets><DamageNugget Damage="8.0" DamageType="GUN"/></Nuggets>
</WeaponTemplate>'''
OVERRIDE = '''<WeaponTemplate id="Gun" inheritFrom="Gun">
  <Nuggets><DamageNugget id="DefaultDamageNugget" Damage="4.0"/></Nuggets>
</WeaponTemplate>'''
RIFLE = '''<WeaponTemplate id="Rifle" AttackRange="300.0">
  <Nuggets><LineDamageNugget Damage="1000.0" DamageType="SNIPER"/></Nuggets>
</WeaponTemplate>'''


def test_override_changes_what_it_writes_whatever_the_file_order():
    for texts in ([BASE, OVERRIDE], [OVERRIDE, BASE]):
        w = simunits._weapons(texts)['Gun']
        assert (w['range'], w['damage'], w['type'], w['shots']) == (150.0, 4.0, 'GUN', 3)


def test_line_damage_counts():
    w = simunits._weapons([RIFLE])['Rifle']
    assert (w['damage'], w['type']) == (1000.0, 'SNIPER')


def test_own_weapon_inherits_a_retail_one():
    retail = simunits._weapons([BASE])
    mine = simunits._weapons(['<WeaponTemplate id="MyGun" inheritFrom="Gun" AttackRange="200"/>'], retail)
    assert (mine['MyGun']['range'], mine['MyGun']['damage']) == (200.0, 8.0)


def test_pre_attack_by_kind():
    w = dict(simunits._weapons([BASE])['Gun'], pre=1.0)          # 3 shots
    assert simunits._pre_per_clip(dict(w, pretype='PER_SHOT'), 3) == 3.0
    assert simunits._pre_per_clip(dict(w, pretype='PER_CLIP'), 3) == 1.0
    assert simunits._pre_per_clip(dict(w, pretype='PER_TARGET'), 3) == 0.0


def test_athena_round_and_cycle():
    """Bench engine_ocl a 2026-11-08: ~600 raw a round (2 s of 20 every frame + 20 when the effect dies), a round
    every ~5.3 s (pre-attack 2 + firing 2 + reload 1.1)."""
    weapons = simunits._fight_data()['weapons']
    assert simunits.ocl_round('OCL_AthenaCannon', weapons) == (620.0, 'EXPLOSIVE')
    (gun,) = simunits.fight('AlliedAntiStructureVehicle')['weapons']
    assert abs(gun['dps'] - 620 / 5.1) < 0.1 and gun['range'] == 500.0


def test_retail_conscript_fires():
    """Was read as no weapon (the override replaced the retail AK47: range 0)."""
    w = simunits.fight('SovietAntiInfantryInfantry')['weapons']
    assert w and w[0]['range'] == 150.0 and w[0]['type'] == 'GUN'
