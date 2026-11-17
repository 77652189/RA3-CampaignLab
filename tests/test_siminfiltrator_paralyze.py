"""Named replay of E128 retail PARALYZE entry observations, including open gaps."""
import importlib.util
from pathlib import Path

import pytest


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


def test_paralyze_japanese_movement_as_on_the_bench():
    """E133 Japanese host: stable windows, same existing-unit controls.

    Prediction fixed before the run: entry consumes enemy spy, refuses ally,
    HP/owner unchanged, only same-owner Mirage delayed. Exact clocks INFERRED.
    Original observations: work/re/e133_paralyze_japan.md.
    """
    import build
    import sim
    m, t, mod = build.resolve('engine_infpjap', 'a')
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


def test_paralyze_japanese_unmeasured_configuration_stays_a_gap():
    """Host extension admits only the measured complete retail configuration."""
    import build
    import sim
    import siminfiltrator
    m, t, _ = build.resolve('engine_infpjap', 'a')
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


@pytest.mark.parametrize('mission_name', ['engine_infpatk', 'engine_infasov', 'engine_infajap'])
def test_paralyze_attack_as_on_the_bench(mission_name):
    """E139/E140/E141 isolated Allied/Soviet/Japanese host attack trials.

    Original readings: work/re/e139_paralyze_attack.md and
    work/re/e140_paralyze_soviet_attack.md and
    work/re/e141_paralyze_japan_attack.md.

    Baseline and recovery must damage all three living targets. During the
    pause only the same-owner Mirage target stays full. Windows and damage
    bounds were fixed before running; exact damage/entry/expiry remain gaps.
    New orders in each trial do not establish retained-order behavior.
    """
    import build
    import sim
    m, t, mod = build.resolve(mission_name, 'a')
    assert len(mod) <= 15 and '_' not in mod
    s = sim.Sim(m, t).run(55)
    for start, end in [(8, 9), (26, 40), (54, 55)]:
        rows = [values for second, values in s.series if start <= second <= end]
        assert rows
        for entry, included, excluded, third in rows:
            assert entry == (111111 if start == 8 else 111011)
            if start == 26:
                assert included == 1100
            else:
                assert 1000 < included < 1100
            assert 1000 < excluded < 1100
            assert 1000 < third < 1100
    assert not s.body(m.role('enemy spy').name).alive
    assert s.body(m.role('ally spy').name).alive


@pytest.mark.parametrize('movement, variant, attack, host', [
    ('engine_infpara', 'b', 'engine_infpatk', 'AlliedTechStructure'),
    ('engine_infpsov', 'a', 'engine_infasov', 'SovietTechStructure'),
    ('engine_infpjap', 'a', 'engine_infajap', 'JapanTechStructure')])
def test_paralyze_complete_configuration_as_on_the_bench(movement, variant, attack, host):
    """E202 complete retail configuration, replaying both measured consumers.

    Stable movement and damage/no-damage windows were fixed before the runs.
    Exact arrival and damage counters have a separate regression below;
    production, repeated entry and retained orders remain gaps.
    See work/re/e202_paralyze.md and E128/E129/E133/E139/E140/E141.
    """
    import build
    import sim
    import siminfiltrator
    for name, check, until in [(movement, variant, 50), (attack, 'a', 55)]:
        m, t, _ = build.resolve(name, check)
        s = sim.Sim(m, t)
        target = s.body(m.role('enemy').name)
        assert target.template == host
        rule = siminfiltrator.spec(host)
        assert {k: v for k, v in rule.items() if k not in ('id', 'xmlns')} == {
            'Effect': 'PARALYZE', 'Duration': '30s',
            'UnitFilter': 'InfiltrationParalyzeObjectFilter'}
        assert siminfiltrator.Infiltrators(s).paralyze_rule(target, rule)
        s.run(until)
        for start, end, wanted in (
                [(1, 7, [11100, 11100, 0, 0]),
                 (30, 35, [1100, 11100, 0, 110]),
                 (49, 50, [1100, 11100, 0, 111])] if name == movement else
                [(8, 9, None), (26, 40, None), (54, 55, None)]):
            rows = [v for second, v in s.series if start <= second <= end]
            assert rows
            for values in rows:
                if wanted is not None:
                    assert values == wanted
                else:
                    entry, included, excluded, third = values
                    assert entry == (111111 if start == 8 else 111011)
                    assert included == 1100 if start == 26 else 1000 < included < 1100
                    assert 1000 < excluded < 1100 and 1000 < third < 1100
        assert not s.body(m.role('enemy spy').name).alive
        assert s.body(m.role('ally spy').name).alive
        assert not any(key[0] == 'InfiltratorContain' for key in s.unmodeled)


@pytest.mark.xfail(strict=True, reason='三国原台基线HP76/95/76，模型80/95/80；精确武器时钟仍gap，见 work/re/e202_paralyze.md')
@pytest.mark.parametrize('name', ['engine_infpatk', 'engine_infasov', 'engine_infajap'])
def test_paralyze_exact_attack_readings_as_on_the_bench(name):
    """Preserve original HP counters without fitting the weapon clock."""
    import build
    import sim
    m, t, _ = build.resolve(name, 'a')
    s = sim.Sim(m, t).run(55)
    for start, end, wanted in [(8, 9, [111111, 1076, 1095, 1076]),
                               (26, 40, [111011, 1100, 1092, 1068]),
                               (54, 55, [111011, 1068, 1092, 1068])]:
        rows = [v for second, v in s.series if start <= second <= end]
        assert rows and all(v == wanted for v in rows), (name, start, rows)


@pytest.mark.xfail(strict=True, reason='台上到达秒21/21/22与45/46/45，模型23与47；精确移动/进入时钟gap，见 work/re/e202_paralyze.md')
@pytest.mark.parametrize('name, variant, control, included', [
    ('engine_infpara', 'b', 21, 45), ('engine_infpsov', 'a', 21, 46),
    ('engine_infpjap', 'a', 22, 45)])
def test_paralyze_exact_arrival_readings_as_on_the_bench(name, variant, control, included):
    """Original compressed seconds are retained, not claimed as frame boundaries."""
    import build
    import sim
    m, t, _ = build.resolve(name, variant)
    s = sim.Sim(m, t).run(50)
    first = [next(second for second, values in s.series if values[3] // scale % 10)
             for scale in (1, 10, 100)]
    assert first == [included, control, control]
