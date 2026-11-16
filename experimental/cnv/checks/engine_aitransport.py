"""Tactic UseTransports: does a SimpleAttack team with a transport put its infantry aboard before it goes?

missions/aitransport_bench.py: Niagara without bridges, four Peacekeepers and a Riptide of s1 on the east bank, the
target plant on Goat Island. Three counters, once a second:
  车内步兵   s1's objects carrying ENCLOSED (only the Peacekeepers can be: aboard the Riptide)
  岛上步兵   s1's Peacekeepers inside Goat Island's box
  激流在岛   1 while the Riptide is inside Goat Island's box
Prediction (b221 read rule): true -> they board (车内步兵 > 0), the Peacekeepers reach the island; false -> the
Riptide crosses alone (激流在岛 1), 岛上步兵 stays 0.

RESULTS (2026-11-16, run_queue, B round 221): aitrans0 PASS, aitrans1 FAIL -- both 0 0 0 from s1 to the end (s117 /
s112); the minimap at s80 shows every s1 unit still at the east base: the team never left in either, so this pair
does not tell the flag apart (the simulator: the same, nobody moves). Not registered. Suspects: the target heuristic
or the team's start wants a ground way to the target (no target / no team), so no pair ever forms. Next: a home-box
counter, and the target reachable by the Riptide but not by the infantry in some other way.
"""
from parts import Script, Test, counted, status

ISLAND = 'CNV Trans Island'
X0, X1, Y0, Y1 = 2450.0, 2750.0, 2450.0, 3350.0      # niagara.GOAT
AT, SECONDS = 75.0, 85.0


def a(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas[ISLAND] = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
    counted('CNV_TR_In', '车内步兵', t, status=status('ENCLOSED'), player=s1)
    counted('CNV_TR_Isle', '岛上步兵', t, template='AlliedAntiInfantryInfantry', area=ISLAND, player=s1)
    counted('CNV_TR_Boat', '激流在岛', t, named='UNIT - CNV AI Riptide', area=ISLAND)
    if m.facts['use transports']:
        t.expect = [('岛上步兵', AT, '>=', 1, AT + 1)]
    else:
        t.expect = [('岛上步兵', AT, '==', 0, AT + 1), ('车内步兵', AT, '==', 0, AT + 1)]
    t.bench = [('bench_watch', dict(seconds=SECONDS, every=1, sheet=False, lines=3))]
    return t


CHECKS = {name: {'a': a} for name in ('aitrans0', 'aitrans1')}
