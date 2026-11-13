"""Named replay of E128 retail PARALYZE entry observations, including open gaps."""
import importlib.util
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    'paralyze_bootstrap', Path(__file__).resolve().parents[1] / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_paralyze_entry_a_as_on_the_bench():
    """a: s1..10=11100/11100/0; s11..51=1100/11100/0.

    Assert the measured zero model-condition bits, not the failed prediction
    that the same-owner Mirage would expose PARALYZED. Exact entry is a gap.
    """
    import build
    import sim
    m, t, mod = build.resolve('engine_infpara', 'a')
    assert len(mod) <= 15 and '_' not in mod
    s = sim.Sim(m, t).run(50)
    for start, end, wanted in [(1, 7, [11100, 11100, 0]),
                               (18, 50, [1100, 11100, 0])]:
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(values == wanted for values in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive


def test_paralyze_movement_b_as_on_the_bench():
    """b: s21..44 arrivals=110; s45..60=111; condition bits remain zero.

    Use stable measured windows: no exact entry/expiry or arrival-frame claim.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_infpara', 'b')
    s = sim.Sim(m, t).run(50)
    for start, end, wanted in [(1, 7, [11100, 11100, 0, 0]),
                               (30, 35, [1100, 11100, 0, 110]),
                               (49, 50, [1100, 11100, 0, 111])]:
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(values == wanted for values in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    assert not any(key[0] == 'InfiltratorContain' for key in s.unmodeled)



def test_paralyze_soviet_movement_as_on_the_bench():
    """E129: Soviet host entry and stable three-car movement windows.

    Exact application, expiry and arrival seconds remain INFERRED.
    See work/re/e129_paralyze_soviet.md for original counter samples.
    """
    import build
    import sim
    m, t, mod = build.resolve('engine_infpsov', 'a')
    assert len(mod) <= 15 and '_' not in mod
    s = sim.Sim(m, t).run(50)
    for start, end, wanted in [(1, 7, [11100, 11100, 0, 0]),
                               (30, 35, [1100, 11100, 0, 110]),
                               (49, 50, [1100, 11100, 0, 111])]:
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows and all(values == wanted for values in rows), rows
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive
    assert not any(key[0] == 'InfiltratorContain' for key in s.unmodeled)



def test_paralyze_soviet_unmeasured_configuration_stays_a_gap():
    """A measured host must not silently admit unmeasured module overrides."""
    import build
    import sim
    import siminfiltrator
    m, t, _ = build.resolve('engine_infpsov', 'a')
    s = sim.Sim(m, t)
    host = s.body(m.role('enemy').name)
    effect = siminfiltrator.Infiltrators(s)
    rule = siminfiltrator.spec(host.template)
    assert effect.paralyze_rule(host, rule)
    for key, value in [('ImmediatelyEnabled', 'true'), ('BlockedDuration', '0s'),
                       ('UnitDuration', '5s'), ('StructureFilter', 'OtherFilter'),
                       ('CanEnterFilter', 'OtherEntry'), ('ObjectStatusToSet', 'IMMOBILE'),
                       ('InfiltratedStatusFilter', 'DESTROYED'), ('Amount', '1.0')]:
        assert not effect.paralyze_rule(host, dict(rule, **{key: value})), key
