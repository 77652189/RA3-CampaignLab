"""Engine unit test: ore mining (ADR 0019 layer 2; docs/engine/mining.md) -- the trip, what a load is worth, when the
money comes, two collectors on one node.

On the probe range's ore pad (maps/probe_range.py 'probe refinery': a refinery facing 45 with one OreNode 180 ahead)
an Allied refinery is placed; it gives its own collector on unpacking (SpawnBehavior SpawnOnUnpack, round 39). The
player's money is set to 0 at the start.

  a  one      the refinery's collector alone
  b  two      as a, plus one AlliedMiner placed beside the refinery: two collectors on one node
  c  legs     as a; where the collector is, to tell the drive from the docks

Counters (four lines), frames from the mission's first frame:
  a  资金 the money; 首笔 frames while the money is 0; 收满 while it is below LOAD; 二笔 while it is below LOAD + 1
  b  资金; 首笔 (< 1), 二笔 (< LOAD + 1), 三笔 (< 2 LOAD + 1)
  c  资金; 到矿 frames until a collector is first in the square around the node; 离矿 until it has left that
     square again; 到场 until it is in the refinery's square after that
  d  as b; frames (summed) with: 名车 the placed collector in c's node square, 一车 at least one collector there,
     两车 both there (which of the two works?)
  e  as d, the placed collector deleted once the money reaches LOAD (does the waiting one get the dock then?)
  f  as b; 首笔; 自到矿 frames until a collector other than the placed one is first in c's node square; 名到矿 until
     the placed one is (does the refinery's own come later, or come first and still wait?)

Bench 11-05 (round 43; docs/engine/mining.md):
  a CampMineA_mcp_1105_201253: 首笔 239, 收满 268 (8 a frame: 16 / 72 / 128 / 200 at 2 / 9 / 16 / 25 frames, then 250),
    二笔 508; 250 more every 269 frames, 1000 by s69.
  b CampMineB_mcp_1105_201544: 首笔 290, 二笔 559, 三笔 828: one collector's income, at a's period.
  c CampMineC_mcp_1105_201837: 到矿 56, 离矿 71, 到场 226, money from 239 -- the node's square (half side 70) misses
    where it docks: the collector only passes through it.
  d CampMineD_mcp_1105_203036: 名车 64 frames in a row each trip, 一车 - 名车 9 frames in 45 s, 两车 0: the placed one
    works; the refinery's own reaches the node later and waits outside for good.
  e CampMineE_mcp_1105_203435: the placed one deleted at s19: the money stays 250 to s61, nobody in the square.
Bench 2026-11-12 (round 178):
  f CampMineF_mcp_1112_095956: 首笔 290 (b's), 名到矿 107, 自到矿 121 -- alone (c) the refinery's own is in the square
    at 56: the placed one, standing by the refinery, holds it up ~65 frames, so it comes second and waits for good.
    (Round 178 read it as a collision; round 189 below shows it is not.)
  g  as f, plus 自离场 frames until the refinery's own has left the pad square (half side 50) it fades in in
  h  g with the placed one deleted at the start (the own one alone)
  mineaway g  g's counters, the placed one AWAY south-east (its drive clear of the refinery and the own one's way)
Bench 2026-11-12 (round 189, work/bench_results/engine_mining__g / __h / mineaway__g.json): 首笔 / 自离场 / 自到矿 /
  名到矿 -- g 290 / 19 / 121 / 107, h 239 / 19 / 56 / -, mineaway g 261 / 19 / 170 / 114. The own one leaves its pad at
  19 every time (not held at its way out), and with the placed one far away it still comes second and waits for
  good: the placed one, made before the refinery's own fades in, claims the node when it looks for it (H2 of
  round 177, which round 178 had ruled out on f's arrival frames alone); the waiting one's square entry is where it
  waits, not an arrival. Sim: sim.Sim._claimed.
Against the model (RA3-EngineModel mining.py, round 43; tests/test_objects_bench.py mining): a, b, e the same with the
drives fitted (spawn -> node 101, node <-> refinery 104, placed -> node 153); b's period and the stuck collector are
predictions. c and d need motion (not compared).
"""
import dataclasses
import math

from maps import probe_range
from parts import Mission, Script, Test, counted, square

MINER, REFINERY = 'AlliedMiner', 'AlliedRefinery'
SITE = 'probe refinery'
LOAD = 250                                  # OreMinerBehavior DeliveryCapacity / OreNodeBehavior DeliveryAmount
RUN = {'a': 75.0, 'b': 75.0, 'c': 45.0, 'd': 45.0, 'e': 60.0, 'f': 30.0, 'g': 30.0, 'h': 30.0}
PLACED = (-110.0, 0.0)                      # b, d: the second collector, from the pad
PAD = (probe_range.SITES[SITE].x, probe_range.SITES[SITE].y)
NODE = probe_range.OBJECTS[0].x, probe_range.OBJECTS[0].y
NODE_R, PAD_R = 70.0, 50.0                  # the squares' half sides (the node 127 + 127 from the pad)


def _n(part):
    return f'UNIT - CNV Mine {part}'


def mission():
    m = Mission(name='CampMine', map=probe_range, units=[], facts={})
    m.put(REFINERY, SITE, role='refinery', name=_n('Refinery'))
    m.put(MINER, SITE, *PLACED, angle=0.0, role='miner', name=_n('Miner'))   # b only (deleted at the start else)
    m.spawns.add(MINER)
    return m


def _below(t, counter, label, limit):
    """counter: frames while the money is below limit (the first frame at or above it stops it)."""
    t.counters.append((counter, label))
    t.scripts.append(Script(f'Test - {counter}', [('COUNTER', 'CNV_Mine_Money', 0, limit)],
                            [('INCREMENT_COUNTER', 1, counter)], once=False))


def _until(t, counter, label, flag, cond, after=None):
    """counter: frames until cond first holds (after flag `after` is set); then flag is set."""
    t.counters.append((counter, label))
    gate = [('FLAG', after, 1)] if after else []
    t.scripts.append(Script(f'Test - {counter}', [('FLAG', flag, 0)], [('INCREMENT_COUNTER', 1, counter)], once=False))
    t.scripts.append(Script(f'Test - {counter} seen', gate + [cond], [('SET_FLAG', flag, 1)]))


def mining_test(m, which='a'):
    t = Test()
    p1 = m.player('p1')
    start = [('MAP_REVEAL_ALL_PERM', p1), ('PLAYER_SET_MONEY', p1, 0)]
    if which not in 'bdefg':
        start.append(('NAMED_DELETE', _n('Miner')))
    t.scripts.append(Script('Test - start', [], start))
    t.counters.append(('CNV_Mine_Money', '资金'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', p1, 'CNV_Mine_Money')], once=False))
    if which == 'a':
        _below(t, 'CNV_Mine_First', '首笔', 1)
        _below(t, 'CNV_Mine_Full', '收满', LOAD)
        _below(t, 'CNV_Mine_Second', '二笔', LOAD + 1)
    elif which == 'b':
        _below(t, 'CNV_Mine_First', '首笔', 1)
        _below(t, 'CNV_Mine_Second', '二笔', LOAD + 1)
        _below(t, 'CNV_Mine_Third', '三笔', 2 * LOAD + 1)
    elif which == 'f':
        t.areas['Test Node'] = square(*NODE, NODE_R)
        placed_in = ('NAMED_INSIDE_AREA', _n('Miner'), 'Test Node')
        _below(t, 'CNV_Mine_First', '首笔', 1)
        _until(t, 'CNV_Mine_OwnAt', '自到矿', 'Test Own At',
               ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', 3, 1, MINER, 'Test Node'))
        t.scripts[-1].when.append(placed_in + ('NOT',))
        _until(t, 'CNV_Mine_PlacedAt', '名到矿', 'Test Placed At', placed_in)
    elif which in 'gh':                     # round 189: f's two arrivals and when the refinery's own leaves its pad
        t.areas['Test Node'] = square(*NODE, NODE_R)
        t.areas['Test Pad'] = square(*PAD, PAD_R)
        placed_in = ('NAMED_INSIDE_AREA', _n('Miner'), 'Test Node')
        in_pad = lambda k, op: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', op, k,  # noqa: E731
                                MINER, 'Test Pad')
        _below(t, 'CNV_Mine_First', '首笔', 1)
        t.scripts.append(Script('Test - own in pad', [in_pad(1, 3)], [('SET_FLAG', 'Test Own In Pad', 1)]))
        _until(t, 'CNV_Mine_OwnOut', '自离场', 'Test Own Out', in_pad(0, 2), after='Test Own In Pad')
        _until(t, 'CNV_Mine_OwnAt', '自到矿', 'Test Own At',
               ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', 3, 1, MINER, 'Test Node'))
        t.scripts[-1].when.append(placed_in + ('NOT',))
        _until(t, 'CNV_Mine_PlacedAt', '名到矿', 'Test Placed At', placed_in)
        t.counters = t.counters[1:]             # the money's own counter not shown: four lines
    elif which in 'de':
        if which == 'e':                    # the worker (d: the placed one) goes once the first load is in
            t.scripts.append(Script('Test - worker gone', [('COUNTER', 'CNV_Mine_Money', 3, LOAD)],
                                    [('NAMED_DELETE', _n('Miner'))]))
        t.areas['Test Node'] = square(*NODE, NODE_R)
        has = lambda k: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', 3, k, MINER,  # noqa: E731
                         'Test Node')
        for counter, label, cond in (
                ('CNV_Mine_Named', '名车', ('NAMED_INSIDE_AREA', _n('Miner'), 'Test Node')),
                ('CNV_Mine_Any', '一车', has(1)), ('CNV_Mine_Two', '两车', has(2))):
            t.counters.append((counter, label))
            t.scripts.append(Script(f'Test - {counter}', [cond], [('INCREMENT_COUNTER', 1, counter)], once=False))
    else:
        t.areas['Test Node'] = square(*NODE, NODE_R)
        t.areas['Test Pad'] = square(*PAD, PAD_R)
        has = lambda area, k=1, op=3: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', op, k,  # noqa
                                        MINER, area)
        _until(t, 'CNV_Mine_AtNode', '到矿', 'Test At Node', has('Test Node'))
        _until(t, 'CNV_Mine_LeftNode', '离矿', 'Test Left Node', has('Test Node', 0, 2), after='Test At Node')
        _until(t, 'CNV_Mine_AtPad', '到场', 'Test At Pad', has('Test Pad'), after='Test Left Node')
    t.expect = [('首笔', 0, 'ever>=', 1, RUN[which])] if which in 'gh' else [('资金', 0, 'ever>=', LOAD, RUN[which])]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=RUN[which]))]
    return t


# Round 174 (the miner's drive by the node's facing): retail stands every node facing its refinery (node angle =
# the refinery's + 180: heidelberg, gibraltar, north sea, all six pairs), the generator (resources.objects) put it
# at 0 till round 175 (probe_range keeps that: NODES = resources.MEASURED) -- 135 off on this pad (a's 104-frame
# leg), 45 off on niagara's east pad (aitowerinc5 f: a trip of 185).
# mineturn<k>: this pad with its node turned to retail's facing + k degrees (m: minus), nothing else changed; check p
# = a's start (the refinery's own collector) with b's three counters (the period twice).
# Bench 2026-11-12 (work/bench_results/mineturn*__p.json, runs CampMineT<k>P_mcp_1112_01*): 首笔 / 二笔 / 三笔
#   0: 111 / 262 / 413 (trip 151)    45: 156 / 342 / 528 (186)    -45: 157 / 344 / 531 (187)
#   90: 214 / 455 / 696 (241)        -90: 214 / 455 / 696 (241)   180: 296 / 619 / 942 (323)
# with a's 269 at 135: the drive round a node turned away (sim.MINE_TURN_EXTRA; tests/test_simbench.py mining).
TURNS = (0, 45, 90, 180, -45, -90)


def _turned(k):
    """probe_range with its one node turned to face the refinery + k degrees."""
    import types
    mp = types.ModuleType(probe_range.__name__)
    mp.__dict__.update({n: v for n, v in vars(probe_range).items() if not n.startswith('__')})
    face = math.radians(probe_range.FIELDS[0].facing + 180.0 + k)
    mp.OBJECTS = [dataclasses.replace(o, angle=face) if o.template == 'OreNode' else o for o in probe_range.OBJECTS]
    assert sum(o.template == 'OreNode' for o in mp.OBJECTS) == 1
    return mp


def _tag(k):
    return f'{k}' if k >= 0 else f'm{-k}'


def turned_mission(k):
    m = mission()
    m.map, m.name = _turned(k), f'CampMineT{_tag(k)}'
    return m


def turned_test(m):
    t = mining_test(m, 'a')
    t.counters = [c for c in t.counters if c[0] == 'CNV_Mine_Money']
    t.scripts = [s for s in t.scripts if s.name in ('Test - start', 'Test - money')]
    _below(t, 'CNV_Mine_First', '首笔', 1)
    _below(t, 'CNV_Mine_Second', '二笔', LOAD + 1)
    _below(t, 'CNV_Mine_Third', '三笔', 2 * LOAD + 1)
    return t


FAR = 38.0              # minefar: the refinery this much further back from its node (contract: 180 +- 40, AXIS_SLACK)


def far_mission():
    """mineturn0 with the refinery FAR further back (240 from its node, still facing it): a longer drive at retail's
    facing -- does the trip grow by the drive (2 x 11 frames), or is the node's own cycle (151) what bounds it?
    Bench 2026-11-12 (work/bench_results/minefar__p.json / __q.json): p 133 / 288 / 443 (a trip of 155) -- the
    round-179 sim's prediction to the frame (a 36-frame leg at 0 and the node's 151; the old 45-frame leg said 144 /
    317 / 490); q 133 / 34 / 107 / 190."""
    m = Mission(name='CampMineFar', map=_turned(0), units=[], facts={})
    back = math.radians(probe_range.FIELDS[0].facing)
    dx, dy = -FAR * math.cos(back), -FAR * math.sin(back)
    m.put(REFINERY, SITE, dx, dy, role='refinery', name=_n('Refinery'))
    m.put(MINER, SITE, dx + PLACED[0], dy + PLACED[1], angle=0.0, role='miner', name=_n('Miner'))   # deleted
    m.spawns.add(MINER)
    return m


def legs_test(m):
    """q (round 179): p's start with the legs apart -- 首笔; 到矿 / 离矿 frames until the collector is first in / out
    of c's node square; 二到矿 until it is in it again (the second leg starts as the unloading ends, 首笔 + 30).
    Bench 2026-11-12: mineturn0 q (CampMineT0Q_mcp_1112_101613) 111 / 23 / 96 / 156 -- 73 frames at the node the
    first time, 91 after: the node's cycle (151) bounds retail's facing, a leg is 36; the first leg 8 longer from
    where the collector faded in (15 from the dock). At 45 / 90 / 180 the drive round the node goes in and out of the
    square (90: 77 / 151 / 191 before its 首笔 214): no legs to read there."""
    t = mining_test(m, 'a')
    t.counters = [c for c in t.counters if c[0] == 'CNV_Mine_Money']
    t.scripts = [s for s in t.scripts if s.name in ('Test - start', 'Test - money')]
    _below(t, 'CNV_Mine_First', '首笔', 1)
    t.areas['Test Node'] = square(*NODE, NODE_R)
    has = lambda k=1, op=3: ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', 'Player_1', op, k,  # noqa: E731
                             MINER, 'Test Node')
    _until(t, 'CNV_Mine_AtNode', '到矿', 'Test At Node', has())
    _until(t, 'CNV_Mine_LeftNode', '离矿', 'Test Left Node', has(0, 2), after='Test At Node')
    _until(t, 'CNV_Mine_AtNode2', '二到矿', 'Test At Node 2', has(), after='Test Left Node')
    t.counters = t.counters[1:]                 # the money's own counter not shown: four lines
    t.expect = [('首笔', 0, 'ever>=', 1, 30.0)]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=len(t.counters), seconds=30.0))]
    return t


# mineniag (round 176): niagara as the generator now makes it (round 175: its nodes at retail's facing, not the
# benches' resources.measured copy), the player's refinery on the east pad (A7's ore), check p as mineturn's. The
# simulator's prediction: the trip of mineturn0 p, 151 (tests/test_simbench.py niagara_at_retail).
# Bench 2026-11-12 (work/bench_results/mineniag__p.json, run CampMineNiagP_mcp_1112_045758): 首笔 / 二笔 / 三笔
#   111 / 262 / 413 -- a trip of 151, as predicted (mineturn0 p's very numbers); 1910 by s77.
NIAGARA_SITE = 'east refinery'


def niagara_mission():
    from maps import niagara
    m = Mission(name='CampMineNiag', map=niagara, units=[], facts={})
    m.put(REFINERY, NIAGARA_SITE, role='refinery', name=_n('Refinery'))
    m.put(MINER, NIAGARA_SITE, *PLACED, angle=0.0, role='miner', name=_n('Miner'))   # deleted at the start
    m.spawns.add(MINER)
    return m


AWAY = (300.0, -200.0)      # mineaway: the placed collector south-east of the pad, its drive to the node clear of the
                            # refinery (171 off its centre) and of the own one's way out


def away_mission():
    """engine_mining with the placed collector AWAY (round 189): is the refinery's own held up by it only when it
    stands by the refinery (f)?"""
    m = Mission(name='CampMineAway', map=probe_range, units=[], facts={})
    m.put(REFINERY, SITE, role='refinery', name=_n('Refinery'))
    m.put(MINER, SITE, *AWAY, angle=0.0, role='miner', name=_n('Miner'))
    m.spawns.add(MINER)
    return m


MISSION = {'engine_mining': mission, 'mineaway': away_mission, 'mineniag': niagara_mission, 'minefar': far_mission,
           **{f'mineturn{_tag(k)}': (lambda k=k: turned_mission(k)) for k in TURNS}}
CHECKS = {'engine_mining': {w: (lambda m, w=w: mining_test(m, w)) for w in 'abcdefgh'},
          'mineaway': {'g': lambda m: mining_test(m, 'g')}, 'mineniag': {'p': turned_test},
          'minefar': {'p': turned_test, 'q': legs_test},
          **{f'mineturn{_tag(k)}': {'p': turned_test, 'q': legs_test} for k in TURNS}}
