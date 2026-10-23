"""The clones' bench scene on the west field: two enemy clones 300 apart, A on Soviet_2's side and B on Soviet_3's
(one side each: units/clone.py), and an engineer of ours 40 north of each (unarmed both ways, so nobody shoots: bench
2026-10-22, ore collectors would not do -- the Imperial one has a gun, the Soviet one drives about and crushes
infantry). The mission's rule: when a clone dies its side's units are handed back to the player. A mind maiden of
ours 260 north of clone B, and her spot 70 north of B's engineer (within her 80); an enemy engineer no clone holds,
by her spot too.

Published (the cast): clone A, clone B, victim A, victim B, maiden, stranger; marks maiden spot.
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


def mission(name='CampClone', picky=True):
    """picky=False: a maiden who takes any enemy (the control of her filter)."""
    u, maiden = cl.clone(), cl.maiden(picky=picky)
    m = Mission(name=name, map=island, units=[u, maiden])
    for k, dx in (('A', 0.0), ('B', 300.0)):
        m.put(u.id, 'west field', dx, 0, side=SIDES[k], name=f'UNIT - CNV Clone {k}', role=f'clone {k}')
        m.put(VICTIMS[k], 'west field', dx, 40, name=f'UNIT - CNV Victim {k}', role=f'victim {k}')
        m.scripts.append(release(m, f'clone {k}', SIDES[k]))
    # bench 2026-10-22: standing 110 from clone B she was taken with B's engineer (a bribe reaches past its 65);
    # so she waits 260 away and is sent to her spot by B's engineer after the clones' one press
    m.put(maiden.id, 'west field', 300, 260, name='UNIT - CNV Maiden', role='maiden')
    m.waypoint('maiden spot', 'CNV Maiden Spot', 'west field', 300, 110)
    # an enemy no clone holds, within her reach at her spot (63), out of clone B's (140)
    m.put('SovietEngineer', 'west field', 360, 130, side='s1', name='UNIT - CNV Stranger', role='stranger')
    return m
