"""Attack waypoint scenes (checks/engine_wayatk.py), sharing marks with the movement waypoint bench.

The player's Guardian tanks (weapon 150, vision 200) start in the west field. Tank 1 is on crew W1, 2 and 3 on W23.
The check places an enemy tank (s1) beside the A -> B leg to vary its distance.
Published (the cast): tank 1-3; marks A, B, C, N; teams W1, W23.
"""
from maps import island
from parts import Mission

START_X = -50.0
ROWS = (-150.0, 0.0, 150.0)
MARKS = {'A': (150.0, -150.0), 'B': (450.0, -150.0), 'C': (450.0, 150.0), 'N': (420.0, -40.0)}


TANK = 'AlliedAntiVehicleVehicleTech1'


def attack_mission(name='CampWayAtk', rows=ROWS):     # + the check's name: 15 characters at most ('CampWayAtkPlain')
    """rows: the tanks' start rows (engine_wayatk2: tank 3 at +450, its team spot far beyond any scan of F)."""
    m = Mission(name=name, map=island, units=[], facts={})
    m.spawns |= {TANK}
    for k, dy in enumerate(rows, 1):
        m.put(TANK, 'west field', START_X, dy, angle=0.0, name=f'UNIT - CNV Wayatk Tank {k}', role=f'tank {k}',
              props={'originalOwner': m.crew('W1' if k == 1 else 'W23')})
    for part, (dx, dy) in MARKS.items():
        m.waypoint(part, f'CNV Wayatk {part}', 'west field', dx, dy)
    return m


MISSION = {'engine_wayatk': attack_mission,
           'engine_wayatk2': lambda: attack_mission('CampWayAtk2', rows=(-150.0, 0.0, 450.0)),
           'engine_wayatk3': lambda: attack_mission('CampWayAtk3', rows=(600.0, 0.0, 300.0))}
