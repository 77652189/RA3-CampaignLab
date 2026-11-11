"""EngineerContain: replay the four ordinary-entry routes, not instant garrison."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_engineer', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_engineer_four_routes_as_on_the_bench():
    """engine_engineer:a 2026-11-10 PASS: s12-s38 1050/1050/100/10050;
    baseline s1-s11 all 10050. Exact arrival time remains INFERRED."""
    import build
    import sim
    m, t, _ = build.resolve('engine_engineer', 'a')
    s = sim.Sim(m, t).run(36)
    assert s.series[0][1] == [10050] * 4
    assert s.series[-1][1] == [1050, 1050, 100, 10050]
    assert s.body(m.role('ally').name).owner == m.player('s2')
    assert s.body(m.role('refused').name).owner == m.player('s1')
    assert [s.body(m.role(role + ' man').name).alive
            for role in ('neutral', 'enemy', 'ally', 'refused')] == [False, False, False, True]


def test_engineer_filters_reject_wrong_template_and_enemy_defence_and_report_replacements():
    import build
    import sim
    import simunits
    m, t, _ = build.resolve('engine_engineer', 'a')
    s = sim.Sim(m, t)
    man = s.body(m.role('neutral man').name)
    tower = s.body(m.role('refused').name)
    assert not s.engineer_entry(man, tower)
    tower.owner = man.owner
    assert s.engineer_entry(man, tower)
    man.template = 'AlliedAntiInfantryInfantry'
    assert not s.engineer_entry(man, tower)
    assert simunits.engineer_contain(man.template) is None
    own = {'Child': '<GameObject id="Child" inheritFrom="AlliedPowerPlant"/>'}
    assert simunits.engineer_contain('Child', own) == simunits.engineer_contain('AlliedPowerPlant')
    # A replacement is deliberately not implemented by the capture-only path.
    own['Replacement'] = ('<GameObject id="Replacement"><Behaviors>'
                          '<EngineerContain ImmediatelyEnabled="true" ReplaceWith="Unmeasured"/>'
                          '</Behaviors></GameObject>')
    s.own.update(own)
    tower.template = 'Replacement'
    assert not s.engineer_entry(man, tower)
    assert ('EngineerContain', 'Replacement') in s.unmodeled
    own['Filtered'] = ('<GameObject id="Filtered"><Behaviors><EngineerContain ImmediatelyEnabled="true">'
                       '<CanEnterFilter Rule="NONE" ExcludeStatusBitFlags="IMMOBILE">'
                       '<IncludeThing>AlliedEngineer</IncludeThing></CanEnterFilter>'
                       '</EngineerContain></Behaviors></GameObject>')
    assert not simunits.engineer_contain('Filtered', own)['supported']


def test_engineer_capture_keeps_the_existing_derrick_bonus_and_deposit():
    import simbench
    status, lines = simbench.run('derrick')
    assert status == 0, '\n'.join(lines)


def test_engineer_partial_slice_does_not_register_the_whole_module_as_benched():
    import inventory
    key = inventory.MODULE, 'Behaviors/EngineerContain'
    assert key not in inventory.BENCHED_TESTS
    assert inventory.NOTES[key][0] == inventory.GUESSED
