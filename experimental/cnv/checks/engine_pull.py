"""Engine unit tests, R3 step X (ADR 0032 5: the pathing details re-derived on the bench): how straight a ground way
runs -- the simulator's Ground.pull (from each anchor straight to the farthest cell it sees). Every unit is a copy with
ra3ext's read-only CNVProbe (a `probe` line per frame it moved: its trajectory), on the blocked-way probe map
(maps/probe_block.py, the simulator reads the same map: ground() / impassable()).

  round   the 'bits' box: a Guardian tank from the start, 250 south of a field-0 wall (x 300..900, y 780..820), sent to
          the goal 250 north of it; the one way round is the gap at the box's east end (x 900..1100). 20 s later a
          Peacekeeper from 60 west of the start, sent to the same goal (the tank is there by then, past the corner).
          Read: the leg start -> wall's east end (its largest step off the straight line), how near the corner
          (900, 780 / 820) it passes, the leg corner -> goal.
  slant   open ground east of the seal lanes: a Guardian from (3900, 1550) sent 800 east and 300 north; a Peacekeeper
          the same 400 further north. Read: the largest step off the straight line.

Each unit is put down facing its first leg (no turn on the spot to read past). No expectations: the readings are the
probe lines (work/re/scripts/x_pull.py reads them against the simulator's ways).
"""
import math
import os

import labpaths
from maps import probe_block
from parts import Mission, Script, Test, Unit

TANK, MAN = 'AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
PROBE = {TANK: 'CNV_PullTank', MAN: 'CNV_PullMan'}
EVERY, LINES = 150, 6000
CORNER = (900.0, 780.0)                   # the wall's east end, start side
SLANT = (800.0, 300.0)
# role: (template, start, goal, the order's delay in seconds)
LANES = {
    'round tank': (TANK, (500.0, 550.0), (500.0, 1050.0), 0.0),
    'round man': (MAN, (440.0, 550.0), (500.0, 1050.0), 20.0),
    'slant tank': (TANK, (3900.0, 1550.0), (3900.0 + SLANT[0], 1550.0 + SLANT[1]), 0.0),
    'slant man': (MAN, (3900.0, 1950.0), (3900.0 + SLANT[0], 1950.0 + SLANT[1]), 0.0),
}
RUN = 50.0


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


def _key(role):
    return role.title().replace(' ', '')


def _first_leg(role):
    _, (x, y), goal, _ = LANES[role]
    tx, ty = CORNER if role.startswith('round') else goal
    return math.atan2(ty - y, tx - x)


def mission():
    m = Mission(name='CampPull', map=probe_block, units=[probe_copy(TANK), probe_copy(MAN)], facts={})
    m.ext = True
    for role, (tpl, (x, y), _, _) in LANES.items():
        sx, sy = m.site('bits start') if role.startswith('round') else m.site('seal move')
        m.put(PROBE[tpl], 'bits start' if role.startswith('round') else 'seal move', x - sx, y - sy, role=role,
              name=f'UNIT - CNV Pull {_key(role)}', angle=_first_leg(role))
    return m


def ways(m):
    t = Test()
    first = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for role, (_, _, goal, delay) in LANES.items():
        wp = f'Test Pull {_key(role)} Goal'
        t.waypoints[wp] = goal
        go = m.order('move', [m.role(role).name], wp, crew=f'Pull{_key(role)}')
        if delay:
            timer = f'Test Pull {_key(role)}'
            first.append(('SET_MILLISECOND_TIMER', timer, delay))
            t.scripts.append(Script(f'Test - go {role}', [('TIMER_EXPIRED', timer)], go))
        else:
            first += go
    t.scripts.insert(0, Script('Test - go', [], first))
    t.bench = [('bench_watch', dict(seconds=RUN, every=5, sheet=False, lines=2))]
    t.expect = []
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_pull': mission}
CHECKS = {'engine_pull': {'ways': ways}}
