"""An ice wall across one way: do the troops on it go round by another? (A4 redesign, docs/design/a4-redesign.md, phase
3's "冰从封门变成改道".) On the festival map: the canal's three bridges (middle on the road, north, south) are the only
ways west from the harbour; their east ends sit on the quay, a strip of land between the canal and the sea. A Japanese
squad (five imperial warriors: the tsunami tank swims, bench 2026-10-27) stands on the quay north of the middle
bridge; checks/reroute.py sends it west, a never-melting ice wall across the quay between it and the middle bridge
(canal to sea): the middle bridge is shut to it, the north one open.

Bench 2026-10-27, a wall on the middle bridge itself stopped nobody, at the deck's middle or its east end: the warriors
walked through it (the bridge object's own way over ignores what stands on it; its deck is drawn much longer than
festival.BRIDGES, ~3615 to ~4090).

Published (the cast): warrior 1-5 (the enemy's); marks goal (the west field), wall (on the quay); the wall's unit and
its angle (ANGLE); bridges() their middles.
"""
from maps import festival
from parts import Mission
from units import icewall as iw

WARRIOR = 'JapanAntiInfantryInfantry'
SQUAD = 5
# the quay at the middle bridge (bench map 2026-10-27): the canal's east edge x ~3823, the sea from ~4167; the deck
# ~80 either side of the road
QUAY = (3823.0, 4167.0)
WALL_Y, THICK, ANGLE = 2650.0, 120.0, 0.0       # across the quay north of the deck (the wall along x)
SQUAD_X, SQUAD_Y = 3880.0, 2800.0               # on the quay's road north of the wall


def bridges():
    return {k: ((p[0] + q[0]) / 2, p[1]) for k, (p, q) in zip(('middle', 'north', 'south'), festival.BRIDGES)}


def wall_unit():
    # a little longer than the quay is wide: canal edge to sea, no gap
    return iw.wall(id='CNV_RerouteWall', length=QUAY[1] - QUAY[0] + 40, thick=THICK, lifetime=None, health=5000,
                   what='改道测试的冰墙：横在中桥北边的码头上，从运河边到海边，不化、不打碎')


def mission(name='CampDetour'):
    m = Mission(name=name, map=festival, units=[wall_unit()])
    hx, hy = m.site('harbour')
    for j in range(1, SQUAD + 1):
        m.put(WARRIOR, 'harbour', SQUAD_X - hx + 40 * ((j - 1) % 2), SQUAD_Y - hy + 40 * (j - 1), side='s1',
              name=f'UNIT - CNV Reroute Warrior {j}', role=f'warrior {j}', angle=3.1416)
    m.waypoint('goal', 'CNV Reroute Goal', 'west field')
    m.waypoint('wall', 'CNV Reroute Wall', 'harbour', sum(QUAY) / 2 - hx, WALL_Y - hy)
    return m
