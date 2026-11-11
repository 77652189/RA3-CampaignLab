"""Replay the funded / zero-credit AI RepairUpdate probes by name."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('repair_simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)


@pytest.mark.parametrize('name, expected', [('repairai', [100, 50, 9900]), ('repairzero', [50, 50, 0])])
def test_ai_repair_funded_and_zero_credit_final_readings(name, expected):
    import build
    from parts import contract, merged

    w = simai.run(name, 'a', until=81, blocks=())
    e = w.sim
    assert not contract(merged(e.m, e.test))
    assert e.m.player('s1') in w.brains
    assert e.ai_switches[e.m.player('s1')]['SKIRMISH_AI_USE_REPAIRS'] == 1
    rows = [row for sec, row in e.series if 75 <= sec <= 80]
    assert rows
    assert all(row == expected for row in rows), rows
    assert build.report(e.test, e.series)[1] == 0


def test_ai_repair_funded_activation_and_cost_prediction():
    import build

    w = simai.run('repairai', 'a', until=81, blocks=())
    rows = [row for sec, row in w.sim.series if 75 <= sec <= 80]
    assert rows
    assert all(row == [100, 50, 9900] for row in rows), rows
    assert build.report(w.sim.test, w.sim.series)[1] == 0
    assert 'repair' in w.sim.used


def test_ai_repair_quarter_health_cost_prediction_and_bench_readings():
    import build
    import sim
    from parts import contract, merged

    m, t, _ = build.resolve('repairq', 'a')
    assert not contract(merged(m, t))
    e = sim.Sim(m, t)
    e.advance(15 * 25)
    plant = e.body(m.role('repair').name)
    assert plant.hp == pytest.approx(500, abs=6)
    assert e.money[plant.owner] == pytest.approx(9925, abs=1)
    assert e.repairs.active[plant.name]['cost'] == 300
    assert e.repairs.active[plant.name]['r'] == pytest.approx(1 / 1500)
    e.advance(15 * 76)
    rows = [row for sec, row in e.series if 90 <= sec <= 95]
    assert rows and all(row == [100, 50, 9775] for row in rows), rows
    assert build.report(t, e.series)[1] == 0
    assert 10000 - e.money[plant.owner] == 800 * .5 * .75 ** 2


@pytest.mark.xfail(strict=True, reason='E50: repairt:a blocked before build by hung tasklist; '
                   '75% initial health remains unmeasured/refused; see work/re/handoff-e.md 待答问题')
def test_ai_repair_three_quarter_health_cost_prediction_and_bench_readings():
    import build
    import sim
    from parts import contract, merged

    m, t, _ = build.resolve('repairt', 'a')
    assert not contract(merged(m, t))
    e = sim.Sim(m, t)
    e.advance(15 * 10)
    plant = e.body(m.role('repair').name)
    assert plant.hp == pytest.approx(850, abs=12)
    assert e.money[plant.owner] == pytest.approx(9990, abs=1)
    assert e.repairs.active[plant.name]['cost'] == 100
    assert e.repairs.active[plant.name]['r'] == pytest.approx(1 / 1500)
    e.advance(15 * 41)
    rows = [row for sec, row in e.series if 40 <= sec <= 45]
    assert rows and all(row == [100, 50, 9975] for row in rows), rows
    assert build.report(t, e.series)[1] == 0
    assert 10000 - e.money[plant.owner] == 800 * .5 * .25 ** 2


def test_ai_repair_rate_and_unmeasured_configuration_gate():
    import build
    import sim

    m, t, _ = build.resolve('repairai', 'a')
    e = sim.Sim(m, t)
    e.advance(15 * 25)
    plant = e.body(m.role('repair').name)
    assert plant.hp == pytest.approx(750, abs=6)
    assert e.money[plant.owner] == pytest.approx(9950, abs=1)
    assert e.repairs.active[plant.name]['cost'] == 200
    assert e.repairs.active[plant.name]['r'] == pytest.approx(1 / 1500)
    assert ('物体模块', 'RepairUpdate boundaries') in e.unmodeled
    plant.hp -= 10
    hp = plant.hp
    e.advance(15)
    assert plant.hp == hp
    assert ('物体模块', 'RepairUpdate interrupted') in e.unmodeled
    # An unhandled field must not disappear in the compact rule dictionary.
    m, t, _ = build.resolve('repairai', 'a')
    e = sim.Sim(m, t)
    plant = e.body(m.role('repair').name)
    # Replace the include with an explicit unsupported default-like module.
    import re
    e.own[plant.template] = re.sub(
        r'<xi:include\s+href="DATA:Includes/GenericBuildingRepair.xml"\s*/>',
        '<RepairUpdate id="Repair" RepopThreshold="50%"/>', e.own[plant.template])
    assert 'RepopThreshold' in e.own[plant.template]
    e.advance(15 * 80)
    assert plant.hp == 500
    assert e.money[plant.owner] == 10000
    assert ('物体模块', 'RepairUpdate') in e.unmodeled


@pytest.mark.parametrize('initial_health', [10, 75])
def test_ai_repair_unmeasured_initial_health_is_refused(initial_health):
    import sim
    from checks.engine_repair_ai import mission, check

    m = mission(True, initial_health)
    e = sim.Sim(m, check(m))
    e.advance(15 * 80)
    plant = e.body(m.role('repair').name)
    assert plant.hp == initial_health * 10
    assert e.money[plant.owner] == 10000
    assert ('物体模块', 'RepairUpdate') in e.unmodeled
