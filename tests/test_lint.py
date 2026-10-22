"""experimental/campaign/lint.py catches each pitfall it was written for (a small XML per bench lesson)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'experimental', 'campaign'))
import lint  # noqa: E402

HEAD = '<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset">\n'


def run(tmp_path, body, placed=None):
    p = tmp_path / 'CNV_Test.xml'
    p.write_text(HEAD + body + '</AssetDeclaration>\n', encoding='utf-8')
    return [(level, msg.split(':')[0]) for level, _, msg in lint.check([str(p)], placed)]


def unit(oid='CNV_Probe', kinds='VEHICLE', weapon='CNV_Gun', vision=200, extra=''):
    return (f'<GameObject id="{oid}" inheritFrom="BaseVehicle" KindOf="{kinds}"><Behaviors>'
            f'<WeaponSetUpdate id="W"><WeaponSlotTurret ID="1"><Weapon Ordering="PRIMARY_WEAPON" Template="{weapon}"/>'
            f'</WeaponSlotTurret></WeaponSetUpdate>{extra}</Behaviors>'
            f'<VisionInfo VisionRange="{vision}" ShroudClearingRange="100"/></GameObject>\n')


def test_vision(tmp_path):
    gun = '<WeaponTemplate id="CNV_Gun" AttackRange="400.0"/>\n'
    assert run(tmp_path, gun + unit(vision=200)) == [('WARN', 'vision')]        # 时滞炮车 400 / 200
    assert run(tmp_path, gun + unit(vision=450)) == []
    trigger = '<WeaponTemplate id="CNV_Gun" AttackRange="10000"/>\n'           # a FireWeaponUpdate trigger
    assert run(tmp_path, trigger + unit(vision=200)) == []


def test_immobile_infantry(tmp_path):
    gun = '<WeaponTemplate id="CNV_Gun" AttackRange="100"/>\n'
    bad = '<AttributeModifier id="M" Category="NONE" ObjectStatusToSet="IMMOBILE"/>\n'
    good = '<AttributeModifier id="M" Category="NONE" ObjectStatusToSet="IMMOBILE_ALLOW_ROTATE"/>\n'
    assert run(tmp_path, gun + bad + unit(kinds='INFANTRY')) == [('ERROR', 'immobile')]
    assert run(tmp_path, gun + good + unit(kinds='INFANTRY')) == []
    assert run(tmp_path, gun + bad + unit(kinds='VEHICLE')) == []


def test_chrono_filter(tmp_path):
    gun = '<WeaponTemplate id="CNV_Gun" AttackRange="100"/>\n'
    store = '<StoreObjectsSpecialPower id="S" SpecialPowerTemplate="SP_Store" Radius="150"/>'
    bare = '<SpecialPowerTemplate id="SP_Store" ReloadTime="0s" TargetType="LOCATION"/>\n'
    filt = ('<SpecialPowerTemplate id="SP_Store" ReloadTime="0s" TargetType="LOCATION">'
            '<ObjectFilter Rule="ANY" Include="VEHICLE"/></SpecialPowerTemplate>\n')
    assert run(tmp_path, gun + bare + unit(extra=store)) == [('ERROR', 'filter')]
    assert run(tmp_path, gun + filt + unit(extra=store)) == []


def test_toggle_needs_skirmish_ai(tmp_path):
    gun = '<WeaponTemplate id="CNV_Gun" AttackRange="100"/>\n'
    bad = '<ToggleState StateName="On"><Command>X</Command></ToggleState>'
    good = '<ToggleState StateName="On"><Command>X</Command><SkirmishAiInfo/></ToggleState>'
    assert run(tmp_path, gun + unit(extra=bad)) == [('ERROR', 'toggle')]
    assert run(tmp_path, gun + unit(extra=good)) == []


def test_retail_id_variant(tmp_path):
    gun = '<WeaponTemplate id="CNV_Gun" AttackRange="100"/>\n'
    variant = '<GameObject id="JapanAntiVehicleInfantry_Ambush" inheritFrom="JapanAntiVehicleInfantry"/>\n'
    assert run(tmp_path, gun + unit() + variant) == [('ERROR', 'retail-id')]   # 坦克杀手的伏击版
    assert run(tmp_path, gun + unit()) == []


def test_spawn_needs_placement(tmp_path):
    gun = '<WeaponTemplate id="CNV_Gun" AttackRange="100"/>\n'
    spawn = '<SpawnBehavior id="S" SpawnNumberData="1"><SpawnTemplate>CNV_Turret</SpawnTemplate></SpawnBehavior>'
    turret = unit(oid='CNV_Turret')
    assert run(tmp_path, gun + unit(extra=spawn) + turret, placed={'CNV_Probe'}) == [('ERROR', 'spawn')]
    assert run(tmp_path, gun + unit(extra=spawn) + turret, placed={'CNV_Probe', 'CNV_Turret'}) == []
    retail = '<SpawnBehavior id="S"><SpawnTemplate>AlliedAntiVehicleVehicleTech1</SpawnTemplate></SpawnBehavior>'
    assert run(tmp_path, gun + unit(extra=retail), placed=set()) == []
