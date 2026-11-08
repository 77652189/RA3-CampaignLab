"""The retail feature inventory (experimental/cnv/inventory.py -> docs/engine/inventory.md, ADR 0026) is generated,
current, complete and only uses legal states."""
import importlib.util
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# loaded by file (guard G4: no new sys.path edits); inventory.py puts the cnv folders on the path itself
_spec = importlib.util.spec_from_file_location('inventory', os.path.join(ROOT, 'experimental', 'cnv', 'inventory.py'))
inventory = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inventory)

pytestmark = pytest.mark.skipif(
    not os.path.isdir(inventory.RETAIL_SCRIPTS) or not __import__('sim').engine_model(),
    reason='needs the retail scripts cache (work/retailref) and the private engine model: the states depend on them')

_items = {}


def items():
    if 'all' not in _items:
        _items['all'] = inventory.collect()
    return _items['all']


def test_the_committed_inventory_is_current():
    want = inventory.render(items())
    got = open(inventory.OUT, encoding='utf-8').read() if os.path.exists(inventory.OUT) else ''
    assert got == want, 'docs/engine/inventory.md is stale: python -I -X utf8 experimental/cnv/inventory.py'


def test_states_are_legal_and_parts_are_all_there():
    xs = items()
    assert {i['state'] for i in xs} <= set(inventory.STATES)
    assert {i['part'] for i in xs} == set(inventory.PARTS)
    assert all(isinstance(i['uses'], int) and i['uses'] >= 0 for i in xs)


def test_every_retail_script_name_is_an_item():
    catalog = json.load(open(inventory.CATALOG, encoding='utf-8'))
    names = {i['name'].split(':')[0] for i in items() if i['part'] in (inventory.ACTION, inventory.CONDITION)}
    assert set(catalog) <= names


def test_the_registers_point_at_real_items_and_tests():
    keys = {(i['part'], i['name']) for i in items()}
    for k, test in inventory.BENCHED_TESTS.items():
        assert k in keys, f'BENCHED_TESTS: no item {k}'
        path, _, fn = test.partition('::')
        assert re.search(rf'^def {re.escape(fn)}\(', open(os.path.join(ROOT, path), encoding='utf-8').read(), re.M), test
    for k, (state, _) in inventory.NOTES.items():
        assert k in keys and state in inventory.STATES, k


def test_a_missing_source_stops_it_instead_of_an_empty_list(monkeypatch, tmp_path):
    monkeypatch.setattr(inventory, 'RETAIL_SCRIPTS', str(tmp_path / 'nowhere'))
    with pytest.raises(SystemExit):
        inventory.retail_uses()
    monkeypatch.setattr(inventory, 'RETAIL_SCRIPTS', str(tmp_path))
    with pytest.raises(SystemExit):
        inventory.retail_uses()
