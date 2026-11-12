"""Replay retail spy readings; do not claim whole-module coverage."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_infiltrator', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('check, template, plant_template', [
    ('a', 'AlliedInfiltrationInfantry', 'AlliedPowerPlant'),
    ('b', 'JapanInfiltrationInfantry', 'AlliedPowerPlant'),
    ('c', 'AlliedInfiltrationInfantry', 'SovietPowerPlant'),
    ('d', 'AlliedInfiltrationInfantry', 'JapanPowerPlant')])
def test_spy_power_plant_as_on_the_bench(check, template, plant_template):
    """engine_infiltrator:a/b/c/d: enemy consumed/20s outage; ally refused, owners stay.

    Bench s1-s10 11100/11100/101/101; s11-s30 1100/11100/12/101;
    s31-s56 1100/11100/101/101. Travel timing INFERRED: stable windows only.
    b: s1-s9 baseline; s10-s29 outage; s30-s56 recovered, same values.
    c (Soviet plant): s1-s10 baseline; s11-s30 outage; s31-s56 recovered.
    d (Japan plant): s1-s10 baseline; s12-s30 outage; s31-s60 recovered;
    s11 absent from sampled frames, so no exact entry-frame claim.
    """
    import build
    import sim
    m, t, mod = build.resolve('engine_infiltrator', check)
    assert len(mod) <= 15 and '_' not in mod
    assert all(m.role(role + ' spy').template == template for role in ('enemy', 'ally'))
    assert all(m.role(role).template == plant_template for role in ('enemy', 'ally'))
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
        assert plant.template == plant_template
        assert plant.owner == m.player(side)
        assert plant.hp == plant.max_hp
    assert not any(key[0] == 'InfiltratorContain' for key in s.unmodeled)
    assert len(s.infiltrators.off_until) == 1
    assert not s.short_of_power(m.player('s1'))
    disabled = [second for second, values in s.series if values[2] == 12]
    step = s.series[1][0] - s.series[0][0]
    assert 19 <= disabled[-1] - disabled[0] + step <= 21


@pytest.mark.parametrize('variant', ['duration', 'spy', 'player', 'repeat'])
def test_ordinary_vision_unmeasured_variants_report_gap(variant):
    import build
    import sim
    m, t, _ = build.resolve('engine_infvis', 'a')
    s = sim.Sim(m, t)
    spy, yard = s.body(m.role('enemy spy').name), s.body(m.role('enemy').name)
    if variant == 'duration':
        s.infiltrators.spec(yard)['Duration'] = '10s'
    elif variant == 'spy':
        spy.template = 'JapanInfiltrationInfantry'
    elif variant == 'player':
        spy.owner = m.player('s3')
        s.relations[(yard.owner, spy.owner)] = 'Enemy'
    else:
        s.infiltrators.observers.append((spy.owner, yard, 0))
    s.infiltrators.send(spy, yard)
    assert ('InfiltratorContain', yard.template) in s.unmodeled
    assert spy.alive and not s.infiltrators.going


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


def test_spy_ordinary_vision_as_on_the_bench():
    """engine_infvis:a: actual discovered markers, consumed enemy, refused ally.

    s1-s10 11100/11100/0; s11-s15 1100/11100/0; s16-s37 1100/11100/1.
    Stable windows only; exact arrival/activation mechanism, other templates,
    observer destruction, radar freeze and repeated infiltration remain gaps.
    """
    import build
    import sim
    import siminfiltrator
    m, t, mod = build.resolve('engine_infvis', 'a')
    assert len(mod) <= 15 and '_' not in mod
    assert all(m.role(role).template == 'AlliedConstructionYard' for role in ('enemy', 'ally'))
    rule = siminfiltrator.spec('AlliedConstructionYard')
    assert (rule['Effect'], rule['Duration'], rule['ObjectRef']) == ('VISION', '-1s', 'VisionObserver')
    s = sim.Sim(m, t).run(35)
    for start, end, wanted in ((1, 7, [11100, 11100, 0]), (18, 35, [1100, 11100, 1])):
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), rows
    early = [values[2] for second, values in s.series if 12 <= second <= 14]
    assert early and all(value == 0 for value in early)
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        yard = s.body(m.role(role).name)
        assert yard.owner == m.player(side) and yard.hp == yard.max_hp
    assert not s.infiltrators.off_until
    assert not any(key[0] == 'InfiltratorContain' for key in s.unmodeled)


@pytest.mark.xfail(strict=True, reason='E61 RESET就绪条件与真实冷却未闭环；见 work/re/handoff-e.md 和 e_infreset_e61.md')
@pytest.mark.parametrize('check, until, windows', [
    ('a', 35, ((1, 8, [1011100, 1011100]), (9, 10, [1111100, 1111100]),
               (11, 20, [1001100, 1111100]), (21, 35, [1101100, 1111100]))),
    ('b', 55, ((1, 7, [1011100, 1011100]), (8, 30, [1111100, 1111100]),
               (31, 40, [1001100, 1111100]), (41, 55, [1101100, 1111100])))])
def test_spy_superweapon_reset_as_on_the_bench(check, until, windows):
    """engine_infreset:a/b: measured readings, not failed initial predictions.

    s1-s8 1011100/1011100; s9-s10 1111100/1111100;
    s11-s20 1001100/1111100; s21-s36 1101100/1111100.
    b: s1-s7 1011100/1011100; s8-s30 1111100/1111100;
    s31-s40 1001100/1111100; s41-s56 1101100/1111100.
    The condition returns true again too soon to prove a full retail reload.
    No cooldown rule or initial ready delay is fitted to these samples.
    """
    import build
    import sim
    import siminfiltrator
    m, t, mod = build.resolve('engine_infreset', check)
    assert len(mod) <= 15 and '_' not in mod
    assert siminfiltrator.spec('SovietSuperWeapon')['Effect'] == 'RESET'
    assert all(m.role(role).template == 'SovietSuperWeapon' for role in ('enemy', 'ally'))
    s = sim.Sim(m, t).run(until)
    for start, end, wanted in windows:
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        building = s.body(m.role(role).name)
        assert building.owner == m.player(side) and building.hp == building.max_hp
        assert not s.short_of_power(building.owner)


@pytest.mark.xfail(strict=True, reason='E60 STEAL_MONEY转账与矿车收入未闭环，清除匿名矿车无效；见 work/re/handoff-e.md 和 e_infmoney_e60.md')
def test_spy_refinery_money_as_on_the_bench():
    """engine_infmon:a: 2000 transfer followed by miner income, failed cleanup.

    Measured second run: no-miner bits stay zero; enemy bank recovers 250 twice.
    Both transfer and the failed unnamed-miner cleanup remain unimplemented.
    """
    import build
    import sim
    import siminfiltrator
    m, t, mod = build.resolve('engine_infmon', 'a')
    assert len(mod) <= 15 and '_' not in mod
    assert all(m.role(role).template == 'AlliedRefinery' for role in ('enemy', 'ally'))
    rule = siminfiltrator.spec('AlliedRefinery')
    assert (rule['Effect'], rule['Amount'], rule['BlockedDuration']) == ('STEAL_MONEY', '2000', '30s')
    s = sim.Sim(m, t).run(35)
    for start, end, wanted in ((2, 7, [11100, 11100, 1000, 5000]),
                               (11, 13, [1100, 11100, 3000, 3000]),
                               (18, 30, [1100, 11100, 3000, 3250]),
                               (35, 35, [1100, 11100, 3000, 3500])):
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        refinery = s.body(m.role(role).name)
        assert refinery.owner == m.player(side) and refinery.hp == refinery.max_hp
    assert not any(key[0] == 'InfiltratorContain' for key in s.unmodeled)
