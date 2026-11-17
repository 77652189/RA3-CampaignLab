"""C line: PLAYER_DISABLE_BASE_CONSTRUCTION(player), native production control.

JapanConstructionYard's UNIT_BUILD Command_ConstructJapanPowerPlantEgg builds an 800-cost
JapanPowerPlantEgg (retail BuildTime 0). No placement or artificial spawning is used.
A disables p1; B disables s5. The human p1 clicks the first structure button; s5 receives
the same native command by NAMED_USE_COMMANDBUTTON_ABILITY at 2 seconds.
Prediction: p1's disabled native click spends nothing and makes no core; the normal click
spends 800 and makes one core. Whether the scripted press bypasses this gate is unmeasured.
Counters: human money, s5 money, human cores + 10*s5 cores, script logic frame.
Evidence and scope: work/re/c_baseban_report.md. Other factions/AI queues remain unmeasured.
BENCH 11-16: A at f74 2000/1426/0, final f488 1200/1200/11;
B at f75 2000/1413/0, final f364 1200/1200/11. Disabling either player
does not block these UNIT_BUILD core orders. The base-construction consumer remains a gap;
do not infer a no-op action or promote it from this control. Payment timing is strict xfail.
"""
from maps import probe_border
from parts import Mission, Script, Test
from checks import engine_scripts8 as s8

CORE = 'JapanPowerPlantEgg'
BUTTON = 'Command_ConstructJapanPowerPlantEgg'


def mission():
    m = Mission(name='CampBaseBan', map=probe_border, units=[], facts={})
    m.spawns.add(CORE)
    for side, dx in (('p1', 0.), ('s5', 1800.)):
        m.put('JapanConstructionYard', 'stop row', dx, -500., side=side,
              name=f'CNV BaseBan {side}', role=f'yard {side}')
    return m


def check(m, disabled):
    t = Test()
    t.scripts.append(Script('Test - baseban setup', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('PLAYER_SET_MONEY', m.player('p1'), 2000),
        ('PLAYER_SET_MONEY', m.player('s5'), 2000),
        ('PLAYER_DISABLE_BASE_CONSTRUCTION', m.player(disabled))]))
    for side, label in (('p1', '甲资金'), ('s5', '乙资金')):
        counter = f'CNV_BaseBan_{side}'
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - baseban money {side}', [], [
            ('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), counter)], once=False))
    s8.total(t, 'CNV_BaseBan_Cores', '核心', [
        (w, ('PLAYER_HAS_OBJECT_COMPARISON', m.player(side), 3, 1, CORE))
        for side, w in (('p1', 1), ('s5', 10))])
    s8.frames(t, 'CNV_BaseBan_Clock', '逻辑帧', [])
    s8.at(t, 'baseban press', 2., [
        ('NAMED_USE_COMMANDBUTTON_ABILITY', 'CNV BaseBan s5', BUTTON)])
    watch = dict(every=1., sheet=False, lines=4)
    t.bench = [('bench_watch', dict(watch, seconds=2.)),
               ('bench_click', dict(x=1120, y=252, world=False, look=False)),
               ('bench_click', dict(x=1120, y=252, world=False, look=False)),
               ('bench_click', dict(x=1137, y=323, world=False, look=False)),
               ('bench_watch', dict(watch, seconds=18.))]
    return t


def a(m):
    return check(m, 'p1')


def b(m):
    return check(m, 's5')


MISSION = {'engine_baseban': mission}
CHECKS = {'engine_baseban': {'a': a, 'b': b}}
