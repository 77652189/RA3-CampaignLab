"""DestroyObjectsUpdate on the Athena effect, isolated from its damage weapons.

Predict that the stock radius/filter removes the nearby civilian only on the
module-on lane. The distant civilian, nearby engineer and module-off civilian
should survive. A civilian spawned 12 frames after the effects distinguishes a
single initial scan (survives) from a scan repeated during the effect (removed).
"""
import re

from checks.engine_modulebatch import native
from maps import probe_range
from parts import Mission, Script, Test


HOST = 'AlliedAntiStructureVehicleCannonEffect'
ARMS = ('on', 'off')
TARGETS = ('near', 'far', 'engineer', 'control')


def mission():
    m = Mission(name='CampDestroyObj', map=probe_range, units=[])
    m.ext = True
    for arm, site in zip(ARMS, ('base gun', 'order gun')):
        effect = native(HOST, 'Props', 'CNVDestroyObj' + arm.title())
        effect.xml = re.sub(r'<GameObject\s+inheritFrom=.*?</GameObject>', '', effect.xml, flags=re.S)
        for module in ('FireWeaponUpdate', 'FireWeaponWhenDead',
                       *(() if arm == 'on' else ('DestroyObjectsUpdate',))):
            effect.xml, count = re.subn(fr'<{module}\b.*?</{module}>', '', effect.xml, flags=re.S)
            assert count == 1
        m.units.append(effect)
        m.spawns.add(effect.id)
        m.facts[arm] = effect.id
        m.waypoint(arm, 'Effect ' + arm, site)
    m.put('CivilianFemale1', 'base gun', 150, 0, role='near', name='Near civilian')
    m.put('CivilianFemale1', 'base gun', 700, 0, role='far', name='Far civilian')
    m.put('AlliedEngineer', 'base gun', 0, 150, role='engineer', name='Near engineer')
    m.put('CivilianFemale1', 'order gun', 150, 0, role='control', name='Control civilian')
    m.spawns.add('CivilianFemale1')
    m.waypoint('late', 'Late civilian point', 'base gun', 250, 0)
    return m


def check(m):
    t = Test()
    frame, effects, alive, late = 'Probe frame', 'Live effects', 'Live targets', 'Late target'
    t.counters = [(frame, 'frame'), (effects, 'effects'), (alive, 'alive'), (late, 'late')]
    t.scripts = [
        Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
        Script('Test - clock', [], [('INCREMENT_COUNTER', 1, frame)], once=False),
        Script('Test - spawn', [('COUNTER', frame, 3, 90)], [
            ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'Beam ' + arm, m.facts[arm], m.team('p1'), m.mark(arm))
            for arm in ARMS]),
        Script('Test - late', [('COUNTER', frame, 3, 102)], [
            ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'Late civilian', 'CivilianFemale1', m.team('p1'), m.mark('late'))]),
        Script('Test - late alive', [('NAMED_NOT_DESTROYED', 'Late civilian')],
               [('SET_COUNTER', late, 1)], once=False),
        Script('Test - late gone', [('NAMED_DESTROYED', 'Late civilian')],
               [('SET_COUNTER', late, 0)], once=False),
        Script('Test - reset', [], [('SET_COUNTER', effects, 0), ('SET_COUNTER', alive, 0)], once=False),
    ]
    for counter, names in ((effects, ['Beam ' + arm for arm in ARMS]),
                           (alive, [m.role(role).name for role in TARGETS])):
        for i, name in enumerate(names):
            t.scripts.append(Script('Test - count ' + name, [('NAMED_NOT_DESTROYED', name)],
                                    [('INCREMENT_COUNTER', 1 << i, counter)], once=False))
    t.expect = [('alive', 3, '==', 15, 5), ('effects', 6.25, 'ever==', 3, 7.75),
                ('alive', 9, '==', 14, 12), ('late', 9, '==', 1, 12)]
    t.bench = [('bench_watch', dict(seconds=15, every=0.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_destroyobjects': mission}
CHECKS = {'engine_destroyobjects': {'a': check}}
