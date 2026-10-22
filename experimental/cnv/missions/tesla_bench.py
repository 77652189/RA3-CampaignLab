"""The Tesla tank's bench scenes on the west field.

mission: ours, three enemy Guardians 120 north of it (inside its 150). Cast: tesla, target (the enemy Guardians).
surge: two of ours 300 apart (A west, B east), an enemy Guardian 40 north of each -- inside the surge's 50 and the
Guardian's 150, out of reach of the other pair. Cast: tesla A, tesla B, guard A, guard B.
"""
from maps import island
from parts import Mission
from units import tesla as te

X = 100.0                                       # east of the field's middle: its west edge is shallows
GAP = 300.0                                     # surge: between the two pairs (the Guardian's cannon reaches 150)
CLOSE = 40.0                                    # surge: each Guardian this far north of its tank


def mission(name='CampTesla'):
    u = te.tesla()
    m = Mission(name=name, map=island, units=[u])
    m.put(u.id, 'west field', X, 0, name='UNIT - CNV Tesla Tank', role='tesla')
    for dx in (-50, 0, 50):
        m.put('AlliedAntiVehicleVehicleTech1', 'west field', X + dx, 120, side='s1', role='target')
    return m


def surge(name='CampTslS', fire=True):
    u = te.tesla(fire=fire)
    m = Mission(name=name, map=island, units=[u])
    for tag, dx in (('A', X - GAP / 2), ('B', X + GAP / 2)):
        m.put(u.id, 'west field', dx, 0, name=f'UNIT - CNV Tesla {tag}', role=f'tesla {tag}')
        m.put('AlliedAntiVehicleVehicleTech1', 'west field', dx, CLOSE, side='s1', name=f'UNIT - CNV Guard {tag}',
              role=f'guard {tag}')
    return m
