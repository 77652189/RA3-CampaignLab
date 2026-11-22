"""E173: produced Apollo, direct reference sortie, retail return versus removal.

Prediction before running: both builds produce one aircraft, the reference
leaves the airport and reaches the sortie area. Only the original return
module sets USER_1 and brings that same live aircraft back. No placed/spawned
aircraft and no assumption that a newly produced aircraft joins a map team.
Frame 660 freezes four HUD lines: clock, departure flags, final flags, cast.
Departure: live=1, airport at 255=2, sortie at 405=4. Final: live=1,
airport=2, sortie=4, ever USER_1 after return=8, ever DOCKING=16.
Expected original final includes live/airport/USER_1 (11); DOCKING is
observational only. Removal prediction is live/sortie (5). Internal producer
identity and parking slot are gaps, even if the spatial prediction succeeds.

MEASURED a: both runs froze at 660/7/11/1. The deletion prediction failed.
Static diagnosis: a supplied a retail-named Unit without Mission.replaces;
the linker retained the retail aircraft in BOTH builds. This is a production,
reference and sortie baseline, NOT a module-removal experiment. b prepares
the explicit asset replacement, retains the original predictions and has NOT
been run. See work/re/e173_returnproducer.md. No third run in this item.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from model import Mission, Role, Script, Test, Unit, square


def mission(enabled=True):
    m = Mission(name='CampReturnOnE' if enabled else 'CampReturnOffE', map=probe_range,
                units=[], facts={'enabled': enabled,
                                 'return': 'Command_AlliedFighterAircraftReturnToAirfield',
                                 'power': 'SpecialPowerReturnToProducer'})
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Units/AlliedFighterAircraft.xml').read_text(encoding='utf-8-sig')
    if not enabled:
        xml, n = re.subn(r'<ReturnToProducerSpecialPower\b[^>]*/>', '', xml, flags=re.S)
        assert n == 1
    m.units.append(Unit('AlliedFighterAircraft', xml, abilities={
        'return': 'Command_AlliedFighterAircraftReturnToAirfield',
        'power': 'SpecialPowerReturnToProducer'}))
    m.spawns.add('AlliedFighterAircraft')
    m.put('AlliedAirfield', 'base gun', role='airport', name='E173 Airport')
    m.put('AlliedConstructionYard', 'base gun', 0, 650, role='yard')
    m.put('AlliedPowerPlant', 'base gun', 400, 0, role='power')
    m.cast['plane'] = Role('AlliedFighterAircraft', 'UNITRef - E173 Plane', 'p1', ['base gun'])
    m.waypoint('sortie', 'E173 Sortie', 'base gun', 0, 850)
    # Production and reference naming belong to the base mission, too.
    plane = m.role('plane').name
    m.scripts = [
        Script('Test - clock', [('COUNTER', 'E173Frame', 0, 660)],
               [('INCREMENT_COUNTER', 1, 'E173Frame')], once=False),
        Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player()),
                                  ('PLAYER_SET_MONEY', m.player(), 20000)]),
        Script('Test - produce', [('COUNTER', 'E173Frame', 2, 30)], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('airport').name,
             'Command_ConstructAlliedFighterAircraft')]),
        Script('Test - reference', [('COUNTER', 'E173Frame', 2, 240)], [
            ('TEAM_SET_PLAYERS_NEAREST_UNIT_OF_TYPE_TO_REFERENCE', m.role('plane').template,
             m.team(), plane)]),
        Script('Test - depart', [('COUNTER', 'E173Frame', 2, 270)], [
            ('MOVE_NAMED_UNIT_TO', plane, m.mark('sortie'))]),
        Script('Test - return', [('COUNTER', 'E173Frame', 2, 420)], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', plane, m.facts['return'])])]
    return m


def check(m, corrected=False):
    if corrected:
        # A retail id needs the replacement path, not merely EXTRA_OWN. Keep
        # a intact as the actually measured (invalid removal) diagnostic.
        unit = m.units[0]
        m.assets.append((unit.id + '.xml', unit.xml, 'GameObject:AlliedFighterAircraft'))
        m.replaces.append('GameObject:AlliedFighterAircraft')
    t = Test()
    plane = m.role('plane').name
    t.areas['E173 Airport'] = square(*m.site(m.role('airport').site), 250)
    t.areas['E173 Sortie'] = square(*m.point('sortie'), 180)
    t.counters = [('E173Frame', '完成帧'), ('E173Depart', '出发位'),
                  ('E173Final', '结束位'), ('E173Cast', '施放数')]
    t.scripts = [
        Script('Test - cast', [('PLAYER_TRIGGERED_SPECIAL_POWER', m.player(), m.facts['power'])],
               [('INCREMENT_COUNTER', 1, 'E173Cast')], once=False)]
    for name, frame, counter, bit, condition in [
        ('initial live', 255, 'E173Depart', 1, ('NAMED_NOT_DESTROYED', plane)),
        ('initial near', 255, 'E173Depart', 2, ('NAMED_INSIDE_AREA', plane, 'E173 Airport')),
        ('departure far', 405, 'E173Depart', 4, ('NAMED_INSIDE_AREA', plane, 'E173 Sortie')),
        ('final live', 660, 'E173Final', 1, ('NAMED_NOT_DESTROYED', plane)),
        ('final near', 660, 'E173Final', 2, ('NAMED_INSIDE_AREA', plane, 'E173 Airport')),
        ('final far', 660, 'E173Final', 4, ('NAMED_INSIDE_AREA', plane, 'E173 Sortie'))]:
        t.scripts.append(Script('Test - ' + name, [('COUNTER', 'E173Frame', 2, frame), condition],
                                [('INCREMENT_COUNTER', bit, counter)]))
    for label, condition, bit in [
        ('boost', ('UNIT_HAS_MODELCONDITION', plane, 'USER_1'), 8),
        ('dock', ('UNIT_HAS_OBJECT_STATUS', plane, 'DOCKING'), 16)]:
        t.scripts.append(Script('Test - ' + label, [('COUNTER', 'E173Frame', 3, 419),
                                                 ('COUNTER', 'E173Frame', 0, 660), condition],
                               [('INCREMENT_COUNTER', bit, 'E173Final')]))
    t.expect = [('完成帧', 0, 'ever==', 660), ('出发位', 0, 'ever==', 7),
                ('结束位', 0, 'ever==', 11 if m.facts['enabled'] else 5),
                ('施放数', 0, 'ever==', int(m.facts['enabled']))]
    t.bench = [('bench_watch', dict(seconds=80, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_returnon_e': mission, 'engine_returnoff_e': lambda: mission(False)}
CHECKS = {name: {'a': check, 'b': lambda m: check(m, corrected=True)} for name in MISSION}
CONTROLS = {'engine_returnoff_e': 'engine_returnon_e'}
