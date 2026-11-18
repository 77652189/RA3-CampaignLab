"""Engine unit tests, R3 step X (ADR 0032 5: the pathing details re-derived on the bench): where a group of infantry
stops when it is sent to one point as one team -- the simulator's Sim.column_ends (the ends of an infantry group's
move: in which rows and files the men stand round the point). Every man is a copy of the Peacekeeper with ra3ext's
read-only CNVProbe (a `probe` line per frame it moved: its last line is where it stopped), on the blocked-way probe
map's open ground (maps/probe_block.py).

What decides the rule (each lane one team, one MOVE_TEAM_TO, the men standing in a block facing the point):
  - how many files across and rows back, against the number of men (3, 6, 10, 16);
  - the spacing across and back; where the front row stands against the point (on it, short of it, centred on it);
  - whether the block is turned with the way in (west / north / south-west) or kept on the world's axes;
  - whether a short move (the front man 70 from the point) makes a block at all;
  - the snap to the 20-unit grid (the north lane's point is off it).

  engine_column lanes   w6 six from the west (2 across, 3 deep), the point (3000, 2000)
                        n6 six from the north, the point (3013, 3007): off the grid
                        w3 three from the west (1 across), the point (3000, 4500)
                        near six from the west, the front man 70 short of the point (3000, 1600)
                        d6 six from the south-west (the way in at 45 degrees), the point (4300, 2000)
  engine_crowd big      w16 sixteen from the west (4 across, 4 deep), the point (3000, 2400)
                        n10 ten from the north (2 across, 5 deep), the point (3600, 3000)
  engine_colgate two    w2 two from the west, one behind the other, the point (3000, 2000)
                        w2s two from the west side by side, the point (3000, 2400)
                        close six from the west, the front man 20 short of the point (3000, 1600)
                        scat six from the west standing anyhow (SCATTER: no two level or abreast), the point (3000, 4500)

No expectations: the readings are the probe lines (work/re/scripts/x_column.py reads them against the simulator's
stops).
"""
import math
import os

import labpaths
from maps import probe_block
from parts import Mission, Script, Test, Unit

MAN = 'AlliedAntiInfantryInfantry'
PROBE = 'CNV_ColMan'
EVERY, LINES = 150, 6000
SPACE = 30.0                     # the start block's spacing, across and back
SCATTER = ((0, -8), (13, 41), (37, -47), (52, 17), (71, -21), (96, 55))   # (back, left): no two alike either way
# build: (mission name, {lane: (the point, the front man's start, men, across)}); the block stands behind the front
# man away from the point, `across` men a row, rows SPACE back
BUILDS = {
    'engine_column': ('CampCols', {
        'w6': ((3000.0, 2000.0), (2500.0, 2000.0), 6, 2),
        'n6': ((3013.0, 3007.0), (3013.0, 3507.0), 6, 2),
        'w3': ((3000.0, 4500.0), (2500.0, 4500.0), 3, 1),
        'near': ((3000.0, 1600.0), (2930.0, 1600.0), 6, 2),
        'd6': ((4300.0, 2000.0), (3946.4, 1646.4), 6, 2),
    }),
    'engine_crowd': ('CampCrowd', {
        'w16': ((3000.0, 2400.0), (2450.0, 2400.0), 16, 4),
        'n10': ((3600.0, 3000.0), (3600.0, 3500.0), 10, 2),
    }),
    'engine_colgate': ('CampColGate', {
        'w2': ((3000.0, 2000.0), (2500.0, 2000.0), 2, 1),
        'w2s': ((3000.0, 2400.0), (2500.0, 2400.0), 2, 2),
        'close': ((3000.0, 1600.0), (2980.0, 1600.0), 6, 2),
        'scat': ((3000.0, 4500.0), (2500.0, 4500.0), 6, SCATTER),
    }),
}
RUN = 30.0


def watch(build):
    """Wall seconds to watch: ~20-26 probes slow the game to ~3-4 frames a second (bench 11-17 engine_drop)."""
    return RUN * 15.0 / 3.0


def starts(build, lane):
    """Each man's start in `lane`: rows from the front, across left to right as seen walking in."""
    (px, py), (fx, fy), count, across = BUILDS[build][1][lane]
    ax, ay = px - fx, py - fy
    n = math.hypot(ax, ay)
    ux, uy = ax / n, ay / n                    # the way in; left = (-uy, ux)
    if isinstance(across, tuple):
        spots = across
    else:
        spots = [(SPACE * (k // across), (k % across - (across - 1) / 2) * SPACE) for k in range(count)]
    return [(fx - ux * back - uy * side, fy - uy * back + ux * side) for back, side in spots]


def probe_copy():
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', MAN + '.xml'), encoding='utf-8') as f:
        x = f.read()
    assert x.count(f'id="{MAN}"') == 1 and x.count('<Behaviors>') == 1
    x = x.replace(f'id="{MAN}"', f'id="{PROBE}"', 1).replace(f'EditorName="{MAN}"', f'EditorName="{PROBE}"')
    x = x.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>''', 1)
    return Unit(PROBE, x, names=dict(unit=PROBE), what=f'原版 {MAN} 的复制（探针）：多一个 ra3ext 的 CNVProbe，逐帧记位置',
                params=dict(of=MAN, every=EVERY, lines=LINES))


def key(lane, k):
    """The man's name is `UNIT - CNV Col <key>`."""
    return f'{lane.title()}M{k + 1}'


def _mission(build):
    name, lanes = BUILDS[build]
    m = Mission(name=name, map=probe_block, units=[probe_copy()], facts={})
    m.ext = True
    sx, sy = m.site('island')
    for lane, ((px, py), _, _, _) in lanes.items():
        for k, (x, y) in enumerate(starts(build, lane)):
            m.put(PROBE, 'island', x - sx, y - sy, role=f'{lane} {k + 1}', name=f'UNIT - CNV Col {key(lane, k)}',
                  angle=math.atan2(py - y, px - x))
    return m


def _check(build):
    def check(m):
        _, lanes = BUILDS[build]
        t = Test()
        go = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane, (point, _, count, _) in lanes.items():
            wp = f'Test Col {lane.title()} Point'
            t.waypoints[wp] = point
            go += m.order('move', [m.role(f'{lane} {k + 1}').name for k in range(count)], wp,
                          crew=f'Col{lane.title()}')
        t.scripts.append(Script('Test - go', [], go))
        t.bench = [('bench_watch', dict(seconds=watch(build), every=20, sheet=False, lines=2))]
        t.expect = []
        return t
    return check


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {b: (lambda b=b: _mission(b)) for b in BUILDS}
CHECKS = {'engine_column': {'lanes': _check('engine_column')}, 'engine_crowd': {'big': _check('engine_crowd')},
          'engine_colgate': {'two': _check('engine_colgate')}}
