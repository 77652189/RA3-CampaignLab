"""C line: PLAYER_ENABLE_UNIT_CONSTRUCTION, native engineer production.

Two fully powered Allied barracks, p1 disabled then enabled, s5 the normal control.
A presses both native engineer buttons at 2 s, enables p1 at 10 s, presses again
at 14 s. Prediction: disabled p1 spends nothing until enabled; s5 pays 500 and
produces an engineer. The pre-run question was whether a scripted press queues
or bypasses the gate. Counters are p1 money, s5 money, engineer threshold code,
and script logic frame. The count encodes >=1 as 1 and >=2 as 2 (two units = 3),
with s5 multiplied by ten.
B presses once at 2 s, disables p1 at 6 s and enables it at 12 s: predict a
partly paid queue freezes without refund and resumes, while s5 finishes normally.
Scope and evidence: work/re/c_unitban_report.md.
BENCH 11-16: A f150 2000/1603/0, f198 1843/1500/10, f484 1000/1000/33;
B f101 1800/1766/0, f180 1800/1503/0, f195 1753/1500/10, f285 1500/1500/11.
The gate holds queued jobs and retains partial payments. A f322 1466/1129/11
exposes a separate second-job payment clock gap (strict xfail), not a gate fit.
"""
from maps import probe_border
from parts import Mission, Script, Test
from checks import engine_scripts8 as s8

ENGINEER = 'AlliedEngineer'
BUTTON = 'Command_ConstructAlliedEngineer'


def mission():
    m = Mission(name='CampUnitBan', map=probe_border, units=[], facts={})
    m.spawns.add(ENGINEER)
    for side, dx in (('p1', 0.), ('s5', 1800.)):
        for template, role, dy in (('AlliedConstructionYard', 'yard', -800.),
                                   ('AlliedPowerPlant', 'power', -650.),
                                   ('AlliedBarracks', 'barracks', -500.)):
            m.put(template, 'stop row', dx, dy, side=side, angle=3.1416,
                  name=f'CNV UnitBan {side} {role}', role=f'{role} {side}')
    return m


def check(m, which):
    t = Test()
    t.scripts.append(Script('Test - unitban setup', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('PLAYER_SET_MONEY', m.player('p1'), 2000),
        ('PLAYER_SET_MONEY', m.player('s5'), 2000)] + (
        [('PLAYER_DISABLE_UNIT_CONSTRUCTION', m.player('p1'))] if which == 'a' else [])))
    for side, label in (('p1', '甲资金'), ('s5', '乙资金')):
        counter = f'CNV_UnitBan_{side}'
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - unitban money {side}', [], [
            ('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), counter)], once=False))
    s8.total(t, 'CNV_UnitBan_Made', '工程师', [
        (w*n, ('PLAYER_HAS_OBJECT_COMPARISON', m.player(side), 3, n, ENGINEER))
        for side, w in (('p1', 1), ('s5', 10)) for n in (1, 2)])
    s8.frames(t, 'CNV_UnitBan_Clock', '逻辑帧', [])
    for secs in ((2., 14.) if which == 'a' else (2.,)):
        s8.at(t, f'unitban press {secs}', secs, [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', f'CNV UnitBan {side} barracks', BUTTON)
            for side in ('p1', 's5')])
    if which == 'b':
        s8.at(t, 'unitban disable', 6., [
            ('PLAYER_DISABLE_UNIT_CONSTRUCTION', m.player('p1'))])
    s8.at(t, 'unitban enable', 10. if which == 'a' else 12., [
        ('PLAYER_ENABLE_UNIT_CONSTRUCTION', m.player('p1'))])
    t.bench = [('bench_watch', dict(seconds=32., every=1., sheet=False, lines=4))]
    return t


def a(m):
    return check(m, 'a')


def b(m):
    return check(m, 'b')


MISSION = {'engine_unitban': mission}
CHECKS = {'engine_unitban': {'a': a, 'b': b}}
