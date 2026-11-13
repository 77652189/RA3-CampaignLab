"""C Expansion interface checks and named bench replay; see work/re/c_expansion_probe_report.md."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
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
    ai = SimpleNamespace(enemy_table=None, rng=None, data=SimpleNamespace(state=lambda sid: state), log=[])
    block.tick(ai, 1)
    assert [block.slot_target('s', n) for n in (0, 1)] == ['exp:a', 'exp:b']
    assert [(block.points[k].x, block.points[k].y) for k in ('exp:a', 'exp:b')] == [(100, 200), (500, 600)]
    assert calls == [(h.base_selection, (0, 0))] * 2


@pytest.mark.xfail(strict=True, reason='Expansion selected the east ore node on the bench; '
                   'automatic candidate eligibility/base discovery is still absent; '
                   'see work/re/c_expansion_probe_report.md and handoff-c.md')
def test_expansion_named_bench_replay():
    w = simai.run('aiexpc', 'a', until=31)
    labels = [label for _, label in w.sim.test.counters]
    row = dict(zip(labels, w.sim.series[-1][1]))
    # Bench aiexpc:a, seconds 22..32: four at east, none at bluff or entity.
    assert (row['候选东'], row['候选崖'], row['普通实体']) == (4, 0, 0)


def test_expansion_named_entity_control_replay():
    w = simai.run('aiexpctl', 'a', until=31)
    labels = [label for _, label in w.sim.test.counters]
    row = dict(zip(labels, w.sim.series[-1][1]))
    assert (row['候选东'], row['候选崖'], row['普通实体']) == (0, 0, 4)


@pytest.mark.parametrize('build', ['aibsold', 'aibsnew'])
@pytest.mark.xfail(strict=True, reason='BaseSelection.SortOrder contrast retains the east ore selection; '
                   'automatic candidate/base discovery is absent and eligible base ages are unobserved; '
                   'see work/re/c_basesort_report.md and handoff-c.md')
def test_base_sort_named_bench_replay(build):
    w = simai.run(build, 'a', until=31)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    # Raw engine readings, not a rule for sorting bases; both layouts are identical.
    assert (row['候选东'], row['候选崖'], row['普通实体']) == (4, 0, 0)


@pytest.mark.parametrize('build', ['aibncap', 'aibnnone'])
@pytest.mark.xfail(strict=True, reason='PreferredNotBaseTypes CAPTURED/empty both select east on the bench; '
                   'automatic candidate discovery is absent; base type/eligibility/selection is unobserved; '
                   'see work/re/c_basenot_report.md and handoff-c.md')
def test_base_preferred_not_named_bench_replay(build):
    w = simai.run(build, 'a', until=31)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    # Retain raw bench counts, without inferring base type or preference scores.
    assert (row['候选东'], row['候选崖'], row['普通实体']) == (4, 0, 0), row


def test_dual_base_candidate_registration():
    """D98 base table: physical scripted yard does not register a second AI base."""
    w = simai.run('aibs2old', 'a', until=19)
    brain = next(iter(w.brains.values()))
    h = brain.targets.tdata.heuristic('CNVExpansion')
    candidates = brain.view.expansion_candidates(h, brain.home)
    assert len(brain.yards()) == 2
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
    w = simai.run(build, 'a', until=65)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert (row['候选东'], row['候选崖'], row['普通实体']) == (4, 0, 0), row


@pytest.mark.parametrize('build', ['aibs2old', 'aibs2new'])
def test_dual_base_physical_yards_named_bench_replay(build):
    """The b check distinguishes physical creation from AI base eligibility."""
    w = simai.run(build, 'b', until=31)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert (row['东建厂'], row['崖建厂']) == (1, 1), row


@pytest.mark.parametrize('build,expected', [('aibs3old', (4, 0, 1, 1)),
                                            ('aibs3new', (0, 0, 1, 1))])
def test_initial_dual_base_counts_named_bench_replay(build, expected):
    """Raw s55..65 counts; NEW's absence at ore is not a base-selection failure."""
    w = simai.run(build, 'b', until=65)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert tuple(row[k] for k in ('候选东', '候选崖', '东建厂', '崖建厂')) == expected, row


@pytest.mark.parametrize('build,base_id,point', [
    ('aibs3old', 0, (4172.7, 2987.3)),
    ('aibs3new', 1, (3400.3, 1300.3)),
])
def test_initial_dual_base_sort_named_bench_replay(build, base_id, point):
    """Initial-yard base table and OLD/NEW choice; see work/re/c_bs3_report.md."""
    w = simai.run(build, 'b', until=19)
    brain = next(iter(w.brains.values()))
    h = brain.targets.tdata.heuristic('CNVExpansion')
    assert len(brain.expansion_initial_yards) == 2
    candidates = brain.view.expansion_candidates(h, brain.home)
    assert [c.base_id for c in candidates] == [base_id]
    picked = simai.model()['targets'].find(h, brain.view, brain.home)
    assert (picked.x, picked.y) == pytest.approx(point, abs=0.1)
    row = dict(zip([label for _, label in w.sim.test.counters], w.sim.series[-1][1]))
    assert (row['东建厂'], row['崖建厂']) == (1, 1), row
