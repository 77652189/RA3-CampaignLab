"""The ice-wall engineer's bench scenes on the west field (east of its middle: the west edge is shallows).

block: two lanes 300 apart (A west, B east), a Guardian of ours at the south end of each, a goal 500 north of it; an
  ice wall across lane A halfway (placed, not built). Cast: runner A, runner B, wall; marks goal A, goal B,
  behind A, behind B (the middle of the strip just past the wall's line in each lane).
freeze: the engineer, a spot 150 north of him to raise a wall at. Cast: engineer, wall (built, not placed); mark spot.
  Variants: builder (retail's Soviet engineer walks there and builds it); spawn (his power makes another template --
  ice_spawn: our Tesla tank, placed nowhere: the check that every unit is compiled and linked).
smash: a wall of ours, three enemy Hammers 120 south of it. Cast: wall, hammer 1 .. 3.
"""
from maps import island
from parts import Mission, Role
from units import icewall as iw

MIDDLE = 150.0
LANE = 150.0
RUNNER = 'AlliedAntiVehicleVehicleTech1'        # the Guardian
WALL_Y = 100.0                                  # block: the wall's line; the runners start at -150, goals at +350
BEHIND = 65.0                                   # block: the middle of the strip just past the wall (north of it)


def block(name='CampIceB'):
    w = iw.wall()
    m = Mission(name=name, map=island, units=[w])
    for tag, dx in (('A', MIDDLE - LANE), ('B', MIDDLE + LANE)):
        m.put(RUNNER, 'west field', dx, -150, name=f'UNIT - CNV Runner {tag}', role=f'runner {tag}', angle=1.5708)
        m.waypoint(f'goal {tag}', f'CNV Ice Goal {tag}', 'west field', dx, 350)
        m.waypoint(f'behind {tag}', f'CNV Ice Behind {tag}', 'west field', dx, WALL_Y + BEHIND)
    m.put(w.id, 'west field', MIDDLE - LANE, WALL_Y, name='UNIT - CNV Ice Wall', role='wall', angle=0.0)
    return m


def freeze(name='CampIceF', builder=False, spawn=None, extra=(), **wall):
    """builder: retail's Soviet engineer walks there and builds our wall instead. spawn: the engineer's power
    creates this template instead of the wall (extra: more units of ours the mission carries, placed nowhere)."""
    w = iw.wall(**wall)
    e = iw.retail_engineer(structure=w.id) if builder else iw.engineer(wall_id=spawn or w.id)
    m = Mission(name=name, map=island, units=[e, w, *extra])
    m.cast['wall'] = Role(spawn or e.params['wall'])
    m.put(e.id, 'west field', MIDDLE, -100, name='UNIT - CNV Ice Engineer', role='engineer')
    m.waypoint('spot', 'CNV Ice Spot', 'west field', MIDDLE, 50)
    return m


def smash(name='CampIceS'):
    w = iw.wall(lifetime=120)
    m = Mission(name=name, map=island, units=[w])
    m.put(w.id, 'west field', MIDDLE, 100, name='UNIT - CNV Ice Wall', role='wall', angle=0.0)
    for k, dx in enumerate((-60, 0, 60)):
        m.put('SovietAntiVehicleVehicleTech1', 'west field', MIDDLE + dx, -20, side='s1',
              name=f'UNIT - CNV Hammer {k + 1}', role=f'hammer {k + 1}')
    return m
