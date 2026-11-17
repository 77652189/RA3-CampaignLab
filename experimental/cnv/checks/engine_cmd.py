"""Engine line D round 60 (handoff-d ④ "connection"): a program outside the game gives the running game an order, the
game carries it out. The write path: ra3ext's CNVCmd module (carrier `<DeletionUpdate id="ModuleTag_CNVCmd"/>` on a
copy of the conscript) looks every frame for ra3ext_cmd.txt in the run folder, sets the map's script counter named in
it and deletes the file. The map's own script does the rest: Cmd_Call >= 1 -> three GIs at 'Test Drop', Cmd_Done + 1,
Cmd_Call back to 0. The sender is experimental/cnv/ext_send.py, started BEFORE the check (it waits for the run's
'cmd: listening' line, then for DELAY seconds, then writes `set Cmd_Call 1`):

  python -I -X utf8 experimental/cnv/ext_send.py --after 8 "set /Cmd_Call 1"    (background; "Cmd_Call" is the same key)
  cnv_check engine_cmd a

Counter names have a scope: a bare name in a map script is its script list owner's (here 'Player_1'), the outside's
bare name is the empty scope. So the map names the shared ones '/Cmd_Call', '/Cmd_Done' (the empty scope), and the
outside reads the map's own bare 'Cmd_Time' as 'Player_1/Cmd_Time' (case matters: 'player_1/...' is another counter).

Counters: 援军 (GIs the player owns), 命令 (/Cmd_Call), 已执行 (/Cmd_Done), 秒 (Cmd_Time, the map's clock). The control
is the start: no GI before the order; without the sender none ever comes.
Bench 2026-11-11 CampCmdA_mcp_1111_220230 PASS: sent at s20 (frame 331), 命令 1 at s20, 援军 3 / 已执行 1 from s21;
`get Player_1/Cmd_Time` = 22 = the counter's 秒 at s20; the file was taken 0.10 s after it appeared.
"""
import os

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted

CONSCRIPT, HOST, GI, CALLS = 'SovietAntiInfantryInfantry', 'CNVCmdHost', 'AlliedAntiInfantryInfantry', 3
RUN = 40.0


def host_unit():
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Units', CONSCRIPT + '.xml'), encoding='utf-8').read()
    assert x.count(f'id="{CONSCRIPT}"') == 1 and x.count('<Behaviors>') == 1
    x = x.replace(f'id="{CONSCRIPT}"', f'id="{HOST}"').replace(f'EditorName="{CONSCRIPT}"', f'EditorName="{HOST}"')
    x = x.replace('<Behaviors>', '''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVCmd" MinFrames="1" MaxFrames="1"/>''')
    return Unit(HOST, x, names=dict(unit=HOST),
                what='动员兵的复制：多一个 ra3ext 的 CNVCmd 模块（每帧看命令文件、写地图计数器）',
                params=dict(of=CONSCRIPT))


def mission():
    m = Mission(name='CampCmd', map=probe_range, units=[host_unit()], facts={}, ext=True)
    m.put(HOST, 'base gun', 0.0, -120.0, side='p1', role='cmd host')
    m.put(GI, 'probe refinery', 0.0, 0.0, side='s1', role='gi model')   # publishes GI; s1's, far: not counted
    return m


def cmd_test(m):
    t = Test()
    team = m.team('p1')
    t.waypoints['Test Drop'] = m.site('base gun', 0.0, 120.0)
    t.scripts += [
        Script('Test - clock start', [], [('SET_MILLISECOND_TIMER', 'Test Tick', 1.0)]),
        Script('Test - clock', [('TIMER_EXPIRED', 'Test Tick')],
               [('INCREMENT_COUNTER', 1, 'Cmd_Time'), ('SET_MILLISECOND_TIMER', 'Test Tick', 1.0)], once=False),
        Script('Test - call', [('COUNTER', '/Cmd_Call', 3, 1)],
               [('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', GI, team, 'Test Drop')] * CALLS +
               [('INCREMENT_COUNTER', 1, '/Cmd_Done'), ('SET_COUNTER', '/Cmd_Call', 0)], once=False)]
    counted('CNV_Cmd_GI', '援军', t, template=GI)
    t.counters += [('/Cmd_Call', '命令'), ('/Cmd_Done', '已执行'), ('Cmd_Time', '秒')]
    t.expect = [('援军', 1, '==', 0, 5.0), ('已执行', 1, '==', 0, 5.0),
                ('援军', 5, 'ever==', CALLS, RUN), ('已执行', 5, 'ever==', 1, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_cmd': mission}
CHECKS = {'engine_cmd': {'a': cmd_test}}
