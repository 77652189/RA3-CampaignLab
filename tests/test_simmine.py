"""Mining and money as rules (simmine.Mining L2, simmoney.Money L4; ADR 0029 "测试分两层"): the minimal world, only
the subsystem asked about. Whole-mission versions against the bench: tests/test_simbench.py mining / money cap /
sharing."""
from types import SimpleNamespace

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.objects.mine as simmine  # noqa: E402
import engine.players.money as simmoney  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402


def test_a_miner_unloads_a_load_8_a_frame_and_the_rest_on_the_last():
    s = simsmall.small_world([('ref', 'AlliedRefinery', 'Player_1', 0.0, 0.0),
                              ('node', 'OreNode', 'PlyrCivilian', 300.0, 0.0),
                              ('miner', 'AlliedMiner', 'Player_1', 150.0, 60.0)])
    paid = []
    mining = simmine.Mining()
    for frame in range(1, 900):
        mining.mine_due(s, frame, lambda owner, give: paid.append((owner, give)))
    assert paid, 'no load came back in 60 s'
    first = [give for _, give in paid[:simmine.MINE_DOCK]]
    assert first == [8] * (simmine.MINE_DOCK - 1) + [simmine.MINE_LOAD - 8 * (simmine.MINE_DOCK - 1)]
    assert {owner for owner, _ in paid} == {'Player_1'}
    assert s.bodies['miner'].mine['node'] == 'node'


def test_sharing_splits_a_deposit_among_sharing_friends_and_the_cap_refuses_a_whole_deposit():
    world = SimpleNamespace(relations={('A', 'B'): 'Friend', ('A', 'C'): 'Friend', ('A', 'D'): 'Enemy'})
    m = simmoney.Money()
    m.sharing |= {'A', 'B', 'C', 'D'}
    m.earn(world, 'A', 250)
    assert m.money == {'B': 83, 'C': 83, 'A': 84}          # two friends share: 250 // 3 each, the rest kept
    m.money_cap['B'] = 90
    m.earn(world, 'A', 30)                                 # B's 10 would pass its cap: not paid at all
    assert m.money['B'] == 83 and m.money['C'] == 93 and m.money['A'] == 94


def test_collect_applies_the_ai_income_multiplier_and_carries_the_fraction():
    world = SimpleNamespace(relations={})
    m = simmoney.Money()
    m.income['AI'] = (1.5, 0.0)
    m.collect(world, 'AI', 8)
    m.collect(world, 'AI', 9)                              # 12, then 13.5 -> 13 paid, 0.5 carried
    assert m.money['AI'] == 25 and m.income['AI'] == (1.5, 0.5)
