"""Does low ground see high ground? (docs/design/principles.md P26: the design line guesses RA3 has no rule that
ground below cannot see up a cliff.) On the festival map's north plateau (its top ~80 world units above the low
ground, the cliff between ~60-70 wide): pairs of a viewer (the player's MCV: no weapon, vision 200, does not move)
and a target (an enemy imperial engineer: no weapon), PAIRS apart along y --
  up 120, up 180:   the viewer at the cliff's foot, the target on the plateau's top
  flat 180, flat 400: both on the plateau's top -- the control: seen within its reach, not beyond it
each pair 400 and more from the others. Read back by checks/sight.py.

Published (the cast): viewer <pair>, target <pair>; facts vision.
"""
from maps import festival
from parts import Mission

VIEWER, TARGET = 'AlliedMCV', 'JapanEngineer'
VISION = 200.0                                  # AlliedMCV's VisionRange (SageXML)
# pair: (x, the viewer's y, apart): measured off the layout's heights 2026-10-27 (the low ground walkable up to
# y ~3500 at x 2450-2950, the plateau's top from ~3570), each one clear of the scenery
PAIRS = {'up 120': (2480.0, 3460.0, 120.0), 'up 180': (2950.0, 3490.0, 180.0),
         'flat 180': (2160.0, 3640.0, 180.0), 'flat 400': (3250.0, 3680.0, 400.0)}
# bench 2026-10-27: a control 260 apart was discovered too -- the MCV clears the shroud to 250 (ShroudClearingRange),
# past its vision, and both have a body: the far control well beyond


def mission(name='CampSight'):
    m = Mission(name=name, map=festival)
    cx, cy = m.site('island')
    for k, (x, y, apart) in PAIRS.items():
        tag = k.title().replace(' ', '')
        m.put(VIEWER, 'island', x - cx, y - cy, name=f'UNIT - CNV Sight Viewer {tag}', role=f'viewer {k}',
              angle=1.5708)
        m.put(TARGET, 'island', x - cx, y + apart - cy, side='s1', name=f'UNIT - CNV Sight Target {tag}',
              role=f'target {k}', angle=-1.5708)
    m.facts.update({'vision': VISION})
    return m
