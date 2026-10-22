"""The Tesla tank's bench scene: ours on the west field, three enemy Guardians 120 north of it (inside its 150).

Published (the cast): tesla, target (the enemy Guardians).
"""
from maps import island
from parts import Mission
from units import tesla as te

X = 100.0                                       # east of the field's middle: its west edge is shallows


def mission(name='CampTesla'):
    u = te.tesla()
    m = Mission(name=name, map=island, units=[u])
    m.put(u.id, 'west field', X, 0, name='UNIT - CNV Tesla Tank', role='tesla')
    for dx in (-50, 0, 50):
        m.put('AlliedAntiVehicleVehicleTech1', 'west field', X + dx, 120, side='s1', role='target')
    return m
