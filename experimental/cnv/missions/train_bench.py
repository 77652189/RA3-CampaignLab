"""The armoured train's bench scene on the west field: a track of three legs (north 600, east 300, south 600) from
the train's start, and -- with enemies=True -- three enemy conscripts 150 east of the first leg's far end, 500 from
the start: out of reach until it drives past.

Published (the cast): train, enemy (with enemies); marks stop 1 .. 3 (the track's waypoints, in order), astray (a
point off the track, where a player might send it).
"""
from maps import island
from parts import Mission
from units import train as tr

TRACK = [(0, 300), (300, 300), (300, -300)]     # from the start at (0, -300), west field offsets
X = 0.0


def mission(name='CampTrain', enemies=False, **unit):
    u = tr.train(**unit)
    m = Mission(name=name, map=island, units=[u])
    m.put(u.id, 'west field', X, -300, name='UNIT - CNV Train', role='train', angle=1.5708)
    for k, (dx, dy) in enumerate(TRACK):
        m.waypoint(f'stop {k + 1}', f'CNV Train Stop {k + 1}', 'west field', X + dx, dy)
    m.waypoint('astray', 'CNV Train Astray', 'west field', X - 300, -100)      # off the track, west of the first leg
    if enemies:
        for dy in (160, 200, 240):
            m.put('SovietAntiInfantryInfantry', 'west field', X + 150, dy, side='s1', role='enemy')
    return m
