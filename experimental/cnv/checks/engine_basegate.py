"""A line: PLAYER_DISABLE_BASE_CONSTRUCTION / PLAYER_ENABLE_BASE_CONSTRUCTION on a real structure queue.

C's engine_baseban measured the gate against JapanPowerPlantEgg, a UNIT_BUILD core, and saw no gate.
Here the Allied yard's CONSTRUCTION_YARD_CONSTRUCT button (Command_ConstructAlliedPowerPlant, 800,
10 s) is pressed by script on both sides; each side also has a powered barracks (engineer, 500).
a: p1 base-disabled from the start, both yards press at 2 s, p1 enabled at 10 s.
   Prediction: s5 pays 800 over the build; p1 holds 2000 until 10 s, then pays (as the unit gate does).
(A crossed-category variant was planned and dropped unrun: the press itself queues nothing.)
Counters: p1 money, s5 money, made code, script logic frame. Made code: p1 plants >= 2 adds 1,
s5 plants >= 2 adds 10, p1 engineer adds 100, s5 engineer adds 1000 (a finished structure waits
unplaced, so the plant digits only say whether a press placed one by itself).
BENCH 11-16 (A269): a 2000/2000/0 from f44 to f377 on BOTH sides -- a script's press of the yard's
CONSTRUCTION_YARD_CONSTRUCT button queues nothing, so this map reads no gate.
aibgate:a: 50000 / 1 structure from the wake (f163) to f1054; paying from f1054, 2 at f1208 --
the base-disabled AI orders nothing till the 70 s enable, then starts as at a wake.
"""
from maps import probe_border
from parts import Mission, Script, Test
from checks import engine_scripts8 as s8
from checks import engine_aiskirm as ak

PLANT, ENGINEER = 'AlliedPowerPlant', 'AlliedEngineer'
PLANT_BUTTON = 'Command_ConstructAlliedPowerPlant'


def mission():
    m = Mission(name='CampBaseGate', map=probe_border, units=[], facts={})
    m.spawns |= {PLANT, ENGINEER}
    for side, dx in (('p1', 0.), ('s5', 1800.)):
        for template, role, dy in (('AlliedConstructionYard', 'yard', -800.),
                                   ('AlliedPowerPlant', 'power', -650.),
                                   ('AlliedBarracks', 'barracks', -500.)):
            m.put(template, 'stop row', dx, dy, side=side, angle=3.1416,
                  name=f'CNV BaseGate {side} {role}', role=f'{role} {side}')
    return m


def a(m):
    t = Test()
    t.scripts.append(Script('Test - basegate setup', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('PLAYER_SET_MONEY', m.player('p1'), 2000),
        ('PLAYER_SET_MONEY', m.player('s5'), 2000),
        ('PLAYER_DISABLE_BASE_CONSTRUCTION', m.player('p1'))]))
    for side, label in (('p1', '甲资金'), ('s5', '乙资金')):
        counter = f'CNV_BaseGate_{side}'
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - basegate money {side}', [], [
            ('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), counter)], once=False))
    s8.total(t, 'CNV_BaseGate_Made', '造出', [
        (w, ('PLAYER_HAS_OBJECT_COMPARISON', m.player(side), 3, n, template))
        for side, template, n, w in (('p1', PLANT, 2, 1), ('s5', PLANT, 2, 10),
                                     ('p1', ENGINEER, 1, 100), ('s5', ENGINEER, 1, 1000))])
    s8.frames(t, 'CNV_BaseGate_Clock', '逻辑帧', [])
    s8.at(t, 'basegate enable', 10., [('PLAYER_ENABLE_BASE_CONSTRUCTION', m.player('p1'))])
    s8.at(t, 'basegate press', 2., [('NAMED_USE_COMMANDBUTTON_ABILITY', f'CNV BaseGate {side} yard', PLANT_BUTTON)
                                    for side in ('p1', 's5')])
    t.bench = [('bench_watch', dict(seconds=32., every=1., sheet=False, lines=4))]
    return t


def ai(m):
    """aibgate (B's aiskirm mission, s1 AlliedBalanced woken at 10 s with 50000): s1 base-disabled from frame 0,
    enabled at 70 s. Control: aiskirm d (bench 11-07) has 建筑数 2 at 11 s after the wake, 3 at 21, money falling.
    Prediction: 建筑数 stays 1 and money 50000 until 70 s, then the AI starts building."""
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - aibgate setup', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')), ('PLAYER_DISABLE_BASE_CONSTRUCTION', s1)]))
    t.counters.append(('CNV_AIBGate_Money', 'AI钱'))
    t.scripts.append(Script('Test - aibgate money', [], [
        ('SET_PLAYER_MONEY_TO_COUNTER', s1, 'CNV_AIBGate_Money')], once=False))
    ak._sum(t, m, s1, 'CNV_AIBGate_Built', '建筑数', ak.BUILDINGS + ak.TOWERS)
    ak._sum(t, m, s1, 'CNV_AIBGate_Army', '兵数', ak.ARMY)
    s8.frames(t, 'CNV_AIBGate_Clock', '逻辑帧', [])
    s8.at(t, 'aibgate enable', 70., [('PLAYER_ENABLE_BASE_CONSTRUCTION', s1)])
    t.bench = [('bench_watch', dict(seconds=105., every=1., sheet=False, lines=4))]
    return t


MISSION = {'engine_basegate': mission}
CHECKS = {'engine_basegate': {'a': a}, 'aibgate': {'a': ai}}
