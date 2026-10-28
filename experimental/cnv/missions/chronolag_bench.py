"""The phase tank's bench scene on the west field (east of its middle: the west edge is shallows), make_campnew35's:
ours 300 south of an enemy Apocalypse (inside the shell's 400 and the tank's 450 vision), facing it.

Published (the cast): tank, target.
"""
from maps import island
from parts import Mission
from units import chronolag as cl

X = 150.0
APOCALYPSE = 'SovietAntiVehicleVehicleTech3'


def mission(name='CampLag', **unit):
    u = cl.chronolag(**unit)
    m = Mission(name=name, map=island, units=[u])
    m.put(u.id, 'west field', X, -150, name='UNIT - CNV Phase Tank', role='tank', angle=1.5708)
    m.put(APOCALYPSE, 'west field', X, 150, side='s1', name='UNIT - CNV Phase Target', role='target', angle=-1.5708)
    return m
