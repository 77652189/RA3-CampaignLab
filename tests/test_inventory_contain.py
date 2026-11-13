"""Coverage accounting must preserve placement weight and unmeasured branches."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('engineer_audit', ROOT / 'experimental/cnv/engineer_audit.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
import contain_audit
import inventory
import retailmodules


def test_containment_forms_conserve_inventory_weight_and_keep_gaps():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    report = contain_audit.audit()
    engineer = report['EngineerContain']
    infiltrator = report['InfiltratorContain']
    assert engineer['campaign'] == 70
    assert sorted((f['campaign'], f['templates']) for f in engineer['forms']) == [(0, 10), (1, 1), (6, 7), (63, 87)]
    assert infiltrator['campaign'] == 34
    assert sorted(f['campaign'] for f in infiltrator['forms']) == [1, 1, 2, 3, 3, 3, 3, 4, 4, 5, 5]
    for kind, part in report.items():
        rows = [r for f in part['forms'] for r in f['rows']]
        assert len({r['template'].lower() for r in rows}) == part['templates']
        assert sum(bool(r['maps']) for r in rows) == part['campaign']
        assert part['unresolved']['include'] == 0
        assert {Path(p).name for p in part['skipped_parse']} == {'MY_Boat_01b.xml', 'Structure.xml'}
        key = inventory.MODULE, 'Behaviors/' + kind
        assert key not in inventory.BENCHED_TESTS
        assert inventory.NOTES[key][0] == inventory.GUESSED
    # VISION's blocked port form must not merge with the unblocked yards.
    vision = [f for f in infiltrator['forms']
              if f['rows'][0]['modules'][0]['attributes'].get('Effect') == 'VISION']
    assert sorted(f['campaign'] for f in vision) == [1, 5]
    effects = {}
    for form in infiltrator['forms']:
        attrs = form['rows'][0]['modules'][0]['attributes']
        effects.setdefault(attrs['Effect'], []).append(form['campaign'])
        if attrs['Effect'] == 'ENERGY':
            assert attrs['Amount'] == '0.2'
            assert attrs['ObjectRef'] == 'EnergyDisabler'
            assert attrs['StructureFilter'] == 'InfiltrationEnergyStructuresFilter'
    assert {k: sorted(v) for k, v in effects.items()} == {
        'ENERGY': [4], 'KILL': [1], 'STEAL_MONEY': [3], 'VISION': [1, 5],
        'PARALYZE': [3], 'VISION_UNITS': [2, 3, 3, 4], 'RESET': [5]}
    japan_only = next(f for f in engineer['forms'] if f['campaign'] == 1)
    assert [r['template'] for r in japan_only['rows']] == ['TH_TombBuilding02']
    assert 'Relationship="ALLIES"' in japan_only['rows'][0]['modules'][0]['xml']
    assert not any('ObjectStatusToSet' in m['xml']
                   for f in engineer['forms'] for r in f['rows'] for m in r['modules'])


def test_containment_signature_keeps_gameplay_fields_but_ignores_formatting():
    parse = retailmodules.ET.fromstring
    sig = contain_audit.signature
    assert sig(parse('<M A="1" B="2"><F> x </F></M>')) == sig(parse('<M B="2" A="1">\n<F>x</F></M>'))
    assert sig(parse('<M Amount=".2"/>')) != sig(parse('<M Amount=".3"/>'))
    assert sig(parse('<M><F Relationship="ALLIES"/></M>')) != sig(parse('<M><F/></M>'))


def test_engineer_generic_split_preserves_weight_and_other_configuration_gaps():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    assert contain_audit.engineer_capture_share() == {'campaign': 63, 'templates': 87}
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/EngineerContain')]
    assert len(rows) == 3
    assert sum(r['uses'] for r in rows) == 70
    assert sum(r['all'] for r in rows) == 105
    generic = next(r for r in rows if r['name'].endswith(':通用三国'))
    gap = next(r for r in rows if r['name'] == 'Behaviors/EngineerContain')
    assert (generic['uses'], generic['all'], generic['state']) == (63, 87, inventory.BENCHED)
    allies = next(r for r in rows if r['name'].endswith(':三国ALLIES'))
    assert (allies['uses'], allies['all'], allies['state']) == (6, 7, inventory.BENCHED)
    assert (gap['uses'], gap['all'], gap['state']) == (1, 11, inventory.GUESSED)
    for measured, checks in ((generic, 'a/b/c/d'), (allies, 'a/e/f')):
        key = inventory.MODULE, measured['name']
        assert measured['why'].startswith(inventory.BENCHED_TESTS[key] + '；')
        assert 'engine_engineer ' + checks in measured['why']
        assert '普通进入' in measured['why']
        assert 'gap：精确进入帧仍INFERRED' in measured['why']
    assert 'gap：日本单人ALLIES型TH_TombBuilding02' in gap['why']
    assert '1用量/1模板' in gap['why']
    assert '0用量/10模板' in gap['why']
    assert '桥修复未对拍' in gap['why']
    # Keep the scope beside the replay link in the published artifact too.
    rendered = inventory.render(rows)
    for row in rows:
        assert row['why'] in rendered


def test_engineer_generic_split_does_not_credit_changed_fields(monkeypatch):
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    raw = contain_audit.engineer_audit.audit()
    monkeypatch.setattr(contain_audit.engineer_audit, 'audit', lambda: raw)
    for row in raw['rows']:
        for module in row['modules']:
            module['xml'] = module['xml'].replace('ImmediatelyEnabled="true"',
                                                 'ImmediatelyEnabled="false"')
    assert contain_audit.engineer_capture_share() == {'campaign': 0, 'templates': 0}


def test_engineer_allies_split_matches_complete_filter_and_preserves_level_scope(monkeypatch):
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    assert contain_audit.engineer_capture_share(allies=True) == {'campaign': 6, 'templates': 7}
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/EngineerContain')]
    import inventory_levels
    scope, _ = inventory_levels.expand_forms(rows, {
        (inventory.MODULE, 'Behaviors/EngineerContain'): {'a1': {
            'AlliedPowerPlant', 'SovietBaseDefenseGround', 'TH_TombBuilding02', 'CustomBuilding'}}})
    assert scope[(inventory.MODULE, 'Behaviors/EngineerContain:通用三国')]['a1'] == {'AlliedPowerPlant'}
    assert scope[(inventory.MODULE, 'Behaviors/EngineerContain:三国ALLIES')]['a1'] == {'SovietBaseDefenseGround'}
    assert scope[(inventory.MODULE, 'Behaviors/EngineerContain')]['a1'] == {'TH_TombBuilding02', 'CustomBuilding'}
    raw = contain_audit.engineer_audit.audit()
    monkeypatch.setattr(contain_audit.engineer_audit, 'audit', lambda: raw)
    for row in raw['rows']:
        for module in row['modules']:
            module['xml'] = module['xml'].replace('Relationship="ALLIES"', 'Relationship="ENEMIES"')
    assert contain_audit.engineer_capture_share(allies=True) == {'campaign': 0, 'templates': 0}


def test_infiltrator_energy_split_preserves_weight_and_other_effect_gaps():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    assert contain_audit.infiltrator_energy_share() == {'campaign': 4, 'templates': 6}
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/InfiltratorContain')]
    assert len(rows) == 2
    assert sum(r['uses'] for r in rows) == 34
    assert sum(r['all'] for r in rows) == 38
    measured = next(r for r in rows if r['name'].endswith(':ENERGY'))
    gap = next(r for r in rows if r['name'] == 'Behaviors/InfiltratorContain')
    assert (measured['uses'], measured['all'], measured['state']) == (4, 6, inventory.BENCHED)
    assert (gap['uses'], gap['all'], gap['state']) == (30, 32, inventory.GUESSED)
    assert measured['why'].startswith('tests/test_siminfiltrator.py::test_spy_power_plant_as_on_the_bench')
    import inventory_levels
    scope, _ = inventory_levels.expand_forms(rows, {
        (inventory.MODULE, 'Behaviors/InfiltratorContain'): {
            'a1': {'JapanPowerPlant', 'AlliedBarracks', 'UnknownPlant'}}})
    assert scope[(inventory.MODULE, measured['name'])]['a1'] == {'JapanPowerPlant'}
    assert scope[(inventory.MODULE, gap['name'])]['a1'] == {'AlliedBarracks', 'UnknownPlant'}


def test_infiltrator_energy_split_does_not_credit_changed_fields(monkeypatch):
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    raw = contain_audit.engineer_audit.audit('InfiltratorContain')
    monkeypatch.setattr(contain_audit.engineer_audit, 'audit', lambda kind: raw)
    for row in raw['rows']:
        for module in row['modules']:
            module['xml'] = module['xml'].replace('Amount="0.2"', 'Amount="0.3"')
    assert contain_audit.infiltrator_energy_share() == {'campaign': 0, 'templates': 0}


@pytest.mark.parametrize('effect, selector, uses, templates, boundary', [
    ('KILL', '', 1, 1, 'KILL 1用量/1模板部分已测'),
    ('PARALYZE', '', 3, 3, 'PARALYZE 3用量/3模板部分已测'),
    ('VISION', '', 5, 5, '普通VISION 5用量/5模板部分已测且暂停扩宿主'),
    ('VISION', '9999999s', 1, 1, '港口阻断VISION 1用量/1模板未测'),
    ('STEAL_MONEY', '', 3, 4, 'STEAL_MONEY 3用量/4模板暂停'),
    ('VISION_UNITS', 'InfiltrationVehicleObjectFilter', 4, 4, '车辆VISION_UNITS 4用量/4模板暂停'),
    ('VISION_UNITS', 'InfiltrationAircraftObjectFilter', 2, 2, '飞机VISION_UNITS 2用量/2模板未测'),
    ('VISION_UNITS', 'InfiltrationInfantryObjectFilter', 3, 3, '步兵VISION_UNITS 3用量/3模板未测'),
    ('VISION_UNITS', 'InfiltrationShipObjectFilter', 3, 3, '舰船VISION_UNITS 3用量/3模板未测'),
    ('RESET', '', 5, 6, 'RESET 5用量/6模板暂停'),
])
def test_infiltrator_residual_closure_preserves_each_configuration_gap(
        effect, selector, uses, templates, boundary):
    """A successful PARALYZE replay cannot grant the other forms bench credit.

    Static counts only: actual readings stay in the named siminfiltrator tests.
    Match all ten remaining forms against the SDK census and their public scope.
    """
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    forms = []
    for form in contain_audit.audit()['InfiltratorContain']['forms']:
        attrs = form['rows'][0]['modules'][0]['attributes']
        discriminator = ('UnitFilter' if effect == 'VISION_UNITS' else
                         'BlockedDuration' if effect == 'VISION' else None)
        if attrs['Effect'] == effect and (
                discriminator is None or attrs.get(discriminator, '') == selector):
            forms.append(form)
    assert [(f['campaign'], f['templates']) for f in forms] == [(uses, templates)]
    key = inventory.MODULE, 'Behaviors/InfiltratorContain'
    state, why = inventory.NOTES[key]
    assert state == inventory.GUESSED and key not in inventory.BENCHED_TESTS
    assert boundary in why
    assert 'work/re/e142_infiltrator_closure.md' in why
