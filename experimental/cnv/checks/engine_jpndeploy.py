"""Japan MCV waypoint command; evidence: work/re/c_jpndeploy_report.md.

Prediction from the SDK ReplaceSelf ability and existing order_unpack:
two ordered MCVs drive 400 east to separate clear pads and become yards;
the untouched MCV stays home. Names survive replacement. At 24 seconds
yard-at-goal / living-name / MCV-at-home masks should be 3/7/4.
Only ordinary living hosts and clear ground; arrival/unfold timing,
obstructed pads, damage transfer and repeated orders remain gaps.
"""
from maps import probe_border
from parts import Mission, Test, square
from checks import engine_scripts8 as s8

ROLES = ('first', 'second', 'control')
BUTTON = 'Command_UnPackJapanMCV'


def mission():
    m = Mission(name='CampJpnDeploy', map=probe_border, units=[], facts={})
    m.spawns.add('JapanConstructionYard')
    for k, role in enumerate(ROLES):
        m.put('JapanMCV', 'stop row', 0., -3100.+900.*k,
              role=role, name='CNV JpnDeploy '+role)
        m.waypoint(role, 'Test JpnDeploy '+role, 'stop row', 400., -3100.+900.*k)
    return m


def check(m):
    t = Test()
    for role in ROLES:
        x, y = m.point(role)
        t.areas['Test JpnHome '+role] = square(x-400., y, 100.)
        t.areas['Test JpnGoal '+role] = square(*m.point(role), 100.)
    s8.at(t, 'deploy', 5., [
        ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', m.role(role).name,
         BUTTON, m.mark(role)) for role in ROLES[:2]])
    s8.total(t, 'CNV_JD_Yard', '场位', [
        (2**k, ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player(), 3, 1,
                'JapanConstructionYard', 'Test JpnGoal '+role)) for k, role in enumerate(ROLES)])
    s8.total(t, 'CNV_JD_Name', '名字位', [
        (2**k, ('NAMED_NOT_DESTROYED', m.role(role).name)) for k, role in enumerate(ROLES)])
    s8.total(t, 'CNV_JD_Home', '原车位', [
        (2**k, ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player(), 3, 1,
                'JapanMCV', 'Test JpnHome '+role)) for k, role in enumerate(ROLES)])
    s8.frames(t, 'CNV_JD_Frame', '逻辑帧', [])
    s8.watch(t, 28., .5)
    return t


MISSION = {'engine_jpndeploy': mission}
CHECKS = {'engine_jpndeploy': {'a': check}}
