"""Our 9 levels' share of the inventory, engine A's parts (experimental/cnv/inventory_levels.py ->
docs/engine/inventory-levels-a.md, ADR 0026 stop condition 1): generated on demand from the inventory's items."""
import importlib.util
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# loaded by file (guard G4: no new sys.path edits); the module puts the cnv folders on the path itself
_spec = importlib.util.spec_from_file_location('inventory_levels',
                                               os.path.join(ROOT, 'experimental', 'cnv', 'inventory_levels.py'))
inventory_levels = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inventory_levels)
import inventory  # noqa: E402  (on the path now)

pytestmark = pytest.mark.skipif(
    not os.path.isdir(inventory.RETAIL_SCRIPTS) or not os.path.isdir(inventory_levels.rm.SAGEXML)
    or not __import__('sim').engine_model(),
    reason='needs the retail scripts cache, the SDK data and the private engine model: the states depend on them')


def test_the_level_scope_a_page_is_generated_from_the_items(tmp_path, monkeypatch):
    from test_inventory import items as all_items

    # generated on demand (not committed, ADR 0030): python -I -X utf8 experimental/cnv/inventory_levels.py --write;
    # its rows carry the inventory's states (plus 0-use rows for a weapon form the inventory has no refinement of)
    items = [i for i in all_items() if i['part'] in inventory_levels.PARTS]
    scope, missing = inventory_levels.level_scope()
    want = inventory_levels.render(items, scope, missing)
    state = {(i['part'], i['name']): i['state'] for i in items}
    rows = {(m[2], m[3]): m[1] for m in re.finditer(r'^\| (\S+) \| (\S+) \| `([^`]+)` \|', want, re.M)}
    known = {k: s for k, s in rows.items() if k in state}
    assert len(known) > len(rows) / 2 and all(state[k] == s for k, s in known.items())
    out = tmp_path / 'inventory-levels-a.md'
    monkeypatch.setattr(inventory_levels, 'OUT', str(out))
    monkeypatch.setattr(inventory_levels, 'level_scope', lambda *a, **k: (scope, missing))
    monkeypatch.setattr(inventory, 'collect', lambda *a, **k: items)
    inventory_levels.main(write=True)
    assert out.read_text(encoding='utf-8') == want


def test_a_module_nothing_moves_in_a_level_leaves_that_levels_scope(monkeypatch):
    key = (inventory_levels.MODULE, 'Behaviors/SpiderHoleUpdate')        # a4: the AI's Tankbusters never dig in
    monkeypatch.setattr(inventory_levels, 'level_uses', lambda lv: ({key: {'JapanAntiVehicleInfantry'}}, []))
    assert list(inventory_levels.level_scope(['a3', 'a4'])[0][key]) == ['a3']


def test_our_own_feature_a_level_reaches_is_a_gap_row_a_reading_can_close():
    L = inventory_levels
    ice, jump = [(L.ACTION, f'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT:SpecialPower_CNV_{p}') for p in ('IceEngineer_Freeze',
                                                                                                     'ChronoDeck')]
    page = L.render([], {ice: {'a4': set()}, jump: {'a7': set()}}, {}, declared={ice: 'checks/x.readings.toml::r'})
    assert f'| 已对拍 | 脚本动作 | `{ice[1]}` | 0 | a4 | checks/x.readings.toml::r |' in page
    assert f'| 未做 | 脚本动作 | `{jump[1]}` | 0 | a7 |' in page and '**已对拍 1 / 2**' in page


def test_an_objects_words_naming_another_object_are_not_followed():
    objs = {'tank': ('Tank', {'Behaviors': [('WeaponSetUpdate', 'w', {'gun', 'truck'}, ())]}, None),
            'truck': ('Truck', {}, None), 'shell': ('Shell', {}, None)}
    weapons = {'gun': ('Gun', ['ProjectileNugget'], {'shell'}, None)}
    got_o, got_w = inventory_levels.reach(['Tank'], objs, weapons)
    assert got_o == {'tank', 'shell'} and got_w == {'gun'}


def test_a_child_module_with_the_parents_id_replaces_it():
    objs = {'base': ('Base', {'Body': [('ActiveBody', 'b', set(), ())], 'Behaviors': [('Physics', 'p', set(), ())]},
                     None),
            'kid': ('Kid', {'Body': [('StructureBody', 'b', set(), ())]}, 'base')}
    assert [(g, t) for g, t, *_ in inventory_levels.effective('kid', objs)] == \
        [('Behaviors', 'Physics'), ('Body', 'StructureBody')]


def test_our_copy_of_a_retail_structure_counts_under_the_retail_name():
    # A2's unsellable dam plant is AlliedPowerPlant's file renamed (units/unsellable.py): its EngineerContain is the
    # measured generic form, so the level's scope names AlliedPowerPlant; a changed config has no retail twin
    uses, _ = inventory_levels.level_uses('a2')
    assert 'CNV_NoSell_AlliedPowerPlant' not in uses[(inventory_levels.MODULE, 'Behaviors/EngineerContain')]
    key = ('Behaviors', 'EngineerContain')
    sigs = inventory_levels.by_type(inventory_levels.effective('alliedpowerplant', inventory_levels.retail_tables()[0]))
    assert inventory_levels.retail_twin('CNV_NoSell_AlliedPowerPlant', *key, sigs[key]) == 'AlliedPowerPlant'
    assert inventory_levels.retail_twin('CNV_NoSell_AlliedPowerPlant', *key, (sigs[key][0][:-1] + ((),),)) is None


def test_our_copy_of_a_retail_weapon_counts_under_a_retail_weapon():
    # A3's Chrono Lag shell is the Guardian's cannon renamed (units/chronolag.py), its InformTargetNugget untouched:
    # the level's scope names a retail weapon carrying the same nugget; a changed nugget has no retail twin
    L = inventory_levels
    uses, _ = L.level_uses('a3')
    assert 'CNV_ChronoLag_Shell' not in uses[(L.NUGGET, 'InformTargetNugget')]
    key = (L.WEAPON, 'InformTargetNugget')
    sigs = L.by_type(L.nugget_mods('alliedantivehiclevehicletech1cannon', L.retail_tables()[1]))
    assert L.retail_twin('CNV_ChronoLag_Shell', *key, sigs[key]).lower() in L.retail_tables()[1]
    assert L.retail_twin('CNV_ChronoLag_Shell', *key, (sigs[key][0][:1] + ((('Radius', '1'),),) + sigs[key][0][2:],)) is None
