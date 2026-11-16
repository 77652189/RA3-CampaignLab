"""E184: airport RecallUnitsSpecialPower, produced Apollo deletion control.

Prediction: both runs produce and name one Apollo, near the airport at f255
and at the sortie at f405 (departure=7). Airport recall at f420 brings it
back only with the original module: f660 live/near/far = 3 versus 5.
Cast events are observed separately (predicted 1/0), not command acceptance.
Producer identity, selected recall members and parking phases remain gaps.
MEASURED: both predictions PASS, on 660/7/3/1 and off 660/7/5/0.
E187 named object-model replays match both complete existing readings.
Single produced Apollo return and cast only; selection, exact return timing,
other aircraft/airports and parking remain gaps. See work/re/e187_recall.md.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from model import Mission, Role, Script, Test, Unit, square


COMMAND = 'Command_AlliedRecallAllAircraft'
POWER = 'SpecialPower_RecallAllAircraft'
REMOVE = r'<RecallUnitsSpecialPower\b[^>]*/>'


def mission(enabled=True):
    m = Mission(name='CampRecallOnE' if enabled else 'CampRecallOffE',
                map=probe_range, units=[], facts={'enabled': enabled})
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedAirfield.xml').read_text(encoding='utf-8-sig')
    if not enabled:
        xml, n = re.subn(REMOVE, '', xml, flags=re.S)
        assert n == 1
    ident = 'AlliedAirfield'
    m.units.append(Unit(ident, xml, abilities={'recall': COMMAND, 'power': POWER}))
    m.assets.append((ident + '.xml', xml, 'GameObject:' + ident))
    m.replaces.append('GameObject:' + ident)
    m.put(ident, 'base gun', role='airport', name='E184 Airport')
    m.put('AlliedConstructionYard', 'base gun', 0, 650, role='yard')
    m.put('AlliedPowerPlant', 'base gun', 400, 0, role='power')
    m.spawns.add('AlliedFighterAircraft')
    m.cast['plane'] = Role('AlliedFighterAircraft', 'UNITRef - E184 Plane', 'p1', ['base gun'])
    m.waypoint('sortie', 'E184 Sortie', 'base gun', 0, 850)
    return m


def check(m):
    t = Test()
    plane = m.role('plane').name
    t.areas['E184 Airport'] = square(*m.site(m.role('airport').site), 250)
    t.areas['E184 Sortie'] = square(*m.point('sortie'), 180)
    t.counters = [('E184Frame', '完成帧'), ('E184Depart', '出发位'),
                  ('E184Final', '结束位'), ('E184Cast', '施放数')]
    t.scripts = [
        Script('Test - clock', [('COUNTER', 'E184Frame', 0, 660)],
               [('INCREMENT_COUNTER', 1, 'E184Frame')], once=False),
        Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player()),
                                  ('PLAYER_SET_MONEY', m.player(), 20000)]),
        Script('Test - produce', [('COUNTER', 'E184Frame', 2, 30)], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('airport').name,
             'Command_ConstructAlliedFighterAircraft')]),
        Script('Test - reference', [('COUNTER', 'E184Frame', 2, 240)], [
            ('TEAM_SET_PLAYERS_NEAREST_UNIT_OF_TYPE_TO_REFERENCE', m.role('plane').template,
             m.team(), plane)]),
        Script('Test - depart', [('COUNTER', 'E184Frame', 2, 270)], [
            ('MOVE_NAMED_UNIT_TO', plane, m.mark('sortie'))]),
        Script('Test - recall', [('COUNTER', 'E184Frame', 2, 420)], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('airport').name, COMMAND)]),
        Script('Test - cast', [('PLAYER_TRIGGERED_SPECIAL_POWER', m.player(), POWER)],
               [('INCREMENT_COUNTER', 1, 'E184Cast')], once=False)]
    for label, frame, counter, bit, cond in [
        ('initial live', 255, 'E184Depart', 1, ('NAMED_NOT_DESTROYED', plane)),
        ('initial near', 255, 'E184Depart', 2, ('NAMED_INSIDE_AREA', plane, 'E184 Airport')),
        ('departure far', 405, 'E184Depart', 4, ('NAMED_INSIDE_AREA', plane, 'E184 Sortie')),
        ('final live', 660, 'E184Final', 1, ('NAMED_NOT_DESTROYED', plane)),
        ('final near', 660, 'E184Final', 2, ('NAMED_INSIDE_AREA', plane, 'E184 Airport')),
        ('final far', 660, 'E184Final', 4, ('NAMED_INSIDE_AREA', plane, 'E184 Sortie'))]:
        t.scripts.append(Script('Test - ' + label, [('COUNTER', 'E184Frame', 2, frame), cond],
                                [('INCREMENT_COUNTER', bit, counter)]))
    t.expect = [('完成帧', 0, 'ever==', 660), ('出发位', 0, 'ever==', 7),
                ('结束位', 0, 'ever==', 3 if m.facts['enabled'] else 5),
                ('施放数', 0, 'ever==', int(m.facts['enabled']))]
    t.bench = [('bench_watch', dict(seconds=80, every=1, sheet=False, lines=4))]
    return t


MISSION = {'recallon_e': mission, 'recalloff_e': lambda: mission(False)}
CHECKS = {name: {'a': check} for name in MISSION}


