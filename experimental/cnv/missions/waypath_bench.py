"""Engine probe for the waypoint paths (*_FOLLOW_WAYPOINTS; checks/engine_waypath.py; work/re/handoff.md round 143):
three convoy trucks in the west field, the ground spots/scripts1 drove on (spots_bench.py).

Island map, offsets from 'west field': truck 1-3 (units/convoy.truck, speed 50, the player's) at (-50, -150) /
(-50, 0) / (-50, 150), facing east, truck 1 alone on crew W1, 2 and 3 on crew W23; marks A (+150, -150), B (+450,
-150), C (+450, +150) -- an L the paths run along (the checks label them: the paths are each check's own) -- and N
(+420, -40), by B, where truck 1 is first sent to join a path there.
Published (the cast): truck 1-3; marks A, B, C, N; teams W1, W23.
"""
from maps import island
from parts import Mission
from units import convoy

START_X = -50.0
ROWS = (-150.0, 0.0, 150.0)
MARKS = {'A': (150.0, -150.0), 'B': (450.0, -150.0), 'C': (450.0, 150.0), 'N': (420.0, -40.0)}


def mission(name='CampPath'):              # + the check's name: 15 characters at most ('CampPathExact')
    u = convoy.truck(speed=50.0)
    m = Mission(name=name, map=island, units=[u])
    for k, dy in enumerate(ROWS, 1):
        m.put(u.id, 'west field', START_X, dy, angle=0.0, name=f'UNIT - CNV Waypath Truck {k}', role=f'truck {k}',
              props={'originalOwner': m.crew('W1' if k == 1 else 'W23')})
    for part, (dx, dy) in MARKS.items():
        m.waypoint(part, f'CNV Waypath {part}', 'west field', dx, dy)
    return m


MISSION = {'engine_waypath': mission}
