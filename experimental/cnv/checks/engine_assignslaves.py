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


MISSION = {'engine_assignon': lambda: mission(True), 'engine_assignoff': lambda: mission(False)}
CHECKS = {name: {'a': check} for name in MISSION}
