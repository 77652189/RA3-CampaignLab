"""Engine probe: the way an amphibious transport takes to a shore point behind a quay (missions/land_bench.py; R7 of
docs/story/sim-vs-bench-a4.md).

At ORDER s a script makes the transport at the sea point and sends it to the shore point as A4's horn does (a team
move, m.order). Four boxes, each a counter: frames from the order until the transport first stands in it (it
stops counting then; never in it: the counter runs on to the end):
  岸   A4's shore area (200 square round the shore point, its sea edge 100 out on the water)
  码头  in front of the quay, on the water (4300, 2900)
  南水  the sea south, on the simulator's way round (4280, 3500)
  南岸  the land south-west, the simulator's way ashore (3800, 3600)
"""
from parts import Script, Test, square

RUN, ORDER = 45.0, 2.0
BOXES = {'岸': ((4120.0, 2900.0), 100.0), '码头': ((4300.0, 2900.0), 80.0), '南水': ((4280.0, 3500.0), 100.0),
         '南岸': ((3800.0, 3600.0), 100.0)}


def way(m):
    t = Test()
    p1, boat = m.player('p1'), 'UNIT - CNV Land Boat'
    t.scripts += [Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Go', ORDER)]),
                  Script('Test - go', [('TIMER_EXPIRED', 'Test Go')],
                         [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', boat, 'JapanLightTransportVehicle', m.team('s1'),
                           m.mark('sea'))] + m.order('move', [boat], m.mark('shore'), 's1') +
                         [('SET_FLAG', 'Test Going', 1)])]
    for k, (label, (p, r)) in enumerate(BOXES.items()):
        area, counter, seen = f'Test Land {k}', f'CNV_Land_{k}', f'Test Land Seen {k}'
        t.areas[area] = square(*p, r)
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - land seen {k}', [('FLAG', 'Test Going', 1), ('NAMED_INSIDE_AREA', boat, area)],
                             [('SET_FLAG', seen, 1)]),
                      Script(f'Test - land count {k}', [('FLAG', 'Test Going', 1), ('FLAG', seen, 0)],
                             [('INCREMENT_COUNTER', 1, counter)], once=False)]
    t.expect += [('岸', RUN - 2, 'ever>=', 1)]              # it ran (the readings are the result)
    t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'engine_land': {'way': way}}
