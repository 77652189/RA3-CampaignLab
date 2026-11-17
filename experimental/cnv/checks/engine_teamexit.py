"""TEAM_EXIT_ALL_BUILDINGS mixed-team building/transport contrast.

Before bench prediction: at 5s Target's house and Bullfrog passengers exit,
Other's passengers sharing both containers stay enclosed. An outside Target
member stays alive. Empty crew at 3s and repeated exit at 9s are harmless.
Four counters: Target enclosed mask (house=1, frog=2, outside=4), Other
enclosed mask (house=1, frog=2), alive mask (five men then two hosts), frame.
MEASURED A: f44..74 3/3/127/frame; f82..287 0/3/127/frame (33 samples).
Evidence and unmeasured boundaries: work/re/c_teamexit_report.md.
"""
from maps import probe_border
from parts import Mission, Script, Test, status
from checks import engine_scripts8 as s8

MAN = 'SovietAntiInfantryInfantry'
ROLES = ('target house', 'target frog', 'target outside', 'other house', 'other frog')


def mission():
    m = Mission(name='CampTeamExit', map=probe_border, units=[], facts={})
    crews = {c: m.crew(c) for c in ('Target', 'Other', 'Empty')}
    for role, template, dx, side in (
            ('house', 'AM_Apartments_01', 0., 'civ'),
            ('frog', 'SovietAntiAirShip', 1800., 'p1')):
        m.put(template, 'stop row', -300.+dx, -1800., side=side,
              role=role, name='CNV TeamExit '+role)
    for k, role in enumerate(ROLES):
        crew = crews['Target' if role.startswith('target') else 'Other']
        m.put(MAN, 'stop row', -500.+k*300., -2100., role=role,
              name='CNV TeamExit '+role, props={'originalOwner': crew})
    return m


def check(m):
    t = Test()
    t.scripts.append(Script('Test - TeamExit hold', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, status('NO_ATTACK'), 1)
        for r in (*ROLES, 'house', 'frog')]))
    s8.at(t, 'load', 1., [
        ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', m.role(r).name,
         m.role(r.split()[1]).name) for r in ROLES if not r.endswith('outside')])
    s8.at(t, 'empty exit', 3., [('TEAM_EXIT_ALL_BUILDINGS', m.teams['Empty'])])
    s8.at(t, 'target exit', 5., [('TEAM_EXIT_ALL_BUILDINGS', m.teams['Target'])])
    s8.at(t, 'repeat exit', 9., [('TEAM_EXIT_ALL_BUILDINGS', m.teams['Target'])])
    for prefix, label in (('target', '本队驻'), ('other', '异队驻')):
        roles = [r for r in ROLES if r.startswith(prefix)]
        s8.total(t, 'CNV_TE_'+prefix, label, [
            (2**k, ('UNIT_HAS_OBJECT_STATUS', m.role(r).name, status('ENCLOSED')))
            for k, r in enumerate(roles)])
    s8.total(t, 'CNV_TE_Alive', '存活位', [
        (2**k, ('NAMED_NOT_DESTROYED', m.role(r).name))
        for k, r in enumerate((*ROLES, 'house', 'frog'))])
    s8.frames(t, 'CNV_TE_Frame', '逻辑帧', [])
    s8.watch(t, 16., .5)
    return t


MISSION = {'engine_teamexit': mission}
CHECKS = {'engine_teamexit': {'a': check}}
