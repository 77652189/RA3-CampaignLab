"""D round 154: SimpleExpansion readings (missions/aisimpleexp_bench.py; aiexpse / aiexpd50 / aiexpd400 differ in
Tactic.Distance only). Counters (four fit): the AI's outposts on the whole map, its outposts and miners within 150 of the Expansion pick
(bench aiexpc f151: (4173, 2987)), its Guardians in C's 350 square round the east candidate. The exact unpack point
and frame come from the CNVTeams host's cmd log (ra3ext.log). Expectations: the simulator's prediction (round 154).
"""
from parts import Test, Script, counted, square


def a(m):
    t = Test()
    s1 = m.player('s1')
    MINER, OUTPOST = m.facts['miner'], m.facts['outpost']
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


def h(m):
    """D round 155 (aiexph200 / aiexph50 / aiexph400): the AI builds the miner (refinery, money, a PRODUCTION
    deposit, no AlliedNeededUnits). Counters: outposts on the map, outposts within 150 of the pick, miners on the
    map, miners within 150 of the pick. The unpack point itself: the teams host's cmd log."""
    t = Test()
    MINER, OUTPOST = m.facts['miner'], m.facts['outpost']
    s1 = m.player('s1')
    near = 'CNV SExp near'
    t.areas[near] = square(*m.facts['expansion pick'], 150.0)
    counted('CNV_SExp_out', '前哨', t, template=OUTPOST, player=s1)
    counted('CNV_SExp_outnear', '前哨近', t, template=OUTPOST, player=s1, area=near, most=2)
    counted('CNV_SExp_miners', '矿车', t, template=MINER, player=s1, most=5)
    counted('CNV_SExp_minernear', '矿车近', t, template=MINER, player=s1, area=near, most=2)
    t.scripts.append(Script('Test - keep targets', [],
                           [('UNIT_SET_HEALTH', m.role(r).name, 100.0)
                            for r in ('plant', 'barracks', 'tank')], once=False))
    # bench round 155, all three alike (s1-s102..s126): one miner throughout (the refinery's free one, harvesting
    # the bluff), no outpost; the teams host: the SimpleExpansion team made f152 with n=0 and still n=0 at f1741,
    # no build order logged -- the CreateUnits slot orders no miner by itself (d154's H1 refuted).
    if not m.facts.get('opener builds miner'):
        t.expect += [('前哨', 30, '==', 0, 90), ('矿车', 30, '==', 1, 90), ('前哨近', 30, '==', 0, 90)]
    # bench round 156 (aiexpb*, the opener builds one miner): the SimpleExpansion team takes it at f465 with the four
    # Guardians; the miner unpacks the first frame it is within Distance of the Expansion node (400: f995 at
    # (3887, 2717), outpost (3885, 2733) counted s95; 200: f1061 at (3998, 2903), outpost (4012, 2903) s106); with
    # 50 the team's destination is 98 from the node, the miner never gets within 50 and never unpacks (to f1936).
    elif m.facts.get('gap node removed'):
        # D round 172 (aiexpb50n): the reading is the miner's stop in the teams host's log (it arrives ~f1150). The
        # watch is long (bench_watch runs at most 120 s a call): on 11-16 this map ran 1.6-6 logic frames a bench
        # second (11-15 02:52: 15), so 130 s ended near f800 with the miner still on its way.
        t.expect += [('前哨', 30, '==', 0, 480)]
        t.bench = [('bench_watch', dict(seconds=120, every=2, sheet=False, lines=4))] * 4
        return t
    elif m.facts['tactic distance'] == 50:
        t.expect += [('前哨', 30, '==', 0, 130), ('矿车近', 80, '==', 1, 130)]
    else:
        t.expect += [('前哨', 112, '==', 1, 130), ('前哨近', 30, '==', 0, 130)]
    t.bench = [('bench_watch', dict(seconds=130 if m.facts.get('opener builds miner') else 90, every=1,
                                    sheet=False, lines=4))]
    return t


CHECKS = {key: {'a': a} for key in ('aiexpse', 'aiexpd50', 'aiexpd400')}
CHECKS |= {key: {'a': h} for key in ('aiexph200', 'aiexph50', 'aiexph400', 'aiexpb200', 'aiexpb50', 'aiexpb400', 'aiexpb50n')}
