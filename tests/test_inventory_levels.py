"""Our 9 levels' share of the inventory, engine A's parts (experimental/cnv/inventory_levels.py ->
docs/engine/inventory-levels-a.md, ADR 0026 stop condition 1): generated and current."""
import importlib.util
import os

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


def test_the_committed_level_scope_a_is_current():
    # regenerate with: python -I -X utf8 experimental/cnv/inventory_levels.py --write
    items = [i for i in inventory.collect() if i['part'] in inventory_levels.PARTS]
    want = inventory_levels.render(items, *inventory_levels.level_scope())
    assert open(inventory_levels.OUT, encoding='utf-8').read() == want


def test_an_objects_words_naming_another_object_are_not_followed():
    objs = {'tank': ('Tank', {'Behaviors': [('WeaponSetUpdate', 'w', {'gun', 'truck'})]}, None),
            'truck': ('Truck', {}, None), 'shell': ('Shell', {}, None)}
    weapons = {'gun': ('Gun', ['ProjectileNugget'], {'shell'}, None)}
    got_o, got_w = inventory_levels.reach(['Tank'], objs, weapons)
    assert got_o == {'tank', 'shell'} and got_w == {'gun'}


def test_a_child_module_with_the_parents_id_replaces_it():
    objs = {'base': ('Base', {'Body': [('ActiveBody', 'b', set())], 'Behaviors': [('Physics', 'p', set())]}, None),
            'kid': ('Kid', {'Body': [('StructureBody', 'b', set())]}, 'base')}
    assert [(g, t) for g, t, _, _ in inventory_levels.effective('kid', objs)] == \
        [('Behaviors', 'Physics'), ('Body', 'StructureBody')]
