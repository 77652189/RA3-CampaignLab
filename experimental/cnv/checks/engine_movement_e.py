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
FAR = [('F5', 'pace start', 542.0), ('F7', 'legs start', 770.0)]   # retail j07 wp_oni_p1_a / _b -> the goto point


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
    for tag, site, far in FAR:              # check b: retail j07's two reaches, on two pace lanes
        m.waypoint('start ' + tag, 'E171 Start ' + tag, site)
        m.waypoint('goal ' + tag, 'E171 Goal ' + tag, site, far, 0)
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


def far(m):
    """A292, retail j07 (O1 Introduce Jinzatsus): an Oni made by CREATE_NAMED_ON_TEAM_AT_WAYPOINT and in the same
    script rushed at a point 542 / 770 away, beyond MaxCastRange 300. Per second, F5 + F7 weighed 1 / 10 (等 1 /
    1000): 激活 (SPECIALABILITY_ACTIVE now), 进 (100-wide bands east of the start ever reached, the goal's 40-square
    one more), 等 (script frames from f30 before the first active one). Refused: 0 / 0 / 270 each; walks in,
    rushes from 300: 等 ~ the walk."""
    t = Test()
    t.counters = [('E171Frame', '帧'), ('E171Act', '激活'), ('E171Go', '进'), ('E171Wait', '等')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E171Frame', 0, 300)], [('INCREMENT_COUNTER', 1, 'E171Frame')],
                        once=False),
                 Script('Test - act reset', [], [('SET_COUNTER', 'E171Act', 0)], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for (tag, _, reach), weight in zip(FAR, (1, 10)):
        name, (x, y) = 'E171 ' + tag, m.point('start ' + tag)
        active = ('UNIT_HAS_OBJECT_STATUS', name, status('SPECIALABILITY_ACTIVE'))
        t.scripts += [
            Script('Test - make ' + tag, [('COUNTER', 'E171Frame', 2, 30)],
                   [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', name, 'JapanAntiVehicleVehicleTech3', m.team('p1'),
                     m.mark('start ' + tag)),
                    ('NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', name, COMMAND, m.mark('goal ' + tag))]),
            Script('Test - active ' + tag, [active],
                   [('INCREMENT_COUNTER', weight, 'E171Act'), ('SET_COUNTER', 'E171Seen' + tag, 1)], once=False),
            Script('Test - wait ' + tag, [('COUNTER', 'E171Frame', 3, 30), ('COUNTER', 'E171Frame', 0, 300),
                                         ('COUNTER', 'E171Seen' + tag, 2, 0)],
                   [('INCREMENT_COUNTER', weight ** 3, 'E171Wait')], once=False)]
        bands = [[(x + d, y - 200), (x + 2000, y - 200), (x + 2000, y + 200), (x + d, y + 200)]
                 for d in range(100, int(reach) + 1, 100)] + [square(x + reach, y, 40)]
        for k, area in enumerate(bands):
            t.areas[f'E171 {tag} band {k}'] = area
            t.scripts.append(Script(f'Test - band {tag} {k}', [('NAMED_INSIDE_AREA', name, f'E171 {tag} band {k}')],
                                    [('INCREMENT_COUNTER', weight, 'E171Go')]))
    t.expect = [('帧', 0, 'ever==', 300)]
    t.bench = [('bench_watch', dict(seconds=25, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_movement_e': mission}
CHECKS = {'engine_movement_e': {'a': check, 'b': far}}
