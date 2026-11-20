"""C Expansion interface checks and named bench replay; see work/re/c_expansion_probe_report.md."""
import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


def test_expansion_interface_preserves_selection_and_slot_points(tmp_path):
    tg = simai.model()['targets']
    data = tg.TargetData(str(tmp_path))
    data.add_text('''<AssetDeclaration>
      <AITargetingHeuristic id="base" HeuristicType="Expansion" RequireUniqueTarget="true">
        <BaseSelection PreferredBaseTypes="MAIN_BASE" PreferredNotBaseTypes="CAPTURED"
                       SortOrder="PREFER_OLDEST"/>
      </AITargetingHeuristic>
      <AITargetingHeuristic id="derived" inheritFrom="base"/>
    </AssetDeclaration>''')
    h = data.heuristic('derived')
    assert h.base_selection.preferred == frozenset({'MAIN_BASE'})
    assert h.base_selection.preferred_not == frozenset({'CAPTURED'})
    assert h.base_selection.sort_order == 'PREFER_OLDEST'
    view = tg.View('ai', [tg.Thing(42, 'ai', x=10)])
    assert tg.find(h, view, (0, 0)) is None
    candidates = [tg.ExpansionCandidate('exp:a', 100, 200, base_id=7,
                                       base_types=frozenset({'MAIN_BASE'}), age=30),
                  tg.ExpansionCandidate('exp:b', 500, 600, base_id=7)]
    calls = []
    def provider(heuristic, base):
        calls.append((heuristic.base_selection, base))
        return candidates
    view.expansion_candidates = provider
    state = SimpleNamespace(targets=[('derived', 10)], max_targets=2)
    block = tg.TargetsBlock(data, lambda ai, frame: ['s'], lambda ai, frame: view,
                            lambda ai, sid: (0, 0))
    # start: the AI has had 'make base'; before it only targets found by name resolve (model 2b6b95b)
    ai = SimpleNamespace(enemy_table=None, rng=None, start=0, data=SimpleNamespace(state=lambda sid: state), log=[])
    block.tick(ai, 1)
    assert [block.slot_target('s', n) for n in (0, 1)] == ['exp:a', 'exp:b']
    assert [(block.points[k].x, block.points[k].y) for k in ('exp:a', 'exp:b')] == [(100, 200), (500, 600)]
    assert calls == [(h.base_selection, (0, 0))] * 2


def test_expansion_named_bench_replay():
    w = simai_run.run('aiexpc', 'a', until=31)
    labels = [label for _, label in w.sim.test.counters]
    row = dict(zip(labels, w.sim.series[-1][1]))
    # Bench aiexpc:a, seconds 22..32: four at east, none at bluff or entity.
    assert (row['候选东'], row['候选崖'], row['普通实体']) == (4, 0, 0)


def test_expansion_named_entity_control_replay():
    w = simai_run.run('aiexpctl', 'a', until=31)
    labels = [label for _, label in w.sim.test.counters]
    row = dict(zip(labels, w.sim.series[-1][1]))
    assert (row['候选东'], row['候选崖'], row['普通实体']) == (0, 0, 4)


@pytest.mark.parametrize('build', ['aibsold', 'aibsnew'])
def test_base_sort_named_bench_replay(build):
    w = simai_run.run(build, 'a', until=31)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    # Raw engine readings, not a rule for sorting bases; both layouts are identical.
    assert (row['候选东'], row['候选崖'], row['普通实体']) == (4, 0, 0)


@pytest.mark.parametrize('build', ['aibncap', 'aibnnone'])
def test_base_preferred_not_named_bench_replay(build):
    w = simai_run.run(build, 'a', until=31)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    # Retain raw bench counts, without inferring base type or preference scores.
    assert (row['候选东'], row['候选崖'], row['普通实体']) == (4, 0, 0), row


def test_dual_base_candidate_registration():
    """D98 base table: physical scripted yard does not register a second AI base."""
    w = simai_run.run('aibs2old', 'a', until=19)
    brain = next(iter(w.brains.values()))
    h = brain.targets.tdata.heuristic('CNVExpansion')
    candidates = brain.view.expansion_candidates(h, brain.home)
    assert sum(b.owner == brain.player and 'CONSTRUCTION_YARD' in b.kinds for b in w.sim.living()) == 2
    assert len(candidates) == 1
    assert candidates[0].base_id == 0
    assert (candidates[0].x, candidates[0].y) == pytest.approx((4172.7, 2987.3), abs=0.1)
    # The unregistered physical yard cannot change the one registered candidate.
    w.sim.bodies['UNIT - CNV BS New Yard'].alive = False
    remaining = brain.view.expansion_candidates(h, brain.home)
    assert [c.base_id for c in remaining] == [candidates[0].base_id]


@pytest.mark.parametrize('build', ['aibs2old', 'aibs2new'])
def test_dual_base_sort_named_bench_replay(build):
    """Retain engine counts, without claiming two yards imply two eligible bases."""
    w = simai_run.run(build, 'a', until=65)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert (row['候选东'], row['候选崖'], row['普通实体']) == (4, 0, 0), row


@pytest.mark.parametrize('build', ['aibs2old', 'aibs2new'])
def test_dual_base_physical_yards_named_bench_replay(build):
    """The b check distinguishes physical creation from AI base eligibility."""
    w = simai_run.run(build, 'b', until=31)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert (row['东建厂'], row['崖建厂']) == (1, 1), row


@pytest.mark.parametrize('build,scores,base_id,point', [
    ('aibn2old', (0, 1), 1, (3400.3, 1300.3)),
    ('aibn2new', (1, 0), 0, (4172.7, 2987.3)),
])
def test_initial_dual_preferred_not_selection_replay(build, scores, base_id, point, monkeypatch):
    """Same-frame eligible base scores and choice; work/re/c_bn2_report.md."""
    tg = simai.model()['targets']
    select = tg.select_expansion_base
    seen = []

    def observe(selection, candidates):
        seen.append((selection, list(candidates)))
        return select(selection, candidates)

    monkeypatch.setattr(tg, 'select_expansion_base', observe)
    w = simai_run.run(build, 'b', until=19)
    brain = next(iter(w.brains.values()))
    h = brain.targets.tdata.heuristic('CNVExpansion')
    picked = tg.find(h, brain.view, brain.home)
    selection, candidates = seen[-1]
    assert selection.sort_order == 'PREFER_OLDEST'
    assert [c.base_id for c in candidates] == [0, 1]
    assert [c.base_types for c in candidates] == [
        frozenset({'MAIN_BASE', 'OLDEST_OF_TYPE'}),
        frozenset({'MAIN_BASE', 'MOST_RECENT_OF_TYPE'}),
    ]
    assert tuple(len(selection.preferred & c.base_types)
                 - len(selection.preferred_not & c.base_types) for c in candidates) == scores
    assert select(selection, candidates) == base_id
    assert (picked.x, picked.y) == pytest.approx(point, abs=0.1)


@pytest.mark.parametrize('build,expected', [('aibn2old', (0, 0, 1, 1)),
                                            ('aibn2new', (4, 0, 1, 1))])
def test_initial_dual_preferred_not_counts_replay(build, expected):
    """Keep the four raw bench counts separate from the base selection verdict."""
    w = simai_run.run(build, 'b', until=65)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert tuple(row[k] for k in ('候选东', '候选崖', '东建厂', '崖建厂')) == expected, row


@pytest.mark.parametrize('build,preferred,scores,base_id,point', [
    ('aibp1old', 'OLDEST_OF_TYPE', (1, 0), 0, (4172.7, 2987.3)),
    ('aibp1new', 'MOST_RECENT_OF_TYPE', (0, 1), 1, (3400.3, 1300.3)),
])
def test_initial_dual_preferred_selection_replay(build, preferred, scores, base_id, point, monkeypatch):
    """Same-frame eligible base scores and choice; work/re/c_bp1_report.md."""
    tg = simai.model()['targets']
    select = tg.select_expansion_base
    seen = []

    def observe(selection, candidates):
        seen.append((selection, list(candidates)))
        return select(selection, candidates)

    monkeypatch.setattr(tg, 'select_expansion_base', observe)
    w = simai_run.run(build, 'b', until=19)
    brain = next(iter(w.brains.values()))
    h = brain.targets.tdata.heuristic('CNVExpansion')
    picked = tg.find(h, brain.view, brain.home)
    selection, candidates = seen[-1]
    assert selection.sort_order == 'PREFER_OLDEST'
    assert selection.preferred == frozenset({preferred})
    assert selection.preferred_not == frozenset()
    assert [c.base_id for c in candidates] == [0, 1]
    assert [c.base_types for c in candidates] == [
        frozenset({'MAIN_BASE', 'OLDEST_OF_TYPE'}),
        frozenset({'MAIN_BASE', 'MOST_RECENT_OF_TYPE'}),
    ]
    assert tuple(len(selection.preferred & c.base_types)
                 - len(selection.preferred_not & c.base_types) for c in candidates) == scores
    assert select(selection, candidates) == base_id
    assert (picked.x, picked.y) == pytest.approx(point, abs=0.1)


@pytest.mark.parametrize('build,expected', [('aibp1old', (4, 0, 1, 1)),
                                          ('aibp1new', (0, 0, 1, 1))])
def test_initial_dual_preferred_counts_replay(build, expected):
    """Four raw s55..65 counts, independent of the base-choice verdict."""
    w = simai_run.run(build, 'b', until=65)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert tuple(row[k] for k in ('候选东', '候选崖', '东建厂', '崖建厂')) == expected, row


@pytest.mark.parametrize('build,expected', [('aibs3old', (4, 0, 1, 1)),
                                            ('aibs3new', (0, 0, 1, 1))])
def test_initial_dual_base_counts_named_bench_replay(build, expected):
    """Raw s55..65 counts; NEW's absence at ore is not a base-selection failure."""
    w = simai_run.run(build, 'b', until=65)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert tuple(row[k] for k in ('候选东', '候选崖', '东建厂', '崖建厂')) == expected, row


@pytest.mark.parametrize('build,base_id,point', [
    ('aibs3old', 0, (4172.7, 2987.3)),
    ('aibs3new', 1, (3400.3, 1300.3)),
])
def test_initial_dual_base_sort_named_bench_replay(build, base_id, point):
    """Initial-yard base table and OLD/NEW choice; see work/re/c_bs3_report.md."""
    w = simai_run.run(build, 'b', until=19)
    brain = next(iter(w.brains.values()))
    h = brain.targets.tdata.heuristic('CNVExpansion')
    assert len(brain.expansion_initial_yards) == 2
    candidates = brain.view.expansion_candidates(h, brain.home)
    assert [c.base_id for c in candidates] == [base_id]
    picked = simai.model()['targets'].find(h, brain.view, brain.home)
    assert (picked.x, picked.y) == pytest.approx(point, abs=0.1)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert (row['东建厂'], row['崖建厂']) == (1, 1), row


def test_expansion_d104_candidate_readings_replay(tmp_path):
    """D104 aiexpc:a f151: three state-2 nodes, centre and final choice."""
    log_spec = importlib.util.spec_from_file_location(
        'expansion_teamlog', ROOT / 'experimental/cnv/teamlog.py')
    teamlog = importlib.util.module_from_spec(log_spec)
    log_spec.loader.exec_module(teamlog)
    p = tmp_path / 'ra3ext.log'
    p.write_text('expc: frame=151 ctr=3850.0:3400.0 mind=0.0 pick=44 n=3 '
                 'cand=44@4173:2987:2:-1/-1:best524,45@4279:3093:2:-1/-1:far,'
                 '46@3400:1300:2:-1/-1:far\n', encoding='utf-8')
    sample, = teamlog.expansion_candidates(str(p))
    assert sample['frame'] == 151 and sample['pick'] == 44
    assert [n['state'] for n in sample['candidates']] == [2, 2, 2]
    tg = simai.model()['targets']
    nodes = [tg.ExpansionOre(n['id'], *n['point'], state=n['state'],
                            occupied=False, blocked=False, water=False)
             for n in sample['candidates']]
    data = tg.TargetData(str(tmp_path))
    data.add_text('<AssetDeclaration><AITargetingHeuristic id="exp" '
                  'HeuristicType="Expansion" SearchRange="1" SortType="ThreatToGround" '
                  'Location="Land"/></AssetDeclaration>')
    picked = tg.select_expansion_ore(data.heuristic('exp'), tg.View('ai', []),
                                    sample['centre'], nodes)
    assert picked.id == sample['pick']
    assert (picked.x, picked.y) == (4173, 2987)


@pytest.mark.parametrize('build', ['aiexpse', 'aiexpd50', 'aiexpd400'])
def test_simple_expansion_placed_miner_named_bench_replay(build):
    w = simai_run.run(build, 'a', until=31)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    # Bench D round 154, all three: the placed miner harvests on its own to the field, the SimpleExpansion team
    # stays empty (miner and escorts never taken), no outpost.
    assert (row['前哨'], row['矿车近'], row['坦克东']) == (0, 1, 0), row


@pytest.mark.parametrize('build', ['aiexph200', 'aiexph50', 'aiexph400'])
def test_simple_expansion_built_miner_named_bench_replay(build):
    w = simai_run.run(build, 'a', until=31)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    # Bench D round 155, all three: refinery + money + a PRODUCTION deposit, no placed miner -- only the refinery's
    # free miner (harvesting the bluff); the SimpleExpansion team stays empty f152..f1741, no build order, no outpost.
    assert (row['前哨'], row['前哨近'], row['矿车']) == (0, 0, 1), row


# Bench D round 156 (aiexpb*: aiexph + the opener's `Build AlliedMiner`), counters at s130 (前哨, 前哨近, 矿车近):
# 400 -> outpost (3885, 2733) s95; 200 -> outpost (4012, 2903) s106; 50 -> no outpost, the miner idles 98 from the node.
OPENER_MINER_BENCH = {'aiexpb400': (1, 0, 0), 'aiexpb200': (1, 0, 0), 'aiexpb50': (0, 0, 1)}


@pytest.mark.parametrize('build', ['aiexpb200', 'aiexpb400', 'aiexpb50'])
def test_simple_expansion_unpacks_within_distance_named_bench_replay(build):
    # bench engine_aisimpleexp aiexpb400 / aiexpb200 / aiexpb50 (only Tactic.Distance differs).
    # D round 169, aiexpb50: the ore node blocks by its own bounding circle (Sim.blocks, 53; with the 40 a building
    # gets the miner's way to its slot slid 45 past it and unpacked) and a miner armed to unpack starts no ore trip
    # (Sim._mine: standing at its slot it was drawn onto the node). Gap left: it stands at (4180, 3060) (D176's
    # goal_off_nodes; before, its slot 67 from the node), the bench (4201, 3081), 98 -- node 45 by the slot not
    # explained (aiexpb50n without it: test_simple_expansion_miner_goal_moved_off_the_node_named_bench_replay).
    # D round 157: the opener's unit Build kept (opening.kept_orders, structures only), a HARVESTER the AI's
    # production made offered to teams, and the miner armed to unpack where it stands within Tactic.Distance
    # (TacticsBlock.approach, Sim.order_unpack here=True): simulator 400 unpacks s64, 200 s68 (bench s66 / s71).
    w = simai_run.run(build, 'a', until=130)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert (row['前哨'], row['前哨近'], row['矿车近']) == OPENER_MINER_BENCH[build], row


def test_simple_expansion_miner_goal_moved_off_the_node_named_bench_replay():
    # bench engine_aisimpleexp aiexpb50n (aiexpb50 without node 45; D175 run CampAIExpB50NA_mcp_1116_030239, ra3ext
    # team rows): the miner, sent to its slot (4215, 3039) 7 off node 44's base plate, turned off its straight way
    # at (4252, 3039) and stood at (4221, 3061) from f1116 to the end, no outpost. D176: Sim.goal_off_nodes moves the
    # goal to the nearest GRID corner whose 2 x 2 cells clear the plate, (4220, 3060).
    w = simai_run.run('aiexpb50n', 'a', until=130)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert row['前哨'] == 0, row
    miner, = [b for b in w.sim.living() if b.template == 'AlliedMiner' and b.name.startswith('#made')]
    assert math.hypot(miner.x - 4221, miner.y - 3061) <= 5, (miner.x, miner.y)
