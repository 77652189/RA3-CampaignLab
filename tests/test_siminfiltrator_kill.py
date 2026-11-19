"""Named replay of the E138 Soviet crane entry comparison."""
import importlib.util
from pathlib import Path

import pytest


_spec = importlib.util.spec_from_file_location(
    'kill_bootstrap', Path(__file__).resolve().parents[1] / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_kill_crane_entry_as_on_the_bench():
    """E138 a: s1..10=11100/11100; s11..31=1100/11100.

    Compare stable counters, not exact entry or fling distance.
    Original evidence: work/re/e138_infiltrator_kill.md.
    """
    import build
    import sim
    import siminfiltrator
    m, t, mod = build.resolve('engine_infkill', 'a')
    assert len(mod) <= 15 and '_' not in mod
    s = sim.Sim(m, t)
    for role in ('enemy', 'ally'):
        host = s.body(m.role(role).name)
        assert host.template == 'SovietCrane'
        rule = siminfiltrator.spec(host.template)
        assert {k: v for k, v in rule.items() if k not in ('id', 'xmlns')} == {
            'Effect': 'KILL', 'Amount': '1.5', 'EvaEventForInfiltratedPlayer': ''}
        assert s.infiltrators.kill_rule(host, rule)
    s.run(30)
    for start, end, wanted in [(1, 7, [11100, 11100]),
                               (18, 30, [1100, 11100])]:
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(values == wanted for values in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    gap = s.unmodeled['InfiltratorContain', 'SovietCrane']
    assert '抛飞/死亡模块派发未对拍' in gap['what']


def test_kill_unmeasured_configuration_stays_a_gap():
    """No fling scaling, extra fields or other spy templates gain acceptance."""
    import build
    import sim
    import siminfiltrator
    m, t, _ = build.resolve('engine_infkill', 'a')
    s = sim.Sim(m, t)
    host = s.body(m.role('enemy').name)
    effect = s.infiltrators
    rule = siminfiltrator.spec(host.template)
    assert effect.kill_rule(host, rule)
    for key, value in [('Amount', '2'), ('Duration', '30s'),
                       ('CanEnterFilter', 'OtherFilter'), ('ImmediatelyEnabled', 'true'),
                       ('EvaEventForInfiltratedPlayer', 'OtherEvent'), ('Effect', 'RESET')]:
        assert not effect.kill_rule(host, dict(rule, **{key: value})), key
    missing_event = dict(rule)
    missing_event.pop('EvaEventForInfiltratedPlayer')
    assert not effect.kill_rule(host, missing_event)
    nested = '''<GameObject id="SovietCrane"><Behaviors>
        <InfiltratorContain Effect="KILL" Amount="1.5" EvaEventForInfiltratedPlayer="">
            <CanEnterFilter Rule="ANY"/>
        </InfiltratorContain></Behaviors></GameObject>'''
    changed = siminfiltrator.spec(host.template, {host.template: nested})
    assert not effect.kill_rule(host, changed)
    sibling = nested.replace('<CanEnterFilter Rule="ANY"/>', '').replace(
        '</Behaviors>', '<InfiltratorContain Effect="RESET"/></Behaviors>')
    changed = siminfiltrator.spec(host.template, {host.template: sibling})
    assert not effect.kill_rule(host, changed)
    spy = s.body(m.role('enemy spy').name)
    spy.template = 'JapanInfiltrationInfantry'
    effect.send(spy, host)
    assert ('InfiltratorContain', host.template) in s.unmodeled
    assert spy.serial not in effect.going


@pytest.mark.xfail(strict=True, reason='E205 b敌间谍到s47仍存活，模型消耗；进入前置未闭合，见 work/re/e205_kill.md')
def test_kill_credit_probe_entry_as_on_the_bench():
    """b actual s1..47=11100/11100/0; zero credit is not KILL acceptance."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infkill', 'b')
    s = sim.Sim(m, t).run(30)
    for start, end in [(1, 7), (18, 30)]:
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(values == [11100, 11100, 0] for values in rows), rows


def test_kill_phase_probe_contract():
    """Resolve the diagnostic before spending a game on its readouts."""
    import build
    m, t, _ = build.resolve('engine_infkill', 'c')
    assert len(t.counters) == 4
    names = {obj.name for obj in m.objects}
    for script in t.scripts:
        for condition in script.when:
            if condition[0] == 'NAMED_INSIDE_AREA':
                assert condition[1] in names and condition[2] in t.areas


def test_kill_owner_credit_as_on_the_bench():
    """c measured s46..52=1100/11100/1/111; assert the independent credit.

    Original early-window/phase readings are retained separately below.
    Named killer identity, fling and death-module dispatch were not observed.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_infkill', 'c')
    s = sim.Sim(m, t).run(52)
    rows = [values for second, values in s.series if 46 <= second <= 52]
    assert rows and all(values[:3] == [1100, 11100, 1] for values in rows), rows


@pytest.mark.xfail(strict=True, reason='E205 c派发到s36、消失到s46，原18..30窗口仍未闭合；不拟合墙钟，见 work/re/e205_kill.md')
def test_kill_phase_probe_exact_readings_as_on_the_bench():
    """Preserve c actual four-line snapshots, including the failed prediction."""
    import build
    import sim
    m, t, _ = build.resolve('engine_infkill', 'c')
    s = sim.Sim(m, t).run(52)
    for start, end, wanted in [(18, 30, [11100, 11100, 0, 1]),
                               (36, 45, [11100, 11100, 0, 11]),
                               (46, 52, [1100, 11100, 1, 111])]:
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(values == wanted for values in rows), rows
