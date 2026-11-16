"""E171: retail Oni targeted rush versus removal of MovementSpecialPower.

Prediction from the SDK: Command_TriggerRushAttackSpecialPower at a waypoint
250 units east (inside its 50..300 range) activates SPECIALABILITY_ACTIVE,
moves the original out of its starting square and clears the status by the
final frame. The otherwise identical removal control does neither. The
four-second duration is data, not an asserted exact activation/expiry frame.
Other hosts, collision damage, bounce and target-follow rules remain gaps.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, square, status


COMMAND = 'Command_TriggerRushAttackSpecialPower'


def mission():
    m = Mission(name='CampMovementE', map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / 'SageXML/Japan/Units/JapanAntiVehicleVehicleTech3.xml').read_text(encoding='utf-8-sig')
    for tag, site in [('On', 'base gun'), ('Off', 'high gun')]:
        ident = 'CNVE171' + tag
        xml = source.replace('id="JapanAntiVehicleVehicleTech3"', f'id="{ident}"', 1)
        for key, value in re.findall(r'<Define\s+name="([^"]+)"\s+value="([^"]+)"\s*/>', xml):
            xml = xml.replace('$' + key, value)
        xml = re.sub(r'<Defines>.*?</Defines>', '', xml, flags=re.S)
        if tag == 'Off':
            xml, n = re.subn(r'<MovementSpecialPower\b[^>]*/>', '', xml)
            assert n == 1
        unit = Unit(ident, xml)
        unit.abilities = {'rush': COMMAND}
        m.units.append(unit)
        m.put(ident, site, role=tag, name='E171 ' + tag, angle=0.0)
        m.waypoint('start ' + tag, 'E171 Start ' + tag, site)
        m.waypoint('goal ' + tag, 'E171 Goal ' + tag, site, 250, 0)
    return m


def check(m):
    t = Test()
    t.counters = [('E171Frame', '完成帧'), ('E171Active', '激活位'),
                  ('E171Moved', '位移位'), ('E171Clear', '结束位')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E171Frame', 0, 210)],
                        [('INCREMENT_COUNTER', 1, 'E171Frame')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for tag, weight in [('On', 1), ('Off', 10)]:
        name = m.role(tag).name
        area = 'E171 Start ' + tag
        t.areas[area] = square(*m.point('start ' + tag), 80)
        active = ('UNIT_HAS_OBJECT_STATUS', name, status('SPECIALABILITY_ACTIVE'))
        t.scripts += [
            Script('Test - quiet ' + tag, [], [('UNIT_CHANGE_OBJECT_STATUS', name, status('NO_ATTACK'), 1)]),
            Script('Test - rush ' + tag, [('COUNTER', 'E171Frame', 2, 60)],
                   [('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', name, m.ability(tag, 'rush'), m.mark('goal ' + tag))]),
            Script('Test - active ' + tag, [('COUNTER', 'E171Frame', 1, 60), active],
                   [('INCREMENT_COUNTER', weight, 'E171Active')]),
            Script('Test - moved ' + tag, [('COUNTER', 'E171Frame', 2, 210), ('NAMED_NOT_DESTROYED', name),
                                          ('NAMED_INSIDE_AREA', name, area, 'NOT')],
                   [('INCREMENT_COUNTER', weight, 'E171Moved')]),
            Script('Test - clear ' + tag, [('COUNTER', 'E171Frame', 2, 210), ('NAMED_NOT_DESTROYED', name), active + ('NOT',)],
                   [('INCREMENT_COUNTER', weight, 'E171Clear')])]
    t.expect = [('完成帧', 0, 'ever==', 210), ('激活位', 0, 'ever==', 1),
                ('位移位', 0, 'ever==', 1), ('结束位', 0, 'ever==', 11)]
    t.bench = [('bench_watch', dict(seconds=65, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_movement_e': mission}
CHECKS = {'engine_movement_e': {'a': check}}
