"""TEAM_SET_HEALTH current-member percentage contrast.

Prediction: at 4s Given Guardian and Conscript become 25 percent; at 8s
both become 75 percent. Same-player other crew and another player's
Guardian stay 100 percent. Variant b reverses 75/25. Actual named HP
counters, controls packed as other + 1000*enemy, and logical frame.
Future/dead/absent members, AI team instances, out-of-range values and
exact dispatch phase remain gaps. Evidence: work/re/c_teamhp_report.md.
MEASURED: a f44..59=100/100, f68..120=25/25, f128..241=75/75;
b f45..59=100/100, f66..120=75/75, f127..241=25/25.
All 54 displayed samples have control HP code 100100.
"""
from maps import probe_border
from parts import Mission, Script, Test
from checks import engine_scripts8 as s8

ROLES = ('first', 'second', 'other', 'enemy')


def mission():
    m = Mission(name='CampTeamHP', map=probe_border, units=[], facts={})
    for k, role in enumerate(ROLES):
        side = 's4' if role == 'enemy' else 'p1'
        crew = 'Given' if k < 2 else 'Other'+role
        template = 'SovietAntiInfantryInfantry' if k == 1 else 'AlliedAntiVehicleVehicleTech1'
        m.put(template, 'stop row', 0., -1800.+k*500., side=side,
              name='CNV TeamHP '+role, role=role,
              props={'originalOwner': m.crew(crew, side=side)})
    return m


def check(m, which):
    t = Test()
    t.scripts.append(Script('Test TeamHP hold', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 1) for r in ROLES]))
    values = (25., 75.) if which == 'a' else (75., 25.)
    for secs, value in zip((4., 8.), values):
        s8.at(t, 'teamhp '+str(secs), secs, [('TEAM_SET_HEALTH', m.teams['Given'], value)])
    for role, label in zip(ROLES[:2], ('甲血量', '乙血量')):
        c = 'CNV_TH_'+role
        t.counters.append((c, label))
        t.scripts.append(Script('Test HP '+role, [], [
            ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role(role).name, c)], once=False))
    c, tmp = 'CNV_TH_Control', 'CNV_TH_Enemy'
    t.counters.append((c, '对照血量码'))
    t.scripts.append(Script('Test HP controls', [], [
        ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role('other').name, c),
        ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role('enemy').name, tmp),
        ('COUNTER_MATH_VALUE', tmp, 2, 1000),
        ('COUNTER_MATH_COUNTER', c, 0, tmp)], once=False))
    s8.frames(t, 'CNV_TH_Frame', '逻辑帧', [])
    t.expect = [('甲血量', 0., 'ever==', 100, 3.),
                ('乙血量', 0., 'ever==', 100, 3.),
                ('甲血量', 6., 'ever==', int(values[0]), 8.),
                ('乙血量', 6., 'ever==', int(values[0]), 8.),
                ('甲血量', 10., '==', int(values[1])),
                ('乙血量', 10., '==', int(values[1])),
                ('对照血量码', 0., '==', 100100)]
    s8.watch(t, 13., .5)
    return t


MISSION = {'engine_teamhp': mission}
CHECKS = {'engine_teamhp': {w: (lambda m, w=w: check(m, w)) for w in 'ab'}}
