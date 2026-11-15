"""E156 StealthDetectorUpdate: retail dog, module removal and out-of-range controls.

Before bench: retail DetectionRange=300; mirage aura at 100 hides a Guardian.
Enemy dogs at 150 (on/off) or 450 (far); off differs only by module removal.
Predict INVISIBLE_DETECTED on the on target only after the initial scan race;
delete all dogs at 15s and expect that mark to clear. No reveal status is forced.
Exact scan phase and edge are outside this probe. See work/re/e156_detector.md.
MEASURED 2026-11-15: f45..105 seen=0, f112..226 seen=1, f234..415
seen=0; alive=111 throughout; evidence=3 from f271. Existing object model
replays f151 (1/111/1) and f310 (0/111/3); plan simulator remains strict xfail.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, status


def mission():
    m = Mission(name='CampDetectE', map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / 'SageXML/Allied/Units/AlliedScoutInfantry.xml').read_text(encoding='utf-8-sig')
    for tag, site, distance in [('on', 'base gun', 150), ('off', 'high gun', 150), ('far', 'order gun', 450)]:
        ident = 'CNVE156Dog' + tag
        xml = source.replace('id="AlliedScoutInfantry"', f'id="{ident}"', 1)
        if tag == 'off':
            xml, n = re.subn(r'<StealthDetectorUpdate\b[^>]*/>', '', xml, flags=re.S)
            assert n == 1
        m.units.append(Unit(ident, xml))
        m.put(ident, site, distance, 0, side='s1', role=tag + ' dog', name='E156 ' + tag + ' dog')
        m.put('AlliedAntiVehicleVehicleTech1', site, side='p1', role=tag + ' target', name='E156 ' + tag + ' target')
        m.put('AlliedAntiVehicleVehicleTech3', site, 0, -100, side='p1', role=tag + ' aura', name='E156 ' + tag + ' aura')
    return m


def check(m):
    t = Test()
    t.counters = [('E156Frame', '帧数'), ('E156Seen', '揭露'), ('E156Alive', '存活'), ('E156Evidence', '证据')]
    t.scripts = [Script('Test - E156 start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('SET_MILLISECOND_TIMER', 'E156Delete', 15.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', obj.name, state, 1)
        for obj in m.objects for state in ('NO_ATTACK', 'IMMOBILE')] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(tag + ' aura').name, 'GENERIC_TOGGLE_STATE', 1)
        for tag in ('on', 'off', 'far')]),
        Script('Test - E156 frame', [], [('INCREMENT_COUNTER', 1, 'E156Frame')], once=False),
        Script('Test - E156 delete', [('TIMER_EXPIRED', 'E156Delete')], [
            ('NAMED_DELETE', m.role(tag + ' dog').name) for tag in ('on', 'off', 'far')])]
    for counter in ('E156Seen', 'E156Alive'):
        t.scripts.append(Script('Test - clear ' + counter, [], [('SET_COUNTER', counter, 0)], once=False))
    for tag, bit in [('on', 1), ('off', 10), ('far', 100)]:
        name = m.role(tag + ' target').name
        t.scripts.append(Script('Test - seen ' + tag,
            [('UNIT_HAS_OBJECT_STATUS', name, status('INVISIBLE_DETECTED'))],
            [('INCREMENT_COUNTER', bit, 'E156Seen')], once=False))
        t.scripts.append(Script('Test - alive ' + tag, [('NAMED_NOT_DESTROYED', name)],
            [('INCREMENT_COUNTER', bit, 'E156Alive')], once=False))
    for tag, bit, conds in [
        ('detected', 1, [('COUNTER', 'E156Seen', 2, 1), ('COUNTER', 'E156Alive', 2, 111)]),
        ('cleared', 2, [('FLAG', 'E156 detected', 1), ('COUNTER', 'E156Frame', 3, 270),
                        ('COUNTER', 'E156Seen', 2, 0), ('COUNTER', 'E156Alive', 2, 111)])]:
        t.scripts.append(Script('Test - evidence ' + tag, conds,
            [('INCREMENT_COUNTER', bit, 'E156Evidence'), ('SET_FLAG', 'E156 ' + tag, 1)]))
    t.expect = [('帧数', 0, 'ever>=', 300), ('存活', 0, '==', 111),
                ('揭露', 8, 'ever==', 1, 14), ('证据', 19, 'ever==', 3)]
    t.bench = [('bench_watch', dict(seconds=24, every=0.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_detector': mission}
CHECKS = {'engine_detector': {'a': check}}
