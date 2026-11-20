"""E198 independent infantry configuration and named bench replays."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_inffoot', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_infantry_configuration():
    import build
    import engine.objects.infiltrator as siminfiltrator
    import engine.data.units as simunits
    import re
    m, t, mod = build.resolve('engine_inffoot', 'a')
    assert len(mod) <= 15 and '_' not in mod
    assert 'contract: ok' in build.show('engine_inffoot', 'a').lower()
    rule = siminfiltrator.spec(m.role('enemy').template)
    assert {k: v for k, v in rule.items() if k not in ('xmlns', 'id')} == {
        'Effect': 'VISION_UNITS', 'Duration': '30s', 'UnitDuration': '30s',
        'ObjectRef': 'UnitVisionObserver', 'UnitFilter': 'InfiltrationInfantryObjectFilter',
        'StructureFilter': 'InfiltrationInfantryStructuresFilter'}
    points = [m.site(m.role(role).site) for role in ('match', 'wrong', 'third')]
    assert all((a[0]-b[0])**2+(a[1]-b[1])**2 >= 900**2
               for i, a in enumerate(points) for b in points[i+1:])
    for role in ('match', 'third'):
        xml = simunits.retail_xml(m.role(role).template)
        assert 'INFANTRY' in re.search(r'KindOf="([^"]+)"', xml).group(1).split()
    assert len(t.counters) == 4
    assert [item[3] for item in t.expect] == [11100, 1100, 11100, 0, 1, 511]


def test_infantry_entry_as_on_the_bench():
    """Only consume the enemy spy; leave friendly spy and both full-HP owners."""
    import build
    import sim
    m, t, _ = build.resolve('engine_inffoot', 'a')
    s = sim.Sim(m, t).run(35)
    for start, end, expected in ((1, 7, [11100, 11100]), (20, 35, [1100, 11100])):
        rows = [values[:2] for second, values in s.series if start <= second <= end]
        assert rows and all(row == expected for row in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    for role, side in (('enemy', 's2'), ('ally', 's5')):
        host = s.body(m.role(role).name)
        assert host.owner == m.player(side) and host.hp == host.max_hp
    assert ('InfiltratorContain', 'AlliedBarracks') in s.unmodeled
    assert not s.infiltrators.observers


@pytest.mark.xfail(strict=True, reason='E198 a墙钟s1–18仍有敌间谍，模型较早入楼；'
                   '不拟合墙钟/移动，见 work/re/e198_infantry.md')
def test_infantry_early_entry_window_as_on_the_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_inffoot', 'a')
    s = sim.Sim(m, t).run(35)
    for start, end, expected in ((1, 18, [11100, 11100]), (20, 35, [1100, 11100])):
        rows = [values[:2] for second, values in s.series if start <= second <= end]
        assert rows and all(row == expected for row in rows), rows


def test_infantry_marker_identity_as_on_the_bench():
    import build
    import sim
    m, t, _ = build.resolve('engine_inffoot', 'a')
    s = sim.Sim(m, t).run(59)
    assert s.series and all(values[3] == 511 for _, values in s.series)


@pytest.mark.xfail(strict=True, reason='E198 a匹配步兵可见位1/0间歇，其他两位0；'
                   '观察者/筛选调度未实现，见 work/re/e198_infantry.md')
def test_infantry_discovery_as_on_the_bench():
    """Actual a samples; do not replace the failed original s20 prediction."""
    import build
    import sim
    m, t, _ = build.resolve('engine_inffoot', 'a')
    s = sim.Sim(m, t).run(59)
    for start, end, expected in ((1, 18, 0), (20, 24, 1), (25, 25, 0),
                                 (26, 26, 1), (28, 28, 0), (29, 29, 1),
                                 (31, 31, 0), (33, 50, 1), (52, 52, 0), (54, 59, 1)):
        rows = [values[2] for second, values in s.series if start <= second <= end]
        assert rows and all(value == expected for value in rows), rows


@pytest.mark.parametrize('variant', ['duration', 'filter', 'extra', 'host', 'spy', 'player', 'repeat', 'entry_recheck'])
def test_infantry_unmeasured_entry_stays_gap(variant):
    """A measured host must not silently enable other complete configurations."""
    import build
    import sim
    m, t, _ = build.resolve('engine_inffoot', 'a')
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
        target.template = 'SovietBarracks'
    elif variant == 'spy':
        spy.template = 'JapanInfiltrationInfantry'
    elif variant == 'player':
        spy.owner = m.player('s6')
        s.relations[target.owner, spy.owner] = 'Enemy'
    elif variant == 'repeat':
        s.infiltrators.mark(target, 'infantry')
    s.infiltrators.send(spy, target)
    if variant == 'entry_recheck':
        assert spy.mode == 'infiltrate'
        s.infiltrators.mark(target, 'infantry')
        spy.x, spy.y, spy.path = target.x, target.y, []
        s.infiltrators.tick()
    assert spy.alive and not s.infiltrators.going
    assert ('InfiltratorContain', target.template) in s.unmodeled


def test_infantry_wrong_kind_and_third_owner_as_on_the_bench():
    """The two negative controls stay hidden throughout the actual first run."""
    import build
    import sim
    m, t, _ = build.resolve('engine_inffoot', 'a')
    s = sim.Sim(m, t).run(59)
    assert s.series and all(values[2] in (0, 1) for _, values in s.series)


def test_infantry_no_hostile_entry_as_on_the_bench():
    """Actual b: all four rows remain constant without hostile entry."""
    import build
    import sim
    m, t, _ = build.resolve('engine_inffoot', 'b')
    s = sim.Sim(m, t).run(60)
    assert s.series and all(values == [11100, 11100, 0, 511] for _, values in s.series)
    assert s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    assert not any(s.infiltrators.entered(b, 'infantry') for b in s.bodies.values() if s.infiltrators.module(b))
    assert not s.infiltrators.observers
