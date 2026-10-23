"""The shikigami's bench scene on the west field: two groups 400 apart (A west, B east), each a VIP of ours (a
Japanese engineer, standing in for Yuriko) with a shikigami 30 east of him, and two enemy conscripts 300 south.

Published (the cast): vip A, vip B, guard A, guard B, shooter A 1 .. 2, shooter B 1 .. 2.
"""
from maps import island
from parts import Mission
from units import shikigami as sk

VIP = 'JapanEngineer'
SHOOTER = 'SovietAntiInfantryInfantry'          # the conscript


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
