"""Engine probe mission: does a unit that is re-ordered every frame still walk (checks/engine_reorder.py; A4's Ghost
King, devices/horn.py ghost_scripts: `smashes` told it every frame and it stood still, `hunts` did and it walked).

The west field (island map), offsets from 'west field':
  S (0, -400)   the attacker's birth point (an enemy s1 'AlliedAntiVehicleVehicleTech1', made at 1 s by the check
                on the s1 crew 'Reo')
  W (0,  500)   the player's ice wall (no lifetime), named: 900 from S, far out of range, the attacker has to walk
  T (250, 500)  the player's tank, named, NO_ATTACK (the target of the tank / alt variants)
  M (0,  200)   the move point of the move variant
Published waypoints: s, mid (0, 0), near (0, 330), m.
"""
from maps import island
from parts import Mission
from units import icewall as iw

WALL = 'CNV_ReoWall'
TANK = 'AlliedAntiVehicleVehicleTech1'
S, W, T, M = (0.0, -400.0), (0.0, 500.0), (250.0, 500.0), (0.0, 200.0)
VARIANTS = ('once', 'every', 'bare', 'tank', 'move', 'alt', 'late')


def mission(name, variant):
    m = Mission(name=name, map=island, facts={'variant': VARIANTS.index(variant)})
    m.units += [iw.wall(WALL, length=60, shape='square', lifetime=None)]
    m.crew('Reo', 's1')
    m.put(WALL, 'west field', *W, role='wall', name='UNIT - CNV Reo Wall')
    m.put(TANK, 'west field', *T, role='tank', name='UNIT - CNV Reo Tank')
    for part, label, at in (('s', 'S', S), ('mid', 'Mid', (0.0, 0.0)), ('near', 'Near', (0.0, 330.0)), ('m', 'M', M)):
        m.waypoint(part, f'CNV Reo {label}', 'west field', *at)
    return m


MISSION = {f'reorder_{v}': (lambda v=v: mission('CampRo' + v[:2].capitalize(), v)) for v in VARIANTS}
