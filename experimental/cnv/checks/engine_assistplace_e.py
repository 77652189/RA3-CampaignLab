"""E169: legal refinery placement, retail placement hint versus hint removal.

Prediction from GenericRefineryPlacementHint.xml: a click 30 units from the
ore's suggested refinery pad snaps to that pad with AssistedPlacementBehavior
(SnappingDistance=50); without it the click stays offset. Both must produce
one refinery. Region counts test this prediction; they do not certify facing,
shroud eligibility, the exact snap radius or rejected-placement reasons.
See work/re/e169_assistplace.md for observations and remaining gaps.
MEASURED: both original and module-removal runs paid the queue (8000 left),
but produced zero refineries and left the completion sentinel at zero.
Both previews remained red. The original predictions below are retained;
this recipe has not established a legal placement or a snapping rule.
b (11-23, the camera put by the mission): the click is accepted; on puts the refinery within 20 of the pad turned
to the node, off (same click) by the click in its default facing -- snapping seen; the sim replays no clicks.
"""
import re
import types
from pathlib import Path

import labpaths
import resources
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted, square
from checks.engine_modulebatch import native

PAD = (3000.0, 4200.0)
CLICK = (3030.0, 4200.0)


def mission(enabled=True):
    mp = types.ModuleType(probe_range.__name__)
    mp.__dict__.update(vars(probe_range))
    mp.OBJECTS = resources.objects(probe_range.FIELDS)
    mp.NODES = resources.RETAIL
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedRefinery.xml').read_text(encoding='utf-8-sig')
    if not enabled:
        xml, n = re.subn(r'<xi:include\s+href="DATA:Includes/GenericRefineryPlacementHint.xml"\s*/>', '', xml)
        assert n == 1
    refinery = Unit('AlliedRefinery', xml)
    yard = native('AlliedConstructionYard', 'Structures', 'CNVE169Yard')
    # native() expands the local time constant; a literal duration is not an expression.
    yard.xml = yard.xml.replace('="=2.0s"', '="2.0s"')
    yard.xml = yard.xml.replace('CommandSet="AlliedConstructionYardCommandSet"', 'CommandSet="CNVE169Menu"')
    yard.xml = yard.xml.replace('</AssetDeclaration>', '''
        <LogicCommandSet id="CNVE169Menu"><Cmd>Command_ConstructAlliedRefinery</Cmd></LogicCommandSet>
        </AssetDeclaration>''')
    yard.link += ['LogicCommandSet:CNVE169Menu']
    m = Mission(name='CampAsst' + ('On' if enabled else 'Off'), map=mp, units=[refinery, yard])
    m.facts['enabled'] = enabled
    m.spawns.add('AlliedRefinery')
    m.put(yard.id, 'probe refinery', -280, -260, role='yard', name='E169 Yard')
    m.put('AlliedPowerPlant', 'probe refinery', -480, -260, role='power', name='E169 Power')
    return m


def check(m):
    t = Test()
    p1 = m.player('p1')
    t.counters = [('E169Age', '采样完成'), ('E169Money', '资金')]
    t.scripts = [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 10000)]),
                 Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'E169Money')], once=False)]
    t.areas['E169 Snap'] = square(*PAD, 8)
    counted('E169Total', '矿场总数', t, template='AlliedRefinery', player=p1)
    counted('E169Snap', '提示位数量', t, template='AlliedRefinery', area='E169 Snap', player=p1, most=2)
    # Freeze both region and total readings after 90 script frames with a refinery.
    for script in t.scripts[2:]:
        script.when.append(('COUNTER', 'E169Age', 0, 90))
    t.scripts.append(Script('Test - age', [('COUNTER', 'E169Total', 3, 1), ('COUNTER', 'E169Age', 0, 90)],
                            [('INCREMENT_COUNTER', 1, 'E169Age')], once=False))
    t.expect = [('采样完成', 0, 'ever==', 90), ('矿场总数', 0, 'ever==', 1),
                ('提示位数量', 0, 'ever==', int(m.facts['enabled']))]
    watch = dict(every=1, sheet=False, lines=4)
    button = ('bench_click', dict(x=1137, y=323, world=False, look=False))
    t.bench = [('bench_start', dict(hold=False)),
               ('bench_camera', dict(x=PAD[0], y=PAD[1], look=False)),
               ('bench_click', dict(x=1120, y=252, world=False, look=False)),
               ('bench_click', dict(x=1120, y=252, world=False, look=False)), button,
               ('bench_watch', dict(watch, seconds=110, until='c2<=8000')), button,
               ('bench_click', dict(x=CLICK[0], y=CLICK[1], look=False)),
               ('bench_watch', dict(watch, seconds=100))]
    return t


def exact(m):
    """b: a with the camera put on the pad by the mission (MOVE_CAMERA_TO at 1 s + bench_view: bench_camera's minimap
    click is off by ~100, twice the snap distance), every click looked at, and a second click 330 from the yard (its +y)
    -- a spot near the yard and far from the node -- for when the pad's leaves the cursor up: is the pad itself red?"""
    t = check(m)
    # where it stands, near the pad (20) or at the click (8), in place of the age and the pad's 8 (four lines fit)
    t.counters = [c for c in t.counters if c[0] not in ('E169Age', 'E169Snap')]
    t.areas.update({'E169 Near': square(*PAD, 20), 'E169 Click': square(*CLICK, 8)})
    counted('E169Near', '提示位20内', t, template='AlliedRefinery', area='E169 Near', player=m.player('p1'), most=2)
    counted('E169Click', '点击处数量', t, template='AlliedRefinery', area='E169 Click', player=m.player('p1'), most=2)
    on = int(m.facts['enabled'])
    t.expect = [('矿场总数', 0, 'ever==', 1), ('提示位20内', 0, 'ever==', on), ('点击处数量', 0, 'ever==', 1 - on)]
    from checks import engine_scripts8 as s8
    t.waypoints['E169 view'] = PAD
    s8.at(t, 'view', 1., [('MOVE_CAMERA_TO', 'E169 view', 0.5, 0.0, 1.0, 1.0)])
    x, y = m.site('probe refinery')
    # money is the first line now (the age left out): the sentinel reads c1
    steps = [(name, dict(kw, look=True) if name == 'bench_click' else
              dict(kw, until=kw.get('until', '').replace('c2', 'c1')) if name == 'bench_watch' else kw)
             for name, kw in t.bench]
    steps[1] = ('bench_view', dict(x=PAD[0], y=PAD[1], look=True))
    t.bench = steps[:-1] + [('bench_watch', dict(steps[-1][1], seconds=5)),
                            ('bench_click', dict(x=x - 280, y=y + 70, look=True)), steps[-1]]
    return t


MISSION = {'assistpon': lambda: mission(True), 'assistpoff': lambda: mission(False)}
CHECKS = {name: {'a': check, 'b': exact} for name in MISSION}
CONTROLS = {'assistpoff': 'assistpon'}
