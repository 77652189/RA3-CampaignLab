"""Stop a unit's sequential queue during a move, with an untouched control.

Predict: both start at 1; stop removes +10 and the separately queued +100,
but the current move still reaches the destination (mask 3). At 20 seconds
a new +1000 script on the stopped unit distinguishes clearing from disabling.
Read counters plus logic frame; evidence: work/re/c_seqstop_report.md.
MEASURED A: f43 1/1/0/43; f242 both at destination (mask 3);
f282 111/1/3/282; f308 111/1001/3/308; f360 111/1001/3/360.
Only the script queue boundary is measured; exact movement/idle timing,
self-stop, loops, dead/missing units and non-move orders remain gaps.
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


MISSION = {'engine_seqstop': mission}
CHECKS = {'engine_seqstop': {'a': check}}
