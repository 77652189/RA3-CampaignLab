"""TEAM_UPGRADE on two living members, same-owner and other-owner negatives.

Retail j05 uses map-local upgrade_j05_easy/med; their consumers are not
published by the SDK. This dispatch slice uses the retail OBJECT upgrade
Upgrade_Veterancy_HEROIC with its real Guardian status-bit consumer instead.
Predict at 10 s: both Given members have WEAPON_UPGRADED_02 (mask 3),
same-owner Other and enemy Other have none (mask 0), player holds >=2
but not >=3 upgraded units (query mask 3). At 16 s remove one member's
upgrade: masks 2/0/1. Re-grant the team at 22 s: masks 3/0/3.
Fourth counter is logic frame. Evidence: work/re/c_teamup_report.md.
MEASURED A: f150 0/0/0/150; f157 3/0/3/157; f248 2/0/1/248;
f323 2/0/1/323; f332 3/0/3/332; f453 3/0/3/453.
Map-local j05 effects, future members, dead/absent teams remain gaps.
"""
from maps import probe_border
from parts import Mission, Script, Test, status
from checks import engine_scripts8 as s8

UPGRADE = 'Upgrade_Veterancy_HEROIC'
ROLES = ('first', 'second', 'other', 'enemy')


def mission():
    m = Mission(name='CampTeamUp', map=probe_border, units=[], facts={})
    for k, role in enumerate(ROLES):
        side = 's4' if role == 'enemy' else 'p1'
        crew = 'Given' if k < 2 else 'Other'+role
        m.put('AlliedAntiVehicleVehicleTech1', 'stop row', 0., -1800.+k*400.,
              side=side, name='CNV TeamUp '+role, role=role,
              props={'originalOwner': m.crew(crew, side=side)})
    return m


def check(m):
    t = Test()
    t.scripts.append(Script('Test TeamUp hold', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 1) for r in ROLES]))
    s8.at(t, 'teamup grant', 10., [('TEAM_UPGRADE', m.teams['Given'], UPGRADE)])
    s8.at(t, 'teamup remove', 16., [('NAMED_REMOVE_UPGRADE', UPGRADE, m.role('first').name)])
    s8.at(t, 'teamup again', 22., [('TEAM_UPGRADE', m.teams['Given'], UPGRADE)])
    for key, label, roles in [('Given', '本队位', ROLES[:2]), ('Other', '异队位', ROLES[2:])]:
        s8.total(t, 'CNV_TeamUp_'+key, label, [
            (2**k, ('UNIT_HAS_OBJECT_STATUS', m.role(r).name, status('WEAPON_UPGRADED_02')))
            for k, r in enumerate(roles)])
    s8.total(t, 'CNV_TeamUp_Query', '升级查询', [
        (2**k, ('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', m.player(), n, UPGRADE))
        for k, n in enumerate((1, 2, 3))])
    s8.frames(t, 'CNV_TeamUp_Clock', '逻辑帧', [])
    s8.watch(t, 28., .5)
    return t


MISSION = {'engine_teamup': mission}
CHECKS = {'engine_teamup': {'a': check}}
