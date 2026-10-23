"""The clones' bench scene on the west field: two enemy clones 300 apart, A on Soviet_2's side and B on Soviet_3's
(one side each: units/clone.py), and an engineer of ours 40 north of each (unarmed both ways, so nobody shoots: bench
2026-10-22, ore collectors would not do -- the Imperial one has a gun, the Soviet one drives about and crushes
infantry). The mission's rule: when a clone dies its side's units are handed back to the player. A mind maiden of
ours 70 north of B's engineer: 110 from clone B, out of its reach (65), B's engineer within hers (80).

Published (the cast): clone A, clone B, victim A, victim B, maiden.
"""
from maps import island
from parts import Mission, Script
from units import clone as cl

SIDES = {'A': 's2', 'B': 's3'}
VICTIMS = {'A': 'AlliedEngineer', 'B': 'JapanEngineer'}


def release(m, part, side):
    """The rule that ends a clone's control: when it dies, all its side owns goes to the player."""
    return Script(f'Clone - release {part}', [('NAMED_DESTROYED', m.role(part).name)],
                  [('PLAYER_TRANSFER_OWNERSHIP_PLAYER', m.player(side), m.player('p1'))])


def mission(name='CampClone'):
    u, maiden = cl.clone(), cl.maiden()
    m = Mission(name=name, map=island, units=[u, maiden])
    for k, dx in (('A', 0.0), ('B', 300.0)):
        m.put(u.id, 'west field', dx, 0, side=SIDES[k], name=f'UNIT - CNV Clone {k}', role=f'clone {k}')
        m.put(VICTIMS[k], 'west field', dx, 40, name=f'UNIT - CNV Victim {k}', role=f'victim {k}')
        m.scripts.append(release(m, f'clone {k}', SIDES[k]))
    m.put(maiden.id, 'west field', 300, 110, name='UNIT - CNV Maiden', role='maiden')
    return m
