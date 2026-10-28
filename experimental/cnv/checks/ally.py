"""Ally tests (missions/ally_bench.py). Counted: truck 1 is the ally's (NAMED_OWNED_BY_PLAYER; 0 once it reached the
exit, where the convoy deletes it), the batches (latched 1 once truck 1 is on the road at approach 1 while truck 2
still stands at the convoy start -- all at once they leave it within a second or two of each other), truck 3's and
the player's own tank's health (both start at 50 %).

Bench 2026-10-27 (no tank yet): the trucks went one by one, 25 s apart (on the road 1, then 2, then 1 as the first got
off at the exit, then 2 again); the depot left truck 3 at 50 %.

mended: the player's repair depot mends their own tank (it works); truck 3 -- the ally's -- the question.
unmended: no depot -- both stay at 50 % (nothing else mends them: the control).
"""
from parts import Script, Test, counted, square

RUN = 90.0


def setup(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    trucks = [m.role(f'truck {j}').name for j in (1, 2, 3)]
    tank = m.role('own tank').name
    for n in (trucks[2], tank):
        m.find(n).props['objectInitialHealth'] = 50
    ally = m.player(m.cast['truck 1'].side)
    counted('Test Ally', '1号车归盟友', t, owner=trucks[0], player=ally)
    t.areas['Test Approach'] = square(*m.site('approach 1'), 150.0)
    t.areas['Test Start'] = square(*m.site('convoy start'), 100.0)
    t.counters.append(('Test Batches', '分批了'))
    t.scripts += [Script('Test - batches zero', [], [('SET_COUNTER', 'Test Batches', 0)]),
                  Script('Test - batches', [('NAMED_INSIDE_AREA', trucks[0], 'Test Approach'),
                                            ('NAMED_INSIDE_AREA', trucks[1], 'Test Start')],
                         [('SET_COUNTER', 'Test Batches', 1)])]
    counted('Test Truck 3', '3号车血量', t, health=trucks[2])
    counted('Test Own', '自己坦克血量', t, health=tank)
    t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=len(t.counters)))]
    return t


def mended(m):
    t = setup(m)
    t.expect += [('1号车归盟友', 1, 'ever==', 1), ('分批了', 1, 'ever==', 1), ('自己坦克血量', 1, 'ever>=', 90),
                 ('3号车血量', 1, 'ever>=', 90)]
    return t


def unmended(m):
    t = setup(m)
    t.expect += [('1号车归盟友', 1, 'ever==', 1), ('3号车血量', 1, '<=', 55), ('自己坦克血量', 1, '<=', 55)]
    return t
