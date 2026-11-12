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

Bench 11-05 (round 43; docs/engine/mining.md):
  a CampMineA_mcp_1105_201253: 首笔 239, 收满 268 (8 a frame: 16 / 72 / 128 / 200 at 2 / 9 / 16 / 25 frames, then 250),
    二笔 508; 250 more every 269 frames, 1000 by s69.
  b CampMineB_mcp_1105_201544: 首笔 290, 二笔 559, 三笔 828: one collector's income, at a's period.
  c CampMineC_mcp_1105_201837: 到矿 56, 离矿 71, 到场 226, money from 239 -- the node's square (half side 70) misses
    where it docks: the collector only passes through it.
  d CampMineD_mcp_1105_203036: 名车 64 frames in a row each trip, 一车 - 名车 9 frames in 45 s, 两车 0: the placed one
    works; the refinery's own reaches the node later and waits outside for good.
  e CampMineE_mcp_1105_203435: the placed one deleted at s19: the money stays 250 to s61, nobody in the square.
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
RUN = {'a': 75.0, 'b': 75.0, 'c': 45.0, 'd': 45.0, 'e': 60.0}
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
    if which not in 'bde':
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
    t.expect = [('资金', 0, 'ever>=', LOAD, RUN[which])]
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


MISSION = {'engine_mining': mission, **{f'mineturn{_tag(k)}': (lambda k=k: turned_mission(k)) for k in TURNS}}
CHECKS = {'engine_mining': {w: (lambda m, w=w: mining_test(m, w)) for w in 'abcde'},
          **{f'mineturn{_tag(k)}': {'p': turned_test} for k in TURNS}}
