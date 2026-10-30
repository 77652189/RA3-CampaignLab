"""The jammer's bench scene on the west field (east of its middle: the west edge is shallows): ours 100 east of a
north-south lane, an enemy Mecha Tengu at the lane's south end, a goal at its north end -- 458 of the 750 between
them lie within the jammer's 250.

Published (the cast): jammer, mech; marks goal.
"""
from maps import island
from parts import Mission
from units import jammer as ja

X = 100.0
MECH = 'JapanAntiInfantryVehicle'               # the Mecha Tengu


def mission(name='CampJam', side='s1', mech=MECH, **unit):
    """side: whose the mech is -- s1 (the enemy) or p1 (ours: the jammer slows friends too); mech: its template
    (a flier, to ask whether the jam reaches aircraft)."""
    u = ja.jammer(**unit)
    m = Mission(name=name, map=island, units=[u])
    m.put(u.id, 'west field', X + 100, 0, name='UNIT - CNV Jammer', role='jammer')
    m.put(mech, 'west field', X, -350, side=side, name='UNIT - CNV Mech', role='mech', angle=1.5708)
    m.waypoint('goal', 'CNV Jam Goal', 'west field', X, 400)
    return m
