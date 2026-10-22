"""The combining mech's bench scene: the parent (King Oni stand-in) on the west field, the child (Tsunami stand-in)
200 south of it.

Published (the cast): parent, child.
"""
from maps import island
from parts import Mission
from units import combo

X = 100.0                                       # east of the field's middle: its west edge is shallows


def mission(name='CampCombo'):
    c = combo.child()
    p = combo.parent(child_id=c.id)
    m = Mission(name=name, map=island, units=[p, c])
    m.put(p.id, 'west field', X, 200, name='UNIT - CNV Combo Parent', role='parent')
    m.put(c.id, 'west field', X, 0, name='UNIT - CNV Combo Child', role='child')
    return m
