"""Do a courtyard's fences bar infantry? (A4 redesign, docs/design/a4-redesign.md: the plazas as flat courtyards closed
by houses, walls and lanterns, one gate; plans/a4.md 待办.) On the festival map's west field, four square rings of
retail Japanese-town props, each closed but the control: TH_JapanFence01 (Tokyo Harbor's wooden fence, a destructible
prop), OK_StoneFence01 (Osaka's stone fence, a crushable obstacle), MJ_PalaceWall01 (Mount Fuji's palace wall, a
structure), and TH_JapanFence01 again with one side left open (the control: the soldiers can get in, the count
works). Three peacekeepers of the player's stand outside each; checks/fence.py sends them to the middle.

Published (the cast): soldier <ring> 1-3 (the rings: RINGS); marks inside <ring>; facts ring (half-side).
"""
import math

from maps import festival
from parts import Mission

HALF = 110.0                                    # a ring's half-side
RINGS = {                                       # name: (template, piece length, offset from the west field, open)
    'wood': ('TH_JapanFence01', 21.0, (-230.0, 230.0), False),
    'stone': ('OK_StoneFence01', 31.0, (230.0, 230.0), False),
    'palace': ('MJ_PalaceWall01', 60.0, (-230.0, -230.0), False),
    'open': ('TH_JapanFence01', 21.0, (230.0, -230.0), True),
}
SOLDIER = 'AlliedAntiInfantryInfantry'


def ring(m, name, tmpl, length, dx, dy, open_side):
    """Pieces round a square of HALF about (dx, dy) off the west field, each side from corner to corner (a piece
    every 0.9 of its length, so they overlap); open_side: the south side left out."""
    n = math.ceil(2 * HALF / (0.9 * length))
    step = 2 * HALF / n
    for k in range(n + 1):
        u = -HALF + step * k
        sides = [(u, HALF, 0.0), (-HALF, u, math.pi / 2), (HALF, u, math.pi / 2)]
        if not open_side:
            sides.append((u, -HALF, 0.0))
        for x, y, a in sides:
            m.put(tmpl, 'west field', dx + x, dy + y, side='civ', angle=a)
    for j in range(3):
        m.put(SOLDIER, 'west field', dx - 40 + 40 * j, dy - HALF - 120, name=f'UNIT - CNV Fence {name} {j + 1}',
              role=f'soldier {name} {j + 1}', angle=1.5708)
    m.waypoint(f'inside {name}', f'CNV Fence Inside {name}', 'west field', dx, dy)


def mission(name='CampFence'):
    m = Mission(name=name, map=festival)
    for k, (tmpl, length, (dx, dy), open_side) in RINGS.items():
        ring(m, k, tmpl, length, dx, dy, open_side)
    m.facts.update({'ring': HALF})
    return m
