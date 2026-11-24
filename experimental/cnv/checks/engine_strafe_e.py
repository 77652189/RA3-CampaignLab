"""E224: StrafeAreaUpdate on a placed SovietSupportBomber_S07 -- does it bomb what it flies over?

Retail: SovietSupportBomber_S07 (a01 / a05 / j01 / s01 / s07 place it on the map and move it by script) carries a
StrafeAreaUpdate with SovietDesolatorBombWeapon (Radius 300). From the program (work/re a353_strafe.md): the module
starts in state 0, which its update skips; only its set-target call moves it on, and only the StrafeAreaSquad OCL nugget
and an OCL CreateObject nugget call that -- nothing a script does.
Prediction: a placed S07 sent by script over two enemy tanks (s1, NO_ATTACK, on its path) bombs nothing: both stay at
100 % while it passes over them, there and back. Counters: the two tanks' health, 1 while the bomber is over the far one.
"""
from maps import probe_range
from parts import Mission, Script, Test, counted, square

BOMBER, TANK = 'SovietSupportBomber_S07', 'AlliedAntiVehicleVehicleTech1'
GO, BACK, END = 30, 30 + 15 * 15, 30 + 15 * 32


def mission():
    m = Mission(name='CampStrafeE', map=probe_range, units=[])
    m.put(BOMBER, 'pace start', role='bomber', name='E224 Bomber', angle=0.0)
    for k in (1, 2):
        m.put(TANK, f'pace leg {k}', role=f'tank {k}', side='s1', name=f'E224 Tank {k}', angle=3.14159)
    m.waypoint('start', 'E224 Start', 'pace start')
    m.waypoint('goal', 'E224 Goal', 'pace goal', 300, 0)
    return m


def check(m):
    t = Test()
    bomber, over = m.role('bomber').name, 'E224 Over'
    t.areas[over] = square(*m.site('pace leg 2'), 100)
    counted('E224Near', '血近', t, health=m.role('tank 1').name)
    counted('E224Far', '血远', t, health=m.role('tank 2').name)
    counted('E224Over', '头顶', t, named=bomber, area=over)
    t.scripts += [Script('Test - clock', [('COUNTER', 'E224Frame', 0, END)],
                         [('INCREMENT_COUNTER', 1, 'E224Frame')], once=False),
                  Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] +
                         [('UNIT_CHANGE_OBJECT_STATUS', m.role(f'tank {k}').name, 'NO_ATTACK', 1) for k in (1, 2)]),
                  Script('Test - go', [('COUNTER', 'E224Frame', 2, GO)],
                         [('MOVE_NAMED_UNIT_TO', bomber, m.mark('goal'))]),
                  Script('Test - back', [('COUNTER', 'E224Frame', 2, BACK)],
                         [('MOVE_NAMED_UNIT_TO', bomber, m.mark('start'))])]
    t.expect = [('头顶', 0, 'ever>', 0)]
    t.bench = [('bench_camera', dict(x=1250, y=1200, look=False)),
               ('bench_watch', dict(seconds=END // 15 + 5, every=1, sheet=False, lines=3))]
    return t


MISSION = {'engine_strafe_e': mission}
CHECKS = {'engine_strafe_e': {'a': check}}
