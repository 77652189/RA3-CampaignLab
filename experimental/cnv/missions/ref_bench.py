"""Engine probe mission: how SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER (type, player, team, ref) picks
(checks/engine_ref.py; A4's Ghost King pick, devices/horn.py ghost_scripts).

The west field (island map). A team (Mission.crew 'Ref', the player's) gets two members by script, made in order
M1 (0, -400) then M2 (0, 400) -- ref_a2 makes them the other way round. Three walls of the player's own (a ice-wall
kind with no lifetime), placed by the map:
  A (-250, -400): 250 from M1, 838 from M2, 472 from the middle   (nearest to the FIRST member)
  B (-100,  400): 100 from M2, 806 from M1, 412 from the middle   (nearest to ANY member, nearest to M2)
  C ( 150,    0): 427 from each, 150 from the middle              (nearest to the CENTRE of the team)
(offsets from 'west field'). ref_a: all three unnamed. ref_b: the nearest of the pair (B) is named, A and C unnamed
stay. ref_c: the pick is made, then asked again with a type nobody owns, again, and with the team emptied.
"""
from maps import island
from parts import Mission
from units import icewall as iw

WALL, NONE = 'CNV_RefWall', 'CNV_RefNone'
MEMBER = 'AlliedAntiVehicleVehicleTech1'
M1, M2 = (0.0, -400.0), (0.0, 400.0)
WALLS = {'A': (-250.0, -400.0), 'B': (-100.0, 400.0), 'C': (150.0, 0.0)}


def mission(name, named=(), swap=False, extra=False):
    wall = iw.wall(WALL, length=60, shape='square', lifetime=None)
    m = Mission(name=name, map=island, facts={'swap': int(swap), 'extra': int(extra)})
    m.units += [wall] + ([iw.wall(NONE, length=60, shape='square', lifetime=None)] if extra else [])
    m.crew('Ref')
    m.waypoint('m1', 'CNV Ref M1', 'west field', *M1)
    m.waypoint('m2', 'CNV Ref M2', 'west field', *M2)
    for k, (dx, dy) in WALLS.items():
        m.put(WALL, 'west field', dx, dy, role=f'wall {k}' if k in named else '',
              name=f'UNIT - CNV Ref Wall {k}' if k in named else '')
        m.waypoint(f'spot {k}', f'CNV Ref Spot {k}', 'west field', dx, dy)     # published: the check counts here
    return m


MISSION = {'ref_a': lambda: mission('CampRefA'),
           'ref_a2': lambda: mission('CampRefA2', swap=True),
           'ref_b': lambda: mission('CampRefB', named='C'),
           'ref_c': lambda: mission('CampRefC', extra=True)}
