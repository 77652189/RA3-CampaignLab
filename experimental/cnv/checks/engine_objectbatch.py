"""E146: three independent object-module treatments on one map.

AutoDeposit: retail Swiss bank versus identical module removal, different owners,
both wallets reset at start. Predict only the enabled owner's balance grows.
HealCrate: retail HealCrate versus module removal; damaged infantry walk onto
each crate. In a, same-owner crates leave both at 50 (initial 100/50 prediction
rejected). Secret-file variants contain unsupported SDK attributes and are not
silently treated as equivalent to this crate.
LoseHealth: retail dreadnought's complete drain module transplanted onto two
identical 480-HP tanks, enabled versus removal. Set GENERIC_TOGGLE_STATE at 8s,
then also UNDER_IRON_CURTAIN at 10s. In a, 101% leaves both at 100 (initial drain
prediction rejected). b tests 0% separately, not a fitted damage rate. This
measures the custom host, not retail naval activation.
No exact capture-index to game-clock correspondence is assumed.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted, square


def clone(relative, original, ident):
    xml = (Path(labpaths.SDK3) / 'SageXML' / relative).read_text(encoding='utf-8-sig')
    xml, n = re.subn(r'\bid="' + original + '"', 'id="' + ident + '"', xml, count=1)
    assert n == 1
    return Unit(ident, xml.replace('EditorName="' + original + '"', 'EditorName="' + ident + '"'))


def remove(unit, module):
    unit.xml, n = re.subn(r'<' + module + r'\b[^>]*>.*?</' + module + '>', '', unit.xml, flags=re.S)
    assert n == 1


def mission():
    m = Mission(name='CampObjectsE', map=probe_range, units=[])
    ship = (Path(labpaths.SDK3) / 'SageXML/Soviet/Units/SovietAntiStructureShip.xml').read_text(encoding='utf-8-sig')
    drain = re.search(r'<LoseHealthUpdate\b.*?</LoseHealthUpdate>', ship, re.S).group()
    for tag, enabled, side, dx in [('on', True, 'p1', 0), ('off', False, 's2', 500)]:
        bank = clone('Civilian/Geneva_GE/Buildings/GE_SwissBank.xml', 'GE_SwissBank', 'CNVE146Bank' + tag)
        file = clone('Neutral/Crates/HealCrate.xml', 'HealCrate', 'CNVE146File' + tag)
        tank = clone('Allied/Units/AlliedAntiVehicleVehicleTech1.xml', 'AlliedAntiVehicleVehicleTech1', 'CNVE146Drain' + tag)
        if not enabled:
            remove(bank, 'AutoDepositUpdate')
            remove(file, 'HealCrateCollide')
        else:
            tank.xml = tank.xml.replace('</Behaviors>', drain + '</Behaviors>')
        m.units += [bank, file, tank]
        m.put(bank.id, 'base gun', dx, 0, side=side, role='bank ' + tag, name='Object Bank ' + tag)
        m.put(file.id, 'switch gun', dx, 0, role='file ' + tag, name='Object File ' + tag)
        # Both infantry and drain controls belong to the human player.
        m.put('AlliedAntiInfantryInfantry', 'switch gun', dx, -250,
              role='man ' + tag, name='Object Man ' + tag)
        m.put(tank.id, 'order gun', dx, 0, role='tank ' + tag, name='Object Tank ' + tag)
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    phase = {8: [], 10: [], 12: []}
    for tag in ('on', 'off'):
        side = 'p1' if tag == 'on' else 's2'
        start.append(('PLAYER_SET_MONEY', m.player(side), 0))
        t.counters.append(('E146Money' + tag, 'money ' + tag))
        t.scripts.append(Script('Test - E146 money ' + tag, [],
            [('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), 'E146Money' + tag)], once=False))
        man, tank = [m.role(kind + ' ' + tag).name for kind in ('man', 'tank')]
        start += [('UNIT_SET_HEALTH', man, 50.0),
                  ('UNIT_CHANGE_OBJECT_STATUS', man, 'NO_ATTACK', 1),
                  ('UNIT_CHANGE_OBJECT_STATUS', tank, 'NO_ATTACK', 1)]
        phase[8] += [('MOVE_NAMED_UNIT_TO', man, 'E146 ' + tag + ' pickup'),
                     ('UNIT_CHANGE_OBJECT_STATUS', tank, 'GENERIC_TOGGLE_STATE', 1)]
        phase[10].append(('UNIT_CHANGE_OBJECT_STATUS', tank, 'UNDER_IRON_CURTAIN', 1))
        phase[12].append(('NAMED_DELETE', m.role('bank ' + tag).name))
        counted('E146Heal' + tag, 'heal ' + tag, t, health=man)
        counted('E146Drain' + tag, 'drain ' + tag, t, health=tank)
    # A separate waypoint keeps the control's movement geometrically identical.
    x, y = m.site('switch gun')
    t.waypoints['E146 on pickup'] = (x, y)
    t.waypoints['E146 off pickup'] = (x + 500, y)
    for at, actions in phase.items():
        timer = f'Test - E146 phase {at}'
        start.append(('SET_MILLISECOND_TIMER', timer, float(at)))
        t.scripts.append(Script(timer, [('TIMER_EXPIRED', timer)], actions))
    t.scripts.insert(0, Script('Test - E146 start', [], start))
    hidden = {label: name for name, label in t.counters}
    t.counters = [(hidden['money on'], 'money on'), (hidden['money off'], 'money off')]
    for family in ('heal', 'drain'):
        packed = 'E146Packed' + family
        t.counters.append((packed, family))
        t.scripts.append(Script('Test - E146 reset ' + family, [], [('SET_COUNTER', packed, 0)], once=False))
        for tag, weight in [('on', 1), ('off', 1000)]:
            for value in range(101):
                t.scripts.append(Script(f'Test - E146 pack {family} {tag} {value}',
                    [('COUNTER', hidden[family + ' ' + tag], 2, value)],
                    [('INCREMENT_COUNTER', value * weight, packed)], once=False))
    # E146 a actual readings. The initial treatment predictions did not occur:
    # same-owner crate pickup and 101% drain remain unresolved, not benched.
    t.expect = [('money on', 20, '==', 60, 25), ('money off', 2, '==', 0, 25),
                ('heal', 3, '==', 50050, 25), ('drain', 3, '==', 100100, 25)]
    t.bench = [('bench_watch', dict(seconds=25, every=1, sheet=False, lines=4))]
    return t


def diagnostic(m):
    """Separate b recipe: neutral crate owners and drain floor 0%, with gates.

    Initial hypotheses: neutral crate ownership permits pickup; HealthTrigger
    is a floor rather than an upper activation threshold. Both failed to
    produce an effect: arrived/status gates=111111, heal=50050, drain=100100.
    Trigger causes remain gaps; see work/re/e146_objectbatch.md. No third run.
    gates: arrival on/off=1/10, toggle on/off=100/1000, curtain=10000/100000.
    """
    for unit in m.units:
        if unit.id == 'CNVE146Drainon':
            unit.xml = unit.xml.replace('HealthTrigger="101%"', 'HealthTrigger="0%"')
    for obj in m.objects:
        if obj.template.startswith('CNVE146File'):
            obj.side = 'neutral'
    t = check(m)
    t.counters[1] = ('E146Gates', 'gates')
    t.scripts.append(Script('Test - gates zero', [], [('SET_COUNTER', 'E146Gates', 0)], once=False))
    for tag, weight in [('on', 1), ('off', 10)]:
        area = 'E146 ' + tag + ' arrived'
        t.areas[area] = square(*t.waypoints['E146 ' + tag + ' pickup'], 35)
        t.scripts.append(Script('Test - arrived ' + tag,
            [('NAMED_INSIDE_AREA', m.role('man ' + tag).name, area)],
            [('INCREMENT_COUNTER', weight, 'E146Gates')], once=False))
        for bit, factor in [('GENERIC_TOGGLE_STATE', 100), ('UNDER_IRON_CURTAIN', 10000)]:
            t.scripts.append(Script('Test - gate ' + tag + bit,
                [('UNIT_HAS_OBJECT_STATUS', m.role('tank ' + tag).name, bit)],
                [('INCREMENT_COUNTER', weight * factor, 'E146Gates')], once=False))
    t.expect = [('money on', 20, '==', 60, 25), ('gates', 20, '==', 111111, 25),
                ('heal', 3, '==', 50050, 25), ('drain', 3, '==', 100100, 25)]
    return t


MISSION = {'engine_objectbatch': mission}
CHECKS = {'engine_objectbatch': {'a': check, 'b': diagnostic}}
