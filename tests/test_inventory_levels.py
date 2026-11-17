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
    # generated on demand (not committed, ADR 0030): python -I -X utf8 experimental/cnv/inventory_levels.py --write;
    # its rows carry the inventory's states (plus 0-use rows for a weapon form the inventory has no refinement of)
    items = [i for i in inventory.collect() if i['part'] in inventory_levels.PARTS]
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
