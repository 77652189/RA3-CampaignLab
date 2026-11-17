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
    assert len(rows) == 11
    assert sum(r['uses'] for r in rows) == 34
    assert sum(r['all'] for r in rows) == 38
    measured = next(r for r in rows if r['name'].endswith(':ENERGY'))
    gap = next(r for r in rows if r['name'] == 'Behaviors/InfiltratorContain')
    assert (measured['uses'], measured['all'], measured['state']) == (4, 6, inventory.BENCHED)
    assert (gap['uses'], gap['all'], gap['state']) == (1, 1, inventory.GUESSED)
    assert measured['why'].startswith('tests/test_siminfiltrator.py::test_spy_power_plant_as_on_the_bench')
    import inventory_levels
    scope, _ = inventory_levels.expand_forms(rows, {
        (inventory.MODULE, 'Behaviors/InfiltratorContain'): {
            'a1': {'JapanPowerPlant', 'AlliedBarracks', 'UnknownPlant'}}})
    assert scope[(inventory.MODULE, measured['name'])]['a1'] == {'JapanPowerPlant'}
    infantry = next(r for r in rows if r['name'].endswith(':VISION_UNITS_INFANTRY'))
    assert scope[(inventory.MODULE, infantry['name'])]['a1'] == {'AlliedBarracks'}
    assert scope[(inventory.MODULE, gap['name'])]['a1'] == {'UnknownPlant'}


def test_infiltrator_energy_split_does_not_credit_changed_fields(monkeypatch):
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    raw = contain_audit.engineer_audit.audit('InfiltratorContain')
    monkeypatch.setattr(contain_audit.engineer_audit, 'audit', lambda kind: raw)
    for row in raw['rows']:
        for module in row['modules']:
            module['xml'] = module['xml'].replace('Amount="0.2"', 'Amount="0.3"')
    assert contain_audit.infiltrator_energy_share() == {'campaign': 0, 'templates': 0}


def test_infiltrator_money_split_preserves_weight_and_level_scope():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    assert contain_audit.infiltrator_money_share() == {'campaign': 3, 'templates': 4}
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/InfiltratorContain')]
    assert sum(r['uses'] for r in rows) == 34
    assert sum(r['all'] for r in rows) == 38
    money = next(r for r in rows if r['name'].endswith(':STEAL_MONEY'))
    assert (money['uses'], money['all'], money['state']) == (3, 4, inventory.BENCHED)
    assert money['why'].startswith('tests/test_siminfiltrator.py::test_spy_refinery_transfer_amount_as_on_the_bench')
    assert 'BlockedDuration收入阻断' in money['why']
    assert 'strict xfail' in money['why']
    import inventory_levels
    scope, _ = inventory_levels.expand_forms(rows, {
        (inventory.MODULE, 'Behaviors/InfiltratorContain'): {
            'a1': {'AlliedRefinery', 'JapanPowerPlant', 'AlliedBarracks'}}})
    assert scope[(inventory.MODULE, money['name'])]['a1'] == {'AlliedRefinery'}
    assert scope[(inventory.MODULE, 'Behaviors/InfiltratorContain:VISION_UNITS_INFANTRY')]['a1'] == {'AlliedBarracks'}
    assert (inventory.MODULE, 'Behaviors/InfiltratorContain') not in scope


@pytest.mark.parametrize('field, value', [('Amount', '1999'), ('BlockedDuration', '29s')])
def test_infiltrator_money_split_rejects_changed_fields(monkeypatch, field, value):
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    raw = contain_audit.engineer_audit.audit('InfiltratorContain')
    monkeypatch.setattr(contain_audit.engineer_audit, 'audit', lambda kind: raw)
    for row in raw['rows']:
        for module in row['modules']:
            element = retailmodules.ET.fromstring(module['xml'])
            if element.get('Effect') == 'STEAL_MONEY':
                element.set(field, value)
                module['xml'] = retailmodules.ET.tostring(element, encoding='unicode')
    assert contain_audit.infiltrator_money_share() == {'campaign': 0, 'templates': 0}


@pytest.mark.parametrize('effect, selector, uses, templates, boundary', [
    ('KILL', '', 1, 1, 'KILL 1用量/1模板部分已测'),
    ('PARALYZE', '', 3, 3, 'PARALYZE单列3用量/3模板已对拍'),
    ('VISION', '', 5, 5, '普通VISION 5用量/5模板部分已测且暂停扩宿主'),
    ('VISION', '9999999s', 1, 1, '港口阻断VISION单列1用量/1模板，实测边界见该行'),
    ('VISION_UNITS', 'InfiltrationAircraftObjectFilter', 2, 2, '飞机VISION_UNITS单列已接E199前300帧周期'),
    ('VISION_UNITS', 'InfiltrationInfantryObjectFilter', 3, 3, '步兵VISION_UNITS单列已接E199前300帧周期'),
    ('VISION_UNITS', 'InfiltrationShipObjectFilter', 3, 3, '舰船VISION_UNITS已独立分区，实测边界见该行'),
    ('RESET', '', 5, 6, 'RESET单列仅入楼已接'),
])
def test_infiltrator_residual_closure_preserves_each_configuration_gap(
        effect, selector, uses, templates, boundary):
    """A successful PARALYZE replay cannot grant the other forms bench credit.

    Static counts only: actual readings stay in the named siminfiltrator tests.
    Match the eight remaining forms against the SDK census and their public scope.
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


def test_infiltrator_reset_configuration_stays_guessed_until_cooldown_replays():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    assert contain_audit.infiltrator_reset_share() == {'campaign': 5, 'templates': 6}
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/InfiltratorContain')]
    reset = next(r for r in rows if r['name'].endswith(':RESET'))
    assert (reset['uses'], reset['all'], reset['state']) == (5, 6, inventory.GUESSED)
    assert (inventory.MODULE, reset['name']) not in inventory.BENCHED_TESTS
    assert sum(r['uses'] for r in rows) == 34
    assert sum(r['all'] for r in rows) == 38
    assert 'strict xfail' in reset['why'] and 'work/re/e195_reset.md' in reset['why']


def test_infiltrator_vehicle_configuration_stays_guessed_until_discovery_replays():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    assert contain_audit.infiltrator_vehicle_share() == {'campaign': 4, 'templates': 4}
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/InfiltratorContain')]
    vehicle = next(r for r in rows if r['name'].endswith(':VISION_UNITS_VEHICLE'))
    assert (vehicle['uses'], vehicle['all'], vehicle['state']) == (1, 1, inventory.GUESSED)
    assert (inventory.MODULE, vehicle['name']) not in inventory.BENCHED_TESTS
    assert sum(r['uses'] for r in rows) == 34
    assert sum(r['all'] for r in rows) == 38
    assert 'strict xfail' in vehicle['why'] and 'work/re/e194_vehicle.md' in vehicle['why']
    import inventory_levels
    scope, _ = inventory_levels.expand_forms(rows, {
        (inventory.MODULE, 'Behaviors/InfiltratorContain'): {
            'a1': {'AlliedWarFactory', 'AlliedRefinery', 'AlliedBarracks'}}})
    assert scope[(inventory.MODULE, vehicle['name'])]['a1'] == {'AlliedWarFactory'}
    assert scope[(inventory.MODULE, 'Behaviors/InfiltratorContain:VISION_UNITS_INFANTRY')]['a1'] == {'AlliedBarracks'}
    assert (inventory.MODULE, 'Behaviors/InfiltratorContain') not in scope


@pytest.mark.parametrize('field, value', [
    ('Duration', '29s'), ('UnitDuration', '29s'), ('ObjectRef', 'VisionObserver'),
    ('UnitFilter', 'InfiltrationInfantryObjectFilter'),
    ('StructureFilter', 'InfiltrationEnergyStructuresFilter')])
def test_infiltrator_vehicle_configuration_rejects_changed_fields(monkeypatch, field, value):
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    raw = contain_audit.engineer_audit.audit('InfiltratorContain')
    monkeypatch.setattr(contain_audit.engineer_audit, 'audit', lambda kind: raw)
    for row in raw['rows']:
        for module in row['modules']:
            element = retailmodules.ET.fromstring(module['xml'])
            if element.get('Effect') == 'VISION_UNITS' and element.get('UnitFilter') == 'InfiltrationVehicleObjectFilter':
                element.set(field, value)
                module['xml'] = retailmodules.ET.tostring(element, encoding='unicode')
    assert contain_audit.infiltrator_vehicle_share() == {'campaign': 0, 'templates': 0}


def test_infiltrator_ordinary_vision_configuration_keeps_timing_gap():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    share = contain_audit.infiltrator_vision_share(with_templates=True)
    assert (share['campaign'], share['templates']) == (5, 5)
    assert 'JapanConstructionYard' in share['template_ids']
    assert 'AlliedNavalYard' not in share['template_ids']
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/InfiltratorContain')]
    vision = next(r for r in rows if r['name'].endswith(':VISION'))
    assert (vision['uses'], vision['all'], vision['state']) == (5, 5, inventory.GUESSED)
    assert (inventory.MODULE, vision['name']) not in inventory.BENCHED_TESTS
    assert 'strict xfail' in vision['why'] and 'work/re/e196_vision.md' in vision['why']
    assert sum(r['uses'] for r in rows) == 34
    assert sum(r['all'] for r in rows) == 38


def test_infiltrator_aircraft_configuration_keeps_discovery_gap():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    assert contain_audit.infiltrator_aircraft_share() == {'campaign': 2, 'templates': 2}
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/InfiltratorContain')]
    aircraft = next(r for r in rows if r['name'].endswith(':VISION_UNITS_AIRCRAFT'))
    assert (aircraft['uses'], aircraft['all'], aircraft['state']) == (2, 2, inventory.GUESSED)
    assert (inventory.MODULE, aircraft['name']) not in inventory.BENCHED_TESTS
    assert sum(r['uses'] for r in rows) == 34
    assert sum(r['all'] for r in rows) == 38
    assert 'strict xfail' in aircraft['why'] and 'work/re/e197_aircraft.md' in aircraft['why']


def test_infiltrator_infantry_configuration_keeps_discovery_gap():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    assert contain_audit.infiltrator_infantry_share() == {'campaign': 3, 'templates': 3}
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/InfiltratorContain')]
    infantry = next(r for r in rows if r['name'].endswith(':VISION_UNITS_INFANTRY'))
    assert (infantry['uses'], infantry['all'], infantry['state']) == (3, 3, inventory.GUESSED)
    assert (inventory.MODULE, infantry['name']) not in inventory.BENCHED_TESTS
    assert sum(r['uses'] for r in rows) == 34
    assert sum(r['all'] for r in rows) == 38
    assert 'strict xfail' in infantry['why'] and 'work/re/e198_infantry.md' in infantry['why']


def test_infiltrator_ship_configuration_keeps_discovery_gap():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    assert contain_audit.infiltrator_ship_share() == {'campaign': 3, 'templates': 3}
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/InfiltratorContain')]
    ship = next(r for r in rows if r['name'].endswith(':VISION_UNITS_SHIP'))
    assert (ship['uses'], ship['all'], ship['state']) == (3, 3, inventory.GUESSED)
    assert (inventory.MODULE, ship['name']) not in inventory.BENCHED_TESTS
    assert sum(r['uses'] for r in rows) == 34
    assert sum(r['all'] for r in rows) == 38
    assert 'work/re/e200_ship.md' in ship['why']
    import inventory_levels
    scope, _ = inventory_levels.expand_forms(rows, {
        (inventory.MODULE, 'Behaviors/InfiltratorContain'): {
            'a1': {'AlliedNavalYard', 'UnknownPlant'}}})
    assert scope[(inventory.MODULE, ship['name'])]['a1'] == {'AlliedNavalYard'}
    assert scope[(inventory.MODULE, 'Behaviors/InfiltratorContain')]['a1'] == {'UnknownPlant'}


def test_infiltrator_port_configuration_partition():
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    assert contain_audit.infiltrator_port_share() == {'campaign': 1, 'templates': 1}
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/InfiltratorContain')]
    port = next(r for r in rows if r['name'].endswith(':VISION_PORT'))
    assert (port['uses'], port['all'], port['state']) == (1, 1, inventory.BENCHED)
    assert inventory.BENCHED_TESTS[inventory.MODULE, port['name']] == (
        'tests/test_siminfiltrator_port.py::test_port_entry_and_blocked_repeat_as_on_the_bench')
    assert sum(r['uses'] for r in rows) == 34
    assert sum(r['all'] for r in rows) == 38
    assert 'work/re/e201_port.md' in port['why']
    import inventory_levels
    scope, _ = inventory_levels.expand_forms(rows, {
        (inventory.MODULE, 'Behaviors/InfiltratorContain'): {
            'a1': {'CA_PortStructure', 'UnknownPlant'}}})
    assert scope[(inventory.MODULE, port['name'])]['a1'] == {'CA_PortStructure'}
    assert scope[(inventory.MODULE, 'Behaviors/InfiltratorContain')]['a1'] == {'UnknownPlant'}


def test_infiltrator_paralyze_configuration_partition(monkeypatch):
    if not Path(retailmodules.SAGEXML).is_dir() or not Path(retailmodules.RETAILREF).is_dir():
        pytest.skip('needs SDK and retail placement cache')
    share = contain_audit.infiltrator_paralyze_share(with_templates=True)
    assert (share['campaign'], share['templates']) == (3, 3)
    assert set(share['template_ids']) == {
        'AlliedTechStructure', 'SovietTechStructure', 'JapanTechStructure'}
    rows = [r for r in inventory.collect((inventory.MODULE,))
            if r['name'].startswith('Behaviors/InfiltratorContain')]
    form = next(r for r in rows if r['name'].endswith(':PARALYZE'))
    assert (form['uses'], form['all'], form['state']) == (3, 3, inventory.BENCHED)
    assert inventory.BENCHED_TESTS[inventory.MODULE, form['name']] == (
        'tests/test_siminfiltrator_paralyze.py::test_paralyze_complete_configuration_as_on_the_bench')
    assert sum(r['uses'] for r in rows) == 34 and sum(r['all'] for r in rows) == 38
    assert 'strict xfail' in form['why'] and 'work/re/e202_paralyze.md' in form['why']
    import inventory_levels
    scope, _ = inventory_levels.expand_forms(rows, {
        (inventory.MODULE, 'Behaviors/InfiltratorContain'): {
            'a1': {'AlliedTechStructure', 'SovietCrane'}}})
    assert scope[(inventory.MODULE, form['name'])]['a1'] == {'AlliedTechStructure'}
    assert scope[(inventory.MODULE, 'Behaviors/InfiltratorContain')]['a1'] == {'SovietCrane'}
    raw = contain_audit.engineer_audit.audit('InfiltratorContain')
    monkeypatch.setattr(contain_audit.engineer_audit, 'audit', lambda kind: raw)
    from copy import deepcopy
    original = deepcopy(raw)
    for field, value in [('Duration', '29s'), ('UnitFilter', 'OtherFilter'),
                         ('BlockedDuration', '1s'), ('Effect', 'RESET')]:
        raw['rows'] = deepcopy(original['rows'])
        for row in raw['rows']:
            for module in row['modules']:
                element = retailmodules.ET.fromstring(module['xml'])
                if element.get('Effect') == 'PARALYZE':
                    element.set(field, value)
                    module['xml'] = retailmodules.ET.tostring(element, encoding='unicode')
        assert contain_audit.infiltrator_paralyze_share() == {'campaign': 0, 'templates': 0}, field
