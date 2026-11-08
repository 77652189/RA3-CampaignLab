"""simunits weapon reading: a campaign override (inheritFrom its own id) changes the earlier template instead of
replacing it; a LineDamageNugget's damage counts; a mission's own WeaponTemplate is read, inheriting a retail one."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'experimental', 'cnv'))
import simunits  # noqa: E402

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


def test_retail_conscript_fires():
    """Was read as no weapon (the override replaced the retail AK47: range 0)."""
    w = simunits.fight('SovietAntiInfantryInfantry')['weapons']
    assert w and w[0]['range'] == 150.0 and w[0]['type'] == 'GUN'
