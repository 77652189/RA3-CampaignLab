"""Engine unit tests, R3 step X (ADR 0032 5: the pathing details re-derived on the bench): where a unit stops when the
point it is sent to is already someone's -- the simulator's Sim.free_spot (a move's goal kept off the spots other
units hold, Sim.claims). Every unit is a copy with ra3ext's read-only CNVProbe (a `probe` line per frame it moved: its
last line is where it stopped), on the blocked-way probe map's open ground (maps/probe_block.py).

Each lane is a column of units of one kind behind a start, sent one at a time (STAGGER apart, each on its own; every
one before it has arrived) to the lane's point. Read: each unit's stop -- the first on the point? the next ones how far
off (a radius sum? cells?), in which direction (the world's axes, or turned with the way it came), in what order round
the point; tanks against men (the distance with the size).

  engine_drop lanes      six of each:
            west   Guardian tanks from the west (column along y 2000, the point (3000, 2000))
            north  Guardian tanks from the north (column along x 3013, the point (3013, 3007): off the 20-unit grid)
            man    Peacekeepers from the west (column along y 4500, the point (3000, 4500))
  engine_dropring tens   ten of each, the order further round:
            tank   Guardian tanks from the west (the point (3000, 1600))
            man    Peacekeepers from the south (the point (3600, 2800))

Each unit is put down facing the point. No expectations: the readings are the probe lines (work/re/scripts/x_drop.py
reads them against the simulator's stops).
"""
import math
import os

import labpaths
from maps import probe_block
from parts import Mission, Script, Test, Unit

TANK, MAN = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
PROBE = {TANK: 'CNV_DropTank', MAN: 'CNV_DropMan'}
EVERY, LINES = 150, 6000
STAGGER = 15.0
# build: (mission name, units a lane, {lane: (template, the point, the first start, the column's step back)})
BUILDS = {
    'engine_drop': ('CampDrop', 6, {
        'west': (TANK, (3000.0, 2000.0), (2500.0, 2000.0), (-100.0, 0.0)),
        'north': (TANK, (3013.0, 3007.0), (3013.0, 3507.0), (0.0, 100.0)),
        'man': (MAN, (3000.0, 4500.0), (2500.0, 4500.0), (-60.0, 0.0)),
    }),
    'engine_dropring': ('CampRing', 10, {
        'tank': (TANK, (3000.0, 1600.0), (2500.0, 1600.0), (-60.0, 0.0)),
        'man': (MAN, (3600.0, 2800.0), (3600.0, 2300.0), (0.0, -30.0)),
    }),
}


def run(build):
    """Game seconds the check needs: the last order, then the last (farthest) unit's walk (a man ~50 a second)."""
    _, count, lanes = BUILDS[build]
    return 1.0 + STAGGER * (count - 1) + 25.0


def watch(build):
    """Wall seconds to watch: ~20 probes slow the game to ~4 frames a second, 15 a game second (bench 11-17: a first
    run watched game seconds on the wall clock and stopped at frame 450, before the third unit's order)."""
    return run(build) * 15.0 / 3.8


def starts(build, lane):
    """Each unit's start in `lane`, the first (sent first) nearest the point."""
    _, count, lanes = BUILDS[build]
    _, _, (x, y), (dx, dy) = lanes[lane]
    return [(x + dx * k, y + dy * k) for k in range(count)]


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


def _role(lane, k):
    return f'{lane} {k + 1}'


def key(lane, k):
    """The unit's name is `UNIT - CNV Drop <key>`."""
    return f'{lane.title()}{k + 1}'


def _mission(build):
    name, _, lanes = BUILDS[build]
    m = Mission(name=name, map=probe_block, units=[probe_copy(TANK), probe_copy(MAN)], facts={})
    m.ext = True
    sx, sy = m.site('island')
    for lane, (tpl, (px, py), _, _) in lanes.items():
        for k, (x, y) in enumerate(starts(build, lane)):
            m.put(PROBE[tpl], 'island', x - sx, y - sy, role=_role(lane, k), name=f'UNIT - CNV Drop {key(lane, k)}',
                  angle=math.atan2(py - y, px - x))
    return m


def _check(build):
    def check(m):
        _, count, lanes = BUILDS[build]
        t = Test()
        first = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
        for lane, (_, point, _, _) in lanes.items():
            wp = f'Test Drop {lane.title()} Point'
            t.waypoints[wp] = point
            for k in range(count):
                go = m.order('move', [m.role(_role(lane, k)).name], wp, crew=f'Drop{key(lane, k)}')
                timer = f'Test Drop {key(lane, k)}'
                first.append(('SET_MILLISECOND_TIMER', timer, 1.0 + STAGGER * k))
                t.scripts.append(Script(f'Test - go {_role(lane, k)}', [('TIMER_EXPIRED', timer)], go))
        t.scripts.insert(0, Script('Test - go', [], first))
        t.bench = [('bench_watch', dict(seconds=watch(build), every=20, sheet=False, lines=2))]
        t.expect = []
        return t
    return check


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {b: (lambda b=b: _mission(b)) for b in BUILDS}
CHECKS = {'engine_drop': {'lanes': _check('engine_drop')}, 'engine_dropring': {'tens': _check('engine_dropring')}}
