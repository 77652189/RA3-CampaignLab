"""Named replay of the E138 Soviet crane entry comparison."""
import importlib.util
from pathlib import Path


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
    m, t, mod = build.resolve('engine_infkill', 'a')
    assert len(mod) <= 15 and '_' not in mod
    s = sim.Sim(m, t).run(30)
    for start, end, wanted in [(1, 7, [11100, 11100]),
                               (18, 30, [1100, 11100])]:
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(values == wanted for values in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    assert not any(key[0] == 'InfiltratorContain' for key in s.unmodeled)


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
                       ('CanEnterFilter', 'OtherFilter'), ('ImmediatelyEnabled', 'true')]:
        assert not effect.kill_rule(host, dict(rule, **{key: value})), key
    spy = s.body(m.role('enemy spy').name)
    spy.template = 'JapanInfiltrationInfantry'
    effect.send(spy, host)
    assert ('InfiltratorContain', host.template) in s.unmodeled
    assert spy.name not in effect.going
