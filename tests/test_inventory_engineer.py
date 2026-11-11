"""Do not mistake unplaced bridge gatehouses for unreachable engineer repair.

Static SDK/cache evidence only; no assertion here promotes a module to benched.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('engineer_audit', ROOT / 'experimental/cnv/engineer_audit.py')
engineer_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engineer_audit)
import inventory
import retailmodules
import simunits


def test_engineer_indirect_bridge_routes_remain_unbenched():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK declarations and retail placement cache')
    report = engineer_audit.audit()
    census = retailmodules.module_census()['Behaviors', 'EngineerContain']
    assert report['templates'] == census['templates']
    assert report['campaign_templates'] == census['campaign']
    assert report['unresolved'] == {'include': 0, 'parse': 2}
    assert {Path(p).name for p in report['skipped_parse']} == {'MY_Boat_01b.xml', 'Structure.xml'}
    # Direct placements are zero, yet BridgeBuilder references reach gatehouses.
    assert report['bridge_templates'] > 0
    assert report['bridge_campaign_templates'] == 0
    builders = [r for r in report['bridge_builders'] if r['maps']]
    assert builders
    assert any('camp_a03_heidelberg_smith' in r['maps'] for r in builders)
    bridge_names = {r['template'] for r in report['bridge']}
    assert {r['gatehouse'] for r in builders} <= bridge_names
    for template in bridge_names:
        module = simunits.engineer_contain(template)
        # Some generated gatehouse ids are absent from the simulator's index;
        # neither missing data nor an explicit bridge rejection is coverage.
        assert module is None or not module['supported'], template
    # ReplaceWith is a schema option, with no declaration in this retail census.
    assert report['replacement_templates'] == report['replacement_campaign_templates'] == 0
    key = inventory.MODULE, 'Behaviors/EngineerContain'
    assert key not in inventory.BENCHED_TESTS
    assert inventory.NOTES[key][0] == inventory.GUESSED
