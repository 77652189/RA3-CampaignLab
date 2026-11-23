"""E183: refinery front placement exclusion, native shape versus module removal.

SDK RestrictedAreaShape is a box (30,45) centered 90 ahead of the refinery.
A power plant centered 120 ahead clears the refinery's base box (60,45)
but overlaps the reserved box: predict no placement on, one placement off.
Only this fixed geometry is probed; placement acceptance/rejection reasons,
rotation and exact edge rules remain gaps.
MEASURED (11-16, a): zero plants in both -- the plant's GameDependency wants the retail yard (not the clone).
11-23, b: with that dropped the plant is paid, but both previews are red alike: the ore node's own no-build
(ProjectedBuildabilityInfo 120 x 105, refineries excepted) covers 60..300 ahead of a refinery 180 from it, the
reserved box inside it: this geometry cannot tell the module. Next (not run): the refinery 200 further back (380
from the node; platmap's ore lint then wants a node within 250, e.g. one behind it) and the plant 140 ahead:
it laps 33 into the reserved box, ~27 clear of the refinery and the node's no-build (box test).
See work/re/e183_structureplace.md.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted, square
from checks.engine_modulebatch import native

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
    # the plant's GameDependency wants the retail yard, not this clone (a's two runs could not queue it): dropped
    plant = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedPowerPlant.xml').read_text(encoding='utf-8-sig')
    plant, n = re.subn(r'<GameDependency>.*?</GameDependency>', '', plant, flags=re.S)
    assert n == 1
    m = Mission(name='CampSp' + ('On' if enabled else 'Off'), map=probe_range,
                units=[refinery, yard, Unit('AlliedPowerPlant', plant)])
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


def exact(m):
    """b: a with the camera put on the click by the mission (MOVE_CAMERA_TO at 1 s + bench_view, as E169's assistp b:
    bench_camera's minimap click is off by ~100), every click looked at, and a 40 s wait for the 10 s plant in place of
    the 9200 sentinel the miner's income (+250 a trip) keeps money above: a paid 800 shows as money off the 250 grid."""
    t = check(m)
    from checks import engine_scripts8 as s8
    t.waypoints['E183 view'] = CLICK
    s8.at(t, 'view', 1., [('MOVE_CAMERA_TO', 'E183 view', 0.5, 0.0, 1.0, 1.0)])
    # off: a plant in front some time (when is the bench's queue); on: none ever
    t.expect = [('前方电厂', 0, 'ever==', 1)] if not m.facts['enabled'] else [('电厂总数', 0, '==', 0)]
    t.bench = [(name, dict(kw, look=True) if name == 'bench_click' else kw) for name, kw in t.bench]
    t.bench[1] = ('bench_view', dict(x=CLICK[0], y=CLICK[1], look=True))
    t.bench[5] = ('bench_watch', dict(t.bench[5][1], seconds=40, until=''))
    return t


MISSION = {'structpon': lambda: mission(True), 'structpoff': lambda: mission(False)}
CHECKS = {name: {'a': check, 'b': exact} for name in MISSION}
CONTROLS = {'structpoff': 'structpon'}
