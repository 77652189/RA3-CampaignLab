"""C borrowed script action: timed ModelCondition, queried on real objects.

At 2 s set USER_1 for 3 s on short and 7 s on long, with the retail fourth
argument 1.0. Control is untouched; held uses the measured permanent USER_1
action. Predict mask 8 -> 11 -> 10 -> 8 and 45/105 active logic frames.
The four counters are mask, short active frames, long active frames, clock.
No visual/animation inference. Fourth-argument alternatives, repeat/overlap,
zero duration and native producers remain gaps. Evidence: work/re/c_modeldur_report.md.
MEASURED A: f44 11/14/14/44, f75 11/45/45/75, f83 10/46/53/83,
f134 10/46/104/134, f144 8/46/106/144. Inclusive duration boundary.
MEASURED B: f44 11/14/14/44, f54 10/16/24/54, f62 8/16/31/62;
final f284 8/16/31/284. One and two seconds also include the boundary.
"""
from maps import probe_border
from parts import Mission, Script, Test
from checks import engine_scripts8 as s8


def mission():
    m = Mission(name='CampModelDur', map=probe_border, units=[], facts={})
    for k, role in enumerate(('short', 'long', 'control', 'held')):
        m.put('SovietAntiInfantryInfantry', 'stop row', k * 200., -500.,
              name='CNV ModelDur '+role, role=role)
    for k, role in enumerate(('e1', 'e2', 'loner')):            # t: s03's Japanese engineer team + one outside it
        props = {} if role == 'loner' else {'originalOwner': m.crew('E')}
        m.put('JapanEngineer', 'stop row', 800. + k * 200., -500., name='CNV ModelDur '+role, role=role, props=props)
    return m


def check(m, durations=(3., 7.)):
    t = Test()
    t.scripts.append(Script('Test - modeldur setup', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('UNIT_SET_MODELCONDITION', m.role('held').name, 1, 1)]))
    s8.at(t, 'modeldur set', 2., [
        ('UNIT_SET_MODELCONDITION_FOR_DURATION', m.role(role).name, 'USER_1', secs, 1.)
        for role, secs in zip(('short', 'long'), durations)])
    s8.total(t, 'CNV_ModelDur_Mask', '状态', [
        (2**k, ('UNIT_HAS_MODELCONDITION', m.role(role).name, 'USER_1'))
        for k, role in enumerate(('short', 'long', 'control', 'held'))])
    for role, label in (('short', '短帧'), ('long', '长帧')):
        s8.frames(t, 'CNV_ModelDur_'+role, label, [
            ('UNIT_HAS_MODELCONDITION', m.role(role).name, 'USER_1')])
    s8.frames(t, 'CNV_ModelDur_Clock', '逻辑帧', [])
    t.bench = [('bench_watch', dict(seconds=14., every=.5, sheet=False, lines=4))]
    return t


def b(m):
    """Independent 1/2-second duration contrast: predict 16/31 inclusive frames."""
    return check(m, (1., 2.))


def _team(m, condition, fires, seconds):
    """The engineer team's members e1 / e2 and the loner outside it: mask of `condition` (1 / 2 / 4), each member's
    frames with it, the clock; `fires` [(mission seconds, label, action)]."""
    t = Test()
    t.scripts.append(Script('Test - modeldur team setup', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    for secs, label, action in fires:
        s8.at(t, label, secs, [action])
    s8.total(t, 'CNV_ModelDur_Team', '状态', [
        (2**k, ('UNIT_HAS_MODELCONDITION', m.role(role).name, condition))
        for k, role in enumerate(('e1', 'e2', 'loner'))])
    for role in ('e1', 'e2'):
        s8.frames(t, 'CNV_ModelDur_'+role, role+'帧', [('UNIT_HAS_MODELCONDITION', m.role(role).name, condition)])
    s8.frames(t, 'CNV_ModelDur_Clock', '逻辑帧', [])
    t.bench = [('bench_watch', dict(seconds=seconds, every=.5, sheet=False, lines=4))]
    return t


def t(m):
    """TEAM_SET_MODELCONDITION_FOR_DURATION as s03 calls it (EMOTION_CELEBRATING, 10 s, 1.0) on the team at 2 s:
    predict both members (mask 3, never the loner's 4) for 151 inclusive frames, as the unit action."""
    return _team(m, 'EMOTION_CELEBRATING', [(2., 'modeldur team set', (
        'TEAM_SET_MODELCONDITION_FOR_DURATION', m.crew('E'), 'EMOTION_CELEBRATING', 10., 1.))], 16.)


def u(m):
    """TEAM_SET_MODELCONDITION as a08 calls it (USER_2 on, later off) on the team at 2 s, off at 8 s: predict mask 3
    (never the loner's 4) from the 2 s frame to the 8 s one."""
    return _team(m, 'USER_2', [(2., 'modeldur team on', ('TEAM_SET_MODELCONDITION', m.crew('E'), 2, 1)),
                               (8., 'modeldur team off', ('TEAM_SET_MODELCONDITION', m.crew('E'), 2, 0))], 12.)


MISSION = {'engine_modeldur': mission}
CHECKS = {'engine_modeldur': {'a': check, 'b': b, 't': t, 'u': u}}
