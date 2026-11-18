"""Engine unit tests, R3 step X (ADR 0032 5): where the first Allied mission's starting squad stops when it is sent to
one point -- tests/test_retail_sim.py's question 1 (docs/story/retail-q1-a01.md), whose closest pair was ~42 read off
a screenshot (11-09, units as team-blue blobs) against 27.6 on the probe bench (engine_column d6: a turned block,
each spot snapped to its cell's centre, diagonal neighbours 20 * sqrt(2)). The bench cannot put a probe on a01 itself
(the plain game loads no mod, ra3ext only starts with one), so the squad is copied: 4 Peacekeepers and 2 dogs, each a
copy with ra3ext's read-only CNVProbe, standing as a01's squad stands when the intro hands it over (the simulator's
a01 at 22.6 s), the point as far and in the same direction, and every coordinate moved by whole 20-cells (the snap
sees the same fractions); on the blocked-way probe map's open ground (maps/probe_block.py).

  engine_a01sq squad   team   a01's squad (4 Peacekeepers, 2 dogs), one MOVE_TEAM_TO (the test's `走 队`)
                       pk6    the same spots, all six Peacekeepers: what the dogs change
                       click  a01's squad again, box-selected and right-clicked by the bench (the 11-09 order)

No expectations: the readings are the probe lines (work/re/scripts/x_a01sq.py reads them against the simulator's stops).
"""
import math
import os

import labpaths
from maps import probe_block
from parts import Mission, Script, Test, Unit

MAN, DOG = 'AlliedAntiInfantryInfantry', 'AlliedScoutInfantry'
PROBE = {MAN: 'CNV_A01Man', DOG: 'CNV_A01Dog'}
EVERY, LINES = 150, 6000
A01_POINT = (505.2, 1576.7)
# a01's squad at the hand-over (simulator, retail a01 at 22.6 s): (template, x, y)
A01_SQUAD = ((DOG, 410.0, 1630.0), (DOG, 390.0, 1670.0), (MAN, 390.0, 1610.0), (MAN, 333.3, 1669.8),
             (MAN, 323.5, 1593.6), (MAN, 303.9, 1620.5))
SHIFT = {'team': (2500.0, 420.0), 'pk6': (2500.0, 820.0), 'click': (2500.0, 1220.0)}   # whole 20-cells
RUN = 20.0


def point(lane):
    dx, dy = SHIFT[lane]
    return A01_POINT[0] + dx, A01_POINT[1] + dy


def starts(lane):
    """[(template, x, y)] of the lane's six."""
    dx, dy = SHIFT[lane]
    return [(MAN if lane == 'pk6' else tpl, x + dx, y + dy) for tpl, x, y in A01_SQUAD]


def probe_copy(template):
    pid = PROBE[template]
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', template + '.xml'), encoding='utf-8') as f:
        x = f.read()
    assert x.count(f'id="{template}"') == 1 and x.count('<Behaviors>') == 1
    x = x.replace(f'id="{template}"', f'id="{pid}"', 1).replace(f'EditorName="{template}"', f'EditorName="{pid}"')
    x = x.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>''', 1)
    return Unit(pid, x, names=dict(unit=pid), what=f'原版 {template} 的复制（探针）：多一个 ra3ext 的 CNVProbe，逐帧记位置',
                params=dict(of=template, every=EVERY, lines=LINES))


def mission():
    m = Mission(name='CampA01Sq', map=probe_block, units=[probe_copy(MAN), probe_copy(DOG)], facts={})
    m.ext = True
    sx, sy = m.site('island')
    for lane in SHIFT:
        px, py = point(lane)
        for k, (tpl, x, y) in enumerate(starts(lane)):
            m.put(PROBE[tpl], 'island', x - sx, y - sy, role=f'{lane} {k + 1}',
                  name=f'UNIT - CNV A01 {lane.title()}M{k + 1}', angle=math.atan2(py - y, px - x))
    return m


def squad(m):
    t = Test()
    go = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for lane in ('team', 'pk6'):
        wp = f'Test A01 {lane.title()} Point'
        t.waypoints[wp] = point(lane)
        go += m.order('move', [m.role(f'{lane} {k + 1}').name for k in range(len(A01_SQUAD))], wp,
                      crew=f'A01{lane.title()}')
    t.scripts.append(Script('Test - go', [], go))
    xs = [x for _, x, _ in starts('click')]
    ys = [y for _, _, y in starts('click')]
    px, py = point('click')
    t.bench = [('bench_view', dict(x=(min(xs) + px) / 2, y=(min(ys) + max(ys)) / 2, look=True)),
               ('bench_box', dict(x0=min(xs) - 25, y0=min(ys) - 25, x1=max(xs) + 25, y1=max(ys) + 25, look=True)),
               ('bench_click', dict(x=px, y=py, right=True, look=True)),
               ('bench_watch', dict(seconds=RUN * 15.0 / 3.0, every=20, sheet=False, lines=2))]
    t.expect = []
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_a01sq': mission}
CHECKS = {'engine_a01sq': {'squad': squad}}
