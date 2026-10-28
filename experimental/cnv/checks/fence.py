"""Fence tests (missions/fence_bench.py): at GO_AT every soldier is sent to the middle of his ring, again every few
seconds. Counted: the player's peacekeepers inside each ring (an area a little inside its walls).

bar: none gets into a closed ring; all three get into the open one (the control).
"""
from missions.fence_bench import RINGS
from parts import Script, Test, counted, square

GO_AT, RUN = 3.0, 60.0
INSIDE = 70.0                                   # half-side of the counted area (the ring's walls stand at 110)


def bar(m):
    t = Test()
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - go', GO_AT)]))
    go = []
    labels = {'wood': '木篱笆里', 'stone': '石栏里', 'palace': '宫墙里', 'open': '开口的里'}
    for ring in RINGS:
        go += [('MOVE_NAMED_UNIT_TO', m.role(f'soldier {ring} {j}').name, m.mark(f'inside {ring}')) for j in (1, 2, 3)]
        t.areas[f'Test {ring}'] = square(*m.point(f'inside {ring}'), INSIDE)
        counted(f'Test {ring}', labels[ring], t, template='AlliedAntiInfantryInfantry', area=f'Test {ring}', most=4)
    t.scripts.append(Script('Test - go', [('TIMER_EXPIRED', 'Test - go')],
                            go + [('SET_MILLISECOND_TIMER', 'Test - go', 5.0)], once=False))
    t.expect += [(labels[r], 1, '==', 0) for r in ('wood', 'stone', 'palace')] + [('开口的里', 1, 'ever==', 3)]
    t.bench = [('bench_camera', dict(x=m.point('inside wood')[0] + 230, y=m.point('inside wood')[1] - 230,
                                     look=False)),
               ('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t
