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
    assert len(rows) == 2
    assert sum(r['uses'] for r in rows) == 70
    assert sum(r['all'] for r in rows) == 105
    generic = next(r for r in rows if r['name'].endswith(':通用三国'))
    gap = next(r for r in rows if r['name'] == 'Behaviors/EngineerContain')
    assert (generic['uses'], generic['all'], generic['state']) == (63, 87, inventory.BENCHED)
    assert (gap['uses'], gap['all'], gap['state']) == (7, 18, inventory.GUESSED)
    assert generic['why'] == ('tests/test_simengineer.py::'
                              'test_engineer_soviet_japan_captures_as_on_the_bench')


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
