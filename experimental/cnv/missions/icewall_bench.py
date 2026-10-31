"""The ice-wall engineer's bench scenes on the west field (east of its middle: the west edge is shallows).

block: two lanes 300 apart (A west, B east), a Guardian of ours at the south end of each, a goal 500 north of it; an
  ice wall across lane A halfway (placed, not built). Cast: runner A, runner B, wall; marks goal A, goal B,
  behind A, behind B (the middle of the strip just past the wall's line in each lane).
freeze: the engineer, a spot 150 north of him to raise a wall at. Cast: engineer, wall (built, not placed); mark spot.
  Variants: builder (retail's Soviet engineer walks there and builds it); spawn (his power makes another template --
  ice_spawn: our Tesla tank, placed nowhere: the check that every unit is compiled and linked).
smash: a wall of ours, three enemy Hammers 120 south of it. Cast: wall, hammer 1 .. 3.
"""
from maps import aso, island
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


TURNS = {'A': dict(angle=0), 'B': dict(angle=90), 'C': dict(angle=0, shape='square')}


def turns(name='CampIceT'):
    """Three lanes 200 apart, each with a runner at its south end, a goal 500 north, and an engineer by a spot on
    its line who builds a core there: A's leaves the bar at absolute 0, B's at 90, C's a square (blocks whichever
    way). Cast: runner A-C, engineer A-C; marks goal A-C, spot A-C, behind A-C."""
    m = Mission(name=name, map=island)
    for k, (tag, opts) in enumerate(TURNS.items()):
        dx = MIDDLE + (k - 1) * 200
        shape = opts.get('shape', 'bar')
        w = iw.wall(f'CNV_IceWallT{tag}', length=160, shape=shape)
        core = iw.seed(f'CNV_IceSeedT{tag}', w.id, angle=opts['angle'])
        e = iw.engineer(f'CNV_IceEngT{tag}', wall_id=core.id, stand=iw.clear_of(w))
        m.units += [w, core, e]
        m.put(RUNNER, 'west field', dx, -150, name=f'UNIT - CNV Runner {tag}', role=f'runner {tag}', angle=1.5708)
        m.put(e.id, 'west field', dx - 60, WALL_Y - 50, name=f'UNIT - CNV Ice Engineer {tag}', role=f'engineer {tag}')
        m.waypoint(f'goal {tag}', f'CNV Ice Goal {tag}', 'west field', dx, 350)
        m.waypoint(f'spot {tag}', f'CNV Ice Spot {tag}', 'west field', dx, WALL_Y)
        m.waypoint(f'behind {tag}', f'CNV Ice Behind {tag}', 'west field', dx, WALL_Y + BEHIND)
    return m


def freeze(name='CampIceF', builder=False, spawn=None, extra=(), **wall):
    """builder: retail's Soviet engineer walks there and builds our wall instead. spawn: the engineer's power
    creates this template instead of the wall (extra: more units of ours the mission carries, placed nowhere)."""
    w = iw.wall(**wall)
    e = iw.retail_engineer(structure=w.id) if builder else iw.engineer(wall_id=spawn or w.id, build=not spawn)
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


GHOST = 'JapanAntiVehicleVehicleTech3'          # the Ghost King (glossary.py 鬼王)
# ghost: four spots on the west field; a nearest-first walker visits them from the ghost's start in the order C, A, B, D
GHOST_SPOTS = {'C': (150, -300), 'A': (150, -40), 'B': (150, 300), 'D': (-250, -300)}


def ghost(name='CampIceG'):
    """Four built ice walls (the A4 device's: a core leaves a 160 square), each by its own engineer; later a Ghost King
    of the enemy appears by wall C. Asks: does it smash walls on its own, does it when ordered, can a script find the
    nearest unnamed wall and order it, is a wall in an area countable. Cast: engineer A-D, ghost, wall; marks spot A-D,
    ghost (where it appears)."""
    w = iw.wall('CNV_IceWallG', length=160, shape='square', lifetime=300)
    core = iw.seed('CNV_IceSeedG', w.id)
    e = iw.engineer('CNV_IceEngG', wall_id=core.id, stand=iw.clear_of(w))
    m = Mission(name=name, map=aso, units=[e, core, w])
    m.cast['wall'] = Role(w.id)
    m.put(GHOST, 'merc camp', 0, 0, side='s1', name='UNIT - CNV Ghost King', role='ghost')   # far off: the check brings it
    for k, (x, y) in GHOST_SPOTS.items():
        m.waypoint(f'spot {k}', f'CNV Ice Ghost Spot {k}', 'west field', x, y)
        m.put(e.id, 'west field', x + 120, y, name=f'UNIT - CNV Ice Engineer {k}',
              role=f'engineer {k}')
    m.waypoint('ghost', 'CNV Ice Ghost Start', 'west field', 300, -300)   # where the check teleports it to
    return m
