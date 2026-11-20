"""E201 independent port configuration and actual bench readings."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simbench_infport', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_port_configuration():
    import build
    import engine.objects.infiltrator as siminfiltrator
    import engine.data.units as simunits
    m, t, mod = build.resolve('engine_infport', 'a')
    assert len(mod) <= 15 and '_' not in mod
    assert build.show('engine_infport', 'a').endswith('contract: ok')
    rule = siminfiltrator.spec(m.role('enemy').template)
    assert {k: v for k, v in rule.items() if k not in ('xmlns', 'id')} == {
        'Effect': 'VISION', 'Duration': '-1s', 'BlockedDuration': '9999999s',
        'ObjectRef': 'VisionObserver'}
    objects = {o.name: o for o in m.objects}
    host = objects[m.role('enemy').name]
    for role in ('match', 'third'):
        marker = objects[m.role(role).name]
        assert (marker.x-host.x)**2 + (marker.y-host.y)**2 < 600**2
        for source in ('enemy spy', 'ally spy', 'second', 'ally'):
            obj = objects[m.role(source).name]
            radius = simunits.resolve(obj.template)['shroud']
            assert (marker.x-obj.x)**2 + (marker.y-obj.y)**2 > radius**2
    assert len(t.counters) == 4
    assert [item[3] for item in t.expect] == [111100, 101100, 11100, 0, 101, 511]


def test_port_entry_and_blocked_repeat_as_on_the_bench():
    """engine_infport:a, actual stable rows after first and second orders."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infport', 'a')
    s = sim.Sim(m, t).run(41)
    for start, end, expected in ((1, 7, [111100, 11100, 0, 511]),
                                 (20, 41, [101100, 11100, 101, 511])):
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(row == expected for row in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    assert s.body(m.role('second').name).alive
    assert not s.infiltrators.going
    # Entry clock/observer internals and blocking expiry are still gaps.
    assert ('InfiltratorContain', 'CA_PortStructure') in s.unmodeled


@pytest.mark.parametrize('variant', ['duration', 'blocked_duration', 'extra', 'host', 'spy', 'player', 'entry_recheck'])
def test_port_unmeasured_configurations_stay_gaps(variant):
    import build
    import sim
    m, t, _ = build.resolve('engine_infport', 'a')
    s = sim.Sim(m, t)
    target, spy = (s.body(m.role(role).name) for role in ('enemy', 'enemy spy'))
    rule = s.infiltrators.spec(target)
    if variant == 'duration':
        rule['Duration'] = '30s'
    elif variant == 'blocked_duration':
        rule['BlockedDuration'] = '30s'
    elif variant == 'extra':
        rule['Amount'] = '1'
    elif variant == 'host':
        target.template = 'AlliedConstructionYard'
        # The port's module (its rule) stays with the thing: the changed name alone is the unmeasured host.
    elif variant == 'spy':
        spy.template = 'JapanInfiltrationInfantry'
    elif variant == 'player':
        spy.owner = m.player('s6')
        s.relations[target.owner, spy.owner] = 'Enemy'
    s.infiltrators.send(spy, target)
    if variant == 'entry_recheck':
        assert spy.mode == 'infiltrate'
        s.infiltrators.module(target).block(s.frame_now() + 100)
        spy.x, spy.y, spy.path = target.x, target.y, []
        s.infiltrators.tick()
    assert spy.alive and not s.infiltrators.going
    assert not s.infiltrators.observers
    if variant != 'entry_recheck':
        assert ('InfiltratorContain', target.template) in s.unmodeled


def test_port_second_entry_without_first_as_on_the_bench():
    """engine_infport:b: same second spy is accepted without prior infiltration."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infport', 'b')
    s = sim.Sim(m, t).run(41)
    for start, end, expected in ((1, 22, [111100, 11100, 0, 511]),
                                 (32, 41, [11100, 11100, 101, 511])):
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(row == expected for row in rows), rows
    assert s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    assert not s.body(m.role('second').name).alive


@pytest.mark.xfail(strict=True, reason='E201 b s25近同属已见、第三方未见，模拟器同帧均未见；'
                   '原入港/有效视野来源时钟未闭合，见 work/re/e201_port.md')
def test_port_second_entry_transition_as_on_the_bench():
    """Original b s25 transient is preserved; no entry-time fit is applied."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infport', 'b')
    s = sim.Sim(m, t).run(25)
    assert [values for second, values in s.series if second == 25] == [[111100, 11100, 1, 511]]
