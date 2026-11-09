"""Engine probe for sim.HOLD_SPOTS (checks/engine_spots.py; work/re/handoff.md round 113): three convoy trucks, each
on a team of its own (a4's staggered convoy, 分批: devices/convoy.py), sent to one waypoint -- do they stand apart?

Island map, west field (offsets from 'west field'): truck 1-3 (units/convoy.truck, speed 50, the player's) at
(-50, -150) / (-50, 0) / (-50, 150), facing east, on crews T1-T3; mark `spot` at (+500, 0), ~550 east of them
(at -250 they stood in the sea, bench 11-09: the west field's shore is east of what its site says; scripts1's tanks
drove from -50 to +600).
Published (the cast): truck 1-3; mark spot; teams T1-T3.
"""
from maps import island
from parts import Mission
from units import convoy

START_X, SPOT_X = -50.0, 500.0
ROWS = (-150.0, 0.0, 150.0)


def mission(name='CampSpots'):
    u = convoy.truck(speed=50.0)
    m = Mission(name=name, map=island, units=[u])
    for k, dy in enumerate(ROWS, 1):
        m.put(u.id, 'west field', START_X, dy, angle=0.0, name=f'UNIT - CNV Spots Truck {k}', role=f'truck {k}',
              props={'originalOwner': m.crew(f'T{k}')})
    m.waypoint('spot', 'CNV Spots Spot', 'west field', SPOT_X, 0.0)
    return m


MISSION = {'engine_spots': mission}
