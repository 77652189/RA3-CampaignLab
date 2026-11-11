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
