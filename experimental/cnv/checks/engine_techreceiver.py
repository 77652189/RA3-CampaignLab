"""E167: retail Tech2 receiver versus deletion of only its Level2 include.

Two isolated players each own one yard and one retail war factory. Near is
300 away, far 750 (retail radius 600). At f90 give only each yard Tech2.
Prediction at f180: near player has two holders with receiver, one without;
far player has one in either build. At f210 delete both yards; f300 predicts
zero holders with both factories alive. f60 freezes the zero-upgrade baseline.
Counts include the source explicitly; they do not identify individual holders.
No production, radius boundary, rectangular corner or exact update-clock claim.
MEASURED on/off: both complete f330, baseline/grant/removed=15/15/15.
Thus f180 holders are near 2/1, far 1/1; f300 both zero with factories alive.
Original evidence: work/re/e167_techreceiver.md and on/off JSON.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, NOT

UP = 'Upgrade_AlliedTech2'


def mission(enabled=True):
    m = Mission(name='CampTechRecv' if enabled else 'CampTechRcvOff', map=probe_range,
                units=[], facts={'receiver': enabled})
    if not enabled:
        xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedWarFactory.xml').read_text(
            encoding='utf-8-sig')
        xml, n = re.subn(r'<xi:include\s+href="DATA:Includes/AlliedTechUpgradeReceiverLevel2.xml"\s*/>',
                         '', xml)
        assert n == 1
        m.assets.append(('E167Factory.xml', xml, 'GameObject:AlliedWarFactory'))
        m.replaces.append('GameObject:AlliedWarFactory')
    for tag, side, site, distance in [('near', 'p1', 'base gun', 300),
                                       ('far', 's1', 'removed gun', 750)]:
        m.put('AlliedConstructionYard', site, side=side, role=tag + 'yard', name='E167 ' + tag + ' yard')
        m.put('AlliedWarFactory', site, distance, 0, side=side,
              role=tag + 'factory', name='E167 ' + tag + ' factory')
        m.put('AlliedPowerPlant', site, 0, 400, side=side, role=tag + 'power')
    m.spawns.add('AlliedWarFactoryRepairDrone')
    return m


def check(m):
    t = Test()
    t.counters = [('E167Frame', 'frame'), ('E167Base', 'baseline'),
                  ('E167Grant', 'grant'), ('E167Gone', 'removed')]
    t.scripts = [Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
        Script('Test - frame', [('COUNTER', 'E167Frame', 0, 330)],
               [('INCREMENT_COUNTER', 1, 'E167Frame')], once=False),
        Script('Test - grant', [('COUNTER', 'E167Frame', 2, 90)],
               [('NAMED_RECEIVE_UPGRADE', UP, m.role(tag + 'yard').name) for tag in ('near', 'far')]),
        Script('Test - delete sources', [('COUNTER', 'E167Frame', 2, 210)],
               [('NAMED_DELETE', m.role(tag + 'yard').name) for tag in ('near', 'far')])]
    for frame, counter, counts in [(60, 'E167Base', (0, 0)),
            (180, 'E167Grant', (2 if m.facts['receiver'] else 1, 1)),
            (300, 'E167Gone', (0, 0))]:
        at = [('COUNTER', 'E167Frame', 2, frame)]
        for bit, (side, count) in enumerate(zip(('p1', 's1'), counts)):
            conditions = [('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', m.player(side), count + 1, UP, NOT)]
            if count:
                conditions.append(('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', m.player(side), count, UP))
            t.scripts.append(Script(f'Test - count {frame} {side}', at + conditions,
                                   [('INCREMENT_COUNTER', 1 << bit, counter)]))
        t.scripts.append(Script(f'Test - factories {frame}', at + [
            ('NAMED_DESTROYED', m.role(tag + 'factory').name, NOT) for tag in ('near', 'far')],
            [('INCREMENT_COUNTER', 4, counter)]))
        t.scripts.append(Script(f'Test - sources {frame}', at + [
            ('NAMED_DESTROYED', m.role(tag + 'yard').name, *(() if frame == 300 else (NOT,)))
            for tag in ('near', 'far')], [('INCREMENT_COUNTER', 8, counter)]))
    t.expect = [(label, 0, 'ever>=', value) for label, value in
                [('frame', 330), ('baseline', 15), ('grant', 15), ('removed', 15)]]
    t.bench = [('bench_watch', dict(seconds=120, every=1, sheet=False, lines=4, until='c1>=330'))]
    return t


MISSION = {'engine_techrecvon': mission, 'engine_techrecvoff': lambda: mission(False)}
CHECKS = {name: {'a': check} for name in MISSION}
