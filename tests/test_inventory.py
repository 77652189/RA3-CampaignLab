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


def test_the_summary_leads_with_the_benched_share_by_use():
    """The main number is 按用量已对拍 (first column, every part, a share 0..100); today's values are not pinned."""
    assert inventory.SUMMARY_COLUMNS[0] == inventory.MAIN == '按用量已对拍'
    rows = inventory.summary(items())
    assert [p for p, _ in rows] == list(inventory.PARTS)
    for part, row in rows:
        assert 0 <= row[inventory.MAIN] <= row['按用量已有（已对拍+推断）'] <= 100, part
    header = next(x for x in inventory.render(items()).splitlines() if x.startswith('| 部分 |'))
    assert header.split('|')[2].strip() == inventory.MAIN


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


# ---- the AI part (engine B, experimental/cnv/inventory_ai.py)
_spec_ai = importlib.util.spec_from_file_location('inventory_ai', os.path.join(ROOT, 'experimental', 'cnv', 'inventory_ai.py'))
inventory_ai = importlib.util.module_from_spec(_spec_ai)
_spec_ai.loader.exec_module(inventory_ai)


def test_every_retail_tactic_and_heuristic_kind_is_an_ai_item():
    names = {i['name'] for i in items() if i['part'] == inventory.AI}
    census = inventory_ai.census()
    assert census and set(census) <= names
    tactics = {n.split('=')[1] for n in names if '/Tactic.Tactic=' in n}
    assert {'SimpleAttack', 'StaticDefense', 'DefenseAvoidanceAttack'} <= tactics
    assert any(n.endswith('/ConstantHeuristic') for n in names)


def test_the_ai_registers_point_at_real_items_and_sources():
    names = {i['name'] for i in items() if i['part'] == inventory.AI}
    for name, (state, _) in inventory_ai.NOTES.items():
        assert name in names and state in inventory.STATES, name
    for name, src in inventory_ai.BENCHED_REG.items():
        assert name in names, name
        assert os.path.exists(os.path.join(ROOT, src.split('::')[0].split('#')[0])), src


def test_the_ai_part_has_no_decompiler_addresses():
    text = open(inventory.OUT, encoding='utf-8').read()
    assert not re.search(r'0x[0-9a-fA-F]{5,}', text)


def test_the_committed_level_scope_is_current():
    # docs/engine/inventory-levels.md: what our 9 levels' enemy AI uses ("AI done" point 1); regenerate with
    # python -I -X utf8 experimental/cnv/inventory_ai.py levels --write
    want = inventory_ai.render_levels(items(), inventory_ai.level_scope())
    assert open(inventory_ai.LEVELS_OUT, encoding='utf-8').read() == want


def test_level_scope_follows_inheritance_overrides_and_campaign_difficulties():
    ET = inventory_ai.ET
    root = ET.fromstring(
        '<AssetDeclaration xmlns:xai="uri:x">'
        '<P id="Base"><S id="keep" State="A"/><S id="over" State="B"/><S id="gone" State="C"/>'
        '<S id="brutal" State="D" Difficulty="BRUTAL"/></P>'
        '<P id="Mine" inheritFrom="Base"><S id="over" State="E"/><S id="gone" xai:joinAction="Remove"/></P>'
        '</AssetDeclaration>')
    index = {el.get('id'): el for el in root}
    chain, kids = inventory_ai._effective(index['Mine'], index)
    assert [c.get('id') for c in chain] == ['Mine', 'Base']
    assert sorted((k.get('id'), k.get('State')) for k in kids) == [('keep', 'A'), ('over', 'E')]


def test_a_missing_ai_source_stops_it(monkeypatch, tmp_path):
    monkeypatch.setattr(inventory_ai, 'AI_DATA', str(tmp_path / 'nowhere'))
    with pytest.raises(SystemExit):
        inventory_ai.census()
    monkeypatch.setattr(inventory_ai, 'AI_DATA', str(tmp_path))
    with pytest.raises(SystemExit):
        inventory_ai.census()


def test_only_a_probe_a_test_holds_the_simulator_to_makes_an_item_benched(tmp_path):
    """已对拍 = a test replays that bench (round 140): a probe a test names (its build, or a variant of it that is not
    a probe of its own) counts; one only read on the bench, or a docs/engine line, leaves the item 推断."""
    checks, tests = tmp_path / 'checks', tmp_path / 'tests'
    checks.mkdir()
    tests.mkdir()
    for p in ('engine_seal', 'engine_seal_ext', 'engine_script', 'engine_scripts5'):
        (checks / f'{p}.py').write_text('', encoding='utf-8')
    (tests / 'test_x.py').write_text("_sim_resolve('engine_seal_move', c)  # bench engine_scripts5 e\n",
                                     encoding='utf-8')
    tested = inventory.tested_probes(str(tests), str(checks))
    assert tested == {'checks/engine_seal.py', 'checks/engine_scripts5.py'}
    src = [('checks/engine_script.py', 'ENABLE_SCRIPT read'), ('checks/engine_scripts5.py', 'NAMED_KILL read'),
           ('docs/engine/x.md', 'ENABLE_SCRIPT NAMED_KILL')]
    items = [dict(part=inventory.ACTION, name='ENABLE_SCRIPT', state=inventory.GUESSED, why='w'),
             dict(part=inventory.ACTION, name='NAMED_KILL', state=inventory.GUESSED, why='w')]
    inventory.benched(items, src, tested)
    assert items[0]['state'] == inventory.GUESSED and '没有测试跑这个台子' in items[0]['why']
    assert items[1]['state'] == inventory.BENCHED and 'engine_scripts5' in items[1]['why']
