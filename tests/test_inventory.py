"""The retail feature inventory (experimental/cnv/inventory.py -> docs/engine/inventory.md, ADR 0026) is generated,
complete and only uses legal states. The pages are generated on demand and not committed (ADR 0030): the tests check
that the generators run and agree with the items, never what a file on disk says."""
import importlib.util
import json
import os
import re
import sys
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import pytest
# by file (G4; tests/guards/test_layers.py keeps helpers out of the top level)
_tc = importlib.util.spec_from_file_location(
    '_testcache', Path(__file__).resolve().parents[1] / 'experimental' / 'testbench' / 'testcache.py')
_testcache = importlib.util.module_from_spec(_tc)
_tc.loader.exec_module(_testcache)
content_key = _testcache.content_key

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# loaded by file (guard G4: no new sys.path edits); inventory.py puts the cnv folders on the path itself
_spec = importlib.util.spec_from_file_location('inventory', os.path.join(ROOT, 'experimental', 'cnv', 'inventory.py'))
inventory = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inventory)

pytestmark = pytest.mark.skipif(
    not os.path.isdir(inventory.RETAIL_SCRIPTS) or not __import__('sim').engine_model(),
    reason='needs the retail scripts cache (work/retailref) and the private engine model: the states depend on them')


@lru_cache(maxsize=1)
def _collect(parts, key):
    import inventory_levels
    import retailmodules
    import simcoverage

    # A miss must rebuild the tables and source census for this input snapshot.
    retailmodules.clear_caches()
    inventory_levels._retail = None
    simcoverage._code.clear()
    return inventory.collect(parts)


def items():
    from inventory_ai import AI_DATA, COMPILED, MODEL_REV_FILE
    from retailmodules import RETAILREF, SAGEXML
    import labpaths

    root = Path(ROOT)
    key = content_key(root / 'experimental', root / 'docs' / 'story', inventory.ENGINE_DOCS,
                      inventory.TESTS, inventory.CHECKS, inventory.READINGS, inventory.CATALOG,
                      inventory.RETAIL_SCRIPTS, RETAILREF, SAGEXML, AI_DATA, COMPILED, MODEL_REV_FILE)
    # The collector reads private AI files from the pinned Git object, not the working tree.
    return deepcopy(_collect(inventory.PARTS, (key, labpaths.ENGINE_MODEL, os.getenv('CNV_MUSIC_CAPTIONS'))))


def test_inventory_cache_refreshes_retail_xml_and_placements(tmp_path, monkeypatch):
    import inventory_levels as levels
    import retailmodules

    # Keep this tiny retail census separate from the real data other tests use.
    spec = importlib.util.spec_from_file_location('retailmodules', retailmodules.__file__)
    rm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rm)
    monkeypatch.setitem(sys.modules, 'retailmodules', rm)
    monkeypatch.setattr(levels, 'rm', rm)
    monkeypatch.setattr(levels, '_retail', None)
    monkeypatch.setattr(inventory, 'PARTS', (inventory.MODULE,))
    sdk, retail = tmp_path / 'sdk', tmp_path / 'retail'
    sdk.mkdir()
    retail.mkdir()
    monkeypatch.setattr(rm, 'SAGEXML', str(sdk))
    monkeypatch.setattr(rm, 'RETAILREF', str(retail))
    (sdk / 'object.xml').write_text(
        '<GameObject id="CacheProbe" xmlns:xi="http://www.w3.org/2001/XInclude">'
        '<Behaviors><xi:include href="DATA:behavior.xml"/></Behaviors></GameObject>', encoding='utf-8')
    behavior, placements = sdk / 'behavior.xml', retail / 'map.json'
    behavior.write_text('<CacheProbeBefore/>', encoding='utf-8')
    placements.write_text('{"objects": [{"t": "CacheProbe"}]}', encoding='utf-8')

    def census():
        return [(row['name'], row['all'], row['uses']) for row in items()]

    assert census() == [('Behaviors/CacheProbeBefore', 1, 1)]
    placements.write_text('{"objects": []}', encoding='utf-8')
    assert census() == [('Behaviors/CacheProbeBefore', 1, 0)]
    behavior.write_text('<CacheProbeAfter/>', encoding='utf-8')
    assert census() == [('Behaviors/CacheProbeAfter', 1, 0)]


def test_the_generator_writes_the_page_it_renders(tmp_path, monkeypatch):
    """inventory.py writes render(collect()) to OUT; every item is a row of it."""
    xs, out = items(), tmp_path / 'inventory.md'
    monkeypatch.setattr(inventory, 'OUT', str(out))
    monkeypatch.setattr(inventory, 'collect', lambda *a, **k: xs)
    assert inventory.main() == 0
    text = out.read_text(encoding='utf-8')
    assert text == inventory.render(xs)
    rows = set(re.findall(r'^\|[^|]*\| `([^`]+)` \|', text, re.M))
    assert {i['name'] for i in xs} <= rows


def test_the_generated_pages_are_not_bench_sources():
    """Read back, a generated page's notes made the next run depend on which pages that checkout had generated."""
    assert {os.path.basename(p) for p in (inventory.OUT, inventory_levels.OUT, inventory_ai.LEVELS_OUT)} \
        == set(inventory.PAGES)
    assert not {s for s, _ in inventory.bench_sources()} & {f'docs/engine/{p}' for p in inventory.PAGES}


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


def named_missing(src):
    """What a register's source names that is not there, or None: 'tests/x.py::test_y' -> a def test_y in that file,
    'checks/b.readings.toml::r' -> a reading id r in that file, any other path (a doc#section) -> the
    file. A test deleted when its readings moved into data left its name behind (T3 line A); this finds every one."""
    head = src.split('（')[0]
    path, _, name = head.partition('::')
    path = path.split('#')[0]
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return f'no file {path}'
    if not name:
        return None
    name = re.match(r'[A-Za-z0-9_]*', name)[0]
    text = open(full, encoding='utf-8').read()
    pattern = rf'^id = "{re.escape(name)}"$' if path.endswith('readings.toml') else rf'^def {re.escape(name)}\('
    return None if re.search(pattern, text, re.M) else f'no {name} in {path}'


# a test or reading a note's prose names: 'tests/x.py', 'tests/x.py::test_y', '<...>.readings.toml::id[case]', and a
# trailing '*' or '…' makes the name a prefix. 'RA3-EngineModel tests/...' is the private model's own test, not ours.
_PROSE_REF = re.compile(r'(?<!RA3-EngineModel )((?:tests|experimental)/[A-Za-z0-9_/.\-]+?\.(?:py|toml))'
                        r'(?:::([A-Za-z0-9_]+(?:\[[^\]\s]*\])?)([*…]?))?')
_BARE_TEST = re.compile(r'(?<![A-Za-z0-9_/:.])(test_[A-Za-z0-9_]+)([*…]?)')
_defs = {}


def _test_defs(root):
    """Every test def name and test file stem under tests/, for a bare 'test_y' in prose."""
    if root not in _defs:
        names = set()
        for top, _, files in os.walk(os.path.join(root, 'tests')):
            for f in files:
                if f.endswith('.py'):
                    names.add(f[:-3])
                    names.update(re.findall(r'^def (test_\w+)\(', open(os.path.join(top, f), encoding='utf-8').read(),
                                            re.M))
        _defs[root] = names
    return _defs[root]


def prose_missing(text, root=ROOT):
    """Every test or reading a register's prose names that is not there (a note outlives the test it cites: T3 moved
    them into readings data). Checks the same things named_missing does, wherever in the text they stand."""
    missing = []
    for m in _PROSE_REF.finditer(text):
        path, name, star = m[1], m[2], m[3]
        full = os.path.join(root, path)
        if not os.path.exists(full):
            missing.append(f'no file {path}')
            continue
        if not name:
            continue
        found = re.findall(r'^id = "([^"]+)"$' if path.endswith('readings.toml') else r'^def (\w+)\(',
                           open(full, encoding='utf-8').read(), re.M)
        if not any(f == name or (star and f.startswith(name)) for f in found):
            missing.append(f'no {name} in {path}')
    for m in _BARE_TEST.finditer(_PROSE_REF.sub(' ', text)):
        if not any(d == m[1] or (m[2] and d.startswith(m[1])) for d in _test_defs(root)):
            missing.append(f'no test {m[1]} under tests/')
    return missing


def test_prose_missing_reads_paths_names_cases_prefixes_and_bare_names(tmp_path):
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests' / 'test_x.py').write_text('def test_kept_one():\n    pass\n', encoding='utf-8')
    (tmp_path / 'experimental').mkdir()
    (tmp_path / 'experimental' / 'r.readings.toml').write_text('[[reading]]\nid = "side[a]"\n', encoding='utf-8')
    root = str(tmp_path)
    assert prose_missing('tests/test_x.py::test_kept_one按名回放、test_kept* 和 tests/test_x.py', root) == []
    assert prose_missing('experimental/r.readings.toml::side[a]通过；test_x 整个文件', root) == []
    assert prose_missing('RA3-EngineModel tests/no_such_file.py::test_y', root) == []
    assert prose_missing('tests/no_such_file.py按名回放；tests/test_x.py::test_nope；test_nope_too；'
                         'experimental/r.readings.toml::side[b]', root) == [
        'no file tests/no_such_file.py', 'no test_nope in tests/test_x.py',
        'no side[b] in experimental/r.readings.toml', 'no test test_nope_too under tests/']


def test_the_registers_point_at_real_items_and_tests():
    keys = {(i['part'], i['name']) for i in items()}
    problems = [f'BENCHED_TESTS: no item {k}' for k in inventory.BENCHED_TESTS if k not in keys]
    problems += [f'BENCHED_TESTS {k}: {why}' for k, test in inventory.BENCHED_TESTS.items()
                 if (why := named_missing(test))]
    problems += [f'NOTES: {k}' for k, (state, _) in inventory.NOTES.items() if k not in keys or state not in inventory.STATES]
    problems += [f'NOTES {k}: {why}' for k, (_, text) in inventory.NOTES.items() for why in prose_missing(text)]
    assert not problems, '\n'.join(problems)


def test_the_items_readings_declare_exist_and_the_held_ones_are_benched_citing_the_reading():
    """A reading's `item` (readings.py) names an inventory item that exists -- every one reported, mismatch-marked
    readings too -- and each one a held reading declares is 已对拍 with that reading in its why."""
    rows = {(i['part'], i['name']): i for i in items()}
    problems = [f'{src}: no item {k[0]} {k[1]}' for k, src in inventory.declared_items(held_only=False).items()
                if k not in rows]
    problems += [f'{k}: {rows[k]["state"]} {rows[k]["why"][:80]}' for k, src in inventory.declared_items().items()
                 if k in rows and (rows[k]['state'] != inventory.BENCHED or src not in rows[k]['why'])
                 and k not in inventory.BENCHED_TESTS]
    assert not problems, '\n'.join(problems)


def test_a_declared_item_counts_only_from_a_reading_without_a_mismatch_mark(tmp_path):
    base = '[[reading]]\nid = "{}"\nscene = {{build = "b", until = 1}}\nbench = "-"\nproves = "-"\nexpect = "1"\n'
    (tmp_path / 'engine_x.readings.toml').write_text(
        base.format('held') + 'item = ["脚本动作 A_ONE", "AI 人格/w"]\n\n'
        + base.format('off') + 'item = "脚本动作 A_TWO"\nmismatch = "sim 1, bench 2"\n', encoding='utf-8')
    held = {(inventory.ACTION, 'A_ONE'): 'checks/engine_x.readings.toml::held',
            (inventory.AI, '人格/w'): 'checks/engine_x.readings.toml::held'}
    assert inventory.declared_items(str(tmp_path)) == held
    assert inventory.declared_items(str(tmp_path), held_only=False) == {
        **held, (inventory.ACTION, 'A_TWO'): 'checks/engine_x.readings.toml::off'}
    xs = [dict(part=inventory.ACTION, name=n, state=inventory.GUESSED, why='-') for n in ('A_ONE', 'A_TWO')]
    inventory.apply_declared(xs, inventory.declared_items(str(tmp_path)), notes={})
    assert [(x['state'], x['why']) for x in xs] == [(inventory.BENCHED, 'checks/engine_x.readings.toml::held'),
                                                    (inventory.GUESSED, '-')]


def test_repair_closure_retains_three_health_slices_and_unmeasured_gaps():
    key = inventory.MODULE, 'Behaviors/RepairUpdate'
    rows = [i for i in items() if i['part'] == key[0] and i['name'].startswith(key[1])]
    assert len(rows) == 1  # shared configuration branches do not split the denominator
    row = rows[0]
    assert row['state'] == inventory.BENCHED
    assert inventory.BENCHED_TESTS[key] in row['why']
    source = open(os.path.join(ROOT, 'tests/test_simrepair_ai.py'), encoding='utf-8').read()
    for probe in ('repairai', 'repairq', 'repairt', 'repairzero'):
        assert probe in row['why'] and f"'{probe}'" in source
    for gap in ('gap：', '玩家入口', '废墟维修', '受伤停修', '其他初始血量/造价/速率',
                '资金耗尽', 'INFERRED', '不拆分分母'):
        assert gap in row['why']


def test_production_info_ui_exclusion_preserves_weight_without_claiming_bench():
    key = inventory.MODULE, 'Behaviors/ProductionUpdateInfo'
    rows = [i for i in items() if i['part'] == key[0] and i['name'].startswith(key[1])]
    assert len(rows) == 1
    row = rows[0]
    assert (row['state'], row['uses'], row['all']) == (inventory.NA, 9, 9)
    assert row['levels'] == ['a1', 'a4', 'a5', 'a6', 'a7', 'a9']
    assert key not in inventory.BENCHED_TESTS
    assert '没有游戏逻辑读者' in row['why']
    assert 'work/re/e_production_e56.md' in row['why']


def test_weapon_fired_stat_exclusion_keeps_both_empty_retail_forms_without_claiming_bench():
    """A statistics exclusion must not swallow OCL effects or a future configured form."""
    import retailmodules as rm

    key = inventory.NUGGET, 'ReportWeaponFiredStatNugget'
    rows = [i for i in items() if (i['part'], i['name']) == key]
    assert len(rows) == 1
    row = rows[0]
    assert (row['state'], row['uses']) == (inventory.NA, 2)
    assert rm.weapon_census()[key[1]]['weapons'] == 2
    assert key not in inventory.BENCHED_TESTS
    assert '未上台' in row['why'] and 'work/re/c_reportstat_report.md' in row['why']
    st = rm._load()
    found = {}
    for k, (name, _, _) in st['weapons'].items():
        forms = rm.effective_weapon_forms(k, st)
        stats = [n for n in forms if rm._tag(n) == key[1]]
        if stats:
            assert len(stats) == 1
            assert not stats[0].attrib and len(stats[0]) == 0
            assert not (stats[0].text or '').strip()
            found[name] = {n.get('WeaponOCL') for n in forms if rm._tag(n) == 'WeaponOCLNugget'}
    assert found == {
        'SovietVacuumBomb': {'OCL_VacuumBombSeed'},
        'ParticleCannonWeapon': {'OCL_ParticleCannonProjectiles', 'OCLParticleCannon'},
    }
    ocl = next(i for i in items() if (i['part'], i['name']) == (inventory.NUGGET, 'WeaponOCLNugget'))
    assert ocl['state'] == inventory.BENCHED


def test_substructure_storage_is_na_and_keeps_its_weight():
    key = inventory.MODULE, 'Behaviors/SubStructureStorageBehavior'
    rows = [i for i in items() if (i['part'], i['name']) == key]
    assert len(rows) == 1
    assert (rows[0]['state'], rows[0]['uses'], rows[0]['all']) == (inventory.NA, 6, 6)
    assert rows[0]['levels'] == ['a1', 'a4', 'a5', 'a6', 'a7', 'a9']
    assert '没人触发' in rows[0]['why'] and 'SubStructureBuild' in rows[0]['why']


def test_spawn_closure_preserves_unmeasured_gaps_and_all_three_named_replays():
    key = inventory.MODULE, 'Behaviors/SpawnBehavior'
    rows = [i for i in items() if i['part'] == key[0] and i['name'].startswith(key[1])]
    assert len(rows) == 1
    row = rows[0]
    assert (row['state'], row['uses'], row['all']) == (inventory.BENCHED, 10, 16)
    assert inventory.BENCHED_TESTS[key] in row['why']
    source = open(os.path.join(ROOT, 'tests', 'test_simspawn.py'), encoding='utf-8').read()
    for probe in ('engine_spawn', 'engine_spawn_refill', 'engine_spawn_power'):
        assert f"build.resolve('{probe}'," in source
        assert probe in row['why']
    for gap in ('gap：', '自主维修飞行', '子体直接删除', '真正禁用/占领',
                '缺电时死亡补充', '展开时机', '其他完整配置', 'INFERRED', '不拆分分母'):
        assert gap in row['why']


def test_levelup_closure_registers_measured_effects_without_hiding_shared_template_gaps():
    """E30: close the measured module once, without counting its overlapping branches twice."""
    key = inventory.MODULE, 'Behaviors/LevelUpUpgrade'
    rows = [i for i in items() if i['part'] == key[0] and i['name'].startswith(key[1])]
    assert len(rows) == 1
    row = rows[0]
    assert (row['state'], row['uses'], row['all']) == (inventory.BENCHED, 88, 124)
    assert row['levels'] == [f'a{k}' for k in range(1, 10)]
    assert inventory.BENCHED_TESTS[key] in row['why']
    test_source = open(os.path.join(ROOT, 'tests', 'test_simbench_c.py'), encoding='utf-8').read()
    # All seven build names are registered by benches/body_death/state/checks.py#engine_levelup, rather than seven source files.
    assert 'benches/body_death/state/checks.py#engine_levelup' in inventory.tested_probes()
    for probe in ('engine_levelup', 'engine_leveldamage', 'engine_levelhealth', 'engine_levelrange',
                  'engine_levelrate', 'engine_levelshroud', 'engine_levelvision'):
        assert probe in row['why']
        assert f"build.resolve('{probe}'," in test_source
    for gap in ('gap：', '自动索敌', '精确射程/揭雾/视野边界', '其他武器', '经验成长', '上限', 'Permanent=true'):
        assert gap in row['why']
    sight = next(i for i in items() if (i['part'], i['name']) == (inventory.CONDITION, 'ENEMY_SIGHTED'))
    assert sight['state'] == inventory.BENCHED          # round 237: benches/ui/presentation/checks.py#engine_eyes all, the relations and owner


def test_bridge_closure_registers_replays_without_hiding_unmeasured_gaps():
    """E37: coordinator closes measured interfaces; no new split or implied geometry support."""
    cases = (
        ('Body/ManagerBody', 32, 'tests/test_simmanagerbody.py',
         ('engine_managerbody', 'engine_managerbody_b'),
         ('内部最大血量', '伤害转发', '显示下限', 'INFERRED', '共享血量', '损毁', '维修')),
        ('Behaviors/BridgeBuilder', 30, 'tests/test_simbridgebuilder.py',
         ('engine_bridgebuilder', 'engine_bridgebuilder_b'),  # gatehouse health / mending measured in engine_bridgefix
         ('桥段物体生成/位置', '断桥通行', '其他桥型/配置/长度', 'engine_bridgefix')),
    )
    for name, all_templates, path, probes, gaps in cases:
        key = inventory.MODULE, name
        rows = [i for i in items() if i['part'] == key[0] and i['name'].startswith(name)]
        assert len(rows) == 1  # shared templates are not counted as disjoint branches
        row = rows[0]
        assert (row['state'], row['uses'], row['all']) == (inventory.BENCHED, 14, all_templates)
        assert inventory.BENCHED_TESTS[key].split('::')[0] == path
        assert inventory.BENCHED_TESTS[key] in row['why']
        source = open(os.path.join(ROOT, path), encoding='utf-8').read()
        for probe in probes:
            assert f"build.resolve('{probe}'," in source
            assert probe in row['why'] or name == 'Body/ManagerBody'
        for gap in ('gap：', 'HV_Bridge_01', *gaps):
            assert gap in row['why']


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
_spec_lv = importlib.util.spec_from_file_location('inventory_levels',
                                                  os.path.join(ROOT, 'experimental', 'cnv', 'inventory_levels.py'))
inventory_levels = importlib.util.module_from_spec(_spec_lv)
_spec_lv.loader.exec_module(inventory_levels)


def test_every_retail_tactic_and_heuristic_kind_is_an_ai_item():
    names = {i['name'] for i in items() if i['part'] == inventory.AI}
    census = inventory_ai.census()
    assert census and set(census) <= names
    tactics = {n.split('=')[1] for n in names if '/Tactic.Tactic=' in n}
    assert {'SimpleAttack', 'StaticDefense', 'DefenseAvoidanceAttack'} <= tactics
    assert any(n.endswith('/ConstantHeuristic') for n in names)


def test_the_ai_registers_point_at_real_items_and_sources():
    names = {i['name'] for i in items() if i['part'] == inventory.AI}
    problems = [f'NOTES: {name}' for name, (state, _) in inventory_ai.NOTES.items()
                if name not in names or state not in inventory.STATES]
    problems += [f'NOTES {name}: {why}' for name, (_, text) in inventory_ai.NOTES.items() for why in prose_missing(text)]
    problems += [f'BENCHED_REG: no item {name}' for name in inventory_ai.BENCHED_REG if name not in names]
    problems += [f'BENCHED_REG {name}: {why}' for name, src in inventory_ai.BENCHED_REG.items()
                 if (why := named_missing(src))]
    assert not problems, '\n'.join(problems)


def test_the_ai_part_has_no_decompiler_addresses():
    assert not re.search(r'0x[0-9a-fA-F]{5,}', inventory.render(items()))


def page_rows(text):
    """{(part, name): state} of a levels page's item rows (| 状态 | 部分 | `项` | ...)."""
    return {(m[2], m[3]): m[1] for m in re.finditer(r'^\| (\S+) \| (\S+) \| `([^`]+)` \|', text, re.M)}


def test_the_ai_level_scope_page_is_generated_from_the_items(tmp_path, monkeypatch):
    # docs/engine/inventory-levels.md: what our 9 levels' enemy AI uses ("AI done" point 1), generated on demand with
    # python -I -X utf8 experimental/cnv/inventory_ai.py levels --write; its rows carry the inventory's states
    xs, scope = items(), inventory_ai.level_scope()
    want = inventory_ai.render_levels(xs, scope)
    state = {(i['part'], i['name']): i['state'] for i in xs}
    rows = page_rows(want)
    assert rows and all(state[k] == s for k, s in rows.items())
    out = tmp_path / 'inventory-levels.md'
    monkeypatch.setattr(inventory_ai, 'LEVELS_OUT', str(out))
    monkeypatch.setattr(inventory_ai, 'level_scope', lambda *a, **k: scope)
    monkeypatch.setattr(inventory, 'collect', lambda *a, **k: xs)
    monkeypatch.setitem(sys.modules, 'inventory', inventory)     # main_levels imports it by name
    inventory_ai.main_levels(write=True)
    assert out.read_text(encoding='utf-8') == want


def test_the_ai_part_reads_the_private_model_at_the_pinned_commit_not_its_working_tree(tmp_path, monkeypatch):
    """The pages used to follow whatever the shared model working tree held at the moment, so 'committed is current'
    went red or green by workspace. A model clone with an uncommitted edit and an untracked file still yields the
    pinned commit's text; pin moves the pin to origin/main."""
    import subprocess

    def git(cwd, *args):
        subprocess.run(['git', '-C', str(cwd), '-c', 'user.email=t@t', '-c', 'user.name=t', *args], check=True,
                       capture_output=True)
    origin, model = tmp_path / 'origin.git', tmp_path / 'model'
    git(tmp_path, 'init', '-q', '--bare', str(origin))
    git(tmp_path, 'clone', '-q', str(origin), str(model))
    (model / 'ra3model' / 'ai').mkdir(parents=True)
    (model / 'ra3model' / 'ai' / 'a.py').write_text("X = 'Committed'\n", encoding='utf-8')
    git(model, 'add', '.')
    git(model, 'commit', '-q', '-m', 'one')
    git(model, 'push', '-q', 'origin', 'HEAD:main')
    (model / 'ra3model' / 'ai' / 'a.py').write_text("X = 'WorkingTree'\n", encoding='utf-8')
    (model / 'ra3model' / 'ai' / 'b.py').write_text("Y = 'Untracked'\n", encoding='utf-8')
    monkeypatch.setattr(inventory_ai.labpaths, 'ENGINE_MODEL', str(model))
    monkeypatch.setattr(inventory_ai, 'MODEL_REV_FILE', str(tmp_path / 'inventory_model.rev'))
    rev = inventory_ai.pin()
    assert inventory_ai.model_rev() == rev
    assert inventory_ai.model_ai_files() == [('ra3model/ai/a.py', "X = 'Committed'\n")]
    code = inventory_ai.ai_code()
    assert "'Committed'" in code and 'WorkingTree' not in code and 'Untracked' not in code


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


def test_a_probe_named_only_by_a_test_of_the_inventory_tools_is_no_replay(tmp_path):
    """A round 267: engine_scripts5 was 已对拍 (SET_MISSION_OBJECTIVE_STATUS and two more) only because the test above
    writes its name into a fixture. A function that calls an inventory tool (any alias of an inventory* module) feeds
    it names as data: they count for nothing; the same name in a replay, or a register read, still counts."""
    checks, tests = tmp_path / 'checks', tmp_path / 'tests'
    checks.mkdir()
    tests.mkdir()
    for p in ('engine_fake', 'engine_fakelv', 'engine_real', 'engine_reg'):
        (checks / f'{p}.py').write_text('', encoding='utf-8')
    (tests / 'test_tool.py').write_text(
        'import inventory_levels as lv\n'
        "inventory = load('inventory')\n\n\n"
        "@pytest.mark.parametrize('p', ['engine_fake_move'])\n"
        'def test_fixture(tmp_path, p):\n'
        "    (tmp_path / 't.py').write_text(\"_sim_resolve('engine_fake', c)  # bench engine_fake e\")\n"
        '    assert inventory.tested_probes(str(tmp_path))\n\n\n'
        'class TestLevels:\n'
        '    def test_levels(self):\n'
        "        assert lv.level_items('engine_fakelv')\n\n\n"
        'def test_register():\n'
        "    assert inventory.BENCHED_TESTS['engine_reg']\n\n\n"
        'def test_replay():\n'
        "    _sim_resolve('engine_real', 'a')\n", encoding='utf-8')
    tested = inventory.tested_probes(str(tests), str(checks))
    assert tested == {'checks/engine_real.py', 'checks/engine_reg.py'}
    src = [('checks/engine_fake.py', 'SET_MISSION_OBJECTIVE_STATUS read'), ('checks/engine_real.py', 'NAMED_KILL read')]
    items = [dict(part=inventory.ACTION, name='SET_MISSION_OBJECTIVE_STATUS', state=inventory.GUESSED, why='w'),
             dict(part=inventory.ACTION, name='NAMED_KILL', state=inventory.GUESSED, why='w')]
    inventory.benched(items, src, tested)
    assert items[0]['state'] == inventory.GUESSED and '没有测试跑这个台子' in items[0]['why']
    assert items[1]['state'] == inventory.BENCHED


def test_a_reading_of_one_check_counts_only_when_a_test_runs_that_check(tmp_path):
    """engine_aiskirm has thirty checks; MinTime was read only in check mt's docstring (B round 151-152: not matched),
    yet a test running checks c / y made it 已对拍. A probe of several checks is split by check (probe_parts): the
    module text counts for any test naming the probe, a check's own function only for a test that runs that check
    (after the name, quoted after it, a build variant, a parametrize list); a line saying it was not measured counts
    for nothing."""
    checks, tests = tmp_path / 'checks', tmp_path / 'tests'
    checks.mkdir()
    tests.mkdir()
    (checks / 'engine_multi.py').write_text(
        '"""Shared: TEAM_COMPARE_NUM_MEMBERS read.\nPrediction: Speed outside the observation."""\n'
        'def c(m):\n    """MaxUnits measured."""\n\n\ndef mt(m):\n    """MinTime measured."""\n\n\n'
        "def y(m):\n    pass\n\n\ndef z(m):\n    pass\n\n\n"
        "CHECKS = {'multi': {'c': c, 'y': y, 'z': z}, 'multimt': {'mt': mt}}\n", encoding='utf-8')
    (checks / 'engine_one.py').write_text('"""Range read."""\nCHECKS = {\'one\': {\'a\': lambda m: m}}\n',
                                          encoding='utf-8')
    (tests / 'test_x.py').write_text(
        '"""bench engine_multi c / q; checks/engine_one.py"""\n'
        "@pytest.mark.parametrize('k', ['z'])\ndef test_a(k):\n    _sim_run('engine_multi', k)\n\n\n"
        "def test_b():\n    simai_run.run('multi', 'y')\n", encoding='utf-8')
    tested = inventory.tested_probes(str(tests), str(checks))
    assert tested == {'checks/engine_multi.py', 'checks/engine_one.py', 'checks/engine_multi.py:c',
                      'checks/engine_multi.py:y', 'checks/engine_multi.py:z'}
    src = [(s, inventory.measured(t)) for p in ('engine_multi', 'engine_one')
           for s, t in inventory.probe_parts(p, (checks / f'{p}.py').read_text(encoding='utf-8'))]
    assert [s for s, _ in src] == ['checks/engine_multi.py', 'checks/engine_multi.py:c', 'checks/engine_multi.py:y',
                                   'checks/engine_multi.py:z', 'checks/engine_multi.py:mt', 'checks/engine_one.py']
    names = ('TEAM_COMPARE_NUM_MEMBERS', 'MaxUnits', 'MinTime', 'Speed', 'Range')
    items = [dict(part=inventory.ACTION, name=n, state=inventory.GUESSED, why='w') for n in names]
    inventory.benched(items, src, tested)
    got = {i['name']: (i['state'], i['why']) for i in items}
    assert got['TEAM_COMPARE_NUM_MEMBERS'] == (inventory.BENCHED, 'w；台上量过、测试对拍：checks/engine_multi.py')
    assert got['MaxUnits'] == (inventory.BENCHED, 'w；台上量过、测试对拍：checks/engine_multi.py:c')
    assert got['MinTime'] == (inventory.GUESSED, 'w；台上量过（checks/engine_multi.py:mt），没有测试跑这个台子')
    assert got['Speed'] == (inventory.GUESSED, 'w')
    assert got['Range'][0] == inventory.BENCHED


PROBE_SHAPES = '''
VARIANTS = {'engine_trial': 'trial', 'engine_trial2': 'trial2'}
NAMES = ('k1', 'k2')


def _build(w):
    return 'engine_tp' if w == 'a' else f'engine_tp_{w}'


def a(m, k): pass
def b(m): pass
def shared(m, w): pass


MISSION = {_build(w): (lambda w=w: None) for w in 'ab'}
CHECKS = ({k: {'x': (lambda m, k=k: a(m, k)), 'y': b} for k in NAMES}
          | {b2: {'trial': b} for b2, v in VARIANTS.items()}
          | {f'unpack_{v}': {'go': b} for v in ('p', 'q')}
          | {'super': {**{w: (lambda m, w=w: shared(m, w)) for w in 'pq'}, **{'z': a}}})
'''


def test_the_probe_reader_works_out_comprehensions_and_lambdas():
    """T6 (11-18): about ninety probes write CHECKS as a comprehension (over a literal, a module-level constant,
    VARIANTS.items(), a string, f-string or helper-built keys, merged with | or **) and about seventy write a check
    as a lambda; the reader read only dict literals with bare function names, so their builds and checks were
    missed (engine_aipullback's airevk2). One reader (probe_checks) serves the inventory and the bench-tests guard;
    a lambda's check is the module-level functions it runs."""
    missions, keys = inventory.probe_checks(PROBE_SHAPES)
    assert missions == {'engine_tp', 'engine_tp_b', 'k1', 'k2', 'engine_trial', 'engine_trial2', 'unpack_p',
                        'unpack_q', 'super'}
    assert keys == {'x': ['a'], 'y': ['b'], 'trial': ['b'], 'go': ['b'], 'p': ['shared'], 'q': ['shared'],
                    'z': ['a']}
    assert inventory.probe_checks("CHECKS = {k: {'a': f} for k in unknown()}\n") == (set(), {})


def test_mintime_is_not_benched_by_a_check_no_test_runs():
    """The live case: no test runs engine_aiskirm's check mt, and engine_aiupgrade says MinTime is outside its
    observation -- MinTime is not 已对拍 until a test replays a MinTime bench (or B registers one)."""
    row = next(i for i in items() if (i['part'], i['name']) == (inventory.AI, '造兵/BuildEntry.MinTime'))
    assert not re.search(r'checks/engine_(?:aiupgrade\.py|aiskirm\.py(?!:mt))', row['why']), row['why']


# ---- our 9 levels' column (the user, 11-11: finish what our 9 levels use first)
def test_every_item_says_which_of_our_levels_use_it_as_the_level_inventories_count():
    """'9 关用到' is the level inventories' scope: engine A's parts as inventory_levels.py (nugget forms split as there),
    the AI part as inventory_ai.py levels -- an item is marked iff that scope has it."""
    import inventory_levels
    xs = items()
    assert all(isinstance(i['levels'], list) for i in xs)
    scope, _ = inventory_levels.expand_forms(xs, inventory_levels.level_scope()[0])
    ai = {k for k in inventory_ai.level_scope() if k[0] == inventory.AI}
    keys = {(i['part'], i['name']) for i in xs}
    assert {(i['part'], i['name']) for i in xs if i['levels']} == (set(scope) | ai) & keys
    assert any(i['levels'] for i in xs if i['part'] == inventory.AI)


def test_the_level_share_counts_only_the_items_our_levels_use():
    xs = [dict(part=inventory.ACTION, name='A', uses=30, state=inventory.BENCHED, why=''),
          dict(part=inventory.ACTION, name='B', uses=10, state=inventory.TODO, why=''),
          dict(part=inventory.ACTION, name='C', uses=60, state=inventory.TODO, why=''),
          dict(part=inventory.ACTION, name='D', uses=99, state=inventory.NA, why=''),
          dict(part=inventory.CONDITION, name='E', uses=5, state=inventory.BENCHED, why='')]
    inventory.mark_levels(xs, {(inventory.ACTION, 'A'): {'a2', 'a1'}, (inventory.ACTION, 'B'): {'a3'},
                               (inventory.ACTION, 'D'): {'a1'}})
    assert xs[0]['levels'] == ['a1', 'a2'] and xs[2]['levels'] == []
    rows = dict(inventory.summary(xs))
    assert rows[inventory.ACTION][inventory.MAIN] == 30
    assert rows[inventory.ACTION][inventory.LEVEL_MAIN] == 75                 # 30 of 40: C unused, D 不涉及
    assert rows[inventory.ACTION][inventory.LEVEL_COUNT] == '1 / 2'
    assert rows[inventory.CONDITION][inventory.LEVEL_MAIN] is None             # no level uses the part: '—'
    text = inventory.render(xs)
    assert '| 已对拍 | `A` | 30 | a1 a2 |' in text and '| 未做 | `C` | 60 |  |' in text
    assert inventory.levels_cell([f'a{k}' for k in range(1, 10)]) == '全部'


def test_an_object_a_weapon_filter_excludes_is_not_reached():
    # 11-25: Tanya's C4 excluding the wall pieces put WallBuilder into our 9 levels' list (and a filter excluding the
    # balloon bomb, HeightDie); an excluded object is one the weapon never touches
    import xml.etree.ElementTree as ET
    words = inventory_levels._words(ET.fromstring(
        '<WeaponTemplate id="W" ProjectileTemplate="Shell"><SpecialObjectFilter><IncludeThing>Tank</IncludeThing>'
        '<ExcludeThing>Wall</ExcludeThing></SpecialObjectFilter></WeaponTemplate>'))
    assert {'w', 'shell', 'tank'} <= words and 'wall' not in words
