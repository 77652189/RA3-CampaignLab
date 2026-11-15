"""D round 154: SimpleExpansion readings (missions/aisimpleexp_bench.py; aiexpse / aiexpd50 / aiexpd400 differ in
Tactic.Distance only). Counters (four fit): the AI's outposts on the whole map, its outposts and miners within 150 of the Expansion pick
(bench aiexpc f151: (4173, 2987)), its Guardians in C's 350 square round the east candidate. The exact unpack point
and frame come from the CNVTeams host's cmd log (ra3ext.log). Expectations: the simulator's prediction (round 154).
"""
from parts import Test, Script, counted, square
from missions.aisimpleexp_bench import MINER, OUTPOST


def a(m):
    t = Test()
    s1 = m.player('s1')
    tank, = m.cnv_units
    near, east = 'CNV SExp near', 'CNV SExp east'
    t.areas[near] = square(*m.facts['expansion pick'], 150.0)
    t.areas[east] = square(*m.facts['candidate east'], 350.0)
    counted('CNV_SExp_out', '前哨', t, template=OUTPOST, player=s1)
    counted('CNV_SExp_outnear', '前哨近', t, template=OUTPOST, player=s1, area=near, most=2)
    counted('CNV_SExp_minernear', '矿车近', t, template=MINER, player=s1, area=near, most=2)
    counted('CNV_SExp_tanks', '坦克东', t, template=tank, player=s1, area=east, most=5)
    t.scripts.append(Script('Test - keep targets', [],
                           [('UNIT_SET_HEALTH', m.role(r).name, 100.0)
                            for r in ('plant', 'barracks', 'tank')], once=False))
    # bench round 154, all three alike: the miner harvests on its own (default team, moving from f9, near s17), the
    # SimpleExpansion team is made empty at f152 and again f230 -- the placed miner is never taken, nor the escorts;
    # no outpost to s68. (The prediction, the model taking the miner: outpost s15 within 150 -- refuted.)
    t.expect += [('前哨', 30, '==', 0, 60), ('矿车近', 30, '==', 1, 60), ('坦克东', 30, '==', 0, 60)]
    t.bench = [('bench_watch', dict(seconds=60, every=1, sheet=False, lines=4))]
    return t


CHECKS = {key: {'a': a} for key in ('aiexpse', 'aiexpd50', 'aiexpd400')}
