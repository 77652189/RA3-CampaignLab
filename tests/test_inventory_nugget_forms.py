"""Weapon field-form registration must conserve uses and leave unsupported variants out."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inventory', ROOT / 'experimental/cnv/inventory.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def test_nugget_form_split_rejects_unmeasured_fields_children_and_mixed_inheritance():
    import retailmodules as rm

    assert inventory.nugget_form_slice('InformTargetNugget', []) == ''
    ordinary = ET.fromstring('<MetaImpactNugget ShockWaveAmount="50" ShockWaveRadius="50" ShockWaveZMult="1"/>')
    assert inventory.nugget_form_slice('MetaImpactNugget', [ordinary]) == ':普通无延迟显式Z'
    omitted = ET.fromstring('<MetaImpactNugget ShockWaveAmount="50" ShockWaveRadius="50"/>')
    assert inventory.nugget_form_slice('MetaImpactNugget', [omitted]) == ':省略Z默认值'
    for field in ('ShockwaveDelaySeconds', 'ShockWaveSpeed', 'CyclonicFactor', 'ShockWaveArc', 'FutureField'):
        other = ET.fromstring(ET.tostring(ordinary))
        other.set(field, '1')
        assert inventory.nugget_form_slice('MetaImpactNugget', [other]) == ''
    filtered = ET.fromstring('<MetaImpactNugget><SpecialObjectFilter/></MetaImpactNugget>')
    st = {'weapons': {'base': ('Base', [], None), 'child': ('Child', [], 'base')},
          'weapon_forms': {'base': [ordinary], 'child': [filtered]}}
    forms = rm.effective_weapon_forms('CHILD', st)
    assert forms == [ordinary, filtered]
    assert inventory.nugget_form_slice('MetaImpactNugget', forms) == ''
    assert inventory.nugget_form_slice('InformTargetNugget', [ET.fromstring('<InformTargetNugget/>')]) == ':默认系数目标通知'
    max16 = ET.fromstring('<InformTargetNugget MaxTimeToImpactFudgeFactor="1.6"/>')
    assert inventory.nugget_form_slice('InformTargetNugget', [max16]) == ':Max1.6目标通知'
    assert inventory.nugget_form_slice('InformTargetNugget', [max16, ET.fromstring('<InformTargetNugget/>')]) == ''
    for xml in ('<InformTargetNugget MaxTimeToImpactFudgeFactor="1.7"/>',
                '<InformTargetNugget MinTimeToImpactFudgeFactor=".5" MaxTimeToImpactFudgeFactor="1.6"/>',
                '<InformTargetNugget Radius="10"/>', '<InformTargetNugget><Filter/></InformTargetNugget>'):
        assert inventory.nugget_form_slice('InformTargetNugget', [ET.fromstring(xml)]) == ''


def test_retail_nugget_partitions_conserve_uses_and_only_register_measured_forms():
    import retailmodules as rm
    import simunits

    if not Path(rm.SAGEXML).is_dir():
        pytest.skip('requires retail XML')
    xs = inventory.apply_registers(inventory.nugget_items())
    weapons = simunits._fight_data()['weapons']
    census = rm.weapon_census()
    for kind in ('MetaImpactNugget', 'InformTargetNugget'):
        rows = [i for i in xs if i['name'].split(':')[0] == kind]
        names = [w for i in rows for w in i['weapon_ids']]
        assert len(names) == len(set(names)) == census[kind]['weapons']
        assert sum(i['uses'] for i in rows) == census[kind]['weapons']
        for i in rows:
            for w in i['weapon_ids']:
                forms = [n for n in rm.effective_weapon_forms(w) if rm._tag(n) == kind]
                assert kind + inventory.nugget_form_slice(kind, forms) == i['name']
            if i['state'] == inventory.BENCHED:
                assert (inventory.NUGGET, i['name']) in inventory.BENCHED_TESTS
                assert '仅' in i['why'] and 'engine_' in i['why']
                field = 'inform' if kind == 'InformTargetNugget' else 'meta_impacts'
                assert all(weapons[w].get(field) for w in i['weapon_ids'])
                if kind == 'InformTargetNugget':
                    maximum = 1.6 if i['name'].endswith(':Max1.6目标通知') else 1.15
                    assert all(effect == dict(min=.85, max=maximum)
                               for w in i['weapon_ids'] for effect in weapons[w][field])
            else:
                assert i['state'] == inventory.TODO
    by = {i['name']: i for i in xs}
    assert 'SovietAntiStructureVehicleV4RocketWarhead' in by['MetaImpactNugget:省略Z默认值']['weapon_ids']
    assert 'JapanCommandoTech1PsyonicBlast' in by['MetaImpactNugget']['weapon_ids']
    assert 'AlliedBaseDefenseRockets_Aircraft' in by['InformTargetNugget:Max1.6目标通知']['weapon_ids']


@pytest.mark.parametrize('with_base', [True, False])
def test_level_nugget_scope_uses_membership_and_keeps_custom_weapons_uncovered(with_base):
    import inventory_levels as levels

    kind = inventory.NUGGET
    items = [dict(part=kind, name='InformTargetNugget', uses=1, state=inventory.TODO,
                  why='remaining', weapon_ids=['Uncovered']),
             dict(part=kind, name='InformTargetNugget:默认系数目标通知', uses=1,
                  state=inventory.BENCHED, why='measured', weapon_ids=['Covered'])]
    if not with_base:
        items = items[1:]
    text = levels.render(items, {(kind, 'InformTargetNugget'): {'a1': {'Covered', 'Uncovered', 'Custom'}}}, {})
    rows = [line for line in text.splitlines() if '`InformTargetNugget' in line]
    assert len(rows) == 2
    assert any('已对拍' in line and 'Covered' in line and 'Custom' not in line for line in rows)
    assert any('未做' in line and 'Custom' in line and 'Uncovered' in line for line in rows)
