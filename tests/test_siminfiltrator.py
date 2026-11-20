"""Replay retail spy readings; do not claim whole-module coverage."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_infiltrator', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.xfail(strict=True, reason='E194已接车辆工厂入楼；当前先卡在s10–16的入楼窗。原台s10已消耗敌间谍，读数1100/11100/1；'
                   'Sim在s10–12仍为11100/11100/0，到s13才完成进入。后续E77可见位间歇1/0的调度未闭合，'
                   '不拟合连续30秒揭示；见 work/re/e194_vehicle.md')
def test_spy_vehicle_factory_as_on_the_bench():
    """engine_infveh:a measured intermittent discovery, not the failed prediction.

    s1-s9=11100/11100/0; s10-s16=1100/11100/1; s18=1100/11100/0;
    s19-s25=1100/11100/1; s26-s27=1100/11100/0; s28-s29=1100/11100/1;
    s30=1100/11100/0; s32=1100/11100/1; s33=1100/11100/0;
    s34-s38=1100/11100/1. Absent samples impose no timing constraint.
    """
    import build
    import sim
    import engine.objects.infiltrator as siminfiltrator
    m, t, mod = build.resolve('engine_infveh', 'a')
    assert len(mod) <= 15 and '_' not in mod
    rule = siminfiltrator.spec('AlliedWarFactory')
    assert (rule['Effect'], rule['Duration'], rule['UnitDuration'], rule['ObjectRef']) == (
        'VISION_UNITS', '30s', '30s', 'UnitVisionObserver')
    s = sim.Sim(m, t).run(35)
    for start, end, wanted in ((1, 7, [11100, 11100, 0]),
                               (10, 16, [1100, 11100, 1]),
                               (18, 18, [1100, 11100, 0]),
                               (19, 25, [1100, 11100, 1]),
                               (26, 27, [1100, 11100, 0]),
                               (28, 29, [1100, 11100, 1]),
                               (30, 30, [1100, 11100, 0]),
                               (32, 32, [1100, 11100, 1]),
                               (33, 33, [1100, 11100, 0]),
                               (34, 35, [1100, 11100, 1])):
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    assert not any(key[0] == 'InfiltratorContain' for key in s.unmodeled)


@pytest.mark.xfail(strict=True, reason='E194原台s10已消耗，Sim到s13才完成进入；'
                   '不调通用移动/进入距离，见 work/re/e194_vehicle.md')
def test_spy_vehicle_factory_entry_window_as_on_the_bench():
    """E77 original mission: enemy consumed, friendly refused, neither captured.

    Keep the early and late measured entry windows. Discovery assertions stay
    unchanged in the strict xfail above; this test grants no reveal coverage.
    Travel/entry clock remains INFERRED.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_infveh', 'a')
    s = sim.Sim(m, t).run(35)
    for start, end, wanted in ((1, 7, [11100, 11100]), (10, 35, [1100, 11100])):
        rows = [values[:2] for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        factory = s.body(m.role(role).name)
        assert factory.owner == m.player(side) and factory.hp == factory.max_hp
    assert ('InfiltratorContain', 'AlliedWarFactory') in s.unmodeled
    assert not s.infiltrators.observers  # no invented continuous sight


@pytest.mark.parametrize('check', ['a', 'b', 'c'])
def test_spy_vehicle_factory_entry_as_on_the_bench(check):
    """E77 measured s19-s25 and s34-s35 entry state, independently of discovery.

    Earlier entry-window failure remains intact above. This comparison of
    existing late samples does not claim the entry clock or reveal effect.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_infveh', check)
    s = sim.Sim(m, t).run(35)
    for start, end, wanted in ((1, 7, [11100, 11100]),
                               (19, 25, [1100, 11100]), (34, 35, [1100, 11100])):
        rows = [values[:2] for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        factory = s.body(m.role(role).name)
        assert factory.owner == m.player(side) and factory.hp == factory.max_hp
    assert ('InfiltratorContain', 'AlliedWarFactory') in s.unmodeled
    assert not s.infiltrators.observers


@pytest.mark.parametrize('variant', ['duration', 'unit_duration', 'filter', 'structure_filter',
                                     'observer', 'host', 'spy', 'player', 'repeat', 'player_at_entry'])
def test_spy_vehicle_unmeasured_entry_reports_gap(variant):
    import build
    import sim
    m, t, _ = build.resolve('engine_infveh', 'a')
    s = sim.Sim(m, t)
    spy, target = s.body(m.role('enemy spy').name), s.body(m.role('enemy').name)
    fields = {'duration': ('Duration', '29s'), 'unit_duration': ('UnitDuration', '29s'),
              'filter': ('UnitFilter', 'InfiltrationInfantryObjectFilter'),
              'structure_filter': ('StructureFilter', 'InfiltrationEnergyStructuresFilter'),
              'observer': ('ObjectRef', 'VisionObserver')}
    if variant in fields:
        key, value = fields[variant]
        s.infiltrators.spec(target)[key] = value
    elif variant == 'host':
        target.template = 'SovietWarFactory'
    elif variant == 'spy':
        spy.template = 'JapanInfiltrationInfantry'
    elif variant == 'player':
        spy.owner = m.player('s3')
        s.relations[target.owner, spy.owner] = 'Enemy'
    elif variant == 'repeat':
        s.infiltrators.mark(target, 'vehicle')
    s.infiltrators.send(spy, target)
    if variant == 'player_at_entry':
        assert spy.mode == 'infiltrate'
        spy.owner = m.player('s3')
        s.relations[target.owner, spy.owner] = 'Enemy'
        spy.x, spy.y, spy.path = target.x, target.y, []
        s.infiltrators.tick()
    assert ('InfiltratorContain', target.template) in s.unmodeled
    assert spy.alive and not s.infiltrators.going
    assert not s.infiltrators.observers


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


@pytest.mark.parametrize('check, template', [
    ('a', 'AlliedConstructionYard'), ('b', 'SovietConstructionYard'),
    ('c', 'JapanConstructionYard')])
def test_spy_ordinary_vision_as_on_the_bench(check, template):
    """engine_infvis:a/b/c: actual discovered markers, consumed enemy, refused ally.

    a: s1-s10 11100/11100/0; s11-s15 1100/11100/0; s16-s37 1100/11100/1.
    b: s1-s10 11100/11100/0; s11-s17 1100/11100/0; s18-s38 1100/11100/1.
    c: s1-s10 11100/11100/0; s11-s18 1100/11100/0; s19-s39 1100/11100/1.
    c failed the unchanged s18 bench window; its exact timing is tested separately.
    Stable windows only; exact arrival/activation mechanism, other templates,
    observer destruction, radar freeze and repeated infiltration remain gaps.
    """
    import build
    import sim
    import engine.objects.infiltrator as siminfiltrator
    m, t, mod = build.resolve('engine_infvis', check)
    assert len(mod) <= 15 and '_' not in mod
    assert all(m.role(role).template == template for role in ('enemy', 'ally'))
    rule = siminfiltrator.spec(template)
    assert (rule['Effect'], rule['Duration'], rule['ObjectRef']) == ('VISION', '-1s', 'VisionObserver')
    s = sim.Sim(m, t).run(35)
    # Replay each host's measured readings; the bench check retains its original
    # s18 diagnostic threshold, which Japan failed. Do not fit the model to it.
    windows = ((1, 7, [11100, 11100, 0]),
               (19 if check == 'c' else 18, 35, [1100, 11100, 1]))
    for start, end, wanted in windows:
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


@pytest.mark.parametrize('check, until, entered', [('a', 35, 11), ('b', 55, 31)])
@pytest.mark.xfail(strict=True, reason='E195入楼晚于E61 s11/s31；不调通用移动或进入距离，见 work/re/e195_reset.md')
def test_spy_superweapon_reset_entry_window_as_on_the_bench(check, until, entered):
    """E61 a/b: replay HP, owner, spy and power independently of ready.

    Remove only the separately observed ready digit, preserving all other
    published digits. This does not assert a reset duration or ready clock.
    """
    import build
    import sim
    import engine.objects.infiltrator as siminfiltrator
    m, t, _ = build.resolve('engine_infreset', check)
    rule = siminfiltrator.spec('SovietSuperWeapon')
    assert {k: v for k, v in rule.items() if k not in ('xmlns', 'id')} == {'Effect': 'RESET'}
    s = sim.Sim(m, t).run(until)
    for start, end, wanted in ((1, entered - 1, [1011100, 1011100]),
                               (entered, until, [1001100, 1011100])):
        rows = [[value - (value // 100000 % 10) * 100000 for value in values]
                for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), rows
    for role, side, alive in (('enemy', 's1', False), ('ally', 's2', True)):
        target = s.body(m.role(role).name)
        assert s.body(m.role(role + ' spy').name).alive == alive
        assert target.owner == m.player(side) and target.hp == target.max_hp
        assert not s.short_of_power(target.owner)
    assert ('InfiltratorContain', 'SovietSuperWeapon') in s.unmodeled


@pytest.mark.parametrize('check, until, entered', [('a', 35, 21), ('b', 55, 41)])
def test_spy_superweapon_reset_entry_as_on_the_bench(check, until, entered):
    """E61's final stable samples: consumed enemy, refused ally, HP/owner/power.

    The earlier entry-window comparison above stays unchanged as strict xfail.
    These existing samples establish neither arrival nor cooldown timing.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_infreset', check)
    s = sim.Sim(m, t).run(until)
    for start, end, wanted in ((1, 7, [1011100, 1011100]),
                               (entered, until, [1001100, 1011100])):
        rows = [[value - (value // 100000 % 10) * 100000 for value in values]
                for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), rows
    for role, side, alive in (('enemy', 's1', False), ('ally', 's2', True)):
        target = s.body(m.role(role).name)
        assert s.body(m.role(role + ' spy').name).alive == alive
        assert target.owner == m.player(side) and target.hp == target.max_hp
        assert not s.short_of_power(target.owner)
    assert ('InfiltratorContain', 'SovietSuperWeapon') in s.unmodeled


@pytest.mark.parametrize('variant', ['config', 'host', 'spy', 'player', 'repeat'])
def test_spy_superweapon_reset_unmeasured_entry_reports_gap(variant):
    import build
    import sim
    m, t, _ = build.resolve('engine_infreset', 'a')
    s = sim.Sim(m, t)
    spy, target = s.body(m.role('enemy spy').name), s.body(m.role('enemy').name)
    if variant == 'config':
        s.infiltrators.spec(target)['BlockedDuration'] = '3s'
    elif variant == 'host':
        target.template = 'AlliedSuperWeapon'
    elif variant == 'spy':
        spy.template = 'JapanInfiltrationInfantry'
    elif variant == 'player':
        spy.owner = m.player('s3')
        s.relations[target.owner, spy.owner] = 'Enemy'
    else:
        s.infiltrators.mark(target, 'reset')
    s.infiltrators.send(spy, target)
    assert not s.infiltrators.going
    assert spy.alive
    assert ('InfiltratorContain', target.template) in s.unmodeled


@pytest.mark.xfail(strict=True, reason='E195仅接RESET入楼；E61就绪条件与真实冷却未闭环；见 work/re/e195_reset.md')
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
    import engine.objects.infiltrator as siminfiltrator
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


@pytest.mark.xfail(strict=True, reason='E193入楼晚于台上s11稳定窗；不调通用移动/进入距离，见 work/re/e193_money.md')
def test_spy_refinery_transfer_window_as_on_the_bench():
    """engine_infmon:a E60: exact 2000 transfer, hostile consumed, ally refused.

    Replay the measured pre-income window with the original mission. The
    failed engine cleanup differs from Sim: compare only the published
    HP/owner/spy digits here. The full counter (including the no-miner bit)
    and later income keep their original assertions in the strict xfail.
    Entry reach/clock remain INFERRED; see work/re/e193_money.md.
    """
    import build
    import sim
    import engine.objects.infiltrator as siminfiltrator
    m, t, mod = build.resolve('engine_infmon', 'a')
    assert len(mod) <= 15 and '_' not in mod
    rule = siminfiltrator.spec('AlliedRefinery')
    assert (rule['Effect'], rule['Amount'], rule['BlockedDuration']) == ('STEAL_MONEY', '2000', '30s')
    s = sim.Sim(m, t).run(13)
    for start, end, wanted in ((2, 7, [11100, 11100, 1000, 5000]),
                               (11, 13, [1100, 11100, 3000, 3000])):
        rows = [[values[0] % 100000, values[1] % 100000, *values[2:]]
                for second, values in s.series if start <= second <= end]
        assert rows and all(row == wanted for row in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        refinery = s.body(m.role(role).name)
        assert refinery.owner == m.player(side) and refinery.hp == refinery.max_hp
    assert s.money[m.player('s2')] == 5000
    assert not any(key[0] == 'InfiltratorContain' for key in s.unmodeled)


def test_spy_refinery_transfer_amount_as_on_the_bench():
    """engine_infmon:a s13: exact balances and entry effects, not arrival clock.

    E60 reads p1=3000/s1=3000 at s13, with hostile spy consumed,
    friendly spy alive and both refinery HP/owners unchanged. The window
    replay above keeps the unresolved earlier arrival as strict xfail.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_infmon', 'a')
    s = sim.Sim(m, t).run(13)
    rows = [values[2:] for second, values in s.series if second == 13]
    assert rows == [[3000, 3000]]
    assert s.money[m.player('s2')] == 5000
    for role, side, alive in (('enemy', 's1', False), ('ally', 's2', True)):
        refinery = s.body(m.role(role).name)
        spy = s.body(m.role(role + ' spy').name)
        assert spy.alive == alive
        assert refinery.owner == m.player(side) and refinery.hp == refinery.max_hp
    assert not any(key[0] == 'InfiltratorContain' for key in s.unmodeled)


@pytest.mark.parametrize('variant', ['amount', 'blocked', 'host', 'spy', 'player', 'repeat', 'poor', 'poor_at_entry'])
def test_spy_refinery_unmeasured_money_variants_report_gap(variant):
    import build
    import sim
    m, t, _ = build.resolve('engine_infmon', 'a')
    s = sim.Sim(m, t)
    spy, target = s.body(m.role('enemy spy').name), s.body(m.role('enemy').name)
    s.money[target.owner] = 5000
    s.money[spy.owner] = 1000
    if variant == 'amount':
        s.infiltrators.spec(target)['Amount'] = '1999'
    elif variant == 'blocked':
        s.infiltrators.spec(target)['BlockedDuration'] = '29s'
    elif variant == 'host':
        target.template = 'SovietRefinery'
    elif variant == 'spy':
        spy.template = 'JapanInfiltrationInfantry'
    elif variant == 'player':
        spy.owner = m.player('s3')
        s.relations[target.owner, spy.owner] = 'Enemy'
    elif variant == 'repeat':
        s.infiltrators.mark(target, 'money')
    elif variant == 'poor':
        s.money[target.owner] = 1999
    s.infiltrators.send(spy, target)
    if variant == 'poor_at_entry':
        assert spy.mode == 'infiltrate'
        s.money[target.owner] = 1999
        spy.x, spy.y, spy.path = target.x, target.y, []
        s.infiltrators.tick()
    assert ('InfiltratorContain', target.template) in s.unmodeled
    assert spy.alive and not s.infiltrators.going
    assert s.money[s.human] == 1000


@pytest.mark.xfail(strict=True, reason='E193已接2000转账；E60后续矿车收入时序与清除匿名矿车仍未闭环；见 work/re/e193_money.md')
def test_spy_refinery_money_as_on_the_bench():
    """engine_infmon:a: 2000 transfer followed by miner income, failed cleanup.

    Measured second run: no-miner bits stay zero; enemy bank recovers 250 twice.
    Transfer is covered separately; keep every original late-income assertion.
    """
    import build
    import sim
    import engine.objects.infiltrator as siminfiltrator
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
