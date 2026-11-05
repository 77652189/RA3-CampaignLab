"""A probe map for the engine line's range tests (checks/engine_range.py, docs/engine/upgrades.md): flat open ground
(tier 1), no walls. Six lanes, each a turret's pad and a line of target spots north of it (`<lane> gun`, `<lane> at
<d>`: d world units from the gun), the lanes 1 500 apart (a gun reaching 600 never sees another lane's targets), and
a row of power plant pads between the two rows of lanes (base defences are POWERED). The player's start (1250, 2500)
stays clear.

Published: SITES (the guns, the target spots, 'power 1'..'power 3', 'probe refinery': a refinery pad facing 45, its
one ore node 180 ahead), PLAYERS, TEAMS, LANES {lane: (x, y)}, DISTANCES {lane: the target distances}, FIELDS,
OBJECTS (that ore node).
"""
import make_campnew18 as c18
import platmap
import resources
from platmap import Layout, poly
from maps import island
from parts import Site

# lane: the gun's pad; its targets stand straight north at these distances
LANES = {
    'base': (800.0, 400.0), 'high': (2300.0, 400.0), 'order': (3800.0, 400.0),
    'removed': (800.0, 3300.0), 'switch': (2300.0, 3300.0), 'low': (3800.0, 3300.0),
}
DISTANCES = {
    'base': (250.0, 450.0), 'high': (450.0, 550.0), 'order': (450.0,),
    'removed': (250.0, 450.0), 'switch': (150.0, 250.0), 'low': (150.0, 250.0),
}

SITES = {k: island.SITES[k] for k in ('island', 'start', 'base factory', 'base power', 'west field')}
for _lane, (_x, _y) in LANES.items():
    SITES[f'{_lane} gun'] = Site(_x, _y, 60.0, f'the {_lane} lane\'s turret')
    for _d in DISTANCES[_lane]:
        SITES[f'{_lane} at {_d:g}'] = Site(_x, _y + _d, 20.0, f'a target {_d:g} north of the {_lane} turret')
# pace lanes (checks/engine_pace.py): open ground west to east between the two rows of guns, 1 500 long, with two
# leg points on the way (500, 1 000 from the start)
PACE = {'pace': 1200.0, 'legs': 1500.0, 'guard': 1800.0}
PACE_X = (500.0, 2000.0)
for _lane, _y in PACE.items():
    SITES[f'{_lane} start'] = Site(PACE_X[0], _y, 60.0, f'where the {_lane} lane\'s pair stands')
    SITES[f'{_lane} goal'] = Site(PACE_X[1], _y, 60.0, f'where the {_lane} lane\'s pair is sent')
    for _k in (1, 2):
        SITES[f'{_lane} leg {_k}'] = Site(PACE_X[0] + 500.0 * _k, _y, 60.0, f'the {_lane} lane\'s leg point {_k}')
for _k in range(3):
    SITES[f'power {_k + 1}'] = Site(3000.0 + 300.0 * _k, 1900.0, 120.0, 'a power plant pad', build=200.0)
# a refinery pad in the free north-east corner with its one ore node (checks/engine_spawn.py count: the refinery's
# collector); far from every lane, the start and the power pads
FIELDS = [resources.Field('probe', 3000.0, 4200.0, 45.0, 0)]
SITES.update(resources.sites(FIELDS))
OBJECTS = resources.objects(FIELDS)
PLAYERS = island.PLAYERS
TEAMS = island.TEAMS

_LAYOUT = Layout(shapes=[poly([(-300, -300), (5300, -300), (5300, 5300), (-300, 5300)], 1, 'level ground')])


def terrain(m):
    """CampNew18's generate (objects, scripts, light, the start), then the level ground."""
    c18.generate(m)
    previews, _ = platmap.apply(m, _LAYOUT)
    c18.PREVIEWS.update(previews)


def like(m, objs, tmpl):
    return island.like(m, objs, tmpl)
