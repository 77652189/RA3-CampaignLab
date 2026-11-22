"""Stop a unit's sequential queue during a move, with an untouched control.

Predict: both start at 1; stop removes +10 and the separately queued +100,
but the current move still reaches the destination (mask 3). At 20 seconds
a new +1000 script on the stopped unit distinguishes clearing from disabling.
Read counters plus logic frame; evidence: work/re/c_seqstop_report.md.
MEASURED A: f43 1/1/0/43; f242 both at destination (mask 3);
f282 111/1/3/282; f308 111/1001/3/308; f360 111/1001/3/360.
Only the script queue boundary is measured; exact movement/idle timing,
self-stop, loops, dead/missing units and non-move orders remain gaps.

engine_seqteam:t -- TEAM_EXECUTE / TEAM_STOP_SEQUENTIAL_SCRIPT (d115 14, A288 read of the handlers: the record on the
team, a group of its members made at the call; a step waits till the group is idle). Three two-tank crews, at 1 s:
  W: [+1, MOVE_NAMED_UNIT_TO(w1, WF 600 east), +10, ATTACK_MOVE_TEAM_TO(<This Team>, W2), +100], then [+1000] queued.
  S: [+1, MOVE_NAMED_UNIT_TO(s1, SF 600 east), +10] and [+100] queued; TEAM_STOP_SEQUENTIAL_SCRIPT(S) at 2 s, [+1000]
     given at 20 s.  L: [+1, MOVE_NAMED_UNIT_TO(l1, LF 900 east), +10]; NAMED_KILL(l1) at 3 s.
  走 / 停 = W's / S's counters; 位 = 1 w1 in WF, 2 w1 in W2, 4 w2 in W2, 8 s1 in SF, 16 / 32 L's counter >= 1 / 11.
  [simulator, the group idle = every living member idle: 走 1 -> 11 once w1 is at WF (~7 s; not at once, w2 being
  idle) -> 111, 1111 once both are at W2 (~16 s); 位 1 -> 6; 停 1 -> 1001 at 20 s, s1 still at SF (8); L 1 -> 11 at
  the kill (the dead member out of the group: 位 16 -> 48)]
"""
from maps import probe_border
from parts import Mission, Script, Test, square
from checks import engine_scripts8 as s8


def mission():
    m = Mission(name='CampSeqStop', map=probe_border, units=[], facts={})
    for k, role in enumerate(('control', 'stopped')):
        m.put('AlliedAntiVehicleVehicleTech1', 'stop row', 0., -1000. - k*400.,
              name='CNV SeqStop '+role, role=role, angle=0.)
        m.waypoint(role, 'CNV SeqStop Goal '+role, 'stop row', 1300., -1000. - k*400.)
    return m


def check(m):
    t = Test()
    s8.at(t, 'seqstop start', 1., [
        (action, m.role(role).name, script)
        for role in ('control', 'stopped')
        for action, script in [('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', 'Test SeqStop '+role),
                               ('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', 'Test SeqStop Queue '+role)]])
    for role, label in (('control', '继续'), ('stopped', '停止')):
        c = 'CNV_SeqStop_'+role
        t.counters.append((c, label))
        t.scripts += [Script('Test SeqStop '+role, [], [
            ('INCREMENT_COUNTER', 1, c),
            ('MOVE_NAMED_UNIT_TO', '<This Object>', m.mark(role)),
            ('INCREMENT_COUNTER', 10, c)], sub=True),
            Script('Test SeqStop Queue '+role, [], [('INCREMENT_COUNTER', 100, c)], sub=True)]
        t.areas['SeqStop '+role] = square(*m.point(role), 100.)
    s8.at(t, 'seqstop stop', 2., [('UNIT_STOP_SEQUENTIAL_SCRIPT', m.role('stopped').name)])
    t.scripts.append(Script('Test SeqStop Fresh', [], [
        ('INCREMENT_COUNTER', 1000, 'CNV_SeqStop_stopped')], sub=True))
    s8.at(t, 'seqstop fresh', 20., [('UNIT_EXECUTE_SEQUENTIAL_SCRIPT', m.role('stopped').name,
                                   'Test SeqStop Fresh')])
    s8.total(t, 'CNV_SeqStop_Where', '到达', [
        (2**k, ('NAMED_INSIDE_AREA', m.role(role).name, 'SeqStop '+role))
        for k, role in enumerate(('control', 'stopped'))])
    s8.frames(t, 'CNV_SeqStop_Clock', '逻辑帧', [])
    s8.watch(t, 27., .5)
    return t


TEAM = {k: ((600., y), (600., y + 120.), x) for k, y, x in (('W', 4100., 1200.), ('S', 4400., 1200.),
                                                            ('L', 4700., 1500.))}
W2 = (1500., 4160.)


def team_mission():
    m = Mission(name='CampSeqTeam', map=probe_border, units=[], facts={})
    o = probe_border.SITES['stop row']
    for k, (a, b, fx) in TEAM.items():
        for i, (x, y) in enumerate((a, b), 1):
            m.put('AlliedAntiVehicleVehicleTech1', 'stop row', x - o.x, y - o.y, name=f'CNV SeqTeam {k}{i}',
                  role=f'{k}{i}', angle=0., props={'originalOwner': m.crew(k)})
        m.waypoint(k, f'CNV SeqTeam {k} Goal', 'stop row', fx - o.x, a[1] - o.y)
    m.waypoint('W2', 'CNV SeqTeam W2', 'stop row', W2[0] - o.x, W2[1] - o.y)
    return m


def team(m):
    t = Test()
    c = {k: 'CNV_SeqTeam_' + k for k in TEAM}
    go = {k: [('INCREMENT_COUNTER', 1, c[k]), ('MOVE_NAMED_UNIT_TO', m.role(k + '1').name, m.mark(k)),
              ('INCREMENT_COUNTER', 10, c[k])] for k in TEAM}
    go['W'] += [('ATTACK_MOVE_TEAM_TO', '<This Team>', m.mark('W2')), ('INCREMENT_COUNTER', 100, c['W'])]
    later = {'W': 1000, 'S': 100}
    t.scripts += [Script(f'Test SeqTeam {k}', [], acts, sub=True) for k, acts in go.items()]
    t.scripts += [Script(f'Test SeqTeam {k} Q', [], [('INCREMENT_COUNTER', n, c[k])], sub=True)
                  for k, n in later.items()]
    t.scripts.append(Script('Test SeqTeam Fresh', [], [('INCREMENT_COUNTER', 1000, c['S'])], sub=True))
    s8.at(t, 'seqteam go', 1., [('TEAM_EXECUTE_SEQUENTIAL_SCRIPT', m.crew(k), f'Test SeqTeam {k}') for k in TEAM] +
          [('TEAM_EXECUTE_SEQUENTIAL_SCRIPT', m.crew(k), f'Test SeqTeam {k} Q') for k in later])
    s8.at(t, 'seqteam stop', 2., [('TEAM_STOP_SEQUENTIAL_SCRIPT', m.crew('S'))])
    s8.at(t, 'seqteam kill', 3., [('NAMED_KILL', m.role('L1').name)])
    s8.at(t, 'seqteam fresh', 20., [('TEAM_EXECUTE_SEQUENTIAL_SCRIPT', m.crew('S'), 'Test SeqTeam Fresh')])
    t.counters += [(c['W'], '走'), (c['S'], '停')]
    for k, r in (('W', 80.), ('W2', 150.), ('S', 80.)):
        t.areas['SeqTeam ' + k] = square(*m.point(k), r)
    s8.total(t, 'CNV_SeqTeam_Where', '位', [
        (1, ('NAMED_INSIDE_AREA', m.role('W1').name, 'SeqTeam W')),
        (2, ('NAMED_INSIDE_AREA', m.role('W1').name, 'SeqTeam W2')),
        (4, ('NAMED_INSIDE_AREA', m.role('W2').name, 'SeqTeam W2')),
        (8, ('NAMED_INSIDE_AREA', m.role('S1').name, 'SeqTeam S')),
        (16, ('COUNTER', c['L'], 3, 1)), (32, ('COUNTER', c['L'], 3, 11))])
    s8.frames(t, 'CNV_SeqTeam_Clock', '逻辑帧', [])
    s8.watch(t, 24.)
    return t


MISSION = {'engine_seqstop': mission, 'engine_seqteam': team_mission}
CHECKS = {'engine_seqstop': {'a': check}, 'engine_seqteam': {'t': team}}
