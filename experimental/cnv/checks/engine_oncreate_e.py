"""E212: ActivateSpecialPowerOnCreate -- retail's one use, JapanAntiVehicleInfantry_Ambush (the tank buster
inheriting the plain one, plus this module firing SpecialPower_ToggleSpiderHole on creation).

Both retail templates as they are, side by side for p1: On the _Ambush one, Off the plain one (the module taken out
is exactly the parent). At GO both press Command_ToggleSpiderHole. Prediction from the data (the toggle's UnpackTime
0, its second state IMMOBILE_ALLOW_ROTATE NO_ATTACK IN_SPIDER_HOLE): On is in the hole from its first frame and the
press takes it out; Off enters at the press. Counters: frame (stops at END), On / Off = 1000 x the status bits at
f15 + 100 x at f45 (IN_SPIDER_HOLE 1, IMMOBILE_ALLOW_ROTATE 2, NO_ATTACK 4) + the frames before IN_SPIDER_HOLE is
first seen (END when never). Predicted On 7000 + 0 + 0..1, Off 0 + 700 + ~GO.
"""
from maps import probe_range
from parts import Mission, Script, Test

GO, END = 30, 60
ARMS = {'On': 'JapanAntiVehicleInfantry_Ambush', 'Off': 'JapanAntiVehicleInfantry'}


def mission():
    m = Mission(name='CampOnCreateE', map=probe_range, units=[])
    for i, (arm, template) in enumerate(ARMS.items()):
        m.put(template, 'base gun', 300.0 * i, 0.0, role=arm, name='E212 ' + arm)
    return m


def check(m):
    t = Test()
    t.counters = [('E212Frame', '完成帧'), ('E212On', '原版'), ('E212Off', '删模块')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E212Frame', 0, END)],
                        [('INCREMENT_COUNTER', 1, 'E212Frame')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for arm in ARMS:
        name, seen, wait = m.role(arm).name, 'E212S' + arm, 'E212W' + arm
        t.scripts += [
            Script('Test - press ' + arm, [('COUNTER', 'E212Frame', 2, GO)],
                   [('NAMED_USE_COMMANDBUTTON_ABILITY', name, 'Command_ToggleSpiderHole')]),
            Script('Test - seen ' + arm, [('UNIT_HAS_OBJECT_STATUS', name, 'IN_SPIDER_HOLE')],
                   [('INCREMENT_COUNTER', 1, seen)]),
            Script('Test - wait ' + arm, [('COUNTER', seen, 2, 0), ('COUNTER', 'E212Frame', 0, END)],
                   [('INCREMENT_COUNTER', 1, wait)], once=False),
            Script('Test - end ' + arm, [('COUNTER', 'E212Frame', 2, END)],
                   [('COUNTER_MATH_COUNTER', 'E212' + arm, 0, wait)])]
        for frame, scale in [(15, 1000), (45, 100)]:
            for value, flag in [(1, 'IN_SPIDER_HOLE'), (2, 'IMMOBILE_ALLOW_ROTATE'), (4, 'NO_ATTACK')]:
                t.scripts.append(Script(f'Test - sample {arm} {frame} {value}',
                    [('COUNTER', 'E212Frame', 2, frame), ('UNIT_HAS_OBJECT_STATUS', name, flag)],
                    [('INCREMENT_COUNTER', value * scale, 'E212' + arm)]))
    t.expect = [('完成帧', 0, 'ever==', END), ('原版', 0, 'ever>=', 7000), ('删模块', 0, 'ever>=', 700)]
    t.bench = [('bench_watch', dict(seconds=END // 15 + 25, every=1, sheet=False, lines=3))]
    return t


MISSION = {'engine_oncreate_e': mission}
CHECKS = {'engine_oncreate_e': {'a': check}}
