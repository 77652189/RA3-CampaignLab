"""Replay retail spy power-plant readings; do not claim whole-module coverage."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_infiltrator', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('check, template', [('a', 'AlliedInfiltrationInfantry'),
                                          ('b', 'JapanInfiltrationInfantry')])
def test_spy_power_plant_as_on_the_bench(check, template):
    """engine_infiltrator:a/b: enemy consumed/20s outage; ally refused, owners stay.

    Bench s1-s10 11100/11100/101/101; s11-s30 1100/11100/12/101;
    s31-s56 1100/11100/101/101. Travel timing INFERRED: stable windows only.
    b: s1-s9 baseline; s10-s29 outage; s30-s56 recovered, same values.
    """
    import build
    import sim
    m, t, mod = build.resolve('engine_infiltrator', check)
    assert len(mod) <= 15 and '_' not in mod
    assert all(m.role(role + ' spy').template == template for role in ('enemy', 'ally'))
    s = sim.Sim(m, t).run(55)
    assert all(s.body(m.role(role + ' spy').name).template == template
               for role in ('enemy', 'ally'))
    assert s.series[0][1] == [11100, 11100, 101, 101]
    for start, end, wanted in ((1, 7, [11100, 11100, 101, 101]),
                               (15, 27, [1100, 11100, 12, 101]),
                               (35, 55, [1100, 11100, 101, 101])):
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        plant = s.body(m.role(role).name)
        assert plant.owner == m.player(side)
        assert plant.hp == plant.max_hp
    assert not any(key[0] == 'InfiltratorContain' for key in s.unmodeled)
    assert len(s.infiltrators.off_until) == 1
    assert not s.short_of_power(m.player('s1'))
    disabled = [second for second, values in s.series if values[2] == 12]
    step = s.series[1][0] - s.series[0][0]
    assert 19 <= disabled[-1] - disabled[0] + step <= 21


def test_spy_entry_rechecks_relation_and_building_state_without_capturing():
    import build
    import sim
    m, t, _ = build.resolve('engine_infiltrator', 'a')
    s = sim.Sim(m, t)
    spy, plant = s.body(m.role('enemy spy').name), s.body(m.role('enemy').name)
    s.act('NAMED_GARRISON_SPECIFIC_BUILDING', [spy.name, plant.name], None)
    assert spy.mode == 'infiltrate'  # plant also has EngineerContain: spy must not go through capture
    spy.x, spy.y, spy.path = plant.x, plant.y, []
    plant.status.add('UNPACKING')
    s.infiltrators.tick()
    assert spy.alive and not s.infiltrators.off_until
    plant.status.remove('UNPACKING')
    s.infiltrators.send(spy, plant)
    plant.owner = spy.owner
    s.infiltrators.tick()
    assert spy.alive and not s.infiltrators.off_until


def test_unmeasured_infiltration_effect_reports_gap_instead_of_capture():
    import build
    import sim
    m, t, _ = build.resolve('engine_infiltrator', 'a')
    s = sim.Sim(m, t)
    spy, plant = s.body(m.role('enemy spy').name), s.body(m.role('enemy').name)
    s.infiltrators.spec(plant)['Effect'] = 'STEAL_MONEY'
    s.act('NAMED_GARRISON_SPECIFIC_BUILDING', [spy.name, plant.name], None)
    assert ('InfiltratorContain', plant.template) in s.unmodeled
    assert spy.alive and plant.owner == m.player('s1')
    assert not s.infiltrators.going
