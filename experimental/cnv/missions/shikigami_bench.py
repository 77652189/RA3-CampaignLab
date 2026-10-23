"""The shikigami's bench scene on the west field: two groups 400 apart (A west, B east), each a VIP of ours (a
Japanese engineer, standing in for Yuriko) with a shikigami 30 east of him, and two enemy conscripts 300 south.

Published (the cast): vip A, vip B, guard A, guard B, shooter A 1 .. 2, shooter B 1 .. 2.
"""
from maps import island
from parts import Mission
from units import shikigami as sk

VIP = 'JapanEngineer'
SHOOTER = 'SovietAntiInfantryInfantry'          # the conscript


V4 = 'SovietAntiStructureVehicle'               # V4 rockets: 500 out, not flagged NOT_ATTRACTED_BY_MAGNETS


def shells(name='CampShikiV', **unit):
    """Shells bending: two groups 400 apart, each a VIP with a shikigami 120 east of him (he stays within its 200;
    a rocket bent onto it bursts away from him) and an enemy V4 launcher 400 south of the VIP (outside the 200: it is
    not made to retarget, only its rockets can bend). Published (the cast): vip A / B, guard A / B, launcher A / B."""
    u = sk.shikigami(**unit)
    m = Mission(name=name, map=island, units=[u])
    for tag, dx in (('A', -100.0), ('B', 300.0)):
        m.put(VIP, 'west field', dx, 150, name=f'UNIT - CNV VIP {tag}', role=f'vip {tag}')
        m.put(u.id, 'west field', dx + 120, 150, name=f'UNIT - CNV Shikigami {tag}', role=f'guard {tag}')
        m.put(V4, 'west field', dx, -250, side='s1', name=f'UNIT - CNV Launcher {tag}', role=f'launcher {tag}')
    return m


def mission(name='CampShiki', **unit):
    u = sk.shikigami(**unit)
    m = Mission(name=name, map=island, units=[u])
    for tag, dx in (('A', -50.0), ('B', 350.0)):
        m.put(VIP, 'west field', dx, 100, name=f'UNIT - CNV VIP {tag}', role=f'vip {tag}')
        m.put(u.id, 'west field', dx + 30, 100, name=f'UNIT - CNV Shikigami {tag}', role=f'guard {tag}')
        for k, sx in enumerate((-25, 25)):
            m.put(SHOOTER, 'west field', dx + sx, -200, side='s1', name=f'UNIT - CNV Shooter {tag}{k + 1}',
                  role=f'shooter {tag} {k + 1}')
    return m
