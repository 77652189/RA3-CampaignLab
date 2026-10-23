"""The combining mech's bench scene: the parent (King Oni stand-in) on the west field, the child (Tsunami stand-in)
200 south of it.

Published (the cast): parent, child.
"""
from maps import island
from parts import Mission
from units import combo, icewall

X = 100.0                                       # east of the field's middle: its west edge is shallows


def breach(name='CampCmbB', **parent):
    """Two pairs 350 apart on the west field, A west, B east, each 220 short of an enemy ice wall (units/icewall.py,
    lasting long enough not to melt first): A is to join and break its wall, B to stay apart and break its own.
    Published (the cast): parent A / B, child A / B, wall A / B."""
    c = combo.child()
    p = combo.parent(child_id=c.id, **parent)
    w = icewall.wall(lifetime=120)
    m = Mission(name=name, map=island, units=[p, c, w])
    for k, dx in (('A', 50.0), ('B', 400.0)):
        m.put(p.id, 'west field', dx, 0, name=f'UNIT - CNV Combo Parent {k}', role=f'parent {k}')
        m.put(c.id, 'west field', dx, -60, name=f'UNIT - CNV Combo Child {k}', role=f'child {k}')
        m.put(w.id, 'west field', dx, 220, side='s1', angle=0.0, name=f'UNIT - CNV Wall {k}', role=f'wall {k}')
    return m


def mission(name='CampCombo'):
    c = combo.child()
    p = combo.parent(child_id=c.id)
    m = Mission(name=name, map=island, units=[p, c])
    m.put(p.id, 'west field', X, 200, name='UNIT - CNV Combo Parent', role='parent')
    m.put(c.id, 'west field', X, 0, name='UNIT - CNV Combo Child', role='child')
    return m
