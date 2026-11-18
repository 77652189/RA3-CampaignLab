"""E197 named aircraft infiltration replay; observation effects remain gaps."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_infair', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_aircraft_entry_as_on_the_bench():
    """Only consume the enemy spy; leave friendly spy and both full-HP owners."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infair', 'a')
    s = sim.Sim(m, t).run(35)
    for start, end, expected in ((1, 7, [11100, 11100]), (29, 35, [1100, 11100])):
        rows = [values[:2] for second, values in s.series if start <= second <= end]
        assert rows and all(row == expected for row in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    for role, side in (('enemy', 's1'), ('ally', 's5')):
        host = s.body(m.role(role).name)
        assert host.owner == m.player(side) and host.hp == host.max_hp
    assert ('InfiltratorContain', 'AlliedAirfield') in s.unmodeled
    assert not s.infiltrators.observers


@pytest.mark.xfail(strict=True, reason='E197 a墙钟s1–28仍有敌间谍，模型较早入楼；'
                   '不拟合墙钟/移动，见 work/re/e197_aircraft.md')
def test_aircraft_early_entry_window_as_on_the_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_infair', 'a')
    s = sim.Sim(m, t).run(35)
    for start, end, expected in ((1, 28, [11100, 11100]), (29, 35, [1100, 11100])):
        rows = [values[:2] for second, values in s.series if start <= second <= end]
        assert rows and all(row == expected for row in rows), rows


def test_aircraft_marker_identity_as_on_the_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_infair', 'a')
    s = sim.Sim(m, t).run(68)
    assert s.series and all(values[3] == 511 for _, values in s.series)


def test_aircraft_no_hostile_entry_as_on_the_bench():
    """The same separated controls stay hidden without hostile entry."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infair', 'b')
    s = sim.Sim(m, t).run(62)
    assert s.series and all(values == [11100, 11100, 0, 511] for _, values in s.series)
    assert s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    assert not any(s.infiltrators.entered(b, 'aircraft') for b in s.living() if s.infiltrators.module(b))
    assert not s.infiltrators.observers


@pytest.mark.xfail(strict=True, reason='E197 a匹配飞机可见位1/0间歇，其他两位0；'
                   '观察者/筛选调度未实现，见 work/re/e197_aircraft.md')
def test_aircraft_discovery_as_on_the_bench():
    """Actual a samples; do not replace the failed original s20 prediction."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infair', 'a')
    s = sim.Sim(m, t).run(68)
    for start, end, expected in ((1, 28, 0), (29, 46, 1), (48, 49, 0),
                                 (51, 59, 1), (62, 62, 0), (63, 68, 1)):
        rows = [values[2] for second, values in s.series if start <= second <= end]
        assert rows and all(value == expected for value in rows), rows


@pytest.mark.parametrize('variant', ['duration', 'filter', 'extra', 'host', 'spy', 'player', 'repeat', 'entry_recheck'])
def test_aircraft_unmeasured_entry_stays_gap(variant):
    """A measured host must not silently enable other complete configurations."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infair', 'a')
    s = sim.Sim(m, t)
    target, spy = (s.body(m.role(role).name) for role in ('enemy', 'enemy spy'))
    rule = s.infiltrators.spec(target)
    if variant == 'duration':
        rule['UnitDuration'] = '29s'
    elif variant == 'filter':
        rule['UnitFilter'] = 'InfiltrationVehicleObjectFilter'
    elif variant == 'extra':
        rule['BlockedDuration'] = '1s'
    elif variant == 'host':
        target.template = 'SovietAirfield'
    elif variant == 'spy':
        spy.template = 'JapanInfiltrationInfantry'
    elif variant == 'player':
        spy.owner = m.player('s6')
        s.relations[target.owner, spy.owner] = 'Enemy'
    elif variant == 'repeat':
        s.infiltrators.mark(target, 'aircraft')
    s.infiltrators.send(spy, target)
    if variant == 'entry_recheck':
        assert spy.mode == 'infiltrate'
        s.infiltrators.mark(target, 'aircraft')
        spy.x, spy.y, spy.path = target.x, target.y, []
        s.infiltrators.tick()
    assert spy.alive and not s.infiltrators.going
    assert ('InfiltratorContain', target.template) in s.unmodeled
