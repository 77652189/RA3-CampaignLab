"""Low ground looking up (missions/sight_bench.py): latched, whether the player has discovered each pair's target
(NAMED_DISCOVERED), the map left shrouded.

look: the controls hold -- on one level, seen within the viewer's vision, not beyond it. The two 'up' pairs are the
finding, read off the counters: 1, the viewer below sees up the cliff; 0, it does not.
"""
from missions.sight_bench import PAIRS
from parts import Script, Test

RUN = 20.0
LABELS = {'up 120': '低看高120', 'up 180': '低看高180', 'flat 180': '平地180', 'flat 400': '平地400'}


def look(m):
    t = Test()
    p1 = m.player('p1')
    for k in PAIRS:
        c = f'Test Seen {k.title()}'
        t.counters.append((c, LABELS[k]))
        t.scripts += [Script(f'{c} zero', [], [('SET_COUNTER', c, 0)]),
                      Script(f'{c} one', [('NAMED_DISCOVERED', p1, m.role(f'target {k}').name)],
                             [('SET_COUNTER', c, 1)])]
    t.expect += [('平地180', 1, 'ever==', 1), ('平地400', 1, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=len(t.counters)))]
    return t
