"""E66: retail repair-bay target assignment, with/without its dispatch module.

Prediction from XML: Command_RepairVehicle targets an object within 200; three
spawned drones may also acquire a damaged vehicle autonomously. Consequently
healing alone cannot establish assignment. Read the cast event and target's
BOOBY_TRAPPED/TARGETED_FOR_REPAIR/UNDERGOING_REPAIR bits as well as health.
Only one friendly damaged vehicle per build; no general slave-system claim.
"""
import os
import re

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted

POWER = 'SpecialPower_TargetedRepairVehicle'


def mission(enabled):
    tag = 'On' if enabled else 'Off'
    m = Mission(name='CampAssign' + tag, map=probe_range, units=[])
    path = os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures',
                        'AlliedConstructionYardRepairBay.xml')
    with open(path, encoding='utf-8-sig') as f:
        xml = f.read()
    ident = 'CNVAssign' + tag
    xml = xml.replace('id="AlliedConstructionYardRepairBay"', f'id="{ident}"', 1)
    pattern = r'<AssignSlavesTargetObjectSpecialPower\b[^>]*/>'
    assert len(re.findall(pattern, xml, re.S)) == 1
    if not enabled:
        xml = re.sub(pattern, '', xml, flags=re.S)
    m.units.append(Unit(ident, xml, abilities={'repair': 'Command_RepairVehicle', 'power': POWER},
                        what='repair target assignment module control'))
    m.put(ident, 'order gun', role='bay', name='Assign Bay')
    m.put('AlliedAntiVehicleVehicleTech1', 'order gun', 0, 170,
          role='target', name='Assign Target')
    m.spawns.add('AlliedWarFactoryRepairDrone')
    return m


def check(m):
    t = Test()
    p, bay, target = m.player('p1'), m.role('bay').name, m.role('target').name
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p),
        ('SET_MILLISECOND_TIMER', 'Assign cast', 8.0)]),
        Script('Test - assign', [('TIMER_EXPIRED', 'Assign cast')], [
            ('UNIT_SET_HEALTH', target, 20.0),
            ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', bay, m.ability('bay', 'repair'), target)]),
        Script('Test - cast seen', [('PLAYER_TRIGGERED_SPECIAL_POWER', p, m.ability('bay', 'power'))],
               [('INCREMENT_COUNTER', 1, 'CNV_Assign_Cast')], once=False)]
    counted('CNV_Assign_HP', '目标血量', t, health=target)
    t.counters.append(('CNV_Assign_Cast', '施放数'))
    t.counters.append(('CNV_Assign_Status', '目标状态'))
    t.scripts.append(Script('Test - status zero', [], [
        ('SET_COUNTER', 'CNV_Assign_Status', 0)], once=False))
    for bit, value in [('BOOBY_TRAPPED', 1), ('TARGETED_FOR_REPAIR', 10),
                       ('UNDERGOING_REPAIR', 100)]:
        t.scripts.append(Script('Test - status ' + bit, [('UNIT_HAS_OBJECT_STATUS', target, bit)],
                               [('INCREMENT_COUNTER', value, 'CNV_Assign_Status')], once=False))
    # E66 on/off both healed autonomously; only the cast event distinguished them.
    # Bounded plateaus avoid claiming exact acquisition/healing frames.
    enabled = m.role('bay').template == 'CNVAssignOn'
    t.expect = [('目标血量', 1, '==', 100, 5),
                ('施放数', 12, '==', int(enabled), 26),
                ('目标状态', 12, '==', 110, 20),
                ('目标血量', 26, '==', 100, 27),
                ('目标状态', 26, '==', 0, 27)]
    t.bench = [('bench_watch', dict(seconds=26, every=1, sheet=False, lines=3))]
    return t


def frame_heal(m):
    """E235: check a on script frames (E68: the capture seconds drift). Damage (and, on, the press) at f120.

    Prediction (simulator 11-25: a drone 170 away flies at 150 after 0.25 s, mends 20 HP/s of the 480): frames from
    f120 until the target reads UNDERGOING_REPAIR on 2 / off 23; HP at f240 on 53 / off 47, at f390 on 95 / off 89.
    """
    t = Test()
    target = m.role('target').name
    t.counters = [('E235F', '脚本帧'), ('E235Wait', '等待帧'), ('E235A', '血量240'), ('E235B', '血量390')]
    t.scripts = [Script('Test - frame', [('COUNTER', 'E235F', 0, 400)], [('INCREMENT_COUNTER', 1, 'E235F')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                 Script('Test - wait', [('COUNTER', 'E235F', 3, 120), ('COUNTER', 'E235On', 2, 0)],
                        [('INCREMENT_COUNTER', 1, 'E235Wait')], once=False),
                 Script('Test - attached', [('COUNTER', 'E235F', 3, 121),
                                            ('UNIT_HAS_OBJECT_STATUS', target, 'UNDERGOING_REPAIR')],
                        [('SET_COUNTER', 'E235On', 1)]),
                 Script('Test - at 240', [('COUNTER', 'E235F', 2, 240)],
                        [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, 'E235A')]),
                 Script('Test - at 390', [('COUNTER', 'E235F', 2, 390)],
                        [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, 'E235B')])]
    t.scripts.append(Script('Test - damage', [('COUNTER', 'E235F', 2, 120)], [   # both arms press (the control's
        ('UNIT_SET_HEALTH', target, 20.0),                                     # button is still there, check a)
        ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', m.role('bay').name, m.ability('bay', 'repair'), target)]))
    t.expect = [('脚本帧', 0, 'ever==', 400)]
    t.bench = [('bench_watch', dict(seconds=32, every=1, sheet=False, lines=4))]
    return t


def heal_curve(m):
    """E235 d: check c's scene, the target's HP % and status code live each frame beside the script frame, so every
    capture is one (frame, HP, status) sample on mission time (E68) -- the heal's shape, f120 to f600.

    Prediction (simulator 11-25, 20 HP/s of 480 = 4.17 %/s from the attach): a straight line from 20 % at the attach
    (f122 on / f143 off) to 100 % about 19 s later, status 110 throughout, then 0.
    """
    t = frame_heal(m)
    target = m.role('target').name
    t.counters = [('E235F', '脚本帧'), ('E235Wait', '等待帧'), ('E235H', '血量'), ('E235S', '状态')]
    t.scripts = [s for s in t.scripts if not s.name.startswith('Test - at ')]
    t.scripts[0].when = [('COUNTER', 'E235F', 0, 600)]
    t.scripts.append(Script('Test - hp', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', target, 'E235H'),
                                              ('SET_COUNTER', 'E235S', 0)], once=False))
    for bit, value in [('TARGETED_FOR_REPAIR', 10), ('UNDERGOING_REPAIR', 100)]:
        t.scripts.append(Script('Test - status ' + bit, [('UNIT_HAS_OBJECT_STATUS', target, bit)],
                                [('INCREMENT_COUNTER', value, 'E235S')], once=False))
    t.expect = [('脚本帧', 0, 'ever==', 600)]
    t.bench = [('bench_watch', dict(seconds=44, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_assignon': lambda: mission(True), 'engine_assignoff': lambda: mission(False)}
CHECKS = {name: {'a': check, 'c': frame_heal, 'd': heal_curve} for name in MISSION}


def competition():
    """E67: occupy three drones before assigning a fourth vehicle, in two isolated lanes.

    Prediction: three UNDERGOING_REPAIR bits must be observed before the cast.
    A dispatch that preempts occupied drones should heal the fourth target earlier
    in the enabled lane. Equal readings leave dispatch unresolved, not disproved.
    Retail drone counts, filters and repair rates are unchanged.
    """
    m = Mission(name='CampAssignRace', map=probe_range, units=[])
    for tag, enabled, site in [('on', True, 'order gun'), ('off', False, 'base gun')]:
        source = mission(enabled)
        if not enabled:
            # Auto-acquisition control receives damage only. Publishing the same
            # retail button on two templates is ambiguous to the contract owner map.
            source.units[0].abilities = {}
        m.units.extend(source.units)
        m.put(source.units[0].id, site, role=tag + 'bay', name=tag + ' Bay')
        for i, (x, y) in enumerate([(-90, 80), (0, 110), (90, 80), (0, 185)]):
            m.put('AlliedAntiVehicleVehicleTech1', site, x, y,
                  role=f'{tag}{i}', name=f'{tag} Target {i}')
    m.spawns.add('AlliedWarFactoryRepairDrone')
    return m


def competition_check(m):
    t = Test()
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('SET_MILLISECOND_TIMER', 'Race damage', 8.0),
        ('SET_MILLISECOND_TIMER', 'Race cast', 12.0)])]
    for tag in ('on', 'off'):
        targets = [m.role(f'{tag}{i}').name for i in range(4)]
        t.scripts.append(Script('Test - occupy ' + tag, [('TIMER_EXPIRED', 'Race damage')],
                               [('UNIT_SET_HEALTH', name, 20.0) for name in targets[:3]]))
        actions = [('UNIT_SET_HEALTH', targets[3], 20.0)]
        if tag == 'on':
            actions.append(('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', m.role(tag + 'bay').name,
                            m.ability(tag + 'bay', 'repair'), targets[3]))
        t.scripts.append(Script('Test - fourth ' + tag, [('TIMER_EXPIRED', 'Race cast')], actions))
        counted(f'CNV_Race_{tag}3', f'{tag} fourth HP', t, health=targets[3])
        counter = 'CNV_Race_Attached_' + tag
        t.counters.append((counter, tag + ' occupied'))
        t.scripts.append(Script('Test - clear ' + tag, [], [('SET_COUNTER', counter, 0)], once=False))
        for i, name in enumerate(targets[:3]):
            t.scripts.append(Script(f'Test - occupied {tag}{i}', [
                ('UNIT_HAS_OBJECT_STATUS', name, 'UNDERGOING_REPAIR')],
                [('INCREMENT_COUNTER', 1, counter)], once=False))
    # E67 single-run measurements (NOEXPECT at capture time). These assert
    # treatment/control behavior, not an inferred drone reallocation algorithm.
    t.expect = [('on fourth HP', 1, '==', 100, 6),
                ('off fourth HP', 1, '==', 100, 6),
                ('on occupied', 8, '==', 3, 10),
                ('off occupied', 8, '==', 3, 10),
                ('on fourth HP', 11, '==', 25, 12),
                ('off fourth HP', 11, '==', 20, 27),
                ('on occupied', 11, '==', 3, 26),
                ('off occupied', 11, '==', 3, 26),
                ('on fourth HP', 26, '==', 86, 26),
                ('on fourth HP', 27, '==', 92, 27)]
    t.bench = [('bench_watch', dict(seconds=26, every=1, sheet=False, lines=4))]
    return t


MISSION['engine_assignrace'] = competition
CHECKS['engine_assignrace'] = {'a': competition_check}


def frame_check(m):
    """E181: freeze competition readings on script frames, not capture seconds.

    Prediction: three occupied targets in each lane at f150 (code 33).
    Damage/cast at f180, snapshot at f360: SDK 480 HP and 20 HP/s predict
    fourth-target HP 70/20 after 12 seconds. Acquisition phase is unmeasured;
    this prediction must not be used to fit the rate or shift the snapshot.
    """
    t = Test()
    t.counters = [('E181Frame', '脚本帧'), ('E181Occupied', '前置占用'),
                  ('E181On', '指定目标血量'), ('E181Off', '对照目标血量')]
    t.scripts = [Script('Test - frame', [('COUNTER', 'E181Frame', 0, 360)],
                        [('INCREMENT_COUNTER', 1, 'E181Frame')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    snapshots = []
    for tag, weight in [('on', 1), ('off', 10)]:
        targets = [m.role(f'{tag}{i}').name for i in range(4)]
        t.scripts.append(Script('Test - occupy ' + tag, [('COUNTER', 'E181Frame', 2, 120)],
                               [('UNIT_SET_HEALTH', name, 20.0) for name in targets[:3]]))
        for i, name in enumerate(targets[:3]):
            t.scripts.append(Script(f'Test - occupied {tag}{i}', [
                ('COUNTER', 'E181Frame', 2, 150),
                ('UNIT_HAS_OBJECT_STATUS', name, 'UNDERGOING_REPAIR')],
                [('INCREMENT_COUNTER', weight, 'E181Occupied')]))
        actions = [('UNIT_SET_HEALTH', targets[3], 20.0)]
        if tag == 'on':
            actions.append(('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', m.role('onbay').name,
                            m.ability('onbay', 'repair'), targets[3]))
        t.scripts.append(Script('Test - fourth ' + tag, [('COUNTER', 'E181Frame', 2, 180)], actions))
        snapshots.append(('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', targets[3], 'E181' + tag.title()))
    t.scripts.append(Script('Test - snapshot', [('COUNTER', 'E181Frame', 2, 360)], snapshots))
    t.expect = [('脚本帧', 0, 'ever==', 360), ('前置占用', 0, 'ever==', 33),
                ('指定目标血量', 0, 'ever==', 70), ('对照目标血量', 0, 'ever==', 20)]
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    return t


CHECKS['engine_assignrace']['b'] = frame_check
CONTROLS = {'engine_assignoff': 'engine_assignon'}
