"""The lock gate's bench scene (A5 / S5, Panama): on the festival map's canal, between its middle and north bridges,
a gate (a never-melting wall the map places across the water) and an Allied ship south of it; the goal is north of
the gate. Does a structure on the water bar a ship, and does deleting it let the ship through?

Published (the cast): gate, ship; marks goal.
"""
from maps import festival
from parts import Mission
from units import icewall as iw

X = sum(festival.CANAL) / 2                      # the canal's middle
GATE_Y, SHIP_Y, GOAL_Y = 3000.0, 2750.0, 3250.0
SHIP = 'AlliedAntiNavyShipTech1'                # the assault destroyer


def gate_unit(id='CNV_LockGate'):
    return iw.wall(id=id, length=240, thick=60, lifetime=None, health=5000, look_as='gate',
                   what='船闸闸门：横在水道上的建筑，不化、不打碎（关卡脚本删掉它就是开闸）')


def mission(name='CampLock', gate=True):
    u = gate_unit()
    m = Mission(name=name, map=festival, units=[u])
    if gate:
        m.put(u.id, 'island', X - 2500, GATE_Y - 2500, side='neutral', name='UNIT - CNV Lock Gate', role='gate',
              angle=0.0)
    m.put(SHIP, 'island', X - 2500, SHIP_Y - 2500, name='UNIT - CNV Lock Ship', role='ship', angle=1.5708)
    m.waypoint('goal', 'CNV Lock Goal', 'island', X - 2500, GOAL_Y - 2500)
    return m
