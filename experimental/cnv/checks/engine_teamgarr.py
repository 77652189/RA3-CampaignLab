"""Nearest-building team action; evidence: work/re/c_teamgarr_report.md.

Prediction before bench: Target's two conscripts walk into the nearer neutral
apartment, Other stays out. Empty crew at 2s and repeated order at 12s do no
harm. a starts by West, b by East, with identical building insertion order.
Counters: enclosed mask (Target 1/2, Other 4), owner mask (West 1/East 2),
alive mask (three men and two apartments 1/2/4/8/16), logical frame.
Walk/entry transition timing, capacity, contested/full buildings and other
templates are gaps; this probes ordinary infantry and two empty apartments.
"""
from maps import probe_border
from parts import Mission, Script, Test, status
from checks import engine_scripts8 as s8

MEN = ('target 1', 'target 2', 'other')
HOUSES = ('west', 'east')


def mission():
    m = Mission(name='CampTeamGarr', map=probe_border, units=[], facts={})
    crews = {c: m.crew(c) for c in ('Target', 'Other', 'Empty')}
    for role, x in zip(HOUSES, (1200., 2300.)):
        m.put('AM_Apartments_01', 'stop row', x-1300., 1500.-4300.,
              side='civ', role=role, name='CNV TeamGarr '+role)
    for k, role in enumerate(MEN):
        m.put('SovietAntiInfantryInfantry', 'stop row', -100.+60.*k, -3100.,
              role=role, name='CNV TeamGarr '+role,
              props={'originalOwner': crews['Other' if role == 'other' else 'Target']})
    return m


def check(m, which):
    if which == 'b':
        for obj in m.objects:
            if obj.name in {m.role(role).name for role in MEN}:
                obj.x += 1100.
    t = Test()
    t.scripts.append(Script('Test - TeamGarr hold', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, status('NO_ATTACK'), 1)
        for r in (*MEN, *HOUSES)]))
    for label, secs, crew in (('empty', 2., 'Empty'), ('enter', 5., 'Target'),
                              ('repeat', 12., 'Target')):
        s8.at(t, label, secs, [('TEAM_GARRISON_NEAREST_BUILDING', m.teams[crew])])
    s8.total(t, 'CNV_TG_In', '进驻位', [
        (2**k, ('UNIT_HAS_OBJECT_STATUS', m.role(r).name, status('ENCLOSED')))
        for k, r in enumerate(MEN)])
    s8.total(t, 'CNV_TG_Own', '楼归属', [
        (2**k, ('NAMED_OWNED_BY_PLAYER', m.player('p1'), m.role(r).name))
        for k, r in enumerate(HOUSES)])
    s8.total(t, 'CNV_TG_Alive', '存活位', [
        (2**k, ('NAMED_NOT_DESTROYED', m.role(r).name))
        for k, r in enumerate((*MEN, *HOUSES))])
    s8.frames(t, 'CNV_TG_Frame', '逻辑帧', [])
    s8.watch(t, 22., .5)
    return t


MISSION = {'engine_teamgarr': mission}
CHECKS = {'engine_teamgarr': {w: (lambda m, w=w: check(m, w)) for w in 'ab'}}
