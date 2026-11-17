"""Named container exit contrast; evidence: work/re/c_exitbld_report.md.

Prediction: four Conscripts (two crews, two per apartment) start enclosed.
At 5s exit West (a) or East (b), irrespective of crew. The other apartment
stays occupied. Repeating at 9s is harmless. Outside crew member stays alive.
Counters: ENCLOSED mask West=1/2 East=4/8 outside=16, near-West/near-East
population packed as west+10*east, alive mask (five men, two houses), frame.
Exact doorway coordinates/timing and other container types remain gaps.
MEASURED: a f45..75 enclosed15, f82..257 enclosed12; b f49..69 enclosed15,
f80..321 enclosed3. All 58 samples area22/alive127. The original area2/20
prediction is retained below and as strict xfail: area counts enclosed men too.
"""
from maps import probe_border
from parts import Mission, Script, Test, square, status
from checks import engine_scripts8 as s8

MAN = 'SovietAntiInfantryInfantry'
MEN = ('west alpha', 'west beta', 'east alpha', 'east beta', 'outside')
HOUSES = ('west', 'east')


def mission():
    m = Mission(name='CampExitBld', map=probe_border, units=[], facts={})
    crews = {c: m.crew(c) for c in ('Alpha', 'Beta')}
    for role, x in zip(HOUSES, (1000., 2800.)):
        m.put('AM_Apartments_01', 'stop row', x-1300., -1800., side='civ',
              role=role, name='CNV ExitBld '+role)
        m.waypoint(role, 'CNV ExitBld '+role, 'stop row', x-1300., -1800.)
    for k, role in enumerate(MEN):
        m.put(MAN, 'stop row', -500.+300.*k, -2300., role=role,
              name='CNV ExitBld '+role,
              props={'originalOwner': crews['Beta' if role.endswith('beta') else 'Alpha']})
    return m


def check(m, which):
    t = Test()
    t.scripts.append(Script('Test - ExitBld hold', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, status('NO_ATTACK'), 1)
        for r in (*MEN, *HOUSES)]))
    s8.at(t, 'exitbld load', 1., [
        ('NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY', m.role(r).name,
         m.role(r.split()[0]).name) for r in MEN[:-1]])
    target = m.role('west' if which == 'a' else 'east').name
    for label, secs in (('exit', 5.), ('repeat', 9.)):
        s8.at(t, 'exitbld '+label, secs, [('EXIT_SPECIFIC_BUILDING', target)])
    s8.total(t, 'CNV_EB_In', '进驻位', [
        (1 << k, ('UNIT_HAS_OBJECT_STATUS', m.role(r).name, status('ENCLOSED')))
        for k, r in enumerate(MEN)])
    for role in HOUSES:
        t.areas['ExitBld '+role] = square(*m.point(role), 450.)
    s8.total(t, 'CNV_EB_Area', '区域码', [
        (weight*n, ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player(),
                    2, n, MAN, 'ExitBld '+role))
        for role, weight in zip(HOUSES, (1, 10)) for n in range(1, 5)])
    s8.total(t, 'CNV_EB_Alive', '存活位', [
        (1 << k, ('NAMED_NOT_DESTROYED', m.role(r).name))
        for k, r in enumerate((*MEN, *HOUSES))])
    s8.frames(t, 'CNV_EB_Frame', '逻辑帧', [])
    t.expect = [('进驻位', 0., 'ever==', 15, 4.),
                ('进驻位', 8., '==', 12 if which == 'a' else 3),
                ('区域码', 8., '==', 2 if which == 'a' else 20),
                ('存活位', 0., '==', 127)]
    s8.watch(t, 14., .5)
    return t


MISSION = {'engine_exitbld': mission}
CHECKS = {'engine_exitbld': {w: (lambda m, w=w: check(m, w)) for w in 'ab'}}
