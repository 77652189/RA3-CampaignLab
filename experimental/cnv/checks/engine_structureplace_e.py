"""E183: refinery front placement exclusion, native shape versus module removal.

SDK RestrictedAreaShape is a box (30,45) centered 90 ahead of the refinery.
A power plant centered 120 ahead clears the refinery's base box (60,45)
but overlaps the reserved box: predict no placement on, one placement off.
Only this fixed geometry is probed; placement acceptance/rejection reasons,
rotation and exact edge rules remain gaps.
MEASURED: both runs produced zero plants, with money rising from 10000
through mining rather than reaching the predicted 9200 payment sentinel.
Queue/placement acceptance was not established; original predictions remain. See work/re/e183_structureplace.md.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted, square
from checks.engine_modulebatch import native

PAD = (3000.0, 4200.0)
CLICK = (3084.852814, 4284.852814)
INCLUDE = r'<xi:include\s+href="DATA:Includes/GenericRefineryStructurePlacementBehavior.xml"\s*/>'


def mission(enabled=True):
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedRefinery.xml').read_text(encoding='utf-8-sig')
    if not enabled:
        xml, n = re.subn(INCLUDE, '', xml)
        assert n == 1
    refinery = Unit('AlliedRefinery', xml)
    yard = native('AlliedConstructionYard', 'Structures', 'CNVE183Yard')
    yard.xml = yard.xml.replace('="=2.0s"', '="2.0s"')
    yard.xml = yard.xml.replace('CommandSet="AlliedConstructionYardCommandSet"', 'CommandSet="CNVE183Menu"')
    yard.xml = yard.xml.replace('</AssetDeclaration>', '<LogicCommandSet id="CNVE183Menu"><Cmd>Command_ConstructAlliedPowerPlant</Cmd></LogicCommandSet></AssetDeclaration>')
    yard.link += ['LogicCommandSet:CNVE183Menu']
    m = Mission(name='CampSp' + ('On' if enabled else 'Off'), map=probe_range, units=[refinery, yard])
    m.facts['enabled'] = enabled
    m.spawns.add('AlliedPowerPlant')
    m.put(refinery.id, 'probe refinery', angle=0.7853981633974483, role='refinery', name='E183 Refinery')
    m.put(yard.id, 'probe refinery', 0, -260, role='yard', name='E183 Yard')
    return m


def check(m):
    t = Test()
    p1 = m.player('p1')
    t.counters = [('E183Age', '采样帧'), ('E183Money', '资金')]
    t.scripts = [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 10000)]),
                 Script('Test - age', [], [('INCREMENT_COUNTER', 1, 'E183Age')], once=False),
                 Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'E183Money')], once=False)]
    t.areas['E183 Front'] = square(*CLICK, 12)
    counted('E183Total', '电厂总数', t, template='AlliedPowerPlant', player=p1)
    counted('E183Front', '前方电厂', t, template='AlliedPowerPlant', player=p1, area='E183 Front', most=2)
    expected = int(not m.facts['enabled'])
    t.expect = [('资金', 0, 'ever==', 9200), ('电厂总数', 20, '==', expected),
                ('前方电厂', 20, '==', expected)]
    watch = dict(every=1, sheet=False, lines=4)
    button = ('bench_click', dict(x=1137, y=323, world=False, look=False))
    t.bench = [('bench_start', dict(hold=False)),
               ('bench_camera', dict(x=CLICK[0], y=CLICK[1], look=False)),
               ('bench_click', dict(x=1120, y=252, world=False, look=False)),
               ('bench_click', dict(x=1120, y=252, world=False, look=False)), button,
               ('bench_watch', dict(watch, seconds=100, until='c2<=9200')), button,
               ('bench_watch', dict(watch, seconds=0.5)),
               ('bench_click', dict(x=CLICK[0], y=CLICK[1], look=False)),
               ('bench_watch', dict(watch, seconds=40))]
    return t


MISSION = {'structpon': lambda: mission(True), 'structpoff': lambda: mission(False)}
CHECKS = {name: {'a': check} for name in MISSION}
